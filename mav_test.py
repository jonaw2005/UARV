"""Quick smoke-test for MAVBridge.

Tests the most important methods and prints PASS / FAIL for each.
Requires a connected Pixhawk on /dev/ttyAMA0 (or set PORT env var).
"""
import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

from mav_bridge import MAVBridge

PORT = "/dev/ttyAMA0"
BAUD = 57600
TIMEOUT = 5

passed = 0
failed = 0


def test_mission_upload(bridge):
    print("\n[MISSION UPLOAD]")
    try:
        mission = [
            {"type": "waypoint", "seq": 0, "lat": 47.66, "lon": 9.48},
            {"type": "action", "seq": 1, "action": "takeoff", "param": "100"},
            {"type": "action", "seq": 2, "action": "rtl"},
        ]

        success = bridge.upload_mission(mission)

        check("upload_mission()", success is True)
    except Exception as e:
        check("upload_mission()", False, str(e))


def test_mission_download(bridge):
    print("\n[MISSION DOWNLOAD]")
    try:
        mission = bridge.download_mission()

        check("download_mission() returns list", isinstance(mission, list))

        if len(mission) > 0:
            check("first item has 'seq'", "seq" in mission[0])
            check("first item has 'type'", "type" in mission[0])
            print(f"  INFO  Downloaded {len(mission)} items")
        else:
            print("  INFO  No mission stored")
    except Exception as e:
        check("download_mission()", False, str(e))


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name} {detail}")
        failed += 1


def show_menu():
    print("\nSelect test mode:")
    print("1 - Test all")
    print("2 - Test mission upload")
    print("3 - Test mission download")
    print("4 - Test mission upload and download")

    while True:
        choice = input("\nEnter choice (1-4): ").strip()
        if choice in ("1", "2", "3", "4"):
            return choice
        print("Invalid choice.")

