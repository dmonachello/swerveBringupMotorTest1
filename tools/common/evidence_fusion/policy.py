from __future__ import annotations

"""
NAME
    policy.py - Freshness and correlation policy helpers for evidence-fusion slice 2.
"""

from tools.common.evidence_fusion.constants import (
    FRESHNESS_POLICY_NAME_CLOCK_TICK,
    FRESHNESS_POLICY_NAME_CONTEXT,
    FRESHNESS_POLICY_NAME_PASSIVE,
    FRESHNESS_POLICY_NAME_RUNTIME,
    FRESHNESS_POLICY_NAME_SOURCE_STATE,
    FRESHNESS_STATE_CURRENT,
    FRESHNESS_STATE_DECAYING,
    FRESHNESS_STATE_EXPIRED,
    FRESHNESS_STATE_HISTORICAL,
    MAJOR_TYPE_CLOCK_TICK,
    MAJOR_TYPE_CONTEXT_REVISION,
    MAJOR_TYPE_SOURCE_STATE,
    ONE_FLOAT,
    POLICY_CLOCK_TICK_CORRELATION_CAP,
    POLICY_CLOCK_TICK_FULL_STRENGTH_MS,
    POLICY_CLOCK_TICK_HARD_EXPIRY_MS,
    POLICY_CLOCK_TICK_HISTORICAL_RETENTION_MS,
    POLICY_CONTEXT_CORRELATION_CAP,
    POLICY_CONTEXT_FULL_STRENGTH_MS,
    POLICY_CONTEXT_HARD_EXPIRY_MS,
    POLICY_CONTEXT_HISTORICAL_RETENTION_MS,
    POLICY_PASSIVE_CORRELATION_CAP,
    POLICY_PASSIVE_FULL_STRENGTH_MS,
    POLICY_PASSIVE_HARD_EXPIRY_MS,
    POLICY_PASSIVE_HISTORICAL_RETENTION_MS,
    POLICY_RUNTIME_CORRELATION_CAP,
    POLICY_RUNTIME_FULL_STRENGTH_MS,
    POLICY_RUNTIME_HARD_EXPIRY_MS,
    POLICY_RUNTIME_HISTORICAL_RETENTION_MS,
    POLICY_SOURCE_STATE_CORRELATION_CAP,
    POLICY_SOURCE_STATE_FULL_STRENGTH_MS,
    POLICY_SOURCE_STATE_HARD_EXPIRY_MS,
    POLICY_SOURCE_STATE_HISTORICAL_RETENTION_MS,
    SOURCE_TYPES_USING_PASSIVE_LANE,
    SOURCE_TYPES_USING_RUNTIME_LANE,
    ZERO_FLOAT,
    ZERO_INT,
)
from tools.common.evidence_fusion.types import EvidenceBlock, FreshnessPolicy

_POLICY_RUNTIME = FreshnessPolicy(
    policy_name=FRESHNESS_POLICY_NAME_RUNTIME,
    full_strength_ms=POLICY_RUNTIME_FULL_STRENGTH_MS,
    hard_expiry_ms=POLICY_RUNTIME_HARD_EXPIRY_MS,
    historical_retention_ms=POLICY_RUNTIME_HISTORICAL_RETENTION_MS,
    correlation_cap=POLICY_RUNTIME_CORRELATION_CAP,
)
_POLICY_PASSIVE = FreshnessPolicy(
    policy_name=FRESHNESS_POLICY_NAME_PASSIVE,
    full_strength_ms=POLICY_PASSIVE_FULL_STRENGTH_MS,
    hard_expiry_ms=POLICY_PASSIVE_HARD_EXPIRY_MS,
    historical_retention_ms=POLICY_PASSIVE_HISTORICAL_RETENTION_MS,
    correlation_cap=POLICY_PASSIVE_CORRELATION_CAP,
)
_POLICY_SOURCE_STATE = FreshnessPolicy(
    policy_name=FRESHNESS_POLICY_NAME_SOURCE_STATE,
    full_strength_ms=POLICY_SOURCE_STATE_FULL_STRENGTH_MS,
    hard_expiry_ms=POLICY_SOURCE_STATE_HARD_EXPIRY_MS,
    historical_retention_ms=POLICY_SOURCE_STATE_HISTORICAL_RETENTION_MS,
    correlation_cap=POLICY_SOURCE_STATE_CORRELATION_CAP,
)
_POLICY_CONTEXT = FreshnessPolicy(
    policy_name=FRESHNESS_POLICY_NAME_CONTEXT,
    full_strength_ms=POLICY_CONTEXT_FULL_STRENGTH_MS,
    hard_expiry_ms=POLICY_CONTEXT_HARD_EXPIRY_MS,
    historical_retention_ms=POLICY_CONTEXT_HISTORICAL_RETENTION_MS,
    correlation_cap=POLICY_CONTEXT_CORRELATION_CAP,
)
_POLICY_CLOCK_TICK = FreshnessPolicy(
    policy_name=FRESHNESS_POLICY_NAME_CLOCK_TICK,
    full_strength_ms=POLICY_CLOCK_TICK_FULL_STRENGTH_MS,
    hard_expiry_ms=POLICY_CLOCK_TICK_HARD_EXPIRY_MS,
    historical_retention_ms=POLICY_CLOCK_TICK_HISTORICAL_RETENTION_MS,
    correlation_cap=POLICY_CLOCK_TICK_CORRELATION_CAP,
)


def resolve_freshness_policy(block: EvidenceBlock) -> FreshnessPolicy:
    """
    NAME
        resolve_freshness_policy - Return one default freshness policy for an accepted block.
    """
    if block.major_type == MAJOR_TYPE_CLOCK_TICK:
        return _POLICY_CLOCK_TICK
    if block.major_type == MAJOR_TYPE_CONTEXT_REVISION:
        return _POLICY_CONTEXT
    if block.major_type == MAJOR_TYPE_SOURCE_STATE:
        return _POLICY_SOURCE_STATE
    if block.source_type in SOURCE_TYPES_USING_RUNTIME_LANE:
        return _POLICY_RUNTIME
    if block.source_type in SOURCE_TYPES_USING_PASSIVE_LANE:
        return _POLICY_PASSIVE
    return _POLICY_PASSIVE


def classify_freshness_state(policy: FreshnessPolicy, age_monotonic_ms: int) -> tuple[str, float]:
    """
    NAME
        classify_freshness_state - Return one freshness bucket and influence factor for an age.
    """
    safe_age = max(ZERO_INT, int(age_monotonic_ms))
    if safe_age <= policy.full_strength_ms:
        return FRESHNESS_STATE_CURRENT, ONE_FLOAT
    if safe_age > policy.historical_retention_ms:
        return FRESHNESS_STATE_HISTORICAL, ZERO_FLOAT
    if safe_age > policy.hard_expiry_ms:
        return FRESHNESS_STATE_EXPIRED, ZERO_FLOAT
    distance_numerator = float(safe_age - policy.full_strength_ms)
    distance_denominator = max(ONE_FLOAT, float(policy.hard_expiry_ms - policy.full_strength_ms))
    normalized = min(ONE_FLOAT, max(ZERO_FLOAT, distance_numerator / distance_denominator))
    smoothstep = ONE_FLOAT - ((3.0 * normalized * normalized) - (2.0 * normalized * normalized * normalized))
    return FRESHNESS_STATE_DECAYING, smoothstep
