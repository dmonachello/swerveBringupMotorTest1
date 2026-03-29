from __future__ import annotations

"""
NAME
    nt_labels.py - Encode labels for NetworkTables key paths.

SYNOPSIS
    from tools.common.nt_labels import encode_label_for_nt

DESCRIPTION
    Provides a stable encoding for device labels so they can be used safely
    as NetworkTables key segments without introducing unintended sub-tables.
"""

from urllib.parse import quote, unquote

ENCODING_UTF8 = "utf-8"
NT_LABEL_SAFE_CHARS = "-_.~"
NT_LABEL_EMPTY = ""
NT_LABEL_FALLBACK = "UNKNOWN"


def encode_label_for_nt(label: str) -> str:
    """
    NAME
        encode_label_for_nt - Encode a label for NT key usage.

    PARAMETERS
        label - Raw device label from bringup_system.json.

    RETURNS
        Encoded label safe for NT key segments.
    """
    if label is None:
        return NT_LABEL_FALLBACK
    raw = str(label)
    if not raw:
        return NT_LABEL_FALLBACK
    return quote(raw, safe=NT_LABEL_SAFE_CHARS, encoding=ENCODING_UTF8, errors="strict")


def decode_label_from_nt(label: str) -> str:
    """
    NAME
        decode_label_from_nt - Decode an NT label key to its display form.

    PARAMETERS
        label - Encoded label key segment.

    RETURNS
        Decoded label string.
    """
    if label is None:
        return NT_LABEL_EMPTY
    raw = str(label)
    if not raw:
        return NT_LABEL_EMPTY
    return unquote(raw, encoding=ENCODING_UTF8, errors="strict")
