from __future__ import annotations

"""
NAME
    time_utils.py - Timestamp formatting helpers.

SYNOPSIS
    from tools.common.time_utils import timestamp_version

DESCRIPTION
    Provides consistent timestamp formatting for data_version fields and
    human-readable log entries.
"""

import time


def timestamp_version(ts: float | None = None) -> str:
    """
    NAME
        timestamp_version - Format timestamps for data_version fields.
    """
    if ts is None:
        ts = time.time()
    return time.strftime("%Y-%m-%d_%H%M%S", time.localtime(ts))


def timestamp_compact(prefix: str, ts: float | None = None) -> str:
    """
    NAME
        timestamp_compact - Format compact timestamp names with a prefix.
    """
    if ts is None:
        ts = time.time()
    return time.strftime(f"{prefix}_%Y%m%d_%H%M%S", time.localtime(ts))


def timestamp_human(ts: float | None = None) -> str:
    """
    NAME
        timestamp_human - Format timestamps for human-readable logs.
    """
    if ts is None:
        ts = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def timestamp_hms(ts: float | None = None) -> str:
    """
    NAME
        timestamp_hms - Format timestamps as HH:MM:SS.
    """
    if ts is None:
        ts = time.time()
    return time.strftime("%H:%M:%S", time.localtime(ts))
