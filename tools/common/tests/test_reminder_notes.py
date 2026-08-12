import tempfile
import unittest
from pathlib import Path

from tools.reminder_notes import (
    MARKER_KEY,
    STATUS_ACTIVE,
    STATUS_NOTE,
    downgrade_reminder,
    find_active_reminders,
)


TEXT_REMINDER_BODY = "- Follow up next session.\n"
TEXT_PLAIN_BODY = "- Just a note.\n"


class ReminderNotesTests(unittest.TestCase):
    """
    NAME
        ReminderNotesTests - Validate listing and downgrade behavior for journal reminders.
    """

    def test_find_active_reminders_returns_only_active_marker_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            journal = root / "notes" / "journal"
            journal.mkdir(parents=True, exist_ok=True)
            active = journal / "2026-08-12-active.md"
            note = journal / "2026-08-12-note.md"
            plain = journal / "2026-08-12-plain.md"
            active.write_text(f"{MARKER_KEY} {STATUS_ACTIVE}\n\n{TEXT_REMINDER_BODY}", encoding="utf-8")
            note.write_text(f"{MARKER_KEY} {STATUS_NOTE}\n\n{TEXT_PLAIN_BODY}", encoding="utf-8")
            plain.write_text(TEXT_PLAIN_BODY, encoding="utf-8")

            reminders = find_active_reminders(root)

            self.assertEqual([active], [entry.path for entry in reminders])

    def test_downgrade_reminder_rewrites_active_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "note.md"
            path.write_text(f"{MARKER_KEY} {STATUS_ACTIVE}\n\n{TEXT_REMINDER_BODY}", encoding="utf-8")

            changed = downgrade_reminder(path)

            self.assertTrue(changed)
            self.assertIn(f"{MARKER_KEY} {STATUS_NOTE}", path.read_text(encoding="utf-8"))

    def test_downgrade_reminder_rejects_non_active_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "note.md"
            path.write_text(f"{MARKER_KEY} {STATUS_NOTE}\n\n{TEXT_PLAIN_BODY}", encoding="utf-8")

            changed = downgrade_reminder(path)

            self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
