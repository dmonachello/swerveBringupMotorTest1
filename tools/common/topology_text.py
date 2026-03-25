from __future__ import annotations

"""
NAME
    topology_text.py - Shared topology text layout helpers.

SYNOPSIS
    from tools.common.topology_text import fit_font_size

DESCRIPTION
    Centralizes text wrapping and font fitting so topology views render
    consistent labels.
"""

from typing import List

import tkinter.font as tkfont


def fit_font_size(text: str, max_w: float, max_h: float, base_size: int, family: str = "Segoe UI") -> int:
    """
    NAME
        fit_font_size - Shrink font size until text fits inside a box.
    """
    size = max(6, base_size)
    lines = text.splitlines() or [text]
    while size >= 6:
        font = tkfont.Font(family=family, size=size)
        line_h = font.metrics("linespace")
        total_h = line_h * len(lines)
        if total_h <= max_h:
            widest = max(font.measure(line) for line in lines)
            if widest <= max_w:
                return size
        size -= 1
    return 6


def truncate_to_width(text: str, font: tkfont.Font, max_w: float) -> str:
    """
    NAME
        truncate_to_width - Trim text to fit a max pixel width.
    """
    if font.measure(text) <= max_w:
        return text
    if max_w <= 0:
        return ""
    trimmed = text
    while trimmed and font.measure(trimmed + "...") > max_w:
        trimmed = trimmed[:-1]
    return (trimmed + "...") if trimmed else ""


def wrap_label_lines(text: str, font: tkfont.Font, max_w: float) -> List[str]:
    """
    NAME
        wrap_label_lines - Wrap label text into at most two lines.
    """
    words = text.split()
    if not words:
        return [text]
    lines: List[str] = []
    current = ""
    idx = 0
    while idx < len(words) and len(lines) < 1:
        word = words[idx]
        cand = word if not current else f"{current} {word}"
        if font.measure(cand) <= max_w or not current:
            current = cand
            idx += 1
        else:
            lines.append(current)
            current = ""
    if not lines:
        lines.append(current or words[0])
    remaining = words[idx:]
    second = " ".join(remaining) if remaining else ""
    if second:
        second = truncate_to_width(second, font, max_w)
        lines.append(second)
    return lines[:2]
