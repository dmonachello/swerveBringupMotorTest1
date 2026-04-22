"""
NAME
    inventory_status_surfaces.py - Inventory status/error message surfaces across Python and Java.

SYNOPSIS
    python tools/status_codes/inventory_status_surfaces.py

DESCRIPTION
    Scans repository source files and emits a structured inventory separating:
    - canonical Python status-coded definitions
    - unstructured Python message string candidates
    - unstructured Java message/status string candidates

    Output files:
    - tools/status_codes/reports/status_surface_inventory.json
    - docs/STATUS_SURFACE_INVENTORY.md
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

REPO_ROOT_DEPTH = 2
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]

DIR_TOOLS = "tools"
DIR_SRC = "src"
DIR_MAIN = "main"
DIR_JAVA = "java"
DIR_DOCS = "docs"
DIR_STATUS_CODES = "status_codes"
DIR_REPORTS = "reports"

EXT_PY = ".py"
EXT_JAVA = ".java"

FILE_OUTPUT_JSON = "status_surface_inventory.json"
FILE_OUTPUT_MD = "STATUS_SURFACE_INVENTORY.md"

TEXT_ENCODING = "utf-8"

REGEX_STATUS_MESSAGES_START = re.compile(r"^\s*STATUS_MESSAGES\s*=\s*\{\s*$")
REGEX_STATUS_MESSAGE_ENTRY = re.compile(
    r'^\s*(SS__[A-Z0-9_]+)\s*:\s*[\"\'](.+?)[\"\']\s*,?\s*$'
)

STATUS_KEYWORD_PATTERN = (
    r"\bERROR\b|\bWARNING\b|\bSUCCESS\b|\bFAIL\b|\bFAILED\b|\bINVALID\b|"
    r"\bNOT\s+FOUND\b|\bMISSING\b|\bREQUIRED\b|\bUNKNOWN\b|\bREJECTED\b|"
    r"\bABORTED\b|\bCANNOT\b|\bUNABLE\b|\bDENIED\b|\bTIMEOUT\b|\bOK\b"
)
REGEX_STATUS_LITERAL = re.compile(STATUS_KEYWORD_PATTERN, re.IGNORECASE)
REGEX_JAVA_ACK_STATUS_LITERAL = re.compile(r'"ack/status"\)\.setString\(ok\s*\?\s*"ok"\s*:\s*"error"\)')
REGEX_JSON_STATUS_LITERAL = re.compile(r'"status"\s*,\s*result\.ok\s*\?\s*"ok"\s*:\s*"error"')

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "build",
    "bin",
    ".gradle",
}

MARKDOWN_HEADER = "# Status Surface Inventory\n"
GENERATED_NOTICE_TEXT = "AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration."


@dataclass
class Hit:
    path: str
    line: int
    text: str


def _iter_source_files(base: Path, suffix: str) -> Iterable[Path]:
    for path in base.rglob(f"*{suffix}"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.is_file():
            yield path


def _read_lines(path: Path) -> List[str]:
    return path.read_text(encoding=TEXT_ENCODING, errors="replace").splitlines()


def _canonical_status_hits() -> List[Hit]:
    hits: List[Hit] = []
    status_dir = REPO_ROOT / DIR_TOOLS / "can_nt" / "status"
    for path in _iter_source_files(status_dir, EXT_PY):
        lines = _read_lines(path)
        in_block = False
        for idx, line in enumerate(lines, start=1):
            if REGEX_STATUS_MESSAGES_START.search(line):
                in_block = True
                continue
            if in_block and line.strip().startswith("}"):
                in_block = False
                continue
            if in_block:
                match = REGEX_STATUS_MESSAGE_ENTRY.search(line)
                if match:
                    symbol = match.group(1)
                    text = match.group(2)
                    hits.append(Hit(path=str(path.relative_to(REPO_ROOT)), line=idx, text=f"{symbol}: {text}"))
    return hits


def _unstructured_python_hits() -> List[Hit]:
    hits: List[Hit] = []
    python_roots = [REPO_ROOT / DIR_TOOLS]
    for root in python_roots:
        for path in _iter_source_files(root, EXT_PY):
            relative = str(path.relative_to(REPO_ROOT))
            if relative.startswith("tools/can_nt/status/"):
                continue
            lines = _read_lines(path)
            for idx, line in enumerate(lines, start=1):
                if REGEX_STATUS_LITERAL.search(line):
                    hits.append(Hit(path=relative, line=idx, text=line.strip()))
    return hits


def _unstructured_java_hits() -> Dict[str, List[Hit]]:
    java_root = REPO_ROOT / DIR_SRC / DIR_MAIN / DIR_JAVA
    text_hits: List[Hit] = []
    ack_hits: List[Hit] = []
    for path in _iter_source_files(java_root, EXT_JAVA):
        relative = str(path.relative_to(REPO_ROOT))
        lines = _read_lines(path)
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if REGEX_STATUS_LITERAL.search(stripped):
                text_hits.append(Hit(path=relative, line=idx, text=stripped))
            if REGEX_JAVA_ACK_STATUS_LITERAL.search(stripped) or REGEX_JSON_STATUS_LITERAL.search(stripped):
                ack_hits.append(Hit(path=relative, line=idx, text=stripped))
    return {
        "text_literals": text_hits,
        "ack_status_literals": ack_hits,
    }


def _hit_to_dict(hit: Hit) -> Dict[str, object]:
    return {
        "path": hit.path,
        "line": hit.line,
        "text": hit.text,
    }


def _render_markdown(payload: Dict[str, object]) -> str:
    canonical_hits = payload["canonical_python_status_messages"]
    py_hits = payload["unstructured_python_candidates"]
    java_text_hits = payload["unstructured_java_candidates"]["text_literals"]
    java_ack_hits = payload["unstructured_java_candidates"]["ack_status_literals"]

    lines: List[str] = [
        MARKDOWN_HEADER.strip(),
        "",
        f"> {GENERATED_NOTICE_TEXT}",
        "",
        "## Purpose",
        "",
        "Inventory canonical status-coded definitions and unstructured status/error string surfaces across Python and Java.",
        "",
        "## Summary",
        "",
        f"- Generated At (UTC): `{payload['generated_at_utc']}`",
        f"- Canonical Python status message entries: `{len(canonical_hits)}`",
        f"- Unstructured Python candidates: `{len(py_hits)}`",
        f"- Unstructured Java text candidates: `{len(java_text_hits)}`",
        f"- Java ack/status literal candidates: `{len(java_ack_hits)}`",
        "",
        "## Top Canonical Python Entries",
        "",
    ]
    for item in canonical_hits[:20]:
        lines.append(f"- `{item['path']}:{item['line']}` {item['text']}")

    lines.extend(
        [
            "",
            "## Top Unstructured Python Candidates",
            "",
        ]
    )
    for item in py_hits[:20]:
        lines.append(f"- `{item['path']}:{item['line']}` {item['text']}")

    lines.extend(
        [
            "",
            "## Top Unstructured Java Candidates",
            "",
        ]
    )
    for item in java_text_hits[:20]:
        lines.append(f"- `{item['path']}:{item['line']}` {item['text']}")

    lines.extend(
        [
            "",
            "## Java ACK Status Literal Candidates",
            "",
        ]
    )
    for item in java_ack_hits[:20]:
        lines.append(f"- `{item['path']}:{item['line']}` {item['text']}")

    lines.extend(
        [
            "",
            "## Output Artifacts",
            "",
            "- `tools/status_codes/reports/status_surface_inventory.json`",
            "- `docs/STATUS_SURFACE_INVENTORY.md`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()
    canonical_hits = _canonical_status_hits()
    py_hits = _unstructured_python_hits()
    java_hits = _unstructured_java_hits()

    payload = {
        "generated_at_utc": generated_at,
        "generated_notice": GENERATED_NOTICE_TEXT,
        "canonical_python_status_messages": [_hit_to_dict(item) for item in canonical_hits],
        "unstructured_python_candidates": [_hit_to_dict(item) for item in py_hits],
        "unstructured_java_candidates": {
            "text_literals": [_hit_to_dict(item) for item in java_hits["text_literals"]],
            "ack_status_literals": [_hit_to_dict(item) for item in java_hits["ack_status_literals"]],
        },
    }

    reports_dir = REPO_ROOT / DIR_TOOLS / DIR_STATUS_CODES / DIR_REPORTS
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / FILE_OUTPUT_JSON
    json_path.write_text(json.dumps(payload, indent=2), encoding=TEXT_ENCODING)

    md_path = REPO_ROOT / DIR_DOCS / FILE_OUTPUT_MD
    md_path.write_text(_render_markdown(payload) + "\n", encoding=TEXT_ENCODING)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
