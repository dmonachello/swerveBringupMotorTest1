from __future__ import annotations

"""
NAME
    bridge_cli_parser.py - EBNF-aligned parser for the Bridge CLI.

SYNOPSIS
    from tools.can_nt.bridge_cli_parser import BridgeCliParser
    parsed = BridgeCliParser().parse("show status", mode="exec")

DESCRIPTION
    Provides a grammar-driven parser for the Bridge CLI command language.
    The parser validates structure per the published EBNF and keeps
    interactive behavior permissive via prefix expansion.
"""

from dataclasses import dataclass
from pathlib import Path
import shlex
from typing import Dict, List, Set

from tools.can_nt.bridge_cli_constants_gen import ParserSpec, SPEC
from tools.can_nt.cli_grammar_model import (
    CliGrammarModel,
    Literal,
    MODE_CONFIG,
    MODE_DEVICE,
    MODE_EXEC,
    MODE_GROUP,
    MODE_TEST,
)

PARSER_META_CONST = {
    "dataclass_frozen": True,
}

PARSER_RUNTIME_CONST = {
    "start_map": {
        "exec": MODE_EXEC,
        "config": MODE_CONFIG,
        "group": MODE_GROUP,
        "device": MODE_DEVICE,
        "test": MODE_TEST,
    },
}

