from __future__ import annotations

"""
NAME
    run_regressions.py - Unified regression runner wrapper for canonical repo checks.

SYNOPSIS
    python tools/can_nt/scripts/run_regressions.py --suite local
    python tools/can_nt/scripts/run_regressions.py --suite robot-non-motion --rio 172.22.11.2

DESCRIPTION
    Provides a single front door for the current regression surface by loading
    the repo's regression manifest, running canonical local or connected
    commands, comparing results against stored baselines, and optionally
    refreshing those baselines.
"""

import argparse
from pathlib import Path
import sys
from typing import Sequence

REPO_ROOT_DEPTH = 3
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.can_nt.scripts.lib.regression_framework import (
    EXIT_FAILED,
    EXIT_OK,
    EXIT_USAGE,
    RegressionComparison,
    RegressionResult,
    available_suites,
    build_suite_commands,
    compare_results_to_baseline,
    collect_run_metadata,
    load_suite_baseline,
    refresh_suite_baseline,
    run_commands,
    summarize_results,
    suite_baseline_path,
    write_history_for_run,
    write_json_report,
)

ARG_SUITE = "--suite"
ARG_INCLUDE_ROBOT = "--include-robot"
ARG_RIO = "--rio"
ARG_UI_REST_PORT = "--ui-rest-port"
ARG_VERBOSE = "--verbose"
ARG_REFRESH_EXPECTED = "--refresh-expected"
ARG_JSON_OUT = "--json-out"
ARG_NO_HISTORY = "--no-history"

HELP_SUITE = "Regression suite to run."
HELP_INCLUDE_ROBOT = "Include robot-connected non-motion suite when using --suite all."
HELP_RIO = "roboRIO host/IP for robot-connected non-motion regressions."
HELP_UI_REST_PORT = "Optional REST command port for robot-connected non-motion regressions."
HELP_VERBOSE = "Print stdout and stderr for passing commands."
HELP_REFRESH_EXPECTED = "Refresh the stored expected baseline for the selected suite."
HELP_JSON_OUT = "Write a machine-readable JSON report to the given path."
HELP_NO_HISTORY = "Skip local failure-history updates for this run."

MSG_COMMAND = "COMMAND"
MSG_PASS = "PASS"
MSG_FAIL = "FAIL"
MSG_STDOUT = "STDOUT"
MSG_STDERR = "STDERR"
MSG_SUMMARY = "SUMMARY"
MSG_STATUS = "STATUS"
MSG_STATUS_REASON = "STATUS_REASON"
MSG_EXPECTED_COMMAND = "EXPECTED_COMMAND"
MSG_FEATURES = "FEATURES"
MSG_BASELINE = "BASELINE"
MSG_NOTE = "NOTE"
MSG_REFRESHED = "REFRESHED"
MSG_HISTORY = "HISTORY"
MSG_PLAN = "PLAN"
MSG_TARGETS = "TARGETS"

TEXT_MODE_UNITTEST = "unittest"
TEXT_FLAG_MODULE = "-m"
TEXT_FLAG_TESTS = "--tests"
TEXT_PREFIX_SCRIPT = "script="
TEXT_PREFIX_MODULE = "module="
TEXT_PREFIX_GRADLE_TEST = "gradle-test="
TEXT_PREFIX_ARGV = "argv="
TEXT_EMPTY = ""


def _describe_command_targets(argv: Sequence[str]) -> tuple[str, ...]:
    """
    NAME
        _describe_command_targets - Return a short stable summary of what one command exercises.
    """
    argv_list = [str(part) for part in argv]
    if len(argv_list) >= 4 and argv_list[1] == TEXT_FLAG_MODULE and argv_list[2] == TEXT_MODE_UNITTEST:
        return tuple(f"{TEXT_PREFIX_MODULE}{target}" for target in argv_list[3:] if str(target).strip())
    if len(argv_list) >= 2 and str(argv_list[1]).lower().endswith(".py"):
        return (f"{TEXT_PREFIX_SCRIPT}{Path(argv_list[1]).name}",)
    if TEXT_FLAG_TESTS in argv_list:
        selector_index = argv_list.index(TEXT_FLAG_TESTS) + 1
        if selector_index < len(argv_list):
            return (f"{TEXT_PREFIX_GRADLE_TEST}{argv_list[selector_index]}",)
    return (f"{TEXT_PREFIX_ARGV}{' '.join(argv_list[1:])}",) if len(argv_list) > 1 else (TEXT_EMPTY,)


