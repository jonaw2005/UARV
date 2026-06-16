from pymavlink import mavutil
import sys

con = "/dev/ttyACM0"
master = None

try:
    print(f"Connecting to {con}...")
    master = mavutil.mavlink_connection(
        con,
        source_system=255,
        autoreconnect=True,
    )

    print("Waiting for heartbeat...")
    try:
        master.wait_heartbeat(timeout=10)
    except Exception as e:
        print(f"Heartbeat timeout/error: {e}", file=sys.stderr)
        sys.exit(1)

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

    for i in range(20):
        try:
            msg = master.recv_match(type=["PARAM_VALUE", "HEARTBEAT"], blocking=True, timeout=5)
            if not msg:
                print("No more messages received.")
                break
            print(msg)
            if msg.get_type() == "PARAM_VALUE":
                continue
        except Exception as e:
            print(f"Error receiving message {i}: {e}", file=sys.stderr)
            break

    print("Finished requesting parameters.")

except Exception as e:
    print(f"Connection error: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    if master:
        try:
            master.close()
        except Exception as e:
            print(f"Error closing connection: {e}", file=sys.stderr)