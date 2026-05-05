from __future__ import annotations

"""
NAME
    serializer.py - Convert between JSON payloads and authoring models.

SYNOPSIS
    from tools.common.test_authoring.serializer import model_from_payload

DESCRIPTION
    Parses bringup_tests.json payloads into the authoring model and serializes
    the model back to the existing JSON schema without modifying robot-side
    behavior.
"""

from typing import Any, Dict, List, Optional

from .model import (
    BUILTIN_TIMER_NAME,
    DeadbandSweepModel,
    DEVICE_ROLE_OBSERVER,
    DEVICE_ROLE_PRIMARY,
    DeviceActionModel,
    PSEUDO_DEVICE_TYPE_TEST_TIMER,
    TerminationModel,
    TestAuthoringModel,
    TestBindingButton,
    TestBindingJoystick,
    TestCommandModel,
    TestConditionModel,
    TestModel,
    TestPseudoDeviceModel,
    TestSetModel,
)

EMPTY_STRING = ""
KEY_DEFAULT_TEST_SET = "default_test_set"
KEY_TEST_SETS = "test_sets"
KEY_TESTS = "tests"
KEY_NAME = "name"
KEY_TYPE = "type"
KEY_ENABLED = "enabled"
KEY_MOTOR_LABELS = "motorLabels"
KEY_INPUT_SOURCE = "inputSource"
KEY_DEADBAND = "deadband"
KEY_DUTY = "duty"
KEY_ACTION = "action"
KEY_COLOR = "color"
KEY_PATTERN = "pattern"
KEY_BRIGHTNESS = "brightness"
KEY_HOLD = "hold"
KEY_TIME = "time"
KEY_ROTATION = "rotation"
KEY_LIMIT_SWITCH = "limitSwitch"
KEY_TIMEOUT_SEC = "timeoutSec"
KEY_ON_TIMEOUT = "onTimeout"
KEY_DURATION_SEC = "durationSec"
KEY_OBSERVER_DEVICES = "observerDevices"
KEY_PSEUDO_DEVICES = "createdDevices"
KEY_DEVICE_TYPE_DSL = "deviceType"
KEY_COMMANDS = "commands"
KEY_SIGNAL = "signal"
KEY_VALUE = "value"
KEY_UNTIL = "until"
KEY_EXPECT = "expect"
KEY_SUCCESS = "success"
KEY_ABORT = "abort"
KEY_OPERATOR = "operator"
KEY_PASSIVE = "passive"
KEY_MANUAL_STOP = "manualStop"
KEY_LIMIT_ROT = "limitRot"
KEY_ENCODER_KEY = "encoderKey"
KEY_ENCODER_SOURCE = "encoderSource"
KEY_ENCODER_MOTOR_INDEX = "encoderMotorIndex"
KEY_ENCODER_COUNTS_PER_REV = "encoderCountsPerRev"
KEY_ON_RELEASE = "onRelease"
KEY_DEADBAND_SWEEP = "deadbandSweep"
KEY_START_DUTY = "startDuty"
KEY_MAX_DUTY = "maxDuty"
KEY_STEP_DUTY = "stepDuty"
KEY_STEP_HOLD_SEC = "stepHoldSec"
KEY_MOTION_THRESHOLD_ROT = "motionThresholdRot"
KEY_REQUIRED_SAMPLES = "requiredSamples"

TYPE_JOYSTICK = "joystick"
TYPE_BUTTON = "button"
TYPE_COMPOSITE = "composite"
TYPE_DEADBAND_SWEEP = "deadbandSweep"
TYPE_DEVICE_ACTION = "deviceAction"
DEFAULT_TEST_SET = "default"
DEFAULT_DEADBAND = 0.12
DEFAULT_DUTY = 0.2
DEFAULT_ON_RELEASE = "pass"


