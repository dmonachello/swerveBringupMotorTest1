"""
NAME
    test_authoring - Shared test authoring model/validation/serialization.

DESCRIPTION
    Provides a shared in-memory model, validation, and JSON serializer for
    bringup_tests.json editing workflows. This package is used by UI and CLI
    tooling to avoid duplicate logic.
"""

from .device_catalog import load_profile_devices
from .model import (
    BUILTIN_TIMER_NAME,
    CONDITION_OPERATOR_EQ,
    CONDITION_OPERATOR_GT,
    CONDITION_OPERATOR_GTE,
    CONDITION_OPERATOR_LT,
    CONDITION_OPERATOR_LTE,
    CONDITION_OPERATOR_NE,
    DeadbandSweepModel,
    DEVICE_ROLE_OBSERVER,
    DEVICE_ROLE_PRIMARY,
    DeviceActionModel,
    PSEUDO_DEVICE_TYPE_TEST_TIMER,
    TestAuthoringModel,
    TestBindingButton,
    TestBindingJoystick,
    TestCommandModel,
    TestConditionModel,
    TestDeviceRef,
    TestModel,
    TestPseudoDeviceModel,
    TestSetModel,
    TerminationModel,
)
from .serializer import (
    model_from_payload,
    model_to_payload,
)
from .validator import (
    ValidationIssue,
    ValidationResult,
    validate_model,
    validate_test_name,
)

__all__ = [
    "TestAuthoringModel",
    "TestCommandModel",
    "TestConditionModel",
    "TestDeviceRef",
    "TestBindingButton",
    "TestBindingJoystick",
    "DeadbandSweepModel",
    "DeviceActionModel",
    "TestModel",
    "TestPseudoDeviceModel",
    "TestSetModel",
    "TerminationModel",
    "DEVICE_ROLE_PRIMARY",
    "DEVICE_ROLE_OBSERVER",
    "PSEUDO_DEVICE_TYPE_TEST_TIMER",
    "BUILTIN_TIMER_NAME",
    "CONDITION_OPERATOR_GT",
    "CONDITION_OPERATOR_GTE",
    "CONDITION_OPERATOR_LT",
    "CONDITION_OPERATOR_LTE",
    "CONDITION_OPERATOR_EQ",
    "CONDITION_OPERATOR_NE",
    "ValidationIssue",
    "ValidationResult",
    "load_profile_devices",
    "model_from_payload",
    "model_to_payload",
    "validate_model",
    "validate_test_name",
]