def print_suite_plan(suite_name: str, commands: Sequence[RegressionCommand]) -> None:
    """
    NAME
        print_suite_plan - Emit a concise up-front summary of the selected regression suite.
    """
    print(f"{MSG_PLAN}: suite={suite_name} commands={len(commands)}")
    for command in commands:
        print(f"{MSG_PLAN}: {command.label} mode={command.mode}")
        targets = tuple(item for item in _describe_command_targets(command.argv) if item)
        if targets:
            print(f"{MSG_TARGETS}: {', '.join(targets)}")
        if command.features:
            print(f"{MSG_FEATURES}: {', '.join(command.features)}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    NAME
        parse_args - Parse command-line arguments for the unified runner.
    """
    parser = argparse.ArgumentParser(description="Run canonical regression suites for this repo.")
    parser.add_argument(
        ARG_SUITE,
        choices=tuple(available_suites()),
        default="local",
        help=HELP_SUITE,
    )
    parser.add_argument(ARG_INCLUDE_ROBOT, action="store_true", help=HELP_INCLUDE_ROBOT)
    parser.add_argument(ARG_RIO, help=HELP_RIO)
    parser.add_argument(ARG_UI_REST_PORT, type=int, help=HELP_UI_REST_PORT)
    parser.add_argument(ARG_VERBOSE, action="store_true", help=HELP_VERBOSE)
    parser.add_argument(ARG_REFRESH_EXPECTED, action="store_true", help=HELP_REFRESH_EXPECTED)
    parser.add_argument(ARG_JSON_OUT, help=HELP_JSON_OUT)
    parser.add_argument(ARG_NO_HISTORY, action="store_true", help=HELP_NO_HISTORY)
    return parser.parse_args(argv)


def print_result(result: RegressionResult, comparison: RegressionComparison, verbose: bool) -> None:
    """
    NAME
        print_result - Emit one regression result in a stable text format.
    """
    outcome = MSG_PASS if result.ok else MSG_FAIL
    print(f"[{outcome}] {result.label}: exit={result.exit_code} mode={result.mode} dur={result.duration_sec:.2f}s")
    print(f"{MSG_COMMAND}: {' '.join(result.argv)}")
    if verbose:
        targets = tuple(item for item in _describe_command_targets(result.argv) if item)
        if targets:
            print(f"{MSG_TARGETS}: {', '.join(targets)}")
    if result.features:
        print(f"{MSG_FEATURES}: {', '.join(result.features)}")
    print(f"{MSG_STATUS}: {comparison.status}")
    print(f"{MSG_STATUS_REASON}: {comparison.status_reason}")
    if not comparison.argv_matches and comparison.expected_argv:
        print(f"{MSG_EXPECTED_COMMAND}: {' '.join(comparison.expected_argv)}")
    if (verbose and not result.stdout) or not result.ok:
        stdout_text = result.stdout.strip()
        stderr_text = result.stderr.strip()
        if stdout_text:
            print(f"{MSG_STDOUT}:")
            print(stdout_text)
        if stderr_text:
            print(f"{MSG_STDERR}:")
            print(stderr_text)


def main(argv: Sequence[str] | None = None) -> int:
    """
    NAME
        main - Entrypoint for the unified regression runner wrapper.
    """
    args = parse_args(argv)
    try:
        commands = build_suite_commands(
            suite_name=str(args.suite),
            rio=args.rio,
            include_robot=bool(args.include_robot),
            ui_rest_port=args.ui_rest_port,
        )
    except ValueError as ex:
        print(f"ERROR: {ex}")
        return EXIT_USAGE

    if bool(args.verbose):
        print_suite_plan(str(args.suite), commands)
    results = run_commands(commands, verbose=bool(args.verbose))
    metadata = collect_run_metadata()
    baseline = None if bool(args.refresh_expected) else load_suite_baseline(str(args.suite))
    comparisons = compare_results_to_baseline(commands, results, baseline)
    for result, comparison in zip(results, comparisons):
        print_result(result, comparison=comparison, verbose=bool(args.verbose))

    summary = summarize_results(results)
    if bool(args.refresh_expected):
        baseline_path = refresh_suite_baseline(str(args.suite), commands, results)
        print(f"{MSG_REFRESHED}: {baseline_path}")
    else:
        baseline_path = suite_baseline_path(str(args.suite)) if baseline is not None else None
        if baseline_path is None:
            print(f"{MSG_NOTE}: no baseline file for suite={args.suite}")
        else:
            print(f"{MSG_BASELINE}: {baseline_path}")

    json_out = args.json_out
    if json_out:
        write_json_report(
            Path(str(json_out)),
            suite_name=str(args.suite),
            results=results,
            summary=summary,
            comparisons=comparisons,
            baseline_path=baseline_path,
            metadata=metadata,
        )

    if not bool(args.refresh_expected) and not bool(args.no_history):
        history = write_history_for_run(
            suite_name=str(args.suite),
            results=results,
            summary=summary,
            comparisons=comparisons,
            baseline_path=baseline_path,
            metadata=metadata,
        )
        print(f"{MSG_HISTORY}: run={history['runPath']} event={history['event']['eventType']}")
        event_path = history["event"]["eventPath"]
        if event_path:
            print(f"{MSG_HISTORY}: eventPath={event_path}")

    print(
        f"{MSG_SUMMARY}: suite={args.suite} passed={summary['passed']} failed={summary['failed']} total={summary['total']}"
    )
    if bool(args.refresh_expected):
        return EXIT_OK
    return EXIT_OK if summary["failed"] == 0 else EXIT_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
