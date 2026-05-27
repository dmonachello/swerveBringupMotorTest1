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
from typing import Dict, List, Optional, Set, Tuple

from .device_catalog import load_profile_devices
from tools.common.profile_constants import (
    INTERFACE_DIO,
    KEY_INTERFACE,
    KEY_INTERFACE_LEGACY,
    KEY_TYPE,
    TYPE_ENCODER_EXTERNAL,
    TYPE_LIMIT_SWITCH,
    TYPE_MOTOR,
    get_device_interface,
)
from .model import (
    BUILTIN_TIMER_NAME,
    CONDITION_OPERATOR_EQ,
    CONDITION_OPERATOR_GT,
    CONDITION_OPERATOR_GTE,
    CONDITION_OPERATOR_LT,
    CONDITION_OPERATOR_LTE,
    CONDITION_OPERATOR_NE,
    DEVICE_ROLE_OBSERVER,
    DEVICE_ROLE_PRIMARY,
    PSEUDO_DEVICE_TYPE_TEST_TIMER,
    TestAuthoringModel,
    TestCommandModel,
    TestConditionModel,
    TestModel,
)


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
FIELD_ACTION = "action"
FIELD_COLOR = "color"
FIELD_PATTERN = "pattern"
FIELD_BRIGHTNESS = "brightness"
FIELD_DURATION = "durationSec"
FIELD_BUTTON = "button"
FIELD_DUTY = "duty"
FIELD_TERMINATION = "termination"
FIELD_LIMIT_SWITCH = "limitSwitch"
FIELD_LIMIT_SWITCH_ENABLED = "enabled"
FIELD_LIMIT_SWITCH_ON_HIT = "onHit"
FIELD_LIMIT_SWITCH_ID = "id"
FIELD_TYPE = "type"
FIELD_DEADBAND_SWEEP = "deadbandSweep"
FIELD_DSL_COMMANDS = "commands"
FIELD_DSL_EXPECT = "expect"
FIELD_DSL_UNTIL = "until"
FIELD_DSL_SUCCESS = "success"
FIELD_DSL_ABORT = "abort"
FIELD_DSL_PASSIVE = "passive"
FIELD_DSL_MANUAL_STOP = "manualStop"
FIELD_DSL_OBSERVERS = "observerDevices"
FIELD_DSL_CREATED_DEVICES = "createdDevices"
FIELD_DSL_ROLE = "role"
FIELD_DSL_DEVICE_TYPE = "deviceType"

