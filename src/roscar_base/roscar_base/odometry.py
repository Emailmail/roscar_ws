"""Planar body-velocity odometry independent of ROS messages."""

from dataclasses import dataclass
import math


def normalize_angle(value: float) -> float:
    return math.atan2(math.sin(value), math.cos(value))


@dataclass
class PlanarOdometry:
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0

    def integrate(self, vx: float, vy: float, wz: float, dt: float) -> None:
        if not math.isfinite(dt) or dt <= 0.0:
            return
        # Midpoint heading reduces integration error while rotating.
        heading = self.yaw + 0.5 * wz * dt
        self.x += (vx * math.cos(heading) - vy * math.sin(heading)) * dt
        self.y += (vx * math.sin(heading) + vy * math.cos(heading)) * dt
        self.yaw = normalize_angle(self.yaw + wz * dt)
