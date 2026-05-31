from __future__ import annotations

"""
NAME
    compiler.py - Line-oriented compiler for the robot test DSL source format.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re

from .model import (
    CONDITION_MODE_BARE,
    CONDITION_MODE_BETWEEN,
    CONDITION_MODE_COMPARISON,
    CONDITION_MODE_OUTSIDE,
    RobotTestDslClearStatement,
    RobotTestDslCondition,
    RobotTestDslDeviceRef,
    RobotTestDslEntry,
    RobotTestDslLiteral,
    RobotTestDslNormalized,
    RobotTestDslPhase,
    RobotTestDslReference,
    RobotTestDslSetStatement,
    RobotTestDslStore,
    RobotTestDslUnsafeExit,
)


PHASE_INIT = "init"
PHASE_MAIN = "main"
PHASE_CLOSE = "close"
STMT_TEST = "test"
STMT_DEVICE = "device"
STMT_SET = "set"
STMT_CLEAR = "clear"
STMT_ABORT = "abort"
STMT_SUCCESS = "success"
STMT_UNTIL = "until"
STMT_REQUIRE = "require"
STMT_UNSAFE_EXIT = "unsafe-exit"
OPERATORS = ("==", "!=", "<=", ">=", "<", ">")
KEYWORD_STABLE = "stable"
KEYWORD_BETWEEN = "between"
KEYWORD_OUTSIDE = "outside"
PHASE_MARKERS = {PHASE_INIT, PHASE_MAIN, PHASE_CLOSE}
LITERAL_TYPE_NUMBER = "number"
RE_STRING = re.compile(r'^"([^"\n]+)"$')
RE_REF = re.compile(r'^(?P<device>"[^"\n]+"|[A-Za-z][A-Za-z0-9_\-]*)\.(?P<signal>[A-Za-z][A-Za-z0-9_\-]*)$')
RE_TEST = re.compile(r'^test\s+"([^"\n]+)"\s*$')
RE_DEVICE = re.compile(r'^device\s+"([^"\n]+)"\s*$')
RE_PHASE = re.compile(r'^(init|main|close):\s*$')
RE_UNSAFE_EXIT = re.compile(r'^unsafe-exit\s+(.+?)\s*$')
RE_SET = re.compile(r'^set\s+(.+?)\s*=\s*(.+?)\s*$')
RE_SET_SIGNAL = re.compile(
    r'^(?P<source>"[^"\n]+"|[A-Za-z][A-Za-z0-9_\-]*\.[A-Za-z][A-Za-z0-9_\-]*|"[^"\n]+"'
    r'\.[A-Za-z][A-Za-z0-9_\-]*)(?:\s+deadband\s+(?P<deadband>.+?))?\s+scaled\s+(?P<scale>.+?)\s+default\s+(?P<default>.+?)\s*$'
)
RE_CLEAR = re.compile(r'^clear\s+(.+?)\s*$')
RE_KEYWORD_EXPR = re.compile(r'^(abort|success|until|require)\s+(.+?)\s*$')
RE_STABLE_SUFFIX = re.compile(r'^(?P<base>.+?)\s+stable\s+(?P<seconds>.+?)\s*$')
RE_RANGE_EXPR = re.compile(
    r'^(?P<ref>"[^"\n]+"|[A-Za-z][A-Za-z0-9_\-]*\.[A-Za-z][A-Za-z0-9_\-]*|"[^"\n]+"'
    r'\.[A-Za-z][A-Za-z0-9_\-]*)\s+(?P<mode>between|outside)\s+(?P<low>\S+)\s+(?P<high>\S+)\s*$'
)


@dataclass
class CompileError(Exception):
    message: str
    line_number: int


def compile_store_sources(store: RobotTestDslStore) -> RobotTestDslStore:
    """
    NAME
        compile_store_sources - Compile every source entry in a store.
    """

    for entry in store.tests_by_name.values():
        entry.normalized = compile_source(entry.name, entry.source)
    return store


def compile_source(name: str, source: str) -> RobotTestDslNormalized:
    """
    NAME
        compile_source - Compile one DSL source string to normalized form.
    """

    if not isinstance(source, str):
        raise CompileError("source must be a string", 0)
    lines = _logical_lines(source)
    test_name: Optional[str] = None
    devices: List[RobotTestDslDeviceRef] = []
    unsafe_exit: List[RobotTestDslUnsafeExit] = []
    init = RobotTestDslPhase()
    main = RobotTestDslPhase()
    close = RobotTestDslPhase()
    active_phase: Optional[str] = None
    condition_counts: Dict[str, int] = {
        STMT_ABORT: 0,
        STMT_SUCCESS: 0,
        STMT_UNTIL: 0,
        STMT_REQUIRE: 0,
    }
    set_count = 0
    clear_count = 0
    unsafe_exit_count = 0
    for line_number, line in lines:
        match = RE_TEST.match(line)
        if match:
            test_name = match.group(1)
            continue
        match = RE_DEVICE.match(line)
        if match:
            devices.append(RobotTestDslDeviceRef(name=match.group(1)))
            continue
        match = RE_UNSAFE_EXIT.match(line)
        if match:
            unsafe_exit_count += 1
            target = _parse_reference(match.group(1), line_number)
            unsafe_exit.append(
                RobotTestDslUnsafeExit(
                    statement_id=f"unsafe_exit_{unsafe_exit_count}",
                    text=line,
                    target=target,
                )
            )
            continue
        match = RE_PHASE.match(line)
        if match:
            active_phase = match.group(1)
            continue
        if active_phase is None:
            raise CompileError("statement must appear inside a phase", line_number)
        target_phase = _phase_object(active_phase, init, main, close)
        match = RE_SET.match(line)
        if match:
            set_count += 1
            target = _parse_reference(match.group(1), line_number)
            rhs = match.group(2)
            signal_match = RE_SET_SIGNAL.match(rhs)
            if signal_match:
                source = _parse_reference(signal_match.group("source"), line_number)
                deadband = signal_match.group("deadband")
                deadband_literal = _parse_literal(deadband) if deadband is not None else None
                if deadband_literal is not None and deadband_literal.value_type != LITERAL_TYPE_NUMBER:
                    raise CompileError("deadband value must be numeric", line_number)
                scale_literal = _parse_literal(signal_match.group("scale"))
                if scale_literal.value_type != LITERAL_TYPE_NUMBER:
                    raise CompileError("scaled value must be numeric", line_number)
                default_literal = _parse_literal(signal_match.group("default"))
                statement = RobotTestDslSetStatement(
                    statement_id=f"set_{set_count}",
                    text=line,
                    target=target,
                    source=source,
                    deadband=float(deadband_literal.value) if deadband_literal is not None else None,
                    scale=float(scale_literal.value),
                    default_literal=default_literal,
                )
            else:
                literal = _parse_literal(rhs)
                statement = RobotTestDslSetStatement(
                    statement_id=f"set_{set_count}",
                    text=line,
                    target=target,
                    literal=literal,
                )
            target_phase.sets.append(
                statement
            )
            continue
        match = RE_CLEAR.match(line)
        if match:
            clear_count += 1
            target = _parse_reference(match.group(1), line_number)
            target_phase.clears.append(
                RobotTestDslClearStatement(
                    statement_id=f"clear_{clear_count}",
                    text=line,
                    target=target,
                )
            )
            continue
        match = RE_KEYWORD_EXPR.match(line)
        if match:
            keyword = match.group(1)
            condition_counts[keyword] += 1
            condition = _parse_condition(
                keyword,
                f"{keyword}_{condition_counts[keyword]}",
                line,
                match.group(2),
                line_number,
            )
            if keyword == STMT_ABORT:
                target_phase.aborts.append(condition)
            elif keyword == STMT_SUCCESS:
                target_phase.successes.append(condition)
            elif keyword == STMT_UNTIL:
                target_phase.untils.append(condition)
            elif keyword == STMT_REQUIRE:
                target_phase.requires.append(condition)
            continue
        raise CompileError(f"unrecognized statement: {line}", line_number)
    final_name = test_name or name
    return RobotTestDslNormalized(
        name=final_name,
        devices=devices,
        unsafe_exit=unsafe_exit,
        init=init,
        main=main,
        close=close,
    )


def _phase_object(name: str, init: RobotTestDslPhase, main: RobotTestDslPhase, close: RobotTestDslPhase) -> RobotTestDslPhase:
    if name == PHASE_INIT:
        return init
    if name == PHASE_MAIN:
        return main
    return close


def _logical_lines(source: str) -> List[Tuple[int, str]]:
    result: List[Tuple[int, str]] = []
    for index, raw in enumerate(source.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        result.append((index, line))
    return result


def _parse_reference(text: str, line_number: int) -> RobotTestDslReference:
    candidate = text.strip()
    match = RE_REF.match(candidate)
    if not match:
        raise CompileError(f"invalid reference: {text}", line_number)
    device = match.group("device")
    if device.startswith('"') and device.endswith('"'):
        device = device[1:-1]
    signal = match.group("signal")
    return RobotTestDslReference(device=device, signal=signal, text=f"{device}.{signal}")


def _parse_literal(text: str) -> RobotTestDslLiteral:
    raw = text.strip()
    if raw == "true":
        return RobotTestDslLiteral(value=True, value_type="boolean")
    if raw == "false":
        return RobotTestDslLiteral(value=False, value_type="boolean")
    string_match = RE_STRING.match(raw)
    if string_match:
        return RobotTestDslLiteral(value=string_match.group(1), value_type="string")
    try:
        if "." in raw:
            return RobotTestDslLiteral(value=float(raw), value_type="number")
        return RobotTestDslLiteral(value=int(raw), value_type="number")
    except ValueError:
        return RobotTestDslLiteral(value=raw, value_type="string")


def _parse_condition(
    kind: str,
    condition_id: str,
    full_text: str,
    text: str,
    line_number: int,
) -> RobotTestDslCondition:
    stripped = text.strip()
    stable_seconds = _parse_stable_seconds(stripped, line_number)
    if stable_seconds is not None:
        stable_match = RE_STABLE_SUFFIX.match(stripped)
        stripped = stable_match.group("base").strip() if stable_match is not None else stripped
    range_match = RE_RANGE_EXPR.match(stripped)
    if range_match:
        reference = _parse_reference(range_match.group("ref"), line_number)
        low_literal = _parse_literal(range_match.group("low"))
        high_literal = _parse_literal(range_match.group("high"))
        return RobotTestDslCondition(
            condition_id=condition_id,
            kind=kind,
            text=full_text,
            reference=reference,
            mode=range_match.group("mode"),
            low_literal=low_literal,
            high_literal=high_literal,
            stable_seconds=stable_seconds,
        )
    for operator in OPERATORS:
        index = stripped.find(f" {operator} ")
        if index > 0:
            ref_text = stripped[:index].strip()
            literal_text = stripped[index + len(operator) + 2 :].strip()
            reference = _parse_reference(ref_text, line_number)
            literal = _parse_literal(literal_text)
            return RobotTestDslCondition(
                condition_id=condition_id,
                kind=kind,
                text=full_text,
                reference=reference,
                mode=CONDITION_MODE_COMPARISON,
                operator=operator,
                literal=literal,
                stable_seconds=stable_seconds,
            )
    reference = _parse_reference(stripped, line_number)
    return RobotTestDslCondition(
        condition_id=condition_id,
        kind=kind,
        text=full_text,
        reference=reference,
        mode=CONDITION_MODE_BARE,
        stable_seconds=stable_seconds,
    )


def _parse_stable_seconds(text: str, line_number: int) -> Optional[float]:
    stable_match = RE_STABLE_SUFFIX.match(text)
    if stable_match is None:
        return None
    seconds_literal = _parse_literal(stable_match.group("seconds"))
    if seconds_literal.value_type != LITERAL_TYPE_NUMBER:
        raise CompileError("stable seconds must be numeric", line_number)
    return float(seconds_literal.value)
