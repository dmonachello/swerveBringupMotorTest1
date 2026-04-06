from __future__ import annotations

"""
NAME
    visibility_provider.py - Multi-analyzer visibility matrix provider.

SYNOPSIS
    from tools.can_nt.visibility_provider import VisibilityProvider

DESCRIPTION
    Maintains per-source device metrics and produces visibility snapshots
    for CLI and UI consumers.
"""

from dataclasses import dataclass, field
import threading
from typing import Dict, List, Optional, Tuple, Iterable

from tools.can_nt.can_nt_publish import decode_frc_ext_id
from tools.can_nt.visibility_constants import (
    VIS_KEY_AGE_MS,
    VIS_KEY_ARB_PREFIX,
    VIS_KEY_AVAILABLE,
    VIS_KEY_DEVICE,
    VIS_KEY_DEVICES,
    VIS_KEY_DEVICES_SHOWN,
    VIS_KEY_FRAMES_PER_SEC,
    VIS_KEY_ID,
    VIS_KEY_KEY,
    VIS_KEY_LABEL,
    VIS_KEY_LAST_SEEN_MS,
    VIS_KEY_METRICS,
    VIS_KEY_MSG_COUNT,
    VIS_KEY_SCOPE,
    VIS_KEY_SEPARATOR,
    VIS_KEY_SOURCE,
    VIS_KEY_SOURCES,
    VIS_KEY_SOURCES_COUNT,
    VIS_KEY_TIMEOUT_MS,
    VIS_KEY_TS_MS,
    VIS_KEY_UNEXPECTED,
    VIS_KEY_VISIBLE_ALL,
    VIS_KEY_VISIBLE_NONE,
    VIS_KEY_VISIBLE_SOME,
    VIS_KEY_VISIBILITY,
    VIS_SCOPE_BOTH,
    VIS_SCOPE_EXPECTED,
    VIS_SCOPE_OBSERVED,
    VIS_FLOAT_ZERO,
    VIS_INT_ONE,
    VIS_INT_ZERO,
    VIS_MS_PER_SEC,
    VIS_VISIBLE_FALSE,
    VIS_VISIBLE_TRUE,
    VIS_VISIBLE_UNKNOWN,
    VIS_EMPTY_STRING,
    VIS_HEX_PREFIX,
    VIS_HEX_FORMAT,
    VIS_RETENTION_MS_DEFAULT,
    VIS_TIMEOUT_MS_DEFAULT,
)


@dataclass
class SourceInfo:
    """
    NAME
        SourceInfo - Source metadata for visibility computation.
    """

    source_id: str
    label: str
    available: bool = True
    timeout_ms: int = VIS_TIMEOUT_MS_DEFAULT


@dataclass
class MetricState:
    """
    NAME
        MetricState - Per-device, per-source rolling metrics.
    """

    last_seen_ms: int = VIS_INT_ZERO
    msg_count: int = VIS_INT_ZERO
    frames_per_sec: float = VIS_FLOAT_ZERO
    last_tick_ms: int = VIS_INT_ZERO
    last_tick_count: int = VIS_INT_ZERO


@dataclass
class DeviceState:
    """
    NAME
        DeviceState - Aggregated device tracking state.
    """

    key: str
    label: str = VIS_EMPTY_STRING
    unexpected: bool = False
    last_seen_ms: int = VIS_INT_ZERO
    metrics: Dict[str, MetricState] = field(default_factory=dict)


def _device_key_from_ids(mfg: int, dtype: int, device_id: int) -> str:
    return (
        str(mfg)
        + VIS_KEY_SEPARATOR
        + str(dtype)
        + VIS_KEY_SEPARATOR
        + str(device_id)
    )


def _device_key_from_arb(arb_id: int) -> str:
    return VIS_KEY_ARB_PREFIX + VIS_HEX_PREFIX + format(arb_id, VIS_HEX_FORMAT)


