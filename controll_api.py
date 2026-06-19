import eventlet
eventlet.monkey_patch()

from flask import Flask, Response, jsonify, request
import threading
from concurrent.futures import ThreadPoolExecutor
import cv2
from flask_socketio import SocketIO
import base64
import time
import atexit
import logging
from pymavlink import mavutil

from mav_bridge import MAVBridge


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s]: %(asctime)s - %(message)s"
)

started = False
running = True

#edit

def start_background():
    global started
    global running
    if not started:
        started = True
        running = True
        socketio.start_background_task(stream_video)

@socketio.on("connect")
def handle_connect():
    print("Client connected")
    start_background()

# Initialize a single shared MAVBridge instance and execution pool
bridge = MAVBridge("/dev/ttyAMA0", baud=57600)
bridge.connect()
executor = ThreadPoolExecutor(max_workers=1)

# Simple in-memory state
state = {
    'armed': False,
    'flying': False,
    'location': {'lat': 0.0, 'lon': 0.0},
}
state_lock = threading.Lock()


def find_working_camera(max_index=6):
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                cap.release()
                return i
        cap.release()
    return None

cam_index = find_working_camera()

if cam_index is None:
    raise Exception("No camera found")

camera = cv2.VideoCapture(cam_index)
print("Using camera:", cam_index)

def stream_video():
    #print("vor while true")
    global running, camera
    while running:
            #print("vor camera.read()")
            success, frame = camera.read()
            if not success:
                #print("Failed to read frame")
                camera.release()
                time.sleep(1)  # Wait a bit before trying to reconnect
                camera.open(cam_index)
                continue

            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            #print(jpg_as_text[:100])  # Debug: print the beginning of the encoded frame
            #print("nach jpg_as_text")  # Debug: confirm we reached this point
            socketio.emit('video_frame', jpg_as_text)

            socketio.sleep(0.03)  # ~30 FPS




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

@app.before_request
def log_request():
    logging.info(f"{request.remote_addr} {request.method} {request.path}")

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


@app.route('/arm', methods=['GET'])
def arm():
    future = run_task(bridge.arm)
    success = future.result(timeout=10)
    if success:
        return jsonify({'status': 'arm successful'})
    else:
        return jsonify({'status': 'arm failed'}), 500


@app.route('/disarm', methods=['GET'])
def disarm():
    future = run_task(bridge.disarm)
    success = future.result(timeout=10)
    if success:
        return jsonify({'status': 'disarm successful'})
    else:
        return jsonify({'status': 'disarm failed'}), 500


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
    

@app.route('/set_mission')
def set_mission():
    pass


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

        # If lat or lon are 0/None, fall back to GPS_RAW_INT values (keep other fields)
        lat = telemetry.get('lat')
        lon = telemetry.get('lon')
        if lat == 0 or lon == 0 or lat is None or lon is None:
            future_raw = run_task(bridge.get_gps_raw)
            gps_raw = future_raw.result(timeout=10)
            if gps_raw.get('lat') not in (0, None):
                telemetry['lat'] = gps_raw['lat']
            if gps_raw.get('lon') not in (0, None):
                telemetry['lon'] = gps_raw['lon']

        # update lightweight cached state (location only)
        with state_lock:
            if telemetry.get('lat') is not None:
                state['location']['lat'] = telemetry.get('lat')
            if telemetry.get('lon') is not None:
                state['location']['lon'] = telemetry.get('lon')

        return jsonify(telemetry)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_gps', methods=['GET'])
def get_gps():
    try:
        future = run_task(bridge.get_gps_int)
        gps = future.result(timeout=10)

        # If lat or lon are 0, fall back to GPS_RAW_INT values
        lat = gps.get('lat')
        lon = gps.get('lon')
        if lat == 0 or lon == 0 or lat is None or lon is None:
            future_raw = run_task(bridge.get_gps_raw)
            gps_raw = future_raw.result(timeout=10)
            if gps_raw.get('lat') not in (0, None):
                gps['lat'] = gps_raw['lat']
            if gps_raw.get('lon') not in (0, None):
                gps['lon'] = gps_raw['lon']

        return jsonify(gps)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/get_gps_raw', methods=['GET'])
def get_gps_raw():
    try:
        future = run_task(bridge.get_gps_raw)
        gps = future.result(timeout=10)
        return jsonify(gps)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/gps_status', methods=['GET'])
def gps_status():
    try:
        future = run_task(bridge.get_gps_status)
        status = future.result(timeout=10)
        return jsonify(status)
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


@app.route('/rc_override', methods=['GET'])
def rc_override():
    try:
        future = run_task(bridge.rc_override)
        result = future.result(timeout=10)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/battery_level', methods=['GET'])
def battery_level():
    try:
        future = run_task(bridge.battery_level)
        battery = future.result(timeout=10)
        return jsonify(battery)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --------------------------------------------------
