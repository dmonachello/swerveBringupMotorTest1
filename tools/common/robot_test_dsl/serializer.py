from __future__ import annotations

"""
NAME
    serializer.py - Convert robot DSL store payloads to and from JSON.
"""

import hashlib
from typing import Any, Dict, List

from .model import (
    CONDITION_MODE_BARE,
    CONDITION_MODE_BETWEEN,
    CONDITION_MODE_COMPARISON,
    CONDITION_MODE_OUTSIDE,
    DEFAULT_TEST_SET,
    DSL_SCHEMA_VERSION,
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


KEY_SCHEMA_VERSION = "schemaVersion"
KEY_TESTS_BY_NAME = "testsByName"
KEY_TEST_SETS = "testSets"
KEY_DEFAULT_SET = "defaultSet"
KEY_SOURCE = "source"
KEY_NORMALIZED = "normalized"
KEY_SOURCE_HASH = "sourceHash"
KEY_ENABLED = "enabled"
KEY_MODE = "mode"
KEY_OPERATOR = "operator"
KEY_LITERAL = "literal"
KEY_LOW_LITERAL = "lowLiteral"
KEY_HIGH_LITERAL = "highLiteral"
KEY_STABLE_SECONDS = "stableSeconds"


def source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def store_from_payload(payload: Dict[str, Any]) -> RobotTestDslStore:
    store = RobotTestDslStore()
    if not isinstance(payload, dict):
        return store
    default_set = payload.get(KEY_DEFAULT_SET)
    if isinstance(default_set, str) and default_set:
        store.default_set = default_set
    test_sets = payload.get(KEY_TEST_SETS)
    if isinstance(test_sets, dict):
        for key, names in test_sets.items():
            if isinstance(key, str) and isinstance(names, list):
                store.test_sets[key] = [str(name) for name in names if isinstance(name, str)]
    tests_by_name = payload.get(KEY_TESTS_BY_NAME)
    if isinstance(tests_by_name, dict):
        for name, entry in tests_by_name.items():
            if not isinstance(name, str) or not isinstance(entry, dict):
                continue
            source = entry.get(KEY_SOURCE)
            normalized = entry.get(KEY_NORMALIZED)
            hash_value = entry.get(KEY_SOURCE_HASH)
            store.tests_by_name[name] = RobotTestDslEntry(
                name=name,
                source=source if isinstance(source, str) else "",
                normalized=_normalized_from_payload(name, normalized),
                source_hash=hash_value if isinstance(hash_value, str) else "",
                enabled=bool(entry.get(KEY_ENABLED, True)),
            )
    if not store.test_sets:
        store.test_sets[store.default_set or DEFAULT_TEST_SET] = list(store.tests_by_name.keys())
    return store


def store_to_payload(store: RobotTestDslStore) -> Dict[str, Any]:
    tests_by_name: Dict[str, Any] = {}
    for name, entry in store.tests_by_name.items():
        tests_by_name[name] = {
            KEY_SOURCE: entry.source,
            KEY_SOURCE_HASH: entry.source_hash or source_hash(entry.source),
            KEY_NORMALIZED: _normalized_to_payload(entry.normalized),
            KEY_ENABLED: bool(entry.enabled),
        }
    return {
        KEY_SCHEMA_VERSION: DSL_SCHEMA_VERSION,
        KEY_DEFAULT_SET: store.default_set or DEFAULT_TEST_SET,
        KEY_TEST_SETS: {name: list(names) for name, names in store.test_sets.items()},
        KEY_TESTS_BY_NAME: tests_by_name,
    }


def _normalized_from_payload(name: str, payload: Any) -> RobotTestDslNormalized | None:
    if not isinstance(payload, dict):
        return None
    return RobotTestDslNormalized(
        name=str(payload.get("name") or name),
        devices=[RobotTestDslDeviceRef(name=str(item.get("name"))) for item in payload.get("devices", []) if isinstance(item, dict)],
        unsafe_exit=[_unsafe_exit_from_payload(item) for item in payload.get("unsafeExit", []) if isinstance(item, dict)],
        init=_phase_from_payload(payload.get("init")),
        main=_phase_from_payload(payload.get("main")),
        close=_phase_from_payload(payload.get("close")),
    )


def _normalized_to_payload(normalized: RobotTestDslNormalized | None) -> Dict[str, Any]:
    if normalized is None:
        return {}
    return {
        "name": normalized.name,
        "devices": [{"name": item.name} for item in normalized.devices],
        "unsafeExit": [_unsafe_exit_to_payload(item) for item in normalized.unsafe_exit],
        "init": _phase_to_payload(normalized.init),
        "main": _phase_to_payload(normalized.main),
        "close": _phase_to_payload(normalized.close),
    }


def _phase_from_payload(payload: Any) -> RobotTestDslPhase:
    if not isinstance(payload, dict):
        return RobotTestDslPhase()
    return RobotTestDslPhase(
        sets=[_set_from_payload(item) for item in payload.get("sets", []) if isinstance(item, dict)],
        clears=[_clear_from_payload(item) for item in payload.get("clears", []) if isinstance(item, dict)],
        aborts=[_condition_from_payload(item) for item in payload.get("aborts", []) if isinstance(item, dict)],
        successes=[_condition_from_payload(item) for item in payload.get("successes", []) if isinstance(item, dict)],
        untils=[_condition_from_payload(item) for item in payload.get("untils", []) if isinstance(item, dict)],
        requires=[_condition_from_payload(item) for item in payload.get("requires", []) if isinstance(item, dict)],
    )


def _phase_to_payload(phase: RobotTestDslPhase) -> Dict[str, Any]:
    return {
        "sets": [_set_to_payload(item) for item in phase.sets],
        "clears": [_clear_to_payload(item) for item in phase.clears],
        "aborts": [_condition_to_payload(item) for item in phase.aborts],
        "successes": [_condition_to_payload(item) for item in phase.successes],
        "untils": [_condition_to_payload(item) for item in phase.untils],
        "requires": [_condition_to_payload(item) for item in phase.requires],
    }


def _reference_from_payload(payload: Dict[str, Any]) -> RobotTestDslReference:
    device = str(payload.get("device", ""))
    signal = str(payload.get("signal", ""))
    text = str(payload.get("text") or f"{device}.{signal}")
    return RobotTestDslReference(device=device, signal=signal, text=text)


def _reference_to_payload(reference: RobotTestDslReference) -> Dict[str, Any]:
    return {"device": reference.device, "signal": reference.signal, "text": reference.text}


def _literal_from_payload(payload: Dict[str, Any]) -> RobotTestDslLiteral:
    return RobotTestDslLiteral(value=payload.get("value"), value_type=str(payload.get("valueType", "")))


def _literal_to_payload(literal: RobotTestDslLiteral) -> Dict[str, Any]:
    return {"value": literal.value, "valueType": literal.value_type}


def _condition_from_payload(payload: Dict[str, Any]) -> RobotTestDslCondition:
    literal = payload.get(KEY_LITERAL)
    low_literal = payload.get(KEY_LOW_LITERAL)
    high_literal = payload.get(KEY_HIGH_LITERAL)
    stable_seconds = payload.get(KEY_STABLE_SECONDS)
    operator = str(payload.get(KEY_OPERATOR)) if payload.get(KEY_OPERATOR) is not None else None
    mode = _infer_condition_mode(payload, operator)
    return RobotTestDslCondition(
        condition_id=str(payload.get("id", "")),
        kind=str(payload.get("kind", "")),
        text=str(payload.get("text", "")),
        reference=_reference_from_payload(payload.get("reference", {})),
        mode=mode,
        operator=operator,
        literal=_literal_from_payload(literal) if isinstance(literal, dict) else None,
        low_literal=_literal_from_payload(low_literal) if isinstance(low_literal, dict) else None,
        high_literal=_literal_from_payload(high_literal) if isinstance(high_literal, dict) else None,
        stable_seconds=float(stable_seconds) if isinstance(stable_seconds, (int, float)) else None,
    )


def _condition_to_payload(condition: RobotTestDslCondition) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "id": condition.condition_id,
        "kind": condition.kind,
        "text": condition.text,
        "reference": _reference_to_payload(condition.reference),
    }
    if condition.mode:
        data[KEY_MODE] = condition.mode
    if condition.operator is not None:
        data[KEY_OPERATOR] = condition.operator
    if condition.literal is not None:
        data[KEY_LITERAL] = _literal_to_payload(condition.literal)
    if condition.low_literal is not None:
        data[KEY_LOW_LITERAL] = _literal_to_payload(condition.low_literal)
    if condition.high_literal is not None:
        data[KEY_HIGH_LITERAL] = _literal_to_payload(condition.high_literal)
    if condition.stable_seconds is not None:
        data[KEY_STABLE_SECONDS] = condition.stable_seconds
    return data