def run_all_tests(bridge):
    # ── 1. Connect ──────────────────────────────────────────────────────────
    print("\n[1] connect()")
    try:
        bridge.connect()
        check("connect()", bridge.master is not None)
    except Exception as e:
        check("connect()", False, str(e))
        print("Cannot continue without connection. Exiting.")
        sys.exit(1)

    # Give the health thread a moment to collect data
    time.sleep(1)

    # ── 2. Health ───────────────────────────────────────────────────────────
    print("\n[2] get_health()")
    try:
        health = bridge.get_health()
        check("get_health() returns dict", isinstance(health, dict))
        check("health has 'connected' key", "connected" in health)
        check("health['connected'] is True", health.get("connected") is True)
    except Exception as e:
        check("get_health()", False, str(e))

    # ── 3. Single parameter read ────────────────────────────────────────────
    print("\n[3] get_param(name)")
    try:
        val = bridge.get_param("SYSID_THISMAV")
        check("get_param('SYSID_THISMAV') returns value", val is not None, f"got {val}")
    except Exception as e:
        check("get_param()", False, str(e))

    # ── 4. All parameters ───────────────────────────────────────────────────
    print("\n[4] get_all_params()")
    try:
        params = bridge.get_all_params()
        check("get_all_params() returns dict", isinstance(params, dict))
        check("params count > 0", len(params) > 0, f"got {len(params)} params")
    except Exception as e:
        check("get_all_params()", False, str(e))

    # ── 5. Telemetry ────────────────────────────────────────────────────────
    print("\n[5] get_telemetry()")
    try:
        telem = bridge.get_telemetry(timeout=3)
        check("get_telemetry() returns dict", isinstance(telem, dict))
        check("telemetry has 'lat' key", "lat" in telem)
        check("telemetry has 'battery_voltage' key", "battery_voltage" in telem)
    except Exception as e:
        check("get_telemetry()", False, str(e))

    # ── 6. GPS status ───────────────────────────────────────────────────────
    print("\n[6] get_gps_status()")
    try:
        gps = bridge.get_gps_status(timeout=3)
        check("get_gps_status() returns dict", isinstance(gps, dict))
        check("gps has 'gps_fix_type' key", "gps_fix_type" in gps)
    except Exception as e:
        check("get_gps_status()", False, str(e))

    # ── 7. GPS raw ──────────────────────────────────────────────────────────
    print("\n[7] get_gps_raw()")
    try:
        raw = bridge.get_gps_raw(timeout=3)
        check("get_gps_raw() returns dict", isinstance(raw, dict))
        check("gps_raw has 'lat' key", "lat" in raw)
    except Exception as e:
        check("get_gps_raw()", False, str(e))

    # ── 8. GPS int ──────────────────────────────────────────────────────────
    print("\n[8] get_gps_int()")
    try:
        gps_int = bridge.get_gps_int(timeout=3)
        check("get_gps_int() returns dict", isinstance(gps_int, dict))
        check("gps_int has 'lat' key", "lat" in gps_int)
    except Exception as e:
        check("get_gps_int()", False, str(e))

    # ── 9. Location ─────────────────────────────────────────────────────────
    print("\n[9] get_location()")
    try:
        loc = bridge.get_location()
        check("get_location() returns dict", isinstance(loc, dict))
        check("location has 'lat' key", "lat" in loc)
    except Exception as e:
        check("get_location()", False, str(e))

    # ── 10. Mode ────────────────────────────────────────────────────────────
    print("\n[10] get_mode()")
    try:
        mode = bridge.get_mode()
        check("get_mode() returns string", isinstance(mode, str) and len(mode) > 0, f"got '{mode}'")
    except Exception as e:
        check("get_mode()", False, str(e))

    # ── 11. Battery level ───────────────────────────────────────────────────
    print("\n[11] battery_level()")
    try:
        batt = bridge.battery_level(timeout=3)
        check("battery_level() returns dict", isinstance(batt, dict))
        check("battery has 'voltage' key", "voltage" in batt)
    except Exception as e:
        check("battery_level()", False, str(e))

    # ── 12. is_armed ────────────────────────────────────────────────────────
    print("\n[12] is_armed()")
    try:
        armed = bridge.is_armed(timeout=2)
        check("is_armed() returns bool", isinstance(armed, bool), f"got {armed}")
    except Exception as e:
        check("is_armed()", False, str(e))

    # ── 13. Mission translator (unit test, no Pixhawk needed) ──────────────
    print("\n[13] translate_mission() — unit test")
    try:
        from controll_api import translate_mission
        sample = [
            {"type": "waypoint", "seq": 0, "lat": 47.66, "lon": 9.48},
            {"type": "action", "seq": 1, "action": "takeoff", "param": "100"},
            {"type": "action", "seq": 2, "action": "rtl"},
        ]
        result = translate_mission(sample)
        check("translate_mission() returns list", isinstance(result, list))
        check("translated 3 items", len(result) == 3, f"got {len(result)}")
        check("first item is waypoint", result[0]["command"] == 16)  # MAV_CMD_NAV_WAYPOINT
        check("second item is takeoff", result[1]["command"] == 22)  # MAV_CMD_NAV_TAKEOFF
        check("third item is rtl", result[2]["command"] == 20)  # MAV_CMD_NAV_RETURN_TO_LAUNCH
    except Exception as e:
        check("translate_mission()", False, str(e))

    # ── 14. Mission download ─────────────────────────────────────────────────
    print("\n[14] download_mission() — requires Pixhawk with stored mission")
    try:
        mission = bridge.download_mission()
        check("download_mission() returns list", isinstance(mission, list))
        if len(mission) > 0:
            check("first item has 'seq'", "seq" in mission[0])
            check("first item has 'type'", "type" in mission[0])
            check("seq is int", isinstance(mission[0]["seq"], int))
            print(f"  INFO  Downloaded {len(mission)} items")
        else:
            print("  INFO  No mission stored on Pixhawk (empty mission is valid)")
    except Exception as e:
        check("download_mission()", False, str(e))

    # ── Summary ─────────────────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"  PASS: {passed}  |  FAIL: {failed}  |  TOTAL: {passed + failed}")
    print(f"{'='*50}\n")

    bridge.running = False
    sys.exit(0 if failed == 0 else 1)

def main():
    choice = show_menu()
    bridge = MAVBridge("/dev/ttyAMA0", baud=57600)

    try:
        bridge.connect()
        check("connect()", bridge.master is not None)
    except Exception as e:
        check("connect()", False, str(e))
        sys.exit(1)

    time.sleep(1)

    if choice == "1":
        run_all_tests(bridge)

    elif choice == "2":
        test_mission_upload(bridge)

    elif choice == "3":
        test_mission_download(bridge)

    elif choice == "4":
        test_mission_upload(bridge)
        test_mission_download(bridge)


if __name__ == "__main__":
    main()