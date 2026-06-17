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
        pass

    def get_param(self, name):
        pass
        

