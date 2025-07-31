import telnetlib
import time

class BI871:

    '''
    Create connection, control and read data from a
    Bristol Instruments 871 Wavelength Meter.
    This wavemeter uses telnet connection.
    '''

    def __init__(self, HOST = "192.168.42.168", PORT = 23, timeout = 10):

        # Create connection to the device
        self.tn = telnetlib.Telnet(HOST, PORT, timeout=timeout)

        # Clear welcome messages by getting them right now
        time.sleep(0.2)
        self.tn.read_very_eager()

        # Check if the connection succeeded
        self.check_connection()


    def check_connection(self):

        self.send("*IDN?")
        msg = self.tn.read_until(b'\n', timeout=2).decode(errors="ignore")
        if "BRISTOL WAVELENGTH METER, 871" not in msg:
            raise RuntimeError(f"Failed to connect or unexpected IDN. Feedback: {msg}")


    def send(self, message):

        # SCPI commands need to be ended by '\n'
        if not message.endswith('\n'):
            message += '\n'

        # Send message to the device
        self.tn.write(message.encode("ascii"))


    def query(self, message, wait=0.1, read_bytes=4096):

        self.send(message)
        time.sleep(wait)
        return self.tn.read_until(b'\n').decode("ascii")
    

    def get_frequency(self):

        response = self.query(":MEAS:FREQ?")
        try: return float(response)
        except ValueError:
            raise RuntimeError(f"Invalid frequency response: {response}")


    def close(self):
        self.tn.close()