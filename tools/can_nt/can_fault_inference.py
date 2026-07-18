from __future__ import annotations

"""
NAME
    can_fault_inference.py - Host-side CAN fault-candidate inference.

SYNOPSIS
    from tools.can_nt.can_fault_inference import build_fault_diagnosis

DESCRIPTION
    Converts already-normalized device evidence rows, console state, and
    optional topology into ranked CAN fault candidates. This module is read-only
    and does not communicate with the robot or the CAN bus.
"""

import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from tools.common.profile_constants import (
    EDGE_TYPE_CAN_DROP,
    EDGE_TYPE_CAN_TAP,
    EDGE_TYPE_CAN_TRUNK,
    KEY_DEVICE_REF,
    KEY_EDGE_ID,
    KEY_EDGE_TYPE,
    KEY_FROM_NODE,
    KEY_NODE_KEY,
    KEY_OBJECT_TYPE,
    KEY_TO_NODE,
    KEY_TOPOLOGY_EDGES,
    KEY_TOPOLOGY_NODES,
    NODE_TYPE_DEVICE,
)


KEY_AFFECTED_DEVICES = "affectedDevices"
KEY_CANDIDATES = "candidates"
KEY_CONFIDENCE = "confidence"
KEY_CONFLICTING_EVIDENCE = "conflictingEvidence"
KEY_EVIDENCE_ROWS = "evidenceRows"
KEY_FAULT_CLASS = "faultClass"
KEY_LABEL = "label"
KEY_NOTES = "notes"
KEY_OBSERVATION = "observation"
KEY_RAN_AT_EPOCH_SEC = "ranAtEpochSec"
KEY_RECOMMENDED_CHECKS = "recommendedChecks"
KEY_SOURCE_AGES = "sourceAges"
KEY_STATUS = "status"
KEY_SUMMARY = "summary"
KEY_SUPPORTING_EVIDENCE = "supportingEvidence"
KEY_SUSPECTED_REGION = "suspectedRegion"
KEY_TOPOLOGY_AVAILABLE = "topologyAvailable"
KEY_INFRASTRUCTURE = "infrastructure"
KEY_INFRA_VISIBLE = "visible"
KEY_INFRA_STALE = "stale"
KEY_INFRA_MISSING = "missing"
KEY_INFRA_CONFLICT = "conflict"

ROW_KEY_CONFIDENCE = "confidence"
ROW_KEY_CONFLICTED = "conflicted"
ROW_KEY_CONSOLE = "console"
ROW_KEY_DEVICE_TYPE = "deviceType"
ROW_KEY_EXISTENCE = "existence"
ROW_KEY_MANUAL = "manual"
ROW_KEY_NOTES_TEXT = "notesText"
ROW_KEY_OPERABILITY = "operability"
ROW_KEY_PASSIVE = "passive"
ROW_KEY_PRESENCE_SCORE = "presenceScore"
ROW_KEY_PRESENCE_STATE = "presenceState"
ROW_KEY_PRESENCE_REASONS = "presenceReasons"
ROW_KEY_PROBE = "probe"
ROW_KEY_STATE = "state"
ROW_KEY_SOURCE_SCORES = "sourceScores"
PASSIVE_TOKEN_PRESENCE_PREFIX = "presence="
PASSIVE_TOKEN_SCORE_PREFIX = "score="
PASSIVE_TOKEN_PACKET_PREFIX = "packets="
PASSIVE_TOKEN_LAST_SEEN_PREFIX = "lastseen="
PASSIVE_PRESENCE_VALUES = {"high", "medium", "low", "uncertain"}
INFRASTRUCTURE_LABELS = {"roborio", "pdp", "pdh"}

CONSOLE_KEY_SYSTEM_CONFLICT = "systemConflict"
CONSOLE_KEY_SYSTEM_TEXT = "systemText"

STATUS_OK = "ok"
STATUS_NO_FAULT = "no_fault_detected"
STATUS_INSUFFICIENT = "insufficient_evidence"

