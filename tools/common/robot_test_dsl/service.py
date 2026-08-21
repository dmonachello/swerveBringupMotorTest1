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
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Optional

from tools.common.json_io import read_json
from tools.common.paths import dsl_global_library_dir, dsl_test_archive_dir, repo_root
from tools.common.profile_constants import (
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_DSL_TESTS,
    KEY_DSL_TEST_SET,
    KEY_LABEL,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
    KEY_TYPE,
)

from .compiler import CompileError, compile_source, compile_source_best_effort
from .model import DEFAULT_TEST_SET, RobotTestDslEntry, RobotTestDslStore
from .serializer import source_hash, store_from_payload, store_to_payload
from .validator import ValidationIssue, ValidationResult, validate_entry, validate_store


SIGNALS_PATH = repo_root() / "tools" / "common" / "generated" / "robot_test_dsl_signals.json"
KEY_DEVICE_TYPES = "deviceTypes"
KEY_DEVICE_TYPE_ALIASES = "deviceTypeAliases"
KEY_DEFAULT_SET = "defaultSet"
KEY_TEST_SETS = "testSets"
KEY_TESTS_BY_NAME = "testsByName"
MESSAGE_UNKNOWN_PROFILE = "ERROR: unknown profile: {name}"
MESSAGE_UNKNOWN_TEST = "ERROR: unknown DSL test: {name}"
MESSAGE_DUPLICATE_TEST = "ERROR: target DSL test already exists: {name}"
MESSAGE_SOURCE_READ_PREFIX = "ERROR: "
EMPTY_DICT: Dict[str, object] = {}
EMPTY_LIST: List[str] = []
ENCODING_UTF8 = "utf-8"
TEST_DECLARATION_PATTERN = re.compile(r'^(?P<prefix>\s*test\s+\")(?P<name>[^\"]+)(?P<suffix>\".*)$', re.MULTILINE)
PROFILE_TEST_SET_NAME_FORMAT = "{profile}"
EXTERNAL_LIBRARY_SUFFIX = ".dsl"
ARCHIVE_SCOPE_EXTERNAL = "external"
ARCHIVE_SCOPE_CONFIG = "config"
ARCHIVE_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
NEW_TEST_TEMPLATE = (
    'test "{name}"\n'
    "\n"
    "main:\n"
    "    require timer.elapsed >= 0.0\n"
    "    until timer.elapsed >= 1.0\n"
)
DEVICE_TYPE_DSL_MOTOR = "motor"
DEVICE_TYPE_DSL_PDH = "PDH"
DEVICE_TYPE_DSL_PDP = "PDP"
DEVICE_TYPE_DSL_LIMIT_SWITCH = "limitSwitch"
DEVICE_TYPE_DSL_ENCODER_EXTERNAL = "encoderExternal"
DEVICE_TYPE_DSL_IMU = "imu"
DEVICE_TYPE_DSL_ROBOT_CONTROLLER = "robotController"
DEVICE_TYPE_DSL_XBOX_CONTROLLER = "xboxController"
MANUFACTURER_CTRE = 4
MANUFACTURER_REV = 5
DEVICE_TYPE_GYRO = 4
DEVICE_TYPE_ENCODER = 7
DEVICE_TYPE_POWER = 8
MANUFACTURER_NI = 1
DEVICE_TYPE_ROBOT_CONTROLLER_NI = 1
MODEL_PDP = "PDP"
MODEL_PDH = "PDH"
MODEL_ROBOT_CONTROLLER = "ROBOTCONTROLLER"


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


def device_type_alias_catalog(signal_catalog_path: Optional[Path] = None) -> Dict[str, str]:
    """
    NAME
        device_type_alias_catalog - Load generated DSL device-type aliases from the shared artifact.
    """
    path = signal_catalog_path if signal_catalog_path is not None else SIGNALS_PATH
    payload = read_json(path)
    if not isinstance(payload, dict):
        return {}
    aliases = payload.get(KEY_DEVICE_TYPE_ALIASES)
    if not isinstance(aliases, dict):
        return {}
    result: Dict[str, str] = {}
    for name, canonical in aliases.items():
        alias_name = str(name or "").strip()
        canonical_name = str(canonical or "").strip()
        if not alias_name or not canonical_name:
            continue
        result[alias_name.lower()] = canonical_name
    return result


