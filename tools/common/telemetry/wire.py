"""
NAME
    wire.py - Strict REST-to-domain telemetry parsing.

DESCRIPTION
    Validates versioned JSON payloads at the transport boundary so graph and
    capture code consume immutable domain records rather than dictionaries.
"""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from .constants import TELEMETRY_SCHEMA_VERSION
from .model import (
    ClockDescriptor,
    SignalDescriptor,
    TelemetryCatalog,
    TelemetryCaptureStatus,
    TelemetryHistoryPage,
    TelemetrySample,
)


def parse_catalog(payload: Mapping[str, Any]) -> TelemetryCatalog:
    """Parse and validate one telemetry catalog payload."""
    _require_schema(payload)
    raw_signals = payload.get("signals")
    if not isinstance(raw_signals, list):
        raise ValueError("telemetry catalog signals must be a list")
    signals = tuple(_parse_descriptor(item) for item in raw_signals)
    raw_clock = payload.get("clockDescriptor")
    if not isinstance(raw_clock, Mapping):
        raise ValueError("telemetry clockDescriptor must be an object")
    return TelemetryCatalog(
        schema_version=_integer(payload, "schemaVersion"),
        history_generation_id=_text(payload, "historyGenerationId"),
        source_instance_id=_text(payload, "sourceInstanceId"),
        revision=_integer(payload, "catalogRevision"),
        clock=ClockDescriptor(
            clock_id=_text(raw_clock, "clockId"),
            kind=_text(raw_clock, "kind"),
            ticks_per_second=_integer(raw_clock, "ticksPerSecond"),
        ),
        signals=signals,
    )


def parse_history_page(payload: Mapping[str, Any]) -> TelemetryHistoryPage:
    """Parse and validate one cursor-addressed telemetry history page."""
    _require_schema(payload)
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        raise ValueError("telemetry history records must be a list")
    records = tuple(_parse_sample(item) for item in raw_records)
    return TelemetryHistoryPage(
        schema_version=_integer(payload, "schemaVersion"),
        history_generation_id=_text(payload, "historyGenerationId"),
        source_instance_id=_text(payload, "sourceInstanceId"),
        oldest_sequence=_integer(payload, "oldestSequence"),
        next_sequence=_integer(payload, "nextSequence"),
        has_more=_boolean(payload, "hasMore"),
        cursor_expired=_boolean(payload, "cursorExpired"),
        robot_reply_us=_integer(payload, "robotReplyUs"),
        records=records,
    )


def parse_capture_status(payload: Mapping[str, Any]) -> TelemetryCaptureStatus:
    """Parse robot-local capture state from its REST boundary."""
    return TelemetryCaptureStatus(
        ok=_boolean(payload, "ok"),
        recording=_boolean(payload, "recording"),
        path=_text(payload, "path"),
        storage=_text(payload, "storage"),
        dropped_records=_integer(payload, "droppedRecords"),
        last_stop_reason=_text(payload, "lastStopReason"),
        message=_text(payload, "message"),
        auto_match_enabled=_boolean(payload, "autoMatchEnabled"),
        auto_exception_enabled=_boolean(payload, "autoExceptionEnabled"),
    )


def _parse_descriptor(value: Any) -> SignalDescriptor:
    if not isinstance(value, Mapping):
        raise ValueError("telemetry signal descriptor must be an object")
    return SignalDescriptor(
        signal_definition_key=_text(value, "signalDefinitionKey"),
        signal_id=_text(value, "signalId"),
        source_instance_id=_text(value, "sourceInstanceId"),
        subject_key=_text(value, "subjectKey"),
        device_label=_text(value, "deviceLabel"),
        signal_name=_text(value, "signalName"),
        value_kind=_text(value, "valueKind"),
        unit=_text(value, "unit"),
        unit_symbol=_text(value, "unitSymbol"),
        engineering_dimension=_text(value, "engineeringDimension"),
        nominal_cadence_us=_integer(value, "nominalCadenceUs"),
        stale_after_us=_integer(value, "staleAfterUs"),
        graphable=_boolean(value, "graphable"),
    )


def _parse_sample(value: Any) -> TelemetrySample:
    if not isinstance(value, Mapping):
        raise ValueError("telemetry sample must be an object")
    return TelemetrySample(
        sequence=_integer(value, "sequence"),
        signal_id=_text(value, "signalId"),
        source_timestamp_us=_integer(value, "sourceTimestampUs"),
        numeric_value=_number(value, "numericValue"),
        quality=_text(value, "quality"),
    )


def _require_schema(payload: Mapping[str, Any]) -> None:
    version = _integer(payload, "schemaVersion")
    if version != TELEMETRY_SCHEMA_VERSION:
        raise ValueError(f"unsupported telemetry schema version: {version}")


def _text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"telemetry field {key} must be text")
    return value


def _integer(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"telemetry field {key} must be an integer")
    return value


def _number(payload: Mapping[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"telemetry field {key} must be numeric")
    return float(value)


def _boolean(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"telemetry field {key} must be boolean")
    return value
