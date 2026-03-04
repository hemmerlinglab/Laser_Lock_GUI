# Config for laser lock in electrons lab.
# Main program imports CONFIG. Edit values here to match your setup (COM port, IPs, PID gains).

CONFIG = {
    # Arduino that drives DAC for laser piezo/current. {arduino_no: "COMx"}.
    "arduino_com_ports": {0: "COM5"},
    # Bristol 871 wavemeter (Telnet). Read frequency here to know which laser is locked.
    "wavemeter_ip": "192.168.42.168",
    "wavemeter_port": 23,
    # TCP server for remote setpoint queries/updates (e.g. from another PC in the lab).
    "setpoint_server_ip": "192.168.42.26",
    "setpoint_server_port": 63700,
    # Per-laser PID and DAC mapping. 422 and 390 nm. Kp/Ki from lock optimization.
    "pids": {
        "422": {"laser": "422", "Kp": 10, "Ki": 1200, "arduino_no": 0, "DAC_chan": 1, "DAC_max_output": 4095.0},
        "390": {"laser": "390", "Kp": -10, "Ki": -3000, "arduino_no": 0, "DAC_chan": 2, "DAC_max_output": 3250.0},
    },
    # Initial offset and step for GUI. init_freq ~ lock point (THz).
    "lasers": [
        {"id": "422", "init_freq": "709.078380", "step_size": "10"},
        {"id": "390", "init_freq": "766.817850", "step_size": "10"},
    ],
    # Save PID output here on exit; loaded at startup to avoid frequency jump when re-launching.
    "last_pid_status": "laserlock_last_pid_state.json",
    "gui": {"title": "Laser Lock", "width": 400, "height": 290},
}