FAULT_CLASS_SINGLE_DEVICE = "single_device_unreachable"
FAULT_CLASS_BRANCH = "possible_branch_isolation"
FAULT_CLASS_TRUNK = "possible_trunk_break"
FAULT_CLASS_CONTROLLER_SIDE = "possible_controller_side_isolation"
FAULT_CLASS_BUS_WIDE = "bus_wide_error_pressure"
FAULT_CLASS_STALE = "intermittent_or_stale_visibility"
FAULT_CLASS_TOPOLOGY = "topology_or_profile_mismatch"
FAULT_CLASS_INSUFFICIENT = "insufficient_evidence"

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"

VALUE_PRESENT = "PRESENT"
VALUE_ABSENT = "ABSENT"
VALUE_FAILED = "FAILED"
VALUE_DEGRADED = "DEGRADED"
VALUE_CONFLICT = "CONFLICT"
VALUE_UNKNOWN = "UNKNOWN"

STATE_FAILED = "failed"
STATE_MISSING = "missing"
STATE_DEGRADED = "degraded"
STATE_UNKNOWN = "unknown"
PRESENCE_STATE_PRESENT = "present"
PRESENCE_STATE_MISSING = "missing"
PRESENCE_STATE_UNKNOWN = "unknown"
PRESENCE_STATE_CONFLICT = "conflict"

TEXT_NO_ACTIVE_FAULT = "No active CAN fault candidate from current evidence."
TEXT_INSUFFICIENT = "Not enough evidence to rank a CAN fault candidate."
TEXT_BUS_WIDE = "Multiple devices or system evidence indicate broad CAN pressure."
TEXT_BRANCH = "Multiple affected devices share a topology-connected CAN region."
TEXT_TRUNK = "Most expected CAN devices are affected; possible trunk/controller-side issue."
TEXT_SINGLE = "One device has strong missing or failed evidence."
TEXT_STALE = "Evidence is stale or conflicted; rerun observation before physical conclusions."
TEXT_TOPOLOGY = "Topology/profile evidence is insufficient or mismatched."
TEXT_CONTROLLER = "Robot-local and passive/device evidence appear disconnected or stale."

RECHECK_OBSERVATION = "Run CAN Break Check again after reseating or power-cycling."
CHECK_SINGLE_FMT = "Inspect power and CAN connectors at {label} first."
CHECK_BRANCH = "Inspect the shared CAN branch or connector feeding the affected devices."
CHECK_TRUNK = "Inspect trunk wiring from the roboRIO side toward the affected group."
CHECK_BUS_WIDE = "Check roboRIO CAN status, termination, power, and broad wiring disturbance."
CHECK_TOPOLOGY = "Verify the selected profile and topology match the robot wiring."
CHECK_STALE = "Refresh robot connection, clear stale probe data, then rerun the observation."
CHECK_CONTROLLER = "Verify roboRIO power/code connection and compare robot-local versus passive CAN evidence."
CHECK_INFRA = "Inspect infrastructure power/CAN connections at the affected singleton device first."

CAN_EDGE_TYPES = {EDGE_TYPE_CAN_TRUNK, EDGE_TYPE_CAN_DROP, EDGE_TYPE_CAN_TAP}


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _row_label(row: Mapping[str, Any]) -> str:
    return _clean_text(row.get(KEY_LABEL))


def _is_infrastructure_label(label: object) -> bool:
    return _clean_text(label).lower() in INFRASTRUCTURE_LABELS


def _is_infrastructure_row(row: Mapping[str, Any]) -> bool:
    return _is_infrastructure_label(row.get(KEY_LABEL))


def _passive_token_values(row: Mapping[str, Any]) -> List[str]:
    passive_text = _clean_text(row.get(ROW_KEY_PASSIVE)).lower()
    if not passive_text or passive_text == "--":
        return []
    return [
        token.strip()
        for token in passive_text.replace("|", " ").replace(";", " ").split()
        if token.strip()
    ]


def _token_float(token: str, prefix: str) -> Optional[float]:
    if not token.startswith(prefix):
        return None
    value_text = token[len(prefix) :].strip()
    if "/" in value_text:
        value_text = value_text.split("/", 1)[0].strip()
    try:
        return float(value_text)
    except ValueError:
        return None


