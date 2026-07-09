from __future__ import annotations

"""
NAME
    result_builder.py - Canonical RunResult construction and update helpers.

DESCRIPTION
    Owns the shared path for building immutable-style run snapshots from
    analysis output and for attaching additive enrichment records without
    surface-specific mutation.
"""

from dataclasses import replace
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from tools.passive_discovery_poc.classify import analyze_frames as _analyze_internal_frames
from tools.passive_discovery_poc.models import EnrichmentRecord, NormalizedFrame, RunResult


ExpectedRows = Dict[Tuple[int, int, int], Dict[str, object]]
DeviceEnrichmentRows = Dict[Tuple[int, int, int], Dict[str, object]]


def build_run_result(
    frames: Iterable[NormalizedFrame],
    *,
    expected_rows: Optional[ExpectedRows] = None,
    ctre_enrichment: Optional[DeviceEnrichmentRows] = None,
    enrichment_records: Optional[Iterable[EnrichmentRecord]] = None,
    run_metadata: Optional[Mapping[str, object]] = None,
    warnings: Optional[Iterable[str]] = None,
) -> RunResult:
    """
    NAME
        build_run_result - Build one canonical RunResult snapshot.
    """
    frame_list = list(frames)
    resolved_expected = _copy_expected_rows(expected_rows or {})
    resolved_enrichment = _copy_device_enrichment(ctre_enrichment or {})
    resolved_records = tuple(enrichment_records or ())
    families, devices, unknown_frames = _analyze_internal_frames(
        frames=frame_list,
        expected_rows=resolved_expected,
        ctre_enrichment=resolved_enrichment,
    )
    metadata = dict(run_metadata or {})
    metadata.setdefault("timestampUtc", datetime.now(timezone.utc).isoformat())
    metadata["frameCount"] = len(frame_list)
    return RunResult(
        run_metadata=metadata,
        device_records=tuple(devices),
        family_records=tuple(families),
        unknown_frames=tuple(dict(row) for row in unknown_frames),
        warnings=tuple(str(item) for item in (warnings or ())),
        source_frames=tuple(frame_list),
        expected_rows=resolved_expected,
        ctre_enrichment=resolved_enrichment,
        enrichment_records=resolved_records,
    )


def append_enrichment_record(result: RunResult, record: EnrichmentRecord) -> RunResult:
    """
    NAME
        append_enrichment_record - Return a new result with one additive enrichment record.
    """
    return replace(
        result,
        enrichment_records=(*result.enrichment_records, record),
        warnings=(*result.warnings, *record.warnings),
    )


def with_warnings(result: RunResult, warnings: Iterable[str]) -> RunResult:
    """
    NAME
        with_warnings - Return a new result with additional warnings appended.
    """
    return replace(result, warnings=(*result.warnings, *(str(item) for item in warnings)))


def _copy_expected_rows(rows: ExpectedRows) -> ExpectedRows:
    """
    NAME
        _copy_expected_rows - Deep-copy expected-row mappings for snapshot safety.
    """
    return {
        (manufacturer, device_type, device_id): dict(value)
        for (manufacturer, device_type, device_id), value in rows.items()
    }


def _copy_device_enrichment(rows: DeviceEnrichmentRows) -> DeviceEnrichmentRows:
    """
    NAME
        _copy_device_enrichment - Deep-copy device-enrichment mappings for snapshot safety.
    """
    return {
        (manufacturer, device_type, device_id): dict(value)
        for (manufacturer, device_type, device_id), value in rows.items()
    }
