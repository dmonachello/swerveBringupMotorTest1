from __future__ import annotations

"""
NAME
    capture.py - Public capture and live-session API for passive discovery.

DESCRIPTION
    Exposes purpose-specific offline readers and live observation sessions
    without requiring callers to import CLI or internal helper modules.
"""

import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, Iterator, List, Optional, Tuple, cast

from tools.passive_discovery_poc.constants import (
    AUTO_PORT_SENTINEL,
    DEFAULT_AUTO_MATCH,
    DEFAULT_CAN_BITRATE,
    DEFAULT_LIVE_DURATION_SEC,
    DEFAULT_MAX_FRAME_HISTORY,
    DEFAULT_REV_AUTO_MATCH,
    DEFAULT_REV_SERIAL_BAUD,
    DEFAULT_SLCAN_INTERFACE,
    DIAGNOSTIC_RESOLVED_CHANNEL,
    DIAGNOSTIC_RESOLVED_PORT,
    DIAGNOSTIC_SOURCE_KIND,
    RUN_METADATA_SOURCE_DIAGNOSTICS,
    SOURCE_KIND_CAPTURE_AUTO,
    SOURCE_KIND_CANDUMP,
    SOURCE_KIND_CTRE_HTTP,
    SOURCE_KIND_LIVE_REV_SERIAL,
    SOURCE_KIND_LIVE_SLCAN,
    SOURCE_KIND_PCAPNG,
    SOURCE_KIND_PROFILE,
)
from tools.passive_discovery_poc.models import NormalizedFrame, RunResult, SessionCallbacks
from tools.passive_discovery_poc.result_builder import build_run_result
from tools.passive_discovery_poc.sources import (
    LiveFrameSourcePlugin,
    RecordedEnrichmentSourcePlugin,
    RecordedFrameSourcePlugin,
    default_source_registry,
)


ExpectedRows = Dict[Tuple[int, int, int], Dict[str, object]]


def read_pcapng(path: str) -> List[NormalizedFrame]:
    """
    NAME
        read_pcapng - Read one SocketCAN-style PCAPNG file into normalized frames.
    """
    plugin = cast(RecordedFrameSourcePlugin, default_source_registry().get(SOURCE_KIND_PCAPNG))
    return list(plugin.read_frames({"path": path}))


def read_candump(path: str) -> List[NormalizedFrame]:
    """
    NAME
        read_candump - Read one candump/text file into normalized frames.
    """
    plugin = cast(RecordedFrameSourcePlugin, default_source_registry().get(SOURCE_KIND_CANDUMP))
    return list(plugin.read_frames({"path": path}))


def read_capture(path: str) -> List[NormalizedFrame]:
    """
    NAME
        read_capture - Read one supported offline capture into normalized frames.
    """
    plugin = cast(RecordedFrameSourcePlugin, default_source_registry().get(SOURCE_KIND_CAPTURE_AUTO))
    return list(plugin.read_frames({"path": path}))


def load_expected_rows(profile_path: str, profile_name: str = "") -> Tuple[str, ExpectedRows]:
    """
    NAME
        load_expected_rows - Public wrapper for bringup profile expectation loading.
    """
    plugin = cast(RecordedEnrichmentSourcePlugin, default_source_registry().get(SOURCE_KIND_PROFILE))
    record = plugin.collect({"profile_path": profile_path, "profile_name": profile_name})
    return str(record.metadata.get("profileName", "")), dict(record.expected_rows)


