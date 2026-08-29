# -*- coding: utf-8 -*-
"""Serial transport and protocol parser for the DAMIAO DM-IMU-L1.

The USB stream contains independent, little-endian floating-point frames:

    55 AA device_id RID payload CRC16(LE) 0A

RID 0x01/0x02/0x03 carry three floats and are 19 bytes long. RID 0x04 carries
four quaternion floats (W, X, Y, Z) and is 23 bytes long. The device can emit
any subset of these frames, so parsing must use the RID to determine length.
"""
from __future__ import annotations

import os
import struct
import threading
import time
from typing import Dict, List, Optional, Tuple

import serial

from .dm_crc import dm_crc16

HDR = b'\x55\xAA'
TAIL = 0x0A
HEADER_LEN = 4
CRC_LEN = 2
TAIL_LEN = 1
VALID_RIDS = {0x01, 0x02, 0x03, 0x04}
PAYLOAD_FLOATS = {0x01: 3, 0x02: 3, 0x03: 3, 0x04: 4}

# Some firmware revisions calculate CRC with or without the 55 AA header.
# Try the documented frame form first, then retain compatibility with both.
SKIP_HDR_IN_CRC = False

Packet = Tuple[int, Tuple[float, ...]]
LatestData = Tuple[Optional[Tuple[float, ...]], float, int]


