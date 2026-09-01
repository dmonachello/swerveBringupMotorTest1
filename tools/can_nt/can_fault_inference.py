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
KEY_CANDIDATE_CATEGORY = "candidateCategory"
KEY_CONFIDENCE = "confidence"
KEY_CONFLICTING_EVIDENCE = "conflictingEvidence"
KEY_DEGRADED_NOTES = "degradedNotes"
KEY_EVIDENCE_ROWS = "evidenceRows"
KEY_FAULT_CLASS = "faultClass"
KEY_LABEL = "label"
KEY_MISSING_DEVICES = "missingDevices"
KEY_NOTES = "notes"
KEY_OBSERVATION = "observation"
KEY_PRIMARY_SUSPECT_REGIONS = "primarySuspectRegions"
KEY_RAN_AT_EPOCH_SEC = "ranAtEpochSec"
KEY_RECOMMENDED_CHECKS = "recommendedChecks"
KEY_RANKING_REASONS = "rankingReasons"
KEY_SECONDARY_SUSPECT_REGIONS = "secondarySuspectRegions"
KEY_SOURCE_AGES = "sourceAges"
KEY_STATUS = "status"
KEY_SUMMARY = "summary"
KEY_SUPPORTING_EVIDENCE = "supportingEvidence"
KEY_SUSPECTED_REGION = "suspectedRegion"
KEY_TOPOLOGY_AVAILABLE = "topologyAvailable"
KEY_TOPOLOGY_NOTE = "topologyNote"
KEY_TRACE = "trace"
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
ROW_KEY_MANUAL_TEXT = "manualText"
ROW_KEY_SHADOW_RESULT = "shadowResult"
SHADOW_KEY_DIMENSIONS = "dimensions"
SHADOW_KEY_CONFLICT = "conflict"
SHADOW_KEY_VALUE = "value"
SHADOW_DIMENSION_COMMUNICATION = "communication"
SHADOW_DIMENSION_EXISTENCE = "existence"
SHADOW_DIMENSION_IDENTITY = "identity"
SHADOW_DIMENSION_OPERABILITY = "operability"
PASSIVE_TOKEN_PRESENCE_PREFIX = "presence="
PASSIVE_TOKEN_SCORE_PREFIX = "score="
PASSIVE_TOKEN_PACKET_PREFIX = "packets="
PASSIVE_TOKEN_LAST_SEEN_PREFIX = "lastseen="
PASSIVE_TOKEN_RATE_PREFIX = "rate="
PASSIVE_TOKEN_EXISTENCE_PACKETS_PREFIX = "existencepackets="
PASSIVE_PRESENCE_VALUES = {"high", "medium", "low", "uncertain"}
INFRASTRUCTURE_LABELS = {"roborio", "pdp", "pdh"}
BOUNDARY_ROBORIO_PREFIX = "between roborio and "

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

CATEGORY_BUS_PATH = "bus_path_fault"
CATEGORY_DEVICE_LOCAL = "device_local_fault"
CATEGORY_CONFIGURATION = "configuration_fault"

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"

VALUE_PRESENT = "PRESENT"
VALUE_ABSENT = "ABSENT"
VALUE_FAILED = "FAILED"
VALUE_DEGRADED = "DEGRADED"
VALUE_CONFLICT = "CONFLICT"
VALUE_UNKNOWN = "UNKNOWN"
VALUE_HEALTHY = "HEALTHY"
VALUE_WORKING = "WORKING"
VALUE_UNPROVEN = "UNPROVEN"

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
NOTE_TOPOLOGY_LIMITED = "topology incomplete; region localization limited"
NOTE_PASSIVE_UNAVAILABLE = "Passive CAN evidence unavailable; confidence reduced."
NOTE_CONSOLE_UNAVAILABLE = "Robot console/runtime evidence unavailable; confidence reduced."
NOTE_SOURCE_DISAGREEMENT = "Passive CAN and robot-side evidence disagree; preferring robot-side evidence."
TRACE_KEY_INPUT_SUMMARY = "inputSummary"
TRACE_KEY_NORMALIZED_ROWS = "normalizedRows"
TRACE_KEY_TOPOLOGY = "topology"
TRACE_KEY_CANDIDATE_TRACE = "candidateTrace"
TRACE_KEY_RANKING = "ranking"

CAN_EDGE_TYPES = {EDGE_TYPE_CAN_TRUNK, EDGE_TYPE_CAN_DROP, EDGE_TYPE_CAN_TAP}
SOURCE_NAME_RUNTIME = "runtime"
SOURCE_NAME_PROBE = "probe"
SOURCE_NAME_MANUAL = "manual"
SOURCE_NAME_PASSIVE = "passive"
SOURCE_NAME_CONSOLE = "console"
SOURCE_SCORE_STATE = "state"
SOURCE_SCORE_PRESENT = "present"
SOURCE_SCORE_UNKNOWN = "unknown"
SOURCE_SCORE_CONFLICT = "conflict"
SOURCE_SCORE_REASON = "reason"
SOURCE_SCORE_SCORE = "score"
MANUAL_SUCCESS_TOKEN_ROTATION = "rotation detected"
MANUAL_SUCCESS_TOKEN_CORRECT = "correct response"
MANUAL_SUCCESS_TOKEN_MOTION_PASS = "motioncheck=pass"
POSITIVE_SOURCE_SCORE_RUNTIME = 70.0
POSITIVE_SOURCE_SCORE_PROBE = 90.0
POSITIVE_SOURCE_SCORE_MANUAL = 60.0
POSITIVE_SOURCE_SCORE_PASSIVE = 70.0
POSITIVE_CURRENT_SOURCE_MIN_COUNT = 2
CONSOLE_SCORE_NEUTRAL = 50.0
PASSIVE_RATE_SUFFIX_HZ = "hz"
PASSIVE_AGE_SUFFIX_SECONDS = "s"
PASSIVE_AGE_SUFFIX_MINUTES = "m"
PASSIVE_AGE_SUFFIX_HOURS = "h"
PASSIVE_FRESH_LAST_SEEN_MAX_SECONDS = 1.0
PASSIVE_CURRENT_RATE_MIN_HZ = 0.1
PASSIVE_CURRENT_EXISTENCE_PACKET_MIN_COUNT = 1.0
TEXT_NONE = "--"


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _row_label(row: Mapping[str, Any]) -> str:
    return _clean_text(row.get(KEY_LABEL))


