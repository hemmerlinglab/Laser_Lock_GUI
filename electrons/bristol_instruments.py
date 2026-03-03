import telnetlib
import time

class BI871:

    '''
    Create connection, control, and read data from a
    Bristol Instruments 871 Wavelength Meter via Telnet.
    '''
    # 1. Initialization --------------------------------------------------
    def __init__(self, HOST = "192.168.42.168", PORT = 23, timeout = 10):

        # Record host and port
        self.host = HOST
        self.port = PORT
        self.timeout = timeout

        # Create connection to the device
        self.tn = telnetlib.Telnet(self.host, self.port, timeout=self.timeout)

        # Attributes to deal with the crazy behavior of the wavemeter
        self._modes = ["FETC", "READ", "MEAS"]
        self._current_mode = 0

        # Clear welcome messages (if any)
        time.sleep(0.2)
        self.tn.read_very_eager()

        # Check connection is successful by requesting device ID
        self.check_connection()


    # 2. Secure Connection -----------------------------------------------
    def check_connection(self):

        """
        Check that the connection is active and the device is responding.
        Raises RuntimeError if the expected ID string is not received.
        """

        self.send("*IDN?")
        msg = self.tn.read_until(b'\n', timeout=2).decode(errors="ignore")
        if "BRISTOL WAVELENGTH METER, 871" not in msg:
            raise RuntimeError(f"Failed to connect or unexpected IDN. Feedback: {msg}")

    def reconnect(self, retries = 3, delay = 0.5):

        """
        Try to restart connection when it is lost
        """

        for _ in range(retries):
            # Try to close current connection
            try:
                self.close()
            except Exception:
                pass
            # Try to establish new connection
            try:
                self.tn = telnetlib.Telnet(self.host, self.port, timeout=self.timeout)
                time.sleep(0.2)
                self.tn.read_very_eager()
                self.check_connection()
                return True
            except Exception:
                time.sleep(delay)

        return False


    # 3. Communication ---------------------------------------------------
    def send(self, message):

        """
        Send a command string to the instrument.
        Automatically appends newline if missing.
        """

        if not message.endswith('\n'):
            message += '\n'
        self.tn.write(message.encode("ascii"))

    def query(self, message, timeout=0.1):

        """
        Send a command and read the reply.
        Waits briefly to ensure the device has time to respond.
        Returns the response string (including newline).
        """

        self.send(message)
        return self.tn.read_until(b'\n', timeout).decode("ascii")

    def get_frequency(self, timeout=0.1):

        """
        Try to get frequency as safe as possible, reduce the errors.
        Returns:
            float: The measured frequency in THz.
        Raises:
            RuntimeError: If the instrument does not return a valid number.

        The logic is to switch mode and continously locked in this mode
        until the next failure, instead of retry in another mode when failed.
        """

        for attempt in (0, 1):
            for m in range(len(self._modes)):
                try:
                    return self._read_frequency(timeout)
                except RuntimeError:
                    old = self._current_mode
                    self._current_mode = (self._current_mode + 1) % len(self._modes)
                    new = self._current_mode
                    print(f"[wavemeter_client] switching from mode {self._modes[old]} to mode {self._modes[new]}")

                    continue

            if attempt == 0 and self.reconnect():
                continue

            break

        raise RuntimeError(f"Failed to read frequency under all modes!")

    def get_error_message(self, timeout=0.1):
        """
        Query and return the error message of the device
        when there is no error, the device will return:
        '0, no error\r\n'
        """
        return self.query(":SYST:ERR?", timeout)


    # 5. Helper functions ------------------------------------------------
    def _clear_messages(self, quiet=0.1):
        """
        Make sure the message queue is cleared, hopefully this
        will address some wired behaviour of the device.
        """

        start_time = time.time()
        while True:
            chunk = self.tn.read_very_eager()
            if chunk:
                start_time = time.time()
            else:
                if (time.time() - start_time) >= quiet:
                    break

        time.sleep(0.01)

    def _read_frequency(self, timeout=0.1):
        """
        Read frequency with flexible commands
        """

        cmd = f":{self._modes[self._current_mode]}:FREQ?"
        return self._process_frequency(self.query(cmd, timeout))

    def _process_frequency(self, freq):
        """
        Convert the frequency string into number
        """

        try:
            return float(freq)
        except ValueError:
            self._clear_messages()
            raise RuntimeError(f"invalid frequency response: {freq}")


    # 6. Debugs or testing features --------------------------------------
    def _fetch_all(self, timeout=0.1):
        return self.query(":FETC:ALL?", timeout)

    def _fetch_power(self, timeout=0.1):
        return self.query(":FETC:POW?", timeout)


    # 7. Light version utilities -----------------------------------------
    def fetch_freq(self, timeout=0.1):
        return self._process_frequency(self.query(":FETC:FREQ?", timeout))

    def read_freq(self, timeout=0.1):
        return self._process_frequency(self.query(":READ:FREQ?", timeout))

    def measure_freq(self, timeout=0.1):
        return self._process_frequency(self.query(":MEAS:FREQ?", timeout))


    # 8. Close the connection --------------------------------------------
    def close(self):

        """
        Close the Telnet connection to the instrument.
        """
        self.tn.close()


if __name__ == "__main__":
    wlm = BI871()
    time.sleep(1)
    freq = wlm.get_frequency()
    print(f"Measured frequency: {freq} THz.")
    wlm.close()
