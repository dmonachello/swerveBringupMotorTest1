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


if __name__ == "__main__":
    unittest.main()
