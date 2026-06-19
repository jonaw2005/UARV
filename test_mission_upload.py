#!/usr/bin/env python3

import time
import logging

from pymavlink import mavutil as mu


# Configure logging
logging.basicConfig(level=logging.INFO, format=">>> %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class MissionUploader:
    """Handles MAVLink connection and mission upload for Pixhawk."""

    def __init__(self, connection_string, baud=115200):
        self.connection_string = connection_string
        self.baud = baud
        self.master = None
        self.target_system = 1  # Standard target system ID for Pixhawk
        self.target_component = 1  # Standard target component ID for Pixhawk

    def connect(self):
        """Establishes MAVLink connection to the Pixhawk."""
        logger.info(f"Connecting to MAVLink: {self.connection_string} @ {self.baud} baud")
        self.master = mu.mavlink_connection(
            self.connection_string,
            baud=self.baud,
            autoreconnect=True,
            source_system=255,  # GCS system ID
        )

        # Wait for a heartbeat to confirm connection
        logger.info("Waiting for Pixhawk heartbeat...")
        self.master.wait_heartbeat()
        logger.info(
            f"Heartbeat from system (SYS {self.master.target_system} COMP {self.master.target_component})"
        )
        self.target_system = self.master.target_system
        self.target_component = self.master.target_component
        logger.info("MAVLink connection established.")

    def _read_message(self, msg_type, timeout=5):
        """Reads a MAVLink message of a specific type with a timeout."""
        msg = self.master.recv_match(type=msg_type, blocking=True, timeout=timeout)
        if msg:
            logger.debug(f"Received {msg.get_type()} message: {msg}")
        return msg

    def _send_mission_item(self, seq, frame, command, current, autocontinue, param1, param2, param3, param4, x, y, z):
        """Sends a single MAVLink mission item (MISSION_ITEM_INT)."""
        self.master.mav.mission_item_int_send(
            self.target_system,
            self.target_component,
            seq,
            frame,
            command,
            current,  # current
            autocontinue,  # autocontinue
            param1,
            param2,
            param3,
            param4,
            x,  # latitude (int32)
            y,  # longitude (int32)
            z,  # altitude (float)
        )
        logger.debug(f"Sent MISSION_ITEM_INT seq={seq}")

    def upload_mission(self, mission_items):
        """Uploads a list of mission items to the Pixhawk."""
        if not self.master:
            logger.error("Not connected to Pixhawk. Call connect() first.")
            return

        num_items = len(mission_items)
        logger.info(f"Uploading mission with {num_items} items.")

        # 1. Clear existing mission
        logger.info("Clearing existing mission...")
        self.master.mav.mission_clear_all_send(
            self.target_system,
            self.target_component
        )
        ack = self._read_message("MISSION_ACK")
        if not ack or ack.type != mu.mavlink.MAV_RESULT_ACCEPTED:
            logger.error(f"Failed to clear mission: {ack.type if ack else 'No ACK'}")
            return False
        logger.info("Mission cleared successfully.")
        time.sleep(0.5) # Give Pixhawk time to process

        # 2. Send mission count
        logger.info(f"Sending mission count: {num_items}")
        self.master.mav.mission_count_send(
            self.target_system,
            self.target_component,
            num_items,
            mu.mavlink.MAV_MISSION_TYPE_MISSION # Mission type
        )

        # 3. Send individual mission items upon request
        uploaded_count = 0
        while uploaded_count < num_items:
            msg = self._read_message(["MISSION_REQUEST", "MISSION_REQUEST_INT"])

            if not msg:
                logger.warning("No MISSION_REQUEST received, resending MISSION_COUNT.")
                self.master.mav.mission_count_send(
                    self.target_system,
                    self.target_component,
                    num_items,
                    mu.mavlink.MAV_MISSION_TYPE_MISSION
                )
                continue

            seq_to_send = msg.seq
            logger.info(f"Received MISSION_REQUEST for sequence {seq_to_send}")

            if seq_to_send != uploaded_count:
                logger.error(f"Unexpected mission request sequence: expected {uploaded_count}, got {seq_to_send}. Aborting upload.")
                return False

            item = mission_items[seq_to_send]
            self._send_mission_item(
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
                item.get("z", 0)
            )
            uploaded_count += 1
            time.sleep(0.1) # Small delay to avoid overwhelming the Pixhawk

        # 4. Wait for final MISSION_ACK
        logger.info("All mission items sent. Waiting for final MISSION_ACK.")
        ack = self._read_message("MISSION_ACK", timeout=10)
        if ack and ack.type == mu.mavlink.MAV_RESULT_ACCEPTED:
            logger.info("Mission upload successful!")
            return True
        else:
            logger.error(f"Mission upload failed: {ack.type if ack else 'No ACK'}")
            return False

    def generate_example_mission(self):
        """Generates an example mission with a takeoff, waypoints, and a landing."""
        mission = []

        # Takeoff to 10 meters
        mission.append({
            "frame": mu.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            "command": mu.mavlink.MAV_CMD_NAV_TAKEOFF,
            "param1": 0, "param2": 0, "param3": 0, "param4": 0,
            "x": 0, "y": 0, "z": 10, # Altitude in meters
            "current": 0, "autocontinue": 1
        })

        # Waypoint 1: Move to a specific GPS coordinate at 10m altitude
        # (Replace with your desired coordinates)
        mission.append({
            "frame": mu.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            "command": mu.mavlink.MAV_CMD_NAV_WAYPOINT,
            "param1": 0, "param2": 0, "param3": 0, "param4": 0,
            "x": int(47.397742 * 1e7), # Example Latitude
            "y": int(8.545594 * 1e7), # Example Longitude
            "z": 10, # Altitude in meters
            "current": 0, "autocontinue": 1
        })

        # Waypoint 2: Another GPS coordinate
        mission.append({
            "frame": mu.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            "command": mu.mavlink.MAV_CMD_NAV_WAYPOINT,
            "param1": 0, "param2": 0, "param3": 0, "param4": 0,
            "x": int(47.397850 * 1e7), # Example Latitude
            "y": int(8.545700 * 1e7), # Example Longitude
            "z": 10, # Altitude in meters
            "current": 0, "autocontinue": 1
        })

        # Land at current position
        mission.append({
            "frame": mu.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            "command": mu.mavlink.MAV_CMD_NAV_LAND,
            "param1": 0, "param2": 0, "param3": 0, "param4": 0,
            "x": 0, "y": 0, "z": 0, # Land at current Lat/Lon, alt 0
            "current": 0, "autocontinue": 1
        })

        return mission


if __name__ == "__main__":
    # --- Configuration ---
    # Replace with your Pixhawk's connection string
    # Example for SITL (Software In The Loop):
    # CONNECTION_STRING = "udp:127.0.0.1:14550"
    # Example for USB serial:
    # CONNECTION_STRING = "/dev/ttyACM0" # Linux
    # CONNECTION_STRING = "COM3" # Windows
    CONNECTION_STRING = "/dev/AMA0" # Default for SITL

    BAUD_RATE = 57600 # Typically 57600 for serial connections
    # ---------------------

    uploader = MissionUploader(CONNECTION_STRING, BAUD_RATE)

    try:
        uploader.connect()
        example_mission = uploader.generate_example_mission()
        if uploader.upload_mission(example_mission):
            logger.info("Mission upload test completed successfully.")
        else:
            logger.error("Mission upload test failed.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        if uploader.master:
            # Close the connection if it was opened
            uploader.master.close()
            logger.info("MAVLink connection closed.")
