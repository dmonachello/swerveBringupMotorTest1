from __future__ import annotations

"""
NAME
    changelog_guard.py - Enforce changelog updates for major user-visible changes.

SYNOPSIS
    python tools/can_nt/scripts/changelog_guard.py

DESCRIPTION
    Inspects the current git worktree for changes in major product surfaces and
    fails when those changes are present without a matching CHANGELOG.md edit.
"""

from pathlib import Path
import subprocess
import sys
from typing import Iterable, List, Sequence, Set

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
MSG_CHANGELOG_REQUIRED = "FAIL: major changes detected but CHANGELOG.md is unchanged."
MSG_GIT_FAILED = "ERROR: failed to inspect git worktree."
MSG_MAJOR_HEADER = "Major-change files:"


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
    _ = argv
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
    print(MSG_CHANGELOG_REQUIRED)
    _print_major_paths(major_paths)
    return EXIT_FAILED


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