def model_from_payload(payload: Dict[str, Any]) -> TestAuthoringModel:
    """
    NAME
        model_from_payload - Parse JSON payload into authoring model.

    PARAMETERS
        payload - bringup_tests.json contents.

    RETURNS
        Parsed TestAuthoringModel.
    """

    model = TestAuthoringModel()
    if not isinstance(payload, dict):
        return model
    default_set = payload.get(KEY_DEFAULT_TEST_SET)
    if isinstance(default_set, str) and default_set:
        model.default_test_set = default_set

    test_sets = payload.get(KEY_TEST_SETS)
    if isinstance(test_sets, dict):
        for name, entries in test_sets.items():
            if not isinstance(name, str) or not isinstance(entries, list):
                continue
            model.test_sets[name] = TestSetModel(name=name, tests=_parse_tests(entries))
    else:
        tests = payload.get(KEY_TESTS)
        if isinstance(tests, list):
            model.test_sets[model.default_test_set] = TestSetModel(
                name=model.default_test_set,
                tests=_parse_tests(tests),
            )
    return model


def model_to_payload(model: TestAuthoringModel) -> Dict[str, Any]:
    """
    NAME
        model_to_payload - Serialize authoring model to JSON payload.

    PARAMETERS
        model - TestAuthoringModel instance.

    RETURNS
        Dictionary ready for bringup_tests.json.
    """

    payload: Dict[str, Any] = {
        KEY_DEFAULT_TEST_SET: model.default_test_set or DEFAULT_TEST_SET,
        KEY_TEST_SETS: {},
    }
    for name, test_set in model.test_sets.items():
        payload[KEY_TEST_SETS][name] = [_test_to_entry(test) for test in test_set.tests]
    return payload


def _parse_tests(entries: List[Dict[str, Any]]) -> List[TestModel]:
    """
    NAME
        _parse_tests - Convert JSON entries into TestModel objects.
    """

    tests: List[TestModel] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get(KEY_NAME)
        if not isinstance(name, str) or not name:
            continue
        raw_type = str(entry.get(KEY_TYPE, EMPTY_STRING)).strip().lower()
        test_type = TYPE_COMPOSITE
        if raw_type == TYPE_JOYSTICK:
            test_type = TYPE_JOYSTICK
        elif raw_type == TYPE_DEADBAND_SWEEP:
            test_type = TYPE_DEADBAND_SWEEP
        elif raw_type == TYPE_DEVICE_ACTION.lower():
            test_type = TYPE_DEVICE_ACTION
        test = TestModel(name=name, test_type=test_type)
        test.enabled = bool(entry.get(KEY_ENABLED, False))
        test.devices = list(entry.get(KEY_MOTOR_LABELS, []) or [])
        test.observers = _parse_string_list(entry.get(KEY_OBSERVER_DEVICES))
        test.pseudo_devices = _parse_pseudo_devices(entry.get(KEY_PSEUDO_DEVICES))
        test.commands = _parse_commands(entry.get(KEY_COMMANDS))
        test.until_conditions = _parse_conditions(entry.get(KEY_UNTIL))
        test.expect_conditions = _parse_conditions(entry.get(KEY_EXPECT))
        test.success_conditions = _parse_conditions(entry.get(KEY_SUCCESS))
        test.abort_conditions = _parse_conditions(entry.get(KEY_ABORT))
        test.passive = bool(entry.get(KEY_PASSIVE, False))
        test.manual_stop = bool(entry.get(KEY_MANUAL_STOP, False))
        if test_type == TYPE_JOYSTICK:
            test.joystick = TestBindingJoystick(
                deadband=float(entry.get(KEY_DEADBAND, DEFAULT_DEADBAND)),
            )
        elif test_type == TYPE_DEADBAND_SWEEP:
            test.deadband_sweep = _parse_deadband_sweep(entry)
        elif test_type == TYPE_DEVICE_ACTION:
            action = entry.get(KEY_ACTION)
            color = entry.get(KEY_COLOR)
            pattern = entry.get(KEY_PATTERN)
            brightness = entry.get(KEY_BRIGHTNESS)
            duration = entry.get(KEY_DURATION_SEC)
            test.device_action = DeviceActionModel(
                action=action if isinstance(action, str) else None,
                color=color if isinstance(color, str) else None,
                pattern=pattern if isinstance(pattern, str) else None,
                brightness=float(brightness) if isinstance(brightness, (int, float)) else None,
                duration_sec=float(duration) if isinstance(duration, (int, float)) else None,
            )
        elif test_type == TYPE_BUTTON:
            test.button = TestBindingButton(duty=float(entry.get(KEY_DUTY, DEFAULT_DUTY)))
            test.termination = _parse_termination(entry)
        test.input_source = entry.get(KEY_INPUT_SOURCE)
        tests.append(test)
    return tests


