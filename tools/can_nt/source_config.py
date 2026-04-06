from __future__ import annotations

"""
NAME
    source_config.py - Multi-analyzer source configuration loader.

SYNOPSIS
    from tools.can_nt.source_config import load_sources_config

DESCRIPTION
    Loads source definitions for multiple CAN analyzers from a JSON file.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from tools.common.json_io import read_json

# Constants (JSON keys).
SRC_KEY_ROOT = "sources"
SRC_KEY_ID = "id"
SRC_KEY_LABEL = "label"
SRC_KEY_PORT = "port"
SRC_KEY_ENABLED = "enabled"
SRC_KEY_TIMEOUT_MS = "visibilityTimeoutMs"
SRC_KEY_INTERFACE = "interface"
SRC_KEY_BITRATE = "bitrate"

# Constants (defaults).
SRC_DEFAULT_ENABLED = True
SRC_EMPTY = ""

# Constants (errors).
SRC_ERR_READ = "Failed to read sources file: {exc}"
SRC_ERR_ROOT = "Sources file root must be a JSON object."
SRC_ERR_LIST = "Sources file must contain a 'sources' array."
SRC_ERR_MISSING_ID = "Source entry missing 'id'."


@dataclass
class SourceConfig:
    """
    NAME
        SourceConfig - Parsed analyzer source configuration.
    """

    source_id: str
    label: str
    port: str
    enabled: bool = SRC_DEFAULT_ENABLED
    visibility_timeout_ms: Optional[int] = None
    interface: Optional[str] = None
    bitrate: Optional[int] = None


def load_sources_config(path: str) -> Tuple[List[SourceConfig], str]:
    """
    NAME
        load_sources_config - Load sources from a JSON config file.

    PARAMETERS
        path: Path to a JSON file with a "sources" array.

    RETURNS
        (sources, error_message) where error_message is empty on success.
    """
    if not path:
        return [], SRC_EMPTY
    try:
        payload = read_json(path)
    except Exception as exc:
        return [], SRC_ERR_READ.format(exc=exc)
    if not isinstance(payload, dict):
        return [], SRC_ERR_ROOT
    entries = payload.get(SRC_KEY_ROOT)
    if not isinstance(entries, list):
        return [], SRC_ERR_LIST
    sources: List[SourceConfig] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        raw_id = entry.get(SRC_KEY_ID)
        source_id = str(raw_id).strip() if raw_id is not None else SRC_EMPTY
        if not source_id:
            return [], SRC_ERR_MISSING_ID
        label = str(entry.get(SRC_KEY_LABEL, source_id)).strip() or source_id
        port = str(entry.get(SRC_KEY_PORT, SRC_EMPTY)).strip()
        enabled = bool(entry.get(SRC_KEY_ENABLED, SRC_DEFAULT_ENABLED))
        timeout_raw = entry.get(SRC_KEY_TIMEOUT_MS)
        timeout_ms = int(timeout_raw) if isinstance(timeout_raw, (int, float)) else None
        interface = str(entry.get(SRC_KEY_INTERFACE)).strip() if entry.get(SRC_KEY_INTERFACE) else None
        bitrate_raw = entry.get(SRC_KEY_BITRATE)
        bitrate = int(bitrate_raw) if isinstance(bitrate_raw, (int, float)) else None
        sources.append(
            SourceConfig(
                source_id=source_id,
                label=label,
                port=port,
                enabled=enabled,
                visibility_timeout_ms=timeout_ms,
                interface=interface,
                bitrate=bitrate,
            )
        )
    return sources, SRC_EMPTY
