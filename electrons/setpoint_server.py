"""
TCP server so remote clients (e.g. another PC in the lab) can query and update setpoints.
Protocol: one message per line.
  - Setpoint update:  "laser_id,frequency"  -> reply "1" or "0"
  - Frequency query:  "laser_id,?"          -> reply "laser_id,frequency" or "0"
  - Setpoint query:   "laser_id,set?"       -> reply "laser_id,frequency" or "0"

All data comes from LaserLocker (wavemeter reading, current setpoint).
"""

import socket


class SetpointServer:
    """Listens for TCP. Remote clients query measured frequency, current setpoint, or submit new setpoint."""

    def __init__(self, host, port, locker):
        """host/port: where to listen. locker: LaserLocker, holds wavemeter readings and setpoints."""
        self._host = host
        self._port = port
        self._locker = locker

    def run(self):
        """Blocking. Run in a daemon thread from main.py."""

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self._host, self._port))
        server_socket.listen(1)

        while True:
            try:
                connection, client_address = server_socket.accept()
            except OSError as error:
                print(f"[setpoint_server] accept() error: {error}")
                continue

            print(f"[setpoint_server] connection from {client_address}")

            try:
                with connection.makefile("r", encoding="utf-8", newline="") as read_file:
                    while True:
                        try:
                            line = read_file.readline()
                            if not line:
                                break
                            message = line.rstrip("\r\n")
                            reply = self._process_message(message)
                            connection.sendall(reply)
                        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                            print(f"[setpoint_server] client {client_address} disconnected")
                            break
                        except OSError as error:
                            print(f"[setpoint_server] socket I/O error {error}")
                            break
            finally:
                try:
                    connection.close()
                except Exception:
                    pass

    def _process_message(self, message):
        """Handle one line: query freq/setpoint, or submit setpoint. Reply "0" on failure."""
        try:
            laser_id, argument = message.split(",", 1)
        except ValueError:
            return b"0\n"

        # frequency request: "laser_id,?", return "laser_id,frequency" (success) or "0" (failure)
        if argument == "?":
            # current wavemeter reading (THz) for this laser
            value = self._locker.get_frequency(laser_id)
            return b"0\n" if value is None else f"{laser_id},{value:.6f}\n".encode()

        # setpoint request: "laser_id,set?", return "laser_id,frequency" (success) or "0" (failure)
        elif argument == "set?":
            # current lock target (setpoint) for this laser
            try:
                value = self._locker.get_setpoint(laser_id)
                return f"{laser_id},{value:.6f}\n".encode()
            except (KeyError, TypeError):
                return b"0\n"

        # setpoint update: "laser_id,frequency", return "1" (success) or "0" (failure)
        else:
            # new lock target (setpoint) from remote client
            try:
                frequency = float(argument)
            except ValueError:
                return b"0\n"
            self._locker.submit_setpoint(laser_id, frequency)
            return b"1\n"
