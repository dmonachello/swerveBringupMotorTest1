from __future__ import annotations

"""
NAME
    update_versions.py - Update app version constants in one command.

SYNOPSIS
    python tools\\update_versions.py --set can_nt_bridge=1.2.3
    python tools\\update_versions.py --set all=1.2.3
    python tools\\update_versions.py --bump bridge_cli=minor
    python tools\\update_versions.py --bump all=patch
"""

import argparse
import re
from pathlib import Path
from typing import Dict, Iterable

from tools.common.app_versions import (
    APP_CAN_BRIDGE_NAME,
    APP_BRIDGE_CLI_NAME,
    APP_BRINGUP_UI_NAME,
    APP_CAN_TOPOLOGY_NAME,
    APP_ROBOT_NAME,
    VERSION_CAN_BRIDGE,
    VERSION_BRIDGE_CLI,
    VERSION_BRINGUP_UI,
    VERSION_CAN_TOPOLOGY,
    VERSION_ROBOT,
)

VERSION_FILE_PATH = "tools/common/app_versions.py"
JAVA_VERSION_FILE_PATH = "src/main/java/frc/robot/AppVersion.java"
CAN_NT_VERSION_FILE_PATH = "tools/can_nt/VERSION"
VERSION_FILE = Path(VERSION_FILE_PATH)
JAVA_VERSION_FILE = Path(JAVA_VERSION_FILE_PATH)
CAN_NT_VERSION_FILE = Path(CAN_NT_VERSION_FILE_PATH)

APP_KEYS = {
    APP_CAN_BRIDGE_NAME: "CAN_BRIDGE",
    APP_BRIDGE_CLI_NAME: "BRIDGE_CLI",
    APP_BRINGUP_UI_NAME: "BRINGUP_UI",
    APP_CAN_TOPOLOGY_NAME: "CAN_TOPOLOGY",
    APP_ROBOT_NAME: "ROBOT",
}

CANONICAL_APP_ORDER = (
    APP_CAN_BRIDGE_NAME,
    APP_BRIDGE_CLI_NAME,
    APP_BRINGUP_UI_NAME,
    APP_CAN_TOPOLOGY_NAME,
    APP_ROBOT_NAME,
)

DEFAULT_VERSIONS = {
    APP_CAN_BRIDGE_NAME: VERSION_CAN_BRIDGE,
    APP_BRIDGE_CLI_NAME: VERSION_BRIDGE_CLI,
    APP_BRINGUP_UI_NAME: VERSION_BRINGUP_UI,
    APP_CAN_TOPOLOGY_NAME: VERSION_CAN_TOPOLOGY,
    APP_ROBOT_NAME: VERSION_ROBOT,
}

ARG_SET = "--set"
ARG_BUMP = "--bump"
ARG_ALL = "all"
ARG_HELP = "Use --set <app>=<version>, --set all=<version>, --bump <app>=<major|minor|patch>, or --bump all=<major|minor|patch>"
MESSAGE_DONE = "Updated versions."
DESCRIPTION_TEXT = "Update app version constants"
ENCODING_UTF8 = "utf-8"
EQUALS = "="
NEWLINE = "\n"
VERSION_KEY_PREFIX = "VERSION_"
VERSION_ASSIGN_PREFIX = " = "
VERSION_FORMAT = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
VERSION_PARTS = ("MAJOR", "MINOR", "PATCH")
VERSION_BUMPS = ("major", "minor", "patch")


