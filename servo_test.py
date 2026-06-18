#!/usr/bin/env python3
"""
Servo test script using pymavlink.

Sends MAV_CMD_DO_SET_SERVO commands to move individual servos
through a range of PWM values to verify servo operation.

Usage:
    python servo_test.py                          # Uses default connection
    python servo_test.py --connection udp:127.0.0.1:14550
    python servo_test.py --connection /dev/ttyAMA0 --baud 57600
"""

import argparse
import time
import sys
from pymavlink import mavutil as mu


def connect(connection_string: str, baud: int = 57600):
    """Establish MAVLink connection and wait for heartbeat."""
    print(f"Connecting to {connection_string} at {baud} baud...")
    master = mu.mavlink_connection(connection_string, baud=57600)

    # Wait for heartbeat
    print("Waiting for heartbeat...")
    master.wait_heartbeat(timeout=30)
    print(f"Connected! System {master.target_system}, component {master.target_component}")
    return master


def set_servo(master, channel: int, pwm: int):
    """
    Set a specific servo channel to a PWM value using MAV_CMD_DO_SET_SERVO.

    Args:
        master: mavutil connection
        channel: Servo channel number (1-based)
        pwm: PWM value in microseconds (typically 1000-2000, 1500 = center)
    """
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mu.mavlink.MAV_CMD_DO_SET_SERVO,
        0,          # confirmation
        channel,    # param1: servo instance
        pwm,        # param2: PWM value
        0, 0, 0, 0, 0
    )
    print(f"  Servo {channel} -> {pwm} us")