def _observer_indicates_presence(row: Mapping[str, Any]) -> bool:
    presence_state = _clean_text(row.get(ROW_KEY_PRESENCE_STATE)).lower()
    presence_score = row.get(ROW_KEY_PRESENCE_SCORE)
    if presence_state == PRESENCE_STATE_PRESENT:
        return True
    if isinstance(presence_score, (int, float)) and float(presence_score) >= 50.0:
        return True
    source_scores = row.get(ROW_KEY_SOURCE_SCORES)
    if isinstance(source_scores, Mapping):
        for source_name in ("passive", "runtime", "probe", "enrichment"):
            source_entry = source_scores.get(source_name)
            if not isinstance(source_entry, Mapping):
                continue
            source_state = _clean_text(source_entry.get("state")).lower()
            source_score = source_entry.get("score")
            if source_state == PRESENCE_STATE_PRESENT:
                return True
            if isinstance(source_score, (int, float)) and float(source_score) >= 70.0:
                return True
    for token in _passive_token_values(row):
        if token.startswith(PASSIVE_TOKEN_PRESENCE_PREFIX):
            value = token[len(PASSIVE_TOKEN_PRESENCE_PREFIX) :].strip()
            if value in PASSIVE_PRESENCE_VALUES:
                return True
        score = _token_float(token, PASSIVE_TOKEN_SCORE_PREFIX)
        if score is not None and score > 0.0:
            return True
        packets = _token_float(token, PASSIVE_TOKEN_PACKET_PREFIX)
        if packets is not None and packets > 0.0:
            return True
        if token.startswith(PASSIVE_TOKEN_LAST_SEEN_PREFIX):
            return True
    return False


def _infrastructure_bucket(row: Mapping[str, Any]) -> str:
    existence = _clean_text(row.get(ROW_KEY_EXISTENCE)).upper()
    state = _clean_text(row.get(ROW_KEY_STATE)).lower()
    presence_state = _clean_text(row.get(ROW_KEY_PRESENCE_STATE)).lower()
    conflicted = bool(row.get(ROW_KEY_CONFLICTED))
    observer_present = _observer_indicates_presence(row)
    if conflicted:
        return KEY_INFRA_CONFLICT
    if presence_state == PRESENCE_STATE_CONFLICT:
        return KEY_INFRA_CONFLICT
    if observer_present:
        if presence_state == PRESENCE_STATE_UNKNOWN or existence == VALUE_UNKNOWN or state == STATE_UNKNOWN:
            return KEY_INFRA_STALE
        return KEY_INFRA_VISIBLE
    if presence_state == PRESENCE_STATE_MISSING or existence == VALUE_ABSENT or state == STATE_MISSING:
        return KEY_INFRA_MISSING
    if presence_state == PRESENCE_STATE_UNKNOWN or existence == VALUE_UNKNOWN or state == STATE_UNKNOWN:
        return KEY_INFRA_STALE
    return KEY_INFRA_VISIBLE


def _is_affected_row(row: Mapping[str, Any]) -> bool:
    state = _clean_text(row.get(ROW_KEY_STATE)).lower()
    existence = _clean_text(row.get(ROW_KEY_EXISTENCE)).upper()
    operability = _clean_text(row.get(ROW_KEY_OPERABILITY)).upper()
    presence_state = _clean_text(row.get(ROW_KEY_PRESENCE_STATE)).lower()
    if operability in {VALUE_FAILED, VALUE_CONFLICT}:
        return True
    if state == STATE_FAILED:
        return True
    if presence_state == PRESENCE_STATE_CONFLICT:
        return True
    if _observer_indicates_presence(row) and (state == STATE_MISSING or existence == VALUE_ABSENT):
        return False
    if presence_state == PRESENCE_STATE_MISSING:
        return True
    if state == STATE_MISSING:
        return True
    return existence in {VALUE_ABSENT, VALUE_CONFLICT}


def _is_degraded_row(row: Mapping[str, Any]) -> bool:
    if _is_affected_row(row):
        return True
    state = _clean_text(row.get(ROW_KEY_STATE)).lower()
    operability = _clean_text(row.get(ROW_KEY_OPERABILITY)).upper()
    return state == STATE_DEGRADED or operability == VALUE_DEGRADED