MESSAGE_NAME_REQUIRED = "Test name is required."
MESSAGE_NAME_INVALID = "Test name must be non-empty."
MESSAGE_NAME_DUPLICATE = "Duplicate test name."
MESSAGE_DEVICES_REQUIRED = "At least one device is required."
MESSAGE_DEVICE_LABEL_INVALID = "Invalid device label."
MESSAGE_DEVICE_DUPLICATE = "Duplicate device in test."
MESSAGE_DEVICE_NOT_IN_PROFILE = "Device not in active profile."
MESSAGE_DEVICE_LABEL_DUPLICATE = (
    "Duplicate device label in profile: {label}. Fix: remove the duplicate label "
    "from the profile device list."
)
MESSAGE_BINDING_JOYSTICK_REQUIRED = "Joystick binding required."
MESSAGE_INPUT_SOURCE_REQUIRED = "inputSource is required."
MESSAGE_INPUT_SOURCE_INVALID = "inputSource must be <controller>.<inputId>."
MESSAGE_INPUT_SOURCE_INPUT_INVALID = "inputSource inputId is invalid."
MESSAGE_INPUT_SOURCE_CONTROLLER_INVALID = "inputSource controller name is invalid."
MESSAGE_DEADBAND_RANGE = "Deadband must be 0.0 to 1.0."
MESSAGE_BINDING_BUTTON_REQUIRED = "Button binding required."
MESSAGE_DUTY_RANGE = "Duty must be -1.0 to 1.0."
MESSAGE_TERMINATION_REQUIRED = (
    "At least one termination is required. Fix: add one of "
    "termination hold | termination time <sec> | termination rotation <rot> | "
    "termination limitswitch <label>."
)
MESSAGE_TEST_TYPE_UNKNOWN = "Unknown test type."
MESSAGE_DEADBAND_SWEEP_REQUIRED = "deadbandSweep config is required."
MESSAGE_DEADBAND_SWEEP_FIELD = "deadbandSweep field is required."
MESSAGE_DEADBAND_SWEEP_SAMPLES = "deadbandSweep requiredSamples must be >= 1."
MESSAGE_ACTION_REQUIRED = "action is required."
MESSAGE_ACTION_INVALID = "action must be toggle_led or set_color."
MESSAGE_COLOR_REQUIRED = "color is required for set_color."
MESSAGE_COLOR_INVALID = "color must be #RRGGBB."
MESSAGE_PATTERN_INVALID = "pattern is not supported."
MESSAGE_BRIGHTNESS_RANGE = "brightness must be 0.0 to 1.0."
MESSAGE_DURATION_RANGE = "durationSec must be >= 0."
MESSAGE_LIMIT_SWITCH_REQUIRED = "limitSwitch must be an object."
MESSAGE_LIMIT_SWITCH_ENABLED = "limitSwitch.enabled must be true/false."
MESSAGE_LIMIT_SWITCH_ON_HIT = "limitSwitch.onHit must be pass or fail."
MESSAGE_LIMIT_SWITCH_ID = "limitSwitch.id must be a non-empty string."
MESSAGE_LIMIT_SWITCH_ID_REQUIRED = (
    "limitSwitch.id is required when limitSwitch is enabled. Fix: set it with "
    "limitswitch id <label>."
)
MESSAGE_LIMIT_SWITCH_NOT_FOUND = (
    "limitSwitch.id not found in active profile. Fix: add the label to the active "
    "profile device list and define it in the device registry."
)
MESSAGE_LIMIT_SWITCH_TYPE_INVALID = "limitSwitch.id must reference a limitSwitch device."
MESSAGE_DSL_COMPOSITE_ONLY = "DSL conditions and commands are supported only on composite tests."
MESSAGE_DSL_UNKNOWN_DEVICE = "Unknown device."
MESSAGE_DSL_DUPLICATE_DEVICE = "Duplicate device reference."
MESSAGE_DSL_DUPLICATE_CREATED_DEVICE = "Duplicate created device."
MESSAGE_DSL_RESERVED_DEVICE = "Reserved built-in device name."
MESSAGE_DSL_CREATED_TYPE = "Created device type is not supported."
MESSAGE_DSL_EXPECT_WITHOUT_UNTIL = "expect without until is invalid."
MESSAGE_DSL_STOP_REQUIRED = "A runnable DSL test requires abort, success, or until unless manualStop is true."
MESSAGE_DSL_COMMAND_OR_PASSIVE = "A runnable DSL test requires a command unless passive is true."
MESSAGE_DSL_UNKNOWN_SIGNAL = "Unknown signal."
MESSAGE_DSL_INVALID_OPERATOR = "Invalid operator."
MESSAGE_DSL_DEVICE_REQUIRED = "Device-scoped signal requires a bound device."
MESSAGE_DSL_EXPLICIT_DEVICE_REQUIRED = "Explicit device reference must resolve to a bound device."
MESSAGE_DSL_READ_ONLY_COMMAND = "Command targets a read-only signal."
MESSAGE_DSL_UNSUPPORTED_COMMAND = "Unsupported command for targeted device."
MESSAGE_DSL_UNSUPPORTED_EXPANDED_SIGNAL = "Unsupported expanded signal."
MESSAGE_DSL_MIXED_SUPPORT = "Mixed primary-device support for expanded signal."
MESSAGE_DSL_BOOLEAN_OPERATOR = "Boolean signals require == or !=."
MESSAGE_DSL_BOOLEAN_VALUE = "Boolean signal requires true or false."
MESSAGE_DSL_NUMERIC_VALUE = "Numeric signal requires a numeric value."
MESSAGE_DSL_NO_PRIMARY = "Unqualified signal requires at least one primary device."
MESSAGE_DSL_SUCCESS_TIMER = "success using timer.elapsed is discouraged."
MESSAGE_DSL_UNTIL_WITHOUT_EXPECT = "until without expect."
MESSAGE_DSL_MANUAL_STOP_WARNING = "No declared stop condition; external stop is required."
MESSAGE_DSL_COLLISION_CREATED_DEVICE = "Created device collides with an existing bound device."

