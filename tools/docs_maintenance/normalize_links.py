from __future__ import annotations

"""
NAME
    normalize_links.py - Convert machine-local Markdown links to repository-relative links.

SYNOPSIS
    python -m tools.docs_maintenance.normalize_links [--apply]

DESCRIPTION
    Scans maintained Markdown outside notes and historical documentation. A link
    is eligible only when its absolute target maps to an existing path in the
    current repository. Dry-run is the default. Apply mode refuses to write when
    any machine-local target cannot be resolved.
"""

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
from typing import Iterable
from urllib.parse import quote, unquote

from .inventory import iter_markdown_paths


ARG_APPLY = "--apply"
ARG_ACTION_STORE_TRUE = "store_true"
ANCHOR_MARKER = "#"
DEFAULT_APPLY_CHANGES = False
DESCRIPTION = "Normalize resolvable machine-local Markdown links."
ENCODING_UTF8 = "utf-8"
EMPTY_TEXT = ""
EXIT_OK = 0
EXIT_UNRESOLVED = 2
FIRST_LINE_NUMBER = 1
GROUP_PREFIX = "prefix"
GROUP_SUFFIX = "suffix"
GROUP_TARGET = "target"
INDEX_NOT_FOUND = 0
JSON_INDENT = 2
KEY_APPLIED = "applied"
KEY_CHANGES = "changes"
KEY_UNRESOLVED = "unresolved"
MARKDOWN_LINK_PATTERN = re.compile(r"(?P<prefix>\[[^\]]+\]\()(?P<target>[^)]+)(?P<suffix>\))")
MACHINE_TARGET_PATTERN = re.compile(r"(?i)^(?:/abs/path/)?/?[a-z]:/|^/abs/path/")
LINE_SUFFIX_PATTERN = re.compile(r":(?P<line>[0-9]+)$")
REPOSITORY_PATH_MARKERS = (
    "/.codex/",
    "/docs/",
    "/notes/",
    "/src/",
    "/tests/",
    "/tools/",
)
ROOT_FILE_MARKERS = (
    "/AGENTS.md",
    "/CHANGELOG.md",
    "/README.md",
    "/build.gradle",
    "/gradlew.bat",
)
SKIP_PATH_PARTS = {"historical", "notes"}
SPACE_SAFE_URL_CHARS = "/._-"
BACKSLASH = "\\"
FORWARD_SLASH = "/"
NEWLINE = "\n"


@dataclass(frozen=True)
class LinkChange:
    """Describe one safe machine-local link replacement."""

    source_repo_path: str
    line: int
    old_target: str
    new_target: str
    target_repo_path: str


@dataclass(frozen=True)
class UnresolvedLink:
    """Describe one machine-local link that does not map to a current path."""

    source_repo_path: str
    line: int
    old_target: str


@dataclass(frozen=True)
class NormalizationReport:
    """Collect planned changes and unresolved machine-local targets."""

    applied: bool
    changes: tuple[LinkChange, ...]
    unresolved: tuple[UnresolvedLink, ...]


def _split_target_suffix(raw_target: str) -> tuple[str, str]:
    """Separate a Markdown path from an optional anchor or renderer line suffix."""
    decoded = unquote(raw_target)
    anchor_index = decoded.find(ANCHOR_MARKER)
    anchor = decoded[anchor_index:] if anchor_index >= INDEX_NOT_FOUND else EMPTY_TEXT
    path_text = decoded[:anchor_index] if anchor_index >= INDEX_NOT_FOUND else decoded
    line_match = LINE_SUFFIX_PATTERN.search(path_text)
    if line_match is None:
        return path_text, anchor
    return path_text[:line_match.start()], path_text[line_match.start():] + anchor


def _candidate_repo_path(raw_target: str) -> tuple[str | None, str]:
    """Extract a repository-relative candidate and preserve any target suffix."""
    path_text, suffix = _split_target_suffix(raw_target)
    normalized = path_text.replace(BACKSLASH, FORWARD_SLASH)
    lowered = normalized.lower()
    candidates: list[tuple[int, str]] = []
    for marker in REPOSITORY_PATH_MARKERS:
        index = lowered.find(marker.lower())
        if index >= INDEX_NOT_FOUND:
            candidates.append((index, normalized[index + FIRST_LINE_NUMBER:]))
    for marker in ROOT_FILE_MARKERS:
        index = lowered.find(marker.lower())
        if index >= INDEX_NOT_FOUND:
            candidates.append((index, normalized[index + FIRST_LINE_NUMBER:]))
    if not candidates:
        return None, suffix
    _, candidate = min(candidates, key=lambda item: item[0])
    return candidate, suffix


