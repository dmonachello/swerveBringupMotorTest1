from __future__ import annotations

"""
NAME
    regression_framework.py - Shared regression-runner suite, baseline, and reporting helpers.

SYNOPSIS
    from tools.can_nt.scripts.lib.regression_framework import (
        SUITE_LOCAL,
        build_suite_commands,
        run_commands,
    )

DESCRIPTION
    Defines the unified regression runner surface by loading a data-driven
    suite manifest, executing canonical commands, and handling baseline
    refresh/compare behavior for stable regression reporting.
"""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence

REPO_ROOT_DEPTH = 4
CURRENT_SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = CURRENT_SCRIPT_PATH.parents[REPO_ROOT_DEPTH]

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

SUITE_LOCAL = "local"
SUITE_DSL = "dsl"
SUITE_CLI = "cli"
SUITE_JAVA = "java"
SUITE_TOPOLOGY = "topology"
SUITE_CHANGELOG = "changelog"
SUITE_ROBOT_NON_MOTION = "robot-non-motion"
SUITE_ALL = "all"

FLAG_RIO = "--rio"
FLAG_UI_TCP_PORT = "--ui-tcp-port"

TEXT_MODE_LOCAL = "local"
TEXT_MODE_CONNECTED = "connected"

JAVA_HOME_ENV = "JAVA_HOME"
JAVA_BIN_SUFFIX = "bin"
GRADLEW_WINDOWS = "gradlew.bat"

MANIFEST_RELATIVE_PATH = Path("tests/regression/fixtures/regression_runner_manifest.json")
BASELINE_DIRECTORY_RELATIVE = Path("tests/regression/expected/runner_baselines")
BASELINE_FILE_SUFFIX = ".expected.json"

KEY_SCHEMA_VERSION = "schemaVersion"
KEY_COMMANDS = "commands"
KEY_SUITES = "suites"
KEY_LABEL = "label"
KEY_MODE = "mode"
KEY_ARGV = "argv"
KEY_FEATURES = "features"
KEY_SUITE = "suite"
KEY_COMMAND = "command"
KEY_COMMAND_ID = "commandId"
KEY_EXPECTED_EXIT_CODE = "expectedExitCode"
KEY_RESULTS = "results"
KEY_SUMMARY = "summary"
KEY_BASELINE = "baseline"
KEY_STATUS = "status"
KEY_BASELINE_PATH = "baselinePath"
KEY_REPORT_VERSION = "reportVersion"
KEY_REPORT_GENERATED_AT = "generatedAt"
KEY_COMMANDS_TOTAL = "commandsTotal"
KEY_MATCHES = "matches"
KEY_REGRESSIONS = "regressions"
KEY_KNOWN_FAILURES = "knownFailures"
KEY_FIXED = "fixed"
KEY_MISSING_BASELINE = "missingBaseline"
KEY_COMMAND_DRIFT = "commandDrift"

TOKEN_PYTHON = "{python}"
TOKEN_GRADLEW = "{gradlew}"
TOKEN_REPO = "{repo}"
TOKEN_RIO = "{rio}"
TOKEN_UI_TCP_PORT = "{ui_tcp_port}"

STATUS_MATCH = "match"
STATUS_REGRESSION = "regression"
STATUS_KNOWN_FAILURE = "known_failure"
STATUS_FIXED = "fixed_since_baseline"
STATUS_MISSING_BASELINE = "missing_baseline"
STATUS_COMMAND_DRIFT = "command_drift"

REPORT_VERSION = 1
BASELINE_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RegressionCommand:
    """
    NAME
        RegressionCommand - One runnable regression step.
    """

    label: str
    argv: Sequence[str]
    mode: str
    command_id: str
    features: Sequence[str]


@dataclass(frozen=True)
class RegressionResult:
    """
    NAME
        RegressionResult - Result of one regression command execution.
    """

    label: str
    argv: Sequence[str]
    mode: str
    exit_code: int
    duration_sec: float
    stdout: str
    stderr: str
    command_id: str
    features: Sequence[str]

    @property
    def ok(self) -> bool:
        return self.exit_code == EXIT_OK


@dataclass(frozen=True)
class RegressionComparison:
    """
    NAME
        RegressionComparison - Baseline comparison result for one command.
    """

    command_id: str
    label: str
    expected_exit_code: Optional[int]
    actual_exit_code: int
    status: str
    argv_matches: bool


RunnerFunction = Callable[[RegressionCommand, Path], RegressionResult]


