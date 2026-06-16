from flask import Flask, Response, jsonify, request
import threading
import time

try:
	from videostream.stream_api import generate
except Exception:
	generate = None

app = Flask(__name__)

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


@app.route('/status')
def status():
	with state_lock:
		return jsonify({'armed': state['armed'], 'flying': state['flying']})


@app.route('/location')
def location():
	with state_lock:
		return jsonify(state['location'])


@app.route('/start', methods=['POST'])
def start():
	with state_lock:
		state['armed'] = True
		state['flying'] = True
	return jsonify({'result': 'started', 'armed': True, 'flying': True})


@app.route('/land', methods=['POST'])
def land():
	with state_lock:
		state['flying'] = False
	return jsonify({'result': 'landed', 'flying': False})


@app.route('/go_to', methods=['POST'])
def go_to():
	data = request.get_json(silent=True)
	if not data or 'lat' not in data or 'lon' not in data:
		return jsonify({'error': 'expected json with lat and lon'}), 400

	lat = float(data['lat'])
	lon = float(data['lon'])

	# Simulate movement by updating location progressively in a background thread
	def move_to(target_lat, target_lon):
		with state_lock:
			state['armed'] = True
			state['flying'] = True
		steps = 10
		for i in range(1, steps + 1):
			with state_lock:
				state['location']['lat'] += (target_lat - state['location']['lat']) * (i / steps)
				state['location']['lon'] += (target_lon - state['location']['lon']) * (i / steps)
			time.sleep(0.2)

	thread = threading.Thread(target=move_to, args=(lat, lon), daemon=True)
	thread.start()

	return jsonify({'result': 'moving', 'target': {'lat': lat, 'lon': lon}})


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8000)