def _infer_condition_mode(payload: Dict[str, Any], operator: str | None) -> str:
    explicit_mode = payload.get(KEY_MODE)
    if isinstance(explicit_mode, str) and explicit_mode:
        return explicit_mode
    if operator is not None:
        return CONDITION_MODE_COMPARISON
    if isinstance(payload.get(KEY_LOW_LITERAL), dict) or isinstance(payload.get(KEY_HIGH_LITERAL), dict):
        return str(payload.get(KEY_MODE, CONDITION_MODE_BETWEEN))
    return CONDITION_MODE_BARE


def _set_from_payload(payload: Dict[str, Any]) -> RobotTestDslSetStatement:
    literal = payload.get("literal")
    source = payload.get("source")
    deadband = payload.get("deadband")
    default_literal = payload.get("defaultLiteral")
    scale = payload.get("scale")
    return RobotTestDslSetStatement(
        statement_id=str(payload.get("id", "")),
        text=str(payload.get("text", "")),
        target=_reference_from_payload(payload.get("target", {})),
        literal=_literal_from_payload(literal) if isinstance(literal, dict) else None,
        source=_reference_from_payload(source) if isinstance(source, dict) else None,
        deadband=float(deadband) if isinstance(deadband, (int, float)) else None,
        scale=float(scale) if isinstance(scale, (int, float)) else None,
        default_literal=_literal_from_payload(default_literal) if isinstance(default_literal, dict) else None,
    )


