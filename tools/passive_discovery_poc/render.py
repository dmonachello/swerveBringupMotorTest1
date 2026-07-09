from __future__ import annotations

"""
NAME
    render.py - Minimal terminal rendering for passive discovery results.

DESCRIPTION
    Produces compact human-readable summaries for interactive verification while
    keeping the canonical JSON artifact machine-oriented.
"""

from typing import Iterable, List

from tools.passive_discovery_poc.constants import (
    RUN_METADATA_SOURCE_DIAGNOSTICS,
    TABLE_COL_DEVICE,
    TABLE_COL_EVIDENCE,
    TABLE_COL_EXPECTED,
    TABLE_COL_HEALTH,
    TABLE_COL_HEALTH_SCORE,
    TABLE_COL_INVENTORY_SCORE,
    TABLE_COL_PRESENCE,
    TABLE_COL_PRESENCE_SCORE,
    TABLE_COL_SOURCES,
)
from tools.passive_discovery_poc.models import DeviceRecord, FamilyRecord


def render_device_table(devices: Iterable[DeviceRecord]) -> str:
    """
    NAME
        render_device_table - Render the default device/evidence summary table.
    """
    ordered_devices = sorted(
        list(devices),
        key=lambda device: (
            -int(device.presence_score),
            -int(device.inventory_score),
            -int(device.health_score),
            _device_label(device).lower(),
        ),
    )
    rows: List[List[str]] = [[
        TABLE_COL_DEVICE,
        TABLE_COL_EXPECTED,
        TABLE_COL_PRESENCE,
        TABLE_COL_PRESENCE_SCORE,
        TABLE_COL_HEALTH,
        TABLE_COL_HEALTH_SCORE,
        TABLE_COL_INVENTORY_SCORE,
        TABLE_COL_SOURCES,
        TABLE_COL_EVIDENCE,
    ]]
    for device in ordered_devices:
        evidence = ", ".join(device.evidence_family_summaries[:2])
        if not evidence:
            evidence = "-"
        sources = ",".join(device.evidence_sources)
        if not sources:
            sources = "-"
        label = _device_label(device)
        rows.append(
            [
                label,
                device.expected_status,
                device.presence_confidence,
                str(device.presence_score),
                device.health,
                str(device.health_score),
                str(device.inventory_score),
                sources,
                evidence,
            ]
        )
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    lines: List[str] = []
    for row_index, row in enumerate(rows):
        padded = "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))
        lines.append(padded)
        if row_index == 0:
            lines.append("  ".join("-" * widths[index] for index in range(len(widths))))
    return "\n".join(lines)


def render_summary_table(result_or_devices) -> str:
    """
    NAME
        render_summary_table - Public summary-table renderer for results or device iterables.
    """
    if hasattr(result_or_devices, "device_records"):
        return render_device_table(result_or_devices.device_records)
    return render_device_table(result_or_devices)


def render_full_dump(devices: Iterable[DeviceRecord], families: Iterable[FamilyRecord], warnings: Iterable[str]) -> str:
    """
    NAME
        render_full_dump - Render a richer textual dump when explicitly requested.
    """
    lines: List[str] = []
    warnings_list = list(warnings)
    if warnings_list:
        lines.append("Warnings:")
        for warning in warnings_list:
            lines.append(f"- {warning}")
        lines.append("")
    lines.append("Devices:")
    for device in devices:
        label = _device_label(device)
        lines.append(
            f"- {label} expected={device.expected_status} presence={device.presence_confidence} health={device.health} sources={','.join(device.evidence_sources)}"
        )
        if device.evidence_family_summaries:
            lines.append(f"  evidence={'; '.join(device.evidence_family_summaries[:4])}")
        if device.evidence_gaps:
            lines.append(f"  gaps={'; '.join(device.evidence_gaps)}")
        if device.notes:
            lines.append(f"  notes={'; '.join(device.notes)}")
    lines.append("")
    lines.append("Families:")
    for family in families:
        lines.append(
            f"- ({family.key.manufacturer},{family.key.device_type},{family.key.device_id},{family.key.api_class},{family.key.api_index}) role={family.role} rateHz={family.metrics.rate_hz:.2f} count={family.metrics.count}"
        )
    return "\n".join(lines)


def render_full_dump_result(result) -> str:
    """
    NAME
        render_full_dump_result - Public full-dump renderer for one result object.
    """
    text = render_full_dump(result.device_records, result.family_records, result.warnings)
    extra_lines: List[str] = []
    source_diagnostics = result.run_metadata.get(RUN_METADATA_SOURCE_DIAGNOSTICS, {})
    if isinstance(source_diagnostics, dict) and source_diagnostics:
        extra_lines.append("")
        extra_lines.append("SourceDiagnostics:")
        for key in sorted(source_diagnostics.keys()):
            extra_lines.append(f"- {key}={source_diagnostics[key]}")
    if getattr(result, "enrichment_records", None):
        extra_lines.append("")
        extra_lines.append("Enrichments:")
        for record in result.enrichment_records:
            extra_lines.append(
                f"- {record.plugin_id} evidenceRecords={len(record.evidence_records)} warnings={len(record.warnings)}"
            )
    return text + "\n".join(extra_lines)


def _device_label(device: DeviceRecord) -> str:
    """
    NAME
        _device_label - Build the preferred human-facing label for one device row.
    """
    if device.profile_label:
        return device.profile_label
    if device.model_name and device.model_name != "Unknown":
        return f"{device.model_name} {device.identity.device_id}"
    return f"{device.manufacturer_name}:{device.device_type_name}:{device.identity.device_id}"
