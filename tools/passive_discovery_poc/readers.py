from __future__ import annotations

"""
NAME
    readers.py - Offline capture readers for passive discovery.

DESCRIPTION
    Provides offline readers for SocketCAN PCAPNG files and candump/text logs.
    The PCAPNG path is intentionally lightweight and targets the SocketCAN
    format already produced by existing repo tools.
"""

import re
import struct
from pathlib import Path
from typing import Iterable, Iterator, List

from tools.common.can_id import decode_frc_ext_id
from tools.passive_discovery_poc.metadata import normalize_device_type
from tools.passive_discovery_poc.constants import (
    CAN_EXT_ID_MAX,
    CAN_STD_ID_MAX,
    CANDUMP_LINE_REGEX,
    ENCODING_UTF8,
    EXT_LOG,
    EXT_PCAPNG,
    EXT_TXT,
    INT_EIGHT,
    INT_FOUR,
    INT_ONE,
    INT_ZERO,
    LINKTYPE_CAN_SOCKETCAN,
    ONE_MILLION,
    PCAPNG_BLOCK_ENHANCED_PACKET,
    PCAPNG_BLOCK_INTERFACE_DESCRIPTION,
    PCAPNG_BLOCK_SECTION_HEADER,
    SOCKETCAN_EFF_FLAG,
    SOCKETCAN_ERR_FLAG,
    SOCKETCAN_HEADER_LEN,
    SOCKETCAN_ID_MASK,
    SOCKETCAN_RTR_FLAG,
    SOURCE_KIND_CANDUMP,
    SOURCE_KIND_PCAPNG,
    STRUCT_ENDIAN_BIG,
    STRUCT_ENDIAN_LITTLE,
)
from tools.passive_discovery_poc.models import NormalizedFrame


def read_frames(input_path: str) -> List[NormalizedFrame]:
    """
    NAME
        read_frames - Dispatch offline frame reading by file suffix.
    """
    suffix = Path(input_path).suffix.lower()
    if suffix == EXT_PCAPNG:
        return list(read_socketcan_pcapng(input_path))
    if suffix in (EXT_LOG, EXT_TXT):
        return list(read_candump_text(input_path))
    return list(read_candump_text(input_path))


def read_socketcan_pcapng(input_path: str) -> Iterator[NormalizedFrame]:
    """
    NAME
        read_socketcan_pcapng - Yield normalized frames from a SocketCAN PCAPNG file.

    NOTES
        This reader targets the minimal PCAPNG format already emitted by the
        project's PCAPNG writer. It is not a general-purpose PCAPNG parser.
    """
    with Path(input_path).open("rb") as handle:
        linktype = None
        while True:
            header = handle.read(INT_EIGHT)
            if len(header) < INT_EIGHT:
                break
            block_type, block_total_len = struct.unpack(f"{STRUCT_ENDIAN_LITTLE}II", header)
            min_block_len = 12
            if block_total_len < min_block_len:
                raise ValueError("invalid pcapng block length")
            remaining_len = block_total_len - INT_EIGHT
            block_body_and_footer = handle.read(remaining_len)
            if len(block_body_and_footer) != remaining_len:
                raise ValueError("truncated pcapng block")
            block_body = block_body_and_footer[:-INT_FOUR]
            footer_len = struct.unpack(f"{STRUCT_ENDIAN_LITTLE}I", block_body_and_footer[-INT_FOUR:])[0]
            if footer_len != block_total_len:
                raise ValueError("pcapng footer length mismatch")
            if block_type == PCAPNG_BLOCK_SECTION_HEADER:
                continue
            if block_type == PCAPNG_BLOCK_INTERFACE_DESCRIPTION:
                linktype = struct.unpack(f"{STRUCT_ENDIAN_LITTLE}H", block_body[:2])[0]
                continue
            if block_type != PCAPNG_BLOCK_ENHANCED_PACKET:
                continue
            if linktype != LINKTYPE_CAN_SOCKETCAN:
                continue
            yield _parse_enhanced_packet_body(block_body=block_body, observer_source=SOURCE_KIND_PCAPNG)


