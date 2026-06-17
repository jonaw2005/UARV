from flask import Flask, Response, jsonify, request
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    from videostream.stream_api import generate
except Exception:
    generate = None

from mav_bridge import MAVBridge

app = Flask(__name__)

# Initialize a single shared MAVBridge instance and execution pool
bridge = MAVBridge("/dev/ttyAMA0", baud=57600)
bridge.connect()
executor = ThreadPoolExecutor(max_workers=2)

# Simple in-memory state
state = {
    'armed': False,
    'flying': False,
    'location': {'lat': 0.0, 'lon': 0.0},
}
state_lock = threading.Lock()


@app.route('/')
def index():
	return """
	<html>
		<body>
			<h1>Control API</h1>
			<p>Available endpoints: /video, /status, /location, /start, /land, /go_to</p>
		</body>
	</html>
	"""


@app.route('/video')
def video():
	if generate is None:
		return jsonify({'error': 'video stream not available'}), 503
	return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')




def run_task(fn, *args, **kwargs):
    return executor.submit(fn, *args, **kwargs)


@app.route('/arm', methods=['POST'])
def arm():
    future = run_task(bridge.arm)
    return jsonify({'status': 'arming requested', 'task_id': id(future)})


@app.route('/disarm', methods=['POST'])
def disarm():
    future = run_task(bridge.disarm)
    return jsonify({'status': 'disarming requested', 'task_id': id(future)})


@app.route('/mode', methods=['POST'])
def mode():
    data = request.get_json(force=True)
    if not data or 'mode' not in data:
        return jsonify({'error': 'mode is required'}), 400

    future = run_task(bridge.set_mode, data['mode'])
    return jsonify({'status': 'mode change requested', 'mode': data['mode'], 'task_id': id(future)})


@app.route('/velocity', methods=['POST'])
def velocity():
    data = request.get_json(force=True)
    if not data or any(k not in data for k in ('vx', 'vy', 'vz')):
        return jsonify({'error': 'vx, vy, vz are required'}), 400

    future = run_task(bridge.set_velocity, data['vx'], data['vy'], data['vz'])
    return jsonify({'status': 'velocity change requested', 'task_id': id(future)})


@app.route('/goto', methods=['POST'])
def goto():
    data = request.get_json(force=True)
    if not data or any(k not in data for k in ('lat', 'lon', 'alt')):
        return jsonify({'error': 'lat, lon, alt are required'}), 400

    future = run_task(bridge.goto, data['lat'], data['lon'], data['alt'])
    return jsonify({'status': 'goto requested', 'task_id': id(future)})


@app.route('/get_param', methods=['POST'])
def get_param():
    data = request.get_json(force=True)
    if not data or 'name' not in data:
        return jsonify({'error': 'name is required'}), 400

    try:
        future = run_task(bridge.get_param, data['name'])
        value = future.result(timeout=10)
        return jsonify({'name': data['name'], 'value': value})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/get_param_test', methods=['GET'])
def get_param_test():
    data = {'name': 'STAT_RUNTIME'}

    try:
        future = run_task(bridge.get_param, data['name'])
        value = future.result(timeout=10)
        return jsonify({'name': data['name'], 'value': value})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_all_params', methods=['GET'])
def get_all_params():
    try:
        future = run_task(bridge.get_all_params)
        params = future.result(timeout=60)
        return jsonify(params)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/telemetry', methods=['GET'])
def telemetry():
    with state_lock:
        return jsonify(state)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, threaded=True)

