from __future__ import annotations

"""
NAME
    bridge_cli_group_targeting_4m2g3t_regression.py - Local regression using premade 4m/2g/3t expected config summary.

SYNOPSIS
    python tools/can_nt/scripts/bridge_cli_group_targeting_4m2g3t_regression.py

DESCRIPTION
    Creates four motors, two groups, and three tests in local/batch mode, saves
    local config, and compares normalized actual results against a premade
    expected summary JSON.

NOTES
    This script does not require a connected robot.
"""

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

REPO_ROOT_DEPTH = 3
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.can_nt.bridge_cli import BridgeCli
from tools.can_nt.bridge_session import BridgeSession
from tools.can_nt.status import SS__CONFIG__SAVED, SS__NETWORK__NOT_CONNECTED, SS__NORMAL

RIO_HOST_LOOPBACK = "127.0.0.1"
TCP_PORT_DUMMY = 9999
STATUS_OK_CODES = (SS__NORMAL, SS__NETWORK__NOT_CONNECTED)

EXPECTED_SUMMARY_RELATIVE = Path("tests/regression/expected/group_targeting_4m2g3t_expected_summary.json")
DSL_TEMPLATE = 'test "{name}"\ndevice "{device}"\n\nmain:\n    until timer.elapsed >= 1.0\n'

KEY_DEFAULT_PROFILE = "default_profile"
KEY_PROFILES = "profiles"
KEY_BY_PROFILE = "byProfile"
KEY_BRIDGE_CONFIG = "bridgeConfig"
KEY_DSL_TESTS = "dslTests"
KEY_GROUPS = "groups"
KEY_NAME = "name"
KEY_MEMBERS = "members"
KEY_DEVICE = "device"
KEY_LABEL = "label"
KEY_TESTS = "tests"
KEY_TEST_SETS = "testSets"
KEY_DEFAULT = "default"
KEY_DEFAULT_SET = "defaultSet"
KEY_DEVICES = "devices"
KEY_LABEL = "label"

CMD_CONFIGURE_TERMINAL = "configure terminal"
CMD_EXIT = "exit"

CMD_DEVICE_MOTOR1 = "device motor1"
CMD_DEVICE_MOTOR2 = "device motor2"
CMD_DEVICE_MOTOR3 = "device motor3"
CMD_DEVICE_MOTOR4 = "device motor4"

CMD_DEVICE_INTERFACE_CAN = "deviceInterface CAN"
CMD_DEVICE_MANUFACTURER_REV = "manufacturer 5"
CMD_DEVICE_TYPE_MOTOR = "deviceType 2"

CMD_ID_21 = "id 21"
CMD_ID_22 = "id 22"
CMD_ID_23 = "id 23"
CMD_ID_24 = "id 24"

CMD_GROUP_CREATE_DRIVE = "group create drive"
CMD_GROUP_CREATE_AUX = "group create aux"
CMD_MEMBER_ASSIGN_MOTOR1 = "member assign motor1"
CMD_MEMBER_ASSIGN_MOTOR2 = "member assign motor2"
CMD_MEMBER_ASSIGN_MOTOR3 = "member assign motor3"
CMD_MEMBER_ASSIGN_MOTOR4 = "member assign motor4"

CMD_TEST_IMPORT_PREFIX = "test import "
CMD_SET_DEFAULT = " set default"
CMD_SAVE_LOCAL_CONFIG_PREFIX = "save config "

OUTCOME_PASS = "PASS"
OUTCOME_FAIL = "FAIL"
LABEL_SUMMARY = "SUMMARY"

DETAIL_EXPECTED_SUMMARY_NOT_FOUND = "expected summary fixture missing"
DETAIL_EXPECTED_SUMMARY_LOAD_FAILED = "expected summary fixture load failed"
DETAIL_ACTUAL_SUMMARY_LOAD_FAILED = "actual local config load failed"


@dataclass
class CheckResult:
    label: str
    ok: bool
    details: str


def _run_command(cli: BridgeCli, command: str) -> Tuple[int, str]:
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        status = cli._execute_line(command)
    return status.code, output_buffer.getvalue()


def _expect_code(label: str, actual_code: int, expected_codes: Iterable[int], output: str) -> CheckResult:
    allowed = tuple(expected_codes)
    ok = actual_code in allowed
    details = f"code={actual_code} allowed={allowed}"
    if not ok:
        details = details + f" output={output.strip()}"
    return CheckResult(label=label, ok=ok, details=details)


