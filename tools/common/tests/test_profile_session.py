"""
NAME
    test_profile_session.py - Unit tests for shared host/robot profile-session policy.
"""

from __future__ import annotations

import unittest

from tools.common.profile_session import (
    SESSION_STATUS_LOCAL_ONLY,
    SYNC_ACTION_ADOPT,
    SYNC_ACTION_MISSING_LOCAL,
    SYNC_ACTION_NONE,
    SYNC_ACTION_PROMPT,
    decide_host_profile_sync,
    normalize_profile_name,
)


class ProfileSessionPolicyTests(unittest.TestCase):
    def test_normalize_profile_name_strips_inactive_suffix(self) -> None:
        self.assertEqual("demo", normalize_profile_name("demo (inactive)"))

    def test_decide_host_profile_sync_adopts_robot_when_host_empty(self) -> None:
        decision = decide_host_profile_sync("", "robot_profile", ["robot_profile"])
        self.assertEqual(SYNC_ACTION_ADOPT, decision.action)

    def test_decide_host_profile_sync_prompts_on_mismatch(self) -> None:
        decision = decide_host_profile_sync("local_profile", "robot_profile", ["local_profile", "robot_profile"])
        self.assertEqual(SYNC_ACTION_PROMPT, decision.action)

    def test_decide_host_profile_sync_marks_missing_local_profile(self) -> None:
        decision = decide_host_profile_sync("local_profile", "robot_profile", ["local_profile"])
        self.assertEqual(SYNC_ACTION_MISSING_LOCAL, decision.action)

    def test_decide_host_profile_sync_noop_when_robot_missing(self) -> None:
        decision = decide_host_profile_sync("local_profile", "", ["local_profile"])
        self.assertEqual(SYNC_ACTION_NONE, decision.action)

    def test_local_only_status_text_is_stable(self) -> None:
        self.assertEqual("Session: local-only (not connected to robot)", SESSION_STATUS_LOCAL_ONLY)
