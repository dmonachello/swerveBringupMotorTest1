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
SUITE_CROSS_SURFACE = "cross-surface"
SUITE_CHANGELOG = "changelog"
SUITE_ROBOT_NON_MOTION = "robot-non-motion"
SUITE_ALL = "all"

FLAG_RIO = "--rio"
FLAG_UI_TCP_PORT = "--ui-tcp-port"

TEXT_MODE_LOCAL = "local"
TEXT_MODE_CONNECTED = "connected"

JAVA_HOME_ENV = "JAVA_HOME"
REGRESSION_VERBOSE_ENV = "BRINGUP_REGRESSION_VERBOSE"
TEXT_TRUE = "1"
JAVA_BIN_SUFFIX = "bin"
PYTHON_EXE_STEM = "python"
WINDOWS_EXE_SUFFIX = ".exe"
GRADLEW_WINDOWS = "gradlew.bat"
TOOLS_PATH_MARKER = "/tools/"
TESTS_PATH_MARKER = "/tests/"

MANIFEST_RELATIVE_PATH = Path("tests/regression/fixtures/regression_runner_manifest.json")
BASELINE_DIRECTORY_RELATIVE = Path("tests/regression/expected/runner_baselines")
BASELINE_FILE_SUFFIX = ".expected.json"
HISTORY_DIRECTORY_RELATIVE = Path(".codex/logs/regressions")
HISTORY_INDEX_FILE_NAME = "index.json"
HISTORY_EVENTS_DIRECTORY_NAME = "events"
HISTORY_LATEST_DIRECTORY_NAME = "latest"
HISTORY_LATEST_FILE_SUFFIX = ".latest.json"
HISTORY_LAST_GREEN_FILE_SUFFIX = ".last_green.json"

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
KEY_STATUS_REASON = "statusReason"
KEY_BASELINE_PATH = "baselinePath"
KEY_REPORT_VERSION = "reportVersion"
KEY_REPORT_GENERATED_AT = "generatedAt"
KEY_REPORT_METADATA = "metadata"
KEY_COMMANDS_TOTAL = "commandsTotal"
KEY_MATCHES = "matches"
KEY_REGRESSIONS = "regressions"
KEY_KNOWN_FAILURES = "knownFailures"
KEY_FIXED = "fixed"
KEY_MISSING_BASELINE = "missingBaseline"
KEY_COMMAND_DRIFT = "commandDrift"
KEY_GIT = "git"
KEY_COMMIT = "commit"
KEY_BRANCH = "branch"
KEY_DIRTY = "dirty"
KEY_CHANGED_FILES = "changedFiles"
KEY_HISTORY_VERSION = "historyVersion"
KEY_HISTORY = "history"
KEY_EVENT = "event"
KEY_EVENT_TYPE = "eventType"
KEY_EVENT_PATH = "eventPath"
KEY_EVENT_AT = "eventAt"
KEY_LAST_RUN_PATH = "lastRunPath"
KEY_LAST_RUN_AT = "lastRunAt"
KEY_LAST_GREEN_PATH = "lastGreenPath"
KEY_LAST_GREEN_AT = "lastGreenAt"
KEY_LAST_GREEN_COMMIT = "lastGreenCommit"
KEY_ACTIVE_FAILURE = "activeFailure"
KEY_FAILURE_SIGNATURE = "failureSignature"
KEY_FIRST_OBSERVED_AT = "firstObservedAt"
KEY_FIRST_OBSERVED_COMMIT = "firstObservedCommit"
KEY_FIRST_REPORT_PATH = "firstReportPath"
KEY_LAST_OBSERVED_AT = "lastObservedAt"
KEY_LAST_OBSERVED_COMMIT = "lastObservedCommit"
KEY_LAST_REPORT_PATH = "lastReportPath"
KEY_PREVIOUS_GREEN_COMMIT = "previousGreenCommit"
KEY_PREVIOUS_GREEN_PATH = "previousGreenPath"
KEY_SUITES_STATE = "suites"
KEY_RUN_PATH = "runPath"
KEY_OK = "ok"

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
REASON_NO_BASELINE = "no baseline loaded for this suite"
REASON_NO_BASELINE_ENTRY = "no baseline entry for commandId={command_id}"
REASON_MATCH = "expected exit code and command argv match baseline"
REASON_KNOWN_FAILURE = "command still fails with baseline expected exit code {exit_code}"
REASON_FIXED = "baseline expected exit code {expected}; actual exit code is 0"
REASON_REGRESSION = "baseline expected exit code {expected}; actual exit code is {actual}"
REASON_COMMAND_DRIFT = "command argv differs from baseline"

