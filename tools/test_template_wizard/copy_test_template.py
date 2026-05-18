from __future__ import annotations

"""
NAME
    copy_test_template.py - Apply a tests template to unified config.

SYNOPSIS
    python -m tools.test_template_wizard.copy_test_template [--path PATH] [--profile NAME]

DESCRIPTION
    Loads a tests template JSON (test_sets/default_test_set), optionally edits
    device labels interactively, and stores the result under:
      bringup_system.json -> bridgeConfig.byProfile.<profile>.tests

    This keeps templates useful while enforcing the repo's supported storage
    location for tests.

SIDE EFFECTS
    Reads template files, prompts on stdin, writes bringup_system.json and its
    deploy copy.
"""

import argparse
import os
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
    KEY_PROFILES,
    KEY_SCHEMA_VERSION,
    PROFILE_SCHEMA_VERSION,
)
from tools.common.profile_io import compute_profiles_hash, validate_profiles_schema
from tools.common.time_utils import timestamp_version


TEMPLATE_DIR = Path(__file__).resolve().parent / "test_templates"

DEFAULT_CANONICAL_PATH = Path("src") / "main" / "deploy" / "bringup_system.json"
DEFAULT_DEPLOY_PATH = Path("src") / "main" / "deploy" / "bringup_system.json"

KEY_TESTS_DEFAULT_SET = "default_test_set"
KEY_TESTS_SETS = "test_sets"
KEY_TESTS_TESTS = "tests"

FIELD_TEST_NAME = "name"
FIELD_TEST_MOTOR_LABELS = "motorLabels"
FIELD_TEST_ROTATION = "rotation"
FIELD_TEST_ENCODER_KEY = "encoderKey"

ENCODER_INTERNAL = "internal"
MSG_HINT_NUMBER = "Enter a number."

# Constants (messages).
MSG_ERR_CONFIG_MISSING = "ERROR: bringup_system.json not found: {path}"
MSG_ERR_NO_TEMPLATES = "ERROR: no templates found in {path}"
MSG_ERR_TEMPLATE_NOT_FOUND = "ERROR: template not found: {path}"
MSG_ERR_TEMPLATE_REQUIRED = "ERROR: --template is required in --non-interactive mode."
MSG_ERR_READ_TEMPLATE = "ERROR: failed to read template {path}: {error}"
MSG_ERR_TEMPLATE_SHAPE = "ERROR: template {path} must be a JSON object."
MSG_ERR_READ_CONFIG = "ERROR: failed to read {path}: {error}"
MSG_ERR_ROOT_OBJECT = "ERROR: bringup_system.json root must be a JSON object."
MSG_ERR_SCHEMA = "ERROR: bringup_system.json schema invalid: {error}"
MSG_ERR_NO_PROFILES = "ERROR: bringup_system.json has no profiles."
MSG_ERR_PROFILE_SELECT = "ERROR: profile not selected or not found. Available: {available}"
MSG_AVAILABLE_PROFILES = "Available profiles: {available}"
MSG_ERR_PROFILE_UNKNOWN = "ERROR: unknown profile: {profile}"
MSG_ERR_WRITE = "ERROR: failed to write outputs: {error}"
MSG_APPLIED = "Applied template '{template}' to profile '{profile}'."
MSG_WROTE = "Wrote: {path}"


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


def _list_templates() -> List[Path]:
    """
    NAME
        _list_templates - Return available JSON templates.
    """

    if not TEMPLATE_DIR.exists():
        return []
    return sorted([p for p in TEMPLATE_DIR.glob("*.json") if p.is_file()])


def _choose_template(templates: List[Path]) -> Path:
    """
    NAME
        _choose_template - Prompt for a template selection.

    RETURNS
        Path to the chosen template.
    """

    print("Available templates:")
    for idx, tpl in enumerate(templates, start=1):
        print(f"  {idx}. {tpl.name}")
    while True:
        raw = _prompt("Select template by number", "1")
        try:
            choice = int(raw)
        except (TypeError, ValueError):
            print(MSG_HINT_NUMBER)
            continue
        if 1 <= choice <= len(templates):
            return templates[choice - 1]
        print("Out of range.")


def _ensure_test_sets(payload: Dict[str, object]) -> Dict[str, object]:
    """
    NAME
        _ensure_test_sets - Normalize payloads to test_sets format.
    """

    if not isinstance(payload, dict):
        payload = {}
    test_sets = payload.get(KEY_TESTS_SETS)
    if isinstance(test_sets, dict):
        if KEY_TESTS_DEFAULT_SET not in payload:
            payload[KEY_TESTS_DEFAULT_SET] = "default"
        return payload
    tests = payload.get(KEY_TESTS_TESTS, [])
    if not isinstance(tests, list):
        tests = []
    return {
        KEY_TESTS_DEFAULT_SET: payload.get(KEY_TESTS_DEFAULT_SET, "default"),
        KEY_TESTS_SETS: {"default": tests},
    }


