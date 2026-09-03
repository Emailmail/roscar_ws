"""Tests for the PC-to-Raspberry-Pi Twist protocol."""

import json
import math
import random

import pytest

from recv_from_server.protocol import ProtocolError, parse_twist_frame


def valid_frame():
    return {
        "source": "pc",
        "type": "ros_topic",
        "seq": 1,
        "timestamp": 123456789,
        "topic": "/cmdvel_remote",
        "msg_type": "geometry_msgs/msg/Twist",
        "data": {
            "linear": {"x": 1.0, "y": -2.5, "z": 0.0},
            "angular": {"x": 0.1, "y": 0.0, "z": -0.8},
        },
    }


def test_parse_twist_frame():
    frame = valid_frame()
    restored = parse_twist_frame(frame)
    assert restored == {
        "linear.x": 1.0,
        "linear.y": -2.5,
        "linear.z": 0.0,
        "angular.x": 0.1,
        "angular.y": 0.0,
        "angular.z": -0.8,
    }


def test_random_json_values_survive_decode():
    generator = random.Random(20260906)
    for sequence in range(1, 51):
        values = [generator.uniform(-10.0, 10.0) for _ in range(6)]
        frame = valid_frame()
        frame["seq"] = sequence
        frame["data"] = {
            "linear": {"x": values[0], "y": values[1], "z": values[2]},
            "angular": {"x": values[3], "y": values[4], "z": values[5]},
        }
        restored = parse_twist_frame(json.loads(json.dumps(frame, allow_nan=False)))
        assert list(restored.values()) == values


@pytest.mark.parametrize(
    "field,value",
    [
        ("source", "rk3576"),
        ("type", "control"),
        ("topic", "/cmd_vel"),
        ("msg_type", "std_msgs/msg/String"),
    ],
)
def test_rejects_wrong_envelope(field, value):
    frame = valid_frame()
    frame[field] = value
    with pytest.raises(ProtocolError):
        parse_twist_frame(frame)


@pytest.mark.parametrize("value", [True, "1", math.nan, math.inf, -math.inf])
def test_rejects_invalid_component(value):
    frame = valid_frame()
    frame["data"]["linear"]["x"] = value
    with pytest.raises(ProtocolError):
        parse_twist_frame(frame)
