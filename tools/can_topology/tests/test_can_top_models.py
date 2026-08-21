from __future__ import annotations

import unittest

from tools.can_topology.can_top_models import (
    INTERFACE_CAN,
    MODEL_CTRE_FALCON_500,
    MODEL_CTRE_KRAKEN_X60,
    MODEL_REV_VORTEX,
    MODEL_REV_NEO,
    MODEL_ROBORIO,
    MODEL_SYSTEMCORE,
    VENDOR_CTRE,
    category_device_defaults,
    canonicalize_model_for_context,
    model_choices_for_context,
)


class CanTopModelsTests(unittest.TestCase):
    """
    NAME
        CanTopModelsTests - Validate shared topology model/default helpers.
    """

    def test_category_device_defaults_define_robot_controller_and_falcon_defaults(self) -> None:
        self.assertEqual(
            ("NI", "robotController", MODEL_ROBORIO),
            category_device_defaults("robotController", INTERFACE_CAN),
        )
        self.assertEqual(
            (VENDOR_CTRE, "FALCON", MODEL_CTRE_FALCON_500),
            category_device_defaults("falcons", INTERFACE_CAN),
        )

    def test_model_choices_for_context_return_vendor_specific_motor_choices(self) -> None:
        self.assertEqual(
            [MODEL_CTRE_FALCON_500, MODEL_CTRE_KRAKEN_X60, "CTRE Kraken X44"],
            model_choices_for_context("devices", VENDOR_CTRE, "MotorController", INTERFACE_CAN),
        )
        self.assertEqual(
            [MODEL_REV_NEO],
            model_choices_for_context("neos", "", "", INTERFACE_CAN),
        )
        self.assertEqual(
            [MODEL_REV_VORTEX],
            model_choices_for_context("flexes", "", "", INTERFACE_CAN),
        )

    def test_canonicalize_model_for_context_normalizes_legacy_aliases(self) -> None:
        self.assertEqual(
            MODEL_CTRE_FALCON_500,
            canonicalize_model_for_context("Falcon 500", "falcons", VENDOR_CTRE, "FALCON", INTERFACE_CAN),
        )
        self.assertEqual(
            MODEL_ROBORIO,
            canonicalize_model_for_context("NI roboRIO", "robotController", "NI", "robotController", INTERFACE_CAN),
        )
        self.assertEqual(
            MODEL_SYSTEMCORE,
            canonicalize_model_for_context("systemcore", "robotController", "NI", "robotController", INTERFACE_CAN),
        )
