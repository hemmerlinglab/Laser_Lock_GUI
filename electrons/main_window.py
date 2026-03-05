"""
Main window for Laser Lock. Shows frequency monitor, laser control (offset/shift/setpoint), PID monitor.
Talks to LaserLocker: submit_setpoint() for user edits; listens to frequency_changed, pid_output_changed, setpoint_changed.
"""

from functools import partial

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QLabel,
)


class MainWindow(QWidget):
    """
    UI only. Uses locker (LaserLocker) for setpoint submit and display updates.
    """

    def __init__(self, config, locker):
        """Initialize main window with config and locker."""
        super().__init__()
        self._config = config
        self._locker = locker
        self._last_offset = {}  # laser_id -> float, for recovering invalid input
        self._last_step = {}    # laser_id -> int, for recovering invalid step input
        self._build_ui()
        self._connect_locker()

    # 1) UI Layout
    # ========================================================
    def _build_ui(self):
        """
        Build UI (master layout).
        Master layout includes:
        1. Frequency monitor:   Display current measured frequency for each laser (390 and 422 for now).
        2. Laser control:       Display frequency offset, shift, step size, and setpoint for each laser.
                                User can edit frequency offset and shift to change setpoint.
        3. PID monitor:         Display current PID output, proportional term, and integral term for each laser.
        """

        # set window title and geometry
        gui_options = self._config.get("gui", {})
        self.setWindowTitle(gui_options.get("title", "Laser Lock"))
        self.setGeometry(0, 0, gui_options.get("width", 400), gui_options.get("height", 290))

        # define the master layout
        layout = QVBoxLayout()
        layout.addLayout(self._build_frequency_monitor())
        layout.addLayout(self._build_laser_control())
        layout.addLayout(self._build_pid_monitor())
        self.setLayout(layout)

    def _build_frequency_monitor(self):
        """
        Define the frequency monitor layout.
        Each laser has a single line titled "Act Frequency (Laser {laser_id}):" to display its measured frequency.
        Only for frequency display, no editing allowed.
        """

        # basic layout of frequency monitor UI
        horizontal = QHBoxLayout()
        self._frequency_lines = {}

        # build the widgets for each laser
        for laser in self._config["lasers"]:
            laser_id = laser["id"]
            line = QLineEdit("None")
            line.setReadOnly(True)
            self._frequency_lines[laser_id] = line
            vertical = QVBoxLayout()
            vertical.addWidget(QLabel(f"Act Frequency (Laser {laser_id}):"))
            vertical.addWidget(line)
            horizontal.addLayout(vertical)

        return horizontal

    def _build_laser_control(self):
        """
        Define the laser control layout.
        Each laser has four lines:
        1. Frequency Offset (THz):      (editable) Current frequency offset for the laser.
        2. Frequency Shift (MHz):       (editable) Current frequency shift for the laser.
        3. Step Size (MHz):             (editable) Current step size for the laser.
        4. Frequency Set Point (THz):   (read-only) Current setpoint for the laser.
                                        Frequency Set Point reflects the current setpoint for the laser.
                                        This value is kept to be frequency offset + frequency shift
                                        even when setpoint is changed by remote (e.g. setpoint_server.py).
        """

        # basic layout of laser control UI
        horizontal = QHBoxLayout()
        self._setpoint_lines = {}
        self._offset_lines = {}
        self._shift_spins = {}

        # build the widgets for each laser
        for laser in self._config["lasers"]:
            # get the laser id, initial frequency, and step size from the config
            laser_id = laser["id"]
            initial_frequency = laser["init_freq"]
            step_size = laser["step_size"]

            # initialize last valid values for rollback on invalid input
            self._last_offset[laser_id] = float(initial_frequency)
            self._last_step[laser_id] = max(1, int(step_size))

            # build the widgets
            step_line = QLineEdit(step_size)
            setpoint_line = QLineEdit(initial_frequency)
            setpoint_line.setReadOnly(True)
            spin = QSpinBox()
            offset_line = QLineEdit(initial_frequency)

            # store references for update_setpoint to keep offset/shift consistent
            self._setpoint_lines[laser_id] = setpoint_line
            self._offset_lines[laser_id] = offset_line
            self._shift_spins[laser_id] = spin

            # connect the signals for frequency shift, frequency offset, and step size
            # step size: textEdited = apply when valid; editingFinished = apply or rollback if invalid
            step_line.textEdited.connect(
                partial(self._apply_step, laser_id, spin, step_line)
            )
            step_line.editingFinished.connect(
                partial(self._on_step_finish, laser_id, spin, step_line)
            )
            offset_line.editingFinished.connect(
                partial(self._apply_offset, laser_id, offset_line, spin)
            )
            spin.valueChanged.connect(partial(self._on_shift_changed, laser_id, offset_line, spin))

            # set the properties of the spin box (frequency shift)
            spin.setSuffix(" MHz")
            spin.setMinimum(-100000)
            spin.setMaximum(100000)
            spin.setSingleStep(int(step_size))

            # arrange the layout
            vertical = QVBoxLayout()
            vertical.addWidget(QLabel("Frequency Offset (THz)"))
            vertical.addWidget(offset_line)
            vertical.addWidget(QLabel("Frequency Shift (MHz)"))
            vertical.addWidget(spin)
            vertical.addWidget(QLabel("Step Size (MHz)"))
            vertical.addWidget(step_line)
            vertical.addWidget(QLabel("Frequency Set Point (THz)"))
            vertical.addWidget(setpoint_line)
            horizontal.addLayout(vertical)

        return horizontal

    def _build_pid_monitor(self):
        """
        Define the PID monitor layout.
        Each laser has one line containing three boxes:
        1. PID Output:          Display the current PID output for the laser.
        2. Proportional Term:   Display the current proportional term for the laser.
        3. Integral Term:       Display the current integral term for the laser.
        All boxes are read-only.
        The PID output values are in the range of -10 to 10, converted into voltages on the Arduino end.
        Derivative term is not used (D=0).
        """

        # basic layout of PID monitor UI
        vertical = QVBoxLayout()
        self._pid_lines = {}

        # build the widgets for each laser
        for laser_id, pid_config in self._config["pids"].items():
            # build the components
            self._pid_lines[laser_id] = {
                "output": QLineEdit("None"),
                "proportional_term": QLineEdit("None"),
                "integral_term": QLineEdit("None"),
            }
            for widget in self._pid_lines[laser_id].values():
                widget.setReadOnly(True)

            # arrange the layout
            horizontal = QHBoxLayout()
            horizontal.addWidget(QLabel(f"{pid_config['laser']} Output:"))
            horizontal.addWidget(self._pid_lines[laser_id]["output"])
            horizontal.addWidget(QLabel("P:"))
            horizontal.addWidget(self._pid_lines[laser_id]["proportional_term"])
            horizontal.addWidget(QLabel("I:"))
            horizontal.addWidget(self._pid_lines[laser_id]["integral_term"])
            vertical.addLayout(horizontal)
            
        return vertical

    # 2) Internal Logics
    # ========================================================
    def _connect_locker(self):
        """Connect locker signals to display update slots."""
        self._locker.frequency_changed.connect(self.update_frequency)
        self._locker.pid_output_changed.connect(self.update_pid_output)
        self._locker.setpoint_changed.connect(self.update_setpoint)

    def _apply_step(self, laser_id, spin, step_line):
        """
        Apply step size. Returns True if applied, False if invalid.
        Triggered when the step size is edited (not required to press Enter or loses focus).
        """
        try:
            value = int(step_line.text().strip())
            if value <= 0:
                value = 1
        except (ValueError, TypeError):
            return False
        self._last_step[laser_id] = value
        if step_line.text() != str(value):
            step_line.blockSignals(True)
            step_line.setText(str(value))
            step_line.blockSignals(False)
        spin.setSingleStep(value)
        return True

    def _on_step_finish(self, laser_id, spin, step_line):
        """On Enter or focus loss: apply if valid, else rollback to last valid step."""
        if not self._apply_step(laser_id, spin, step_line):
            step_line.setText(str(self._last_step[laser_id]))

    def _apply_offset(self, laser_id, offset_line, spin):
        """
        On Enter or focus loss: apply if valid and send setpoint, else rollback.
        Triggered when the frequency offset is edited and the user presses Enter or loses focus.
        """
        try:
            offset = float(offset_line.text().strip())
            self._last_offset[laser_id] = offset
            formatted = f"{offset:.6f}"
            if formatted != offset_line.text():
                offset_line.setText(formatted)
        except (ValueError, TypeError):
            offset_line.setText(f"{self._last_offset[laser_id]:.6f}")
            return
        self._send_setpoint(laser_id, offset_line, spin)

    def _on_shift_changed(self, laser_id, offset_line, spin):
        self._send_setpoint(laser_id, offset_line, spin)

    def _send_setpoint(self, laser_id, offset_line, spin):
        """
        Send setpoint when offset or shift is changed (not triggered continuously).
        """
        try:
            offset = float(offset_line.text().strip())
        except (ValueError, TypeError):
            return
        frequency = offset + spin.value() * 1e-6
        self._locker.submit_setpoint(laser_id, frequency)

    # 3) External Interactions
    # ========================================================
    def update_frequency(self, laser_id, frequency):
        """
        Called when lock controller has new frequency.
        Update current measured frequency for the laser in the frequency monitor UI.
        """
        if laser_id in self._frequency_lines:
            self._frequency_lines[laser_id].setText(f"{frequency:.6f}")

    def update_pid_output(self, laser_id, output, proportional_term, integral_term):
        """
        Called when lock controller (usually LaserLocker) has new PID output.
        Update current PID output, proportional term, and integral term for the laser in the PID monitor UI.
        """
        if laser_id in self._pid_lines:
            lines = self._pid_lines[laser_id]
            lines["output"].setText(f"{output:.6f}")
            lines["proportional_term"].setText(f"{proportional_term:.6f}")
            lines["integral_term"].setText(f"{integral_term:.6f}")

    def update_setpoint(self, laser_id, value):
        """
        Called when setpoint changed (e.g. by remote). Update setpoint display and keep
        offset/shift consistent: keep shift unchanged, back-calculate offset = setpoint - shift*1e-6.
        Do not trigger another setpoint submit.
        """
        if laser_id not in self._setpoint_lines or laser_id not in self._offset_lines:
            return
        self._setpoint_lines[laser_id].setText(f"{value:.6f}")
        # keep shift unchanged, back-calculate offset
        spin = self._shift_spins[laser_id]
        offset = value - spin.value() * 1e-6
        self._last_offset[laser_id] = offset
        offset_line = self._offset_lines[laser_id]
        offset_line.blockSignals(True)
        offset_line.setText(f"{offset:.6f}")
        offset_line.blockSignals(False)

    def closeEvent(self, event):
        # Shutdown is handled by app.aboutToQuit in main.py; avoid double-close
        super().closeEvent(event)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    from config import CONFIG
    from laser_locker import LaserLocker

    app = QApplication(sys.argv)
    locker = LaserLocker(CONFIG)
    app.aboutToQuit.connect(locker.close)
    win = MainWindow(CONFIG, locker)
    win.show()
    sys.exit(app.exec_())
