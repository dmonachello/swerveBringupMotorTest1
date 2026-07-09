from __future__ import annotations

"""
NAME
    serializer.py - JSON serialization for passive discovery results.

DESCRIPTION
    Converts dataclass-based run results into stable machine-consumable JSON
    payloads for verification and later integration.
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from tools.passive_discovery_poc.constants import ENCODING_UTF8, ENRICHMENTS_KEY, FAMILIES_KEY, JSON_INDENT, RUN_METADATA_KEY, DEVICES_KEY, UNKNOWN_TRAFFIC_KEY, WARNINGS_KEY
from tools.passive_discovery_poc.models import DeviceRecord, EnrichmentRecord, FamilyRecord, RunResult


def run_result_to_dict(result: RunResult) -> Dict[str, object]:
    """
    NAME
        run_result_to_dict - Convert a run result into canonical JSON payload form.
    """
    return {
        RUN_METADATA_KEY: dict(result.run_metadata),
        DEVICES_KEY: [_device_to_dict(device) for device in result.device_records],
        FAMILIES_KEY: [_family_to_dict(family) for family in result.family_records],
        UNKNOWN_TRAFFIC_KEY: list(result.unknown_frames),
        WARNINGS_KEY: list(result.warnings),
        ENRICHMENTS_KEY: [_enrichment_to_dict(record) for record in result.enrichment_records],
    }


def write_run_result(path: str, result: RunResult) -> None:
    """
    NAME
        write_run_result - Persist one canonical JSON artifact for a run.
    """
    payload = run_result_to_dict(result)
    Path(path).write_text(json.dumps(payload, indent=JSON_INDENT), encoding=ENCODING_UTF8)


def _device_to_dict(device: DeviceRecord) -> Dict[str, object]:
    """
    NAME
        _device_to_dict - Serialize one device record.
    """
    data = asdict(device)
    data["identity"] = {
        "manufacturer": device.identity.manufacturer,
        "deviceType": device.identity.device_type,
        "deviceId": device.identity.device_id,
        "bus": device.identity.bus,
        "profileNode": device.identity.profile_node,
    }
    data["evidenceFamilyKeys"] = [
        {
            "manufacturer": key.manufacturer,
            "deviceType": key.device_type,
            "deviceId": key.device_id,
            "apiClass": key.api_class,
            "apiIndex": key.api_index,
        }
        for key in device.evidence_family_keys
    ]
    return data


def _family_to_dict(family: FamilyRecord) -> Dict[str, object]:
    """
    NAME
        _family_to_dict - Serialize one family record.
    """
    return {
        "key": {
            "manufacturer": family.key.manufacturer,
            "deviceType": family.key.device_type,
            "deviceId": family.key.device_id,
            "apiClass": family.key.api_class,
            "apiIndex": family.key.api_index,
        },
        "metrics": asdict(family.metrics),
        "role": family.role,
        "confidence": family.confidence,
        "modelHint": family.model_hint,
        "observedCanIds": list(family.observed_can_ids),
        "samplePayloads": list(family.sample_payloads),
    }


def _enrichment_to_dict(record: EnrichmentRecord) -> Dict[str, object]:
    """
    NAME
        _enrichment_to_dict - Serialize one enrichment record.
    """
    return {
        "pluginId": record.plugin_id,
        "sourceClass": record.source_class,
        "sourceMode": record.source_mode,
        "metadata": dict(record.metadata),
        "expectedRows": {
            f"{manufacturer}:{device_type}:{device_id}": dict(value)
            for (manufacturer, device_type, device_id), value in record.expected_rows.items()
        },
        "deviceEnrichment": {
            f"{manufacturer}:{device_type}:{device_id}": dict(value)
            for (manufacturer, device_type, device_id), value in record.device_enrichment.items()
        },
        "evidenceRecords": list(record.evidence_records),
        "warnings": list(record.warnings),
    }