def run_servo_sweep(master, channel: int, steps: int = 5, delay: float = 1.0):
    """
    Sweep a single servo from min to center to max and back.

    Args:
        master: mavutil connection
        channel: Servo channel number
        steps: Number of intermediate positions
        delay: Seconds to hold each position
    """
    print(f"\n--- Sweeping Servo {channel} ---")
    min_pwm = 1000
    center_pwm = 1500
    max_pwm = 2000

    # Move to center first
    print("  Moving to center...")
    set_servo(master, channel, center_pwm)
    time.sleep(1.0)

    # Sweep from center to min
    for pwm in range(center_pwm, min_pwm - 1, -(max_pwm - min_pwm) // steps):
        set_servo(master, channel, pwm)
        time.sleep(delay)

    # Hold at min
    print(f"  Holding at minimum ({min_pwm} us)...")
    time.sleep(delay)

    # Sweep from min to max
    for pwm in range(min_pwm, max_pwm + 1, (max_pwm - min_pwm) // steps):
        set_servo(master, channel, pwm)
        time.sleep(delay)

    # Hold at max
    print(f"  Holding at maximum ({max_pwm} us)...")
    time.sleep(delay)

    # Sweep back to center
    for pwm in range(max_pwm, center_pwm - 1, -(max_pwm - min_pwm) // steps):
        set_servo(master, channel, pwm)
        time.sleep(delay)

    # Return to center
    print("  Returning to center...")
    set_servo(master, channel, center_pwm)
    time.sleep(0.5)


def test_single_servo(master, channel: int):
    """
    Quick test of a single servo: center, min, max, center.

    Args:
        master: mavutil connection
        channel: Servo channel number
    """
    print(f"\n--- Testing Servo {channel} ---")
    positions = [
        (1500, "Center (1500 us)"),
        (1200, "Low (1200 us)"),
        (1800, "High (1800 us)"),
        (1500, "Return to Center (1500 us)"),
    ]

    for pwm, label in positions:
        set_servo(master, channel, pwm)
        print(f"  Holding {label}...")
        time.sleep(1.5)


def test_all_servos(master, max_channel: int = 8, sweep: bool = False):
    """
    Test all servos from channel 1 to max_channel one after another.

    Args:
        master: mavutil connection
        max_channel: Highest channel number to test (default 8)
        sweep: If True, run full sweep on each channel; otherwise quick test
    """
    print(f"\n=== Testing all servos (1-{max_channel}) ===")
    for ch in range(1, max_channel + 1):
        if sweep:
            run_servo_sweep(master, ch)
        else:
            test_single_servo(master, ch)
        # Small pause between channels
        time.sleep(0.5)
    print("\nAll servos tested.")


def list_channels_interactive(master, max_channel: int = 8):
    """Interactive mode: let user test individual channels."""
    print("\n=== Interactive Servo Test ===")
    print("Enter channel numbers to test, or 'q' to quit.")
    print("Enter 'sweep <channel>' for a full sweep test.")
    print("Enter 'all' to test every servo quickly.")
    print("Enter 'all sweep' to sweep every servo.\n")

    while True:
        try:
            cmd = input("servo_test> ").strip()
            if not cmd:
                continue
            if cmd.lower() == 'q':
                break
            if cmd.lower() == 'all sweep':
                test_all_servos(master, max_channel, sweep=True)
            elif cmd.lower() == 'all':
                test_all_servos(master, max_channel, sweep=False)
            elif cmd.lower().startswith('sweep '):
                channel = int(cmd.split()[1])
                run_servo_sweep(master, channel)
            else:
                channel = int(cmd)
                test_single_servo(master, channel)
        except (ValueError, IndexError):
            print("Usage: <channel_number> or 'sweep <channel_number>' or 'all' or 'all sweep' or 'q'")
        except KeyboardInterrupt:
            print("\nExiting interactive mode.")
            break


def emergency_disarm(master):
    """Send a disarm command to disable all servos."""
    print("\nDisarming to disable servos...")
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mu.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        0,  # disarm
        0, 0, 0, 0, 0, 0
    )
    # Also send servo override to neutral
    for ch in range(1, 9):
        set_servo(master, ch, 1500)
    time.sleep(0.2)


def get_armed_status(master) -> bool:
    """Check if the vehicle is armed by reading heartbeat."""
    master.mav.heartbeat_send(
        mu.mavlink.MAV_TYPE_GCS,
        mu.mavlink.MAV_AUTOPILOT_INVALID,
        0, 0, 0
    )
    msg = master.recv_match(type='HEARTBEAT', blocking=True, timeout=5)
    if msg:
        return (msg.base_mode & mu.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
    return False


def main():
    parser = argparse.ArgumentParser(description="Servo test tool using pymavlink")
    parser.add_argument(
        "--connection", "-c",
        default="/dev/ttyAMA0",
        help="MAVLink connection string (default: /dev/ttyAMA0)"
    )
    parser.add_argument(
        "--baud", "-b",
        type=int,
        default=57600,
        help="Baud rate (default: 57600)"
    )
    parser.add_argument(
        "--channel", "-ch",
        type=int,
        default=None,
        help="Single servo channel to test (omit for interactive mode)"
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Run a full sweep test on the specified channel"
    )
    parser.add_argument(
        "--disarm",
        action="store_true",
        help="Disarm and return servos to center before exiting"
    )

    args = parser.parse_args()

    # Connect
    try:
        master = connect(args.connection, args.baud)
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    try:
        if args.channel is not None:
            # Non-interactive mode: test a specific channel
            if args.sweep:
                run_servo_sweep(master, args.channel)
            else:
                test_single_servo(master, args.channel)
        else:
            # Interactive mode
            print("\nAvailable commands:")
            print("  <number>       - Quick test a servo channel")
            print("  sweep <number> - Full sweep test a servo channel")
            print("  q              - Quit")
            list_channels_interactive(master)

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        if args.disarm:
            emergency_disarm(master)
        else:
            # At least return all servos to center
            print("\nReturning servos to center position...")
            for ch in range(1, 5):
                set_servo(master, ch, 1500)
            time.sleep(0.3)

        print("Done.")
        master.close()


if __name__ == "__main__":
    main()