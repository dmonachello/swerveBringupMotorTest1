from __future__ import annotations

import unittest

from tools.common.workflows import Workflow01Service


class Workflow01ServiceTests(unittest.TestCase):
    """Validate workflow readiness sequencing semantics."""

    def test_assess_blocked_when_prerequisites_missing(self) -> None:
        service = Workflow01Service()
        result = service.assess(
            config_loaded=False,
            profile_selected=False,
            robot_connected=False,
            test_selected=False,
        )
        self.assertEqual(result.state, "blocked")
        self.assertGreaterEqual(len(result.blocking_reasons), 1)

    def test_assess_ready_when_all_prerequisites_met(self) -> None:
        service = Workflow01Service()
        result = service.assess(
            config_loaded=True,
            profile_selected=True,
            robot_connected=True,
            test_selected=True,
        )
        self.assertEqual(result.state, "ready")
        self.assertEqual(result.blocking_reasons, [])
        self.assertGreaterEqual(len(result.next_steps), 3)


if __name__ == "__main__":
    unittest.main()