def resolve_profile_device_dsl_type(
    device_entry: Dict[str, object],
    signal_catalog_path: Optional[Path] = None,
) -> str:
    """
    NAME
        resolve_profile_device_dsl_type - Resolve one profile/config device entry to the shared DSL device type name.
    """
    if not isinstance(device_entry, dict):
        return ""
    explicit_type = str(device_entry.get(KEY_TYPE, "") or "").strip()
    if explicit_type:
        return _canonicalize_profile_device_dsl_type(explicit_type, signal_catalog_path)
    raw_model = str(device_entry.get(KEY_MODEL, "") or "").strip().upper()
    raw_manufacturer = device_entry.get(KEY_MANUFACTURER)
    raw_device_type = device_entry.get(KEY_DEVICE_TYPE)
    try:
        manufacturer = int(raw_manufacturer)
    except Exception:
        manufacturer = None
    try:
        device_type = int(raw_device_type)
    except Exception:
        device_type = None
    if manufacturer == MANUFACTURER_CTRE and device_type == DEVICE_TYPE_ENCODER:
        return DEVICE_TYPE_DSL_ENCODER_EXTERNAL
    if manufacturer == MANUFACTURER_CTRE and device_type == DEVICE_TYPE_GYRO:
        return DEVICE_TYPE_DSL_IMU
    if manufacturer == MANUFACTURER_NI and device_type == DEVICE_TYPE_ROBOT_CONTROLLER_NI:
        return DEVICE_TYPE_DSL_ROBOT_CONTROLLER
    if device_type == DEVICE_TYPE_POWER:
        if manufacturer == MANUFACTURER_CTRE or MODEL_PDP in raw_model:
            return DEVICE_TYPE_DSL_PDP
        if manufacturer == MANUFACTURER_REV or MODEL_PDH in raw_model:
            return DEVICE_TYPE_DSL_PDH
    if MODEL_ROBOT_CONTROLLER in raw_model:
        return DEVICE_TYPE_DSL_ROBOT_CONTROLLER
    return ""


def _canonicalize_profile_device_dsl_type(
    device_type: str,
    signal_catalog_path: Optional[Path] = None,
) -> str:
    """
    NAME
        _canonicalize_profile_device_dsl_type - Normalize one profile/config logical device type to the shared DSL catalog key.
    """
    if not device_type:
        return ""
    normalized = device_type.strip()
    alias_map = device_type_alias_catalog(signal_catalog_path)
    return alias_map.get(normalized.lower(), normalized)


def device_catalog(
    root_payload: Dict[str, object],
    profile_name: str,
    signal_catalog_path: Optional[Path] = None,
) -> Dict[str, Dict[str, object]]:
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
                entry = by_label[label]
                resolved = resolve_profile_device_dsl_type(entry, signal_catalog_path)
                if resolved:
                    copied = dict(entry)
                    copied[KEY_TYPE] = resolved
                    result[label] = copied
                else:
                    result[label] = entry
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
    profile_test_names = resolve_profile_test_names(root_payload, profile_name)
    filtered_store = RobotTestDslStore(
        tests_by_name={
            test_name: entry
            for test_name, entry in store.tests_by_name.items()
            if test_name in profile_test_names
        },
        test_sets={resolve_profile_test_set_name(root_payload, profile_name): list(profile_test_names)},
        default_set=resolve_profile_test_set_name(root_payload, profile_name),
    )
    return validate_store(
        filtered_store,
        device_catalog(root_payload, profile_name, signal_catalog_path),
        signal_catalog(signal_catalog_path),
    )


def resolve_runnable_profile_test_names(
    root_payload: Dict[str, object],
    profile_name: str,
    signal_catalog_path: Optional[Path] = None,
) -> List[str]:
    """
    NAME
        resolve_runnable_profile_test_names - Resolve profile-owned DSL test names that validate cleanly.
    """
    store = store_from_root_payload(root_payload)
    saved_names = resolve_profile_test_names(root_payload, profile_name)
    if not saved_names:
        return []
    devices = device_catalog(root_payload, profile_name, signal_catalog_path)
    signals = signal_catalog(signal_catalog_path)
    runnable_names: List[str] = []
    for test_name in saved_names:
        entry = store.tests_by_name.get(test_name)
        if not isinstance(entry, RobotTestDslEntry):
            continue
        if entry.runnable:
            runnable_names.append(test_name)
            continue
        result = validate_entry(test_name, entry, devices, signals)
        if result.ok():
            runnable_names.append(test_name)
    return runnable_names


