from __future__ import annotations

"""
NAME
    test_passive_discovery_integration_service.py - Focused tests for the first passive-discovery integration slice.
"""

import unittest

from tools.can_nt.passive_discovery_integration_service import (
    ENGINE_LABEL_NEW,
    SECTION_CONSOLE,
    SECTION_ENRICHMENT,
    SECTION_INTERPRETATION,
    SECTION_MANUAL,
    SECTION_PASSIVE,
    SECTION_PRESENCE_CHECK,
    SECTION_PROFILE_INVENTORY,
    SECTION_PROBE,
    SECTION_TOPOLOGY_VIEW,
    build_enrichment_run_snapshot,
    build_console_snapshot_from_entries,
    build_interpreted_evidence_row,
    build_manual_snapshot,
    build_runtime_probe_snapshot,
    build_runtime_presence_catalog,
    build_live_passive_result,
    default_evidence_engine_status,
    evidence_engine_banner_text,
    evidence_overall_title,
    index_run_result_by_identity,
    load_profile_device_catalog,
    normalize_evidence_engine_status,
)
from tools.can_nt.visibility_provider import SourceInfo, VisibilityProvider
from tools.passive_discovery_poc.models import DeviceIdentity, DeviceRecord, FamilyKey, NormalizedFrame


TEST_SOURCE_ID = "src0"
TEST_SOURCE_LABEL = "analyzer0"
TEST_TIMEOUT_MS = 1000
TEST_SPARK_IDENTITY = (5, 2, 25)
TEST_SPARK_LABEL = "SPARKMAX/NEO 25"


