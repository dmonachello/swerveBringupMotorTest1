from __future__ import annotations

"""
NAME
    bridge_cli_parser.py - EBNF-aligned parser for the Bridge CLI.

SYNOPSIS
    from tools.can_nt.bridge_cli_parser import BridgeCliParser
    parsed = BridgeCliParser().parse("show status", mode="exec")

DESCRIPTION
    Provides a lightweight, Lark-based parser for the Bridge CLI command
    language. The parser validates minimal structure per the published
    grammar while remaining permissive enough to act as a drop-in
    replacement for legacy token-based parsing.
"""

from dataclasses import dataclass
import shlex
from typing import Dict, List

from lark import Lark, UnexpectedInput

from tools.can_nt.bridge_cli_constants_gen import ParserSpec, SPEC
from tools.can_nt.bridge_cli_grammar_gen import GRAMMAR

PARSER_META_CONST = {
    "dataclass_frozen": True,
}

PARSER_RUNTIME_CONST = {
    "engine": "lalr",
    "lexer": "contextual",
    "start_map": {
        "exec": "exec_line",
        "config": "config_line",
        "group": "group_line",
        "device": "device_line",
    },
}


class CliParseError(ValueError):
    """
    NAME
        CliParseError - Raised when a CLI line fails grammar checks.
    """


@dataclass(frozen=PARSER_META_CONST["dataclass_frozen"])
class CommandAst:
    """
    NAME
        CommandAst - Parsed command structure for CLI execution.

    DESCRIPTION
        Captures the command verb, args, and normalized tokens for
        compatibility with the legacy executor while enabling AST
        execution paths.
    """

    mode: str
    verb: str
    args: List[str]
    tokens: List[str]
    normalized_tokens: List[str]
    kind: str
    show_target: str
    show_name: str
    show_source: str
    show_json: bool
    group_name: str
    device_name: str
    input_name: str
    bind_kind: str
    bind_value: str
    member_action: str
    export_target: str
    save_target: str
    path: str
    test_name: str
    field: str
    value: str


@dataclass(frozen=PARSER_META_CONST["dataclass_frozen"])
class ParsedLine:
    """
    NAME
        ParsedLine - Parsed command line with original tokens.

    DESCRIPTION
        Carries the original token list along with the active CLI mode.
        The tokens are preserved so callers can reuse existing command
        dispatch logic without behavioral changes.
    """

    tokens: List[str]
    mode: str
    ast: CommandAst