TEST_TYPE_JOYSTICK = "joystick"
TEST_TYPE_BUTTON = "button"
TEST_TYPE_COMPOSITE = "composite"
TEST_TYPE_DEADBAND_SWEEP = "deadbandSweep"
TEST_TYPE_DEVICE_ACTION = "deviceAction"
LIMIT_SWITCH_DEVICE_TYPE = "limitSwitch"
DEADBAND_MIN = 0.0
DEADBAND_MAX = 1.0
DUTY_MIN = -1.0
DUTY_MAX = 1.0
BRIGHTNESS_MIN = 0.0
BRIGHTNESS_MAX = 1.0
DURATION_MIN_SEC = 0.0
DURATION_PASS = "pass"
DURATION_FAIL = "fail"
LIMIT_SWITCH_ON_HIT_ALLOWED = {DURATION_PASS, DURATION_FAIL}
ACTION_TOGGLE_LED = "toggle_led"
ACTION_SET_COLOR = "set_color"
ACTION_ALLOWED = {ACTION_TOGGLE_LED, ACTION_SET_COLOR}
PATTERN_SOLID = "solid"
PATTERN_ALLOWED = {PATTERN_SOLID}
COLOR_PREFIX = "#"
COLOR_HEX_LEN = 7
COLOR_HEX_REGEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
DSL_COMPARISON_OPERATORS = {
    CONDITION_OPERATOR_GT,
    CONDITION_OPERATOR_GTE,
    CONDITION_OPERATOR_LT,
    CONDITION_OPERATOR_LTE,
    CONDITION_OPERATOR_EQ,
    CONDITION_OPERATOR_NE,
}
DSL_NUMERIC_SIGNALS = {
    "current",
    "velocity_actual",
    "current_actual",
    "temperature",
    "temperature_actual",
    "velocity",
    "position",
    "position_actual",
    "position_delta",
    "elapsed",
    "output",
    "output_percent_cmd",
    "output_percent_applied",
}
DSL_BOOLEAN_SIGNALS = {
    "pressed",
}
DSL_COMMAND_SIGNALS = {
    "output",
    "output_percent_cmd",
}
DSL_TIMER_SIGNALS = {
    "elapsed",
}


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
    device_catalog: Optional[Dict[str, object]] = None,
    duplicate_labels: Optional[Set[str]] = None,
) -> ValidationResult:
    """
    NAME
        validate_model - Validate the full authoring model.

    PARAMETERS
        model - TestAuthoringModel instance.
        profile_name - Optional profile name for device validation.
        controller_names - Optional set of valid controller names.
        device_catalog - Optional device catalog mapping.
        duplicate_labels - Optional duplicate label set.

    RETURNS
        ValidationResult with errors and warnings.
    """

    result = ValidationResult()
    devices_catalog: Dict[str, object] = {}
    duplicate_label_set: Set[str] = set()
    if device_catalog is not None:
        devices_catalog = device_catalog
    if duplicate_labels is not None:
        duplicate_label_set = duplicate_labels
    if profile_name and device_catalog is None:
        try:
            devices_catalog, duplicate_label_set = load_profile_devices(profile_name)
        except Exception:
            devices_catalog = {}
            duplicate_label_set = set()

    for label in sorted(duplicate_label_set):
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

    if test.test_type == TEST_TYPE_COMPOSITE or _uses_dsl(test):
        _validate_dsl_test(test, result, catalog)
        return

    if test.test_type == TEST_TYPE_JOYSTICK:
        if not test.devices:
            result.errors.append(ValidationIssue(MESSAGE_DEVICES_REQUIRED, test.name, FIELD_DEVICES))
        else:
            _validate_devices(test, result, catalog)
        _validate_joystick(test, result, controller_names)
    elif test.test_type == TEST_TYPE_BUTTON:
        if not test.devices:
            result.errors.append(ValidationIssue(MESSAGE_DEVICES_REQUIRED, test.name, FIELD_DEVICES))
        else:
            _validate_devices(test, result, catalog)
        _validate_button(test, result, controller_names, catalog)
    elif test.test_type == TEST_TYPE_DEADBAND_SWEEP:
        if not test.devices:
            result.errors.append(ValidationIssue(MESSAGE_DEVICES_REQUIRED, test.name, FIELD_DEVICES))
        else:
            _validate_devices(test, result, catalog)
        _validate_deadband_sweep(test, result)
    elif test.test_type == TEST_TYPE_DEVICE_ACTION:
        if not test.devices:
            result.errors.append(ValidationIssue(MESSAGE_DEVICES_REQUIRED, test.name, FIELD_DEVICES))
        else:
            _validate_devices(test, result, catalog)
        _validate_device_action(test, result)
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


