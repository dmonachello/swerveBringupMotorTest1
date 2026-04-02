"""
NAME
    bump_version.py - Repo-level version helper.

SYNOPSIS
    bump show <app|all>
    bump bump <app|all> <major|minor|patch> [--dry-run]
    bump set <app|all> <X.Y.Z> [--dry-run]
    bump field-set <app|all> <major|minor|patch> <value> [--dry-run]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.update_versions as update_versions

USAGE = (
    "Usage:\n"
    "  bump show <app|all>\n"
    "  bump bump <app|all> <major|minor|patch> [--dry-run]\n"
    "  bump set <app|all> <X.Y.Z> [--dry-run]\n"
    "  bump field-set <app|all> <major|minor|patch> <value> [--dry-run]\n"
    "\n"
    "Apps:\n"
    "  can_nt_bridge\n"
    "  bridge_cli\n"
    "  bringup_ui\n"
    "  can_topology_editor\n"
    "  robot_bringup\n"
    "  all\n"
    "\n"
    "Examples:\n"
    "  bump show bridge_cli\n"
    "  bump bump bridge_cli minor\n"
    "  bump bump all patch --dry-run\n"
    "  bump set bridge_cli 0.4.1\n"
    "  bump field-set bridge_cli patch 7\n"
)

CMD_SHOW = "show"
CMD_BUMP = "bump"
CMD_SET = "set"
CMD_FIELD_SET = "field-set"
CMD_HELP = "help"
FLAG_DRY_RUN = "--dry-run"

FIELD_MAJOR = "major"
FIELD_MINOR = "minor"
FIELD_PATCH = "patch"


def _print_error(message: str) -> int:
    print(f"ERROR: {message}")
    return 2


def _is_help(args: List[str]) -> bool:
    return not args or args[0] in (CMD_HELP, "-h", "--help")


def _parse_dry_run(args: List[str]) -> Tuple[List[str], bool]:
    if FLAG_DRY_RUN in args:
        filtered = [arg for arg in args if arg != FLAG_DRY_RUN]
        return filtered, True
    return args, False


def _resolve_apps(target: str) -> List[str]:
    if target == update_versions.ARG_ALL:
        return list(update_versions.CANONICAL_APP_ORDER)
    if target not in update_versions.APP_KEYS:
        raise ValueError(f"unknown app '{target}'")
    return [target]


def _format_transition(prefix: str, app: str, old: str, new: str) -> str:
    return f"{prefix} {app}: {old} -> {new}"


def _cmd_show(app: str) -> int:
    try:
        apps = _resolve_apps(app)
    except ValueError as exc:
        return _print_error(str(exc))
    versions = update_versions.get_current_versions()
    for name in apps:
        print(f"{name}: {versions.get(name, '0.0.0')}")
    return 0


def _cmd_set(app: str, version: str, dry_run: bool) -> int:
    try:
        update_versions.parse_version(version)
    except Exception:
        return _print_error(f"invalid semantic version '{version}'")
    try:
        apps = _resolve_apps(app)
    except ValueError as exc:
        return _print_error(str(exc))
    current = update_versions.get_current_versions()
    updates: Dict[str, str] = {name: version for name in apps}
    for name in apps:
        print(_format_transition("DRY-RUN" if dry_run else "APPLY", name, current[name], version))
    if dry_run:
        return 0
    try:
        update_versions.write_versions(updates)
    except Exception:
        return 1
    return 0


def _cmd_bump(app: str, field: str, dry_run: bool) -> int:
    if field not in update_versions.VERSION_BUMPS:
        return _print_error(f"invalid version field '{field}'")
    try:
        apps = _resolve_apps(app)
    except ValueError as exc:
        return _print_error(str(exc))
    current = update_versions.get_current_versions()
    updates: Dict[str, str] = {}
    for name in apps:
        parts = update_versions.parse_version(current[name])
        bumped = update_versions.bump_version(parts, field)
        updates[name] = update_versions.format_version(bumped)
        print(_format_transition("DRY-RUN" if dry_run else "APPLY", name, current[name], updates[name]))
    if dry_run:
        return 0
    try:
        update_versions.write_versions(updates)
    except Exception:
        return 1
    return 0


def _cmd_field_set(app: str, field: str, value: str, dry_run: bool) -> int:
    if field not in update_versions.VERSION_BUMPS:
        return _print_error(f"invalid version field '{field}'")
    try:
        num = int(value)
    except Exception:
        return _print_error("invalid version value")
    if num < 0:
        return _print_error("invalid version value")
    try:
        apps = _resolve_apps(app)
    except ValueError as exc:
        return _print_error(str(exc))
    current = update_versions.get_current_versions()
    updates: Dict[str, str] = {}
    for name in apps:
        major, minor, patch = update_versions.parse_version(current[name])
        if field == FIELD_MAJOR:
            major = num
        elif field == FIELD_MINOR:
            minor = num
        else:
            patch = num
        updates[name] = update_versions.format_version((major, minor, patch))
        print(_format_transition("DRY-RUN" if dry_run else "APPLY", name, current[name], updates[name]))
    if dry_run:
        return 0
    try:
        update_versions.write_versions(updates)
    except Exception:
        return 1
    return 0


def main(argv: Iterable[str]) -> int:
    args = list(argv)
    if _is_help(args):
        print(USAGE)
        return 0
    args, dry_run = _parse_dry_run(args)
    if not args:
        print(USAGE)
        return 2
    cmd = args[0]
    if cmd == CMD_SHOW:
        if len(args) < 2:
            return _print_error("missing required argument <app|all>")
        return _cmd_show(args[1])
    if cmd == CMD_BUMP:
        if len(args) < 3:
            return _print_error("missing required argument <app|all> or <major|minor|patch>")
        return _cmd_bump(args[1], args[2], dry_run)
    if cmd == CMD_SET:
        if len(args) < 3:
            return _print_error("missing required argument <app|all> or <X.Y.Z>")
        return _cmd_set(args[1], args[2], dry_run)
    if cmd == CMD_FIELD_SET:
        if len(args) < 4:
            return _print_error("missing required argument <app|all> or <value>")
        return _cmd_field_set(args[1], args[2], args[3], dry_run)
    if cmd == CMD_HELP:
        print(USAGE)
        return 0
    print(USAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