class DM_Serial:
    """Non-blocking reader with per-RID caches and serial reconnect support."""

    def __init__(self, port: str, baudrate: int):
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout = 0.0
        self.ser: Optional[serial.Serial] = None
        self._buf = bytearray()

        self.cnt_ok = 0
        self.cnt_crc = 0
        self.cnt_short = 0
        self.cnt_nohdr = 0
        self.cnt_invalid = 0

        self._th: Optional[threading.Thread] = None
        self._stop_evt: Optional[threading.Event] = None
        self._read_sleep = 0.001

        self._latest_lock = threading.Lock()
        self._latest_pkt: Optional[Packet] = None
        self._latest_ts = 0.0
        self._latest_count = 0
        self._latest_by_rid: Dict[int, LatestData] = {
            rid: (None, 0.0, 0) for rid in VALID_RIDS
        }
        self._last_error: Optional[str] = None

        self._open()

    # ------------ Public API ------------
    def read(self, max_bytes: int | None = None) -> Optional[Packet]:
        """Read and parse available bytes, returning the last parsed packet."""
        frames = self.read_all(max_bytes)
        return frames[-1] if frames else None

    def read_all(self, max_bytes: int | None = None) -> List[Packet]:
        """Read and parse all complete frames currently available."""
        if not self.ser or not self.ser.is_open:
            return []
        self._read_into_buf(max_bytes)
        return self._parse_all()

    def start_reader(self, read_sleep: float = 0.001) -> bool:
        """Start the background reader thread."""
        if self._th and self._th.is_alive():
            self._read_sleep = read_sleep
            return True
        if not self.is_open and not self._open():
            return False
        self._stop_evt = threading.Event()
        self._read_sleep = read_sleep
        self._th = threading.Thread(target=self._reader_loop, daemon=True)
        self._th.start()
        return True

    def stop_reader(self) -> None:
        """Stop the background reader thread."""
        if self._stop_evt:
            self._stop_evt.set()
        if self._th:
            self._th.join(timeout=1.0)
        self._th = None
        self._stop_evt = None

    def get_latest(self) -> Tuple[Optional[Packet], float, int]:
        """Return the most recently received packet, timestamp and count."""
        with self._latest_lock:
            return self._latest_pkt, self._latest_ts, self._latest_count

    def get_latest_by_rid(self, rid: int) -> LatestData:
        """Return ``(values, timestamp, count)`` for one protocol RID."""
        with self._latest_lock:
            return self._latest_by_rid.get(rid, (None, 0.0, 0))

    def get_latest_all(self):
        """Return the legacy accel/gyro/RPY cache tuple used by the node."""
        accel, accel_ts, accel_count = self.get_latest_by_rid(0x01)
        gyro, gyro_ts, gyro_count = self.get_latest_by_rid(0x02)
        rpy, rpy_ts, rpy_count = self.get_latest_by_rid(0x03)
        return (
            accel,
            gyro,
            rpy,
            accel_ts,
            gyro_ts,
            rpy_ts,
            accel_count,
            gyro_count,
            rpy_count,
        )

    def get_latest_quaternion(self) -> LatestData:
        """Return the latest protocol quaternion in W, X, Y, Z order."""
        return self.get_latest_by_rid(0x04)

    def get_stats(self) -> dict:
        """Return parser counters for diagnostics."""
        with self._latest_lock:
            return {
                'ok': self.cnt_ok,
                'crc': self.cnt_crc,
                'short': self.cnt_short,
                'nohdr': self.cnt_nohdr,
                'invalid': self.cnt_invalid,
                'frames': self._latest_count,
                'accel': self._latest_by_rid[0x01][2],
                'gyro': self._latest_by_rid[0x02][2],
                'rpy': self._latest_by_rid[0x03][2],
                'quaternion': self._latest_by_rid[0x04][2],
            }

    def last_error(self) -> Optional[str]:
        return self._last_error

    def debug_read_raw_frames(self, max_bytes: int = 512, max_frames: int = 3) -> List[str]:
        """Return up to ``max_frames`` complete raw frames as hex strings."""
        if not self.ser or not self.ser.is_open:
            return []
        self._read_into_buf(max_bytes)
        frames: List[str] = []
        buf = self._buf
        offset = 0
        while len(frames) < max_frames:
            start = buf.find(HDR, offset)
            if start < 0 or len(buf) - start < HEADER_LEN:
                break
            frame_len = self._frame_length(buf[start + 3])
            if frame_len is None or len(buf) - start < frame_len:
                break
            frames.append(bytes(buf[start:start + frame_len]).hex())
            offset = start + frame_len
        return frames

    def close(self) -> None:
        """Close the reader and serial device."""
        self.stop_reader()
        if self.ser:
            try:
                self.ser.close()
            finally:
                self.ser = None

    # Keep the original misspelled API for callers from the extracted pack.
    def destory(self) -> None:
        self.close()

    def destroy(self) -> None:
        self.close()

    def reopen(self) -> bool:
        """Close and reopen the serial device."""
        self.close()
        return self._open()

    @property
    def is_open(self) -> bool:
        return bool(self.ser and self.ser.is_open)

    # ------------ Internal implementation ------------
    def _open(self) -> bool:
        try:
            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout,
                write_timeout=0,
                # TIOCEXCL: a stale duplicate of this node must fail to open
                # the port instead of silently interleaving /imu/data stamps
                # from two processes, which breaks Cartographer ordering.
                exclusive=True,
            )
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass
            self._last_error = None
            return True
        except Exception as exc:
            self._last_error = str(exc)
            self.ser = None
            return False

    def _reader_loop(self) -> None:
        evt = self._stop_evt
        while evt and not evt.is_set():
            try:
                frames = self.read_all(None)
                if frames:
                    self._update_latest(frames)
                if self._read_sleep > 0.0:
                    time.sleep(self._read_sleep)
            except (serial.SerialException, OSError, IOError) as exc:
                self._last_error = f'USB I/O error: {exc!r}, reconnecting...'
                self._close_serial()
                if not self._wait_reconnect(evt):
                    break
            except Exception as exc:
                self._last_error = f'reader_loop: {exc!r}'
                time.sleep(0.01)

    def _update_latest(self, frames: List[Packet]) -> None:
        now = time.time()
        with self._latest_lock:
            for pkt in frames:
                rid, values = pkt
                self._latest_pkt = pkt
                self._latest_ts = now
                self._latest_count += 1
                _, _, count = self._latest_by_rid[rid]
                self._latest_by_rid[rid] = (values, now, count + 1)

    def _close_serial(self) -> None:
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            finally:
                self.ser = None

    def _wait_reconnect(self, evt: threading.Event) -> bool:
        while not evt.is_set():
            if os.path.exists(self.port) and self._open():
                self._buf.clear()
                return True
            evt.wait(0.5)
        return False

    def _read_into_buf(self, max_bytes: Optional[int]) -> int:
        n = getattr(self.ser, 'in_waiting', 0) if self.ser else 0
        if max_bytes is not None:
            n = min(n, max_bytes)
        if n <= 0:
            return 0
        self._buf.extend(self.ser.read(n))
        return n

    @staticmethod
    def _frame_length(rid: int) -> Optional[int]:
        payload_floats = PAYLOAD_FLOATS.get(rid)
        if payload_floats is None:
            return None
        return HEADER_LEN + payload_floats * 4 + CRC_LEN + TAIL_LEN

    def _parse_all(self) -> List[Packet]:
        results: List[Packet] = []
        buf = self._buf

        while True:
            start = buf.find(HDR)
            if start < 0:
                self._buf = bytearray(buf[-1:] if buf else b'')
                if buf:
                    self.cnt_nohdr += 1
                break
            if start:
                self.cnt_nohdr += 1
                buf = buf[start:]

            if len(buf) < HEADER_LEN:
                self._buf = bytearray(buf)
                self.cnt_short += 1
                break

            rid = buf[3]
            frame_len = self._frame_length(rid)
            if frame_len is None:
                self.cnt_invalid += 1
                buf = buf[1:]
                continue
            if len(buf) < frame_len:
                self._buf = bytearray(buf)
                self.cnt_short += 1
                break

            frame = bytes(buf[:frame_len])
            if frame[-1] != TAIL:
                self.cnt_invalid += 1
                buf = buf[1:]
                continue

            crc_wire = frame[-3] | (frame[-2] << 8)
            crc_calc = dm_crc16(frame[:-3])
            if crc_calc != crc_wire:
                if dm_crc16(frame[2:-3]) != crc_wire:
                    self.cnt_crc += 1
                    buf = buf[1:]
                    continue

            values = struct.unpack('<' + 'f' * PAYLOAD_FLOATS[rid], frame[4:-3])
            results.append((rid, tuple(values)))
            buf = buf[frame_len:]

        self.cnt_ok += len(results)
        return results
