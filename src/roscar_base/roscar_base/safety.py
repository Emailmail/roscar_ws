"""Pure command limiting and watchdog helpers."""

from typing import Tuple


def safe_velocity(
    vx: float,
    vy: float,
    wz: float,
    command_age: float,
    timeout: float,
    max_linear: float,
    max_angular: float,
) -> Tuple[float, float, float]:
    if command_age < 0.0 or command_age > timeout:
        return 0.0, 0.0, 0.0
    return (
        max(-max_linear, min(max_linear, vx)),
        max(-max_linear, min(max_linear, vy)),
        max(-max_angular, min(max_angular, wz)),
    )