class PassiveDiscoveryIntegrationServiceTests(unittest.TestCase):
    """
    NAME
        PassiveDiscoveryIntegrationServiceTests - Validate the explicit migration boundary metadata.
    """

    def test_default_evidence_engine_status_marks_whole_surface_new(self) -> None:
        status = default_evidence_engine_status()

        self.assertEqual(ENGINE_LABEL_NEW, status["engineLabel"])
        self.assertEqual(ENGINE_LABEL_NEW, status["sections"][SECTION_PROFILE_INVENTORY])
        self.assertEqual(ENGINE_LABEL_NEW, status["sections"][SECTION_PRESENCE_CHECK])
        self.assertEqual(ENGINE_LABEL_NEW, status["sections"][SECTION_PASSIVE])
        self.assertEqual(ENGINE_LABEL_NEW, status["sections"][SECTION_CONSOLE])
        self.assertEqual(ENGINE_LABEL_NEW, status["sections"][SECTION_PROBE])
        self.assertEqual(ENGINE_LABEL_NEW, status["sections"][SECTION_MANUAL])
        self.assertEqual(ENGINE_LABEL_NEW, status["sections"][SECTION_ENRICHMENT])
        self.assertEqual(ENGINE_LABEL_NEW, status["sections"][SECTION_TOPOLOGY_VIEW])
        self.assertEqual(ENGINE_LABEL_NEW, status["sections"][SECTION_INTERPRETATION])

    def test_evidence_engine_banner_text_lists_section_ownership(self) -> None:
        banner = evidence_engine_banner_text(default_evidence_engine_status())

        self.assertIn("Evidence Engine: NEW", banner)
        self.assertIn("profileInventory=NEW", banner)
        self.assertIn("presenceCheck=NEW", banner)
        self.assertIn("passive=NEW", banner)
        self.assertIn("console=NEW", banner)
        self.assertIn("probe=NEW", banner)
        self.assertIn("manual=NEW", banner)
        self.assertIn("enrichment=NEW", banner)
        self.assertIn("topologyView=NEW", banner)
        self.assertIn("interpretation=NEW", banner)

    def test_evidence_overall_title_uses_overall_engine_label_not_section_label(self) -> None:
        status = default_evidence_engine_status()

        title = evidence_overall_title("Device Evidence", status)

        self.assertEqual("Device Evidence [NEW]", title)

    def test_normalize_evidence_engine_status_promotes_all_new_sections(self) -> None:
        status = {
            "engineLabel": "MIXED",
            "sections": {
                "profileInventory": "NEW",
                "presenceCheck": "NEW",
                "passive": "NEW",
                "console": "NEW",
                "probe": "NEW",
                "manual": "NEW",
                "enrichment": "NEW",
                "topologyView": "NEW",
                "interpretation": "NEW",
            },
        }

        normalized = normalize_evidence_engine_status(status)

        self.assertEqual("NEW", normalized["engineLabel"])
        self.assertEqual("passive_discovery_poc", normalized["engineId"])
        self.assertEqual("new_only", normalized["rolloutMode"])

    def test_load_profile_device_catalog_uses_passive_discovery_profile_loader(self) -> None:
        catalog = load_profile_device_catalog("test_minimal_25_9")

        self.assertIn("falcon 9", catalog)
        self.assertIn("sparkmax/neo 25", catalog)
        self.assertEqual("FALCON 9", catalog["falcon 9"]["label"])
        self.assertEqual("SPARKMAX/NEO 25", catalog["sparkmax/neo 25"]["label"])
        self.assertEqual(ENGINE_LABEL_NEW, catalog["falcon 9"]["evidenceEngineLabel"])

    def test_build_live_passive_result_analyzes_recent_visibility_frames(self) -> None:
        provider = VisibilityProvider(timeout_ms=TEST_TIMEOUT_MS)
        provider.set_sources(
            [
                SourceInfo(
                    source_id=TEST_SOURCE_ID,
                    label=TEST_SOURCE_LABEL,
                    available=True,
                    timeout_ms=TEST_TIMEOUT_MS,
                )
            ]
        )
        profile_devices = load_profile_device_catalog("test_minimal_25_9")
        for timestamp_s, api_class, api_index, payload in (
            (1.00, 46, 0, "0011223344556677"),
            (1.02, 46, 0, "1111223344556677"),
            (1.10, 46, 1, "8899aabbccddeeff"),
            (1.35, 46, 1, "8899aabbccddee00"),
            (1.00, 47, 0, "0102030405060708"),
            (1.95, 47, 0, "0102030405060709"),
        ):
            provider.ingest_frame(
                TEST_SOURCE_ID,
                arb_id=0,
                ts_ms=1000,
                decoded_key="5:2:25",
                label=TEST_SPARK_LABEL,
                normalized_frame=NormalizedFrame(
                    timestamp_s=timestamp_s,
                    can_id=0,
                    dlc=8,
                    data_hex=payload,
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=TEST_SPARK_IDENTITY[0],
                    device_type=TEST_SPARK_IDENTITY[1],
                    api_class=api_class,
                    api_index=api_index,
                    device_id=TEST_SPARK_IDENTITY[2],
                    observer_source=TEST_SOURCE_ID,
                ),
            )

        result = build_live_passive_result(provider, profile_devices)
        devices_by_identity = index_run_result_by_identity(result)
        spark = devices_by_identity[TEST_SPARK_IDENTITY]

        self.assertEqual("observed", spark.expected_status)
        self.assertEqual("high", spark.presence_confidence)
        self.assertGreaterEqual(spark.presence_score, 90)

    def test_build_runtime_presence_catalog_normalizes_presence_attachment(self) -> None:
        profile_devices = load_profile_device_catalog("test_minimal_25_9")
        runtime_devices = {
            "sparkmax/neo 25": {
                "label": TEST_SPARK_LABEL,
                "presenceConfidence": 1.0,
                "attachments": [
                    {
                        "type": "presenceCheck",
                        "bucket": "present",
                        "source": "localSnapshot",
                        "updatedAtMs": 1500.0,
                        "message": "device visible in local robot snapshot",
                    }
                ],
            }
        }

        catalog = build_runtime_presence_catalog(runtime_devices, profile_devices, now_s=2.0)
        spark = catalog["sparkmax/neo 25"]

        self.assertEqual("present", spark["bucket"])
        self.assertEqual("PRESENT", spark["existence"])
        self.assertEqual("HIGH", spark["confidence"])
        self.assertEqual("localSnapshot", spark["source"])
        self.assertEqual("0.5s ago", spark["ageText"])

    def test_build_enrichment_run_snapshot_collects_topology_and_marks_missing_live_sources(self) -> None:
        profile_devices = load_profile_device_catalog("test_minimal_25_9")

        snapshot = build_enrichment_run_snapshot(
            profile_devices=profile_devices,
            profile_name="test_minimal_25_9",
            rio_host="",
            output_log_text="",
            now_s=10.0,
        )

        self.assertIn("devices", snapshot)
        self.assertIn("metadata", snapshot)
        self.assertEqual("ok", snapshot["metadata"]["topology"]["status"])
        self.assertEqual("unavailable", snapshot["metadata"]["ctreHttp"]["status"])
        self.assertEqual("empty", snapshot["metadata"]["consoleLog"]["status"])

    def test_build_interpreted_evidence_row_presence_text_calls_out_runtime_scope_lens(self) -> None:
        row = build_interpreted_evidence_row(
            label=TEST_SPARK_LABEL,
            presence_entry={
                "bucket": "absent",
                "score": 0.0,
                "source": "localSnapshot",
                "updatedAtMs": 1500.0,
                "message": "Runtime snapshot did not observe device present.",
                "existence": "ABSENT",
                "confidence": "LOW",
                "ageText": "0.5s ago",
            },
            passive_device=None,
            visibility_device=None,
            runtime_device=None,
            console_entry=None,
            system_console={},
            manual_entry=None,
            manual_observation=None,
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=0.0,
            probe_run_count=0,
            now_s=2.0,
        )

        self.assertIn(
            "Lens=robot-local runtime snapshot; result applies only to the current runtime/test scope.",
            row["presenceText"],
        )
        self.assertIn("bucket=absent", row["presenceText"])

    def test_build_interpreted_evidence_row_uses_ctre_enrichment_for_corroboration(self) -> None:
        row = build_interpreted_evidence_row(
            label="FALCON 9",
            presence_entry=None,
            passive_device=None,
            enrichment_snapshot={
                "ranAtEpochSec": 1.0,
                "devices": {
                    "falcon 9": {
                        "ctre": {
                            "model": "Talon FX",
                            "firmware": "1.2.3",
                            "faultsTrue": [],
                            "stickyFaultsTrue": [],
                        }
                    }
                },
                "metadata": {},
                "ageText": "0.0s ago",
            },
            visibility_device=None,
            runtime_device=None,
            console_entry=None,
            system_console={},
            manual_entry=None,
            manual_observation=None,
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=0.0,
            probe_run_count=0,
            now_s=2.0,
        )

        self.assertEqual("PRESENT", row["existence"])
        self.assertEqual("MATCHING", row["identity"])
        self.assertIn("runStatus=Enrichment: ran 1.0s ago", row["enrichmentText"])
        self.assertIn("ctreHttp=present", row["enrichmentText"])
        self.assertIn("deviceContribution=ctreHttp", row["enrichmentText"])

    def test_build_runtime_probe_snapshot_formats_cached_probe_attachment(self) -> None:
        runtime_device = {
            "instantiated": True,
            "attachments": [
                {
                    "type": "activePresenceProbe",
                    "bucket": "present",
                    "score": 90,
                    "maxScore": 100,
                    "updatedAtMs": 1500.0,
                    "failedChecks": ["STATUS_REFRESH_OK=false"],
                    "warnings": [],
                    "errors": [],
                    "message": "Device present: FALCON 9.",
                }
            ],
        }

        snapshot = build_runtime_probe_snapshot(
            runtime_device,
            probe_pending=False,
            last_probe_completed_at=1.0,
            probe_run_count=1,
            now_s=40.0,
        )

        self.assertEqual("present", snapshot["bucket"])
        self.assertEqual("present*", snapshot["summary"])
        self.assertEqual("90/100", snapshot["scoreText"])
        self.assertIn("failed: STATUS_REFRESH_OK=false", snapshot["text"])

    def test_build_runtime_probe_snapshot_marks_infrastructure_device_as_out_of_scope(self) -> None:
        snapshot = build_runtime_probe_snapshot(
            None,
            label="pdp",
            probe_pending=False,
            last_probe_completed_at=20.0,
            probe_run_count=1,
            now_s=40.0,
        )

        self.assertEqual("unknown", snapshot["bucket"])
        self.assertIn("Not probed in current motion-test scope.", snapshot["text"])
        self.assertIn("Infrastructure device; evaluated from passive/runtime evidence instead.", snapshot["text"])

    def test_build_runtime_probe_snapshot_uses_runtime_infrastructure_detail_when_singleton_telemetry_exists(self) -> None:
        snapshot = build_runtime_probe_snapshot(
            {
                "instantiated": True,
                "busV": 12.3,
                "totalCurrentA": 1.5,
                "lifecycleState": "instantiated-present",
            },
            label="pdp",
            probe_pending=False,
            last_probe_completed_at=20.0,
            probe_run_count=1,
            now_s=40.0,
        )

        self.assertEqual("unknown", snapshot["bucket"])
        self.assertIn("Not probed in current motion-test scope.", snapshot["text"])
        self.assertIn("using singleton runtime telemetry", snapshot["text"])

    def test_build_manual_snapshot_formats_auto_rotation_observation(self) -> None:
        snapshot = build_manual_snapshot(
            manual_entry=None,
            manual_observation={
                "autoResult": "rotation_detected",
                "recordedAt": "11:02:29",
                "recordedAtEpochSec": 90.0,
                "cmdDuty": 0.25,
                "appliedDuty": 0.24,
                "velRpm": 120.0,
                "positionRot": 2.0,
                "positionDeltaRot": 0.5,
                "motorCurrentA": 8.0,
            },
            manual_motion=None,
            runtime_values={},
            now_s=100.0,
        )

        self.assertEqual("Rotation detected", snapshot["summary"])
        self.assertIn("autoResult=Rotation detected", snapshot["text"])

    def test_build_console_snapshot_from_entries_normalizes_device_and_system_rows(self) -> None:
        entries = [
            type(
                "EntryStub",
                (),
                {
                    "active": True,
                    "severity": "WARN",
                    "event_type": "SPARK_STATUS_TIMEOUT",
                    "last_message": "device 25 timed out",
                    "device_label": "SPARKMAX/NEO 25",
                    "count": 2,
                },
            )(),
            type(
                "EntryStub",
                (),
                {
                    "active": True,
                    "severity": "ERROR",
                    "event_type": "BUS_FAULT_SUSPECTED",
                    "last_message": "multiple device timeouts",
                    "device_label": "",
                    "count": 1,
                },
            )(),
        ]

        snapshot = build_console_snapshot_from_entries(entries)

        device_row = snapshot["devices"]["sparkmax/neo 25"]
        self.assertTrue(device_row["hasWarn"])
        self.assertEqual("[WARN] SPARK_STATUS_TIMEOUT: device 25 timed out", device_row["summary"])
        self.assertEqual("NEW", device_row["evidenceEngineLabel"])
        self.assertEqual(
            ["[ERROR] BUS_FAULT_SUSPECTED: multiple device timeouts"],
            snapshot["system"],
        )
        self.assertTrue(snapshot["systemConflict"])

    def test_interpreted_row_uses_strong_passive_status_when_runtime_presence_is_absent(self) -> None:
        passive_device = DeviceRecord(
            identity=DeviceIdentity(manufacturer=4, device_type=8, device_id=20),
            expected_status="observed",
            manufacturer_name="CTRE",
            device_type_name="PDP",
            model_name="pdp",
            profile_label="pdp",
            presence_confidence="medium",
            presence_score=78,
            inventory_confidence="medium",
            inventory_score=70,
            health_confidence="limited",
            health_score=65,
            health="limited",
            evidence_sources=("passive_can",),
            evidence_family_keys=(FamilyKey(4, 8, 20, 5, 13),),
            evidence_family_summaries=("api=5/13 primary_status 49.9Hz",),
            evidence_gaps=(),
            notes=(),
        )

        row = build_interpreted_evidence_row(
            label="pdp",
            presence_entry={
                "bucket": "absent",
                "score": 0.0,
                "ageText": "1.0s ago",
                "existence": "ABSENT",
                "confidence": "MEDIUM",
            },
            passive_device=passive_device,
            visibility_device=None,
            runtime_device=None,
            console_entry=None,
            system_console={},
            manual_entry=None,
            manual_observation=None,
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=0.0,
            probe_run_count=0,
            now_s=10.0,
        )

        self.assertEqual("PRESENT", row["existence"])
        self.assertEqual("MEDIUM", row["confidence"])
        self.assertEqual("degraded", row["state"])
        self.assertFalse(row["conflicted"])
        self.assertIn(
            "Infrastructure device observed by passive CAN even though the current motion-test scope did not include it.",
            row["notesText"],
        )

    def test_interpreted_row_does_not_mark_roborio_missing_only_from_scope_absence(self) -> None:
        row = build_interpreted_evidence_row(
            label="roborio",
            presence_entry={
                "bucket": "absent",
                "score": 0.0,
                "ageText": "1.0s ago",
                "existence": "ABSENT",
                "confidence": "MEDIUM",
            },
            passive_device=None,
            visibility_device=None,
            runtime_device=None,
            console_entry=None,
            system_console={},
            manual_entry=None,
            manual_observation=None,
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=20.0,
            probe_run_count=1,
            now_s=40.0,
        )

        self.assertEqual("UNKNOWN", row["existence"])
        self.assertEqual("unknown", row["state"])
        self.assertIn(
            "Infrastructure device is outside the current motion-test scope",
            row["notesText"],
        )

    def test_interpreted_row_marks_infrastructure_present_from_visibility_metrics(self) -> None:
        row = build_interpreted_evidence_row(
            label="roborio",
            presence_entry={
                "bucket": "absent",
                "score": 0.0,
                "ageText": "1.0s ago",
                "existence": "ABSENT",
                "confidence": "MEDIUM",
            },
            passive_device=None,
            visibility_device={
                "label": "roborio",
                "visibility": {"observerA": None},
                "metrics": {
                    "observerA": {
                        "msgCount": 5518,
                        "lastSeenMs": 1000,
                        "framesPerSec": 333.3,
                    }
                },
            },
            runtime_device=None,
            console_entry=None,
            system_console={},
            manual_entry=None,
            manual_observation=None,
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=20.0,
            probe_run_count=1,
            now_s=40.0,
            visibility_last_seen_text="0.0s",
            visibility_packet_count_text="5518",
            visibility_packet_rate_text="333.3/s",
        )

        self.assertEqual("PRESENT", row["existence"])
        self.assertEqual("degraded", row["state"])
        self.assertIn("lastSeen=0.0s", row["passive"])
        self.assertIn(
            "Infrastructure device observed by passive CAN",
            row["notesText"],
        )

    def test_interpreted_row_marks_infrastructure_present_from_runtime_singleton_telemetry(self) -> None:
        row = build_interpreted_evidence_row(
            label="pdp",
            presence_entry={
                "bucket": "absent",
                "score": 0.0,
                "ageText": "1.0s ago",
                "existence": "ABSENT",
                "confidence": "MEDIUM",
            },
            passive_device=None,
            visibility_device=None,
            runtime_device={
                "instantiated": True,
                "lifecycleState": "instantiated-present",
                "busV": 12.4,
                "totalCurrentA": 1.2,
                "lastSeenMs": 1000,
            },
            console_entry=None,
            system_console={},
            manual_entry=None,
            manual_observation=None,
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=20.0,
            probe_run_count=1,
            now_s=40.0,
        )

        self.assertEqual("PRESENT", row["existence"])
        self.assertEqual("degraded", row["state"])
        self.assertEqual("MEDIUM", row["confidence"])
        self.assertIn("singleton runtime telemetry is present", row["notesText"])

    def test_interpreted_row_keeps_infrastructure_unknown_when_passive_profile_row_is_missing_without_packets(self) -> None:
        passive_device = DeviceRecord(
            identity=DeviceIdentity(manufacturer=1, device_type=1, device_id=0),
            expected_status="missing",
            manufacturer_name="NI",
            device_type_name="Robot Controller",
            model_name="roborio",
            profile_label="roborio",
            presence_confidence="none",
            presence_score=0,
            inventory_confidence="low",
            inventory_score=0,
            health_confidence="low",
            health_score=0,
            health="unknown",
            evidence_sources=(),
            evidence_family_keys=(),
            evidence_family_summaries=(),
            evidence_gaps=(),
            notes=(),
        )

        row = build_interpreted_evidence_row(
            label="roborio",
            presence_entry={
                "bucket": "absent",
                "score": 0.0,
                "ageText": "1.0s ago",
                "existence": "ABSENT",
                "confidence": "MEDIUM",
            },
            passive_device=passive_device,
            visibility_device=None,
            runtime_device=None,
            console_entry=None,
            system_console={},
            manual_entry=None,
            manual_observation=None,
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=20.0,
            probe_run_count=1,
            now_s=40.0,
        )

        self.assertEqual("UNKNOWN", row["existence"])
        self.assertEqual("unknown", row["state"])
        self.assertEqual("LOW", row["confidence"])

    def test_interpreted_row_marks_no_rotation_motor_failure_as_failed_state(self) -> None:
        row = build_interpreted_evidence_row(
            label="FALCON 9",
            presence_entry={
                "bucket": "present",
                "score": 1.0,
                "ageText": "0.0s ago",
                "existence": "PRESENT",
                "confidence": "HIGH",
            },
            passive_device=None,
            visibility_device=None,
            runtime_device={
                "cmdDuty": 0.25,
                "appliedDuty": 0.0,
                "velRpm": 0.7,
                "motorCurrentA": 0.0,
                "positionRot": 2531.01,
            },
            console_entry={
                "hasWarn": True,
                "hasError": False,
                "events": ["[WARN] TALON_STATUS_SIGNAL_STALE: tCAN message is stale"],
                "summary": "[WARN] TALON_STATUS_SIGNAL_STALE: tCAN message is stale",
            },
            system_console={},
            manual_entry=None,
            manual_observation={
                "autoResult": "no_rotation_detected",
                "recordedAt": "19:54:49",
                "recordedAtEpochSec": 90.0,
                "cmdDuty": 0.25,
                "appliedDuty": 0.0,
                "velRpm": 0.7,
                "positionRot": 2531.01,
                "positionDeltaRot": 0.0,
                "motorCurrentA": 0.0,
            },
            manual_motion={
                "startedAt": 99.0,
                "duty": 0.25,
                "sawMotion": False,
                "startPositionRot": 2531.01,
            },
            probe_pending=False,
            last_probe_completed_at=0.0,
            probe_run_count=0,
            now_s=100.0,
        )

        self.assertEqual("FAILED", row["operability"])
        self.assertEqual("failed", row["state"])
        self.assertIn(
            "Motor commanded with little current and no motion; possible electrical/output-path issue.",
            row["notesText"],
        )


if __name__ == "__main__":
    unittest.main()
