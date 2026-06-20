from __future__ import annotations

"""
NAME
    model.py - In-memory model for the robot diagnostic test DSL.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union


DSL_SCHEMA_VERSION = 1
DEFAULT_TEST_SET = "default"
BUILTIN_TIMER_NAME = "timer"

DslScalar = Union[bool, float, int, str]
CONDITION_MODE_COMPARISON = "comparison"
CONDITION_MODE_BARE = "bare"
CONDITION_MODE_BETWEEN = "between"
CONDITION_MODE_OUTSIDE = "outside"


@dataclass
class RobotTestDslReference:
    device: str
    signal: str
    text: str


@dataclass
class RobotTestDslLiteral:
    value: DslScalar
    value_type: str


@dataclass
class RobotTestDslCondition:
    condition_id: str
    kind: str
    text: str
    reference: RobotTestDslReference
    mode: str = CONDITION_MODE_BARE
    operator: Optional[str] = None
    literal: Optional[RobotTestDslLiteral] = None
    low_literal: Optional[RobotTestDslLiteral] = None
    high_literal: Optional[RobotTestDslLiteral] = None
    stable_seconds: Optional[float] = None


@dataclass
class RobotTestDslSetStatement:
    statement_id: str
    text: str
    target: RobotTestDslReference
    literal: Optional[RobotTestDslLiteral] = None
    source: Optional[RobotTestDslReference] = None
    deadband: Optional[float] = None
    scale: Optional[float] = None
    default_literal: Optional[RobotTestDslLiteral] = None


@dataclass
class RobotTestDslClearStatement:
    statement_id: str
    text: str
    target: RobotTestDslReference


@dataclass
class RobotTestDslUnsafeExit:
    statement_id: str
    text: str
    target: RobotTestDslReference


@dataclass
class RobotTestDslPhase:
    sets: List[RobotTestDslSetStatement] = field(default_factory=list)
    clears: List[RobotTestDslClearStatement] = field(default_factory=list)
    aborts: List[RobotTestDslCondition] = field(default_factory=list)
    successes: List[RobotTestDslCondition] = field(default_factory=list)
    untils: List[RobotTestDslCondition] = field(default_factory=list)
    requires: List[RobotTestDslCondition] = field(default_factory=list)


@dataclass
class RobotTestDslDeviceRef:
    name: str


@dataclass
class RobotTestDslNormalized:
    name: str
    devices: List[RobotTestDslDeviceRef] = field(default_factory=list)
    unsafe_exit: List[RobotTestDslUnsafeExit] = field(default_factory=list)
    init: RobotTestDslPhase = field(default_factory=RobotTestDslPhase)
    main: RobotTestDslPhase = field(default_factory=RobotTestDslPhase)
    close: RobotTestDslPhase = field(default_factory=RobotTestDslPhase)


@dataclass
class RobotTestDslEntry:
    name: str
    source: str
    normalized: Optional[RobotTestDslNormalized] = None
    source_hash: str = ""
    runnable: bool = True


@dataclass
class RobotTestDslStore:
    tests_by_name: Dict[str, RobotTestDslEntry] = field(default_factory=dict)
    test_sets: Dict[str, List[str]] = field(default_factory=dict)
    default_set: str = DEFAULT_TEST_SET
