from __future__ import annotations

import unittest

from tools.common.motor_runtime_verdict import (
    RESULT_ELECTRICAL,
    RESULT_ROTATING,
    infer_motor_runtime_verdict,
)


class MotorRuntimeVerdictTests(unittest.TestCase):
    """
    NAME
        MotorRuntimeVerdictTests - Validate shared runtime motor verdict classification.
    """

    def test_commanded_without_motion_telemetry_keeps_existing_electrical_verdict(self) -> None:
        verdict = infer_motor_runtime_verdict(
            present=True,
            cmd_duty=0.13,
            applied_duty=0.13,
            applied_v=1.5,
            bus_v=11.5,
            vel_rpm=None,
            position_delta_rot=None,
            motor_current_a=0.0,
            attachment=None,
            duty_threshold=0.05,
            rpm_threshold=5.0,
            position_delta_threshold=0.05,
            current_active_threshold=0.2,
            low_bus_v_threshold=7.0,
            applied_v_active_threshold=1.0,
        )

        self.assertEqual(verdict["result"], RESULT_ELECTRICAL)

    def test_commanded_with_motion_telemetry_and_low_current_marks_electrical(self) -> None:
        verdict = infer_motor_runtime_verdict(
            present=True,
            cmd_duty=0.13,
            applied_duty=0.13,
            applied_v=1.5,
            bus_v=11.5,
            vel_rpm=0.0,
            position_delta_rot=0.0,
            motor_current_a=0.0,
            attachment=None,
            duty_threshold=0.05,
            rpm_threshold=5.0,
            position_delta_threshold=0.05,
            current_active_threshold=0.2,
            low_bus_v_threshold=7.0,
            applied_v_active_threshold=1.0,
        )

        self.assertEqual(verdict["result"], RESULT_ELECTRICAL)

    def test_commanded_with_velocity_marks_rotating(self) -> None:
        verdict = infer_motor_runtime_verdict(
            present=True,
            cmd_duty=0.13,
            applied_duty=0.13,
            applied_v=1.5,
            bus_v=11.5,
            vel_rpm=120.0,
            position_delta_rot=None,
            motor_current_a=0.0,
            attachment=None,
            duty_threshold=0.05,
            rpm_threshold=5.0,
            position_delta_threshold=0.05,
            current_active_threshold=0.2,
            low_bus_v_threshold=7.0,
            applied_v_active_threshold=1.0,
        )

        self.assertEqual(verdict["result"], RESULT_ROTATING)


if __name__ == "__main__":
    unittest.main()
