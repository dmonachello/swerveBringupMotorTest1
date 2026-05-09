from __future__ import annotations

"""
NAME
    topology_editor_regression.py - Deterministic topology editor regression checks.

SYNOPSIS
    python tools/can_nt/scripts/topology_editor_regression.py

DESCRIPTION
    Validates the committed deploy-time bringup config with the topology
    profile validator and runs focused headless topology/editor unit tests.
"""

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

REPO_ROOT_DEPTH = 3
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[REPO_ROOT_DEPTH]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.can_topology.validate_profiles import Reporter, load_profiles_json, validate_profiles

TOPOLOGY_FIXTURE_RELATIVE = Path("tests/regression/fixtures/topology_editor_regression_fixture.json")

MODULE_TOPOLOGY_EDITOR_LOAD = "tools.can_topology.tests.test_can_top_editor_profile_load"
MODULE_TOPOLOGY_SHOW = "tools.can_nt.tests.test_bridge_cli_topology_show"
MODULE_TOPOLOGY_VALIDATE = "tools.can_topology.tests.test_validate_profiles_topology"
MODULE_LIVE_TOPOLOGY_VIEW = "tools.can_topology.tests.test_live_topology_view"

LABEL_FIXTURE_VALIDATE = "topology-fixture-validate"
LABEL_TOPOLOGY_UNIT = "topology-editor-unit"
LABEL_SUMMARY = "SUMMARY"
OUTCOME_PASS = "PASS"
OUTCOME_FAIL = "FAIL"

DETAIL_VALIDATION_PASSED = "topology fixture validation passed"
DETAIL_VALIDATION_LOAD_FAILED = "topology fixture load failed"
DETAIL_VALIDATION_ERRORS = "topology fixture validation returned errors"
DETAIL_VALIDATION_WARNINGS = "topology fixture validation returned warnings"
DETAIL_UNIT_TESTS_PASSED = "topology/editor unit modules passed"
DETAIL_UNIT_TESTS_FAILED = "topology/editor unit modules failed"


class CheckResult:
    """
    NAME
        CheckResult - One topology regression assertion outcome.
    """

    def __init__(self, label: str, ok: bool, details: str) -> None:
        self.label = label
        self.ok = ok
        self.details = details


def _validate_topology_fixture() -> CheckResult:
    """
    NAME
        _validate_topology_fixture - Validate the committed topology fixture.
    """
    path = REPO_ROOT / TOPOLOGY_FIXTURE_RELATIVE
    try:
        payload = load_profiles_json(path)
    except ValueError as exc:
        return CheckResult(LABEL_FIXTURE_VALIDATE, False, f"{DETAIL_VALIDATION_LOAD_FAILED}: {exc}")
    reporter = Reporter(False)
    errors, warnings = validate_profiles(payload, reporter)
    if errors:
        return CheckResult(LABEL_FIXTURE_VALIDATE, False, f"{DETAIL_VALIDATION_ERRORS}: {errors}")
    if warnings:
        return CheckResult(LABEL_FIXTURE_VALIDATE, False, f"{DETAIL_VALIDATION_WARNINGS}: {warnings}")
    return CheckResult(LABEL_FIXTURE_VALIDATE, True, DETAIL_VALIDATION_PASSED)


def _run_unit_modules(module_names: Sequence[str]) -> CheckResult:
    """
    NAME
        _run_unit_modules - Run focused topology/editor unittest modules.
    """
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in module_names)
    output = io.StringIO()
    with redirect_stdout(output), redirect_stderr(output):
        result = unittest.TextTestRunner(stream=output, verbosity=1).run(suite)
    if result.wasSuccessful():
        return CheckResult(LABEL_TOPOLOGY_UNIT, True, DETAIL_UNIT_TESTS_PASSED)
    details = output.getvalue().strip()
    return CheckResult(
        LABEL_TOPOLOGY_UNIT,
        False,
        f"{DETAIL_UNIT_TESTS_FAILED}: {details}",
    )


def _run_regression() -> List[CheckResult]:
    """
    NAME
        _run_regression - Execute the topology regression checks.
    """
    return [
        _validate_topology_fixture(),
        _run_unit_modules(
            (
                MODULE_TOPOLOGY_EDITOR_LOAD,
                MODULE_TOPOLOGY_SHOW,
                MODULE_TOPOLOGY_VALIDATE,
                MODULE_LIVE_TOPOLOGY_VIEW,
            )
        ),
    ]


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


def main() -> int:
    """
    NAME
        main - Entrypoint for topology editor regression checks.
    """
    return _print_results(_run_regression())


if __name__ == "__main__":
    raise SystemExit(main())