class BridgeCliParser:
    """
    NAME
        BridgeCliParser - Grammar-aware parser for Bridge CLI commands.
    """

    def __init__(self, strict: bool = SPEC.strict_default) -> None:
        """
        NAME
            __init__ - Create a Bridge CLI parser.

        PARAMETERS
            strict: When true, reject extra tokens beyond the minimal
                command shape. Default false keeps compatibility with
                legacy permissive parsing.
        """
        self._strict = bool(strict)
        self._common = set(SPEC.common)
        self._show_flags = set(SPEC.show_flags)
        self._show_targets = set(SPEC.show_targets)
        self._bind_kinds = set(SPEC.bind_kinds)
        self._modes = set(SPEC.modes)
        self._dispatch = self._build_dispatch()
        self._parser = Lark(
            GRAMMAR,
            parser=PARSER_RUNTIME_CONST["engine"],
            lexer=PARSER_RUNTIME_CONST["lexer"],
            start=list(PARSER_RUNTIME_CONST["start_map"].values()),
        )

    def _build_dispatch(self) -> Dict[str, Dict[str, callable]]:
        """
        NAME
            _build_dispatch - Build the table-driven command dispatch.
        """
        return {
            SPEC.modes[SPEC.idx_exec]: {
                SPEC.cmd_connect: self._handle_simple,
                SPEC.cmd_disconnect: self._handle_simple,
                SPEC.cmd_configure: self._handle_configure_terminal,
                SPEC.cmd_show: self._handle_show_command,
            },
            SPEC.modes[SPEC.idx_config]: {
                SPEC.cmd_show: self._handle_show_command,
                SPEC.cmd_group: self._handle_group_command,
                SPEC.cmd_no: self._handle_no_group,
                SPEC.cmd_selected_device: self._handle_selected_device,
                SPEC.cmd_selected_mode: self._handle_selected_mode,
                SPEC.cmd_merge: self._handle_merge_import,
                SPEC.cmd_import: self._handle_merge_import,
                SPEC.cmd_export: self._handle_export,
                SPEC.cmd_save: self._handle_save,
                SPEC.cmd_rename: self._handle_rename,
                SPEC.cmd_device: self._handle_device_command,
                SPEC.cmd_validate: self._handle_validate,
            },
            SPEC.modes[SPEC.idx_group]: {
                SPEC.cmd_show: self._handle_group_show,
                SPEC.cmd_add: self._handle_group_add,
                SPEC.cmd_no: self._handle_group_no,
                SPEC.cmd_member: self._handle_group_member,
                SPEC.cmd_bind: self._handle_group_bind,
                SPEC.cmd_enable: self._handle_group_toggle,
                SPEC.cmd_disable: self._handle_group_toggle,
                SPEC.cmd_run: self._handle_group_run,
            },
            SPEC.modes[SPEC.idx_device]: {
                SPEC.cmd_show: self._handle_device_show,
                SPEC.cmd_set: self._handle_device_set,
                SPEC.cmd_no: self._handle_device_no,
            },
        }

    def tokenize(self, line: str) -> List[str]:
        """
        NAME
            tokenize - Split a CLI line into tokens.

        DESCRIPTION
            Uses shlex without escapes to match legacy token behavior.
        """
        lexer = shlex.shlex(line, posix=bool(SPEC.shlex_posix))
        lexer.whitespace_split = bool(SPEC.bool_true)
        lexer.escape = SPEC.empty_str
        lexer.escapechar = SPEC.empty_str
        return list(lexer)

    def parse(self, line: str, mode: str) -> ParsedLine:
        """
        NAME
            parse - Parse and validate a CLI line.

        PARAMETERS
            line: Raw input line from the CLI.
            mode: Current CLI mode (exec/config/group/device).
        """
        tokens = self.tokenize(line)
        if not tokens:
            ast = CommandAst(
                mode=mode,
                verb=SPEC.empty_str,
                args=list(),
                tokens=tokens,
                normalized_tokens=tokens,
                kind=SPEC.empty_str,
                show_target=SPEC.empty_str,
                show_name=SPEC.empty_str,
                show_source=SPEC.empty_str,
                show_json=bool(SPEC.bool_false),
                group_name=SPEC.empty_str,
                device_name=SPEC.empty_str,
                input_name=SPEC.empty_str,
                bind_kind=SPEC.empty_str,
                bind_value=SPEC.empty_str,
                member_action=SPEC.empty_str,
                export_target=SPEC.empty_str,
                save_target=SPEC.empty_str,
                path=SPEC.empty_str,
                test_name=SPEC.empty_str,
                field=SPEC.empty_str,
                value=SPEC.empty_str,
            )
            return ParsedLine(tokens=tokens, mode=mode, ast=ast)
        self._parse_tokens(tokens, mode)
        if line.strip():
            try:
                start_rule = PARSER_RUNTIME_CONST["start_map"].get(mode, "exec_line")
                self._parser.parse(line, start=start_rule)
            except UnexpectedInput as exc:
                raise CliParseError(SPEC.msg_parse_error) from exc
        ast = self._build_ast(tokens, mode)
        return ParsedLine(tokens=tokens, mode=mode, ast=ast)

    def _build_ast(self, tokens: List[str], mode: str) -> CommandAst:
        """
        NAME
            _build_ast - Build a compatibility AST from tokens.
        """
        verb = tokens[SPEC.count_zero].lower() if tokens else SPEC.empty_str
        args = tokens[SPEC.count_one :] if len(tokens) > SPEC.count_one else list()
        normalized = tokens
        kind = SPEC.empty_str
        show_target = SPEC.empty_str
        show_name = SPEC.empty_str
        show_source = SPEC.empty_str
        show_json = bool(SPEC.bool_false)
        group_name = SPEC.empty_str
        device_name = SPEC.empty_str
        input_name = SPEC.empty_str
        bind_kind = SPEC.empty_str
        bind_value = SPEC.empty_str
        member_action = SPEC.empty_str
        export_target = SPEC.empty_str
        save_target = SPEC.empty_str
        path = SPEC.empty_str
        test_name = SPEC.empty_str
        field = SPEC.empty_str
        value = SPEC.empty_str

        if verb in self._common:
            kind = self._common_kind(verb)
        elif mode == SPEC.modes[SPEC.idx_exec]:
            kind, show_target, show_name, show_source, show_json = self._build_exec_ast(tokens)
        elif mode == SPEC.modes[SPEC.idx_config]:
            (
                kind,
                group_name,
                device_name,
                field,
                value,
                save_target,
                export_target,
                path,
                show_target,
                show_name,
                show_source,
                show_json,
            ) = self._build_config_ast(tokens)
        elif mode == SPEC.modes[SPEC.idx_group]:
            (
                kind,
                input_name,
                bind_kind,
                bind_value,
                member_action,
                test_name,
                show_target,
                show_name,
                show_source,
                show_json,
            ) = self._build_group_ast(tokens)
        elif mode == SPEC.modes[SPEC.idx_device]:
            kind, field, value, show_target, show_name, show_source, show_json = self._build_device_ast(tokens)

        return CommandAst(
            mode=mode,
            verb=verb,
            args=args,
            tokens=tokens,
            normalized_tokens=normalized,
            kind=kind,
            show_target=show_target,
            show_name=show_name,
            show_source=show_source,
            show_json=show_json,
            group_name=group_name,
            device_name=device_name,
            input_name=input_name,
            bind_kind=bind_kind,
            bind_value=bind_value,
            member_action=member_action,
            export_target=export_target,
            save_target=save_target,
            path=path,
            test_name=test_name,
            field=field,
            value=value,
        )

    def _common_kind(self, verb: str) -> str:
        if verb in (SPEC.common[SPEC.count_zero], SPEC.common[SPEC.count_four]):
            return SPEC.kind_common_exit
        if verb == SPEC.common[SPEC.count_one]:
            return SPEC.kind_common_end
        if verb == SPEC.common[SPEC.count_two]:
            return SPEC.kind_common_help
        if verb == SPEC.common[SPEC.count_three]:
            return SPEC.kind_common_ping
        return SPEC.empty_str

    def _build_exec_ast(self, tokens: List[str]) -> tuple[str, str, str, str, bool]:
        verb = tokens[SPEC.count_zero].lower()
        if verb == SPEC.cmd_connect:
            return (SPEC.kind_exec_connect, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, bool(SPEC.bool_false))
        if verb == SPEC.cmd_disconnect:
            return (SPEC.kind_exec_disconnect, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, bool(SPEC.bool_false))
        if verb == SPEC.cmd_configure:
            return (SPEC.kind_exec_configure_terminal, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, bool(SPEC.bool_false))
        if verb == SPEC.cmd_show:
            show_source, cleaned, show_json = self._parse_show_flags(tokens[SPEC.count_one :])
            show_target, show_name = self._split_show_target(cleaned)
            return (SPEC.kind_show, show_target, show_name, show_source, show_json)
        return (SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, bool(SPEC.bool_false))

    def _build_config_ast(
        self, tokens: List[str]
    ) -> tuple[str, str, str, str, str, str, str, str, str, str, str, bool]:
        verb = tokens[SPEC.count_zero].lower()
        if verb == SPEC.cmd_show:
            show_source, cleaned, show_json = self._parse_show_flags(tokens[SPEC.count_one :])
            show_target, show_name = self._split_show_target(cleaned)
            return (
                SPEC.kind_show,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                show_target,
                show_name,
                show_source,
                show_json,
            )
        if verb == SPEC.cmd_group:
            return (
                SPEC.kind_config_group,
                tokens[SPEC.count_one],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_no and tokens[SPEC.count_one].lower() == SPEC.cmd_group:
            return (
                SPEC.kind_config_no_group,
                tokens[SPEC.count_two],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_selected_device:
            return (
                SPEC.kind_config_selected_device,
                SPEC.empty_str,
                tokens[SPEC.count_one],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_selected_mode:
            return (
                SPEC.kind_config_selected_mode,
                SPEC.empty_str,
                SPEC.empty_str,
                tokens[SPEC.count_one],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb in (SPEC.cmd_merge, SPEC.cmd_import):
            return (
                SPEC.kind_config_merge if verb == SPEC.cmd_merge else SPEC.kind_config_import,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                tokens[SPEC.count_two],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_export:
            return (
                SPEC.kind_config_export,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                tokens[SPEC.count_one],
                tokens[SPEC.count_two],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_save:
            return (
                SPEC.kind_config_save,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                tokens[SPEC.count_one],
                SPEC.empty_str,
                tokens[SPEC.count_two],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_rename and tokens[SPEC.count_one].lower() == SPEC.cmd_device:
            return (
                SPEC.kind_config_rename_device,
                SPEC.empty_str,
                tokens[SPEC.count_two],
                tokens[SPEC.count_three],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_device:
            if len(tokens) >= SPEC.count_three and tokens[SPEC.count_two].lower() == SPEC.cmd_set:
                value = SPEC.space_str.join(tokens[SPEC.count_four :])
                return (
                    SPEC.kind_config_device_set,
                    SPEC.empty_str,
                    tokens[SPEC.count_one],
                    tokens[SPEC.count_three],
                    value,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                )
            return (
                SPEC.kind_config_device,
                SPEC.empty_str,
                tokens[SPEC.count_one],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_validate:
            path = tokens[SPEC.count_two] if len(tokens) > SPEC.count_two else SPEC.empty_str
            return (
                SPEC.kind_config_validate,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                path,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        return (
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            bool(SPEC.bool_false),
        )

    def _build_group_ast(
        self, tokens: List[str]
    ) -> tuple[str, str, str, str, str, str, str, str, str, bool]:
        verb = tokens[SPEC.count_zero].lower()
        if verb == SPEC.cmd_show:
            if len(tokens) == SPEC.count_one:
                return (
                    SPEC.kind_group_show,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    self._has_json(tokens),
                )
            sub = tokens[SPEC.count_one].lower()
            if sub == SPEC.cmd_members:
                return (
                    SPEC.kind_group_show_members,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    self._has_json(tokens),
                )
            if sub == SPEC.cmd_binding:
                return (
                    SPEC.kind_group_show_binding,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    self._has_json(tokens),
                )
            show_source, cleaned, show_json = self._parse_show_flags(tokens[SPEC.count_one :])
            show_target, show_name = self._split_show_target(cleaned)
            return (
                SPEC.kind_show,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                show_target,
                show_name,
                show_source,
                show_json,
            )
        if verb == SPEC.cmd_add and tokens[SPEC.count_one].lower() == SPEC.cmd_device:
            return (
                SPEC.kind_group_add_device,
                tokens[SPEC.count_two],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_no and tokens[SPEC.count_one].lower() == SPEC.cmd_device:
            return (
                SPEC.kind_group_no_device,
                tokens[SPEC.count_two],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_member:
            return (
                SPEC.kind_group_member,
                tokens[SPEC.count_one],
                SPEC.empty_str,
                SPEC.empty_str,
                tokens[SPEC.count_two].lower(),
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_bind:
            bind_value = tokens[SPEC.count_three] if len(tokens) > SPEC.count_three else SPEC.empty_str
            return (
                SPEC.kind_group_bind,
                tokens[SPEC.count_one],
                tokens[SPEC.count_two].lower(),
                bind_value,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_no and tokens[SPEC.count_one].lower() == SPEC.cmd_bind:
            return (
                SPEC.kind_group_no_bind,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_enable:
            return (
                SPEC.kind_group_enable,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_disable:
            return (
                SPEC.kind_group_disable,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_run:
            name = tokens[SPEC.count_two] if len(tokens) > SPEC.count_two else SPEC.empty_str
            return (
                SPEC.kind_group_run_test,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                name,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        return (
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            bool(SPEC.bool_false),
        )

    def _build_device_ast(
        self, tokens: List[str]
    ) -> tuple[str, str, str, str, str, str, bool]:
        verb = tokens[SPEC.count_zero].lower()
        if verb == SPEC.cmd_show:
            if len(tokens) == SPEC.count_one:
                return (SPEC.kind_device_show, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, self._has_json(tokens))
            show_source, cleaned, show_json = self._parse_show_flags(tokens[SPEC.count_one :])
            show_target, show_name = self._split_show_target(cleaned)
            return (SPEC.kind_show, SPEC.empty_str, SPEC.empty_str, show_target, show_name, show_source, show_json)
        if verb == SPEC.cmd_set:
            value = SPEC.space_str.join(tokens[SPEC.count_two :])
            return (SPEC.kind_device_set, tokens[SPEC.count_one], value, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, bool(SPEC.bool_false))
        if verb == SPEC.cmd_no:
            return (SPEC.kind_device_no, tokens[SPEC.count_one], SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, bool(SPEC.bool_false))
        return (SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, SPEC.empty_str, bool(SPEC.bool_false))

    def _parse_show_flags(self, tokens: List[str]) -> tuple[str, List[str], bool]:
        source = SPEC.empty_str
        cleaned: List[str] = []
        json_output = bool(SPEC.bool_false)
        for tok in tokens:
            lower = tok.lower()
            if lower == SPEC.show_flags[SPEC.count_zero]:
                json_output = bool(SPEC.bool_true)
                continue
            if lower in (SPEC.show_flags[SPEC.count_one], SPEC.show_flags[SPEC.count_two]):
                source = SPEC.show_source_robot
                continue
            if lower in (SPEC.show_flags[SPEC.count_three], SPEC.show_flags[SPEC.count_four]):
                source = SPEC.show_source_local
                continue
            if lower in (SPEC.show_flags[SPEC.count_five], SPEC.show_flags[SPEC.count_six]):
                source = SPEC.show_source_both
                continue
            cleaned.append(tok)
        return source, cleaned, json_output

    def _split_show_target(self, tokens: List[str]) -> tuple[str, str]:
        if not tokens:
            return (SPEC.empty_str, SPEC.empty_str)
        target = tokens[SPEC.count_zero]
        name = tokens[SPEC.count_one] if len(tokens) > SPEC.count_one else SPEC.empty_str
        return (target, name)

    def _has_json(self, tokens: List[str]) -> bool:
        for tok in tokens:
            if tok.lower() == SPEC.show_flags[SPEC.count_zero]:
                return bool(SPEC.bool_true)
        return bool(SPEC.bool_false)

    def _parse_tokens(self, tokens: List[str], mode: str) -> None:
        cmd = tokens[SPEC.count_zero].lower()
        if cmd in self._common:
            return
        mode_rules = self._dispatch.get(mode)
        if not mode_rules:
            raise CliParseError(SPEC.msg_unknown_mode_fmt % mode)
        handler = mode_rules.get(cmd)
        if not handler:
            allowed = self._allowed_modes_for_cmd(cmd)
            if allowed:
                mode_label = self._mode_label(mode)
                allowed_label = ", ".join(allowed)
                raise CliParseError(
                    SPEC.msg_mode_only_fmt % (tokens[SPEC.count_zero], allowed_label)
                )
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        handler(tokens)

    def _allowed_modes_for_cmd(self, cmd: str) -> List[str]:
        allowed: List[str] = []
        for mode_name, rules in self._dispatch.items():
            if cmd in rules:
                allowed.append(self._mode_label(mode_name))
        return allowed

    def _mode_label(self, mode: str) -> str:
        if mode == SPEC.modes[SPEC.idx_exec]:
            return SPEC.msg_mode_name_exec
        if mode == SPEC.modes[SPEC.idx_config]:
            return SPEC.msg_mode_name_config
        if mode == SPEC.modes[SPEC.idx_group]:
            return SPEC.msg_mode_name_group
        if mode == SPEC.modes[SPEC.idx_device]:
            return SPEC.msg_mode_name_device
        return mode

    def _handle_simple(self, tokens: List[str]) -> None:
        self._reject_extra(tokens, SPEC.count_one, SPEC.label_connect)

    def _handle_configure_terminal(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two or tokens[SPEC.count_one].lower() != SPEC.cmd_terminal:
            raise CliParseError(SPEC.msg_config_terminal)
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_configure)

    def _handle_show_command(self, tokens: List[str]) -> None:
        self._parse_show(tokens[SPEC.count_one :], allow_empty=bool(SPEC.disallow_empty))

    def _handle_group_command(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_two, SPEC.msg_group_name)
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_group)

    def _handle_no_group(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two or tokens[SPEC.count_one].lower() != SPEC.cmd_group:
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        self._require(tokens, SPEC.count_three, SPEC.msg_no_group_name)
        self._reject_extra(tokens, SPEC.count_three, SPEC.label_no_group)

    def _handle_selected_device(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_two, SPEC.msg_selected_device)
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_selected_device)

    def _handle_selected_mode(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_two, SPEC.msg_selected_mode)
        if tokens[SPEC.count_one].lower() not in (SPEC.cmd_on, SPEC.cmd_off):
            raise CliParseError(SPEC.msg_selected_mode_value)
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_selected_mode)

    def _handle_merge_import(self, tokens: List[str]) -> None:
        cmd = tokens[SPEC.count_zero].lower()
        if len(tokens) < SPEC.count_three or tokens[SPEC.count_one].lower() != SPEC.cmd_config:
            msg = SPEC.msg_merge_config if cmd == SPEC.cmd_merge else SPEC.msg_import_config
            raise CliParseError(msg)
        label = SPEC.label_merge if cmd == SPEC.cmd_merge else SPEC.label_import
        self._reject_extra(tokens, SPEC.count_three, label)

    def _handle_export(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_three:
            raise CliParseError(SPEC.msg_export_requires)
        target = tokens[SPEC.count_one].lower()
        if target not in (SPEC.cmd_export_runtime_groups, SPEC.cmd_export_cli_script):
            raise CliParseError(SPEC.msg_export_target)
        self._reject_extra(tokens, SPEC.count_three, SPEC.label_export)

    def _handle_save(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_three:
            raise CliParseError(SPEC.msg_save_requires)
        target = tokens[SPEC.count_one].lower()
        if target not in (
            SPEC.cmd_save_config,
            SPEC.cmd_save_local_config,
            SPEC.cmd_save_profiles,
            SPEC.cmd_save_unified,
        ):
            raise CliParseError(SPEC.msg_save_target)
        self._reject_extra(tokens, SPEC.count_three, SPEC.label_save)

    def _handle_rename(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_four or tokens[SPEC.count_one].lower() != SPEC.cmd_device:
            raise CliParseError(SPEC.msg_rename_device)
        self._reject_extra(tokens, SPEC.count_four, SPEC.label_rename)

    def _handle_device_command(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_two, SPEC.msg_device_name)
        if len(tokens) >= SPEC.count_three and tokens[SPEC.count_two].lower() == SPEC.cmd_set:
            self._require(tokens, SPEC.count_five, SPEC.msg_device_set)
            self._reject_extra(tokens, SPEC.count_five, SPEC.label_device_set)
            return
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_device)

    def _handle_validate(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two or tokens[SPEC.count_one].lower() != SPEC.cmd_config:
            raise CliParseError(SPEC.msg_validate_config)
        self._reject_extra(tokens, SPEC.count_three, SPEC.label_validate)

    def _handle_group_show(self, tokens: List[str]) -> None:
        if len(tokens) == SPEC.count_one:
            return
        sub = tokens[SPEC.count_one].lower()
        if sub in (SPEC.cmd_members, SPEC.cmd_binding):
            self._reject_extra(tokens, SPEC.count_two, SPEC.label_show_members)
            return
        self._parse_show(tokens[SPEC.count_one :], allow_empty=bool(SPEC.disallow_empty))

    def _handle_group_add(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two or tokens[SPEC.count_one].lower() != SPEC.cmd_device:
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        self._require(tokens, SPEC.count_three, SPEC.msg_add_device)
        self._reject_extra(tokens, SPEC.count_three, SPEC.label_add_device)

    def _handle_group_no(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two:
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        if tokens[SPEC.count_one].lower() == SPEC.cmd_bind:
            self._reject_extra(tokens, SPEC.count_two, SPEC.label_no_bind)
            return
        if tokens[SPEC.count_one].lower() != SPEC.cmd_device:
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        self._require(tokens, SPEC.count_three, SPEC.msg_no_device)
        self._reject_extra(tokens, SPEC.count_three, SPEC.label_no_device)

    def _handle_group_member(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_three, SPEC.msg_member)
        if tokens[SPEC.count_two].lower() not in (SPEC.cmd_enable, SPEC.cmd_disable, SPEC.cmd_toggle):
            raise CliParseError(SPEC.msg_member_action)
        self._reject_extra(tokens, SPEC.count_three, SPEC.label_member)

    def _handle_group_bind(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_three, SPEC.msg_bind)
        kind = tokens[SPEC.count_two].lower()
        if kind not in self._bind_kinds:
            raise CliParseError(SPEC.msg_bind_kind)
        if kind == SPEC.bind_kinds[SPEC.count_zero]:
            self._reject_extra(tokens, SPEC.count_three, SPEC.label_bind_analog)
            return
        self._require(tokens, SPEC.count_four, SPEC.msg_bind_value)
        self._reject_extra(tokens, SPEC.count_four, SPEC.label_bind)

    def _handle_group_toggle(self, tokens: List[str]) -> None:
        self._reject_extra(tokens, SPEC.count_one, SPEC.label_enable)

    def _handle_group_run(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two or tokens[SPEC.count_one].lower() != SPEC.cmd_test:
            raise CliParseError(SPEC.msg_run_test)
        self._reject_extra(tokens, SPEC.count_three, SPEC.label_run_test)

    def _handle_device_show(self, tokens: List[str]) -> None:
        if len(tokens) == SPEC.count_one:
            return
        self._parse_show(tokens[SPEC.count_one :], allow_empty=bool(SPEC.disallow_empty))

    def _handle_device_set(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_three, SPEC.msg_set)
        self._reject_extra(tokens, SPEC.count_three, SPEC.cmd_set)

    def _handle_device_no(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_two, SPEC.msg_no)
        self._reject_extra(tokens, SPEC.count_two, SPEC.cmd_no)

    def _parse_show(self, tokens: List[str], allow_empty: bool) -> None:
        if not tokens:
            if allow_empty:
                return
            raise CliParseError(SPEC.msg_show_requires)
        core = [tok for tok in tokens if tok.lower() not in self._show_flags]
        if not core:
            raise CliParseError(SPEC.msg_show_requires)
        target = core[SPEC.count_zero].lower()
        if target not in self._show_targets:
            raise CliParseError(SPEC.msg_unknown_show)
        if target in (SPEC.show_target_group, SPEC.show_target_device) and len(core) < SPEC.count_two:
            raise CliParseError(SPEC.msg_show_name % target)
        if self._strict:
            max_len = SPEC.count_two if target in (SPEC.show_target_group, SPEC.show_target_device) else SPEC.count_one
            if len(core) > max_len:
                raise CliParseError(SPEC.msg_show_too_many)

    def _require(self, tokens: List[str], count: int, message: str) -> None:
        if len(tokens) < count:
            raise CliParseError(message)

    def _reject_extra(self, tokens: List[str], count: int, label: str) -> None:
        if self._strict and len(tokens) > count:
            raise CliParseError(SPEC.msg_too_many_fmt % label)
