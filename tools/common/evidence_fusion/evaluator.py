from __future__ import annotations

"""
NAME
    evaluator.py - Slice-3 shadow-mode per-dimension fusion evaluator.

DESCRIPTION
    Builds structured shadow results for configured devices from accepted
    observation blocks and their freshness-classified state. This module does
    not own ingest, queueing, or UI presentation. It only converts the shared
    ledger into deterministic per-dimension conclusions.
"""

from collections import defaultdict
from typing import Any, Dict, Iterable, Tuple

from tools.common.evidence_fusion.constants import (
    COMMUNICATION_DEGRADED,
    COMMUNICATION_FAILED,
    COMMUNICATION_HEALTHY,
    COMMUNICATION_UNKNOWN,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CONFLICT_MARGIN_THRESHOLD,
    CONFLICT_SUPPORT_THRESHOLD,
    DIMENSION_ALLOWED_VALUES,
    DIMENSION_COMMUNICATION,
    DIMENSION_EXISTENCE,
    DIMENSION_IDENTITY,
    DIMENSION_OPERABILITY,
    DIMENSIONS,
    EXISTENCE_PRESENT,
    EXISTENCE_UNKNOWN,
    HIGH_CONFIDENCE_THRESHOLD,
    IDENTITY_MATCHING,
    IDENTITY_MISMATCHED,
    IDENTITY_UNKNOWN,
    MEDIUM_CONFIDENCE_THRESHOLD,
    NEAR_ZERO_THRESHOLD,
    ONE_FLOAT,
    OPERABILITY_FAILED,
    OPERABILITY_UNPROVEN,
    OPERABILITY_UNKNOWN,
    OPERABILITY_WORKING,
    OVERALL_CAUTION,
    OVERALL_FAILED,
    OVERALL_HEALTHY,
    OVERALL_IDENTITY_FAULT,
    OVERALL_PROBABLE_FAULT,
    OVERALL_UNKNOWN,
    PAYLOAD_KEY_ASSERTION,
    PAYLOAD_KEY_BASE_RELIABILITY,
    PAYLOAD_KEY_CLAIM_STRENGTH,
    PAYLOAD_KEY_DIMENSION,
    PAYLOAD_KEY_DIRECTNESS,
    PAYLOAD_KEY_INDEPENDENCE_GROUP,
    PAYLOAD_KEY_POLARITY,
    PAYLOAD_KEY_QUALITY,
    PAYLOAD_KEY_REASON_CODE,
    PAYLOAD_KEY_SOURCE_HEALTH,
    PAYLOAD_KEY_SPECIFICITY,
    PAYLOAD_POLARITY_SUPPORT,
    ZERO_FLOAT,
)
from tools.common.evidence_fusion.types import EvidenceBlock, ObservationFreshnessState

RESULT_KEY_DIMENSIONS = "dimensions"
RESULT_KEY_OVERALL_STATE = "overallState"
RESULT_KEY_EVIDENCE_COUNT = "evidenceCount"
RESULT_KEY_CURRENT_OBSERVATION_COUNT = "currentObservationCount"
RESULT_KEY_REASON_CODES = "reasonCodes"
RESULT_KEY_TRACE = "trace"

DIMENSION_KEY_VALUE = "value"
DIMENSION_KEY_CONFIDENCE = "confidence"
DIMENSION_KEY_CONFIDENCE_BAND = "confidenceBand"
DIMENSION_KEY_CONFLICT = "conflict"
DIMENSION_KEY_WINNING_SUPPORT = "winningSupport"
DIMENSION_KEY_OPPOSING_SUPPORT = "opposingSupport"
DIMENSION_KEY_MARGIN = "margin"
DIMENSION_KEY_INDEPENDENT_GROUPS = "independentGroups"
DIMENSION_KEY_REASON_CODES = "reasonCodes"

TRACE_KEY_BLOCK_ID = "blockId"
TRACE_KEY_DIMENSION = "dimension"
TRACE_KEY_ASSERTION = "assertion"
TRACE_KEY_INFLUENCE = "influence"
TRACE_KEY_GROUP = "group"
TRACE_KEY_REASON_CODE = "reasonCode"


