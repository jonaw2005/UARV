from pymavlink import mavutil

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

master.mav.param_request_list_send(1, 1)

while True:
    msg = master.recv_match(blocking=True)

    if not msg:
        continue

    msg_type = msg.get_type()

    # Nur interessante Nachrichten anzeigen
    if msg_type == "HEARTBEAT" and beat == 0:
        print("Heartbeat OK")
        beat = 1

    elif msg_type == "SYS_STATUS" and status == 0:
        print("Systemstatus:", msg)
        status = 1

    elif msg_type == "GLOBAL_POSITION_INT" and gps == 0:
        print("Position:", msg.lat/1e7, msg.lon/1e7, "Alt:", msg.relative_alt/1000.0, "m")
        gps = 1

    elif msg_type == "PARAM_VALUE":
        # optional: Parameterwerte anzeigen
        print(f"Parameter: {msg.param_id} = {msg.param_value}")

    master.mav.param_request_list_send(1, 1)