from __future__ import annotations

"""
NAME
    bridge_cli_facades.py - Domain facades for bridge CLI command flow.

SYNOPSIS
    Internal helper module used by bridge_cli.py.

DESCRIPTION
    Provides small, stable facades that isolate parse, execute, and output
    responsibilities from the monolithic BridgeCli class. The facades are
    intentionally thin and behavior-preserving.
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from tools.can_nt.bridge_cli_parser import CliParseError
from tools.can_nt.bridge_ops import BridgeCommand
from tools.can_nt.bridge_robot_control_facade import (
    BridgeRobotControlFacade,
    BridgeRobotControlTransport,
)
from tools.can_nt.status import (
    FLAG_PRINT_MESSAGE,
    SS__CLI_PARSER__INVALID_SYNTAX,
    SS__CLI_PARSER__UNKNOWN_COMMAND,
    SS__NORMAL,
    StatusResult,
    format_status,
    format_status_message,
)


LINE_FLAG_PRETTY = "--pretty"
LINE_FLAG_JSON = "--json"
STATUS_DETAIL_PREFIX = "DETAIL: "


@dataclass(frozen=True)
class BridgeCliParseContext:
    """
    NAME
        BridgeCliParseContext - Narrow parse contract for CLI parse facade.
    """

    parse_line: Callable[[str, str], Any]
    split_command: Callable[[str], List[str]]
    maybe_print_failure_hint: Callable[[str], None]
    alias_replacement: Callable[[List[str]], Optional[tuple[str, str]]]
    print_alias_removed: Callable[[str, str], None]
    normalize_tokens: Callable[[List[str], str], List[str]]
    fallback_device_set: Callable[[List[str]], bool]
    config_command: Callable[[List[str]], Optional[object]]
    coerce_status: Callable[[Optional[object]], StatusResult]
    mode_name: str


@dataclass(frozen=True)
class ParsedLineResult:
    """
    NAME
        ParsedLineResult - Parsed CLI line payload for downstream execution.
    """

    tokens: List[str]
    ast: Optional[Any]
    status: Optional[StatusResult]
    line_pretty: bool


class BridgeCliOutputFacade:
    """
    NAME
        BridgeCliOutputFacade - Emit status output for CLI command results.
    """

    def emit_status(self, result: StatusResult, status_include_raw_default: bool) -> None:
        include_raw = status_include_raw_default or bool(result.code & FLAG_PRINT_MESSAGE)
        print(format_status(result.code, include_raw=include_raw))
        status_message = format_status_message(result.code, **result.message_args)
        if status_message:
            print(STATUS_DETAIL_PREFIX + status_message)
        elif result.message:
            print(STATUS_DETAIL_PREFIX + result.message)
        if result.detail:
            print(STATUS_DETAIL_PREFIX + result.detail)


class BridgeCliExecuteFacade:
    """
    NAME
        BridgeCliExecuteFacade - Execute robot-facing bridge commands.
    """

    def __init__(self, robot_control: Optional[BridgeRobotControlFacade] = None) -> None:
        self._robot_control = robot_control if robot_control is not None else BridgeRobotControlFacade()

    def execute_command(self, transport: BridgeRobotControlTransport, command: BridgeCommand) -> StatusResult:
        return self._robot_control.execute_command(transport, command)


class BridgeCliParseFacade:
    """
    NAME
        BridgeCliParseFacade - Parse raw CLI lines into tokens + AST payloads.
    """

    def parse_line(self, context: BridgeCliParseContext, line: str) -> ParsedLineResult:
        line_pretty = self._line_has_pretty_json(line)
        try:
            parsed = context.parse_line(line, context.mode_name)
            tokens = parsed.tokens
            ast = parsed.ast
            if ast is not None and (not ast.verb or not ast.kind):
                ast = None
        except (CliParseError, ValueError) as exc:
            return self._build_parse_error_result(context, line, exc, line_pretty)
        if not tokens:
            return ParsedLineResult(tokens=tokens, ast=ast, status=StatusResult(code=SS__NORMAL), line_pretty=line_pretty)
        return ParsedLineResult(tokens=tokens, ast=ast, status=None, line_pretty=line_pretty)

    @staticmethod
    def _line_has_pretty_json(line: str) -> bool:
        lower_line = line.lower() if isinstance(line, str) else EMPTY_STRING
        return LINE_FLAG_PRETTY in lower_line and LINE_FLAG_JSON in lower_line

    def _build_parse_error_result(
        self,
        context: BridgeCliParseContext,
        line: str,
        exc: Exception,
        line_pretty: bool,
    ) -> ParsedLineResult:
        try:
            tokens = context.split_command(line)
        except Exception as split_exc:
            result = StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX, message=str(split_exc))
            context.maybe_print_failure_hint(line)
            return ParsedLineResult(tokens=[], ast=None, status=result, line_pretty=line_pretty)
        alias_hit = context.alias_replacement(tokens)
        if alias_hit is not None:
            alias_name, canonical = alias_hit
            context.print_alias_removed(alias_name, canonical)
            result = StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)
            return ParsedLineResult(tokens=tokens, ast=None, status=result, line_pretty=line_pretty)
        normalized = context.normalize_tokens(tokens, context.mode_name)
        if context.fallback_device_set(normalized):
            status = context.coerce_status(context.config_command(normalized))
            return ParsedLineResult(tokens=tokens, ast=None, status=status, line_pretty=line_pretty)
        result = StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX, message=str(exc))
        context.maybe_print_failure_hint(line)
        return ParsedLineResult(tokens=tokens, ast=None, status=result, line_pretty=line_pretty)


class BridgeCliValidateFacade:
    """
    NAME
        BridgeCliValidateFacade - Validate parsed line payload before dispatch.
    """

    def validate_parsed_line(self, parsed_line: ParsedLineResult) -> Optional[StatusResult]:
        if parsed_line.status is not None:
            return parsed_line.status
        if not parsed_line.tokens:
            return StatusResult(code=SS__NORMAL)
        return None