def _row_support(row: Mapping[str, Any]) -> List[str]:
    parts: List[str] = []
    for key in (ROW_KEY_PASSIVE, ROW_KEY_CONSOLE, ROW_KEY_PROBE, ROW_KEY_MANUAL):
        value = _clean_text(row.get(key))
        if value and value != "--":
            parts.append(f"{key}={value}")
    notes = _clean_text(row.get(ROW_KEY_NOTES_TEXT))
    if notes and notes != "--":
        parts.append(f"notes={notes}")
    return parts


def _candidate(
    *,
    fault_class: str,
    confidence: str,
    summary: str,
    affected: Iterable[str],
    region: str,
    supporting: Iterable[str],
    conflicting: Iterable[str],
    checks: Iterable[str],
) -> Dict[str, Any]:
    return {
        KEY_FAULT_CLASS: fault_class,
        KEY_CONFIDENCE: confidence,
        KEY_SUMMARY: summary,
        KEY_AFFECTED_DEVICES: list(affected),
        KEY_SUSPECTED_REGION: region,
        KEY_SUPPORTING_EVIDENCE: list(supporting),
        KEY_CONFLICTING_EVIDENCE: list(conflicting),
        KEY_RECOMMENDED_CHECKS: list(checks),
        KEY_SOURCE_AGES: {},
    }


def _topology_graph(topology_profile: Optional[Mapping[str, Any]]) -> Tuple[Dict[str, int], Dict[int, Set[int]]]:
    label_to_node: Dict[str, int] = {}
    graph: Dict[int, Set[int]] = {}
    if not isinstance(topology_profile, Mapping):
        return label_to_node, graph
    nodes = topology_profile.get(KEY_TOPOLOGY_NODES)
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, Mapping):
                continue
            node_key = node.get(KEY_NODE_KEY)
            if not isinstance(node_key, int):
                continue
            graph.setdefault(node_key, set())
            object_type = _clean_text(node.get(KEY_OBJECT_TYPE))
            if object_type == NODE_TYPE_DEVICE:
                label = _clean_text(node.get(KEY_DEVICE_REF)).lower()
                if label:
                    label_to_node[label] = node_key
    edges = topology_profile.get(KEY_TOPOLOGY_EDGES)
    if isinstance(edges, list):
        for edge in edges:
            if not isinstance(edge, Mapping):
                continue
            edge_type = _clean_text(edge.get(KEY_EDGE_TYPE))
            if edge_type not in CAN_EDGE_TYPES:
                continue
            left = edge.get(KEY_FROM_NODE)
            right = edge.get(KEY_TO_NODE)
            if not isinstance(left, int) or not isinstance(right, int):
                continue
            graph.setdefault(left, set()).add(right)
            graph.setdefault(right, set()).add(left)
    return label_to_node, graph


def _connected_components(nodes: Set[int], graph: Mapping[int, Set[int]]) -> List[Set[int]]:
    remaining = set(nodes)
    components: List[Set[int]] = []
    while remaining:
        start = remaining.pop()
        component = {start}
        stack = [start]
        while stack:
            current = stack.pop()
            for neighbor in graph.get(current, set()):
                if neighbor not in remaining:
                    continue
                remaining.remove(neighbor)
                component.add(neighbor)
                stack.append(neighbor)
        components.append(component)
    return components


def _topology_region_for_labels(labels: Iterable[str], topology_profile: Optional[Mapping[str, Any]]) -> Tuple[str, bool]:
    label_to_node, graph = _topology_graph(topology_profile)
    node_keys = {
        label_to_node[label.lower()]
        for label in labels
        if label.lower() in label_to_node
    }
    if not node_keys:
        return "topology region unknown", False
    components = _connected_components(node_keys, graph)
    if len(components) == 1:
        return "connected CAN topology region", True
    return "multiple topology regions", True


