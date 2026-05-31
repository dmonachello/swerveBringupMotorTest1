from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.common.robot_test_dsl import (
    RobotTestDslEntry,
    RobotTestDslStore,
    compile_source,
    source_hash,
    store_to_payload,
    validate_store,
)


class RobotTestDslTests(unittest.TestCase):
    def test_compile_source(self) -> None:
        normalized = compile_source(
            "spin",
            '\n'.join(
                [
                    'test "spin"',
                    'device "motor1"',
                    "init:",
                    "  clear motor1.faults",
                    "main:",
                    "  set motor1.output = 0.5",
                    "  until timer.elapsed >= 3.0",
                    "  require motor1.velocity > 1000",
                ]
            ),
        )
        self.assertEqual("spin", normalized.name)
        self.assertEqual("motor1", normalized.devices[0].name)
        self.assertEqual("set_1", normalized.main.sets[0].statement_id)
        self.assertEqual("until_1", normalized.main.untils[0].condition_id)

    def test_compile_signal_set_source(self) -> None:
        normalized = compile_source(
            "drive",
            '\n'.join(
                [
                    'test "drive"',
                    'device "motor1"',
                    'device "controller0"',
                    "main:",
                    "  set motor1.output = controller0.leftY scaled 0.25 default 0.0",
                    "  until timer.elapsed >= 3.0",
                ]
            ),
        )
        statement = normalized.main.sets[0]
        self.assertIsNone(statement.literal)
        self.assertEqual("controller0", statement.source.device)
        self.assertEqual("leftY", statement.source.signal)
        self.assertIsNone(statement.deadband)
        self.assertEqual(0.25, statement.scale)
        self.assertEqual(0.0, statement.default_literal.value)

    def test_compile_signal_set_source_with_deadband(self) -> None:
        normalized = compile_source(
            "drive",
            '\n'.join(
                [
                    'test "drive"',
                    'device "motor1"',
                    'device "controller0"',
                    "main:",
                    "  set motor1.output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0",
                    "  until timer.elapsed >= 3.0",
                ]
            ),
        )
        statement = normalized.main.sets[0]
        self.assertEqual(0.08, statement.deadband)
        self.assertEqual(0.25, statement.scale)

    def test_validate_store(self) -> None:
        source = '\n'.join(
            [
                'test "spin"',
                'device "motor1"',
                'device "controller0"',
                "main:",
                "  set motor1.output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0",
                "  until timer.elapsed >= 3.0",
                "  require motor1.velocity > 1000",
            ]
        )
        store = RobotTestDslStore(
            tests_by_name={
                "spin": RobotTestDslEntry(
                    name="spin",
                    source=source,
                    normalized=compile_source("spin", source),
                    source_hash=source_hash(source),
                )
            },
            test_sets={"default": ["spin"]},
            default_set="default",
        )
        result = validate_store(
            store,
            device_catalog={"motor1": {"type": "motor"}, "controller0": {"type": "xboxController"}},
            signal_catalog={
                "motor": {
                    "output": {"writable": True, "safeValue": 0.0, "valueType": "number"},
                    "velocity": {"writable": False, "readable": True, "valueType": "number"},
                    "faults": {"clearable": True, "valueType": "boolean", "writable": False},
                },
                "xboxController": {
                    "leftY": {"writable": False, "readable": True, "valueType": "number"},
                },
                "TestTimer": {"elapsed": {"writable": False, "valueType": "number"}},
            },
        )
        self.assertTrue(result.ok(), [issue.message for issue in result.errors])

    def test_validate_store_accepts_qualified_motor_signal_names(self) -> None:
        source = '\n'.join(
            [
                'test "spin"',
                'device "motor1"',
                'device "controller0"',
                "main:",
                "  set motor1.output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0",
                "  until timer.elapsed >= 3.0",
                "  require motor1.velocity_actual > 1000",
                "  abort motor1.current_actual > 35",
            ]
        )
        store = RobotTestDslStore(
            tests_by_name={
                "spin": RobotTestDslEntry(
                    name="spin",
                    source=source,
                    normalized=compile_source("spin", source),
                    source_hash=source_hash(source),
                )
            },
            test_sets={"default": ["spin"]},
            default_set="default",
        )
        result = validate_store(
            store,
            device_catalog={"motor1": {"type": "motor"}, "controller0": {"type": "xboxController"}},
            signal_catalog={
                "motor": {
                    "output_percent_cmd": {"writable": True, "safeValue": 0.0, "valueType": "number"},
                    "velocity_actual": {"writable": False, "readable": True, "valueType": "number"},
                    "current_actual": {"writable": False, "readable": True, "valueType": "number"},
                    "faults": {"clearable": True, "valueType": "boolean", "writable": False},
                },
                "xboxController": {
                    "leftY": {"writable": False, "readable": True, "valueType": "number"},
                },
                "TestTimer": {"elapsed": {"writable": False, "valueType": "number"}},
            },
        )
        self.assertTrue(result.ok(), [issue.message for issue in result.errors])

    def test_validate_store_rejects_motor_source_signal_set(self) -> None:
        source = '\n'.join(
            [
                'test "bad_drive"',
                'device "motor1"',
                'device "motor2"',
                "main:",
                "  set motor1.output = motor2.velocity scaled 0.1 default 0.0",
                "  until timer.elapsed >= 3.0",
            ]
        )
        store = RobotTestDslStore(
            tests_by_name={
                "bad_drive": RobotTestDslEntry(
                    name="bad_drive",
                    source=source,
                    normalized=compile_source("bad_drive", source),
                    source_hash=source_hash(source),
                )
            },
            test_sets={"default": ["bad_drive"]},
            default_set="default",
        )
        result = validate_store(
            store,
            device_catalog={"motor1": {"type": "motor"}, "motor2": {"type": "motor"}},
            signal_catalog={
                "motor": {
                    "output": {"writable": True, "safeValue": 0.0, "valueType": "number"},
                    "velocity": {"writable": False, "readable": True, "valueType": "number"},
                },
                "TestTimer": {"elapsed": {"writable": False, "valueType": "number"}},
            },
        )
        self.assertFalse(result.ok())
        self.assertTrue(any("motor-device source" in issue.message for issue in result.errors))

    def test_store_payload_round_trip_preserves_deadband(self) -> None:
        source = '\n'.join(
            [
                'test "drive"',
                'device "motor1"',
                'device "controller0"',
                "main:",
                "  set motor1.output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0",
                "  until timer.elapsed >= 3.0",
            ]
        )
        normalized = compile_source("drive", source)
        store = RobotTestDslStore(
            tests_by_name={
                "drive": RobotTestDslEntry(
                    name="drive",
                    source=source,
                    normalized=normalized,
                    source_hash=source_hash(source),
                )
            },
            test_sets={"default": ["drive"]},
            default_set="default",
        )
        payload = store_to_payload(store)
        statement = payload["testsByName"]["drive"]["normalized"]["main"]["sets"][0]
        self.assertEqual(0.08, statement["deadband"])

    def test_validate_store_rejects_deadband_out_of_range(self) -> None:
        source = '\n'.join(
            [
                'test "drive"',
                'device "motor1"',
                'device "controller0"',
                "main:",
                "  set motor1.output = controller0.leftY deadband 1.2 scaled 0.25 default 0.0",
                "  until timer.elapsed >= 3.0",
            ]
        )
        store = RobotTestDslStore(
            tests_by_name={
                "drive": RobotTestDslEntry(
                    name="drive",
                    source=source,
                    normalized=compile_source("drive", source),
                    source_hash=source_hash(source),
                )
            },
            test_sets={"default": ["drive"]},
            default_set="default",
        )
        result = validate_store(
            store,
            device_catalog={"motor1": {"type": "motor"}, "controller0": {"type": "xboxController"}},
            signal_catalog={
                "motor": {
                    "output": {"writable": True, "safeValue": 0.0, "valueType": "number"},
                },
                "xboxController": {
                    "leftY": {"writable": False, "readable": True, "valueType": "number"},
                },
                "TestTimer": {"elapsed": {"writable": False, "valueType": "number"}},
            },
        )
        self.assertFalse(result.ok())
        self.assertTrue(any("deadband out of range" in issue.message for issue in result.errors))

    def test_validate_store_rejects_malformed_signal_set_syntax(self) -> None:
        source = '\n'.join(
            [
                'test "bad_drive"',
                'device "motor1"',
                "main:",
                "  set motor1.output = 0.5 deadband 0.08 scaled 0.25 default 0.0",
                "  until timer.elapsed >= 1.0",
            ]
        )
        store = RobotTestDslStore(
            tests_by_name={
                "bad_drive": RobotTestDslEntry(
                    name="bad_drive",
                    source=source,
                    normalized=compile_source("bad_drive", source),
                    source_hash=source_hash(source),
                )
            },
            test_sets={"default": ["bad_drive"]},
            default_set="default",
        )
        result = validate_store(
            store,
            device_catalog={"motor1": {"type": "motor"}},
            signal_catalog={
                "motor": {
                    "output": {"writable": True, "safeValue": 0.0, "valueType": "number"},
                },
                "TestTimer": {"elapsed": {"writable": False, "valueType": "number"}},
            },
        )
        self.assertFalse(result.ok())
        self.assertTrue(any("set literal must be numeric" in issue.message for issue in result.errors))

    def test_compile_condition_stable_and_range_forms(self) -> None:
        normalized = compile_source(
            "stable_range",
            '\n'.join(
                [
                    'test "stable_range"',
                    'device "encoder1"',
                    'device "controller0"',
                    "main:",
                    "  require encoder1.position between 10 20 stable 0.1",
                    "  abort encoder1.position outside 0 30 stable 0.05",
                    "  success controller0.A stable 0.15",
                ]
            ),
        )
        require_condition = normalized.main.requires[0]
        abort_condition = normalized.main.aborts[0]
        success_condition = normalized.main.successes[0]
        self.assertEqual("between", require_condition.mode)
        self.assertEqual(10, require_condition.low_literal.value)
        self.assertEqual(20, require_condition.high_literal.value)
        self.assertEqual(0.1, require_condition.stable_seconds)
        self.assertEqual("outside", abort_condition.mode)
        self.assertEqual(0.05, abort_condition.stable_seconds)
        self.assertEqual("bare", success_condition.mode)
        self.assertEqual(0.15, success_condition.stable_seconds)

    def test_store_payload_round_trip_preserves_condition_extensions(self) -> None:
        source = '\n'.join(
            [
                'test "condition_extensions"',
                'device "encoder1"',
                "main:",
                "  require encoder1.position between 10 20 stable 0.1",
            ]
        )
        normalized = compile_source("condition_extensions", source)
        store = RobotTestDslStore(
            tests_by_name={
                "condition_extensions": RobotTestDslEntry(
                    name="condition_extensions",
                    source=source,
                    normalized=normalized,
                    source_hash=source_hash(source),
                )
            },
            test_sets={"default": ["condition_extensions"]},
            default_set="default",
        )
        payload = store_to_payload(store)
        condition = payload["testsByName"]["condition_extensions"]["normalized"]["main"]["requires"][0]
        self.assertEqual("between", condition["mode"])
        self.assertEqual(10, condition["lowLiteral"]["value"])
        self.assertEqual(20, condition["highLiteral"]["value"])
        self.assertEqual(0.1, condition["stableSeconds"])

    def test_validate_store_rejects_non_positive_stable_seconds(self) -> None:
        source = '\n'.join(
            [
                'test "bad_stable"',
                'device "controller0"',
                "main:",
                "  success controller0.A stable 0",
            ]
        )
        store = RobotTestDslStore(
            tests_by_name={
                "bad_stable": RobotTestDslEntry(
                    name="bad_stable",
                    source=source,
                    normalized=compile_source("bad_stable", source),
                    source_hash=source_hash(source),
                )
            },
            test_sets={"default": ["bad_stable"]},
            default_set="default",
        )
        result = validate_store(
            store,
            device_catalog={"controller0": {"type": "xboxController"}},
            signal_catalog={
                "xboxController": {
                    "A": {"writable": False, "readable": True, "valueType": "boolean"},
                }
            },
        )
        self.assertFalse(result.ok())
        self.assertTrue(any("stable seconds must be > 0" in issue.message for issue in result.errors))

    def test_validate_store_rejects_invalid_range_usage(self) -> None:
        source = '\n'.join(
            [
                'test "bad_range"',
                'device "encoder1"',
                'device "controller0"',
                "main:",
                "  require encoder1.position between 20 10 stable 0.1",
                "  abort controller0.A outside 0 1",
            ]
        )
        store = RobotTestDslStore(
            tests_by_name={
                "bad_range": RobotTestDslEntry(
                    name="bad_range",
                    source=source,
                    normalized=compile_source("bad_range", source),
                    source_hash=source_hash(source),
                )
            },
            test_sets={"default": ["bad_range"]},
            default_set="default",
        )
        result = validate_store(
            store,
            device_catalog={"encoder1": {"type": "encoderExternal"}, "controller0": {"type": "xboxController"}},
            signal_catalog={
                "encoderExternal": {
                    "position": {"writable": False, "readable": True, "valueType": "number"},
                },
                "xboxController": {
                    "A": {"writable": False, "readable": True, "valueType": "boolean"},
                },
            },
        )
        self.assertFalse(result.ok())
        self.assertTrue(any("range low must be <= high" in issue.message for issue in result.errors))
        self.assertTrue(any("range condition requires numeric signal" in issue.message for issue in result.errors))


if __name__ == "__main__":
    unittest.main()
