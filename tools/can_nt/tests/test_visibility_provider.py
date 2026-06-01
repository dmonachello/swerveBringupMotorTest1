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

    def test_rate_uses_long_window_average_after_burst(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
