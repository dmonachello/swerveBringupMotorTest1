from __future__ import annotations

import unittest

from tools.common.diagnostics import normalize_device_attachments, summarize_attachment_metrics


class DiagnosticsNormalizeTests(unittest.TestCase):
    """Validate shared diagnostics normalization."""

    def test_normalize_device_attachments_extracts_expected_fields(self) -> None:
        payload = {
            "devices": [
                {
                    "label": "motor1",
                    "attachments": [
                        {
                            "type": "revMotor",
                            "cmdDuty": 0.5,
                            "appliedDuty": 0.45,
                            "motorCurrentA": 12.3,
                        }
                    ],
                }
            ]
        }
        rows = normalize_device_attachments(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["label"], "motor1")

    def test_summarize_attachment_metrics_returns_average_current(self) -> None:
        rows = [
            {"motorCurrentA": 10.0},
            {"motorCurrentA": 14.0},
        ]
        summary = summarize_attachment_metrics(rows)
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["withCurrent"], 2)
        self.assertEqual(summary["avgCurrentA"], 12.0)


if __name__ == "__main__":
    unittest.main()

