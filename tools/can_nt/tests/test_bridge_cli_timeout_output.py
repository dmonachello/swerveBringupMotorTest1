from __future__ import annotations

import contextlib
import io
import unittest

from tools.can_nt.bridge_cli import (
    BridgeCli,
    EVENT_TYPE_ACK,
    MESSAGE_LEVEL_BEGINNER,
    MESSAGE_LEVEL_EXPERT,
    MESSAGE_WAITING_FOR_OUT,
)
from tools.can_nt.bridge_cmd_tracker import CommandTracker
from tools.can_nt.bridge_session import BridgeEvent


class _AckOnlySession:
    """
    NAME
        _AckOnlySession - Fake session that never returns an OUT event.
    """

    def __init__(self) -> None:
        self._events = [
            BridgeEvent(
                type=EVENT_TYPE_ACK,
                seq=1,
                name="test",
                status="ok",
                message="accepted",
                text="",
                json_text="",
                ts=0.0,
                session_id="",
                state={},
                raw={},
            )
        ]

    def poll_events(self):
        events = self._events
        self._events = []
        return events


class BridgeCliTimeoutOutputTests(unittest.TestCase):
    """
    NAME
        BridgeCliTimeoutOutputTests - Validate host/robot timeout verbosity.
    """

    def _cli_with_level(self, level: str) -> BridgeCli:
        cli = BridgeCli.__new__(BridgeCli)
        cli._session = _AckOnlySession()
        cli._tracker = CommandTracker(timeout_sec=0.01, max_retries=0)
        cli._last_seq = None
        cli._message_level = level
        cli._proto_ack_count = 0
        cli._proto_last_ack_seq = 0
        cli._proto_last_ack_at = 0.0
        cli._proto_out_count = 0
        cli._proto_last_out_seq = 0
        cli._proto_last_out_at = 0.0
        cli._proto_timeout_count = 0
        cli._proto_last_timeout_at = 0.0
        return cli

    def test_interim_out_timeout_hidden_for_beginner(self) -> None:
        cli = self._cli_with_level(MESSAGE_LEVEL_BEGINNER)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            cli._wait_for_seq(1, timeout_sec=0.03, print_events=False)

        self.assertNotIn(MESSAGE_WAITING_FOR_OUT, output.getvalue())

    def test_interim_out_timeout_visible_for_expert(self) -> None:
        cli = self._cli_with_level(MESSAGE_LEVEL_EXPERT)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            cli._wait_for_seq(1, timeout_sec=0.03, print_events=False)

        self.assertIn(MESSAGE_WAITING_FOR_OUT, output.getvalue())


if __name__ == "__main__":
    unittest.main()