def available_suites() -> Sequence[str]:
    """
    NAME
        available_suites - Return supported suite names in stable order.
    """
    return (
        SUITE_LOCAL,
        SUITE_DSL,
        SUITE_CLI,
        SUITE_JAVA,
        SUITE_TOPOLOGY,
        SUITE_CHANGELOG,
        SUITE_ROBOT_NON_MOTION,
        SUITE_ALL,
    )


def build_suite_commands(
    suite_name: str,
    rio: Optional[str] = None,
    include_robot: bool = False,
    ui_tcp_port: Optional[int] = None,
) -> List[RegressionCommand]:
    """
    NAME
        build_suite_commands - Build the canonical command list for a suite.
    """
    manifest = load_manifest()
    if suite_name == SUITE_ALL:
        command_ids = list(_suite_command_ids(manifest, SUITE_LOCAL))
        if include_robot:
            command_ids.extend(_suite_command_ids(manifest, SUITE_ROBOT_NON_MOTION))
    else:
        command_ids = list(_suite_command_ids(manifest, suite_name))
    context = _manifest_context(rio=rio, ui_tcp_port=ui_tcp_port)
    return [_build_command_from_manifest(manifest, command_id, context) for command_id in command_ids]


def run_commands(
    commands: Iterable[RegressionCommand],
    runner: Optional[RunnerFunction] = None,
) -> List[RegressionResult]:
    """
    NAME
        run_commands - Execute regression commands in order.
    """
    active_runner = runner or execute_command
    results: List[RegressionResult] = []
    for command in commands:
        results.append(active_runner(command, REPO_ROOT))
    return results


def execute_command(command: RegressionCommand, workdir: Path) -> RegressionResult:
    """
    NAME
        execute_command - Run one subprocess-backed regression command.
    """
    start_sec = time.monotonic()
    completed = subprocess.run(
        list(command.argv),
        cwd=str(workdir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_subprocess_env_for_command(command),
    )
    duration_sec = time.monotonic() - start_sec
    return RegressionResult(
        label=command.label,
        argv=list(command.argv),
        mode=command.mode,
        exit_code=int(completed.returncode),
        duration_sec=duration_sec,
        stdout=completed.stdout,
        stderr=completed.stderr,
        command_id=command.command_id,
        features=tuple(command.features),
    )


def summarize_results(results: Sequence[RegressionResult]) -> Dict[str, int]:
    """
    NAME
        summarize_results - Build a small pass/fail summary.
    """
    total_count = len(results)
    failed_count = sum(0 if result.ok else 1 for result in results)
    passed_count = total_count - failed_count
    return {
        "passed": passed_count,
        "failed": failed_count,
        "total": total_count,
    }


def load_manifest() -> Dict[str, object]:
    """
    NAME
        load_manifest - Load the runner manifest from disk.
    """
    path = REPO_ROOT / MANIFEST_RELATIVE_PATH
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    schema_version = int(payload.get(KEY_SCHEMA_VERSION, 0))
    if schema_version != MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"unsupported regression manifest schemaVersion: {schema_version}")
    return payload


def suite_baseline_path(suite_name: str) -> Path:
    """
    NAME
        suite_baseline_path - Resolve baseline file path for one suite.
    """
    return REPO_ROOT / BASELINE_DIRECTORY_RELATIVE / f"{suite_name}{BASELINE_FILE_SUFFIX}"


def load_suite_baseline(suite_name: str) -> Optional[Dict[str, object]]:
    """
    NAME
        load_suite_baseline - Load a suite baseline when present.
    """
    path = suite_baseline_path(suite_name)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else None


def refresh_suite_baseline(
    suite_name: str,
    commands: Sequence[RegressionCommand],
    results: Sequence[RegressionResult],
) -> Path:
    """
    NAME
        refresh_suite_baseline - Write a stable expected-results baseline for a suite.
    """
    baseline_path = suite_baseline_path(suite_name)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        KEY_SCHEMA_VERSION: BASELINE_SCHEMA_VERSION,
        KEY_SUITE: suite_name,
        KEY_RESULTS: [
            {
                KEY_COMMAND_ID: command.command_id,
                KEY_LABEL: command.label,
                KEY_MODE: command.mode,
                KEY_ARGV: list(command.argv),
                KEY_FEATURES: list(command.features),
                KEY_EXPECTED_EXIT_CODE: int(result.exit_code),
            }
            for command, result in zip(commands, results)
        ],
    }
    with baseline_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return baseline_path