# TRANSLATOR (JSON → MAVLink Items)
# --------------------------------------------------
def translate_mission(json_mission):
    items = []

    for item in json_mission:
        seq = int(item.get("seq", 0))
        t = item["type"]

        # ---------------- WAYPOINT ----------------
        if t == "waypoint":
            items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                "command": mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                "lat": int(item["lat"] * 1e7),
                "lon": int(item["lon"] * 1e7),
                "alt": 50.0
            })

        # ---------------- TAKEOFF ----------------
        elif t == "action" and item["action"] == "takeoff":
            # ArduPlane NAV_TAKEOFF expects position in lat/lon/alt fields;
            # param1 is minimum pitch (not altitude). Altitude goes in 'alt'.
            items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                "command": mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                "lat": 0,
                "lon": 0,
                "alt": float(item["param"])
            })

        # ---------------- LOITER ----------------
        elif t == "action" and item["action"] == "loiter":
            # LOITER_TIME is location-dependent → use GLOBAL_RELATIVE_ALT frame
            items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                "command": mavutil.mavlink.MAV_CMD_NAV_LOITER_TIME,
                "param1": float(item["param"])
            })

        # ---------------- RTL ----------------
        elif t == "action" and item["action"] == "rtl":
            items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_MISSION,
                "command": mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH
            })

        # ---------------- LAND ----------------
        elif t == "action" and item["action"] == "land":
            items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_MISSION,
                "command": mavutil.mavlink.MAV_CMD_NAV_LAND
            })

        # ---------------- SPEED ----------------
        elif t == "action" and item["action"] == "set_speed":
            # param1=0 (ground speed), param2=speed value
            items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_MISSION,
                "command": mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED,
                "param1": 0,
                "param2": float(item["param"])
            })

        # ---------------- ALT CHANGE ----------------
        elif t == "action" and item["action"] == "change_alt":
            # DO_CHANGE_ALTITUDE: use GLOBAL_RELATIVE_ALT, alt goes in param1
            items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                "command": mavutil.mavlink.MAV_CMD_DO_CHANGE_ALTITUDE,
                "param1": float(item["param"])
            })

        # ---------------- DELAY ----------------
        elif t == "action" and item["action"] == "delay":
            items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                "command": mavutil.mavlink.MAV_CMD_NAV_DELAY,
                "param1": float(item["param"])
            })

        # ---------------- YAW ----------------
        elif t == "action" and item["action"] == "condition_yaw":
            items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                "command": mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                "param1": float(item["param"])
            })

        # ---------------- LAND START ----------------
        elif t == "action" and item["action"] == "land_start":
            items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_MISSION,
                "command": mavutil.mavlink.MAV_CMD_DO_LAND_START
            })

    # sort by seq (important) — ensures correct order regardless of input order
    items.sort(key=lambda x: x["seq"])
    # Reassign seq to array index so it always matches the position
    for i, item in enumerate(items):
        item["seq"] = i
    logging.info(f"Translated {len(items)} mission items")
    return items


# --------------------------------------------------
# ENDPOINT
# --------------------------------------------------
@app.route("/mission_upload", methods=["POST"])
def upload_mission():
    data = request.get_json(force=True)
    logging.debug(f"received {data}")

    if not data or "mission" not in data:
        return jsonify({"error": "missing mission"}), 400

    mission_json = sorted(data["mission"], key=lambda x: int(x["seq"]))

    #mav_items = translate_mission(mission_json)
    mav_items = mission_json
    logging.info("Translated MAVLink items: %s", mav_items)
    #logging.warning("Translated MAVLink items: %s", mav_items)
    try:
        future = run_task(bridge.upload_mission_test, mav_items)
        response = future.result(timeout=30)
        return jsonify({
            "status": "upload_complete",
            "result": response,
            "items": len(mav_items)
        }), 200
    except Exception as e:
        logging.error(f"Mission upload failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/mission_download", methods=["GET"])
def download_mission():
    try:
        future = run_task(bridge.download_mission_test_2)
        result = future.result(timeout=35)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Mission download failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/mission_download_raw", methods=["GET"])
def download_mission_raw():
    try:
        future = run_task(bridge.download_mission_test)
        raw = future.result(timeout=35)
        return jsonify({
            "mission": raw
        }), 200
    except Exception as e:
        logging.error(f"Mission download raw failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/mission_start", methods=["GET"])
def start_mission():
    future = run_task(bridge.start_mission)
    return jsonify({
        "status": "mission_start_requested",
        "task_id": id(future)
    }), 202

@app.route("/abort_mission", methods=["GET"])
def abort_mission():
    future = run_task(bridge.abort_mission)
    return jsonify({
        "status": "mission_abort_requested",
        "task_id": id(future)
    }), 202


@app.route("/change_flightmode", methods=["POST"])
def change_flightmode():
    data = request.get_json(force=True)
    mode = data.get("mode")
    if not mode:
        return jsonify({"error": "missing mode"}), 400

    future = run_task(bridge.change_mode, mode)
    return jsonify({
        "status": "mode_change_requested",
        "task_id": id(future)
    }), 202


@app.route("/get_flightmode", methods=["GET"])
def get_mode():
    future = run_task(bridge.get_mode)
    mode = future.result()
    return jsonify({
        "mode": mode
    }), 200


@app.route("/takeoff", methods=["GET"])
def takeoff():
    future = run_task(bridge.takeoff)
    return jsonify({
        "status": "takeoff_requested",
        "task_id": id(future)
    }), 202


@app.route("/is_armed", methods=["GET"])
def is_armed():
    future = run_task(bridge.is_armed)
    armed = future.result()
    return str(armed)


@app.route("/arm_disarm", methods=["GET"])
def arm_disarm():
    if is_armed() == "True":
        future = run_task(bridge.disarm)
        return jsonify({"status": "disarm requested", "task_id": id(future)})
    elif is_armed() == "False":
        future = run_task(bridge.arm)
        return jsonify({"status": "arm requested", "task_id": id(future)})
    else:
        return jsonify({"error": "unable to determine armed status"}), 500

    

@app.route("/change_nv", methods=["GET"])
def change_nv():
    pass

def cleanup():
    global running, camera, bridge, executor
    running = False
    print("Cleaning up resources...")
    camera.release()
    bridge.close()
    executor.shutdown(wait=False)



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000)

