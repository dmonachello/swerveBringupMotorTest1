from __future__ import annotations

"""
NAME
    model.py - In-memory test authoring model.

SYNOPSIS
    from tools.common.test_authoring.model import TestAuthoringModel

DESCRIPTION
    Provides dataclasses for tests, bindings, and termination settings used by
    the Bridge UI and CLI authoring workflows.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


DEFAULT_DEADBAND = 0.12
DEFAULT_DUTY = 0.2
DEFAULT_TEST_SET = "default"
DEFAULT_BRIGHTNESS = 1.0


@dataclass
class TestBindingJoystick:
    """
    NAME
        TestBindingJoystick - Joystick binding parameters.
    """

    deadband: float = DEFAULT_DEADBAND


@dataclass
class TestBindingButton:
    """
    NAME
        TestBindingButton - Button binding parameters.
    """

    duty: float = DEFAULT_DUTY


@dataclass
class TerminationModel:
    """
    NAME
        TerminationModel - Termination settings for a test.
    """

    hold_enabled: bool = False
    hold_on_release: Optional[str] = None
    time_sec: Optional[float] = None
    time_on_timeout: Optional[str] = None
    rotation_limit: Optional[float] = None
    rotation_encoder_key: Optional[str] = None
    rotation_encoder_source: Optional[str] = None
    rotation_encoder_motor_index: Optional[int] = None
    rotation_encoder_counts_per_rev: Optional[float] = None
    limit_switch: Optional[Dict[str, object]] = None


@dataclass
class DeadbandSweepModel:
    """
    NAME
        DeadbandSweepModel - Deadband sweep parameters.
    """

    start_duty: Optional[float] = None
    max_duty: Optional[float] = None
    step_duty: Optional[float] = None
    step_hold_sec: Optional[float] = None
    motion_threshold_rot: Optional[float] = None
    required_samples: Optional[int] = None
    encoder_key: Optional[str] = None
    encoder_source: Optional[str] = None
    encoder_counts_per_rev: Optional[float] = None
    encoder_motor_index: Optional[int] = None


@dataclass
class DeviceActionModel:
    """
    NAME
        DeviceActionModel - Device action parameters for non-motor tests.
    """

    action: Optional[str] = None
    color: Optional[str] = None
    pattern: Optional[str] = None
    brightness: Optional[float] = None
    duration_sec: Optional[float] = None


@dataclass
class TestModel:
    """
    NAME
        TestModel - Single test authoring entry.
    """

    name: str
    test_type: str  # joystick | button | composite | deadbandSweep
    devices: List[str] = field(default_factory=list)
    input_source: Optional[str] = None
    joystick: Optional[TestBindingJoystick] = None
    button: Optional[TestBindingButton] = None
    termination: TerminationModel = field(default_factory=TerminationModel)
    deadband_sweep: Optional[DeadbandSweepModel] = None
    device_action: Optional[DeviceActionModel] = None
    enabled: bool = False


@dataclass
class TestSetModel:
    """
    NAME
        TestSetModel - Named list of tests.
    """

    name: str
    tests: List[TestModel] = field(default_factory=list)


@dataclass
class TestAuthoringModel:
    """
    NAME
        TestAuthoringModel - Root test authoring payload.
    """

    default_test_set: str = DEFAULT_TEST_SET
    test_sets: Dict[str, TestSetModel] = field(default_factory=dict)
