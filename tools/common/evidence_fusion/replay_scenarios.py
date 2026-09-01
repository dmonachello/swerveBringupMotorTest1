from __future__ import annotations

"""
NAME
    replay_scenarios.py - Offline canned-block runner for evidence-fusion shadow testing.

SYNOPSIS
    python tools/common/evidence_fusion/replay_scenarios.py --list
    python tools/common/evidence_fusion/replay_scenarios.py --scenario present_only
    python tools/common/evidence_fusion/replay_scenarios.py --all --verbose

DESCRIPTION
    Loads committed JSON scenarios, submits EvidenceBlock envelopes through the
    production EvidenceFusionEngine, drains scheduled evaluation work, and
    prints the resulting shadow snapshot. This harness is intentionally
    headless so the fusion algorithm can be exercised without UI, REST, CAN,
    or roboRIO dependencies.
"""

import os
import sys

if __package__ in ("", None):
    SCRIPT_PATH = os.path.abspath(__file__)
    SCRIPT_DIRECTORY = os.path.dirname(SCRIPT_PATH)
    REPO_ROOT = os.path.dirname(
        os.path.dirname(
            os.path.dirname(SCRIPT_DIRECTORY)
        )
    )
    if sys.path and sys.path[0] == SCRIPT_DIRECTORY:
        sys.path.pop(0)
    sys.path.insert(0, REPO_ROOT)

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from tools.common.evidence_fusion.api import EvidenceFusionEngine
from tools.common.evidence_fusion.types import (
    DrainResult,
    EvaluationBudget,
    EvidenceBlock,
    EvidenceTarget,
    SubmitResult,
)
from tools.common.json_io import read_json

ARG_LIST = "--list"
ARG_SCENARIO = "--scenario"
ARG_ALL = "--all"
ARG_VERBOSE = "--verbose"
ARG_SHOW_OBSERVATIONS = "--show-observations"
ARG_JSON = "--json"

SCENARIO_DIR_RELATIVE = Path("tests/regression/fixtures/evidence_fusion")
SCENARIO_SUFFIX = ".json"
STEP_KEY_SUBMIT = "submit"
STEP_KEY_DRAIN = "drain"
STEP_KEY_NOTE = "note"
STEP_KEY_EXPECT = "expect"
BLOCK_KEY_TARGET = "target"
DRAIN_KEY_NOW_MS = "nowMonotonicMs"
DRAIN_KEY_MAX_WORK_ITEMS = "maxWorkItems"
DEFAULT_MAX_WORK_ITEMS = 100

TEXT_ACTION_SUBMIT = "submit"
TEXT_ACTION_DRAIN = "drain"
TEXT_ACTION_NOTE = "note"
TEXT_ACTION_EXPECT = "expect"
TEXT_NO_SCENARIO_SELECTED = "Select one scenario with --scenario or use --all."
TEXT_SCENARIO_NOT_FOUND = "Scenario not found"
TEXT_NO_SCENARIOS_FOUND = "No replay scenarios found."


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _scenario_directory() -> Path:
    return _repo_root() / SCENARIO_DIR_RELATIVE


def _scenario_name_from_path(path: Path) -> str:
    return path.stem


def _scenario_paths() -> List[Path]:
    directory = _scenario_directory()
    if not directory.exists():
        return []
    return sorted(directory.glob(f"*{SCENARIO_SUFFIX}"))


def _load_scenario_payload(name: str) -> Dict[str, Any]:
    candidate = _scenario_directory() / f"{name}{SCENARIO_SUFFIX}"
    if not candidate.exists():
        raise FileNotFoundError(f"{TEXT_SCENARIO_NOT_FOUND}: {candidate}")
    payload = read_json(candidate)
    if not isinstance(payload, dict):
        raise ValueError(f"Scenario payload must be an object: {candidate}")
    return payload


def _target_from_payload(payload: Any) -> EvidenceTarget | None:
    if not isinstance(payload, dict):
        return None
    return EvidenceTarget(
        configured_label=payload.get("configured_label"),
        vendor=payload.get("vendor"),
        device_type=payload.get("device_type"),
        interface_type=payload.get("interface_type"),
        bus_name=payload.get("bus_name"),
        address_value=payload.get("address_value"),
        mechanism_name=payload.get("mechanism_name"),
        target_confidence=payload.get("target_confidence"),
    )