def profile_test_runnable_map(
    root_payload: Dict[str, object],
    profile_name: str,
    signal_catalog_path: Optional[Path] = None,
) -> Dict[str, bool]:
    """
    NAME
        profile_test_runnable_map - Return per-test runnable state for one profile.
    """
    store = store_from_root_payload(root_payload)
    saved_names = resolve_profile_test_names(root_payload, profile_name)
    devices = device_catalog(root_payload, profile_name, signal_catalog_path)
    signals = signal_catalog(signal_catalog_path)
    result: Dict[str, bool] = {}
    for test_name in saved_names:
        entry = store.tests_by_name.get(test_name)
        if not isinstance(entry, RobotTestDslEntry):
            result[test_name] = False
            continue
        if entry.runnable:
            result[test_name] = True
            continue
        result[test_name] = validate_entry(test_name, entry, devices, signals).ok()
    return result


def config_library_test_runnable_map(
    root_payload: Dict[str, object],
    profile_name: str,
    signal_catalog_path: Optional[Path] = None,
) -> Dict[str, bool]:
    """
    NAME
        config_library_test_runnable_map - Return per-test runnable state for the config-scoped shared library.
    """
    store = store_from_root_payload(root_payload)
    config_names = resolve_global_library_test_names(root_payload)
    devices = device_catalog(root_payload, profile_name, signal_catalog_path)
    signals = signal_catalog(signal_catalog_path)
    result: Dict[str, bool] = {}
    for test_name in config_names:
        entry = store.tests_by_name.get(test_name)
        if not isinstance(entry, RobotTestDslEntry):
            result[test_name] = False
            continue
        result[test_name] = validate_entry(test_name, entry, devices, signals).ok()
    return result


def external_library_test_runnable_map(
    root_payload: Dict[str, object],
    profile_name: str,
    signal_catalog_path: Optional[Path] = None,
    library_dir: Optional[Path] = None,
) -> Dict[str, bool]:
    """
    NAME
        external_library_test_runnable_map - Return per-test runnable state for the external shared library.
    """
    _require_known_profile(root_payload, profile_name)
    devices = device_catalog(root_payload, profile_name, signal_catalog_path)
    signals = signal_catalog(signal_catalog_path)
    result: Dict[str, bool] = {}
    for test_name in list_external_library_test_names(library_dir):
        try:
            source = read_external_library_test_source(test_name, library_dir)
        except DslServiceError:
            result[test_name] = False
            continue
        entry, validation = _build_entry_from_source_text(
            test_name,
            source,
            root_payload,
            profile_name,
            signal_catalog_path=signal_catalog_path,
        )
        _ = entry
        result[test_name] = validation.ok()
    return result


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
    _require_known_profile(root_payload, profile_name)
    effective_set = _resolve_profile_target_set_name(
        root_payload,
        store,
        profile_name,
        set_name,
    )
    try:
        source = source_path.read_text(encoding=ENCODING_UTF8)
        renamed_source = _rename_test_declaration(source, test_name)
        normalized = compile_source(test_name, renamed_source)
    except CompileError:
        normalized, _compile_errors = compile_source_best_effort(test_name, renamed_source)
    except Exception as exc:
        raise DslServiceError(MESSAGE_SOURCE_READ_PREFIX + str(exc)) from exc
    entry = RobotTestDslEntry(
        name=test_name,
        source=renamed_source,
        normalized=normalized,
        source_hash=source_hash(renamed_source),
        runnable=True,
    )
    result = validate_entry(
        test_name,
        entry,
        device_catalog(root_payload, profile_name, signal_catalog_path),
        signal_catalog(signal_catalog_path),
    )
    entry.runnable = result.ok()
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


