from __future__ import annotations

"""
NAME
    classify.py - Family analysis and device inference for passive discovery.

DESCRIPTION
    Groups normalized frames into families, computes cadence and payload metrics,
    classifies likely purpose, and infers per-device evidence.
"""

import math
import statistics
from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List, Set, Tuple

from tools.passive_discovery_poc.constants import (
    CONSTANT_PAYLOAD_VARIATION_MAX,
    CTRE_MANUFACTURER,
    DEVICE_TYPE_BROADCAST,
    DEVICE_TYPE_MOTOR_CONTROLLER,
    EXPECTED_STATUS_MISSING,
    EXPECTED_STATUS_OBSERVED,
    EXPECTED_STATUS_UNCERTAIN,
    EXPECTED_STATUS_UNEXPECTED,
    HEALTH_DEGRADED,
    HEALTH_FAULT_INDICATED,
    HEALTH_GOOD_EVIDENCE,
    HEALTH_LIMITED,
    HEALTH_UNKNOWN,
    MODEL_UNKNOWN,
    PRESENCE_HIGH,
    PRESENCE_LOW,
    PRESENCE_MEDIUM,
    PRESENCE_NONE,
    PRESENCE_UNCERTAIN,
    RATE_HEARTBEAT_MAX_HZ,
    RATE_HIGH_MAX_HZ,
    RATE_HIGH_MIN_HZ,
    RATE_SECONDARY_MAX_HZ,
    RATE_SECONDARY_MIN_HZ,
    REV_COMMAND_API_CLASS,
    REV_COMMAND_INDEX_CURRENT,
    REV_COMMAND_INDEX_DUTY,
    REV_COMMAND_INDEX_VOLTAGE,
    REV_MANUFACTURER,
    ROLE_CONTROLLER_EMITTED_COMMAND,
    ROLE_DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING,
    ROLE_DEVICE_EMITTED_PRIMARY_STATUS,
    ROLE_DEVICE_EMITTED_SECONDARY_STATUS,
    ROLE_SHARED_BUS_CONTROL,
    ROLE_UNKNOWN,
    STABILITY_MAX_REL_STDDEV,
)
from tools.passive_discovery_poc.metadata import device_type_name, manufacturer_name, model_hint
from tools.passive_discovery_poc.models import (
    DeviceIdentity,
    DeviceRecord,
    FamilyKey,
    FamilyMetrics,
    FamilyRecord,
    NormalizedFrame,
)


def analyze_frames(
    frames: Iterable[NormalizedFrame],
    expected_rows: Dict[Tuple[int, int, int], Dict[str, object]],
    ctre_enrichment: Dict[Tuple[int, int, int], Dict[str, object]],
) -> Tuple[List[FamilyRecord], List[DeviceRecord], List[Dict[str, object]]]:
    """
    NAME
        analyze_frames - Build family and device records from normalized frames.
    """
    grouped: DefaultDict[FamilyKey, List[NormalizedFrame]] = defaultdict(list)
    unknown_frames: List[Dict[str, object]] = []
    for frame in frames:
        if frame.manufacturer is None or frame.device_type is None or frame.api_class is None or frame.api_index is None or frame.device_id is None:
            unknown_frames.append(
                {
                    "timestamp": frame.timestamp_s,
                    "canId": f"0x{frame.can_id:08x}" if frame.is_extended else f"0x{frame.can_id:03x}",
                    "data": frame.data_hex,
                    "source": frame.observer_source,
                }
            )
            continue
        key = FamilyKey(
            manufacturer=frame.manufacturer,
            device_type=frame.device_type,
            device_id=frame.device_id,
            api_class=frame.api_class,
            api_index=frame.api_index,
        )
        grouped[key].append(frame)
    family_records = [_build_family_record(key=key, frames=members) for key, members in grouped.items()]
    family_records.sort(key=lambda item: (item.key.manufacturer, item.key.device_type, item.key.device_id, item.key.api_class, item.key.api_index))
    device_records = _build_device_records(
        family_records=family_records,
        expected_rows=expected_rows,
        ctre_enrichment=ctre_enrichment,
    )
    return (family_records, device_records, unknown_frames)