def _set_to_payload(statement: RobotTestDslSetStatement) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "id": statement.statement_id,
        "text": statement.text,
        "target": _reference_to_payload(statement.target),
    }
    if statement.literal is not None:
        data["literal"] = _literal_to_payload(statement.literal)
    if statement.source is not None:
        data["source"] = _reference_to_payload(statement.source)
    if statement.deadband is not None:
        data["deadband"] = statement.deadband
    if statement.scale is not None:
        data["scale"] = statement.scale
    if statement.default_literal is not None:
        data["defaultLiteral"] = _literal_to_payload(statement.default_literal)
    return data


def _clear_from_payload(payload: Dict[str, Any]) -> RobotTestDslClearStatement:
    return RobotTestDslClearStatement(
        statement_id=str(payload.get("id", "")),
        text=str(payload.get("text", "")),
        target=_reference_from_payload(payload.get("target", {})),
    )


def _clear_to_payload(statement: RobotTestDslClearStatement) -> Dict[str, Any]:
    return {"id": statement.statement_id, "text": statement.text, "target": _reference_to_payload(statement.target)}


def _unsafe_exit_from_payload(payload: Dict[str, Any]) -> RobotTestDslUnsafeExit:
    return RobotTestDslUnsafeExit(
        statement_id=str(payload.get("id", "")),
        text=str(payload.get("text", "")),
        target=_reference_from_payload(payload.get("target", {})),
    )


def _unsafe_exit_to_payload(statement: RobotTestDslUnsafeExit) -> Dict[str, Any]:
    return {"id": statement.statement_id, "text": statement.text, "target": _reference_to_payload(statement.target)}
