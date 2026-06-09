"""
NAME
    test_command_workflow_service.py - Unit tests for shared command workflow helpers.
"""

from __future__ import annotations

import unittest

from tools.can_nt.bridge_cmd_tracker import CommandTracker
from tools.can_nt.bridge_session import BridgeEvent
from tools.can_nt.command_workflow_service import send_tracked_command, wait_for_command_event


class _FakeSession:
    """
    NAME
        _FakeSession - Minimal BridgeSession stand-in for workflow helper tests.
    """

    def __init__(self, events_by_poll):
        self._events_by_poll = list(events_by_poll)
        self.sent = []

    def send_command(self, name, args=None):
        self.sent.append((name, dict(args or {})))
        return 7

    def poll_events(self):
        if not self._events_by_poll:
            return []
        return self._events_by_poll.pop(0)


def _event(event_type: str, seq: int, name: str, status: str, message: str, json_text: str = "") -> BridgeEvent:
    """
    NAME
        _event - Build a minimal BridgeEvent for tests.
    """
    return BridgeEvent(
        type=event_type,
        seq=seq,
        name=name,
        status=status,
        message=message,
        text="",
        json_text=json_text,
        ts=0.0,
        session_id="",
        state={},
        raw={},
    )


class CommandWorkflowServiceTests(unittest.TestCase):
    """
    NAME
        CommandWorkflowServiceTests - Validate shared tracker/send/wait behavior.
    """

    def test_send_tracked_command_starts_tracker(self) -> None:
        session = _FakeSession([])
        tracker = CommandTracker(timeout_sec=1.0, max_retries=0)

        seq = send_tracked_command(session, tracker, "showStatus", {"json": True})

        self.assertEqual(7, seq)
        self.assertTrue(tracker.is_pending())
        self.assertEqual(("showStatus", {"json": True}), tracker.last_command())

    def test_wait_for_command_event_merges_ack_status_into_out(self) -> None:
        session = _FakeSession(
            [
                [_event("ack", 7, "showStatus", "ok", "accepted")],
                [_event("out", 7, "showStatus", "error", "ignored", json_text='{"ok":true}')],
            ]
        )
        tracker = CommandTracker(timeout_sec=1.0, max_retries=0)
        tracker.start("showStatus", {"json": True}, 7, now=0.0)

        result = wait_for_command_event(session, tracker, 7, timeout_sec=0.5)

        self.assertIsNotNone(result.event)
        self.assertEqual("ok", result.event.status)
        self.assertEqual("accepted", result.event.message)
        self.assertFalse(tracker.is_pending())


if __name__ == "__main__":
    unittest.main()
