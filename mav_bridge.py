"""Simple MAVLink bridge using pymavlink (mavutil).

Provides connect, send_command_long, arm/disarm, set_mode and a receive loop.

Install dependency: pip install pymavlink
"""
from venv import logger

from pymavlink import mavutil as mu
import threading
import time
import logging

class MAVBridge:
    def __init__(self, connection_string, baud=115200, source_system=255, target_system=1, target_component=1):
        """Create bridge.

        connection_string: e.g. 'udp:127.0.0.1:14550' or 'COM3' or '/dev/ttyUSB0'
        """
        #self.logger.debug(f"__init__")
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

    def _read(self, msg_type=None, timeout=10.0):
        """Single threaded recv_match wrapper.

        Acquires _master_lock, calls recv_match, caches result in thread-local
        self._latest, releases lock, and returns the message.
        """
        self.logger.debug(f"_read")
        with self._master_lock:
            self.logger.debug(f"trying to find message {msg_type}")
            msg = self.master.recv_match(blocking=True, timeout=timeout)
            self.logger.debug(f"found message {msg.get_type()}")
            self._latest.value = msg
            if msg and (msg.get_type() in msg_type):
                return msg

        return self._read(msg_type=msg_type, timeout=timeout)
        
    def _write(self, msg, log: bool = True):
        """Single threaded mav.send wrapper."""
        self.logger.debug(f"_write")
        with self._master_lock:
            if log:
                self.logger.debug(f"Sending message: {msg}")
            self.master.mav.send(msg)

    def connect(self, timeout=30):
        self.logger.debug(f"connect")
        self.master = mu.mavlink_connection(
            self.connection_string,
            baud=self.baud,
            source_system=self.source_system,
            autoreconnect=True,
        )
        # mark connected and start background health thread
        self.health['connected'] = True
        self.running = True
        #self._health_thread = threading.Thread(target=self._health_loop, daemon=True)
        #self._health_thread.start()


# done
    def command_long_send(self, command, param1=0, param2=0, param3=0, param4=0, param5=0, param6=0, param7=0, confirmation=0):
        self.logger.debug(f"send_command_long")

        command_long_message = mu.mavlink.MAVLink_command_long_message(
            self.target_system,
            self.target_component,
            command,
            confirmation,
            param1,
            param2,
            param3,
            param4,
            param5,
            param6,
            param7
        )
        self._write(command_long_message)

# done
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
        self.logger.debug(f"_arm_disarm_sync")
        self.command_long_send(
            mu.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # confirmation
            1 if arm else 0,  # param1: 1=arm, 0=disarm
            21196 if force else 0,  # param2: force flag
            0,
            0,
            0,
            0,
            0
        )

        start = time.time()
        while time.time() - start < timeout:
            msg = self._read(msg_type='COMMAND_ACK', timeout=1)

            if msg and msg.command == mu.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                if msg.result == mu.mavlink.MAV_RESULT_ACCEPTED:
                    return True

        return False

# done
    def arm(self, force: bool = False, timeout: float = 5.0) -> bool:
        """
        Arms the vehicle and waits for confirmation.

        Returns True if armed successfully.
        """
        self.logger.debug(f"arm")
        return self._arm_disarm_sync(arm=True, force=force, timeout=timeout)

# done
    def disarm(self, force: bool = False, timeout: float = 5.0) -> bool:
        """
        Disarms the vehicle and waits for confirmation.

        Returns True if disarmed successfully.
        """
        self.logger.debug(f"disarm")
        return self._arm_disarm_sync(arm=False, force=force, timeout=timeout)

# done
    def is_armed(self, timeout=3):
        """Return True if the vehicle is armed, False if disarmed."""
        self.logger.debug(f"is_armed")
        msg = self._read(msg_type='HEARTBEAT', timeout=timeout)
        if not msg:
            return False
        self.logger.debug(f"HEARTBEAT received: base_mode={msg.base_mode}, system_status={msg.system_status}")

        return bool(msg.base_mode & mu.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)

