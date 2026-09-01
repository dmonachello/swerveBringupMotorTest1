"""
NAME
    test_evidence_fusion_api.py - Focused regression tests for the first evidence-fusion implementation slice.
"""

import unittest

from tools.common.evidence_fusion.api import EvidenceFusionEngine
from tools.common.evidence_fusion.constants import (
    COMMUNICATION_FAILED,
    COMMUNICATION_HEALTHY,
    COMMUNICATION_UNKNOWN,
    FRESHNESS_STATE_CURRENT,
    FRESHNESS_STATE_DECAYING,
    FRESHNESS_STATE_EXPIRED,
    FRESHNESS_STATE_HISTORICAL,
    DIMENSION_COMMUNICATION,
    DIMENSION_EXISTENCE,
    DIMENSION_IDENTITY,
    EXISTENCE_PRESENT,
    HIGH_CONFIDENCE_THRESHOLD,
    MAJOR_TYPE_CLOCK_TICK,
    MAJOR_TYPE_CONTEXT_REVISION,
    MAJOR_TYPE_OBSERVATION,
    MAJOR_TYPE_RETRACTION,
    OPERABILITY_UNPROVEN,
    OVERALL_CAUTION,
    OVERALL_HEALTHY,
    OVERALL_UNKNOWN,
    PAYLOAD_KEY_RETRACTED_BLOCK_ID,
    QUEUE_LANE_CLOCK_TICK,
    QUEUE_LANE_PERIODIC_RUNTIME,
    RESULT_CODE_ACCEPTED,
    RESULT_CODE_DUPLICATE,
    RESULT_CODE_REJECTED,
    SCHEMA_VERSION_1,
    SCOPE_DEVICE,
    SCOPE_SYSTEM,
    SOURCE_TYPE_RUNTIME,
    SOURCE_TYPE_SYSTEM_CLOCK,
)
from tools.common.evidence_fusion.types import EvaluationBudget, EvidenceBlock, EvidenceTarget

BLOCK_ID_RUNTIME_1 = "runtime:block:1"
BLOCK_ID_RUNTIME_2 = "runtime:block:2"
BLOCK_ID_CLOCK_1 = "clock:block:1"
CONTEXT_REVISION_ID_1 = "context:1"
SOURCE_INSTANCE_RUNTIME = "rio-runtime"
SOURCE_INSTANCE_CLOCK = "fusion-clock"
SOURCE_SESSION_ID_RUNTIME = "session-runtime-1"
SOURCE_SESSION_ID_CLOCK = "session-clock-1"
CONFIGURED_LABEL_FALCON = "FALCON 9"
VENDOR_CTRE = "ctre"
DEVICE_TYPE_MOTOR = "motor"
INTERFACE_CAN = "CAN"
BUS_RIO = "rio"
ADDRESS_NINE = 9
ADDRESS_TWENTY_FIVE = 25
TIME_OBSERVED_100 = 100
TIME_RECEIVED_110 = 110
TIME_OBSERVED_120 = 120
TIME_RECEIVED_130 = 130
TIME_EVAL_300 = 300
TIME_EVAL_500 = 500
TIME_EVAL_800 = 800
TIME_EVAL_2500 = 2500
TIME_EVAL_12001 = 12001
TIME_OBSERVED_140 = 140
TIME_RECEIVED_150 = 150
MAX_WORK_ITEMS_ONE = 1
MAX_WORK_ITEMS_TEN = 10
CONTEXT_REVISION_ID_2 = "context:2"
SOURCE_SESSION_ID_RUNTIME_2 = "session-runtime-2"
CORRELATION_GROUP_SHARED = "shared-correlation"
CONFIGURED_LABEL_SPARK25 = "SPARKMAX/NEO 25"
CONFIGURED_LABEL_SPARK7 = "SPARKMAX/NEO 7"


