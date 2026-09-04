"""Frame builders for the vehicle-to-viewer status WebSocket protocol.

The wire format is defined in ``doc/通信格式.md``: the Qt viewer accepts a
text JSON object ``{"type": "status", "x": ..., "y": ..., "yaw": ...,
"speed": ..., "battery": ..., "traffic": ...}`` and measures latency by
sending ``ping`` frames that must be echoed back as ``pong`` with the same
integer millisecond ``timestamp``.
"""

import math
import time
from typing import Any, Dict


STATUS_TYPE = "status"
PING_TYPE = "ping"
PONG_TYPE = "pong"
TRAFFIC_STATES = frozenset({"green", "red", "stop"})


class ProtocolError(ValueError):
    """Raised when a frame violates the status protocol."""


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolError(f"{field} must be a number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ProtocolError(f"{field} must be finite")
    return converted


def yaw_from_quaternion(quaternion: Any) -> float:
    """Return the planar yaw (radians) of a geometry_msgs Quaternion."""
    x = _finite_number(quaternion.x, "quaternion.x")
    y = _finite_number(quaternion.y, "quaternion.y")
    z = _finite_number(quaternion.z, "quaternion.z")
    w = _finite_number(quaternion.w, "quaternion.w")
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def normalize_traffic(value: Any) -> str:
    """Validate a traffic state and return its lowercase canonical form."""
    if not isinstance(value, str):
        raise ProtocolError("traffic must be a string")
    lowered = value.lower()
    if lowered not in TRAFFIC_STATES:
        raise ProtocolError(
            f"traffic must be one of {sorted(TRAFFIC_STATES)}, got {value!r}"
        )
    return lowered


def _timestamp_ms(timestamp: Any) -> int:
    if timestamp is None:
        return int(time.time() * 1000.0)
    if isinstance(timestamp, bool) or not isinstance(timestamp, int):
        raise ProtocolError("timestamp must be an integer")
    if timestamp < 0:
        raise ProtocolError("timestamp must be non-negative")
    return timestamp


def build_status_frame(
    x: Any,
    y: Any,
    yaw: Any,
    speed: Any,
    battery: Any,
    traffic: Any,
    timestamp: Any = None,
) -> Dict[str, Any]:
    """Validate inputs and return one complete status JSON object."""
    return {
        "type": STATUS_TYPE,
        "x": round(_finite_number(x, "x"), 4),
        "y": round(_finite_number(y, "y"), 4),
        "yaw": round(_finite_number(yaw, "yaw"), 4),
        "speed": round(_finite_number(speed, "speed"), 4),
        "battery": round(_finite_number(battery, "battery"), 4),
        "traffic": normalize_traffic(traffic),
        "timestamp": _timestamp_ms(timestamp),
    }


def build_pong_frame(ping: Any) -> Dict[str, Any]:
    """Validate an incoming ping object and return its pong echo."""
    if not isinstance(ping, dict):
        raise ProtocolError("frame must be an object")
    if ping.get("type") != PING_TYPE:
        raise ProtocolError(f"type does not match the protocol: {PING_TYPE!r} expected")
    timestamp = ping.get("timestamp")
    if timestamp is None:
        raise ProtocolError("ping.timestamp is required so pong can echo it")
    return {"type": PONG_TYPE, "timestamp": _timestamp_ms(timestamp)}
