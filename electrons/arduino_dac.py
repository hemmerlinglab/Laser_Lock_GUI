"""
Arduino DAC control. PID output (-10~10) is sent to DAC → piezo/current modulation.
Serial 7O1, 9600. Protocol: $channel,value*checksum (NMEA-style, XOR checksum).
"""

import serial
import time


class ArduinoDAC:
    """Sends PID output to DAC channels. Each laser has its own channel (piezo or current)."""

    def __init__(self, com_ports, channel_config, initial_outputs=None):
        """
        com_ports:          {arduino_no: "COMx"} usually {0: "COM5"}.
        channel_config:     per-laser DAC mapping (usually CONFIG["lasers"]).
        initial_outputs:    {laser_id: float} last PID output from file; applied at startup to avoid
                            frequency jump (without this, DAC starts at mid-scale and laser jumps).
        """
        self._serial_ports = {}
        self._channel_config = channel_config

        # DTR=False avoids Arduino reset on connect → no frequency jump
        for arduino_no, port in com_ports.items():
            serial_port = serial.Serial()
            serial_port.port = port
            serial_port.baudrate = 9600
            serial_port.bytesize = serial.SEVENBITS
            serial_port.parity = serial.PARITY_ODD
            serial_port.stopbits = serial.STOPBITS_ONE
            serial_port.timeout = 1
            serial_port.dtr = False  # avoid frequency jump at startup
            serial_port.open()
            self._serial_ports[arduino_no] = serial_port

        # apply saved PID outputs so laser frequency stays continuous across relaunch
        if initial_outputs:
            time.sleep(0.2)
            for laser_id, value in initial_outputs.items():
                if laser_id in channel_config:
                    self.set_output(laser_id, value)

    @staticmethod
    def _checksum(payload):
        """XOR of all bytes in payload (NMEA-style)."""
        result = 0
        for b in payload.encode("ascii"):
            result ^= b
        return result

    @staticmethod
    def _build_message(channel, raw_value):
        """Build $channel,value*checksum message. Checksum = XOR of payload, 3 decimal digits (0-255)."""
        payload = f"{channel},{raw_value}"
        checksum = ArduinoDAC._checksum(payload)
        return f"${payload}*{checksum:03d}\n"

    def write(self, arduino_no, data):
        """
        Send raw data to the given Arduino. Simple passthrough for testing or custom protocol.
        data: str or bytes; if str, encoded as ASCII.
        """
        if arduino_no not in self._serial_ports:
            raise KeyError(f"arduino_no {arduino_no} not in {list(self._serial_ports.keys())}")
        payload = data.encode("ascii") if isinstance(data, str) else data
        self._serial_ports[arduino_no].write(payload)

    def set_output(self, laser_id, control_value):
        """Write PID output (-10~10) to DAC. control_value drives piezo/current for this laser."""
        dac_params = self._channel_config[laser_id]["dac"]
        arduino_no = dac_params["arduino_no"]
        dac_channel = dac_params["DAC_chan"]
        max_output = dac_params["DAC_max_output"]

        raw_value = int(max_output / 20.0 * control_value + max_output / 2.0)
        raw_value = max(0, min(int(max_output), raw_value))
        message = self._build_message(dac_channel, raw_value)
        self.write(arduino_no, message)

    def close(self):
        """Close all serial ports."""
        for serial_port in self._serial_ports.values():
            try:
                serial_port.close()
            except Exception:
                pass


if __name__ == "__main__":
    from config import CONFIG

    dac = ArduinoDAC(CONFIG["arduino_com_ports"], {}, None)
    dac.write(0, ArduinoDAC._build_message(1, 0))
    dac.close()
