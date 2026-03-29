from __future__ import annotations

"""
NAME
    validator.py - Test authoring validation helpers.

SYNOPSIS
    from tools.common.test_authoring.validator import validate_model

DESCRIPTION
    Validates the authoring model against the feature spec rules. Returns
    structured errors and warnings for UI/CLI display.
"""

from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Set

from .device_catalog import load_profile_devices
from .model import TestAuthoringModel, TestModel


NAME_PATTERN = re.compile(r"^.+$")
INPUT_SEPARATOR = "."
AXIS_INPUTS = {
    "leftX",
    "leftY",
    "rightX",
    "rightY",
    "leftTrigger",
    "rightTrigger",
}
BUTTON_INPUTS = {
    "A",
    "B",
    "X",
    "Y",
    "LB",
    "RB",
    "LS",
    "RS",
    "START",
    "BACK",
    "D_UP",
    "D_DOWN",
    "D_LEFT",
    "D_RIGHT",
}
FIELD_NAME = "name"
FIELD_DEVICES = "devices"
FIELD_JOYSTICK = "joystick"
FIELD_AXIS = "axis"
FIELD_INPUT_SOURCE = "inputSource"
FIELD_DEADBAND = "deadband"
FIELD_BUTTON = "button"
FIELD_DUTY = "duty"
FIELD_TERMINATION = "termination"
FIELD_TYPE = "type"
FIELD_DEADBAND_SWEEP = "deadbandSweep"

MESSAGE_NAME_REQUIRED = "Test name is required."
MESSAGE_NAME_INVALID = "Test name must be non-empty."
MESSAGE_NAME_DUPLICATE = "Duplicate test name."
MESSAGE_DEVICES_REQUIRED = "At least one device is required."
MESSAGE_DEVICE_LABEL_INVALID = "Invalid device label."
MESSAGE_DEVICE_DUPLICATE = "Duplicate device in test."
MESSAGE_DEVICE_NOT_IN_PROFILE = "Device not in active profile."
MESSAGE_DEVICE_LABEL_DUPLICATE = "Duplicate device label in profile: {label}"
MESSAGE_BINDING_JOYSTICK_REQUIRED = "Joystick binding required."
MESSAGE_INPUT_SOURCE_REQUIRED = "inputSource is required."
MESSAGE_INPUT_SOURCE_INVALID = "inputSource must be <controller>.<inputId>."
MESSAGE_INPUT_SOURCE_INPUT_INVALID = "inputSource inputId is invalid."
MESSAGE_INPUT_SOURCE_CONTROLLER_INVALID = "inputSource controller name is invalid."
MESSAGE_DEADBAND_RANGE = "Deadband must be 0.0 to 1.0."
MESSAGE_BINDING_BUTTON_REQUIRED = "Button binding required."
MESSAGE_DUTY_RANGE = "Duty must be -1.0 to 1.0."
MESSAGE_TERMINATION_REQUIRED = "At least one termination is required."
MESSAGE_TEST_TYPE_UNKNOWN = "Unknown test type."
MESSAGE_DEADBAND_SWEEP_REQUIRED = "deadbandSweep config is required."
MESSAGE_DEADBAND_SWEEP_FIELD = "deadbandSweep field is required."
MESSAGE_DEADBAND_SWEEP_SAMPLES = "deadbandSweep requiredSamples must be >= 1."

TEST_TYPE_JOYSTICK = "joystick"
TEST_TYPE_BUTTON = "button"
TEST_TYPE_COMPOSITE = "composite"
TEST_TYPE_DEADBAND_SWEEP = "deadbandSweep"
DEADBAND_MIN = 0.0
DEADBAND_MAX = 1.0
DUTY_MIN = -1.0
DUTY_MAX = 1.0


@dataclass
class ValidationIssue:
    """
    NAME
        ValidationIssue - Single validation warning or error.
    """

    message: str
    test_name: Optional[str] = None
    field: Optional[str] = None


@dataclass
class ValidationResult:
    """
    NAME
        ValidationResult - Validation output with errors and warnings.
    """

    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)

    def ok(self) -> bool:
        """
        NAME
            ok - Return True when no errors were recorded.
        """

        return not self.errors


def validate_test_name(name: str) -> Optional[str]:
    """
    NAME
        validate_test_name - Validate a test name.

    PARAMETERS
        name - Proposed test name.

    RETURNS
        Error message or None when valid.
    """

    if not name or not isinstance(name, str):
        return MESSAGE_NAME_REQUIRED
    if not NAME_PATTERN.match(name.strip()):
        return MESSAGE_NAME_INVALID
    return None