def _uses_dsl(test: TestModel) -> bool:
    """
    NAME
        _uses_dsl - Return True when a test uses DSL-only fields.
    """

    return bool(
        test.observers
        or test.pseudo_devices
        or test.commands
        or test.until_conditions
        or test.expect_conditions
        or test.success_conditions
        or test.abort_conditions
        or test.passive
        or test.manual_stop
    )


def _validate_dsl_test(
    test: TestModel,
    result: ValidationResult,
    catalog: Dict[str, object],
) -> None:
    """
    NAME
        _validate_dsl_test - Validate DSL-style test declarations.
    """

    if test.test_type != TEST_TYPE_COMPOSITE:
        result.errors.append(
            ValidationIssue(MESSAGE_DSL_COMPOSITE_ONLY, test.name, FIELD_TYPE)
        )
    _validate_dsl_bound_devices(test, result, catalog)
    _validate_dsl_created_devices(test, result)
    _validate_dsl_commands(test, result, catalog)
    _validate_dsl_conditions(test, result, catalog)
    if test.expect_conditions and not test.until_conditions:
        result.errors.append(
            ValidationIssue(MESSAGE_DSL_EXPECT_WITHOUT_UNTIL, test.name, FIELD_DSL_EXPECT)
        )
    if not _has_dsl_stop_condition(test):
        if test.manual_stop:
            result.warnings.append(
                ValidationIssue(MESSAGE_DSL_MANUAL_STOP_WARNING, test.name, FIELD_DSL_MANUAL_STOP)
            )
        else:
            result.errors.append(
                ValidationIssue(MESSAGE_DSL_STOP_REQUIRED, test.name, FIELD_DSL_MANUAL_STOP)
            )
    elif test.until_conditions and not test.expect_conditions:
        result.warnings.append(
            ValidationIssue(MESSAGE_DSL_UNTIL_WITHOUT_EXPECT, test.name, FIELD_DSL_UNTIL)
        )
    if not test.commands and not test.passive:
        result.errors.append(
            ValidationIssue(MESSAGE_DSL_COMMAND_OR_PASSIVE, test.name, FIELD_DSL_COMMANDS)
        )


