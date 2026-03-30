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
    DeadbandSweepModel,
    DeviceActionModel,
    TestAuthoringModel,
    TestBindingButton,
    TestBindingJoystick,
    TestModel,
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
    "TestBindingButton",
    "TestBindingJoystick",
    "DeadbandSweepModel",
    "DeviceActionModel",
    "TestModel",
    "TestSetModel",
    "TerminationModel",
    "ValidationIssue",
    "ValidationResult",
    "load_profile_devices",
    "model_from_payload",
    "model_to_payload",
    "validate_model",
    "validate_test_name",
]
