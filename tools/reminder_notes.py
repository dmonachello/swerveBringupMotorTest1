from __future__ import annotations

"""
NAME
    reminder_notes.py - List and downgrade active reminder notes.

SYNOPSIS
    python tools\\reminder_notes.py list
    python tools\\reminder_notes.py downgrade notes\\journal\\YYYY-MM-DD-name.md

DESCRIPTION
    Scans repo journal notes for explicit reminder markers and supports
    downgrading an active reminder into a normal note by rewriting its marker.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


PATH_NOTES = "notes"
PATH_JOURNAL = "journal"
CMD_LIST = "list"
CMD_DOWNGRADE = "downgrade"
ENCODING_UTF8 = "utf-8"
MARKER_KEY = "REMINDER_STATUS:"
STATUS_ACTIVE = "ACTIVE"
STATUS_NOTE = "NOTE"
TEXT_NEWLINE = "\n"
TEXT_EMPTY = ""
EXIT_OK = 0
EXIT_ERROR = 1
MESSAGE_NO_ACTIVE = "No active reminders."
MESSAGE_DOWNGRADED = "Downgraded reminder:"
MESSAGE_NOT_FOUND = "Reminder note not found:"
MESSAGE_NOT_REMINDER = "Note is not an active reminder:"


@dataclass(frozen=True)
class ReminderNote:
    """
    NAME
        ReminderNote - One reminder note discovered from the journal directory.
    """

    path: Path
    status: str


def _repo_root() -> Path:
    """
    NAME
        _repo_root - Return the repository root inferred from this tool path.
    """
    return Path(__file__).resolve().parent.parent


def _journal_dir(root: Path) -> Path:
    """
    NAME
        _journal_dir - Return the journal notes directory.
    """
    return root / PATH_NOTES / PATH_JOURNAL


def _iter_markdown_files(path: Path) -> Iterable[Path]:
    """
    NAME
        _iter_markdown_files - Yield markdown files from one directory in stable order.
    """
    if not path.exists():
        return []
    return sorted(child for child in path.iterdir() if child.is_file() and child.suffix.lower() == ".md")


def _read_status(path: Path) -> str:
    """
    NAME
        _read_status - Return reminder status parsed from the note marker.
    """
    try:
        for line in path.read_text(encoding=ENCODING_UTF8).splitlines():
            clean_line = line.strip()
            if clean_line.startswith(MARKER_KEY):
                return clean_line[len(MARKER_KEY) :].strip().upper()
    except OSError:
        return TEXT_EMPTY
    return TEXT_EMPTY


def find_active_reminders(root: Path | None = None) -> List[ReminderNote]:
    """
    NAME
        find_active_reminders - Return active reminder notes from notes/journal.
    """
    resolved_root = root if root is not None else _repo_root()
    results: List[ReminderNote] = []
    for path in _iter_markdown_files(_journal_dir(resolved_root)):
        status = _read_status(path)
        if status == STATUS_ACTIVE:
            results.append(ReminderNote(path=path, status=status))
    return results


def downgrade_reminder(path: Path) -> bool:
    """
    NAME
        downgrade_reminder - Rewrite one active reminder marker into a normal note marker.
    """
    if not path.exists():
        return False
    text = path.read_text(encoding=ENCODING_UTF8)
    lines = text.splitlines()
    replaced = False
    for index, line in enumerate(lines):
        clean_line = line.strip()
        if clean_line == f"{MARKER_KEY} {STATUS_ACTIVE}":
            lines[index] = f"{MARKER_KEY} {STATUS_NOTE}"
            replaced = True
            break
    if not replaced:
        return False
    rewritten = TEXT_NEWLINE.join(lines)
    if text.endswith(TEXT_NEWLINE):
        rewritten += TEXT_NEWLINE
    path.write_text(rewritten, encoding=ENCODING_UTF8)
    return True


def _build_parser() -> argparse.ArgumentParser:
    """
    NAME
        _build_parser - Build the reminder-note CLI parser.
    """
    parser = argparse.ArgumentParser(description="List and downgrade reminder notes.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(CMD_LIST, help="List active reminder notes.")
    downgrade_parser = subparsers.add_parser(CMD_DOWNGRADE, help="Downgrade one reminder to a normal note.")
    downgrade_parser.add_argument("path", help="Path to the reminder note.")
    return parser


def main() -> int:
    """
    NAME
        main - Run the reminder-note helper CLI.
    """
    args = _build_parser().parse_args()
    root = _repo_root()
    if args.command == CMD_LIST:
        reminders = find_active_reminders(root)
        if not reminders:
            print(MESSAGE_NO_ACTIVE)
            return EXIT_OK
        for reminder in reminders:
            print(reminder.path.relative_to(root))
        return EXIT_OK
    note_path = Path(str(args.path)).resolve()
    if not note_path.exists():
        print(f"{MESSAGE_NOT_FOUND} {args.path}")
        return EXIT_ERROR
    if _read_status(note_path) != STATUS_ACTIVE:
        print(f"{MESSAGE_NOT_REMINDER} {args.path}")
        return EXIT_ERROR
    if not downgrade_reminder(note_path):
        print(f"{MESSAGE_NOT_REMINDER} {args.path}")
        return EXIT_ERROR
    print(f"{MESSAGE_DOWNGRADED} {note_path.relative_to(root)}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
