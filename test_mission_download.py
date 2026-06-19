#!/usr/bin/env python3

import time
import logging
import argparse

from pymavlink import mavutil as mu


# Configure logging
logging.basicConfig(level=logging.INFO, format=">>> %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class MissionDownloader:
    """Handles MAVLink connection and mission download from Pixhawk."""

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

    def download_mission(self, timeout=10):
        """Downloads the mission from the Pixhawk and returns a list of items."""
        if not self.master:
            logger.error("Not connected to Pixhawk. Call connect() first.")
            return None

        mission_items = []

        logger.info("Requesting mission list...")
        self.master.mav.mission_request_list_send(
            self.target_system,
            self.target_component,
            mu.mavlink.MAV_MISSION_TYPE_MISSION
        )

        msg = self._read_message("MISSION_COUNT", timeout=timeout)
        if not msg:
            logger.error("Failed to get MISSION_COUNT from Pixhawk.")
            return None

        num_items = msg.count
        logger.info(f"Pixhawk reports {num_items} mission items.")

        if num_items == 0:
            logger.info("No mission items on Pixhawk.")
            return []

        for seq in range(num_items):
            self.master.mav.mission_request_int_send(
                self.target_system,
                self.target_component,
                seq,
                mu.mavlink.MAV_MISSION_TYPE_MISSION
            )
            item_msg = self._read_message(["MISSION_ITEM_INT", "MISSION_ITEM"], timeout=timeout)

            if not item_msg or item_msg.seq != seq:
                logger.error(f"Failed to download mission item {seq}.")
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
            logger.debug(f"Downloaded mission item {seq}")

        logger.info("Mission download complete.")
        return mission_items


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and log MAVLink missions from Pixhawk.")

    CONNECTION_STRING = "/dev/ttyAMA0" # Default for SITL
    BAUD_RATE = 57600 # Typically 57600 for serial connections
    downloader = MissionDownloader(CONNECTION_STRING, BAUD_RATE)

    try:
        downloader.connect()
        downloaded_mission = downloader.download_mission()

        if downloaded_mission is not None:
            if downloaded_mission:
                logger.info("Downloaded Mission Items:")
                for i, item in enumerate(downloaded_mission):
                    logger.info(f"  Item {i}: {item}")
            else:
                logger.info("No mission found on Pixhawk.")
        else:
            logger.error("Mission download failed.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        if downloader.master:
            downloader.master.close()
            logger.info("MAVLink connection closed.")
