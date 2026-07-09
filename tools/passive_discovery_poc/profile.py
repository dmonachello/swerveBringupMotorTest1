from __future__ import annotations

"""
NAME
    profile.py - Public profile-comparison API for passive discovery.

DESCRIPTION
    Exposes explicit profile loading and re-comparison helpers for callers that
    want to apply expected inventory after an initial discovery pass.
"""

from dataclasses import replace
from typing import Dict, Tuple

from tools.passive_discovery_poc.constants import DEFAULT_BRINGUP_PROFILE_PATH, SOURCE_KIND_PROFILE
from tools.passive_discovery_poc.discovery import analyze_frames
from tools.passive_discovery_poc.models import DeviceRecord, RunResult
from tools.passive_discovery_poc.sources import RecordedEnrichmentSourcePlugin, default_source_registry


ExpectedRows = Dict[Tuple[int, int, int], Dict[str, object]]


def load_profile(profile_path: str, profile_name: str = "") -> Tuple[str, ExpectedRows]:
    """
    NAME
        load_profile - Load one bringup profile into expected-row form.
    """
    plugin = default_source_registry().get(SOURCE_KIND_PROFILE)
    record = plugin.collect({"profile_path": profile_path, "profile_name": profile_name}) if isinstance(plugin, RecordedEnrichmentSourcePlugin) else None
    if record is None:
        raise ValueError("registered profile source plugin did not implement recorded enrichment contract")
    return str(record.metadata.get("profileName", "")), dict(record.expected_rows)


def compare_profile(
    result: RunResult,
    *,
    profile_path: str,
    profile_name: str = "",
) -> RunResult:
    """
    NAME
        compare_profile - Rebuild one result with explicit expected profile rows applied.
    """
    resolved_name, expected_rows = load_profile(profile_path=profile_path, profile_name=profile_name)
    metadata = dict(result.run_metadata)
    metadata["profilePath"] = profile_path
    metadata["profileName"] = resolved_name
    compared = analyze_frames(
        result.source_frames,
        expected_rows=expected_rows,
        ctre_enrichment=result.ctre_enrichment,
        enrichment_records=list(result.enrichment_records),
        run_metadata=metadata,
    )
    return compared


def apply_profile_labels(
    result: RunResult,
    *,
    expected_rows: ExpectedRows,
) -> RunResult:
    """
    NAME
        apply_profile_labels - Apply configured labels and metadata without changing expected-state logic.
    """
    relabeled_devices = []
    for device in result.device_records:
        key = (
            device.identity.manufacturer,
            device.identity.device_type,
            device.identity.device_id,
        )
        expected = expected_rows.get(key)
        if not isinstance(expected, dict):
            relabeled_devices.append(device)
            continue
        profile_label = str(expected.get("label", "")).strip()
        model_name = str(expected.get("model", "")).strip()
        relabeled_devices.append(
            replace(
                device,
                profile_label=profile_label or device.profile_label,
                model_name=model_name if ((not device.model_name or device.model_name == "Unknown") and model_name) else device.model_name,
            )
        )
    return replace(result, device_records=tuple(relabeled_devices))


def resolve_label_rows(
    *,
    expected_rows: ExpectedRows,
    profile_name: str = "",
    fallback_profile_path: str = DEFAULT_BRINGUP_PROFILE_PATH,
) -> ExpectedRows:
    """
    NAME
        resolve_label_rows - Resolve label rows for display without forcing expected-state comparison.
    """
    if expected_rows:
        return dict(expected_rows)
    try:
        _resolved_profile, label_rows = load_profile(
            profile_path=fallback_profile_path,
            profile_name=profile_name,
        )
    except ValueError:
        return {}
    return dict(label_rows)
