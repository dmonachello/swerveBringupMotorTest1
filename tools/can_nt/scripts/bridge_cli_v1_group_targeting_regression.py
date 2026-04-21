from __future__ import annotations

"""
NAME
    bridge_cli_v1_group_targeting_regression.py - Local V1 group/targeting regression checks.

SYNOPSIS
    python tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py

DESCRIPTION
    Runs a deterministic, no-hardware regression sequence against BridgeCli in
    batch mode to verify Group and Targeting V1 behavior on the host/local path.

NOTES
    This script does not connect to a roboRIO and does not access CAN/NT.
"""

import io
import sys
import tempfile
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Tuple

REPO_ROOT_DEPTH = 3
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.can_nt.bridge_cli import BridgeCli
from tools.can_nt.bridge_session import BridgeSession
from tools.can_nt.status import (
    SS__CLI_PARSER__INVALID_SYNTAX,
    SS__CONFIG__SAVED,
    SS__CONFIG__DUPLICATE_LABEL,
    SS__CONFIG__INVALID,
    SS__DEVICE__NOT_DEFINED,
    SS__NETWORK__NOT_CONNECTED,
    SS__NORMAL,
)

RIO_HOST_LOOPBACK = "127.0.0.1"
TCP_PORT_DUMMY = 9999
STATUS_OK_CODES = (SS__NORMAL, SS__NETWORK__NOT_CONNECTED)

CMD_CONFIGURE_TERMINAL = "configure terminal"
CMD_EXIT = "exit"
CMD_END = "end"
CMD_GROUP_CREATE_INTAKE = "group create intake"
CMD_GROUP_CREATE_INTAKE_MIXED_CASE = "group create INTAKE"
CMD_GROUP_CREATE_SHOOTER = "group create shooter"
CMD_GROUP_ACTIVE = "group active"
CMD_GROUP_INTAKE = "group intake"
CMD_GROUP_DELETE_ACTIVE = "group delete active"
CMD_GROUP_CLEAR_ACTIVE = "group clear active"
CMD_GROUP_CLEAR_INTAKE = "group clear intake"
CMD_GROUP_CLEAR_INTAKE_V2 = "group clear intake_v2"
CMD_GROUP_RENAME_INTAKE_INTAKE_V2 = "group rename intake intake_v2"
CMD_GROUP_INTAKE_V2 = "group intake_v2"
CMD_ADD_NEXT = "add next"
CMD_ADD_NEXT_GROUP_ACTIVE = "add next group active"
CMD_ADD_ALL_GROUP_INTAKE = "add all group intake"
CMD_ADD_ALL_GROUP_INTAKE_V2 = "add all group intake_v2"
CMD_COPY_GROUP_INTAKE_ACTIVE = "copy group intake active"
CMD_COPY_GROUP_INTAKE_SHOOTER = "copy group intake shooter"
CMD_COPY_GROUP_INTAKE_V2_ACTIVE = "copy group intake_v2 active"
CMD_COPY_GROUP_INTAKE_V2_SHOOTER = "copy group intake_v2 shooter"
CMD_COPY_GROUP_ACTIVE_ACTIVE = "copy group active active"
CMD_DEVICE_MOTOR1 = "device motor1"
CMD_DEVICE_MOTOR2 = "device motor2"
CMD_DEVICE_INTERFACE_CAN = "deviceInterface CAN"
CMD_DEVICE_MANUFACTURER_REV = "manufacturer 5"
CMD_DEVICE_TYPE_MOTOR_CONTROLLER = "deviceType 2"
CMD_DEVICE_ID_25 = "id 25"
CMD_DEVICE_ID_26 = "id 26"
CMD_SHOW_DEVICE_MOTOR1_JSON = "show device motor1 --json --pretty"
CMD_SHOW_DEVICE_REGISTRY_MOTOR1 = "show device registry motor1"
CMD_ADD_DEVICE_MOTOR1 = "add device motor1"
CMD_REMOVE_DEVICE_MOTOR1 = "remove device motor1"
CMD_SAVE_LOCAL_CONFIG_PREFIX = "save local-config "
FLAG_FORCE = " --force"

MSG_WARNING_DUPLICATE = "WARNING: device already in group"
MSG_WARNING_MISSING = "WARNING: device not in group"
MSG_ERROR_NO_DEVICE_NEXT = "ERROR: no device available for add next."
MSG_ERROR_COPY_NON_INTERACTIVE = "ERROR: non-interactive copy to existing group"
MSG_ERROR_COPY_SAME_SOURCE_DEST = "ERROR: source and destination are the same"
MSG_JSON_LABEL_MOTOR1 = '"label": "motor1"'
MSG_HINT_SHOW = "HINT: show <target>"

OUTCOME_PASS = "PASS"
OUTCOME_FAIL = "FAIL"
LABEL_SUMMARY = "SUMMARY"


