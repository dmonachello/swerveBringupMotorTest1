"""Regression tests for typed host telemetry parsing and retention."""

import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.common.telemetry.capture import LongFormCsvSink
from tools.common.telemetry.constants import MAX_HOST_HISTORY_BYTES
from tools.common.telemetry.history import PrimitiveSampleRing, TelemetryHistoryStore
from tools.common.telemetry.wire import parse_catalog, parse_history_page


SOURCE_ID = "source-a"
SIGNAL_ID = "source-a:test|motor|1|current_actual"
DEFINITION_KEY = "test|motor|1|current_actual"


def catalog_payload() -> dict:
    """Build one minimal valid wire catalog fixture."""
    return {
        "schemaVersion": 1,
        "historyGenerationId": "source-a:1",
        "sourceInstanceId": SOURCE_ID,
        "catalogRevision": 1,
        "clockDescriptor": {
            "clockId": SOURCE_ID,
            "kind": "FPGA_MONOTONIC",
            "ticksPerSecond": 1_000_000,
        },
        "signals": [
            {
                "signalDefinitionKey": DEFINITION_KEY,
                "signalId": SIGNAL_ID,
                "sourceInstanceId": SOURCE_ID,
                "subjectKey": "test|motor|1",
                "deviceLabel": "motor1",
                "signalName": "current_actual",
                "valueKind": "NUMBER",
                "unit": "amperes",
                "unitSymbol": "A",
                "engineeringDimension": "ELECTRIC_CURRENT",
                "nominalCadenceUs": 20_000,
                "staleAfterUs": 100_000,
                "graphable": True,
            }
        ],
    }


def history_payload(sequence: int, value: float) -> dict:
    """Build one valid single-sample wire history fixture."""
    return {
        "schemaVersion": 1,
        "historyGenerationId": "source-a:1",
        "sourceInstanceId": SOURCE_ID,
        "oldestSequence": sequence,
        "nextSequence": sequence,
        "hasMore": False,
        "cursorExpired": False,
        "robotReplyUs": sequence * 20_000,
        "records": [
            {
                "sequence": sequence,
                "signalId": SIGNAL_ID,
                "sourceTimestampUs": sequence * 20_000,
                "numericValue": value,
                "quality": "GOOD",
            }
        ],
    }


