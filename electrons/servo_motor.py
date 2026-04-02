"""
Servo motor control. Sends angle commands via serial. Protocol: $channel,angle*checksum.
Serial 7O1, 9600. Standalone, knows nothing about lasers.
"""

import serial
import time


class ServoMotor:
    """Sends angle (0-180) to servo channels. Generic, no laser-specific logic."""

    def __init__(self, com_port):
        self._port = serial.Serial()
        self._port.port = com_port
        self._port.baudrate = 115200
        self._port.bytesize = serial.EIGHTBITS
        self._port.parity = serial.PARITY_NONE
        self._port.stopbits = serial.STOPBITS_ONE
        self._port.timeout = 1
        self._port.dtr = False
        self._port.open()
        time.sleep(2.0)

    @staticmethod
    def _checksum(payload):
        result = 0
        for b in payload.encode("ascii"):
            result ^= b
        return result

    @staticmethod
    def _build_message(channel, angle):
        payload = f"{channel},{angle}"
        checksum = ServoMotor._checksum(payload)
        return f"${payload}*{checksum:03d}\n"

    def write(self, data):
        """Send raw data. For testing or custom protocol."""
        payload = data.encode("ascii") if isinstance(data, str) else data
        self._port.write(payload)

    def set_angle(self, channel, angle):
        """Set servo channel (1 or 2) to angle (0-180)."""
        angle = max(0, min(180, int(angle)))
        msg = self._build_message(channel, angle)
        self.write(msg)

    def close(self):
        try:
            self._port.close()
        except Exception:
            pass


class LaserSwitcher(ServoMotor):
    """Subclass for switching fiber to a specific laser. API: switch(laser_id)."""

    def __init__(self, com_port, lasers_config):
        super().__init__(com_port)
        self._lasers = lasers_config

    def switch_to_laser(self, laser_id):
        """Switch to laser_id (e.g. '422', '390')."""
        print(f"[LaserSwitcher] received query: {laser_id}")
        if laser_id not in self._lasers:
            return
        for channel, angle in self._lasers[laser_id]["servo"].items():
            self.set_angle(channel, angle)


if __name__ == "__main__":
    from config import CONFIG

    motor = ServoMotor(CONFIG["servo_com_port"])
    lasers = list(CONFIG["lasers"].items())
    interval = 2.0
    try:
        idx = 0
        while True:
            laser_id, laser_config = lasers[idx % len(lasers)]
            for ch, angle in laser_config["servo"].items():
                motor.set_angle(ch, angle)
            time.sleep(interval)
            idx += 1
    except KeyboardInterrupt:
        pass
    finally:
        motor.close()