SHOW_CONFIG_LOCAL_RAW = "local-raw"
SHOW_CONFIG_DIRTY = "dirty"
PATH_SEPARATORS = ("/", "\\", ":")
TOKEN_PREFIX_SKIP = ("\"", "'")
QUESTION_MARK = "?"
EBNF_PATH = Path("tools/can_nt/bridge_cli_ebnf.txt")
SHOW_TARGET_DEVICE = "device"
SHOW_TARGET_CONFIG = "config"
SHOW_TARGET_PROFILE = "profile"
SHOW_TARGET_GROUP = "group"
SHOW_TARGET_TEST = "test"
SHOW_TARGET_TOPOLOGY = "topology"
SHOW_TARGET_NEIGHBORS = "neighbors"
SHOW_TARGET_DEVICE_USAGE = "device-usage"
SHOW_TARGET_BINDING_USAGE = "binding-usage"
SHOW_TARGET_ACTIVE = "active"
SHOW_TARGET_INSTANTIATED = "instantiated"
SHOW_TARGET_FAULTS = "faults"
SHOW_TARGET_SIGNALS = "signals"
SHOW_TARGET_SIGNAL = "signal"
CMD_CONFIG = "config"
CMD_SHOW = "show"
CMD_LS = "ls"
CMD_CONFIGURE = "configure"
CMD_PROFILE = "profile"
CMD_PROFILES = "profiles"
CMD_RUNTIME = "runtime"
CMD_DEVICE = "device"
CMD_DEVICES = "devices"
CMD_GROUP = "group"
CMD_MEMBER = "member"
CMD_NO = "no"
CMD_ASSIGN = "assign"
CMD_DEFAULT = "default"
CMD_CREATE = "create"
CMD_DELETE = "delete"
CMD_SHOW_ALL = "show-all"
CMD_MEMBERS = "members"
CMD_BINDING = "binding"
CMD_ENABLE = "enable"
CMD_DISABLE = "disable"
CMD_TOGGLE = "toggle"
CMD_SELECTED_MODE = "selected-mode"
CMD_ON = "on"
CMD_OFF = "off"
CMD_SAVE = "save"
CMD_SAVE_TESTS = "save-tests"
CMD_RELOAD = SPEC.cmd_reload
CMD_RECOVER = "recover"
CMD_LAST_GOOD = "last-good"
CMD_FROM = "from"
CMD_LIST = "list"
CMD_EXPLAIN = "explain"
CMD_FILE = "file"
CMD_NEXT = "next"
CMD_REMOVE = "remove"
CMD_INSTANTIATE = "instantiate"
CMD_MOTOR = "motor"
FLAG_FORCE = "--force"
FLAG_INSTALL_ROBOT = "--install-robot"
FLAG_REPAIR = "--repair"
FLAG_MERGE = SPEC.cmd_merge_flag
FLAG_REPLACE = SPEC.cmd_replace_flag
CMD_EXPORT = "export"
CMD_IMPORT = "import"
CMD_MERGE = "merge"
CMD_VALIDATE = "validate"
CMD_ALL = "all"
CMD_SCRIPT = "script"
CMD_BINDINGS = "bindings"
CMD_CAN_MAPPINGS = "can-mappings"
CMD_TESTS = "tests"
CMD_TOPOLOGY = "topology"
KIND_GROUP_BIND_LIST = "group_bind_list"
KIND_GROUP_BIND_EXPLAIN = "group_bind_explain"
KIND_GROUP_BIND_TEST = "group_bind_test"
CMD_NEIGHBORS = "neighbors"
CMD_NEIGHBOR_PORTS = "neighbor-ports"
CMD_NEIGHBOR_AUTO = "neighbor-auto"
CMD_NODE = "node"
CMD_NODES = "nodes"
CMD_EDGES = "edges"
CMD_CLEAR = "clear"
CMD_SELECT = "select"
CMD_ACTIVATE_TESTS = "activate"
CMD_DEACTIVATE_TESTS = "deactivate"
CMD_RUN_ALL = "run-all"
CMD_STOP_LATCH = "stop-latch"
CMD_SAFETY_LATCH = "safety-latch"
CMD_PUSH = "push"
CMD_ACTIVATE = "--activate"
CMD_TERMINAL = "terminal"
CMD_PROMPT = "--prompt"
LABEL_ADD = "add"
EXPORT_TARGET_RUNTIME_GROUPS = "runtime-groups"
EXPORT_TARGET_CLI_SCRIPT = "cli-script"
SAVE_TARGET_CONFIG = "config"
SAVE_TARGET_BRIDGE_CONFIG = "bridge-config"
SAVE_TARGET_RUNTIME_GROUPS = "runtime-groups"
SAVE_TARGET_PROFILES = "profiles"
KIND_EXEC_RUN_TEST_DEFAULT = "exec_run_test_default"
KIND_EXEC_CLEAR_STOP_LATCH = "exec_clear_stop_latch"


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
    compatibility with the CLI AST executor
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
    show_pretty: bool
    group_name: str
    profile_name: str
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
                command shape. Default false keeps interactive usage
                permissive.
        """
        self._strict = bool(strict)
        self._common = {cmd.lower() for cmd in SPEC.common}
        self._show_flags = set(SPEC.show_flags)
        self._show_targets = set(SPEC.show_targets)
        self._show_targets.add(SHOW_TARGET_NEIGHBORS)
        self._show_targets.update(
            {
                SHOW_TARGET_ACTIVE,
                SHOW_TARGET_INSTANTIATED,
                SHOW_TARGET_FAULTS,
                SHOW_TARGET_SIGNALS,
                SHOW_TARGET_SIGNAL,
            }
        )
        self._bind_kinds = set(SPEC.bind_kinds)
        self._modes = set(SPEC.modes)
        self._mode = SPEC.modes[SPEC.idx_exec]
        self._mode_cmds = {
            SPEC.modes[SPEC.idx_exec]: set(SPEC.mode_exec_cmds),
            SPEC.modes[SPEC.idx_config]: set(SPEC.mode_config_cmds),
            SPEC.modes[SPEC.idx_group]: set(SPEC.mode_group_cmds),
            SPEC.modes[SPEC.idx_device]: set(SPEC.mode_device_cmds),
            SPEC.modes[SPEC.idx_test]: set(SPEC.mode_test_cmds),
        }
        self._mode_cmds[SPEC.modes[SPEC.idx_config]].add(CMD_TOPOLOGY)
        self._mode_cmds[SPEC.modes[SPEC.idx_exec]].add(CMD_RUNTIME)
        self._mode_cmds[SPEC.modes[SPEC.idx_config]].add(CMD_RUNTIME)
        self._dispatch = self._build_dispatch()
        self._grammar = CliGrammarModel.from_ebnf(EBNF_PATH)

    def _build_dispatch(self) -> Dict[str, Dict[str, callable]]:
        """
        NAME
            _build_dispatch - Build the table-driven command dispatch.
        """
        def _k(cmd: str) -> str:
            return cmd.lower()

        dispatch: Dict[str, Dict[str, callable]] = {}
        for mode, commands in self._mode_cmds.items():
            dispatch[mode] = {}
            for cmd in commands:
                handler = self._handler_for(mode, cmd)
                if handler is None:
                    handler = self._handle_test_any
                dispatch[mode][cmd] = handler
        return dispatch

    def _handler_for(self, mode: str, cmd: str):
        if mode == SPEC.modes[SPEC.idx_exec]:
            if cmd == SPEC.cmd_connect.lower():
                return self._handle_simple
            if cmd == SPEC.cmd_disconnect.lower():
                return self._handle_simple
            if cmd == SPEC.cmd_configure.lower():
                return self._handle_configure_terminal
            if cmd == SPEC.cmd_show.lower():
                return self._handle_show_command
            if cmd == CMD_INSTANTIATE:
                return self._handle_instantiate_command
            if cmd == SPEC.cmd_profile.lower():
                return self._handle_profile
            if cmd == SPEC.cmd_add.lower():
                return self._handle_add_command
            if cmd == CMD_CLEAR:
                return self._handle_clear_command
            if cmd == SPEC.cmd_run.lower():
                return self._handle_run_command
            if cmd == CMD_RUNTIME:
                return self._handle_runtime_command
            return None
        if mode == SPEC.modes[SPEC.idx_config]:
            if cmd == SPEC.cmd_show.lower():
                return self._handle_show_command
            if cmd == CMD_TOPOLOGY:
                return self._handle_topology_command
            if cmd == SPEC.cmd_group.lower():
                return self._handle_group_command
            if cmd == CMD_MEMBER:
                return self._handle_group_member
            if cmd == SPEC.cmd_no.lower():
                return self._handle_config_no
            if cmd == SPEC.cmd_profile.lower():
                return self._handle_profile
            if cmd == SPEC.cmd_profiles.lower():
                return self._handle_profiles_command
            if cmd == CMD_INSTANTIATE:
                return self._handle_instantiate_command
            if cmd == SPEC.cmd_add.lower():
                return self._handle_add_command
            if cmd == CMD_CLEAR:
                return self._handle_clear_command
            if cmd == SPEC.cmd_run.lower():
                return self._handle_run_command
            if cmd == CMD_RUNTIME:
                return self._handle_runtime_command
            if cmd == SPEC.cmd_selected_device.lower():
                return self._handle_selected_device
            if cmd == SPEC.cmd_selected_mode.lower():
                return self._handle_selected_mode
            if cmd == SPEC.cmd_merge.lower() or cmd == SPEC.cmd_import.lower():
                return self._handle_merge_import
            if cmd == SPEC.cmd_export.lower():
                return self._handle_export
            if cmd == SPEC.cmd_save.lower():
                return self._handle_save
            if cmd == CMD_RECOVER:
                return self._handle_recover
            if cmd == SPEC.cmd_load.lower():
                return self._handle_load
            if cmd == SPEC.cmd_reload.lower():
                return self._handle_load
            if cmd == SPEC.cmd_config.lower():
                return self._handle_config_command
            if cmd == SPEC.cmd_rename.lower():
                return self._handle_rename
            if cmd == SPEC.cmd_device.lower():
                return self._handle_device_command
            if cmd == SPEC.cmd_validate.lower():
                return self._handle_validate
            return self._handle_test_any
        if mode == SPEC.modes[SPEC.idx_group]:
            if cmd == SPEC.cmd_show.lower():
                return self._handle_group_show
            if cmd == SPEC.cmd_add.lower():
                return self._handle_group_add
            if cmd == SPEC.cmd_no.lower():
                return self._handle_group_no
            if cmd == SPEC.cmd_member.lower():
                return self._handle_group_member
            if cmd == SPEC.cmd_bind.lower():
                return self._handle_group_bind
            if cmd == SPEC.cmd_enable.lower() or cmd == SPEC.cmd_disable.lower():
                return self._handle_group_toggle
            if cmd == SPEC.cmd_run.lower():
                return self._handle_group_run
            return self._handle_test_any
        if mode == SPEC.modes[SPEC.idx_device]:
            if cmd == SPEC.cmd_show.lower():
                return self._handle_device_show
            if cmd == SPEC.cmd_set.lower():
                return self._handle_device_set
            if cmd == SPEC.cmd_no.lower():
                return self._handle_device_no
            if cmd == SPEC.cmd_delete.lower():
                return self._handle_device_delete
            return self._handle_test_any
        if mode == SPEC.modes[SPEC.idx_test]:
            return self._handle_test_any
        return None

    def tokenize(self, line: str) -> List[str]:
        """
        NAME
            tokenize - Split a CLI line into tokens.

        DESCRIPTION
            Uses shlex without escapes to match token behavior.
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
            mode: Current CLI mode (exec/config/group/device/test).
        """
        tokens = self.tokenize(line)
        if tokens and tokens[-1] == QUESTION_MARK:
            tokens = tokens[:-1]
        normalized_tokens = self.normalize_tokens(tokens, mode)
        if not tokens:
            ast = CommandAst(
                mode=mode,
                verb=SPEC.empty_str,
                args=list(),
                tokens=normalized_tokens,
                normalized_tokens=normalized_tokens,
                kind=SPEC.empty_str,
                show_target=SPEC.empty_str,
                show_name=SPEC.empty_str,
                show_source=SPEC.empty_str,
                show_json=bool(SPEC.bool_false),
                show_pretty=bool(SPEC.bool_false),
                group_name=SPEC.empty_str,
                profile_name=SPEC.empty_str,
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
            return ParsedLine(tokens=normalized_tokens, mode=mode, ast=ast)
        self._parse_tokens(normalized_tokens, mode)
        if line.strip():
            if normalized_tokens and normalized_tokens[SPEC.count_zero].lower() == SPEC.common[SPEC.count_two]:
                return ParsedLine(tokens=normalized_tokens, mode=mode, ast=self._build_ast(normalized_tokens, mode))
            ok, _expected = self._grammar.validate(normalized_tokens, mode)
            if not ok:
                raise CliParseError(SPEC.msg_parse_error)
        ast = self._build_ast(normalized_tokens, mode)
        return ParsedLine(tokens=normalized_tokens, mode=mode, ast=ast)

    def normalize_tokens(self, tokens: List[str], mode: str | None = None) -> List[str]:
        """
        NAME
            normalize_tokens - Normalize alias tokens to canonical commands.
        """
        if not tokens:
            return tokens
        self._mode = mode or SPEC.modes[SPEC.idx_exec]
        normalized: List[str] = []
        expected = self._grammar.expected_next([], self._mode)
        for token in tokens:
            expanded = self._expand_prefix_token(token, expected)
            normalized.append(expanded)
            expected = self._grammar.expected_next(normalized, self._mode)
        return normalized

    def _expand_prefix_token(self, token: str, expected: Set[object]) -> str:
        if not token:
            return token
        if token.startswith(TOKEN_PREFIX_SKIP):
            return token
        for ch in PATH_SEPARATORS:
            if ch in token:
                return token
        token_lower = token.lower()
        candidates = [entry.value for entry in expected if isinstance(entry, Literal)]
        exact = [cand for cand in candidates if cand.lower() == token_lower]
        if exact:
            return exact[0]
        matches = [cand for cand in candidates if cand.lower().startswith(token_lower)]
        if len(matches) == 1:
            return matches[0]
        return token

    def _tokens_to_line(self, tokens: List[str]) -> str:
        result = []
        for token in tokens:
            if not token:
                continue
            if any(ch.isspace() for ch in token) or "\"" in token:
                escaped = token.replace("\"", "\\\"")
                result.append(f"\"{escaped}\"")
            else:
                result.append(token)
        return SPEC.space_str.join(result)

    def expected_suggestions(self, tokens: List[str], mode: str) -> List[str]:
        """
        NAME
            expected_suggestions - Return grammar-driven suggestions.
        """
        expected = self._grammar.expected_next(tokens, mode)
        return self._grammar.expected_to_suggestions(expected)

    def dump_grammar(self, mode: str) -> Dict[str, object]:
        """
        NAME
            dump_grammar - Return a structured grammar dump.
        """
        return self._grammar.dump(mode)

    def dump_grammar_dot(self, mode: str) -> str:
        """
        NAME
            dump_grammar_dot - Return Graphviz DOT for the grammar model.
        """
        return self._grammar.dump_dot(mode)

    def _mode_cmds_for(self, mode: str) -> tuple[str, ...]:
        if mode == SPEC.modes[SPEC.idx_exec]:
            return SPEC.mode_exec_cmds
        if mode == SPEC.modes[SPEC.idx_config]:
            return SPEC.mode_config_cmds
        if mode == SPEC.modes[SPEC.idx_group]:
            return SPEC.mode_group_cmds
        if mode == SPEC.modes[SPEC.idx_device]:
            return SPEC.mode_device_cmds
        if mode == SPEC.modes[SPEC.idx_test]:
            return SPEC.mode_test_cmds
        return tuple()

    def _build_ast(self, tokens: List[str], mode: str) -> CommandAst:
        """
        NAME
            _build_ast - Build a compatibility AST from tokens.
        """
        def _pad(values: tuple, length: int) -> List[object]:
            items = list(values)
            while len(items) < length:
                items.append(bool(SPEC.bool_false))
            return items

        verb = tokens[SPEC.count_zero].lower() if tokens else SPEC.empty_str
        args = tokens[SPEC.count_one :] if len(tokens) > SPEC.count_one else list()
        normalized = tokens
        kind = SPEC.empty_str
        show_target = SPEC.empty_str
        show_name = SPEC.empty_str
        show_source = SPEC.empty_str
        show_json = bool(SPEC.bool_false)
        show_pretty = bool(SPEC.bool_false)
        group_name = SPEC.empty_str
        profile_name = SPEC.empty_str
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
        elif mode == SPEC.modes[SPEC.idx_exec] and verb == SPEC.cmd_profile:
            values = _pad(self._build_config_ast(tokens), 14)
            (
                kind,
                group_name,
                profile_name,
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
                show_pretty,
            ) = values
        elif mode == SPEC.modes[SPEC.idx_exec]:
            values = _pad(self._build_exec_ast(tokens), 6)
            kind, show_target, show_name, show_source, show_json, show_pretty = values
        elif mode == SPEC.modes[SPEC.idx_config]:
            values = _pad(self._build_config_ast(tokens), 14)
            (
                kind,
                group_name,
                profile_name,
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
                show_pretty,
            ) = values
        elif mode == SPEC.modes[SPEC.idx_group]:
            values = _pad(self._build_group_ast(tokens), 11)
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
                show_pretty,
            ) = values
        elif mode == SPEC.modes[SPEC.idx_device]:
            values = _pad(self._build_device_ast(tokens), 8)
            kind, field, value, show_target, show_name, show_source, show_json, show_pretty = values

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
            show_pretty=show_pretty,
            group_name=group_name,
            profile_name=profile_name,
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
        if verb in ("exit", "quit"):
            return SPEC.kind_common_exit
        if verb == "end":
            return SPEC.kind_common_end
        if verb == "help":
            return SPEC.kind_common_help
        if verb == "ping":
            return SPEC.kind_common_ping
        return SPEC.empty_str

    def _build_exec_ast(self, tokens: List[str]) -> tuple[str, str, str, str, bool, bool]:
        verb = tokens[SPEC.count_zero].lower()
        if verb == SPEC.cmd_connect:
            return (
                SPEC.kind_exec_connect,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_disconnect:
            return (
                SPEC.kind_exec_disconnect,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_configure:
            return (
                SPEC.kind_exec_configure_terminal,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_show:
            show_source, cleaned, show_json, show_pretty = self._parse_show_flags(
                tokens[SPEC.count_one :]
            )
            show_target, show_name = self._split_show_target(cleaned)
            return (SPEC.kind_show, show_target, show_name, show_source, show_json, show_pretty)
        if verb == SPEC.cmd_add:
            kind = self._build_add_kind(tokens)
            return (
                kind,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        if verb == CMD_CLEAR:
            return (
                KIND_EXEC_CLEAR_STOP_LATCH,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_run:
            kind = SPEC.empty_str
            if len(tokens) >= SPEC.count_two and tokens[SPEC.count_one].lower() == SPEC.cmd_test:
                kind = KIND_EXEC_RUN_TEST_DEFAULT
            return (
                kind,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_tests:
            if len(tokens) < SPEC.count_two:
                return (
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                    bool(SPEC.bool_false),
                )
            sub = tokens[SPEC.count_one].lower()
            if sub == CMD_SELECT:
                kind = SPEC.kind_exec_tests_select
            elif sub == SPEC.cmd_toggle:
                kind = SPEC.kind_exec_tests_toggle
            elif sub == CMD_ACTIVATE_TESTS:
                kind = SPEC.kind_exec_tests_activate
            elif sub == CMD_DEACTIVATE_TESTS:
                kind = SPEC.kind_exec_tests_deactivate
            elif sub == SPEC.cmd_run:
                kind = SPEC.kind_exec_tests_run
            elif sub == CMD_RUN_ALL:
                kind = SPEC.kind_exec_tests_run_all
            else:
                kind = SPEC.empty_str
            return (
                kind,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_bindings:
            return (
                SPEC.kind_config_bindings,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        return (
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            bool(SPEC.bool_false),
            bool(SPEC.bool_false),
        )

    def _build_config_ast(
        self, tokens: List[str]
    ) -> tuple[str, str, str, str, str, str, str, str, str, str, str, str, bool]:
        verb = tokens[SPEC.count_zero].lower()
        if verb == SPEC.cmd_tests:
            if len(tokens) < SPEC.count_two:
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
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                    bool(SPEC.bool_false),
                )
            sub = tokens[SPEC.count_one].lower()
            if sub == CMD_SELECT:
                kind = SPEC.kind_exec_tests_select
            elif sub == SPEC.cmd_toggle:
                kind = SPEC.kind_exec_tests_toggle
            elif sub == CMD_ACTIVATE_TESTS:
                kind = SPEC.kind_exec_tests_activate
            elif sub == CMD_DEACTIVATE_TESTS:
                kind = SPEC.kind_exec_tests_deactivate
            elif sub == SPEC.cmd_run:
                kind = SPEC.kind_exec_tests_run
            elif sub == CMD_RUN_ALL:
                kind = SPEC.kind_exec_tests_run_all
            else:
                kind = SPEC.empty_str
            return (
                kind,
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
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_run:
            kind = SPEC.empty_str
            if len(tokens) >= SPEC.count_two and tokens[SPEC.count_one].lower() == SPEC.cmd_test:
                kind = KIND_EXEC_RUN_TEST_DEFAULT
            return (
                kind,
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
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_show:
            show_source, cleaned, show_json, show_pretty = self._parse_show_flags(
                tokens[SPEC.count_one :]
            )
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
                SPEC.empty_str,
                show_target,
                show_name,
                show_source,
                show_json,
                show_pretty,
            )
        if verb == SPEC.cmd_add:
            kind = self._build_add_kind(tokens)
            return (
                kind,
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
                bool(SPEC.bool_false),
            )
        if verb == CMD_CLEAR:
            return (
                KIND_EXEC_CLEAR_STOP_LATCH,
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
                bool(SPEC.bool_false),
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
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_no and tokens[SPEC.count_one].lower() == SPEC.cmd_device:
            return (
                SPEC.kind_config_no_device,
                SPEC.empty_str,
                SPEC.empty_str,
                tokens[SPEC.count_two],
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
        if verb == SPEC.cmd_profile:
            if tokens[SPEC.count_one].lower() == SPEC.cmd_create:
                return (
                    SPEC.kind_config_profile,
                    SPEC.empty_str,
                    tokens[SPEC.count_two],
                    SPEC.empty_str,
                    SPEC.cmd_create,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                )
            if tokens[SPEC.count_one].lower() == SPEC.cmd_delete:
                return (
                    SPEC.kind_config_profile,
                    SPEC.empty_str,
                    tokens[SPEC.count_two],
                    SPEC.empty_str,
                    SPEC.cmd_delete,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                )
            if tokens[SPEC.count_one].lower() == SPEC.cmd_default:
                return (
                    SPEC.kind_config_profile,
                    SPEC.empty_str,
                    tokens[SPEC.count_two],
                    SPEC.empty_str,
                    SPEC.cmd_default,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                )
            if tokens[SPEC.count_one].lower() == SPEC.cmd_export:
                return (
                    SPEC.kind_config_profile,
                    SPEC.empty_str,
                    tokens[SPEC.count_two],
                    SPEC.empty_str,
                    SPEC.cmd_export,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    tokens[SPEC.count_three],
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                )
            if (
                len(tokens) >= SPEC.count_four
                and tokens[SPEC.count_one].lower() == SPEC.cmd_device
                and tokens[SPEC.count_two].lower() in (SPEC.cmd_delete, SPEC.cmd_show_all)
            ):
                return (
                    SPEC.kind_config_profile,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    tokens[SPEC.count_three],
                    tokens[SPEC.count_two].lower(),
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                )
            return (
                SPEC.kind_config_profile,
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
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_selected_device:
            return (
                SPEC.kind_config_selected_device,
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
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_selected_mode:
            return (
                SPEC.kind_config_selected_mode,
                SPEC.empty_str,
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
                SPEC.empty_str,
                tokens[SPEC.count_one],
                tokens[SPEC.count_two],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_save:
            cleaned, _flags = self._strip_flags(tokens, [FLAG_FORCE, CMD_PROMPT])
            if len(cleaned) < SPEC.count_two:
                return (
                    SPEC.kind_config_save,
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
            target = cleaned[SPEC.count_one]
            if target.lower() in (SPEC.cmd_sources, CMD_ALL):
                return (
                    SPEC.kind_config_save,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    target,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                )
            path = cleaned[SPEC.count_two] if len(cleaned) >= SPEC.count_three else SPEC.empty_str
            return (
                SPEC.kind_config_save,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                target,
                SPEC.empty_str,
                path,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == CMD_RECOVER:
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
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb in (SPEC.cmd_load, SPEC.cmd_reload):
            target = SPEC.empty_str
            path = SPEC.empty_str
            mode = SPEC.empty_str
            if verb == SPEC.cmd_reload:
                target = SPEC.cmd_sources
            elif len(tokens) >= SPEC.count_two:
                target = tokens[SPEC.count_one].lower()
                if target == SPEC.cmd_config and len(tokens) >= SPEC.count_three:
                    path = tokens[SPEC.count_two]
                    if len(tokens) >= SPEC.count_four:
                        mode = tokens[SPEC.count_three].lower()
            return (
                SPEC.kind_config_load,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                target,
                mode,
                SPEC.empty_str,
                SPEC.empty_str,
                path,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_rename and tokens[SPEC.count_one].lower() == SPEC.cmd_device:
            return (
                SPEC.kind_config_rename_device,
                SPEC.empty_str,
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
        if verb == SPEC.cmd_rename and len(tokens) >= SPEC.count_three:
            return (
                SPEC.kind_config_rename_device,
                SPEC.empty_str,
                SPEC.empty_str,
                tokens[SPEC.count_one],
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
        if verb == SPEC.cmd_device:
            if len(tokens) >= SPEC.count_three and tokens[SPEC.count_two].lower() == SPEC.cmd_set:
                value = SPEC.space_str.join(tokens[SPEC.count_four :])
                return (
                    SPEC.kind_config_device_set,
                    SPEC.empty_str,
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
            cleaned, flags = self._strip_flags(tokens, [FLAG_REPAIR])
            target = cleaned[SPEC.count_one].lower() if len(cleaned) > SPEC.count_one else SPEC.empty_str
            path = SPEC.empty_str
            field = target
            value = SPEC.empty_str
            if len(cleaned) > SPEC.count_two:
                if cleaned[SPEC.count_two].lower() == SPEC.cmd_validate_all:
                    value = SPEC.cmd_validate_all
                elif target in (SPEC.cmd_bindings, SPEC.cmd_can_mappings, SPEC.cmd_config, CMD_FILE):
                    path = cleaned[SPEC.count_two]
                elif target == "profiles":
                    value = cleaned[SPEC.count_two].lower()
            if len(cleaned) > SPEC.count_three and cleaned[SPEC.count_three].lower() == SPEC.cmd_validate_all:
                value = SPEC.cmd_validate_all
            if FLAG_REPAIR in flags:
                value = FLAG_REPAIR
            return (
                SPEC.kind_config_validate,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                field,
                value,
                SPEC.empty_str,
                SPEC.empty_str,
                path,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
            )
        if verb in (SPEC.cmd_profiles, SPEC.cmd_config):
            if len(tokens) >= SPEC.count_two and tokens[SPEC.count_one].lower() == SPEC.cmd_init:
                return (
                    SPEC.kind_config_profiles_init,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    verb,
                    SPEC.cmd_init,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                )
            if len(tokens) >= SPEC.count_three and tokens[SPEC.count_one].lower() == SPEC.cmd_push:
                path = tokens[SPEC.count_two]
                value = SPEC.empty_str
                if len(tokens) >= SPEC.count_five and tokens[SPEC.count_three].lower() == SPEC.cmd_activate:
                    value = tokens[SPEC.count_four]
                return (
                    SPEC.kind_config_push,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    verb,
                    value,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    path,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    bool(SPEC.bool_false),
                )
        if verb == SPEC.cmd_bindings:
            return (
                SPEC.kind_config_bindings,
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
        if verb == SPEC.cmd_can_mappings:
            return (
                SPEC.kind_config_can_mappings,
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
            SPEC.empty_str,
            bool(SPEC.bool_false),
        )

    def _build_add_kind(self, tokens: List[str]) -> str:
        if len(tokens) < SPEC.count_two:
            return SPEC.empty_str
        target = tokens[SPEC.count_one].lower()
        if target == CMD_NEXT:
            return SPEC.kind_exec_add_next
        if target == CMD_ALL:
            return SPEC.kind_exec_add_all
        return SPEC.empty_str

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
                    self._has_pretty(tokens),
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
                    self._has_pretty(tokens),
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
                    self._has_pretty(tokens),
                )
            show_source, cleaned, show_json, show_pretty = self._parse_show_flags(
                tokens[SPEC.count_one :]
            )
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
                show_pretty,
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
            if len(tokens) >= SPEC.count_two:
                action = tokens[SPEC.count_one].lower()
                if action == CMD_LIST:
                    return (
                        KIND_GROUP_BIND_LIST,
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
                if action == CMD_EXPLAIN:
                    return (
                        KIND_GROUP_BIND_EXPLAIN,
                        tokens[SPEC.count_two] if len(tokens) > SPEC.count_two else SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        bool(SPEC.bool_false),
                    )
                if action == SPEC.cmd_test:
                    return (
                        KIND_GROUP_BIND_TEST,
                        tokens[SPEC.count_two] if len(tokens) > SPEC.count_two else SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        SPEC.empty_str,
                        bool(SPEC.bool_false),
                    )
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
                return (
                    SPEC.kind_device_show,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    SPEC.empty_str,
                    self._has_json(tokens),
                    self._has_pretty(tokens),
                )
            show_source, cleaned, show_json, show_pretty = self._parse_show_flags(
                tokens[SPEC.count_one :]
            )
            show_target, show_name = self._split_show_target(cleaned)
            return (
                SPEC.kind_show,
                SPEC.empty_str,
                SPEC.empty_str,
                show_target,
                show_name,
                show_source,
                show_json,
                show_pretty,
            )
        if verb == SPEC.cmd_set:
            value = SPEC.space_str.join(tokens[SPEC.count_two :])
            return (
                SPEC.kind_device_set,
                tokens[SPEC.count_one],
                value,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        if verb not in (SPEC.cmd_no, SPEC.cmd_delete, SPEC.cmd_show, SPEC.cmd_set) and len(tokens) >= SPEC.count_two:
            value = SPEC.space_str.join(tokens[SPEC.count_one :])
            return (
                SPEC.kind_device_set,
                tokens[SPEC.count_zero],
                value,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_no:
            return (
                SPEC.kind_device_no,
                tokens[SPEC.count_one],
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        if verb == SPEC.cmd_delete:
            return (
                SPEC.kind_device_delete,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                SPEC.empty_str,
                bool(SPEC.bool_false),
                bool(SPEC.bool_false),
            )
        return (
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            SPEC.empty_str,
            bool(SPEC.bool_false),
            bool(SPEC.bool_false),
        )

    def _parse_show_flags(self, tokens: List[str]) -> tuple[str, List[str], bool, bool]:
        source = SPEC.empty_str
        cleaned: List[str] = []
        json_output = bool(SPEC.bool_false)
        pretty = bool(SPEC.bool_false)
        for tok in tokens:
            lower = tok.lower()
            if lower == "--json":
                json_output = bool(SPEC.bool_true)
                continue
            if lower == "--pretty":
                pretty = bool(SPEC.bool_true)
                continue
            if lower == "--grouped":
                continue
            if lower in (SPEC.show_source_robot, "--robot"):
                source = SPEC.show_source_robot
                continue
            if lower in (SPEC.show_source_local, "--local"):
                source = SPEC.show_source_local
                continue
            if lower in (SPEC.show_source_both, "--both"):
                source = SPEC.show_source_both
                continue
            cleaned.append(tok)
        return source, cleaned, json_output, pretty

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

    def _has_pretty(self, tokens: List[str]) -> bool:
        for tok in tokens:
            if tok.lower() == SPEC.show_flags[SPEC.count_one]:
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
            ok, _expected = self._grammar.validate(tokens, mode)
            if ok:
                return
            allowed = self._allowed_modes_for_cmd(cmd)
            if allowed:
                mode_label = self._mode_label(mode)
                allowed_label = ", ".join(allowed)
                raise CliParseError(
                    SPEC.msg_mode_only_fmt % (tokens[SPEC.count_zero], allowed_label)
                )
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        handler(tokens)

    def _expand_alias_tokens(self, tokens: List[str]) -> List[str]:
        return tokens

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
        if mode == SPEC.modes[SPEC.idx_test]:
            return SPEC.msg_mode_name_test
        return mode

    def _handle_simple(self, tokens: List[str]) -> None:
        self._reject_extra(tokens, SPEC.count_one, SPEC.label_connect)

    def _handle_test_any(self, tokens: List[str]) -> None:
        """
        NAME
            _handle_test_any - Permissive handler for test authoring commands.
        """

        return

    def _handle_configure_terminal(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two or tokens[SPEC.count_one].lower() != SPEC.cmd_terminal:
            raise CliParseError(SPEC.msg_config_terminal)
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_configure)

    def _handle_show_command(self, tokens: List[str]) -> None:
        self._parse_show(tokens[SPEC.count_one :], allow_empty=bool(SPEC.disallow_empty))

    def _handle_add_command(self, tokens: List[str]) -> None:
        if len(tokens) >= SPEC.count_two and tokens[SPEC.count_one].lower() == CMD_DEVICE:
            if len(tokens) >= SPEC.count_five and tokens[SPEC.count_three].lower() == CMD_GROUP:
                canonical = f"{CMD_GROUP} {CMD_MEMBER} {CMD_ASSIGN} {tokens[SPEC.count_four]} {tokens[SPEC.count_two]}"
            else:
                canonical = f"{CMD_MEMBER} {CMD_ASSIGN} {tokens[SPEC.count_two] if len(tokens) >= SPEC.count_three else '<device>'}"
            raise CliParseError(f"Command '{' '.join(tokens)}' was removed. Use '{canonical}'.")
        if len(tokens) >= SPEC.count_two and tokens[SPEC.count_one].lower() in (CMD_NEXT, CMD_ALL):
            if len(tokens) >= SPEC.count_four and tokens[SPEC.count_two].lower() == CMD_GROUP:
                canonical = f"{CMD_GROUP} {CMD_MEMBER} {CMD_ASSIGN} {tokens[SPEC.count_one].lower()} {tokens[SPEC.count_three]}"
                raise CliParseError(f"Command '{' '.join(tokens)}' was removed. Use '{canonical}'.")
            canonical = (
                f"{CMD_INSTANTIATE} {CMD_NEXT} {CMD_MOTOR}"
                if tokens[SPEC.count_one].lower() == CMD_NEXT
                else f"{CMD_INSTANTIATE} {CMD_ALL} {CMD_DEVICES}"
            )
            raise CliParseError(f"Command '{' '.join(tokens)}' was removed. Use '{canonical}'.")
        raise CliParseError(SPEC.msg_parse_error)

    def _handle_instantiate_command(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_three:
            raise CliParseError(SPEC.msg_parse_error)
        action = tokens[SPEC.count_one].lower()
        target = tokens[SPEC.count_two].lower()
        if action == CMD_NEXT and target == CMD_MOTOR:
            self._reject_extra(tokens, SPEC.count_three, CMD_INSTANTIATE)
            return
        if action == CMD_ALL and target == CMD_DEVICES:
            self._reject_extra(tokens, SPEC.count_three, CMD_INSTANTIATE)
            return
        raise CliParseError(SPEC.msg_parse_error)

    def _handle_clear_command(self, tokens: List[str]) -> None:
        """
        NAME
            _handle_clear_command - Validate robot-side clear commands.
        """
        if len(tokens) < SPEC.count_two:
            raise CliParseError(SPEC.msg_parse_error)
        target = tokens[SPEC.count_one].lower()
        if target not in (CMD_STOP_LATCH, CMD_SAFETY_LATCH):
            raise CliParseError(SPEC.msg_parse_error)
        self._reject_extra(tokens, SPEC.count_two, CMD_CLEAR)

    def _handle_run_command(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two:
            raise CliParseError(SPEC.msg_parse_error)
        if tokens[SPEC.count_one].lower() != SPEC.cmd_test:
            raise CliParseError(SPEC.msg_parse_error)

    def _handle_group_command(self, tokens: List[str]) -> None:
        if len(tokens) >= SPEC.count_two and tokens[SPEC.count_one].lower() == CMD_MEMBER:
            if len(tokens) < SPEC.count_four:
                raise CliParseError(SPEC.msg_member)
            action = tokens[SPEC.count_two].lower()
            if action not in (CMD_ASSIGN, CMD_REMOVE, CMD_ENABLE, CMD_DISABLE, CMD_TOGGLE):
                raise CliParseError(SPEC.msg_member_action)
            if action == CMD_ASSIGN and tokens[SPEC.count_three].lower() in (CMD_ALL, CMD_NEXT):
                self._require(tokens, SPEC.count_five, SPEC.msg_member)
                self._reject_extra(tokens, SPEC.count_five, SPEC.label_member)
                return
            self._require(tokens, SPEC.count_five, SPEC.msg_member)
            self._reject_extra(tokens, SPEC.count_five, SPEC.label_member)
            return
        self._require(tokens, SPEC.count_two, SPEC.msg_group_name)
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_group)

    def _handle_no_group(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two or tokens[SPEC.count_one].lower() != SPEC.cmd_group:
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        self._require(tokens, SPEC.count_three, SPEC.msg_no_group_name)
        self._reject_extra(tokens, SPEC.count_three, SPEC.label_no_group)

    def _handle_config_no(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two:
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        if tokens[SPEC.count_one].lower() == SPEC.cmd_group:
            self._handle_no_group(tokens)
            return
        if tokens[SPEC.count_one].lower() == SPEC.cmd_device:
            self._require(tokens, SPEC.count_three, SPEC.msg_no_device)
            self._reject_extra(tokens, SPEC.count_three, SPEC.label_no_device)
            return
        raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])

    def _handle_selected_device(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_two, SPEC.msg_selected_device)
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_selected_device)

    def _handle_profile(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_two, SPEC.msg_profile_name)
        if tokens[SPEC.count_one].lower() == SPEC.cmd_create:
            self._require(tokens, SPEC.count_three, SPEC.msg_profile_name)
            self._reject_extra(tokens, SPEC.count_three, SPEC.cmd_profile)
            return
        if tokens[SPEC.count_one].lower() == SPEC.cmd_delete:
            self._require(tokens, SPEC.count_three, SPEC.msg_profile_name)
            self._reject_extra(tokens, SPEC.count_three, SPEC.cmd_profile)
            return
        if tokens[SPEC.count_one].lower() == SPEC.cmd_default:
            self._require(tokens, SPEC.count_three, SPEC.msg_profile_name)
            self._reject_extra(tokens, SPEC.count_three, SPEC.cmd_profile)
            return
        if tokens[SPEC.count_one].lower() == SPEC.cmd_export:
            cleaned, _flags = self._strip_flags(tokens, [FLAG_INSTALL_ROBOT])
            self._require(cleaned, SPEC.count_four, SPEC.msg_profile_name)
            self._reject_extra(cleaned, SPEC.count_four, SPEC.cmd_profile)
            return
        if (
            len(tokens) >= SPEC.count_four
            and tokens[SPEC.count_one].lower() == SPEC.cmd_device
            and tokens[SPEC.count_two].lower() in (SPEC.cmd_delete, SPEC.cmd_show_all)
        ):
            self._require(tokens, SPEC.count_four, SPEC.msg_device_name)
            self._reject_extra(tokens, SPEC.count_four, SPEC.cmd_profile)
            return
        self._reject_extra(tokens, SPEC.count_two, SPEC.cmd_profile)

    def _handle_selected_mode(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_two, SPEC.msg_selected_mode)
        if tokens[SPEC.count_one].lower() not in (SPEC.cmd_on, SPEC.cmd_off):
            raise CliParseError(SPEC.msg_selected_mode_value)
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_selected_mode)

    def _handle_profiles_command(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two:
            raise CliParseError(SPEC.msg_push_requires)
        if len(tokens) >= SPEC.count_two and tokens[SPEC.count_one].lower() == SPEC.cmd_init:
            self._reject_extra(tokens, SPEC.count_two, SPEC.label_profiles_init)
            return
        if len(tokens) >= SPEC.count_two and tokens[SPEC.count_one].lower() == SPEC.cmd_reload:
            self._reject_extra(tokens, SPEC.count_two, SPEC.cmd_profiles)
            return
        if len(tokens) >= SPEC.count_two and tokens[SPEC.count_one].lower() == SPEC.cmd_activate_profile:
            self._require(tokens, SPEC.count_three, SPEC.msg_profile_name)
            self._reject_extra(tokens, SPEC.count_three, SPEC.cmd_activate_profile)
            return
        if tokens[SPEC.count_one].lower() == SPEC.cmd_export:
            if len(tokens) < SPEC.count_three:
                raise CliParseError(SPEC.msg_export_requires)
            self._reject_extra(tokens, SPEC.count_three, SPEC.label_export)
            return
        if len(tokens) < SPEC.count_three or tokens[SPEC.count_one].lower() != SPEC.cmd_push:
            raise CliParseError(SPEC.msg_push_requires)
        if len(tokens) == SPEC.count_three:
            return
        if len(tokens) == SPEC.count_five:
            if tokens[SPEC.count_three].lower() != SPEC.cmd_activate:
                self._reject_extra(tokens, SPEC.count_three, SPEC.cmd_push)
            return
        self._reject_extra(tokens, SPEC.count_three, SPEC.cmd_push)

    def _handle_runtime_command(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two:
            raise CliParseError("runtime requires activate [<profile>] or deactivate")
        action = tokens[SPEC.count_one].lower()
        if action == SPEC.cmd_activate_profile:
            self._reject_extra(tokens, SPEC.count_three if len(tokens) >= SPEC.count_three else SPEC.count_two, CMD_RUNTIME)
            return
        if action == "deactivate":
            self._reject_extra(tokens, SPEC.count_two, CMD_RUNTIME)
            return
        raise CliParseError("runtime requires activate [<profile>] or deactivate")

    def _handle_config_command(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_three or tokens[SPEC.count_one].lower() != SPEC.cmd_push:
            raise CliParseError(SPEC.msg_push_requires)
        if len(tokens) == SPEC.count_three:
            return
        if len(tokens) == SPEC.count_five:
            if tokens[SPEC.count_three].lower() != SPEC.cmd_activate:
                self._reject_extra(tokens, SPEC.count_three, SPEC.cmd_push)
            return
        self._reject_extra(tokens, SPEC.count_three, SPEC.cmd_push)

    def _handle_topology_command(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two:
            raise CliParseError(SPEC.msg_parse_error)
        sub = tokens[SPEC.count_one].lower()
        if sub == CMD_NEIGHBOR_PORTS:
            if len(tokens) < SPEC.count_three:
                raise CliParseError(SPEC.msg_parse_error)
            action = tokens[SPEC.count_two].lower()
            if action == SPEC.cmd_set:
                self._require(tokens, 6, SPEC.msg_parse_error)
                self._reject_extra(tokens, 6, CMD_TOPOLOGY)
                return
            if action == SPEC.cmd_delete:
                self._require(tokens, 5, SPEC.msg_parse_error)
                self._reject_extra(tokens, 5, CMD_TOPOLOGY)
                return
            if action == CMD_CLEAR:
                self._require(tokens, 4, SPEC.msg_parse_error)
                self._reject_extra(tokens, 4, CMD_TOPOLOGY)
                return
            raise CliParseError(SPEC.msg_parse_error)
        if sub == CMD_NEIGHBOR_AUTO:
            if len(tokens) < SPEC.count_three:
                raise CliParseError(SPEC.msg_parse_error)
            action = tokens[SPEC.count_two].lower()
            if action == CMD_ALL:
                self._reject_extra(tokens, 4 if len(tokens) > 3 else 3, CMD_TOPOLOGY)
                return
            if action == CMD_NODE:
                self._require(tokens, 4, SPEC.msg_parse_error)
                self._reject_extra(tokens, 4, CMD_TOPOLOGY)
                return
            raise CliParseError(SPEC.msg_parse_error)
        raise CliParseError(SPEC.msg_parse_error)

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

    def _strip_flags(self, tokens: List[str], flags: List[str]) -> tuple[List[str], List[str]]:
        cleaned: List[str] = []
        seen: List[str] = []
        for token in tokens:
            lowered = token.lower()
            if lowered in flags:
                seen.append(lowered)
                continue
            cleaned.append(token)
        return (cleaned, seen)

    def _handle_save(self, tokens: List[str]) -> None:
        cleaned, flags = self._strip_flags(tokens, [FLAG_FORCE, CMD_PROMPT])
        if len(cleaned) < SPEC.count_two:
            raise CliParseError(SPEC.msg_save_requires)
        target = cleaned[SPEC.count_one].lower()
        if CMD_PROMPT in flags and target != CMD_ALL:
            raise CliParseError(SPEC.msg_save_target)
        if target == SPEC.cmd_sources:
            self._reject_extra(cleaned, SPEC.count_two, SPEC.label_save)
            return
        if target == CMD_ALL:
            self._reject_extra(cleaned, SPEC.count_two, SPEC.label_save)
            return
        if target == SPEC.cmd_save_profiles:
            if len(cleaned) == SPEC.count_two:
                return
            self._reject_extra(cleaned, SPEC.count_three, SPEC.label_save)
            return
        if len(cleaned) < SPEC.count_three:
            raise CliParseError(SPEC.msg_save_requires)
        if target not in (
            SAVE_TARGET_CONFIG,
            SAVE_TARGET_BRIDGE_CONFIG,
            SAVE_TARGET_RUNTIME_GROUPS,
            SPEC.cmd_save_profiles,
            SPEC.cmd_save_tests,
        ):
            raise CliParseError(SPEC.msg_save_target)
        self._reject_extra(cleaned, SPEC.count_three, SPEC.label_save)

    def _handle_recover(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two:
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        action = tokens[SPEC.count_one].lower()
        if action in (CMD_LIST, CMD_LAST_GOOD):
            self._reject_extra(tokens, SPEC.count_two, CMD_RECOVER)
            return
        if action == CMD_FROM:
            self._require(tokens, SPEC.count_three, SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
            self._reject_extra(tokens, SPEC.count_three, CMD_RECOVER)
            return
        raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])

    def _handle_load(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two:
            raise CliParseError(SPEC.msg_load_requires)
        verb = tokens[SPEC.count_zero].lower()
        if verb == SPEC.cmd_reload:
            if tokens[SPEC.count_one].lower() != SPEC.cmd_sources:
                raise CliParseError(SPEC.msg_load_requires)
            self._reject_extra(tokens, SPEC.count_two, SPEC.cmd_reload)
            return
        target = tokens[SPEC.count_one].lower()
        if target == SPEC.cmd_sources:
            self._reject_extra(tokens, SPEC.count_two, SPEC.cmd_load)
            return
        if target == SPEC.cmd_config:
            self._require(tokens, SPEC.count_three, SPEC.msg_load_requires)
            if len(tokens) == SPEC.count_three:
                return
            if len(tokens) == SPEC.count_four and tokens[SPEC.count_three].lower() in (
                FLAG_MERGE,
                FLAG_REPLACE,
            ):
                return
            self._reject_extra(tokens, SPEC.count_four, SPEC.cmd_load)
            return
        raise CliParseError(SPEC.msg_load_requires)

    def _handle_rename(self, tokens: List[str]) -> None:
        if len(tokens) >= SPEC.count_four and tokens[SPEC.count_one].lower() == SPEC.cmd_device:
            self._reject_extra(tokens, SPEC.count_four, SPEC.label_rename)
            return
        if len(tokens) >= SPEC.count_three:
            self._reject_extra(tokens, SPEC.count_three, SPEC.label_rename)
            return
        raise CliParseError(SPEC.msg_rename_device)

    def _handle_device_command(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_two, SPEC.msg_device_name)
        if len(tokens) >= SPEC.count_three and tokens[SPEC.count_two].lower() == SPEC.cmd_set:
            self._require(tokens, SPEC.count_five, SPEC.msg_device_set)
            self._reject_extra(tokens, SPEC.count_five, SPEC.label_device_set)
            return
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_device)

    def _handle_validate(self, tokens: List[str]) -> None:
        cleaned, _flags = self._strip_flags(tokens, [FLAG_REPAIR])
        if len(cleaned) < SPEC.count_two:
            raise CliParseError(SPEC.msg_validate_config)
        target = cleaned[SPEC.count_one].lower()
        if target == CMD_ALL:
            self._reject_extra(cleaned, SPEC.count_two, SPEC.label_validate)
            return
        if target == CMD_FILE:
            self._require(cleaned, SPEC.count_three, SPEC.msg_validate_config)
            self._reject_extra(cleaned, SPEC.count_three, SPEC.label_validate)
            return
        if target == SPEC.cmd_config:
            if len(cleaned) > SPEC.count_four:
                self._reject_extra(cleaned, SPEC.count_four, SPEC.label_validate)
                return
            if len(cleaned) == SPEC.count_three:
                if cleaned[SPEC.count_two].lower() == SPEC.cmd_validate_all:
                    return
                self._reject_extra(cleaned, SPEC.count_three, SPEC.label_validate)
                return
            if len(cleaned) == SPEC.count_four:
                if cleaned[SPEC.count_three].lower() != SPEC.cmd_validate_all:
                    self._reject_extra(cleaned, SPEC.count_three, SPEC.label_validate)
                return
            return
        if target in (SPEC.cmd_bindings, SPEC.cmd_can_mappings, CMD_SCRIPT):
            if len(cleaned) > SPEC.count_three:
                self._reject_extra(cleaned, SPEC.count_three, SPEC.label_validate)
                return
            if target == CMD_SCRIPT and len(cleaned) < SPEC.count_three:
                raise CliParseError(SPEC.msg_validate_config)
            return
        if target == "profiles":
            if len(cleaned) > SPEC.count_three:
                self._reject_extra(cleaned, SPEC.count_three, SPEC.label_validate)
                return
            if len(cleaned) == SPEC.count_three:
                if cleaned[SPEC.count_two].lower() not in (
                    SPEC.show_source_robot,
                    SPEC.show_source_local,
                ):
                    self._reject_extra(cleaned, SPEC.count_two, SPEC.label_validate)
                return
            return
        if target == SPEC.cmd_tests:
            self._reject_extra(cleaned, SPEC.count_two, SPEC.label_validate)
            return
        if target == CMD_TOPOLOGY:
            self._reject_extra(cleaned, SPEC.count_two, SPEC.label_validate)
            return
        raise CliParseError(SPEC.msg_validate_config)

    def _handle_group_show(self, tokens: List[str]) -> None:
        if len(tokens) == SPEC.count_one:
            return
        sub = tokens[SPEC.count_one].lower()
        if sub in (SPEC.cmd_members, SPEC.cmd_binding):
            self._reject_extra(tokens, SPEC.count_two, SPEC.label_show_members)
            return
        self._parse_show(tokens[SPEC.count_one :], allow_empty=bool(SPEC.disallow_empty))

    def _handle_group_add(self, tokens: List[str]) -> None:
        if len(tokens) >= SPEC.count_three and tokens[SPEC.count_one].lower() == SPEC.cmd_device:
            raise CliParseError(
                f"Command '{' '.join(tokens)}' was removed. Use '{CMD_MEMBER} {CMD_ASSIGN} {tokens[SPEC.count_two]}'."
            )
        raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])

    def _handle_group_no(self, tokens: List[str]) -> None:
        if len(tokens) < SPEC.count_two:
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        if tokens[SPEC.count_one].lower() == SPEC.cmd_bind:
            self._reject_extra(tokens, SPEC.count_two, SPEC.label_no_bind)
            return
        if tokens[SPEC.count_one].lower() != SPEC.cmd_device:
            raise CliParseError(SPEC.msg_unknown_cmd_fmt % tokens[SPEC.count_zero])
        self._require(tokens, SPEC.count_three, SPEC.msg_no_device)
        raise CliParseError(
            f"Command '{' '.join(tokens)}' was removed. Use '{CMD_MEMBER} {CMD_REMOVE} {tokens[SPEC.count_two]}'."
        )

    def _handle_group_member(self, tokens: List[str]) -> None:
        self._require(tokens, SPEC.count_three, SPEC.msg_member)
        action = tokens[SPEC.count_one].lower()
        if action in (CMD_ASSIGN, CMD_REMOVE, CMD_ENABLE, CMD_DISABLE, CMD_TOGGLE):
            self._reject_extra(tokens, SPEC.count_three, SPEC.label_member)
            return
        if tokens[SPEC.count_two].lower() in (SPEC.cmd_enable, SPEC.cmd_disable, SPEC.cmd_toggle):
            canonical = f"{CMD_MEMBER} {tokens[SPEC.count_two].lower()} {tokens[SPEC.count_one]}"
            raise CliParseError(f"Command '{' '.join(tokens)}' was removed. Use '{canonical}'.")
        raise CliParseError(SPEC.msg_member_action)

    def _handle_group_bind(self, tokens: List[str]) -> None:
        if len(tokens) >= SPEC.count_two:
            action = tokens[SPEC.count_one].lower()
            if action == CMD_LIST:
                self._reject_extra(tokens, SPEC.count_two, SPEC.label_bind)
                return
            if action == CMD_EXPLAIN:
                self._require(tokens, SPEC.count_three, SPEC.msg_bind)
                self._reject_extra(tokens, SPEC.count_three, SPEC.label_bind)
                return
            if action == SPEC.cmd_test:
                self._require(tokens, SPEC.count_three, SPEC.msg_bind)
                self._reject_extra(tokens, SPEC.count_three, SPEC.label_bind)
                return
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
        self._reject_extra(tokens, SPEC.count_two, SPEC.label_no_device)

    def _handle_device_delete(self, tokens: List[str]) -> None:
        self._reject_extra(tokens, SPEC.count_one, SPEC.label_device_delete)

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
        if target in (
            SPEC.show_target_group,
            SPEC.show_target_device,
            SPEC.show_target_test,
            SPEC.show_target_device_usage,
            SPEC.show_target_device_group,
        ) and len(core) < SPEC.count_two:
            raise CliParseError(SPEC.msg_show_name % target)
        if target == SHOW_TARGET_BINDING_USAGE and len(core) < SPEC.count_two:
            raise CliParseError(SPEC.msg_show_name % target)
        if target == SHOW_TARGET_TOPOLOGY:
            if len(core) >= SPEC.count_two and core[SPEC.count_one].lower() == CMD_NODE:
                if len(core) < 3:
                    raise CliParseError(SPEC.msg_show_name % target)
            elif len(core) > 1 and core[SPEC.count_one].lower() not in (CMD_NEIGHBORS, CMD_NODES, CMD_EDGES):
                raise CliParseError(SPEC.msg_show_too_many)
        if target == SHOW_TARGET_NEIGHBORS and len(core) < SPEC.count_two:
            raise CliParseError(SPEC.msg_show_name % target)
        if target == "profiles" and len(core) > SPEC.count_one and self._strict:
            raise CliParseError(SPEC.msg_show_too_many)
        if target == SPEC.show_target_config and len(core) > SPEC.count_one:
            if (
                len(core) == SPEC.count_two
                and core[SPEC.count_one].lower() in (SHOW_CONFIG_LOCAL_RAW, SHOW_CONFIG_DIRTY)
            ):
                pass
            elif self._strict:
                raise CliParseError(SPEC.msg_show_too_many)
        if self._strict:
            if (
                target == SPEC.show_target_config
                and len(core) == SPEC.count_two
                and core[SPEC.count_one].lower() in (SHOW_CONFIG_LOCAL_RAW, SHOW_CONFIG_DIRTY)
            ):
                max_len = SPEC.count_two
            else:
                max_len = SPEC.count_two if target in (
                    SPEC.show_target_group,
                    SPEC.show_target_device,
                    SPEC.show_target_device_group,
                    SPEC.show_target_device_usage,
                    SPEC.show_target_test,
                    SHOW_TARGET_BINDING_USAGE,
                    SHOW_TARGET_NEIGHBORS,
                ) else SPEC.count_one
                if target == SHOW_TARGET_TOPOLOGY:
                    if len(core) >= 2 and core[SPEC.count_one].lower() == CMD_NODE:
                        max_len = 3
                    elif len(core) >= 2 and core[SPEC.count_one].lower() in (CMD_NEIGHBORS, CMD_NODES, CMD_EDGES):
                        max_len = 2
                    else:
                        max_len = 1
            if len(core) > max_len:
                raise CliParseError(SPEC.msg_show_too_many)

    def _require(self, tokens: List[str], count: int, message: str) -> None:
        if len(tokens) < count:
            raise CliParseError(message)

    def _reject_extra(self, tokens: List[str], count: int, label: str) -> None:
        if self._strict and len(tokens) > count:
            raise CliParseError(SPEC.msg_too_many_fmt % label)