@dataclass
class CheckResult:
    """
    NAME
        CheckResult - Single assertion outcome.
    """

    label: str
    ok: bool
    details: str


def _run_command(cli: BridgeCli, command: str) -> Tuple[int, str]:
    """
    NAME
        _run_command - Execute one CLI line and capture stdout.

    RETURNS
        (status_code, stdout_text)
    """
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        status = cli._execute_line(command)
    return status.code, buffer.getvalue()


def _expect_code(
    label: str,
    actual_code: int,
    expected_codes: Iterable[int],
    output: str,
) -> CheckResult:
    """
    NAME
        _expect_code - Validate a status code against an allowed set.
    """
    allowed = tuple(expected_codes)
    ok = actual_code in allowed
    detail = f"code={actual_code} allowed={allowed}"
    if not ok:
        detail = detail + f" output={output.strip()}"
    return CheckResult(label=label, ok=ok, details=detail)


def _expect_contains(label: str, output: str, required: str) -> CheckResult:
    """
    NAME
        _expect_contains - Validate required substring in command output.
    """
    ok = required in output
    detail = f"contains={required!r}"
    if not ok:
        detail = detail + f" output={output.strip()}"
    return CheckResult(label=label, ok=ok, details=detail)


def _expect_not_code(label: str, actual_code: int, forbidden_codes: Iterable[int], output: str) -> CheckResult:
    """
    NAME
        _expect_not_code - Validate status code is not in a forbidden set.
    """
    forbidden = tuple(forbidden_codes)
    ok = actual_code not in forbidden
    detail = f"code={actual_code} forbidden={forbidden}"
    if not ok:
        detail = detail + f" output={output.strip()}"
    return CheckResult(label=label, ok=ok, details=detail)


def _new_cli() -> BridgeCli:
    """
    NAME
        _new_cli - Construct a disconnected batch BridgeCli for local tests.
    """
    session = BridgeSession(RIO_HOST_LOOPBACK, TCP_PORT_DUMMY, auto_handshake=False)
    return BridgeCli(session, batch=True)