def create_blank_test_in_root_payload(
    root_payload: Dict[str, object],
    profile_name: str,
    test_name: str,
    *,
    set_name: Optional[str] = None,
    signal_catalog_path: Optional[Path] = None,
) -> DslImportResult:
    """
    NAME
        create_blank_test_in_root_payload - Create a new minimal profile-owned DSL test.
    """
    store = store_from_root_payload(root_payload)
    _require_known_profile(root_payload, profile_name)
    clean_name = str(test_name or "").strip()
    if clean_name in store.tests_by_name:
        raise DslServiceError(MESSAGE_DUPLICATE_TEST.format(name=clean_name))
    effective_set = _resolve_profile_target_set_name(
        root_payload,
        store,
        profile_name,
        set_name,
    )
    try:
        source = NEW_TEST_TEMPLATE.format(name=clean_name)
        normalized = compile_source(clean_name, source)
    except CompileError:
        normalized, _compile_errors = compile_source_best_effort(clean_name, source)
    except Exception as exc:
        raise DslServiceError(MESSAGE_SOURCE_READ_PREFIX + str(exc)) from exc
    entry = RobotTestDslEntry(
        name=clean_name,
        source=source,
        normalized=normalized,
        source_hash=source_hash(source),
        runnable=True,
    )
    result = validate_entry(
        clean_name,
        entry,
        device_catalog(root_payload, profile_name, signal_catalog_path),
        signal_catalog(signal_catalog_path),
    )
    entry.runnable = result.ok()
    store.tests_by_name[clean_name] = entry
    names = list(store.test_sets.get(effective_set, []))
    if clean_name not in names:
        names.append(clean_name)
    store.test_sets[effective_set] = names
    if not store.default_set:
        store.default_set = effective_set
    _set_profile_test_set(root_payload, profile_name, effective_set)
    write_store_to_root_payload(root_payload, store)
    return DslImportResult(entry=entry, set_name=effective_set, validation=result)


def write_test_source_into_profile(
    root_payload: Dict[str, object],
    profile_name: str,
    test_name: str,
    source_text: str,
    *,
    set_name: Optional[str] = None,
    signal_catalog_path: Optional[Path] = None,
) -> DslImportResult:
    """
    NAME
        write_test_source_into_profile - Store DSL source directly into a profile-owned runnable set.
    """
    store = store_from_root_payload(root_payload)
    _require_known_profile(root_payload, profile_name)
    clean_name = str(test_name or "").strip()
    effective_set = _resolve_profile_target_set_name(
        root_payload,
        store,
        profile_name,
        set_name,
    )
    entry, result = _build_entry_from_source_text(
        clean_name,
        str(source_text or ""),
        root_payload,
        profile_name,
        signal_catalog_path=signal_catalog_path,
    )
    store.tests_by_name[clean_name] = entry
    names = list(store.test_sets.get(effective_set, []))
    if clean_name not in names:
        names.append(clean_name)
    store.test_sets[effective_set] = names
    if not store.default_set:
        store.default_set = effective_set
    _set_profile_test_set(root_payload, profile_name, effective_set)
    write_store_to_root_payload(root_payload, store)
    return DslImportResult(entry=entry, set_name=effective_set, validation=result)


def write_test_source_into_config_library(
    root_payload: Dict[str, object],
    profile_name: str,
    test_name: str,
    source_text: str,
    *,
    signal_catalog_path: Optional[Path] = None,
) -> DslImportResult:
    """
    NAME
        write_test_source_into_config_library - Store DSL source into the config-scoped shared test library set.
    """
    store = store_from_root_payload(root_payload)
    _require_known_profile(root_payload, profile_name)
    clean_name = str(test_name or "").strip()
    config_set_name = _resolve_config_library_set_name(store)
    entry, result = _build_entry_from_source_text(
        clean_name,
        str(source_text or ""),
        root_payload,
        profile_name,
        signal_catalog_path=signal_catalog_path,
    )
    store.tests_by_name[clean_name] = entry
    names = list(store.test_sets.get(config_set_name, []))
    if clean_name not in names:
        names.append(clean_name)
    store.test_sets[config_set_name] = names
    if not store.default_set:
        store.default_set = config_set_name
    write_store_to_root_payload(root_payload, store)
    return DslImportResult(entry=entry, set_name=config_set_name, validation=result)