def _shadow_dimensions(row: Mapping[str, Any]) -> Mapping[str, Any]:
    shadow_result = row.get(ROW_KEY_SHADOW_RESULT)
    if not isinstance(shadow_result, Mapping):
        return {}
    dimensions = shadow_result.get(SHADOW_KEY_DIMENSIONS)
    return dimensions if isinstance(dimensions, Mapping) else {}


def _shadow_dimension_entry(row: Mapping[str, Any], dimension_name: str) -> Mapping[str, Any]:
    dimensions = _shadow_dimensions(row)
    entry = dimensions.get(dimension_name)
    return entry if isinstance(entry, Mapping) else {}


def _shadow_dimension_value(row: Mapping[str, Any], dimension_name: str) -> str:
    return _clean_text(_shadow_dimension_entry(row, dimension_name).get(SHADOW_KEY_VALUE)).upper()


def _shadow_dimension_conflict(row: Mapping[str, Any], dimension_name: str) -> bool:
    return bool(_shadow_dimension_entry(row, dimension_name).get(SHADOW_KEY_CONFLICT))


def _row_existence_value(row: Mapping[str, Any]) -> str:
    shadow_value = _shadow_dimension_value(row, SHADOW_DIMENSION_EXISTENCE)
    if shadow_value:
        return shadow_value
    return _clean_text(row.get(ROW_KEY_EXISTENCE)).upper()


def _row_communication_value(row: Mapping[str, Any]) -> str:
    shadow_value = _shadow_dimension_value(row, SHADOW_DIMENSION_COMMUNICATION)
    if shadow_value:
        return shadow_value
    return VALUE_UNKNOWN


def _row_operability_value(row: Mapping[str, Any]) -> str:
    shadow_value = _shadow_dimension_value(row, SHADOW_DIMENSION_OPERABILITY)
    if shadow_value:
        return shadow_value
    return _clean_text(row.get(ROW_KEY_OPERABILITY)).upper()


def _row_identity_value(row: Mapping[str, Any]) -> str:
    shadow_value = _shadow_dimension_value(row, SHADOW_DIMENSION_IDENTITY)
    if shadow_value:
        return shadow_value
    return VALUE_UNKNOWN


def _row_has_shadow_conflict(row: Mapping[str, Any]) -> bool:
    for dimension_name in (
        SHADOW_DIMENSION_EXISTENCE,
        SHADOW_DIMENSION_COMMUNICATION,
        SHADOW_DIMENSION_OPERABILITY,
        SHADOW_DIMENSION_IDENTITY,
    ):
        if _shadow_dimension_conflict(row, dimension_name):
            return True
    return False


def _is_infrastructure_label(label: object) -> bool:
    return _clean_text(label).lower() in INFRASTRUCTURE_LABELS


def _is_infrastructure_row(row: Mapping[str, Any]) -> bool:
    return _is_infrastructure_label(row.get(KEY_LABEL))


def _is_healthy_motion_row(row: Mapping[str, Any]) -> bool:
    if _is_infrastructure_row(row):
        return False
    existence = _row_existence_value(row)
    operability = _row_operability_value(row)
    state = _clean_text(row.get(ROW_KEY_STATE)).lower()
    confidence = _clean_text(row.get(ROW_KEY_CONFIDENCE)).upper()
    return (
        existence == VALUE_PRESENT
        and operability in {"OK", VALUE_UNKNOWN, VALUE_WORKING, VALUE_UNPROVEN}
        and state in {"ok", STATE_UNKNOWN}
        and confidence in {CONFIDENCE_HIGH, CONFIDENCE_MEDIUM}
    )


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
    if value_text.lower().endswith(PASSIVE_RATE_SUFFIX_HZ):
        value_text = value_text[: -len(PASSIVE_RATE_SUFFIX_HZ)].strip()
    if "/" in value_text:
        value_text = value_text.split("/", 1)[0].strip()
    try:
        return float(value_text)
    except ValueError:
        return None


def _token_age_seconds(token: str, prefix: str) -> Optional[float]:
    if not token.startswith(prefix):
        return None
    value_text = token[len(prefix) :].strip().lower()
    if not value_text or value_text == TEXT_NONE:
        return None
    multiplier = 1.0
    if value_text.endswith(PASSIVE_AGE_SUFFIX_HOURS):
        multiplier = 3600.0
        value_text = value_text[: -len(PASSIVE_AGE_SUFFIX_HOURS)].strip()
    elif value_text.endswith(PASSIVE_AGE_SUFFIX_MINUTES):
        multiplier = 60.0
        value_text = value_text[: -len(PASSIVE_AGE_SUFFIX_MINUTES)].strip()
    elif value_text.endswith(PASSIVE_AGE_SUFFIX_SECONDS):
        value_text = value_text[: -len(PASSIVE_AGE_SUFFIX_SECONDS)].strip()
    try:
        return float(value_text) * multiplier
    except ValueError:
        return None


