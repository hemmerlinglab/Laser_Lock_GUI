"""
Laser Lock entry point. Assembles: LaserLocker (wavemeter + PID + DAC), SetpointServer (remote queries),
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
from setpoint_server import SetpointServer


def main():
    locker = LaserLocker(CONFIG)  # starts lock loop in background

    server = SetpointServer(
        CONFIG["setpoint_server_ip"],
        CONFIG["setpoint_server_port"],
        locker,
    )
    threading.Thread(target=server.run, daemon=True).start()  # remote setpoint queries

    app = QApplication(sys.argv)
    win = MainWindow(CONFIG, locker)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