REPORT_VERSION = 1
BASELINE_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1
HISTORY_SCHEMA_VERSION = 1

EVENT_FIRST_FAILURE = "first_failure"
EVENT_CHANGED_FAILURE = "changed_failure"
EVENT_RECOVERED = "recovered"


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
    status_reason: str
    expected_argv: Sequence[str]
    actual_argv: Sequence[str]


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
        SUITE_CROSS_SURFACE,
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
    verbose: bool = False,
) -> List[RegressionResult]:
    """
    NAME
        run_commands - Execute regression commands in order.
    """
    results: List[RegressionResult] = []
    for command in commands:
        if runner is not None:
            results.append(runner(command, REPO_ROOT))
        else:
            results.append(execute_command(command, REPO_ROOT, verbose=verbose))
    return results


def execute_command(command: RegressionCommand, workdir: Path, verbose: bool = False) -> RegressionResult:
    """
    NAME
        execute_command - Run one subprocess-backed regression command.
    """
    start_sec = time.monotonic()
    env = _subprocess_env_for_command(command, verbose=verbose)
    if verbose:
        process = subprocess.Popen(
            list(command.argv),
            cwd=str(workdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            env=env,
        )
        stdout_parts: List[str] = []
        if process.stdout is not None:
            for line in process.stdout:
                print(line, end="")
                stdout_parts.append(line)
        exit_code = int(process.wait())
        duration_sec = time.monotonic() - start_sec
        return RegressionResult(
            label=command.label,
            argv=list(command.argv),
            mode=command.mode,
            exit_code=exit_code,
            duration_sec=duration_sec,
            stdout="".join(stdout_parts),
            stderr="",
            command_id=command.command_id,
            features=tuple(command.features),
        )
    completed = subprocess.run(
        list(command.argv),
        cwd=str(workdir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
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
                status_reason=REASON_NO_BASELINE,
                expected_argv=(),
                actual_argv=tuple(command.argv),
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
                    status_reason=REASON_NO_BASELINE_ENTRY.format(command_id=command.command_id),
                    expected_argv=(),
                    actual_argv=tuple(command.argv),
                )
            )
            continue
        expected_exit_code = int(baseline_entry.get(KEY_EXPECTED_EXIT_CODE, 0))
        expected_argv = baseline_entry.get(KEY_ARGV)
        expected_argv_list = expected_argv if isinstance(expected_argv, list) else []
        argv_matches = _argv_matches_portably(command.argv, expected_argv_list)
        status = _comparison_status(expected_exit_code, int(result.exit_code), argv_matches)
        reason = _comparison_reason(
            status=status,
            expected_exit_code=expected_exit_code,
            actual_exit_code=int(result.exit_code),
        )
        comparisons.append(
            RegressionComparison(
                command_id=command.command_id,
                label=command.label,
                expected_exit_code=expected_exit_code,
                actual_exit_code=int(result.exit_code),
                status=status,
                argv_matches=argv_matches,
                status_reason=reason,
                expected_argv=tuple(str(part) for part in expected_argv_list),
                actual_argv=tuple(command.argv),
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
    metadata: Optional[Mapping[str, object]] = None,
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
        KEY_REPORT_METADATA: dict(metadata) if metadata is not None else {},
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


def history_root_path() -> Path:
    """
    NAME
        history_root_path - Resolve the local regression-history root directory.
    """
    return REPO_ROOT / HISTORY_DIRECTORY_RELATIVE


def collect_run_metadata() -> Dict[str, object]:
    """
    NAME
        collect_run_metadata - Capture repo/worktree metadata for one run.
    """
    changed_files = _git_changed_files()
    return {
        KEY_GIT: {
            KEY_COMMIT: _git_command_output("rev-parse", "HEAD"),
            KEY_BRANCH: _git_command_output("rev-parse", "--abbrev-ref", "HEAD"),
            KEY_DIRTY: len(changed_files) > 0,
            KEY_CHANGED_FILES: changed_files,
        }
    }


def write_history_for_run(
    suite_name: str,
    results: Sequence[RegressionResult],
    summary: Mapping[str, int],
    comparisons: Sequence[RegressionComparison],
    baseline_path: Optional[Path],
    metadata: Mapping[str, object],
) -> Mapping[str, object]:
    """
    NAME
        write_history_for_run - Maintain local latest pointers and failure-transition history.
    """
    root = history_root_path()
    latest_directory = root / HISTORY_LATEST_DIRECTORY_NAME
    events_directory = root / HISTORY_EVENTS_DIRECTORY_NAME / suite_name
    root.mkdir(parents=True, exist_ok=True)
    latest_directory.mkdir(parents=True, exist_ok=True)
    events_directory.mkdir(parents=True, exist_ok=True)

    timestamp = _utc_timestamp()
    latest_path = latest_directory / f"{suite_name}{HISTORY_LATEST_FILE_SUFFIX}"
    write_json_report(
        latest_path,
        suite_name=suite_name,
        results=results,
        summary=summary,
        comparisons=comparisons,
        baseline_path=baseline_path,
        metadata=metadata,
    )

    index = _load_history_index(root)
    suites_state = _history_suites_state(index)
    suite_state = _history_suite_state(suites_state, suite_name)
    suite_state[KEY_LAST_RUN_PATH] = _relative_history_path(latest_path, root)
    suite_state[KEY_LAST_RUN_AT] = timestamp

    failure_signature = _failure_signature(results, comparisons)
    previous_active = suite_state.get(KEY_ACTIVE_FAILURE)
    history_event: Dict[str, object] = {
        KEY_EVENT_TYPE: "none",
        KEY_EVENT_PATH: None,
    }

    if summary.get("failed", 0) == 0:
        last_green_path = latest_directory / f"{suite_name}{HISTORY_LAST_GREEN_FILE_SUFFIX}"
        write_json_report(
            last_green_path,
            suite_name=suite_name,
            results=results,
            summary=summary,
            comparisons=comparisons,
            baseline_path=baseline_path,
            metadata=metadata,
        )
        suite_state[KEY_LAST_GREEN_PATH] = _relative_history_path(last_green_path, root)
        suite_state[KEY_LAST_GREEN_AT] = timestamp
        suite_state[KEY_LAST_GREEN_COMMIT] = _git_commit_from_metadata(metadata)
        if isinstance(previous_active, dict):
            event_path = events_directory / f"{_history_file_timestamp(timestamp)}_{EVENT_RECOVERED}.json"
            event_payload = _history_event_payload(
                suite_name=suite_name,
                event_type=EVENT_RECOVERED,
                timestamp=timestamp,
                run_path=latest_path,
                metadata=metadata,
                summary=summary,
                previous_active=previous_active,
            )
            _write_json(event_path, event_payload)
            history_event = {
                KEY_EVENT_TYPE: EVENT_RECOVERED,
                KEY_EVENT_PATH: _relative_history_path(event_path, root),
            }
        suite_state.pop(KEY_ACTIVE_FAILURE, None)
    else:
        current_signature = failure_signature
        previous_signature = _failure_signature_from_state(previous_active)
        if current_signature != previous_signature:
            event_type = EVENT_FIRST_FAILURE if previous_signature is None else EVENT_CHANGED_FAILURE
            event_path = events_directory / f"{_history_file_timestamp(timestamp)}_{event_type}.json"
            event_payload = _history_event_payload(
                suite_name=suite_name,
                event_type=event_type,
                timestamp=timestamp,
                run_path=latest_path,
                metadata=metadata,
                summary=summary,
                current_signature=current_signature,
                previous_active=previous_active if isinstance(previous_active, dict) else None,
                previous_green_commit=_optional_str(suite_state.get(KEY_LAST_GREEN_COMMIT)),
                previous_green_path=_optional_str(suite_state.get(KEY_LAST_GREEN_PATH)),
            )
            _write_json(event_path, event_payload)
            history_event = {
                KEY_EVENT_TYPE: event_type,
                KEY_EVENT_PATH: _relative_history_path(event_path, root),
            }
            suite_state[KEY_ACTIVE_FAILURE] = {
                KEY_FAILURE_SIGNATURE: list(current_signature),
                KEY_FIRST_OBSERVED_AT: timestamp if previous_signature is None else previous_active.get(KEY_FIRST_OBSERVED_AT),
                KEY_FIRST_OBSERVED_COMMIT: _git_commit_from_metadata(metadata) if previous_signature is None else previous_active.get(KEY_FIRST_OBSERVED_COMMIT),
                KEY_FIRST_REPORT_PATH: _relative_history_path(event_path, root) if previous_signature is None else previous_active.get(KEY_FIRST_REPORT_PATH),
                KEY_LAST_OBSERVED_AT: timestamp,
                KEY_LAST_OBSERVED_COMMIT: _git_commit_from_metadata(metadata),
                KEY_LAST_REPORT_PATH: _relative_history_path(event_path, root),
                KEY_PREVIOUS_GREEN_COMMIT: _optional_str(suite_state.get(KEY_LAST_GREEN_COMMIT)),
                KEY_PREVIOUS_GREEN_PATH: _optional_str(suite_state.get(KEY_LAST_GREEN_PATH)),
            }
        elif isinstance(previous_active, dict):
            previous_active[KEY_LAST_OBSERVED_AT] = timestamp
            previous_active[KEY_LAST_OBSERVED_COMMIT] = _git_commit_from_metadata(metadata)
            suite_state[KEY_ACTIVE_FAILURE] = previous_active

    _write_history_index(root, index)
    return {
        KEY_RUN_PATH: str(latest_path),
        KEY_EVENT: history_event,
    }


def _load_history_index(root: Path) -> Dict[str, object]:
    index_path = root / HISTORY_INDEX_FILE_NAME
    if not index_path.exists():
        return {
            KEY_HISTORY_VERSION: HISTORY_SCHEMA_VERSION,
            KEY_SUITES_STATE: {},
        }
    with index_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return {
            KEY_HISTORY_VERSION: HISTORY_SCHEMA_VERSION,
            KEY_SUITES_STATE: {},
        }
    payload.setdefault(KEY_HISTORY_VERSION, HISTORY_SCHEMA_VERSION)
    payload.setdefault(KEY_SUITES_STATE, {})
    return payload


def _write_history_index(root: Path, payload: Mapping[str, object]) -> None:
    index_path = root / HISTORY_INDEX_FILE_NAME
    _write_json(index_path, payload)


def _history_suites_state(index: Dict[str, object]) -> Dict[str, object]:
    suites = index.get(KEY_SUITES_STATE)
    if isinstance(suites, dict):
        return suites
    suites = {}
    index[KEY_SUITES_STATE] = suites
    return suites


def _history_suite_state(suites: Dict[str, object], suite_name: str) -> Dict[str, object]:
    suite_state = suites.get(suite_name)
    if isinstance(suite_state, dict):
        return suite_state
    suite_state = {}
    suites[suite_name] = suite_state
    return suite_state


def _failure_signature(results: Sequence[RegressionResult], comparisons: Sequence[RegressionComparison]) -> List[str]:
    items: List[str] = []
    comparison_by_id = {comparison.command_id: comparison for comparison in comparisons}
    for result in results:
        if result.ok:
            continue
        comparison = comparison_by_id.get(result.command_id)
        comparison_status = comparison.status if comparison is not None else STATUS_MISSING_BASELINE
        items.append(f"{result.command_id}:{result.exit_code}:{comparison_status}")
    return items


def _failure_signature_from_state(active_failure: object) -> Optional[List[str]]:
    if not isinstance(active_failure, dict):
        return None
    value = active_failure.get(KEY_FAILURE_SIGNATURE)
    if not isinstance(value, list):
        return None
    return [str(item) for item in value]


def _history_event_payload(
    suite_name: str,
    event_type: str,
    timestamp: str,
    run_path: Path,
    metadata: Mapping[str, object],
    summary: Mapping[str, int],
    current_signature: Optional[Sequence[str]] = None,
    previous_active: Optional[Mapping[str, object]] = None,
    previous_green_commit: Optional[str] = None,
    previous_green_path: Optional[str] = None,
) -> Dict[str, object]:
    payload: Dict[str, object] = {
        KEY_HISTORY_VERSION: HISTORY_SCHEMA_VERSION,
        KEY_SUITE: suite_name,
        KEY_EVENT_TYPE: event_type,
        KEY_EVENT_AT: timestamp,
        KEY_RUN_PATH: str(run_path),
        KEY_SUMMARY: dict(summary),
        KEY_REPORT_METADATA: dict(metadata),
    }
    if current_signature is not None:
        payload[KEY_FAILURE_SIGNATURE] = list(current_signature)
    if previous_active is not None:
        payload[KEY_ACTIVE_FAILURE] = dict(previous_active)
    if previous_green_commit is not None:
        payload[KEY_PREVIOUS_GREEN_COMMIT] = previous_green_commit
    if previous_green_path is not None:
        payload[KEY_PREVIOUS_GREEN_PATH] = previous_green_path
    return payload


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _relative_history_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _optional_str(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _git_command_output(*argv: str) -> str:
    try:
        completed = subprocess.run(
            ("git", *argv),
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return "unknown"
    if completed.returncode != EXIT_OK:
        return "unknown"
    text = completed.stdout.strip()
    return text if text else "unknown"


def _git_changed_files() -> List[str]:
    try:
        completed = subprocess.run(
            ("git", "status", "--short"),
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return []
    if completed.returncode != EXIT_OK:
        return []
    lines = [line.rstrip() for line in completed.stdout.splitlines() if line.strip()]
    files: List[str] = []
    for line in lines:
        if len(line) <= 3:
            continue
        files.append(line[3:])
    return files


def _git_commit_from_metadata(metadata: Mapping[str, object]) -> str:
    git_info = metadata.get(KEY_GIT)
    if isinstance(git_info, dict):
        commit = _optional_str(git_info.get(KEY_COMMIT))
        if commit is not None:
            return commit
    return "unknown"


def _history_file_timestamp(timestamp: str) -> str:
    return timestamp.replace(":", "").replace("-", "").replace("T", "_").replace("Z", "")


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


def _subprocess_env_for_command(command: RegressionCommand, verbose: bool = False) -> Dict[str, str]:
    env = dict(os.environ)
    if verbose:
        env[REGRESSION_VERBOSE_ENV] = TEXT_TRUE
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


def _argv_matches_portably(actual: Sequence[str], expected: Sequence[object]) -> bool:
    """
    NAME
        _argv_matches_portably - Compare command argv without machine-local paths.

    DESCRIPTION
        Baselines are written with resolved paths, but Python install locations
        and repo checkout roots vary across machines. Normalize those stable
        command roles before deciding whether the command changed.
    """
    return _portable_argv(actual) == _portable_argv(expected)


def _portable_argv(argv: Sequence[object]) -> List[str]:
    """
    NAME
        _portable_argv - Normalize argv entries for baseline comparison.
    """
    return [_portable_argv_part(str(part)) for part in argv]


def _portable_argv_part(value: str) -> str:
    """
    NAME
        _portable_argv_part - Normalize one argv entry for baseline comparison.
    """
    normalized = value.replace("\\", "/")
    name = Path(normalized).name.lower()
    if name.startswith(PYTHON_EXE_STEM) and (
        name == PYTHON_EXE_STEM or name.endswith(WINDOWS_EXE_SUFFIX)
    ):
        return TOKEN_PYTHON
    if name == GRADLEW_WINDOWS:
        return TOKEN_GRADLEW
    for marker in (TOOLS_PATH_MARKER, TESTS_PATH_MARKER):
        marker_index = normalized.find(marker)
        if marker_index >= 0:
            return TOKEN_REPO + normalized[marker_index:]
    return normalized


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


def _comparison_reason(status: str, expected_exit_code: int, actual_exit_code: int) -> str:
    """
    NAME
        _comparison_reason - Explain why a baseline comparison status was chosen.
    """
    if status == STATUS_COMMAND_DRIFT:
        return REASON_COMMAND_DRIFT
    if status == STATUS_MATCH:
        return REASON_MATCH
    if status == STATUS_KNOWN_FAILURE:
        return REASON_KNOWN_FAILURE.format(exit_code=actual_exit_code)
    if status == STATUS_FIXED:
        return REASON_FIXED.format(expected=expected_exit_code)
    return REASON_REGRESSION.format(expected=expected_exit_code, actual=actual_exit_code)


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
