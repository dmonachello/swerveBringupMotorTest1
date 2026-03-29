from __future__ import annotations

"""
NAME
    can_analyzer.py - Live CAN traffic analyzer.

SYNOPSIS
    from tools.can_nt.can_analyzer import CanLiveAnalyzer

DESCRIPTION
    Tracks per-arbitration-ID counters, rates, and byte-change masks to
    summarize bus activity.
"""

from dataclasses import dataclass, field
from collections import Counter, deque
from typing import Any, Deque, Dict, Optional, Set, Callable

LABEL_UNKNOWN = "UNKNOWN"


@dataclass
class _IdLiveState:
    """
    NAME
        _IdLiveState - Per-CAN-ID tracking state for live analysis.
    """
    can_id: int
    first_t: float
    last_t: float
    count: int = 0
    dlc_counts: Counter = field(default_factory=Counter)
    last_data: bytes = b""
    changing_mask: int = 0
    ts_window: Deque[float] = field(default_factory=lambda: deque(maxlen=200))

    def ingest(self, t: float, data: bytes) -> None:
        """
        NAME
            ingest - Update counters and change mask with a new frame.
        """
        if self.count > 0:
            for i in range(min(8, len(self.last_data), len(data))):
                if self.last_data[i] != data[i]:
                    self.changing_mask |= (1 << i)
        self.last_data = data
        self.last_t = t
        self.count += 1
        self.dlc_counts[len(data)] += 1
        self.ts_window.append(t)

    def hz(self) -> float:
        """
        NAME
            hz - Estimate frame rate from the sliding timestamp window.
        """
        if len(self.ts_window) < 2:
            return 0.0
        dt = self.ts_window[-1] - self.ts_window[0]
        return (len(self.ts_window) - 1) / dt if dt > 0 else 0.0


class CanLiveAnalyzer:
    """
    NAME
        CanLiveAnalyzer - Aggregate and summarize live CAN traffic.

    DESCRIPTION
        Maintains per-ID live state and computes bus-level summary metrics.
    """
    def __init__(self, expected_ids: Optional[Set[int]] = None):
        self.states: Dict[int, _IdLiveState] = {}
        self.expected_ids: Set[int] = expected_ids or set()
        self.t0: Optional[float] = None
        self.frame_count = 0
        self.byte_count = 0

    def ingest(self, t: float, can_id: int, data: bytes) -> None:
        """
        NAME
            ingest - Record a received frame for analysis.

        PARAMETERS
            t: Timestamp in seconds.
            can_id: Arbitration ID.
            data: Frame payload bytes.
        """
        if self.t0 is None:
            self.t0 = t

        self.frame_count += 1
        self.byte_count += len(data)

        st = self.states.get(can_id)
        if st is None:
            st = _IdLiveState(can_id=can_id, first_t=t, last_t=t)
            self.states[can_id] = st
        st.ingest(t, data)

    def seen_ids(self) -> Set[int]:
        """
        NAME
            seen_ids - Return the set of observed arbitration IDs.
        """
        return set(self.states.keys())

    def summary(
        self,
        now: float,
        stale_s: float,
        top_n: int,
        label_lookup: Optional[Dict[tuple[int, int, int], str]] = None,
        decode_device_key: Optional[Callable[[int], tuple[int, int, int]]] = None,
    ) -> Dict[str, Any]:
        """
        NAME
            summary - Build a summary snapshot of bus health and top talkers.

        PARAMETERS
            now: Current wall-clock time (seconds).
            stale_s: Age threshold for stale IDs.
            top_n: Number of top IDs to include by rate.

        RETURNS
            Dictionary with bus metrics, health lists, and top talkers.
        """
        uptime = (now - self.t0) if self.t0 else 0.0
        fps = self.frame_count / uptime if uptime > 0 else 0.0
        bps = self.byte_count / uptime if uptime > 0 else 0.0

        seen = self.seen_ids()
        missing = sorted(self.expected_ids - seen)
        stale = sorted(cid for cid, st in self.states.items() if (now - st.last_t) > stale_s)

        top = sorted(self.states.values(), key=lambda s: s.hz(), reverse=True)[:top_n]

        def _label_for(can_id: int) -> str:
            if label_lookup is None or decode_device_key is None:
                return LABEL_UNKNOWN
            key = decode_device_key(can_id)
            return label_lookup.get(key, LABEL_UNKNOWN)

        missing_labels = [_label_for(can_id) for can_id in missing]
        stale_labels = [_label_for(can_id) for can_id in stale]

        return {
            "bus": {
                "uptime_s": round(uptime, 3),
                "fps": round(fps, 2),
                "bytes_per_s": round(bps, 2),
                "unique_ids": len(seen),
            },
            "health": {
                "missing": missing_labels,
                "stale": stale_labels,
            },
            "top": [
                {
                    "label": _label_for(st.can_id),
                    "hz": round(st.hz(), 2),
                    "last": st.last_data.hex(),
                    "changing": [i for i in range(8) if (st.changing_mask >> i) & 1],
                }
                for st in top
            ],
        }