def _passive_snapshot_is_current(row: Mapping[str, Any]) -> bool:
    passive_last_seen_seconds: Optional[float] = None
    passive_rate_hz: Optional[float] = None
    passive_existence_packets: Optional[float] = None
    passive_packets: Optional[float] = None
    passive_presence_token = False
    for token in _passive_token_values(row):
        if token.startswith(PASSIVE_TOKEN_PRESENCE_PREFIX):
            value = token[len(PASSIVE_TOKEN_PRESENCE_PREFIX) :].strip()
            if value in PASSIVE_PRESENCE_VALUES:
                passive_presence_token = True
            continue
        score = _token_float(token, PASSIVE_TOKEN_SCORE_PREFIX)
        if score is not None and score > 0.0:
            passive_presence_token = True
            continue
        packets = _token_float(token, PASSIVE_TOKEN_PACKET_PREFIX)
        if packets is not None:
            passive_packets = packets
            continue
        passive_last_seen = _token_age_seconds(token, PASSIVE_TOKEN_LAST_SEEN_PREFIX)
        if passive_last_seen is not None:
            passive_last_seen_seconds = passive_last_seen
            continue
        passive_rate = _token_float(token, PASSIVE_TOKEN_RATE_PREFIX)
        if passive_rate is not None:
            passive_rate_hz = passive_rate
            continue
        existence_packets = _token_float(token, PASSIVE_TOKEN_EXISTENCE_PACKETS_PREFIX)
        if existence_packets is not None:
            passive_existence_packets = existence_packets
            continue
    if passive_last_seen_seconds is not None and passive_last_seen_seconds <= PASSIVE_FRESH_LAST_SEEN_MAX_SECONDS:
        return True
    if passive_rate_hz is not None and passive_rate_hz >= PASSIVE_CURRENT_RATE_MIN_HZ:
        return True
    if (
        passive_existence_packets is not None
        and passive_existence_packets >= PASSIVE_CURRENT_EXISTENCE_PACKET_MIN_COUNT
    ):
        return True
    if (
        passive_presence_token
        and passive_packets is not None
        and passive_packets > 0.0
        and passive_last_seen_seconds is None
        and passive_rate_hz is None
        and passive_existence_packets is None
    ):
        return True
    return False


def _passive_snapshot_has_observer_history(row: Mapping[str, Any]) -> bool:
    passive_packets: Optional[float] = None
    passive_last_seen_seconds: Optional[float] = None
    passive_presence_token = False
    for token in _passive_token_values(row):
        if token.startswith(PASSIVE_TOKEN_PRESENCE_PREFIX):
            value = token[len(PASSIVE_TOKEN_PRESENCE_PREFIX) :].strip()
            if value in PASSIVE_PRESENCE_VALUES:
                passive_presence_token = True
            continue
        score = _token_float(token, PASSIVE_TOKEN_SCORE_PREFIX)
        if score is not None and score > 0.0:
            passive_presence_token = True
            continue
        packets = _token_float(token, PASSIVE_TOKEN_PACKET_PREFIX)
        if packets is not None:
            passive_packets = packets
            continue
        passive_last_seen = _token_age_seconds(token, PASSIVE_TOKEN_LAST_SEEN_PREFIX)
        if passive_last_seen is not None:
            passive_last_seen_seconds = passive_last_seen
    return bool(
        passive_presence_token
        or (passive_packets is not None and passive_packets > 0.0)
        or passive_last_seen_seconds is not None
    )


def _passive_visibility_decay_with_console_failure(row: Mapping[str, Any]) -> bool:
    if not _console_is_current_negative(row):
        return False
    if _passive_snapshot_is_current(row):
        return False
    if not _passive_snapshot_has_observer_history(row):
        return False
    return True


def _observer_indicates_presence(row: Mapping[str, Any]) -> bool:
    presence_state = _clean_text(row.get(ROW_KEY_PRESENCE_STATE)).lower()
    presence_score = row.get(ROW_KEY_PRESENCE_SCORE)
    passive_snapshot_current = _passive_snapshot_is_current(row)
    if presence_state == PRESENCE_STATE_PRESENT:
        return passive_snapshot_current or not _passive_token_values(row)
    if isinstance(presence_score, (int, float)) and float(presence_score) >= 50.0:
        return passive_snapshot_current or not _passive_token_values(row)
    source_scores = row.get(ROW_KEY_SOURCE_SCORES)
    if isinstance(source_scores, Mapping):
        for source_name in ("passive", "runtime", "probe", "enrichment"):
            source_entry = source_scores.get(source_name)
            if not isinstance(source_entry, Mapping):
                continue
            source_state = _clean_text(source_entry.get("state")).lower()
            source_score = source_entry.get("score")
            if source_name == SOURCE_NAME_PASSIVE and not passive_snapshot_current:
                continue
            if source_state == PRESENCE_STATE_PRESENT:
                return True
            if isinstance(source_score, (int, float)) and float(source_score) >= 70.0:
                return True
    return passive_snapshot_current


def _source_score_entry(row: Mapping[str, Any], source_name: str) -> Optional[Mapping[str, Any]]:
    source_scores = row.get(ROW_KEY_SOURCE_SCORES)
    if not isinstance(source_scores, Mapping):
        return None
    source_entry = source_scores.get(source_name)
    return source_entry if isinstance(source_entry, Mapping) else None


