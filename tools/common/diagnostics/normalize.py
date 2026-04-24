from __future__ import annotations

"""
NAME
    normalize.py - Shared diagnostics normalization for runtime attachments.
"""

from typing import Any, Dict, List


KEY_DEVICES = "devices"
KEY_LABEL = "label"
KEY_ATTACHMENTS = "attachments"
KEY_TYPE = "type"
KEY_CMD_DUTY = "cmdDuty"
KEY_APPLIED_DUTY = "appliedDuty"
KEY_MOTOR_CURRENT_A = "motorCurrentA"

KEY_COUNT = "count"
KEY_WITH_CURRENT = "withCurrent"
KEY_AVG_CURRENT_A = "avgCurrentA"


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def normalize_device_attachments(runtime_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    NAME
        normalize_device_attachments - Flatten runtime device attachment telemetry.
    """
    devices = runtime_payload.get(KEY_DEVICES, []) if isinstance(runtime_payload, dict) else []
    if not isinstance(devices, list):
        return []
    rows: List[Dict[str, Any]] = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        label = str(device.get(KEY_LABEL, "")).strip()
        attachments = device.get(KEY_ATTACHMENTS, [])
        if not isinstance(attachments, list):
            continue
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            rows.append(
                {
                    KEY_LABEL: label,
                    KEY_TYPE: str(attachment.get(KEY_TYPE, "")).strip(),
                    KEY_CMD_DUTY: _as_float(attachment.get(KEY_CMD_DUTY)),
                    KEY_APPLIED_DUTY: _as_float(attachment.get(KEY_APPLIED_DUTY)),
                    KEY_MOTOR_CURRENT_A: _as_float(attachment.get(KEY_MOTOR_CURRENT_A)),
                }
            )
    return rows


def summarize_attachment_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    NAME
        summarize_attachment_metrics - Build compact aggregate diagnostics summary.
    """
    count = len(rows)
    current_values = [row.get(KEY_MOTOR_CURRENT_A) for row in rows if isinstance(row.get(KEY_MOTOR_CURRENT_A), float)]
    with_current = len(current_values)
    avg_current = sum(current_values) / with_current if with_current > 0 else 0.0
    return {
        KEY_COUNT: count,
        KEY_WITH_CURRENT: with_current,
        KEY_AVG_CURRENT_A: avg_current,
    }

