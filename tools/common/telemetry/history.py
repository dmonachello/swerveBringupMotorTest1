"""
NAME
    history.py - Bounded host history and persistent watch-list state.

DESCRIPTION
    Owns the session watch set, cursor, gap/reset handling, and fixed per-signal
    sample retention shared by live graph and future capture surfaces.
"""

from __future__ import annotations

from array import array
from dataclasses import replace
import time
from typing import Dict, Iterator, Tuple

from .constants import (
    EMPTY_SEQUENCE,
    MAX_ACTIVE_SIGNALS,
    MAX_HOST_SAMPLES_TOTAL,
    MAX_LANES,
    MAX_SAMPLES_PER_SIGNAL,
    HOST_RETENTION_SECONDS,
    MICROSECONDS_PER_SECOND,
)
from .model import SignalDescriptor, TelemetryCatalog, TelemetryHistoryPage, TelemetrySample


QUALITY_CODES = {"GOOD": 1, "STALE": 2, "UNAVAILABLE": 3, "READ_ERROR": 4}
QUALITY_NAMES = {value: key for key, value in QUALITY_CODES.items()}


class PrimitiveSampleRing:
    """Store one signal in fixed primitive arrays without per-sample objects."""

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._sequences = array("q", [0]) * capacity
        self._timestamps = array("q", [0]) * capacity
        self._values = array("d", [0.0]) * capacity
        self._receive_wall = array("q", [0]) * capacity
        self._receive_monotonic = array("q", [0]) * capacity
        self._source_age = array("q", [0]) * capacity
        self._qualities = bytearray(capacity)
        self._gaps = bytearray(capacity)
        self._head = 0
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def append(self, sample: TelemetrySample) -> None:
        if self._size == self._capacity:
            self.popleft()
        index = (self._head + self._size) % self._capacity
        self._sequences[index] = sample.sequence
        self._timestamps[index] = sample.source_timestamp_us
        self._values[index] = sample.numeric_value
        self._receive_wall[index] = sample.receive_timestamp_ns
        self._receive_monotonic[index] = sample.receive_monotonic_ns
        self._source_age[index] = sample.source_age_at_receive_us
        self._qualities[index] = QUALITY_CODES.get(sample.quality, 0)
        self._gaps[index] = 1 if sample.gap_before else 0
        self._size += 1

    def popleft(self) -> None:
        if self._size:
            self._head = (self._head + 1) % self._capacity
            self._size -= 1

    def first_sequence(self) -> int:
        return self._sequences[self._head] if self._size else EMPTY_SEQUENCE

    def first_timestamp_us(self) -> int:
        return self._timestamps[self._head] if self._size else 0

    def latest(self, signal_id: str) -> TelemetrySample | None:
        if not self._size:
            return None
        return self._sample(signal_id, self._size - 1)

    def latest_timestamp_us(self) -> int:
        """Return the newest source timestamp without constructing a sample."""
        if not self._size:
            return 0
        return self._timestamps[(self._head + self._size - 1) % self._capacity]

    def nearest(self, signal_id: str, target_us: int) -> TelemetrySample | None:
        """Find the nearest monotonic timestamp with a binary search."""
        if not self._size:
            return None
        low = 0
        high = self._size
        while low < high:
            middle = (low + high) // 2
            index = (self._head + middle) % self._capacity
            if self._timestamps[index] < target_us:
                low = middle + 1
            else:
                high = middle
        offsets = {min(low, self._size - 1), max(0, low - 1)}
        offset = min(
            offsets,
            key=lambda item: abs(
                self._timestamps[(self._head + item) % self._capacity] - target_us
            ),
        )
        return self._sample(signal_id, offset)

    def decimated(
        self,
        signal_id: str,
        pixel_width: int,
        start_us: int,
        end_us: int,
    ) -> Tuple[TelemetrySample, ...]:
        """Return at most two extrema-preserving samples per horizontal bucket."""
        bucket_count = max(2, pixel_width)
        first = self._lower_bound(start_us)
        last = self._upper_bound(end_us)
        visible_size = max(0, last - first)
        if visible_size <= bucket_count:
            return tuple(self._sample(signal_id, offset) for offset in range(first, last))
        bucket_size = max(1, (visible_size + bucket_count - 1) // bucket_count)
        selected_offsets: list[int] = []
        for start in range(first, last, bucket_size):
            stop = min(last, start + bucket_size)
            minimum = min(range(start, stop), key=self._value_at)
            maximum = max(range(start, stop), key=self._value_at)
            if start == first:
                candidates = (start, self._farther_extreme(start, minimum, maximum))
            elif stop == last:
                end = stop - 1
                candidates = (self._farther_extreme(end, minimum, maximum), end)
            else:
                candidates = (minimum, maximum)
            gap_offsets = (
                offset
                for offset in range(start, stop)
                if self._gaps[(self._head + offset) % self._capacity]
            )
            for offset in sorted(set((*candidates, *gap_offsets))):
                if not selected_offsets or selected_offsets[-1] != offset:
                    selected_offsets.append(offset)
        return tuple(self._sample(signal_id, offset) for offset in selected_offsets)

    def _lower_bound(self, target_us: int) -> int:
        low = 0
        high = self._size
        while low < high:
            middle = (low + high) // 2
            timestamp = self._timestamps[(self._head + middle) % self._capacity]
            if timestamp < target_us:
                low = middle + 1
            else:
                high = middle
        return low

    def _upper_bound(self, target_us: int) -> int:
        low = 0
        high = self._size
        while low < high:
            middle = (low + high) // 2
            timestamp = self._timestamps[(self._head + middle) % self._capacity]
            if timestamp <= target_us:
                low = middle + 1
            else:
                high = middle
        return low

    def _value_at(self, offset: int) -> float:
        return self._values[(self._head + offset) % self._capacity]

    def _farther_extreme(self, anchor: int, minimum: int, maximum: int) -> int:
        anchor_value = self._value_at(anchor)
        return max(
            (minimum, maximum),
            key=lambda offset: abs(self._value_at(offset) - anchor_value),
        )

    def storage_bytes(self) -> int:
        """Return the fixed primitive payload allocated by this ring."""
        arrays = (
            self._sequences,
            self._timestamps,
            self._values,
            self._receive_wall,
            self._receive_monotonic,
            self._source_age,
        )
        return sum(len(values) * values.itemsize for values in arrays) + len(
            self._qualities
        ) + len(self._gaps)

    def snapshot(self, signal_id: str) -> Tuple[TelemetrySample, ...]:
        return tuple(self._sample(signal_id, offset) for offset in range(self._size))

    def iter_samples(self, signal_id: str) -> Iterator[TelemetrySample]:
        for offset in range(self._size):
            yield self._sample(signal_id, offset)

    def _sample(self, signal_id: str, offset: int) -> TelemetrySample:
        index = (self._head + offset) % self._capacity
        return TelemetrySample(
            sequence=self._sequences[index],
            signal_id=signal_id,
            source_timestamp_us=self._timestamps[index],
            numeric_value=self._values[index],
            quality=QUALITY_NAMES.get(self._qualities[index], "UNKNOWN"),
            receive_timestamp_ns=self._receive_wall[index],
            receive_monotonic_ns=self._receive_monotonic[index],
            source_age_at_receive_us=self._source_age[index],
            gap_before=bool(self._gaps[index]),
        )


class TelemetryHistoryStore:
    """Maintain watched signals and bounded samples for one robot source."""

    def __init__(
        self,
        max_active_signals: int = MAX_ACTIVE_SIGNALS,
        max_lanes: int = MAX_LANES,
        max_samples_per_signal: int = MAX_SAMPLES_PER_SIGNAL,
        max_samples_total: int = MAX_HOST_SAMPLES_TOTAL,
        retention_seconds: int = HOST_RETENTION_SECONDS,
    ) -> None:
        self._max_active_signals = max_active_signals
        self._max_lanes = max_lanes
        self._max_samples_per_signal = max_samples_per_signal
        self._max_samples_total = max_samples_total
        self._retention_us = int(retention_seconds * MICROSECONDS_PER_SECOND)
        self._catalog_by_id: Dict[str, SignalDescriptor] = {}
        self._watched_ids: list[str] = []
        self._watched_definition_keys: list[str] = []
        self._samples_by_id: Dict[str, PrimitiveSampleRing] = {}
        self._last_sequence_by_id: Dict[str, int] = {}
        self._source_instance_id = ""
        self._clock_id = ""
        self._clock_kind = ""
        self._generation = ""
        self._cursor = EMPTY_SEQUENCE
        self._gap_detected = False
        self._pending_gap_signal_ids: set[str] = set()

    @property
    def cursor(self) -> int:
        """Return the next query cursor owned by this store."""
        return self._cursor

    @property
    def source_instance_id(self) -> str:
        """Return the currently bound robot source instance."""
        return self._source_instance_id

    @property
    def retention_seconds(self) -> float:
        """Return the configured host retention duration in seconds."""
        return self._retention_us / MICROSECONDS_PER_SECOND

    @property
    def gap_detected(self) -> bool:
        """Report whether robot eviction or a source reset broke continuity."""
        return self._gap_detected

    @property
    def allocated_sample_bytes(self) -> int:
        """Return fixed primitive storage allocated for watched signals."""
        return sum(samples.storage_bytes() for samples in self._samples_by_id.values())

    @property
    def clock_summary(self) -> str:
        """Return provenance text suitable for a graph legend or status row."""
        if not self._clock_id:
            return "Robot clock unavailable"
        gap = " · gap detected" if self._gap_detected else ""
        return f"Robot-local · {self._clock_kind} · exact source timestamps{gap}"

    def apply_catalog(self, catalog: TelemetryCatalog) -> None:
        """Bind descriptors and rebind saved definitions after a source reset."""
        old_catalog = self._catalog_by_id
        old_samples = self._samples_by_id
        old_ids_by_definition = {
            descriptor.signal_definition_key: signal_id
            for signal_id, descriptor in old_catalog.items()
        }
        instance_changed = bool(self._source_instance_id) and (
            self._source_instance_id != catalog.source_instance_id
        )
        generation_changed = bool(self._generation) and (
            self._generation != catalog.history_generation_id
        )
        next_catalog = {signal.signal_id: signal for signal in catalog.signals}
        self._source_instance_id = catalog.source_instance_id
        self._clock_id = catalog.clock.clock_id
        self._clock_kind = catalog.clock.kind
        self._generation = catalog.history_generation_id
        if instance_changed:
            self._cursor = EMPTY_SEQUENCE
            self._gap_detected = True
            self._samples_by_id = {
                signal_id: PrimitiveSampleRing(self._max_samples_per_signal)
                for signal_id in self._watched_ids
            }
            self._last_sequence_by_id = {
                signal_id: EMPTY_SEQUENCE for signal_id in self._watched_ids
            }
        elif generation_changed:
            self._cursor = EMPTY_SEQUENCE
            self._gap_detected = True
            self._last_sequence_by_id = {
                signal_id: EMPTY_SEQUENCE for signal_id in self._watched_ids
            }
            self._pending_gap_signal_ids.update(self._watched_ids)
        if next_catalog:
            rebound_ids = [
                signal.signal_id
                for signal in catalog.signals
                if signal.signal_definition_key in self._watched_definition_keys
            ][: self._max_active_signals]
            rebound_samples: Dict[str, PrimitiveSampleRing] = {}
            for signal in catalog.signals:
                if signal.signal_id not in rebound_ids:
                    continue
                old_id = old_ids_by_definition.get(signal.signal_definition_key)
                retained = None if instance_changed else old_samples.get(old_id or "")
                rebound_samples[signal.signal_id] = retained or PrimitiveSampleRing(
                    self._max_samples_per_signal
                )
            self._catalog_by_id = next_catalog
            self._watched_ids = rebound_ids
            self._samples_by_id = rebound_samples
            if instance_changed or generation_changed:
                self._last_sequence_by_id = {
                    signal_id: EMPTY_SEQUENCE for signal_id in rebound_ids
                }
            else:
                self._last_sequence_by_id = {
                    signal_id: self._last_sequence_by_id.get(
                        old_ids_by_definition.get(
                            next_catalog[signal_id].signal_definition_key,
                            "",
                        ),
                        EMPTY_SEQUENCE,
                    )
                    for signal_id in rebound_ids
                }

    def watch(self, signal_id: str) -> bool:
        """Watch one catalog signal, enforcing the approved eight-trace cap."""
        if signal_id in self._watched_ids:
            return True
        if self.watch_block_reason(signal_id):
            return False
        self._watched_ids.append(signal_id)
        descriptor = self._catalog_by_id[signal_id]
        self._watched_definition_keys.append(descriptor.signal_definition_key)
        self._samples_by_id.setdefault(
            signal_id, PrimitiveSampleRing(self._max_samples_per_signal)
        )
        self._last_sequence_by_id.setdefault(signal_id, EMPTY_SEQUENCE)
        self._cursor = EMPTY_SEQUENCE
        return True

    def watch_block_reason(self, signal_id: str) -> str:
        """Explain why an unchecked signal cannot enter the watch set."""
        if signal_id in self._watched_ids:
            return ""
        descriptor = self._catalog_by_id.get(signal_id)
        if descriptor is None or not descriptor.graphable:
            return "Signal is not graphable."
        if len(self._watched_ids) >= self._max_active_signals:
            return f"Maximum of {self._max_active_signals} active traces reached."
        dimensions = {
            watched.engineering_dimension for watched in self.watched_descriptors()
        }
        if (
            descriptor.engineering_dimension not in dimensions
            and len(dimensions) >= self._max_lanes
        ):
            return f"Maximum of {self._max_lanes} engineering-dimension lanes reached."
        return ""

    def unwatch(self, signal_id: str) -> None:
        """Remove a signal and its retained host samples from the watch set."""
        if signal_id in self._watched_ids:
            self._watched_ids.remove(signal_id)
        descriptor = self._catalog_by_id.get(signal_id)
        if (
            descriptor is not None
            and descriptor.signal_definition_key in self._watched_definition_keys
        ):
            self._watched_definition_keys.remove(descriptor.signal_definition_key)
        self._samples_by_id.pop(signal_id, None)
        self._last_sequence_by_id.pop(signal_id, None)

    def watched_descriptors(self) -> Tuple[SignalDescriptor, ...]:
        """Return watched descriptors in stable user-selection order."""
        return tuple(
            self._catalog_by_id[signal_id]
            for signal_id in self._watched_ids
            if signal_id in self._catalog_by_id
        )

    def catalog_descriptors(self) -> Tuple[SignalDescriptor, ...]:
        """Return the current source catalog in robot declaration order."""
        return tuple(self._catalog_by_id.values())

    def signal_ids_for_query(self) -> Tuple[str, ...]:
        """Return the selected signal IDs sent in a REST history query."""
        return tuple(self._watched_ids)

    def apply_page(self, page: TelemetryHistoryPage) -> None:
        """Append a page, clearing incompatible data on source discontinuity."""
        if (
            page.source_instance_id != self._source_instance_id
            or page.history_generation_id != self._generation
        ):
            self._cursor = EMPTY_SEQUENCE
            self._gap_detected = True
            return
        if page.cursor_expired:
            self._gap_detected = True
            self._pending_gap_signal_ids.update(self._watched_ids)
        for sample in page.records:
            last_sequence = self._last_sequence_by_id.get(
                sample.signal_id,
                EMPTY_SEQUENCE,
            )
            if sample.sequence <= last_sequence:
                continue
            samples = self._samples_by_id.get(sample.signal_id)
            if samples is not None:
                if sample.signal_id in self._pending_gap_signal_ids:
                    sample = replace(sample, gap_before=True)
                    self._pending_gap_signal_ids.remove(sample.signal_id)
                samples.append(sample)
                self._last_sequence_by_id[sample.signal_id] = sample.sequence
                self._evict_expired(sample.source_timestamp_us)
                self._evict_total_overflow()
        self._cursor = max(self._cursor, page.next_sequence)

    def samples(self, signal_id: str) -> Tuple[TelemetrySample, ...]:
        """Return an immutable snapshot of retained samples for one signal."""
        samples = self._samples_by_id.get(signal_id)
        return samples.snapshot(signal_id) if samples is not None else tuple()

    def latest_sample(self, signal_id: str) -> TelemetrySample | None:
        """Return the newest sample without copying the retained history."""
        samples = self._samples_by_id.get(signal_id)
        return samples.latest(signal_id) if samples is not None else None

    def latest_source_timestamp_us(self, signal_id: str) -> int:
        """Return the newest source timestamp without materializing samples."""
        samples = self._samples_by_id.get(signal_id)
        return samples.latest_timestamp_us() if samples is not None else 0

    def nearest_sample(self, signal_id: str, target_us: int) -> TelemetrySample | None:
        """Return the nearest retained sample using the primitive-ring index."""
        samples = self._samples_by_id.get(signal_id)
        return samples.nearest(signal_id, target_us) if samples is not None else None

    def decimated_samples(
        self,
        signal_id: str,
        pixel_width: int,
        start_us: int,
        end_us: int,
    ) -> Tuple[TelemetrySample, ...]:
        """Build one bounded render frame directly from primitive storage."""
        samples = self._samples_by_id.get(signal_id)
        return (
            samples.decimated(signal_id, pixel_width, start_us, end_us)
            if samples is not None
            else tuple()
        )

    def iter_samples(self, signal_id: str) -> Iterator[TelemetrySample]:
        """Stream retained samples without creating an intermediate snapshot."""
        samples = self._samples_by_id.get(signal_id)
        return samples.iter_samples(signal_id) if samples is not None else iter(())

    def current_quality(self, signal_id: str) -> str:
        """Return source quality with host-observed staleness applied."""
        descriptor = self._catalog_by_id.get(signal_id)
        samples = self._samples_by_id.get(signal_id)
        if descriptor is None or not samples:
            return "UNAVAILABLE"
        sample = samples.latest(signal_id)
        if sample is None:
            return "UNAVAILABLE"
        if sample.receive_monotonic_ns > 0:
            elapsed_us = (
                time.monotonic_ns() - sample.receive_monotonic_ns
            ) // 1_000
            age_us = sample.source_age_at_receive_us + elapsed_us
            if age_us > descriptor.stale_after_us:
                return "STALE"
        return sample.quality

    def _evict_expired(self, newest_timestamp_us: int) -> None:
        oldest_allowed = newest_timestamp_us - self._retention_us
        for samples in self._samples_by_id.values():
            while len(samples) and samples.first_timestamp_us() < oldest_allowed:
                samples.popleft()

    def _evict_total_overflow(self) -> None:
        total = sum(len(samples) for samples in self._samples_by_id.values())
        while total > self._max_samples_total:
            oldest_samples = min(
                (samples for samples in self._samples_by_id.values() if len(samples)),
                key=lambda samples: samples.first_sequence(),
                default=None,
            )
            if oldest_samples is None:
                return
            oldest_samples.popleft()
            total -= 1
