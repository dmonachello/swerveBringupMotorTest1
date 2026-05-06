from __future__ import annotations

"""
NAME
    compiler.py - Line-oriented compiler for the robot test DSL source format.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re

from .model import (
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
PHASE_MARKERS = {PHASE_INIT, PHASE_MAIN, PHASE_CLOSE}
RE_STRING = re.compile(r'^"([^"\n]+)"$')
RE_REF = re.compile(r'^(?P<device>"[^"\n]+"|[A-Za-z][A-Za-z0-9_\-]*)\.(?P<signal>[A-Za-z][A-Za-z0-9_\-]*)$')
RE_TEST = re.compile(r'^test\s+"([^"\n]+)"\s*$')
RE_DEVICE = re.compile(r'^device\s+"([^"\n]+)"\s*$')
RE_PHASE = re.compile(r'^(init|main|close):\s*$')
RE_UNSAFE_EXIT = re.compile(r'^unsafe-exit\s+(.+?)\s*$')
RE_SET = re.compile(r'^set\s+(.+?)\s*=\s*(.+?)\s*$')
RE_CLEAR = re.compile(r'^clear\s+(.+?)\s*$')
RE_KEYWORD_EXPR = re.compile(r'^(abort|success|until|require)\s+(.+?)\s*$')


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
            literal = _parse_literal(match.group(2))
            target_phase.sets.append(
                RobotTestDslSetStatement(
                    statement_id=f"set_{set_count}",
                    text=line,
                    target=target,
                    literal=literal,
                )
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
                operator=operator,
                literal=literal,
            )
    reference = _parse_reference(stripped, line_number)
    return RobotTestDslCondition(
        condition_id=condition_id,
        kind=kind,
        text=full_text,
        reference=reference,
    )
