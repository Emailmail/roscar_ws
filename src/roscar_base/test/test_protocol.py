import struct

import pytest

from roscar_base.protocol import (
    decode_telemetry, encode_velocity_command, TelemetryParser, xor_checksum,
)


def make_uplink(vx=100, vy=-200, wz=300):
    frame = bytearray(24)
    frame[0] = 0x7B
    struct.pack_into('>hhhhhhhhhh', frame, 2, vx, vy, wz, 1, 2, 3, 4, 5, 6, 12500)
    frame[22] = xor_checksum(frame[:22])
    frame[23] = 0x7D
    return bytes(frame)


def test_command_encoding_and_clamping():
    frame = encode_velocity_command(0.5, -0.25, 100.0)
    assert len(frame) == 11
    assert frame[0] == 0x7B and frame[-1] == 0x7D
    assert struct.unpack_from('>hhh', frame, 3) == (500, -250, 32767)
    assert frame[9] == xor_checksum(frame[:9])


def test_decode_telemetry():
    msg = decode_telemetry(make_uplink())
    assert msg.vx == pytest.approx(0.1)
    assert msg.vy == pytest.approx(-0.2)
    assert msg.wz == pytest.approx(0.3)
    assert msg.voltage == pytest.approx(12.5)


def test_parser_handles_split_noise_and_concatenated_frames():
    parser = TelemetryParser()
    first = make_uplink(100)
    second = make_uplink(200)
    assert parser.feed(b'noise' + first[:7]) == []
    messages = parser.feed(first[7:] + second)
    assert [msg.vx for msg in messages] == pytest.approx([0.1, 0.2])


def test_parser_recovers_after_bad_checksum():
    parser = TelemetryParser()
    bad = bytearray(make_uplink())
    bad[10] ^= 0xFF
    messages = parser.feed(bytes(bad) + make_uplink(400))
    assert len(messages) == 1
    assert messages[0].vx == pytest.approx(0.4)
    assert parser.bad_frames >= 1