def copy_test_into_root_payload(
    root_payload: Dict[str, object],
    profile_name: str,
    source_test_name: str,
    target_test_name: str,
    *,
    set_name: Optional[str] = None,
    signal_catalog_path: Optional[Path] = None,
) -> DslImportResult:
    """
    NAME
        copy_test_into_root_payload - Copy one existing DSL test into a profile-owned runnable set.
    """
    store = store_from_root_payload(root_payload)
    _require_known_profile(root_payload, profile_name)
    source_name = str(source_test_name or "").strip()
    target_name = str(target_test_name or "").strip()
    source_entry = store.tests_by_name.get(source_name)
    if not isinstance(source_entry, RobotTestDslEntry):
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=source_name))
    if target_name in store.tests_by_name:
        raise DslServiceError(MESSAGE_DUPLICATE_TEST.format(name=target_name))
    effective_set = _resolve_profile_target_set_name(
        root_payload,
        store,
        profile_name,
        set_name,
    )
    try:
        renamed_source = _rename_test_declaration(source_entry.source, target_name)
        normalized = compile_source(target_name, renamed_source)
    except CompileError:
        normalized, _compile_errors = compile_source_best_effort(target_name, renamed_source)
    except Exception as exc:
        raise DslServiceError(MESSAGE_SOURCE_READ_PREFIX + str(exc)) from exc
    entry = RobotTestDslEntry(
        name=target_name,
        source=renamed_source,
        normalized=normalized,
        source_hash=source_hash(renamed_source),
        runnable=True,
    )
    result = validate_entry(
        target_name,
        entry,
        device_catalog(root_payload, profile_name, signal_catalog_path),
        signal_catalog(signal_catalog_path),
    )
    entry.runnable = result.ok()
    store.tests_by_name[target_name] = entry
    names = list(store.test_sets.get(effective_set, []))
    if target_name not in names:
        names.append(target_name)
    store.test_sets[effective_set] = names
    _set_profile_test_set(root_payload, profile_name, effective_set)
    write_store_to_root_payload(root_payload, store)
    return DslImportResult(entry=entry, set_name=effective_set, validation=result)


def update_test_source_in_root_payload(
    root_payload: Dict[str, object],
    profile_name: str,
    test_name: str,
    source_text: str,
    *,
    signal_catalog_path: Optional[Path] = None,
) -> DslImportResult:
    """
    NAME
        update_test_source_in_root_payload - Replace the source text for one profile-owned DSL test.
    """
    store = store_from_root_payload(root_payload)
    _require_known_profile(root_payload, profile_name)
    clean_name = str(test_name or "").strip()
    source_entry = store.tests_by_name.get(clean_name)
    if not isinstance(source_entry, RobotTestDslEntry):
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=clean_name))
    profile_test_names = resolve_profile_test_names(root_payload, profile_name)
    if clean_name not in profile_test_names:
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=clean_name))
    try:
        clean_source = str(source_text or "")
        renamed_source = _rename_test_declaration(clean_source, clean_name)
        normalized = compile_source(clean_name, renamed_source)
    except CompileError:
        normalized, _compile_errors = compile_source_best_effort(clean_name, renamed_source)
    except Exception as exc:
        raise DslServiceError(MESSAGE_SOURCE_READ_PREFIX + str(exc)) from exc
    entry = RobotTestDslEntry(
        name=clean_name,
        source=renamed_source,
        normalized=normalized,
        source_hash=source_hash(renamed_source),
        runnable=True,
    )
    result = validate_entry(
        clean_name,
        entry,
        device_catalog(root_payload, profile_name, signal_catalog_path),
        signal_catalog(signal_catalog_path),
    )
    entry.runnable = result.ok()
    store.tests_by_name[clean_name] = entry
    write_store_to_root_payload(root_payload, store)
    return DslImportResult(entry=entry, set_name=resolve_profile_test_set_name(root_payload, profile_name), validation=result)


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
    devices = device_catalog(root_payload, profile_name, signal_catalog_path)
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
    if not profile_set:
        return []
    if profile_set not in store.test_sets:
        return []
    selected_names = list(store.test_sets.get(profile_set, []))
    return _dedupe_preserve_order(selected_names)


def resolve_global_library_test_names(root_payload: Dict[str, object]) -> List[str]:
    """
    NAME
        resolve_global_library_test_names - Resolve ordered DSL test names from the shared global library set.
    """
    store = store_from_root_payload(root_payload)
    if not store.tests_by_name:
        return []
    global_set = str(store.default_set or "").strip()
    if not global_set or global_set not in store.test_sets:
        return []
    return _dedupe_preserve_order(list(store.test_sets.get(global_set, [])))


def list_external_library_test_names(library_dir: Optional[Path] = None) -> List[str]:
    """
    NAME
        list_external_library_test_names - List test names from the external shared DSL library directory.
    """
    directory = library_dir if library_dir is not None else dsl_global_library_dir()
    if not directory.exists():
        return []
    names: List[str] = []
    for path in sorted(directory.glob(f"*{EXTERNAL_LIBRARY_SUFFIX}")):
        if path.is_file():
            names.append(path.stem)
    return names


