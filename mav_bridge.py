"""Simple MAVLink bridge using pymavlink (mavutil).

Provides connect, send_command_long, arm/disarm, set_mode and a receive loop.

Install dependency: pip install pymavlink
"""
from pymavlink import mavutil as mu
import threading
import time
import logging

class MAVBridge:
    def __init__(self, connection_string, baud=115200, source_system=255, target_system=1, target_component=1):
        """Create bridge.

        connection_string: e.g. 'udp:127.0.0.1:14550' or 'COM3' or '/dev/ttyUSB0'
        """
        self.connection_string = connection_string
        self.baud = baud
        self.master = None
        self.running = False
        self.recv_thread = None
        self.source_system = source_system
        self.target_system = target_system
        self.target_component = target_component
        self._master_lock = threading.Lock()
        self._latest = threading.local()  # thread-local cache of last received message
        self.health = {
            'connected': False,
            'battery_voltage': None,
            'battery_current': None,
            'battery_remaining': None,
            'gps_fix_type': None,
            'satellites_visible': None,
            'last_heartbeat': None,
            'system_status': None,
        }
        self._health_thread = None

        self.logger = logging.getLogger("MAVBridge")

    def _read(self, msg_type=None, timeout=1.0):
        """Single threaded recv_match wrapper.

        Acquires _master_lock, calls recv_match, caches result in thread-local
        self._latest, releases lock, and returns the message.
        """
        with self._master_lock:
            msg = self.master.recv_match(type=msg_type, blocking=True, timeout=timeout)
            self._latest.value = msg
            return msg

    def connect(self, timeout=30):
        self.master = mu.mavlink_connection(
            self.connection_string,
            baud=self.baud,
            source_system=self.source_system,
            autoreconnect=True,
        )
        # mark connected and start background health thread
        self.health['connected'] = True
        self.running = True
        self._health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self._health_thread.start()


    def send_command_long(self, command, param1=0, param2=0, param3=0, param4=0, param5=0, param6=0, param7=0, confirmation=0):
        pass


    def _arm_disarm_sync(self, arm: bool, force: bool = False, timeout: float = 5.0) -> bool:
        """
        Synchronously send arm/disarm command and wait for COMMAND_ACK.

        Args:
            arm: True to arm, False to disarm.
            force: Force arming/disarming (skips pre-arm checks).
            timeout: Max seconds to wait for acknowledgment.

        Returns:
            True if the command was accepted, False otherwise.
        """
        self.master.mav.command_long_send(
            self.target_system,
            self.target_component,
            mu.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # confirmation
            1 if arm else 0,  # param1: 1=arm, 0=disarm
            21196 if force else 0,  # param2: force flag
            0, 0, 0, 0, 0
        )

        start = time.time()
        while time.time() - start < timeout:
            msg = self._read(type='COMMAND_ACK', timeout=1)

            if msg and msg.command == mu.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                if msg.result == mu.mavlink.MAV_RESULT_ACCEPTED:
                    return True

        return False

    def arm(self, force: bool = True, timeout: float = 5.0) -> bool:
        """
        Arms the vehicle and waits for confirmation.

        Returns True if armed successfully.
        """
        return self._arm_disarm_sync(arm=True, force=force, timeout=timeout)

    def disarm(self, force: bool = False, timeout: float = 5.0) -> bool:
        """
        Disarms the vehicle and waits for confirmation.

        Returns True if disarmed successfully.
        """
        return self._arm_disarm_sync(arm=False, force=force, timeout=timeout)


    def is_armed(self, timeout=3):
        """Return True if the vehicle is armed, False if disarmed."""
        msg = self._read(type='HEARTBEAT', timeout=timeout)
        if not msg:
            return False

        return bool(msg.base_mode & mu.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)


    def goto(self, lat, lon, alt):
            """
            Send a GPS waypoint (global position target).
            lat, lon in degrees
            alt in meters (relative or absolute depending on frame)
            """

            self.master.mav.set_position_target_global_int_send(
                0,  # time_boot_ms

                self.master.target_system,
                self.master.target_component,

                mu.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,

                # type_mask: ignore velocity, accel, yaw
                0b0000111111111000,

                int(lat * 1e7),   # latitude (E7 format)
                int(lon * 1e7),   # longitude (E7 format)
                alt,              # altitude in meters

                0, 0, 0,          # velocity ignored
                0, 0, 0,          # acceleration ignored
                0, 0              # yaw ignored
            )


    def get_all_params(self):

        self.logger.info("Requesting parameter list...")

        self.master.mav.param_request_list_send(
            self.master.target_system,
            self.master.target_component
        )

        params = {}

        last_param_time = time.time()
        last_request_time = time.time()
        param_request_sent = True

        while True:
            msg = self._read(type='PARAM_VALUE', timeout=1)

            if msg:
                # param_id may be bytes (py3) or already str depending on pymavlink version
                if isinstance(msg.param_id, (bytes, bytearray)):
                    name = msg.param_id.decode('utf-8', errors='ignore').rstrip('\x00')
                else:
                    name = str(msg.param_id).rstrip('\x00')
                params[name] = msg.param_value
                last_param_time = time.time()

            # Retry parameter request if no response for 3 seconds
            if time.time() - last_param_time > 3 and time.time() - last_request_time > 3:
                if len(params) == 0:  # No parameters received yet, retry
                    self.logger.info("No parameters received, retrying request...")
                    self.master.mav.param_request_list_send(
                        self.master.target_system,
                        self.master.target_component
                    )
                    last_request_time = time.time()
                else:
                    # Got some parameters but no more for 3 seconds, stop
                    break

            # Stop if 5 seconds of no new parameters after receiving at least one
            if len(params) > 0 and time.time() - last_param_time > 5:
                break

        self.logger.info(f"Fertig: {len(params)} Parameter")
        return params


    def get_param(self, name):
        self.master.mav.param_request_read_send(
            self.master.target_system,
            self.master.target_component,
            name.encode('utf-8'),
            -1
        )

        while True:
            msg = self._read(type='PARAM_VALUE', timeout=5)
            if msg:
                if isinstance(msg.param_id, (bytes, bytearray)):
                    param_name = msg.param_id.decode('utf-8', errors='ignore').rstrip('\x00')
                else:
                    param_name = str(msg.param_id).rstrip('\x00')
                if param_name == name:
                    return msg.param_value
            else:
                raise TimeoutError(f"Timeout waiting for parameter {name}")


    def get_telemetry(self, timeout=5):
        """Request current telemetry and return a JSON-friendly dict."""
        try:
            self.master.mav.request_data_stream_send(
                self.master.target_system,
                self.master.target_component,
                mu.mavlink.MAV_DATA_STREAM_ALL,
                1,
                1,
            )
        except Exception:
            pass

        telemetry = {
            'lat': None,
            'lon': None,
            'altitude': None,
            'relative_altitude': None,
            'groundspeed': None,
            'airspeed': None,
            'heading': None,
            'climb': None,
            'roll': None,
            'pitch': None,
            'yaw': None,
            'satellites_visible': None,
            'gps_fix_type': None,
            'battery_voltage': None,
            'battery_current': None,
            'load': None,
        }

        start = time.time()
        end = start + timeout
        while time.time() < end:
            msg = self._read(timeout=0.5)
            if msg is None:
                continue

            msg_type = msg.get_type()
            if msg_type == 'GLOBAL_POSITION_INT':
                telemetry['lat'] = msg.lat / 1e7
                telemetry['lon'] = msg.lon / 1e7
                telemetry['altitude'] = msg.alt / 1000.0
                telemetry['relative_altitude'] = msg.relative_alt / 1000.0
                if hasattr(msg, 'hdg') and msg.hdg != 65535:
                    telemetry['heading'] = msg.hdg / 100.0
                if hasattr(msg, 'velocity'):
                    telemetry['groundspeed'] = msg.velocity / 100.0

            elif msg_type == 'VFR_HUD':
                telemetry['groundspeed'] = msg.groundspeed
                telemetry['airspeed'] = msg.airspeed
                telemetry['heading'] = msg.heading
                telemetry['climb'] = msg.climb

            elif msg_type == 'ATTITUDE':
                telemetry['roll'] = msg.roll
                telemetry['pitch'] = msg.pitch
                telemetry['yaw'] = msg.yaw

            elif msg_type == 'GPS_RAW_INT':
                telemetry['gps_fix_type'] = msg.fix_type
                telemetry['satellites_visible'] = msg.satellites_visible

            elif msg_type == 'SYS_STATUS':
                telemetry['battery_voltage'] = msg.voltage_battery / 1000.0 if msg.voltage_battery is not None else None
                telemetry['battery_current'] = msg.current_battery / 100.0 if msg.current_battery is not None else None
                telemetry['load'] = msg.load / 10.0 if msg.load is not None else None

        return telemetry

    def get_gps_status(self, timeout=5):
        try:
            self.master.mav.request_data_stream_send(
                self.master.target_system,
                self.master.target_component,
                mu.mavlink.MAV_DATA_STREAM_ALL,
                1,
                1,
            )
        except Exception:
            pass

        gps_status = {
            'gps_fix_type': None,
            'satellites_visible': None,
        }

        start = time.time()
        end = start + timeout
        while time.time() < end:
            msg = self._read(timeout=0.5)
            if msg is None:
                continue

            if msg.get_type() == 'GPS_RAW_INT':
                gps_status['gps_fix_type'] = msg.fix_type
                gps_status['satellites_visible'] = msg.satellites_visible
                break

        return gps_status

    def get_gps_raw(self, timeout=5, hz: int = 5):
        interval_us = int(1e6 / hz)
        try:
            self.master.mav.command_long_send(
                self.target_system,
                self.target_component,
                mu.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
                0,
                mu.mavlink.MAVLINK_MSG_ID_GPS_RAW_INT,
                interval_us,
                0, 0, 0, 0, 0
            )
        except Exception:
            pass

        gps_raw = {
            'lat': None,
            'lon': None,
            'altitude': None,
            'groundspeed': None,
            'heading': None,
        }

        start = time.time()
        end = start + timeout
        while time.time() < end:
            msg = self._read(timeout=0.5)
            if msg is None:
                continue

            if msg.get_type() == 'GPS_RAW_INT':
                gps_raw['lat'] = msg.lat / 1e7
                gps_raw['lon'] = msg.lon / 1e7
                gps_raw['altitude'] = msg.alt / 1000.0
                if hasattr(msg, 'hdg') and msg.hdg != 65535:
                    gps_raw['heading'] = msg.hdg / 100.0
                if hasattr(msg, 'velocity'):
                    gps_raw['groundspeed'] = msg.velocity / 100.0
                break

        return gps_raw

    def get_gps_int(self, timeout=5, hz: int=5):
        interval_us = int(1e6 / hz)
        try:
            self.master.mav.command_long_send(
                self.target_system,
                self.target_component,
                mu.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
                0,
                mu.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT,
                interval_us,
                0, 0, 0, 0, 0
            )
        except Exception:
            pass

        gps_int = {
            'lat': None,
            'lon': None,
            'altitude': None,
            'relative_altitude': None,
            'groundspeed': None,
            'heading': None,
        }

        start = time.time()
        end = start + timeout
        while time.time() < end:
            msg = self._read(timeout=0.5)
            if msg is None:
                continue

            if msg.get_type() == 'GLOBAL_POSITION_INT':
                gps_int['lat'] = msg.lat / 1e7
                gps_int['lon'] = msg.lon / 1e7
                gps_int['altitude'] = msg.alt / 1000.0
                gps_int['relative_altitude'] = msg.relative_alt / 1000.0
                if hasattr(msg, 'hdg') and msg.hdg != 65535:
                    gps_int['heading'] = msg.hdg / 100.0
                if hasattr(msg, 'velocity'):
                    gps_int['groundspeed'] = msg.velocity / 100.0
                break

        return gps_int

    def _health_loop(self):
        # continuously collect a small set of status messages into self.health
        while self.running:
            try:
                try:
                    self.master.mav.request_data_stream_send(
                        self.master.target_system,
                        self.master.target_component,
                        mu.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS,
                        1,
                        1,
                    )
                except Exception:
                    pass

                start = time.time()
                # collect messages for a short window
                while time.time() - start < 0.8:
                    msg = self._read(timeout=0.3)
                    if not msg:
                        continue
                    t = msg.get_type()
                    if t == 'SYS_STATUS':
                        if getattr(msg, 'voltage_battery', None) is not None:
                            self.health['battery_voltage'] = msg.voltage_battery / 1000.0
                        if getattr(msg, 'current_battery', None) is not None:
                            self.health['battery_current'] = msg.current_battery / 100.0
                        if getattr(msg, 'battery_remaining', None) is not None:
                            self.health['battery_remaining'] = msg.battery_remaining
                        self.health['system_status'] = getattr(msg, 'system_status', None)
                    elif t == 'GPS_RAW_INT':
                        self.health['gps_fix_type'] = getattr(msg, 'fix_type', None)
                        self.health['satellites_visible'] = getattr(msg, 'satellites_visible', None)
                    elif t == 'HEARTBEAT':
                        self.health['last_heartbeat'] = time.time()
                        self.health['system_status'] = getattr(msg, 'system_status', self.health.get('system_status'))
            except Exception:
                # swallow errors to keep thread alive
                pass
            time.sleep(1.0)

    def get_health(self):
        # return a shallow copy of health dictionary
        return dict(self.health)

    def battery_level(self, timeout=3):
        """
        Request and return battery status from the autopilot.

        Returns a dict with:
            voltage  (float, V)
            current  (float, A)
            remaining (int, percent 0-100)

        Returns None fields if data not received within timeout.
        """
        try:
            self.master.mav.request_data_stream_send(
                self.master.target_system,
                self.master.target_component,
                mu.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS,
                1,
                1,
            )
        except Exception:
            pass

        start = time.time()
        end = start + timeout
        while time.time() < end:
            msg = self._read(type='SYS_STATUS', timeout=0.5)
            if msg:
                return {
                    'voltage': msg.voltage_battery / 1000.0 if msg.voltage_battery is not None else None,
                    'current': msg.current_battery / 100.0 if msg.current_battery is not None else None,
                    'remaining': msg.battery_remaining if msg.battery_remaining is not None else None,
                }

        # Fallback: return cached health values if SYS_STATUS wasn't received
        return {
            'voltage': self.health.get('battery_voltage'),
            'current': self.health.get('battery_current'),
            'remaining': self.health.get('battery_remaining'),
        }

    def get_location(self):
        telemetry = self.get_telemetry()
        return {
            'lat': telemetry.get('lat'),
            'lon': telemetry.get('lon'),
            'altitude': telemetry.get('altitude'),
            'relative_altitude': telemetry.get('relative_altitude'),
        }


