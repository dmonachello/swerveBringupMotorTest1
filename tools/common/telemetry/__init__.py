"""Typed host-side telemetry history domain."""

from .history import TelemetryHistoryStore
from .model import (
    SignalDescriptor,
    TelemetryCatalog,
    TelemetryCaptureStatus,
    TelemetryHistoryPage,
    TelemetrySample,
)
from .wire import parse_capture_status, parse_catalog, parse_history_page

__all__ = [
    "SignalDescriptor",
    "TelemetryCatalog",
    "TelemetryCaptureStatus",
    "TelemetryHistoryPage",
    "TelemetryHistoryStore",
    "TelemetrySample",
    "parse_catalog",
    "parse_capture_status",
    "parse_history_page",
]