def _edit_tests(payload: Dict[str, object]) -> Dict[str, object]:
    """
    NAME
        _edit_tests - Interactive editing of test entries.

    DESCRIPTION
        Updates motor labels and encoder keys in-place based on user input.
    """

    set_name = payload.get(KEY_TESTS_DEFAULT_SET) or "default"
    test_sets = payload.get(KEY_TESTS_SETS, {})
    if not isinstance(test_sets, dict):
        test_sets = {}
    tests = test_sets.get(set_name, [])
    if not isinstance(tests, list):
        tests = []
    for idx, test in enumerate(tests, start=1):
        if not isinstance(test, dict):
            continue
        name = test.get(FIELD_TEST_NAME, f"Test {idx}")
        print(f"\nTest {idx}: {name}")
        motor_labels = test.get(FIELD_TEST_MOTOR_LABELS)
        if isinstance(motor_labels, list) and motor_labels:
            default_labels = ", ".join([str(v) for v in motor_labels])
            new_labels = _prompt("Motor labels (comma-separated)", default_labels)
            labels = [part.strip() for part in (new_labels or "").split(",") if part.strip()]
            if labels:
                test[FIELD_TEST_MOTOR_LABELS] = labels
        rotation = test.get(FIELD_TEST_ROTATION)
        if isinstance(rotation, dict):
            encoder_key = rotation.get(FIELD_TEST_ENCODER_KEY)
            if isinstance(encoder_key, str) and encoder_key and encoder_key.lower() != ENCODER_INTERNAL:
                new_encoder = _prompt("Encoder (internal or device label)", encoder_key)
                rotation[FIELD_TEST_ENCODER_KEY] = new_encoder
        tests[idx - 1] = test
    test_sets[set_name] = tests
    payload[KEY_TESTS_SETS] = test_sets
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


def _set_profile_tests(payload: Dict[str, object], profile: str, tests_payload: Dict[str, object]) -> None:
    """
    NAME
        _set_profile_tests - Replace bridgeConfig.byProfile.<profile>.tests.
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
    entry[KEY_BRIDGE_TESTS] = tests_payload


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
    parser = argparse.ArgumentParser(description="Apply a test template to bringup_system.json.")
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
    parser.add_argument("--template", default="", help="Template filename (optional; otherwise prompt).")
    parser.add_argument(
        "--no-edit",
        action="store_true",
        help="Skip interactive label editing; apply template as-is.",
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
        main - CLI entry point for template copying.
    """

    args = _parse_args()
    canonical_path = Path(args.path)
    deploy_path = Path(args.deploy)
    if not canonical_path.exists():
        print(MSG_ERR_CONFIG_MISSING.format(path=canonical_path))
        return 2

    templates = _list_templates()
    if not templates:
        print(MSG_ERR_NO_TEMPLATES.format(path=TEMPLATE_DIR))
        return 2

    template_path: Optional[Path] = None
    if args.template:
        candidate = TEMPLATE_DIR / args.template
        if not candidate.exists():
            print(MSG_ERR_TEMPLATE_NOT_FOUND.format(path=candidate))
            return 2
        template_path = candidate
    elif args.non_interactive:
        print(MSG_ERR_TEMPLATE_REQUIRED)
        return 2
    else:
        template_path = _choose_template(templates)

    try:
        template_payload = read_json(template_path)
    except Exception as exc:
        print(MSG_ERR_READ_TEMPLATE.format(path=template_path, error=exc))
        return 2
    if not isinstance(template_payload, dict):
        print(MSG_ERR_TEMPLATE_SHAPE.format(path=template_path))
        return 2

    tests_payload = _ensure_test_sets(template_payload)
    if not args.no_edit and not args.non_interactive:
        tests_payload = _edit_tests(tests_payload)

    try:
        payload = read_json(canonical_path)
    except Exception as exc:
        print(MSG_ERR_READ_CONFIG.format(path=canonical_path, error=exc))
        return 2
    if not isinstance(payload, dict):
        print(MSG_ERR_ROOT_OBJECT)
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
        profile = _prompt("Profile", next(iter(profiles.keys())))
        if profile not in profiles:
            print(MSG_ERR_PROFILE_UNKNOWN.format(profile=profile))
            return 2

    _set_profile_tests(payload, profile, tests_payload)
    try:
        _finalize_and_write(payload, canonical_path, deploy_path)
    except Exception as exc:
        print(MSG_ERR_WRITE.format(error=exc))
        return 2

    print(MSG_APPLIED.format(template=template_path.name, profile=profile))
    print(MSG_WROTE.format(path=canonical_path))
    print(MSG_WROTE.format(path=deploy_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
