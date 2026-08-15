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
from collections import deque
import threading
import math
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from tools.can_nt.can_frc_defs import decode_frc_ext_id_full
from tools.common.can_id import decode_frc_ext_id as decode_shared_frc_ext_id
from tools.passive_discovery_poc.models import NormalizedFrame
from tools.can_nt.visibility_constants import (
    VIS_KEY_AGE_MS,
    VIS_KEY_API_CLASS,
    VIS_KEY_API_INDEX,
    VIS_KEY_ARB_HEX,
    VIS_KEY_ARB_ID,
    VIS_KEY_ARB_PREFIX,
    VIS_KEY_AVAILABLE,
    VIS_KEY_DATA_PAGE,
    VIS_KEY_DEVICE,
    VIS_KEY_DEVICES,
    VIS_KEY_DEVICES_SHOWN,
    VIS_KEY_FRAMES_PER_SEC,
    VIS_KEY_ID,
    VIS_KEY_IDENTITY,
    VIS_KEY_KEY,
    VIS_KEY_LABEL,
    VIS_KEY_LAST_SEEN_MS,
    VIS_KEY_METRICS,
    VIS_KEY_MSG_COUNT,
    VIS_KEY_PF,
    VIS_KEY_PGN,
    VIS_KEY_PRIORITY,
    VIS_KEY_PS,
    VIS_KEY_RAW_IDS,
    VIS_KEY_RESERVED,
    VIS_KEY_SA,
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
    VIS_FLOAT_ONE,
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
    VIS_RECENT_FRAME_HISTORY_DEFAULT,
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
    first_seen_ms: int = VIS_INT_ZERO
    msg_count: int = VIS_INT_ZERO
    frames_per_sec: float = VIS_FLOAT_ZERO
    last_tick_ms: int = VIS_INT_ZERO
    last_tick_count: int = VIS_INT_ZERO


@dataclass
class RawIdState:
    """
    NAME
        RawIdState - Per-arbitration-ID rolling metrics for one visibility device row.
    """

    arb_id: int
    last_seen_ms: int = VIS_INT_ZERO
    first_seen_ms: int = VIS_INT_ZERO
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
    identity_key: str = VIS_EMPTY_STRING
    expected: bool = False
    unexpected: bool = False
    last_seen_ms: int = VIS_INT_ZERO
    metrics: Dict[str, MetricState] = field(default_factory=dict)
    raw_ids: Dict[int, RawIdState] = field(default_factory=dict)


DISCOVERED_LABEL_SEPARATOR = "_"
DISCOVERED_LABEL_COLLISION_SUFFIX_SEPARATOR = "_"
DISCOVERED_LABEL_COLLISION_SUFFIX_START = 2
DISCOVERED_LABEL_PARTS = 3
DISCOVERED_LABEL_BASE = 10
DISCOVERED_LABEL_CAN_ID_WIDTH = 2
DISCOVERED_LABEL_ARB_PREFIX = "UNKNOWN_ARBITRATION"
DISCOVERED_LABEL_MANUFACTURER_UNKNOWN_PREFIX = "MFG"
DISCOVERED_LABEL_DEVICE_TYPE_UNKNOWN_PREFIX = "DEVICETYPE"
DISCOVERED_LABEL_MANUFACTURER_NI = "NI"
DISCOVERED_LABEL_MANUFACTURER_CTRE = "CTRE"
DISCOVERED_LABEL_MANUFACTURER_REV = "REV"
DISCOVERED_LABEL_DEVICE_TYPE_ROBOTCONTROLLER = "ROBOTCONTROLLER"
DISCOVERED_LABEL_DEVICE_TYPE_MOTORCONTROLLER = "MOTORCONTROLLER"
DISCOVERED_LABEL_DEVICE_TYPE_GYRO = "GYRO"
DISCOVERED_LABEL_DEVICE_TYPE_ENCODER = "ENCODER"
DISCOVERED_LABEL_DEVICE_TYPE_POWER = "POWER"
DISCOVERED_LABEL_MANUFACTURER_NAMES = {
    1: DISCOVERED_LABEL_MANUFACTURER_NI,
    4: DISCOVERED_LABEL_MANUFACTURER_CTRE,
    5: DISCOVERED_LABEL_MANUFACTURER_REV,
}
DISCOVERED_LABEL_DEVICE_TYPE_NAMES = {
    1: DISCOVERED_LABEL_DEVICE_TYPE_ROBOTCONTROLLER,
    2: DISCOVERED_LABEL_DEVICE_TYPE_MOTORCONTROLLER,
    4: DISCOVERED_LABEL_DEVICE_TYPE_GYRO,
    7: DISCOVERED_LABEL_DEVICE_TYPE_ENCODER,
    8: DISCOVERED_LABEL_DEVICE_TYPE_POWER,
}
RATE_DECAY_TIME_CONSTANT_MS = 3000.0
RATE_DECAY_MIN_VALUE = 0.05


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


def _device_key_from_normalized_frame(frame: NormalizedFrame) -> str:
    """
    NAME
        _device_key_from_normalized_frame - Build a visibility key from one normalized frame.
    """
    if frame.manufacturer is None or frame.device_type is None or frame.device_id is None:
        return VIS_EMPTY_STRING
    return _device_key_from_ids(int(frame.manufacturer), int(frame.device_type), int(frame.device_id))


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
        recent_frame_history_limit: int = VIS_RECENT_FRAME_HISTORY_DEFAULT,
    ) -> None:
        self._sources: Dict[str, SourceInfo] = {}
        self._source_order: List[str] = []
        self._devices: Dict[str, DeviceState] = {}
        self._identity_to_label: Dict[str, str] = {}
        self._expected_labels: Dict[str, str] = {}
        self._timeout_ms = int(timeout_ms)
        self._observed_retention_ms = int(observed_retention_ms)
        self._recent_frame_history_limit = max(VIS_INT_ONE, int(recent_frame_history_limit))
        self._recent_frames: Deque[NormalizedFrame] = deque(maxlen=self._recent_frame_history_limit)
        self._allow_suggested_labels_for_unexpected = True
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
            devices: Iterable of (label, identity_key) tuples.
        """
        with self._lock:
            for state in self._devices.values():
                state.expected = False
                state.unexpected = state.last_seen_ms > VIS_INT_ZERO
            self._expected_labels = {}
            for label, identity_key in devices:
                clean_label = str(label).strip()
                if not clean_label:
                    continue
                label_key = clean_label.lower()
                clean_identity = str(identity_key).strip()
                existing_label_key = self._identity_to_label.get(clean_identity) if clean_identity else None
                if existing_label_key and existing_label_key != label_key:
                    self._relabel_state(existing_label_key, clean_label)
                state = self._devices.get(label_key)
                if state is None:
                    state = DeviceState(
                        key=label_key,
                        label=clean_label,
                        identity_key=clean_identity,
                        expected=True,
                        unexpected=False,
                    )
                    self._devices[label_key] = state
                else:
                    state.key = label_key
                    state.label = clean_label
                    if clean_identity:
                        state.identity_key = clean_identity
                    state.expected = True
                    state.unexpected = False
                self._expected_labels[label_key] = clean_label
                if clean_identity:
                    self._identity_to_label[clean_identity] = label_key

    def reset_observed_state(self) -> None:
        """
        NAME
            reset_observed_state - Clear all observed/passive device state while preserving source configuration.

        DESCRIPTION
            This is used by scratch-session workflows that want a true blank
            starting point for passive visibility/discovery state as well as
            local config state.
        """
        with self._lock:
            self._devices = {}
            self._identity_to_label = {}
            self._expected_labels = {}
            self._recent_frames.clear()

    def set_allow_suggested_labels_for_unexpected(self, allowed: bool) -> None:
        """
        NAME
            set_allow_suggested_labels_for_unexpected - Control whether unexpected rows may reuse suggested labels.
        """
        with self._lock:
            self._allow_suggested_labels_for_unexpected = bool(allowed)

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
        normalized_frame: Optional[NormalizedFrame] = None,
        allow_unexpected_create: bool = True,
    ) -> None:
        """
        NAME
            ingest_frame - Record a frame for a source.
        """
        with self._lock:
            if source_id not in self._sources:
                return
            key = decoded_key
            if not key and normalized_frame is not None:
                key = _device_key_from_normalized_frame(normalized_frame)
            if not key:
                try:
                    decoded = decode_shared_frc_ext_id(arb_id)
                    mfg, dtype, did = (
                        decoded.manufacturer,
                        decoded.device_type,
                        decoded.device_id,
                    )
                    key = _device_key_from_ids(mfg, dtype, did)
                except Exception:
                    key = _device_key_from_arb(arb_id)
            if not key:
                return
            state = self._state_for_identity(key, label, allow_unexpected_create=allow_unexpected_create)
            if state is None:
                if normalized_frame is not None:
                    self._recent_frames.append(normalized_frame)
                return
            metric = state.metrics.get(source_id)
            if metric is None:
                metric = MetricState()
                state.metrics[source_id] = metric
            if metric.first_seen_ms <= VIS_INT_ZERO:
                metric.first_seen_ms = ts_ms
            metric.last_seen_ms = ts_ms
            metric.msg_count += VIS_INT_ONE
            state.last_seen_ms = max(state.last_seen_ms, ts_ms)
            raw_state = state.raw_ids.get(arb_id)
            if raw_state is None:
                raw_state = RawIdState(arb_id=arb_id)
                state.raw_ids[arb_id] = raw_state
            if raw_state.first_seen_ms <= VIS_INT_ZERO:
                raw_state.first_seen_ms = ts_ms
            raw_state.last_seen_ms = ts_ms
            raw_state.msg_count += VIS_INT_ONE
            if normalized_frame is not None:
                self._recent_frames.append(normalized_frame)

    def recent_frames(self) -> List[NormalizedFrame]:
        """
        NAME
            recent_frames - Return the bounded recent normalized-frame history.
        """
        with self._lock:
            return list(self._recent_frames)

    def resolve_label(self, identity_key: str, suggested_label: Optional[str] = None) -> str:
        """
        NAME
            resolve_label - Return the canonical label for an observed identity.

        DESCRIPTION
            Expected configured devices resolve to their configured labels.
            Unconfigured observed identities are assigned stable temporary labels.
        """
        with self._lock:
            state = self._state_for_identity(identity_key, suggested_label, allow_unexpected_create=True)
            return state.label

    def rename_discovered_label(self, old_label: str, new_label: str) -> bool:
        """
        NAME
            rename_discovered_label - Rename one discovered unexpected device label.
        """
        with self._lock:
            old_key = str(old_label).strip().lower()
            new_clean = str(new_label).strip()
            new_key = new_clean.lower()
            if not old_key or not new_clean or old_key == new_key:
                return False
            state = self._devices.get(old_key)
            if state is None or state.expected:
                return False
            if new_key in self._devices:
                return False
            self._relabel_state(old_key, new_clean)
            return True

    def _state_for_identity(
        self,
        identity_key: str,
        suggested_label: Optional[str],
        *,
        allow_unexpected_create: bool,
    ) -> Optional[DeviceState]:
        """
        NAME
            _state_for_identity - Resolve or create the state tracked for one observed identity.
        """
        label_key = self._identity_to_label.get(identity_key)
        if label_key:
            state = self._devices.get(label_key)
            if state is not None:
                return state
        clean_label = str(suggested_label or VIS_EMPTY_STRING).strip()
        if not self._allow_suggested_labels_for_unexpected:
            clean_label = VIS_EMPTY_STRING
        candidate_key = clean_label.lower() if clean_label else VIS_EMPTY_STRING
        if candidate_key and candidate_key in self._devices:
            state = self._devices[candidate_key]
            self._identity_to_label[identity_key] = candidate_key
            return state
        if not allow_unexpected_create:
            return None
        if not clean_label:
            clean_label = self._allocate_discovered_label(identity_key)
            candidate_key = clean_label.lower()
        state = DeviceState(
            key=candidate_key,
            label=clean_label,
            identity_key=identity_key,
            expected=False,
            unexpected=True,
        )
        self._devices[candidate_key] = state
        self._identity_to_label[identity_key] = candidate_key
        return state

    def _allocate_discovered_label(self, identity_key: str) -> str:
        """
        NAME
            _allocate_discovered_label - Generate a stable temporary discovered-device label.
        """
        base_label = self._base_discovered_label(identity_key)
        if base_label.lower() not in self._devices:
            return base_label
        suffix = DISCOVERED_LABEL_COLLISION_SUFFIX_START
        while True:
            label = (
                base_label
                + DISCOVERED_LABEL_COLLISION_SUFFIX_SEPARATOR
                + str(suffix)
            )
            if label.lower() not in self._devices:
                return label
            suffix += 1

    def _base_discovered_label(self, identity_key: str) -> str:
        """
        NAME
            _base_discovered_label - Build the structured default discovered label for one identity.
        """
        parts = str(identity_key).split(VIS_KEY_SEPARATOR)
        if len(parts) == DISCOVERED_LABEL_PARTS:
            try:
                manufacturer = int(parts[0], DISCOVERED_LABEL_BASE)
                device_type = int(parts[1], DISCOVERED_LABEL_BASE)
                device_id = int(parts[2], DISCOVERED_LABEL_BASE)
                manufacturer_name = self._discovered_manufacturer_name(manufacturer)
                device_type_name = self._discovered_device_type_name(device_type)
                return (
                    manufacturer_name
                    + DISCOVERED_LABEL_SEPARATOR
                    + device_type_name
                    + DISCOVERED_LABEL_SEPARATOR
                    + format(device_id, f"0{DISCOVERED_LABEL_CAN_ID_WIDTH}d")
                )
            except Exception:
                return self._arb_discovered_label(identity_key)
        return self._arb_discovered_label(identity_key)

    def _arb_discovered_label(self, identity_key: str) -> str:
        """
        NAME
            _arb_discovered_label - Build the fallback discovered label for an arbitration-only identity.
        """
        arb_suffix = str(identity_key or VIS_EMPTY_STRING).strip()
        if arb_suffix.lower().startswith(VIS_KEY_ARB_PREFIX):
            arb_suffix = arb_suffix[len(VIS_KEY_ARB_PREFIX):]
        arb_suffix = arb_suffix.replace(VIS_HEX_PREFIX, VIS_EMPTY_STRING).upper()
        return (
            DISCOVERED_LABEL_ARB_PREFIX
            + DISCOVERED_LABEL_SEPARATOR
            + (arb_suffix or "UNKNOWN")
        )

    def _discovered_manufacturer_name(self, manufacturer: int) -> str:
        """
        NAME
            _discovered_manufacturer_name - Return the manufacturer token for one discovered identity.
        """
        return DISCOVERED_LABEL_MANUFACTURER_NAMES.get(
            int(manufacturer),
            DISCOVERED_LABEL_MANUFACTURER_UNKNOWN_PREFIX + format(int(manufacturer), "02d"),
        )

    def _discovered_device_type_name(self, device_type: int) -> str:
        """
        NAME
            _discovered_device_type_name - Return the device-type token for one discovered identity.
        """
        return DISCOVERED_LABEL_DEVICE_TYPE_NAMES.get(
            int(device_type),
            DISCOVERED_LABEL_DEVICE_TYPE_UNKNOWN_PREFIX + format(int(device_type), "02d"),
        )

    def _relabel_state(self, old_label_key: str, new_label: str) -> None:
        """
        NAME
            _relabel_state - Move a tracked device state to a new canonical label.
        """
        state = self._devices.pop(old_label_key)
        new_key = new_label.lower()
        state.key = new_key
        state.label = new_label
        self._devices[new_key] = state
        if old_label_key in self._expected_labels:
            self._expected_labels.pop(old_label_key, None)
            self._expected_labels[new_key] = new_label
        for identity_key, label_key in list(self._identity_to_label.items()):
            if label_key == old_label_key:
                self._identity_to_label[identity_key] = new_key

    def tick(self, now_ms: int) -> None:
        """
        NAME
            tick - Update rolling frames-per-second metrics.
        """
        with self._lock:
            for state in self._devices.values():
                for _source_id, metric in state.metrics.items():
                    if metric.first_seen_ms <= VIS_INT_ZERO:
                        continue
                    tick_start_ms = (
                        metric.last_tick_ms
                        if metric.last_tick_ms > VIS_INT_ZERO
                        else metric.first_seen_ms
                    )
                    tick_start_count = (
                        metric.last_tick_count
                        if metric.last_tick_ms > VIS_INT_ZERO
                        else VIS_INT_ZERO
                    )
                    elapsed_ms = now_ms - tick_start_ms
                    if elapsed_ms <= VIS_INT_ZERO:
                        continue
                    delta_count = max(VIS_INT_ZERO, metric.msg_count - tick_start_count)
                    metric.frames_per_sec = _blend_rate(
                        previous_rate=metric.frames_per_sec,
                        delta_count=delta_count,
                        elapsed_ms=elapsed_ms,
                    )
                    metric.last_tick_ms = now_ms
                    metric.last_tick_count = metric.msg_count
                for raw_state in state.raw_ids.values():
                    if raw_state.first_seen_ms <= VIS_INT_ZERO:
                        continue
                    tick_start_ms = (
                        raw_state.last_tick_ms
                        if raw_state.last_tick_ms > VIS_INT_ZERO
                        else raw_state.first_seen_ms
                    )
                    tick_start_count = (
                        raw_state.last_tick_count
                        if raw_state.last_tick_ms > VIS_INT_ZERO
                        else VIS_INT_ZERO
                    )
                    elapsed_ms = now_ms - tick_start_ms
                    if elapsed_ms <= VIS_INT_ZERO:
                        continue
                    delta_count = max(VIS_INT_ZERO, raw_state.msg_count - tick_start_count)
                    raw_state.frames_per_sec = _blend_rate(
                        previous_rate=raw_state.frames_per_sec,
                        delta_count=delta_count,
                        elapsed_ms=elapsed_ms,
                    )
                    raw_state.last_tick_ms = now_ms
                    raw_state.last_tick_count = raw_state.msg_count

    def _device_in_scope(self, state: DeviceState, scope: str, now_ms: int) -> bool:
        if scope == VIS_SCOPE_EXPECTED:
            return state.expected
        if scope == VIS_SCOPE_OBSERVED:
            if state.expected:
                return False
            if state.last_seen_ms <= VIS_INT_ZERO:
                return False
            return (now_ms - state.last_seen_ms) <= self._observed_retention_ms
        if scope == VIS_SCOPE_BOTH:
            if state.expected:
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
                        VIS_KEY_KEY: state.label,
                        VIS_KEY_LABEL: state.label,
                        VIS_KEY_IDENTITY: state.identity_key,
                        VIS_KEY_VISIBILITY: visibility,
                        VIS_KEY_METRICS: metrics_out,
                        VIS_KEY_UNEXPECTED: bool(state.unexpected),
                        VIS_KEY_RAW_IDS: self._raw_id_snapshot(state, now_ms),
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
            for entry in self._devices.values():
                if entry.label.strip().lower() == sel_lower or entry.key == sel_lower:
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
            VIS_KEY_DEVICE: {
                VIS_KEY_KEY: state.label,
                VIS_KEY_LABEL: state.label,
                VIS_KEY_IDENTITY: state.identity_key,
            },
            VIS_KEY_SOURCES: sources_out,
            VIS_KEY_RAW_IDS: self._raw_id_snapshot(state, now_ms),
        }

    def _raw_id_snapshot(self, state: DeviceState, now_ms: int) -> List[Dict[str, object]]:
        """
        NAME
            _raw_id_snapshot - Return sorted raw arbitration-ID stats for one device row.
        """
        rows: List[Dict[str, object]] = []
        for arb_id, raw_state in sorted(
            state.raw_ids.items(),
            key=lambda item: (-item[1].msg_count, item[0]),
        ):
            _mfg, _dtype, api_class, api_index, _did = decode_frc_ext_id_full(arb_id)
            rows.append(
                {
                    VIS_KEY_ARB_ID: arb_id,
                    VIS_KEY_ARB_HEX: VIS_HEX_PREFIX + format(arb_id, "08X"),
                    VIS_KEY_MSG_COUNT: raw_state.msg_count,
                    VIS_KEY_FRAMES_PER_SEC: raw_state.frames_per_sec,
                    VIS_KEY_LAST_SEEN_MS: raw_state.last_seen_ms,
                    VIS_KEY_API_CLASS: api_class,
                    VIS_KEY_API_INDEX: api_index,
                    VIS_KEY_PRIORITY: (arb_id >> 26) & 0x7,
                    VIS_KEY_RESERVED: (arb_id >> 25) & 0x1,
                    VIS_KEY_DATA_PAGE: (arb_id >> 24) & 0x1,
                    VIS_KEY_PF: (arb_id >> 16) & 0xFF,
                    VIS_KEY_PS: (arb_id >> 8) & 0xFF,
                    VIS_KEY_SA: arb_id & 0xFF,
                    VIS_KEY_PGN: self._candidate_pgn(arb_id),
                    VIS_KEY_AGE_MS: max(VIS_INT_ZERO, now_ms - raw_state.last_seen_ms)
                    if raw_state.last_seen_ms > VIS_INT_ZERO
                    else None,
                }
            )
        return rows

    def _candidate_pgn(self, arb_id: int) -> int:
        """
        NAME
            _candidate_pgn - Compute a candidate J1939 PGN from a raw 29-bit arbitration ID.
        """
        reserved = (arb_id >> 25) & 0x1
        data_page = (arb_id >> 24) & 0x1
        pf = (arb_id >> 16) & 0xFF
        ps = (arb_id >> 8) & 0xFF
        base = (reserved << 17) | (data_page << 16) | (pf << 8)
        if pf < 240:
            return base
        return base | ps

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


def _blend_rate(*, previous_rate: float, delta_count: int, elapsed_ms: int) -> float:
    """
    NAME
        _blend_rate - Return one slowly decaying rolling frames-per-second estimate.
    """
    if elapsed_ms <= VIS_INT_ZERO:
        return max(VIS_FLOAT_ZERO, float(previous_rate or VIS_FLOAT_ZERO))
    instant_rate = float(delta_count) / (float(elapsed_ms) / VIS_MS_PER_SEC)
    if float(previous_rate or VIS_FLOAT_ZERO) <= VIS_FLOAT_ZERO:
        return instant_rate
    decay_weight = math.exp(-float(elapsed_ms) / RATE_DECAY_TIME_CONSTANT_MS)
    blended_rate = (float(previous_rate) * decay_weight) + (instant_rate * (VIS_FLOAT_ONE - decay_weight))
    if blended_rate < RATE_DECAY_MIN_VALUE and delta_count <= VIS_INT_ZERO:
        return VIS_FLOAT_ZERO
    return blended_rate
