from __future__ import annotations

"""
NAME
    runtime_state.py - Shared runtime-state query and normalization helpers.

SYNOPSIS
    from tools.common.runtime_state import runtime_device_index

DESCRIPTION
    Centralizes host-side runtime-state lookup rules so CLI, UI, and live
    topology surfaces interpret the same payload through one shared contract.
"""

from typing import Dict, List, Optional

from tools.common.motor_runtime_verdict import runtime_motor_attachment
from tools.common.profile_constants import KEY_ATTACHMENTS, KEY_DEVICES, KEY_GENERATED_AT_MS, KEY_LABEL

ATTACHMENT_KEY_TYPE = "type"
ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE = "activePresenceProbe"
ATTACHMENT_TYPE_PRESENCE_CHECK = "presenceCheck"
RUNTIME_KEY_UPDATED_AT_MS = "updatedAtMs"


def runtime_devices(payload: Dict[str, object]) -> List[Dict[str, object]]:
    """
    NAME
        runtime_devices - Return runtime device entries from one payload.
    """
    devices = payload.get(KEY_DEVICES)
    if not isinstance(devices, list):
        return []
    return [entry for entry in devices if isinstance(entry, dict)]


def runtime_device_index(runtime_payload: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    """
    NAME
        runtime_device_index - Index runtime devices by normalized label.
    """
    indexed: Dict[str, Dict[str, object]] = {}
    for entry in runtime_devices(runtime_payload):
        label = str(entry.get(KEY_LABEL, "")).strip().lower()
        if label:
            indexed[label] = entry
    return indexed


def runtime_attachment_by_type(device: Dict[str, object], attachment_type: str) -> Optional[Dict[str, object]]:
    """
    NAME
        runtime_attachment_by_type - Return the first attachment of one type.
    """
    if not isinstance(device, dict):
        return None
    attachments = device.get(KEY_ATTACHMENTS)
    if not isinstance(attachments, list):
        return None
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        if str(attachment.get(ATTACHMENT_KEY_TYPE, "")).strip() == attachment_type:
            return attachment
    return None


def runtime_active_probe_attachment(device: Dict[str, object]) -> Optional[Dict[str, object]]:
    """
    NAME
        runtime_active_probe_attachment - Return the active presence probe attachment.
    """
    return runtime_attachment_by_type(device, ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE)


def runtime_presence_check_attachment(device: Dict[str, object]) -> Optional[Dict[str, object]]:
    """
    NAME
        runtime_presence_check_attachment - Return the live presence-check attachment.
    """
    return runtime_attachment_by_type(device, ATTACHMENT_TYPE_PRESENCE_CHECK)


def runtime_device_field(device: Dict[str, object], key: str) -> object:
    """
    NAME
        runtime_device_field - Read one runtime field from top-level or motor attachment.
    """
    if not isinstance(device, dict) or not key:
        return None
    value = device.get(key)
    if value is not None:
        return value
    attachment = runtime_motor_attachment(device)
    if not isinstance(attachment, dict):
        return None
    return attachment.get(key)


def runtime_attachment_age_seconds(
    device: Dict[str, object],
    attachment_type: str,
    *,
    now_epoch_sec: Optional[float] = None,
    updated_key: str = RUNTIME_KEY_UPDATED_AT_MS,
) -> Optional[float]:
    """
    NAME
        runtime_attachment_age_seconds - Return attachment age in seconds when available.
    """
    attachment = runtime_attachment_by_type(device, attachment_type)
    if not isinstance(attachment, dict):
        return None
    updated_at_ms = attachment.get(updated_key)
    if not isinstance(updated_at_ms, (int, float)) or float(updated_at_ms) <= 0.0:
        return None
    import time

    current_sec = float(now_epoch_sec) if isinstance(now_epoch_sec, (int, float)) else time.time()
    return max(0.0, current_sec - (float(updated_at_ms) / 1000.0))


def runtime_generated_at_ms(payload: Dict[str, object]) -> Optional[int]:
    """
    NAME
        runtime_generated_at_ms - Return the top-level runtime generatedAtMs field when present.
    """
    value = payload.get(KEY_GENERATED_AT_MS)
    return int(value) if isinstance(value, int) else None