class VisibilityProvider:
    """
    NAME
        VisibilityProvider - In-process visibility matrix provider.
    """

    def __init__(
        self,
        *,
        timeout_ms: int = VIS_TIMEOUT_MS_DEFAULT,
        observed_retention_ms: int = VIS_RETENTION_MS_DEFAULT,
    ) -> None:
        self._sources: Dict[str, SourceInfo] = {}
        self._source_order: List[str] = []
        self._devices: Dict[str, DeviceState] = {}
        self._expected_keys: Dict[str, str] = {}
        self._timeout_ms = int(timeout_ms)
        self._observed_retention_ms = int(observed_retention_ms)
        self._lock = threading.Lock()

    def set_sources(self, sources: Iterable[SourceInfo]) -> None:
        """
        NAME
            set_sources - Replace sources and ordering.
        """
        with self._lock:
            self._sources = {}
            self._source_order = []
            for src in sources:
                self._sources[src.source_id] = src
                self._source_order.append(src.source_id)

    def set_expected_devices(self, devices: Iterable[Tuple[str, str]]) -> None:
        """
        NAME
            set_expected_devices - Replace expected device keys and labels.

        PARAMETERS
            devices: Iterable of (key, label) tuples.
        """
        with self._lock:
            self._expected_keys = {}
            for key, label in devices:
                self._expected_keys[key] = label
                state = self._devices.get(key)
                if state is None:
                    self._devices[key] = DeviceState(key=key, label=label, unexpected=False)
                else:
                    state.label = label or state.label
                    state.unexpected = False

    def set_source_available(self, source_id: str, available: bool, ts_ms: int) -> None:
        """
        NAME
            set_source_available - Update source availability.
        """
        with self._lock:
            src = self._sources.get(source_id)
            if src is None:
                return
            src.available = bool(available)
            if not src.available:
                for state in self._devices.values():
                    metric = state.metrics.get(source_id)
                    if metric is not None:
                        metric.last_tick_ms = ts_ms
                        metric.last_tick_count = metric.msg_count

    def ingest_frame(
        self,
        source_id: str,
        arb_id: int,
        ts_ms: int,
        decoded_key: Optional[str] = None,
        label: Optional[str] = None,
    ) -> None:
        """
        NAME
            ingest_frame - Record a frame for a source.
        """
        with self._lock:
            if source_id not in self._sources:
                return
            key = decoded_key
            if not key:
                try:
                    mfg, dtype, did = decode_frc_ext_id(arb_id)
                    key = _device_key_from_ids(mfg, dtype, did)
                except Exception:
                    key = _device_key_from_arb(arb_id)
            if not key:
                return
            state = self._devices.get(key)
            if state is None:
                state = DeviceState(key=key, label=label or VIS_EMPTY_STRING, unexpected=True)
                self._devices[key] = state
            if label:
                state.label = label
            if key in self._expected_keys:
                state.unexpected = False
                if not state.label:
                    state.label = self._expected_keys.get(key, VIS_EMPTY_STRING)
            metric = state.metrics.get(source_id)
            if metric is None:
                metric = MetricState()
                state.metrics[source_id] = metric
            metric.last_seen_ms = ts_ms
            metric.msg_count += VIS_INT_ONE
            state.last_seen_ms = max(state.last_seen_ms, ts_ms)

    def tick(self, now_ms: int) -> None:
        """
        NAME
            tick - Update rolling frames-per-second metrics.
        """
        with self._lock:
            for state in self._devices.values():
                for _source_id, metric in state.metrics.items():
                    if metric.last_tick_ms <= VIS_INT_ZERO:
                        metric.last_tick_ms = now_ms
                        metric.last_tick_count = metric.msg_count
                        continue
                    elapsed_ms = now_ms - metric.last_tick_ms
                    if elapsed_ms <= VIS_INT_ZERO:
                        continue
                    delta = metric.msg_count - metric.last_tick_count
                    metric.frames_per_sec = float(delta) / (float(elapsed_ms) / VIS_MS_PER_SEC)
                    metric.last_tick_ms = now_ms
                    metric.last_tick_count = metric.msg_count

    def _device_in_scope(self, state: DeviceState, scope: str, now_ms: int) -> bool:
        if scope == VIS_SCOPE_EXPECTED:
            return state.key in self._expected_keys
        if scope == VIS_SCOPE_OBSERVED:
            if state.key in self._expected_keys:
                return False
            if state.last_seen_ms <= VIS_INT_ZERO:
                return False
            return (now_ms - state.last_seen_ms) <= self._observed_retention_ms
        if scope == VIS_SCOPE_BOTH:
            if state.key in self._expected_keys:
                return True
            if state.last_seen_ms <= VIS_INT_ZERO:
                return False
            return (now_ms - state.last_seen_ms) <= self._observed_retention_ms
        return False

    def snapshot(self, scope: str, now_ms: int) -> Dict[str, object]:
        """
        NAME
            snapshot - Return the full visibility matrix snapshot.
        """
        scope_value = scope if scope else VIS_SCOPE_BOTH
        with self._lock:
            sources_out = [
                {
                    VIS_KEY_ID: src.source_id,
                    VIS_KEY_LABEL: src.label,
                    VIS_KEY_AVAILABLE: src.available,
                }
                for src in (self._sources[sid] for sid in self._source_order if sid in self._sources)
            ]
            devices_out: List[Dict[str, object]] = []
            for key, state in sorted(self._devices.items(), key=lambda kv: (kv[1].label or kv[0], kv[0])):
                if not self._device_in_scope(state, scope_value, now_ms):
                    continue
                visibility: Dict[str, Optional[bool]] = {}
                metrics_out: Dict[str, Optional[Dict[str, object]]] = {}
                for sid in self._source_order:
                    src = self._sources.get(sid)
                    if src is None:
                        continue
                    metric = state.metrics.get(sid)
                    if not src.available:
                        visibility[sid] = VIS_VISIBLE_UNKNOWN
                        metrics_out[sid] = None
                        continue
                    if metric is None or metric.last_seen_ms <= VIS_INT_ZERO:
                        visibility[sid] = VIS_VISIBLE_FALSE
                        metrics_out[sid] = {
                            VIS_KEY_AGE_MS: None,
                            VIS_KEY_FRAMES_PER_SEC: VIS_FLOAT_ZERO,
                            VIS_KEY_MSG_COUNT: VIS_INT_ZERO,
                            VIS_KEY_LAST_SEEN_MS: None,
                        }
                        continue
                    age_ms = max(VIS_INT_ZERO, now_ms - metric.last_seen_ms)
                    visibility[sid] = (
                        VIS_VISIBLE_TRUE if age_ms <= src.timeout_ms else VIS_VISIBLE_FALSE
                    )
                    metrics_out[sid] = {
                        VIS_KEY_AGE_MS: age_ms,
                        VIS_KEY_FRAMES_PER_SEC: metric.frames_per_sec,
                        VIS_KEY_MSG_COUNT: metric.msg_count,
                        VIS_KEY_LAST_SEEN_MS: metric.last_seen_ms,
                    }
                devices_out.append(
                    {
                        VIS_KEY_KEY: state.key,
                        VIS_KEY_LABEL: state.label,
                        VIS_KEY_VISIBILITY: visibility,
                        VIS_KEY_METRICS: metrics_out,
                        VIS_KEY_UNEXPECTED: bool(state.unexpected),
                    }
                )
        return {
            VIS_KEY_SOURCES: sources_out,
            VIS_KEY_DEVICES: devices_out,
            VIS_KEY_TIMEOUT_MS: self._timeout_ms,
            VIS_KEY_TS_MS: now_ms,
            VIS_KEY_SCOPE: scope_value,
        }

    def snapshot_device(self, selector: str, now_ms: int) -> Optional[Dict[str, object]]:
        """
        NAME
            snapshot_device - Return a per-device visibility snapshot.
        """
        if not selector:
            return None
        sel_lower = selector.strip().lower()
        with self._lock:
            state = None
            for key, entry in self._devices.items():
                if key.lower() == sel_lower or entry.label.strip().lower() == sel_lower:
                    state = entry
                    break
            if state is None:
                return None
            sources_out = []
            for sid in self._source_order:
                src = self._sources.get(sid)
                if src is None:
                    continue
                metric = state.metrics.get(sid)
                if not src.available:
                    sources_out.append(
                        {
                            VIS_KEY_ID: src.source_id,
                            VIS_KEY_LABEL: src.label,
                            VIS_KEY_AVAILABLE: False,
                            VIS_KEY_VISIBILITY: VIS_VISIBLE_UNKNOWN,
                        }
                    )
                    continue
                if metric is None or metric.last_seen_ms <= VIS_INT_ZERO:
                    sources_out.append(
                        {
                            VIS_KEY_ID: src.source_id,
                            VIS_KEY_LABEL: src.label,
                            VIS_KEY_AVAILABLE: True,
                            VIS_KEY_VISIBILITY: VIS_VISIBLE_FALSE,
                            VIS_KEY_AGE_MS: None,
                            VIS_KEY_FRAMES_PER_SEC: VIS_FLOAT_ZERO,
                            VIS_KEY_MSG_COUNT: VIS_INT_ZERO,
                            VIS_KEY_LAST_SEEN_MS: None,
                        }
                    )
                    continue
                age_ms = max(VIS_INT_ZERO, now_ms - metric.last_seen_ms)
                visible = VIS_VISIBLE_TRUE if age_ms <= src.timeout_ms else VIS_VISIBLE_FALSE
                sources_out.append(
                    {
                        VIS_KEY_ID: src.source_id,
                        VIS_KEY_LABEL: src.label,
                        VIS_KEY_AVAILABLE: True,
                        VIS_KEY_VISIBILITY: visible,
                        VIS_KEY_AGE_MS: age_ms,
                        VIS_KEY_FRAMES_PER_SEC: metric.frames_per_sec,
                        VIS_KEY_MSG_COUNT: metric.msg_count,
                        VIS_KEY_LAST_SEEN_MS: metric.last_seen_ms,
                    }
                )
        return {
            VIS_KEY_DEVICE: {VIS_KEY_KEY: state.key, VIS_KEY_LABEL: state.label},
            VIS_KEY_SOURCES: sources_out,
        }

    def summary(self, scope: str, now_ms: int) -> Dict[str, object]:
        """
        NAME
            summary - Return visibility summary counts.
        """
        scope_value = scope if scope else VIS_SCOPE_BOTH
        with self._lock:
            visible_all = VIS_INT_ZERO
            visible_some = VIS_INT_ZERO
            visible_none = VIS_INT_ZERO
            total = VIS_INT_ZERO
            for _key, state in self._devices.items():
                if not self._device_in_scope(state, scope_value, now_ms):
                    continue
                total += VIS_INT_ONE
                avail_sources = [self._sources[sid] for sid in self._source_order if sid in self._sources]
                if not avail_sources:
                    visible_none += VIS_INT_ONE
                    continue
                vis_values: List[Optional[bool]] = []
                for src in avail_sources:
                    if not src.available:
                        continue
                    metric = state.metrics.get(src.source_id)
                    if metric is None or metric.last_seen_ms <= VIS_INT_ZERO:
                        vis_values.append(VIS_VISIBLE_FALSE)
                    else:
                        age_ms = max(VIS_INT_ZERO, now_ms - metric.last_seen_ms)
                        vis_values.append(VIS_VISIBLE_TRUE if age_ms <= src.timeout_ms else VIS_VISIBLE_FALSE)
                if not vis_values:
                    visible_none += VIS_INT_ONE
                    continue
                if all(v is VIS_VISIBLE_TRUE for v in vis_values):
                    visible_all += VIS_INT_ONE
                elif any(v is VIS_VISIBLE_TRUE for v in vis_values):
                    visible_some += VIS_INT_ONE
                else:
                    visible_none += VIS_INT_ONE
        return {
            VIS_KEY_SOURCES_COUNT: len(self._sources),
            VIS_KEY_DEVICES_SHOWN: total,
            VIS_KEY_VISIBLE_ALL: visible_all,
            VIS_KEY_VISIBLE_SOME: visible_some,
            VIS_KEY_VISIBLE_NONE: visible_none,
        }