def _parse_termination(entry: Dict[str, Any]) -> TerminationModel:
    """
    NAME
        _parse_termination - Parse termination fields into TerminationModel.
    """

    term = TerminationModel()
    hold = entry.get(KEY_HOLD)
    if isinstance(hold, dict):
        enabled = hold.get(KEY_ENABLED)
        term.hold_enabled = bool(enabled) if enabled is not None else True
        on_release = hold.get(KEY_ON_RELEASE)
        if isinstance(on_release, str) and on_release:
            term.hold_on_release = on_release
    time = entry.get(KEY_TIME)
    if isinstance(time, dict):
        sec = time.get(KEY_TIMEOUT_SEC)
        if isinstance(sec, (int, float)):
            term.time_sec = float(sec)
        on_timeout = time.get(KEY_ON_TIMEOUT)
        if isinstance(on_timeout, str) and on_timeout:
            term.time_on_timeout = on_timeout
    rotation = entry.get(KEY_ROTATION)
    if isinstance(rotation, dict):
        limit = rotation.get(KEY_LIMIT_ROT)
        if isinstance(limit, (int, float)):
            term.rotation_limit = float(limit)
        key = rotation.get(KEY_ENCODER_KEY)
        if isinstance(key, str) and key:
            term.rotation_encoder_key = key
        source = rotation.get(KEY_ENCODER_SOURCE)
        if isinstance(source, str) and source:
            term.rotation_encoder_source = source
        idx = rotation.get(KEY_ENCODER_MOTOR_INDEX)
        if isinstance(idx, int):
            term.rotation_encoder_motor_index = idx
        cpr = rotation.get(KEY_ENCODER_COUNTS_PER_REV)
        if isinstance(cpr, (int, float)):
            term.rotation_encoder_counts_per_rev = float(cpr)
    limit_switch = entry.get(KEY_LIMIT_SWITCH)
    if isinstance(limit_switch, dict):
        term.limit_switch = dict(limit_switch)
    return term


def _test_to_entry(test: TestModel) -> Dict[str, Any]:
    """
    NAME
        _test_to_entry - Serialize a TestModel to JSON entry.
    """

    entry: Dict[str, Any] = {
        KEY_NAME: test.name,
        KEY_ENABLED: bool(test.enabled),
        KEY_MOTOR_LABELS: list(test.devices),
    }
    if test.observers:
        entry[KEY_OBSERVER_DEVICES] = list(test.observers)
    if test.pseudo_devices:
        entry[KEY_PSEUDO_DEVICES] = _pseudo_devices_entry(test.pseudo_devices)
    if test.commands:
        entry[KEY_COMMANDS] = _commands_entry(test.commands)
    if test.until_conditions:
        entry[KEY_UNTIL] = _conditions_entry(test.until_conditions)
    if test.expect_conditions:
        entry[KEY_EXPECT] = _conditions_entry(test.expect_conditions)
    if test.success_conditions:
        entry[KEY_SUCCESS] = _conditions_entry(test.success_conditions)
    if test.abort_conditions:
        entry[KEY_ABORT] = _conditions_entry(test.abort_conditions)
    if test.passive:
        entry[KEY_PASSIVE] = True
    if test.manual_stop:
        entry[KEY_MANUAL_STOP] = True
    if test.test_type == TYPE_JOYSTICK:
        entry[KEY_TYPE] = TYPE_JOYSTICK
        if test.input_source:
            entry[KEY_INPUT_SOURCE] = test.input_source
        binding = test.joystick or TestBindingJoystick()
        entry[KEY_DEADBAND] = binding.deadband
        return entry
    if test.test_type == TYPE_DEADBAND_SWEEP:
        entry[KEY_TYPE] = TYPE_DEADBAND_SWEEP
        if test.input_source:
            entry[KEY_INPUT_SOURCE] = test.input_source
        sweep = test.deadband_sweep or DeadbandSweepModel()
        entry[KEY_DEADBAND_SWEEP] = _deadband_sweep_entry(sweep)
        return entry
    if test.test_type == TYPE_DEVICE_ACTION:
        entry[KEY_TYPE] = TYPE_DEVICE_ACTION
        device_action = test.device_action or DeviceActionModel()
        if device_action.action:
            entry[KEY_ACTION] = device_action.action
        if device_action.color:
            entry[KEY_COLOR] = device_action.color
        if device_action.pattern:
            entry[KEY_PATTERN] = device_action.pattern
        if device_action.brightness is not None:
            entry[KEY_BRIGHTNESS] = device_action.brightness
        if device_action.duration_sec is not None:
            entry[KEY_DURATION_SEC] = device_action.duration_sec
        return entry

    entry[KEY_TYPE] = TYPE_COMPOSITE
    return entry


