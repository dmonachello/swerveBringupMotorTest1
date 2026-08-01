from __future__ import annotations

from dataclasses import replace
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.passive_discovery_poc.adapters import apply_discovery_to_devices, update_or_create_device
from tools.passive_discovery_poc.capture import observe_rev_serial_session, observe_slcan_session
from tools.passive_discovery_poc.discovery import analyze_capture, analyze_frames
from tools.passive_discovery_poc.enrich_ctre import collect_ctre_enrichment
from tools.passive_discovery_poc.enrichment import enrich_console_log, enrich_topology
from tools.passive_discovery_poc.json_api import result_from_json_dict, result_to_json_dict
from tools.passive_discovery_poc.models import AdapterContext
from tools.passive_discovery_poc.profile import apply_profile_labels, compare_profile, load_profile
from tools.passive_discovery_poc.render import render_summary_table
from tools.passive_discovery_poc.sources import (
    LiveFrameSourcePlugin,
    RecordedEnrichmentSourcePlugin,
    RecordedFrameSourcePlugin,
    default_source_registry,
)


PROFILE_PATH = "src/main/deploy/bringup_system.json"
PROFILE_NAME = "test_minimal_25_9"
FIXTURE_USB_CAP_8 = "tools/vendor_diag/usbCap8_socketcan.pcapng"

TEXT_GOLDEN_FRAME_A = "(1.000000) slcan0 0205B819#00008E0600188000 R"
TEXT_GOLDEN_FRAME_B = "(1.020000) slcan0 0205B819#00008E0600188000 R"
TEXT_GOLDEN_FRAME_C = "(1.250000) slcan0 000502C0#01 R"
FAKE_CTRE_ENRICHMENT = {
    (4, 2, 9): {"model": "Talon FX", "name": "Talon FX (Device ID 9)"},
    (4, 8, 20): {"model": "PDP", "name": "PDP (Device ID 20)"},
}


class _FakeCanMessage:
    def __init__(self, timestamp, arbitration_id, data, is_extended_id=True, is_remote_frame=False):
        self.timestamp = timestamp
        self.arbitration_id = arbitration_id
        self.data = data
        self.is_extended_id = is_extended_id
        self.is_remote_frame = is_remote_frame


class _FakeBus:
    def __init__(self, messages):
        self._messages = list(messages)
        self._index = 0

    def recv(self, timeout=None):
        _ = timeout
        if self._index >= len(self._messages):
            return None
        value = self._messages[self._index]
        self._index += 1
        return value

    def shutdown(self):
        return None


class _FakeSerialHandle:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self._index = 0

    def read(self, size):
        _ = size
        if self._index >= len(self._chunks):
            return b""
        value = self._chunks[self._index]
        self._index += 1
        return value

    def close(self):
        return None