def _source_score_present(
    row: Mapping[str, Any],
    source_name: str,
    minimum_score: float,
) -> bool:
    source_entry = _source_score_entry(row, source_name)
    if not isinstance(source_entry, Mapping):
        return False
    source_state = _clean_text(source_entry.get(SOURCE_SCORE_STATE)).lower()
    source_score = source_entry.get(SOURCE_SCORE_SCORE)
    return (
        source_state == PRESENCE_STATE_PRESENT
        or (
            isinstance(source_score, (int, float))
            and float(source_score) >= minimum_score
        )
    )


def _manual_indicates_success(row: Mapping[str, Any]) -> bool:
    manual_summary = _clean_text(row.get(ROW_KEY_MANUAL)).lower()
    manual_text = _clean_text(row.get(ROW_KEY_MANUAL_TEXT)).lower()
    return any(
        token in manual_summary or token in manual_text
        for token in (
            MANUAL_SUCCESS_TOKEN_ROTATION,
            MANUAL_SUCCESS_TOKEN_CORRECT,
            MANUAL_SUCCESS_TOKEN_MOTION_PASS,
        )
    )


def _console_is_current_negative(row: Mapping[str, Any]) -> bool:
    source_entry = _source_score_entry(row, SOURCE_NAME_CONSOLE)
    if not isinstance(source_entry, Mapping):
        return False
    source_state = _clean_text(source_entry.get(SOURCE_SCORE_STATE)).lower()
    source_score = source_entry.get(SOURCE_SCORE_SCORE)
    if source_state == PRESENCE_STATE_CONFLICT:
        return True
    return isinstance(source_score, (int, float)) and float(source_score) < CONSOLE_SCORE_NEUTRAL


def _has_strong_current_positive_counterevidence(row: Mapping[str, Any]) -> bool:
    if _console_is_current_negative(row):
        return False
    positive_sources = 0
    if _source_score_present(row, SOURCE_NAME_RUNTIME, POSITIVE_SOURCE_SCORE_RUNTIME):
        positive_sources += 1
    if _source_score_present(row, SOURCE_NAME_PROBE, POSITIVE_SOURCE_SCORE_PROBE):
        positive_sources += 1
    if (
        _source_score_present(row, SOURCE_NAME_MANUAL, POSITIVE_SOURCE_SCORE_MANUAL)
        and _manual_indicates_success(row)
    ):
        positive_sources += 1
    if _source_score_present(row, SOURCE_NAME_PASSIVE, POSITIVE_SOURCE_SCORE_PASSIVE):
        positive_sources += 1
    return positive_sources >= POSITIVE_CURRENT_SOURCE_MIN_COUNT


def _infrastructure_bucket(row: Mapping[str, Any]) -> str:
    existence = _row_existence_value(row)
    state = _clean_text(row.get(ROW_KEY_STATE)).lower()
    presence_state = _clean_text(row.get(ROW_KEY_PRESENCE_STATE)).lower()
    conflicted = bool(row.get(ROW_KEY_CONFLICTED)) or _row_has_shadow_conflict(row)
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
    existence = _row_existence_value(row)
    communication = _row_communication_value(row)
    operability = _row_operability_value(row)
    presence_state = _clean_text(row.get(ROW_KEY_PRESENCE_STATE)).lower()
    strong_positive_counterevidence = _has_strong_current_positive_counterevidence(row)
    passive_visibility_decay = _passive_visibility_decay_with_console_failure(row)
    if operability in {VALUE_FAILED, VALUE_CONFLICT}:
        return True
    if communication == VALUE_FAILED:
        return True
    if state == STATE_FAILED:
        return True
    if presence_state == PRESENCE_STATE_CONFLICT:
        if strong_positive_counterevidence:
            return False
        return True
    if passive_visibility_decay:
        if strong_positive_counterevidence:
            return False
        return True
    if _observer_indicates_presence(row) and (state == STATE_MISSING or existence == VALUE_ABSENT):
        return False
    if presence_state == PRESENCE_STATE_MISSING:
        if strong_positive_counterevidence:
            return False
        return True
    if state == STATE_MISSING:
        if strong_positive_counterevidence:
            return False
        return True
    if strong_positive_counterevidence and existence in {VALUE_ABSENT, VALUE_CONFLICT}:
        return False
    return existence in {VALUE_ABSENT, VALUE_CONFLICT}


def _is_degraded_row(row: Mapping[str, Any]) -> bool:
    if _is_affected_row(row):
        return True
    state = _clean_text(row.get(ROW_KEY_STATE)).lower()
    operability = _row_operability_value(row)
    communication = _row_communication_value(row)
    return (
        state == STATE_DEGRADED
        or operability == VALUE_DEGRADED
        or communication == VALUE_DEGRADED
    )


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
    category: str,
    confidence: str,
    summary: str,
    affected: Iterable[str],
    missing: Iterable[str],
    region: str,
    primary_regions: Iterable[str],
    secondary_regions: Iterable[str],
    supporting: Iterable[str],
    conflicting: Iterable[str],
    checks: Iterable[str],
    ranking_reasons: Iterable[str],
) -> Dict[str, Any]:
    return {
        KEY_FAULT_CLASS: fault_class,
        KEY_CANDIDATE_CATEGORY: category,
        KEY_CONFIDENCE: confidence,
        KEY_SUMMARY: summary,
        KEY_AFFECTED_DEVICES: list(affected),
        KEY_MISSING_DEVICES: list(missing),
        KEY_SUSPECTED_REGION: region,
        KEY_PRIMARY_SUSPECT_REGIONS: list(primary_regions),
        KEY_SECONDARY_SUSPECT_REGIONS: list(secondary_regions),
        KEY_SUPPORTING_EVIDENCE: list(supporting),
        KEY_CONFLICTING_EVIDENCE: list(conflicting),
        KEY_RECOMMENDED_CHECKS: list(checks),
        KEY_RANKING_REASONS: list(ranking_reasons),
        KEY_SOURCE_AGES: {},
    }


