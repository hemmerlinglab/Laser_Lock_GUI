"""
LaserLocker API. All peripherals (SetpointServer, MainWindow) interact only with LaserLocker.

LaserLocker must provide:

  Methods (request/response):
    - get_freq(laserid: str) -> float | None     current measured freq, or None if unavailable
    - get_setpoint(laserid: str) -> float        current setpoint (may raise KeyError for unknown laserid)
    - submit_setpoint(laserid: str, freq: float) -> None   enqueue setpoint update

  Signals (push to GUI, PyQt):
    - freq_changed.emit(laserid, freq)
    - pid_changed.emit(laserid, output, p, i)
    - setpoint_changed.emit(laserid, value)
"""