def _validate_dsl_bound_devices(
    test: TestModel,
    result: ValidationResult,
    catalog: Dict[str, object],
) -> None:
    """
    NAME
        _validate_dsl_bound_devices - Validate primary and observer device bindings.
    """

    seen: Set[str] = set()
    for field_name, labels in (
        (FIELD_DEVICES, test.devices),
        (FIELD_DSL_OBSERVERS, test.observers),
    ):
        for label in labels:
            normalized = _normalized_name(label)
            if not normalized:
                result.errors.append(
                    ValidationIssue(MESSAGE_DEVICE_LABEL_INVALID, test.name, field_name)
                )
                continue
            if normalized in seen:
                result.errors.append(
                    ValidationIssue(MESSAGE_DSL_DUPLICATE_DEVICE, test.name, field_name)
                )
            else:
                seen.add(normalized)
            if catalog and label not in catalog:
                result.errors.append(
                    ValidationIssue(MESSAGE_DSL_UNKNOWN_DEVICE, test.name, field_name)
                )


def _validate_dsl_created_devices(test: TestModel, result: ValidationResult) -> None:
    """
    NAME
        _validate_dsl_created_devices - Validate pseudo-device declarations.
    """

    seen: Set[str] = set()
    bound = {_normalized_name(label) for label in list(test.devices) + list(test.observers)}
    for device in test.pseudo_devices:
        normalized = _normalized_name(device.name)
        if not normalized:
            result.errors.append(
                ValidationIssue(MESSAGE_DEVICE_LABEL_INVALID, test.name, FIELD_DSL_CREATED_DEVICES)
            )
            continue
        if normalized == BUILTIN_TIMER_NAME.lower():
            result.errors.append(
                ValidationIssue(MESSAGE_DSL_RESERVED_DEVICE, test.name, FIELD_DSL_CREATED_DEVICES)
            )
        if normalized in seen:
            result.errors.append(
                ValidationIssue(
                    MESSAGE_DSL_DUPLICATE_CREATED_DEVICE, test.name, FIELD_DSL_CREATED_DEVICES
                )
            )
        else:
            seen.add(normalized)
        if normalized in bound:
            result.errors.append(
                ValidationIssue(
                    MESSAGE_DSL_COLLISION_CREATED_DEVICE, test.name, FIELD_DSL_CREATED_DEVICES
                )
            )
        if device.device_type != PSEUDO_DEVICE_TYPE_TEST_TIMER:
            result.errors.append(
                ValidationIssue(MESSAGE_DSL_CREATED_TYPE, test.name, FIELD_DSL_DEVICE_TYPE)
            )


def _validate_dsl_commands(
    test: TestModel,
    result: ValidationResult,
    catalog: Dict[str, object],
) -> None:
    """
    NAME
        _validate_dsl_commands - Validate command assignments.
    """

    for command in test.commands:
        targets, signal_name, explicit = _resolve_signal_targets(test, command.signal, catalog)
        if targets is None:
            result.errors.append(
                ValidationIssue(MESSAGE_DSL_DEVICE_REQUIRED, test.name, FIELD_DSL_COMMANDS)
            )
            continue
        if signal_name not in DSL_COMMAND_SIGNALS:
            result.errors.append(
                ValidationIssue(MESSAGE_DSL_READ_ONLY_COMMAND, test.name, FIELD_DSL_COMMANDS)
            )
            continue
        if not explicit and not targets:
            result.errors.append(
                ValidationIssue(MESSAGE_DSL_NO_PRIMARY, test.name, FIELD_DSL_COMMANDS)
            )
            continue
        for target_name, target_kind in targets:
            if not _device_supports_signal(target_kind, signal_name):
                result.errors.append(
                    ValidationIssue(
                        MESSAGE_DSL_UNSUPPORTED_COMMAND, test.name, FIELD_DSL_COMMANDS
                    )
                )
                break
        if not _is_numeric_value(command.value):
            result.errors.append(
                ValidationIssue(MESSAGE_DSL_NUMERIC_VALUE, test.name, FIELD_DSL_COMMANDS)
            )


