from __future__ import annotations

import os
import struct
import time


class PcapLogger:
    def __init__(self, path: str):
        self.path = path
        self._logger = None

    def start(self) -> bool:
        if not self.path:
            return False
        from can.io import Logger  # type: ignore
        try:
            if self._path_is_pcapng():
                self._logger = _PcapngWriter(self.path)
                self._logger.start()
            else:
                self._logger = Logger(self.path)
            return True
        except ValueError as exc:
            print(f"WARNING: {exc}. Logging disabled.")
            self._logger = None
            return False
        except RuntimeError as exc:
            print(f"WARNING: {exc}. Logging disabled.")
            self._logger = None
            return False

    def _path_is_pcapng(self) -> bool:
        return os.path.splitext(self.path)[1].lower() == ".pcapng"

    def log(self, msg) -> None:
        if self._logger is None:
            return
        try:
            self._logger.on_message_received(msg)
        except Exception:
            pass

    def stop(self) -> None:
        if self._logger is None:
            return
        try:
            self._logger.stop()
        except Exception:
            pass
        self._logger = None


class _PcapngWriter:
    _BLOCK_SHB = 0x0A0D0D0A
    _BLOCK_IDB = 0x00000001
    _BLOCK_EPB = 0x00000006

    _LINKTYPE_CAN_SOCKETCAN = 227
    _SNAPLEN = 0xFFFF

    _CAN_EFF_FLAG = 0x80000000
    _CAN_RTR_FLAG = 0x40000000
    _CAN_ERR_FLAG = 0x20000000

    _CANFD_BRS = 0x01
    _CANFD_ESI = 0x02
    _CANFD_FDF = 0x04

    def __init__(self, path: str):
        self._path = path
        self._file = None

    def start(self) -> None:
        self._file = open(self._path, "wb")
        self._write_shb()
        self._write_idb()

    def on_message_received(self, msg) -> None:
        if self._file is None:
            return
        payload = self._build_socketcan_payload(msg)
        self._write_epb(payload, self._timestamp_us(msg))

    def stop(self) -> None:
        if self._file is None:
            return
        self._file.flush()
        self._file.close()
        self._file = None

    def _write_shb(self) -> None:
        block_body = struct.pack(
            "<IHHq",
            0x1A2B3C4D,  # byte-order magic
            1,
            0,
            -1,  # section length unknown
        )
        self._write_block(self._BLOCK_SHB, block_body)

    def _write_idb(self) -> None:
        block_body = struct.pack(
            "<HHI",
            self._LINKTYPE_CAN_SOCKETCAN,
            0,
            self._SNAPLEN,
        )
        self._write_block(self._BLOCK_IDB, block_body)

    def _write_epb(self, packet_data: bytes, ts_us: int) -> None:
        ts_high = (ts_us >> 32) & 0xFFFFFFFF
        ts_low = ts_us & 0xFFFFFFFF
        cap_len = len(packet_data)
        epb_header = struct.pack("<IIII", 0, ts_high, ts_low, cap_len)
        epb_header += struct.pack("<I", cap_len)
        block_body = epb_header + self._pad4(packet_data)
        self._write_block(self._BLOCK_EPB, block_body)

    def _write_block(self, block_type: int, block_body: bytes) -> None:
        if self._file is None:
            return
        total_len = 12 + len(block_body)
        total_len += (-total_len) % 4
        header = struct.pack("<II", block_type, total_len)
        footer = struct.pack("<I", total_len)
        padding = b"\x00" * ((total_len - 12) - len(block_body))
        self._file.write(header)
        self._file.write(block_body)
        self._file.write(padding)
        self._file.write(footer)

    def _pad4(self, payload: bytes) -> bytes:
        pad = (-len(payload)) % 4
        if pad:
            return payload + (b"\x00" * pad)
        return payload

    def _timestamp_us(self, msg) -> int:
        ts = getattr(msg, "timestamp", None)
        if ts is None:
            ts = time.time()
        return int(ts * 1_000_000)

    def _build_socketcan_payload(self, msg) -> bytes:
        can_id = int(getattr(msg, "arbitration_id", 0))
        if getattr(msg, "is_extended_id", False):
            can_id |= self._CAN_EFF_FLAG
        if getattr(msg, "is_remote_frame", False):
            can_id |= self._CAN_RTR_FLAG
        if getattr(msg, "is_error_frame", False):
            can_id |= self._CAN_ERR_FLAG

        data = bytes(getattr(msg, "data", b"") or b"")
        dlc = getattr(msg, "dlc", None)
        if dlc is None:
            dlc = len(data)
        if getattr(msg, "is_remote_frame", False):
            data = b""

        fd_flags = 0
        if getattr(msg, "is_fd", False):
            fd_flags |= self._CANFD_FDF
            if getattr(msg, "bitrate_switch", False):
                fd_flags |= self._CANFD_BRS
            if getattr(msg, "error_state_indicator", False):
                fd_flags |= self._CANFD_ESI

        header = struct.pack(">IBBB", can_id, dlc & 0xFF, fd_flags & 0xFF, 0)
        header += b"\x00"
        return header + data
