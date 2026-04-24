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

BLOCK_CONFIG = "Local config is not loaded. Import or merge bringup_system.json first."
BLOCK_PROFILE = "Profile is not selected. Select/activate a profile first."
BLOCK_TEST = "No test selected. Select one focused test before running."
BLOCK_ROBOT = "Robot is not connected. Connect/session handshake first."


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
        if not test_selected:
            blocking.append(BLOCK_TEST)

        if blocking:
            return Workflow01Assessment(
                state=STATE_BLOCKED,
                blocking_reasons=blocking,
                next_steps=[STEP_VALIDATE_SYNC],
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