def _validate_dsl_conditions(
    test: TestModel,
    result: ValidationResult,
    catalog: Dict[str, object],
) -> None:
    """
    NAME
        _validate_dsl_conditions - Validate abort/success/until/expect conditions.
    """

    for field_name, conditions in (
        (FIELD_DSL_ABORT, test.abort_conditions),
        (FIELD_DSL_SUCCESS, test.success_conditions),
        (FIELD_DSL_UNTIL, test.until_conditions),
        (FIELD_DSL_EXPECT, test.expect_conditions),
    ):
        for condition in conditions:
            _validate_dsl_condition(test, result, catalog, field_name, condition)
            if (
                field_name == FIELD_DSL_SUCCESS
                and condition.signal == BUILTIN_TIMER_NAME + INPUT_SEPARATOR + "elapsed"
            ):
                result.warnings.append(
                    ValidationIssue(MESSAGE_DSL_SUCCESS_TIMER, test.name, FIELD_DSL_SUCCESS)
                )


def _validate_dsl_condition(
    test: TestModel,
    result: ValidationResult,
    catalog: Dict[str, object],
    field_name: str,
    condition: TestConditionModel,
) -> None:
    """
    NAME
        _validate_dsl_condition - Validate one DSL condition expression.
    """

    if condition.operator not in DSL_COMPARISON_OPERATORS:
        result.errors.append(
            ValidationIssue(MESSAGE_DSL_INVALID_OPERATOR, test.name, field_name)
        )
        return
    targets, signal_name, explicit = _resolve_signal_targets(test, condition.signal, catalog)
    if targets is None:
        message = MESSAGE_DSL_EXPLICIT_DEVICE_REQUIRED if _is_explicit_signal(condition.signal) else MESSAGE_DSL_DEVICE_REQUIRED
        result.errors.append(ValidationIssue(message, test.name, field_name))
        return
    if not explicit and not targets:
        result.errors.append(ValidationIssue(MESSAGE_DSL_NO_PRIMARY, test.name, field_name))
        return
    supports = [_device_supports_signal(target_kind, signal_name) for _, target_kind in targets]
    if not all(supports):
        message = MESSAGE_DSL_UNSUPPORTED_EXPANDED_SIGNAL
        if not explicit and any(supports):
            message = MESSAGE_DSL_MIXED_SUPPORT
        result.errors.append(ValidationIssue(message, test.name, field_name))
        return
    if signal_name in DSL_BOOLEAN_SIGNALS:
        if condition.operator not in (CONDITION_OPERATOR_EQ, CONDITION_OPERATOR_NE):
            result.errors.append(
                ValidationIssue(MESSAGE_DSL_BOOLEAN_OPERATOR, test.name, field_name)
            )
        if not isinstance(condition.value, bool):
            result.errors.append(
                ValidationIssue(MESSAGE_DSL_BOOLEAN_VALUE, test.name, field_name)
            )
    elif signal_name in DSL_NUMERIC_SIGNALS:
        if not _is_numeric_value(condition.value):
            result.errors.append(
                ValidationIssue(MESSAGE_DSL_NUMERIC_VALUE, test.name, field_name)
            )
    else:
        result.errors.append(
            ValidationIssue(MESSAGE_DSL_UNKNOWN_SIGNAL, test.name, field_name)
        )


def _has_dsl_stop_condition(test: TestModel) -> bool:
    """
    NAME
        _has_dsl_stop_condition - Return True when the DSL test can stop normally.
    """

    return bool(test.abort_conditions or test.success_conditions or test.until_conditions)


