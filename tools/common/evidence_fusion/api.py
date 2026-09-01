from __future__ import annotations

"""
NAME
    api.py - Slice-2 in-memory evidence-fusion ingest, freshness, and invalidation API.

DESCRIPTION
    Provides one isolated additive engine instance with:
    - block validation
    - deduplication
    - queue-lane assignment
    - latest-wins coalescing metadata
    - unknown observed-device indexing
    - source-session rollover tracking
    - context-revision invalidation
    - clock-driven freshness classification
    - correlation-cap enforcement
    - immutable snapshot publication

    This slice still stops short of full per-dimension fusion. It only
    establishes the common freshness and invalidation substrate needed before
    authoritative device truth can move onto the new engine.
"""

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple

from tools.common.evidence_fusion.blocks import (
    build_coalescing_key,
    build_unknown_device_key,
    select_queue_lane,
    validate_evidence_block,
)
from tools.common.evidence_fusion.constants import (
    AFFECTED_SCOPE_CONTEXT,
    AFFECTED_SCOPE_DEVICE,
    AFFECTED_SCOPE_SOURCE,
    AFFECTED_SCOPE_SYSTEM,
    AFFECTED_SCOPE_UNKNOWN_DEVICE,
    DROP_REASON_DUPLICATE,
    DROP_REASON_INVALID,
    DROP_REASON_NONE,
    EVALUATION_ID_PREFIX,
    FRESHNESS_STATE_CURRENT,
    FRESHNESS_STATE_DECAYING,
    FRESHNESS_STATE_EXPIRED,
    FRESHNESS_STATE_HISTORICAL,
    MAJOR_TYPE_CLOCK_TICK,
    MAJOR_TYPE_CONTEXT_REVISION,
    MAJOR_TYPE_RETRACTION,
    ONE_INT,
    PAYLOAD_KEY_RETRACTED_BLOCK_ID,
    QUEUE_LANES_IN_PRIORITY_ORDER,
    RESULT_CODE_ACCEPTED,
    RESULT_CODE_DUPLICATE,
    RESULT_CODE_REJECTED,
    SCOPE_CONTEXT,
    SCOPE_DEVICE,
    SCOPE_SOURCE,
    SCOPE_SYSTEM,
    SNAPSHOT_ID_PREFIX,
    SYSTEM_STATE_KEY_ACTIVE_SOURCE_SESSIONS,
    SYSTEM_STATE_KEY_DEVICE_RESULTS,
    SYSTEM_STATE_KEY_OBSERVATION_STATE_COUNTS,
    SYSTEM_STATE_KEY_RETRACTED_BLOCK_IDS,
    SYSTEM_STATE_KEY_SYSTEM_RESULTS,
    UNKNOWN_DEVICE_PREFIX,
    ZERO_INT,
)
from tools.common.evidence_fusion.evaluator import build_shadow_device_results
from tools.common.evidence_fusion.policy import (
    classify_freshness_state,
    resolve_freshness_policy,
)
from tools.common.evidence_fusion.types import (
    DrainResult,
    EvaluationBudget,
    EvidenceBlock,
    EvidenceSnapshot,
    FreshnessPolicy,
    MutableRuntimeStats,
    ObservationFreshnessState,
    SubmitResult,
    UnknownObservedDeviceRecord,
)


@dataclass
class _AcceptedBlockRecord:
    """
    NAME
        _AcceptedBlockRecord - Internal accepted-block state.
    """

    block: EvidenceBlock
    queue_lane: str
    coalescing_key: Optional[Tuple[str, ...]]
    freshness_policy: FreshnessPolicy


