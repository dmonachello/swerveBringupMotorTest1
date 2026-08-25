from __future__ import annotations

"""
NAME
    changelog_guard.py - Enforce or auto-seed changelog updates for major user-visible changes.

SYNOPSIS
    python tools/can_nt/scripts/changelog_guard.py
    python tools/can_nt/scripts/changelog_guard.py --check-only

DESCRIPTION
    Inspects the current git worktree for changes in major product surfaces and
    auto-updates CHANGELOG.md by default when those changes are present without
    a matching changelog edit. In strict mode, it fails instead.
"""

import argparse
from datetime import date
from pathlib import Path
import subprocess
import sys
from typing import Iterable, List, Optional, Sequence, Set

REPO_ROOT_DEPTH = 3
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

GIT_CMD = "git"
GIT_DIFF_ARGS = ("diff", "--name-only", "HEAD")
GIT_UNTRACKED_ARGS = ("ls-files", "--others", "--exclude-standard")

PATH_CHANGELOG = "CHANGELOG.md"
ARG_CHECK_ONLY = "--check-only"
HELP_CHECK_ONLY = "Do not modify CHANGELOG.md; fail if major changes are present without a changelog edit."

CHANGELOG_HEADER = "# Changelog"
CHANGELOG_INTRO = "All notable user-facing changes are documented in this file."
SECTION_PREFIX = "## "
AUTO_SECTION_KIND = "Changed"
AUTO_SEED_BULLET = "- Auto-generated changelog seed for current worktree changes in guarded major surfaces."
AUTO_FILE_BULLET_TEMPLATE = "- Touched major-change file: `{path}`"
TEXT_ENCODING_UTF8 = "utf-8"
NEWLINE_CRLF = "\r\n"
NEWLINE_LF = "\n"

MAJOR_PREFIX_JAVA_RUNTIME = "src/main/java/"
MAJOR_PREFIX_CLI = "tools/can_nt/"
MAJOR_PREFIX_DSL = "tools/common/robot_test_dsl/"
MAJOR_PREFIX_TOPOLOGY = "tools/can_topology/"
MAJOR_PREFIX_DEPLOY = "src/main/deploy/"
MAJOR_PREFIX_EXAMPLES = "docs/examples/"

IGNORE_PREFIX_TESTS = "tests/"
IGNORE_PREFIX_LOCAL_DATA = "data/"
IGNORE_PREFIX_PI = ".pi/"
IGNORE_PREFIX_CODEX = ".codex/"