def compare_results_to_baseline(
    commands: Sequence[RegressionCommand],
    results: Sequence[RegressionResult],
    baseline: Optional[Mapping[str, object]],
) -> List[RegressionComparison]:
    """
    NAME
        compare_results_to_baseline - Compare actual results against stored expectations.
    """
    if baseline is None:
        return [
            RegressionComparison(
                command_id=command.command_id,
                label=command.label,
                expected_exit_code=None,
                actual_exit_code=int(result.exit_code),
                status=STATUS_MISSING_BASELINE,
                argv_matches=False,
            )
            for command, result in zip(commands, results)
        ]
    baseline_entries = baseline.get(KEY_RESULTS)
    if not isinstance(baseline_entries, list):
        baseline_entries = []
    by_command_id: Dict[str, Mapping[str, object]] = {}
    for entry in baseline_entries:
        if not isinstance(entry, dict):
            continue
        command_id = str(entry.get(KEY_COMMAND_ID, "")).strip()
        if command_id:
            by_command_id[command_id] = entry
    comparisons: List[RegressionComparison] = []
    for command, result in zip(commands, results):
        baseline_entry = by_command_id.get(command.command_id)
        if baseline_entry is None:
            comparisons.append(
                RegressionComparison(
                    command_id=command.command_id,
                    label=command.label,
                    expected_exit_code=None,
                    actual_exit_code=int(result.exit_code),
                    status=STATUS_MISSING_BASELINE,
                    argv_matches=False,
                )
            )
            continue
        expected_exit_code = int(baseline_entry.get(KEY_EXPECTED_EXIT_CODE, 0))
        expected_argv = baseline_entry.get(KEY_ARGV)
        argv_matches = list(command.argv) == (expected_argv if isinstance(expected_argv, list) else [])
        status = _comparison_status(expected_exit_code, int(result.exit_code), argv_matches)
        comparisons.append(
            RegressionComparison(
                command_id=command.command_id,
                label=command.label,
                expected_exit_code=expected_exit_code,
                actual_exit_code=int(result.exit_code),
                status=status,
                argv_matches=argv_matches,
            )
        )
    return comparisons


def summarize_comparisons(comparisons: Sequence[RegressionComparison]) -> Dict[str, int]:
    """
    NAME
        summarize_comparisons - Count comparison statuses in a stable shape.
    """
    summary = {
        KEY_COMMANDS_TOTAL: len(comparisons),
        KEY_MATCHES: 0,
        KEY_REGRESSIONS: 0,
        KEY_KNOWN_FAILURES: 0,
        KEY_FIXED: 0,
        KEY_MISSING_BASELINE: 0,
        KEY_COMMAND_DRIFT: 0,
    }
    status_to_key = {
        STATUS_MATCH: KEY_MATCHES,
        STATUS_REGRESSION: KEY_REGRESSIONS,
        STATUS_KNOWN_FAILURE: KEY_KNOWN_FAILURES,
        STATUS_FIXED: KEY_FIXED,
        STATUS_MISSING_BASELINE: KEY_MISSING_BASELINE,
        STATUS_COMMAND_DRIFT: KEY_COMMAND_DRIFT,
    }
    for comparison in comparisons:
        summary[status_to_key[comparison.status]] += 1
    return summary


