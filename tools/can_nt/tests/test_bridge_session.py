"""
NAME
    test_bridge_session.py - Unit tests for BridgeSession cache/reset behavior.
"""

from __future__ import annotations

import unittest

from tools.can_nt.bridge_session import BridgeSession


class BridgeSessionTests(unittest.TestCase):
    def test_reset_handshake_clears_cached_runtime_and_session_state(self) -> None:
        session = BridgeSession("127.0.0.1", 5805, auto_handshake=False)
        session._handshake_done = True
        session._session_id = "session-1"
        session._last_state = {"sessionId": "session-1", "connected": True}
        session._last_runtime_state = {"generatedAtMs": 1234, "selectedProfile": "profile-a"}
        session._last_tests_state = {"rows": [{"name": "test-a"}]}
        session._pending_by_seq[5] = object()  # type: ignore[assignment]

        session.reset_handshake()

        self.assertFalse(session.handshake_done())
        self.assertEqual("", session.session_id())
        self.assertEqual({}, session._last_state)
        self.assertEqual({}, session._last_runtime_state)
        self.assertEqual({}, session._last_tests_state)
        self.assertEqual({}, session._pending_by_seq)

    def test_fetch_runtime_state_returns_empty_when_http_fetch_fails(self) -> None:
        session = BridgeSession("127.0.0.1", 5805, auto_handshake=False)
        session._last_runtime_state = {"generatedAtMs": 1234, "selectedProfile": "profile-a"}
        session._http = type(
            "HttpStub",
            (),
            {"request": lambda _self, *_args, **_kwargs: {"_http_status": 0, "ok": False}},
        )()

        payload = session.fetch_runtime_state()

        self.assertEqual({}, payload)
        self.assertEqual({"generatedAtMs": 1234, "selectedProfile": "profile-a"}, session._last_runtime_state)

    def test_fetch_session_snapshot_returns_empty_when_http_fetch_fails(self) -> None:
        session = BridgeSession("127.0.0.1", 5805, auto_handshake=False)
        session._last_state = {"sessionId": "session-1", "connected": True}
        session._http = type(
            "HttpStub",
            (),
            {"request": lambda _self, *_args, **_kwargs: {"_http_status": 0, "ok": False}},
        )()

        payload = session.fetch_session_snapshot()

        self.assertEqual({}, payload)
        self.assertEqual({"sessionId": "session-1", "connected": True}, session._last_state)


if __name__ == "__main__":
    unittest.main()