def validate_model(
    model: TestAuthoringModel,
    profile_name: Optional[str] = None,
    controller_names: Optional[Set[str]] = None,
) -> ValidationResult:
    """
    NAME
        validate_model - Validate the full authoring model.

    PARAMETERS
        model - TestAuthoringModel instance.
        profile_name - Optional profile name for device validation.

    RETURNS
        ValidationResult with errors and warnings.
    """

    result = ValidationResult()
    devices_catalog: Dict[str, object] = {}
    duplicate_labels: Set[str] = set()
    if profile_name:
        try:
            devices_catalog, duplicate_labels = load_profile_devices(profile_name)
        except Exception:
            devices_catalog = {}
            duplicate_labels = set()

    for label in sorted(duplicate_labels):
        result.errors.append(
            ValidationIssue(MESSAGE_DEVICE_LABEL_DUPLICATE.format(label=label), None, FIELD_DEVICES)
        )

    for test_set in model.test_sets.values():
        seen_names: Set[str] = set()
        for test in test_set.tests:
            _validate_test(test, result, seen_names, devices_catalog, controller_names)
    return result


def _validate_test(
    test: TestModel,
    result: ValidationResult,
    seen_names: Set[str],
    catalog: Dict[str, object],
    controller_names: Optional[Set[str]],
) -> None:
    """
    NAME
        _validate_test - Validate a single test entry.
    """

    name_error = validate_test_name(test.name)
    if name_error:
        result.errors.append(ValidationIssue(name_error, test.name, FIELD_NAME))
        return
    if test.name in seen_names:
        result.errors.append(ValidationIssue(MESSAGE_NAME_DUPLICATE, test.name, FIELD_NAME))
    else:
        seen_names.add(test.name)

    if not test.devices:
        result.errors.append(ValidationIssue(MESSAGE_DEVICES_REQUIRED, test.name, FIELD_DEVICES))
    else:
        _validate_devices(test, result, catalog)

    if test.test_type == TEST_TYPE_JOYSTICK:
        _validate_joystick(test, result, controller_names)
    elif test.test_type == TEST_TYPE_BUTTON:
        _validate_button(test, result, controller_names)
    elif test.test_type == TEST_TYPE_COMPOSITE:
        _validate_composite(test, result, controller_names)
    elif test.test_type == TEST_TYPE_DEADBAND_SWEEP:
        _validate_deadband_sweep(test, result)
    else:
        result.errors.append(ValidationIssue(MESSAGE_TEST_TYPE_UNKNOWN, test.name, FIELD_TYPE))


def _validate_devices(
    test: TestModel,
    result: ValidationResult,
    catalog: Dict[str, object],
) -> None:
    """
    NAME
        _validate_devices - Validate device labels for a test.
    """

    seen: Set[str] = set()
    for label in test.devices:
        if not isinstance(label, str) or not label.strip():
            result.errors.append(ValidationIssue(MESSAGE_DEVICE_LABEL_INVALID, test.name, FIELD_DEVICES))
            continue
        if label in seen:
            result.warnings.append(ValidationIssue(MESSAGE_DEVICE_DUPLICATE, test.name, FIELD_DEVICES))
        else:
            seen.add(label)
        if catalog and label not in catalog:
            result.warnings.append(
                ValidationIssue(MESSAGE_DEVICE_NOT_IN_PROFILE, test.name, FIELD_DEVICES)
            )


def _validate_joystick(
    test: TestModel,
    result: ValidationResult,
    controller_names: Optional[Set[str]],
) -> None:
    """
    NAME
        _validate_joystick - Validate joystick test settings.
    """

    binding = test.joystick
    if binding is None:
        result.errors.append(
            ValidationIssue(MESSAGE_BINDING_JOYSTICK_REQUIRED, test.name, FIELD_JOYSTICK)
        )
        return
    _validate_input_source(
        test,
        result,
        allowed_inputs=AXIS_INPUTS,
        controller_names=controller_names,
        allow_ui=False,
    )
    if binding.deadband < DEADBAND_MIN or binding.deadband > DEADBAND_MAX:
        result.errors.append(ValidationIssue(MESSAGE_DEADBAND_RANGE, test.name, FIELD_DEADBAND))