def read_external_library_test_source(test_name: str, library_dir: Optional[Path] = None) -> str:
    """
    NAME
        read_external_library_test_source - Read one DSL source from the external shared library.
    """
    path = _external_library_test_path(test_name, library_dir)
    if path is None or not path.exists():
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=str(test_name or "").strip()))
    return path.read_text(encoding=ENCODING_UTF8)


def import_test_into_external_library(
    test_name: str,
    source_path: Path,
    library_dir: Optional[Path] = None,
) -> Path:
    """
    NAME
        import_test_into_external_library - Import one DSL file into the external shared library directory.
    """
    clean_name = str(test_name or "").strip()
    if not clean_name:
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=clean_name))
    try:
        source = source_path.read_text(encoding=ENCODING_UTF8)
    except Exception as exc:
        raise DslServiceError(MESSAGE_SOURCE_READ_PREFIX + str(exc)) from exc
    renamed_source = _rename_test_declaration(source, clean_name)
    return write_external_library_test_source(clean_name, renamed_source, library_dir)


def write_external_library_test_source(
    test_name: str,
    source_text: str,
    library_dir: Optional[Path] = None,
) -> Path:
    """
    NAME
        write_external_library_test_source - Write one DSL source into the external shared library directory.
    """
    path = _external_library_test_path(test_name, library_dir)
    if path is None:
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=str(test_name or "").strip()))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_rename_test_declaration(str(source_text or ""), str(test_name or "").strip()), encoding=ENCODING_UTF8)
    return path


def import_test_into_config_library(
    root_payload: Dict[str, object],
    profile_name: str,
    test_name: str,
    source_path: Path,
    *,
    signal_catalog_path: Optional[Path] = None,
) -> DslImportResult:
    """
    NAME
        import_test_into_config_library - Import one DSL source file into the config-scoped shared test library.
    """
    try:
        source = source_path.read_text(encoding=ENCODING_UTF8)
    except Exception as exc:
        raise DslServiceError(MESSAGE_SOURCE_READ_PREFIX + str(exc)) from exc
    return write_test_source_into_config_library(
        root_payload,
        profile_name,
        test_name,
        source,
        signal_catalog_path=signal_catalog_path,
    )


def copy_external_library_test_into_root_payload(
    root_payload: Dict[str, object],
    profile_name: str,
    source_test_name: str,
    target_test_name: str,
    *,
    destination: str,
    signal_catalog_path: Optional[Path] = None,
    library_dir: Optional[Path] = None,
) -> DslImportResult:
    """
    NAME
        copy_external_library_test_into_root_payload - Copy one external shared-library test into config or profile scope.
    """
    source = read_external_library_test_source(source_test_name, library_dir)
    if str(destination or "").strip().lower() == "config":
        return write_test_source_into_config_library(
            root_payload,
            profile_name,
            target_test_name,
            source,
            signal_catalog_path=signal_catalog_path,
        )
    return write_test_source_into_profile(
        root_payload,
        profile_name,
        target_test_name,
        source,
        signal_catalog_path=signal_catalog_path,
    )


def rename_test_in_root_payload(
    root_payload: Dict[str, object],
    old_test_name: str,
    new_test_name: str,
) -> RobotTestDslEntry:
    """
    NAME
        rename_test_in_root_payload - Rename one config-backed DSL test and update all set references.
    """
    store = store_from_root_payload(root_payload)
    old_name = str(old_test_name or "").strip()
    new_name = str(new_test_name or "").strip()
    entry = store.tests_by_name.get(old_name)
    if not isinstance(entry, RobotTestDslEntry):
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=old_name))
    if not new_name:
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=new_name))
    if new_name != old_name and new_name in store.tests_by_name:
        raise DslServiceError(MESSAGE_DUPLICATE_TEST.format(name=new_name))
    renamed_source = _rename_test_declaration(entry.source, new_name)
    renamed_entry = RobotTestDslEntry(
        name=new_name,
        source=renamed_source,
        normalized=entry.normalized,
        source_hash=source_hash(renamed_source),
        runnable=entry.runnable,
    )
    if renamed_entry.normalized is not None:
        renamed_entry.normalized.name = new_name
    del store.tests_by_name[old_name]
    store.tests_by_name[new_name] = renamed_entry
    for set_names in store.test_sets.values():
        for index, value in enumerate(list(set_names)):
            if str(value or "").strip() == old_name:
                set_names[index] = new_name
    write_store_to_root_payload(root_payload, store)
    return renamed_entry