# done
    def goto(self, lat, lon, alt):
            """
            Send a GPS waypoint (global position target).
            lat, lon in degrees
            alt in meters (relative or absolute depending on frame)
            """
            self.logger.debug(f"goto")

            set_position_target_global_int_message = mu.mavlink.MAVLink_set_position_target_global_int_message(
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

            self._write(set_position_target_global_int_message)

#done
    def get_all_params(self):
        self.logger.debug(f"get_all_params")

        self.logger.info("Requesting parameter list...")

        param_request_list_message = mu.mavlink.MAVLink_param_request_list_message(
            self.master.target_system,
            self.master.target_component
        )

        self._write(param_request_list_message)

        params = {}

        last_param_time = time.time()
        last_request_time = time.time()
        param_request_sent = True

        while True:
            msg = self._read(msg_type='PARAM_VALUE', timeout=1)

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
                    param_request_list_message = mu.mavlink.MAVLink_param_request_list_message(
                        self.master.target_system,
                        self.master.target_component
                    )

                    self._write(param_request_list_message)
                    last_request_time = time.time()
                else:
                    # Got some parameters but no more for 3 seconds, stop
                    break

            # Stop if 5 seconds of no new parameters after receiving at least one
            if len(params) > 0 and time.time() - last_param_time > 5:
                break

        self.logger.info(f"Fertig: {len(params)} Parameter")
        return params

# done
    def get_param(self, name):
        self.logger.debug(f"get_param")

        param_request_read_message = mu.mavlink.MAVLink_param_request_read_message(
            self.master.target_system,
            self.master.target_component,
            name.encode('utf-8'),
            -1
        )

        self._write(param_request_read_message)

        while True:
            msg = self._read(msg_type='PARAM_VALUE', timeout=5)
            if msg:
                if isinstance(msg.param_id, (bytes, bytearray)):
                    param_name = msg.param_id.decode('utf-8', errors='ignore').rstrip('\x00')
                else:
                    param_name = str(msg.param_id).rstrip('\x00')
                if param_name == name:
                    return msg.param_value
            else:
                raise TimeoutError(f"Timeout waiting for parameter {name}")

# done
    def get_telemetry(self, timeout=5):
        """Request current telemetry and return a JSON-friendly dict."""
        self.logger.debug(f"get_telemetry")
        try:
            request_data_stream_message = mu.mavlink.MAVLink_request_data_stream_message(
                self.master.target_system,
                self.master.target_component,
                mu.mavlink.MAV_DATA_STREAM_ALL,
                1,
                1,
            )
            
            self._write(request_data_stream_message)

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

# done
    def get_gps_status(self, timeout=5):
        self.logger.debug(f"get_gps_status")
        try:
            request_data_stream_message = mu.mavlink.MAVLink_request_data_stream_message(
                self.master.target_system,
                self.master.target_component,
                mu.mavlink.MAV_DATA_STREAM_ALL,
                1,
                1,
            )
            
            self._write(request_data_stream_message)

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

# done
    def get_gps_raw(self, timeout=5, hz: int = 5):
        self.logger.debug(f"get_gps_raw")
        interval_us = int(1e6 / hz)
        try:
            self.command_long_send(
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

# done
    def get_gps_int(self, timeout=5, hz: int=5):
        self.logger.debug(f"get_gps_int")
        interval_us = int(1e6 / hz)
        try:
            self.command_long_send(
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

# not needed anymore
    def _health_loop(self):
        # continuously collect a small set of status messages into self.health
        self.logger.debug(f"_health_loop")
        while self.running:
            try:
                try:
                    request_data_stream_message = mu.mavlink.MAVLink_request_data_stream_message(
                        self.master.target_system,
                        self.master.target_component,
                        mu.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS,
                        1,
                        1
                    )
                    
                    self._write(request_data_stream_message)
                except Exception:
                    pass

                start = time.time()
                # collect messages for a short window
                while time.time() - start < 0.8:
                    msg = self._read(type=['SYS_STATUS','GPS_RAW_INT','HEARTBEAT'], timeout=0.3)
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

# unused
    def get_health(self):
        # return a shallow copy of health dictionary
        self.logger.debug(f"get_health")
        return dict(self.health)

# done
    def battery_level(self, timeout=3):
        """
        Request and return battery status from the autopilot.

        Returns a dict with:
            voltage  (float, V)
            current  (float, A)
            remaining (int, percent 0-100)

        Returns None fields if data not received within timeout.
        """
        self.logger.debug(f"battery_level")
        try:
            request_data_stream_message = mu.mavlink.MAVLink_request_data_stream_message(
                self.master.target_system,
                self.master.target_component,
                mu.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS,
                1,
                1,
            )
            
            self._write(request_data_stream_message)

        except Exception:
            pass

        start = time.time()
        end = start + timeout
        while time.time() < end:
            msg = self._read(msg_type='SYS_STATUS', timeout=0.5)
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

# done
    def get_location(self):
        self.logger.debug(f"get_location")
        telemetry = self.get_telemetry()
        return {
            'lat': telemetry.get('lat'),
            'lon': telemetry.get('lon'),
            'altitude': telemetry.get('altitude'),
            'relative_altitude': telemetry.get('relative_altitude'),
        }


    # -----------------------------
    # VELOCITY CONTROL (dein Beispiel) # done
    # -----------------------------
    def set_velocity(self, vx, vy, vz):
        """
        Local NED velocity (m/s)
        vx: North (+)
        vy: East (+)
        vz: Down (+)
        """
        self.logger.debug(f"set_velocity")

        type_mask = 0b0000111111000111

        set_position_target_local_ned_message = mu.mavlink.MAVLink_set_position_target_local_ned_message(
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

        self._write(set_position_target_local_ned_message)

    # -----------------------------
    # TAKEOFF (GUIDED MODE) # done
    # -----------------------------
    def takeoff(self, altitude):
        self.logger.debug(f"takeoff")
        self.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,
            0, 0, 0, 0,
            0, 0,
            altitude
        )

    # -----------------------------
    # RTL # done
    # -----------------------------
    def rtl(self):
        self.logger.debug(f"rtl")
        self.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            0,
            0, 0, 0, 0, 0, 0, 0
        )

    # -----------------------------
    # LAND # done
    # -----------------------------
    def land(self):
        self.logger.debug(f"land")
        self.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_NAV_LAND,
            0,
            0, 0, 0, 0, 0, 0, 0
        )

    # -----------------------------
    # CHANGE SPEED # done
    # -----------------------------
    def set_speed(self, speed, airspeed=True):
        self.logger.debug(f"set_speed")
        speed_type = 0 if airspeed else 1

        self.command_long_send(
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
    # CONDITION YAW # done
    # -----------------------------
    def condition_yaw(self, heading, relative=False, speed=0, direction=0):
        self.logger.debug(f"condition_yaw")
        self.command_long_send(
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
    # LOITER TIME (guided trigger) # done
    # -----------------------------
    def loiter_time(self, seconds):
        self.logger.debug(f"loiter_time")
        self.command_long_send(
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
    # CHANGE ALTITUDE (guided) # done
    # -----------------------------
    def change_altitude(self, altitude):
        self.logger.debug(f"change_altitude")
        self.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_CMD_DO_CHANGE_ALTITUDE,
            0,
            altitude,
            0, 0, 0, 0, 0, 0
        )

    # -----------------------------
    # SET MODE (optional but useful) # done
    # -----------------------------
    def set_mode(self, mode):
        self.logger.debug(f"set_mode")
        mode_mapping = self.master.mode_mapping()

        if mode not in mode_mapping:
            raise ValueError(f"Unknown mode: {mode}")

        mode_id = mode_mapping[mode]

        set_mode_message = mu.mavlink.MAVLink_set_mode_message(
            self.master.target_system,
            mu.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )

        self._write(set_mode_message)


    # --------------------------------------------------
    # PUBLIC: Mission Upload Entry Point # done
    # --------------------------------------------------

    def upload_mission(self, mission_items):
        self.logger.debug(f"upload_mission_test")
        num_items = len(mission_items)
        self.logger.info(f"Uploading mission with {num_items} items.")

        self.logger.info("Clearing existing mission...")

        clear_msg = mu.mavlink.MAVLink_mission_clear_all_message(
            self.target_system,
            self.target_component
        )

        self._write(clear_msg, log=True)

        ack = self._read("MISSION_ACK")

        self.logger.debug(f"Received ack {ack}")

        if not ack or ack.type != mu.mavlink.MAV_RESULT_ACCEPTED:
            self.logger.error(f"Failed to clear mission: {ack.type if ack else 'No ACK'}")
            return False
        self.logger.info("Mission cleared successfully.")
        time.sleep(0.5) # Give Pixhawk time to process

        mission_count_msg = mu.mavlink.MAVLink_mission_count_message(
            self.target_system,
            self.target_component,
            num_items,
            mu.mavlink.MAV_MISSION_TYPE_MISSION # Mission type
        )

        self._write(mission_count_msg, log=True)

        uploaded_count = 0
        while uploaded_count < num_items:
            msg = self._read(["MISSION_REQUEST", "MISSION_REQUEST_INT"])

            if not msg:
                self.logger.warning("No MISSION_REQUEST received, resending MISSION_COUNT.")
                
                mission_count_msg = mu.mavlink.MAVLink_mission_count_message(
                    self.target_system,
                    self.target_component,
                    num_items,
                    mu.mavlink.MAV_MISSION_TYPE_MISSION # Mission type
                )
                
                self._write(mission_count_msg, log=True)
                continue

            
            seq_to_send = msg.seq
            self.logger.info(f"Received MISSION_REQUEST for sequence {seq_to_send}")

            if seq_to_send != uploaded_count:
                self.logger.error(f"Unexpected mission request sequence: expected {uploaded_count}, got {seq_to_send}. Aborting upload.")
                return False

            item = mission_items[seq_to_send]

            mission_item_msg = mu.mavlink.MAVLink_mission_item_int_message(
                self.target_system,
                self.target_component,
                seq_to_send,
                item["frame"],
                item["command"],
                item.get("current", 0),
                item.get("autocontinue", 1),
                item.get("param1", 0),
                item.get("param2", 0),
                item.get("param3", 0),
                item.get("param4", 0),
                item.get("x", 0),
                item.get("y", 0),
                item.get("z", 0),
            )

            self._write(mission_item_msg, log=True)

            self.logger.info(f"Sent MISSION_ITEM_INT seq={seq_to_send}")

            uploaded_count += 1
            time.sleep(0.1) # Small delay to avoid overwhelming the Pixhawk


        self.logger.info("All mission items sent. Waiting for final MISSION_ACK.")
        ack = self._read("MISSION_ACK", timeout=10)
        if ack and ack.type == mu.mavlink.MAV_RESULT_ACCEPTED:
            self.logger.info("Mission upload successful!")
            return True
        else:
            self.logger.error(f"Mission upload failed: {ack.type if ack else 'No ACK'}")
            return False


    # --------------------------------------------------
    # INTERNAL: send single item # done
    # --------------------------------------------------
    def _send_mission_item(self, seq, item):
        self.logger.debug(f"_send_mission_item")

        mission_item_int_message = mu.mavlink.MAVLink_mission_item_int_message(
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

        self._write(mission_item_int_message)


# done
    def download_mission(self, timeout=10):
        """Downloads the mission from the Pixhawk and returns a list of items."""
        self.logger.debug(f"download_mission_test_2")
        if not self.master:
            self.logger.error("Not connected to Pixhawk. Call connect() first.")
            return None

        mission_items = []

        self.logger.info("Requesting mission list...")

        mission_request_list_message = mu.mavlink.MAVLink_mission_request_list_message(
            self.target_system,
            self.target_component#,
            #mu.mavlink.MAV_MISSION_TYPE_MISSION
        )

        self._write(mission_request_list_message)

        msg = self._read("MISSION_COUNT", timeout=timeout)
        if not msg:
            self.logger.error("Failed to get MISSION_COUNT from Pixhawk.")
            return None

        num_items = msg.count
        self.logger.info(f"Pixhawk reports {num_items} mission items.")

        if num_items == 0:
            self.logger.info("No mission items on Pixhawk.")
            return []

        for seq in range(num_items):
            mission_request_int_message = mu.mavlink.MAVLink_mission_request_int_message(
                self.target_system,
                self.target_component,
                seq,
                mu.mavlink.MAV_MISSION_TYPE_MISSION
            )

            self._write(mission_request_int_message)

            item_msg = self._read(["MISSION_ITEM_INT", "MISSION_ITEM"], timeout=timeout)

            if not item_msg or item_msg.seq != seq:
                self.logger.error(f"Failed to download mission item {seq}.")
                return None

            # Convert MAVLink message to a dictionary for logging and comparison
            mission_items.append({
                "frame": item_msg.frame,
                "command": item_msg.command,
                "param1": item_msg.param1,
                "param2": item_msg.param2,
                "param3": item_msg.param3,
                "param4": item_msg.param4,
                "x": item_msg.x,
                "y": item_msg.y,
                "z": item_msg.z,
                "current": item_msg.current,
                "autocontinue": item_msg.autocontinue
            })
            self.logger.debug(f"Downloaded mission item {seq}")

        logger.info("Mission download complete.")
        return mission_items


    # --------------------------------------------------
    # INTERNAL: MAVLink → JSON # done
    # --------------------------------------------------
    def _parse_mission_item(self, item, seq=None):
        self.logger.debug(f"_parse_mission_item")

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

#done
    def change_mode(self, mode):
        self.logger.debug(f"change_mode")
        mode_mapping = self.master.mode_mapping()

        if mode not in mode_mapping:
            raise ValueError(f"Unknown mode: {mode}")

        mode_id = mode_mapping[mode]

        set_mode_message = mu.mavlink.MAVLink_set_mode_message(
            self.master.target_system,
            mu.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )
        self._write(set_mode_message)

#done
    def abort_mission(self):
        self.logger.debug(f"abort_mission")
        # example: disarm and set mode to MANUAL
        self.disarm()
        time.sleep(0.5)
        self.change_mode("MANUAL")

#done
    def start_mission(self):
        self.logger.debug(f"start_mission")
        # example: set mode to AUTO
        self.change_mode("AUTO")


#done
    def get_mode(self):
        self.logger.debug(f"get_mode")

        request_data_stream_message = mu.mavlink.MAVLink_request_data_stream_message(
            self.master.target_system,
            self.master.target_component,
            mu.mavlink.MAV_DATA_STREAM_ALL,
            1,
            1,
        )

        self._write(request_data_stream_message)

        while True:
            msg = self._read(msg_type=None, timeout=5)
            if msg and msg.get_type() == 'HEARTBEAT':
                mode_id = msg.custom_mode
                mode_mapping = self.master.mode_mapping()
                for mode_name, mid in mode_mapping.items():
                    if mid == mode_id:
                        return mode_name
                return f"UNKNOWN({mode_id})"
            elif not msg:
                raise TimeoutError("Timeout waiting for HEARTBEAT to get mode")

#TODO: edit to message
    def start_rc_override(self):
        self.logger.debug(f"start_rc_override")
        while True:
            self.master.mav.rc_channels_override_send(
                self.master.target_system,
                self.master.target_component,
                1500, 1500, 1000, 1500,
                0, 0, 0, 0
            )
            time.sleep(0.1)



if __name__ == "__main__":
    #bridge = MAVBridge("/dev/ttyAMA0", baud=57600)
    #bridge.connect()
    #bridge.logger.info("Connected, requesting parameters...")
    #params = bridge.get_all_params()
    #bridge.logger.info(f"Got parameters: {params}")
    #bridge.logger.info("Requesting single parameter...")
    #param_value = bridge.get_param("GPS_RAW_DATA")
    #bridge.logger.info(f"Got parameter: {param_value}")