# -----------------------------
    # VELOCITY CONTROL (dein Beispiel)
    # -----------------------------
    def set_velocity(self, vx, vy, vz):
        """
        Local NED velocity (m/s)
        vx: North (+)
        vy: East (+)
        vz: Down (+)
        """

        type_mask = 0b0000111111000111

        self.master.mav.set_position_target_local_ned_send(
            0,
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_FRAME_LOCAL_NED,
            type_mask,
            0, 0, 0,
            vx, vy, vz,
            0, 0, 0,
            0, 0
        )

    # -----------------------------
    # TAKEOFF (GUIDED MODE)
    # -----------------------------
    def takeoff(self, altitude):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,
            0, 0, 0, 0,
            0, 0,
            altitude
        )

    # -----------------------------
    # RTL
    # -----------------------------
    def rtl(self):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            0,
            0, 0, 0, 0, 0, 0, 0
        )

    # -----------------------------
    # LAND
    # -----------------------------
    def land(self):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_NAV_LAND,
            0,
            0, 0, 0, 0, 0, 0, 0
        )

    # -----------------------------
    # CHANGE SPEED
    # -----------------------------
    def set_speed(self, speed, airspeed=True):
        speed_type = 0 if airspeed else 1

        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_DO_CHANGE_SPEED,
            0,
            speed_type,
            speed,
            -1,
            0, 0, 0, 0
        )

    # -----------------------------
    # CONDITION YAW
    # -----------------------------
    def condition_yaw(self, heading, relative=False, speed=0, direction=0):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_CONDITION_YAW,
            0,
            heading,
            speed,
            direction,
            int(relative),
            0, 0, 0
        )

    # -----------------------------
    # LOITER TIME (guided trigger)
    # -----------------------------
    def loiter_time(self, seconds):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_NAV_LOITER_TIME,
            0,
            seconds,
            0,
            0,
            0,
            0,
            0,
            0
        )

    # -----------------------------
    # CHANGE ALTITUDE (guided)
    # -----------------------------
    def change_altitude(self, altitude):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_DO_CHANGE_ALTITUDE,
            0,
            altitude,
            0, 0, 0, 0, 0, 0
        )

    # -----------------------------
    # SET MODE (optional but useful)
    # -----------------------------
    def set_mode(self, mode):
        mode_mapping = self.master.mode_mapping()

        if mode not in mode_mapping:
            raise ValueError(f"Unknown mode: {mode}")

        mode_id = mode_mapping[mode]

        self.master.mav.set_mode_send(
            self.master.target_system,
            mu.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )


 # --------------------------------------------------
    # PUBLIC: Mission Upload Entry Point
    # --------------------------------------------------
    def upload_mission(self, mission_items):
        """
        mission_items = already translated MAVLink-ready list
        """
        with self._master_lock:

            self.master.mav.mission_clear_all_send(
                self.master.target_system,
                self.master.target_component
            )

            time.sleep(0.3)

            count = len(mission_items)
            self.logger.info(f"Starting mission upload: {count} items")
            uploaded = 0

            self.master.mav.mission_count_send(
                self.master.target_system,
                self.master.target_component,
                count
            )

            while uploaded < count:
                msg = self._read(
                    type=["MISSION_REQUEST", "MISSION_REQUEST_INT"],
                    timeout=5
                )

                if not msg:
                    # Autopilot stopped requesting — re-send count as reminder
                    self.logger.warning(
                        f"No request received, re-sending count ({uploaded}/{count} done)"
                    )
                    self.master.mav.mission_count_send(
                        self.master.target_system,
                        self.master.target_component,
                        count
                    )
                    continue

                seq = msg.seq
                self.logger.info(f"Received request for seq {seq}/{count}")

                # If the autopilot requests an item we already sent, it likely
                # reset its buffer (e.g. after mission_clear_all). Re-send it.
                if seq < uploaded:
                    self.logger.warning(
                        f"Pixhawk requested seq {seq} again (buffer reset?), re-sending"
                    )
                    item = mission_items[seq]
                    self._send_mission_item(seq, item)
                    continue

                # If seq jumped ahead, we can't handle that — abort
                if seq != uploaded:
                    raise RuntimeError(
                        f"Autopilot requested seq {seq} but expected {uploaded}"
                    )

                item = mission_items[seq]
                self.logger.info(f"Uploading mission seq {seq}/{count}: {item}")
                self._send_mission_item(seq, item)
                uploaded += 1

            ack = self._read(type="MISSION_ACK", timeout=5)

            if not ack:
                raise TimeoutError("No MISSION_ACK received after upload")

            ack_result = getattr(ack, 'result', None)
            if ack_result is not None and ack_result != mu.mavlink.MAV_RESULT_ACCEPTED:
                raise RuntimeError(
                    f"MISSION_ACK not accepted: result={ack_result}, type={ack.type}"
                )

            self.logger.info(f"Mission upload complete: {count} items, ACK={ack.result}, type={ack.type}")
            return str(ack)

    # --------------------------------------------------
    # INTERNAL: send single item
    # --------------------------------------------------
    def _send_mission_item(self, seq, item):

        self.master.mav.mission_item_int_send(
            self.master.target_system,
            self.master.target_component,
            seq,
            item["frame"],
            item["command"],
            0, 1,
            item.get("param1", 0),
            item.get("param2", 0),
            item.get("param3", 0),
            item.get("param4", 0),
            item.get("lat", 0),
            item.get("lon", 0),
            item.get("alt", 0)
        )


    # --------------------------------------------------
    # DOWNLOAD MISSION FROM AUTOPILOT (raw MAVLink messages)
    # --------------------------------------------------
    def download_mission_raw(self):
        """
        Download mission and return raw MAVLink message dicts
        (no translation / parsing — original MAVLink field names).
        """
        with self._master_lock:
            mission = []

            # 1. Request Mission List (with retry)
            msg = None
            for attempt in range(3):
                self.master.mav.mission_request_list_send(
                    self.master.target_system,
                    self.master.target_component
                )

                msg = self._read(type="MISSION_COUNT", timeout=5)

                if msg:
                    break

                self.logger.warning(f"MISSION_COUNT not received (attempt {attempt + 1}/3)")
                time.sleep(0.5)

            if not msg:
                raise TimeoutError("No MISSION_COUNT received after 3 attempts")

            count = msg.count
            self.logger.info(f"Pixhawk reports {count} mission items")

            # Empty mission is valid
            if count == 0:
                return []

            # ArduPlane needs time to load mission from flash after MISSION_COUNT.
            # Without this delay it re-sends seq 0 for every request.
            time.sleep(5.0)

            self.logger.info(
                f"Downloading items from sys={self.master.target_system} comp={self.master.target_component}"
            )

            # 2. Request each item by seq, return raw message as dict
            for seq in range(count):
                item = None
                for attempt in range(5):
                    # Try MISSION_REQUEST_INT first, fall back to MISSION_REQUEST
                    if attempt < 3:
                        self.master.mav.mission_request_int_send(
                            self.master.target_system,
                            self.master.target_component,
                            seq
                        )
                    else:
                        self.master.mav.mission_request_send(
                            self.master.target_system,
                            self.master.target_component,
                            seq
                        )

                    self.logger.debug(f"Sent request for seq {seq} (attempt {attempt + 1})")

                    # Read with a short non-blocking timeout in a loop so we can
                    # also catch any stray messages the Pixhawk might send
                    deadline = time.time() + 10
                    while time.time() < deadline:
                        msg = self._read(
                            type=["MISSION_ITEM_INT", "MISSION_ITEM", "MISSION_REQUEST", "MISSION_ACK", "HEARTBEAT"],
                            timeout=1
                        )
                        if not msg:
                            continue
                        msg_type = msg.get_type()
                        if msg_type in ("MISSION_ITEM_INT", "MISSION_ITEM"):
                            item = msg
                            break
                        self.logger.debug(
                            f"Ignoring {msg_type} during download (seq={getattr(msg, 'seq', '?')})"
                        )

                    if item:
                        self.logger.info(f"Received {item.get_type()} for seq {item.seq}")
                        break

                    self.logger.warning(f"No mission item for seq {seq} (attempt {attempt + 1}/5)")
                    time.sleep(0.5)
                else:
                    raise TimeoutError(f"No mission item for seq {seq} after 5 attempts")

                if item.seq == seq:
                    mission.append(item.to_dict())
                else:
                    # Pixhawk sent wrong seq — discard and re-request same seq
                    self.logger.warning(f"Got seq {item.seq} instead of {seq}, re-requesting...")
                    time.sleep(0.5)
                    seq -= 1
                    continue

            return mission

    # --------------------------------------------------
    # DOWNLOAD MISSION FROM AUTOPILOT (parsed / translated)
    # --------------------------------------------------
    def download_mission_2(self):
        """
        Holt komplette Mission vom Pixhawk (ArduPlane)
        und gibt sie als strukturierte Liste zurück
        """
        with self._master_lock:
            mission = []

            # 1. Request Mission List (with retry)
            msg = None
            for attempt in range(3):
                self.master.mav.mission_request_list_send(
                    self.master.target_system,
                    self.master.target_component
                )

                msg = self._read(type="MISSION_COUNT", timeout=5)

                if msg:
                    break

                self.logger.warning(f"MISSION_COUNT not received (attempt {attempt + 1}/3)")
                time.sleep(0.5)

            if not msg:
                raise TimeoutError("No MISSION_COUNT received after 3 attempts")

            count = msg.count
            self.logger.info(f"Pixhawk reports {count} mission items")

            # Empty mission is valid
            if count == 0:
                return []

            # ArduPlane needs time to load mission from flash after MISSION_COUNT.
            # Without this delay it re-sends seq 0 for every request.
            time.sleep(5.0)

            self.logger.info(
                f"Downloading items from sys={self.master.target_system} comp={self.master.target_component}"
            )

            # 2. Items einzeln anfordern (mit Seq-Check gegen veraltete/versetzte Messages)
            for seq in range(count):
                item = None
                for attempt in range(5):
                    # Try MISSION_REQUEST_INT first, fall back to MISSION_REQUEST
                    if attempt < 3:
                        self.master.mav.mission_request_int_send(
                            self.master.target_system,
                            self.master.target_component,
                            seq
                        )
                    else:
                        self.master.mav.mission_request_send(
                            self.master.target_system,
                            self.master.target_component,
                            seq
                        )

                    self.logger.debug(f"Sent request for seq {seq} (attempt {attempt + 1})")

                    # Read with a short non-blocking timeout in a loop so we can
                    # also catch any stray messages the Pixhawk might send
                    deadline = time.time() + 10
                    while time.time() < deadline:
                        msg = self._read(
                            type=["MISSION_ITEM_INT", "MISSION_ITEM", "MISSION_REQUEST", "MISSION_ACK", "HEARTBEAT"],
                            timeout=1
                        )
                        if not msg:
                            continue
                        msg_type = msg.get_type()
                        if msg_type in ("MISSION_ITEM_INT", "MISSION_ITEM"):
                            item = msg
                            break
                        self.logger.debug(
                            f"Ignoring {msg_type} during download (seq={getattr(msg, 'seq', '?')})"
                        )

                    if item:
                        self.logger.info(f"Received {item.get_type()} for seq {item.seq}")
                        break

                    self.logger.warning(f"No mission item for seq {seq} (attempt {attempt + 1}/5)")
                    time.sleep(0.5)
                else:
                    raise TimeoutError(f"No mission item for seq {seq} after 5 attempts")

                if item.seq == seq:
                    mission.append(self._parse_mission_item(item, seq=seq))
                else:
                    # Pixhawk sent wrong seq — discard and re-request same seq
                    self.logger.warning(f"Got seq {item.seq} instead of {seq}, re-requesting...")
                    time.sleep(0.5)
                    seq -= 1
                    continue

            return mission

    def download_mission(self, timeout: float = 10.0):
        """
        Fully self-contained mission download.
        Directly reads from MAVLink stream (NO cache, NO _get, NO shared state).
        Must be the only recv_match consumer while running.
        """
        with self._master_lock:
            mission = {}

            start = time.time()

            # -------------------------------------------------
            # 1. Request mission list
            # -------------------------------------------------
            self.master.mav.mission_request_list_send(
                self.target_system,
                self.target_component,
                mu.mavlink.MAV_MISSION_TYPE_MISSION
            )

            # -------------------------------------------------
            # 2. Wait for MISSION_COUNT
            # -------------------------------------------------
            count = None

            while time.time() - start < timeout:
                msg = self._read(type="MISSION_COUNT", timeout=1)

                if msg:
                    count = msg.count
                    break

            if count is None:
                raise TimeoutError("No MISSION_COUNT received")

            # -------------------------------------------------
            # 3. Request + receive each mission item
            # -------------------------------------------------
            for seq in range(count):

                # request item
                self.master.mav.mission_request_int_send(
                    self.target_system,
                    self.target_component,
                    seq,
                    mu.mavlink.MAV_MISSION_TYPE_MISSION
                )

                item = None
                t0 = time.time()

                while time.time() - t0 < timeout:
                    msg = self._read(type="MISSION_ITEM_INT", timeout=1)

                    if msg and msg.seq == seq:
                        item = msg
                        break

                if item is None:
                    raise TimeoutError(f"Missing mission item seq={seq}")

                mission[seq] = self._parse_mission_item(item, seq=seq)

            # -------------------------------------------------
            # 4. Wait for ACK
            # -------------------------------------------------
            ack = self._read(type="MISSION_ACK", timeout=timeout)

            return {
                "count": count,
                "mission": mission,
                "ack": getattr(ack, "type", None) if ack else None
            }


    # --------------------------------------------------
    # INTERNAL: MAVLink → JSON
    # --------------------------------------------------
    def _parse_mission_item(self, item, seq=None):

        cmd = item.command
        msg_type = item.get_type()
        is_int = msg_type == 'MISSION_ITEM_INT'

        # WAYPOINT
        if cmd == mu.mavlink.MAV_CMD_NAV_WAYPOINT:
            if is_int:
                lat = item.x / 1e7
                lon = item.y / 1e7
            else:
                lat = item.lat
                lon = item.lon
            return {
                "seq": seq,
                "type": "waypoint",
                "lat": lat,
                "lon": lon,
                "alt": item.z
            }

        # TAKEOFF
        elif cmd == mu.mavlink.MAV_CMD_NAV_TAKEOFF:
            return {
                "seq": seq,
                "type": "action",
                "action": "takeoff",
                "param": item.param1
            }

        # RTL
        elif cmd == mu.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH:
            return {
                "seq": seq,
                "type": "action",
                "action": "rtl"
            }

        # LAND
        elif cmd == mu.mavlink.MAV_CMD_NAV_LAND:
            return {
                "seq": seq,
                "type": "action",
                "action": "land"
            }

        # LOITER TIME
        elif cmd == mu.mavlink.MAV_CMD_NAV_LOITER_TIME:
            return {
                "seq": seq,
                "type": "action",
                "action": "loiter",
                "param": item.param1
            }

        # SPEED
        elif cmd == mu.mavlink.MAV_CMD_DO_CHANGE_SPEED:
            return {
                "seq": seq,
                "type": "action",
                "action": "set_speed",
                "param": item.param2
            }

        # ALT CHANGE
        elif cmd == mu.mavlink.MAV_CMD_DO_CHANGE_ALTITUDE:
            return {
                "seq": seq,
                "type": "action",
                "action": "change_alt",
                "param": item.param1
            }

        # DELAY
        elif cmd == mu.mavlink.MAV_CMD_NAV_DELAY:
            return {
                "seq": seq,
                "type": "action",
                "action": "delay",
                "param": item.param1
            }

        # YAW
        elif cmd == mu.mavlink.MAV_CMD_CONDITION_YAW:
            return {
                "seq": seq,
                "type": "action",
                "action": "condition_yaw",
                "param": item.param1
            }

        # LAND START
        elif cmd == mu.mavlink.MAV_CMD_DO_LAND_START:
            return {
                "seq": seq,
                "type": "action",
                "action": "land_start"
            }

        # UNKNOWN
        return {
            "seq": seq,
            "type": "unknown",
            "command": cmd
        }


    def change_mode(self, mode):
        mode_mapping = self.master.mode_mapping()

        if mode not in mode_mapping:
            raise ValueError(f"Unknown mode: {mode}")

        mode_id = mode_mapping[mode]

        self.master.mav.set_mode_send(
            self.master.target_system,
            mu.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )

    def abort_mission(self):
        # example: disarm and set mode to MANUAL
        self.disarm()
        time.sleep(0.5)
        self.change_mode("MANUAL")

    def start_mission(self):
        # example: set mode to AUTO
        self.change_mode("AUTO")

    def get_mode(self):
        self.master.mav.request_data_stream_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_DATA_STREAM_ALL,
            1,
            1,
        )

        while True:
            msg = self._read(timeout=5)
            if msg and msg.get_type() == 'HEARTBEAT':
                mode_id = msg.custom_mode
                mode_mapping = self.master.mode_mapping()
                for mode_name, mid in mode_mapping.items():
                    if mid == mode_id:
                        return mode_name
                return f"UNKNOWN({mode_id})"
            elif not msg:
                raise TimeoutError("Timeout waiting for HEARTBEAT to get mode")


    def start_rc_override(self):
        while True:
            self.master.mav.rc_channels_override_send(
                self.master.target_system,
                self.master.target_component,
                1500, 1500, 1000, 1500,
                0, 0, 0, 0
            )
            time.sleep(0.1)



if __name__ == "__main__":
    bridge = MAVBridge("/dev/ttyAMA0", baud=57600)
    bridge.connect()
    bridge.logger.info("Connected, requesting parameters...")
    #params = bridge.get_all_params()
    #bridge.logger.info(f"Got parameters: {params}")
    bridge.logger.info("Requesting single parameter...")
    param_value = bridge.get_param("GPS_RAW_DATA")
    bridge.logger.info(f"Got parameter: {param_value}")