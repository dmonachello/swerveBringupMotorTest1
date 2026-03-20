from __future__ import annotations

"""
NAME
    can_id.py - Shared helpers for FRC CAN arbitration IDs.

SYNOPSIS
    from tools.common.can_id import decode_frc_ext_id

DESCRIPTION
    Centralizes decoding of 29-bit FRC extended IDs to reduce drift across tools.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DecodedFrcId:
    """
    NAME
        DecodedFrcId - Parsed fields from an FRC extended arbitration ID.
    """
    manufacturer: int
    device_type: int
    api_class: int
    api_index: int
    device_id: int


def decode_frc_ext_id(arb: int) -> DecodedFrcId:
    """
    NAME
        decode_frc_ext_id - Decode a 29-bit FRC arbitration ID.
    """
    device_type = (arb >> 24) & 0x1F
    manufacturer = (arb >> 16) & 0xFF
    api_class = (arb >> 10) & 0x3F
    api_index = (arb >> 6) & 0x0F
    device_id = arb & 0x3F
    return DecodedFrcId(
        manufacturer=manufacturer,
        device_type=device_type,
        api_class=api_class,
        api_index=api_index,
        device_id=device_id,
    )
