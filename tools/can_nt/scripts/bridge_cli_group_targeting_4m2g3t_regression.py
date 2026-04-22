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

KEY_BY_PROFILE = "byProfile"
KEY_ROBOT = "robot"
KEY_GROUPS = "groups"
KEY_NAME = "name"
KEY_MEMBERS = "members"
KEY_DEVICE = "device"
KEY_TESTS = "tests"
KEY_TEST_SETS = "test_sets"
KEY_DEFAULT = "default"
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
CMD_ADD_DEVICE_MOTOR1 = "add device motor1"
CMD_ADD_DEVICE_MOTOR2 = "add device motor2"
CMD_ADD_DEVICE_MOTOR3 = "add device motor3"
CMD_ADD_DEVICE_MOTOR4 = "add device motor4"

CMD_TEST_CREATE_1 = "test create spin_motor1"
CMD_TEST_CREATE_2 = "test create spin_motor2"
CMD_TEST_CREATE_3 = "test create spin_motor3"
CMD_TEST_DEVICE_ADD_1 = "device add motor1"
CMD_TEST_DEVICE_ADD_2 = "device add motor2"
CMD_TEST_DEVICE_ADD_3 = "device add motor3"
CMD_TEST_ENABLED_TRUE = "enabled true"
CMD_TEST_TERMINATION_HOLD = "termination hold"

CMD_SAVE_LOCAL_CONFIG_PREFIX = "save local-config "

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


def _build_actual_summary(cli: BridgeCli, saved_local_config: Dict[str, object]) -> Dict[str, object]:
    root_payload = cli._local_root_payload if isinstance(cli._local_root_payload, dict) else {}
    raw_devices = root_payload.get(KEY_DEVICES)
    device_entries = raw_devices if isinstance(raw_devices, list) else []
    device_labels = []
    for entry in device_entries:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, "")).strip()
        if label:
            device_labels.append(label)
    device_labels = sorted(device_labels)

    by_profile = saved_local_config.get(KEY_BY_PROFILE) if isinstance(saved_local_config, dict) else {}
    robot = by_profile.get(KEY_ROBOT) if isinstance(by_profile, dict) else {}

    raw_groups = robot.get(KEY_GROUPS) if isinstance(robot, dict) else []
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
            label = str(member.get(KEY_DEVICE, "")).strip()
            if label:
                labels.append(label)
        groups_map[group_name] = sorted(labels)

    tests_payload = robot.get(KEY_TESTS) if isinstance(robot, dict) else {}
    test_sets = tests_payload.get(KEY_TEST_SETS) if isinstance(tests_payload, dict) else {}
    default_tests = test_sets.get(KEY_DEFAULT) if isinstance(test_sets, dict) else []
    default_entries = default_tests if isinstance(default_tests, list) else []
    default_names = []
    for test in default_entries:
        if not isinstance(test, dict):
            continue
        test_name = str(test.get(KEY_NAME, "")).strip()
        if test_name:
            default_names.append(test_name)

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
        ("add motor1 to drive", CMD_ADD_DEVICE_MOTOR1, STATUS_OK_CODES),
        ("add motor2 to drive", CMD_ADD_DEVICE_MOTOR2, STATUS_OK_CODES),
        ("exit drive group", CMD_EXIT, STATUS_OK_CODES),
        ("create aux group", CMD_GROUP_CREATE_AUX, STATUS_OK_CODES),
        ("add motor3 to aux", CMD_ADD_DEVICE_MOTOR3, STATUS_OK_CODES),
        ("add motor4 to aux", CMD_ADD_DEVICE_MOTOR4, STATUS_OK_CODES),
        ("exit aux group", CMD_EXIT, STATUS_OK_CODES),
        ("create test spin_motor1", CMD_TEST_CREATE_1, STATUS_OK_CODES),
        ("test1 add device", CMD_TEST_DEVICE_ADD_1, STATUS_OK_CODES),
        ("test1 enabled", CMD_TEST_ENABLED_TRUE, STATUS_OK_CODES),
        ("test1 termination", CMD_TEST_TERMINATION_HOLD, STATUS_OK_CODES),
        ("exit test1", CMD_EXIT, STATUS_OK_CODES),
        ("create test spin_motor2", CMD_TEST_CREATE_2, STATUS_OK_CODES),
        ("test2 add device", CMD_TEST_DEVICE_ADD_2, STATUS_OK_CODES),
        ("test2 enabled", CMD_TEST_ENABLED_TRUE, STATUS_OK_CODES),
        ("test2 termination", CMD_TEST_TERMINATION_HOLD, STATUS_OK_CODES),
        ("exit test2", CMD_EXIT, STATUS_OK_CODES),
        ("create test spin_motor3", CMD_TEST_CREATE_3, STATUS_OK_CODES),
        ("test3 add device", CMD_TEST_DEVICE_ADD_3, STATUS_OK_CODES),
        ("test3 enabled", CMD_TEST_ENABLED_TRUE, STATUS_OK_CODES),
        ("test3 termination", CMD_TEST_TERMINATION_HOLD, STATUS_OK_CODES),
        ("exit test3", CMD_EXIT, STATUS_OK_CODES),
    ]

    for label, command, allowed_codes in command_sequence:
        code, out = _run_command(cli, command)
        results.append(_expect_code(label, code, allowed_codes, out))

    with tempfile.TemporaryDirectory() as temp_dir:
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

        actual_summary = _build_actual_summary(cli, actual_payload if isinstance(actual_payload, dict) else {})
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

