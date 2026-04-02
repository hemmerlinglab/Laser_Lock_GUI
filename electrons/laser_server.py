"""
TCP server so remote clients (e.g. another PC in the lab) can query and update setpoints.
Protocol: one message per line.
  - Setpoint update:  "<laser_id>,<frequency>"  -> reply "1" or "0"
  - Frequency query:  "<laser_id>,?"            -> reply "<laser_id>,<frequency>" or "0"
  - Setpoint query:   "<laser_id>,set?"         -> reply "<laser_id>,<frequency>" or "0"
  - Switch laser:     "<laser_id>,switch"       -> reply "1" or "0"

All data comes from LaserLocker (wavemeter reading, current setpoint).
"""

import socket
import threading


class LaserServer:
    """Listens for TCP. Remote clients query measured frequency, current setpoint, submit new setpoint, or switch laser."""

    def __init__(self, host, port, locker):
        """host/port: where to listen. locker: LaserLocker, holds wavemeter readings and setpoints."""
        self._host = host
        self._port = port
        self._locker = locker
        self._stop_event = threading.Event()
        self._server_socket = None
        self._active_connection = None

    def stop(self):
        """Request the server to stop."""

        # Set the stop event flag to terminate run loop
        self._stop_event.set()

        # Close binding socket to stop accepting new connections
        try:
            if self._server_socket:
                self._server_socket.close()
        except Exception:
            pass

        # Close connection socket to stop communication with client
        try:
            if self._active_connection:
                self._active_connection.close()
        except Exception:
            pass

    def run(self):
        """Run the server."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self._host, self._port))
        server_socket.listen(1)
        server_socket.settimeout(1.0)

        self._server_socket = server_socket

        while not self._stop_event.is_set():
            try:
                connection, client_address = server_socket.accept()
                #connection.settimeout(1.0)
            except socket.timeout:
                continue
            except OSError as error:
                if self._stop_event.is_set():
                    break
                print(f"[LaserServer] accept() error: {error}")
                continue

            print(f"[LaserServer] connection from {client_address}")
            self._active_connection = connection

            try:
                with connection.makefile("r", encoding="utf-8", newline="") as read_file:
                    while not self._stop_event.is_set():
                        try:
                            line = read_file.readline()
                            if not line:
                                break
                            message = line.rstrip("\r\n")
                            reply = self._process_message(message)
                            connection.sendall(reply)
                        #except socket.timeout:
                            #continue
                        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                            print(f"[LaserServer] client {client_address} disconnected")
                            break
                        except OSError as error:
                            print(f"[LaserServer] socket I/O error {error}")
                            break

            finally:
                try:
                    connection.close()
                except Exception:
                    pass
                finally:
                    self._active_connection = None

        print("[LaserServer] laser server safely closed.")

    def _process_message(self, message):
        """Handle one line: query freq/setpoint, submit setpoint, or switch laser. Reply "0" on failure."""
        try:
            laser_id, argument = message.split(",", 1)
        except ValueError:
            return b"0\n"

        # frequency request: "laser_id,?", return "laser_id,frequency" (success) or "0" (failure)
        if argument == "?":
            value = self._locker.get_frequency(laser_id)
            return b"0\n" if value is None else f"{laser_id},{value:.6f}\n".encode()

        # setpoint request: "laser_id,set?", return "laser_id,frequency" (success) or "0" (failure)
        if argument == "set?":
            value = self._locker.get_setpoint(laser_id)
            if value is None:
                return b"0\n"
            return f"{laser_id},{value:.6f}\n".encode()

        # switch laser: "laser_id,switch", return "1" (success) or "0" (failure)
        if argument == "switch":
            if not self._locker.is_valid_laser_id(laser_id):
                return b"0\n"
            self._locker.switch_laser(laser_id)
            return b"1\n"

        # setpoint update: "laser_id,frequency", return "1" (success) or "0" (failure)
        if not self._locker.is_valid_laser_id(laser_id):
            return b"0\n"
        try:
            frequency = float(argument)
        except ValueError:
            return b"0\n"
        self._locker.submit_setpoint(laser_id, frequency)
        return b"1\n"


if __name__ == "__main__":
    import threading
    from laser_locker import LaserLocker
    from config import CONFIG

    locker = LaserLocker(CONFIG)
    server = LaserServer(
        CONFIG["setpoint_server_ip"],
        CONFIG["setpoint_server_port"],
        locker,
    )
    try:
        threading.Thread(target=locker.start, daemon=True).start()
        server.run()
    except KeyboardInterrupt:
        server.stop()
        locker.close()