MSG_NO_MAJOR = "PASS: no major changelog-relevant changes detected."
MSG_CHANGELOG_PRESENT = "PASS: major changes detected and CHANGELOG.md is updated."
MSG_CHANGELOG_AUTOSEEDED = "PASS: major changes detected and CHANGELOG.md was auto-updated."
MSG_CHANGELOG_REQUIRED = "FAIL: major changes detected but CHANGELOG.md is unchanged."
MSG_GIT_FAILED = "ERROR: failed to inspect git worktree."
MSG_CHANGELOG_WRITE_FAILED = "ERROR: failed to auto-update CHANGELOG.md."
MSG_MAJOR_HEADER = "Major-change files:"
MSG_AUTOWRITE_PATH = "CHANGELOG_PATH"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    NAME
        parse_args - Parse command-line arguments for changelog enforcement.
    """
    parser = argparse.ArgumentParser(description="Enforce or auto-seed changelog updates for major changes.")
    parser.add_argument(ARG_CHECK_ONLY, action="store_true", help=HELP_CHECK_ONLY)
    return parser.parse_args(argv)


def git_changed_paths() -> List[str]:
    """
    NAME
        git_changed_paths - Return changed and untracked paths in the worktree.
    """
    diff_paths = _git_lines(GIT_DIFF_ARGS)
    untracked_paths = _git_lines(GIT_UNTRACKED_ARGS)
    combined: Set[str] = set(diff_paths)
    combined.update(untracked_paths)
    return sorted(path for path in combined if path)


def major_change_paths(paths: Iterable[str]) -> List[str]:
    """
    NAME
        major_change_paths - Filter worktree paths to changelog-relevant surfaces.
    """
    matches: List[str] = []
    for path in paths:
        normalized = str(path).replace("\\", "/")
        if normalized == PATH_CHANGELOG:
            continue
        if _is_ignored_path(normalized):
            continue
        if _is_major_surface(normalized):
            matches.append(normalized)
    return sorted(matches)


def changelog_is_changed(paths: Iterable[str]) -> bool:
    """
    NAME
        changelog_is_changed - Return whether CHANGELOG.md is part of the worktree delta.
    """
    return any(str(path).replace("\\", "/") == PATH_CHANGELOG for path in paths)


def main(argv: Sequence[str] | None = None) -> int:
    """
    NAME
        main - Entrypoint for changelog guard enforcement.
    """
    args = parse_args(argv)
    try:
        changed = git_changed_paths()
    except RuntimeError as exc:
        print(f"{MSG_GIT_FAILED} {exc}")
        return EXIT_USAGE
    major_paths = major_change_paths(changed)
    if not major_paths:
        print(MSG_NO_MAJOR)
        return EXIT_OK
    if changelog_is_changed(changed):
        print(MSG_CHANGELOG_PRESENT)
        _print_major_paths(major_paths)
        return EXIT_OK
    if bool(args.check_only):
        print(MSG_CHANGELOG_REQUIRED)
        _print_major_paths(major_paths)
        return EXIT_FAILED
    try:
        written_path = write_auto_changelog_entry(major_paths)
    except OSError as exc:
        print(f"{MSG_CHANGELOG_WRITE_FAILED} {exc}")
        _print_major_paths(major_paths)
        return EXIT_FAILED
    print(MSG_CHANGELOG_AUTOSEEDED)
    print(f"{MSG_AUTOWRITE_PATH}: {written_path}")
    _print_major_paths(major_paths)
    return EXIT_OK


def write_auto_changelog_entry(
    major_paths: Sequence[str],
    changelog_path: Optional[Path] = None,
    date_text: Optional[str] = None,
) -> Path:
    """
    NAME
        write_auto_changelog_entry - Insert a dated auto-generated changelog seed.
    """
    target_path = changelog_path if changelog_path is not None else REPO_ROOT / PATH_CHANGELOG
    effective_date = date_text if date_text is not None else today_iso()
    existing_text = target_path.read_text(encoding=TEXT_ENCODING_UTF8) if target_path.exists() else str()
    newline = detect_newline(existing_text)
    entry_text = build_auto_entry_text(date_text=effective_date, major_paths=major_paths, newline=newline)
    updated_text = insert_latest_entry(existing_text=existing_text, entry_text=entry_text, newline=newline)
    target_path.write_text(updated_text, encoding=TEXT_ENCODING_UTF8)
    return target_path


def today_iso() -> str:
    """
    NAME
        today_iso - Return today's local date in ISO format.
    """
    return date.today().isoformat()


def detect_newline(text: str) -> str:
    """
    NAME
        detect_newline - Preserve CRLF when present, otherwise use LF.
    """
    return NEWLINE_CRLF if NEWLINE_CRLF in text else NEWLINE_LF


def build_auto_entry_text(date_text: str, major_paths: Sequence[str], newline: str) -> str:
    """
    NAME
        build_auto_entry_text - Build a changelog section for the current worktree.
    """
    lines: List[str] = [
        f"{SECTION_PREFIX}{date_text}",
        str(),
        f"### {AUTO_SECTION_KIND} - {date_text}",
        str(),
        AUTO_SEED_BULLET,
    ]
    for path in major_paths:
        lines.append(AUTO_FILE_BULLET_TEMPLATE.format(path=path))
    lines.append(str())
    return newline.join(lines) + newline


def insert_latest_entry(existing_text: str, entry_text: str, newline: str) -> str:
    """
    NAME
        insert_latest_entry - Insert a new latest changelog section near the top.
    """
    if not existing_text.strip():
        preamble_lines = [CHANGELOG_HEADER, str(), CHANGELOG_INTRO, str()]
        return newline.join(preamble_lines) + newline + entry_text

    first_section_marker = f"{newline}{SECTION_PREFIX}"
    marker_index = existing_text.find(first_section_marker)
    if marker_index == -1:
        normalized = ensure_double_trailing_newline(existing_text, newline)
        return normalized + entry_text
    insert_index = marker_index + len(newline)
    return existing_text[:insert_index] + entry_text + existing_text[insert_index:]


def ensure_double_trailing_newline(text: str, newline: str) -> str:
    """
    NAME
        ensure_double_trailing_newline - Normalize trailing blank space before append.
    """
    if text.endswith(newline + newline):
        return text
    if text.endswith(newline):
        return text + newline
    return text + newline + newline


def _git_lines(args: Sequence[str]) -> List[str]:
    completed = subprocess.run(
        (GIT_CMD, *args),
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != EXIT_OK:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    lines = [line.strip() for line in completed.stdout.splitlines()]
    return [line for line in lines if line]


def _is_ignored_path(path: str) -> bool:
    return (
        path.startswith(IGNORE_PREFIX_TESTS)
        or path.startswith(IGNORE_PREFIX_LOCAL_DATA)
        or path.startswith(IGNORE_PREFIX_PI)
        or path.startswith(IGNORE_PREFIX_CODEX)
    )


def _is_major_surface(path: str) -> bool:
    return (
        path.startswith(MAJOR_PREFIX_JAVA_RUNTIME)
        or path.startswith(MAJOR_PREFIX_CLI)
        or path.startswith(MAJOR_PREFIX_DSL)
        or path.startswith(MAJOR_PREFIX_TOPOLOGY)
        or path.startswith(MAJOR_PREFIX_DEPLOY)
        or path.startswith(MAJOR_PREFIX_EXAMPLES)
    )


def _print_major_paths(paths: Sequence[str]) -> None:
    print(MSG_MAJOR_HEADER)
    for path in paths:
        print(f"  - {path}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
