"""
NAME
    can_top_selection.py - Tag parsing, filtering, and sorting helpers.

SYNOPSIS
    from tools.can_topology.can_top_selection import compile_tag_filter

DESCRIPTION
    Provides pure helpers for tag normalization, filtering, and list sorting.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Iterable, List, Optional, Tuple


def normalize_tag(value: str) -> str:
    """
    NAME
        normalize_tag - Normalize a tag string for comparisons.
    """
    return (value or "").strip().lower()


def normalize_tags(value: object) -> List[str]:
    """
    NAME
        normalize_tags - Normalize tags into a cleaned list.
    """
    tags: List[str] = []
    if isinstance(value, str):
        tags = [tag.strip() for tag in value.split(",")]
    elif isinstance(value, list):
        tags = [str(tag).strip() for tag in value]
    seen: set[str] = set()
    normalized: List[str] = []
    for tag in tags:
        if not tag:
            continue
        norm = normalize_tag(tag)
        if norm in seen:
            continue
        seen.add(norm)
        normalized.append(norm)
    return normalized


def tags_to_string(tags: List[str]) -> str:
    """
    NAME
        tags_to_string - Format tag list for display.
    """
    return ", ".join(tags) if tags else ""


def collect_tags(nodes: Iterable[Any]) -> List[str]:
    """
    NAME
        collect_tags - Gather all known tags for prompts.
    """
    tags: set[str] = set()
    for node in nodes:
        for tag in getattr(node, "tags", []) or []:
            if tag:
                tags.add(normalize_tag(tag))
    return sorted(tags)


def match_tag(node: Any, tag: str) -> bool:
    """
    NAME
        match_tag - Return True if a node has the given tag.
    """
    target = normalize_tag(tag)
    if not target:
        return False
    return target in {normalize_tag(t) for t in (getattr(node, "tags", []) or [])}


def compile_tag_filter(expr: str) -> Callable[[Any], bool]:
    """
    NAME
        compile_tag_filter - Compile a tag filter expression.
    """
    text = (expr or "").strip()
    if not text:
        raise ValueError("Filter expression is empty.")
    text = re.sub(r"\\bAND\\b", "&&", text, flags=re.IGNORECASE)
    text = re.sub(r"\\bOR\\b", "||", text, flags=re.IGNORECASE)

    tokens: List[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if text.startswith("&&", i):
            tokens.append("&&")
            i += 2
            continue
        if text.startswith("||", i):
            tokens.append("||")
            i += 2
            continue
        if ch == "&":
            tokens.append("&&")
            i += 1
            continue
        if ch == "|":
            tokens.append("||")
            i += 1
            continue
        if ch == ",":
            tokens.append("||")
            i += 1
            continue
        if ch in ("(", ")"):
            tokens.append(ch)
            i += 1
            continue
        j = i
        while j < len(text):
            if text[j].isspace():
                break
            if text.startswith("&&", j) or text.startswith("||", j):
                break
            if text[j] in ("(", ")", "&", "|", ","):
                break
            j += 1
        token = text[i:j].strip()
        if token:
            tokens.append(token)
        i = j

    if not tokens:
        raise ValueError("Filter expression is empty.")

    expanded: List[str] = []
    prev_type: Optional[str] = None
    for token in tokens:
        if token in ("&&", "||"):
            cur_type = "op"
        elif token == "(":
            cur_type = "lparen"
        elif token == ")":
            cur_type = "rparen"
        else:
            cur_type = "term"
        if prev_type in ("term", "rparen") and cur_type in ("term", "lparen"):
            expanded.append("||")
        expanded.append(token)
        prev_type = cur_type

    precedence = {"&&": 2, "||": 1}
    output: List[str] = []
    ops: List[str] = []

    for token in expanded:
        if token in ("&&", "||"):
            while ops and ops[-1] in precedence and precedence[ops[-1]] >= precedence[token]:
                output.append(ops.pop())
            ops.append(token)
        elif token == "(":
            ops.append(token)
        elif token == ")":
            while ops and ops[-1] != "(":
                output.append(ops.pop())
            if not ops or ops[-1] != "(":
                raise ValueError("Mismatched parentheses in filter.")
            ops.pop()
        else:
            output.append(token)

    while ops:
        if ops[-1] in ("(", ")"):
            raise ValueError("Mismatched parentheses in filter.")
        output.append(ops.pop())

    def _eval(node: Any) -> bool:
        stack: List[bool] = []
        for token in output:
            if token == "&&":
                if len(stack) < 2:
                    return False
                b = stack.pop()
                a = stack.pop()
                stack.append(a and b)
            elif token == "||":
                if len(stack) < 2:
                    return False
                b = stack.pop()
                a = stack.pop()
                stack.append(a or b)
            else:
                stack.append(match_tag(node, token))
        return bool(stack[-1]) if stack else False

    return _eval


def sort_nodes(nodes: List[Any], mode: str) -> List[Any]:
    """
    NAME
        sort_nodes - Sort nodes for the list view.
    """
    if mode == "tag":
        def _tag_key(node: Any) -> Tuple[str, str, int]:
            tags = getattr(node, "tags", []) or []
            primary = tags[0] if tags else ""
            return (normalize_tag(primary), str(getattr(node, "label", "")).lower(), int(getattr(node, "can_id", 0)))
        return sorted(nodes, key=_tag_key)
    return sorted(nodes, key=lambda n: int(getattr(n, "can_id", 0)))