def _resolve_signal_targets(
    test: TestModel,
    signal_ref: str,
    catalog: Dict[str, object],
) -> Tuple[Optional[List[Tuple[str, str]]], str, bool]:
    """
    NAME
        _resolve_signal_targets - Resolve signal targets and signal name.
    """

    if not isinstance(signal_ref, str) or not signal_ref.strip():
        return (None, "", False)
    raw = signal_ref.strip()
    if _is_explicit_signal(raw):
        device_name, signal_name = raw.rsplit(INPUT_SEPARATOR, 1)
        target_kind = _resolve_device_kind(test, catalog, device_name)
        if target_kind is None:
            return (None, signal_name, True)
        return ([(device_name, target_kind)], signal_name, True)
    primary_targets = []
    for device_name in test.devices:
        target_kind = _resolve_device_kind(test, catalog, device_name)
        if target_kind is not None:
            primary_targets.append((device_name, target_kind))
    return (primary_targets, raw, False)


def _resolve_device_kind(
    test: TestModel,
    catalog: Dict[str, object],
    device_name: str,
) -> Optional[str]:
    """
    NAME
        _resolve_device_kind - Resolve device kind for DSL signal validation.
    """

    normalized = _normalized_name(device_name)
    if not normalized:
        return None
    if normalized == BUILTIN_TIMER_NAME.lower():
        return PSEUDO_DEVICE_TYPE_TEST_TIMER
    for device in test.pseudo_devices:
        if _normalized_name(device.name) == normalized:
            return device.device_type
    entry = catalog.get(device_name)
    if isinstance(entry, dict):
        device_type = entry.get(KEY_TYPE)
        if isinstance(device_type, str) and device_type.strip():
            return device_type.strip()
    return None


def _device_supports_signal(device_kind: str, signal_name: str) -> bool:
    """
    NAME
        _device_supports_signal - Return True when a device kind supports a signal.
    """

    if device_kind == PSEUDO_DEVICE_TYPE_TEST_TIMER:
        return signal_name in DSL_TIMER_SIGNALS
    if device_kind == TYPE_MOTOR:
        return signal_name in DSL_NUMERIC_SIGNALS
    if device_kind == TYPE_LIMIT_SWITCH:
        return signal_name in DSL_BOOLEAN_SIGNALS
    if device_kind == TYPE_ENCODER_EXTERNAL:
        return signal_name in {"position", "position_actual", "position_delta"}
    return False


def _normalized_name(value: object) -> str:
    """
    NAME
        _normalized_name - Normalize a device-like name.
    """

    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _is_explicit_signal(signal_ref: str) -> bool:
    """
    NAME
        _is_explicit_signal - Return True when a signal ref includes a device prefix.
    """

    return isinstance(signal_ref, str) and INPUT_SEPARATOR in signal_ref


def _is_numeric_value(value: object) -> bool:
    """
    NAME
        _is_numeric_value - Return True for int/float excluding bool.
    """

    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
    catalog: Dict[str, object],
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
    _validate_limit_switch(test, result, catalog)


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


def _validate_device_action(test: TestModel, result: ValidationResult) -> None:
    """
    NAME
        _validate_device_action - Validate deviceAction tests.
    """

    action = test.device_action.action if test.device_action else None
    if not action:
        result.errors.append(ValidationIssue(MESSAGE_ACTION_REQUIRED, test.name, FIELD_ACTION))
        return
    if action not in ACTION_ALLOWED:
        result.errors.append(ValidationIssue(MESSAGE_ACTION_INVALID, test.name, FIELD_ACTION))
        return
    if action == ACTION_SET_COLOR:
        color = test.device_action.color if test.device_action else None
        if not color:
            result.errors.append(ValidationIssue(MESSAGE_COLOR_REQUIRED, test.name, FIELD_COLOR))
        elif not COLOR_HEX_REGEX.match(color):
            result.errors.append(ValidationIssue(MESSAGE_COLOR_INVALID, test.name, FIELD_COLOR))
        pattern = test.device_action.pattern if test.device_action else None
        if pattern and pattern not in PATTERN_ALLOWED:
            result.errors.append(ValidationIssue(MESSAGE_PATTERN_INVALID, test.name, FIELD_PATTERN))
        brightness = test.device_action.brightness if test.device_action else None
        if brightness is not None and (brightness < BRIGHTNESS_MIN or brightness > BRIGHTNESS_MAX):
            result.errors.append(ValidationIssue(MESSAGE_BRIGHTNESS_RANGE, test.name, FIELD_BRIGHTNESS))
        duration_sec = test.device_action.duration_sec if test.device_action else None
        if duration_sec is not None and duration_sec < DURATION_MIN_SEC:
            result.errors.append(ValidationIssue(MESSAGE_DURATION_RANGE, test.name, FIELD_DURATION))