def build_fault_diagnosis(
    *,
    evidence_rows: Iterable[Mapping[str, Any]],
    console_snapshot: Optional[Mapping[str, Any]] = None,
    topology_profile: Optional[Mapping[str, Any]] = None,
    now_s: Optional[float] = None,
) -> Dict[str, Any]:
    """
    NAME
        build_fault_diagnosis - Build ranked CAN fault candidates.

    PARAMETERS
        evidence_rows: Interpreted per-device evidence rows.
        console_snapshot: Optional system/device console evidence.
        topology_profile: Optional topology graph for region grouping.
        now_s: Optional timestamp for deterministic tests.

    RETURNS
        Dictionary containing observation metadata and ranked candidates.
    """
    ran_at = time.time() if now_s is None else float(now_s)
    rows = [dict(row) for row in evidence_rows if isinstance(row, Mapping)]
    infrastructure_rows = [row for row in rows if _is_infrastructure_row(row)]
    affected_rows = [row for row in rows if _is_affected_row(row)]
    degraded_rows = [row for row in rows if _is_degraded_row(row)]
    affected_labels = [_row_label(row) for row in affected_rows if _row_label(row)]
    degraded_labels = [_row_label(row) for row in degraded_rows if _row_label(row)]
    affected_set = set(affected_labels)
    degraded_only_labels = [label for label in degraded_labels if label not in affected_set]
    console = console_snapshot if isinstance(console_snapshot, Mapping) else {}
    system_conflict = bool(console.get(CONSOLE_KEY_SYSTEM_CONFLICT))
    system_text = _clean_text(console.get(CONSOLE_KEY_SYSTEM_TEXT))
    candidates: List[Dict[str, Any]] = []
    infrastructure = {
        KEY_INFRA_VISIBLE: [],
        KEY_INFRA_STALE: [],
        KEY_INFRA_MISSING: [],
        KEY_INFRA_CONFLICT: [],
    }
    for row in infrastructure_rows:
        label = _row_label(row)
        if not label:
            continue
        infrastructure[_infrastructure_bucket(row)].append(label)

    if not rows:
        candidates.append(
            _candidate(
                fault_class=FAULT_CLASS_INSUFFICIENT,
                confidence=CONFIDENCE_LOW,
                summary=TEXT_INSUFFICIENT,
                affected=[],
                region="none",
                supporting=[],
                conflicting=[],
                checks=[CHECK_TOPOLOGY],
            )
        )
    else:
        if system_conflict or len(degraded_only_labels) >= 2:
            support = [system_text] if system_text else []
            support.extend(degraded_only_labels or degraded_labels)
            candidates.append(
                _candidate(
                    fault_class=FAULT_CLASS_BUS_WIDE,
                    confidence=CONFIDENCE_MEDIUM if system_conflict else CONFIDENCE_LOW,
                    summary=TEXT_BUS_WIDE,
                    affected=degraded_labels,
                    region="whole CAN bus or shared controller path",
                    supporting=support,
                    conflicting=[],
                    checks=[CHECK_BUS_WIDE, RECHECK_OBSERVATION],
                )
            )

        if len(affected_labels) == 1:
            label = affected_labels[0]
            row = affected_rows[0]
            candidates.append(
                _candidate(
                    fault_class=FAULT_CLASS_SINGLE_DEVICE,
                    confidence=CONFIDENCE_HIGH if _clean_text(row.get(ROW_KEY_CONFIDENCE)).upper() == CONFIDENCE_HIGH else CONFIDENCE_MEDIUM,
                    summary=TEXT_SINGLE,
                    affected=[label],
                    region=label,
                    supporting=_row_support(row),
                    conflicting=[],
                    checks=[CHECK_SINGLE_FMT.format(label=label), RECHECK_OBSERVATION],
                )
            )
        elif len(affected_labels) > 1:
            region, has_topology = _topology_region_for_labels(affected_labels, topology_profile)
            candidates.append(
                _candidate(
                    fault_class=FAULT_CLASS_BRANCH if has_topology else FAULT_CLASS_TRUNK,
                    confidence=CONFIDENCE_MEDIUM if has_topology else CONFIDENCE_LOW,
                    summary=TEXT_BRANCH if has_topology else TEXT_TRUNK,
                    affected=affected_labels,
                    region=region,
                    supporting=affected_labels,
                    conflicting=[],
                    checks=[CHECK_BRANCH if has_topology else CHECK_TRUNK, RECHECK_OBSERVATION],
                )
            )

        stale_or_conflicted = [
            _row_label(row)
            for row in rows
            if bool(row.get(ROW_KEY_CONFLICTED)) or STATE_UNKNOWN == _clean_text(row.get(ROW_KEY_STATE)).lower()
        ]
        if stale_or_conflicted and not affected_labels:
            candidates.append(
                _candidate(
                    fault_class=FAULT_CLASS_STALE,
                    confidence=CONFIDENCE_LOW,
                    summary=TEXT_STALE,
                    affected=stale_or_conflicted,
                    region="evidence freshness",
                    supporting=stale_or_conflicted,
                    conflicting=[],
                    checks=[CHECK_STALE, RECHECK_OBSERVATION],
                )
            )

        if not candidates:
            return {
                KEY_STATUS: STATUS_NO_FAULT,
                KEY_RAN_AT_EPOCH_SEC: ran_at,
                KEY_SUMMARY: TEXT_NO_ACTIVE_FAULT,
                KEY_AFFECTED_DEVICES: [],
                KEY_CANDIDATES: [],
                KEY_OBSERVATION: {
                    KEY_EVIDENCE_ROWS: len(rows),
                    KEY_TOPOLOGY_AVAILABLE: isinstance(topology_profile, Mapping) and bool(topology_profile),
                    KEY_INFRASTRUCTURE: infrastructure,
                },
            }

    return {
        KEY_STATUS: STATUS_OK,
        KEY_RAN_AT_EPOCH_SEC: ran_at,
        KEY_SUMMARY: _clean_text(candidates[0].get(KEY_SUMMARY)) if candidates else TEXT_INSUFFICIENT,
        KEY_AFFECTED_DEVICES: affected_labels,
        KEY_CANDIDATES: candidates,
        KEY_OBSERVATION: {
            KEY_EVIDENCE_ROWS: len(rows),
            KEY_TOPOLOGY_AVAILABLE: isinstance(topology_profile, Mapping) and bool(topology_profile),
            KEY_INFRASTRUCTURE: infrastructure,
        },
    }