def _build_family_record(key: FamilyKey, frames: List[NormalizedFrame]) -> FamilyRecord:
    """
    NAME
        _build_family_record - Compute metrics and role for one frame family.
    """
    timestamps = [frame.timestamp_s for frame in frames]
    payloads = [frame.data_hex for frame in frames]
    interarrivals = [timestamps[index] - timestamps[index - 1] for index in range(1, len(timestamps))]
    duration = max((timestamps[-1] - timestamps[0]), 0.0) if len(timestamps) > 1 else 0.0
    rate_hz = float(len(timestamps)) / duration if duration > 0.0 else 0.0
    interarrival_mean = statistics.fmean(interarrivals) if interarrivals else 0.0
    interarrival_stddev = statistics.pstdev(interarrivals) if len(interarrivals) > 1 else 0.0
    unique_payloads = list(dict.fromkeys(payloads))
    payload_transition_count = sum(1 for index in range(1, len(payloads)) if payloads[index] != payloads[index - 1])
    rel_stddev = (interarrival_stddev / interarrival_mean) if interarrival_mean > 0.0 else math.inf
    metrics = FamilyMetrics(
        count=len(frames),
        rate_hz=rate_hz,
        interarrival_mean_sec=interarrival_mean,
        interarrival_stddev_sec=interarrival_stddev,
        unique_payload_count=len(unique_payloads),
        payload_transition_count=payload_transition_count,
        first_seen_s=timestamps[0],
        last_seen_s=timestamps[-1],
        is_recurring=len(frames) >= 2,
        is_stable_cadence=bool(interarrivals) and rel_stddev <= STABILITY_MAX_REL_STDDEV,
        is_high_rate=RATE_HIGH_MIN_HZ <= rate_hz <= RATE_HIGH_MAX_HZ,
        is_secondary_rate=RATE_SECONDARY_MIN_HZ <= rate_hz <= RATE_SECONDARY_MAX_HZ,
        is_heartbeat_rate=rate_hz <= RATE_HEARTBEAT_MAX_HZ,
        is_mostly_constant_payload=len(unique_payloads) <= CONSTANT_PAYLOAD_VARIATION_MAX,
    )
    role, confidence = _classify_family_role(key=key, metrics=metrics)
    observed_ids = [f"0x{frame.can_id:08x}" if frame.is_extended else f"0x{frame.can_id:03x}" for frame in frames[:1]]
    sample_payloads = unique_payloads[:3]
    return FamilyRecord(
        key=key,
        metrics=metrics,
        role=role,
        confidence=confidence,
        model_hint=model_hint(key.manufacturer, key.device_type),
        observed_can_ids=tuple(observed_ids),
        sample_payloads=tuple(sample_payloads),
    )


