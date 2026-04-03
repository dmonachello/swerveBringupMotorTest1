from __future__ import annotations

"""
NAME
    cli_grammar_model.py - EBNF grammar model for CLI parsing and completion.

SYNOPSIS
    model = CliGrammarModel.from_ebnf(Path("tools/can_nt/bridge_cli_ebnf.txt"))
    ok, expected = model.validate(tokens, mode="exec")

DESCRIPTION
    Parses the CLI EBNF into a grammar model used for parsing validation
    and completion. The model is token-based and ignores explicit whitespace
    rules so it can work directly with shlex tokenization.
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

TOKEN_KIND_IDENT = "ident"
TOKEN_KIND_STRING = "string"
TOKEN_KIND_SYMBOL = "symbol"

SYMBOL_ASSIGN = "="
SYMBOL_SEMI = ";"
SYMBOL_OR = "|"
SYMBOL_LPAREN = "("
SYMBOL_RPAREN = ")"
SYMBOL_LBRACK = "["
SYMBOL_RBRACK = "]"
SYMBOL_LBRACE = "{"
SYMBOL_RBRACE = "}"

COMMENT_START = "(*"
COMMENT_END = "*)"

MODE_EXEC = "exec"
MODE_CONFIG = "config"
MODE_GROUP = "group"
MODE_DEVICE = "device"
MODE_TEST = "test"

RULE_COMMON = "common"
RULE_EXEC = "exec"
RULE_CONFIG = "config"
RULE_GROUP = "group"
RULE_DEVICE = "device"
RULE_TEST = "test"
RULE_WS = "ws"
RULE_NUMBER = "number"
RULE_VALUE = "value"

PLACEHOLDER_NAME = "<name>"
PLACEHOLDER_PATH = "<path>"
PLACEHOLDER_NUMBER = "<number>"
PLACEHOLDER_VALUE = "<value>"
PLACEHOLDER_TEXT = "<text>"
PLACEHOLDER_INPUT = "<input>"
PLACEHOLDER_FIELD = "<field>"

RULE_NAME = "name"
RULE_PATH = "path"
RULE_VALUE_OR_TEXT = "value_or_text"
RULE_VALUE_TEXT = "value_text"
RULE_INPUT = "input"
RULE_FIELD = "field"
RULE_TOKEN = "token"
RULE_TOKEN_CHAR = "token_char"
RULE_DIGIT = "digit"

PLACEHOLDER_RULES = {
    RULE_NAME: PLACEHOLDER_NAME,
    RULE_PATH: PLACEHOLDER_PATH,
    RULE_NUMBER: PLACEHOLDER_NUMBER,
    RULE_VALUE: PLACEHOLDER_VALUE,
    RULE_VALUE_OR_TEXT: PLACEHOLDER_VALUE,
    RULE_VALUE_TEXT: PLACEHOLDER_TEXT,
    RULE_INPUT: PLACEHOLDER_INPUT,
    RULE_FIELD: PLACEHOLDER_FIELD,
    RULE_TOKEN: PLACEHOLDER_TEXT,
}

NUMBER_RE = re.compile(r"^[+-]?\d+(\.\d+)?$")

INDEX_ZERO = 0
INDEX_ONE = 1
INDEX_TWO = 2

CHAR_DOUBLE_QUOTE = "\""
CHAR_UNDERSCORE = "_"
CHAR_DASH = "-"
CHAR_BACKSLASH = "\\"
CHAR_FORWARD_SLASH = "/"
CHAR_COLON = ":"

EMPTY_STRING = ""

KEY_RULES = "rules"
KEY_TERM = "terminals"
KEY_PLACEHOLDERS = "placeholders"
KEY_MODES = "modes"
KEY_MODE = "mode"
KEY_EXPECTED = "expected"
KEY_RULE_NAME = "name"
KEY_RULE_EXPR = "expr"
KEY_EXPR_TYPE = "type"
KEY_EXPR_VALUE = "value"
KEY_EXPR_CHILDREN = "children"
KEY_DOT = "dot"

DOT_GRAPH = "digraph"
DOT_RANKDIR = "rankdir"
DOT_RANKDIR_LR = "LR"
DOT_NODE = "node"
DOT_EDGE = "edge"
DOT_LABEL = "label"
DOT_SHAPE = "shape"
DOT_SHAPE_BOX = "box"
DOT_SHAPE_OVAL = "oval"
DOT_SHAPE_DIAMOND = "diamond"
DOT_STYLE = "style"
DOT_STYLE_DASHED = "dashed"
DOT_SEPARATOR = " -> "
DOT_LINE_END = ";"
DOT_LBRACE = "{"
DOT_RBRACE = "}"
DOT_NEWLINE = "\n"
DOT_QUOTE = "\""
DOT_SPACE = " "
DOT_COMMA_SPACE = ", "
DOT_EQUALS = "="
DOT_ATTR_OPEN = " ["
DOT_ATTR_CLOSE = "]"
DOT_ID_SEP = "_"
DOT_PREFIX_RULE = "rule"
DOT_PREFIX_EXPR = "expr"
DOT_LABEL_LITERAL = "literal"
DOT_LABEL_PLACEHOLDER = "placeholder"
DOT_LABEL_REF = "ref"
DOT_LABEL_SEQUENCE = "sequence"
DOT_LABEL_CHOICE = "choice"
DOT_LABEL_REPEAT = "repeat"
DOT_LABEL_EMPTY = "empty"
DOT_LABEL_FAIL = "fail"
DOT_LABEL_UNKNOWN = "unknown"
DOT_LABEL_SEPARATOR = ": "

EXPR_TYPE_LITERAL = "literal"
EXPR_TYPE_PLACEHOLDER = "placeholder"
EXPR_TYPE_REF = "ref"
EXPR_TYPE_SEQUENCE = "sequence"
EXPR_TYPE_CHOICE = "choice"
EXPR_TYPE_REPEAT = "repeat"
EXPR_TYPE_EMPTY = "empty"
EXPR_TYPE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class EbnfToken:
    kind: str
    value: str
    pos: int


class Expr:
    pass


@dataclass(frozen=True)
class Empty(Expr):
    pass


@dataclass(frozen=True)
class Fail(Expr):
    pass


@dataclass(frozen=True)
class Literal(Expr):
    value: str


@dataclass(frozen=True)
class Placeholder(Expr):
    name: str


@dataclass(frozen=True)
class Ref(Expr):
    name: str


@dataclass(frozen=True)
class Sequence(Expr):
    parts: Tuple[Expr, ...]


@dataclass(frozen=True)
class Choice(Expr):
    options: Tuple[Expr, ...]


@dataclass(frozen=True)
class Repeat(Expr):
    expr: Expr


class CliGrammarModel:
    """
    NAME
        CliGrammarModel - Token-level grammar model for CLI parsing.
    """

    def __init__(self, rules: Dict[str, Expr]) -> None:
        self._rules = rules
        self._expanded: Dict[str, Expr] = {}
        self._first_cache: Dict[Expr, Tuple[Set[Expr], bool]] = {}
        self._derive_cache: Dict[Tuple[Expr, str], Expr] = {}

    @classmethod
    def from_ebnf(cls, path: Path) -> "CliGrammarModel":
        text = path.read_text(encoding="utf-8")
        tokens = _lex_ebnf(text)
        rules = _parse_rules(tokens)
        return cls(rules)

    def validate(self, tokens: List[str], mode: str) -> Tuple[bool, Set[Expr]]:
        """
        NAME
            validate - Validate tokens against the grammar.

        RETURNS
            ok - True if tokens match.
            expected - Set of expected tokens when not ok.
        """
        expr = self._mode_expr(mode)
        current = expr
        expected: Set[Expr] = set()
        for token in tokens:
            expected = self._first(current)[0]
            current = self._derive(current, token, expected)
            if isinstance(current, Fail):
                return False, expected
        if self._nullable(current):
            return True, set()
        expected = self._first(current)[0]
        return False, expected

    def expected_next(self, tokens: List[str], mode: str) -> Set[Expr]:
        """
        NAME
            expected_next - Return expected next tokens for completion.
        """
        expr = self._mode_expr(mode)
        current = expr
        for token in tokens:
            expected = self._first(current)[0]
            current = self._derive(current, token, expected)
            if isinstance(current, Fail):
                return set()
        expected = self._first(current)[0]
        return expected

    def mode_keywords(self, mode: str) -> List[str]:
        """
        NAME
            mode_keywords - Return top-level keywords for a mode.
        """
        expr = self._mode_expr(mode)
        expected, _nullable = self._first(expr)
        keywords: List[str] = []
        for entry in sorted(expected, key=lambda item: _expr_key(item)):
            if isinstance(entry, Literal):
                keywords.append(entry.value)
        return keywords

    def expected_to_suggestions(self, expected: Iterable[Expr]) -> List[str]:
        """
        NAME
            expected_to_suggestions - Convert expected tokens to completion strings.
        """
        suggestions: List[str] = []
        for item in sorted(expected, key=lambda entry: _expr_key(entry)):
            if isinstance(item, Literal):
                suggestions.append(item.value)
            elif isinstance(item, Placeholder):
                placeholder = PLACEHOLDER_RULES.get(item.name, PLACEHOLDER_NAME)
                if placeholder not in suggestions:
                    suggestions.append(placeholder)
        return suggestions

    def dump(self, mode: str) -> Dict[str, object]:
        """
        NAME
            dump - Return a structured grammar dump for a mode.
        """
        expected = self.expected_next([], mode)
        terminals = sorted({item.value for item in expected if isinstance(item, Literal)})
        placeholders = sorted(
            {
                PLACEHOLDER_RULES.get(item.name, PLACEHOLDER_NAME)
                for item in expected
                if isinstance(item, Placeholder)
            }
        )
        rules = [
            {
                KEY_RULE_NAME: name,
                KEY_RULE_EXPR: _expr_to_dict(expr),
            }
            for name, expr in sorted(self._rules.items())
        ]
        return {
            KEY_MODE: mode,
            KEY_EXPECTED: self.expected_to_suggestions(expected),
            KEY_TERM: terminals,
            KEY_PLACEHOLDERS: placeholders,
            KEY_RULES: rules,
        }

    def dump_dot(self, mode: str) -> str:
        """
        NAME
            dump_dot - Return Graphviz DOT for the grammar model.
        """
        expr_cache: Dict[Expr, str] = {}
        lines: List[str] = []
        lines.append(DOT_GRAPH + DOT_SPACE + DOT_LBRACE)
        lines.append(DOT_RANKDIR + DOT_EQUALS + DOT_RANKDIR_LR + DOT_LINE_END)
        lines.append(
            DOT_NODE
            + DOT_ATTR_OPEN
            + DOT_SHAPE
            + DOT_EQUALS
            + DOT_SHAPE_BOX
            + DOT_ATTR_CLOSE
            + DOT_LINE_END
        )
        for name in sorted(self._rules.keys()):
            rule_id = _dot_id(DOT_PREFIX_RULE, name)
            lines.append(_dot_node(rule_id, name, DOT_SHAPE_BOX))
            expr = self._rules[name]
            expr_id = self._dot_expr(expr, expr_cache, lines)
            lines.append(_dot_edge(rule_id, expr_id))
        lines.append(DOT_RBRACE)
        return DOT_NEWLINE.join(lines)

    def _dot_expr(self, expr: Expr, cache: Dict[Expr, str], lines: List[str]) -> str:
        if expr in cache:
            return cache[expr]
        node_id = _dot_id(DOT_PREFIX_EXPR, str(len(cache)))
        cache[expr] = node_id
        label = _expr_label(expr)
        shape = _expr_shape(expr)
        lines.append(_dot_node(node_id, label, shape))
        for child in _expr_children(expr):
            child_id = self._dot_expr(child, cache, lines)
            lines.append(_dot_edge(node_id, child_id))
        return node_id

    def _mode_expr(self, mode: str) -> Expr:
        if mode == MODE_CONFIG:
            return self._choice_of(RULE_COMMON, RULE_CONFIG)
        if mode == MODE_GROUP:
            return self._choice_of(RULE_COMMON, RULE_GROUP)
        if mode == MODE_DEVICE:
            return self._choice_of(RULE_COMMON, RULE_DEVICE)
        if mode == MODE_TEST:
            return self._choice_of(RULE_COMMON, RULE_TEST)
        return self._choice_of(RULE_COMMON, RULE_EXEC)

    def _choice_of(self, left: str, right: str) -> Expr:
        return Choice((self._expand(left), self._expand(right)))

    def _expand(self, name: str) -> Expr:
        if name in self._expanded:
            return self._expanded[name]
        if name in PLACEHOLDER_RULES or name in LEXICAL_RULES:
            expr = Placeholder(name)
        else:
            expr = self._rules.get(name)
            if expr is None:
                expr = Placeholder(name)
        expr = _strip_ws(expr)
        self._expanded[name] = expr
        return expr

    def _first(self, expr: Expr) -> Tuple[Set[Expr], bool]:
        cached = self._first_cache.get(expr)
        if cached is not None:
            return cached
        if isinstance(expr, Empty):
            result = (set(), True)
        elif isinstance(expr, Fail):
            result = (set(), False)
        elif isinstance(expr, Literal):
            result = ({expr}, False)
        elif isinstance(expr, Placeholder):
            result = ({expr}, False)
        elif isinstance(expr, Ref):
            result = self._first(self._expand(expr.name))
        elif isinstance(expr, Choice):
            items: Set[Expr] = set()
            nullable = False
            for option in expr.options:
                first_set, can_empty = self._first(option)
                items |= first_set
                nullable = nullable or can_empty
            result = (items, nullable)
        elif isinstance(expr, Sequence):
            items: Set[Expr] = set()
            nullable = True
            for part in expr.parts:
                first_set, can_empty = self._first(part)
                items |= first_set
                if not can_empty:
                    nullable = False
                    break
            result = (items, nullable)
        elif isinstance(expr, Repeat):
            first_set, _ = self._first(expr.expr)
            result = (first_set, True)
        else:
            result = (set(), False)
        self._first_cache[expr] = result
        return result

    def _nullable(self, expr: Expr) -> bool:
        return self._first(expr)[1]

    def _derive(self, expr: Expr, token: str, expected: Set[Expr]) -> Expr:
        key = (expr, token)
        cached = self._derive_cache.get(key)
        if cached is not None:
            return cached
        if isinstance(expr, Empty):
            result = Fail()
        elif isinstance(expr, Fail):
            result = expr
        elif isinstance(expr, Literal):
            if _token_matches_literal(token, expr.value, expected):
                result = Empty()
            else:
                result = Fail()
        elif isinstance(expr, Placeholder):
            if _token_matches_placeholder(token, expr.name):
                result = Empty()
            else:
                result = Fail()
        elif isinstance(expr, Ref):
            result = self._derive(self._expand(expr.name), token, expected)
        elif isinstance(expr, Choice):
            derived = tuple(
                part for part in (self._derive(opt, token, expected) for opt in expr.options) if not isinstance(part, Fail)
            )
            if not derived:
                result = Fail()
            elif len(derived) == 1:
                result = derived[0]
            else:
                result = Choice(derived)
        elif isinstance(expr, Sequence):
            if not expr.parts:
                result = Fail()
            else:
                first, rest = expr.parts[0], expr.parts[1:]
                first_derived = self._derive(first, token, expected)
                parts: List[Expr] = []
                if not isinstance(first_derived, Fail):
                    parts.append(_sequence(first_derived, rest))
                if self._nullable(first):
                    rest_expr = _sequence(Empty(), rest)
                    rest_derived = self._derive(rest_expr, token, expected)
                    if not isinstance(rest_derived, Fail):
                        parts.append(rest_derived)
                if not parts:
                    result = Fail()
                elif len(parts) == 1:
                    result = parts[0]
                else:
                    result = Choice(tuple(parts))
        elif isinstance(expr, Repeat):
            derived = self._derive(expr.expr, token, expected)
            if isinstance(derived, Fail):
                result = Fail()
            else:
                result = _sequence(derived, (expr,))
        else:
            result = Fail()
        self._derive_cache[key] = result
        return result


def _sequence(first: Expr, rest: Iterable[Expr]) -> Expr:
    parts: List[Expr] = []
    if isinstance(first, Sequence):
        parts.extend(first.parts)
    else:
        parts.append(first)
    for part in rest:
        if isinstance(part, Sequence):
            parts.extend(part.parts)
        else:
            parts.append(part)
    parts = [p for p in parts if not isinstance(p, Empty)]
    if not parts:
        return Empty()
    if len(parts) == 1:
        return parts[0]
    return Sequence(tuple(parts))


def _token_matches_literal(token: str, literal: str, expected: Set[Expr]) -> bool:
    token_lower = token.lower()
    literal_lower = literal.lower()
    if token_lower == literal_lower:
        return True
    if token.startswith(CHAR_DOUBLE_QUOTE):
        return False
    candidates = [
        item.value.lower()
        for item in expected
        if isinstance(item, Literal)
    ]
    matches = [value for value in candidates if value.startswith(token_lower)]
    if len(matches) == 1 and matches[0] == literal_lower:
        return True
    return False


def _token_matches_placeholder(token: str, name: str) -> bool:
    if name in (RULE_NUMBER, RULE_VALUE):
        return NUMBER_RE.match(token) is not None
    if name == RULE_WS:
        return False
    return True


def _strip_ws(expr: Expr) -> Expr:
    if isinstance(expr, Ref) and expr.name == RULE_WS:
        return Empty()
    if isinstance(expr, Sequence):
        parts = [_strip_ws(part) for part in expr.parts]
        return _sequence(Empty(), parts)
    if isinstance(expr, Choice):
        return Choice(tuple(_strip_ws(opt) for opt in expr.options))
    if isinstance(expr, Repeat):
        return Repeat(_strip_ws(expr.expr))
    return expr


def _expr_key(expr: Expr) -> str:
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, Placeholder):
        return expr.name
    return str(type(expr))


def _expr_to_dict(expr: Expr) -> Dict[str, object]:
    if isinstance(expr, Literal):
        return {KEY_EXPR_TYPE: EXPR_TYPE_LITERAL, KEY_EXPR_VALUE: expr.value}
    if isinstance(expr, Placeholder):
        return {KEY_EXPR_TYPE: EXPR_TYPE_PLACEHOLDER, KEY_EXPR_VALUE: expr.name}
    if isinstance(expr, Ref):
        return {KEY_EXPR_TYPE: EXPR_TYPE_REF, KEY_EXPR_VALUE: expr.name}
    if isinstance(expr, Sequence):
        return {
            KEY_EXPR_TYPE: EXPR_TYPE_SEQUENCE,
            KEY_EXPR_CHILDREN: [_expr_to_dict(child) for child in expr.parts],
        }
    if isinstance(expr, Choice):
        return {
            KEY_EXPR_TYPE: EXPR_TYPE_CHOICE,
            KEY_EXPR_CHILDREN: [_expr_to_dict(child) for child in expr.options],
        }
    if isinstance(expr, Repeat):
        return {KEY_EXPR_TYPE: EXPR_TYPE_REPEAT, KEY_EXPR_CHILDREN: [_expr_to_dict(expr.expr)]}
    if isinstance(expr, Empty):
        return {KEY_EXPR_TYPE: EXPR_TYPE_EMPTY}
    return {KEY_EXPR_TYPE: EXPR_TYPE_UNKNOWN}


def _dot_id(prefix: str, value: str) -> str:
    return prefix + DOT_ID_SEP + _dot_escape(value)


def _dot_escape(value: str) -> str:
    return value.replace(DOT_QUOTE, "")


def _dot_node(node_id: str, label: str, shape: str) -> str:
    return (
        DOT_QUOTE
        + node_id
        + DOT_QUOTE
        + DOT_ATTR_OPEN
        + DOT_LABEL
        + DOT_EQUALS
        + DOT_QUOTE
        + _dot_escape(label)
        + DOT_QUOTE
        + DOT_COMMA_SPACE
        + DOT_SHAPE
        + DOT_EQUALS
        + shape
        + DOT_ATTR_CLOSE
        + DOT_LINE_END
    )


def _dot_edge(source: str, target: str) -> str:
    return DOT_QUOTE + source + DOT_QUOTE + DOT_SEPARATOR + DOT_QUOTE + target + DOT_QUOTE + DOT_LINE_END


def _expr_label(expr: Expr) -> str:
    if isinstance(expr, Literal):
        return DOT_LABEL_LITERAL + DOT_LABEL_SEPARATOR + expr.value
    if isinstance(expr, Placeholder):
        return DOT_LABEL_PLACEHOLDER + DOT_LABEL_SEPARATOR + expr.name
    if isinstance(expr, Ref):
        return DOT_LABEL_REF + DOT_LABEL_SEPARATOR + expr.name
    if isinstance(expr, Sequence):
        return DOT_LABEL_SEQUENCE
    if isinstance(expr, Choice):
        return DOT_LABEL_CHOICE
    if isinstance(expr, Repeat):
        return DOT_LABEL_REPEAT
    if isinstance(expr, Empty):
        return DOT_LABEL_EMPTY
    if isinstance(expr, Fail):
        return DOT_LABEL_FAIL
    return DOT_LABEL_UNKNOWN


def _expr_shape(expr: Expr) -> str:
    if isinstance(expr, Choice):
        return DOT_SHAPE_DIAMOND
    if isinstance(expr, Literal) or isinstance(expr, Placeholder):
        return DOT_SHAPE_BOX
    return DOT_SHAPE_OVAL


def _expr_children(expr: Expr) -> List[Expr]:
    if isinstance(expr, Sequence):
        return list(expr.parts)
    if isinstance(expr, Choice):
        return list(expr.options)
    if isinstance(expr, Repeat):
        return [expr.expr]
    if isinstance(expr, Ref):
        return [expr]
    return []


def _lex_ebnf(text: str) -> List[EbnfToken]:
    tokens: List[EbnfToken] = []
    i = INDEX_ZERO
    length = len(text)
    while i < length:
        if text.startswith(COMMENT_START, i):
            end = text.find(COMMENT_END, i + len(COMMENT_START))
            if end == -1:
                break
            i = end + len(COMMENT_END)
            continue
        ch = text[i]
        if ch.isspace():
            i += INDEX_ONE
            continue
        if ch == CHAR_DOUBLE_QUOTE:
            j = i + INDEX_ONE
            while j < length and text[j] != CHAR_DOUBLE_QUOTE:
                j += INDEX_ONE
            value = text[i + INDEX_ONE : j]
            tokens.append(EbnfToken(TOKEN_KIND_STRING, value, i))
            i = j + INDEX_ONE
            continue
        if ch.isalpha() or ch == CHAR_UNDERSCORE:
            j = i + INDEX_ONE
            while j < length and (text[j].isalnum() or text[j] in (CHAR_UNDERSCORE, CHAR_DASH)):
                j += INDEX_ONE
            value = text[i:j]
            tokens.append(EbnfToken(TOKEN_KIND_IDENT, value, i))
            i = j
            continue
        if ch in (SYMBOL_ASSIGN, SYMBOL_SEMI, SYMBOL_OR, SYMBOL_LPAREN, SYMBOL_RPAREN, SYMBOL_LBRACK, SYMBOL_RBRACK, SYMBOL_LBRACE, SYMBOL_RBRACE):
            tokens.append(EbnfToken(TOKEN_KIND_SYMBOL, ch, i))
            i += INDEX_ONE
            continue
        i += INDEX_ONE
    return tokens


def _parse_rules(tokens: List[EbnfToken]) -> Dict[str, Expr]:
    rules: Dict[str, Expr] = {}
    index = INDEX_ZERO
    count = len(tokens)
    while index < count:
        token = tokens[index]
        if token.kind != TOKEN_KIND_IDENT:
            index += INDEX_ONE
            continue
        name = token.value
        index += INDEX_ONE
        if index >= count or tokens[index].value != SYMBOL_ASSIGN:
            continue
        index += INDEX_ONE
        expr, index = _parse_expr(tokens, index)
        rules[name] = expr
        if index < count and tokens[index].value == SYMBOL_SEMI:
            index += INDEX_ONE
    return rules


def _parse_expr(tokens: List[EbnfToken], index: int) -> Tuple[Expr, int]:
    term, index = _parse_term(tokens, index)
    options = [term]
    while index < len(tokens) and tokens[index].value == SYMBOL_OR:
        index += INDEX_ONE
        term, index = _parse_term(tokens, index)
        options.append(term)
    if len(options) == 1:
        return options[0], index
    return Choice(tuple(options)), index


def _parse_term(tokens: List[EbnfToken], index: int) -> Tuple[Expr, int]:
    parts: List[Expr] = []
    while index < len(tokens):
        tok = tokens[index]
        if tok.kind == TOKEN_KIND_SYMBOL and tok.value in (SYMBOL_OR, SYMBOL_SEMI, SYMBOL_RPAREN, SYMBOL_RBRACK, SYMBOL_RBRACE):
            break
        factor, index = _parse_factor(tokens, index)
        if factor is not None:
            parts.append(factor)
    if not parts:
        return Empty(), index
    if len(parts) == 1:
        return parts[0], index
    return Sequence(tuple(parts)), index


def _parse_factor(tokens: List[EbnfToken], index: int) -> Tuple[Optional[Expr], int]:
    tok = tokens[index]
    if tok.kind == TOKEN_KIND_IDENT:
        index += INDEX_ONE
        return Ref(tok.value), index
    if tok.kind == TOKEN_KIND_STRING:
        index += INDEX_ONE
        return Literal(tok.value), index
    if tok.kind == TOKEN_KIND_SYMBOL:
        if tok.value == SYMBOL_LPAREN:
            index += INDEX_ONE
            expr, index = _parse_expr(tokens, index)
            if tokens[index].value == SYMBOL_RPAREN:
                index += INDEX_ONE
            return expr, index
        if tok.value == SYMBOL_LBRACK:
            index += INDEX_ONE
            expr, index = _parse_expr(tokens, index)
            if tokens[index].value == SYMBOL_RBRACK:
                index += INDEX_ONE
            return Choice((Empty(), expr)), index
        if tok.value == SYMBOL_LBRACE:
            index += INDEX_ONE
            expr, index = _parse_expr(tokens, index)
            if tokens[index].value == SYMBOL_RBRACE:
                index += INDEX_ONE
            return Repeat(expr), index
    return None, index + INDEX_ONE
LEXICAL_RULES = {RULE_TOKEN, RULE_TOKEN_CHAR, RULE_DIGIT}
