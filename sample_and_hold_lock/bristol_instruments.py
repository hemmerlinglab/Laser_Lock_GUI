import telnetlib
import time

class BI871:

    '''
    Create connection, control, and read data from a
    Bristol Instruments 871 Wavelength Meter via Telnet.
    '''

    def __init__(self, HOST = "192.168.42.168", PORT = 23, timeout = 10):

        """
        Initialize the Telnet connection to the instrument.
        """

        # Create connection to the device
        self.tn = telnetlib.Telnet(HOST, PORT, timeout=timeout)

        # Clear welcome messages (if any)
        time.sleep(0.2)
        self.tn.read_very_eager()

        # Check connection is successful by requesting device ID
        self.check_connection()


    def check_connection(self):

        """
        Check that the connection is active and the device is responding.
        Raises RuntimeError if the expected ID string is not received.
        """

        self.send("*IDN?")
        msg = self.tn.read_until(b'\n', timeout=2).decode(errors="ignore")
        if "BRISTOL WAVELENGTH METER, 871" not in msg:
            raise RuntimeError(f"Failed to connect or unexpected IDN. Feedback: {msg}")


    def send(self, message):

        """
        Send a command string to the instrument.
        Automatically appends newline if missing.
        """

        if not message.endswith('\n'):
            message += '\n'
        self.tn.write(message.encode("ascii"))


    def query(self, message, wait=0.1):

        """
        Send a command and read the reply.
        Waits briefly to ensure the device has time to respond.
        Returns the response string (including newline).
        """

        self.send(message)
        time.sleep(wait)
        return self.tn.read_until(b'\n').decode("ascii")


    def get_frequency(self):

        """
        Query and return the measured frequency value (in THz).
        Returns:
            float: The measured frequency in THz.
        Raises:
            RuntimeError: If the instrument does not return a valid number.
        """
        
        response = self.query(":MEAS:FREQ?")
        try:
            return float(response)
        except ValueError:
            raise RuntimeError(f"Invalid frequency response: {response}")


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
