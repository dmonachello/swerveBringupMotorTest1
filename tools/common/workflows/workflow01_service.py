from __future__ import annotations

"""
NAME
    workflow01_service.py - Application service for Workflow 01 (new robot bring-up).
"""

from dataclasses import dataclass
from typing import List


STATE_READY = "ready"
STATE_BLOCKED = "blocked"

STEP_VALIDATE_SYNC = "Run: python -m tools.validate_sync"
STEP_DEPLOY = "Deploy robot code (GradleRIO)."
STEP_REPORTS = "Run focused report(s): state, summary, health."
STEP_RUN_TEST = "Run one focused bring-up test."
STEP_CAPTURE = "Capture evidence if result is ambiguous."
STEP_CONNECT = "Connect to robot TCP session and complete handshake."
STEP_SAVE = "Save local changes (profiles/tests/bindings/mappings) before execution."

BLOCK_CONFIG = "Local config is not loaded. Import or merge bringup_system.json first."
BLOCK_PROFILE = "Profile is not selected. Select/activate a profile first."
BLOCK_TEST = "No test selected. Select one focused test before running."
BLOCK_ROBOT = "Robot is not connected. Connect/session handshake first."
BLOCK_HANDSHAKE = "UI handshake is not complete. Reconnect or run uiHandshake."
BLOCK_SESSION_MISMATCH = "UI session mismatch with robot state. UI lock may be held by another client."
BLOCK_DISABLED = "Robot is disabled. Enable robot before running motion tests."
BLOCK_ESTOP = "Robot is E-stopped. Clear E-stop before proceeding."
BLOCK_UNSAVED = "Unsaved local changes detected. Save sources before execution."


@dataclass(frozen=True)
class Workflow01Assessment:
    """
    NAME
        Workflow01Assessment - Status + next-step guidance for Workflow 01.
    """

    state: str
    blocking_reasons: List[str]
    next_steps: List[str]


class Workflow01Service:
    """
    NAME
        Workflow01Service - Canonical workflow guidance sequencing service.
    """

    def assess(
        self,
        *,
        config_loaded: bool,
        profile_selected: bool,
        robot_connected: bool,
        test_selected: bool,
        handshake_done: bool = False,
        session_mismatch: bool = False,
        robot_enabled: bool = True,
        robot_estopped: bool = False,
        has_unsaved_changes: bool = False,
    ) -> Workflow01Assessment:
        """
        NAME
            assess - Build workflow readiness and guidance for current state.
        """
        blocking: List[str] = []
        if not config_loaded:
            blocking.append(BLOCK_CONFIG)
        if not profile_selected:
            blocking.append(BLOCK_PROFILE)
        if not robot_connected:
            blocking.append(BLOCK_ROBOT)
        if robot_connected and not handshake_done:
            blocking.append(BLOCK_HANDSHAKE)
        if robot_connected and session_mismatch:
            blocking.append(BLOCK_SESSION_MISMATCH)
        if robot_connected and robot_estopped:
            blocking.append(BLOCK_ESTOP)
        if robot_connected and not robot_estopped and not robot_enabled:
            blocking.append(BLOCK_DISABLED)
        if not test_selected:
            blocking.append(BLOCK_TEST)
        if has_unsaved_changes:
            blocking.append(BLOCK_UNSAVED)

        if blocking:
            next_steps: List[str] = [STEP_VALIDATE_SYNC]
            if not robot_connected or not handshake_done:
                next_steps.append(STEP_CONNECT)
            if has_unsaved_changes:
                next_steps.append(STEP_SAVE)
            return Workflow01Assessment(
                state=STATE_BLOCKED,
                blocking_reasons=blocking,
                next_steps=next_steps,
            )

        return Workflow01Assessment(
            state=STATE_READY,
            blocking_reasons=[],
            next_steps=[
                STEP_VALIDATE_SYNC,
                STEP_DEPLOY,
                STEP_REPORTS,
                STEP_RUN_TEST,
                STEP_CAPTURE,
            ],
        )
