from __future__ import annotations

import os
import struct
import time


class PcapLogger:
    def __init__(self, path: str, pcapng_comment: str = "", pipe_name: str = ""):
        self.path = path
        self.pipe_name = pipe_name
        self._logger = None
        self._pcapng_comment = pcapng_comment

    def start(self) -> bool:
        if not self.path:
            if not self.pipe_name:
                return False
        from can.io import Logger  # type: ignore
        try:
            if self.pipe_name:
                if os.name != "nt":
                    raise RuntimeError("Named pipes are only supported on Windows.")
                pipe_path = _normalize_pipe_name(self.pipe_name)
                self.pipe_name = pipe_path
                pipe_file = _open_named_pipe_writer(pipe_path)
                self._logger = _PcapngWriter(
                    path=None,
                    comment=self._pcapng_comment,
                    file_obj=pipe_file,
                    flush_each_block=True,
                )
                self._logger.start()
            elif self._path_is_pcapng():
                self._logger = _PcapngWriter(self.path, self._pcapng_comment)
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

    def log(self, msg, timestamp_s: float | None = None) -> None:
        if self._logger is None:
            return
        if timestamp_s is not None:
            try:
                msg.timestamp = float(timestamp_s)
            except Exception:
                pass
        try:
            self._logger.on_message_received(msg)
        except Exception:
            pass

    def write_can_frame(
        self,
        timestamp_s: float,
        arb_id: int,
        data_bytes: bytes,
        is_extended: bool,
        is_rtr: bool,
        is_error: bool = False,
    ) -> bool:
        if self._logger is None:
            return False
        writer = getattr(self._logger, "write_can_frame", None)
        if not callable(writer):
            return False
        try:
            writer(timestamp_s, arb_id, data_bytes, is_extended, is_rtr, is_error)
            return True
        except Exception:
            return False

    def write_marker(
        self,
        timestamp_s: float,
        marker_id: int,
        key_char: str,
        counter: int,
        extra: int = 0,
    ) -> bool:
        if not key_char:
            return False
        key_byte = ord(key_char[0]) & 0xFF
        counter_byte = counter & 0xFF
        extra_low = extra & 0xFF
        extra_high = (extra >> 8) & 0xFF
        payload = bytes([0x4D, 0x41, 0x52, 0x4B, key_byte, counter_byte, extra_low, extra_high])
        return self.write_can_frame(timestamp_s, marker_id, payload, True, False)

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

    def __init__(
        self,
        path: str | None,
        comment: str = "",
        file_obj=None,
        flush_each_block: bool = False,
    ):
        self._path = path
        self._file = file_obj
        self._comment = comment
        self._flush_each_block = flush_each_block
        self._close_on_stop = file_obj is None

    def start(self) -> None:
        if self._file is None:
            self._file = open(self._path, "wb")
        self._write_shb(self._comment)
        self._write_idb()

    def on_message_received(self, msg) -> None:
        if self._file is None:
            return
        payload = self._build_socketcan_payload(msg)
        self._write_epb(payload, self._timestamp_us(msg))

    def stop(self) -> None:
        if self._file is None:
            return
        try:
            self._file.flush()
        except Exception:
            pass
        if self._close_on_stop:
            try:
                self._file.close()
            except Exception:
                pass
        self._file = None

    def write_can_frame(
        self,
        timestamp_s: float,
        arb_id: int,
        data_bytes: bytes,
        is_extended: bool,
        is_rtr: bool,
        is_error: bool,
    ) -> None:
        if self._file is None:
            return
        payload = self._build_socketcan_payload_raw(
            arb_id=arb_id,
            data=data_bytes,
            is_extended=is_extended,
            is_rtr=is_rtr,
            is_error=is_error,
        )
        self._write_epb(payload, self._timestamp_us_from_seconds(timestamp_s))

    def _write_shb(self, comment: str) -> None:
        block_body = struct.pack(
            "<IHHq",
            0x1A2B3C4D,  # byte-order magic
            1,
            0,
            -1,  # section length unknown
        )
        options = self._build_shb_options(comment)
        block_body += options
        self._write_block(self._BLOCK_SHB, block_body)

    def _build_shb_options(self, comment: str) -> bytes:
        if not comment:
            return struct.pack("<HH", 0, 0)
        value = comment.encode("utf-8", errors="replace")
        pad_len = (-len(value)) % 4
        opt = struct.pack("<HH", 1, len(value)) + value + (b"\x00" * pad_len)
        return opt + struct.pack("<HH", 0, 0)

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
        try:
            self._file.write(header)
            self._file.write(block_body)
            self._file.write(padding)
            self._file.write(footer)
            if self._flush_each_block:
                self._file.flush()
        except Exception:
            pass

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

    def _timestamp_us_from_seconds(self, ts: float) -> int:
        return int(float(ts) * 1_000_000)

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

    def _build_socketcan_payload_raw(
        self,
        arb_id: int,
        data: bytes,
        is_extended: bool,
        is_rtr: bool,
        is_error: bool,
    ) -> bytes:
        can_id = int(arb_id)
        if is_extended:
            can_id |= self._CAN_EFF_FLAG
        if is_rtr:
            can_id |= self._CAN_RTR_FLAG
        if is_error:
            can_id |= self._CAN_ERR_FLAG

        data_bytes = bytes(data or b"")
        if is_rtr:
            data_bytes = b""
        dlc = len(data_bytes)

        header = struct.pack(">IBBB", can_id, dlc & 0xFF, 0, 0)
        header += b"\x00"
        return header + data_bytes


def _normalize_pipe_name(name: str) -> str:
    if name.startswith("\\\\.\\pipe\\"):
        return name
    trimmed = name.strip().lstrip("\\")
    return f"\\\\.\\pipe\\{trimmed}"


def _open_named_pipe_writer(pipe_name: str):
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    PIPE_ACCESS_OUTBOUND = 0x00000002
    PIPE_TYPE_BYTE = 0x00000000
    PIPE_READMODE_BYTE = 0x00000000
    PIPE_WAIT = 0x00000000

    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
    ERROR_PIPE_CONNECTED = 535

    kernel32.CreateNamedPipeW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
    ]
    kernel32.CreateNamedPipeW.restype = wintypes.HANDLE
    kernel32.ConnectNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
    kernel32.ConnectNamedPipe.restype = wintypes.BOOL
    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD

    handle = kernel32.CreateNamedPipeW(
        pipe_name,
        PIPE_ACCESS_OUTBOUND,
        PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
        1,
        65536,
        65536,
        0,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        raise RuntimeError(f"CreateNamedPipe failed for {pipe_name}")

    connected = kernel32.ConnectNamedPipe(handle, None)
    if not connected:
        err = kernel32.GetLastError()
        if err != ERROR_PIPE_CONNECTED:
            raise RuntimeError(f"ConnectNamedPipe failed (err={err}) for {pipe_name}")

    fd = msvcrt.open_osfhandle(handle, os.O_WRONLY)
    return os.fdopen(fd, "wb", buffering=0)