class PassiveDiscoveryPublicApiTests(unittest.TestCase):
    """
    NAME
        PassiveDiscoveryPublicApiTests - Validate the library-shaped public API.
    """

    def test_json_round_trip_returns_payload_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mini.log"
            path.write_text(
                "\n".join([TEXT_GOLDEN_FRAME_A, TEXT_GOLDEN_FRAME_B, TEXT_GOLDEN_FRAME_C]) + "\n",
                encoding="utf-8",
            )
            result = analyze_capture(str(path))
        payload = result_to_json_dict(result)
        restored = result_from_json_dict(payload)
        self.assertEqual(payload["devices"][0]["presence_score"], restored["devices"][0]["presence_score"])
        self.assertEqual(payload["families"][0]["role"], restored["families"][0]["role"])

    def test_default_source_registry_lists_current_builtin_plugins(self) -> None:
        registry = default_source_registry()
        plugin_ids = [info.plugin_id for info in registry.list_plugins()]
        self.assertIn("pcapng", plugin_ids)
        self.assertIn("candump", plugin_ids)
        self.assertIn("capture_auto", plugin_ids)
        self.assertIn("live_slcan", plugin_ids)
        self.assertIn("live_rev_serial", plugin_ids)
        self.assertIn("ctre_http", plugin_ids)
        self.assertIn("profile", plugin_ids)
        self.assertIn("topology", plugin_ids)
        self.assertIn("rio_console_log", plugin_ids)
        self.assertIsInstance(registry.get("pcapng"), RecordedFrameSourcePlugin)
        self.assertIsInstance(registry.get("live_slcan"), LiveFrameSourcePlugin)
        self.assertIsInstance(registry.get("profile"), RecordedEnrichmentSourcePlugin)

    def test_compare_profile_rebuilds_result_with_expected_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mini.log"
            path.write_text(TEXT_GOLDEN_FRAME_A + "\n", encoding="utf-8")
            result = analyze_capture(str(path))
        compared = compare_profile(result, profile_path=PROFILE_PATH, profile_name=PROFILE_NAME)
        self.assertEqual(PROFILE_NAME, compared.run_metadata["profileName"])
        self.assertTrue(any(device.expected_status == "missing" for device in compared.device_records))

    def test_adapter_updates_or_creates_device_object_with_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mini.log"
            path.write_text(TEXT_GOLDEN_FRAME_A + "\n", encoding="utf-8")
            result = analyze_capture(str(path))
        discovered = result.device_records[0]
        context = AdapterContext(source_name="test_suite", attachment_type="passiveDiscovery")
        created = update_or_create_device(None, discovered, context=context)
        self.assertEqual(discovered.identity.device_id, created["canId"])
        self.assertTrue(created["attachments"])
        self.assertEqual("passiveDiscovery", created["attachments"][0]["type"])
        updated_map = apply_discovery_to_devices({}, result, context=context)
        self.assertGreaterEqual(len(updated_map), 1)

    def test_live_session_emits_snapshot_and_callbacks(self) -> None:
        snapshots = []
        frames_seen = []
        fake_can = types.SimpleNamespace(
            Bus=lambda interface, channel, bitrate: _FakeBus(
                [
                    _FakeCanMessage(1.0, int("0205B819", 16), bytes.fromhex("00008E0600188000")),
                    _FakeCanMessage(1.1, int("02042C49", 16), bytes.fromhex("0000006000000000")),
                ]
            )
        )
        with patch.dict("sys.modules", {"can": fake_can}):
            session = observe_slcan_session(
                channel="COM3",
                duration_sec=0.02,
            )
            session.subscribe(
                on_frame=lambda frame: frames_seen.append(frame),
                on_snapshot=lambda snapshot: snapshots.append(snapshot),
            )
            session.start()
            session.wait(timeout=0.5)
            final_snapshot = session.snapshot()
        self.assertGreaterEqual(len(frames_seen), 2)
        self.assertTrue(snapshots)
        self.assertGreaterEqual(len(final_snapshot.device_records), 1)

    def test_profile_source_plugin_collects_expected_rows(self) -> None:
        registry = default_source_registry()
        plugin = registry.get("profile")
        self.assertIsInstance(plugin, RecordedEnrichmentSourcePlugin)
        record = plugin.collect({"profile_path": PROFILE_PATH, "profile_name": PROFILE_NAME})
        self.assertEqual(PROFILE_NAME, record.metadata["profileName"])
        self.assertIn((4, 2, 9), record.expected_rows)

    def test_topology_source_plugin_collects_profile_topology_rows(self) -> None:
        record = enrich_topology(PROFILE_PATH, PROFILE_NAME)
        self.assertEqual("topology", record.plugin_id)
        self.assertGreater(record.metadata["nodeCount"], 0)
        self.assertGreater(record.metadata["edgeCount"], 0)
        self.assertTrue(any(row.get("kind") == "topology_node" for row in record.evidence_records))

    def test_console_log_enrichment_resolves_profile_device_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "console.log"
            path.write_text("[Spark Max] IDs: 25, timed out while waiting for Period Status 0\n", encoding="utf-8")
            record = enrich_console_log(
                str(path),
                profile_path=PROFILE_PATH,
                profile_name=PROFILE_NAME,
            )
        self.assertEqual("rio_console_log", record.plugin_id)
        self.assertEqual(1, len(record.evidence_records))
        evidence = record.evidence_records[0]
        self.assertEqual("SPARK_STATUS_TIMEOUT", evidence["parsedEvidenceType"])
        self.assertEqual(25, evidence["candidateDeviceId"])
        self.assertEqual("SPARKMAX/NEO 25", evidence["candidateProfileNode"])
        self.assertEqual(5, evidence["candidateDeviceIdentity"]["manufacturer"])

    def test_render_summary_table_shows_ctre_http_source_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mini.log"
            path.write_text(TEXT_GOLDEN_FRAME_A + "\n", encoding="utf-8")
            result = analyze_capture(str(path))
        device = replace(result.device_records[0], evidence_sources=("passive_can", "ctre_http"))
        table = render_summary_table(replace(result, device_records=(device, *result.device_records[1:])))
        self.assertIn("sources", table)
        self.assertIn("ctre_http", table)

    def test_render_summary_table_shows_scores_and_sorts_highest_first(self) -> None:
        result = analyze_capture(FIXTURE_USB_CAP_8)
        table = render_summary_table(result)
        self.assertIn("presenceScore", table)
        self.assertIn("healthScore", table)
        self.assertIn("inventoryScore", table)
        lines = table.splitlines()
        data_lines = lines[2:]
        self.assertTrue(data_lines)
        self.assertIn("95", data_lines[0])
        self.assertNotIn("roborio", data_lines[0].lower())

    def test_apply_profile_labels_maps_exact_identity_without_changing_expected_status(self) -> None:
        result = analyze_capture(FIXTURE_USB_CAP_8)
        _resolved_profile, expected_rows = load_profile(PROFILE_PATH, PROFILE_NAME)
        labeled = apply_profile_labels(result, expected_rows=expected_rows)
        falcon = next(
            device
            for device in labeled.device_records
            if (
                device.identity.manufacturer,
                device.identity.device_type,
                device.identity.device_id,
            )
            == (4, 2, 9)
        )
        self.assertEqual("FALCON 9", falcon.profile_label)
        self.assertEqual("unexpected", falcon.expected_status)

    def test_profile_plus_ctre_only_marks_expected_ctre_device_observed_not_missing(self) -> None:
        _resolved_profile, expected_rows = load_profile(PROFILE_PATH, PROFILE_NAME)
        compared = analyze_frames(
            [],
            expected_rows=expected_rows,
            ctre_enrichment=FAKE_CTRE_ENRICHMENT,
        )
        falcon = next(
            device
            for device in compared.device_records
            if (
                device.identity.manufacturer,
                device.identity.device_type,
                device.identity.device_id,
            )
            == (4, 2, 9)
        )
        self.assertEqual("observed", falcon.expected_status)
        self.assertNotEqual("degraded", falcon.health)

    def test_ctre_corroboration_increases_presence_score_for_same_device(self) -> None:
        base_result = analyze_capture(FIXTURE_USB_CAP_8)
        passive_falcon = next(
            device
            for device in base_result.device_records
            if (
                device.identity.manufacturer,
                device.identity.device_type,
                device.identity.device_id,
            )
            == (4, 2, 9)
        )
        enriched = analyze_frames(
            base_result.source_frames,
            expected_rows=base_result.expected_rows,
            ctre_enrichment=FAKE_CTRE_ENRICHMENT,
            run_metadata=dict(base_result.run_metadata),
        )
        enriched_falcon = next(
            device
            for device in enriched.device_records
            if (
                device.identity.manufacturer,
                device.identity.device_type,
                device.identity.device_id,
            )
            == (4, 2, 9)
        )
        self.assertGreater(enriched_falcon.presence_score, passive_falcon.presence_score)

    def test_live_rev_session_snapshot_exposes_source_diagnostics(self) -> None:
        fake_serial_module = types.SimpleNamespace(
            Serial=lambda port, baudrate, timeout: _FakeSerialHandle(
                [
                    b"T0205B819800008E0600188000\r",
                ]
            )
        )
        with patch.dict("sys.modules", {"serial": fake_serial_module}):
            session = observe_rev_serial_session(port="COM7", duration_sec=0.02)
            session.start()
            session.wait(timeout=0.5)
            snapshot = session.snapshot()
        diagnostics = snapshot.run_metadata["sourceDiagnostics"]
        self.assertEqual("COM7", diagnostics["resolvedPort"])
        self.assertGreaterEqual(diagnostics["rawBytesReceived"], 1)
        self.assertGreaterEqual(diagnostics["parsedRecordCount"], 1)
        self.assertGreaterEqual(diagnostics["normalizedFrameCount"], 1)

    def test_collect_ctre_enrichment_preserves_vendor_fields_from_getdevices(self) -> None:
        responses = {
            "getdevices": {
                "DeviceArray": [
                    {
                        "Model": "CANcoder",
                        "Name": "Front Right",
                        "ID": 18,
                        "CANbus": "rio",
                        "CurrentVers": "25.5.1.0 (Phoenix 6)",
                        "Status": "Running Application",
                        "Vendor": "CTR Electronics",
                        "HardwareRev": "1.0",
                        "BootloaderRev": "1.0",
                        "Manufactured": "Jun 30, 2025",
                        "IsPROLicensed": False,
                        "SupportsControl": False,
                        "SupportsConfigs": True,
                        "SupportsDecoratedSelfTest": True,
                    },
                    {
                        "Model": "Pigeon 2 vers. S",
                        "Name": "Pigeon 2 vers. S (Device ID 19)",
                        "ID": 19,
                        "CANbus": "rio",
                        "CurrentVers": "26.1.0.0 (Phoenix 6)",
                        "Status": "Running Application",
                        "Vendor": "CTR Electronics",
                        "HardwareRev": "1.0",
                        "BootloaderRev": "1.0",
                        "Manufactured": "Jun 30, 2025",
                        "IsPROLicensed": False,
                        "SupportsControl": False,
                        "SupportsConfigs": False,
                        "SupportsDecoratedSelfTest": False,
                    },
                ]
            },
            "decoratedselftest": {
                "SelfTest": {
                    "Fault_Hardware": {"Value": "True"},
                    "StickyFault_BootDuringEnable": {"Value": "True"},
                }
            },
        }

        def fake_http_get_json(base_url, params):
            _ = base_url
            action = str(params.get("action", "")).strip()
            return responses[action]

        with patch("tools.passive_discovery_poc.enrich_ctre._http_get_json", side_effect=fake_http_get_json):
            enrichment, warnings = collect_ctre_enrichment("http://127.0.0.1:1250")

        self.assertEqual([], warnings)
        cancoder = enrichment[(4, 7, 18)]
        self.assertEqual("CANcoder", cancoder["model"])
        self.assertEqual("Front Right", cancoder["name"])
        self.assertEqual("rio", cancoder["canbus"])
        self.assertEqual("Running Application", cancoder["status"])
        self.assertEqual("CTR Electronics", cancoder["vendor"])
        self.assertEqual("1.0", cancoder["hardwareRev"])
        self.assertEqual("1.0", cancoder["bootloader"])
        self.assertEqual("Jun 30, 2025", cancoder["manufactured"])
        self.assertFalse(cancoder["isProLicensed"])
        self.assertFalse(cancoder["supportsControl"])
        self.assertTrue(cancoder["supportsConfigs"])
        self.assertTrue(cancoder["supportsDecoratedSelfTest"])
        self.assertEqual(["Fault_Hardware"], cancoder["faultsTrue"])
        self.assertEqual(["StickyFault_BootDuringEnable"], cancoder["stickyFaultsTrue"])

        pigeon = enrichment[(4, 4, 19)]
        self.assertEqual("Pigeon 2 vers. S", pigeon["model"])
        self.assertEqual("Pigeon 2 vers. S (Device ID 19)", pigeon["name"])
        self.assertEqual("rio", pigeon["canbus"])
        self.assertEqual("Running Application", pigeon["status"])
        self.assertEqual("CTR Electronics", pigeon["vendor"])
        self.assertFalse(pigeon["supportsControl"])
        self.assertFalse(pigeon["supportsConfigs"])
        self.assertFalse(pigeon["supportsDecoratedSelfTest"])
        self.assertNotIn("faultsTrue", pigeon)


if __name__ == "__main__":
    unittest.main()
