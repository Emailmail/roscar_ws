"""Tests for the vehicle-to-viewer status WebSocket protocol."""

import json
import math
import random
from types import SimpleNamespace

import pytest

import send2server.status_node as status_node_module
from send2server.protocol import (
    ProtocolError,
    build_pong_frame,
    build_status_frame,
    normalize_traffic,
    yaw_from_quaternion,
)


def quaternion(yaw: float) -> SimpleNamespace:
    half = 0.5 * yaw
    return SimpleNamespace(x=0.0, y=0.0, z=math.sin(half), w=math.cos(half))


def test_status_frame_has_all_documented_fields():
    frame = build_status_frame(
        x=1.23456,
        y=-2.34567,
        yaw=0.78539816,
        speed=0.8,
        battery=24.6,
        traffic="green",
        timestamp=1756800000123,
    )
    assert frame == {
        "type": "status",
        "x": 1.2346,
        "y": -2.3457,
        "yaw": 0.7854,
        "speed": 0.8,
        "battery": 24.6,
        "traffic": "green",
        "timestamp": 1756800000123,
    }


def test_status_frame_timestamp_defaults_to_current_milliseconds():
    frame = build_status_frame(0.0, 0.0, 0.0, 0.0, 0.0, "green")
    assert isinstance(frame["timestamp"], int)
    assert frame["timestamp"] >= 0


@pytest.mark.parametrize(
    "field",
    ["x", "y", "yaw", "speed", "battery"],
)
@pytest.mark.parametrize("value", [True, "1", None, math.nan, math.inf, -math.inf])
def test_status_frame_rejects_invalid_numbers(field, value):
    with pytest.raises(ProtocolError):
        build_status_frame(
            **{field: value},
            **{name: 0.0 for name in ("x", "y", "yaw", "speed", "battery")
               if name != field},
            traffic="green",
        )


@pytest.mark.parametrize("value", ["GREEN", "Green", "red", "stop"])
def test_traffic_is_normalized_to_lowercase(value):
    frame = build_status_frame(0.0, 0.0, 0.0, 0.0, 0.0, value)
    assert frame["traffic"] == value.lower()


@pytest.mark.parametrize("value", ["yellow", "", 1, True, None])
def test_traffic_rejects_unknown_states(value):
    with pytest.raises(ProtocolError):
        normalize_traffic(value)


def test_random_status_values_survive_json_round_trip():
    generator = random.Random(20260904)
    for _ in range(50):
        values = [generator.uniform(-100.0, 100.0) for _ in range(5)]
        frame = build_status_frame(*values, "green", timestamp=42)
        restored = json.loads(json.dumps(frame, allow_nan=False))
        assert restored["type"] == "status"
        for name, value in zip(("x", "y", "yaw", "speed", "battery"), values):
            assert restored[name] == pytest.approx(value, abs=1e-4)


def test_pong_echoes_ping_timestamp():
    pong = build_pong_frame({"type": "ping", "timestamp": 1756800000123})
    assert pong == {"type": "pong", "timestamp": 1756800000123}


@pytest.mark.parametrize(
    "frame",
    [
        None,
        7,
        "ping",
        {},
        {"type": "pong", "timestamp": 1},
        {"type": "control", "steer": 0.0, "timestamp": 1},
        {"type": "ping"},
        {"type": "ping", "timestamp": None},
        {"type": "ping", "timestamp": True},
        {"type": "ping", "timestamp": 12.5},
        {"type": "ping", "timestamp": -1},
    ],
)
def test_pong_rejects_invalid_pings(frame):
    with pytest.raises(ProtocolError):
        build_pong_frame(frame)


@pytest.mark.parametrize(
    "yaw",
    [0.0, math.pi / 2, -math.pi / 2, math.pi, -2.5, 0.1],
)
def test_yaw_from_quaternion_round_trips(yaw):
    result = yaw_from_quaternion(quaternion(yaw))
    assert math.remainder(result - yaw, 2 * math.pi) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize("value", [True, "0.1", math.nan])
def test_yaw_from_quaternion_rejects_invalid_components(value):
    with pytest.raises(ProtocolError):
        yaw_from_quaternion(SimpleNamespace(x=value, y=0.0, z=0.0, w=1.0))


def test_node_module_imports_and_declares_default_port():
    assert status_node_module.DEFAULT_SERVER_URI == "ws://8.134.118.29:8772"
