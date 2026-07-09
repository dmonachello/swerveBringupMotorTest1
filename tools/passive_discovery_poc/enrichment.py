from __future__ import annotations

"""
NAME
    enrichment.py - Public enrichment API for passive discovery.

DESCRIPTION
    Exposes explicit enrichment steps that can be called directly or supplied as
    optional inputs to higher-level analysis flows.
"""

from dataclasses import replace
from typing import Dict, List, Tuple

from tools.passive_discovery_poc.constants import SOURCE_KIND_CTRE_HTTP, SOURCE_KIND_RIO_CONSOLE_LOG, SOURCE_KIND_TOPOLOGY
from tools.passive_discovery_poc.discovery import analyze_frames
from tools.passive_discovery_poc.models import EnrichmentRecord, RunResult
from tools.passive_discovery_poc.result_builder import append_enrichment_record
from tools.passive_discovery_poc.sources import RecordedEnrichmentSourcePlugin, default_source_registry


def enrich_ctre(base_url: str) -> Tuple[Dict[Tuple[int, int, int], Dict[str, object]], List[str]]:
    """
    NAME
        enrich_ctre - Collect explicit CTRE enrichment rows and warnings.
    """
    plugin = default_source_registry().get(SOURCE_KIND_CTRE_HTTP)
    resolved = plugin.collect({"base_url": base_url}) if isinstance(plugin, RecordedEnrichmentSourcePlugin) else None
    if resolved is None:
        raise ValueError("registered CTRE source plugin did not implement recorded enrichment contract")
    return dict(resolved.device_enrichment), list(resolved.warnings)


def enrich_result_with_ctre(result: RunResult, base_url: str) -> RunResult:
    """
    NAME
        enrich_result_with_ctre - Rebuild one result with CTRE enrichment applied.
    """
    plugin = default_source_registry().get(SOURCE_KIND_CTRE_HTTP)
    record = plugin.collect({"base_url": base_url}) if isinstance(plugin, RecordedEnrichmentSourcePlugin) else None
    if record is None:
        raise ValueError("registered CTRE source plugin did not implement recorded enrichment contract")
    enrichment_rows = dict(record.device_enrichment)
    warnings = list(record.warnings)
    enriched = analyze_frames(
        result.source_frames,
        expected_rows=result.expected_rows,
        ctre_enrichment=enrichment_rows,
        enrichment_records=[*list(result.enrichment_records), record],
        run_metadata=dict(result.run_metadata),
    )
    return replace(enriched, warnings=(*enriched.warnings, *(str(item) for item in warnings)))


def enrich_topology(profile_path: str, profile_name: str = "") -> EnrichmentRecord:
    """
    NAME
        enrich_topology - Collect explicit topology enrichment from bringup topology data.
    """
    plugin = default_source_registry().get(SOURCE_KIND_TOPOLOGY)
    resolved = plugin.collect({"profile_path": profile_path, "profile_name": profile_name}) if isinstance(plugin, RecordedEnrichmentSourcePlugin) else None
    if resolved is None:
        raise ValueError("registered topology source plugin did not implement recorded enrichment contract")
    return resolved


def enrich_result_with_topology(result: RunResult, profile_path: str, profile_name: str = "") -> RunResult:
    """
    NAME
        enrich_result_with_topology - Attach one topology enrichment record to an existing result.
    """
    return append_enrichment_record(result, enrich_topology(profile_path=profile_path, profile_name=profile_name))


def enrich_console_log(
    log_path: str,
    *,
    profile_path: str = "",
    profile_name: str = "",
    rules_path: str = "",
) -> EnrichmentRecord:
    """
    NAME
        enrich_console_log - Parse one saved roboRIO console log into enrichment evidence.
    """
    plugin = default_source_registry().get(SOURCE_KIND_RIO_CONSOLE_LOG)
    resolved = (
        plugin.collect(
            {
                "log_path": log_path,
                "profile_path": profile_path,
                "profile_name": profile_name,
                "rules_path": rules_path,
            }
        )
        if isinstance(plugin, RecordedEnrichmentSourcePlugin)
        else None
    )
    if resolved is None:
        raise ValueError("registered rio_console_log source plugin did not implement recorded enrichment contract")
    return resolved
