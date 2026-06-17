from pymavlink import mavutil
import time

# Verbindung zum Pixhawk (USB Serial)
master = mavutil.mavlink_connection('/dev/ttyAMA0', baud=57600)

print("Warte auf Heartbeat vom Pixhawk...")

# Warten bis Verbindung steht
master.wait_heartbeat()
print("Heartbeat empfangen!")

# Hauptloop: MAVLink Nachrichten lesen

beat = 0
status = 0
gps = 0
param_request_sent = False
last_param_request = 0

while True:
    msg = master.recv_match(blocking=True)

    if not msg:
        continue

    msg_type = msg.get_type()

    # Nur interessante Nachrichten anzeigen
    if msg_type == "HEARTBEAT" and beat == 0:
        print("Heartbeat OK")
        beat = 1
        # Send parameter request after heartbeat received
        if not param_request_sent:
            master.mav.param_request_list_send(1, 1)
            param_request_sent = True
            last_param_request = time.time()

    elif msg_type == "SYS_STATUS" and status == 0:
        print("Systemstatus:", msg)
        status = 1

    elif msg_type == "GLOBAL_POSITION_INT" and gps == 0:
        print("Position:", msg.lat/1e7, msg.lon/1e7, "Alt:", msg.relative_alt/1000.0, "m")
        gps = 1

    elif msg_type == "PARAM_VALUE":
        # optional: Parameterwerte anzeigen
        print(f"Parameter: {msg.param_id} = {msg.param_value}")
    
    # Resend parameter request if no response for 5 seconds
    if param_request_sent and time.time() - last_param_request > 5:
        master.mav.param_request_list_send(1, 1)
        last_param_request = time.time()