def _classify_family_role(key: FamilyKey, metrics: FamilyMetrics) -> Tuple[str, str]:
    """
    NAME
        _classify_family_role - Apply first-pass family heuristics.
    """
    if key.manufacturer == REV_MANUFACTURER and key.api_class == REV_COMMAND_API_CLASS and key.api_index in (
        REV_COMMAND_INDEX_DUTY,
        REV_COMMAND_INDEX_VOLTAGE,
        REV_COMMAND_INDEX_CURRENT,
    ):
        return (ROLE_CONTROLLER_EMITTED_COMMAND, PRESENCE_HIGH)
    if key.manufacturer == REV_MANUFACTURER and key.device_type == DEVICE_TYPE_MOTOR_CONTROLLER:
        # The live REV USB relay path adds enough timing jitter that requiring
        # stable cadence here produces false negatives even when the family is
        # clearly recurring at the expected status rate.
        if key.api_class == 46 and key.api_index in (0, 2) and metrics.is_high_rate and metrics.is_recurring:
            return (ROLE_DEVICE_EMITTED_PRIMARY_STATUS, PRESENCE_HIGH)
        if key.api_class == 46 and key.api_index == 1 and metrics.is_secondary_rate and metrics.is_recurring:
            return (ROLE_DEVICE_EMITTED_SECONDARY_STATUS, PRESENCE_MEDIUM)
        if key.api_class == 47 and key.api_index == 0 and metrics.is_heartbeat_rate and metrics.is_recurring:
            return (ROLE_DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING, PRESENCE_MEDIUM)
    if key.device_type == DEVICE_TYPE_BROADCAST or key.device_id == 0:
        return (ROLE_SHARED_BUS_CONTROL, PRESENCE_HIGH)
    if metrics.is_high_rate and metrics.is_stable_cadence:
        return (ROLE_DEVICE_EMITTED_PRIMARY_STATUS, PRESENCE_HIGH)
    if metrics.is_secondary_rate and metrics.is_stable_cadence:
        return (ROLE_DEVICE_EMITTED_SECONDARY_STATUS, PRESENCE_MEDIUM)
    if metrics.is_heartbeat_rate and metrics.is_recurring:
        return (ROLE_DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING, PRESENCE_MEDIUM)
    return (ROLE_UNKNOWN, PRESENCE_LOW)


def _build_device_records(
    family_records: List[FamilyRecord],
    expected_rows: Dict[Tuple[int, int, int], Dict[str, object]],
    ctre_enrichment: Dict[Tuple[int, int, int], Dict[str, object]],
) -> List[DeviceRecord]:
    """
    NAME
        _build_device_records - Aggregate family records into per-device records.
    """
    by_device: DefaultDict[Tuple[int, int, int], List[FamilyRecord]] = defaultdict(list)
    for family in family_records:
        by_device[(family.key.manufacturer, family.key.device_type, family.key.device_id)].append(family)

    observed_keys: Set[Tuple[int, int, int]] = set(by_device.keys())
    all_keys = sorted(observed_keys | set(expected_rows.keys()) | set(ctre_enrichment.keys()))
    records: List[DeviceRecord] = []
    for key in all_keys:
        families = by_device.get(key, [])
        expected = expected_rows.get(key, {})
        enrichment = ctre_enrichment.get(key, {})
        manufacturer, device_type, device_id = key
        identity = DeviceIdentity(
            manufacturer=manufacturer,
            device_type=device_type,
            device_id=device_id,
            bus=str(expected.get("bus", "")),
            profile_node=str(expected.get("profileNode", "")),
        )
        expected_status = _expected_status_for_key(
            key=key,
            families=families,
            expected_rows=expected_rows,
            enrichment=enrichment,
        )
        presence_confidence = _presence_confidence(families=families, enrichment=enrichment)
        inventory_confidence = PRESENCE_HIGH if expected_status in (EXPECTED_STATUS_OBSERVED, EXPECTED_STATUS_MISSING) else PRESENCE_MEDIUM
        health, health_confidence, gaps, notes = _health_for_device(
            key=key,
            families=families,
            expected_status=expected_status,
            enrichment=enrichment,
        )
        evidence_sources = _evidence_sources(families=families, enrichment=enrichment, expected=expected)
        evidence_keys = tuple(family.key for family in families if family.role.startswith("DEVICE_EMITTED"))
        evidence_summaries = tuple(_family_summary(family) for family in families if family.role.startswith("DEVICE_EMITTED"))
        records.append(
            DeviceRecord(
                identity=identity,
                expected_status=expected_status,
                manufacturer_name=manufacturer_name(manufacturer),
                device_type_name=device_type_name(device_type),
                model_name=str(expected.get("model", "")).strip() or str(enrichment.get("model", "")).strip() or model_hint(manufacturer, device_type),
                profile_label=str(expected.get("label", "")).strip(),
                presence_confidence=presence_confidence,
                presence_score=_presence_score(families=families, enrichment=enrichment, presence_confidence=presence_confidence),
                inventory_confidence=inventory_confidence,
                inventory_score=_inventory_score(expected_status=expected_status, inventory_confidence=inventory_confidence),
                health_confidence=health_confidence,
                health_score=_health_score(health=health, health_confidence=health_confidence),
                health=health,
                evidence_sources=tuple(evidence_sources),
                evidence_family_keys=evidence_keys,
                evidence_family_summaries=evidence_summaries,
                evidence_gaps=tuple(gaps),
                notes=tuple(notes),
                ctre_enrichment=dict(enrichment),
            )
        )
    return records


