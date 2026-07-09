"""
NAME
    passive_discovery_poc - Offline-first passive CAN discovery proof of concept.

DESCRIPTION
    Provides capture ingestion, frame-family analysis, passive device inference,
    optional CTRE enrichment, and machine-consumable output artifacts without
    using NetworkTables.
"""

from tools.passive_discovery_poc.adapters import apply_discovery_to_devices, update_or_create_device
from tools.passive_discovery_poc.capture import (
    PassiveObservationSession,
    load_expected_rows,
    observe_rev_serial_session,
    observe_slcan_session,
    read_candump,
    read_capture,
    read_pcapng,
)
from tools.passive_discovery_poc.discovery import analyze_capture, analyze_frames
from tools.passive_discovery_poc.enrichment import enrich_console_log, enrich_ctre, enrich_result_with_ctre, enrich_topology
from tools.passive_discovery_poc.json_api import result_from_json_dict, result_to_json_dict, write_json_result
from tools.passive_discovery_poc.models import AdapterContext, EnrichmentRecord, RunResult, SessionCallbacks, SourcePluginInfo
from tools.passive_discovery_poc.profile import compare_profile, load_profile
from tools.passive_discovery_poc.render import render_full_dump_result, render_summary_table
from tools.passive_discovery_poc.sources import (
    LiveEnrichmentSourcePlugin,
    LiveFrameSourcePlugin,
    RecordedEnrichmentSourcePlugin,
    RecordedFrameSourcePlugin,
    SourcePluginBase,
    SourceRegistry,
    default_source_registry,
)

__all__ = [
    "AdapterContext",
    "EnrichmentRecord",
    "LiveEnrichmentSourcePlugin",
    "LiveFrameSourcePlugin",
    "PassiveObservationSession",
    "RecordedEnrichmentSourcePlugin",
    "RecordedFrameSourcePlugin",
    "RunResult",
    "SessionCallbacks",
    "SourcePluginBase",
    "SourcePluginInfo",
    "SourceRegistry",
    "analyze_capture",
    "analyze_frames",
    "apply_discovery_to_devices",
    "compare_profile",
    "enrich_ctre",
    "enrich_console_log",
    "enrich_result_with_ctre",
    "enrich_topology",
    "load_expected_rows",
    "load_profile",
    "observe_rev_serial_session",
    "observe_slcan_session",
    "default_source_registry",
    "read_candump",
    "read_capture",
    "read_pcapng",
    "render_full_dump_result",
    "render_summary_table",
    "result_from_json_dict",
    "result_to_json_dict",
    "update_or_create_device",
    "write_json_result",
]