def get_current_versions() -> Dict[str, str]:
    """
    NAME
        get_current_versions - Read current app versions from app_versions.py.
    """
    parts: Dict[str, Dict[str, int | None]] = {}
    for key in APP_KEYS.values():
        parts[key] = {"MAJOR": None, "MINOR": None, "PATCH": None}
    try:
        lines = VERSION_FILE.read_text(encoding=ENCODING_UTF8).splitlines()
    except Exception:
        lines = []
    pattern = re.compile(r"^VERSION_(?P<key>[A-Z_]+)_(?P<part>MAJOR|MINOR|PATCH)\s*=\s*(?P<val>\d+)")
    for line in lines:
        match = pattern.match(line.strip())
        if not match:
            continue
        key = match.group("key")
        part = match.group("part")
        val = int(match.group("val"))
        if key in parts and part in parts[key]:
            parts[key][part] = val
    result: Dict[str, str] = {}
    for app, key in APP_KEYS.items():
        entry = parts.get(key, {})
        major = entry.get("MAJOR")
        minor = entry.get("MINOR")
        patch = entry.get("PATCH")
        if major is None or minor is None or patch is None:
            fallback = DEFAULT_VERSIONS.get(app, "0.0.0")
            major, minor, patch = parse_version(fallback)
        result[app] = format_version((int(major), int(minor), int(patch)))
    return result


def parse_version(version: str) -> tuple[int, int, int]:
    """
    NAME
        parse_version - Parse a semantic version string.
    """
    if not VERSION_FORMAT.match(version):
        raise ValueError(ARG_HELP)
    major, minor, patch = version.split(".")
    return (int(major), int(minor), int(patch))


def format_version(parts: tuple[int, int, int]) -> str:
    """
    NAME
        format_version - Format version parts into a semantic version string.
    """
    return f"{parts[0]}.{parts[1]}.{parts[2]}"


def bump_version(parts: tuple[int, int, int], field: str) -> tuple[int, int, int]:
    """
    NAME
        bump_version - Increment a semantic version field.
    """
    return _bump_version(parts, field)


def write_versions(updates: Dict[str, str]) -> None:
    """
    NAME
        write_versions - Persist version updates to canonical files.
    """
    for app in updates:
        if app not in APP_KEYS:
            raise ValueError(ARG_HELP)
    _update_python_versions(VERSION_FILE, updates)
    if APP_ROBOT_NAME in updates:
        _update_java_version(JAVA_VERSION_FILE, updates[APP_ROBOT_NAME])
    if APP_CAN_BRIDGE_NAME in updates:
        _update_can_nt_version(CAN_NT_VERSION_FILE, updates[APP_CAN_BRIDGE_NAME])


def _parse_assignments(values: Iterable[str]) -> Dict[str, str]:
    """
    NAME
        _parse_assignments - Parse app=version assignments.
    """
    result: Dict[str, str] = {}
    for value in values:
        if EQUALS not in value:
            raise ValueError(ARG_HELP)
        app, version = value.split(EQUALS, 1)
        app = app.strip()
        version = version.strip()
        if not VERSION_FORMAT.match(version):
            raise ValueError(ARG_HELP)
        if app == ARG_ALL:
            for key in APP_KEYS:
                result[key] = version
            continue
        if app not in APP_KEYS:
            raise ValueError(ARG_HELP)
        result[app] = version
    return result


def _parse_bumps(values: Iterable[str]) -> Dict[str, str]:
    """
    NAME
        _parse_bumps - Parse app=bump assignments.
    """
    result: Dict[str, str] = {}
    for value in values:
        if EQUALS not in value:
            raise ValueError(ARG_HELP)
        app, bump = value.split(EQUALS, 1)
        app = app.strip()
        bump = bump.strip().lower()
        if bump not in VERSION_BUMPS:
            raise ValueError(ARG_HELP)
        if app == ARG_ALL:
            for key in APP_KEYS:
                result[key] = bump
            continue
        if app not in APP_KEYS:
            raise ValueError(ARG_HELP)
        result[app] = bump
    return result


def _split_version(version: str) -> tuple[int, int, int]:
    """
    NAME
        _split_version - Parse a version string into major/minor/patch ints.
    """
    if not VERSION_FORMAT.match(version):
        raise ValueError(ARG_HELP)
    parts = version.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def _format_version(parts: tuple[int, int, int]) -> str:
    return f"{parts[0]}.{parts[1]}.{parts[2]}"