def read_candump_text(input_path: str) -> Iterator[NormalizedFrame]:
    """
    NAME
        read_candump_text - Yield normalized frames from candump/text logs.
    """
    regex = re.compile(CANDUMP_LINE_REGEX)
    with Path(input_path).open("r", encoding=ENCODING_UTF8, errors="ignore") as handle:
        for line in handle:
            match = regex.match(line.strip())
            if match is None:
                continue
            timestamp_s = float(match.group("ts"))
            can_id = int(match.group("id"), 16)
            data_hex = str(match.group("data") or "").strip().upper()
            data_bytes = bytes.fromhex(data_hex) if data_hex else b""
            yield build_normalized_frame(
                timestamp_s=timestamp_s,
                can_id=can_id,
                data_bytes=data_bytes,
                is_extended=can_id > CAN_STD_ID_MAX,
                is_rtr=False,
                observer_source=SOURCE_KIND_CANDUMP,
            )


def _parse_enhanced_packet_body(block_body: bytes, observer_source: str) -> NormalizedFrame:
    """
    NAME
        _parse_enhanced_packet_body - Decode one Enhanced Packet Block payload.
    """
    if len(block_body) < 20:
        raise ValueError("enhanced packet block too short")
    interface_id, ts_high, ts_low, captured_len, packet_len = struct.unpack(
        f"{STRUCT_ENDIAN_LITTLE}IIIII", block_body[:20]
    )
    _ = interface_id
    _ = packet_len
    packet_data = block_body[20 : 20 + captured_len]
    ts_us = ((ts_high << 32) | ts_low)
    timestamp_s = float(ts_us) / ONE_MILLION
    if len(packet_data) < SOCKETCAN_HEADER_LEN:
        raise ValueError("socketcan packet too short")
    raw_can_id, dlc, _fd_flags, _reserved = struct.unpack(
        f"{STRUCT_ENDIAN_BIG}IBBB", packet_data[:7]
    )
    _ = _reserved
    raw_can_id_masked = raw_can_id & SOCKETCAN_ID_MASK
    is_extended = bool(raw_can_id & SOCKETCAN_EFF_FLAG)
    is_rtr = bool(raw_can_id & SOCKETCAN_RTR_FLAG)
    is_error = bool(raw_can_id & SOCKETCAN_ERR_FLAG)
    _ = is_error
    data_len = min(int(dlc), max(len(packet_data) - SOCKETCAN_HEADER_LEN, INT_ZERO))
    data_bytes = packet_data[SOCKETCAN_HEADER_LEN : SOCKETCAN_HEADER_LEN + data_len]
    return build_normalized_frame(
        timestamp_s=timestamp_s,
        can_id=raw_can_id_masked,
        data_bytes=data_bytes,
        is_extended=is_extended,
        is_rtr=is_rtr,
        observer_source=observer_source,
    )


def build_normalized_frame(
    timestamp_s: float,
    can_id: int,
    data_bytes: bytes,
    is_extended: bool,
    is_rtr: bool,
    observer_source: str,
) -> NormalizedFrame:
    """
    NAME
        build_normalized_frame - Convert raw frame fields into a normalized frame.
    """
    manufacturer = None
    device_type = None
    api_class = None
    api_index = None
    device_id = None
    if is_extended and can_id <= CAN_EXT_ID_MAX:
        decoded = decode_frc_ext_id(can_id)
        manufacturer = decoded.manufacturer
        device_type = normalize_device_type(decoded.manufacturer, decoded.device_type)
        api_class = decoded.api_class
        api_index = decoded.api_index
        device_id = decoded.device_id
    return NormalizedFrame(
        timestamp_s=float(timestamp_s),
        can_id=int(can_id),
        dlc=len(data_bytes),
        data_hex=data_bytes.hex(),
        is_extended=bool(is_extended),
        is_rtr=bool(is_rtr),
        manufacturer=manufacturer,
        device_type=device_type,
        api_class=api_class,
        api_index=api_index,
        device_id=device_id,
        observer_source=observer_source,
    )
