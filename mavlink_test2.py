from pymavlink import mavutil
import sys
import time
import json

con = "/dev/ttyAMA0"
master = None
baud = 57600

try:
    print(f"Connecting to {con}...")
    master = mavutil.mavlink_connection(
        con,
        baud=baud
#        source_system=255,
#        autoreconnect=True,
    )

    print("Waiting for heartbeat...")
    try:
#        master.wait_heartbeat(timeout=10)
        master.wait_heartbeat()
    except Exception as e:
        print(f"Heartbeat timeout/error: {e}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Heartbeat received from system {master.target_system}, component {master.target_component}"
    )
#    try:
#        print("MAVLink version:", master.version)
#    except Exception as e:
#        print(f"Error retrieving MAVLink version: {e}", file=sys.stderr)
    master.target_system = 1
    master.target_component = 1
    print("Requesting parameter list...")
    master.mav.param_request_list_send(
        master.target_system,
        master.target_component
#        mavutil.mavlink.MAV_MISSION_TYPE_ALL
    )

#    print("Requesting parameters...")
#    master.mav.param_request_list_send(1,1)

#    received = master.recv_msg()

#    print("Received message:", received)

    params = {}

    last_param_time = time.time()
    last_request_time = time.time()
    param_request_sent = True

    while True:
        msg = master.recv_match(type='PARAM_VALUE', blocking=True, timeout=1)

        if msg:
            name = msg.param_id.decode().strip('\x00')
            params[name] = msg.param_value
            last_param_time = time.time()
            print(name, params[name])

        # Retry parameter request if no response for 3 seconds
        if time.time() - last_param_time > 3 and time.time() - last_request_time > 3:
            if len(params) == 0:  # No parameters received yet, retry
                print("No parameters received, retrying request...")
                master.mav.param_request_list_send(
                    master.target_system,
                    master.target_component
                )
                last_request_time = time.time()
            else:
                # Got some parameters but no more for 3 seconds, stop
                break
        
        # Stop if 5 seconds of no new parameters after receiving at least one
        if len(params) > 0 and time.time() - last_param_time > 5:
            break

    print("Fertig:", len(params), "Parameter")

    with open("params.json", "w") as f:
        json.dump(params, f, indent=2)
    
    print("Parameter saved to params.json")
#    for i in range(20):
#        try:
#            msg = master.recv_match(type=["PARAM_VALUE", "HEARTBEAT"], blocking=True, timeout=5)
#            if not msg:
#                print("No more messages received.")
#                break
#            print(msg)
#            if msg.get_type() == "PARAM_VALUE":
#                continue
#        except Exception as e:
#            print(f"Error receiving message {i}: {e}", file=sys.stderr)
#            break
#
#    print("Finished requesting parameters.")

except Exception as e:
    print(f"Connection error: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    if master:
        try:
            master.close()
        except Exception as e:
            print(f"Error closing connection: {e}", file=sys.stderr)