"""
NAME
    capture.py - Portable telemetry capture and export adapters.

DESCRIPTION
    Writes normalized host-domain records without depending on REST payloads or
    graph widgets. CSV remains an analytical export, not the capture authority.
"""

from __future__ import annotations

import csv
import heapq
from pathlib import Path

from .history import TelemetryHistoryStore


CSV_COLUMNS = (
    "sourceTime",
    "receiveTime",
    "source",
    "signalId",
    "valueKind",
    "value",
    "quality",
    "sequence",
    "unit",
    "gapBefore",
)
CSV_ENCODING = "utf-8"
CSV_NEWLINE = ""


class LongFormCsvSink:
    """Export retained asynchronous samples as one row per source record."""

    @staticmethod
    def export(path: Path, store: TelemetryHistoryStore) -> int:
        """Write watched retained records and return the exported row count."""
        descriptors = {
            descriptor.signal_id: descriptor
            for descriptor in store.watched_descriptors()
        }
        records = heapq.merge(
            *(store.iter_samples(signal_id) for signal_id in descriptors),
            key=lambda sample: (sample.source_timestamp_us, sample.sequence),
        )
        row_count = 0
        with Path(path).open("w", encoding=CSV_ENCODING, newline=CSV_NEWLINE) as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for sample in records:
                descriptor = descriptors[sample.signal_id]
                writer.writerow(
                    {
                        "sourceTime": sample.source_timestamp_us,
                        "receiveTime": sample.receive_timestamp_ns,
                        "source": descriptor.source_instance_id,
                        "signalId": sample.signal_id,
                        "valueKind": descriptor.value_kind,
                        "value": sample.numeric_value,
                        "quality": sample.quality,
                        "sequence": sample.sequence,
                        "unit": descriptor.unit_symbol or descriptor.unit,
                        "gapBefore": sample.gap_before,
                    }
                )
                row_count += 1
        return row_count