def _build_runtime_block(
    *,
    block_id: str,
    configured_label: str | None,
    address_value: int,
    observed_at: int,
    received_at: int,
    source_session_id: str = SOURCE_SESSION_ID_RUNTIME,
    context_revision_id: str = CONTEXT_REVISION_ID_1,
    correlation_id: str | None = None,
    payload: dict | None = None,
) -> EvidenceBlock:
    return EvidenceBlock(
        schema_version=SCHEMA_VERSION_1,
        block_id=block_id,
        source_type=SOURCE_TYPE_RUNTIME,
        source_instance=SOURCE_INSTANCE_RUNTIME,
        source_session_id=source_session_id,
        major_type=MAJOR_TYPE_OBSERVATION,
        scope=SCOPE_DEVICE,
        target=EvidenceTarget(
            configured_label=configured_label,
            vendor=VENDOR_CTRE,
            device_type=DEVICE_TYPE_MOTOR,
            interface_type=INTERFACE_CAN,
            bus_name=BUS_RIO,
            address_value=address_value,
        ),
        observed_at_monotonic_ms=observed_at,
        received_at_monotonic_ms=received_at,
        context_revision_id=context_revision_id,
        correlation_id=correlation_id,
        priority_hint="default",
        payload={} if payload is None else payload,
    )


def _build_clock_block() -> EvidenceBlock:
    return EvidenceBlock(
        schema_version=SCHEMA_VERSION_1,
        block_id=BLOCK_ID_CLOCK_1,
        source_type=SOURCE_TYPE_SYSTEM_CLOCK,
        source_instance=SOURCE_INSTANCE_CLOCK,
        source_session_id=SOURCE_SESSION_ID_CLOCK,
        major_type=MAJOR_TYPE_CLOCK_TICK,
        scope=SCOPE_SYSTEM,
        target=None,
        observed_at_monotonic_ms=TIME_OBSERVED_120,
        received_at_monotonic_ms=TIME_RECEIVED_130,
        context_revision_id=CONTEXT_REVISION_ID_1,
        correlation_id=None,
        priority_hint="default",
        payload={},
    )


def _build_context_block(
    *,
    block_id: str,
    context_revision_id: str,
    observed_at: int,
    received_at: int,
) -> EvidenceBlock:
    return EvidenceBlock(
        schema_version=SCHEMA_VERSION_1,
        block_id=block_id,
        source_type=SOURCE_TYPE_SYSTEM_CLOCK,
        source_instance=SOURCE_INSTANCE_CLOCK,
        source_session_id=SOURCE_SESSION_ID_CLOCK,
        major_type=MAJOR_TYPE_CONTEXT_REVISION,
        scope=SCOPE_SYSTEM,
        target=None,
        observed_at_monotonic_ms=observed_at,
        received_at_monotonic_ms=received_at,
        context_revision_id=context_revision_id,
        correlation_id=None,
        priority_hint="default",
        payload={},
    )


def _build_retraction_block(
    *,
    block_id: str,
    retracted_block_id: str,
    observed_at: int,
    received_at: int,
) -> EvidenceBlock:
    return EvidenceBlock(
        schema_version=SCHEMA_VERSION_1,
        block_id=block_id,
        source_type=SOURCE_TYPE_SYSTEM_CLOCK,
        source_instance=SOURCE_INSTANCE_CLOCK,
        source_session_id=SOURCE_SESSION_ID_CLOCK,
        major_type=MAJOR_TYPE_RETRACTION,
        scope=SCOPE_SYSTEM,
        target=None,
        observed_at_monotonic_ms=observed_at,
        received_at_monotonic_ms=received_at,
        context_revision_id=CONTEXT_REVISION_ID_1,
        correlation_id=None,
        priority_hint="default",
        payload={PAYLOAD_KEY_RETRACTED_BLOCK_ID: retracted_block_id},
    )


