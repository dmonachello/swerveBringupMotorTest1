"""Regression tests for lossless cursor advancement in telemetry polling."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from tools.can_nt.telemetry_polling import RESULT_QUEUE_CAPACITY, TelemetryPollingWorker
from tools.common.telemetry.model import TelemetryHistoryPage


class _UnusedSession:
    """Placeholder because queue tests do not perform REST calls."""


class TelemetryPollingWorkerTest(unittest.TestCase):
    """Protect bounded-queue behavior that preserves ordered history pages."""

    def test_full_result_queue_rejects_new_update_without_evicting_oldest(self) -> None:
        worker = TelemetryPollingWorker(_UnusedSession())
        expected = tuple(range(RESULT_QUEUE_CAPACITY))
        for value in expected:
            self.assertTrue(worker._offer(value))

        self.assertFalse(worker._offer(RESULT_QUEUE_CAPACITY))

        self.assertEqual(expected, worker.drain())

    def test_signal_selection_change_discards_queued_old_query_page(self) -> None:
        worker = TelemetryPollingWorker(_UnusedSession())
        worker.update_query(True, 0, ("signal-a",))
        revision = worker._query_revision
        page = Mock(spec=TelemetryHistoryPage)
        page.next_sequence = 12
        self.assertTrue(worker._offer_history(page, revision))

        worker.update_query(True, 0, ("signal-a", "signal-b"))

        self.assertEqual((), worker.drain())


if __name__ == "__main__":
    unittest.main()
