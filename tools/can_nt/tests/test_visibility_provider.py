"""
NAME
    test_visibility_provider.py - Unit tests for label-first visibility tracking.
"""

from __future__ import annotations

import unittest

from tools.can_nt.visibility_constants import (
    VIS_KEY_API_CLASS,
    VIS_KEY_API_INDEX,
    VIS_KEY_DEVICES,
    VIS_KEY_FRAMES_PER_SEC,
    VIS_KEY_IDENTITY,
    VIS_KEY_KEY,
    VIS_KEY_LABEL,
    VIS_KEY_METRICS,
    VIS_KEY_MSG_COUNT,
    VIS_KEY_RAW_IDS,
    VIS_KEY_UNEXPECTED,
    VIS_SCOPE_BOTH,
)
from tools.passive_discovery_poc.models import NormalizedFrame
from tools.can_nt.visibility_provider import SourceInfo, VisibilityProvider


TEST_TIMEOUT_MS = 1000
TEST_NOW_MS = 5000
TEST_SEEN_MS = 4500
TEST_SOURCE_ID = "src0"
TEST_SOURCE_LABEL = "analyzer0"
TEST_EXPECTED_LABEL = "FALCON 9"
TEST_EXPECTED_IDENTITY = "1:2:9"
TEST_DISCOVERED_IDENTITY = "99:88:77"
TEST_DISCOVERED_LABEL = "UNPROFILED_DEVICE_1"
TEST_RENAMED_LABEL = "rear-can-observer"
TEST_OBSERVER_SOURCE = "src0"


