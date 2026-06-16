"""Simple MAVLink bridge using pymavlink (mavutil).

Provides connect, send_command_long, arm/disarm, set_mode and a receive loop.

Install dependency: pip install pymavlink
"""
from pymavlink import mavutil
import threading
import time


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

    def connect(self, timeout=30):
        if self.connection_string.lower().startswith(('udp:', 'tcp:')):
            self.master = mavutil.mavlink_connection(self.connection_string)
        else:
            # assume serial
            self.master = mavutil.mavlink_connection(self.connection_string, baud=self.baud)

        # wait for heartbeat
        start = time.time()
        while True:
            try:
                self.master.wait_heartbeat(timeout=1)
                break
            except Exception:
                if time.time() - start > timeout:
                    raise TimeoutError('No heartbeat received')
        # set running flag and start receive thread
        self.running = True
        self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.recv_thread.start()

    def _recv_loop(self):
        while self.running:
            msg = self.master.recv_match(blocking=True, timeout=1)
            if msg is None:
                continue
            # simple print; users can extend by subclassing or replacing this method
            print(f"RECV: {msg.get_type()} {msg}")

    def send_heartbeat(self):
        # send a heartbeat from this ground station
        self.master.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,
                                       mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                                       0, 0, 0)

    def send_command_long(self, command, param1=0, param2=0, param3=0, param4=0, param5=0, param6=0, param7=0, confirmation=0):
        # wrapper to send COMMAND_LONG to target
        self.master.mav.command_long_send(self.target_system,
                                          self.target_component,
                                          command,
                                          confirmation,
                                          param1, param2, param3, param4, param5, param6, param7)

    def arm(self):
        # MAV_CMD_COMPONENT_ARM_DISARM, param1=1 to arm
        self.send_command_long(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, param1=1)

    def disarm(self):
        self.send_command_long(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, param1=0)

    def set_mode(self, mode):
        # mode can be string; need to map to custom mode number if required by autopilot
        # use mavutil to set mode by name when possible
        if not hasattr(self.master, 'set_mode'):
            # generic: send COMMAND_LONG MAV_CMD_DO_SET_MODE (deprecated on many autopilots)
            raise NotImplementedError('set_mode not supported for this connection')
        self.master.set_mode(mode)

    def close(self):
        self.running = False
        if self.recv_thread:
            self.recv_thread.join(timeout=1)
        if self.master:
            try:
                self.master.close()
            except Exception:
                pass


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='MAVLink bridge')
    parser.add_argument('connection', help="Connection string, e.g. udp:127.0.0.1:14550 or COM3")
    args = parser.parse_args()

    bridge = MAVBridge(args.connection)
    print('Connecting...')
    bridge.connect()
    print('Connected. Sending heartbeat every 2s. Ctrl-C to stop.')
    try:
        while True:
            bridge.send_heartbeat()
            time.sleep(2)
    except KeyboardInterrupt:
        print('Exiting')
    finally:
        bridge.close()