def _run_regression() -> List[CheckResult]:
    """
    NAME
        _run_regression - Execute V1 regression command sequence.
    """
    results: List[CheckResult] = []
    cli = _new_cli()

    code, out = _run_command(cli, CMD_CONFIGURE_TERMINAL)
    results.append(_expect_code("enter config", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_ADD_NEXT)
    results.append(_expect_code("add next without devices fails", code, (SS__CONFIG__INVALID,), out))
    results.append(_expect_contains("add next missing device message", out, MSG_ERROR_NO_DEVICE_NEXT))

    code, out = _run_command(cli, CMD_GROUP_CREATE_INTAKE)
    results.append(_expect_code("create intake", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_GROUP_CREATE_INTAKE_MIXED_CASE)
    results.append(
        _expect_code(
            "create duplicate intake case-insensitive",
            code,
            (SS__CONFIG__DUPLICATE_LABEL, SS__CONFIG__INVALID),
            out,
        )
    )

    code, out = _run_command(cli, CMD_EXIT)
    results.append(_expect_code("exit intake context after create", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_GROUP_ACTIVE)
    results.append(_expect_code("enter active context", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_EXIT)
    results.append(_expect_code("exit active context", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_GROUP_INTAKE)
    results.append(_expect_code("enter intake context", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_ADD_DEVICE_MOTOR1)
    results.append(_expect_code("add undefined member fails", code, (SS__CONFIG__INVALID, SS__DEVICE__NOT_DEFINED), out))

    code, out = _run_command(cli, CMD_EXIT)
    results.append(_expect_code("exit intake context", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_DEVICE_MOTOR1)
    results.append(_expect_code("create device motor1", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_DEVICE_INTERFACE_CAN)
    results.append(_expect_code("set motor1 interface", code, STATUS_OK_CODES, out))
    code, out = _run_command(cli, CMD_DEVICE_MANUFACTURER_REV)
    results.append(_expect_code("set motor1 manufacturer", code, STATUS_OK_CODES, out))
    code, out = _run_command(cli, CMD_DEVICE_TYPE_MOTOR_CONTROLLER)
    results.append(_expect_code("set motor1 deviceType", code, STATUS_OK_CODES, out))
    code, out = _run_command(cli, CMD_DEVICE_ID_25)
    results.append(_expect_code("set motor1 id", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_SHOW_DEVICE_MOTOR1_JSON)
    results.append(_expect_code("show device motor1 json", code, STATUS_OK_CODES, out))
    results.append(_expect_contains("show device motor1 json label", out, MSG_JSON_LABEL_MOTOR1))

    code, out = _run_command(cli, CMD_SHOW_DEVICE_REGISTRY_MOTOR1)
    results.append(_expect_code("show device registry removed", code, (SS__CLI_PARSER__INVALID_SYNTAX,), out))
    results.append(_expect_contains("show device registry removed hint", out, MSG_HINT_SHOW))

    code, out = _run_command(cli, CMD_EXIT)
    results.append(_expect_code("exit device motor1", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_DEVICE_MOTOR2)
    results.append(_expect_code("create device motor2", code, STATUS_OK_CODES, out))
    code, out = _run_command(cli, CMD_DEVICE_INTERFACE_CAN)
    results.append(_expect_code("set motor2 interface", code, STATUS_OK_CODES, out))
    code, out = _run_command(cli, CMD_DEVICE_MANUFACTURER_REV)
    results.append(_expect_code("set motor2 manufacturer", code, STATUS_OK_CODES, out))
    code, out = _run_command(cli, CMD_DEVICE_TYPE_MOTOR_CONTROLLER)
    results.append(_expect_code("set motor2 deviceType", code, STATUS_OK_CODES, out))
    code, out = _run_command(cli, CMD_DEVICE_ID_26)
    results.append(_expect_code("set motor2 id", code, STATUS_OK_CODES, out))
    code, out = _run_command(cli, CMD_EXIT)
    results.append(_expect_code("exit device motor2", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_GROUP_INTAKE)
    results.append(_expect_code("re-enter intake", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_ADD_DEVICE_MOTOR1)
    results.append(_expect_code("add motor1 member", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_ADD_DEVICE_MOTOR1)
    results.append(_expect_code("duplicate member no-op", code, STATUS_OK_CODES, out))
    results.append(_expect_contains("duplicate warning", out, MSG_WARNING_DUPLICATE))

    code, out = _run_command(cli, CMD_REMOVE_DEVICE_MOTOR1)
    results.append(_expect_code("remove existing member", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_REMOVE_DEVICE_MOTOR1)
    results.append(_expect_code("remove missing member no-op", code, STATUS_OK_CODES, out))
    results.append(_expect_contains("missing warning", out, MSG_WARNING_MISSING))

    code, out = _run_command(cli, CMD_EXIT)
    results.append(_expect_code("exit intake second time", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_GROUP_CREATE_SHOOTER)
    results.append(_expect_code("create shooter", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_EXIT)
    results.append(_expect_code("exit shooter context", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_GROUP_RENAME_INTAKE_INTAKE_V2)
    results.append(_expect_code("rename intake to intake_v2", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_GROUP_INTAKE)
    results.append(_expect_not_code("old intake name rejected", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_GROUP_INTAKE_V2)
    results.append(_expect_code("enter intake_v2 context", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_EXIT)
    results.append(_expect_code("exit intake_v2 context", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_ADD_ALL_GROUP_INTAKE_V2)
    results.append(_expect_code("add all into intake_v2", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_COPY_GROUP_ACTIVE_ACTIVE)
    results.append(_expect_code("copy active to active fails", code, (SS__CONFIG__INVALID,), out))
    results.append(_expect_contains("copy active to active message", out, MSG_ERROR_COPY_SAME_SOURCE_DEST))

    code, out = _run_command(cli, CMD_COPY_GROUP_INTAKE_V2_ACTIVE)
    results.append(_expect_code("copy intake_v2 to active", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_COPY_GROUP_INTAKE_V2_SHOOTER)
    results.append(_expect_code("copy intake to existing shooter fails", code, (SS__CONFIG__INVALID,), out))
    results.append(_expect_contains("copy non-interactive message", out, MSG_ERROR_COPY_NON_INTERACTIVE))

    code, out = _run_command(cli, CMD_GROUP_DELETE_ACTIVE)
    results.append(_expect_code("delete active fails", code, (SS__CONFIG__INVALID,), out))

    code, out = _run_command(cli, CMD_GROUP_CLEAR_ACTIVE)
    results.append(_expect_code("clear active", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_GROUP_CLEAR_INTAKE_V2)
    results.append(_expect_code("clear intake", code, STATUS_OK_CODES, out))

    code, out = _run_command(cli, CMD_ADD_NEXT_GROUP_ACTIVE)
    results.append(_expect_code("add next active", code, STATUS_OK_CODES, out))

    with tempfile.TemporaryDirectory() as temp_dir:
        path = str(Path(temp_dir) / "bridge_local_config.json")
        save_command = CMD_SAVE_LOCAL_CONFIG_PREFIX + path + FLAG_FORCE
        code, out = _run_command(cli, save_command)
        results.append(_expect_code("save local config", code, (SS__CONFIG__SAVED, SS__NORMAL), out))
        active_count = len(cli._active_group_members)
        is_preserved = active_count > 0
        details = f"active_count_after_save={active_count}"
        results.append(CheckResult(label="active preserved on save", ok=is_preserved, details=details))

    return results


def _print_results(results: List[CheckResult]) -> int:
    """
    NAME
        _print_results - Emit check-by-check results and return process exit code.
    """
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
    """
    NAME
        main - Entrypoint for V1 group/targeting regression script.
    """
    results = _run_regression()
    return _print_results(results)


if __name__ == "__main__":
    raise SystemExit(main())
