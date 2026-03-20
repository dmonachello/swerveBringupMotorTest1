from __future__ import annotations

"""
NAME
    text_io.py - Text file helpers.

SYNOPSIS
    from tools.common.text_io import read_lines

DESCRIPTION
    Simple helpers for reading and writing text files consistently.
"""

from pathlib import Path
from typing import Iterable, List


def read_lines(path: Path) -> List[str]:
    """
    NAME
        read_lines - Read text file into a list of lines.
    """
    return path.read_text(encoding="utf-8").splitlines()


def write_lines(path: Path, lines: Iterable[str]) -> None:
    """
    NAME
        write_lines - Write lines to a text file.
    """
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
