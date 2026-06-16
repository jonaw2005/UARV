from pymavlink import mavutil

# Verbindung zum Pixhawk (USB Serial)
master = mavutil.mavlink_connection('/dev/ttyACM0', baud=57600)

print("Warte auf Heartbeat vom Pixhawk...")

# Warten bis Verbindung steht
master.wait_heartbeat()
print("Heartbeat empfangen!")

# Hauptloop: MAVLink Nachrichten lesen
while True:
    msg = master.recv_match(blocking=True)

    if not msg:
        continue

    msg_type = msg.get_type()

    # Nur interessante Nachrichten anzeigen
    if msg_type == "HEARTBEAT":
        print("Heartbeat OK")

    elif msg_type == "SYS_STATUS":
        print("Systemstatus:", msg)

    elif msg_type == "GLOBAL_POSITION_INT":
        print("Position:", msg.lat/1e7, msg.lon/1e7, "Alt:", msg.relative_alt/1000.0, "m")

    else:
        # optional: andere Nachrichten ignorieren oder debuggen
        pass