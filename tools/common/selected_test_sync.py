from __future__ import annotations

"""
NAME
    selected_test_sync.py - Shared host-side selected-test synchronization rules.

DESCRIPTION
    Encapsulates the profile-scoped selected-test contract used by host
    operator surfaces so they do not each decide independently when a robot
    selection is stale or when a deferred action should wait on a re-select.
"""

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence


@dataclass(frozen=True)
class SelectedTestCommandPlan:
    """
    NAME
        SelectedTestCommandPlan - Decision for one selected-test action.
    """

    requires_sync: bool
    selected_name: str


def current_test_choices(values: Iterable[object]) -> list[str]:
    """
    NAME
        current_test_choices - Return normalized selected-test choice names.
    """
    choices: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            choices.append(text)
    return choices


def should_accept_robot_selected_test(name: str, choices: Sequence[str]) -> bool:
    """
    NAME
        should_accept_robot_selected_test - Return whether a robot selection is valid locally.
    """
    selected = str(name or "").strip()
    return bool(selected and selected in choices)


def plan_selected_test_command(
    command: str,
    selected_name: str,
    robot_selected_name: str,
    sync_commands: Sequence[str],
) -> SelectedTestCommandPlan:
    """
    NAME
        plan_selected_test_command - Decide whether a selected-test action must sync first.
    """
    local_name = str(selected_name or "").strip()
    robot_name = str(robot_selected_name or "").strip()
    requires_sync = bool(
        command in sync_commands
        and local_name
        and local_name != robot_name
    )
    return SelectedTestCommandPlan(
        requires_sync=requires_sync,
        selected_name=local_name,
    )
