from flask import Flask, Response, jsonify, request
import threading
from concurrent.futures import ThreadPoolExecutor
import cv2
from flask_socketio import SocketIO
import base64
import time

from mav_bridge import MAVBridge

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

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


camera = cv2.VideoCapture(1)

def stream_video():
    #print("vor while true")
    while True:
            #print("vor camera.read()")
            success, frame = camera.read()
            if not success:
                print("Failed to read frame")
                continue

            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            #print(jpg_as_text[:100])  # Debug: print the beginning of the encoded frame
            #print("nach jpg_as_text")  # Debug: confirm we reached this point
            socketio.emit('video_frame', jpg_as_text)

            socketio.sleep(0.03)  # ~30 FPS


@socketio.on('connect')
def handle_connect():
    print('Client connected')

def generate_frames():
    while True:
        success, frame = camera.read()

        if not success:
            break

        # Frame zu JPEG encoden
        ret, buffer = cv2.imencode('.jpg', frame)

        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        # MJPEG Stream Format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


def generate_video():
    while True:
        success, frame = camera.read()
        if not success:
            break

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/api/status')
def status():
    return jsonify({'status': 'API is running'})


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
	#return Response(generate_video(), mimetype='multipart/x-mixed-replace; boundary=frame', status=200)
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame', status=200)


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


@app.route('/change_mode', methods=['POST'])
def change_mode():
    data = request.get_json(force=True)
    if not data or 'mode' not in data:
        return jsonify({'error': 'mode is required'}), 400

    future = run_task(bridge.set_mode, data['mode'])
    return jsonify({'status': 'mode change requested', 'mode': data['mode'], 'task_id': id(future)})


@app.route('/set_velocity', methods=['POST'])
def set_velocity():
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


@app.route('/get_telemetry', methods=['GET'])
def get_telemetry():
    try:
        # run telemetry collection in background to avoid blocking server threads
        future = run_task(bridge.get_telemetry)
        telemetry = future.result(timeout=10)

        # update lightweight cached state (location only)
        with state_lock:
            if telemetry.get('lat') is not None:
                state['location']['lat'] = telemetry.get('lat')
            if telemetry.get('lon') is not None:
                state['location']['lon'] = telemetry.get('lon')

        return jsonify(telemetry)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_health', methods=['GET'])
def get_health():
    try:
        health = bridge.get_health()
        return jsonify(health)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_location', methods=['GET'])
def get_location():
    try:
        future = run_task(bridge.get_location)
        location = future.result(timeout=10)
        return jsonify(location)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=8000, threaded=True)
    socketio.start_background_task(stream_video)
    socketio.run(app, host='0.0.0.0', port=8000)