class EvidenceFusionApiTests(unittest.TestCase):
    def test_shadow_snapshot_publishes_fresh_existence_result_for_configured_device(self) -> None:
        engine = EvidenceFusionEngine()

        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
                payload={
                    "dimension": "existence",
                    "assertion": "PRESENT",
                    "polarity": "support",
                    "claimStrength": 1.0,
                    "specificity": 1.0,
                    "directness": 1.0,
                    "quality": 1.0,
                    "sourceHealth": 1.0,
                    "baseReliability": 1.0,
                    "independenceGroup": "runtime:f9:existence",
                    "reasonCode": "RUNTIME_PRESENT",
                },
            )
        )
        engine.drain_evaluation_budget(
            TIME_EVAL_300,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )

        snapshot = engine.get_current_snapshot()
        result = snapshot.configured_devices[CONFIGURED_LABEL_FALCON]
        dimensions = result["dimensions"]

        self.assertEqual(
            EXISTENCE_PRESENT,
            dimensions[DIMENSION_EXISTENCE]["value"],
        )
        self.assertGreaterEqual(
            dimensions[DIMENSION_EXISTENCE]["confidence"],
            HIGH_CONFIDENCE_THRESHOLD,
        )
        self.assertEqual(OVERALL_CAUTION, result["overallState"])
        self.assertEqual(OPERABILITY_UNPROVEN, dimensions["operability"]["value"])
        self.assertEqual("UNKNOWN", dimensions[DIMENSION_IDENTITY]["value"])

    def test_shadow_snapshot_prefers_stronger_communication_assertion(self) -> None:
        engine = EvidenceFusionEngine()

        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
                payload={
                    "dimension": "communication",
                    "assertion": "HEALTHY",
                    "polarity": "support",
                    "claimStrength": 0.9,
                    "specificity": 1.0,
                    "directness": 1.0,
                    "quality": 1.0,
                    "sourceHealth": 1.0,
                    "baseReliability": 1.0,
                    "independenceGroup": "runtime:f9:comm",
                    "reasonCode": "RUNTIME_COMM_HEALTHY",
                },
            )
        )
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_2,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_120,
                received_at=TIME_RECEIVED_130,
                payload={
                    "dimension": "communication",
                    "assertion": "FAILED",
                    "polarity": "support",
                    "claimStrength": 0.3,
                    "specificity": 1.0,
                    "directness": 1.0,
                    "quality": 1.0,
                    "sourceHealth": 1.0,
                    "baseReliability": 1.0,
                    "independenceGroup": "console:f9:comm",
                    "reasonCode": "CONSOLE_TIMEOUT",
                },
            )
        )
        engine.drain_evaluation_budget(
            TIME_EVAL_300,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )

        snapshot = engine.get_current_snapshot()
        dimensions = snapshot.configured_devices[CONFIGURED_LABEL_FALCON]["dimensions"]

        self.assertEqual(
            COMMUNICATION_HEALTHY,
            dimensions[DIMENSION_COMMUNICATION]["value"],
        )
        self.assertGreater(
            dimensions[DIMENSION_COMMUNICATION]["winningSupport"],
            dimensions[DIMENSION_COMMUNICATION]["opposingSupport"],
        )

    def test_shadow_snapshot_marks_present_healthy_unproven_device_as_healthy_overall(self) -> None:
        engine = EvidenceFusionEngine()

        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
                payload={
                    "dimension": "existence",
                    "assertion": "PRESENT",
                    "polarity": "support",
                    "claimStrength": 1.0,
                    "specificity": 1.0,
                    "directness": 1.0,
                    "quality": 1.0,
                    "sourceHealth": 1.0,
                    "baseReliability": 1.0,
                    "independenceGroup": "runtime:f9:existence",
                    "reasonCode": "RUNTIME_PRESENT",
                },
            )
        )
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_2,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_120,
                received_at=TIME_RECEIVED_130,
                payload={
                    "dimension": "communication",
                    "assertion": "HEALTHY",
                    "polarity": "support",
                    "claimStrength": 1.0,
                    "specificity": 1.0,
                    "directness": 1.0,
                    "quality": 1.0,
                    "sourceHealth": 1.0,
                    "baseReliability": 1.0,
                    "independenceGroup": "runtime:f9:communication",
                    "reasonCode": "RUNTIME_COMM_HEALTHY",
                },
            )
        )
        engine.drain_evaluation_budget(
            TIME_EVAL_300,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )

        snapshot = engine.get_current_snapshot()
        result = snapshot.configured_devices[CONFIGURED_LABEL_FALCON]

        self.assertEqual(OVERALL_HEALTHY, result["overallState"])
        self.assertEqual(OPERABILITY_UNPROVEN, result["dimensions"]["operability"]["value"])

    def test_shadow_snapshot_expires_dimension_observation_to_unknown(self) -> None:
        engine = EvidenceFusionEngine()

        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
                payload={
                    "dimension": "communication",
                    "assertion": "FAILED",
                    "polarity": "support",
                    "claimStrength": 1.0,
                    "specificity": 1.0,
                    "directness": 1.0,
                    "quality": 1.0,
                    "sourceHealth": 1.0,
                    "baseReliability": 1.0,
                    "independenceGroup": "console:f9:comm",
                    "reasonCode": "CONSOLE_TIMEOUT",
                },
            )
        )
        engine.drain_evaluation_budget(
            TIME_EVAL_300,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )
        engine.submit_evidence_block(_build_clock_block())
        engine.drain_evaluation_budget(
            TIME_EVAL_12001,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )

        snapshot = engine.get_current_snapshot()
        dimensions = snapshot.configured_devices.get(CONFIGURED_LABEL_FALCON, {}).get("dimensions", {})

        self.assertEqual(
            COMMUNICATION_UNKNOWN,
            dimensions[DIMENSION_COMMUNICATION]["value"],
        )

    def test_shadow_snapshot_conflicted_communication_yields_caution_overall(self) -> None:
        engine = EvidenceFusionEngine()

        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
                payload={
                    "dimension": "communication",
                    "assertion": "HEALTHY",
                    "polarity": "support",
                    "claimStrength": 0.8,
                    "specificity": 1.0,
                    "directness": 1.0,
                    "quality": 1.0,
                    "sourceHealth": 1.0,
                    "baseReliability": 1.0,
                    "independenceGroup": "runtime:f9:comm",
                    "reasonCode": "RUNTIME_COMM_HEALTHY",
                },
            )
        )
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_2,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_120,
                received_at=TIME_RECEIVED_130,
                payload={
                    "dimension": "communication",
                    "assertion": "FAILED",
                    "polarity": "support",
                    "claimStrength": 0.8,
                    "specificity": 1.0,
                    "directness": 1.0,
                    "quality": 1.0,
                    "sourceHealth": 1.0,
                    "baseReliability": 1.0,
                    "independenceGroup": "console:f9:comm",
                    "reasonCode": "CONSOLE_TIMEOUT",
                },
            )
        )
        engine.drain_evaluation_budget(
            TIME_EVAL_300,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )

        snapshot = engine.get_current_snapshot()
        result = snapshot.configured_devices[CONFIGURED_LABEL_FALCON]

        self.assertTrue(result["dimensions"][DIMENSION_COMMUNICATION]["conflict"])
        self.assertEqual(OVERALL_CAUTION, result["overallState"])

    def test_submit_accepts_valid_block_and_assigns_runtime_lane(self) -> None:
        engine = EvidenceFusionEngine()

        result = engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
            )
        )

        self.assertTrue(result.accepted)
        self.assertEqual(RESULT_CODE_ACCEPTED, result.result_code)
        self.assertEqual(QUEUE_LANE_PERIODIC_RUNTIME, result.queue_lane)
        self.assertFalse(result.coalesced)
        self.assertFalse(result.duplicate)
        self.assertFalse(result.dropped)

    def test_submit_rejects_duplicate_block_id(self) -> None:
        engine = EvidenceFusionEngine()
        block = _build_runtime_block(
            block_id=BLOCK_ID_RUNTIME_1,
            configured_label=CONFIGURED_LABEL_FALCON,
            address_value=ADDRESS_NINE,
            observed_at=TIME_OBSERVED_100,
            received_at=TIME_RECEIVED_110,
        )

        first_result = engine.submit_evidence_block(block)
        second_result = engine.submit_evidence_block(block)

        self.assertTrue(first_result.accepted)
        self.assertFalse(second_result.accepted)
        self.assertEqual(RESULT_CODE_DUPLICATE, second_result.result_code)
        stats = engine.get_runtime_stats()
        self.assertEqual(1, stats.duplicate_blocks)

    def test_submit_rejects_invalid_block(self) -> None:
        engine = EvidenceFusionEngine()
        invalid_block = EvidenceBlock(
            schema_version=SCHEMA_VERSION_1,
            block_id="",
            source_type=SOURCE_TYPE_RUNTIME,
            source_instance=SOURCE_INSTANCE_RUNTIME,
            source_session_id=SOURCE_SESSION_ID_RUNTIME,
            major_type=MAJOR_TYPE_OBSERVATION,
            scope=SCOPE_DEVICE,
            target=None,
            observed_at_monotonic_ms=TIME_OBSERVED_100,
            received_at_monotonic_ms=TIME_RECEIVED_110,
            context_revision_id=CONTEXT_REVISION_ID_1,
            correlation_id=None,
            priority_hint="default",
            payload={},
        )

        result = engine.submit_evidence_block(invalid_block)

        self.assertFalse(result.accepted)
        self.assertEqual(RESULT_CODE_REJECTED, result.result_code)
        stats = engine.get_runtime_stats()
        self.assertEqual(1, stats.dropped_blocks)

    def test_submit_updates_unknown_observed_device_record_for_partial_target(self) -> None:
        engine = EvidenceFusionEngine()

        result = engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=None,
                address_value=ADDRESS_TWENTY_FIVE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
            )
        )

        snapshot = engine.get_current_snapshot()

        self.assertTrue(result.accepted)
        self.assertEqual(1, len(snapshot.unknown_observed_devices))
        unknown_record = next(iter(snapshot.unknown_observed_devices.values()))
        self.assertEqual(BLOCK_ID_RUNTIME_1, unknown_record.last_block_id)
        self.assertEqual(TIME_OBSERVED_100, unknown_record.last_observed_at_monotonic_ms)

    def test_submit_marks_second_pending_block_with_same_coalescing_key_as_coalesced(self) -> None:
        engine = EvidenceFusionEngine()
        first_block = _build_runtime_block(
            block_id=BLOCK_ID_RUNTIME_1,
            configured_label=CONFIGURED_LABEL_FALCON,
            address_value=ADDRESS_NINE,
            observed_at=TIME_OBSERVED_100,
            received_at=TIME_RECEIVED_110,
        )
        second_block = _build_runtime_block(
            block_id=BLOCK_ID_RUNTIME_2,
            configured_label=CONFIGURED_LABEL_FALCON,
            address_value=ADDRESS_NINE,
            observed_at=TIME_OBSERVED_120,
            received_at=TIME_RECEIVED_130,
        )

        first_result = engine.submit_evidence_block(first_block)
        second_result = engine.submit_evidence_block(second_block)

        self.assertFalse(first_result.coalesced)
        self.assertTrue(second_result.coalesced)
        stats = engine.get_runtime_stats()
        self.assertEqual(1, stats.coalesced_blocks)

    def test_submit_does_not_coalesce_pending_blocks_for_different_dimensions(self) -> None:
        engine = EvidenceFusionEngine()
        first_block = _build_runtime_block(
            block_id=BLOCK_ID_RUNTIME_1,
            configured_label=CONFIGURED_LABEL_FALCON,
            address_value=ADDRESS_NINE,
            observed_at=TIME_OBSERVED_100,
            received_at=TIME_RECEIVED_110,
            payload={
                "dimension": DIMENSION_EXISTENCE,
                "assertion": EXISTENCE_PRESENT,
                "polarity": "support",
                "claimStrength": 1.0,
                "specificity": 1.0,
                "directness": 1.0,
                "quality": 1.0,
                "sourceHealth": 1.0,
                "baseReliability": 1.0,
                "independenceGroup": "runtime:f9:existence",
                "reasonCode": "RUNTIME_PRESENT",
            },
        )
        second_block = _build_runtime_block(
            block_id=BLOCK_ID_RUNTIME_2,
            configured_label=CONFIGURED_LABEL_FALCON,
            address_value=ADDRESS_NINE,
            observed_at=TIME_OBSERVED_120,
            received_at=TIME_RECEIVED_130,
            payload={
                "dimension": DIMENSION_COMMUNICATION,
                "assertion": COMMUNICATION_HEALTHY,
                "polarity": "support",
                "claimStrength": 1.0,
                "specificity": 1.0,
                "directness": 1.0,
                "quality": 1.0,
                "sourceHealth": 1.0,
                "baseReliability": 1.0,
                "independenceGroup": "runtime:f9:communication",
                "reasonCode": "RUNTIME_CONTROLLER_COMM_HEALTHY",
            },
        )

        first_result = engine.submit_evidence_block(first_block)
        second_result = engine.submit_evidence_block(second_block)

        self.assertFalse(first_result.coalesced)
        self.assertFalse(second_result.coalesced)

    def test_drain_prefers_source_health_lane_over_runtime_lane(self) -> None:
        engine = EvidenceFusionEngine()
        runtime_block = _build_runtime_block(
            block_id=BLOCK_ID_RUNTIME_1,
            configured_label=CONFIGURED_LABEL_FALCON,
            address_value=ADDRESS_NINE,
            observed_at=TIME_OBSERVED_100,
            received_at=TIME_RECEIVED_110,
        )
        clock_block = _build_clock_block()

        runtime_result = engine.submit_evidence_block(runtime_block)
        clock_result = engine.submit_evidence_block(clock_block)

        self.assertEqual(QUEUE_LANE_PERIODIC_RUNTIME, runtime_result.queue_lane)
        self.assertEqual(QUEUE_LANE_CLOCK_TICK, clock_result.queue_lane)

        drain_result = engine.drain_evaluation_budget(
            TIME_EVAL_500,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_ONE),
        )

        self.assertEqual(1, drain_result.work_items_processed)
        self.assertEqual(1, drain_result.pending_work_items)

    def test_drain_updates_service_counters_for_configured_and_unknown_devices(self) -> None:
        engine = EvidenceFusionEngine()
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
            )
        )
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_2,
                configured_label=None,
                address_value=ADDRESS_TWENTY_FIVE,
                observed_at=TIME_OBSERVED_120,
                received_at=TIME_RECEIVED_130,
            )
        )

        engine.drain_evaluation_budget(
            TIME_EVAL_500,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )
        snapshot = engine.get_current_snapshot()
        stats = snapshot.runtime_stats

        self.assertEqual(1, stats.per_device_service_count[CONFIGURED_LABEL_FALCON.lower()])
        unknown_service_keys = [key for key in stats.per_device_service_count if key.startswith("unknown:")]
        self.assertEqual(1, len(unknown_service_keys))
        unknown_record = next(iter(snapshot.unknown_observed_devices.values()))
        self.assertEqual(TIME_EVAL_500, unknown_record.last_evaluated_at_monotonic_ms)

    def test_clock_driven_decay_reclassifies_without_new_device_block(self) -> None:
        engine = EvidenceFusionEngine()
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
            )
        )

        engine.drain_evaluation_budget(
            TIME_EVAL_300,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )
        state_current = engine.get_current_snapshot().observation_states[BLOCK_ID_RUNTIME_1]
        engine.drain_evaluation_budget(
            TIME_EVAL_800,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )
        state_decaying = engine.get_current_snapshot().observation_states[BLOCK_ID_RUNTIME_1]
        engine.drain_evaluation_budget(
            TIME_EVAL_2500,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )
        state_expired = engine.get_current_snapshot().observation_states[BLOCK_ID_RUNTIME_1]
        engine.drain_evaluation_budget(
            TIME_EVAL_12001,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )
        state_historical = engine.get_current_snapshot().observation_states[BLOCK_ID_RUNTIME_1]

        self.assertEqual(FRESHNESS_STATE_CURRENT, state_current.freshness_state)
        self.assertEqual(FRESHNESS_STATE_DECAYING, state_decaying.freshness_state)
        self.assertLess(state_decaying.current_influence, state_current.current_influence)
        self.assertEqual(FRESHNESS_STATE_EXPIRED, state_expired.freshness_state)
        self.assertEqual(0.0, state_expired.current_influence)
        self.assertEqual(FRESHNESS_STATE_HISTORICAL, state_historical.freshness_state)

    def test_new_source_session_invalidates_prior_session_observation(self) -> None:
        engine = EvidenceFusionEngine()
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
                source_session_id=SOURCE_SESSION_ID_RUNTIME,
            )
        )
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_2,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_140,
                received_at=TIME_RECEIVED_150,
                source_session_id=SOURCE_SESSION_ID_RUNTIME_2,
            )
        )

        engine.drain_evaluation_budget(
            TIME_EVAL_500,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )
        snapshot = engine.get_current_snapshot()

        self.assertEqual(
            FRESHNESS_STATE_HISTORICAL,
            snapshot.observation_states[BLOCK_ID_RUNTIME_1].freshness_state,
        )
        self.assertFalse(snapshot.observation_states[BLOCK_ID_RUNTIME_1].source_session_current)
        self.assertTrue(snapshot.observation_states[BLOCK_ID_RUNTIME_2].source_session_current)
        self.assertEqual(1, snapshot.runtime_stats.source_session_rollovers)

    def test_context_revision_block_invalidates_prior_context_observation(self) -> None:
        engine = EvidenceFusionEngine()
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
                context_revision_id=CONTEXT_REVISION_ID_1,
            )
        )
        engine.submit_evidence_block(
            _build_context_block(
                block_id="context:block:2",
                context_revision_id=CONTEXT_REVISION_ID_2,
                observed_at=TIME_OBSERVED_140,
                received_at=TIME_RECEIVED_150,
            )
        )

        engine.drain_evaluation_budget(
            TIME_EVAL_500,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )
        state = engine.get_current_snapshot().observation_states[BLOCK_ID_RUNTIME_1]

        self.assertEqual(FRESHNESS_STATE_HISTORICAL, state.freshness_state)
        self.assertFalse(state.context_current)
        self.assertEqual(
            CONTEXT_REVISION_ID_2,
            engine.get_current_snapshot().context_revision_id,
        )

    def test_retraction_forces_historical_state(self) -> None:
        engine = EvidenceFusionEngine()
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id=BLOCK_ID_RUNTIME_1,
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
            )
        )
        engine.submit_evidence_block(
            _build_retraction_block(
                block_id="retract:block:1",
                retracted_block_id=BLOCK_ID_RUNTIME_1,
                observed_at=TIME_OBSERVED_140,
                received_at=TIME_RECEIVED_150,
            )
        )

        engine.drain_evaluation_budget(
            TIME_EVAL_500,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )
        state = engine.get_current_snapshot().observation_states[BLOCK_ID_RUNTIME_1]

        self.assertEqual(FRESHNESS_STATE_HISTORICAL, state.freshness_state)
        self.assertTrue(state.retracted)

    def test_correlation_cap_zeroes_current_influence_beyond_policy_limit(self) -> None:
        engine = EvidenceFusionEngine()
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id="corr:block:1",
                configured_label=CONFIGURED_LABEL_FALCON,
                address_value=ADDRESS_NINE,
                observed_at=TIME_OBSERVED_100,
                received_at=TIME_RECEIVED_110,
                correlation_id=CORRELATION_GROUP_SHARED,
            )
        )
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id="corr:block:2",
                configured_label=CONFIGURED_LABEL_SPARK25,
                address_value=ADDRESS_TWENTY_FIVE,
                observed_at=TIME_OBSERVED_120,
                received_at=TIME_RECEIVED_130,
                correlation_id=CORRELATION_GROUP_SHARED,
            )
        )
        engine.submit_evidence_block(
            _build_runtime_block(
                block_id="corr:block:3",
                configured_label=CONFIGURED_LABEL_SPARK7,
                address_value=7,
                observed_at=TIME_OBSERVED_140,
                received_at=TIME_RECEIVED_150,
                correlation_id=CORRELATION_GROUP_SHARED,
            )
        )

        engine.drain_evaluation_budget(
            TIME_EVAL_500,
            EvaluationBudget(max_work_items=MAX_WORK_ITEMS_TEN),
        )
        snapshot = engine.get_current_snapshot()

        self.assertFalse(snapshot.observation_states["corr:block:3"].correlation_capped)
        self.assertFalse(snapshot.observation_states["corr:block:2"].correlation_capped)
        self.assertTrue(snapshot.observation_states["corr:block:1"].correlation_capped)
        self.assertEqual(0.0, snapshot.observation_states["corr:block:1"].current_influence)


if __name__ == "__main__":
    unittest.main()
