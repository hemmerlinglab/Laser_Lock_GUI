"""
LaserLocker: central lock controller. Reads wavemeter → identifies laser by frequency range →
runs PID → outputs to DAC. MainWindow and LaserServer only talk to LaserLocker.
"""

import json
import queue
import threading
import time
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal

from bristol_instruments import BI871
from simple_pid import PID

from arduino_dac import ArduinoDAC
from servo_motor import LaserSwitcher


def _frequency_to_laser_id(config, frequency):
    """Which laser is the wavemeter seeing? Ranges from config["lasers"]."""
    for laser_id, params in config["lasers"].items():
        lo, hi = params["freq_min"], params["freq_max"]
        if lo < frequency < hi:
            return laser_id
    return 0


class LaserLocker(QObject):
    """
    Lock controller. UI and remote clients call get_frequency, get_setpoint, submit_setpoint.
    Emits frequency_changed (wavemeter reading), pid_output_changed, setpoint_changed.
    """

    frequency_changed = pyqtSignal(str, float)  # laser_id, measured freq (THz)
    pid_output_changed = pyqtSignal(str, float, float, float)  # laser_id, output, P, I
    setpoint_changed = pyqtSignal(str, float)  # laser_id, lock target (THz)

    def __init__(self, config):
        super().__init__()
        self._config = config
        self._setpoint_queue = queue.Queue()  # GUI/remote setpoint updates
        self._running = False

        self._last_pid_output = {laser_id: 0.0 for laser_id in config["lasers"]}
        self._last_frequency = {laser_id: None for laser_id in config["lasers"]}
        self._frequency_lock = threading.Lock()
        self._last_proportional_term = {laser_id: None for laser_id in config["lasers"]}
        self._last_integral_term = {laser_id: None for laser_id in config["lasers"]}

        # load last PID output so DAC starts at same value (no frequency jump on relaunch)
        state_path = Path(__file__).resolve().parent / config["last_pid_status"]
        try:
            with open(state_path, encoding="utf-8") as state_file:
                saved = json.load(state_file)
                for key in saved:
                    if key in self._last_pid_output:
                        self._last_pid_output[key] = float(saved[key])
        except Exception:
            pass

        self._wavemeter = BI871(config["wavemeter_ip"], config["wavemeter_port"])
        self._wavemeter_lock = threading.Lock()
        self._dac = ArduinoDAC(  # PID output → piezo/current
            config["arduino_com_ports"],
            config["lasers"],
            initial_outputs=self._last_pid_output,
        )
        self._switcher = None
        if "servo_com_port" in config:
            try:
                self._switcher = LaserSwitcher(config["servo_com_port"], config["lasers"])
            except Exception as error:
                print(f"[laser_locker] Servo motor not connected, running without switching: {error}")
        self._switching = False
        self._last_active_laser_id = None
        self._active_laser_lock = threading.Lock()

    def _read_frequency(self):
        """Read wavemeter (THz), infer which laser from frequency range."""
        try:
            with self._wavemeter_lock:
                frequency = self._wavemeter.get_frequency()
            laser_id = _frequency_to_laser_id(self._config, frequency)
            return laser_id, frequency
        except (EOFError, OSError, ConnectionResetError, BrokenPipeError):
            print("Wavemeter disconnected, reconnecting ...")
            if self._wavemeter.reconnect():
                print("Reconnected!")
                return 0, 0.0
            raise
        except RuntimeError as error:
            print(error)
            return 0, 0.0

    def _initialize_pid(self):
        """Set up PID for each laser. Auto-switches to each laser (if servo available), waits until wavemeter sees it."""
        pid_controllers = {}
        setpoints = {}
        for laser_id, laser_config in self._config["lasers"].items():
            pid_config = laser_config["pid"]
            if self._switcher is not None:
                print(f"Initializing PID on laser {laser_id}: switching to this laser ...")
                self._switcher.switch_to_laser(laser_id)
                time.sleep(1.0)
            else:
                print(f"Initializing PID on laser {laser_id}: unblock this laser so wavemeter can see it.")
            # Wait until wavemeter sees this laser (can hang if laser is off)
            while True:
                read_laser_id, frequency = self._read_frequency()
                if read_laser_id == laser_id:
                    setpoints[laser_id] = frequency
                    print(f"PID on laser {laser_id} initialized. Initial setpoint: {frequency}")
                    break

            seed = self._last_pid_output.get(laser_id, 0.0)
            setpoint = setpoints[laser_id]
            pid = PID(
                pid_config["Kp"],
                pid_config["Ki"],
                0.0,
                setpoint,
                sample_time=0.001,
                output_limits=(-10, 10),
                starting_output=seed,
            )
            pid_controllers[laser_id] = pid
        return pid_controllers, setpoints

    def _run_lock_loop(self, setpoints):
        """Loop: apply setpoint updates → read wavemeter → identify laser → run PID for that laser → DAC."""
        pid_keys = list(self._config["lasers"].keys())
        if not pid_keys:
            return
        last_laser_id = pid_keys[-1]

        while self._running:
            try:
                item = self._setpoint_queue.get(block=False)
                laser_id, frequency = item["laser_id"], item["frequency"]
                if laser_id in setpoints:
                    setpoints[laser_id] = frequency
                    print(f"[lock] New setpoint for {laser_id}: {frequency:.6f}")
                    self.setpoint_changed.emit(laser_id, frequency)
            except queue.Empty:
                pass

            laser_id, measured_frequency = self._read_frequency()
            if laser_id in self._config["lasers"]:  # valid laser; 0 = fiber switch or invalid
                with self._frequency_lock:
                    self._last_frequency[laser_id] = measured_frequency
                with self._active_laser_lock:
                    self._last_active_laser_id = laser_id

            if self._switching or laser_id == 0:
                # switching in progress or wavemeter saw no configured laser: disable all PIDs
                for pid in self._pid_controllers.values():
                    pid.set_auto_mode(False)
            elif laser_id == last_laser_id:
                self._run_single_pid_step(laser_id, setpoints, measured_frequency)
            else:
                # switched to other laser; resume its PID from last output
                if last_laser_id != 0:
                    self._pid_controllers[last_laser_id].set_auto_mode(False)
                self._pid_controllers[laser_id].set_auto_mode(
                    True, last_output=self._last_pid_output[laser_id]
                )
                self._run_single_pid_step(laser_id, setpoints, measured_frequency)

            last_laser_id = laser_id

    def _run_single_pid_step(self, laser_id, setpoints, measured_frequency):
        """One PID step: (setpoint - measured) → PID → DAC. Emit signals for UI."""
        self._pid_controllers[laser_id].setpoint = float(setpoints[laser_id])
        self._last_pid_output[laser_id] = self._pid_controllers[laser_id](measured_frequency)
        proportional, integral, _ = self._pid_controllers[laser_id].components
        self._last_proportional_term[laser_id] = proportional
        self._last_integral_term[laser_id] = integral

        self.pid_output_changed.emit(
            laser_id, self._last_pid_output[laser_id], proportional, integral
        )
        self.frequency_changed.emit(laser_id, measured_frequency)
        self._dac.set_output(laser_id, self._last_pid_output[laser_id])

    def start(self):
        if self._running:
            return

        self._pid_controllers, self._setpoints = self._initialize_pid()
        for laser_id, setpoint in self._setpoints.items():
            self.setpoint_changed.emit(laser_id, setpoint)

        self._lock_thread = threading.Thread(
            target=self._run_lock_loop, args=(self._setpoints,), daemon=True
        )

        self._running = True
        self._lock_thread.start()

    def get_frequency(self, laser_id):
        """Latest wavemeter reading (THz) for this laser, or None if not seen yet."""
        with self._frequency_lock:
            return self._last_frequency.get(laser_id)

    def get_setpoint(self, laser_id):
        """Current lock target (THz) for this laser."""
        if not self._running:
            return None
        try:
            return self._pid_controllers[laser_id].setpoint
        except KeyError:
            return None

    def submit_setpoint(self, laser_id, frequency):
        """Enqueue new lock target from GUI or remote (laser_server)."""
        if laser_id not in self._config["lasers"]:
            return
        self._setpoint_queue.put({"laser_id": laser_id, "frequency": frequency})

    def is_valid_laser_id(self, laser_id):
        """Whether this laser_id is configured (for remote server validation)."""
        return laser_id in self._config["lasers"]

    def get_current_laser(self):
        """Laser id currently seen by wavemeter (from lock loop), or None if unknown."""
        with self._active_laser_lock:
            return self._last_active_laser_id

    def switch_laser(self, laser_id):
        """Safely switch to laser_id: disable all PIDs, switch fiber, wait, then let lock loop re-enable."""
        if laser_id not in self._config["lasers"]:
            return
        if self._switcher is None:
            return
        if laser_id == self.get_current_laser():
            return
        self._switching = True
        time.sleep(0.05)  # let lock loop disable PIDs
        self._switcher.switch_to_laser(laser_id)
        time.sleep(1.0)  # fixed sleep for servo movement
        self._switching = False

    def close(self):
        """Stop loop, save PID output to file (for next launch), close wavemeter and DAC."""
        was_running = self._running
        self._running = False
        if was_running and getattr(self, "_lock_thread", None) is not None and self._lock_thread.is_alive():
            self._lock_thread.join(timeout=2.0)
        if was_running:
            state_path = Path(__file__).resolve().parent / self._config["last_pid_status"]
            try:
                with open(state_path, "w", encoding="utf-8") as state_file:
                    json.dump(self._last_pid_output, state_file)
            except Exception:
                pass
        try:
            self._dac.close()
        except Exception:
            pass
        try:
            if self._switcher is not None:
                self._switcher.close()
        except Exception:
            pass
        try:
            self._wavemeter.close()
        except Exception:
            pass


if __name__ == "__main__":

    from config import CONFIG

    locker = LaserLocker(CONFIG)

    try:
        locker.start()
    except KeyboardInterrupt:
        locker.close()