def delete_test_from_root_payload(
    root_payload: Dict[str, object],
    test_name: str,
) -> Path:
    """
    NAME
        delete_test_from_root_payload - Archive and delete one config-backed DSL test from the store and all sets.
    """
    store = store_from_root_payload(root_payload)
    clean_name = str(test_name or "").strip()
    entry = store.tests_by_name.get(clean_name)
    if not isinstance(entry, RobotTestDslEntry):
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=clean_name))
    archive_path = _archive_dsl_source(clean_name, entry.source, ARCHIVE_SCOPE_CONFIG)
    del store.tests_by_name[clean_name]
    for set_names in store.test_sets.values():
        while clean_name in set_names:
            set_names.remove(clean_name)
    write_store_to_root_payload(root_payload, store)
    return archive_path


def rename_external_library_test(
    old_test_name: str,
    new_test_name: str,
    library_dir: Optional[Path] = None,
) -> Path:
    """
    NAME
        rename_external_library_test - Rename one external shared-library DSL source file and its internal test declaration.
    """
    old_name = str(old_test_name or "").strip()
    new_name = str(new_test_name or "").strip()
    source = read_external_library_test_source(old_name, library_dir)
    old_path = _external_library_test_path(old_name, library_dir)
    new_path = _external_library_test_path(new_name, library_dir)
    if old_path is None or new_path is None:
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=old_name))
    if new_path.exists() and new_name != old_name:
        raise DslServiceError(MESSAGE_DUPLICATE_TEST.format(name=new_name))
    renamed_source = _rename_test_declaration(source, new_name)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_text(renamed_source, encoding=ENCODING_UTF8)
    if old_path.exists() and old_path != new_path:
        old_path.unlink()
    return new_path


def delete_external_library_test(
    test_name: str,
    library_dir: Optional[Path] = None,
) -> Path:
    """
    NAME
        delete_external_library_test - Archive and delete one external shared-library DSL source file.
    """
    clean_name = str(test_name or "").strip()
    path = _external_library_test_path(clean_name, library_dir)
    if path is None or not path.exists():
        raise DslServiceError(MESSAGE_UNKNOWN_TEST.format(name=clean_name))
    source = path.read_text(encoding=ENCODING_UTF8)
    archive_path = _archive_dsl_source(clean_name, source, ARCHIVE_SCOPE_EXTERNAL)
    path.unlink()
    return archive_path


def resolve_profile_test_set_name(root_payload: Dict[str, object], profile_name: str) -> str:
    """
    NAME
        resolve_profile_test_set_name - Return the explicitly bound DSL set name for one profile.
    """
    profiles = root_payload.get(KEY_PROFILES) if isinstance(root_payload, dict) else None
    profile_entry = profiles.get(profile_name) if isinstance(profiles, dict) else None
    if not isinstance(profile_entry, dict):
        return ""
    return str(profile_entry.get(KEY_DSL_TEST_SET, "") or "").strip()


def issue_line_excerpt(entry: RobotTestDslEntry, field: str) -> Optional[str]:
    """
    NAME
        issue_line_excerpt - Resolve a DSL validation field to a source excerpt when possible.
    """
    field_text = str(field or "").strip()
    if not field_text:
        return _first_nonempty_line_excerpt(entry)
    if field_text in _validation_meta_fields():
        return _first_nonempty_line_excerpt(entry)
    for line_number, source_line in enumerate(entry.source.splitlines(), start=1):
        line_text = source_line.strip()
        if not line_text:
            continue
        if line_text == field_text or field_text in line_text:
            return f"line {line_number}: {line_text}"
    return _first_nonempty_line_excerpt(entry) or f"field {field_text}"


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
    message = str(getattr(issue, "message", "") or "")
    if message.startswith("Compile error at line "):
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
        if isinstance(field, str) and field.strip() in _validation_meta_fields():
            return ""
        if isinstance(field, str) and field.strip():
            return f" (field {field.strip()})"
        return ""
    excerpt = issue_line_excerpt(entry, field if isinstance(field, str) else "")
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


def _profile_default_test_set_name(profile_name: str) -> str:
    clean_name = str(profile_name or "").strip()
    if not clean_name:
        return DEFAULT_TEST_SET
    return PROFILE_TEST_SET_NAME_FORMAT.format(profile=clean_name)


