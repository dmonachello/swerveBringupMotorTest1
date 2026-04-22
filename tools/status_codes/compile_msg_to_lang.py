"""
NAME
    compile_msg_to_lang.py - Compile OpenVMS-style .MSG files into Python and Java status artifacts.

SYNOPSIS
    python tools/status_codes/compile_msg_to_lang.py
    python tools/status_codes/compile_msg_to_lang.py --check

DESCRIPTION
    Parses .MSG sources and generates:
    - compiled status catalog JSON
    - Python generated status constants/messages modules
    - Java generated status constants/messages classes

    In check mode, validates that generated outputs are up to date.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

REPO_ROOT_DEPTH = 2
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_SRC_DIR = "tools/status_codes/vms_msg"
DEFAULT_OUT_CATALOG = "tools/status_codes/generated/status_catalog.compiled.json"
DEFAULT_OUT_PY_DIR = "tools/can_nt/status/generated"
DEFAULT_OUT_JAVA_DIR = "src/main/java/frc/robot/status/generated"

FILE_PY_CATALOG = "status_catalog_generated.py"
FILE_PY_MESSAGES = "status_messages_generated.py"
FILE_JAVA_CATALOG = "StatusCatalogGenerated.java"
FILE_JAVA_MESSAGES = "StatusMessagesGenerated.java"

ENCODING_UTF8 = "utf-8"

EXT_MSG = ".msg"

DIRECTIVE_TITLE = ".TITLE"
DIRECTIVE_IDENT = ".IDENT"
DIRECTIVE_FACILITY = ".FACILITY"
DIRECTIVE_SEVERITY = ".SEVERITY"
DIRECTIVE_END = ".END"

SEV_SUCCESS = "SUCCESS"
SEV_INFORMATION = "INFORMATION"
SEV_WARNING = "WARNING"
SEV_ERROR = "ERROR"
SEV_FATAL = "FATAL"

SEVERITY_NAME_TO_VALUE = {
    SEV_SUCCESS: 0,
    SEV_INFORMATION: 1,
    SEV_WARNING: 2,
    SEV_ERROR: 3,
    SEV_FATAL: 4,
}

SEVERITY_VALUE_TO_PY = {
    0: "SUCCESS",
    1: "INFO",
    2: "WARNING",
    3: "ERROR",
    4: "FATAL",
}

SHIFT_SEVERITY = 0
SHIFT_MESSAGE = 3
SHIFT_FACILITY = 16

REGEX_FACILITY = re.compile(r"^\.FACILITY\s+([A-Za-z0-9_]+)\s*,\s*([0-9]+)(?:\s+/PREFIX=([A-Za-z0-9_]+)_)?\s*$")
REGEX_IDENT = re.compile(r"^\.IDENT\s+/([^/]+)/\s*$")
REGEX_TITLE = re.compile(r"^\.TITLE\s+(.+?)\s*$")
REGEX_SEVERITY = re.compile(r"^\.SEVERITY\s+([A-Za-z]+)\s*$")
REGEX_MESSAGE = re.compile(r'^([A-Za-z0-9_]+)\s*,\s*"(.*)"\s*$')

TEXT_COMMENT_PREFIX = "!"
TEXT_EMPTY = ""

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_STALE = 2

KEY_VERSION = "version"
KEY_GENERATED_FROM = "generatedFrom"
KEY_GENERATED_NOTICE = "_generatedNotice"
KEY_SOURCE_HASH = "sourceHash"
KEY_SOURCES = "sources"
KEY_DATA = "data"
KEY_SEVERITIES = "severities"
KEY_FACILITIES = "facilities"
KEY_MESSAGES = "messages"
KEY_MESSAGE_TEXT = "messageText"

CATALOG_VERSION = "1"
GENERATED_NOTICE_TEXT = "AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration."


@dataclass
class MsgDefinition:
    facility_name: str
    facility_value: int
    message_name: str
    message_value: int
    severity_name: str
    severity_value: int
    text: str
    source_file: str
    source_line: int


def _encode_status(severity: int, facility: int, message: int) -> int:
    return (facility << SHIFT_FACILITY) | (message << SHIFT_MESSAGE) | (severity << SHIFT_SEVERITY)


def _iter_msg_files(src_dirs: Sequence[Path]) -> List[Path]:
    files: List[Path] = []
    for src in src_dirs:
        if not src.exists():
            continue
        for path in sorted(src.rglob("*")):
            if path.is_file() and path.suffix.lower() == EXT_MSG:
                files.append(path)
    return files


def _parse_msg_file(path: Path) -> List[MsgDefinition]:
    lines = path.read_text(encoding=ENCODING_UTF8).splitlines()
    title = TEXT_EMPTY
    ident = TEXT_EMPTY
    facility_name = TEXT_EMPTY
    facility_value = 0
    severity_name = TEXT_EMPTY
    msg_number = 0
    seen_end = False
    parsed: List[MsgDefinition] = []

    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith(TEXT_COMMENT_PREFIX):
            continue
        if line.startswith(DIRECTIVE_TITLE):
            match = REGEX_TITLE.match(line)
            if not match:
                raise ValueError(f"Invalid .TITLE syntax in {path}:{line_number}")
            title = match.group(1).strip()
            continue
        if line.startswith(DIRECTIVE_IDENT):
            match = REGEX_IDENT.match(line)
            if not match:
                raise ValueError(f"Invalid .IDENT syntax in {path}:{line_number}")
            ident = match.group(1).strip()
            continue
        if line.startswith(DIRECTIVE_FACILITY):
            match = REGEX_FACILITY.match(line)
            if not match:
                raise ValueError(f"Invalid .FACILITY syntax in {path}:{line_number}")
            facility_name = match.group(1).strip().upper()
            facility_value = int(match.group(2))
            msg_number = 0
            continue
        if line.startswith(DIRECTIVE_SEVERITY):
            match = REGEX_SEVERITY.match(line)
            if not match:
                raise ValueError(f"Invalid .SEVERITY syntax in {path}:{line_number}")
            candidate = match.group(1).strip().upper()
            if candidate not in SEVERITY_NAME_TO_VALUE:
                raise ValueError(f"Unknown severity {candidate} in {path}:{line_number}")
            severity_name = candidate
            continue
        if line.startswith(DIRECTIVE_END):
            seen_end = True
            continue

        msg_match = REGEX_MESSAGE.match(line)
        if msg_match:
            if not facility_name:
                raise ValueError(f"Message before .FACILITY in {path}:{line_number}")
            if not severity_name:
                raise ValueError(f"Message before .SEVERITY in {path}:{line_number}")
            msg_number += 1
            message_name = msg_match.group(1).strip().upper()
            message_text = msg_match.group(2)
            parsed.append(
                MsgDefinition(
                    facility_name=facility_name,
                    facility_value=facility_value,
                    message_name=message_name,
                    message_value=msg_number,
                    severity_name=severity_name,
                    severity_value=SEVERITY_NAME_TO_VALUE[severity_name],
                    text=message_text,
                    source_file=str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    source_line=line_number,
                )
            )
            continue

        raise ValueError(f"Unknown line in {path}:{line_number}: {line}")

    if not title:
        raise ValueError(f"Missing .TITLE in {path}")
    if not ident:
        raise ValueError(f"Missing .IDENT in {path}")
    if not seen_end:
        raise ValueError(f"Missing .END in {path}")
    return parsed


def _normalize(defs: Iterable[MsgDefinition]) -> Tuple[Dict[str, int], Dict[str, Dict[str, int]], Dict[int, str], List[MsgDefinition]]:
    facilities: Dict[str, int] = {}
    messages: Dict[str, Dict[str, int]] = {}
    message_text: Dict[int, str] = {}
    sorted_defs = sorted(
        list(defs),
        key=lambda item: (
            item.facility_value,
            item.facility_name,
            item.severity_value,
            item.message_name,
        ),
    )
    for item in sorted_defs:
        existing_facility_value = facilities.get(item.facility_name)
        if existing_facility_value is not None and existing_facility_value != item.facility_value:
            raise ValueError(
                f"Facility collision {item.facility_name}: {existing_facility_value} vs {item.facility_value}"
            )
        facilities[item.facility_name] = item.facility_value
        facility_messages = messages.setdefault(item.facility_name, {})
        existing_message_value = facility_messages.get(item.message_name)
        if existing_message_value is not None and existing_message_value != item.message_value:
            raise ValueError(
                f"Message collision {item.facility_name}.{item.message_name}: {existing_message_value} vs {item.message_value}"
            )
        facility_messages[item.message_name] = item.message_value
        code = _encode_status(item.severity_value, item.facility_value, item.message_value)
        previous_text = message_text.get(code)
        if previous_text is not None and previous_text != item.text:
            raise ValueError(
                f"Code collision text mismatch {item.facility_name}.{item.message_name} 0x{code:08X}"
            )
        message_text[code] = item.text
    return facilities, messages, message_text, sorted_defs


def _build_source_hash(paths: Sequence[Path]) -> str:
    hasher = hashlib.sha256()
    for path in sorted(paths):
        hasher.update(str(path.relative_to(REPO_ROOT)).replace("\\", "/").encode(ENCODING_UTF8))
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _render_python_catalog(
    source_hash: str,
    facilities: Dict[str, int],
    messages: Dict[str, Dict[str, int]],
    definitions: Sequence[MsgDefinition],
) -> str:
    lines: List[str] = []
    lines.append(f'"""{GENERATED_NOTICE_TEXT}"""')
    lines.append("")
    lines.append(f"GENERATED_FROM_HASH = \"{source_hash}\"")
    lines.append("")
    lines.append("SEVERITIES = {")
    for value in sorted(SEVERITY_VALUE_TO_PY.keys()):
        lines.append(f"    \"{SEVERITY_VALUE_TO_PY[value]}\": {value},")
    lines.append("}")
    lines.append("")
    lines.append("FACILITIES = {")
    for name, value in sorted(facilities.items(), key=lambda item: (item[1], item[0])):
        lines.append(f"    \"{name}\": {value},")
    lines.append("}")
    lines.append("")
    lines.append("MESSAGES = {")
    for facility_name, mapping in sorted(messages.items(), key=lambda item: (facilities.get(item[0], 0), item[0])):
        lines.append(f"    \"{facility_name}\": {{")
        for message_name, message_value in sorted(mapping.items(), key=lambda item: item[1]):
            lines.append(f"        \"{message_name}\": {message_value},")
        lines.append("    },")
    lines.append("}")
    lines.append("")
    lines.append("STATUS_CODES = {")
    for item in sorted(definitions, key=lambda value: (value.facility_value, value.message_value, value.message_name)):
        symbol = f"SS__{item.facility_name}__{item.message_name}"
        code_value = _encode_status(item.severity_value, item.facility_value, item.message_value)
        lines.append(f"    \"{symbol}\": {code_value},")
    lines.append("}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_python_messages(source_hash: str, message_text: Dict[int, str]) -> str:
    lines: List[str] = []
    lines.append(f'"""{GENERATED_NOTICE_TEXT}"""')
    lines.append("")
    lines.append(f"GENERATED_FROM_HASH = \"{source_hash}\"")
    lines.append("")
    lines.append("MESSAGE_TABLE = {")
    for code, text in sorted(message_text.items()):
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f"    {code}: \"{escaped}\",")
    lines.append("}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_java_catalog(
    source_hash: str,
    facilities: Dict[str, int],
    messages: Dict[str, Dict[str, int]],
    definitions: Sequence[MsgDefinition],
) -> str:
    lines: List[str] = []
    lines.append("package frc.robot.status.generated;")
    lines.append("")
    lines.append("/** AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration. */")
    lines.append("public final class StatusCatalogGenerated {")
    lines.append("  public static final String GENERATED_FROM_HASH = \"%s\";" % source_hash)
    lines.append("")
    lines.append("  public static final class Severity {")
    for value in sorted(SEVERITY_VALUE_TO_PY.keys()):
        lines.append(f"    public static final int {SEVERITY_VALUE_TO_PY[value]} = {value};")
    lines.append("    private Severity() {}")
    lines.append("  }")
    lines.append("")
    lines.append("  public static final class Facility {")
    for name, value in sorted(facilities.items(), key=lambda item: (item[1], item[0])):
        lines.append(f"    public static final int {name} = {value};")
    lines.append("    private Facility() {}")
    lines.append("  }")
    lines.append("")
    lines.append("  public static final class Message {")
    for facility_name, mapping in sorted(messages.items(), key=lambda item: (facilities.get(item[0], 0), item[0])):
        lines.append(f"    public static final class {facility_name} {{")
        for message_name, message_value in sorted(mapping.items(), key=lambda item: item[1]):
            lines.append(f"      public static final int {message_name} = {message_value};")
        lines.append(f"      private {facility_name}() {{}}")
        lines.append("    }")
    lines.append("    private Message() {}")
    lines.append("  }")
    lines.append("")
    lines.append("  public static int encode(int severity, int facility, int message) {")
    lines.append("    return (facility << 16) | (message << 3) | severity;")
    lines.append("  }")
    lines.append("")
    for item in sorted(definitions, key=lambda value: (value.facility_value, value.message_value, value.message_name)):
            lines.append(
                "  public static final int SS__%s__%s = encode(Severity.%s, Facility.%s, Message.%s.%s);"
                % (
                    item.facility_name,
                    item.message_name,
                    SEVERITY_VALUE_TO_PY[item.severity_value],
                    item.facility_name,
                    item.facility_name,
                    item.message_name,
                )
            )
    lines.append("")
    lines.append("  private StatusCatalogGenerated() {}")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _render_java_messages(source_hash: str, message_text: Dict[int, str]) -> str:
    lines: List[str] = []
    lines.append("package frc.robot.status.generated;")
    lines.append("")
    lines.append("import java.util.HashMap;")
    lines.append("import java.util.Map;")
    lines.append("")
    lines.append("/** AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration. */")
    lines.append("public final class StatusMessagesGenerated {")
    lines.append("  public static final String GENERATED_FROM_HASH = \"%s\";" % source_hash)
    lines.append("  private static final Map<Integer, String> TABLE = new HashMap<>();")
    lines.append("")
    lines.append("  static {")
    for code, text in sorted(message_text.items()):
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f"    TABLE.put({code}, \"{escaped}\");")
    lines.append("  }")
    lines.append("")
    lines.append("  public static String getMessageTemplate(int code) {")
    lines.append("    return TABLE.get(code);")
    lines.append("  }")
    lines.append("")
    lines.append("  private StatusMessagesGenerated() {}")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _compose_catalog_payload(source_hash: str, files: Sequence[Path], facilities: Dict[str, int], messages: Dict[str, Dict[str, int]], message_text: Dict[int, str]) -> Dict[str, object]:
    sources = [str(path.relative_to(REPO_ROOT)).replace("\\", "/") for path in sorted(files)]
    return {
        KEY_VERSION: CATALOG_VERSION,
        KEY_GENERATED_FROM: "msg",
        KEY_GENERATED_NOTICE: GENERATED_NOTICE_TEXT,
        KEY_SOURCE_HASH: source_hash,
        KEY_SOURCES: sources,
        KEY_DATA: {
            KEY_SEVERITIES: {
                "SUCCESS": 0,
                "INFO": 1,
                "WARNING": 2,
                "ERROR": 3,
                "FATAL": 4,
            },
            KEY_FACILITIES: facilities,
            KEY_MESSAGES: messages,
            KEY_MESSAGE_TEXT: {str(code): text for code, text in sorted(message_text.items())},
        },
    }


def _write_or_check(path: Path, content: str, check: bool) -> bool:
    existing = path.read_text(encoding=ENCODING_UTF8) if path.exists() else None
    if check:
        return existing == content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=ENCODING_UTF8)
    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile .MSG status files to Python and Java artifacts.")
    parser.add_argument("--src", action="append", default=[DEFAULT_SRC_DIR], help="Source directory containing .MSG files.")
    parser.add_argument("--out-catalog", default=DEFAULT_OUT_CATALOG, help="Output compiled catalog JSON path.")
    parser.add_argument("--out-py", default=DEFAULT_OUT_PY_DIR, help="Output Python directory.")
    parser.add_argument("--out-java", default=DEFAULT_OUT_JAVA_DIR, help="Output Java directory.")
    parser.add_argument("--check", action="store_true", help="Check mode; fails if outputs are stale.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    src_dirs = [REPO_ROOT / item for item in args.src]
    files = _iter_msg_files(src_dirs)
    if not files:
        print("ERROR: no .MSG files found.")
        return EXIT_ERROR

    definitions: List[MsgDefinition] = []
    for path in files:
        definitions.extend(_parse_msg_file(path))
    facilities, messages, message_text, sorted_defs = _normalize(definitions)
    source_hash = _build_source_hash(files)

    catalog_payload = _compose_catalog_payload(source_hash, files, facilities, messages, message_text)
    catalog_content = json.dumps(catalog_payload, indent=2, sort_keys=True) + "\n"

    py_catalog_content = _render_python_catalog(source_hash, facilities, messages, sorted_defs)
    py_messages_content = _render_python_messages(source_hash, message_text)
    java_catalog_content = _render_java_catalog(source_hash, facilities, messages, sorted_defs)
    java_messages_content = _render_java_messages(source_hash, message_text)

    out_catalog = REPO_ROOT / args.out_catalog
    out_py_dir = REPO_ROOT / args.out_py
    out_java_dir = REPO_ROOT / args.out_java

    checks: List[bool] = []
    checks.append(_write_or_check(out_catalog, catalog_content, args.check))
    checks.append(_write_or_check(out_py_dir / FILE_PY_CATALOG, py_catalog_content, args.check))
    checks.append(_write_or_check(out_py_dir / FILE_PY_MESSAGES, py_messages_content, args.check))
    checks.append(_write_or_check(out_java_dir / FILE_JAVA_CATALOG, java_catalog_content, args.check))
    checks.append(_write_or_check(out_java_dir / FILE_JAVA_MESSAGES, java_messages_content, args.check))

    if args.check and not all(checks):
        print("ERROR: generated status artifacts are stale.")
        return EXIT_STALE
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