def _rotation_entry(term: TerminationModel) -> Dict[str, Any]:
    """
    NAME
        _rotation_entry - Serialize rotation termination fields.
    """

    rotation: Dict[str, Any] = {}
    if term.rotation_limit is not None:
        rotation[KEY_LIMIT_ROT] = term.rotation_limit
    if term.rotation_encoder_key:
        rotation[KEY_ENCODER_KEY] = term.rotation_encoder_key
    if term.rotation_encoder_source:
        rotation[KEY_ENCODER_SOURCE] = term.rotation_encoder_source
    if term.rotation_encoder_motor_index is not None:
        rotation[KEY_ENCODER_MOTOR_INDEX] = term.rotation_encoder_motor_index
    if term.rotation_encoder_counts_per_rev is not None:
        rotation[KEY_ENCODER_COUNTS_PER_REV] = term.rotation_encoder_counts_per_rev
    return rotation


def _time_entry(term: TerminationModel) -> Dict[str, Any]:
    """
    NAME
        _time_entry - Serialize time termination fields.
    """

    time: Dict[str, Any] = {}
    if term.time_sec is not None:
        time[KEY_TIMEOUT_SEC] = term.time_sec
    if term.time_on_timeout:
        time[KEY_ON_TIMEOUT] = term.time_on_timeout
    return time


def _parse_deadband_sweep(entry: Dict[str, Any]) -> DeadbandSweepModel:
    """
    NAME
        _parse_deadband_sweep - Parse deadband sweep fields.
    """

    sweep = DeadbandSweepModel()
    raw = entry.get(KEY_DEADBAND_SWEEP)
    if not isinstance(raw, dict):
        return sweep
    for key, attr in (
        (KEY_START_DUTY, "start_duty"),
        (KEY_MAX_DUTY, "max_duty"),
        (KEY_STEP_DUTY, "step_duty"),
        (KEY_STEP_HOLD_SEC, "step_hold_sec"),
        (KEY_MOTION_THRESHOLD_ROT, "motion_threshold_rot"),
        (KEY_REQUIRED_SAMPLES, "required_samples"),
        (KEY_ENCODER_KEY, "encoder_key"),
        (KEY_ENCODER_SOURCE, "encoder_source"),
        (KEY_ENCODER_COUNTS_PER_REV, "encoder_counts_per_rev"),
        (KEY_ENCODER_MOTOR_INDEX, "encoder_motor_index"),
    ):
        value = raw.get(key)
        if value is None:
            continue
        if attr in ("encoder_key", "encoder_source"):
            if isinstance(value, str) and value:
                setattr(sweep, attr, value)
        elif attr == "required_samples":
            if isinstance(value, int):
                setattr(sweep, attr, value)
        elif attr == "encoder_motor_index":
            if isinstance(value, int):
                setattr(sweep, attr, value)
        elif isinstance(value, (int, float)):
            setattr(sweep, attr, float(value))
    return sweep