def _validate_button(
    test: TestModel,
    result: ValidationResult,
    controller_names: Optional[Set[str]],
) -> None:
    """
    NAME
        _validate_button - Validate button test settings.
    """

    binding = test.button
    if binding is None:
        result.errors.append(
            ValidationIssue(MESSAGE_BINDING_BUTTON_REQUIRED, test.name, FIELD_BUTTON)
        )
        return
    _validate_input_source(
        test,
        result,
        allowed_inputs=BUTTON_INPUTS,
        controller_names=controller_names,
        allow_ui=True,
    )
    if binding.duty < DUTY_MIN or binding.duty > DUTY_MAX:
        result.errors.append(ValidationIssue(MESSAGE_DUTY_RANGE, test.name, FIELD_DUTY))
    if not _has_termination(test):
        result.errors.append(
            ValidationIssue(MESSAGE_TERMINATION_REQUIRED, test.name, FIELD_TERMINATION)
        )


def _validate_composite(
    test: TestModel,
    result: ValidationResult,
    controller_names: Optional[Set[str]],
) -> None:
    """
    NAME
        _validate_composite - Validate composite test settings.
    """

    binding = test.button
    if binding is None:
        result.errors.append(
            ValidationIssue(MESSAGE_BINDING_BUTTON_REQUIRED, test.name, FIELD_BUTTON)
        )
        return
    if test.input_source:
        _validate_input_source(
            test,
            result,
            allowed_inputs=BUTTON_INPUTS,
            controller_names=controller_names,
            allow_ui=True,
        )
    if binding.duty < DUTY_MIN or binding.duty > DUTY_MAX:
        result.errors.append(ValidationIssue(MESSAGE_DUTY_RANGE, test.name, FIELD_DUTY))
    if not _has_termination(test):
        result.errors.append(
            ValidationIssue(MESSAGE_TERMINATION_REQUIRED, test.name, FIELD_TERMINATION)
        )


def _validate_deadband_sweep(test: TestModel, result: ValidationResult) -> None:
    """
    NAME
        _validate_deadband_sweep - Validate deadband sweep settings.
    """

    sweep = test.deadband_sweep
    if sweep is None:
        result.errors.append(
            ValidationIssue(MESSAGE_DEADBAND_SWEEP_REQUIRED, test.name, FIELD_DEADBAND_SWEEP)
        )
        return
    required_fields = {
        "start_duty": sweep.start_duty,
        "max_duty": sweep.max_duty,
        "step_duty": sweep.step_duty,
        "step_hold_sec": sweep.step_hold_sec,
        "motion_threshold_rot": sweep.motion_threshold_rot,
        "required_samples": sweep.required_samples,
        "encoder_key": sweep.encoder_key,
    }
    for field_name, value in required_fields.items():
        if value is None or value == "":
            result.errors.append(
                ValidationIssue(MESSAGE_DEADBAND_SWEEP_FIELD, test.name, field_name)
            )
    if sweep.required_samples is not None and sweep.required_samples < 1:
        result.errors.append(
            ValidationIssue(MESSAGE_DEADBAND_SWEEP_SAMPLES, test.name, FIELD_DEADBAND_SWEEP)
        )

def _has_termination(test: TestModel) -> bool:
    """
    NAME
        _has_termination - Return True when a termination rule exists.
    """

    term = test.termination
    if term.hold_enabled:
        return True
    if term.time_sec is not None:
        return True
    if term.rotation_limit is not None:
        return True
    if term.limit_switch:
        return True
    return False


def _validate_input_source(
    test: TestModel,
    result: ValidationResult,
    allowed_inputs: Set[str],
    controller_names: Optional[Set[str]],
    allow_ui: bool,
) -> None:
    """
    NAME
        _validate_input_source - Validate inputSource syntax and allowed inputs.
    """

    source = test.input_source
    if not source or not isinstance(source, str):
        result.errors.append(ValidationIssue(MESSAGE_INPUT_SOURCE_REQUIRED, test.name, FIELD_INPUT_SOURCE))
        return
    if INPUT_SEPARATOR not in source:
        result.errors.append(ValidationIssue(MESSAGE_INPUT_SOURCE_INVALID, test.name, FIELD_INPUT_SOURCE))
        return
    controller, input_id = source.split(INPUT_SEPARATOR, 1)
    if not controller or not input_id:
        result.errors.append(ValidationIssue(MESSAGE_INPUT_SOURCE_INVALID, test.name, FIELD_INPUT_SOURCE))
        return
    if allow_ui and controller == "ui":
        return
    if controller_names is not None and controller not in controller_names:
        result.errors.append(ValidationIssue(MESSAGE_INPUT_SOURCE_CONTROLLER_INVALID, test.name, FIELD_INPUT_SOURCE))
    if input_id not in allowed_inputs:
        result.errors.append(ValidationIssue(MESSAGE_INPUT_SOURCE_INPUT_INVALID, test.name, FIELD_INPUT_SOURCE))
