from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.passive_discovery_poc.capture import load_expected_rows, read_capture
from tools.passive_discovery_poc.discovery import analyze_capture, analyze_frames
from tools.passive_discovery_poc.json_api import result_to_json_dict
from tools.passive_discovery_poc.models import NormalizedFrame


FIXTURE_USB_CAP_8 = "tools/vendor_diag/usbCap8_socketcan.pcapng"
PROFILE_PATH = "src/main/deploy/bringup_system.json"
PROFILE_NAME = "test_minimal_25_9"

TEXT_GOLDEN_FRAME_A = "(1.000000) slcan0 0205B819#00008E0600188000 R"
TEXT_GOLDEN_FRAME_B = "(1.020000) slcan0 0205B819#00008E0600188000 R"
TEXT_GOLDEN_FRAME_C = "(1.250000) slcan0 000502C0#01 R"


class PassiveDiscoveryAnalysisTests(unittest.TestCase):
    """
    NAME
        PassiveDiscoveryAnalysisTests - Validate semantic offline analysis behavior.
    """

    def test_usbcap8_detects_expected_and_unexpected_devices(self) -> None:
        resolved_profile, expected_rows = load_expected_rows(
            profile_path=PROFILE_PATH,
            profile_name=PROFILE_NAME,
        )
        self.assertEqual(PROFILE_NAME, resolved_profile)
        frames = read_capture(FIXTURE_USB_CAP_8)

        result = analyze_frames(
            frames=frames,
            expected_rows=expected_rows,
        )

        self.assertGreater(len(result.family_records), 0)
        self.assertEqual(0, len(result.unknown_frames))
        by_key = {
            (device.identity.manufacturer, device.identity.device_type, device.identity.device_id): device
            for device in result.device_records
        }
        spark_25 = by_key[(5, 2, 25)]
        spark_7 = by_key[(5, 2, 7)]
        falcon_9 = by_key[(4, 2, 9)]
        self.assertEqual("observed", spark_25.expected_status)
        self.assertEqual("high", spark_25.presence_confidence)
        self.assertGreaterEqual(spark_25.presence_score, 90)
        self.assertEqual("unexpected", spark_7.expected_status)
        self.assertEqual("high", spark_7.presence_confidence)
        self.assertEqual("observed", falcon_9.expected_status)

    def test_small_candump_result_has_stable_json_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mini.log"
            path.write_text(
                "\n".join([TEXT_GOLDEN_FRAME_A, TEXT_GOLDEN_FRAME_B, TEXT_GOLDEN_FRAME_C]) + "\n",
                encoding="utf-8",
            )
            result = analyze_capture(str(path))
        payload = result_to_json_dict(result)
        self.assertEqual(["devices", "enrichments", "families", "run", "unknownTraffic", "warnings"], sorted(payload.keys()))
        self.assertEqual(2, len(payload["devices"]))
        self.assertEqual(2, len(payload["families"]))
        first_family = payload["families"][0]
        self.assertIn("key", first_family)
        self.assertIn("metrics", first_family)
        self.assertIn("role", first_family)
        self.assertIn("presence_score", payload["devices"][0])

    def test_rev_single_device_status_families_promote_primary_and_heartbeat_presence(self) -> None:
        frames = []
        for index in range(60):
            timestamp = float(index) * 0.02
            frames.append(
                NormalizedFrame(
                    timestamp_s=timestamp,
                    can_id=int("0205B819", 16),
                    dlc=8,
                    data_hex="00008E0600188000",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=5,
                    device_type=2,
                    api_class=46,
                    api_index=0,
                    device_id=25,
                    observer_source="test",
                )
            )
        for index in range(5):
            timestamp = float(index) * 0.25
            frames.append(
                NormalizedFrame(
                    timestamp_s=timestamp,
                    can_id=int("0205B859", 16),
                    dlc=8,
                    data_hex="0000000000000000",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=5,
                    device_type=2,
                    api_class=46,
                    api_index=1,
                    device_id=25,
                    observer_source="test",
                )
            )
        for index in range(2):
            timestamp = float(index)
            frames.append(
                NormalizedFrame(
                    timestamp_s=timestamp,
                    can_id=int("0205BC19", 16),
                    dlc=8,
                    data_hex="0000000000000000",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=5,
                    device_type=2,
                    api_class=47,
                    api_index=0,
                    device_id=25,
                    observer_source="test",
                )
            )
        result = analyze_frames(frames=frames, expected_rows={})
        by_family = {(family.key.api_class, family.key.api_index): family for family in result.family_records}
        self.assertEqual("DEVICE_EMITTED_PRIMARY_STATUS", by_family[(46, 0)].role)
        self.assertEqual("DEVICE_EMITTED_SECONDARY_STATUS", by_family[(46, 1)].role)
        self.assertEqual("DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING", by_family[(47, 0)].role)
        device = result.device_records[0]
        self.assertEqual("high", device.presence_confidence)
        self.assertGreaterEqual(device.presence_score, 90)

    def test_rev_status_family_classification_tolerates_live_usb_jitter(self) -> None:
        frames = []
        high_rate_timestamps = [
            0.00, 0.017, 0.036, 0.053, 0.071, 0.089, 0.106, 0.124, 0.141, 0.160,
            0.177, 0.195, 0.214, 0.231, 0.249, 0.266, 0.285, 0.302, 0.320, 0.338,
        ]
        secondary_timestamps = [0.00, 0.19, 0.41, 0.60, 0.82]
        heartbeat_timestamps = [0.00, 0.94]
        for timestamp in high_rate_timestamps:
            frames.append(
                NormalizedFrame(
                    timestamp_s=timestamp,
                    can_id=int("0205B819", 16),
                    dlc=8,
                    data_hex="00008E0600188000",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=5,
                    device_type=2,
                    api_class=46,
                    api_index=0,
                    device_id=25,
                    observer_source="test",
                )
            )
        for timestamp in secondary_timestamps:
            frames.append(
                NormalizedFrame(
                    timestamp_s=timestamp,
                    can_id=int("0205B859", 16),
                    dlc=8,
                    data_hex="0000000000000000",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=5,
                    device_type=2,
                    api_class=46,
                    api_index=1,
                    device_id=25,
                    observer_source="test",
                )
            )
        for timestamp in heartbeat_timestamps:
            frames.append(
                NormalizedFrame(
                    timestamp_s=timestamp,
                    can_id=int("0205BC19", 16),
                    dlc=8,
                    data_hex="0000000000000000",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=5,
                    device_type=2,
                    api_class=47,
                    api_index=0,
                    device_id=25,
                    observer_source="test",
                )
            )
        result = analyze_frames(frames=frames, expected_rows={})
        by_family = {(family.key.api_class, family.key.api_index): family for family in result.family_records}
        self.assertEqual("DEVICE_EMITTED_PRIMARY_STATUS", by_family[(46, 0)].role)
        self.assertEqual("DEVICE_EMITTED_SECONDARY_STATUS", by_family[(46, 1)].role)
        self.assertEqual("DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING", by_family[(47, 0)].role)

    def test_roborio_periodic_status_family_counts_as_device_emitted_presence(self) -> None:
        frames = []
        for index in range(25):
            frames.append(
                NormalizedFrame(
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
                    observer_source="test",
                )
            )

        result = analyze_frames(
            frames=frames,
            expected_rows={(1, 1, 0): {"label": "roborio", "model": "roborio"}},
        )

        self.assertEqual(1, len(result.family_records))
        self.assertEqual("DEVICE_EMITTED_PRIMARY_STATUS", result.family_records[0].role)
        self.assertEqual("observed", result.device_records[0].expected_status)
        self.assertEqual("medium", result.device_records[0].presence_confidence)

    def test_ctre_motor_verified_status_families_count_as_presence_evidence(self) -> None:
        frames = []
        for index in range(50):
            frames.append(
                NormalizedFrame(
                    timestamp_s=0.01 * float(index),
                    can_id=int("02041D49", 16),
                    dlc=8,
                    data_hex="0000000000000000",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=4,
                    device_type=2,
                    api_class=11,
                    api_index=1,
                    device_id=9,
                    observer_source="test",
                )
            )
        for index in range(5):
            frames.append(
                NormalizedFrame(
                    timestamp_s=0.25 * float(index),
                    can_id=int("02041CC9", 16),
                    dlc=8,
                    data_hex="0000000000000001",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=4,
                    device_type=2,
                    api_class=11,
                    api_index=5,
                    device_id=9,
                    observer_source="test",
                )
            )

        result = analyze_frames(
            frames=frames,
            expected_rows={(4, 2, 9): {"label": "FALCON 9", "model": "falcon"}},
        )

        by_family = {(family.key.api_class, family.key.api_index): family for family in result.family_records}
        self.assertEqual("DEVICE_EMITTED_PRIMARY_STATUS", by_family[(11, 1)].role)
        self.assertEqual("DEVICE_EMITTED_SECONDARY_STATUS", by_family[(11, 5)].role)
        self.assertEqual("observed", result.device_records[0].expected_status)
        self.assertEqual("high", result.device_records[0].presence_confidence)

    def test_ctre_motor_reference_family_does_not_count_as_device_emitted_presence(self) -> None:
        frames = []
        for index in range(20):
            frames.append(
                NormalizedFrame(
                    timestamp_s=0.05 * float(index),
                    can_id=int("02041CC9", 16),
                    dlc=8,
                    data_hex="0000000000000000",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=4,
                    device_type=2,
                    api_class=7,
                    api_index=3,
                    device_id=9,
                    observer_source="test",
                )
            )
        for index in range(50):
            frames.append(
                NormalizedFrame(
                    timestamp_s=0.01 * float(index),
                    can_id=int("02041D49", 16),
                    dlc=8,
                    data_hex="0000000000000000",
                    is_extended=True,
                    is_rtr=False,
                    manufacturer=4,
                    device_type=2,
                    api_class=7,
                    api_index=5,
                    device_id=9,
                    observer_source="test",
                )
            )

        result = analyze_frames(
            frames=frames,
            expected_rows={(4, 2, 9): {"label": "FALCON 9", "model": "falcon"}},
        )

        by_family = {(family.key.api_class, family.key.api_index): family for family in result.family_records}
        self.assertEqual("UNKNOWN", by_family[(7, 3)].role)
        self.assertEqual("UNKNOWN", by_family[(7, 5)].role)
        self.assertEqual("missing", result.device_records[0].expected_status)
        self.assertEqual("uncertain", result.device_records[0].presence_confidence)


if __name__ == "__main__":
    unittest.main()
