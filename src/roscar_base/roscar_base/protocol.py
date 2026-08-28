"""Pure C30D serial protocol helpers.

The module deliberately has no ROS or serial-port dependency so protocol
handling can be tested without hardware.
"""

from dataclasses import dataclass
import struct
from typing import List

FRAME_HEADER = 0x7B
FRAME_TAIL = 0x7D
UPLINK_SIZE = 24
DOWNLINK_SIZE = 11


def xor_checksum(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return value


def _clamp_i16(value: int) -> int:
    return max(-32768, min(32767, value))


def encode_velocity_command(
    vx: float, vy: float, wz: float, command: int = 0x00
) -> bytes:
    """Encode SI velocity values into the 11-byte C30D downlink frame."""
    raw = tuple(_clamp_i16(round(value * 1000.0)) for value in (vx, vy, wz))
    frame = bytearray(DOWNLINK_SIZE)
    frame[0] = FRAME_HEADER
    frame[1] = command & 0xFF
    frame[2] = 0x00
    struct.pack_into('>hhh', frame, 3, *raw)
    frame[9] = xor_checksum(frame[:9])
    frame[10] = FRAME_TAIL
    return bytes(frame)


@dataclass(frozen=True)
class Telemetry:
    stopped: bool
    vx: float
    vy: float
    wz: float
    acceleration_raw: tuple[int, int, int]
    gyro_raw: tuple[int, int, int]
    voltage: float


def decode_telemetry(frame: bytes) -> Telemetry:
    if len(frame) != UPLINK_SIZE:
        raise ValueError(f'expected {UPLINK_SIZE} bytes, got {len(frame)}')
    if frame[0] != FRAME_HEADER or frame[-1] != FRAME_TAIL:
        raise ValueError('invalid frame boundary')
    if xor_checksum(frame[:22]) != frame[22]:
        raise ValueError('invalid checksum')

    values = struct.unpack_from('>hhhhhhhhhh', frame, 2)
    return Telemetry(
        stopped=frame[1] != 0,
        vx=values[0] / 1000.0,
        vy=values[1] / 1000.0,
        wz=values[2] / 1000.0,
        acceleration_raw=(values[3], values[4], values[5]),
        gyro_raw=(values[6], values[7], values[8]),
        voltage=values[9] / 1000.0,
    )


class TelemetryParser:
    """Incremental parser tolerant of noise, split frames and bad frames."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self.bad_frames = 0

    def feed(self, data: bytes) -> List[Telemetry]:
        self._buffer.extend(data)
        messages: List[Telemetry] = []
        while True:
            try:
                start = self._buffer.index(FRAME_HEADER)
            except ValueError:
                self._buffer.clear()
                break
            if start:
                del self._buffer[:start]
            if len(self._buffer) < UPLINK_SIZE:
                break
            candidate = bytes(self._buffer[:UPLINK_SIZE])
            try:
                messages.append(decode_telemetry(candidate))
                del self._buffer[:UPLINK_SIZE]
            except ValueError:
                self.bad_frames += 1
                del self._buffer[0]
        return messages
