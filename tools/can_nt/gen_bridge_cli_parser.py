from __future__ import annotations

"""
NAME
    gen_bridge_cli_parser.py - Generate CLI grammar/constants from EBNF spec.

SYNOPSIS
    python tools\\can_nt\\gen_bridge_cli_parser.py

DESCRIPTION
    Reads bridge_cli_ebnf.txt plus bridge_cli_grammar_meta.json and writes
    bridge_cli_grammar_gen.py and bridge_cli_constants_gen.py.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
EBNF_PATH = SCRIPT_DIR / "bridge_cli_ebnf.txt"
META_PATH = SCRIPT_DIR / "bridge_cli_grammar_meta.json"
OUT_GRAMMAR = SCRIPT_DIR / "bridge_cli_grammar_gen.py"
OUT_CONST = SCRIPT_DIR / "bridge_cli_constants_gen.py"

SHOW_TARGET_MESSAGE_LEVEL = "message-level"
SHOW_TARGET_DEVICE_USAGE = "device-usage"

RULE_SKIP = {
    "name",
    "input",
    "value",
    "path",
    "field",
    "value_text",
    "number",
    "digit",
    "token",
    "token_char",
    "ws",
}

LARK_PREAMBLE = """
%import common.WS_INLINE
%ignore /\\r?\\n/
""".lstrip()

LEXICAL_RULES = """
TOKEN: /\\\"[^\\\"]*\\\"|[^\\s]+/
NUMBER: /[+-]?\\d+(\\.\\d+)?/
WS: /[ \\t]+/
""".strip()

CUSTOM_RULES = """
ws: WS
name: TOKEN
input: TOKEN
path: TOKEN
field: TOKEN | "type" | "invert"
value: NUMBER
number: NUMBER
value_text: (TOKEN | "true" | "false" | "on" | "off") (WS (TOKEN | "true" | "false" | "on" | "off"))*
""".strip()

CMD_SHOW_ALL = "show-all"


@dataclass
class RuleBlock:
    name: str
    expr: str


def _strip_comments(text: str) -> str:
    return re.sub(r"\\(\\*.*?\\*\\)", "", text, flags=re.S)


def _collect_rules(text: str) -> List[RuleBlock]:
    rules: List[RuleBlock] = []
    current_name = None
    current_parts: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "=" in line and line.split("=")[0].strip().isidentifier():
            if current_name is not None:
                rules.append(RuleBlock(current_name, " ".join(current_parts)))
            before, after = line.split("=", 1)
            current_name = before.strip()
            current_parts = [after.strip()]
            if after.strip().endswith(";"):
                current_parts[-1] = current_parts[-1].rstrip(";")
                rules.append(RuleBlock(current_name, " ".join(current_parts)))
                current_name = None
                current_parts = []
            continue
        if current_name is None:
            continue
        current_parts.append(line)
        if line.endswith(";"):
            current_parts[-1] = current_parts[-1].rstrip(";")
            rules.append(RuleBlock(current_name, " ".join(current_parts)))
            current_name = None
            current_parts = []
    if current_name is not None:
        rules.append(RuleBlock(current_name, " ".join(current_parts)))
    return rules


def _prepare_expr(expr: str) -> str:
    expr = re.sub(r"(\"[^\"]+\")\?", r"\\1 ?", expr)
    expr = re.sub(r"([A-Za-z_][A-Za-z0-9_]*)\?", r"\\1 ?", expr)
    return expr


def _tokenize_expr(expr: str) -> List[tuple[str, str]]:
    expr = _prepare_expr(expr)
    tokens: List[tuple[str, str]] = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "|(){}[]?":
            tokens.append((ch, ch))
            i += 1
            continue
        if ch == '"':
            j = i + 1
            while j < len(expr) and expr[j] != '"':
                j += 1
            value = expr[i + 1 : j]
            tokens.append(("lit", value))
            i = j + 1
            continue
        if ch.isalnum() or ch == "_":
            j = i + 1
            while j < len(expr) and (expr[j].isalnum() or expr[j] == "_"):
                j += 1
            tokens.append(("id", expr[i:j]))
            i = j
            continue
        i += 1
    return tokens


def _parse_expr(tokens: List[tuple[str, str]], idx: int = 0) -> tuple[dict, int]:
    def parse_seq(index: int) -> tuple[list, int]:
        items: List[dict] = []
        while index < len(tokens):
            kind, value = tokens[index]
            if kind in (")", "]", "}", "|"):
                break
            if kind == "(":
                node, index = _parse_expr(tokens, index + 1)
                if index < len(tokens) and tokens[index][0] == ")":
                    index += 1
            elif kind == "[":
                node, index = _parse_expr(tokens, index + 1)
                if index < len(tokens) and tokens[index][0] == "]":
                    index += 1
                node = {"type": "opt", "child": node}
            elif kind == "{":
                node, index = _parse_expr(tokens, index + 1)
                if index < len(tokens) and tokens[index][0] == "}":
                    index += 1
                node = {"type": "rep", "child": node}
            elif kind == "lit":
                node = {"type": "lit", "value": value}
                index += 1
            elif kind == "id":
                node = {"type": "id", "value": value}
                index += 1
            else:
                index += 1
                continue

            if index < len(tokens) and tokens[index][0] == "?":
                node = {"type": "opt", "child": node}
                index += 1
            items.append(node)
        return items, index

    alts: List[dict] = []
    seq, idx = parse_seq(idx)
    alts.append({"type": "seq", "items": seq})
    while idx < len(tokens) and tokens[idx][0] == "|":
        seq, idx = parse_seq(idx + 1)
        alts.append({"type": "seq", "items": seq})
    return {"type": "alt", "alts": alts}, idx


def _build_rule_ast(expr: str) -> dict:
    tokens = _tokenize_expr(expr)
    node, _ = _parse_expr(tokens, 0)
    return node


def _compute_first_sets(rules: Dict[str, dict]) -> Dict[str, set[str]]:
    nullable_cache: Dict[str, bool] = {}
    first_cache: Dict[str, set[str]] = {}

    def nullable(node: dict) -> bool:
        t = node["type"]
        if t == "lit":
            return False
        if t == "id":
            name = node["value"]
            if name == "ws":
                return True
            if name in nullable_cache:
                return nullable_cache[name]
            if name not in rules:
                return False
            nullable_cache[name] = False
            nullable_cache[name] = nullable(rules[name])
            return nullable_cache[name]
        if t == "seq":
            return all(nullable(item) for item in node["items"])
        if t == "alt":
            return any(nullable(alt) for alt in node["alts"])
        if t in ("opt", "rep"):
            return True
        return False

    def first(node: dict) -> set[str]:
        t = node["type"]
        if t == "lit":
            return {node["value"]}
        if t == "id":
            name = node["value"]
            if name == "ws":
                return set()
            if name in first_cache:
                return first_cache[name]
            if name not in rules:
                return set()
            first_cache[name] = set()
            first_cache[name] = first(rules[name])
            return first_cache[name]
        if t == "alt":
            out: set[str] = set()
            for alt in node["alts"]:
                out |= first(alt)
            return out
        if t == "seq":
            out: set[str] = set()
            for item in node["items"]:
                out |= first(item)
                if not nullable(item):
                    break
            return out
        if t in ("opt", "rep"):
            return first(node["child"])
        return set()

    return {name: {lit for lit in first(node)} for name, node in rules.items()}


def _convert_expr(expr: str) -> str:
    expr = re.sub(r"\?\s*any non-whitespace character\s*\?", r"/[^\\s]/", expr)
    expr = re.sub(r"\"0\"\\.\\.\\.\"9\"", "\"0\"..\"9\"", expr)
    expr = expr.replace("...", "..")
    out: List[str] = []
    stack: List[str] = []
    for ch in expr:
        if ch == "{":
            out.append("(")
            stack.append("}")
        elif ch == "[":
            out.append("(")
            stack.append("]")
        elif ch == "}" and stack and stack[-1] == "}":
            stack.pop()
            out.append(")*")
        elif ch == "]" and stack and stack[-1] == "]":
            stack.pop()
            out.append(")?")
        else:
            out.append(ch)
    return "".join(out)


def _build_lark(text: str) -> str:
    rules = _collect_rules(_strip_comments(text))
    lines: List[str] = []
    for rule in rules:
        if rule.name in RULE_SKIP:
            continue
        expr = _convert_expr(rule.expr)
        lines.append(f"{rule.name}: {expr}")
    lines.append("exec_line: ws? (common | exec) ws?")
    lines.append("config_line: ws? (common | config) ws?")
    lines.append("group_line: ws? (common | group) ws?")
    lines.append("device_line: ws? (common | device) ws?")
    lines.append("test_line: ws? (common | test) ws?")
    lines.append(LEXICAL_RULES)
    lines.append(CUSTOM_RULES)
    lines.append(LARK_PREAMBLE)
    return "\n".join(lines)


def _write_grammar(grammar: str) -> None:
    OUT_GRAMMAR.write_text(
        "\n".join(
            [
                '"""',
                "NAME",
                "    bridge_cli_grammar_gen.py - Generated Lark grammar.",
                '"""',
                "",
                "GRAMMAR = r'''",
                grammar,
                "'''",
            ]
        )
        + "\n",
        encoding="ascii",
    )


