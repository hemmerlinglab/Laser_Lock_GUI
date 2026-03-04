"""
Arduino DAC control. PID output (-10~10) is sent to DAC → piezo/current modulation.
Serial 7N1. Uses last saved output at startup to avoid frequency jump when relaunching.
"""

import serial
import time


class ArduinoDAC:
    """Sends PID output to DAC channels. Each laser has its own channel (piezo or current)."""

    def __init__(self, com_ports, channel_config, initial_outputs=None):
        """
        com_ports:          {arduino_no: "COMx"} usually {0: "COM5"}.
        channel_config:     per-laser DAC mapping (usually CONFIG["pids"]).
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

    def set_output(self, laser_id, control_value):
        """Write PID output (-10~10) to DAC. control_value drives piezo/current for this laser."""
        channel_params = self._channel_config[laser_id]
        serial_port = self._serial_ports[channel_params["arduino_no"]]
        dac_channel = channel_params["DAC_chan"]
        max_output = channel_params["DAC_max_output"]

        # protocol: 5 digits, last digit = channel, rest = value (Arduino-side format)
        # ugly protocol, maybe improve later
        raw_value = int(max_output / 20.0 * control_value + max_output / 2.0)
        message = raw_value * 10 + dac_channel
        serial_port.write(f"{message:05d}".encode())

    def close(self):
        """Close all serial ports."""
        for serial_port in self._serial_ports.values():
            try:
                serial_port.close()
            except Exception:
                pass
