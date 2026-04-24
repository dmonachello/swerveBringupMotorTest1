from __future__ import annotations

"""
NAME
    semantics.py - Shared test-domain selection/validation semantics.
"""

from typing import Any, Dict, List, Tuple

from tools.common.tests_io import extract_test_names


KEY_TOTAL = "total"
KEY_UNIQUE = "unique"
KEY_EMPTY = "empty"
KEY_DUPLICATE = "duplicate"

MSG_MISSING = "Test name is required."
MSG_NOT_FOUND = "Test not found: {name}"


def collect_available_tests(payload: Dict[str, Any]) -> List[str]:
    """
    NAME
        collect_available_tests - Collect ordered test names from payload.
    """
    if not isinstance(payload, dict):
        return []
    return extract_test_names(payload)


def validate_selected_test(test_name: str, available_names: List[str]) -> Tuple[bool, str]:
    """
    NAME
        validate_selected_test - Validate a selected test name.
    """
    if not isinstance(test_name, str) or not test_name.strip():
        return False, MSG_MISSING
    name = test_name.strip()
    if name not in available_names:
        return False, MSG_NOT_FOUND.format(name=name)
    return True, ""


def build_test_overview(available_names: List[str]) -> Dict[str, int]:
    """
    NAME
        build_test_overview - Build a small test inventory summary.
    """
    total = len(available_names)
    unique = len(set(available_names))
    empty = sum(1 for entry in available_names if not isinstance(entry, str) or not entry.strip())
    duplicate = max(total - unique, 0)
    return {
        KEY_TOTAL: total,
        KEY_UNIQUE: unique,
        KEY_EMPTY: empty,
        KEY_DUPLICATE: duplicate,
    }

