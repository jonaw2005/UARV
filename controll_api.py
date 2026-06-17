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




@app.route('/arm', methods=['POST'])
def arm():
	pass

@app.route('/disarm', methods=['POST'])
def disarm():
	pass

@app.route('/mode', methods=['POST'])
def mode():
	pass

@app.route('/velocity', methods=['POST'])
def velocity():
	pass

@app.route('/goto', methods=['POST'])
def goto():
	pass

@app.route('/telemetry', methods=['GET'])
def telemetry():
	pass

@app.route('/health', methods=['GET'])
def health():
	pass


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8000)

