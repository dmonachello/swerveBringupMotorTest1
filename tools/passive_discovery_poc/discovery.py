from __future__ import annotations

"""
NAME
    discovery.py - Public discovery API for passive CAN analysis.

DESCRIPTION
    Exposes stable analysis entrypoints over normalized frames and offline
    captures while preserving the current PoC heuristics under the hood.
"""

from typing import Dict, Iterable, Optional, Tuple, cast

from tools.passive_discovery_poc.models import EnrichmentRecord, NormalizedFrame, RunResult
from tools.passive_discovery_poc.constants import SOURCE_KIND_CAPTURE_AUTO
from tools.passive_discovery_poc.result_builder import build_run_result
from tools.passive_discovery_poc.sources import RecordedFrameSourcePlugin, default_source_registry


ExpectedRows = Dict[Tuple[int, int, int], Dict[str, object]]
EnrichmentRows = Dict[Tuple[int, int, int], Dict[str, object]]


def analyze_frames(
    frames: Iterable[NormalizedFrame],
    *,
    expected_rows: Optional[ExpectedRows] = None,
    ctre_enrichment: Optional[EnrichmentRows] = None,
    enrichment_records: Optional[Iterable[EnrichmentRecord]] = None,
    run_metadata: Optional[Dict[str, object]] = None,
) -> RunResult:
    """
    NAME
        analyze_frames - Analyze normalized frames into one public discovery result.
    """
    return build_run_result(
        frames,
        expected_rows=expected_rows,
        ctre_enrichment=ctre_enrichment,
        enrichment_records=enrichment_records,
        run_metadata=run_metadata,
    )


def analyze_capture(
    path: str,
    *,
    expected_rows: Optional[ExpectedRows] = None,
    ctre_enrichment: Optional[EnrichmentRows] = None,
    enrichment_records: Optional[Iterable[EnrichmentRecord]] = None,
    run_metadata: Optional[Dict[str, object]] = None,
) -> RunResult:
    """
    NAME
        analyze_capture - Read one offline capture and analyze it into a discovery result.
    """
    metadata = dict(run_metadata or {})
    metadata.setdefault("input", path)
    plugin = cast(RecordedFrameSourcePlugin, default_source_registry().get(SOURCE_KIND_CAPTURE_AUTO))
    return analyze_frames(
        plugin.read_frames({"path": path}),
        expected_rows=expected_rows,
        ctre_enrichment=ctre_enrichment,
        enrichment_records=enrichment_records,
        run_metadata=metadata,
    )
