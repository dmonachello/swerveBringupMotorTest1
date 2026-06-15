from __future__ import annotations

"""
NAME
    bridge_cli_runtime_scope_regression.py - Local regression for runtime scope CLI activation forms.

SYNOPSIS
    python tools/can_nt/scripts/bridge_cli_runtime_scope_regression.py

DESCRIPTION
    Verifies the scoped runtime activation command family on the host/local
    path without requiring a roboRIO.
"""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT_DEPTH = 3
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.can_nt.bridge_cli import BridgeCli
from tools.can_nt.bridge_cli_parser import BridgeCliParser
from tools.can_nt.status import SS__NORMAL


class _FakeSession:
    """
    NAME
        _FakeSession - Minimal connected session stub for runtime command tests.
    """

    def is_connected(self) -> bool:
        return True


class RuntimeScopeRegressionTests(unittest.TestCase):
    def test_parser_accepts_scope_forms(self) -> None:
        parser = BridgeCliParser()
        self.assertEqual(
            parser.parse("runtime activate scope all", mode="exec").tokens,
            ["runtime", "activate", "scope", "all"],
        )
        self.assertEqual(
            parser.parse("runtime activate demo scope all", mode="exec").tokens,
            ["runtime", "activate", "demo", "scope", "all"],
        )
        self.assertEqual(
            parser.parse("runtime activate scope group active-group", mode="exec").tokens,
            ["runtime", "activate", "scope", "group", "active-group"],
        )
        self.assertEqual(
            parser.parse("runtime activate demo scope group motors", mode="exec").tokens,
            ["runtime", "activate", "demo", "scope", "group", "motors"],
        )

    def test_runtime_command_forwards_scope_all(self) -> None:
        cli = BridgeCli(_FakeSession(), batch=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: object()  # type: ignore[method-assign]
        cli._event_failed = lambda event, command_name: False  # type: ignore[method-assign]
        with patch("tools.can_nt.bridge_cli.runtime_activate", return_value=11) as runtime_activate_mock:
            result = cli._runtime_command(["runtime", "activate", "demo", "scope", "all"])
        self.assertEqual(result.code, SS__NORMAL)
        runtime_activate_mock.assert_called_once_with(cli._session, "demo", "all", "")

    def test_runtime_command_forwards_scope_group(self) -> None:
        cli = BridgeCli(_FakeSession(), batch=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: object()  # type: ignore[method-assign]
        cli._event_failed = lambda event, command_name: False  # type: ignore[method-assign]
        with patch("tools.can_nt.bridge_cli.runtime_activate", return_value=12) as runtime_activate_mock:
            result = cli._runtime_command(
                ["runtime", "activate", "demo", "scope", "group", "motors"]
            )
        self.assertEqual(result.code, SS__NORMAL)
        runtime_activate_mock.assert_called_once_with(
            cli._session,
            "demo",
            "group",
            "motors",
        )


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeScopeRegressionTests)
    runner = unittest.TextTestRunner(verbosity=2)
    outcome = runner.run(suite)
    sys.exit(0 if outcome.wasSuccessful() else 1)
