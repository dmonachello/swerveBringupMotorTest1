"""
NAME
    export_vms_msg_full_surface.py - Export full status/error surfaces as OpenVMS-style .MSG files.

SYNOPSIS
    python tools/status_codes/export_vms_msg_full_surface.py

DESCRIPTION
    Generates inventory-backed .MSG files that cover:
    - canonical Python status definitions
    - unstructured Python status/error literals
    - unstructured Java status/error literals
    - Java ack/status literals

    This is additive to export_vms_msg_files.py and is intended for full-surface
    auditing/migration work.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

REPO_ROOT_DEPTH = 2
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.status_codes import inventory_status_surfaces

DIR_TOOLS = "tools"
DIR_STATUS_CODES = "status_codes"
DIR_REPORTS = "reports"
DIR_VMS_MSG_SURFACE = "vms_msg_surface"

FILE_INVENTORY_JSON = "status_surface_inventory.json"
FILE_EXT_MSG = ".MSG"

FILE_CANONICAL = "PY_CANONICAL_SURFACE.MSG"
FILE_PY_UNSTRUCTURED = "PY_UNSTRUCTURED_SURFACE.MSG"
FILE_JAVA_UNSTRUCTURED = "JAVA_UNSTRUCTURED_SURFACE.MSG"
FILE_JAVA_ACK = "JAVA_ACK_STATUS_SURFACE.MSG"

TITLE_CANONICAL = "PY_CANONICAL_SURFACE"
TITLE_PY_UNSTRUCTURED = "PY_UNSTRUCTURED_SURFACE"
TITLE_JAVA_UNSTRUCTURED = "JAVA_UNSTRUCTURED_SURFACE"
TITLE_JAVA_ACK = "JAVA_ACK_STATUS_SURFACE"

IDENT_CANONICAL = "PY-CANONICAL-V1"
IDENT_PY_UNSTRUCTURED = "PY-UNSTRUCTURED-V1"
IDENT_JAVA_UNSTRUCTURED = "JAVA-UNSTRUCTURED-V1"
IDENT_JAVA_ACK = "JAVA-ACK-V1"

FACILITY_CANONICAL = "PYCANON"
FACILITY_PY_UNSTRUCTURED = "PYUNSTR"
FACILITY_JAVA_UNSTRUCTURED = "JAVUNSTR"
FACILITY_JAVA_ACK = "JAVACK"

FACILITY_NUM_CANONICAL = 401
FACILITY_NUM_PY_UNSTRUCTURED = 402
FACILITY_NUM_JAVA_UNSTRUCTURED = 403
FACILITY_NUM_JAVA_ACK = 404

SEV_SUCCESS = "SUCCESS"
SEV_INFORMATION = "INFORMATION"
SEV_WARNING = "WARNING"
SEV_ERROR = "ERROR"
SEV_FATAL = "FATAL"

SEVERITY_ORDER = {
    SEV_SUCCESS: 0,
    SEV_INFORMATION: 1,
    SEV_WARNING: 2,
    SEV_ERROR: 3,
    SEV_FATAL: 4,
}

HEADER_COMMENT = "! Generated from full-surface status inventory."
HEADER_COMMENT_2 = "! AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration."

LINE_TITLE_FMT = ".TITLE {title}"
LINE_IDENT_FMT = ".IDENT /{ident}/"
LINE_FACILITY_FMT = ".FACILITY {facility},{number} /PREFIX={prefix}_"
LINE_SEVERITY_FMT = ".SEVERITY {severity}"
LINE_MESSAGE_FMT = "{name}, \"{text}\""
LINE_END = ".END"

KEY_GENERATED_AT = "generated_at_utc"
KEY_CANONICAL = "canonical_python_status_messages"
KEY_PY_UNSTRUCTURED = "unstructured_python_candidates"
KEY_JAVA_UNSTRUCTURED = "unstructured_java_candidates"
KEY_TEXT_LITERALS = "text_literals"
KEY_ACK_LITERALS = "ack_status_literals"

KEY_PATH = "path"
KEY_LINE = "line"
KEY_TEXT = "text"

REGEX_CANONICAL_SPLIT = re.compile(r"^(SS__[A-Z0-9_]+):\s*(.+)$")
REGEX_ANY_QUOTED = re.compile(r"['\"]([^'\"]{1,240})['\"]")
REGEX_SANITIZE_NAME = re.compile(r"[^A-Z0-9_]+")
REGEX_MULTI_UNDERSCORE = re.compile(r"_+")

MIN_NAME_LEN = 3
TRIM_QUOTE = "'\""


@dataclass
class MsgEntry:
    severity: str
    name: str
    text: str


def _load_inventory() -> Dict[str, object]:
    inventory_status_surfaces.main()
    inventory_path = (
        REPO_ROOT
        / DIR_TOOLS
        / DIR_STATUS_CODES
        / DIR_REPORTS
        / FILE_INVENTORY_JSON
    )
    return json.loads(inventory_path.read_text(encoding="utf-8"))


def _escape_text(text: str) -> str:
    return text.replace('"', "''")


def _classify_severity(text: str) -> str:
    upper_text = text.upper()
    if "FATAL" in upper_text:
        return SEV_FATAL
    if "ERROR" in upper_text:
        return SEV_ERROR
    if "WARNING" in upper_text:
        return SEV_WARNING
    if "SUCCESS" in upper_text:
        return SEV_SUCCESS
    if upper_text.strip() in {"OK", "ERROR"}:
        if upper_text == "OK":
            return SEV_SUCCESS
        return SEV_ERROR
    return SEV_INFORMATION


def _sanitize_message_name(name: str) -> str:
    normalized = REGEX_MULTI_UNDERSCORE.sub(
        "_",
        REGEX_SANITIZE_NAME.sub("_", name.upper()).strip("_"),
    )
    if len(normalized) < MIN_NAME_LEN:
        return "MSG"
    return normalized


def _build_name(prefix: str, path: str, line: int) -> str:
    path_token = Path(path).stem
    base = f"{prefix}_{path_token}_L{line}"
    return _sanitize_message_name(base)


def _extract_literal_text(code_text: str) -> str:
    matches = REGEX_ANY_QUOTED.findall(code_text)
    if matches:
        return matches[0].strip(TRIM_QUOTE)
    return code_text.strip()


def _canonical_entries(rows: Iterable[Dict[str, object]]) -> List[MsgEntry]:
    entries: List[MsgEntry] = []
    for row in rows:
        row_text = str(row[KEY_TEXT])
        match = REGEX_CANONICAL_SPLIT.match(row_text)
        if match:
            name = _sanitize_message_name(match.group(1))
            message_text = match.group(2)
        else:
            name = _build_name("CANON", str(row[KEY_PATH]), int(row[KEY_LINE]))
            message_text = row_text
        severity = _classify_severity(message_text)
        entries.append(MsgEntry(severity=severity, name=name, text=message_text))
    return entries


def _unstructured_entries(
    rows: Iterable[Dict[str, object]],
    prefix: str,
) -> List[MsgEntry]:
    entries: List[MsgEntry] = []
    for row in rows:
        path = str(row[KEY_PATH])
        line = int(row[KEY_LINE])
        code_text = str(row[KEY_TEXT])
        message_text = _extract_literal_text(code_text)
        severity = _classify_severity(message_text)
        name = _build_name(prefix, path, line)
        entries.append(MsgEntry(severity=severity, name=name, text=message_text))
    return entries


def _sort_entries(entries: Iterable[MsgEntry]) -> List[MsgEntry]:
    return sorted(
        entries,
        key=lambda item: (
            SEVERITY_ORDER.get(item.severity, 99),
            item.name,
        ),
    )


def _render_msg_file(
    title: str,
    ident: str,
    facility: str,
    facility_num: int,
    entries: Iterable[MsgEntry],
) -> str:
    lines: List[str] = [
        HEADER_COMMENT,
        HEADER_COMMENT_2,
        f"! Source inventory generated_at_utc: {payload_generated_at}",
        LINE_TITLE_FMT.format(title=title),
        LINE_IDENT_FMT.format(ident=ident),
        LINE_FACILITY_FMT.format(
            facility=facility,
            number=facility_num,
            prefix=facility,
        ),
        "",
    ]
    current_severity = ""
    for entry in _sort_entries(entries):
        if entry.severity != current_severity:
            lines.append(LINE_SEVERITY_FMT.format(severity=entry.severity))
            current_severity = entry.severity
        lines.append(
            LINE_MESSAGE_FMT.format(
                name=entry.name,
                text=_escape_text(entry.text),
            )
        )
    lines.append("")
    lines.append(LINE_END)
    return "\n".join(lines) + "\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


payload_generated_at = ""


def main() -> int:
    global payload_generated_at
    inventory = _load_inventory()
    payload_generated_at = str(inventory[KEY_GENERATED_AT])

    canonical = _canonical_entries(inventory[KEY_CANONICAL])
    py_unstructured = _unstructured_entries(inventory[KEY_PY_UNSTRUCTURED], "PY")
    java_text = _unstructured_entries(
        inventory[KEY_JAVA_UNSTRUCTURED][KEY_TEXT_LITERALS],
        "JAVA",
    )
    java_ack = _unstructured_entries(
        inventory[KEY_JAVA_UNSTRUCTURED][KEY_ACK_LITERALS],
        "ACK",
    )

    output_dir = REPO_ROOT / DIR_TOOLS / DIR_STATUS_CODES / DIR_VMS_MSG_SURFACE
    _write(
        output_dir / FILE_CANONICAL,
        _render_msg_file(
            title=TITLE_CANONICAL,
            ident=IDENT_CANONICAL,
            facility=FACILITY_CANONICAL,
            facility_num=FACILITY_NUM_CANONICAL,
            entries=canonical,
        ),
    )
    _write(
        output_dir / FILE_PY_UNSTRUCTURED,
        _render_msg_file(
            title=TITLE_PY_UNSTRUCTURED,
            ident=IDENT_PY_UNSTRUCTURED,
            facility=FACILITY_PY_UNSTRUCTURED,
            facility_num=FACILITY_NUM_PY_UNSTRUCTURED,
            entries=py_unstructured,
        ),
    )
    _write(
        output_dir / FILE_JAVA_UNSTRUCTURED,
        _render_msg_file(
            title=TITLE_JAVA_UNSTRUCTURED,
            ident=IDENT_JAVA_UNSTRUCTURED,
            facility=FACILITY_JAVA_UNSTRUCTURED,
            facility_num=FACILITY_NUM_JAVA_UNSTRUCTURED,
            entries=java_text,
        ),
    )
    _write(
        output_dir / FILE_JAVA_ACK,
        _render_msg_file(
            title=TITLE_JAVA_ACK,
            ident=IDENT_JAVA_ACK,
            facility=FACILITY_JAVA_ACK,
            facility_num=FACILITY_NUM_JAVA_ACK,
            entries=java_ack,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
