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

    def test_validate_store(self) -> None:
        source = '\n'.join(
            [
                'test "spin"',
                'device "motor1"',
                "main:",
                "  set motor1.output = 0.5",
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
            device_catalog={"motor1": {"type": "motor"}},
            signal_catalog={
                "motor": {
                    "output": {"writable": True, "safeValue": 0.0},
                    "velocity": {"writable": False, "valueType": "number"},
                    "faults": {"clearable": True, "valueType": "boolean", "writable": False},
                },
                "TestTimer": {"elapsed": {"writable": False, "valueType": "number"}},
            },
        )
        self.assertTrue(result.ok(), [issue.message for issue in result.errors])


if __name__ == "__main__":
    unittest.main()
