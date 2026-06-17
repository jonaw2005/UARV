#!/usr/bin/env python3
"""
Simple MAVLink connection tester.

Usage:
 python mavlink_test.py --connection udp:127.0.0.1:14550
 python mavlink_test.py --connection /dev/ttyAMA0:921600
"""

import argparse
import sys

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
        master.target_component,
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