class EvidenceFusionEngine:
    """
    NAME
        EvidenceFusionEngine - Slice-2 isolated ingest and freshness engine.
    """

    def __init__(self) -> None:
        self._accepted_blocks: Dict[str, _AcceptedBlockRecord] = {}
        self._pending_by_lane: Dict[str, Deque[str]] = {
            lane: deque() for lane in QUEUE_LANES_IN_PRIORITY_ORDER
        }
        self._pending_latest_by_coalescing_key: Dict[Tuple[str, ...], str] = {}
        self._unknown_observed_devices: Dict[str, UnknownObservedDeviceRecord] = {}
        self._source_session_by_key: Dict[str, str] = {}
        self._source_session_last_received_by_key: Dict[str, int] = {}
        self._retracted_block_ids: Dict[str, bool] = {}
        self._runtime_stats = MutableRuntimeStats()
        self._snapshot_counter = ZERO_INT
        self._evaluation_counter = ZERO_INT
        self._current_context_revision_id = ""
        self._current_snapshot = self._build_snapshot(
            evaluation_time_monotonic_ms=ZERO_INT
        )

    def submit_evidence_block(self, block: EvidenceBlock) -> SubmitResult:
        """
        NAME
            submit_evidence_block - Validate and enqueue one slice-2 block.
        """
        self._runtime_stats.submitted_blocks += ONE_INT
        valid, _errors = validate_evidence_block(block)
        if not valid:
            self._runtime_stats.dropped_blocks += ONE_INT
            return SubmitResult(
                accepted=False,
                result_code=RESULT_CODE_REJECTED,
                block_id=block.block_id,
                queue_lane="",
                coalesced=False,
                duplicate=False,
                dropped=True,
                drop_reason=DROP_REASON_INVALID,
                affected_scope_mask=tuple(),
                context_revision_id=block.context_revision_id,
            )
        if block.block_id in self._accepted_blocks:
            self._runtime_stats.duplicate_blocks += ONE_INT
            return SubmitResult(
                accepted=False,
                result_code=RESULT_CODE_DUPLICATE,
                block_id=block.block_id,
                queue_lane=self._accepted_blocks[block.block_id].queue_lane,
                coalesced=False,
                duplicate=True,
                dropped=True,
                drop_reason=DROP_REASON_DUPLICATE,
                affected_scope_mask=self._build_affected_scope_mask(
                    block,
                    unknown_created=False,
                ),
                context_revision_id=block.context_revision_id,
            )
        queue_lane = select_queue_lane(block)
        coalescing_key = build_coalescing_key(block)
        freshness_policy = resolve_freshness_policy(block)
        coalesced = False
        if (
            coalescing_key is not None
            and coalescing_key in self._pending_latest_by_coalescing_key
        ):
            coalesced = True
            self._runtime_stats.coalesced_blocks += ONE_INT
        record = _AcceptedBlockRecord(
            block=block,
            queue_lane=queue_lane,
            coalescing_key=coalescing_key,
            freshness_policy=freshness_policy,
        )
        self._accepted_blocks[block.block_id] = record
        self._pending_by_lane[queue_lane].append(block.block_id)
        if coalescing_key is not None:
            self._pending_latest_by_coalescing_key[coalescing_key] = block.block_id
        self._runtime_stats.accepted_blocks += ONE_INT
        self._update_lane_high_water(queue_lane)
        self._update_active_source_session(block)
        self._apply_context_revision(block)
        self._apply_retraction(block)
        unknown_created = self._maybe_update_unknown_observed_device(block)
        self._current_snapshot = self._build_snapshot(
            evaluation_time_monotonic_ms=self._runtime_stats.last_evaluation_time_monotonic_ms
        )
        return SubmitResult(
            accepted=True,
            result_code=RESULT_CODE_ACCEPTED,
            block_id=block.block_id,
            queue_lane=queue_lane,
            coalesced=coalesced,
            duplicate=False,
            dropped=False,
            drop_reason=DROP_REASON_NONE,
            affected_scope_mask=self._build_affected_scope_mask(
                block,
                unknown_created=unknown_created,
            ),
            context_revision_id=block.context_revision_id,
        )

    def drain_evaluation_budget(
        self,
        now_monotonic_ms: int,
        budget: EvaluationBudget,
    ) -> DrainResult:
        """
        NAME
            drain_evaluation_budget - Process up to the budgeted number of pending work items.
        """
        processed = ZERO_INT
        effective_now_monotonic_ms = max(
            int(now_monotonic_ms),
            int(self._runtime_stats.last_evaluation_time_monotonic_ms),
        )
        remaining_budget = max(ZERO_INT, budget.max_work_items)
        while remaining_budget > ZERO_INT:
            next_block_id = self._pop_next_pending_block_id()
            if not next_block_id:
                break
            record = self._accepted_blocks.get(next_block_id)
            if record is None:
                continue
            if record.coalescing_key is not None:
                latest_block_id = self._pending_latest_by_coalescing_key.get(
                    record.coalescing_key
                )
                if latest_block_id != next_block_id:
                    continue
                del self._pending_latest_by_coalescing_key[record.coalescing_key]
            self._mark_serviced(record.block, effective_now_monotonic_ms)
            processed += ONE_INT
            remaining_budget -= ONE_INT
        self._evaluation_counter += ONE_INT
        self._snapshot_counter += ONE_INT
        self._runtime_stats.last_evaluation_time_monotonic_ms = (
            effective_now_monotonic_ms
        )
        self._current_snapshot = self._build_snapshot(
            evaluation_time_monotonic_ms=effective_now_monotonic_ms
        )
        return DrainResult(
            work_items_processed=processed,
            pending_work_items=self._pending_work_item_count(),
            evaluation_id=self._current_snapshot.evaluation_id,
        )

    def get_current_snapshot(self) -> EvidenceSnapshot:
        """
        NAME
            get_current_snapshot - Return the current shared slice-2 snapshot.
        """
        return self._current_snapshot

    def get_runtime_stats(self):
        """
        NAME
            get_runtime_stats - Return current immutable runtime counters.
        """
        return self._runtime_stats.to_snapshot()

    def reset_runtime_state(self) -> None:
        """
        NAME
            reset_runtime_state - Clear all slice-2 in-memory state.
        """
        self.__init__()

    def _build_affected_scope_mask(
        self,
        block: EvidenceBlock,
        *,
        unknown_created: bool,
    ) -> Tuple[str, ...]:
        """
        NAME
            _build_affected_scope_mask - Return one machine-friendly affected-scope tuple.
        """
        scopes = []
        if block.scope == SCOPE_DEVICE:
            scopes.append(AFFECTED_SCOPE_DEVICE)
        if block.scope == SCOPE_SYSTEM:
            scopes.append(AFFECTED_SCOPE_SYSTEM)
        if block.scope == SCOPE_CONTEXT:
            scopes.append(AFFECTED_SCOPE_CONTEXT)
        if block.scope == SCOPE_SOURCE:
            scopes.append(AFFECTED_SCOPE_SOURCE)
        if unknown_created:
            scopes.append(AFFECTED_SCOPE_UNKNOWN_DEVICE)
        return tuple(scopes)

    def _update_lane_high_water(self, queue_lane: str) -> None:
        """
        NAME
            _update_lane_high_water - Track one queue depth high-water mark.
        """
        depth = len(self._pending_by_lane[queue_lane])
        current = self._runtime_stats.per_lane_depth_high_water.get(queue_lane, ZERO_INT)
        if depth > current:
            self._runtime_stats.per_lane_depth_high_water[queue_lane] = depth

    def _source_session_key_for_block(self, block: EvidenceBlock) -> str:
        """
        NAME
            _source_session_key_for_block - Return one stable active-session key for a source instance.
        """
        return "|".join((block.source_type, block.source_instance))

    def _update_active_source_session(self, block: EvidenceBlock) -> None:
        """
        NAME
            _update_active_source_session - Track the newest active source session for one source instance.
        """
        session_key = self._source_session_key_for_block(block)
        previous_received_at = self._source_session_last_received_by_key.get(
            session_key,
            ZERO_INT,
        )
        if block.received_at_monotonic_ms < previous_received_at:
            return
        previous_session_id = self._source_session_by_key.get(session_key, "")
        if previous_session_id and previous_session_id != block.source_session_id:
            self._runtime_stats.source_session_rollovers += ONE_INT
        self._source_session_by_key[session_key] = block.source_session_id
        self._source_session_last_received_by_key[session_key] = (
            block.received_at_monotonic_ms
        )

    def _apply_context_revision(self, block: EvidenceBlock) -> None:
        """
        NAME
            _apply_context_revision - Track the current context revision boundary.
        """
        if block.major_type == MAJOR_TYPE_CONTEXT_REVISION:
            if (
                self._current_context_revision_id
                and self._current_context_revision_id != block.context_revision_id
            ):
                self._runtime_stats.context_revision_rollovers += ONE_INT
            self._current_context_revision_id = block.context_revision_id
            return
        if not self._current_context_revision_id:
            self._current_context_revision_id = block.context_revision_id
            return
        if block.context_revision_id != self._current_context_revision_id:
            self._runtime_stats.late_context_blocks += ONE_INT

    def _apply_retraction(self, block: EvidenceBlock) -> None:
        """
        NAME
            _apply_retraction - Record explicit retractions for later historical-only classification.
        """
        if block.major_type != MAJOR_TYPE_RETRACTION:
            return
        retracted_block_id = str(
            block.payload.get(PAYLOAD_KEY_RETRACTED_BLOCK_ID, "")
        ).strip()
        if retracted_block_id:
            self._retracted_block_ids[retracted_block_id] = True

    def _maybe_update_unknown_observed_device(self, block: EvidenceBlock) -> bool:
        """
        NAME
            _maybe_update_unknown_observed_device - Create or update one unresolved observed-device record.
        """
        if block.scope != SCOPE_DEVICE or block.target is None or block.target.configured_label:
            return False
        unknown_device_key = build_unknown_device_key(block.target)
        if not unknown_device_key:
            return False
        unknown_device_id = f"{UNKNOWN_DEVICE_PREFIX}:{unknown_device_key}"
        existing = self._unknown_observed_devices.get(unknown_device_id)
        last_evaluated = (
            ZERO_INT
            if existing is None
            else existing.last_evaluated_at_monotonic_ms
        )
        self._unknown_observed_devices[unknown_device_id] = (
            UnknownObservedDeviceRecord(
                unknown_device_id=unknown_device_id,
                target=block.target,
                last_observed_at_monotonic_ms=block.observed_at_monotonic_ms,
                last_received_at_monotonic_ms=block.received_at_monotonic_ms,
                last_evaluated_at_monotonic_ms=last_evaluated,
                last_block_id=block.block_id,
            )
        )
        return True

    def _pop_next_pending_block_id(self) -> str:
        """
        NAME
            _pop_next_pending_block_id - Return the next pending block ID in lane priority order.
        """
        for queue_lane in QUEUE_LANES_IN_PRIORITY_ORDER:
            pending = self._pending_by_lane[queue_lane]
            if pending:
                return pending.popleft()
        return ""

    def _mark_serviced(self, block: EvidenceBlock, now_monotonic_ms: int) -> None:
        """
        NAME
            _mark_serviced - Update per-device and unknown-device service counters.
        """
        service_key = self._service_key_for_block(block)
        if service_key:
            count = (
                self._runtime_stats.per_device_service_count.get(service_key, ZERO_INT)
                + ONE_INT
            )
            previous_time = self._runtime_stats.per_device_last_serviced_time.get(
                service_key
            )
            self._runtime_stats.per_device_service_count[service_key] = count
            self._runtime_stats.per_device_last_serviced_time[service_key] = (
                now_monotonic_ms
            )
            if previous_time is not None:
                gap = now_monotonic_ms - previous_time
                current_max_gap = self._runtime_stats.per_device_max_service_gap.get(
                    service_key,
                    ZERO_INT,
                )
                if gap > current_max_gap:
                    self._runtime_stats.per_device_max_service_gap[service_key] = gap
        if (
            block.scope == SCOPE_DEVICE
            and block.target is not None
            and not block.target.configured_label
        ):
            unknown_device_key = build_unknown_device_key(block.target)
            unknown_device_id = f"{UNKNOWN_DEVICE_PREFIX}:{unknown_device_key}"
            existing = self._unknown_observed_devices.get(unknown_device_id)
            if existing is not None:
                self._unknown_observed_devices[unknown_device_id] = (
                    UnknownObservedDeviceRecord(
                        unknown_device_id=existing.unknown_device_id,
                        target=existing.target,
                        last_observed_at_monotonic_ms=existing.last_observed_at_monotonic_ms,
                        last_received_at_monotonic_ms=existing.last_received_at_monotonic_ms,
                        last_evaluated_at_monotonic_ms=now_monotonic_ms,
                        last_block_id=existing.last_block_id,
                    )
                )

    def _service_key_for_block(self, block: EvidenceBlock) -> str:
        """
        NAME
            _service_key_for_block - Return a stable service key for fairness counters.
        """
        if block.scope != SCOPE_DEVICE or block.target is None:
            return ""
        if block.target.configured_label:
            return block.target.configured_label.strip().lower()
        unknown_device_key = build_unknown_device_key(block.target)
        if not unknown_device_key:
            return ""
        return f"{UNKNOWN_DEVICE_PREFIX}:{unknown_device_key}"

    def _pending_work_item_count(self) -> int:
        """
        NAME
            _pending_work_item_count - Return the total number of queued block IDs.
        """
        return sum(len(queue) for queue in self._pending_by_lane.values())

    def _build_observation_states(
        self,
        *,
        evaluation_time_monotonic_ms: int,
    ) -> Dict[str, ObservationFreshnessState]:
        """
        NAME
            _build_observation_states - Classify accepted evidence-bearing blocks for the current snapshot.
        """
        observation_states: Dict[str, ObservationFreshnessState] = {}
        for block_id, record in self._accepted_blocks.items():
            block = record.block
            if block.major_type in (
                MAJOR_TYPE_CLOCK_TICK,
                MAJOR_TYPE_CONTEXT_REVISION,
                MAJOR_TYPE_RETRACTION,
            ):
                continue
            session_key = self._source_session_key_for_block(block)
            source_session_current = (
                self._source_session_by_key.get(session_key, "") == block.source_session_id
            )
            context_current = (
                not self._current_context_revision_id
                or block.context_revision_id == self._current_context_revision_id
            )
            retracted = bool(self._retracted_block_ids.get(block_id, False))
            age_monotonic_ms = max(
                ZERO_INT,
                evaluation_time_monotonic_ms - block.observed_at_monotonic_ms,
            )
            if not source_session_current or not context_current or retracted:
                freshness_state = FRESHNESS_STATE_HISTORICAL
                freshness_factor = 0.0
            else:
                freshness_state, freshness_factor = classify_freshness_state(
                    record.freshness_policy,
                    age_monotonic_ms,
                )
            current_influence = (
                freshness_factor
                if freshness_state in (FRESHNESS_STATE_CURRENT, FRESHNESS_STATE_DECAYING)
                else 0.0
            )
            configured_label = ""
            if block.target is not None and block.target.configured_label:
                configured_label = block.target.configured_label.strip()
            observation_states[block_id] = ObservationFreshnessState(
                block_id=block_id,
                source_type=block.source_type,
                source_instance=block.source_instance,
                source_session_id=block.source_session_id,
                major_type=block.major_type,
                scope=block.scope,
                configured_label=configured_label,
                freshness_policy_name=record.freshness_policy.policy_name,
                freshness_state=freshness_state,
                freshness_factor=freshness_factor,
                current_influence=current_influence,
                age_monotonic_ms=age_monotonic_ms,
                full_strength_until_monotonic_ms=(
                    block.observed_at_monotonic_ms
                    + record.freshness_policy.full_strength_ms
                ),
                hard_expiry_at_monotonic_ms=(
                    block.observed_at_monotonic_ms
                    + record.freshness_policy.hard_expiry_ms
                ),
                historical_until_monotonic_ms=(
                    block.observed_at_monotonic_ms
                    + record.freshness_policy.historical_retention_ms
                ),
                source_session_current=source_session_current,
                context_current=context_current,
                retracted=retracted,
                correlation_id=block.correlation_id,
                correlation_rank=ONE_INT,
                correlation_capped=False,
            )
        return self._apply_correlation_caps(observation_states)

    def _apply_correlation_caps(
        self,
        observation_states: Dict[str, ObservationFreshnessState],
    ) -> Dict[str, ObservationFreshnessState]:
        """
        NAME
            _apply_correlation_caps - Limit current influence for oversized correlation groups.
        """
        grouped_block_ids: Dict[str, list[str]] = {}
        for block_id, state in observation_states.items():
            if not state.correlation_id:
                continue
            if state.freshness_state not in (
                FRESHNESS_STATE_CURRENT,
                FRESHNESS_STATE_DECAYING,
            ):
                continue
            grouped_block_ids.setdefault(state.correlation_id, []).append(block_id)
        for correlation_id, block_ids in grouped_block_ids.items():
            ordered = sorted(
                block_ids,
                key=lambda current_block_id: (
                    self._accepted_blocks[current_block_id].block.observed_at_monotonic_ms,
                    self._accepted_blocks[current_block_id].block.received_at_monotonic_ms,
                ),
                reverse=True,
            )
            for index, block_id in enumerate(ordered, start=ONE_INT):
                state = observation_states[block_id]
                correlation_cap = self._accepted_blocks[
                    block_id
                ].freshness_policy.correlation_cap
                correlation_capped = index > correlation_cap
                observation_states[block_id] = ObservationFreshnessState(
                    block_id=state.block_id,
                    source_type=state.source_type,
                    source_instance=state.source_instance,
                    source_session_id=state.source_session_id,
                    major_type=state.major_type,
                    scope=state.scope,
                    configured_label=state.configured_label,
                    freshness_policy_name=state.freshness_policy_name,
                    freshness_state=state.freshness_state,
                    freshness_factor=state.freshness_factor,
                    current_influence=(
                        0.0 if correlation_capped else state.current_influence
                    ),
                    age_monotonic_ms=state.age_monotonic_ms,
                    full_strength_until_monotonic_ms=state.full_strength_until_monotonic_ms,
                    hard_expiry_at_monotonic_ms=state.hard_expiry_at_monotonic_ms,
                    historical_until_monotonic_ms=state.historical_until_monotonic_ms,
                    source_session_current=state.source_session_current,
                    context_current=state.context_current,
                    retracted=state.retracted,
                    correlation_id=correlation_id,
                    correlation_rank=index,
                    correlation_capped=correlation_capped,
                )
        return observation_states

    def _build_snapshot(
        self,
        *,
        evaluation_time_monotonic_ms: int,
    ) -> EvidenceSnapshot:
        """
        NAME
            _build_snapshot - Freeze one shared slice-2 snapshot.
        """
        snapshot_id = f"{SNAPSHOT_ID_PREFIX}:{self._snapshot_counter}"
        evaluation_id = f"{EVALUATION_ID_PREFIX}:{self._evaluation_counter}"
        observation_states = self._build_observation_states(
            evaluation_time_monotonic_ms=evaluation_time_monotonic_ms
        )
        configured_device_results = build_shadow_device_results(
            self._accepted_blocks,
            observation_states,
        )
        observation_state_counts = {
            FRESHNESS_STATE_CURRENT: ZERO_INT,
            FRESHNESS_STATE_DECAYING: ZERO_INT,
            FRESHNESS_STATE_EXPIRED: ZERO_INT,
            FRESHNESS_STATE_HISTORICAL: ZERO_INT,
        }
        for state in observation_states.values():
            observation_state_counts[state.freshness_state] = (
                observation_state_counts.get(state.freshness_state, ZERO_INT)
                + ONE_INT
            )
        return EvidenceSnapshot(
            snapshot_id=snapshot_id,
            evaluation_id=evaluation_id,
            context_revision_id=self._current_context_revision_id,
            evaluation_time_monotonic_ms=evaluation_time_monotonic_ms,
            configured_devices=configured_device_results,
            observation_states=observation_states,
            unknown_observed_devices=dict(self._unknown_observed_devices),
            system_state={
                SYSTEM_STATE_KEY_ACTIVE_SOURCE_SESSIONS: dict(
                    self._source_session_by_key
                ),
                SYSTEM_STATE_KEY_RETRACTED_BLOCK_IDS: tuple(
                    sorted(self._retracted_block_ids.keys())
                ),
                SYSTEM_STATE_KEY_OBSERVATION_STATE_COUNTS: observation_state_counts,
                SYSTEM_STATE_KEY_DEVICE_RESULTS: tuple(
                    sorted(configured_device_results.keys())
                ),
                SYSTEM_STATE_KEY_SYSTEM_RESULTS: {},
            },
            runtime_stats=self._runtime_stats.to_snapshot(),
        )


_DEFAULT_ENGINE = EvidenceFusionEngine()


def submit_evidence_block(block: EvidenceBlock) -> SubmitResult:
    """
    NAME
        submit_evidence_block - Submit one block through the default engine instance.
    """
    return _DEFAULT_ENGINE.submit_evidence_block(block)


def drain_evaluation_budget(
    now_monotonic_ms: int,
    budget: EvaluationBudget,
) -> DrainResult:
    """
    NAME
        drain_evaluation_budget - Drain one evaluation budget through the default engine instance.
    """
    return _DEFAULT_ENGINE.drain_evaluation_budget(now_monotonic_ms, budget)


def get_current_snapshot() -> EvidenceSnapshot:
    """
    NAME
        get_current_snapshot - Return the default engine snapshot.
    """
    return _DEFAULT_ENGINE.get_current_snapshot()


def get_runtime_stats():
    """
    NAME
        get_runtime_stats - Return default engine runtime stats.
    """
    return _DEFAULT_ENGINE.get_runtime_stats()


def reset_runtime_state() -> None:
    """
    NAME
        reset_runtime_state - Clear default engine state.
    """
    _DEFAULT_ENGINE.reset_runtime_state()
