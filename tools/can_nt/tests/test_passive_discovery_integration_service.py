from __future__ import annotations

"""
NAME
    test_passive_discovery_integration_service.py - Focused tests for the first passive-discovery integration slice.
"""

import unittest

from tools.can_nt.passive_discovery_integration_service import (
    ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE,
    ENGINE_LABEL_NEW,
    FAULT_SNAPSHOT_KEY_CANDIDATE_COUNT,
    FAULT_SNAPSHOT_KEY_RAN_AT,
    FAULT_SNAPSHOT_KEY_RENDERED_TEXT,
    FAULT_SNAPSHOT_KEY_RESULT,
    FAULT_SNAPSHOT_KEY_ROWS,
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
    build_evidence_fault_snapshot,
    build_interpreted_device_state,
    build_interpreted_evidence_row,
    build_passive_device_detail_snapshot,
    build_passive_visibility_deep_dive_text,
    build_manual_snapshot,
    build_runtime_device_detail_snapshot,
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
from tools.passive_discovery_poc.models import DeviceIdentity, DeviceRecord, FamilyKey, FamilyMetrics, FamilyRecord, NormalizedFrame, RunResult


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

    def test_build_live_passive_result_treats_roborio_periodic_status_as_presence_evidence(self) -> None:
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
        for index in range(25):
            provider.ingest_frame(
                TEST_SOURCE_ID,
                arb_id=int("01011840", 16),
                ts_ms=1000,
                decoded_key="1:1:0",
                label="roborio",
                normalized_frame=NormalizedFrame(
                    timestamp_s=0.006 + (0.020 * float(index)),
                    can_id=int("01011840", 16),
                    dlc=8,
                    data_hex="8101184008000000",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=1,
                    device_type=1,
                    api_class=6,
                    api_index=1,
                    device_id=0,
                    observer_source=TEST_SOURCE_ID,
                ),
            )

        result = build_live_passive_result(provider, profile_devices)
        devices_by_identity = index_run_result_by_identity(result)
        roborio = devices_by_identity[(1, 1, 0)]

        self.assertEqual("observed", roborio.expected_status)
        self.assertGreater(roborio.presence_score, 0)
        self.assertTrue(roborio.evidence_family_keys)

    def test_build_passive_device_detail_snapshot_uses_visibility_fallback_when_no_device_record_exists(self) -> None:
        result = RunResult(
            run_metadata={},
            device_records=(),
            family_records=(),
            unknown_frames=(),
            warnings=(),
        )

        snapshot = build_passive_device_detail_snapshot(
            "FALCON 9",
            passive_result=result,
            visibility_device={
                "metrics": {
                    "observerA": {
                        "lastSeenMs": 9800.0,
                        "framesPerSec": 19.9,
                    }
                }
            },
            now_s=10.0,
        )

        self.assertEqual("0.00", snapshot["presence"])
        self.assertEqual("none", snapshot["presenceStatus"])
        self.assertEqual("0.2s ago", snapshot["presenceAge"])
        self.assertEqual("passiveCan", snapshot["presenceSource"])
        self.assertEqual("0.2s ago", snapshot["lastSeen"])

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

    def test_build_runtime_device_detail_snapshot_exposes_group_scope_and_instantiation(self) -> None:
        snapshot = build_runtime_device_detail_snapshot(
            {
                "activeGroupLabel": "active-group",
                "lifecycleState": "defined",
                "instantiated": False,
                "testable": False,
            },
            now_s=2.0,
        )

        self.assertEqual("yes", snapshot["groupMember"])
        self.assertEqual("no", snapshot["scopeActive"])
        self.assertEqual("no", snapshot["instantiated"])
        self.assertEqual("defined", snapshot["lifecycleState"])

    def test_build_interpreted_device_state_adapts_to_legacy_row_contract(self) -> None:
        state = build_interpreted_device_state(
            label=TEST_SPARK_LABEL,
            presence_entry={
                "bucket": "present",
                "score": 1.0,
                "source": "localSnapshot",
                "updatedAtMs": 1500.0,
                "message": "Runtime snapshot observed device present.",
                "existence": "PRESENT",
                "confidence": "HIGH",
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

        row = state.to_row()

        self.assertEqual(TEST_SPARK_LABEL, state.label)
        self.assertEqual(TEST_SPARK_LABEL, row["label"])
        self.assertEqual(state.existence, row["existence"])
        self.assertEqual(state.presence_text, row["presenceText"])
        self.assertEqual(state.source_scores, row["sourceScores"])

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
                "metadata": {
                    "ctreHttp": {"status": "ok", "summary": "baseUrl=http://172.22.11.2:1250 | devices=3"},
                    "topology": {"status": "ok", "summary": "profile=test_minimal_25_9 | nodes=4 | edges=3"},
                    "consoleLog": {"status": "empty", "summary": "records=0 | warnings=0"},
                },
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
        self.assertIn("deviceType", row)
        self.assertIn("dirty", row)
        self.assertIn("eventLog", row)
        self.assertIn("lastEvaluationAt", row)
        self.assertIn("runStatus=Enrichment: ran 1.0s ago", row["enrichmentText"])
        self.assertIn("ctreHttp=present", row["enrichmentText"])
        self.assertIn("deviceContribution=ctreHttp", row["enrichmentText"])
        self.assertIn(
            "Host enrichment ran 1.0s ago; ctreHttp=ok; topology=ok; consoleLog=empty.",
            row["notesText"],
        )

    def test_build_passive_visibility_deep_dive_text_separates_evidence_and_supporting_families(self) -> None:
        primary_key = FamilyKey(5, 2, 25, 46, 0)
        command_key = FamilyKey(5, 2, 25, 32, 1)
        passive_result = RunResult(
            run_metadata={},
            device_records=(
                DeviceRecord(
                    identity=DeviceIdentity(5, 2, 25, "node.spark25", "rio"),
                    expected_status="observed",
                    manufacturer_name="REV",
                    device_type_name="SPARK MAX",
                    model_name="SPARK MAX",
                    profile_label="SPARKMAX/NEO 25",
                    presence_confidence="HIGH",
                    presence_score=92,
                    inventory_confidence="HIGH",
                    inventory_score=90,
                    health_confidence="MEDIUM",
                    health_score=70,
                    health="ok",
                    evidence_sources=("passive_can", "bringup_profile"),
                    evidence_family_keys=(primary_key, command_key),
                    evidence_family_summaries=("api=46/0 primary_status 40.3Hz",),
                    evidence_gaps=("No fresh heartbeat family.",),
                    notes=(),
                ),
            ),
            family_records=(
                FamilyRecord(
                    key=primary_key,
                    metrics=FamilyMetrics(120, 40.3, 0.0248, 0.001, 1, 0, 1.0, 3.9, True, True, True, False, False, True),
                    role="DEVICE_EMITTED_PRIMARY_STATUS",
                    confidence="HIGH",
                    model_hint="SPARK MAX",
                    observed_can_ids=("0x02042C49",),
                    sample_payloads=("0011",),
                ),
                FamilyRecord(
                    key=command_key,
                    metrics=FamilyMetrics(30, 10.0, 0.1, 0.01, 3, 10, 1.0, 3.9, True, False, False, False, False, False),
                    role="CONTROLLER_EMITTED_COMMAND",
                    confidence="HIGH",
                    model_hint="SPARK MAX",
                    observed_can_ids=("0x02042C50",),
                    sample_payloads=("0022",),
                ),
            ),
            unknown_frames=(),
            warnings=(),
        )

        text = build_passive_visibility_deep_dive_text(
            label="SPARKMAX/NEO 25",
            passive_result=passive_result,
            visibility_device={"metrics": {}},
            visibility_identity_text="MATCHING",
            visibility_last_seen_text="0.1s ago",
            visibility_packet_count_text="150",
            visibility_packet_rate_text="50.3/s",
        )

        self.assertIn("Shared Passive CAN Deep Dive", text)
        self.assertIn("passiveScore=92/100", text)
        self.assertIn("existencePackets=120", text)
        self.assertIn("Evidence Families", text)
        self.assertIn("role=DEVICE_EMITTED_PRIMARY_STATUS", text)
        self.assertIn("countsForPresence=yes", text)
        self.assertIn("Supporting / Reference Families", text)
        self.assertIn("role=CONTROLLER_EMITTED_COMMAND", text)
        self.assertIn("countsForPresence=no", text)
        self.assertIn("No fresh heartbeat family.", text)

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
                "lastSeenMs": 39000.0,
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
        self.assertEqual(2, device_row["totalCount"])
        self.assertEqual("[WARN] SPARK_STATUS_TIMEOUT: device 25 timed out", device_row["summary"])
        self.assertEqual("NEW", device_row["evidenceEngineLabel"])
        self.assertIn("Selected Device Console Stats:", device_row["statsText"])
        self.assertIn("label=SPARKMAX/NEO 25", device_row["statsText"])
        self.assertIn("vendor=rev", device_row["statsText"])
        self.assertIn("deviceType=spark max", device_row["statsText"])
        self.assertIn("total=2", device_row["statsText"])
        self.assertIn("warn=2", device_row["statsText"])
        self.assertEqual("rev_timeout", device_row["topFaultFamily"])
        self.assertEqual("high", device_row["parserConfidence"])
        self.assertEqual("structured", device_row["normalizationStatus"])
        self.assertIn("examples=[WARN] SPARK_STATUS_TIMEOUT: device 25 timed out", device_row["statsText"])
        self.assertEqual(
            ["[ERROR] BUS_FAULT_SUSPECTED: multiple device timeouts"],
            snapshot["system"],
        )
        self.assertTrue(snapshot["systemConflict"])
        self.assertEqual(3, snapshot["stats"]["totalCount"])
        self.assertEqual(2, snapshot["stats"]["deviceEventCount"])
        self.assertEqual(1, snapshot["stats"]["systemEventCount"])
        self.assertIn("General Console Stats:", snapshot["statsText"])
        self.assertIn("total=3", snapshot["statsText"])
        self.assertIn("device=2", snapshot["statsText"])
        self.assertIn("system=1", snapshot["statsText"])
        self.assertIn("warn=2", snapshot["statsText"])
        self.assertIn("error=1", snapshot["statsText"])
        self.assertIn("topFaultFamilies=rev_timeout(2), controller_side_comm_loss(1)", snapshot["statsText"])
        self.assertIn("topVendors=rev(2), unknown(1)", snapshot["statsText"])

    def test_interpreted_row_console_text_includes_general_and_device_console_stats(self) -> None:
        snapshot = build_console_snapshot_from_entries(
            [
                type(
                    "EntryStub",
                    (),
                    {
                        "active": True,
                        "severity": "WARN",
                        "event_type": "TALON_STATUS_SIGNAL_STALE",
                        "last_message": 'CAN message is stale. talon fx 9 ("") Status Signal SupplyVoltage',
                        "device_label": "FALCON 9",
                        "count": 3,
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
        )

        row = build_interpreted_evidence_row(
            label="FALCON 9",
            presence_entry=None,
            passive_device=None,
            visibility_device=None,
            runtime_device=None,
            console_entry=snapshot["devices"]["falcon 9"],
            system_console=snapshot,
            manual_entry=None,
            manual_observation=None,
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=0.0,
            probe_run_count=0,
            now_s=10.0,
        )

        self.assertIn("General Console Stats:", row["consoleText"])
        self.assertIn("Selected Device Console Stats:", row["consoleText"])
        self.assertIn("label=FALCON 9", row["consoleText"])
        self.assertIn("vendor=ctre", row["consoleText"])
        self.assertIn("deviceType=talon fx", row["consoleText"])
        self.assertIn("canId=9", row["consoleText"])
        self.assertIn("total=3", row["consoleText"])
        self.assertIn("warn=3", row["consoleText"])
        self.assertIn("topFaultFamily=ctre_stale_status_signal", row["consoleText"])
        self.assertIn("parserConfidence=high", row["consoleText"])
        self.assertIn("examples=[WARN] TALON_STATUS_SIGNAL_STALE", row["consoleText"])

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

    def test_interpreted_row_promotes_targeted_stale_console_warning_to_failed_and_ignores_stale_auto_rotation(self) -> None:
        passive_device = DeviceRecord(
            identity=DeviceIdentity(manufacturer=4, device_type=2, device_id=9),
            expected_status="observed",
            manufacturer_name="CTRE",
            device_type_name="TalonFX",
            model_name="falcon",
            profile_label="FALCON 9",
            presence_confidence="medium",
            presence_score=78,
            inventory_confidence="medium",
            inventory_score=70,
            health_confidence="limited",
            health_score=65,
            health="limited",
            evidence_sources=("passive_can",),
            evidence_family_keys=(FamilyKey(4, 2, 9, 6, 0),),
            evidence_family_summaries=("api=6/0 primary_status 100.0Hz",),
            evidence_gaps=(),
            notes=(),
        )

        row = build_interpreted_evidence_row(
            label="FALCON 9",
            presence_entry={
                "bucket": "present",
                "score": 1.0,
                "ageText": "1.2s ago",
                "existence": "PRESENT",
                "confidence": "HIGH",
                "source": "localSnapshot",
                "message": "Runtime snapshot indicates device present.",
            },
            passive_device=passive_device,
            visibility_device={
                "metrics": {
                    "observerA": {
                        "msgCount": 269924,
                        "lastSeenMs": 9800.0,
                        "framesPerSec": 0.0,
                    }
                }
            },
            runtime_device={
                "label": "FALCON 9",
                "cmdDuty": 0.0,
                "appliedDuty": 0.0,
                "velRpm": 0.0,
                "positionRot": 0.0,
                "motorCurrentA": 0.0,
                "attachments": [
                    {
                        "type": ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE,
                        "bucket": "present",
                        "score": 100,
                        "maxScore": 100,
                        "updatedAtMs": 1000.0,
                        "status": "ok",
                        "message": "Device present: FALCON 9.",
                    }
                ],
            },
            console_entry={
                "summary": "[WARN] TALON_STATUS_SIGNAL_STALE",
                "events": [
                    '[WARN] TALON_STATUS_SIGNAL_STALE: CAN message is stale, data is valid but old. talon fx 9 ("") Status Signal SupplyVoltage'
                ],
                "hasError": False,
                "hasWarn": True,
            },
            system_console={},
            manual_entry=None,
            manual_observation={
                "autoResult": "rotation_detected",
                "recordedAtEpochSec": 0.0,
                "recordedAt": "11:44:29",
            },
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=0.0,
            probe_run_count=0,
            now_s=232.3,
            visibility_last_seen_text="0.0s",
            visibility_packet_count_text="269924",
            visibility_packet_rate_text="0.0/s",
        )

        self.assertEqual("CONFLICT", row["existence"])
        self.assertEqual("FAILED", row["operability"])
        self.assertEqual("failed", row["state"])
        self.assertEqual("conflict", row["presenceState"])
        self.assertEqual("unknown", row["sourceScores"]["passive"]["state"])
        self.assertEqual("Invalidated by console fault", row["probe"])
        self.assertEqual("--", row["probeScore"])
        self.assertEqual("Historical only", row["manual"])
        self.assertIn("invalidated by fresh device-targeted console fault evidence", row["probeText"])
        self.assertIn("historical only because fresh device-targeted console fault evidence conflicts with it", row["manualText"])
        self.assertEqual("conflict", row["sourceScores"]["probe"]["state"])
        self.assertEqual("conflict", row["sourceScores"]["manual"]["state"])
        self.assertIn("Device-targeted stale/timeout console evidence present.", row["notesText"])
        self.assertIn("Full-probe result was invalidated by fresh device-targeted console fault evidence.", row["notesText"])
        self.assertIn("Manual result is being treated as historical only because fresh device-targeted console fault evidence conflicts with it.", row["notesText"])
        self.assertIn(
            "Fresh targeted console fault evidence conflicts with weak/stale positive presence evidence.",
            row["notesText"],
        )
        self.assertIn("Passive CAN observation is stale or no longer emitting traffic at a non-zero rate.", row["notesText"])

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
                        "lastSeenMs": 39000,
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
                "lastSeenMs": 39000,
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
        self.assertEqual("infrastructure_device", row["deviceType"])
        self.assertEqual("present", row["presenceState"])
        self.assertGreaterEqual(row["presenceScore"], 70)
        self.assertEqual("present", row["sourceScores"]["runtime"]["state"])

    def test_interpreted_row_marks_infrastructure_present_from_runtime_singleton_telemetry_without_last_seen(self) -> None:
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
                "attachments": [{"type": "pdpStatus"}],
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
        self.assertEqual("present", row["presenceState"])
        self.assertEqual("present", row["sourceScores"]["runtime"]["state"])

    def test_interpreted_row_does_not_keep_infrastructure_present_from_stale_runtime_telemetry(self) -> None:
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

        self.assertEqual("UNKNOWN", row["existence"])
        self.assertEqual("unknown", row["state"])
        self.assertEqual("unknown", row["presenceState"])

    def test_interpreted_row_marks_infrastructure_missing_from_fresh_targeted_console_timeout_without_positive_corroboration(self) -> None:
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
                "lastSeenMs": 1000,
            },
            console_entry={
                "summary": "HAL: CAN Receive has Timed Out",
                "hasError": True,
                "hasWarn": False,
                "totalCount": 3,
                "freshness": "fresh",
                "records": [
                    {
                        "scope": "device",
                        "faultFamily": "ctre_timeout",
                        "freshness": "fresh",
                        "totalCount": 3,
                    }
                ],
                "events": [
                    "HAL: CAN Receive has Timed Out",
                ],
            },
            system_console={},
            manual_entry=None,
            manual_observation=None,
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=20.0,
            probe_run_count=1,
            now_s=40.0,
        )

        self.assertEqual("ABSENT", row["existence"])
        self.assertEqual("FAILED", row["operability"])
        self.assertEqual("failed", row["state"])
        self.assertEqual("missing", row["presenceState"])
        self.assertIn(
            "Fresh device-targeted console timeout evidence with no fresh positive corroboration is being treated as missing infrastructure presence.",
            row["notesText"],
        )

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

    def test_build_evidence_fault_snapshot_freezes_rows_and_rendered_result(self) -> None:
        snapshot = build_evidence_fault_snapshot(
            evidence_rows=[
                {
                    "label": "FALCON 9",
                    "existence": "ABSENT",
                    "operability": "FAILED",
                    "identity": "MATCHING",
                    "confidence": "HIGH",
                    "state": "missing",
                    "notesText": "Runtime snapshot did not observe device.",
                }
            ],
            console_snapshot={},
            topology_profile={},
            now_s=10.0,
        )

        self.assertEqual(10.0, snapshot[FAULT_SNAPSHOT_KEY_RAN_AT])
        self.assertEqual(1, snapshot[FAULT_SNAPSHOT_KEY_CANDIDATE_COUNT])
        self.assertEqual("FALCON 9", snapshot[FAULT_SNAPSHOT_KEY_ROWS][0]["label"])
        self.assertEqual(
            ["FALCON 9"],
            snapshot[FAULT_SNAPSHOT_KEY_RESULT]["candidates"][0]["affectedDevices"],
        )
        self.assertIn(
            "single_device_unreachable",
            snapshot[FAULT_SNAPSHOT_KEY_RENDERED_TEXT],
        )

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

    def test_interpreted_row_demotes_local_snapshot_presence_when_manual_motion_and_passive_can_do_not_confirm_motor(self) -> None:
        passive_device = DeviceRecord(
            identity=DeviceIdentity(manufacturer=4, device_type=2, device_id=9),
            expected_status="missing",
            manufacturer_name="CTRE",
            device_type_name="TalonFX",
            model_name="falcon",
            profile_label="FALCON 9",
            presence_confidence="uncertain",
            presence_score=25,
            inventory_confidence="low",
            inventory_score=25,
            health_confidence="low",
            health_score=25,
            health="unknown",
            evidence_sources=("passive_can",),
            evidence_family_keys=(),
            evidence_family_summaries=(),
            evidence_gaps=(),
            notes=(),
        )

        row = build_interpreted_evidence_row(
            label="FALCON 9",
            presence_entry={
                "bucket": "present",
                "score": 1.0,
                "ageText": "0.0s ago",
                "existence": "PRESENT",
                "confidence": "HIGH",
                "source": "localSnapshot",
            },
            passive_device=passive_device,
            visibility_device={
                "metrics": {
                    "src0": {
                        "lastSeenMs": 100000.0,
                        "packets": 4300,
                        "framesPerSec": 99.9,
                    }
                }
            },
            runtime_device={
                "cmdDuty": 0.0,
                "appliedDuty": 0.0,
                "velRpm": 0.0,
                "motorCurrentA": 0.0,
                "positionRot": 0.0,
                "attachments": [
                    {
                        "type": "presenceCheck",
                        "bucket": "present",
                        "score": 1.0,
                        "source": "localSnapshot",
                    }
                ],
            },
            console_entry=None,
            system_console={},
            manual_entry=None,
            manual_observation={
                "autoResult": "no_rotation_detected",
                "recordedAt": "18:51:30",
                "recordedAtEpochSec": 90.0,
                "cmdDuty": 0.24,
                "appliedDuty": 0.0,
                "velRpm": 0.0,
                "positionRot": 0.0,
                "positionDeltaRot": 0.0,
                "motorCurrentA": 0.0,
            },
            manual_motion=None,
            probe_pending=False,
            last_probe_completed_at=0.0,
            probe_run_count=0,
            now_s=100.0,
        )

        self.assertEqual("CONFLICT", row["existence"])
        self.assertEqual("FAILED", row["operability"])
        self.assertEqual("LOW", row["confidence"])
        self.assertEqual("failed", row["state"])
        self.assertTrue(row["conflicted"])
        self.assertIn(
            "Runtime scope snapshot says present, but recent motion check and passive CAN did not confirm the motor as physically present.",
            row["notesText"],
        )


if __name__ == "__main__":
    unittest.main()