def _resolve_profile_target_set_name(
    root_payload: Dict[str, object],
    store: RobotTestDslStore,
    profile_name: str,
    set_name: Optional[str],
) -> str:
    explicit_name = str(set_name or "").strip()
    if explicit_name:
        return explicit_name
    profile_set = resolve_profile_test_set_name(root_payload, profile_name)
    if profile_set:
        return profile_set
    default_name = _profile_default_test_set_name(profile_name)
    if default_name not in store.test_sets:
        store.test_sets[default_name] = []
    return default_name


def _resolve_config_library_set_name(store: RobotTestDslStore) -> str:
    config_set = str(store.default_set or "").strip()
    if not config_set:
        config_set = DEFAULT_TEST_SET
        store.default_set = config_set
    if config_set not in store.test_sets:
        store.test_sets[config_set] = []
    return config_set


def _build_entry_from_source_text(
    test_name: str,
    source_text: str,
    root_payload: Dict[str, object],
    profile_name: str,
    *,
    signal_catalog_path: Optional[Path] = None,
) -> tuple[RobotTestDslEntry, ValidationResult]:
    clean_name = str(test_name or "").strip()
    renamed_source = _rename_test_declaration(str(source_text or ""), clean_name)
    try:
        normalized = compile_source(clean_name, renamed_source)
    except CompileError:
        normalized, _compile_errors = compile_source_best_effort(clean_name, renamed_source)
    entry = RobotTestDslEntry(
        name=clean_name,
        source=renamed_source,
        normalized=normalized,
        source_hash=source_hash(renamed_source),
        runnable=True,
    )
    result = validate_entry(
        clean_name,
        entry,
        device_catalog(root_payload, profile_name, signal_catalog_path),
        signal_catalog(signal_catalog_path),
    )
    entry.runnable = result.ok()
    return entry, result


def _rename_test_declaration(source: str, test_name: str) -> str:
    clean_name = str(test_name or "").strip()
    if not clean_name:
        return source
    match = TEST_DECLARATION_PATTERN.search(source)
    if match is None:
        return source
    prefix = str(match.group("prefix"))
    suffix = str(match.group("suffix"))
    replacement = f"{prefix}{clean_name}{suffix}"
    start_index = match.start()
    end_index = match.end()
    return source[:start_index] + replacement + source[end_index:]


def _external_library_test_path(test_name: str, library_dir: Optional[Path] = None) -> Optional[Path]:
    clean_name = str(test_name or "").strip()
    if not clean_name:
        return None
    directory = library_dir if library_dir is not None else dsl_global_library_dir()
    return directory / f"{clean_name}{EXTERNAL_LIBRARY_SUFFIX}"


def _archive_dsl_source(test_name: str, source_text: str, scope_name: str) -> Path:
    clean_name = str(test_name or "").strip()
    archive_root = dsl_test_archive_dir() / str(scope_name or "").strip()
    archive_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(ARCHIVE_TIMESTAMP_FORMAT)
    archive_path = archive_root / f"{timestamp}__{clean_name}{EXTERNAL_LIBRARY_SUFFIX}"
    archive_path.write_text(_rename_test_declaration(str(source_text or ""), clean_name), encoding=ENCODING_UTF8)
    return archive_path


def _require_known_profile(root_payload: Dict[str, object], profile_name: str) -> None:
    profiles = root_payload.get(KEY_PROFILES) if isinstance(root_payload, dict) else None
    clean_name = str(profile_name or "").strip()
    if not isinstance(profiles, dict) or clean_name not in profiles:
        raise DslServiceError(MESSAGE_UNKNOWN_PROFILE.format(name=clean_name))


def _validation_meta_fields() -> set[str]:
    return {KEY_DSL_TESTS, KEY_TEST_SETS, KEY_TESTS_BY_NAME, KEY_DEFAULT_SET, "source", "normalized", "sourceHash"}


def _first_nonempty_line_excerpt(entry: RobotTestDslEntry) -> Optional[str]:
    """
    NAME
        _first_nonempty_line_excerpt - Return the first non-empty source line with a line number.
    """
    for line_number, source_line in enumerate(entry.source.splitlines(), start=1):
        line_text = source_line.strip()
        if line_text:
            return f"line {line_number}: {line_text}"
    return None
