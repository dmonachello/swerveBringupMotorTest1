"""
NAME
    status_result.py - StatusResult value container.

SYNOPSIS
    from tools.can_nt.status.status_result import StatusResult

DESCRIPTION
    Container for structured status outcomes, including optional payloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from tools.can_nt.status.status_encode import decode

KEY_SEVERITY = "severity"
EXIT_CODE_OK = 0
EXIT_CODE_ERROR = 2
EXIT_CODE_FATAL = 4
SEVERITY_ERROR = 3
SEVERITY_FATAL = 4


@dataclass(frozen=True)
class StatusResult:
    code: int
    message_args: Dict[str, object] = field(default_factory=dict)
    message: str = ""
    detail: str = ""
    payload: Optional[Dict[str, object]] = None
    exit_requested: bool = False

    def ok(self) -> bool:
        return decode(self.code)[KEY_SEVERITY] < SEVERITY_ERROR

    def exit_code(self) -> int:
        severity = decode(self.code)[KEY_SEVERITY]
        if severity >= SEVERITY_FATAL:
            return EXIT_CODE_FATAL
        if severity >= SEVERITY_ERROR:
            return EXIT_CODE_ERROR
        return EXIT_CODE_OK
