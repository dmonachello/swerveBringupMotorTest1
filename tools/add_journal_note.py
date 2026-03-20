from __future__ import annotations

"""
NAME
    add_journal_note.py - Fast journal note helper.

SYNOPSIS
    python tools\\add_journal_note.py --text "..." [--date YYYY-MM-DD] [--title "..."]

DESCRIPTION
    Creates a dated journal entry under notes/journal with a title derived
    from the content if not provided.
"""

import argparse
import re
import textwrap
from datetime import datetime
from pathlib import Path


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "note"


def _derive_title(text: str) -> str:
    line = text.strip().splitlines()[0].strip()
    if not line:
        return "Journal Note"
    words = line.split()
    return " ".join(words[:8])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add a journal note.")
    parser.add_argument("--text", required=True, help="Note content.")
    parser.add_argument("--title", default="", help="Optional title override.")
    parser.add_argument(
        "--date",
        default="",
        help="Date in YYYY-MM-DD (default: today).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    title = args.title.strip() or _derive_title(args.text)
    date = args.date.strip() or datetime.now().strftime("%Y-%m-%d")
    slug = _slugify(title)
    path = Path("notes") / "journal" / f"{date}-{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = textwrap.dedent(
        f"""\
        # {title}

        {args.text.strip()}
        """
    )
    path.write_text(body, encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