class VisibilityProviderTests(unittest.TestCase):
    def _build_provider(self) -> VisibilityProvider:
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
        return provider

    def test_expected_device_uses_configured_label(self) -> None:
        provider = self._build_provider()
        provider.set_expected_devices([(TEST_EXPECTED_LABEL, TEST_EXPECTED_IDENTITY)])

        provider.ingest_frame(
            TEST_SOURCE_ID,
            arb_id=0x02042C49,
            ts_ms=TEST_SEEN_MS,
            decoded_key=TEST_EXPECTED_IDENTITY,
            label=TEST_EXPECTED_LABEL,
        )
        snapshot = provider.snapshot(VIS_SCOPE_BOTH, TEST_NOW_MS)
        devices = snapshot[VIS_KEY_DEVICES]

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0][VIS_KEY_LABEL], TEST_EXPECTED_LABEL)
        self.assertEqual(devices[0][VIS_KEY_KEY], TEST_EXPECTED_LABEL)
        self.assertEqual(devices[0][VIS_KEY_IDENTITY], TEST_EXPECTED_IDENTITY)
        self.assertFalse(devices[0][VIS_KEY_UNEXPECTED])
        self.assertEqual(len(devices[0][VIS_KEY_RAW_IDS]), 1)
        self.assertEqual(devices[0][VIS_KEY_RAW_IDS][0][VIS_KEY_API_CLASS], 11)
        self.assertEqual(devices[0][VIS_KEY_RAW_IDS][0][VIS_KEY_API_INDEX], 1)

    def test_unconfigured_identity_gets_stable_discovered_label(self) -> None:
        provider = self._build_provider()

        first = provider.resolve_label(TEST_DISCOVERED_IDENTITY)
        second = provider.resolve_label(TEST_DISCOVERED_IDENTITY)

        self.assertEqual(first, TEST_DISCOVERED_LABEL)
        self.assertEqual(second, TEST_DISCOVERED_LABEL)

    def test_rename_discovered_label_persists_for_identity(self) -> None:
        provider = self._build_provider()

        original = provider.resolve_label(TEST_DISCOVERED_IDENTITY)
        provider.ingest_frame(
            TEST_SOURCE_ID,
            arb_id=0,
            ts_ms=TEST_SEEN_MS,
            decoded_key=TEST_DISCOVERED_IDENTITY,
            label=original,
        )
        renamed = provider.rename_discovered_label(original, TEST_RENAMED_LABEL)
        snapshot = provider.snapshot(VIS_SCOPE_BOTH, TEST_NOW_MS)
        devices = snapshot[VIS_KEY_DEVICES]

        self.assertTrue(renamed)
        self.assertEqual(provider.resolve_label(TEST_DISCOVERED_IDENTITY), TEST_RENAMED_LABEL)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0][VIS_KEY_LABEL], TEST_RENAMED_LABEL)
        self.assertEqual(devices[0][VIS_KEY_KEY], TEST_RENAMED_LABEL)
        self.assertEqual(devices[0][VIS_KEY_IDENTITY], TEST_DISCOVERED_IDENTITY)
        self.assertTrue(devices[0][VIS_KEY_UNEXPECTED])

    def test_expected_device_reclaims_matching_discovered_identity(self) -> None:
        provider = self._build_provider()

        discovered = provider.resolve_label(TEST_EXPECTED_IDENTITY)
        provider.set_expected_devices([(TEST_EXPECTED_LABEL, TEST_EXPECTED_IDENTITY)])
        snapshot = provider.snapshot(VIS_SCOPE_BOTH, TEST_NOW_MS)
        devices = snapshot[VIS_KEY_DEVICES]

        self.assertEqual(discovered, TEST_DISCOVERED_LABEL)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0][VIS_KEY_LABEL], TEST_EXPECTED_LABEL)
        self.assertFalse(devices[0][VIS_KEY_UNEXPECTED])

    def test_rate_uses_recent_tick_window_and_decays_to_zero_without_new_frames(self) -> None:
        provider = self._build_provider()
        provider.set_expected_devices([(TEST_EXPECTED_LABEL, TEST_EXPECTED_IDENTITY)])

        provider.ingest_frame(
            TEST_SOURCE_ID,
            arb_id=0x02042C49,
            ts_ms=TEST_SEEN_MS,
            decoded_key=TEST_EXPECTED_IDENTITY,
            label=TEST_EXPECTED_LABEL,
        )
        provider.ingest_frame(
            TEST_SOURCE_ID,
            arb_id=0x02042C49,
            ts_ms=TEST_SEEN_MS,
            decoded_key=TEST_EXPECTED_IDENTITY,
            label=TEST_EXPECTED_LABEL,
        )
        provider.tick(TEST_NOW_MS)

        snapshot = provider.snapshot(VIS_SCOPE_BOTH, TEST_NOW_MS)
        device = snapshot[VIS_KEY_DEVICES][0]
        metrics = device[VIS_KEY_METRICS]
        source_metric = metrics[TEST_SOURCE_ID]
        raw_id = device[VIS_KEY_RAW_IDS][0]

        self.assertEqual(source_metric[VIS_KEY_MSG_COUNT], 2)
        self.assertGreater(source_metric[VIS_KEY_FRAMES_PER_SEC], 0.0)
        self.assertEqual(raw_id[VIS_KEY_MSG_COUNT], 2)
        self.assertGreater(raw_id[VIS_KEY_FRAMES_PER_SEC], 0.0)
        first_rate = float(source_metric[VIS_KEY_FRAMES_PER_SEC])
        first_raw_rate = float(raw_id[VIS_KEY_FRAMES_PER_SEC])

        provider.tick(TEST_NOW_MS + 1000)
        snapshot = provider.snapshot(VIS_SCOPE_BOTH, TEST_NOW_MS + 1000)
        device = snapshot[VIS_KEY_DEVICES][0]
        metrics = device[VIS_KEY_METRICS]
        source_metric = metrics[TEST_SOURCE_ID]
        raw_id = device[VIS_KEY_RAW_IDS][0]

        self.assertGreater(source_metric[VIS_KEY_FRAMES_PER_SEC], 0.0)
        self.assertLess(source_metric[VIS_KEY_FRAMES_PER_SEC], first_rate)
        self.assertGreater(raw_id[VIS_KEY_FRAMES_PER_SEC], 0.0)
        self.assertLess(raw_id[VIS_KEY_FRAMES_PER_SEC], first_raw_rate)

        provider.tick(TEST_NOW_MS + 20000)
        snapshot = provider.snapshot(VIS_SCOPE_BOTH, TEST_NOW_MS + 20000)
        device = snapshot[VIS_KEY_DEVICES][0]
        metrics = device[VIS_KEY_METRICS]
        source_metric = metrics[TEST_SOURCE_ID]
        raw_id = device[VIS_KEY_RAW_IDS][0]

        self.assertEqual(source_metric[VIS_KEY_FRAMES_PER_SEC], 0.0)
        self.assertEqual(raw_id[VIS_KEY_FRAMES_PER_SEC], 0.0)

    def test_recent_frames_retains_normalized_frame_history(self) -> None:
        provider = self._build_provider()
        frame = NormalizedFrame(
            timestamp_s=1.25,
            can_id=0,
            dlc=8,
            data_hex="0011223344556677",
            is_extended=True,
            is_rtr=False,
            manufacturer=5,
            device_type=2,
            api_class=46,
            api_index=0,
            device_id=25,
            observer_source=TEST_OBSERVER_SOURCE,
        )

        provider.ingest_frame(
            TEST_SOURCE_ID,
            arb_id=0,
            ts_ms=TEST_SEEN_MS,
            decoded_key="5:2:25",
            label="SPARKMAX/NEO 25",
            normalized_frame=frame,
        )

        recent = provider.recent_frames()

        self.assertEqual(1, len(recent))
        self.assertEqual(frame, recent[0])


if __name__ == "__main__":
    unittest.main()
