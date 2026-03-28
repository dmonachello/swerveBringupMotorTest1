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
    DeadbandSweepModel,
    TerminationModel,
    TestAuthoringModel,
    TestBindingButton,
    TestBindingJoystick,
    TestModel,
    TestSetModel,
)

EMPTY_STRING = ""
KEY_DEFAULT_TEST_SET = "default_test_set"
KEY_TEST_SETS = "test_sets"
KEY_TESTS = "tests"
KEY_NAME = "name"
KEY_TYPE = "type"
KEY_ENABLED = "enabled"
KEY_MOTOR_KEYS = "motorKeys"
KEY_INPUT_SOURCE = "inputSource"
KEY_DEADBAND = "deadband"
KEY_DUTY = "duty"
KEY_HOLD = "hold"
KEY_TIME = "time"
KEY_ROTATION = "rotation"
KEY_LIMIT_SWITCH = "limitSwitch"
KEY_TIMEOUT_SEC = "timeoutSec"
KEY_ON_TIMEOUT = "onTimeout"
KEY_DURATION_SEC = "durationSec"
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
        test = TestModel(name=name, test_type=test_type)
        test.enabled = bool(entry.get(KEY_ENABLED, False))
        test.devices = list(entry.get(KEY_MOTOR_KEYS, []) or [])
        if test_type == TYPE_JOYSTICK:
            test.joystick = TestBindingJoystick(
                deadband=float(entry.get(KEY_DEADBAND, DEFAULT_DEADBAND)),
            )
        elif test_type == TYPE_DEADBAND_SWEEP:
            test.deadband_sweep = _parse_deadband_sweep(entry)
        else:
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
        KEY_MOTOR_KEYS: list(test.devices),
    }
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

    entry[KEY_TYPE] = TYPE_COMPOSITE
    if test.input_source:
        entry[KEY_INPUT_SOURCE] = test.input_source
    binding = test.button or TestBindingButton()
    entry[KEY_DUTY] = binding.duty
    term = test.termination or TerminationModel()
    if term.rotation_limit is not None or term.rotation_encoder_key:
        entry[KEY_ROTATION] = _rotation_entry(term)
    if term.time_sec is not None:
        entry[KEY_TIME] = _time_entry(term)
    if term.hold_enabled:
        hold = {KEY_ENABLED: True}
        hold[KEY_ON_RELEASE] = term.hold_on_release or DEFAULT_ON_RELEASE
        entry[KEY_HOLD] = hold
    if term.limit_switch:
        entry[KEY_LIMIT_SWITCH] = dict(term.limit_switch)
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
