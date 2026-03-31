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
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from tools.common.paths import repo_root

KEY_DATA = "data"
KEY_SEVERITIES = "severities"
KEY_FACILITIES = "facilities"
KEY_MESSAGES = "messages"

CATALOG_PATH = Path(repo_root()) / "tools" / "status_codes" / "status_codes.generated.json"


@dataclass(frozen=True)
class SeverityCodes:
    SUCCESS: int
    INFO: int
    WARNING: int
    ERROR: int
    FATAL: int


@dataclass(frozen=True)
class FacilityCodes:
    CLI_PARSER: int
    CLI_VALIDATOR: int
    EXECUTOR: int
    DEVICE: int
    GROUP: int
    INPUT_BINDING: int
    NETWORK: int
    CONFIG: int


class MessageCodes:
    def __init__(self, raw: Dict[str, Dict[str, int]]) -> None:
        self._raw = raw
        for facility, mapping in raw.items():
            obj = type(f"Msg_{facility}", (), mapping)
            setattr(self, facility, obj)


@dataclass(frozen=True)
class StatusCatalog:
    severities: Dict[str, int]
    facilities: Dict[str, int]
    messages: Dict[str, Dict[str, int]]


payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
_data = payload.get(KEY_DATA, {})

FAC = FacilityCodes(**_data.get(KEY_FACILITIES, {}))
SEV = SeverityCodes(**_data.get(KEY_SEVERITIES, {}))
MSG = MessageCodes(_data.get(KEY_MESSAGES, {}))
