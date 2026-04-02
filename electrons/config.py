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

    # Lasers. Key = laser_id. Each entry: GUI (init_freq, step_size), wavemeter (freq_min/max), pid, dac, servo.
    "lasers": {
        "422": {
            "init_freq": "709.078380",
            "step_size": "10",
            "freq_min": 708,
            "freq_max": 710,
            "pid": {"Kp": 10, "Ki": 1200},
            "dac": {"arduino_no": 0, "DAC_chan": 1, "DAC_max_output": 4095.0},
            "servo": {1: 90, 2: 0},
        },
        "390": {
            "init_freq": "766.817850",
            "step_size": "10",
            "freq_min": 766,
            "freq_max": 770,
            "pid": {"Kp": -10, "Ki": -3000},
            "dac": {"arduino_no": 0, "DAC_chan": 2, "DAC_max_output": 3250.0},
            "servo": {1: 0, 2: 90},
        },
    },

    # Servo motor com port for fiber switching (controlled_servo.ino).
    "servo_com_port": "COM8",

    # Save PID output here on exit; loaded at startup to avoid frequency jump when re-launching.
    "last_pid_status": "laserlock_last_pid_state.json",
    "gui": {"title": "Laser Lock", "width": 400, "height": 290},
}
