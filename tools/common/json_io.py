from __future__ import annotations

"""
NAME
    json_io.py - JSON read/write helpers for tools.

SYNOPSIS
    from tools.common.json_io import read_json, write_json

DESCRIPTION
    Small wrappers for consistent UTF-8 JSON IO across tools. Keeps file IO
    behavior uniform without changing caller-level error handling.
"""

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    """
    NAME
        read_json - Read JSON from a path with UTF-8 decoding.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, indent: int = 2, trailing_newline: bool = True) -> None:
    """
    NAME
        write_json - Write JSON to a path with UTF-8 encoding.

    PARAMETERS
        path: Destination file path.
        payload: JSON-serializable value.
        indent: Indentation spaces for pretty output.
        trailing_newline: When True, append a newline after the JSON.
    """
    text = json.dumps(payload, indent=indent)
    if trailing_newline:
        text += "\n"
    path.write_text(text, encoding="utf-8")
