from __future__ import annotations

"""
NAME
    command_catalog_service.py - Shared host-side command catalog loading.

SYNOPSIS
    from tools.can_nt.command_catalog_service import load_host_ui_command_metadata

DESCRIPTION
    Centralizes host/UI command inventory composition so UI surfaces do not own
    their own merge rules for generated robot commands plus host-local actions.
"""

import importlib
from pathlib import Path
from typing import Any, Dict, List, Tuple

from tools.common.json_io import read_json
from tools.common.paths import repo_root

GENERATED_MODULE_NAME = "tools.can_nt.generated.robot_local_commands_generated"
GENERATED_INVENTORY_PATH = (
    repo_root() / "tools" / "can_nt" / "generated" / "robot_local_command_inventory.json"
)
INVENTORY_KEY_ACTION_KIND = "actionKind"
INVENTORY_KEY_COMMANDS = "commands"
INVENTORY_KEY_NAME = "name"
INVENTORY_KEY_SHOW_IN_HOST_UI = "showInHostUi"
INVENTORY_KEY_SOURCE = "source"
INVENTORY_KEY_UI_ARGS_JSON = "uiArgsJson"
INVENTORY_KEY_UI_DESCRIPTION = "uiDescription"
INVENTORY_KEY_UI_LABEL = "uiLabel"
INVENTORY_KEY_UI_SECTION = "uiSection"
ACTION_KIND_REMOTE_COMMAND = "remoteCommand"
EMPTY_STRING = ""


def normalize_action_row(
    row: Dict[str, Any],
    default_source: str,
    default_kind: str,
) -> Dict[str, Any]:
    """
    NAME
        normalize_action_row - Normalize one command/action row to the shared UI schema.
    """
    normalized = dict(row)
    normalized[INVENTORY_KEY_NAME] = str(row.get(INVENTORY_KEY_NAME, EMPTY_STRING)).strip()
    normalized[INVENTORY_KEY_UI_SECTION] = str(
        row.get(INVENTORY_KEY_UI_SECTION, EMPTY_STRING)
    ).strip()
    normalized[INVENTORY_KEY_UI_LABEL] = str(
        row.get(INVENTORY_KEY_UI_LABEL, normalized[INVENTORY_KEY_NAME])
    ).strip()
    normalized[INVENTORY_KEY_UI_DESCRIPTION] = str(
        row.get(INVENTORY_KEY_UI_DESCRIPTION, EMPTY_STRING)
    ).strip()
    normalized[INVENTORY_KEY_UI_ARGS_JSON] = str(
        row.get(INVENTORY_KEY_UI_ARGS_JSON, EMPTY_STRING)
    ).strip()
    normalized[INVENTORY_KEY_SHOW_IN_HOST_UI] = bool(
        row.get(INVENTORY_KEY_SHOW_IN_HOST_UI, True)
    )
    normalized[INVENTORY_KEY_ACTION_KIND] = str(
        row.get(INVENTORY_KEY_ACTION_KIND, default_kind)
    ).strip() or default_kind
    normalized[INVENTORY_KEY_SOURCE] = str(
        row.get(INVENTORY_KEY_SOURCE, default_source)
    ).strip() or default_source
    return normalized


def build_host_ui_sections_from_inventory(
    commands: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    NAME
        build_host_ui_sections_from_inventory - Group UI-visible commands by section.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in commands:
        if not isinstance(row, dict):
            continue
        if not bool(row.get(INVENTORY_KEY_SHOW_IN_HOST_UI)):
            continue
        section = str(row.get(INVENTORY_KEY_UI_SECTION, EMPTY_STRING)).strip()
        if not section:
            continue
        grouped.setdefault(section, []).append(dict(row))
    sections: List[Dict[str, Any]] = []
    for section, items in grouped.items():
        items.sort(key=lambda row: str(row.get(INVENTORY_KEY_NAME, EMPTY_STRING)))
        sections.append({"section": section, "commands": items})
    return sections


def merge_host_ui_actions(
    robot_actions: List[Dict[str, Any]],
    host_actions: List[Dict[str, Any]],
    robot_source: str,
    host_source: str,
    host_action_kind: str,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    NAME
        merge_host_ui_actions - Merge generated robot commands with host-local actions.
    """
    merged_actions = [
        normalize_action_row(row, robot_source, ACTION_KIND_REMOTE_COMMAND)
        for row in robot_actions
        if isinstance(row, dict)
    ]
    merged_actions.extend(
        normalize_action_row(row, host_source, host_action_kind)
        for row in host_actions
        if isinstance(row, dict)
    )
    actions_by_name: Dict[str, Dict[str, Any]] = {}
    for row in merged_actions:
        name = str(row.get(INVENTORY_KEY_NAME, EMPTY_STRING)).strip()
        if not name:
            continue
        actions_by_name[name] = row
    return actions_by_name, build_host_ui_sections_from_inventory(merged_actions)


def load_host_ui_command_metadata(
    host_actions: List[Dict[str, Any]],
    robot_source: str,
    host_source: str,
    host_action_kind: str,
    generated_inventory_path: Path = GENERATED_INVENTORY_PATH,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    NAME
        load_host_ui_command_metadata - Load merged command metadata from generated artifacts plus host actions.
    """
    robot_actions: List[Dict[str, Any]] = []
    try:
        generated = importlib.import_module(GENERATED_MODULE_NAME)
        commands_by_name = getattr(generated, "COMMANDS_BY_NAME", {})
        if isinstance(commands_by_name, dict):
            robot_actions = [
                dict(row) for row in commands_by_name.values() if isinstance(row, dict)
            ]
            return merge_host_ui_actions(
                robot_actions,
                host_actions,
                robot_source,
                host_source,
                host_action_kind,
            )
    except Exception:
        pass
    try:
        payload = read_json(generated_inventory_path)
    except Exception:
        return merge_host_ui_actions(
            [],
            host_actions,
            robot_source,
            host_source,
            host_action_kind,
        )
    commands = payload.get(INVENTORY_KEY_COMMANDS)
    if not isinstance(commands, list):
        return merge_host_ui_actions(
            [],
            host_actions,
            robot_source,
            host_source,
            host_action_kind,
        )
    robot_actions = [dict(row) for row in commands if isinstance(row, dict)]
    return merge_host_ui_actions(
        robot_actions,
        host_actions,
        robot_source,
        host_source,
        host_action_kind,
    )
