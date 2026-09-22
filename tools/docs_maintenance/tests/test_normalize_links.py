from __future__ import annotations

"""
NAME
    test_normalize_links.py - Tests for safe machine-local Markdown link normalization.
"""

import tempfile
import unittest
from pathlib import Path

from tools.docs_maintenance.normalize_links import normalize_machine_local_links


README_NAME = "README.md"
DOCS_DIR_NAME = "docs"
GUIDE_NAME = "Guide With Spaces.md"
SOURCE_TEXT = (
    "[Guide](/abs/path/c:/Users/example/repo/docs/Guide With Spaces.md)\n"
    "[Guide Windows](C:\\Users\\example\\repo\\docs\\Guide With Spaces.md)\n"
    "[Missing](C:/Users/example/repo/docs/Missing.md)\n"
)
EXPECTED_TEXT = (
    "[Guide](Guide%20With%20Spaces.md)\n"
    "[Guide Windows](Guide%20With%20Spaces.md)\n"
    "[Missing](C:/Users/example/repo/docs/Missing.md)\n"
)


class NormalizeLinksTests(unittest.TestCase):
    def test_dry_run_plans_existing_target_and_preserves_missing_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs_dir = root / DOCS_DIR_NAME
            docs_dir.mkdir()
            source = docs_dir / README_NAME
            source.write_text(SOURCE_TEXT, encoding="utf-8")
            (docs_dir / GUIDE_NAME).write_text("# Guide\n", encoding="utf-8")

            report = normalize_machine_local_links(root, apply_changes=False)

            self.assertEqual(SOURCE_TEXT, source.read_text(encoding="utf-8"))
            self.assertEqual(2, len(report.changes))
            self.assertEqual(1, len(report.unresolved))
            self.assertEqual("docs/Guide With Spaces.md", report.changes[0].target_repo_path)

    def test_apply_rewrites_only_existing_target_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs_dir = root / DOCS_DIR_NAME
            docs_dir.mkdir()
            source = docs_dir / README_NAME
            source.write_text(SOURCE_TEXT, encoding="utf-8")
            (docs_dir / GUIDE_NAME).write_text("# Guide\n", encoding="utf-8")

            first_report = normalize_machine_local_links(root, apply_changes=True)
            second_report = normalize_machine_local_links(root, apply_changes=True)

            self.assertEqual(EXPECTED_TEXT, source.read_text(encoding="utf-8"))
            self.assertEqual(2, len(first_report.changes))
            self.assertEqual(0, len(second_report.changes))
