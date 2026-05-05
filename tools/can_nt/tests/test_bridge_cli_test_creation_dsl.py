from __future__ import annotations

"""
NAME
    test_bridge_cli_test_creation_dsl.py - Unit tests for DSL-style test authoring.
"""

import unittest

from tools.can_nt.bridge_cli import BridgeCli, CliMode
from tools.can_nt.bridge_cli_parser import BridgeCliParser
from tools.can_nt.status import SS__NORMAL
from tools.common.profile_constants import KEY_TYPE, TYPE_LIMIT_SWITCH, TYPE_MOTOR
from tools.common.test_authoring import (
    TestAuthoringModel,
    TestModel,
    TestSetModel,
    model_to_payload,
    validate_model,
)


TEST_SET_DEFAULT = "default"
TEST_NAME_DSL = "dsl_test"
DEVICE_MOTOR = "FALCON 9"
DEVICE_SWITCH = "lmtSw1"
PSEUDO_TIMER = "timer2"


class _FakeSession:
    """
    NAME
        _FakeSession - Minimal session used for local CLI tests.
    """

    def is_connected(self) -> bool:
        return False

    def send_command(self, _name: str, _args: dict | None = None) -> int:
        return 1

    def ensure_handshake(self) -> bool:
        return True


class BridgeCliDslAuthoringTests(unittest.TestCase):
    """
    NAME
        BridgeCliDslAuthoringTests - Validate new DSL test authoring behavior.
    """

    def test_parser_accepts_new_test_mode_forms(self) -> None:
        parser = BridgeCliParser()

        parser.parse('device add "lmtSw1" role observer', mode="test")
        parser.parse('device create "timer2" type TestTimer', mode="test")
        parser.parse("command output_percent_cmd = 0.25", mode="test")
        parser.parse("until timer.elapsed >= 4.0", mode="test")
        parser.parse("manual_stop true", mode="test")

    def test_cli_updates_dsl_fields_in_test_mode(self) -> None:
        cli = self._build_cli()

        for line in (
            f'device add "{DEVICE_MOTOR}"',
            f'device add "{DEVICE_SWITCH}" role observer',
            f'device create "{PSEUDO_TIMER}" type TestTimer',
            "command output_percent_cmd = 0.25",
            "until timer.elapsed >= 4.0",
            "expect velocity_actual > 100",
            "abort lmtSw1.pressed == true",
            "passive false",
            "manual_stop false",
        ):
            result = cli._test_mode_command(cli._parser.tokenize(line))
            self.assertEqual(result.code, SS__NORMAL)

        test = cli._get_active_test()
        assert test is not None
        self.assertEqual(test.devices, [DEVICE_MOTOR])
        self.assertEqual(test.observers, [DEVICE_SWITCH])
        self.assertEqual(len(test.pseudo_devices), 1)
        self.assertEqual(test.pseudo_devices[0].name, PSEUDO_TIMER)
        self.assertEqual(len(test.commands), 1)
        self.assertEqual(test.commands[0].signal, "output_percent_cmd")
        self.assertEqual(test.commands[0].value, 0.25)
        self.assertEqual(len(test.until_conditions), 1)
        self.assertEqual(test.until_conditions[0].signal, "timer.elapsed")
        self.assertEqual(len(test.expect_conditions), 1)
        self.assertEqual(len(test.abort_conditions), 1)
        self.assertFalse(test.passive)
        self.assertFalse(test.manual_stop)

    def test_validator_accepts_well_formed_dsl_test(self) -> None:
        model = TestAuthoringModel(
            default_test_set=TEST_SET_DEFAULT,
            test_sets={
                TEST_SET_DEFAULT: TestSetModel(
                    name=TEST_SET_DEFAULT,
                    tests=[
                        TestModel(
                            name=TEST_NAME_DSL,
                            test_type="composite",
                            devices=[DEVICE_MOTOR],
                            observers=[DEVICE_SWITCH],
                            enabled=True,
                        )
                    ],
                )
            },
        )
        test = model.test_sets[TEST_SET_DEFAULT].tests[0]
        test.commands.append(self._conditionless_command())
        test.until_conditions.append(self._condition("timer.elapsed", ">=", 4.0))
        test.expect_conditions.append(self._condition("velocity_actual", ">", 100.0))
        test.abort_conditions.append(self._condition("lmtSw1.pressed", "==", True))

        result = validate_model(model, device_catalog=self._device_catalog(), duplicate_labels=set())

        self.assertTrue(result.ok(), [issue.message for issue in result.errors])
        self.assertEqual(result.warnings, [])

    def test_validator_rejects_expect_without_until(self) -> None:
        model = TestAuthoringModel(
            default_test_set=TEST_SET_DEFAULT,
            test_sets={
                TEST_SET_DEFAULT: TestSetModel(
                    name=TEST_SET_DEFAULT,
                    tests=[
                        TestModel(
                            name=TEST_NAME_DSL,
                            test_type="composite",
                            devices=[DEVICE_MOTOR],
                            enabled=True,
                        )
                    ],
                )
            },
        )
        test = model.test_sets[TEST_SET_DEFAULT].tests[0]
        test.commands.append(self._conditionless_command())
        test.expect_conditions.append(self._condition("velocity_actual", ">", 100.0))

        result = validate_model(model, device_catalog=self._device_catalog(), duplicate_labels=set())

        self.assertFalse(result.ok())
        self.assertTrue(any("expect without until" in issue.message for issue in result.errors))

    def test_serializer_keeps_dsl_fields_and_omits_legacy_duty(self) -> None:
        test = TestModel(
            name=TEST_NAME_DSL,
            test_type="composite",
            devices=[DEVICE_MOTOR],
            enabled=True,
        )
        test.commands.append(self._conditionless_command())
        test.until_conditions.append(self._condition("timer.elapsed", ">=", 4.0))
        test.expect_conditions.append(self._condition("velocity_actual", ">", 100.0))

        payload = model_to_payload(
            TestAuthoringModel(
                default_test_set=TEST_SET_DEFAULT,
                test_sets={TEST_SET_DEFAULT: TestSetModel(name=TEST_SET_DEFAULT, tests=[test])},
            )
        )
        entry = payload["test_sets"][TEST_SET_DEFAULT][0]

        self.assertIn("commands", entry)
        self.assertIn("until", entry)
        self.assertIn("expect", entry)
        self.assertNotIn("duty", entry)
        self.assertNotIn("time", entry)

    def _build_cli(self) -> BridgeCli:
        cli = BridgeCli(_FakeSession(), batch=True)
        cli._tests_model = TestAuthoringModel(
            default_test_set=TEST_SET_DEFAULT,
            test_sets={
                TEST_SET_DEFAULT: TestSetModel(
                    name=TEST_SET_DEFAULT,
                    tests=[
                        TestModel(
                            name=TEST_NAME_DSL,
                            test_type="composite",
                            devices=[],
                            enabled=False,
                        )
                    ],
                )
            },
        )
        cli._tests_active_set = TEST_SET_DEFAULT
        cli._tests_profile = "robot"
        cli._tests_device_catalog = self._device_catalog()
        cli._tests_duplicate_labels = set()
        cli._modes = [CliMode("exec"), CliMode("config"), CliMode("test", test=TEST_NAME_DSL)]
        return cli

    def _device_catalog(self) -> dict[str, dict[str, object]]:
        return {
            DEVICE_MOTOR: {KEY_TYPE: TYPE_MOTOR},
            DEVICE_SWITCH: {KEY_TYPE: TYPE_LIMIT_SWITCH},
        }

    def _conditionless_command(self):
        from tools.common.test_authoring import TestCommandModel

        return TestCommandModel(signal="output_percent_cmd", value=0.25)

    def _condition(self, signal: str, operator: str, value: object):
        from tools.common.test_authoring import TestConditionModel

        return TestConditionModel(signal=signal, operator=operator, value=value)


if __name__ == "__main__":
    unittest.main()
