"""
NAME
    profile_session.py - Shared host/robot profile-session policy helpers.

DESCRIPTION
    Centralizes host-side profile context rules that must stay consistent across
    CLI, UI, and topology/editor surfaces. The module intentionally separates
    local file defaults from live robot-selected profile context so disconnected
    host tools do not imply robot alignment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

TEXT_EMPTY = ""
PROFILE_NONE = "(none)"
PROFILE_INACTIVE_SUFFIX = " (inactive)"
SYNC_ACTION_NONE = "none"
SYNC_ACTION_ADOPT = "adopt"
SYNC_ACTION_PROMPT = "prompt"
SYNC_ACTION_MISSING_LOCAL = "missing-local"
SESSION_STATUS_LOCAL_ONLY = "Session: local-only (not connected to robot)"


def normalize_profile_name(value: object) -> str:
    """
    NAME
        normalize_profile_name - Normalize one profile token for host/robot comparison.
    """
    text = str(value or TEXT_EMPTY).strip()
    if not text or text in (PROFILE_NONE, "(none)", "(none) (inactive)"):
        return TEXT_EMPTY
    if text.endswith(PROFILE_INACTIVE_SUFFIX):
        text = text[: -len(PROFILE_INACTIVE_SUFFIX)].strip()
    return text


@dataclass(frozen=True)
class HostProfileSyncDecision:
    """
    NAME
        HostProfileSyncDecision - One shared host-profile reconciliation outcome.
    """

    action: str
    host_profile: str
    robot_profile: str


def decide_host_profile_sync(
    host_profile: object,
    robot_profile: object,
    available_profiles: Iterable[object],
) -> HostProfileSyncDecision:
    """
    NAME
        decide_host_profile_sync - Decide how a host surface should reconcile to robot state.

    DESCRIPTION
        Returns a shared decision so CLI and UI follow the same policy after a
        live robot connection is established:
        - no robot profile: no-op
        - empty host context: adopt robot profile only when it exists locally
        - same host/robot context: no-op
        - robot profile missing locally: warn only
        - otherwise: prompt before adopting the robot profile
    """
    host_name = normalize_profile_name(host_profile)
    robot_name = normalize_profile_name(robot_profile)
    known_profiles = {
        normalize_profile_name(value) for value in available_profiles if normalize_profile_name(value)
    }
    if not robot_name:
        return HostProfileSyncDecision(SYNC_ACTION_NONE, host_name, robot_name)
    if not host_name:
        if robot_name not in known_profiles:
            return HostProfileSyncDecision(SYNC_ACTION_MISSING_LOCAL, host_name, robot_name)
        return HostProfileSyncDecision(SYNC_ACTION_ADOPT, host_name, robot_name)
    if host_name == robot_name:
        return HostProfileSyncDecision(SYNC_ACTION_NONE, host_name, robot_name)
    if robot_name not in known_profiles:
        return HostProfileSyncDecision(SYNC_ACTION_MISSING_LOCAL, host_name, robot_name)
    return HostProfileSyncDecision(SYNC_ACTION_PROMPT, host_name, robot_name)