def _new_cli() -> BridgeCli:
    session = BridgeSession(RIO_HOST_LOOPBACK, TCP_PORT_DUMMY, auto_handshake=False)
    return BridgeCli(session, batch=True)


def _load_json(path: Path) -> Tuple[bool, object]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return True, json.load(handle)
    except Exception:
        return False, None


def _build_actual_summary(saved_local_config: Dict[str, object]) -> Dict[str, object]:
    raw_devices = saved_local_config.get(KEY_DEVICES)
    device_entries = raw_devices if isinstance(raw_devices, list) else []
    device_labels = []
    for entry in device_entries:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, "")).strip()
        if label:
            device_labels.append(label)
    device_labels = sorted(device_labels)

    default_profile = str(saved_local_config.get(KEY_DEFAULT_PROFILE, "")).strip()
    bridge_config = saved_local_config.get(KEY_BRIDGE_CONFIG)
    by_profile = bridge_config.get(KEY_BY_PROFILE) if isinstance(bridge_config, dict) else {}
    profile_payload = by_profile.get(default_profile) if isinstance(by_profile, dict) else {}

    raw_groups = profile_payload.get(KEY_GROUPS) if isinstance(profile_payload, dict) else []
    groups = raw_groups if isinstance(raw_groups, list) else []
    groups_map: Dict[str, List[str]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_name = str(group.get(KEY_NAME, "")).strip()
        if not group_name:
            continue
        raw_members = group.get(KEY_MEMBERS)
        members = raw_members if isinstance(raw_members, list) else []
        labels: List[str] = []
        for member in members:
            if not isinstance(member, dict):
                continue
            label = str(member.get(KEY_LABEL, member.get(KEY_DEVICE, ""))).strip()
            if label:
                labels.append(label)
        groups_map[group_name] = sorted(labels)

    dsl_tests = saved_local_config.get(KEY_DSL_TESTS)
    default_set_name = str(dsl_tests.get(KEY_DEFAULT_SET, "")).strip() if isinstance(dsl_tests, dict) else ""
    test_sets = dsl_tests.get(KEY_TEST_SETS) if isinstance(dsl_tests, dict) else {}
    default_entries = test_sets.get(default_set_name) if isinstance(test_sets, dict) else []
    default_names = [str(test_name).strip() for test_name in default_entries if str(test_name).strip()]

    return {
        "devices": sorted(device_labels),
        "groups": {name: groups_map[name] for name in sorted(groups_map.keys())},
        "tests": {KEY_DEFAULT: sorted(default_names)},
    }


def _run_regression() -> List[CheckResult]:
    results: List[CheckResult] = []
    cli = _new_cli()

    command_sequence: List[Tuple[str, str, Tuple[int, ...]]] = [
        ("enter config", CMD_CONFIGURE_TERMINAL, STATUS_OK_CODES),
        ("create motor1", CMD_DEVICE_MOTOR1, STATUS_OK_CODES),
        ("set motor1 interface", CMD_DEVICE_INTERFACE_CAN, STATUS_OK_CODES),
        ("set motor1 manufacturer", CMD_DEVICE_MANUFACTURER_REV, STATUS_OK_CODES),
        ("set motor1 deviceType", CMD_DEVICE_TYPE_MOTOR, STATUS_OK_CODES),
        ("set motor1 id", CMD_ID_21, STATUS_OK_CODES),
        ("exit motor1", CMD_EXIT, STATUS_OK_CODES),
        ("create motor2", CMD_DEVICE_MOTOR2, STATUS_OK_CODES),
        ("set motor2 interface", CMD_DEVICE_INTERFACE_CAN, STATUS_OK_CODES),
        ("set motor2 manufacturer", CMD_DEVICE_MANUFACTURER_REV, STATUS_OK_CODES),
        ("set motor2 deviceType", CMD_DEVICE_TYPE_MOTOR, STATUS_OK_CODES),
        ("set motor2 id", CMD_ID_22, STATUS_OK_CODES),
        ("exit motor2", CMD_EXIT, STATUS_OK_CODES),
        ("create motor3", CMD_DEVICE_MOTOR3, STATUS_OK_CODES),
        ("set motor3 interface", CMD_DEVICE_INTERFACE_CAN, STATUS_OK_CODES),
        ("set motor3 manufacturer", CMD_DEVICE_MANUFACTURER_REV, STATUS_OK_CODES),
        ("set motor3 deviceType", CMD_DEVICE_TYPE_MOTOR, STATUS_OK_CODES),
        ("set motor3 id", CMD_ID_23, STATUS_OK_CODES),
        ("exit motor3", CMD_EXIT, STATUS_OK_CODES),
        ("create motor4", CMD_DEVICE_MOTOR4, STATUS_OK_CODES),
        ("set motor4 interface", CMD_DEVICE_INTERFACE_CAN, STATUS_OK_CODES),
        ("set motor4 manufacturer", CMD_DEVICE_MANUFACTURER_REV, STATUS_OK_CODES),
        ("set motor4 deviceType", CMD_DEVICE_TYPE_MOTOR, STATUS_OK_CODES),
        ("set motor4 id", CMD_ID_24, STATUS_OK_CODES),
        ("exit motor4", CMD_EXIT, STATUS_OK_CODES),
        ("create drive group", CMD_GROUP_CREATE_DRIVE, STATUS_OK_CODES),
        ("add motor1 to drive", CMD_MEMBER_ASSIGN_MOTOR1, STATUS_OK_CODES),
        ("add motor2 to drive", CMD_MEMBER_ASSIGN_MOTOR2, STATUS_OK_CODES),
        ("exit drive group", CMD_EXIT, STATUS_OK_CODES),
        ("create aux group", CMD_GROUP_CREATE_AUX, STATUS_OK_CODES),
        ("add motor3 to aux", CMD_MEMBER_ASSIGN_MOTOR3, STATUS_OK_CODES),
        ("add motor4 to aux", CMD_MEMBER_ASSIGN_MOTOR4, STATUS_OK_CODES),
        ("exit aux group", CMD_EXIT, STATUS_OK_CODES),
    ]

    for label, command, allowed_codes in command_sequence:
        code, out = _run_command(cli, command)
        results.append(_expect_code(label, code, allowed_codes, out))

    with tempfile.TemporaryDirectory() as temp_dir:
        for test_name, device_name in (
            ("spin_motor1", "motor1"),
            ("spin_motor2", "motor2"),
            ("spin_motor3", "motor3"),
        ):
            source_path = Path(temp_dir) / f"{test_name}.dsl"
            source_path.write_text(DSL_TEMPLATE.format(name=test_name, device=device_name), encoding="utf-8")
            command = CMD_TEST_IMPORT_PREFIX + f"{test_name} {source_path}" + CMD_SET_DEFAULT
            code, out = _run_command(cli, command)
            results.append(_expect_code(f"import {test_name}", code, STATUS_OK_CODES, out))

        saved_path = Path(temp_dir) / "group_targeting_4m2g3t_local_config.json"
        save_command = CMD_SAVE_LOCAL_CONFIG_PREFIX + str(saved_path)
        code, out = _run_command(cli, save_command)
        results.append(_expect_code("save local config", code, (SS__CONFIG__SAVED, SS__NORMAL), out))

        expected_path = REPO_ROOT / EXPECTED_SUMMARY_RELATIVE
        if not expected_path.exists():
            results.append(CheckResult("summary matches expected", False, DETAIL_EXPECTED_SUMMARY_NOT_FOUND))
            return results

        ok_expected, expected_payload = _load_json(expected_path)
        ok_actual, actual_payload = _load_json(saved_path)
        if not ok_expected:
            results.append(CheckResult("summary matches expected", False, DETAIL_EXPECTED_SUMMARY_LOAD_FAILED))
            return results
        if not ok_actual:
            results.append(CheckResult("summary matches expected", False, DETAIL_ACTUAL_SUMMARY_LOAD_FAILED))
            return results

        actual_summary = _build_actual_summary(actual_payload if isinstance(actual_payload, dict) else {})
        expected_summary = expected_payload if isinstance(expected_payload, dict) else {}
        matches = actual_summary == expected_summary
        detail = "summary equality"
        if not matches:
            detail = detail + " mismatch"
        results.append(CheckResult("summary matches expected", matches, detail))

    return results


def _print_results(results: List[CheckResult]) -> int:
    failures = 0
    for result in results:
        outcome = OUTCOME_PASS if result.ok else OUTCOME_FAIL
        print(f"[{outcome}] {result.label}: {result.details}")
        if not result.ok:
            failures += 1
    total = len(results)
    passed = total - failures
    print(f"{LABEL_SUMMARY}: passed={passed} failed={failures} total={total}")
    return 0 if failures == 0 else 1


def main() -> int:
    results = _run_regression()
    return _print_results(results)


if __name__ == "__main__":
    raise SystemExit(main())
