from __future__ import annotations

"""
NAME
    gen_bringup_tests.py - Guided bringup test generator (unified config).

SYNOPSIS
    python -m tools.bringup_test_wizard.gen_bringup_tests [--path PATH] [--profile NAME]

DESCRIPTION
    Interactive wizard that creates a safe baseline test set and stores it in
    bringup_system.json under:
      bridgeConfig.byProfile.<profile>.tests

    This is the supported persistence path for tests in this repo. Standalone
    bringup_tests.json is treated as a legacy import/export format and is not
    the robot's primary input.

SIDE EFFECTS
    Reads and writes the deploy-owned bringup_system.json file.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.common.json_io import read_json, write_json
from tools.common.profile_constants import (
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_CONFIG,
    KEY_BRIDGE_GENERATED_AT,
    KEY_BRIDGE_SCHEMA_VERSION,
    KEY_BRIDGE_TESTS,
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICES,
    KEY_INTERFACE,
    KEY_LABEL,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
    KEY_SCHEMA_VERSION,
    KEY_TYPE,
    PROFILE_SCHEMA_VERSION,
)
from tools.common.profile_io import compute_profiles_hash, validate_profiles_schema
from tools.common.time_utils import timestamp_version


DEFAULT_CANONICAL_PATH = Path("src") / "main" / "deploy" / "bringup_system.json"
DEFAULT_DEPLOY_PATH = Path("src") / "main" / "deploy" / "bringup_system.json"
DEFAULT_TEST_SET = "smoke"

KEY_TESTS_DEFAULT_SET = "default_test_set"
KEY_TESTS_SETS = "test_sets"

TEST_TYPE_COMPOSITE = "composite"
FIELD_TEST_NAME = "name"
FIELD_TEST_ENABLED = "enabled"
FIELD_TEST_TYPE = "type"
FIELD_TEST_MOTOR_LABELS = "motorLabels"
FIELD_TEST_DUTY = "duty"
FIELD_TEST_TIME = "time"
FIELD_TEST_TIMEOUT_SEC = "timeoutSec"
FIELD_TEST_ON_TIMEOUT = "onTimeout"

DEFAULT_DUTY = 0.15
DEFAULT_TIMEOUT_SEC = 0.5
DEFAULT_ON_TIMEOUT = "pass"

DEVICE_TYPE_MOTOR = "motor"

NAME_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9_]+")

# Constants (messages).
MSG_ERR_MISSING_CONFIG = "ERROR: bringup_system.json not found: {path}"
MSG_ERR_READ_CONFIG = "ERROR: failed to read {path}: {error}"
MSG_ERR_ROOT_OBJECT = "ERROR: bringup_system.json root must be a JSON object"
MSG_ERR_SCHEMA = "ERROR: bringup_system.json schema invalid: {error}"
MSG_ERR_NO_PROFILES = "ERROR: bringup_system.json has no profiles."
MSG_ERR_PROFILE_SELECT = "ERROR: profile not selected or not found. Available: {available}"
MSG_AVAILABLE_PROFILES = "Available profiles: {available}"
MSG_ERR_PROFILE_UNKNOWN = "ERROR: unknown profile: {profile}"
MSG_ERR_NO_MOTORS = "ERROR: profile '{profile}' has no motor devices (type=motor)."
MSG_ERR_DEVICES_UNKNOWN = "ERROR: unknown device label(s) for profile '{profile}': {labels}"
MSG_ERR_DEVICES_NOT_MOTORS = "ERROR: selected device(s) are not motors in profile '{profile}': {labels}"
MSG_UPDATED = "Updated profile '{profile}' test set '{set_name}'."
MSG_COUNTS = "Motors: {motors}  Added: {added}  Replaced: {replaced}"
MSG_WROTE = "Wrote: {path}"
MSG_PROMPT_REPLACE = "Replace test set '{set_name}' (otherwise merge/update by name)?"
MSG_PROMPT_DEVICES = "Device labels (comma-separated; blank = all motors)"
MSG_PROMPT_PROFILE = "Profile"
MSG_HINT_ENTER_NUMBER = "Enter a number."
MSG_HINT_ENTER_YN = "Enter y or n."


def _prompt(text: str, default: Optional[str] = None) -> str:
    """
    NAME
        _prompt - Prompt for a value with an optional default.
    """

    if default is None:
        prompt = f"{text}: "
    else:
        prompt = f"{text} [{default}]: "
    value = input(prompt).strip()
    return value if value else (default or "")


def _prompt_float(text: str, default: float) -> float:
    """
    NAME
        _prompt_float - Prompt until a float is entered.
    """

    while True:
        raw = _prompt(text, str(default))
        try:
            return float(raw)
        except (TypeError, ValueError):
            print(MSG_HINT_ENTER_NUMBER)


def _prompt_yes_no(text: str, default: bool) -> bool:
    """
    NAME
        _prompt_yes_no - Prompt for a boolean with y/n responses.
    """

    default_str = "y" if default else "n"
    while True:
        raw = _prompt(text, default_str).strip().lower()
        if raw in ("y", "yes", "true", "1"):
            return True
        if raw in ("n", "no", "false", "0"):
            return False
        print(MSG_HINT_ENTER_YN)


def _load_bringup_system(path: Path) -> Dict[str, object]:
    """
    NAME
        _load_bringup_system - Load bringup_system.json from disk.
    """

    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("bringup_system.json root must be an object")
    return payload


def _ensure_bridge_config(payload: Dict[str, object]) -> Dict[str, object]:
    """
    NAME
        _ensure_bridge_config - Ensure bridgeConfig structure exists.
    """

    bridge = payload.get(KEY_BRIDGE_CONFIG)
    if not isinstance(bridge, dict):
        bridge = {
            KEY_BRIDGE_SCHEMA_VERSION: 2,
            KEY_BRIDGE_GENERATED_AT: None,
            KEY_BRIDGE_BY_PROFILE: {},
        }
        payload[KEY_BRIDGE_CONFIG] = bridge
    if KEY_BRIDGE_SCHEMA_VERSION not in bridge:
        bridge[KEY_BRIDGE_SCHEMA_VERSION] = 2
    if KEY_BRIDGE_GENERATED_AT not in bridge:
        bridge[KEY_BRIDGE_GENERATED_AT] = None
    by_profile = bridge.get(KEY_BRIDGE_BY_PROFILE)
    if not isinstance(by_profile, dict):
        by_profile = {}
        bridge[KEY_BRIDGE_BY_PROFILE] = by_profile
    return bridge


def _ensure_profile_tests(payload: Dict[str, object], profile: str) -> Dict[str, object]:
    """
    NAME
        _ensure_profile_tests - Ensure bridgeConfig.byProfile.<profile>.tests exists.
    """

    bridge = _ensure_bridge_config(payload)
    by_profile = bridge.get(KEY_BRIDGE_BY_PROFILE)
    if not isinstance(by_profile, dict):
        by_profile = {}
        bridge[KEY_BRIDGE_BY_PROFILE] = by_profile
    entry = by_profile.get(profile)
    if not isinstance(entry, dict):
        entry = {}
        by_profile[profile] = entry
    tests = entry.get(KEY_BRIDGE_TESTS)
    if not isinstance(tests, dict):
        tests = {KEY_TESTS_DEFAULT_SET: DEFAULT_TEST_SET, KEY_TESTS_SETS: {DEFAULT_TEST_SET: []}}
        entry[KEY_BRIDGE_TESTS] = tests
    if KEY_TESTS_DEFAULT_SET not in tests:
        tests[KEY_TESTS_DEFAULT_SET] = DEFAULT_TEST_SET
    if KEY_TESTS_SETS not in tests or not isinstance(tests.get(KEY_TESTS_SETS), dict):
        tests[KEY_TESTS_SETS] = {str(tests.get(KEY_TESTS_DEFAULT_SET) or DEFAULT_TEST_SET): []}
    return tests


def _profile_device_labels(payload: Dict[str, object], profile: str) -> List[str]:
    """
    NAME
        _profile_device_labels - Return the profile's device label list.
    """

    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict):
        return []
    entry = profiles.get(profile)
    if not isinstance(entry, dict):
        return []
    labels = entry.get(KEY_PROFILE_DEVICES)
    if not isinstance(labels, list):
        return []
    out: List[str] = []
    for label in labels:
        if isinstance(label, str) and label.strip():
            out.append(label.strip())
    return out


def _device_registry_map(payload: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    """
    NAME
        _device_registry_map - Build a label->device mapping.
    """

    registry = payload.get(KEY_DEVICES)
    if not isinstance(registry, list):
        return {}
    out: Dict[str, Dict[str, object]] = {}
    for entry in registry:
        if not isinstance(entry, dict):
            continue
        label = entry.get(KEY_LABEL)
        if isinstance(label, str) and label.strip():
            out[label.strip()] = entry
    return out


def _motor_labels_for_profile(payload: Dict[str, object], profile: str) -> List[str]:
    """
    NAME
        _motor_labels_for_profile - Return motor device labels for a profile.
    """

    labels = _profile_device_labels(payload, profile)
    registry = _device_registry_map(payload)
    motors: List[str] = []
    for label in labels:
        dev = registry.get(label)
        if not dev:
            continue
        dev_type = dev.get(KEY_TYPE)
        if dev_type == DEVICE_TYPE_MOTOR:
            motors.append(label)
    return motors


def _sanitize_test_name(label: str) -> str:
    """
    NAME
        _sanitize_test_name - Create a stable test name from a device label.
    """

    base = NAME_SANITIZE_RE.sub("_", (label or "").strip())
    base = base.strip("_")
    return base or "device"


def _build_smoke_test(label: str, duty: float, timeout_sec: float) -> Dict[str, object]:
    """
    NAME
        _build_smoke_test - Build a safe time-limited composite test entry.
    """

    return {
        FIELD_TEST_TYPE: TEST_TYPE_COMPOSITE,
        FIELD_TEST_NAME: f"smoke_{_sanitize_test_name(label)}",
        FIELD_TEST_ENABLED: False,
        FIELD_TEST_MOTOR_LABELS: [label],
        FIELD_TEST_DUTY: duty,
        FIELD_TEST_TIME: {
            FIELD_TEST_TIMEOUT_SEC: timeout_sec,
            FIELD_TEST_ON_TIMEOUT: DEFAULT_ON_TIMEOUT,
        },
    }


def _upsert_test_set(
    tests_payload: Dict[str, object],
    set_name: str,
    new_tests: List[Dict[str, object]],
    replace: bool,
) -> Tuple[int, int]:
    """
    NAME
        _upsert_test_set - Insert tests into a named test set.

    RETURNS
        (added_count, replaced_count)
    """

    test_sets = tests_payload.get(KEY_TESTS_SETS)
    if not isinstance(test_sets, dict):
        test_sets = {}
        tests_payload[KEY_TESTS_SETS] = test_sets
    existing = test_sets.get(set_name)
    if not isinstance(existing, list):
        existing = []
    if replace:
        test_sets[set_name] = list(new_tests)
        return (len(new_tests), len(existing))

    existing_by_name: Dict[str, Dict[str, object]] = {}
    for entry in existing:
        if isinstance(entry, dict) and isinstance(entry.get(FIELD_TEST_NAME), str):
            existing_by_name[entry[FIELD_TEST_NAME]] = entry
    added = 0
    replaced = 0
    for entry in new_tests:
        name = entry.get(FIELD_TEST_NAME)
        if not isinstance(name, str):
            continue
        if name in existing_by_name:
            existing_by_name[name].clear()
            existing_by_name[name].update(entry)
            replaced += 1
        else:
            existing.append(entry)
            added += 1
    test_sets[set_name] = existing
    return (added, replaced)


def _finalize_and_write(payload: Dict[str, object], canonical_path: Path, deploy_path: Path) -> None:
    """
    NAME
        _finalize_and_write - Update version/hash and write canonical + deploy copies.
    """

    payload[KEY_SCHEMA_VERSION] = PROFILE_SCHEMA_VERSION
    payload[KEY_DATA_VERSION] = timestamp_version()
    payload[KEY_DATA_HASH] = compute_profiles_hash(payload)
    write_json(canonical_path, payload)
    if canonical_path.resolve() != deploy_path.resolve():
        deploy_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(deploy_path, payload)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate bringup tests into bringup_system.json.")
    parser.add_argument(
        "--path",
        default=str(DEFAULT_CANONICAL_PATH),
        help="Path to active bringup_system.json (default: src/main/deploy/bringup_system.json).",
    )
    parser.add_argument(
        "--deploy",
        default=str(DEFAULT_DEPLOY_PATH),
        help="Path to deploy bringup_system.json (default: src/main/deploy/bringup_system.json).",
    )
    parser.add_argument("--profile", default="", help="Profile name to edit (default: default_profile).")
    parser.add_argument("--test-set", default=DEFAULT_TEST_SET, help="Test set name to create/update.")
    parser.add_argument(
        "--devices",
        default="",
        help="Comma-separated device labels to generate tests for (default: all motor devices in the profile).",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the target test set instead of merging.",
    )
    parser.add_argument("--duty", type=float, default=DEFAULT_DUTY, help="Default duty for generated tests.")
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=DEFAULT_TIMEOUT_SEC,
        help="Timeout seconds for generated tests (time termination).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fail with an error instead of prompting for missing selections.",
    )
    return parser.parse_args()


def main() -> int:
    """
    NAME
        main - CLI entry point for the test generator.
    """

    args = _parse_args()
    canonical_path = Path(args.path)
    deploy_path = Path(args.deploy)

    if not canonical_path.exists():
        print(MSG_ERR_MISSING_CONFIG.format(path=canonical_path))
        return 2

    try:
        payload = _load_bringup_system(canonical_path)
    except Exception as exc:
        print(MSG_ERR_READ_CONFIG.format(path=canonical_path, error=exc))
        return 2

    ok, err = validate_profiles_schema(payload, PROFILE_SCHEMA_VERSION)
    if not ok:
        print(MSG_ERR_SCHEMA.format(error=err))
        return 2

    profile = args.profile.strip()
    if not profile:
        default_profile = payload.get(KEY_DEFAULT_PROFILE)
        if isinstance(default_profile, str) and default_profile.strip():
            profile = default_profile.strip()

    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict) or not profiles:
        print(MSG_ERR_NO_PROFILES)
        return 2

    if not profile or profile not in profiles:
        available = ", ".join(sorted([str(k) for k in profiles.keys()]))
        if args.non_interactive:
            print(MSG_ERR_PROFILE_SELECT.format(available=available))
            return 2
        print(MSG_AVAILABLE_PROFILES.format(available=available))
        profile = _prompt(MSG_PROMPT_PROFILE, next(iter(profiles.keys())))
        if profile not in profiles:
            print(MSG_ERR_PROFILE_UNKNOWN.format(profile=profile))
            return 2

    all_motors = _motor_labels_for_profile(payload, profile)
    if not all_motors:
        print(MSG_ERR_NO_MOTORS.format(profile=profile))
        return 2

    selected_raw = str(args.devices or "").strip()
    if not selected_raw and not args.non_interactive:
        selected_raw = _prompt(MSG_PROMPT_DEVICES, "")
    selected = [s.strip() for s in selected_raw.split(",") if s.strip()] if selected_raw else []

    motors = list(all_motors)
    if selected:
        selected_set = {label for label in selected}
        all_set = {label for label in _profile_device_labels(payload, profile)}
        missing = [label for label in selected if label not in all_set]
        if missing:
            print(MSG_ERR_DEVICES_UNKNOWN.format(profile=profile, labels=", ".join(missing)))
            return 2
        not_motors = [label for label in selected if label not in set(all_motors)]
        if not_motors:
            print(MSG_ERR_DEVICES_NOT_MOTORS.format(profile=profile, labels=", ".join(not_motors)))
            return 2
        motors = [label for label in all_motors if label in selected_set]

    set_name = str(args.test_set).strip() or DEFAULT_TEST_SET
    duty = float(args.duty)
    timeout_sec = float(args.timeout_sec)
    replace = bool(args.replace)

    if not args.non_interactive and not args.replace:
        replace = _prompt_yes_no(
            MSG_PROMPT_REPLACE.format(set_name=set_name),
            False,
        )

    tests_payload = _ensure_profile_tests(payload, profile)
    tests_payload[KEY_TESTS_DEFAULT_SET] = set_name

    new_tests = [_build_smoke_test(label, duty=duty, timeout_sec=timeout_sec) for label in motors]
    added, replaced_count = _upsert_test_set(tests_payload, set_name, new_tests, replace=replace)

    try:
        _finalize_and_write(payload, canonical_path, deploy_path)
    except Exception as exc:
        print(f"ERROR: failed to write outputs: {exc}")
        return 2

    print(MSG_UPDATED.format(profile=profile, set_name=set_name))
    print(MSG_COUNTS.format(motors=len(motors), added=added, replaced=replaced_count))
    print(MSG_WROTE.format(path=canonical_path))
    print(MSG_WROTE.format(path=deploy_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
