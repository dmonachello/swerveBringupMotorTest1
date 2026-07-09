from __future__ import annotations

"""
NAME
    models.py - Data models for passive discovery analysis.

DESCRIPTION
    Defines normalized frame, family, device, and run-result structures used by
    the PoC.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class NormalizedFrame:
    """
    NAME
        NormalizedFrame - One CAN frame normalized for analysis.
    """

    timestamp_s: float
    can_id: int
    dlc: int
    data_hex: str
    is_extended: bool
    is_rtr: bool
    manufacturer: Optional[int]
    device_type: Optional[int]
    api_class: Optional[int]
    api_index: Optional[int]
    device_id: Optional[int]
    observer_source: str


@dataclass(frozen=True)
class DeviceIdentity:
    """
    NAME
        DeviceIdentity - Canonical passive identity for one observed device.
    """

    manufacturer: int
    device_type: int
    device_id: int
    bus: str = ""
    profile_node: str = ""


@dataclass(frozen=True)
class FamilyKey:
    """
    NAME
        FamilyKey - Canonical key for one frame family.
    """

    manufacturer: int
    device_type: int
    device_id: int
    api_class: int
    api_index: int


@dataclass(frozen=True)
class FamilyMetrics:
    """
    NAME
        FamilyMetrics - Derived measurements for one frame family.
    """

    count: int
    rate_hz: float
    interarrival_mean_sec: float
    interarrival_stddev_sec: float
    unique_payload_count: int
    payload_transition_count: int
    first_seen_s: float
    last_seen_s: float
    is_recurring: bool
    is_stable_cadence: bool
    is_high_rate: bool
    is_secondary_rate: bool
    is_heartbeat_rate: bool
    is_mostly_constant_payload: bool


@dataclass(frozen=True)
class FamilyRecord:
    """
    NAME
        FamilyRecord - One analyzed frame family plus role classification.
    """

    key: FamilyKey
    metrics: FamilyMetrics
    role: str
    confidence: str
    model_hint: str
    observed_can_ids: Tuple[str, ...]
    sample_payloads: Tuple[str, ...]


@dataclass(frozen=True)
class DeviceRecord:
    """
    NAME
        DeviceRecord - One inferred device plus evidence summary.
    """

    identity: DeviceIdentity
    expected_status: str
    manufacturer_name: str
    device_type_name: str
    model_name: str
    profile_label: str
    presence_confidence: str
    presence_score: int
    inventory_confidence: str
    inventory_score: int
    health_confidence: str
    health_score: int
    health: str
    evidence_sources: Tuple[str, ...]
    evidence_family_keys: Tuple[FamilyKey, ...]
    evidence_family_summaries: Tuple[str, ...]
    evidence_gaps: Tuple[str, ...]
    notes: Tuple[str, ...]
    ctre_enrichment: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    """
    NAME
        RunResult - Full machine-consumable result of one PoC run.
    """

    run_metadata: Dict[str, Any]
    device_records: Tuple[DeviceRecord, ...]
    family_records: Tuple[FamilyRecord, ...]
    unknown_frames: Tuple[Dict[str, Any], ...]
    warnings: Tuple[str, ...]
    source_frames: Tuple[NormalizedFrame, ...] = field(default_factory=tuple)
    expected_rows: Dict[Tuple[int, int, int], Dict[str, object]] = field(default_factory=dict)
    ctre_enrichment: Dict[Tuple[int, int, int], Dict[str, object]] = field(default_factory=dict)
    enrichment_records: Tuple["EnrichmentRecord", ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SourcePluginInfo:
    """
    NAME
        SourcePluginInfo - Public metadata describing one registered source plugin.
    """

    plugin_id: str
    display_name: str
    source_class: str
    source_mode: str
    description: str


@dataclass(frozen=True)
class EnrichmentRecord:
    """
    NAME
        EnrichmentRecord - Normalized output from one enrichment-source plugin.
    """

    plugin_id: str
    source_class: str
    source_mode: str
    metadata: Dict[str, Any]
    expected_rows: Dict[Tuple[int, int, int], Dict[str, object]] = field(default_factory=dict)
    device_enrichment: Dict[Tuple[int, int, int], Dict[str, object]] = field(default_factory=dict)
    evidence_records: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AdapterContext:
    """
    NAME
        AdapterContext - Explicit configuration for device-object adaptation.
    """

    source_name: str = "passive_discovery_poc"
    attachment_type: str = "passiveDiscovery"
    label_fallback_prefix: str = "DISCOVERED"
    include_family_evidence: bool = True


@dataclass(frozen=True)
class SessionCallbacks:
    """
    NAME
        SessionCallbacks - Optional callback hooks for live observation sessions.
    """

    on_frame: Optional[Callable[[NormalizedFrame], None]] = None
    on_snapshot: Optional[Callable[[RunResult], None]] = None
    on_warning: Optional[Callable[[str], None]] = None