def _bump_version(parts: tuple[int, int, int], bump: str) -> tuple[int, int, int]:
    major, minor, patch = parts
    if bump == "major":
        return (major + 1, 0, 0)
    if bump == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def _update_python_versions(path: Path, updates: Dict[str, str]) -> None:
    """
    NAME
        _update_python_versions - Update versions in app_versions.py.
    """
    lines = path.read_text(encoding=ENCODING_UTF8).splitlines()
    new_lines = []
    for line in lines:
        updated = line
        for app, key in APP_KEYS.items():
            if app not in updates:
                continue
            major, minor, patch = _split_version(updates[app])
            if line.startswith(f"VERSION_{key}_MAJOR{VERSION_ASSIGN_PREFIX}"):
                updated = f"VERSION_{key}_MAJOR{VERSION_ASSIGN_PREFIX}{major}"
                break
            if line.startswith(f"VERSION_{key}_MINOR{VERSION_ASSIGN_PREFIX}"):
                updated = f"VERSION_{key}_MINOR{VERSION_ASSIGN_PREFIX}{minor}"
                break
            if line.startswith(f"VERSION_{key}_PATCH{VERSION_ASSIGN_PREFIX}"):
                updated = f"VERSION_{key}_PATCH{VERSION_ASSIGN_PREFIX}{patch}"
                break
        new_lines.append(updated)
    path.write_text(NEWLINE.join(new_lines) + NEWLINE, encoding=ENCODING_UTF8)


def _update_java_version(path: Path, version: str) -> None:
    """
    NAME
        _update_java_version - Update the robot app version constant.
    """
    lines = path.read_text(encoding=ENCODING_UTF8).splitlines()
    new_lines = []
    major, minor, patch = _split_version(version)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("public static final int ROBOT_APP_VERSION_MAJOR"):
            new_lines.append(f"  public static final int ROBOT_APP_VERSION_MAJOR = {major};")
            continue
        if stripped.startswith("public static final int ROBOT_APP_VERSION_MINOR"):
            new_lines.append(f"  public static final int ROBOT_APP_VERSION_MINOR = {minor};")
            continue
        if stripped.startswith("public static final int ROBOT_APP_VERSION_PATCH"):
            new_lines.append(f"  public static final int ROBOT_APP_VERSION_PATCH = {patch};")
            continue
        new_lines.append(line)
    path.write_text(NEWLINE.join(new_lines) + NEWLINE, encoding=ENCODING_UTF8)


def _update_can_nt_version(path: Path, version: str) -> None:
    """
    NAME
        _update_can_nt_version - Update tools/can_nt/VERSION for legacy tooling.
    """
    path.write_text(version + NEWLINE, encoding=ENCODING_UTF8)


def main(argv: Iterable[str] | None = None) -> int:
    """
    NAME
        main - Entry point for version updates.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION_TEXT)
    parser.add_argument(ARG_SET, action="append", default=[])
    parser.add_argument(ARG_BUMP, action="append", default=[])
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.set and not args.bump:
        raise SystemExit(ARG_HELP)
    updates = _parse_assignments(args.set)
    bumps = _parse_bumps(args.bump)
    if bumps:
        # Start from current versions, apply explicit --set overrides, then bump.
        base_versions = dict(DEFAULT_VERSIONS)
        base_versions.update(updates)
        for app, bump in bumps.items():
            parts = _split_version(base_versions[app])
            base_versions[app] = _format_version(_bump_version(parts, bump))
        updates = base_versions
    _update_python_versions(VERSION_FILE, updates)
    if APP_ROBOT_NAME in updates:
        _update_java_version(JAVA_VERSION_FILE, updates[APP_ROBOT_NAME])
    if APP_CAN_BRIDGE_NAME in updates:
        _update_can_nt_version(CAN_NT_VERSION_FILE, updates[APP_CAN_BRIDGE_NAME])
    print(MESSAGE_DONE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
