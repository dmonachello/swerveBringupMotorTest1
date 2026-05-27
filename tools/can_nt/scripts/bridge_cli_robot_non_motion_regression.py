from __future__ import annotations

"""
NAME
    bridge_cli_robot_non_motion_regression.py - Connected robot non-motion regression checks.

SYNOPSIS
    python tools/can_nt/scripts/bridge_cli_robot_non_motion_regression.py --rio 172.22.11.2

DESCRIPTION
    Runs a deterministic regression sequence against BridgeCli over the robot
    REST command server using
    only non-motion commands. The script validates connectivity, read-only show
    paths, and basic mode transitions without issuing test-run or motor commands.

NOTES
    This script requires a reachable roboRIO REST command endpoint.
"""

import argparse
import io
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

REPO_ROOT_DEPTH = 3
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.can_nt.bridge_cli import BridgeCli
from tools.can_nt.bridge_session import BridgeSession
from tools.can_nt.status import (
    SS__NETWORK__CONNECT_FAILED,
    SS__NETWORK__HANDSHAKE_FAILED,
    SS__NETWORK__NOT_CONNECTED,
    SS__NETWORK__ROBOT_UNAVAILABLE,
    SS__NORMAL,
)

DEFAULT_RIO = "172.22.11.2"
DEFAULT_UI_REST_PORT = 5805

CMD_PING = "ping"
CMD_CONNECT = "connect"
CMD_DISCONNECT = "disconnect"
CMD_CONFIGURE_TERMINAL = "configure terminal"
CMD_END = "end"
CMD_SHOW_STATUS_ROBOT = "show status robot"
CMD_SHOW_GROUPS_ROBOT = "show groups robot"
CMD_SHOW_DEVICES_ROBOT = "show devices robot"
CMD_SHOW_SELECTED_DEVICE_ROBOT = "show selected-device robot"
CMD_SHOW_RUNTIME_STATE_ROBOT = "show runtime-state robot"
CMD_SHOW_GROUPS_BOTH = "show groups both"
CMD_SHOW_WORKSPACE = "show workspace"

TEXT_SOURCE_ROBOT = "SOURCE: robot"
TEXT_SOURCE_LOCAL = "SOURCE: local"
TEXT_CONNECT_FAILED = "ERROR: Failed to connect."
TEXT_HANDSHAKE_FAILED = "ERROR: Handshake failed."

OUTCOME_PASS = "PASS"
OUTCOME_FAIL = "FAIL"
LABEL_SUMMARY = "SUMMARY"


@dataclass
class CheckResult:
    """
    NAME
        CheckResult - Single command assertion outcome.
    """

    label: str
    ok: bool
    details: str


@dataclass
class CommandCheck:
    """
    NAME
        CommandCheck - Declarative command expectation.
    """

    label: str
    command: str
    allowed_codes: Tuple[int, ...]
    required_substrings: Tuple[str, ...]


def _parse_args() -> argparse.Namespace:
    """
    NAME
        _parse_args - Parse command-line options.
    """
    parser = argparse.ArgumentParser(
        description="Run non-motion connected robot regression checks over Bridge CLI."
    )
    parser.add_argument("--rio", default=DEFAULT_RIO, help="roboRIO host/IP.")
    parser.add_argument(
        "--ui-rest-port",
        type=int,
        default=DEFAULT_UI_REST_PORT,
        help="Robot REST command port.",
    )
    return parser.parse_args()


def _run_command(cli: BridgeCli, command: str) -> Tuple[int, str]:
    """
    NAME
        _run_command - Execute one CLI line and capture stdout.
    """
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        status = cli._execute_line(command)
    return status.code, output_buffer.getvalue()


def _evaluate_command(
    check: CommandCheck,
    status_code: int,
    output: str,
) -> CheckResult:
    """
    NAME
        _evaluate_command - Validate status and required output fragments.
    """
    status_ok = status_code in check.allowed_codes
    missing = [item for item in check.required_substrings if item not in output]
    output_ok = not missing
    all_ok = status_ok and output_ok
    detail = f"code={status_code} allowed={check.allowed_codes}"
    if not output_ok:
        detail = detail + f" missing={missing}"
    if not all_ok:
        detail = detail + f" output={output.strip()}"
    return CheckResult(label=check.label, ok=all_ok, details=detail)


def _append_check_result(
    results: List[CheckResult],
    cli: BridgeCli,
    check: CommandCheck,
) -> None:
    """
    NAME
        _append_check_result - Run one command check and append result.
    """
    code, out = _run_command(cli, check.command)
    results.append(_evaluate_command(check, code, out))


