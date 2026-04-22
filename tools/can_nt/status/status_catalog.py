"""
NAME
    status_catalog.py - Load status code catalog into enums.

SYNOPSIS
    from tools.can_nt.status.status_catalog import FAC, SEV, MSG

DESCRIPTION
    Loads the generated status code catalog and exposes facility, severity,
    and message constants grouped by facility.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from tools.common.paths import repo_root

KEY_DATA = "data"
KEY_SEVERITIES = "severities"
KEY_FACILITIES = "facilities"
KEY_MESSAGES = "messages"
KEY_SOURCE_HASH = "sourceHash"

CATALOG_PATH = Path(repo_root()) / "tools" / "status_codes" / "status_codes.generated.json"
COMPILED_CATALOG_PATH = (
    Path(repo_root()) / "tools" / "status_codes" / "generated" / "status_catalog.compiled.json"
)


class _Codes:
    def __init__(self, raw: Dict[str, int]) -> None:
        self._raw = raw
        for key, value in raw.items():
            setattr(self, key, value)


class MessageCodes:
    def __init__(self, raw: Dict[str, Dict[str, int]]) -> None:
        self._raw = raw
        for facility, mapping in raw.items():
            obj = type(f"Msg_{facility}", (), mapping)
            setattr(self, facility, obj)


payload_path = COMPILED_CATALOG_PATH if COMPILED_CATALOG_PATH.exists() else CATALOG_PATH
payload = json.loads(payload_path.read_text(encoding="utf-8"))
_data = payload.get(KEY_DATA, {})
SOURCE_HASH = payload.get(KEY_SOURCE_HASH, "")

FAC = _Codes(_data.get(KEY_FACILITIES, {}))
SEV = _Codes(_data.get(KEY_SEVERITIES, {}))
MSG = MessageCodes(_data.get(KEY_MESSAGES, {}))
