"""
NAME
    telemetry_polling.py - Background REST acquisition for signal history.

DESCRIPTION
    Keeps higher-rate catalog/history HTTP work off the Tk thread. A bounded
    queue lets the UI coalesce updates without losing ownership of host samples.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from tools.can_nt.bridge_session import BridgeSession
from tools.common.telemetry.model import (
    TelemetryCatalog,
    TelemetryCaptureStatus,
    TelemetryHistoryPage,
)


POLL_PERIOD_SECONDS = 0.1
CATALOG_PERIOD_SECONDS = 2.0
RESULT_QUEUE_CAPACITY = 8
THREAD_NAME = "telemetry-rest-poller"


@dataclass(frozen=True)
class TelemetryCatalogUpdate:
    """One catalog update ready for the Tk thread."""

    catalog: TelemetryCatalog


@dataclass(frozen=True)
class TelemetryHistoryUpdate:
    """One history page ready for the Tk thread."""

    page: TelemetryHistoryPage


@dataclass(frozen=True)
class TelemetryCaptureStatusUpdate:
    """One robot-local capture status ready for the Tk thread."""

    status: TelemetryCaptureStatus


TelemetryPollingUpdate = Union[
    TelemetryCatalogUpdate,
    TelemetryHistoryUpdate,
    TelemetryCaptureStatusUpdate,
]


class TelemetryPollingWorker:
    """Poll telemetry REST endpoints on one bounded daemon worker."""

    def __init__(self, session: BridgeSession) -> None:
        self._session = session
        self._stop_event = threading.Event()
        self._query_lock = threading.Lock()
        self._connected = False
        self._cursor = 0
        self._signal_ids: Tuple[str, ...] = tuple()
        self._query_revision = 0
        self._results: queue.Queue[TelemetryPollingUpdate] = queue.Queue(
            maxsize=RESULT_QUEUE_CAPACITY
        )
        self._thread = threading.Thread(
            target=self._run,
            name=THREAD_NAME,
            daemon=True,
        )

    def start(self) -> None:
        """Start the background poller once."""
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        """Request shutdown without blocking the Tk close path."""
        self._stop_event.set()

    def update_query(
        self,
        connected: bool,
        cursor: int,
        signal_ids: Tuple[str, ...],
    ) -> None:
        """Publish the latest UI-owned cursor and watch selection."""
        with self._query_lock:
            next_query = (bool(connected), int(cursor), tuple(signal_ids))
            current_query = (self._connected, self._cursor, self._signal_ids)
            if next_query != current_query:
                signal_selection_changed = next_query[2] != self._signal_ids
                self._query_revision += 1
                self._connected, self._cursor, self._signal_ids = next_query
                if signal_selection_changed:
                    self._drop_pending_history_locked()

    def drain(self) -> Tuple[TelemetryPollingUpdate, ...]:
        """Drain all currently queued immutable updates without blocking."""
        updates = []
        while True:
            try:
                updates.append(self._results.get_nowait())
            except queue.Empty:
                return tuple(updates)

    def _run(self) -> None:
        last_catalog_fetch = 0.0
        while not self._stop_event.wait(POLL_PERIOD_SECONDS):
            with self._query_lock:
                connected = self._connected
                cursor = self._cursor
                signal_ids = self._signal_ids
                query_revision = self._query_revision
            if not connected:
                continue
            now = time.monotonic()
            if now - last_catalog_fetch >= CATALOG_PERIOD_SECONDS:
                catalog = self._session.fetch_telemetry_catalog()
                if catalog is not None:
                    self._offer(TelemetryCatalogUpdate(catalog))
                capture_status = self._session.fetch_telemetry_capture_status()
                if capture_status is not None:
                    self._offer(TelemetryCaptureStatusUpdate(capture_status))
                last_catalog_fetch = now
            if not signal_ids:
                continue
            page = self._session.fetch_telemetry_history(cursor, list(signal_ids))
            if page is not None and self._offer_history(page, query_revision):
                continue

    def _offer_history(
        self,
        page: TelemetryHistoryPage,
        query_revision: int,
    ) -> bool:
        """Atomically reject history produced for an obsolete watch query."""
        with self._query_lock:
            if self._query_revision != query_revision:
                return False
            if not self._offer(TelemetryHistoryUpdate(page)):
                return False
            self._cursor = page.next_sequence
            return True

    def _drop_pending_history_locked(self) -> None:
        """Remove stale history pages while retaining catalog and capture updates."""
        retained = []
        while True:
            try:
                update = self._results.get_nowait()
            except queue.Empty:
                break
            if not isinstance(update, TelemetryHistoryUpdate):
                retained.append(update)
        for update in retained:
            self._offer(update)

    def _offer(self, update: TelemetryPollingUpdate) -> bool:
        """Queue an update without discarding an earlier history page."""
        try:
            self._results.put_nowait(update)
            return True
        except queue.Full:
            return False
