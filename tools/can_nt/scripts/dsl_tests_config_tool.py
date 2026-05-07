from __future__ import annotations

"""
NAME
    dsl_tests_config_tool.py - File-based import/export/validate tool for DSL tests.

SYNOPSIS
    python tools/can_nt/scripts/dsl_tests_config_tool.py import --config data/bringup_system.json --profile robot --test spin --source spin.dsl
"""

import argparse
import json
from pathlib import Path
import sys

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.common.json_io import read_json, write_json
from tools.common.profile_constants import (
    KEY_DEFAULT_PROFILE,
    KEY_DSL_DEFAULT_SET,
    KEY_DSL_TEST_SET,
    KEY_DSL_TEST_SETS,
    KEY_DSL_TESTS,
    KEY_DSL_TESTS_BY_NAME,
    KEY_PROFILES,
)
from tools.common.robot_test_dsl import (
    DEFAULT_TEST_SET,
    RobotTestDslEntry,
    RobotTestDslStore,
    compile_source,
    store_from_payload,
    store_to_payload,
    source_hash,
    validate_store,
)


GENERATED_SIGNALS_PATH = REPO_ROOT / "tools" / "common" / "generated" / "robot_test_dsl_signals.json"
KEY_NORMALIZED = "normalized"


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", required=True)
    common.add_argument("--profile")

    import_parser = sub.add_parser("import", parents=[common])
    import_parser.add_argument("--test", required=True)
    import_parser.add_argument("--source", required=True)
    import_parser.add_argument("--set", dest="set_name", default=DEFAULT_TEST_SET)

    export_parser = sub.add_parser("export", parents=[common])
    export_parser.add_argument("--test", required=True)
    export_parser.add_argument("--out", required=True)

    show_parser = sub.add_parser("show", parents=[common])
    show_parser.add_argument("--test")
    show_parser.add_argument("--normalized", action="store_true")

    validate_parser = sub.add_parser("validate", parents=[common])
    validate_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    path = Path(args.config)
    payload = read_json(path)
    if not isinstance(payload, dict):
        print("ERROR: config payload must be a JSON object.")
        return 1
    profile_name = args.profile or str(payload.get(KEY_DEFAULT_PROFILE, "")).strip()
    if args.command == "import":
        return _import_test(payload, path, profile_name, args.test, Path(args.source), args.set_name)
    if args.command == "export":
        return _export_test(payload, args.test, Path(args.out))
    if args.command == "show":
        return _show_tests(payload, args.test, args.normalized)
    if args.command == "validate":
        return _validate(payload, profile_name, emit_json=args.json)
    return 1


def _load_store(payload: dict) -> RobotTestDslStore:
    dsl_payload = payload.get(KEY_DSL_TESTS)
    return store_from_payload(dsl_payload if isinstance(dsl_payload, dict) else {})


def _save_store(payload: dict, path: Path, store: RobotTestDslStore) -> int:
    payload[KEY_DSL_TESTS] = store_to_payload(store)
    write_json(path, payload)
    return 0


def _ensure_profile_set_reference(payload: dict, profile_name: str, set_name: str) -> None:
    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict):
        payload[KEY_PROFILES] = {}
        profiles = payload[KEY_PROFILES]
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        profiles[profile_name] = {"devices": [], KEY_DSL_TEST_SET: set_name}
        return
    profile[KEY_DSL_TEST_SET] = set_name


def _import_test(payload: dict, config_path: Path, profile_name: str, test_name: str, source_path: Path, set_name: str) -> int:
    source = source_path.read_text(encoding="utf-8")
    normalized = compile_source(test_name, source)
    store = _load_store(payload)
    store.tests_by_name[test_name] = RobotTestDslEntry(
        name=test_name,
        source=source,
        normalized=normalized,
        source_hash=source_hash(source),
    )
    names = list(store.test_sets.get(set_name, []))
    if test_name not in names:
        names.append(test_name)
    store.test_sets[set_name] = names
    if not store.default_set:
        store.default_set = set_name
    _ensure_profile_set_reference(payload, profile_name, set_name)
    result = _validate_store_against_generated(store, payload, profile_name)
    if not result.ok():
        _print_validation(result)
        return 1
    return _save_store(payload, config_path, store)


def _export_test(payload: dict, test_name: str, out_path: Path) -> int:
    store = _load_store(payload)
    entry = store.tests_by_name.get(test_name)
    if entry is None:
        print(f"ERROR: test not found: {test_name}")
        return 1
    out_path.write_text(entry.source, encoding="utf-8")
    return 0


def _show_tests(payload: dict, test_name: str | None, normalized: bool) -> int:
    store = _load_store(payload)
    if test_name:
        entry = store.tests_by_name.get(test_name)
        if entry is None:
            print(f"ERROR: test not found: {test_name}")
            return 1
        if normalized:
            print(json.dumps(store_to_payload(RobotTestDslStore(tests_by_name={test_name: entry}, test_sets={}, default_set=store.default_set))[KEY_DSL_TESTS_BY_NAME][test_name][KEY_NORMALIZED], indent=2))
        else:
            print(entry.source)
        return 0
    print(json.dumps(store_to_payload(store), indent=2))
    return 0


def _validate(payload: dict, profile_name: str, emit_json: bool) -> int:
    store = _load_store(payload)
    result = _validate_store_against_generated(store, payload, profile_name)
    if emit_json:
        print(
            json.dumps(
                {
                    "errors": [issue.__dict__ for issue in result.errors],
                    "warnings": [issue.__dict__ for issue in result.warnings],
                },
                indent=2,
            )
        )
    else:
        _print_validation(result)
    return 0 if result.ok() else 1


def _validate_store_against_generated(store: RobotTestDslStore, payload: dict, profile_name: str):
    signals_payload = read_json(GENERATED_SIGNALS_PATH)
    signal_catalog = {}
    if isinstance(signals_payload, dict):
        device_types = signals_payload.get("deviceTypes")
        if isinstance(device_types, dict):
            signal_catalog = {str(name): value for name, value in device_types.items() if isinstance(value, dict)}
    device_catalog = {}
    profiles = payload.get(KEY_PROFILES)
    devices = payload.get("devices")
    if isinstance(profiles, dict) and profile_name not in profiles:
        from tools.common.robot_test_dsl.validator import ValidationIssue, ValidationResult

        return ValidationResult(errors=[ValidationIssue(f"unknown profile: {profile_name}")])
    if isinstance(profiles, dict) and isinstance(devices, list) and profile_name in profiles and isinstance(profiles[profile_name], dict):
        selected = profiles[profile_name].get("devices", [])
        by_label = {str(item.get("label")): item for item in devices if isinstance(item, dict) and isinstance(item.get("label"), str)}
        for label in selected if isinstance(selected, list) else []:
            if isinstance(label, str) and label in by_label:
                device_catalog[label] = by_label[label]
    return validate_store(store, device_catalog, signal_catalog)


def _print_validation(result) -> None:
    if not result.errors and not result.warnings:
        print("OK")
        return
    for issue in result.errors:
        print(f"ERROR: {issue.test_name or '-'}: {issue.message}")
    for issue in result.warnings:
        print(f"WARNING: {issue.test_name or '-'}: {issue.message}")


if __name__ == "__main__":
    raise SystemExit(main())