def _expected_status_for_key(
    key: Tuple[int, int, int],
    families: List[FamilyRecord],
    expected_rows: Dict[Tuple[int, int, int], Dict[str, object]],
    enrichment: Dict[str, object],
) -> str:
    """
    NAME
        _expected_status_for_key - Determine expected/observed category.
    """
    is_expected = key in expected_rows
    has_presence_evidence = any(family.role.startswith("DEVICE_EMITTED") for family in families) or bool(enrichment)
    if is_expected and has_presence_evidence:
        return EXPECTED_STATUS_OBSERVED
    if is_expected and not has_presence_evidence:
        return EXPECTED_STATUS_MISSING
    if not is_expected and has_presence_evidence:
        return EXPECTED_STATUS_UNEXPECTED
    return EXPECTED_STATUS_UNCERTAIN


def _presence_confidence(families: List[FamilyRecord], enrichment: Dict[str, object]) -> str:
    """
    NAME
        _presence_confidence - Score passive presence confidence.
    """
    primary = sum(1 for family in families if family.role == ROLE_DEVICE_EMITTED_PRIMARY_STATUS)
    secondary = sum(
        1
        for family in families
        if family.role in (ROLE_DEVICE_EMITTED_SECONDARY_STATUS, ROLE_DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING)
    )
    if enrichment:
        return PRESENCE_HIGH
    if primary >= 1 and secondary >= 1:
        return PRESENCE_HIGH
    if primary >= 1:
        return PRESENCE_MEDIUM
    if secondary >= 1:
        return PRESENCE_LOW
    if families:
        return PRESENCE_UNCERTAIN
    return PRESENCE_NONE


def _health_for_device(
    key: Tuple[int, int, int],
    families: List[FamilyRecord],
    expected_status: str,
    enrichment: Dict[str, object],
) -> Tuple[str, str, List[str], List[str]]:
    """
    NAME
        _health_for_device - Infer bounded health state and confidence.
    """
    _ = key
    gaps: List[str] = []
    notes: List[str] = []
    if expected_status == EXPECTED_STATUS_MISSING:
        gaps.append("expected in profile but no passive presence evidence observed")
        return (HEALTH_DEGRADED, PRESENCE_HIGH, gaps, notes)
    fault_flags = enrichment.get("faultsTrue", [])
    sticky_flags = enrichment.get("stickyFaultsTrue", [])
    if isinstance(fault_flags, list) and fault_flags:
        notes.append("CTRE enrichment reported active fault fields")
        return (HEALTH_FAULT_INDICATED, PRESENCE_HIGH, gaps, notes)
    if isinstance(sticky_flags, list) and sticky_flags:
        notes.append("CTRE enrichment reported sticky fault fields")
        return (HEALTH_DEGRADED, PRESENCE_HIGH, gaps, notes)
    device_emitted = [family for family in families if family.role.startswith("DEVICE_EMITTED")]
    if len(device_emitted) >= 2:
        if not enrichment and key[0] == CTRE_MANUFACTURER:
            gaps.append("no CTRE HTTP corroboration available")
        return (HEALTH_GOOD_EVIDENCE, PRESENCE_MEDIUM if gaps else PRESENCE_HIGH, gaps, notes)
    if len(device_emitted) == 1:
        gaps.append("limited passive evidence families available")
        return (HEALTH_LIMITED, PRESENCE_MEDIUM, gaps, notes)
    if enrichment:
        gaps.append("CTRE inventory evidence available but no passive device-emitted families observed")
        return (HEALTH_LIMITED, PRESENCE_MEDIUM, gaps, notes)
    if families:
        gaps.append("traffic observed but not yet classifiable as device-emitted status")
        return (HEALTH_LIMITED, PRESENCE_LOW, gaps, notes)
    gaps.append("no device evidence available")
    return (HEALTH_UNKNOWN, PRESENCE_NONE, gaps, notes)