def _block_from_payload(payload: Dict[str, Any]) -> EvidenceBlock:
    return EvidenceBlock(
        schema_version=int(payload["schema_version"]),
        block_id=str(payload["block_id"]),
        source_type=str(payload["source_type"]),
        source_instance=str(payload["source_instance"]),
        source_session_id=str(payload["source_session_id"]),
        major_type=str(payload["major_type"]),
        scope=str(payload["scope"]),
        target=_target_from_payload(payload.get(BLOCK_KEY_TARGET)),
        observed_at_monotonic_ms=int(payload["observed_at_monotonic_ms"]),
        received_at_monotonic_ms=int(payload["received_at_monotonic_ms"]),
        context_revision_id=str(payload["context_revision_id"]),
        correlation_id=payload.get("correlation_id"),
        priority_hint=str(payload["priority_hint"]),
        payload=dict(payload.get("payload", {})),
    )


def _run_scenario_payload(
    payload: Dict[str, Any],
    *,
    verbose: bool,
) -> Dict[str, Any]:
    engine = EvidenceFusionEngine()
    steps = payload.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError("Scenario 'steps' must be a list.")
    submit_results: List[Dict[str, Any]] = []
    drain_results: List[Dict[str, Any]] = []
    step_log: List[Dict[str, Any]] = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"Step {index} must be an object.")
        if STEP_KEY_NOTE in step:
            note = str(step.get(STEP_KEY_NOTE, "")).strip()
            if verbose:
                print(f"[{index}] {TEXT_ACTION_NOTE}: {note}")
            step_log.append({"step": index, "action": TEXT_ACTION_NOTE, "note": note})
            continue
        if STEP_KEY_SUBMIT in step:
            blocks = step.get(STEP_KEY_SUBMIT, [])
            if not isinstance(blocks, list):
                raise ValueError(f"Step {index} submit must be a list.")
            for block_payload in blocks:
                block = _block_from_payload(dict(block_payload))
                result = engine.submit_evidence_block(block)
                submit_results.append(asdict(result))
                if verbose:
                    print(
                        f"[{index}] {TEXT_ACTION_SUBMIT}: {block.block_id} -> "
                        f"{result.result_code} lane={result.queue_lane}"
                    )
            step_log.append({"step": index, "action": TEXT_ACTION_SUBMIT, "count": len(blocks)})
            continue
        if STEP_KEY_DRAIN in step:
            drain_payload = step.get(STEP_KEY_DRAIN, {})
            if not isinstance(drain_payload, dict):
                raise ValueError(f"Step {index} drain must be an object.")
            now_monotonic_ms = int(drain_payload.get(DRAIN_KEY_NOW_MS, 0))
            max_work_items = int(drain_payload.get(DRAIN_KEY_MAX_WORK_ITEMS, DEFAULT_MAX_WORK_ITEMS))
            result = engine.drain_evaluation_budget(
                now_monotonic_ms,
                EvaluationBudget(max_work_items=max_work_items),
            )
            drain_results.append(asdict(result))
            if verbose:
                print(
                    f"[{index}] {TEXT_ACTION_DRAIN}: now={now_monotonic_ms} "
                    f"processed={result.work_items_processed} pending={result.pending_work_items}"
                )
            step_log.append(
                {
                    "step": index,
                    "action": TEXT_ACTION_DRAIN,
                    "nowMonotonicMs": now_monotonic_ms,
                    "maxWorkItems": max_work_items,
                }
            )
            continue
        if STEP_KEY_EXPECT in step:
            expectation = step.get(STEP_KEY_EXPECT)
            step_log.append({"step": index, "action": TEXT_ACTION_EXPECT, "expect": expectation})
            if verbose:
                print(f"[{index}] {TEXT_ACTION_EXPECT}: documented expectation")
            continue
        raise ValueError(f"Step {index} has no supported action.")
    snapshot = engine.get_current_snapshot()
    return {
        "name": str(payload.get("name", "")).strip(),
        "description": str(payload.get("description", "")).strip(),
        "submitResults": submit_results,
        "drainResults": drain_results,
        "stepLog": step_log,
        "snapshot": {
            "snapshot_id": snapshot.snapshot_id,
            "evaluation_id": snapshot.evaluation_id,
            "context_revision_id": snapshot.context_revision_id,
            "evaluation_time_monotonic_ms": snapshot.evaluation_time_monotonic_ms,
            "configured_devices": snapshot.configured_devices,
            "unknown_observed_devices": {
                key: asdict(value)
                for key, value in snapshot.unknown_observed_devices.items()
            },
            "system_state": snapshot.system_state,
            "runtime_stats": asdict(snapshot.runtime_stats),
            "observation_states": {
                key: asdict(value)
                for key, value in snapshot.observation_states.items()
            },
        },
    }