def _topology_graph(
    topology_profile: Optional[Mapping[str, Any]]
) -> Tuple[Dict[str, int], Dict[int, str], Dict[int, Set[int]]]:
    label_to_node: Dict[str, int] = {}
    node_to_label: Dict[int, str] = {}
    graph: Dict[int, Set[int]] = {}
    if not isinstance(topology_profile, Mapping):
        return label_to_node, node_to_label, graph
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
                    node_to_label[node_key] = _clean_text(node.get(KEY_DEVICE_REF))
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
    return label_to_node, node_to_label, graph


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
    label_to_node, _node_to_label, graph = _topology_graph(topology_profile)
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


def _topology_component_regions(
    affected_labels: Iterable[str],
    all_labels: Iterable[str],
    topology_profile: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    label_to_node, node_to_label, graph = _topology_graph(topology_profile)
    affected_label_list = [label for label in affected_labels if _clean_text(label)]
    all_label_set = {_clean_text(label) for label in all_labels if _clean_text(label)}
    affected_nodes = {
        label_to_node[label.lower()]
        for label in affected_label_list
        if label.lower() in label_to_node
    }
    if not affected_nodes:
        return {
            "available": False,
            "region": "topology region unknown",
            "primaryRegions": [],
            "secondaryRegions": [],
            "boundaryPairs": [],
            "note": NOTE_TOPOLOGY_LIMITED,
        }

    components = _connected_components(affected_nodes, graph)
    primary_regions: List[str] = []
    secondary_regions: List[str] = []
    boundary_pairs: List[str] = []
    for component in components:
        component_labels = [
            node_to_label[node_key]
            for node_key in component
            if node_key in node_to_label
        ]
        component_boundaries: List[str] = []
        for node_key in component:
            for neighbor in graph.get(node_key, set()):
                if neighbor in component:
                    continue
                neighbor_label = node_to_label.get(neighbor, "")
                current_label = node_to_label.get(node_key, "")
                if not neighbor_label or not current_label:
                    continue
                if neighbor_label not in all_label_set:
                    continue
                pair_text = f"between {neighbor_label} and {current_label}"
                if pair_text not in component_boundaries:
                    component_boundaries.append(pair_text)
                if pair_text not in boundary_pairs:
                    boundary_pairs.append(pair_text)
        if component_boundaries:
            primary_regions.append(component_boundaries[0])
            for extra_boundary in component_boundaries[1:]:
                secondary_regions.append(extra_boundary)
        elif component_labels:
            primary_regions.append(", ".join(component_labels))

    region_text = primary_regions[0] if primary_regions else "connected CAN topology region"
    return {
        "available": True,
        "region": region_text,
        "primaryRegions": primary_regions[:3],
        "secondaryRegions": secondary_regions[:3],
        "boundaryPairs": boundary_pairs[:6],
        "note": "",
    }


def _controller_side_boundary_pairs(boundary_pairs: Iterable[object]) -> List[str]:
    """
    NAME
        _controller_side_boundary_pairs - Select topology boundaries that start at the roboRIO side.
    """
    return [
        boundary_text
        for boundary_text in (_clean_text(boundary) for boundary in boundary_pairs)
        if boundary_text.lower().startswith(BOUNDARY_ROBORIO_PREFIX)
    ]


def _normalized_trace_rows(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                KEY_LABEL: _row_label(row),
                ROW_KEY_STATE: _clean_text(row.get(ROW_KEY_STATE)).lower(),
                ROW_KEY_EXISTENCE: _clean_text(row.get(ROW_KEY_EXISTENCE)).upper(),
                ROW_KEY_OPERABILITY: _clean_text(row.get(ROW_KEY_OPERABILITY)).upper(),
                ROW_KEY_CONFIDENCE: _clean_text(row.get(ROW_KEY_CONFIDENCE)).upper(),
                ROW_KEY_PRESENCE_STATE: _clean_text(row.get(ROW_KEY_PRESENCE_STATE)).lower(),
                ROW_KEY_CONFLICTED: bool(row.get(ROW_KEY_CONFLICTED)),
                "support": _row_support(row),
            }
        )
    return normalized


def _console_runtime_available(console: Mapping[str, Any], rows: Iterable[Mapping[str, Any]]) -> bool:
    if bool(console):
        return True
    for row in rows:
        if _clean_text(row.get(ROW_KEY_CONSOLE)) not in ("", TEXT_NONE):
            return True
        if isinstance(_source_score_entry(row, SOURCE_NAME_RUNTIME), Mapping):
            return True
        if isinstance(_source_score_entry(row, SOURCE_NAME_CONSOLE), Mapping):
            return True
    return False


