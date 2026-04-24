from __future__ import annotations

import unittest

from tools.common.tests_domain import (
    build_test_overview,
    collect_available_tests,
    validate_selected_test,
)


class TestsDomainSemanticsTests(unittest.TestCase):
    """Validate shared test-domain behaviors."""

    def test_collect_available_tests_supports_legacy_tests_list(self) -> None:
        payload = {
            "tests": [
                {"name": "A"},
                {"name": "B"},
            ]
        }
        names = collect_available_tests(payload)
        self.assertEqual(names, ["A", "B"])

    def test_validate_selected_test_returns_error_for_unknown_test(self) -> None:
        ok, message = validate_selected_test("Missing", ["A", "B"])
        self.assertFalse(ok)
        self.assertIn("Test not found", message)

    def test_build_test_overview_counts_duplicates(self) -> None:
        overview = build_test_overview(["A", "B", "A"])
        self.assertEqual(overview["total"], 3)
        self.assertEqual(overview["duplicate"], 1)


if __name__ == "__main__":
    unittest.main()