def _evidence_sources(
    families: List[FamilyRecord],
    enrichment: Dict[str, object],
    expected: Dict[str, object],
) -> List[str]:
    """
    NAME
        _evidence_sources - Summarize evidence-source categories for one device.
    """
    result: List[str] = []
    if families:
        result.append("passive_can")
    if enrichment:
        result.append("ctre_http")
    if expected:
        result.append("bringup_profile")
    return result


def _family_summary(family: FamilyRecord) -> str:
    """
    NAME
        _family_summary - Build a compact human-readable summary for one family.
    """
    role_text = family.role.removeprefix("DEVICE_EMITTED_").lower()
    return f"api={family.key.api_class}/{family.key.api_index} {role_text} {family.metrics.rate_hz:.1f}Hz"


def _confidence_score(confidence: str) -> int:
    """
    NAME
        _confidence_score - Map semantic confidence buckets into 0..100 scores.
    """
    mapping = {
        PRESENCE_NONE: 0,
        PRESENCE_UNCERTAIN: 25,
        PRESENCE_LOW: 45,
        PRESENCE_MEDIUM: 70,
        PRESENCE_HIGH: 95,
    }
    return int(mapping.get(confidence, 0))


def _presence_score(
    families: List[FamilyRecord],
    enrichment: Dict[str, object],
    presence_confidence: str,
) -> int:
    """
    NAME
        _presence_score - Derive a more discriminating 0..100 presence score.
    """
    primary = sum(1 for family in families if family.role == ROLE_DEVICE_EMITTED_PRIMARY_STATUS)
    secondary = sum(
        1
        for family in families
        if family.role in (ROLE_DEVICE_EMITTED_SECONDARY_STATUS, ROLE_DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING)
    )
    if enrichment and primary >= 1 and secondary >= 1:
        return 100
    if enrichment and primary >= 1:
        return 98
    if enrichment:
        return 80
    if primary >= 1 and secondary >= 1:
        return 92
    if primary >= 1:
        return 78
    if secondary >= 1:
        return 55
    if families:
        return 25
    return _confidence_score(presence_confidence)


def _inventory_score(expected_status: str, inventory_confidence: str) -> int:
    """
    NAME
        _inventory_score - Derive inventory score with status-aware adjustments.
    """
    base = _confidence_score(inventory_confidence)
    if expected_status == EXPECTED_STATUS_MISSING:
        return max(base, 90)
    if expected_status == EXPECTED_STATUS_OBSERVED:
        return max(base, 95)
    if expected_status == EXPECTED_STATUS_UNEXPECTED:
        return max(base, 70)
    return base


def _health_score(health: str, health_confidence: str) -> int:
    """
    NAME
        _health_score - Derive a 0..100 health evidence score.
    """
    base = _confidence_score(health_confidence)
    if health == HEALTH_FAULT_INDICATED:
        return 20
    if health == HEALTH_DEGRADED:
        return min(base, 40)
    if health == HEALTH_LIMITED:
        return min(max(base, 45), 65)
    if health == HEALTH_GOOD_EVIDENCE:
        return max(base, 85)
    return base
