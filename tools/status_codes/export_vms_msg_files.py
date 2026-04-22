"""
NAME
    export_vms_msg_files.py - Export status catalog as OpenVMS-style .MSG files.

SYNOPSIS
    python tools/status_codes/export_vms_msg_files.py

DESCRIPTION
    Reads the generated status code catalog and Python status message templates,
    then emits one .MSG source file per facility for review/reference.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT_DEPTH = 2
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.can_nt.status.status_catalog import FAC, MSG, SEV
from tools.can_nt.status.status_encode import decode
from tools.can_nt.status.status_messages import MESSAGE_TABLE
from tools.common.paths import repo_root

KEY_SEVERITY = "severity"
KEY_MESSAGE = "message"
KEY_FACILITY = "facility"

DIR_TOOLS = "tools"
DIR_STATUS_CODES = "status_codes"
DIR_VMS_MSG = "vms_msg"

FILE_EXT_MSG = ".MSG"

LINE_TITLE_FMT = ".TITLE {title}"
LINE_IDENT_FMT = ".IDENT /{ident}/"
LINE_FACILITY_FMT = ".FACILITY {facility},{number} /PREFIX={prefix}_"
LINE_SEVERITY_FMT = ".SEVERITY {severity}"
LINE_MESSAGE_FMT = "{name}, \"{text}\""
LINE_END = ".END"

SEV_INFORMATION = "INFORMATION"
SEVERITY_ORDER = {
    "SUCCESS": 0,
    "INFORMATION": 1,
    "WARNING": 2,
    "ERROR": 3,
    "FATAL": 4,
}

HEADER_COMMENT = "! Generated from Python status catalog and status templates."
HEADER_COMMENT_2 = "! Do not hand-edit generated files."


def _reverse_lookup(mapping: Dict[str, int], value: int) -> str:
    for key, mapped in mapping.items():
        if key.startswith("_"):
            continue
        if mapped == value:
            return key
    return "UNKNOWN"


def _severity_name_from_code(code_value: int) -> str:
    sev_value = decode(code_value)[KEY_SEVERITY]
    raw_name = _reverse_lookup(SEV.__dict__, sev_value)
    if raw_name == "INFO":
        return SEV_INFORMATION
    return raw_name


def _facility_name_from_code(code_value: int) -> str:
    fac_value = decode(code_value)[KEY_FACILITY]
    return _reverse_lookup(FAC.__dict__, fac_value)


def _message_name_from_code(code_value: int, facility_name: str) -> str:
    msg_value = decode(code_value)[KEY_MESSAGE]
    facility_obj = getattr(MSG, facility_name, None)
    if facility_obj is None:
        return "UNKNOWN_MESSAGE"
    return _reverse_lookup(getattr(facility_obj, "__dict__", {}), msg_value)


def _escape_text(text: str) -> str:
    return text.replace('"', "''")


def _group_entries() -> Dict[str, List[Tuple[str, str, str]]]:
    grouped: Dict[str, List[Tuple[str, str, str]]] = {}
    for code_value, template in MESSAGE_TABLE.items():
        facility_name = _facility_name_from_code(code_value)
        severity_name = _severity_name_from_code(code_value)
        message_name = _message_name_from_code(code_value, facility_name)
        entry = (severity_name, message_name, template)
        grouped.setdefault(facility_name, []).append(entry)
    for facility_name, entries in grouped.items():
        grouped[facility_name] = sorted(
            entries,
            key=lambda item: (SEVERITY_ORDER.get(item[0], 99), item[1]),
        )
    return grouped


def _build_file_lines(facility_name: str, entries: List[Tuple[str, str, str]]) -> List[str]:
    facility_code = getattr(FAC, facility_name)
    lines: List[str] = [
        HEADER_COMMENT,
        HEADER_COMMENT_2,
        LINE_TITLE_FMT.format(title=f"{facility_name}_STATUS_MESSAGES"),
        LINE_IDENT_FMT.format(ident=f"{facility_name}-V1"),
        LINE_FACILITY_FMT.format(
            facility=facility_name,
            number=facility_code,
            prefix=facility_name,
        ),
        "",
    ]
    current_severity = ""
    for severity_name, message_name, template in entries:
        if severity_name != current_severity:
            lines.append(LINE_SEVERITY_FMT.format(severity=severity_name))
            current_severity = severity_name
        lines.append(
            LINE_MESSAGE_FMT.format(
                name=message_name,
                text=_escape_text(str(template)),
            )
        )
    lines.append("")
    lines.append(LINE_END)
    return lines


def main() -> int:
    output_dir = Path(repo_root()) / DIR_TOOLS / DIR_STATUS_CODES / DIR_VMS_MSG
    output_dir.mkdir(parents=True, exist_ok=True)
    grouped = _group_entries()
    for facility_name, entries in grouped.items():
        filename = f"{facility_name}{FILE_EXT_MSG}"
        path = output_dir / filename
        content = "\n".join(_build_file_lines(facility_name, entries)) + "\n"
        path.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
