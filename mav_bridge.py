"""Simple MAVLink bridge using pymavlink (mavutil).

Provides connect, send_command_long, arm/disarm, set_mode and a receive loop.

Install dependency: pip install pymavlink
"""
from pymavlink import mavutil as mu
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
        self.master = mu.mavlink_connection(
            self.connection_string,
            baud=self.baud,
            source_system=self.source_system,
            autoreconnect=True,
        )

    def _recv_loop(self):
        pass

    def send_heartbeat(self):
        pass

    def send_command_long(self, command, param1=0, param2=0, param3=0, param4=0, param5=0, param6=0, param7=0, confirmation=0):
        pass

   

    def set_mode(self, mode):
        pass
       
    def close(self):
        pass


    def get_all_params(self):
            
        print("Requesting parameter list...")

        self.master.mav.param_request_list_send(
            self.master.target_system,
            self.master.target_component
        )

        params = {}

        last_param_time = time.time()
        last_request_time = time.time()
        param_request_sent = True

        while True:
            msg = self.master.recv_match(type='PARAM_VALUE', blocking=True, timeout=1)

            if msg:
                # param_id may be bytes (py3) or already str depending on pymavlink version
                if isinstance(msg.param_id, (bytes, bytearray)):
                    name = msg.param_id.decode('utf-8', errors='ignore').rstrip('\x00')
                else:
                    name = str(msg.param_id).rstrip('\x00')
                params[name] = msg.param_value
                last_param_time = time.time()
                print(msg.param_id)

            # Retry parameter request if no response for 3 seconds
            if time.time() - last_param_time > 3 and time.time() - last_request_time > 3:
                if len(params) == 0:  # No parameters received yet, retry
                    print("No parameters received, retrying request...")
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

        print("Fertig:", len(params), "Parameter")
        return params.to_dict()

    def get_param(self, name):
        pass
        

if __name__ == "__main__":
    bridge = MAVBridge("/dev/ttyAMA0", baud=57600)
    bridge.connect()
    print("Connected, requesting parameters...")
    params = bridge.get_all_params()
    print("Got parameters:", params)