def _passive_available(rows: Iterable[Mapping[str, Any]]) -> bool:
    for row in rows:
        if _clean_text(row.get(ROW_KEY_PASSIVE)) not in ("", TEXT_NONE):
            return True
        if isinstance(_source_score_entry(row, SOURCE_NAME_PASSIVE), Mapping):
            return True
    return False


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
    healthy_motion_labels = [_row_label(row) for row in rows if _is_healthy_motion_row(row)]
    console = console_snapshot if isinstance(console_snapshot, Mapping) else {}
    system_conflict = bool(console.get(CONSOLE_KEY_SYSTEM_CONFLICT))
    system_text = _clean_text(console.get(CONSOLE_KEY_SYSTEM_TEXT))
    candidates: List[Dict[str, Any]] = []
    degraded_notes: List[str] = []
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
    passive_available = _passive_available(rows)
    console_runtime_available = _console_runtime_available(console, rows)
    topology_available = isinstance(topology_profile, Mapping) and bool(topology_profile)
    topology_note = ""
    if not passive_available:
        degraded_notes.append(NOTE_PASSIVE_UNAVAILABLE)
    if not console_runtime_available:
        degraded_notes.append(NOTE_CONSOLE_UNAVAILABLE)
    if topology_available and affected_labels:
        topology_context = _topology_component_regions(affected_labels, [_row_label(row) for row in rows], topology_profile)
    else:
        topology_context = {
            "available": False,
            "region": "topology region unknown",
            "primaryRegions": [],
            "secondaryRegions": [],
            "boundaryPairs": [],
            "note": NOTE_TOPOLOGY_LIMITED if affected_labels and not topology_available else "",
        }
    topology_note = _clean_text(topology_context.get("note"))
    if topology_note:
        degraded_notes.append(topology_note)

    conflict_rows = [
        _row_label(row)
        for row in rows
        if _clean_text(row.get(ROW_KEY_PRESENCE_STATE)).lower() == PRESENCE_STATE_CONFLICT
    ]
    if conflict_rows:
        degraded_notes.append(NOTE_SOURCE_DISAGREEMENT)

    trace: Dict[str, Any] = {
        TRACE_KEY_INPUT_SUMMARY: {
            "passiveAvailable": passive_available,
            "consoleRuntimeAvailable": console_runtime_available,
            "topologyAvailable": topology_available,
            "systemConflict": system_conflict,
            "systemText": system_text,
        },
        TRACE_KEY_NORMALIZED_ROWS: _normalized_trace_rows(rows),
        TRACE_KEY_TOPOLOGY: {
            "available": topology_available,
            "note": topology_note,
            "boundaryPairs": list(topology_context.get("boundaryPairs", [])),
        },
        TRACE_KEY_CANDIDATE_TRACE: [],
        TRACE_KEY_RANKING: [],
    }

    if not rows:
        candidates.append(
            _candidate(
                fault_class=FAULT_CLASS_INSUFFICIENT,
                category=CATEGORY_CONFIGURATION,
                confidence=CONFIDENCE_LOW,
                summary=TEXT_INSUFFICIENT,
                affected=[],
                missing=[],
                region="none",
                primary_regions=[],
                secondary_regions=[],
                supporting=[],
                conflicting=[],
                checks=[CHECK_TOPOLOGY],
                ranking_reasons=["No evidence rows were available for diagnosis."],
            )
        )
    else:
        if system_conflict or (len(degraded_only_labels) >= 2 and bool(affected_labels)):
            support = [system_text] if system_text else []
            support.extend(degraded_only_labels or degraded_labels)
            bus_wide_affected = list(affected_labels)
            bus_wide_missing = list(affected_labels)
            if not bus_wide_affected and system_conflict:
                bus_wide_affected = []
                bus_wide_missing = []
            candidates.append(
                _candidate(
                    fault_class=FAULT_CLASS_BUS_WIDE,
                    category=CATEGORY_BUS_PATH,
                    confidence=CONFIDENCE_MEDIUM if system_conflict else CONFIDENCE_LOW,
                    summary=TEXT_BUS_WIDE,
                    affected=bus_wide_affected,
                    missing=bus_wide_missing,
                    region="whole CAN bus or shared controller path",
                    primary_regions=["whole CAN bus or shared controller path"],
                    secondary_regions=[],
                    supporting=support,
                    conflicting=[],
                    checks=[CHECK_BUS_WIDE, RECHECK_OBSERVATION],
                    ranking_reasons=[
                        "Multiple devices or system-level evidence point to a broad CAN communication problem.",
                        "System conflict evidence raises bus-path candidates above isolated device failures.",
                    ],
                )
            )
            trace[TRACE_KEY_CANDIDATE_TRACE].append(
                {
                    KEY_FAULT_CLASS: FAULT_CLASS_BUS_WIDE,
                    "rule": "system_conflict_or_multi_degraded",
                    "supporting": list(support),
                }
            )

        if len(affected_labels) == 1:
            label = affected_labels[0]
            row = affected_rows[0]
            candidates.append(
                _candidate(
                    fault_class=FAULT_CLASS_SINGLE_DEVICE,
                    category=CATEGORY_DEVICE_LOCAL,
                    confidence=CONFIDENCE_HIGH if _clean_text(row.get(ROW_KEY_CONFIDENCE)).upper() == CONFIDENCE_HIGH else CONFIDENCE_MEDIUM,
                    summary=TEXT_SINGLE,
                    affected=[label],
                    missing=[label],
                    region=label,
                    primary_regions=[label],
                    secondary_regions=[],
                    supporting=_row_support(row),
                    conflicting=[],
                    checks=[CHECK_SINGLE_FMT.format(label=label), RECHECK_OBSERVATION],
                    ranking_reasons=[
                        "Exactly one affected device was found in the observation window.",
                        "No broader connected missing-device region outranked this device-local explanation.",
                    ],
                )
            )
            trace[TRACE_KEY_CANDIDATE_TRACE].append(
                {
                    KEY_FAULT_CLASS: FAULT_CLASS_SINGLE_DEVICE,
                    "rule": "single_affected_device",
                    "supporting": _row_support(row),
                }
            )
        elif len(affected_labels) > 1:
            region, has_topology = _topology_region_for_labels(affected_labels, topology_profile)
            missing_labels = list(affected_labels)
            primary_regions = list(topology_context.get("primaryRegions", []))
            secondary_regions = list(topology_context.get("secondaryRegions", []))
            boundary_pairs = list(topology_context.get("boundaryPairs", []))
            controller_boundary_pairs = _controller_side_boundary_pairs(boundary_pairs)
            checks = [CHECK_BRANCH if has_topology else CHECK_TRUNK, RECHECK_OBSERVATION]
            ranking_reasons = [
                "Multiple affected devices were found in the same diagnosis window.",
                "A grouped missing-device set is more consistent with a bus-path fault than unrelated device-local failures.",
            ]
            if primary_regions:
                ranking_reasons.append(
                    "Topology boundaries were used to localize the first suspect region."
                )
            if controller_boundary_pairs:
                candidates.append(
                    _candidate(
                        fault_class=FAULT_CLASS_CONTROLLER_SIDE,
                        category=CATEGORY_BUS_PATH,
                        confidence=CONFIDENCE_HIGH,
                        summary=TEXT_CONTROLLER,
                        affected=affected_labels,
                        missing=missing_labels,
                        region=controller_boundary_pairs[0],
                        primary_regions=controller_boundary_pairs[:1],
                        secondary_regions=controller_boundary_pairs[1:3],
                        supporting=affected_labels + controller_boundary_pairs,
                        conflicting=[],
                        checks=[CHECK_CONTROLLER, RECHECK_OBSERVATION],
                        ranking_reasons=[
                            "Affected devices localize to a boundary immediately downstream of the roboRIO side of the CAN bus.",
                            "Robot-local infrastructure can remain alive while the controller-side CAN link to downstream devices is broken.",
                        ],
                    )
                )
                trace[TRACE_KEY_CANDIDATE_TRACE].append(
                    {
                        KEY_FAULT_CLASS: FAULT_CLASS_CONTROLLER_SIDE,
                        "rule": "controller_side_boundary_from_topology",
                        "supporting": affected_labels,
                        "boundaryPairs": controller_boundary_pairs,
                    }
                )
            candidates.append(
                _candidate(
                    fault_class=FAULT_CLASS_BRANCH if has_topology else FAULT_CLASS_TRUNK,
                    category=CATEGORY_BUS_PATH,
                    confidence=CONFIDENCE_MEDIUM if has_topology else CONFIDENCE_LOW,
                    summary=TEXT_BRANCH if has_topology else TEXT_TRUNK,
                    affected=affected_labels,
                    missing=missing_labels,
                    region=region,
                    primary_regions=primary_regions or [region],
                    secondary_regions=secondary_regions,
                    supporting=affected_labels + boundary_pairs,
                    conflicting=[],
                    checks=checks,
                    ranking_reasons=ranking_reasons,
                )
            )
            trace[TRACE_KEY_CANDIDATE_TRACE].append(
                {
                    KEY_FAULT_CLASS: FAULT_CLASS_BRANCH if has_topology else FAULT_CLASS_TRUNK,
                    "rule": "multi_affected_group",
                    "supporting": affected_labels,
                    "missingDevices": missing_labels,
                    "boundaryPairs": boundary_pairs,
                }
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
                    category=CATEGORY_BUS_PATH,
                    confidence=CONFIDENCE_LOW,
                    summary=TEXT_STALE,
                    affected=stale_or_conflicted,
                    missing=[],
                    region="evidence freshness",
                    primary_regions=["evidence freshness"],
                    secondary_regions=[],
                    supporting=stale_or_conflicted,
                    conflicting=[],
                    checks=[CHECK_STALE, RECHECK_OBSERVATION],
                    ranking_reasons=[
                        "Evidence rows are stale or conflicted, so localization confidence is limited."
                    ],
                )
            )
            trace[TRACE_KEY_CANDIDATE_TRACE].append(
                {
                    KEY_FAULT_CLASS: FAULT_CLASS_STALE,
                    "rule": "stale_or_conflicted_without_localized_fault",
                    "supporting": stale_or_conflicted,
                }
            )

        if not candidates:
            return {
                KEY_STATUS: STATUS_NO_FAULT,
                KEY_RAN_AT_EPOCH_SEC: ran_at,
                KEY_SUMMARY: TEXT_NO_ACTIVE_FAULT,
                KEY_AFFECTED_DEVICES: [],
                KEY_MISSING_DEVICES: [],
                KEY_CANDIDATES: [],
                KEY_PRIMARY_SUSPECT_REGIONS: [],
                KEY_SECONDARY_SUSPECT_REGIONS: [],
                KEY_DEGRADED_NOTES: degraded_notes,
                KEY_TOPOLOGY_NOTE: topology_note,
                KEY_TRACE: trace,
                KEY_OBSERVATION: {
                    KEY_EVIDENCE_ROWS: len(rows),
                    KEY_TOPOLOGY_AVAILABLE: topology_available,
                    KEY_INFRASTRUCTURE: infrastructure,
                    "healthyMotionDevices": healthy_motion_labels,
                },
            }

    trace[TRACE_KEY_RANKING] = [
        {
            KEY_FAULT_CLASS: _clean_text(candidate.get(KEY_FAULT_CLASS)),
            KEY_CANDIDATE_CATEGORY: _clean_text(candidate.get(KEY_CANDIDATE_CATEGORY)),
            KEY_RANKING_REASONS: list(candidate.get(KEY_RANKING_REASONS, [])),
        }
        for candidate in candidates
        if isinstance(candidate, Mapping)
    ]

    return {
        KEY_STATUS: STATUS_OK,
        KEY_RAN_AT_EPOCH_SEC: ran_at,
        KEY_SUMMARY: _clean_text(candidates[0].get(KEY_SUMMARY)) if candidates else TEXT_INSUFFICIENT,
        KEY_AFFECTED_DEVICES: affected_labels,
        KEY_MISSING_DEVICES: list(affected_labels),
        KEY_CANDIDATES: candidates,
        KEY_PRIMARY_SUSPECT_REGIONS: list(candidates[0].get(KEY_PRIMARY_SUSPECT_REGIONS, [])) if candidates else [],
        KEY_SECONDARY_SUSPECT_REGIONS: list(candidates[0].get(KEY_SECONDARY_SUSPECT_REGIONS, [])) if candidates else [],
        KEY_DEGRADED_NOTES: degraded_notes,
        KEY_TOPOLOGY_NOTE: topology_note,
        KEY_TRACE: trace,
        KEY_OBSERVATION: {
            KEY_EVIDENCE_ROWS: len(rows),
            KEY_TOPOLOGY_AVAILABLE: topology_available,
            KEY_INFRASTRUCTURE: infrastructure,
            "healthyMotionDevices": healthy_motion_labels,
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
    degraded_notes = result.get(KEY_DEGRADED_NOTES)
    if isinstance(degraded_notes, list) and degraded_notes:
        lines.append("")
        lines.append("notes:")
        for note in degraded_notes[:6]:
            if _clean_text(note):
                lines.append(f"  - {_clean_text(note)}")
    primary_regions = result.get(KEY_PRIMARY_SUSPECT_REGIONS)
    if isinstance(primary_regions, list) and primary_regions:
        lines.append("")
        lines.append("primaryRegions:")
        for region in primary_regions[:3]:
            if _clean_text(region):
                lines.append(f"  - {_clean_text(region)}")
    secondary_regions = result.get(KEY_SECONDARY_SUSPECT_REGIONS)
    if isinstance(secondary_regions, list) and secondary_regions:
        lines.append("")
        lines.append("secondaryRegions:")
        for region in secondary_regions[:3]:
            if _clean_text(region):
                lines.append(f"  - {_clean_text(region)}")
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
            f"{index}. {candidate.get(KEY_FAULT_CLASS)} | category={candidate.get(KEY_CANDIDATE_CATEGORY)} | confidence={candidate.get(KEY_CONFIDENCE)}"
        )
        lines.append(f"   region={candidate.get(KEY_SUSPECTED_REGION)}")
        affected = candidate.get(KEY_AFFECTED_DEVICES)
        lines.append(f"   affected={', '.join(affected) if isinstance(affected, list) and affected else 'none'}")
        missing = candidate.get(KEY_MISSING_DEVICES)
        lines.append(
            "   missing="
            + (", ".join(str(item) for item in missing) if isinstance(missing, list) and missing else "none")
        )
        support = candidate.get(KEY_SUPPORTING_EVIDENCE)
        if isinstance(support, list) and support:
            lines.append("   supporting=" + " ; ".join(str(item) for item in support[:4]))
        conflicts = candidate.get(KEY_CONFLICTING_EVIDENCE)
        if isinstance(conflicts, list) and conflicts:
            lines.append("   conflicting=" + " ; ".join(str(item) for item in conflicts[:4]))
        primary = candidate.get(KEY_PRIMARY_SUSPECT_REGIONS)
        if isinstance(primary, list) and primary:
            lines.append("   primary=" + " ; ".join(str(item) for item in primary[:3]))
        secondary = candidate.get(KEY_SECONDARY_SUSPECT_REGIONS)
        if isinstance(secondary, list) and secondary:
            lines.append("   secondary=" + " ; ".join(str(item) for item in secondary[:3]))
        ranking_reasons = candidate.get(KEY_RANKING_REASONS)
        if isinstance(ranking_reasons, list) and ranking_reasons:
            lines.append("   ranking=" + " ; ".join(str(item) for item in ranking_reasons[:3]))
        checks = candidate.get(KEY_RECOMMENDED_CHECKS)
        if isinstance(checks, list) and checks:
            lines.append("   next=" + " ; ".join(str(item) for item in checks[:3]))
    trace = result.get(KEY_TRACE)
    if isinstance(trace, Mapping):
        input_summary = trace.get(TRACE_KEY_INPUT_SUMMARY)
        if isinstance(input_summary, Mapping):
            lines.append("")
            lines.append("why:")
            passive_available = input_summary.get("passiveAvailable")
            console_runtime_available = input_summary.get("consoleRuntimeAvailable")
            topology_available = input_summary.get("topologyAvailable")
            lines.append(
                "  inputs="
                + f"passive:{passive_available} "
                + f"consoleRuntime:{console_runtime_available} "
                + f"topology:{topology_available}"
            )
            system_text = _clean_text(input_summary.get("systemText"))
            if system_text:
                lines.append(f"  system={system_text}")
    return "\n".join(lines)
