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
    print(f"Opening MAVLink connection to {connection_string}")
    master = mavutil.mavlink_connection(
        connection_string,
        source_system=source_system,
        autoreconnect=True,
    )

    print("Waiting for heartbeat...")
    master.wait_heartbeat(timeout=timeout)
    print(
        f"Heartbeat received from system {master.target_system}, component {master.target_component}"
    )
    print("MAVLink version:", master.version)
    return master


def request_params(master):
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


def main():
    parser = argparse.ArgumentParser(description="Test MAVLink connection")
    parser.add_argument(
        "--connection",
        "-c",
        default="udp:127.0.0.1:14550",
        help="Connection string, e.g. udp:127.0.0.1:14550 or /dev/ttyUSB0:57600",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=10,
        help="Heartbeat timeout in seconds",
    )
    parser.add_argument(
        "--params",
        "-p",
        action="store_true",
        help="Request parameter list after heartbeat",
    )
    args = parser.parse_args()

    try:
        master = create_connection(args.connection, timeout=args.timeout)
        if args.params:
            request_params(master)
    except Exception as exc:
        print("Connection failed:", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
