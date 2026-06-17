#!/usr/bin/env python3
"""
Simple MAVLink connection tester.

Usage:
 python mavlink_test.py --connection udp:127.0.0.1:14550
 python mavlink_test.py --connection /dev/ttyAMA0:921600
"""

import argparse
import sys
import time

from pymavlink import mavutil


def create_connection(connection_string, source_system=255, timeout=10):
    connection_string = "/dev/ttyAMA0"
    print(f"Opening MAVLink connection to {connection_string}")
    master = mavutil.mavlink_connection(
        connection_string,
        source_system=source_system,
        autoreconnect=True,
        baud=57600
    )

    print("Waiting for heartbeat...")
    master.wait_heartbeat(timeout=timeout)
    print(
        f"Heartbeat received from system {master.target_system}, component {master.target_component}"
    )
    
    return master

def request_params(master):
   
    print("Requesting parameter list...")

    master.mav.param_request_list_send(
        master.target_system,
        master.target_component
    )

    params = {}

    last_param_time = time.time()
    last_request_time = time.time()
    param_request_sent = True

    while True:
        msg = master.recv_match(type='PARAM_VALUE', blocking=True, timeout=1)

        if msg:
            # param_id may be bytes (py3) or already str depending on pymavlink version
            if isinstance(msg.param_id, (bytes, bytearray)):
                name = msg.param_id.decode('utf-8', errors='ignore').rstrip('\x00')
            else:
                name = str(msg.param_id).rstrip('\x00')
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


def main():
    connection = "/dev/ttyAMA0"
    timeout = 10
    try:
        master = create_connection(connection, timeout=timeout)
        print("Connection established successfully.\n\n")
        request_params(master)
    except Exception as exc:
        print("Connection failed:", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
