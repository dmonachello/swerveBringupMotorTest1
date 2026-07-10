from __future__ import annotations

"""
NAME
    visibility_constants.py - Shared constants for multi-analyzer visibility.

SYNOPSIS
    from tools.can_nt.visibility_constants import VIS_KEY_SOURCES

DESCRIPTION
    Centralizes literals for the visibility provider and CLI/UI outputs.
"""

# Snapshot keys.
VIS_KEY_SOURCES = "sources"
VIS_KEY_DEVICES = "devices"
VIS_KEY_TIMEOUT_MS = "timeoutMs"
VIS_KEY_TS_MS = "tsMs"
VIS_KEY_SCOPE = "scope"
VIS_KEY_LABEL = "label"
VIS_KEY_KEY = "key"
VIS_KEY_IDENTITY = "identityKey"
VIS_KEY_VISIBILITY = "visibility"
VIS_KEY_METRICS = "metrics"
VIS_KEY_UNEXPECTED = "unexpected"
VIS_KEY_RAW_IDS = "rawIds"
VIS_KEY_AVAILABLE = "available"
VIS_KEY_ID = "id"
VIS_KEY_SOURCE = "source"

# Metrics keys.
VIS_KEY_AGE_MS = "ageMs"
VIS_KEY_FRAMES_PER_SEC = "framesPerSec"
VIS_KEY_MSG_COUNT = "msgCount"
VIS_KEY_LAST_SEEN_MS = "lastSeenMs"

# Raw CAN arbitration ID keys.
VIS_KEY_ARB_ID = "arbId"
VIS_KEY_ARB_HEX = "arbHex"
VIS_KEY_PRIORITY = "priority"
VIS_KEY_RESERVED = "reserved"
VIS_KEY_DATA_PAGE = "dataPage"
VIS_KEY_API_CLASS = "apiClass"
VIS_KEY_API_INDEX = "apiIndex"
VIS_KEY_PF = "pf"
VIS_KEY_PS = "ps"
VIS_KEY_SA = "sa"
VIS_KEY_PGN = "pgn"

# Device snapshot keys.
VIS_KEY_DEVICE = "device"

# Summary keys.
VIS_KEY_VISIBLE_ALL = "visibleAll"
VIS_KEY_VISIBLE_SOME = "visibleSome"
VIS_KEY_VISIBLE_NONE = "visibleNone"
VIS_KEY_DEVICES_SHOWN = "devicesShown"
VIS_KEY_SOURCES_COUNT = "sources"

# Scope values.
VIS_SCOPE_EXPECTED = "expected"
VIS_SCOPE_OBSERVED = "observed"
VIS_SCOPE_BOTH = "both"

# Visibility state markers.
VIS_VISIBLE_TRUE = True
VIS_VISIBLE_FALSE = False
VIS_VISIBLE_UNKNOWN = None

# Key formatting.
VIS_KEY_SEPARATOR = ":"
VIS_KEY_ARB_PREFIX = "arb:"
VIS_ARB_PREFIX = VIS_KEY_ARB_PREFIX
VIS_HEX_PREFIX = "0x"
VIS_HEX_FORMAT = "x"
VIS_EMPTY_STRING = ""

# Defaults.
VIS_TIMEOUT_MS_DEFAULT = 1000
VIS_RETENTION_MS_DEFAULT = 10000
VIS_RECENT_FRAME_HISTORY_DEFAULT = 4096

# Numeric constants.
VIS_INT_ZERO = 0
VIS_INT_ONE = 1
VIS_FLOAT_ZERO = 0.0
VIS_FLOAT_ONE = 1.0
VIS_MS_PER_SEC = 1000.0