def _deadband_sweep_entry(sweep: DeadbandSweepModel) -> Dict[str, Any]:
    """
    NAME
        _deadband_sweep_entry - Serialize deadband sweep fields.
    """

    entry: Dict[str, Any] = {}
    if sweep.start_duty is not None:
        entry[KEY_START_DUTY] = sweep.start_duty
    if sweep.max_duty is not None:
        entry[KEY_MAX_DUTY] = sweep.max_duty
    if sweep.step_duty is not None:
        entry[KEY_STEP_DUTY] = sweep.step_duty
    if sweep.step_hold_sec is not None:
        entry[KEY_STEP_HOLD_SEC] = sweep.step_hold_sec
    if sweep.motion_threshold_rot is not None:
        entry[KEY_MOTION_THRESHOLD_ROT] = sweep.motion_threshold_rot
    if sweep.required_samples is not None:
        entry[KEY_REQUIRED_SAMPLES] = sweep.required_samples
    if sweep.encoder_key:
        entry[KEY_ENCODER_KEY] = sweep.encoder_key
    if sweep.encoder_source:
        entry[KEY_ENCODER_SOURCE] = sweep.encoder_source
    if sweep.encoder_counts_per_rev is not None:
        entry[KEY_ENCODER_COUNTS_PER_REV] = sweep.encoder_counts_per_rev
    if sweep.encoder_motor_index is not None:
        entry[KEY_ENCODER_MOTOR_INDEX] = sweep.encoder_motor_index
    return entry


def _parse_string_list(raw: Any) -> List[str]:
    """
    NAME
        _parse_string_list - Parse a list of non-empty strings.
    """

    if not isinstance(raw, list):
        return []
    values: List[str] = []
    for entry in raw:
        if isinstance(entry, str) and entry.strip():
            values.append(entry.strip())
    return values


def _parse_pseudo_devices(raw: Any) -> List[TestPseudoDeviceModel]:
    """
    NAME
        _parse_pseudo_devices - Parse created pseudo-device entries.
    """

    if not isinstance(raw, list):
        return []
    devices: List[TestPseudoDeviceModel] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get(KEY_NAME)
        device_type = entry.get(KEY_DEVICE_TYPE_DSL)
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(device_type, str) or not device_type.strip():
            continue
        devices.append(
            TestPseudoDeviceModel(
                name=name.strip(),
                device_type=device_type.strip(),
            )
        )
    return devices


def _parse_commands(raw: Any) -> List[TestCommandModel]:
    """
    NAME
        _parse_commands - Parse DSL command assignments.
    """

    if not isinstance(raw, list):
        return []
    commands: List[TestCommandModel] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        signal = entry.get(KEY_SIGNAL)
        if not isinstance(signal, str) or not signal.strip():
            continue
        if KEY_VALUE not in entry:
            continue
        commands.append(TestCommandModel(signal=signal.strip(), value=entry.get(KEY_VALUE)))
    return commands


def _parse_conditions(raw: Any) -> List[TestConditionModel]:
    """
    NAME
        _parse_conditions - Parse DSL condition lists.
    """

    if not isinstance(raw, list):
        return []
    conditions: List[TestConditionModel] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        signal = entry.get(KEY_SIGNAL)
        operator = entry.get(KEY_OPERATOR)
        if not isinstance(signal, str) or not signal.strip():
            continue
        if not isinstance(operator, str) or not operator.strip():
            continue
        if KEY_VALUE not in entry:
            continue
        conditions.append(
            TestConditionModel(
                signal=signal.strip(),
                operator=operator.strip(),
                value=entry.get(KEY_VALUE),
            )
        )
    return conditions


def _pseudo_devices_entry(devices: List[TestPseudoDeviceModel]) -> List[Dict[str, Any]]:
    """
    NAME
        _pseudo_devices_entry - Serialize created pseudo-devices.
    """

    entries: List[Dict[str, Any]] = []
    for device in devices:
        entries.append(
            {
                KEY_NAME: device.name,
                KEY_DEVICE_TYPE_DSL: device.device_type,
            }
        )
    return entries


def _commands_entry(commands: List[TestCommandModel]) -> List[Dict[str, Any]]:
    """
    NAME
        _commands_entry - Serialize DSL commands.
    """

    entries: List[Dict[str, Any]] = []
    for command in commands:
        entries.append(
            {
                KEY_SIGNAL: command.signal,
                KEY_VALUE: command.value,
            }
        )
    return entries


def _conditions_entry(conditions: List[TestConditionModel]) -> List[Dict[str, Any]]:
    """
    NAME
        _conditions_entry - Serialize DSL conditions.
    """

    entries: List[Dict[str, Any]] = []
    for condition in conditions:
        entries.append(
            {
                KEY_SIGNAL: condition.signal,
                KEY_OPERATOR: condition.operator,
                KEY_VALUE: condition.value,
            }
        )
    return entries

