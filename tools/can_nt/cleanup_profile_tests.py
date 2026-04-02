from __future__ import annotations

"""
NAME
    cleanup_profile_tests.py - Remove profile tests that don't match devices.

SYNOPSIS
    python tools/can_nt/cleanup_profile_tests.py [--profiles <path>] [--apply]

DESCRIPTION
    Scans bringup_system.json profile-scoped tests and removes test sets whose
    referenced device labels are all missing from the profile device list.
    This ignores legacy bringup_tests.json.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import sys

REPO_ROOT_DEPTH = 2
REPO_ROOT = Path(__file__).resolve().parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.common.json_io import read_json, write_json
from tools.common.paths import repo_root
from tools.common.profile_constants import (
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_CONFIG,
    KEY_BRIDGE_TESTS,
    KEY_PROFILE_DEVICES,
    KEY_PROFILES,
)
from tools.common.test_authoring.serializer import (
    DEFAULT_TEST_SET,
    KEY_DEFAULT_TEST_SET,
    KEY_TEST_SETS,
    KEY_TESTS,
)

APP_NAME = "cleanup_profile_tests"

ARG_PROFILES = "--profiles"
ARG_APPLY = "--apply"
ARG_DEST_PROFILES_PATH = "profiles_path"
ARG_DEST_APPLY = "apply"

DEFAULT_PROFILES_FILENAME = "data/bringup_system.json"

MESSAGE_NO_PROFILES = "ERROR: No profiles found."
MESSAGE_DRY_RUN = "Dry run only. Re-run with --apply to write changes."
MESSAGE_DONE = "Done."
MESSAGE_WROTE = "Wrote updated profiles: {path}"
MESSAGE_PROFILE = "Profile: {name}"
MESSAGE_NO_TESTS = "  tests: (none)"
MESSAGE_REMOVED = "  removed: {set_name}"

MIN_COUNT = 0

EXIT_OK = 0
EXIT_ERROR = 1


@dataclass
class Removal:
    """
    NAME
        Removal - Test set removal record.
    """

    profile: str
    set_name: str


def main() -> int:
    """
    NAME
        main - CLI entrypoint.
    """

    import argparse

    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument(ARG_PROFILES, dest=ARG_DEST_PROFILES_PATH, default=None)
    parser.add_argument(ARG_APPLY, dest=ARG_DEST_APPLY, action="store_true")
    args = parser.parse_args()

    profiles_path = _resolve_profiles_path(args.profiles_path)
    payload = _read_json_or_empty(profiles_path)
    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict) or not profiles:
        print(MESSAGE_NO_PROFILES)
        return EXIT_ERROR

    removals = _collect_removals(payload)
    _print_removals(removals)

    if not args.apply:
        print(MESSAGE_DRY_RUN)
        return EXIT_OK

    if not removals:
        print(MESSAGE_DONE)
        return EXIT_OK

    _apply_removals(payload, removals)
    write_json(profiles_path, payload, indent=2, trailing_newline=True)
    print(MESSAGE_WROTE.format(path=profiles_path))
    return EXIT_OK


def _resolve_profiles_path(arg: Optional[str]) -> Path:
    """
    NAME
        _resolve_profiles_path - Resolve bringup_system.json path.
    """

    if arg:
        return Path(arg)
    return repo_root() / DEFAULT_PROFILES_FILENAME


def _read_json_or_empty(path: Path) -> Dict[str, object]:
    """
    NAME
        _read_json_or_empty - Read JSON or return empty dict.
    """

    try:
        payload = read_json(path)
    except Exception:
        payload = {}
    if isinstance(payload, dict):
        return payload
    return {}


def _collect_removals(payload: Dict[str, object]) -> List[Removal]:
    """
    NAME
        _collect_removals - Identify test sets with no matching device labels.
    """

    removals: List[Removal] = []
    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict):
        return removals
    bridge = payload.get(KEY_BRIDGE_CONFIG)
    if not isinstance(bridge, dict):
        return removals
    by_profile = bridge.get(KEY_BRIDGE_BY_PROFILE)
    if not isinstance(by_profile, dict):
        return removals
    for profile_name, entry in by_profile.items():
        if not isinstance(profile_name, str) or not isinstance(entry, dict):
            continue
        labels = _profile_labels(profiles, profile_name)
        tests_payload = entry.get(KEY_BRIDGE_TESTS)
        if not isinstance(tests_payload, dict):
            continue
        test_sets = _extract_test_sets(tests_payload)
        for set_name, entries in test_sets.items():
            refs = _collect_labels(entries, labels)
            if not refs:
                continue
            if refs.isdisjoint(labels):
                removals.append(Removal(profile=profile_name, set_name=set_name))
    return removals


def _profile_labels(profiles: Dict[str, object], profile_name: str) -> Set[str]:
    """
    NAME
        _profile_labels - Get device labels for a profile.
    """

    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        return set()
    labels = profile.get(KEY_PROFILE_DEVICES)
    if not isinstance(labels, list):
        return set()
    return {label for label in labels if isinstance(label, str) and label}


def _extract_test_sets(payload: Dict[str, object]) -> Dict[str, List[Dict[str, object]]]:
    """
    NAME
        _extract_test_sets - Normalize tests payload into test sets.
    """

    if not isinstance(payload, dict):
        return {}
    test_sets_payload = payload.get(KEY_TEST_SETS)
    if isinstance(test_sets_payload, dict):
        normalized: Dict[str, List[Dict[str, object]]] = {}
        for name, entries in test_sets_payload.items():
            if not isinstance(name, str) or not isinstance(entries, list):
                continue
            normalized[name] = [entry for entry in entries if isinstance(entry, dict)]
        return normalized
    tests = payload.get(KEY_TESTS)
    if isinstance(tests, list):
        entries = [entry for entry in tests if isinstance(entry, dict)]
        return {DEFAULT_TEST_SET: entries}
    return {}


def _collect_labels(entries: List[Dict[str, object]], candidates: Set[str]) -> Set[str]:
    """
    NAME
        _collect_labels - Collect device label references from test entries.
    """

    labels: Set[str] = set()
    if not candidates:
        return labels
    for entry in entries:
        for value in _walk_values(entry):
            if isinstance(value, str) and value in candidates:
                labels.add(value)
    return labels


def _walk_values(value: object) -> Iterable[object]:
    """
    NAME
        _walk_values - Recursively yield nested values.
    """

    if isinstance(value, dict):
        for nested in value.values():
            yield from _walk_values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_values(nested)
    else:
        yield value


def _print_removals(removals: List[Removal]) -> None:
    """
    NAME
        _print_removals - Print removal summary.
    """

    if not removals:
        print(MESSAGE_DONE)
        return
    by_profile: Dict[str, List[str]] = {}
    for removal in removals:
        by_profile.setdefault(removal.profile, []).append(removal.set_name)
    for profile_name, sets in by_profile.items():
        print(MESSAGE_PROFILE.format(name=profile_name))
        if not sets:
            print(MESSAGE_NO_TESTS)
            continue
        for set_name in sets:
            print(MESSAGE_REMOVED.format(set_name=set_name))


def _apply_removals(payload: Dict[str, object], removals: List[Removal]) -> None:
    """
    NAME
        _apply_removals - Delete test sets from profile tests.
    """

    bridge = payload.get(KEY_BRIDGE_CONFIG)
    if not isinstance(bridge, dict):
        return
    by_profile = bridge.get(KEY_BRIDGE_BY_PROFILE)
    if not isinstance(by_profile, dict):
        return
    remove_map: Dict[str, Set[str]] = {}
    for removal in removals:
        remove_map.setdefault(removal.profile, set()).add(removal.set_name)
    for profile_name, set_names in remove_map.items():
        entry = by_profile.get(profile_name)
        if not isinstance(entry, dict):
            continue
        tests_payload = entry.get(KEY_BRIDGE_TESTS)
        if not isinstance(tests_payload, dict):
            continue
        test_sets = tests_payload.get(KEY_TEST_SETS)
        if isinstance(test_sets, dict):
            for set_name in set_names:
                test_sets.pop(set_name, None)
            tests_payload[KEY_TEST_SETS] = test_sets
            default_set = tests_payload.get(KEY_DEFAULT_TEST_SET)
            if isinstance(default_set, str) and default_set in set_names:
                tests_payload[KEY_DEFAULT_TEST_SET] = DEFAULT_TEST_SET
        else:
            tests = tests_payload.get(KEY_TESTS)
            if isinstance(tests, list) and DEFAULT_TEST_SET in set_names:
                tests_payload[KEY_TESTS] = []
        entry[KEY_BRIDGE_TESTS] = tests_payload


if __name__ == "__main__":
    raise SystemExit(main())
