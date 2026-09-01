from __future__ import annotations

"""
NAME
    types.py - Typed records for the stage-1 evidence-fusion core.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class EvidenceTarget:
    """
    NAME
        EvidenceTarget - Source-resolved target identity for one evidence block.
    """

    configured_label: Optional[str] = None
    vendor: Optional[str] = None
    device_type: Optional[str] = None
    interface_type: Optional[str] = None
    bus_name: Optional[str] = None
    address_value: Optional[int] = None
    mechanism_name: Optional[str] = None
    target_confidence: Optional[float] = None


@dataclass(frozen=True)
class EvidenceBlock:
    """
    NAME
        EvidenceBlock - Immutable stage-1 production evidence envelope.
    """

    schema_version: int
    block_id: str
    source_type: str
    source_instance: str
    source_session_id: str
    major_type: str
    scope: str
    target: Optional[EvidenceTarget]
    observed_at_monotonic_ms: int
    received_at_monotonic_ms: int
    context_revision_id: str
    correlation_id: Optional[str]
    priority_hint: str
    payload: Dict[str, Any]


@dataclass(frozen=True)
class FreshnessPolicy:
    """
    NAME
        FreshnessPolicy - Time-window and correlation-cap policy for one block family.
    """

    policy_name: str
    full_strength_ms: int
    hard_expiry_ms: int
    historical_retention_ms: int
    correlation_cap: int


@dataclass(frozen=True)
class ObservationFreshnessState:
    """
    NAME
        ObservationFreshnessState - Frozen freshness and invalidation state for one accepted block.
    """

    block_id: str
    source_type: str
    source_instance: str
    source_session_id: str
    major_type: str
    scope: str
    configured_label: str
    freshness_policy_name: str
    freshness_state: str
    freshness_factor: float
    current_influence: float
    age_monotonic_ms: int
    full_strength_until_monotonic_ms: int
    hard_expiry_at_monotonic_ms: int
    historical_until_monotonic_ms: int
    source_session_current: bool
    context_current: bool
    retracted: bool
    correlation_id: Optional[str]
    correlation_rank: int
    correlation_capped: bool


@dataclass(frozen=True)
class SubmitResult:
    """
    NAME
        SubmitResult - Machine result from one enqueue attempt.
    """

    accepted: bool
    result_code: str
    block_id: str
    queue_lane: str
    coalesced: bool
    duplicate: bool
    dropped: bool
    drop_reason: str
    affected_scope_mask: Tuple[str, ...]
    context_revision_id: str


@dataclass(frozen=True)
class EvaluationBudget:
    """
    NAME
        EvaluationBudget - Limits one drain pass.
    """

    max_work_items: int


@dataclass(frozen=True)
class DrainResult:
    """
    NAME
        DrainResult - Summary from one scheduler drain pass.
    """

    work_items_processed: int
    pending_work_items: int
    evaluation_id: str


@dataclass(frozen=True)
class UnknownObservedDeviceRecord:
    """
    NAME
        UnknownObservedDeviceRecord - Current state for one unresolved observed device.
    """

    unknown_device_id: str
    target: EvidenceTarget
    last_observed_at_monotonic_ms: int
    last_received_at_monotonic_ms: int
    last_evaluated_at_monotonic_ms: int
    last_block_id: str


@dataclass(frozen=True)
class RuntimeStatsSnapshot:
    """
    NAME
        RuntimeStatsSnapshot - Immutable runtime counters and service metrics.
    """

    submitted_blocks: int
    accepted_blocks: int
    duplicate_blocks: int
    coalesced_blocks: int
    dropped_blocks: int
    late_context_blocks: int
    expired_before_eval_blocks: int
    source_session_rollovers: int
    context_revision_rollovers: int
    last_evaluation_time_monotonic_ms: int
    per_lane_depth_high_water: Dict[str, int]
    per_device_service_count: Dict[str, int]
    per_device_last_serviced_time: Dict[str, int]
    per_device_max_service_gap: Dict[str, int]


@dataclass(frozen=True)
class EvidenceSnapshot:
    """
    NAME
        EvidenceSnapshot - Shared machine-readable stage-1 snapshot.
    """

    snapshot_id: str
    evaluation_id: str
    context_revision_id: str
    evaluation_time_monotonic_ms: int
    configured_devices: Dict[str, Dict[str, Any]]
    observation_states: Dict[str, ObservationFreshnessState]
    unknown_observed_devices: Dict[str, UnknownObservedDeviceRecord]
    system_state: Dict[str, Any]
    runtime_stats: RuntimeStatsSnapshot


@dataclass
class MutableRuntimeStats:
    """
    NAME
        MutableRuntimeStats - Internal mutable counters for one engine instance.
    """

    submitted_blocks: int = 0
    accepted_blocks: int = 0
    duplicate_blocks: int = 0
    coalesced_blocks: int = 0
    dropped_blocks: int = 0
    late_context_blocks: int = 0
    expired_before_eval_blocks: int = 0
    source_session_rollovers: int = 0
    context_revision_rollovers: int = 0
    last_evaluation_time_monotonic_ms: int = 0
    per_lane_depth_high_water: Dict[str, int] = field(default_factory=dict)
    per_device_service_count: Dict[str, int] = field(default_factory=dict)
    per_device_last_serviced_time: Dict[str, int] = field(default_factory=dict)
    per_device_max_service_gap: Dict[str, int] = field(default_factory=dict)

    def to_snapshot(self) -> RuntimeStatsSnapshot:
        """
        NAME
            to_snapshot - Freeze runtime counters into an immutable result.
        """
        return RuntimeStatsSnapshot(
            submitted_blocks=self.submitted_blocks,
            accepted_blocks=self.accepted_blocks,
            duplicate_blocks=self.duplicate_blocks,
            coalesced_blocks=self.coalesced_blocks,
            dropped_blocks=self.dropped_blocks,
            late_context_blocks=self.late_context_blocks,
            expired_before_eval_blocks=self.expired_before_eval_blocks,
            source_session_rollovers=self.source_session_rollovers,
            context_revision_rollovers=self.context_revision_rollovers,
            last_evaluation_time_monotonic_ms=self.last_evaluation_time_monotonic_ms,
            per_lane_depth_high_water=dict(self.per_lane_depth_high_water),
            per_device_service_count=dict(self.per_device_service_count),
            per_device_last_serviced_time=dict(self.per_device_last_serviced_time),
            per_device_max_service_gap=dict(self.per_device_max_service_gap),
        )
