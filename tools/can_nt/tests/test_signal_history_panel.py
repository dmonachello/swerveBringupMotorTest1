"""Pure rendering-helper regressions for the live signal graph."""

import unittest

from tools.can_topology.signal_history_panel import decimate_samples, project_source_times
from tools.common.telemetry.model import TelemetrySample


class SignalHistoryPanelTest(unittest.TestCase):
    """Verify display decimation retains diagnostic extrema."""

    def test_decimation_preserves_spike_and_endpoints(self) -> None:
        samples = tuple(
            TelemetrySample(
                sequence=index,
                signal_id="signal",
                source_timestamp_us=index * 20_000,
                numeric_value=100.0 if index == 50 else float(index % 5),
                quality="GOOD",
            )
            for index in range(100)
        )

        result = decimate_samples(samples, pixel_width=10)

        self.assertEqual(0, result[0].sequence)
        self.assertEqual(99, result[-1].sequence)
        self.assertIn(50, [sample.sequence for sample in result])
        self.assertLessEqual(len(result), 20)

    def test_review_projection_does_not_move_when_newer_sample_arrives(self) -> None:
        original = (
            TelemetrySample(1, "signal", 1_000_000, 1.0, "GOOD"),
            TelemetrySample(2, "signal", 2_000_000, 2.0, "GOOD"),
        )
        extended = original + (
            TelemetrySample(3, "signal", 3_000_000, 3.0, "GOOD"),
        )

        self.assertEqual([-1.0, 0.0], project_source_times(original, 2_000_000))
        self.assertEqual(
            [-1.0, 0.0, 1.0],
            project_source_times(extended, 2_000_000),
        )


if __name__ == "__main__":
    unittest.main()
