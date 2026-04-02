from __future__ import annotations

"""
NAME
    update_versions.py - Update app version constants in one command.

SYNOPSIS
    python tools\\update_versions.py --set can_nt_bridge=1.2.3
    python tools\\update_versions.py --set all=1.2.3
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
    APP_CAN_BRIDGE_NAME: "VERSION_CAN_BRIDGE",
    APP_BRIDGE_CLI_NAME: "VERSION_BRIDGE_CLI",
    APP_BRINGUP_UI_NAME: "VERSION_BRINGUP_UI",
    APP_CAN_TOPOLOGY_NAME: "VERSION_CAN_TOPOLOGY",
    APP_ROBOT_NAME: "VERSION_ROBOT",
}

DEFAULT_VERSIONS = {
    APP_CAN_BRIDGE_NAME: VERSION_CAN_BRIDGE,
    APP_BRIDGE_CLI_NAME: VERSION_BRIDGE_CLI,
    APP_BRINGUP_UI_NAME: VERSION_BRINGUP_UI,
    APP_CAN_TOPOLOGY_NAME: VERSION_CAN_TOPOLOGY,
    APP_ROBOT_NAME: VERSION_ROBOT,
}

ARG_SET = "--set"
ARG_ALL = "all"
ARG_HELP = "Use --set <app>=<version> or --set all=<version>"
MESSAGE_DONE = "Updated versions."
DESCRIPTION_TEXT = "Update app version constants"
ENCODING_UTF8 = "utf-8"
EQUALS = "="
NEWLINE = "\n"
ROBOT_VERSION_DECL = "public static final String ROBOT_APP_VERSION"
VERSION_KEY_PREFIX = "VERSION_"
VERSION_ASSIGN_PREFIX = " = "
VERSION_FORMAT = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


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
            if line.startswith(f"{key}{VERSION_ASSIGN_PREFIX}"):
                updated = f'{key}{VERSION_ASSIGN_PREFIX}"{updates[app]}"'
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
    for line in lines:
        if line.strip().startswith(ROBOT_VERSION_DECL):
            updated = line.split(EQUALS, 1)[0].rstrip()
            new_lines.append(f"{updated}{VERSION_ASSIGN_PREFIX}\\\"{version}\\\";")
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
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.set:
        raise SystemExit(ARG_HELP)
    updates = _parse_assignments(args.set)
    _update_python_versions(VERSION_FILE, updates)
    if APP_ROBOT_NAME in updates:
        _update_java_version(JAVA_VERSION_FILE, updates[APP_ROBOT_NAME])
    if APP_CAN_BRIDGE_NAME in updates:
        _update_can_nt_version(CAN_NT_VERSION_FILE, updates[APP_CAN_BRIDGE_NAME])
    print(MESSAGE_DONE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