def write_json_report(
    path: Path,
    suite_name: str,
    results: Sequence[RegressionResult],
    summary: Mapping[str, int],
    comparisons: Sequence[RegressionComparison],
    baseline_path: Optional[Path],
) -> None:
    """
    NAME
        write_json_report - Emit a machine-readable regression report.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    comparison_by_command_id = {item.command_id: item for item in comparisons}
    payload = {
        KEY_REPORT_VERSION: REPORT_VERSION,
        KEY_REPORT_GENERATED_AT: _utc_timestamp(),
        KEY_SUITE: suite_name,
        KEY_SUMMARY: dict(summary),
        KEY_BASELINE: {
            KEY_BASELINE_PATH: str(baseline_path) if baseline_path is not None else None,
            KEY_SUMMARY: summarize_comparisons(comparisons),
        },
        KEY_RESULTS: [
            {
                KEY_COMMAND: {
                    KEY_COMMAND_ID: result.command_id,
                    KEY_LABEL: result.label,
                    KEY_MODE: result.mode,
                    KEY_ARGV: list(result.argv),
                },
                "exitCode": int(result.exit_code),
                "durationSec": result.duration_sec,
                KEY_STATUS: asdict(comparison_by_command_id[result.command_id]),
            }
            for result in results
        ],
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _manifest_context(rio: Optional[str], ui_tcp_port: Optional[int]) -> Dict[str, Optional[str]]:
    return {
        TOKEN_PYTHON: sys.executable,
        TOKEN_GRADLEW: str(REPO_ROOT / GRADLEW_WINDOWS),
        TOKEN_REPO: str(REPO_ROOT),
        TOKEN_RIO: rio,
        TOKEN_UI_TCP_PORT: None if ui_tcp_port is None else str(ui_tcp_port),
    }


def _suite_command_ids(manifest: Mapping[str, object], suite_name: str) -> Sequence[str]:
    suites = manifest.get(KEY_SUITES)
    if not isinstance(suites, dict):
        raise ValueError("regression manifest missing suites map")
    suite_entry = suites.get(suite_name)
    if not isinstance(suite_entry, list):
        raise ValueError(f"unknown suite: {suite_name}")
    command_ids = [str(value).strip() for value in suite_entry if str(value).strip()]
    if not command_ids:
        raise ValueError(f"suite has no commands: {suite_name}")
    return command_ids


def _build_command_from_manifest(
    manifest: Mapping[str, object],
    command_id: str,
    context: Mapping[str, Optional[str]],
) -> RegressionCommand:
    commands = manifest.get(KEY_COMMANDS)
    if not isinstance(commands, dict):
        raise ValueError("regression manifest missing commands map")
    entry = commands.get(command_id)
    if not isinstance(entry, dict):
        raise ValueError(f"unknown command id: {command_id}")
    argv_raw = entry.get(KEY_ARGV)
    if not isinstance(argv_raw, list) or not argv_raw:
        raise ValueError(f"command has no argv: {command_id}")
    argv = [_resolve_manifest_token(str(token), context, command_id) for token in argv_raw]
    if FLAG_UI_TCP_PORT in argv and context.get(TOKEN_UI_TCP_PORT) is None:
        flag_index = argv.index(FLAG_UI_TCP_PORT)
        argv = argv[:flag_index]
    label = str(entry.get(KEY_LABEL, command_id)).strip()
    mode = str(entry.get(KEY_MODE, TEXT_MODE_LOCAL)).strip() or TEXT_MODE_LOCAL
    features_raw = entry.get(KEY_FEATURES)
    features = tuple(str(value).strip() for value in features_raw) if isinstance(features_raw, list) else ()
    features = tuple(value for value in features if value)
    return RegressionCommand(
        label=label,
        argv=tuple(argv),
        mode=mode,
        command_id=command_id,
        features=features,
    )


def _resolve_manifest_token(token: str, context: Mapping[str, Optional[str]], command_id: str) -> str:
    if token == TOKEN_RIO and not context.get(TOKEN_RIO):
        raise ValueError(f"command {command_id} requires {FLAG_RIO}")
    if token == TOKEN_UI_TCP_PORT and not context.get(TOKEN_UI_TCP_PORT):
        return FLAG_UI_TCP_PORT
    resolved = token
    for key, value in context.items():
        if value is not None:
            resolved = resolved.replace(key, value)
    return resolved


def _subprocess_env_for_command(command: RegressionCommand) -> Dict[str, str]:
    env = dict(os.environ)
    if not command.argv:
        return env
    executable = str(command.argv[0]).lower()
    if not executable.endswith(GRADLEW_WINDOWS):
        return env
    normalized_java_home = _normalized_java_home(env.get(JAVA_HOME_ENV))
    if normalized_java_home is not None:
        env[JAVA_HOME_ENV] = normalized_java_home
    return env


def _normalized_java_home(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    candidate = Path(str(value))
    if candidate.name.lower() != JAVA_BIN_SUFFIX:
        return str(candidate)
    return str(candidate.parent)


def _comparison_status(expected_exit_code: int, actual_exit_code: int, argv_matches: bool) -> str:
    if not argv_matches:
        return STATUS_COMMAND_DRIFT
    if expected_exit_code == actual_exit_code:
        return STATUS_MATCH if actual_exit_code == EXIT_OK else STATUS_KNOWN_FAILURE
    if expected_exit_code != EXIT_OK and actual_exit_code == EXIT_OK:
        return STATUS_FIXED
    if expected_exit_code == EXIT_OK and actual_exit_code != EXIT_OK:
        return STATUS_REGRESSION
    return STATUS_REGRESSION


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