class PassiveObservationSession:
    """
    NAME
        PassiveObservationSession - Mutable live collector that emits immutable-style snapshots.
    """

    def __init__(
        self,
        *,
        frame_iterator_factory,
        source_name: str,
        run_metadata: Dict[str, object],
        expected_rows: Optional[ExpectedRows] = None,
        ctre_base_url: str = "",
        callbacks: Optional[SessionCallbacks] = None,
        snapshot_interval_sec: float = 0.5,
        max_frame_history: int = DEFAULT_MAX_FRAME_HISTORY,
    ) -> None:
        self._frame_iterator_factory = frame_iterator_factory
        self._source_name = source_name
        self._run_metadata = dict(run_metadata)
        self._expected_rows = dict(expected_rows or {})
        self._ctre_base_url = str(ctre_base_url).strip()
        self._callbacks = callbacks or SessionCallbacks()
        self._snapshot_interval_sec = float(snapshot_interval_sec)
        self._max_frame_history = max(int(max_frame_history), 1)
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._frames: Deque[NormalizedFrame] = deque(maxlen=self._max_frame_history)
        self._total_frames_seen = 0
        self._warnings: List[str] = []
        self._last_snapshot: Optional[RunResult] = None
        self._started = False

    def start(self) -> None:
        """
        NAME
            start - Start background live observation.
        """
        if self._started:
            return
        self._started = True
        self._thread = threading.Thread(target=self._run, name=f"PassiveObservationSession-{self._source_name}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """
        NAME
            stop - Request session shutdown and wait for completion.
        """
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    def close(self) -> None:
        """
        NAME
            close - Alias for stop so callers can use explicit cleanup style.
        """
        self.stop()

    def wait(self, timeout: Optional[float] = None) -> None:
        """
        NAME
            wait - Wait for the background worker to finish naturally.
        """
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def snapshot(self) -> RunResult:
        """
        NAME
            snapshot - Return the latest analysis snapshot.
        """
        with self._lock:
            frames = list(self._frames)
            warnings = list(self._warnings)
            total_frames_seen = int(self._total_frames_seen)
        result = _build_result(
            frames=frames,
            expected_rows=self._expected_rows,
            ctre_base_url=self._ctre_base_url,
            run_metadata={
                **dict(self._run_metadata),
                "retainedFrameCount": len(frames),
                "frameHistoryLimit": self._max_frame_history,
                "totalFramesSeen": total_frames_seen,
            },
            extra_warnings=warnings,
        )
        with self._lock:
            self._last_snapshot = result
        return result

    def subscribe(
        self,
        *,
        on_frame=None,
        on_snapshot=None,
        on_warning=None,
    ) -> None:
        """
        NAME
            subscribe - Register or replace callback hooks.
        """
        self._callbacks = SessionCallbacks(
            on_frame=on_frame or self._callbacks.on_frame,
            on_snapshot=on_snapshot or self._callbacks.on_snapshot,
            on_warning=on_warning or self._callbacks.on_warning,
        )

    def _run(self) -> None:
        """
        NAME
            _run - Internal worker loop for live collection.
        """
        next_snapshot_at = time.time() + self._snapshot_interval_sec
        try:
            for frame in self._frame_iterator_factory(self._stop_event):
                with self._lock:
                    self._frames.append(frame)
                    self._total_frames_seen += 1
                if self._callbacks.on_frame is not None:
                    self._callbacks.on_frame(frame)
                if time.time() >= next_snapshot_at:
                    snapshot = self.snapshot()
                    if self._callbacks.on_snapshot is not None:
                        self._callbacks.on_snapshot(snapshot)
                    next_snapshot_at = time.time() + self._snapshot_interval_sec
        except Exception as exc:
            warning = str(exc)
            with self._lock:
                self._warnings.append(warning)
            if self._callbacks.on_warning is not None:
                self._callbacks.on_warning(warning)
        finally:
            snapshot = self.snapshot()
            if self._callbacks.on_snapshot is not None:
                self._callbacks.on_snapshot(snapshot)


def observe_slcan_session(
    *,
    channel: str = "",
    auto_match: str = DEFAULT_AUTO_MATCH,
    bitrate: int = DEFAULT_CAN_BITRATE,
    interface: str = DEFAULT_SLCAN_INTERFACE,
    duration_sec: Optional[float] = None,
    expected_rows: Optional[ExpectedRows] = None,
    ctre_base_url: str = "",
    callbacks: Optional[SessionCallbacks] = None,
    max_frame_history: int = DEFAULT_MAX_FRAME_HISTORY,
) -> PassiveObservationSession:
    """
    NAME
        observe_slcan_session - Create a live passive session for a CANable/slcan source.
    """
    plugin = cast(LiveFrameSourcePlugin, default_source_registry().get(SOURCE_KIND_LIVE_SLCAN))
    resolved_config = plugin.validate_config(
        {
            "channel": channel,
            "auto_match": auto_match,
            "bitrate": bitrate,
            "interface": interface,
            "duration_sec": duration_sec,
            "diagnostics": {
                DIAGNOSTIC_SOURCE_KIND: SOURCE_KIND_LIVE_SLCAN,
            },
        }
    )
    diagnostics = dict(resolved_config.get("diagnostics", {}))
    diagnostics[DIAGNOSTIC_RESOLVED_CHANNEL] = str(resolved_config["channel"])
    resolved_config["diagnostics"] = diagnostics

    def _factory(stop_event: threading.Event) -> Iterator[NormalizedFrame]:
        return plugin.iter_live_frames(resolved_config, stop_event)

    return PassiveObservationSession(
        frame_iterator_factory=_factory,
        source_name="live_slcan",
        run_metadata={
            "timestampUtc": datetime.now(timezone.utc).isoformat(),
            "liveSlcan": True,
            "channel": str(resolved_config["channel"]),
            "durationSec": duration_sec if duration_sec is not None else DEFAULT_LIVE_DURATION_SEC,
            RUN_METADATA_SOURCE_DIAGNOSTICS: diagnostics,
        },
        expected_rows=expected_rows,
        ctre_base_url=ctre_base_url,
        callbacks=callbacks,
        max_frame_history=max_frame_history,
    )


def observe_rev_serial_session(
    *,
    port: str = AUTO_PORT_SENTINEL,
    auto_match: str = DEFAULT_REV_AUTO_MATCH,
    baudrate: int = DEFAULT_REV_SERIAL_BAUD,
    duration_sec: Optional[float] = None,
    expected_rows: Optional[ExpectedRows] = None,
    ctre_base_url: str = "",
    callbacks: Optional[SessionCallbacks] = None,
    max_frame_history: int = DEFAULT_MAX_FRAME_HISTORY,
) -> PassiveObservationSession:
    """
    NAME
        observe_rev_serial_session - Create a live passive session for a REV serial bridge.
    """
    plugin = cast(LiveFrameSourcePlugin, default_source_registry().get(SOURCE_KIND_LIVE_REV_SERIAL))
    resolved_config = plugin.validate_config(
        {
            "port": port,
            "auto_match": auto_match,
            "baudrate": baudrate,
            "duration_sec": duration_sec,
            "diagnostics": {
                DIAGNOSTIC_SOURCE_KIND: SOURCE_KIND_LIVE_REV_SERIAL,
            },
        }
    )
    diagnostics = dict(resolved_config.get("diagnostics", {}))
    diagnostics[DIAGNOSTIC_RESOLVED_PORT] = str(resolved_config["port"])
    resolved_config["diagnostics"] = diagnostics

    def _factory(stop_event: threading.Event) -> Iterator[NormalizedFrame]:
        return plugin.iter_live_frames(resolved_config, stop_event)

    return PassiveObservationSession(
        frame_iterator_factory=_factory,
        source_name="live_rev_serial",
        run_metadata={
            "timestampUtc": datetime.now(timezone.utc).isoformat(),
            "liveRevSerial": str(resolved_config["port"]),
            "revBaudrate": int(resolved_config["baudrate"]),
            "durationSec": duration_sec if duration_sec is not None else DEFAULT_LIVE_DURATION_SEC,
            RUN_METADATA_SOURCE_DIAGNOSTICS: diagnostics,
        },
        expected_rows=expected_rows,
        ctre_base_url=ctre_base_url,
        callbacks=callbacks,
        max_frame_history=max_frame_history,
    )


def _build_result(
    *,
    frames: List[NormalizedFrame],
    expected_rows: ExpectedRows,
    ctre_base_url: str,
    run_metadata: Dict[str, object],
    extra_warnings: List[str],
) -> RunResult:
    """
    NAME
        _build_result - Reusable snapshot builder for live sessions.
    """
    if ctre_base_url:
        plugin = cast(RecordedEnrichmentSourcePlugin, default_source_registry().get(SOURCE_KIND_CTRE_HTTP))
        enrichment_record = plugin.collect({"base_url": ctre_base_url})
        ctre_enrichment = dict(enrichment_record.device_enrichment)
        ctre_warnings = list(enrichment_record.warnings)
        enrichment_records = [enrichment_record]
    else:
        ctre_enrichment, ctre_warnings, enrichment_records = ({}, [], [])
    warnings = list(extra_warnings) + list(ctre_warnings)
    return build_run_result(
        frames,
        expected_rows=expected_rows,
        ctre_enrichment=ctre_enrichment,
        enrichment_records=enrichment_records,
        run_metadata=run_metadata,
        warnings=warnings,
    )
