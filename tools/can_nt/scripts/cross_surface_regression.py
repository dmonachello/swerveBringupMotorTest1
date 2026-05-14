from __future__ import annotations

"""
NAME
    cross_surface_regression.py - Automated cross-surface bringup config regression checks.

SYNOPSIS
    python tools/can_nt/scripts/cross_surface_regression.py

DESCRIPTION
    Runs integration checks that verify topology-editor output remains
    consumable by the CLI, schema store, and profile validators.
"""

import argparse
import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Iterable, List, Sequence

REPO_ROOT_DEPTH = 3
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MODULE_CROSS_SURFACE = "tools.can_nt.tests.test_cross_surface_regression"
LABEL_CROSS_SURFACE = "cross-surface-unit"
LABEL_SUMMARY = "SUMMARY"
OUTCOME_PASS = "PASS"
OUTCOME_FAIL = "FAIL"
ARG_VERBOSE = "--verbose"
ENV_REGRESSION_VERBOSE = "BRINGUP_REGRESSION_VERBOSE"
TEXT_TRUE = "1"
DETAIL_UNIT_TESTS_PASSED = "cross-surface integration checks passed"
DETAIL_UNIT_TESTS_FAILED = "cross-surface integration checks failed"


class CheckResult:
    """
    NAME
        CheckResult - One cross-surface regression assertion outcome.
    """

    def __init__(self, label: str, ok: bool, details: str) -> None:
        self.label = label
        self.ok = ok
        self.details = details


def _run_unit_modules(module_names: Sequence[str], verbose: bool = False) -> CheckResult:
    """
    NAME
        _run_unit_modules - Run cross-surface unittest modules.
    """
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in module_names)
    if verbose:
        for module_name in module_names:
            print(f"CHECK {LABEL_CROSS_SURFACE}: {module_name}")
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
        if result.wasSuccessful():
            return CheckResult(LABEL_CROSS_SURFACE, True, DETAIL_UNIT_TESTS_PASSED)
        return CheckResult(LABEL_CROSS_SURFACE, False, DETAIL_UNIT_TESTS_FAILED)
    output = io.StringIO()
    with redirect_stdout(output), redirect_stderr(output):
        result = unittest.TextTestRunner(stream=output, verbosity=1).run(suite)
    if result.wasSuccessful():
        return CheckResult(LABEL_CROSS_SURFACE, True, DETAIL_UNIT_TESTS_PASSED)
    details = output.getvalue().strip()
    return CheckResult(
        LABEL_CROSS_SURFACE,
        False,
        f"{DETAIL_UNIT_TESTS_FAILED}: {details}",
    )


def _run_regression(verbose: bool = False) -> List[CheckResult]:
    """
    NAME
        _run_regression - Execute the cross-surface regression checks.
    """
    return [_run_unit_modules((MODULE_CROSS_SURFACE,), verbose=verbose)]


def _print_results(results: Iterable[CheckResult]) -> int:
    """
    NAME
        _print_results - Print results and return process exit code.
    """
    result_list = list(results)
    failures = 0
    for result in result_list:
        outcome = OUTCOME_PASS if result.ok else OUTCOME_FAIL
        print(f"[{outcome}] {result.label}: {result.details}")
        if not result.ok:
            failures += 1
    total = len(result_list)
    passed = total - failures
    print(f"{LABEL_SUMMARY}: passed={passed} failed={failures} total={total}")
    return 0 if failures == 0 else 1


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    NAME
        _parse_args - Parse cross-surface regression command-line flags.
    """
    parser = argparse.ArgumentParser(description="Run cross-surface regression checks.")
    parser.add_argument(ARG_VERBOSE, action="store_true", help="Print per-test progress.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """
    NAME
        main - Entrypoint for cross-surface regression checks.
    """
    args = _parse_args(argv)
    verbose = bool(args.verbose) or os.environ.get(ENV_REGRESSION_VERBOSE) == TEXT_TRUE
    return _print_results(_run_regression(verbose=verbose))


if __name__ == "__main__":
    raise SystemExit(main())