def _format_text_report(report: Dict[str, Any], *, show_observations: bool) -> str:
    lines: List[str] = []
    lines.append(f"Scenario: {report.get('name', '')}")
    description = str(report.get("description", "")).strip()
    if description:
        lines.append(f"Description: {description}")
    snapshot = dict(report.get("snapshot", {}))
    lines.append(f"Evaluation: {snapshot.get('evaluation_id', '')}")
    lines.append(f"Snapshot: {snapshot.get('snapshot_id', '')}")
    configured_devices = snapshot.get("configured_devices", {})
    lines.append(f"Configured devices: {len(configured_devices)}")
    for label in sorted(configured_devices.keys()):
        device_result = configured_devices[label]
        lines.append(f"- {label}")
        lines.append(f"  overall={device_result.get('overallState', '')}")
        dimensions = device_result.get("dimensions", {})
        for dimension_name in ("existence", "communication", "operability", "identity"):
            dimension_result = dimensions.get(dimension_name, {})
            lines.append(
                "  "
                + f"{dimension_name}="
                + f"{dimension_result.get('value', '')}"
                + f" confidence={dimension_result.get('confidence', 0.0):.3f}"
                + f" band={dimension_result.get('confidenceBand', '')}"
                + f" conflict={dimension_result.get('conflict', False)}"
            )
    if show_observations:
        observation_states = snapshot.get("observation_states", {})
        lines.append(f"Observation states: {len(observation_states)}")
        for block_id in sorted(observation_states.keys()):
            current = observation_states[block_id]
            lines.append(
                "- "
                + f"{block_id} state={current.get('freshness_state', '')}"
                + f" influence={current.get('current_influence', 0.0):.3f}"
                + f" label={current.get('configured_label', '')}"
            )
    return "\n".join(lines)


def _selected_scenarios(args: argparse.Namespace) -> List[str]:
    if bool(args.all):
        return [_scenario_name_from_path(path) for path in _scenario_paths()]
    scenario_name = str(args.scenario or "").strip()
    if scenario_name:
        return [scenario_name]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline evidence-fusion replay harness.")
    parser.add_argument(ARG_LIST, action="store_true", dest="list_scenarios")
    parser.add_argument(ARG_SCENARIO, default="")
    parser.add_argument(ARG_ALL, action="store_true")
    parser.add_argument(ARG_VERBOSE, action="store_true")
    parser.add_argument(ARG_SHOW_OBSERVATIONS, action="store_true")
    parser.add_argument(ARG_JSON, action="store_true", dest="emit_json")
    args = parser.parse_args()

    if bool(args.list_scenarios):
        paths = _scenario_paths()
        if not paths:
            print(TEXT_NO_SCENARIOS_FOUND)
            return 1
        for path in paths:
            print(_scenario_name_from_path(path))
        return 0

    scenario_names = _selected_scenarios(args)
    if not scenario_names:
        print(TEXT_NO_SCENARIO_SELECTED)
        return 1

    reports = []
    for scenario_name in scenario_names:
        payload = _load_scenario_payload(scenario_name)
        reports.append(
            _run_scenario_payload(
                payload,
                verbose=bool(args.verbose),
            )
        )
    if bool(args.emit_json):
        print(json.dumps(reports if len(reports) > 1 else reports[0], indent=2))
        return 0
    for index, report in enumerate(reports):
        if index > 0:
            print()
        print(
            _format_text_report(
                report,
                show_observations=bool(args.show_observations),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