def build_shadow_device_results(
    accepted_blocks: Dict[str, Any],
    observation_states: Dict[str, ObservationFreshnessState],
) -> Dict[str, Dict[str, Any]]:
    """
    NAME
        build_shadow_device_results - Evaluate configured-device shadow truth from accepted observations.
    """
    observations_by_label: Dict[str, list[Tuple[EvidenceBlock, ObservationFreshnessState]]] = defaultdict(list)
    known_labels = set()
    for block_id, record in accepted_blocks.items():
        block = record.block
        state = observation_states.get(block_id)
        configured_label = ""
        if state is not None and state.configured_label:
            configured_label = state.configured_label
        elif block.target is not None and block.target.configured_label:
            configured_label = block.target.configured_label.strip()
        if not configured_label:
            continue
        known_labels.add(configured_label)
        if state is None:
            continue
        if state.current_influence <= ZERO_FLOAT:
            continue
        dimension_name = _payload_text(block.payload, PAYLOAD_KEY_DIMENSION)
        assertion_value = _payload_text(block.payload, PAYLOAD_KEY_ASSERTION)
        polarity_value = _payload_text(block.payload, PAYLOAD_KEY_POLARITY)
        if not _is_supported_assertion(dimension_name, assertion_value, polarity_value):
            continue
        observations_by_label[configured_label].append((block, state))
    results: Dict[str, Dict[str, Any]] = {}
    for configured_label in sorted(known_labels):
        rows = observations_by_label.get(configured_label, [])
        dimension_results = {
            dimension_name: _evaluate_dimension(rows, dimension_name)
            for dimension_name in DIMENSIONS
        }
        _apply_semantic_defaults(dimension_results)
        results[configured_label] = {
            RESULT_KEY_DIMENSIONS: dimension_results,
            RESULT_KEY_OVERALL_STATE: _derive_overall_state(dimension_results),
            RESULT_KEY_EVIDENCE_COUNT: len(rows),
            RESULT_KEY_CURRENT_OBSERVATION_COUNT: len(rows),
            RESULT_KEY_REASON_CODES: _collect_reason_codes(rows),
            RESULT_KEY_TRACE: _build_trace(rows),
        }
    return results


def _apply_semantic_defaults(dimension_results: Dict[str, Dict[str, Any]]) -> None:
    existence_value = dimension_results[DIMENSION_EXISTENCE][DIMENSION_KEY_VALUE]
    operability_value = dimension_results[DIMENSION_OPERABILITY][DIMENSION_KEY_VALUE]
    if existence_value == EXISTENCE_PRESENT and operability_value == OPERABILITY_UNKNOWN:
        dimension_results[DIMENSION_OPERABILITY] = _build_dimension_result(
            value=OPERABILITY_UNPROVEN,
            winning_support=ZERO_FLOAT,
            opposing_support=ZERO_FLOAT,
            group_count=ZERO_FLOAT,
            conflict=False,
            reason_codes=tuple(),
        )


def _evaluate_dimension(
    rows: Iterable[Tuple[EvidenceBlock, ObservationFreshnessState]],
    dimension_name: str,
) -> Dict[str, Any]:
    grouped_support: Dict[str, Dict[str, float]] = defaultdict(dict)
    grouped_reason_codes: Dict[str, list[str]] = defaultdict(list)
    for block, state in rows:
        if _payload_text(block.payload, PAYLOAD_KEY_DIMENSION) != dimension_name:
            continue
        assertion_value = _payload_text(block.payload, PAYLOAD_KEY_ASSERTION)
        group_name = _payload_text(block.payload, PAYLOAD_KEY_INDEPENDENCE_GROUP)
        if not group_name:
            group_name = block.block_id
        grouped_support[assertion_value][group_name] = _combine_group_member_influence(
            current_value=grouped_support[assertion_value].get(group_name, ZERO_FLOAT),
            added_value=_observation_influence(block, state),
        )
        reason_code = _payload_text(block.payload, PAYLOAD_KEY_REASON_CODE)
        if reason_code:
            grouped_reason_codes[assertion_value].append(reason_code)
    support_by_assertion = {
        assertion_value: _aggregate_independent_groups(group_values.values())
        for assertion_value, group_values in grouped_support.items()
    }
    if not support_by_assertion:
        default_value = _default_unknown_value(dimension_name)
        return _build_dimension_result(
            value=default_value,
            winning_support=ZERO_FLOAT,
            opposing_support=ZERO_FLOAT,
            group_count=ZERO_FLOAT,
            conflict=False,
            reason_codes=tuple(),
        )
    ordered = sorted(
        support_by_assertion.items(),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )
    winning_value = ordered[0][0]
    winning_support = ordered[0][1]
    opposing_support = ordered[1][1] if len(ordered) > 1 else ZERO_FLOAT
    if winning_support <= NEAR_ZERO_THRESHOLD:
        default_value = _default_unknown_value(dimension_name)
        return _build_dimension_result(
            value=default_value,
            winning_support=ZERO_FLOAT,
            opposing_support=ZERO_FLOAT,
            group_count=ZERO_FLOAT,
            conflict=False,
            reason_codes=tuple(),
        )
    margin = max(ZERO_FLOAT, winning_support - opposing_support)
    conflict = (
        winning_support >= CONFLICT_SUPPORT_THRESHOLD
        and opposing_support >= CONFLICT_SUPPORT_THRESHOLD
        and margin < CONFLICT_MARGIN_THRESHOLD
    )
    group_count = float(len(grouped_support.get(winning_value, {})))
    return _build_dimension_result(
        value=winning_value,
        winning_support=winning_support,
        opposing_support=opposing_support,
        group_count=group_count,
        conflict=conflict,
        reason_codes=tuple(sorted(set(grouped_reason_codes.get(winning_value, [])))),
    )


