"""Validation and decoding for the PC-to-vehicle Twist JSON frame."""

import math
from typing import Any, Dict


REMOTE_SOURCE = "pc"
FRAME_TYPE = "ros_topic"
MSG_TYPE = "geometry_msgs/msg/Twist"
DEFAULT_REMOTE_TOPIC = "/cmdvel_remote"


class ProtocolError(ValueError):
    """Raised when a received frame does not match the Twist protocol."""


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolError(f"{field} must be a number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ProtocolError(f"{field} must be finite")
    return converted


def parse_twist_frame(
    frame: Any,
    topic: str = DEFAULT_REMOTE_TOPIC,
) -> Dict[str, float]:
    """Validate a frame and return its six Twist components."""
    if not isinstance(frame, dict):
        raise ProtocolError("frame must be an object")

    expected = {
        "source": REMOTE_SOURCE,
        "type": FRAME_TYPE,
        "topic": topic,
        "msg_type": MSG_TYPE,
    }
    for field, expected_value in expected.items():
        if frame.get(field) != expected_value:
            raise ProtocolError(f"{field} does not match the protocol")

    sequence = frame.get("seq")
    timestamp = frame.get("timestamp")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ProtocolError("seq must be a positive integer")
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < 0:
        raise ProtocolError("timestamp must be a non-negative integer")

    data = frame.get("data")
    if not isinstance(data, dict):
        raise ProtocolError("data must be an object")
    linear = data.get("linear")
    angular = data.get("angular")
    if not isinstance(linear, dict) or not isinstance(angular, dict):
        raise ProtocolError("data.linear and data.angular must be objects")

    return {
        "linear.x": _finite_number(linear.get("x"), "linear.x"),
        "linear.y": _finite_number(linear.get("y"), "linear.y"),
        "linear.z": _finite_number(linear.get("z"), "linear.z"),
        "angular.x": _finite_number(angular.get("x"), "angular.x"),
        "angular.y": _finite_number(angular.get("y"), "angular.y"),
        "angular.z": _finite_number(angular.get("z"), "angular.z"),
    }