def _initial_connect(cli: BridgeCli, results: List[CheckResult]) -> bool:
    """
    NAME
        _initial_connect - Attempt connection and record a deterministic result.

    RETURNS
        True if connected and safe to proceed; False otherwise.
    """
    connect_check = CommandCheck(
        label="connect",
        command=CMD_CONNECT,
        allowed_codes=(SS__NORMAL,),
        required_substrings=tuple(),
    )
    code, out = _run_command(cli, connect_check.command)
    results.append(_evaluate_command(connect_check, code, out))
    if code == SS__NORMAL:
        return True
    expected_text = TEXT_CONNECT_FAILED if code == SS__NETWORK__CONNECT_FAILED else TEXT_HANDSHAKE_FAILED
    results.append(
        CheckResult(
            label="connect failure message",
            ok=False,
            details=f"expected={expected_text!r}",
        )
    )
    return False


def _non_motion_checks() -> Sequence[CommandCheck]:
    """
    NAME
        _non_motion_checks - Build ordered non-motion command checks.
    """
    return (
        CommandCheck("ping", CMD_PING, (SS__NORMAL,), tuple()),
        CommandCheck("show status robot", CMD_SHOW_STATUS_ROBOT, (SS__NORMAL,), (TEXT_SOURCE_ROBOT,)),
        CommandCheck("show groups robot", CMD_SHOW_GROUPS_ROBOT, (SS__NORMAL,), (TEXT_SOURCE_ROBOT,)),
        CommandCheck("show devices robot", CMD_SHOW_DEVICES_ROBOT, (SS__NORMAL,), (TEXT_SOURCE_ROBOT,)),
        CommandCheck(
            "show selected-device robot",
            CMD_SHOW_SELECTED_DEVICE_ROBOT,
            (SS__NORMAL,),
            (TEXT_SOURCE_ROBOT,),
        ),
        CommandCheck(
            "show runtime-state robot",
            CMD_SHOW_RUNTIME_STATE_ROBOT,
            (SS__NORMAL,),
            (TEXT_SOURCE_ROBOT,),
        ),
        CommandCheck("configure terminal", CMD_CONFIGURE_TERMINAL, (SS__NORMAL,), tuple()),
        CommandCheck("show groups both", CMD_SHOW_GROUPS_BOTH, (SS__NORMAL,), (TEXT_SOURCE_LOCAL, TEXT_SOURCE_ROBOT)),
        CommandCheck("show workspace", CMD_SHOW_WORKSPACE, (SS__NORMAL,), ("Profiles:",)),
        CommandCheck("end", CMD_END, (SS__NORMAL,), tuple()),
        CommandCheck("disconnect", CMD_DISCONNECT, (SS__NORMAL,), tuple()),
        CommandCheck(
            "show status robot after disconnect",
            CMD_SHOW_STATUS_ROBOT,
            (SS__NORMAL, SS__NETWORK__NOT_CONNECTED, SS__NETWORK__ROBOT_UNAVAILABLE),
            ("ERROR: Robot source unavailable (not connected).",),
        ),
    )


def _run_regression(rio: str, rest_port: int) -> List[CheckResult]:
    """
    NAME
        _run_regression - Execute connected non-motion regression sequence.
    """
    results: List[CheckResult] = []
    session = BridgeSession(rio, int(rest_port), auto_handshake=False)
    cli = BridgeCli(session, batch=True)
    if not _initial_connect(cli, results):
        return results
    for check in _non_motion_checks():
        _append_check_result(results, cli, check)
    return results


def _print_results(results: List[CheckResult]) -> int:
    """
    NAME
        _print_results - Emit check-by-check results and return process exit code.
    """
    failure_count = 0
    for result in results:
        outcome = OUTCOME_PASS if result.ok else OUTCOME_FAIL
        print(f"[{outcome}] {result.label}: {result.details}")
        if not result.ok:
            failure_count += 1
    total_count = len(results)
    pass_count = total_count - failure_count
    print(f"{LABEL_SUMMARY}: passed={pass_count} failed={failure_count} total={total_count}")
    return 0 if failure_count == 0 else 1


def main() -> int:
    """
    NAME
        main - Entrypoint for connected non-motion regression script.
    """
    args = _parse_args()
    results = _run_regression(str(args.rio), int(args.ui_rest_port))
    return _print_results(results)


if __name__ == "__main__":
    raise SystemExit(main())
