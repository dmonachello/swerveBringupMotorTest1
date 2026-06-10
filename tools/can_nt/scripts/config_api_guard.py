from __future__ import annotations

"""
NAME
    config_api_guard.py - Enforce shared config API usage for bringup_system.json.

SYNOPSIS
    python tools/can_nt/scripts/config_api_guard.py

DESCRIPTION
    Scans Python source under tools/ and fails when code bypasses the shared
    config API for bringup_system.json access. The guard is intentionally
    narrow: it flags explicit path-helper bypasses and direct JSON I/O patterns
    that clearly target bringup_system.json.
"""

import ast
import argparse
import sys
import time
from pathlib import Path
from typing import Iterable, List, Sequence, Set


REPO_ROOT_DEPTH = 3
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
TOOLS_ROOT = REPO_ROOT / "tools"

EXIT_OK = 0
EXIT_FAILED = 1

MSG_PASS = "PASS: no shared-config-API violations detected."
MSG_FAIL = "FAIL: shared-config-API violations detected."
MSG_SCAN_FMT = "[scan {index}/{total}] {path}"
MSG_SCAN_DONE_FMT = "[done] scanned={count} violations={violations} elapsed={elapsed:.2f}s"

PATH_ALLOWED_HELPER_FILES = {
    "tools/common/paths.py",
    "tools/common/config_lifecycle/service.py",
}
PATH_ALLOWED_PREFIXES = (
    "tools/common/config_api/",
    "tools/can_topology/legacy/",
)
PATH_IGNORED_PREFIXES = (
    "tools/can_nt/tests/",
    "tools/common/tests/",
    "tools/can_topology/tests/",
    "tools/can_nt/generated/",
)
PATH_IGNORED_PARTS = {
    "__pycache__",
}

HELPER_NAMES = {
    "profiles_canonical_path",
    "profiles_deploy_path",
    "legacy_profiles_canonical_path",
    "legacy_profiles_deploy_path",
}
DIRECT_IO_NAMES = {
    "read_json",
    "write_json",
}
LITERAL_BRINGUP_NAME = "bringup_system.json"


def python_source_paths(root: Path = TOOLS_ROOT) -> List[Path]:
    """
    NAME
        python_source_paths - Return Python sources that should be scanned.
    """
    paths: List[Path] = []
    for path in root.rglob("*.py"):
        normalized = _normalize_path(path)
        if _is_ignored_path(normalized):
            continue
        paths.append(path)
    return sorted(paths)


def scan_path(path: Path) -> List[str]:
    """
    NAME
        scan_path - Return config API guard violations for one file.
    """
    source = path.read_text(encoding="utf-8-sig")
    return scan_text(source, _normalize_path(path))


def scan_text(source: str, normalized_path: str) -> List[str]:
    """
    NAME
        scan_text - Return config API guard violations for one source text blob.
    """
    try:
        tree = ast.parse(source, filename=normalized_path)
    except SyntaxError as exc:
        return [f"{normalized_path}: syntax-error: {exc.msg}"]
    tainted_names = _tainted_names(tree, source)
    violations: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node)
        if call_name in HELPER_NAMES and not _path_helper_allowed(normalized_path):
            violations.append(
                f"{normalized_path}:{node.lineno}: direct path helper '{call_name}' is not allowed here"
            )
            continue
        if call_name in DIRECT_IO_NAMES and _is_forbidden_direct_io_call(node, source, tainted_names):
            violations.append(
                f"{normalized_path}:{node.lineno}: direct {call_name}(...) targeting bringup_system.json bypasses ConfigRepository"
            )
    return sorted(violations)


def main(argv: Sequence[str] | None = None) -> int:
    """
    NAME
        main - Entrypoint for config API guard enforcement.
    """

    args = _parse_args(argv)
    verbose = bool(args.verbose)
    violations: List[str] = []
    paths = python_source_paths()
    started_at = time.perf_counter()
    total = len(paths)
    for index, path in enumerate(paths, start=1):
        if verbose:
            print(MSG_SCAN_FMT.format(index=index, total=total, path=_normalize_path(path)))
        violations.extend(scan_path(path))
    if verbose:
        elapsed = time.perf_counter() - started_at
        print(MSG_SCAN_DONE_FMT.format(count=total, violations=len(violations), elapsed=elapsed))
    if not violations:
        print(MSG_PASS)
        return EXIT_OK
    print(MSG_FAIL)
    for violation in violations:
        print(f"  - {violation}")
    return EXIT_FAILED


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    NAME
        _parse_args - Parse config API guard command-line flags.
    """

    parser = argparse.ArgumentParser(
        description="Scan tools/ for bringup_system.json shared-config-API bypasses."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-file scan progress and elapsed summary.",
    )
    return parser.parse_args(argv)


def _normalize_path(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def _is_ignored_path(normalized_path: str) -> bool:
    if any(part in PATH_IGNORED_PARTS for part in normalized_path.split("/")):
        return True
    return normalized_path.startswith(PATH_IGNORED_PREFIXES)


def _path_helper_allowed(normalized_path: str) -> bool:
    return normalized_path in PATH_ALLOWED_HELPER_FILES or normalized_path.startswith(PATH_ALLOWED_PREFIXES)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _tainted_names(tree: ast.AST, source: str) -> Set[str]:
    names: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            target_name = node.targets[0].id
            if target_name in names:
                continue
            if _expr_mentions_bringup_system(node.value, source, names):
                names.add(target_name)
                changed = True
    return names


def _is_forbidden_direct_io_call(node: ast.Call, source: str, tainted_names: Set[str]) -> bool:
    first_arg = node.args[0] if node.args else None
    if first_arg is None:
        return False
    return _expr_mentions_bringup_system(first_arg, source, tainted_names)


def _expr_mentions_bringup_system(node: ast.AST, source: str, tainted_names: Set[str]) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return LITERAL_BRINGUP_NAME in node.value
    if isinstance(node, ast.Name):
        return node.id in tainted_names
    if isinstance(node, ast.Call):
        call_name = _call_name(node)
        if call_name in HELPER_NAMES:
            return True
    segment = ast.get_source_segment(source, node) or ""
    if LITERAL_BRINGUP_NAME in segment:
        return True
    return any(helper_name in segment for helper_name in HELPER_NAMES)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
