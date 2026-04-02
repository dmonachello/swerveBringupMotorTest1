from __future__ import annotations

"""
NAME
    migrate_tests_profiles.py - Migrate bringup tests into profile-scoped config.

SYNOPSIS
    python tools/can_nt/migrate_tests_profiles.py [--tests <path>] [--profiles <path>] [--apply]

DESCRIPTION
    One-time utility that reads bringup_tests.json (or an override path),
    scores each test set against profile device labels, and helps assign
    each test set to a profile. When --apply is provided, the selected
    assignments are written into bringup_system.json under
    bridgeConfig.byProfile.<profile>.tests.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

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
    KEY_DEFAULT_PROFILE,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
)
from tools.common.test_authoring.serializer import (
    DEFAULT_TEST_SET,
    KEY_DEFAULT_TEST_SET,
    KEY_TEST_SETS,
    KEY_TESTS,
)

APP_NAME = "migrate_tests_profiles"

ARG_TESTS = "--tests"
ARG_PROFILES = "--profiles"
ARG_APPLY = "--apply"

DEFAULT_TESTS_FILENAME = "bringup_tests.json"
DEFAULT_PROFILES_FILENAME = "data/bringup_system.json"

PROMPT_ASSIGN = "Select profile (name/number), or 'skip'/'delete': "
PROMPT_OVERWRITE = "Profile '{profile}' already has tests. Overwrite? (y/N): "

CHOICE_SKIP = "skip"
CHOICE_DELETE = "delete"
CHOICE_YES = "y"
CHOICE_NO = "n"

LABEL_NONE = "(none)"
MESSAGE_NO_PROFILES = "ERROR: No profiles found in bringup_system.json."
MESSAGE_NO_TESTS = "ERROR: No test sets found in bringup_tests.json."
MESSAGE_DRY_RUN = "Dry run only. Re-run with --apply to write changes."
MESSAGE_NO_ASSIGNMENTS = "No assignments selected. Exiting without changes."
MESSAGE_NO_CHANGES = "No changes written."
MESSAGE_WROTE = "Wrote updated profiles: {path}"
MESSAGE_TEST_SET = "Test set: {name}"
MESSAGE_LABELS = "  labels: {labels}"
MESSAGE_PROFILES_NONE = "  profiles: (none)"
MESSAGE_ASSIGN_HEADER = "Assign test set: {name}"
MESSAGE_SCORED_ENTRY = "  {index}. {profile}: {score}"
MESSAGE_SCORE_ENTRY = "  {profile}: {score}"
MESSAGE_NO_PROFILES_AVAILABLE = "  (no profiles available)"
MESSAGE_UNKNOWN_SELECTION = (
    "Unknown selection '{selection}'. Options: profile name, number, skip, delete."
)
MESSAGE_EMPTY_LINE = ""

FORMAT_SCORE_SIMPLE = "{hits}/{total}"
FORMAT_SCORE_PERCENT = "{hits}/{total} ({percent}%)"

MIN_SCORE = 0
INDEX_ZERO = 0
INDEX_ONE = 1
PERCENT_MULTIPLIER = 100

ARG_DEST_TESTS_PATH = "tests_path"
ARG_DEST_PROFILES_PATH = "profiles_path"
ARG_DEST_APPLY = "apply"

EXIT_OK = 0
EXIT_ERROR = 1


@dataclass
class TestSetMatch:
    """
    NAME
        TestSetMatch - Scoring summary for a test set.

    PARAMETERS
        name - Test set name.
        labels - Device labels referenced in the test set.
        scores - Mapping of profile name to score tuple.
    """

    name: str
    labels: Set[str]
    scores: Dict[str, Tuple[int, int]]


def main() -> int:
    """
    NAME
        main - CLI entrypoint.
    """

    import argparse

    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument(ARG_TESTS, dest=ARG_DEST_TESTS_PATH, default=None)
    parser.add_argument(ARG_PROFILES, dest=ARG_DEST_PROFILES_PATH, default=None)
    parser.add_argument(ARG_APPLY, dest=ARG_DEST_APPLY, action="store_true")
    args = parser.parse_args()

    tests_path = _resolve_tests_path(args.tests_path)
    profiles_path = _resolve_profiles_path(args.profiles_path)

    tests_payload = _read_json_or_empty(tests_path)
    profiles_payload = _read_json_or_empty(profiles_path)

    profile_labels = _profile_device_labels(profiles_payload)
    if not profile_labels:
        print(MESSAGE_NO_PROFILES)
        return EXIT_ERROR

    test_sets, default_set = _extract_test_sets(tests_payload)
    if not test_sets:
        print(MESSAGE_NO_TESTS)
        return EXIT_ERROR

    matches = _score_test_sets(test_sets, profile_labels)
    _print_match_summary(matches)

    if not args.apply:
        print(MESSAGE_DRY_RUN)
        return EXIT_OK

    assignments = _prompt_assignments(matches, list(profile_labels.keys()))
    if not assignments:
        print(MESSAGE_NO_ASSIGNMENTS)
        return EXIT_OK

    updated = _apply_assignments(
        profiles_payload,
        test_sets,
        default_set,
        assignments,
    )
    if not updated:
        print(MESSAGE_NO_CHANGES)
        return EXIT_OK

    write_json(profiles_path, profiles_payload, indent=2, trailing_newline=True)
    print(MESSAGE_WROTE.format(path=profiles_path))
    return EXIT_OK


def _resolve_tests_path(arg: Optional[str]) -> Path:
    """
    NAME
        _resolve_tests_path - Resolve tests JSON path.
    """

    if arg:
        return Path(arg)
    return repo_root() / DEFAULT_TESTS_FILENAME


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


def _profile_device_labels(payload: Dict[str, object]) -> Dict[str, Set[str]]:
    """
    NAME
        _profile_device_labels - Build device label sets per profile.
    """

    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict):
        return {}
    labels_by_profile: Dict[str, Set[str]] = {}
    for profile_name, entry in profiles.items():
        if not isinstance(profile_name, str) or not isinstance(entry, dict):
            continue
        devices = entry.get(KEY_PROFILE_DEVICES)
        if not isinstance(devices, list):
            continue
        labels: Set[str] = set()
        for label in devices:
            if isinstance(label, str) and label:
                labels.add(label)
        labels_by_profile[profile_name] = labels
    if not labels_by_profile:
        default_profile = payload.get(KEY_DEFAULT_PROFILE)
        if isinstance(default_profile, str) and default_profile:
            labels_by_profile[default_profile] = set()
    return labels_by_profile


def _extract_test_sets(payload: Dict[str, object]) -> Tuple[Dict[str, List[Dict[str, object]]], str]:
    """
    NAME
        _extract_test_sets - Normalize tests payload into test set mapping.
    """

    if not isinstance(payload, dict):
        return {}, DEFAULT_TEST_SET
    test_sets_payload = payload.get(KEY_TEST_SETS)
    if isinstance(test_sets_payload, dict):
        normalized: Dict[str, List[Dict[str, object]]] = {}
        for name, entries in test_sets_payload.items():
            if not isinstance(name, str) or not isinstance(entries, list):
                continue
            normalized[name] = [entry for entry in entries if isinstance(entry, dict)]
        default_set = payload.get(KEY_DEFAULT_TEST_SET)
        if isinstance(default_set, str) and default_set:
            return normalized, default_set
        return normalized, DEFAULT_TEST_SET

    legacy_tests = payload.get(KEY_TESTS)
    if isinstance(legacy_tests, list):
        entries = [entry for entry in legacy_tests if isinstance(entry, dict)]
        return {DEFAULT_TEST_SET: entries}, DEFAULT_TEST_SET
    return {}, DEFAULT_TEST_SET


def _score_test_sets(
    test_sets: Dict[str, List[Dict[str, object]]],
    profile_labels: Dict[str, Set[str]],
) -> List[TestSetMatch]:
    """
    NAME
        _score_test_sets - Score test sets against profiles.
    """

    results: List[TestSetMatch] = []
    for set_name, entries in test_sets.items():
        labels = _collect_labels(entries, profile_labels)
        scores: Dict[str, Tuple[int, int]] = {}
        for profile_name, device_labels in profile_labels.items():
            hits = len(labels & device_labels)
            scores[profile_name] = (hits, len(labels))
        results.append(TestSetMatch(name=set_name, labels=labels, scores=scores))
    return results


def _collect_labels(
    entries: List[Dict[str, object]],
    profile_labels: Dict[str, Set[str]],
) -> Set[str]:
    """
    NAME
        _collect_labels - Collect device label references from test entries.
    """

    candidates = _all_device_labels(profile_labels)
    labels: Set[str] = set()
    for entry in entries:
        for value in _walk_values(entry):
            if isinstance(value, str) and value in candidates:
                labels.add(value)
    return labels


def _all_device_labels(profile_labels: Dict[str, Set[str]]) -> Set[str]:
    """
    NAME
        _all_device_labels - Union of device labels across profiles.
    """

    labels: Set[str] = set()
    for device_labels in profile_labels.values():
        labels.update(device_labels)
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


def _print_match_summary(matches: Sequence[TestSetMatch]) -> None:
    """
    NAME
        _print_match_summary - Print match scores for each test set.
    """

    for match in matches:
        labels = sorted(match.labels)
        labels_text = ", ".join(labels) if labels else LABEL_NONE
        print(MESSAGE_TEST_SET.format(name=match.name))
        print(MESSAGE_LABELS.format(labels=labels_text))
        scored = _sorted_scores(match.scores)
        if not scored:
            print(MESSAGE_PROFILES_NONE)
            continue
        for profile_name, hits, total in scored:
            score_text = _format_score(hits, total)
            print(MESSAGE_SCORE_ENTRY.format(profile=profile_name, score=score_text))


def _sorted_scores(scores: Dict[str, Tuple[int, int]]) -> List[Tuple[str, int, int]]:
    """
    NAME
        _sorted_scores - Sort score tuples by descending hits.
    """

    entries = [(name, value[0], value[1]) for name, value in scores.items()]
    entries.sort(key=lambda entry: (-entry[1], entry[0]))
    return entries


def _format_score(hits: int, total: int) -> str:
    """
    NAME
        _format_score - Format a hit/total score with percent.
    """

    if total <= MIN_SCORE:
        return FORMAT_SCORE_SIMPLE.format(hits=hits, total=total)
    percent = int((hits / total) * PERCENT_MULTIPLIER)
    return FORMAT_SCORE_PERCENT.format(hits=hits, total=total, percent=percent)


def _prompt_assignments(
    matches: Sequence[TestSetMatch],
    profiles: List[str],
) -> Dict[str, List[str]]:
    """
    NAME
        _prompt_assignments - Prompt user for per-test-set assignments.
    """

    assignments: Dict[str, List[str]] = {}
    for match in matches:
        print(MESSAGE_EMPTY_LINE)
        print(MESSAGE_ASSIGN_HEADER.format(name=match.name))
        scored = _sorted_scores(match.scores)
        for idx, (profile_name, hits, total) in enumerate(scored, start=INDEX_ONE):
            score_text = _format_score(hits, total)
            print(MESSAGE_SCORED_ENTRY.format(index=idx, profile=profile_name, score=score_text))
        if not scored:
            print(MESSAGE_NO_PROFILES_AVAILABLE)
        selection = _prompt_for_profile(scored, profiles)
        if selection == CHOICE_SKIP:
            continue
        if selection == CHOICE_DELETE:
            assignments.setdefault(CHOICE_DELETE, []).append(match.name)
            continue
        assignments.setdefault(selection, []).append(match.name)
    return assignments


def _prompt_for_profile(
    scored: List[Tuple[str, int, int]],
    profiles: List[str],
) -> str:
    """
    NAME
        _prompt_for_profile - Prompt for profile choice or skip/delete.
    """

    while True:
        response = input(PROMPT_ASSIGN).strip()
        if not response:
            return CHOICE_SKIP
        token = response.lower()
        if token in (CHOICE_SKIP, CHOICE_DELETE):
            return token
        if response.isdigit():
            index = int(response) - INDEX_ONE
            if INDEX_ZERO <= index < len(scored):
                return scored[index][0]
        if response in profiles:
            return response
        print(
            MESSAGE_UNKNOWN_SELECTION.format(
                selection=response,
            )
        )


def _apply_assignments(
    profiles_payload: Dict[str, object],
    test_sets: Dict[str, List[Dict[str, object]]],
    default_set: str,
    assignments: Dict[str, List[str]],
) -> bool:
    """
    NAME
        _apply_assignments - Apply assignments to bringup_system.json payload.
    """

    by_profile = _ensure_bridge_by_profile(profiles_payload)
    if by_profile is None:
        return False

    changed = False
    for profile_name, set_names in assignments.items():
        if profile_name == CHOICE_DELETE:
            continue
        entry = _ensure_profile_entry(by_profile, profile_name)
        if entry is None:
            continue
        existing = entry.get(KEY_TESTS)
        if existing:
            if not _confirm_overwrite(profile_name):
                continue
        payload = _build_tests_payload(test_sets, default_set, set_names)
        entry[KEY_TESTS] = payload
        changed = True
    return changed


def _ensure_bridge_by_profile(payload: Dict[str, object]) -> Optional[Dict[str, object]]:
    """
    NAME
        _ensure_bridge_by_profile - Return or create bridgeConfig.byProfile.
    """

    bridge = payload.get(KEY_BRIDGE_CONFIG)
    if bridge is None:
        bridge = {}
        payload[KEY_BRIDGE_CONFIG] = bridge
    if not isinstance(bridge, dict):
        return None
    by_profile = bridge.get(KEY_BRIDGE_BY_PROFILE)
    if by_profile is None:
        by_profile = {}
        bridge[KEY_BRIDGE_BY_PROFILE] = by_profile
    if not isinstance(by_profile, dict):
        return None
    return by_profile


def _ensure_profile_entry(by_profile: Dict[str, object], profile_name: str) -> Optional[Dict[str, object]]:
    """
    NAME
        _ensure_profile_entry - Return or create a bridgeConfig profile entry.
    """

    entry = by_profile.get(profile_name)
    if entry is None:
        entry = {}
        by_profile[profile_name] = entry
    if not isinstance(entry, dict):
        return None
    return entry


def _build_tests_payload(
    test_sets: Dict[str, List[Dict[str, object]]],
    default_set: str,
    set_names: List[str],
) -> Dict[str, object]:
    """
    NAME
        _build_tests_payload - Build payload containing assigned test sets.
    """

    payload: Dict[str, object] = {
        KEY_TEST_SETS: {},
    }
    tests_block = payload.get(KEY_TEST_SETS)
    if isinstance(tests_block, dict):
        for set_name in set_names:
            tests_block[set_name] = test_sets.get(set_name, [])
    chosen = default_set if default_set in set_names else (set_names[0] if set_names else DEFAULT_TEST_SET)
    payload[KEY_DEFAULT_TEST_SET] = chosen
    return payload


def _confirm_overwrite(profile_name: str) -> bool:
    """
    NAME
        _confirm_overwrite - Prompt before overwriting existing profile tests.
    """

    response = input(PROMPT_OVERWRITE.format(profile=profile_name)).strip().lower()
    if response == CHOICE_YES:
        return True
    if response == CHOICE_NO:
        return False
    return False


if __name__ == "__main__":
    raise SystemExit(main())
