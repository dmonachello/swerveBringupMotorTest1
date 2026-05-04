from __future__ import annotations

import unittest

from tools.can_nt.bridge_cli_ast import BridgeCliAstExecutor
from tools.can_nt.bridge_cli_parser import (
    BridgeCliParser,
    KIND_EXEC_CLEAR_STOP_LATCH,
)


class _FakeSession:
    """
    NAME
        _FakeSession - Minimal command session for executor tests.
    """

    def __init__(self) -> None:
        self.commands: list[tuple[str, dict]] = []

    def is_connected(self) -> bool:
        return True

    def send_command(self, name: str, args: dict | None = None) -> int:
        self.commands.append((name, args or {}))
        return 17


class _FakeCli:
    """
    NAME
        _FakeCli - Minimal CLI facade for AST executor tests.
    """

    def __init__(self) -> None:
        self._session = _FakeSession()
        self.waited_seq: int | None = None

    def _wait_for_seq(self, seq: int) -> object:
        self.waited_seq = seq
        return object()

    def _event_failed(self, _event: object, _label: str) -> bool:
        return False


class BridgeCliClearStopLatchTests(unittest.TestCase):
    """
    NAME
        BridgeCliClearStopLatchTests - Validate CLI safety latch clearing.
    """

    def test_clear_stop_latch_parses_in_exec_mode(self) -> None:
        ast = BridgeCliParser().parse("clear stop-latch", mode="exec").ast

        self.assertEqual(ast.kind, KIND_EXEC_CLEAR_STOP_LATCH)

    def test_clear_safety_latch_alias_parses_in_config_mode(self) -> None:
        ast = BridgeCliParser().parse("clear safety-latch", mode="config").ast

        self.assertEqual(ast.kind, KIND_EXEC_CLEAR_STOP_LATCH)

    def test_executor_sends_robot_clear_stop_latch_command(self) -> None:
        cli = _FakeCli()
        ast = BridgeCliParser().parse("clear stop-latch", mode="exec").ast

        result = BridgeCliAstExecutor(cli).execute(ast)

        self.assertIsNone(result)
        self.assertEqual(cli.waited_seq, 17)
        self.assertEqual(cli._session.commands, [("clearStopLatch", {})])

    def test_show_safety_latch_parses_as_show_target(self) -> None:
        ast = BridgeCliParser().parse("show safety-latch --json", mode="exec").ast

        self.assertEqual(ast.show_target, "safety-latch")
        self.assertTrue(ast.show_json)


if __name__ == "__main__":
    unittest.main()