def _build_dimension_result(
    *,
    value: str,
    winning_support: float,
    opposing_support: float,
    group_count: float,
    conflict: bool,
    reason_codes: Tuple[str, ...],
) -> Dict[str, Any]:
    margin = max(ZERO_FLOAT, winning_support - opposing_support)
    return {
        DIMENSION_KEY_VALUE: value,
        DIMENSION_KEY_CONFIDENCE: winning_support,
        DIMENSION_KEY_CONFIDENCE_BAND: _confidence_band(winning_support),
        DIMENSION_KEY_CONFLICT: conflict,
        DIMENSION_KEY_WINNING_SUPPORT: winning_support,
        DIMENSION_KEY_OPPOSING_SUPPORT: opposing_support,
        DIMENSION_KEY_MARGIN: margin,
        DIMENSION_KEY_INDEPENDENT_GROUPS: int(group_count),
        DIMENSION_KEY_REASON_CODES: reason_codes,
    }


def _derive_overall_state(dimension_results: Dict[str, Dict[str, Any]]) -> str:
    existence_value = dimension_results[DIMENSION_EXISTENCE][DIMENSION_KEY_VALUE]
    communication_value = dimension_results[DIMENSION_COMMUNICATION][DIMENSION_KEY_VALUE]
    operability_value = dimension_results[DIMENSION_OPERABILITY][DIMENSION_KEY_VALUE]
    identity_value = dimension_results[DIMENSION_IDENTITY][DIMENSION_KEY_VALUE]
    any_conflict = any(
        bool(current_result[DIMENSION_KEY_CONFLICT])
        for current_result in dimension_results.values()
    )
    if any_conflict:
        return OVERALL_CAUTION
    if communication_value == COMMUNICATION_FAILED or operability_value == OPERABILITY_FAILED:
        return OVERALL_FAILED
    if identity_value == IDENTITY_MISMATCHED:
        return OVERALL_IDENTITY_FAULT
    if existence_value != EXISTENCE_PRESENT:
        return OVERALL_UNKNOWN
    if communication_value == COMMUNICATION_DEGRADED:
        return OVERALL_PROBABLE_FAULT
    if communication_value == COMMUNICATION_HEALTHY and operability_value in (
        OPERABILITY_UNPROVEN,
        OPERABILITY_UNKNOWN,
    ):
        return OVERALL_HEALTHY
    if operability_value in (OPERABILITY_UNPROVEN, OPERABILITY_UNKNOWN):
        return OVERALL_CAUTION
    if communication_value == COMMUNICATION_HEALTHY and operability_value == OPERABILITY_WORKING:
        return OVERALL_HEALTHY
    return OVERALL_CAUTION


