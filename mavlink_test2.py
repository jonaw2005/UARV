from pymavlink import mavutil

con = "/dev/ttyACM0:115200"

master = mavutil.mavlink_connection(
        con,
        source_system=255,
        autoreconnect=True,
    )


print("Waiting for heartbeat...")

master.wait_heartbeat(timeout=10)

print(
        f"Heartbeat received from system {master.target_system}, component {master.target_component}"
    )
print("MAVLink version:", master.version)

print("Requesting parameter list...")
master.mav.param_request_list_send(
    master.target_system,
    master.target_component,
    0,
    0,
)

for _ in range(20):
    msg = master.recv_match(type=["PARAM_VALUE", "HEARTBEAT"], blocking=True, timeout=5)
    if not msg:
        print("No more messages received.")
        break
    print(msg)
    if msg.get_type() == "PARAM_VALUE":
        continue

print("Finished requesting parameters.")