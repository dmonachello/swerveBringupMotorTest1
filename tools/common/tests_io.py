from __future__ import annotations

"""
NAME
    tests_io.py - bringup_tests.json helpers.

SYNOPSIS
    from tools.common.tests_io import extract_test_names

DESCRIPTION
    Helpers to extract test names from bringup_tests.json without embedding
    file layout knowledge into UI code.
"""

from pathlib import Path
from typing import Any, Dict, List

from .json_io import read_json, write_json


def extract_test_names(payload: Dict[str, Any]) -> List[str]:
    """
    NAME
        extract_test_names - Extract ordered test names from payload.

    DESCRIPTION
        Supports both legacy "tests" list and "test_sets"/"default_test_set".
    """
    tests = payload.get("tests")
    if isinstance(tests, list):
        names: List[str] = []
        for entry in tests:
            if isinstance(entry, dict):
                name = entry.get("name")
                if isinstance(name, str) and name:
                    names.append(name)
        return names

    test_sets = payload.get("test_sets")
    if isinstance(test_sets, dict):
        default_set = payload.get("default_test_set")
        if isinstance(default_set, str) and default_set in test_sets:
            tests = test_sets.get(default_set, [])
        else:
            tests = next(iter(test_sets.values()), [])
        if isinstance(tests, list):
            names = []
            for entry in tests:
                if isinstance(entry, dict):
                    name = entry.get("name")
                    if isinstance(name, str) and name:
                        names.append(name)
            return names

    return []


def load_tests_payload(path: Path) -> Any:
    """
    NAME
        load_tests_payload - Load bringup_tests.json from disk.
    """
    return read_json(path)


def write_tests_payload(path: Path, payload: Dict[str, Any]) -> None:
    """
    NAME
        write_tests_payload - Write bringup_tests.json to disk.
    """
    write_json(path, payload, indent=2, trailing_newline=False)
