from __future__ import annotations

"""
NAME
    add_tbd_note.py - Append a line to notes/planning/TBD.md.

SYNOPSIS
    python tools\\add_tbd_note.py --text "..." [--path PATH]

DESCRIPTION
    Appends a bullet under a target section in a single TBD list file,
    creating the section or file if needed.
"""

import argparse
from pathlib import Path

from tools.common.cli_helpers import add_path_arg
from datetime import datetime


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append a note to TBD.md.")
    parser.add_argument("--text", required=True, help="TBD note text.")
    add_path_arg(
        parser,
        default=str(Path("notes") / "planning" / "TBD.md"),
        help_text="Path to TBD list file.",
    )
    parser.add_argument(
        "--section",
        default="Tests",
        help="Section header to append under (default: Tests).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    text = args.text.strip()
    if not text:
        print("ERROR: text is required.")
        return 2
    path = Path(args.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"- {text}\n"
    if not path.exists():
        path.write_text("# TBD\n\n", encoding="utf-8")
    content = path.read_text(encoding="utf-8")
    header = f"## {args.section}"
    if header not in content:
        content = content.rstrip() + f"\n\n{header}\n"
    parts = content.split(header, 1)
    prefix = parts[0] + header + "\n"
    suffix = parts[1]
    if not suffix.startswith("\n"):
        suffix = "\n" + suffix
    content = prefix + line + suffix.lstrip("\n")
    path.write_text(content, encoding="utf-8")
    print(f"Appended to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
