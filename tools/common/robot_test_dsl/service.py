from __future__ import annotations

"""
NAME
    service.py - Shared host-side workflow helpers for the robot test DSL.

DESCRIPTION
    Owns profile-aware DSL store loading, import, validation, cleanup, and
    test-name resolution so CLI and UI surfaces do not need to reimplement
    these workflows or depend on each other's internals.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from tools.common.json_io import read_json
from tools.common.paths import repo_root
from tools.common.profile_constants import KEY_DEVICES, KEY_DSL_TESTS, KEY_DSL_TEST_SET, KEY_LABEL, KEY_PROFILES, KEY_PROFILE_DEVICES

from .compiler import compile_source
from .model import DEFAULT_TEST_SET, RobotTestDslEntry, RobotTestDslStore
from .serializer import source_hash, store_from_payload, store_to_payload
from .validator import ValidationIssue, ValidationResult, validate_entry, validate_store


SIGNALS_PATH = repo_root() / "tools" / "common" / "generated" / "robot_test_dsl_signals.json"
KEY_DEVICE_TYPES = "deviceTypes"
KEY_DEFAULT_SET = "defaultSet"
KEY_TEST_SETS = "testSets"
KEY_TESTS_BY_NAME = "testsByName"
MESSAGE_UNKNOWN_PROFILE = "ERROR: unknown profile: {name}"
MESSAGE_SOURCE_READ_PREFIX = "ERROR: "
EMPTY_DICT: Dict[str, object] = {}
EMPTY_LIST: List[str] = []
ENCODING_UTF8 = "utf-8"


class DslServiceError(Exception):
    """
    NAME
        DslServiceError - Workflow-level DSL service failure.
    """


@dataclass(frozen=True)
class DslImportResult:
    """
    NAME
        DslImportResult - Result of importing one DSL source file.
    """

    entry: RobotTestDslEntry
    set_name: str
    validation: ValidationResult

    def ok(self) -> bool:
        return self.validation.ok()


def store_from_root_payload(root_payload: Dict[str, object]) -> RobotTestDslStore:
    """
    NAME
        store_from_root_payload - Load the DSL store from a root config payload.
    """
    payload = root_payload.get(KEY_DSL_TESTS) if isinstance(root_payload, dict) else EMPTY_DICT
    if not isinstance(payload, dict):
        payload = EMPTY_DICT
    return store_from_payload(payload)


def write_store_to_root_payload(root_payload: Dict[str, object], store: RobotTestDslStore) -> None:
    """
    NAME
        write_store_to_root_payload - Persist the DSL store into a root config payload.
    """
    root_payload[KEY_DSL_TESTS] = store_to_payload(store)


def signal_catalog(signal_catalog_path: Optional[Path] = None) -> Dict[str, Dict[str, object]]:
    """
    NAME
        signal_catalog - Load the generated DSL signal catalog.
    """
    path = signal_catalog_path if signal_catalog_path is not None else SIGNALS_PATH
    payload = read_json(path)
    if not isinstance(payload, dict):
        return {}
    device_types = payload.get(KEY_DEVICE_TYPES)
    if not isinstance(device_types, dict):
        return {}
    return {str(name): value for name, value in device_types.items() if isinstance(value, dict)}


def device_catalog(root_payload: Dict[str, object], profile_name: str) -> Dict[str, Dict[str, object]]:
    """
    NAME
        device_catalog - Build the profile-scoped DSL device catalog from a root config payload.
    """
    result: Dict[str, Dict[str, object]] = {}
    profiles = root_payload.get(KEY_PROFILES) if isinstance(root_payload, dict) else None
    devices = root_payload.get(KEY_DEVICES) if isinstance(root_payload, dict) else None
    if not isinstance(profiles, dict) or not isinstance(devices, list):
        return result
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        return result
    selected = profile.get(KEY_PROFILE_DEVICES, EMPTY_LIST)
    by_label = {
        str(item.get(KEY_LABEL)): item
        for item in devices
        if isinstance(item, dict) and isinstance(item.get(KEY_LABEL), str)
    }
    if isinstance(selected, list):
        for label in selected:
            if isinstance(label, str) and label in by_label:
                result[label] = by_label[label]
    return result


def validate_store_for_profile(
    root_payload: Dict[str, object],
    store: RobotTestDslStore,
    profile_name: str,
    signal_catalog_path: Optional[Path] = None,
) -> ValidationResult:
    """
    NAME
        validate_store_for_profile - Validate a DSL store against one active profile.
    """
    profiles = root_payload.get(KEY_PROFILES) if isinstance(root_payload, dict) else None
    if isinstance(profiles, dict) and profile_name not in profiles:
        return ValidationResult(errors=[ValidationIssue(MESSAGE_UNKNOWN_PROFILE.format(name=profile_name))])
    return validate_store(store, device_catalog(root_payload, profile_name), signal_catalog(signal_catalog_path))


def import_test_into_root_payload(
    root_payload: Dict[str, object],
    profile_name: str,
    test_name: str,
    source_path: Path,
    *,
    set_name: Optional[str] = None,
    signal_catalog_path: Optional[Path] = None,
) -> DslImportResult:
    """
    NAME
        import_test_into_root_payload - Import one DSL file into the root config payload.
    """
    store = store_from_root_payload(root_payload)
    effective_set = (set_name or store.default_set or DEFAULT_TEST_SET).strip() or DEFAULT_TEST_SET
    try:
        source = source_path.read_text(encoding=ENCODING_UTF8)
        normalized = compile_source(test_name, source)
    except Exception as exc:
        raise DslServiceError(MESSAGE_SOURCE_READ_PREFIX + str(exc)) from exc
    entry = RobotTestDslEntry(
        name=test_name,
        source=source,
        normalized=normalized,
        source_hash=source_hash(source),
    )
    result = validate_entry(
        test_name,
        entry,
        device_catalog(root_payload, profile_name),
        signal_catalog(signal_catalog_path),
    )
    if result.ok():
        store.tests_by_name[test_name] = entry
        names = list(store.test_sets.get(effective_set, []))
        if test_name not in names:
            names.append(test_name)
        store.test_sets[effective_set] = names
        if not store.default_set:
            store.default_set = effective_set
        _set_profile_test_set(root_payload, profile_name, effective_set)
        write_store_to_root_payload(root_payload, store)
    return DslImportResult(entry=entry, set_name=effective_set, validation=result)


def cleanup_stale_tests_in_store(
    root_payload: Dict[str, object],
    store: RobotTestDslStore,
    profile_name: str,
    signal_catalog_path: Optional[Path] = None,
) -> List[str]:
    """
    NAME
        cleanup_stale_tests_in_store - Remove non-validating DSL tests from a store.
    """
    devices = device_catalog(root_payload, profile_name)
    signals = signal_catalog(signal_catalog_path)
    removed: List[str] = []
    for test_name in sorted(list(store.tests_by_name.keys())):
        entry = store.tests_by_name.get(test_name)
        if not isinstance(entry, RobotTestDslEntry):
            continue
        result = validate_entry(test_name, entry, devices, signals)
        if result.ok():
            continue
        del store.tests_by_name[test_name]
        removed.append(test_name)
        for set_names in store.test_sets.values():
            while test_name in set_names:
                set_names.remove(test_name)
    return removed


def resolve_profile_test_names(root_payload: Dict[str, object], profile_name: str) -> List[str]:
    """
    NAME
        resolve_profile_test_names - Resolve ordered DSL test names for one profile.
    """
    store = store_from_root_payload(root_payload)
    if not store.tests_by_name:
        return []
    profiles = root_payload.get(KEY_PROFILES) if isinstance(root_payload, dict) else None
    profile_entry = profiles.get(profile_name) if isinstance(profiles, dict) else None
    profile_set = ""
    if isinstance(profile_entry, dict):
        profile_set = str(profile_entry.get(KEY_DSL_TEST_SET, "") or "").strip()
    selected_names: List[str]
    if profile_set and profile_set in store.test_sets:
        selected_names = list(store.test_sets.get(profile_set, []))
    elif store.default_set and store.default_set in store.test_sets:
        selected_names = list(store.test_sets.get(store.default_set, []))
    elif store.test_sets:
        first_set = next(iter(store.test_sets.values()))
        selected_names = list(first_set)
    else:
        selected_names = list(store.tests_by_name.keys())
    return _dedupe_preserve_order(selected_names)


def issue_line_excerpt(entry: RobotTestDslEntry, field: str) -> Optional[str]:
    """
    NAME
        issue_line_excerpt - Resolve a DSL validation field to a source excerpt when possible.
    """
    field_text = str(field or "").strip()
    if not field_text or field_text in _validation_meta_fields():
        return None
    for line_number, source_line in enumerate(entry.source.splitlines(), start=1):
        line_text = source_line.strip()
        if not line_text:
            continue
        if line_text == field_text or field_text in line_text:
            return f"line {line_number}: {line_text}"
    return f"field {field_text}"


def issue_detail(
    issue: ValidationIssue,
    store: RobotTestDslStore,
    entries_override: Optional[Dict[str, RobotTestDslEntry]] = None,
) -> str:
    """
    NAME
        issue_detail - Render a detail suffix for one validation issue.
    """
    field = getattr(issue, "field", None)
    if not isinstance(field, str) or not field.strip():
        return ""
    entry: Optional[RobotTestDslEntry] = None
    test_name = getattr(issue, "test_name", None)
    if isinstance(entries_override, dict) and isinstance(test_name, str):
        candidate = entries_override.get(test_name)
        if isinstance(candidate, RobotTestDslEntry):
            entry = candidate
    if entry is None and isinstance(test_name, str):
        candidate = store.tests_by_name.get(test_name)
        if isinstance(candidate, RobotTestDslEntry):
            entry = candidate
    if entry is None:
        if field.strip() in _validation_meta_fields():
            return ""
        return f" (field {field.strip()})"
    excerpt = issue_line_excerpt(entry, field)
    return f" ({excerpt})" if excerpt else ""


def render_validation_text(
    result: ValidationResult,
    store: RobotTestDslStore,
    *,
    json_output: bool = False,
    pretty: bool = False,
    entries_override: Optional[Dict[str, RobotTestDslEntry]] = None,
) -> str:
    """
    NAME
        render_validation_text - Render validation results as text or JSON.
    """
    payload = {
        "errors": [issue.__dict__ for issue in result.errors],
        "warnings": [issue.__dict__ for issue in result.warnings],
    }
    if json_output:
        import json

        indent = 2 if pretty else None
        return json.dumps(payload, indent=indent)
    if not result.errors and not result.warnings:
        return "OK"
    lines: List[str] = []
    for issue in result.errors:
        prefix = issue.test_name or "-"
        lines.append(f"ERROR: {prefix}: {issue.message}{issue_detail(issue, store, entries_override)}")
    for issue in result.warnings:
        prefix = issue.test_name or "-"
        lines.append(f"WARNING: {prefix}: {issue.message}{issue_detail(issue, store, entries_override)}")
    return "\n".join(lines)


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _set_profile_test_set(root_payload: Dict[str, object], profile_name: str, set_name: str) -> None:
    profiles = root_payload.get(KEY_PROFILES) if isinstance(root_payload, dict) else None
    if not isinstance(profiles, dict):
        return
    profile = profiles.get(profile_name)
    if isinstance(profile, dict):
        profile[KEY_DSL_TEST_SET] = set_name


def _validation_meta_fields() -> set[str]:
    return {KEY_DSL_TESTS, KEY_TEST_SETS, KEY_TESTS_BY_NAME, KEY_DEFAULT_SET, "source", "normalized", "sourceHash"}
