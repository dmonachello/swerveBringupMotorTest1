"""
NAME
    test_bridge_cli_facades.py - Unit tests for bridge CLI facade boundaries.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any, Optional

from tools.can_nt.bridge_cli_facades import (
    BridgeCliParseContext,
    BridgeCliParseFacade,
    BridgeCliValidateFacade,
    ParsedLineResult,
)
from tools.can_nt.bridge_ops import BridgeCommand
from tools.can_nt.bridge_robot_control_facade import (
    BridgeRobotControlFacade,
    BridgeRobotControlTransport,
)
from tools.can_nt.status import (
    SS__CLI_PARSER__UNKNOWN_COMMAND,
    SS__NETWORK__COMMAND_SEND_FAILED,
    SS__NORMAL,
    StatusResult,
)


MODE_EXEC = "exec"
LINE_ALIAS = "old command"
EMPTY_STRING = ""
CMD_TEST = "test"
FIELD_EMPTY = {}


@dataclass
class _ParsedStub:
    tokens: list[str]
    ast: Optional[Any]


class BridgeCliFacadeTests(unittest.TestCase):
    """
    NAME
        BridgeCliFacadeTests - Validate parse/validate/robot-control facade behavior.
    """

    def test_validate_empty_tokens_returns_normal_status(self) -> None:
        facade = BridgeCliValidateFacade()
        parsed = ParsedLineResult(tokens=[], ast=None, status=None, line_pretty=False)
        result = facade.validate_parsed_line(parsed)
        self.assertIsNotNone(result)
        self.assertEqual(result.code, SS__NORMAL)

    def test_parse_alias_replacement_returns_unknown_command(self) -> None:
        facade = BridgeCliParseFacade()
        alias_calls: list[tuple[str, str]] = []

        def _raise_parse(_line: str, _mode: str) -> Any:
            raise ValueError("bad")

        context = BridgeCliParseContext(
            parse_line=_raise_parse,
            split_command=lambda _line: ["old", "command"],
            maybe_print_failure_hint=lambda _line: None,
            alias_replacement=lambda _tokens: (LINE_ALIAS, CMD_TEST),
            print_alias_removed=lambda alias, canonical: alias_calls.append((alias, canonical)),
            normalize_tokens=lambda tokens, _mode: tokens,
            fallback_device_set=lambda _tokens: False,
            config_command=lambda _tokens: None,
            coerce_status=lambda _outcome: StatusResult(code=SS__NORMAL),
            mode_name=MODE_EXEC,
        )

        parsed = facade.parse_line(context, LINE_ALIAS)
        self.assertIsNotNone(parsed.status)
        self.assertEqual(parsed.status.code, SS__CLI_PARSER__UNKNOWN_COMMAND)
        self.assertEqual(alias_calls, [(LINE_ALIAS, CMD_TEST)])

    def test_robot_control_send_failure_maps_status(self) -> None:
        facade = BridgeRobotControlFacade()
        transport = BridgeRobotControlTransport(
            send_command=lambda _name, _args: None,
            mark_command_sent=lambda _name, _now: None,
            wait_for_seq=lambda _seq: None,
            event_failed=lambda _event, _name: False,
            handle_add_device_conflict=lambda _event, _group, _device: False,
        )
        command = BridgeCommand(name=CMD_TEST, args=FIELD_EMPTY)

        result = facade.execute_command(transport, command)
        self.assertEqual(result.code, SS__NETWORK__COMMAND_SEND_FAILED)


if __name__ == "__main__":
    unittest.main()