def _validate_limit_switch(
    test: TestModel,
    result: ValidationResult,
    catalog: Dict[str, object],
) -> None:
    """
    NAME
        _validate_limit_switch - Validate limitSwitch termination configuration.
    """

    term = test.termination
    limit_switch = term.limit_switch
    if limit_switch is None:
        return
    if not isinstance(limit_switch, dict):
        result.errors.append(
            ValidationIssue(MESSAGE_LIMIT_SWITCH_REQUIRED, test.name, FIELD_LIMIT_SWITCH)
        )
        return
    enabled = limit_switch.get(FIELD_LIMIT_SWITCH_ENABLED)
    if enabled is not None and not isinstance(enabled, bool):
        result.errors.append(
            ValidationIssue(MESSAGE_LIMIT_SWITCH_ENABLED, test.name, FIELD_LIMIT_SWITCH)
        )
    on_hit = limit_switch.get(FIELD_LIMIT_SWITCH_ON_HIT)
    if on_hit is not None:
        if not isinstance(on_hit, str) or on_hit not in LIMIT_SWITCH_ON_HIT_ALLOWED:
            result.errors.append(
                ValidationIssue(MESSAGE_LIMIT_SWITCH_ON_HIT, test.name, FIELD_LIMIT_SWITCH)
            )
    limit_id = limit_switch.get(FIELD_LIMIT_SWITCH_ID)
    if limit_id is not None and (not isinstance(limit_id, str) or not limit_id.strip()):
        result.errors.append(
            ValidationIssue(MESSAGE_LIMIT_SWITCH_ID, test.name, FIELD_LIMIT_SWITCH)
        )
        return
    if enabled is not False:
        if limit_id is None:
            result.errors.append(
                ValidationIssue(MESSAGE_LIMIT_SWITCH_ID_REQUIRED, test.name, FIELD_LIMIT_SWITCH)
            )
            return
        if not isinstance(limit_id, str) or not limit_id.strip():
            result.errors.append(
                ValidationIssue(MESSAGE_LIMIT_SWITCH_ID, test.name, FIELD_LIMIT_SWITCH)
            )
            return
        if catalog and limit_id not in catalog:
            result.errors.append(
                ValidationIssue(MESSAGE_LIMIT_SWITCH_NOT_FOUND, test.name, FIELD_LIMIT_SWITCH)
            )
            return
        if catalog and limit_id in catalog:
            entry = catalog.get(limit_id)
            if isinstance(entry, dict):
                interface = entry.get(KEY_INTERFACE)
                if interface is None and entry.get(KEY_INTERFACE_LEGACY) is not None:
                    entry[KEY_INTERFACE] = entry.get(KEY_INTERFACE_LEGACY)
                    interface = entry.get(KEY_INTERFACE)
                if interface is None:
                    interface = get_device_interface(entry)
                device_type = entry.get(KEY_TYPE)
                if interface != INTERFACE_DIO or device_type != LIMIT_SWITCH_DEVICE_TYPE:
                    result.errors.append(
                        ValidationIssue(
                            MESSAGE_LIMIT_SWITCH_TYPE_INVALID, test.name, FIELD_LIMIT_SWITCH
                        )
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
        if isinstance(term.limit_switch, dict):
            enabled = term.limit_switch.get(FIELD_LIMIT_SWITCH_ENABLED)
            if enabled is not None and not bool(enabled):
                return False
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
