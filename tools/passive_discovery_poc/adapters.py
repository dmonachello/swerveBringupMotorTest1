from __future__ import annotations

"""
NAME
    adapters.py - Integration adapters from discovery results into device objects.

DESCRIPTION
    Provides explicit helpers to create or update existing project-facing device
    objects from passive discovery output while preserving evidence provenance.
"""

from typing import Dict, Mapping, Optional

from tools.passive_discovery_poc.models import AdapterContext, DeviceRecord, RunResult


def update_or_create_device(
    existing_device: Optional[Dict[str, object]],
    discovered_device: DeviceRecord,
    *,
    context: AdapterContext,
) -> Dict[str, object]:
    """
    NAME
        update_or_create_device - Create or update one device object from discovery output.
    """
    device = dict(existing_device or {})
    device["vendor"] = discovered_device.manufacturer_name
    device["deviceType"] = discovered_device.device_type_name
    device["canId"] = discovered_device.identity.device_id
    device["present"] = discovered_device.expected_status != "missing" and discovered_device.presence_score > 0
    device["label"] = _label_for_device(existing_device=device, discovered_device=discovered_device, context=context)
    device["note"] = "; ".join(discovered_device.notes[:2]) if discovered_device.notes else ""
    attachments = list(device.get("attachments", [])) if isinstance(device.get("attachments"), list) else []
    attachments = _replace_attachment(
        attachments=attachments,
        new_attachment={
            "type": context.attachment_type,
            "source": context.source_name,
            "expectedStatus": discovered_device.expected_status,
            "presenceConfidence": discovered_device.presence_confidence,
            "presenceScore": discovered_device.presence_score,
            "inventoryConfidence": discovered_device.inventory_confidence,
            "inventoryScore": discovered_device.inventory_score,
            "healthConfidence": discovered_device.health_confidence,
            "healthScore": discovered_device.health_score,
            "health": discovered_device.health,
            "evidenceSources": list(discovered_device.evidence_sources),
            "evidenceGaps": list(discovered_device.evidence_gaps),
            "notes": list(discovered_device.notes),
            "model": discovered_device.model_name,
            "profileNode": discovered_device.identity.profile_node,
            "bus": discovered_device.identity.bus,
            "evidenceFamilies": list(discovered_device.evidence_family_summaries) if context.include_family_evidence else [],
        },
        attachment_type=context.attachment_type,
    )
    device["attachments"] = attachments
    return device


def apply_discovery_to_devices(
    existing_devices: Mapping[str, Dict[str, object]],
    result: RunResult,
    *,
    context: AdapterContext,
) -> Dict[str, Dict[str, object]]:
    """
    NAME
        apply_discovery_to_devices - Batch-apply discovery output to device objects.
    """
    updated = {str(label): dict(device) for label, device in existing_devices.items()}
    for discovered_device in result.device_records:
        label = _label_for_batch(discovered_device=discovered_device, context=context)
        updated[label] = update_or_create_device(
            updated.get(label),
            discovered_device,
            context=context,
        )
    return updated


def _replace_attachment(
    *,
    attachments,
    new_attachment: Dict[str, object],
    attachment_type: str,
) -> list:
    """
    NAME
        _replace_attachment - Replace one attachment by type while preserving others.
    """
    remaining = [attachment for attachment in attachments if not (isinstance(attachment, dict) and attachment.get("type") == attachment_type)]
    remaining.append(new_attachment)
    return remaining


def _label_for_device(
    *,
    existing_device: Dict[str, object],
    discovered_device: DeviceRecord,
    context: AdapterContext,
) -> str:
    """
    NAME
        _label_for_device - Resolve the preferred label for one adapted device.
    """
    existing_label = str(existing_device.get("label", "")).strip()
    if existing_label:
        return existing_label
    if discovered_device.profile_label:
        return discovered_device.profile_label
    if discovered_device.model_name and discovered_device.model_name != "Unknown":
        return f"{discovered_device.model_name} {discovered_device.identity.device_id}"
    return f"{context.label_fallback_prefix}_{discovered_device.identity.manufacturer}_{discovered_device.identity.device_type}_{discovered_device.identity.device_id}"


def _label_for_batch(*, discovered_device: DeviceRecord, context: AdapterContext) -> str:
    """
    NAME
        _label_for_batch - Resolve the batch dictionary key for one discovered device.
    """
    if discovered_device.profile_label:
        return discovered_device.profile_label
    if discovered_device.model_name and discovered_device.model_name != "Unknown":
        return f"{discovered_device.model_name} {discovered_device.identity.device_id}"
    return f"{context.label_fallback_prefix}_{discovered_device.identity.manufacturer}_{discovered_device.identity.device_type}_{discovered_device.identity.device_id}"
