from __future__ import annotations

"""
NAME
    validator.py - Validation helpers for the robot diagnostic test DSL store.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import json

from .compiler import CompileError, compile_source
from .model import (
    BUILTIN_TIMER_NAME,
    RobotTestDslEntry,
    RobotTestDslNormalized,
    RobotTestDslStore,
)
from .serializer import source_hash


KEY_TYPE = "type"
TYPE_MOTOR = "motor"
TYPE_LIMIT_SWITCH = "limitSwitch"
TYPE_ENCODER_EXTERNAL = "encoderExternal"
TYPE_XBOX_CONTROLLER = "xboxController"
SIGNAL_OUTPUT = "output"
SIGNAL_CATEGORY_BOOLEAN = "boolean"
SIGNAL_CATEGORY_NUMBER = "number"
VALUE_RANGE_BY_SIGNAL = {
    (TYPE_MOTOR, SIGNAL_OUTPUT): (-1.0, 1.0),
}


@dataclass
class ValidationIssue:
    message: str
    test_name: Optional[str] = None
    field: Optional[str] = None


@dataclass
class ValidationResult:
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)

    def ok(self) -> bool:
        return not self.errors


def validate_store(
    store: RobotTestDslStore,
    device_catalog: Dict[str, Dict[str, object]],
    signal_catalog: Dict[str, Dict[str, object]],
) -> ValidationResult:
    result = ValidationResult()
    seen_names: Set[str] = set()
    for name, entry in store.tests_by_name.items():
        if name in seen_names:
            result.errors.append(ValidationIssue("Duplicate test name.", test_name=name))
            continue
        seen_names.add(name)
        _validate_entry(result, name, entry, device_catalog, signal_catalog)
    for set_name, test_names in store.test_sets.items():
        for test_name in test_names:
            if test_name not in store.tests_by_name:
                result.errors.append(
                    ValidationIssue(
                        f"Unknown test referenced by set '{set_name}': {test_name}",
                        test_name=test_name,
                        field="testSets",
                    )
                )
    return result


def _validate_entry(
    result: ValidationResult,
    name: str,
    entry: RobotTestDslEntry,
    device_catalog: Dict[str, Dict[str, object]],
    signal_catalog: Dict[str, Dict[str, object]],
) -> None:
    if not entry.source.strip():
        result.errors.append(ValidationIssue("DSL source is required.", test_name=name, field="source"))
        return
    try:
        regenerated = compile_source(name, entry.source)
    except CompileError as ex:
        result.errors.append(
            ValidationIssue(f"Compile error at line {ex.line_number}: {ex.message}", test_name=name, field="source")
        )
        return
    if entry.normalized is None:
        result.errors.append(ValidationIssue("Normalized test payload missing.", test_name=name, field="normalized"))
        return
    if _normalized_json(regenerated) != _normalized_json(entry.normalized):
        result.errors.append(ValidationIssue("Source and normalized payload are out of sync.", test_name=name))
    expected_hash = source_hash(entry.source)
    if entry.source_hash and entry.source_hash != expected_hash:
        result.errors.append(ValidationIssue("Source hash mismatch.", test_name=name, field="sourceHash"))
    _validate_normalized(result, entry.normalized, device_catalog, signal_catalog)


def _validate_normalized(
    result: ValidationResult,
    normalized: RobotTestDslNormalized,
    device_catalog: Dict[str, Dict[str, object]],
    signal_catalog: Dict[str, Dict[str, object]],
) -> None:
    declared_devices = {item.name for item in normalized.devices}
    if BUILTIN_TIMER_NAME in declared_devices:
        result.errors.append(
            ValidationIssue("Declaring reserved built-in device `timer`.", test_name=normalized.name, field="devices")
        )
    for device in declared_devices:
        if device not in device_catalog:
            result.errors.append(ValidationIssue("Undeclared or unknown device.", test_name=normalized.name, field=device))
    for signal in normalized.unsafe_exit:
        _validate_reference_declared(result, normalized.name, signal.target.device, declared_devices, signal.text)
        _validate_signal_writeable(result, normalized.name, signal.target.device, signal.target.signal, device_catalog, signal_catalog, "unsafe-exit")
    _validate_phase(result, normalized.name, "init", normalized.init, declared_devices, device_catalog, signal_catalog)
    _validate_phase(result, normalized.name, "main", normalized.main, declared_devices, device_catalog, signal_catalog)
    _validate_phase(result, normalized.name, "close", normalized.close, declared_devices, device_catalog, signal_catalog)
    if not normalized.main.aborts and not normalized.main.successes and not normalized.main.untils:
        result.warnings.append(ValidationIssue("no until or success -> runs forever", test_name=normalized.name))
    if not normalized.main.untils and normalized.main.aborts and not normalized.main.successes:
        result.warnings.append(ValidationIssue("only abort termination -> may never stop", test_name=normalized.name))
    if normalized.main.untils and not normalized.main.requires:
        result.warnings.append(ValidationIssue("until without require -> may pass without proof", test_name=normalized.name))


def _validate_phase(
    result: ValidationResult,
    test_name: str,
    phase_name: str,
    phase: RobotTestDslNormalized.__annotations__.get("init", None) or object,
    declared_devices: Set[str],
    device_catalog: Dict[str, Dict[str, object]],
    signal_catalog: Dict[str, Dict[str, object]],
) -> None:
    for statement in phase.sets:
        _validate_reference_declared(result, test_name, statement.target.device, declared_devices, statement.text)
        _validate_set_statement(result, test_name, statement, declared_devices, device_catalog, signal_catalog, phase_name)
    for statement in phase.clears:
        _validate_reference_declared(result, test_name, statement.target.device, declared_devices, statement.text)
        signal_meta = _signal_meta(statement.target.device, statement.target.signal, device_catalog, signal_catalog)
        if signal_meta is None or not signal_meta.get("clearable"):
            result.errors.append(ValidationIssue("invalid clear target", test_name=test_name, field=statement.text))
    if phase_name != "main":
        for bucket in (phase.aborts, phase.successes, phase.untils, phase.requires):
            for condition in bucket:
                result.errors.append(ValidationIssue(f"{condition.kind} outside main", test_name=test_name, field=condition.text))
    for bucket in (phase.aborts, phase.successes, phase.untils, phase.requires):
        for condition in bucket:
            _validate_reference_declared(result, test_name, condition.reference.device, declared_devices, condition.text)
            signal_meta = _signal_meta(condition.reference.device, condition.reference.signal, device_catalog, signal_catalog)
            if signal_meta is None:
                result.errors.append(ValidationIssue("unknown signal", test_name=test_name, field=condition.text))
                continue
            if condition.operator is None and signal_meta.get("valueType") != SIGNAL_CATEGORY_BOOLEAN:
                result.errors.append(ValidationIssue("bare non-boolean condition reference", test_name=test_name, field=condition.text))


def _validate_set_statement(
    result: ValidationResult,
    test_name: str,
    statement,
    declared_devices: Set[str],
    device_catalog: Dict[str, Dict[str, object]],
    signal_catalog: Dict[str, Dict[str, object]],
    phase_name: str,
) -> None:
    target_meta = _signal_meta(statement.target.device, statement.target.signal, device_catalog, signal_catalog)
    if target_meta is None:
        result.errors.append(ValidationIssue("unknown signal", test_name=test_name, field=f"{statement.target.device}.{statement.target.signal}"))
        return
    if not target_meta.get("writable"):
        result.errors.append(ValidationIssue("set to read-only signal", test_name=test_name, field=f"{statement.target.device}.{statement.target.signal}"))
        return
    if target_meta.get("writable") and target_meta.get("safeValue") is None and not target_meta.get("safeProvider"):
        result.errors.append(ValidationIssue("writable signal has no safe value", test_name=test_name, field=f"{statement.target.device}.{statement.target.signal}"))
    if target_meta.get("valueType") != SIGNAL_CATEGORY_NUMBER:
        result.errors.append(ValidationIssue("signal set target must be numeric", test_name=test_name, field=statement.text))
    if statement.source is None:
        if statement.literal is None:
            result.errors.append(ValidationIssue("set statement missing literal", test_name=test_name, field=statement.text))
        if statement.deadband is not None:
            result.errors.append(ValidationIssue("deadband not allowed on literal set", test_name=test_name, field=statement.text))
        return
    _validate_reference_declared(result, test_name, statement.source.device, declared_devices, statement.text)
    source_meta = _signal_meta(statement.source.device, statement.source.signal, device_catalog, signal_catalog)
    if source_meta is None:
        result.errors.append(ValidationIssue("unknown signal", test_name=test_name, field=f"{statement.source.device}.{statement.source.signal}"))
        return
    source_device = device_catalog.get(statement.source.device)
    if isinstance(source_device, dict) and str(source_device.get(KEY_TYPE, "")) == TYPE_MOTOR:
        result.errors.append(ValidationIssue("motor-device source signals are not allowed", test_name=test_name, field=statement.text))
    if not source_meta.get("readable"):
        result.errors.append(ValidationIssue("signal set source must be readable", test_name=test_name, field=statement.text))
    if source_meta.get("valueType") != SIGNAL_CATEGORY_NUMBER:
        result.errors.append(ValidationIssue("signal set source must be numeric", test_name=test_name, field=statement.text))
    if statement.deadband is not None and (statement.deadband < 0.0 or statement.deadband > 1.0):
        result.errors.append(ValidationIssue("signal set deadband out of range", test_name=test_name, field=statement.text))
    if statement.scale is None:
        result.errors.append(ValidationIssue("signal set requires scale", test_name=test_name, field=statement.text))
    elif abs(statement.scale) > 1.0:
        result.errors.append(ValidationIssue("signal set scale out of range", test_name=test_name, field=statement.text))
    if statement.default_literal is None:
        result.errors.append(ValidationIssue("signal set requires default literal", test_name=test_name, field=statement.text))
    elif statement.default_literal.value_type != SIGNAL_CATEGORY_NUMBER:
        result.errors.append(ValidationIssue("signal set default must be numeric", test_name=test_name, field=statement.text))
    else:
        _validate_numeric_target_range(
            result,
            test_name,
            statement.target.device,
            statement.target.signal,
            float(statement.default_literal.value),
            statement.text,
            device_catalog,
        )


def _validate_reference_declared(
    result: ValidationResult,
    test_name: str,
    device_name: str,
    declared_devices: Set[str],
    field: str,
) -> None:
    if device_name == BUILTIN_TIMER_NAME:
        return
    if device_name not in declared_devices:
        result.errors.append(ValidationIssue("undeclared device reference", test_name=test_name, field=field))


def _validate_signal_writeable(
    result: ValidationResult,
    test_name: str,
    device_name: str,
    signal_name: str,
    device_catalog: Dict[str, Dict[str, object]],
    signal_catalog: Dict[str, Dict[str, object]],
    field: str,
) -> None:
    signal_meta = _signal_meta(device_name, signal_name, device_catalog, signal_catalog)
    if signal_meta is None:
        result.errors.append(ValidationIssue("unknown signal", test_name=test_name, field=f"{device_name}.{signal_name}"))
        return
    if not signal_meta.get("writable"):
        result.errors.append(ValidationIssue("set to read-only signal", test_name=test_name, field=f"{device_name}.{signal_name}"))
    if signal_meta.get("writable") and signal_meta.get("safeValue") is None and not signal_meta.get("safeProvider"):
        result.errors.append(ValidationIssue("writable signal has no safe value", test_name=test_name, field=f"{device_name}.{signal_name}"))


def _validate_numeric_target_range(
    result: ValidationResult,
    test_name: str,
    device_name: str,
    signal_name: str,
    value: float,
    field: str,
    device_catalog: Dict[str, Dict[str, object]],
) -> None:
    device = device_catalog.get(device_name)
    if not isinstance(device, dict):
        return
    device_type = str(device.get(KEY_TYPE, ""))
    bounds = VALUE_RANGE_BY_SIGNAL.get((device_type, signal_name))
    if bounds is None:
        return
    lower, upper = bounds
    if value < lower or value > upper:
        result.errors.append(ValidationIssue("signal set default out of range", test_name=test_name, field=field))


def _signal_meta(
    device_name: str,
    signal_name: str,
    device_catalog: Dict[str, Dict[str, object]],
    signal_catalog: Dict[str, Dict[str, object]],
) -> Dict[str, object] | None:
    if device_name == BUILTIN_TIMER_NAME:
        return signal_catalog.get("TestTimer", {}).get(signal_name) if isinstance(signal_catalog.get("TestTimer"), dict) else None
    device = device_catalog.get(device_name)
    if not isinstance(device, dict):
        return None
    device_type = str(device.get(KEY_TYPE, ""))
    signals = signal_catalog.get(device_type)
    if not isinstance(signals, dict):
        return None
    meta = signals.get(signal_name)
    return meta if isinstance(meta, dict) else None


def _normalized_json(normalized: RobotTestDslNormalized) -> str:
    from .serializer import _normalized_to_payload  # type: ignore

    return json.dumps(_normalized_to_payload(normalized), sort_keys=True, separators=(",", ":"))