def _normalized_target(source: Path, root: Path, raw_target: str) -> tuple[str, str] | None:
    """Return the relative Markdown target only when the repository path exists."""
    candidate, suffix = _candidate_repo_path(raw_target)
    if candidate is None:
        return None
    target_path = root / candidate
    if not target_path.exists():
        return None
    relative = os.path.relpath(target_path, start=source.parent).replace(BACKSLASH, FORWARD_SLASH)
    encoded = quote(relative, safe=SPACE_SAFE_URL_CHARS)
    return encoded + suffix, Path(candidate).as_posix()


def _maintained_paths(root: Path) -> Iterable[Path]:
    """Yield active Markdown paths eligible for normalization."""
    for path in iter_markdown_paths(root):
        relative_parts = {part.lower() for part in path.relative_to(root).parts}
        if relative_parts.intersection(SKIP_PATH_PARTS):
            continue
        yield path


def normalize_machine_local_links(
    root: Path,
    apply_changes: bool = DEFAULT_APPLY_CHANGES,
) -> NormalizationReport:
    """
    NAME
        normalize_machine_local_links - Plan or apply safe Markdown link replacements.

    RETURNS
        A report containing every replacement and unresolved absolute target.

    SIDE EFFECTS
        Writes changed Markdown files only when apply_changes is true.
    """
    changes: list[LinkChange] = []
    unresolved: list[UnresolvedLink] = []
    for source in _maintained_paths(root):
        original = source.read_text(encoding=ENCODING_UTF8)
        source_repo_path = source.relative_to(root).as_posix()

        def replace(match: re.Match[str]) -> str:
            raw_target = match.group(GROUP_TARGET)
            normalized_raw_target = raw_target.replace(BACKSLASH, FORWARD_SLASH)
            if MACHINE_TARGET_PATTERN.search(normalized_raw_target) is None:
                return match.group(0)
            line = original.count(NEWLINE, INDEX_NOT_FOUND, match.start()) + FIRST_LINE_NUMBER
            normalized = _normalized_target(source, root, raw_target)
            if normalized is None:
                unresolved.append(UnresolvedLink(source_repo_path, line, raw_target))
                return match.group(0)
            new_target, target_repo_path = normalized
            changes.append(
                LinkChange(source_repo_path, line, raw_target, new_target, target_repo_path)
            )
            return match.group(GROUP_PREFIX) + new_target + match.group(GROUP_SUFFIX)

        updated = MARKDOWN_LINK_PATTERN.sub(replace, original)
        if apply_changes and updated != original:
            source.write_text(updated, encoding=ENCODING_UTF8)
    return NormalizationReport(apply_changes, tuple(changes), tuple(unresolved))


def _report_payload(report: NormalizationReport) -> dict[str, object]:
    """Convert a normalization report into JSON-safe output."""
    return {
        KEY_APPLIED: report.applied,
        KEY_CHANGES: [asdict(change) for change in report.changes],
        KEY_UNRESOLVED: [asdict(link) for link in report.unresolved],
    }


def main() -> int:
    """Run the dry-run or guarded apply command from the repository root."""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(ARG_APPLY, action=ARG_ACTION_STORE_TRUE)
    args = parser.parse_args()
    root = Path.cwd()
    dry_report = normalize_machine_local_links(root, apply_changes=DEFAULT_APPLY_CHANGES)
    apply_requested = bool(getattr(args, ARG_APPLY.lstrip("-").replace("-", "_")))
    if apply_requested and dry_report.unresolved:
        print(json.dumps(_report_payload(dry_report), indent=JSON_INDENT))
        return EXIT_UNRESOLVED
    report = normalize_machine_local_links(root, apply_changes=apply_requested)
    print(json.dumps(_report_payload(report), indent=JSON_INDENT))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