def _observation_influence(
    block: EvidenceBlock,
    state: ObservationFreshnessState,
) -> float:
    claim_strength = _payload_float(block.payload, PAYLOAD_KEY_CLAIM_STRENGTH, ONE_FLOAT)
    specificity = _payload_float(block.payload, PAYLOAD_KEY_SPECIFICITY, ONE_FLOAT)
    directness = _payload_float(block.payload, PAYLOAD_KEY_DIRECTNESS, ONE_FLOAT)
    quality = _payload_float(block.payload, PAYLOAD_KEY_QUALITY, ONE_FLOAT)
    source_health = _payload_float(block.payload, PAYLOAD_KEY_SOURCE_HEALTH, ONE_FLOAT)
    base_reliability = _payload_float(block.payload, PAYLOAD_KEY_BASE_RELIABILITY, ONE_FLOAT)
    return (
        base_reliability
        * state.current_influence
        * claim_strength
        * specificity
        * directness
        * quality
        * source_health
    )


def _combine_group_member_influence(*, current_value: float, added_value: float) -> float:
    return ONE_FLOAT - ((ONE_FLOAT - current_value) * (ONE_FLOAT - added_value))


def _aggregate_independent_groups(group_values: Iterable[float]) -> float:
    support_value = ZERO_FLOAT
    for group_value in group_values:
        support_value = _combine_group_member_influence(
            current_value=support_value,
            added_value=group_value,
        )
    return support_value


def _collect_reason_codes(rows: Iterable[Tuple[EvidenceBlock, ObservationFreshnessState]]) -> Tuple[str, ...]:
    codes = []
    for block, _state in rows:
        reason_code = _payload_text(block.payload, PAYLOAD_KEY_REASON_CODE)
        if reason_code:
            codes.append(reason_code)
    return tuple(sorted(set(codes)))


def _build_trace(rows: Iterable[Tuple[EvidenceBlock, ObservationFreshnessState]]) -> Tuple[Dict[str, Any], ...]:
    trace_rows = []
    for block, state in rows:
        trace_rows.append(
            {
                TRACE_KEY_BLOCK_ID: block.block_id,
                TRACE_KEY_DIMENSION: _payload_text(block.payload, PAYLOAD_KEY_DIMENSION),
                TRACE_KEY_ASSERTION: _payload_text(block.payload, PAYLOAD_KEY_ASSERTION),
                TRACE_KEY_INFLUENCE: _observation_influence(block, state),
                TRACE_KEY_GROUP: _payload_text(block.payload, PAYLOAD_KEY_INDEPENDENCE_GROUP) or block.block_id,
                TRACE_KEY_REASON_CODE: _payload_text(block.payload, PAYLOAD_KEY_REASON_CODE),
            }
        )
    return tuple(trace_rows)


def _is_supported_assertion(dimension_name: str, assertion_value: str, polarity_value: str) -> bool:
    if polarity_value != PAYLOAD_POLARITY_SUPPORT:
        return False
    if dimension_name not in DIMENSION_ALLOWED_VALUES:
        return False
    return assertion_value in DIMENSION_ALLOWED_VALUES[dimension_name]


def _default_unknown_value(dimension_name: str) -> str:
    if dimension_name == DIMENSION_EXISTENCE:
        return EXISTENCE_UNKNOWN
    if dimension_name == DIMENSION_COMMUNICATION:
        return COMMUNICATION_UNKNOWN
    if dimension_name == DIMENSION_OPERABILITY:
        return OPERABILITY_UNKNOWN
    if dimension_name == DIMENSION_IDENTITY:
        return IDENTITY_UNKNOWN
    return IDENTITY_UNKNOWN


def _confidence_band(confidence_value: float) -> str:
    if confidence_value >= HIGH_CONFIDENCE_THRESHOLD:
        return CONFIDENCE_HIGH
    if confidence_value >= MEDIUM_CONFIDENCE_THRESHOLD:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


def _payload_text(payload: Dict[str, Any], key: str) -> str:
    return str(payload.get(key, "") or "").strip()


def _payload_float(payload: Dict[str, Any], key: str, default_value: float) -> float:
    raw_value = payload.get(key, default_value)
    if isinstance(raw_value, (int, float)):
        bounded = float(raw_value)
    else:
        try:
            bounded = float(str(raw_value).strip())
        except ValueError:
            bounded = default_value
    if bounded < ZERO_FLOAT:
        return ZERO_FLOAT
    if bounded > ONE_FLOAT + NEAR_ZERO_THRESHOLD:
        return ONE_FLOAT
    return min(ONE_FLOAT, bounded)