class TelemetryHistoryStoreTest(unittest.TestCase):
    """Cover watch caps, bounded retention, and source-safe parsing."""

    def test_selected_signal_receives_bounded_timestamped_samples(self) -> None:
        store = TelemetryHistoryStore(max_samples_per_signal=2)
        store.apply_catalog(parse_catalog(catalog_payload()))
        self.assertTrue(store.watch(SIGNAL_ID))

        store.apply_page(parse_history_page(history_payload(1, 1.0)))
        store.apply_page(parse_history_page(history_payload(2, 2.0)))
        store.apply_page(parse_history_page(history_payload(3, 3.0)))

        samples = store.samples(SIGNAL_ID)
        self.assertEqual([2, 3], [sample.sequence for sample in samples])
        self.assertEqual(3, store.cursor)

    def test_primitive_ring_capacity_stays_within_host_memory_budget(self) -> None:
        ring = PrimitiveSampleRing(100_000)

        self.assertLess(ring.storage_bytes() * 8, MAX_HOST_HISTORY_BYTES)

    def test_primitive_ring_preserves_every_robot_quality(self) -> None:
        ring = PrimitiveSampleRing(4)
        qualities = ("GOOD", "UNAVAILABLE", "READ_ERROR", "STALE")
        for index, quality in enumerate(qualities, start=1):
            sample = parse_history_page(
                history_payload(index, float(index))
            ).records[0]
            ring.append(
                sample if quality == "GOOD" else replace(sample, quality=quality)
            )

        self.assertEqual(
            qualities,
            tuple(sample.quality for sample in ring.snapshot(SIGNAL_ID)),
        )

    def test_parser_rejects_unknown_schema_version(self) -> None:
        payload = catalog_payload()
        payload["schemaVersion"] = 99
        with self.assertRaises(ValueError):
            parse_catalog(payload)

    def test_watch_cap_rejects_ninth_signal(self) -> None:
        payload = catalog_payload()
        template = payload["signals"][0]
        payload["signals"] = [
            {
                **template,
                "signalDefinitionKey": f"definition-{index}",
                "signalId": f"signal-{index}",
                "signalName": f"signal_{index}",
            }
            for index in range(9)
        ]
        store = TelemetryHistoryStore()
        store.apply_catalog(parse_catalog(payload))

        for index in range(8):
            self.assertTrue(store.watch(f"signal-{index}"))
        self.assertFalse(store.watch("signal-8"))
        self.assertIn("8", store.watch_block_reason("signal-8"))

    def test_long_form_csv_preserves_each_source_sample(self) -> None:
        store = TelemetryHistoryStore()
        store.apply_catalog(parse_catalog(catalog_payload()))
        store.watch(SIGNAL_ID)
        store.apply_page(parse_history_page(history_payload(1, 7.5)))

        with TemporaryDirectory() as directory:
            path = Path(directory) / "capture.csv"
            row_count = LongFormCsvSink.export(path, store)
            text = path.read_text(encoding="utf-8")

        self.assertEqual(1, row_count)
        self.assertIn(SIGNAL_ID, text)
        self.assertIn("7.5", text)

    def test_repeated_page_is_deduplicated(self) -> None:
        store = TelemetryHistoryStore()
        store.apply_catalog(parse_catalog(catalog_payload()))
        store.watch(SIGNAL_ID)
        page = parse_history_page(history_payload(1, 4.0))

        store.apply_page(page)
        store.apply_page(page)

        self.assertEqual(1, len(store.samples(SIGNAL_ID)))

    def test_expired_cursor_retains_old_segment_and_marks_gap(self) -> None:
        store = TelemetryHistoryStore()
        store.apply_catalog(parse_catalog(catalog_payload()))
        store.watch(SIGNAL_ID)
        store.apply_page(parse_history_page(history_payload(1, 1.0)))
        expired = history_payload(3, 3.0)
        expired["cursorExpired"] = True

        store.apply_page(parse_history_page(expired))

        self.assertTrue(store.gap_detected)
        samples = store.samples(SIGNAL_ID)
        self.assertEqual([1, 3], [sample.sequence for sample in samples])
        self.assertTrue(samples[-1].gap_before)

    def test_generation_change_keeps_watch_and_retained_segment(self) -> None:
        store = TelemetryHistoryStore()
        store.apply_catalog(parse_catalog(catalog_payload()))
        store.watch(SIGNAL_ID)
        store.apply_page(parse_history_page(history_payload(1, 1.0)))
        next_catalog = deepcopy(catalog_payload())
        next_catalog["historyGenerationId"] = "source-a:2"
        next_catalog["signals"] = []

        store.apply_catalog(parse_catalog(next_catalog))

        self.assertEqual((SIGNAL_ID,), store.signal_ids_for_query())
        self.assertEqual([1], [sample.sequence for sample in store.samples(SIGNAL_ID)])
        self.assertTrue(store.gap_detected)

    def test_new_generation_rebinds_watch_by_definition_key(self) -> None:
        store = TelemetryHistoryStore()
        store.apply_catalog(parse_catalog(catalog_payload()))
        store.watch(SIGNAL_ID)
        next_catalog = deepcopy(catalog_payload())
        next_catalog["historyGenerationId"] = "source-b:1"
        next_catalog["sourceInstanceId"] = "source-b"
        next_catalog["clockDescriptor"]["clockId"] = "source-b"
        next_catalog["signals"][0]["sourceInstanceId"] = "source-b"
        next_catalog["signals"][0]["signalId"] = "source-b:def"

        store.apply_catalog(parse_catalog(next_catalog))

        self.assertEqual(("source-b:def",), store.signal_ids_for_query())
        self.assertTrue(store.gap_detected)

    def test_empty_new_source_catalog_preserves_watch_intent_for_rebind(self) -> None:
        store = TelemetryHistoryStore()
        store.apply_catalog(parse_catalog(catalog_payload()))
        store.watch(SIGNAL_ID)
        empty_catalog = deepcopy(catalog_payload())
        empty_catalog["sourceInstanceId"] = "source-b"
        empty_catalog["historyGenerationId"] = "source-b:1"
        empty_catalog["clockDescriptor"]["clockId"] = "source-b"
        empty_catalog["signals"] = []
        store.apply_catalog(parse_catalog(empty_catalog))
        restored_catalog = deepcopy(catalog_payload())
        restored_catalog["sourceInstanceId"] = "source-b"
        restored_catalog["historyGenerationId"] = "source-b:1"
        restored_catalog["clockDescriptor"]["clockId"] = "source-b"
        restored_catalog["signals"][0]["sourceInstanceId"] = "source-b"
        restored_catalog["signals"][0]["signalId"] = "source-b:def"

        store.apply_catalog(parse_catalog(restored_catalog))

        self.assertEqual(("source-b:def",), store.signal_ids_for_query())

    def test_new_watch_rewinds_for_pretrigger_without_duplicating_existing_trace(self) -> None:
        payload = catalog_payload()
        second = dict(payload["signals"][0])
        second["signalDefinitionKey"] = "second-definition"
        second["signalId"] = "second-signal"
        second["signalName"] = "velocity_actual"
        second["engineeringDimension"] = "ROTATIONAL_VELOCITY"
        payload["signals"].append(second)
        store = TelemetryHistoryStore()
        store.apply_catalog(parse_catalog(payload))
        store.watch(SIGNAL_ID)
        store.apply_page(parse_history_page(history_payload(4, 4.0)))

        self.assertTrue(store.watch("second-signal"))
        self.assertEqual(0, store.cursor)
        backfill = history_payload(4, 4.0)
        second_record = dict(backfill["records"][0])
        second_record.update(
            sequence=5,
            signalId="second-signal",
            sourceTimestampUs=90_000,
            numericValue=5.0,
        )
        backfill["records"].append(second_record)
        backfill["nextSequence"] = 5
        store.apply_page(parse_history_page(backfill))

        self.assertEqual([4], [item.sequence for item in store.samples(SIGNAL_ID)])
        self.assertEqual([5], [item.sequence for item in store.samples("second-signal")])


if __name__ == "__main__":
    unittest.main()