def render_fault_diagnosis(result: Mapping[str, Any]) -> str:
    """
    NAME
        render_fault_diagnosis - Render fault diagnosis as operator-facing text.
    """
    if not isinstance(result, Mapping):
        return TEXT_INSUFFICIENT
    lines = [
        f"status={_clean_text(result.get(KEY_STATUS)) or STATUS_INSUFFICIENT}",
        f"summary={_clean_text(result.get(KEY_SUMMARY)) or TEXT_INSUFFICIENT}",
    ]
    observation = result.get(KEY_OBSERVATION)
    if isinstance(observation, Mapping):
        infrastructure = observation.get(KEY_INFRASTRUCTURE)
        if isinstance(infrastructure, Mapping):
            lines.append("")
            lines.append("infrastructure:")
            for bucket_key in (
                KEY_INFRA_VISIBLE,
                KEY_INFRA_STALE,
                KEY_INFRA_MISSING,
                KEY_INFRA_CONFLICT,
            ):
                bucket_items = infrastructure.get(bucket_key)
                bucket_text = (
                    ", ".join(str(item) for item in bucket_items)
                    if isinstance(bucket_items, list) and bucket_items
                    else "none"
                )
                lines.append(f"  {bucket_key}={bucket_text}")
    candidates = result.get(KEY_CANDIDATES)
    if not isinstance(candidates, list) or not candidates:
        lines.append("candidates=none")
        return "\n".join(lines)
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, Mapping):
            continue
        lines.append("")
        lines.append(
            f"{index}. {candidate.get(KEY_FAULT_CLASS)} | confidence={candidate.get(KEY_CONFIDENCE)}"
        )
        lines.append(f"   region={candidate.get(KEY_SUSPECTED_REGION)}")
        affected = candidate.get(KEY_AFFECTED_DEVICES)
        lines.append(f"   affected={', '.join(affected) if isinstance(affected, list) and affected else 'none'}")
        support = candidate.get(KEY_SUPPORTING_EVIDENCE)
        if isinstance(support, list) and support:
            lines.append("   supporting=" + " ; ".join(str(item) for item in support[:4]))
        conflicts = candidate.get(KEY_CONFLICTING_EVIDENCE)
        if isinstance(conflicts, list) and conflicts:
            lines.append("   conflicting=" + " ; ".join(str(item) for item in conflicts[:4]))
        checks = candidate.get(KEY_RECOMMENDED_CHECKS)
        if isinstance(checks, list) and checks:
            lines.append("   next=" + " ; ".join(str(item) for item in checks[:3]))
    return "\n".join(lines)
