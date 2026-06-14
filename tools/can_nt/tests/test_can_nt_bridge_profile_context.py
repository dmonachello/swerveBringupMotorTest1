from __future__ import annotations

import contextlib
import io
import unittest

from unittest.mock import patch

from tools.can_nt.can_nt_bridge import _resolve_startup_profile_name, _sync_cli_profile_context


class _FakeStatus:
    def __init__(self, ok: bool) -> None:
        self._ok = ok

    def ok(self) -> bool:
        return self._ok


class _FakeCli:
    def __init__(self, active_profile: str = "", accept: bool = True) -> None:
        self._profile = active_profile
        self._accept = accept

    def _set_active_profile(self, name: str) -> _FakeStatus:
        if self._accept:
            self._profile = name
            return _FakeStatus(True)
        return _FakeStatus(False)

    def _active_profile_name(self) -> str:
        return self._profile


class CanNtBridgeProfileContextTests(unittest.TestCase):
    """
    NAME
        CanNtBridgeProfileContextTests - Validate host/CLI profile context sync.
    """

    def test_sync_cli_profile_context_updates_active_profile(self) -> None:
        cli = _FakeCli(active_profile="2026_no_swyfts")

        synced = _sync_cli_profile_context(cli, "test_minimal_25_9")

        self.assertTrue(synced)
        self.assertEqual(cli._active_profile_name(), "test_minimal_25_9")

    def test_sync_cli_profile_context_reports_bug_when_cli_rejects_profile(self) -> None:
        cli = _FakeCli(active_profile="2026_no_swyfts", accept=False)
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            synced = _sync_cli_profile_context(cli, "test_minimal_25_9")

        self.assertFalse(synced)
        self.assertIn("BUG: host profile context switched to 'test_minimal_25_9'", output.getvalue())

    def test_resolve_startup_profile_name_falls_back_to_current_default_when_requested_is_stale(self) -> None:
        output = io.StringIO()

        with (
            patch("tools.can_nt.can_nt_bridge.reload_profiles", return_value=(True, "")),
            patch("tools.can_nt.can_nt_bridge.list_profiles", return_value=["test_minimal_25_9", "robot"]),
            patch("tools.can_nt.can_nt_bridge.get_default_profile", return_value="test_minimal_25_9"),
            contextlib.redirect_stdout(output),
        ):
            resolved = _resolve_startup_profile_name("2026_no_swyfts")

        self.assertEqual("test_minimal_25_9", resolved)
        self.assertIn("WARNING: startup profile '2026_no_swyfts' is unavailable; using 'test_minimal_25_9'.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