def _write_constants(meta: Dict[str, object], mode_commands: Dict[str, tuple[str, ...]]) -> None:
    modes = meta["modes"]
    commands = meta["commands"]
    kinds = meta["kinds"]
    labels = meta["labels"]
    messages = meta["messages"]
    parser_meta = meta.get("parser", {})

    lines: List[str] = []
    lines.append('"""')
    lines.append("NAME")
    lines.append("    bridge_cli_constants_gen.py - Generated CLI parser constants.")
    lines.append('"""')
    lines.append("")
    lines.append("from dataclasses import dataclass")
    lines.append("")
    lines.append("@dataclass(frozen=True)")
    lines.append("class ParserSpec:")
    lines.append("    bool_true: bool")
    lines.append("    bool_false: bool")
    lines.append("    count_zero: int")
    lines.append("    count_one: int")
    lines.append("    count_two: int")
    lines.append("    count_three: int")
    lines.append("    count_four: int")
    lines.append("    count_five: int")
    lines.append("    count_six: int")
    lines.append("    idx_exec: int")
    lines.append("    idx_config: int")
    lines.append("    idx_group: int")
    lines.append("    idx_device: int")
    lines.append("    idx_test: int")
    lines.append("    modes: tuple[str, ...]")
    lines.append("    common: tuple[str, ...]")
    lines.append("    show_flags: tuple[str, ...]")
    lines.append("    show_source_robot: str")
    lines.append("    show_source_local: str")
    lines.append("    show_source_both: str")
    lines.append("    show_targets: tuple[str, ...]")
    lines.append("    show_target_config: str")
    lines.append("    show_target_runtime_state: str")
    lines.append("    show_target_tests: str")
    lines.append("    show_target_test: str")
    lines.append("    show_target_status: str")
    lines.append("    show_target_groups: str")
    lines.append("    show_target_devices: str")
    lines.append("    show_target_bindings: str")
    lines.append("    show_target_selected_device: str")
    lines.append("    show_target_device_registry: str")
    lines.append("    show_target_commands: str")
    lines.append("    show_target_help: str")
    lines.append("    show_target_device_usage: str")
    lines.append("    show_target_message_level: str")
    lines.append("    bind_kinds: tuple[str, ...]")
    lines.append("    cmd_connect: str")
    lines.append("    cmd_disconnect: str")
    lines.append("    cmd_configure: str")
    lines.append("    cmd_cfg: str")
    lines.append("    cmd_terminal: str")
    lines.append("    cmd_show: str")
    lines.append("    cmd_ls: str")
    lines.append("    cmd_group: str")
    lines.append("    cmd_no: str")
    lines.append("    cmd_profile: str")
    lines.append("    cmd_profiles: str")
    lines.append("    cmd_prof: str")
    lines.append("    cmd_selected_device: str")
    lines.append("    cmd_selected_mode: str")
    lines.append("    cmd_on: str")
    lines.append("    cmd_off: str")
    lines.append("    cmd_merge: str")
    lines.append("    cmd_import: str")
    lines.append("    cmd_config: str")
    lines.append("    cmd_export: str")
    lines.append("    cmd_export_runtime_groups: str")
    lines.append("    cmd_export_cli_script: str")
    lines.append("    cmd_save: str")
    lines.append("    cmd_save_config: str")
    lines.append("    cmd_save_local_config: str")
    lines.append("    cmd_save_profiles: str")
    lines.append("    cmd_save_unified: str")
    lines.append("    cmd_savep: str")
    lines.append("    cmd_rename: str")
    lines.append("    cmd_device: str")
    lines.append("    cmd_registry: str")
    lines.append("    cmd_set: str")
    lines.append("    cmd_write: str")
    lines.append("    cmd_bindings: str")
    lines.append("    cmd_can_mappings: str")
    lines.append("    cmd_tests: str")
    lines.append("    cmd_create: str")
    lines.append("    cmd_delete: str")
    lines.append("    cmd_type: str")
    lines.append("    cmd_input_source: str")
    lines.append("    cmd_deadband: str")
    lines.append("    cmd_duty: str")
    lines.append("    cmd_termination: str")
    lines.append("    cmd_limitswitch: str")
    lines.append("    cmd_validate: str")
    lines.append("    cmd_val: str")
    lines.append("    cmd_add: str")
    lines.append("    cmd_member: str")
    lines.append("    cmd_enable: str")
    lines.append("    cmd_disable: str")
    lines.append("    cmd_toggle: str")
    lines.append("    cmd_bind: str")
    lines.append("    cmd_run: str")
    lines.append("    cmd_test: str")
    lines.append("    cmd_members: str")
    lines.append("    cmd_binding: str")
    lines.append("    cmd_show_all: str")
    lines.append("    cmd_validate_all: str")
    lines.append("    show_target_group: str")
    lines.append("    show_target_device: str")
    lines.append("    strict_default: bool")
    lines.append("    allow_empty: bool")
    lines.append("    disallow_empty: bool")
    lines.append("    msg_unknown_mode_fmt: str")
    lines.append("    msg_unknown_cmd_fmt: str")
    lines.append("    msg_config_terminal: str")
    lines.append("    msg_show_requires: str")
    lines.append("    msg_unknown_show: str")
    lines.append("    msg_show_name: str")
    lines.append("    msg_show_too_many: str")
    lines.append("    msg_too_many_fmt: str")
    lines.append("    msg_group_name: str")
    lines.append("    msg_no_group_name: str")
    lines.append("    msg_profile_name: str")
    lines.append("    msg_selected_device: str")
    lines.append("    msg_selected_mode: str")
    lines.append("    msg_selected_mode_value: str")
    lines.append("    msg_merge_config: str")
    lines.append("    msg_import_config: str")
    lines.append("    msg_export_requires: str")
    lines.append("    msg_export_target: str")
    lines.append("    msg_save_requires: str")
    lines.append("    msg_save_target: str")
    lines.append("    msg_rename_device: str")
    lines.append("    msg_device_name: str")
    lines.append("    msg_device_set: str")
    lines.append("    msg_validate_config: str")
    lines.append("    msg_add_device: str")
    lines.append("    msg_no_device: str")
    lines.append("    msg_member: str")
    lines.append("    msg_member_action: str")
    lines.append("    msg_bind: str")
    lines.append("    msg_bind_kind: str")
    lines.append("    msg_bind_value: str")
    lines.append("    msg_no_bind: str")
    lines.append("    msg_run_test: str")
    lines.append("    msg_set: str")
    lines.append("    msg_no: str")
    lines.append("    msg_parse_error: str")
    lines.append("    msg_mode_only_fmt: str")
    lines.append("    msg_mode_name_exec: str")
    lines.append("    msg_mode_name_config: str")
    lines.append("    msg_mode_name_group: str")
    lines.append("    msg_mode_name_device: str")
    lines.append("    msg_mode_name_test: str")
    lines.append("    label_connect: str")
    lines.append("    label_configure: str")
    lines.append("    label_group: str")
    lines.append("    label_no_group: str")
    lines.append("    label_selected_device: str")
    lines.append("    label_selected_mode: str")
    lines.append("    label_merge: str")
    lines.append("    label_import: str")
    lines.append("    label_export: str")
    lines.append("    label_save: str")
    lines.append("    label_rename: str")
    lines.append("    label_device: str")
    lines.append("    label_device_set: str")
    lines.append("    label_device_delete: str")
    lines.append("    mode_exec_cmds: tuple[str, ...]")
    lines.append("    mode_config_cmds: tuple[str, ...]")
    lines.append("    mode_group_cmds: tuple[str, ...]")
    lines.append("    mode_device_cmds: tuple[str, ...]")
    lines.append("    mode_test_cmds: tuple[str, ...]")
    lines.append("    label_validate: str")
    lines.append("    label_show_members: str")
    lines.append("    label_add_device: str")
    lines.append("    label_no_device: str")
    lines.append("    label_member: str")
    lines.append("    label_bind_analog: str")
    lines.append("    label_bind: str")
    lines.append("    label_no_bind: str")
    lines.append("    label_enable: str")
    lines.append("    label_run_test: str")
    lines.append("    shlex_posix: bool")
    lines.append("    empty_str: str")
    lines.append("    space_str: str")
    lines.append("    kind_common_exit: str")
    lines.append("    kind_common_end: str")
    lines.append("    kind_common_help: str")
    lines.append("    kind_common_ping: str")
    lines.append("    kind_exec_connect: str")
    lines.append("    kind_exec_disconnect: str")
    lines.append("    kind_exec_configure_terminal: str")
    lines.append("    kind_show: str")
    lines.append("    kind_config_group: str")
    lines.append("    kind_config_no_group: str")
    lines.append("    kind_config_no_device: str")
    lines.append("    kind_config_profile: str")
    lines.append("    kind_config_selected_device: str")
    lines.append("    kind_config_selected_mode: str")
    lines.append("    kind_config_merge: str")
    lines.append("    kind_config_import: str")
    lines.append("    kind_config_export: str")
    lines.append("    kind_config_save: str")
    lines.append("    kind_config_rename_device: str")
    lines.append("    kind_config_device: str")
    lines.append("    kind_config_device_set: str")
    lines.append("    kind_config_validate: str")
    lines.append("    kind_config_bindings: str")
    lines.append("    kind_config_can_mappings: str")
    lines.append("    kind_group_show: str")
    lines.append("    kind_group_show_members: str")
    lines.append("    kind_group_show_binding: str")
    lines.append("    kind_group_add_device: str")
    lines.append("    kind_group_no_device: str")
    lines.append("    kind_group_member: str")
    lines.append("    kind_group_bind: str")
    lines.append("    kind_group_no_bind: str")
    lines.append("    kind_group_enable: str")
    lines.append("    kind_group_disable: str")
    lines.append("    kind_group_run_test: str")
    lines.append("    kind_device_show: str")
    lines.append("    kind_device_set: str")
    lines.append("    kind_device_no: str")
    lines.append("    kind_device_delete: str")
    lines.append("")
    lines.append("SPEC = ParserSpec(")
    lines.append("    bool_true=True,")
    lines.append("    bool_false=False,")
    lines.append("    count_zero=0,")
    lines.append("    count_one=1,")
    lines.append("    count_two=2,")
    lines.append("    count_three=3,")
    lines.append("    count_four=4,")
    lines.append("    count_five=5,")
    lines.append("    count_six=6,")
    lines.append("    idx_exec=0,")
    lines.append("    idx_config=1,")
    lines.append("    idx_group=2,")
    lines.append("    idx_device=3,")
    lines.append("    idx_test=4,")
    lines.append(f"    modes={tuple(modes)!r},")
    lines.append(f"    common={tuple(meta['common'])!r},")
    lines.append(f"    show_flags={tuple(meta['show_flags'])!r},")
    lines.append(f"    show_source_robot={meta['show_sources'][0]!r},")
    lines.append(f"    show_source_local={meta['show_sources'][1]!r},")
    lines.append(f"    show_source_both={meta['show_sources'][2]!r},")
    show_targets = meta["show_targets"]
    def _target(name: str) -> str:
        return show_targets[show_targets.index(name)]
    lines.append(f"    show_targets={tuple(show_targets)!r},")
    lines.append(f"    show_target_config={_target('config')!r},")
    lines.append(f"    show_target_runtime_state={_target('runtime-state')!r},")
    lines.append(f"    show_target_tests={_target('tests')!r},")
    lines.append(f"    show_target_test={_target('test')!r},")
    lines.append(f"    show_target_status={_target('status')!r},")
    lines.append(f"    show_target_groups={_target('groups')!r},")
    lines.append(f"    show_target_devices={_target('devices')!r},")
    lines.append(f"    show_target_bindings={_target('bindings')!r},")
    lines.append(f"    show_target_selected_device={_target('selected-device')!r},")
    lines.append(f"    show_target_device_registry={_target('device-registry')!r},")
    lines.append(f"    show_target_commands={_target('commands')!r},")
    lines.append(f"    show_target_help={_target('help')!r},")
    lines.append(f"    show_target_device_usage={_target(SHOW_TARGET_DEVICE_USAGE)!r},")
    lines.append(f"    show_target_message_level={_target(SHOW_TARGET_MESSAGE_LEVEL)!r},")
    lines.append(f"    bind_kinds={tuple(meta['bind_kinds'])!r},")
    lines.append(f"    cmd_connect={commands['connect']!r},")
    lines.append(f"    cmd_disconnect={commands['disconnect']!r},")
    lines.append(f"    cmd_configure={commands['configure']!r},")
    lines.append(f"    cmd_cfg={commands['cfg']!r},")
    lines.append(f"    cmd_terminal={commands['terminal']!r},")
    lines.append(f"    cmd_show={commands['show']!r},")
    lines.append(f"    cmd_ls={commands['ls']!r},")
    lines.append(f"    cmd_group={commands['group']!r},")
    lines.append(f"    cmd_no={commands['no']!r},")
    lines.append(f"    cmd_profile={commands['profile']!r},")
    lines.append(f"    cmd_profiles={commands['profiles']!r},")
    lines.append(f"    cmd_prof={commands['prof']!r},")
    lines.append(f"    cmd_selected_device={commands['selected_device']!r},")
    lines.append(f"    cmd_selected_mode={commands['selected_mode']!r},")
    lines.append(f"    cmd_on={commands['on']!r},")
    lines.append(f"    cmd_off={commands['off']!r},")
    lines.append(f"    cmd_merge={commands['merge']!r},")
    lines.append(f"    cmd_import={commands['import']!r},")
    lines.append(f"    cmd_config={commands['config']!r},")
    lines.append(f"    cmd_export={commands['export']!r},")
    lines.append(f"    cmd_export_runtime_groups={commands['export_runtime_groups']!r},")
    lines.append(f"    cmd_export_cli_script={commands['export_cli_script']!r},")
    lines.append(f"    cmd_save={commands['save']!r},")
    lines.append(f"    cmd_save_config={commands['save_config']!r},")
    lines.append(f"    cmd_save_local_config={commands['save_local_config']!r},")
    lines.append(f"    cmd_save_profiles={commands['save_profiles']!r},")
    lines.append(f"    cmd_save_unified={commands['save_unified']!r},")
    lines.append(f"    cmd_savep={commands['savep']!r},")
    lines.append(f"    cmd_push={commands['push']!r},")
    lines.append(f"    cmd_activate={commands['activate']!r},")
    lines.append(f"    cmd_rename={commands['rename']!r},")
    lines.append(f"    cmd_device={commands['device']!r},")
    lines.append(f"    cmd_registry={commands['registry']!r},")
    lines.append(f"    cmd_set={commands['set']!r},")
    lines.append(f"    cmd_write={commands['write']!r},")
    lines.append(f"    cmd_bindings={commands['bindings']!r},")
    lines.append(f"    cmd_can_mappings={commands['can_mappings']!r},")
    lines.append(f"    cmd_tests={commands['tests']!r},")
    lines.append(f"    cmd_create={commands['create']!r},")
    lines.append(f"    cmd_delete={commands['delete']!r},")
    lines.append(f"    cmd_type={commands['type']!r},")
    lines.append(f"    cmd_input_source={commands['inputSource']!r},")
    lines.append(f"    cmd_deadband={commands['deadband']!r},")
    lines.append(f"    cmd_duty={commands['duty']!r},")
    lines.append(f"    cmd_termination={commands['termination']!r},")
    lines.append(f"    cmd_limitswitch={commands['limitswitch']!r},")
    lines.append(f"    cmd_validate={commands['validate']!r},")
    lines.append(f"    cmd_val={commands['val']!r},")
    lines.append(f"    cmd_add={commands['add']!r},")
    lines.append(f"    cmd_member={commands['member']!r},")
    lines.append(f"    cmd_enable={commands['enable']!r},")
    lines.append(f"    cmd_disable={commands['disable']!r},")
    lines.append(f"    cmd_toggle={commands['toggle']!r},")
    lines.append(f"    cmd_bind={commands['bind']!r},")
    lines.append(f"    cmd_run={commands['run']!r},")
    lines.append(f"    cmd_test={commands['test']!r},")
    lines.append(f"    cmd_members={commands['members']!r},")
    lines.append(f"    cmd_binding={commands['binding']!r},")
    lines.append(f"    cmd_show_all={commands['show_all']!r},")
    lines.append(f"    cmd_validate_all={commands['validate_all']!r},")
    lines.append(f"    show_target_group={_target('group')!r},")
    lines.append(f"    show_target_device={_target('device')!r},")
    lines.append(f"    strict_default={parser_meta.get('strict_default', False)!r},")
    lines.append("    allow_empty=True,")
    lines.append("    disallow_empty=False,")
    lines.append(f"    msg_unknown_mode_fmt={messages['unknown_mode']!r},")
    lines.append(f"    msg_unknown_cmd_fmt={messages['unknown_cmd']!r},")
    lines.append(f"    msg_config_terminal={messages['config_terminal']!r},")
    lines.append(f"    msg_show_requires={messages['show_requires']!r},")
    lines.append(f"    msg_unknown_show={messages['unknown_show']!r},")
    lines.append(f"    msg_show_name={messages['show_name']!r},")
    lines.append(f"    msg_show_too_many={messages['show_too_many']!r},")
    lines.append(f"    msg_too_many_fmt={messages['too_many']!r},")
    lines.append(f"    msg_group_name={messages['group_name']!r},")
    lines.append(f"    msg_no_group_name={messages['no_group_name']!r},")
    lines.append(f"    msg_profile_name={messages['profile_name']!r},")
    lines.append(f"    msg_selected_device={messages['selected_device']!r},")
    lines.append(f"    msg_selected_mode={messages['selected_mode']!r},")
    lines.append(f"    msg_selected_mode_value={messages['selected_mode_value']!r},")
    lines.append(f"    msg_merge_config={messages['merge_config']!r},")
    lines.append(f"    msg_import_config={messages['import_config']!r},")
    lines.append(f"    msg_export_requires={messages['export_requires']!r},")
    lines.append(f"    msg_export_target={messages['export_target']!r},")
    lines.append(f"    msg_save_requires={messages['save_requires']!r},")
    lines.append(f"    msg_save_target={messages['save_target']!r},")
    lines.append(f"    msg_rename_device={messages['rename_device']!r},")
    lines.append(f"    msg_device_name={messages['device_name']!r},")
    lines.append(f"    msg_device_set={messages['device_set']!r},")
    lines.append(f"    msg_validate_config={messages['validate_config']!r},")
    lines.append(f"    msg_add_device={messages['add_device']!r},")
    lines.append(f"    msg_no_device={messages['no_device']!r},")
    lines.append(f"    msg_member={messages['member']!r},")
    lines.append(f"    msg_member_action={messages['member_action']!r},")
    lines.append(f"    msg_bind={messages['bind']!r},")
    lines.append(f"    msg_bind_kind={messages['bind_kind']!r},")
    lines.append(f"    msg_bind_value={messages['bind_value']!r},")
    lines.append(f"    msg_no_bind={messages['no_bind']!r},")
    lines.append(f"    msg_run_test={messages['run_test']!r},")
    lines.append(f"    msg_set={messages['set']!r},")
    lines.append(f"    msg_no={messages['no']!r},")
    lines.append(f"    msg_parse_error={messages['parse_error']!r},")
    lines.append(f"    msg_mode_only_fmt={messages['mode_only_fmt']!r},")
    lines.append(f"    msg_mode_name_exec={messages['mode_name_exec']!r},")
    lines.append(f"    msg_mode_name_config={messages['mode_name_config']!r},")
    lines.append(f"    msg_mode_name_group={messages['mode_name_group']!r},")
    lines.append(f"    msg_mode_name_device={messages['mode_name_device']!r},")
    lines.append(f"    msg_mode_name_test={messages['mode_name_test']!r},")
    lines.append(f"    label_connect={labels['connect']!r},")
    lines.append(f"    label_configure={labels['configure']!r},")
    lines.append(f"    label_group={labels['group']!r},")
    lines.append(f"    label_no_group={labels['no_group']!r},")
    lines.append(f"    label_selected_device={labels['selected_device']!r},")
    lines.append(f"    label_selected_mode={labels['selected_mode']!r},")
    lines.append(f"    label_merge={labels['merge']!r},")
    lines.append(f"    label_import={labels['import']!r},")
    lines.append(f"    label_export={labels['export']!r},")
    lines.append(f"    label_save={labels['save']!r},")
    lines.append(f"    label_rename={labels['rename']!r},")
    lines.append(f"    label_device={labels['device']!r},")
    lines.append(f"    label_device_set={labels['device_set']!r},")
    lines.append(f"    label_device_delete={labels['device_delete']!r},")
    lines.append(f"    mode_exec_cmds={mode_commands['exec']!r},")
    lines.append(f"    mode_config_cmds={mode_commands['config']!r},")
    lines.append(f"    mode_group_cmds={mode_commands['group']!r},")
    lines.append(f"    mode_device_cmds={mode_commands['device']!r},")
    lines.append(f"    mode_test_cmds={mode_commands['test']!r},")
    lines.append(f"    label_validate={labels['validate']!r},")
    lines.append(f"    label_show_members={labels['show_members']!r},")
    lines.append(f"    label_add_device={labels['add_device']!r},")
    lines.append(f"    label_no_device={labels['no_device']!r},")
    lines.append(f"    label_member={labels['member']!r},")
    lines.append(f"    label_bind_analog={labels['bind_analog']!r},")
    lines.append(f"    label_bind={labels['bind']!r},")
    lines.append(f"    label_no_bind={labels['no_bind']!r},")
    lines.append(f"    label_enable={labels['enable']!r},")
    lines.append(f"    label_run_test={labels['run_test']!r},")
    lines.append("    shlex_posix=True,")
    lines.append("    empty_str=\"\",")
    lines.append("    space_str=\" \",")
    lines.append(f"    kind_common_exit={kinds['common_exit']!r},")
    lines.append(f"    kind_common_end={kinds['common_end']!r},")
    lines.append(f"    kind_common_help={kinds['common_help']!r},")
    lines.append(f"    kind_common_ping={kinds['common_ping']!r},")
    lines.append(f"    kind_exec_connect={kinds['exec_connect']!r},")
    lines.append(f"    kind_exec_disconnect={kinds['exec_disconnect']!r},")
    lines.append(f"    kind_exec_configure_terminal={kinds['exec_configure_terminal']!r},")
    lines.append(f"    kind_show={kinds['show']!r},")
    lines.append(f"    kind_config_group={kinds['config_group']!r},")
    lines.append(f"    kind_config_no_group={kinds['config_no_group']!r},")
    lines.append(f"    kind_config_no_device={kinds['config_no_device']!r},")
    lines.append(f"    kind_config_profile={kinds['config_profile']!r},")
    lines.append(f"    kind_config_selected_device={kinds['config_selected_device']!r},")
    lines.append(f"    kind_config_selected_mode={kinds['config_selected_mode']!r},")
    lines.append(f"    kind_config_merge={kinds['config_merge']!r},")
    lines.append(f"    kind_config_import={kinds['config_import']!r},")
    lines.append(f"    kind_config_export={kinds['config_export']!r},")
    lines.append(f"    kind_config_save={kinds['config_save']!r},")
    lines.append(f"    kind_config_push={kinds['config_push']!r},")
    lines.append(f"    kind_config_rename_device={kinds['config_rename_device']!r},")
    lines.append(f"    kind_config_device={kinds['config_device']!r},")
    lines.append(f"    kind_config_device_set={kinds['config_device_set']!r},")
    lines.append(f"    kind_config_validate={kinds['config_validate']!r},")
    lines.append(f"    kind_config_bindings={kinds['config_bindings']!r},")
    lines.append(f"    kind_config_can_mappings={kinds['config_can_mappings']!r},")
    lines.append(f"    kind_group_show={kinds['group_show']!r},")
    lines.append(f"    kind_group_show_members={kinds['group_show_members']!r},")
    lines.append(f"    kind_group_show_binding={kinds['group_show_binding']!r},")
    lines.append(f"    kind_group_add_device={kinds['group_add_device']!r},")
    lines.append(f"    kind_group_no_device={kinds['group_no_device']!r},")
    lines.append(f"    kind_group_member={kinds['group_member']!r},")
    lines.append(f"    kind_group_bind={kinds['group_bind']!r},")
    lines.append(f"    kind_group_no_bind={kinds['group_no_bind']!r},")
    lines.append(f"    kind_group_enable={kinds['group_enable']!r},")
    lines.append(f"    kind_group_disable={kinds['group_disable']!r},")
    lines.append(f"    kind_group_run_test={kinds['group_run_test']!r},")
    lines.append(f"    kind_device_show={kinds['device_show']!r},")
    lines.append(f"    kind_device_set={kinds['device_set']!r},")
    lines.append(f"    kind_device_no={kinds['device_no']!r},")
    lines.append(f"    kind_device_delete={kinds['device_delete']!r},")
    lines.append(")")

    OUT_CONST.write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    ebnf = EBNF_PATH.read_text(encoding="ascii")
    meta = json.loads(META_PATH.read_text(encoding="ascii"))
    grammar = _build_lark(ebnf)
    _write_grammar(grammar)
    rules = _collect_rules(_strip_comments(ebnf))
    rule_asts = {rule.name: _build_rule_ast(rule.expr) for rule in rules}
    first_sets = _compute_first_sets(rule_asts)
    common = {lit.lower() for lit in first_sets.get("common", set())}
    mode_commands: Dict[str, tuple[str, ...]] = {}
    for mode in ("exec", "config", "group", "device", "test"):
        literals = {lit.lower() for lit in first_sets.get(mode, set())}
        literals = {lit for lit in literals if lit and lit not in common}
        mode_commands[mode] = tuple(sorted(literals))
    _write_constants(meta, mode_commands)


if __name__ == "__main__":
    main()
