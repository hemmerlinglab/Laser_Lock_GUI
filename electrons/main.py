"""
Laser Lock entry point. Assembles: LaserLocker (wavemeter + PID + DAC), LaserServer (remote queries),
MainWindow (GUI). Run from electrons dir:  python main.py
"""

import sys
import threading
from pathlib import Path

# allow imports when run as python electrons/main.py from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5.QtWidgets import QApplication

from config import CONFIG
from laser_locker import LaserLocker
from main_window import MainWindow
from laser_server import LaserServer


def main():

    # initialize laser locker
    locker = LaserLocker(CONFIG)

    # initialize and run setpoint server
    server = LaserServer(
        CONFIG["setpoint_server_ip"],
        CONFIG["setpoint_server_port"],
        locker,
    )
    threading.Thread(target=server.run, daemon=True).start()

    # initialize the application
    app = QApplication(sys.argv)

    # manage shutdown of the application
    def shutdown():
        server.stop()
        locker.close()

    app.aboutToQuit.connect(shutdown)

    # initialize and run the GUI
    win = MainWindow(CONFIG, locker)
    win.show()

    # run laser locker (after the server and GUI to prevent jamming the GUI)
    threading.Thread(target=locker.start, daemon=True).start()

    # run and exit (when window is closed) the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
