"""
NAME
    test_ui_runtime_rules_lockstep.py - Guard CURRENT_UI_RUNTIME_RULES workflow headings against regression-guide drift.
"""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
UI_RULES_PATH = REPO_ROOT / "docs" / "CURRENT_UI_RUNTIME_RULES.md"
REGRESSION_GUIDE_PATH = REPO_ROOT / "docs" / "USER_GUIDE_REGRESSION_RUNNER.md"

SECTION_COMMON_WORKFLOWS = "## Common Workflows"
SECTION_LOCKSTEP = "## UI Runtime Workflow Lockstep"
WORKFLOW_HEADING_PREFIX = "### "


def _section_lines(path: Path, section_heading: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == section_heading:
            start = index + 1
            break
    if start is None:
        raise AssertionError(f"Missing section {section_heading!r} in {path}")
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return lines[start:end]


def _workflow_headings(path: Path, section_heading: str) -> list[str]:
    section = _section_lines(path, section_heading)
    return [
        line.strip()[len(WORKFLOW_HEADING_PREFIX):].strip()
        for line in section
        if line.strip().startswith(WORKFLOW_HEADING_PREFIX)
    ]


class UiRuntimeRulesLockstepTests(unittest.TestCase):
    """
    NAME
        UiRuntimeRulesLockstepTests - Keep runtime-rule workflows and regression-guide workflows in lockstep.
    """

    def test_regression_guide_has_matching_workflow_headings(self) -> None:
        runtime_rule_workflows = _workflow_headings(UI_RULES_PATH, SECTION_COMMON_WORKFLOWS)
        regression_guide_workflows = _workflow_headings(
            REGRESSION_GUIDE_PATH,
            SECTION_LOCKSTEP,
        )

        self.assertTrue(runtime_rule_workflows)
        self.assertEqual(runtime_rule_workflows, regression_guide_workflows)


if __name__ == "__main__":
    unittest.main()
