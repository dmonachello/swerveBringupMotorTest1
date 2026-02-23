from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter, deque
from typing import Any, Deque, Dict, Optional, Set


@dataclass
class _IdLiveState:
    can_id: int
    first_t: float
    last_t: float
    count: int = 0
    dlc_counts: Counter = field(default_factory=Counter)
    last_data: bytes = b""
    changing_mask: int = 0
    ts_window: Deque[float] = field(default_factory=lambda: deque(maxlen=200))

    def ingest(self, t: float, data: bytes) -> None:
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
        if len(self.ts_window) < 2:
            return 0.0
        dt = self.ts_window[-1] - self.ts_window[0]
        return (len(self.ts_window) - 1) / dt if dt > 0 else 0.0


class CanLiveAnalyzer:
    def __init__(self, expected_ids: Optional[Set[int]] = None):
        self.states: Dict[int, _IdLiveState] = {}
        self.expected_ids: Set[int] = expected_ids or set()
        self.t0: Optional[float] = None
        self.frame_count = 0
        self.byte_count = 0

    def ingest(self, t: float, can_id: int, data: bytes) -> None:
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
        return set(self.states.keys())

    def summary(self, now: float, stale_s: float, top_n: int) -> Dict[str, Any]:
        uptime = (now - self.t0) if self.t0 else 0.0
        fps = self.frame_count / uptime if uptime > 0 else 0.0
        bps = self.byte_count / uptime if uptime > 0 else 0.0

        seen = self.seen_ids()
        missing = sorted(self.expected_ids - seen)
        stale = sorted(cid for cid, st in self.states.items() if (now - st.last_t) > stale_s)

        top = sorted(self.states.values(), key=lambda s: s.hz(), reverse=True)[:top_n]

        return {
            "bus": {
                "uptime_s": round(uptime, 3),
                "fps": round(fps, 2),
                "bytes_per_s": round(bps, 2),
                "unique_ids": len(seen),
            },
            "health": {
                "missing": [hex(x) for x in missing],
                "stale": [hex(x) for x in stale],
            },
            "top": [
                {
                    "id": hex(st.can_id),
                    "hz": round(st.hz(), 2),
                    "last": st.last_data.hex(),
                    "changing": [i for i in range(8) if (st.changing_mask >> i) & 1],
                }
                for st in top
            ],
        }
