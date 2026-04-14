from __future__ import annotations

"""
NAME
    schema_store.py - Schema-aware config store (middle layer).

SYNOPSIS
    store = ConfigSchemaStore()
    warnings = store.load(repo_root)
    result = store.validate(strict=False)

DESCRIPTION
    Provides a centralized, CLI-agnostic in-memory store for configuration
    data used by Windows-side Python tools. JSON files are imported into
    the store and exported on save. Validation runs against the in-memory
    snapshot and can be strict or lenient.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from tools.common.json_io import write_json
from tools.common.paths import repo_root as repo_root_path
from tools.common.profile_constants import (
    BRIDGE_CONFIG_SCHEMA_VERSION,
    KEY_ANALOG,
    KEY_ATTACHMENTS,
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_CONFIG,
    KEY_BRIDGE_TESTS,
    KEY_BRIDGE_GENERATED_AT,
    KEY_BRIDGE_GROUPS,
    KEY_BRIDGE_SCHEMA_VERSION,
    KEY_BRIDGE_SELECTED_DEVICE,
    KEY_BUS,
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DEFAULT_PROFILE,
    KEY_DIAGRAM,
    KEY_DEVICE,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_DIO,
    KEY_ID,
    KEY_INTERFACE,
    KEY_INTERFACE_LEGACY,
    KEY_INVERT,
    KEY_LABEL,
    KEY_LIMITS,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_NOTES,
    KEY_INPUT_ALIASES,
    KEY_PROFILE_DEVICES,
    KEY_PROFILES,
    KEY_PWM,
    KEY_ROLE,
    KEY_SCHEMA_VERSION,
    KEY_TAGS,
    KEY_TERMINATOR,
    KEY_TYPE,
    KEY_VENDOR,
    INTERFACE_ANALOG,
    INTERFACE_CAN,
    INTERFACE_DIO,
    INTERFACE_INTERNAL,
    INTERFACE_PWM,
    PROFILE_SCHEMA_VERSION,
    get_device_interface,
)
from tools.common.test_authoring import (
    TestAuthoringModel,
    model_from_payload,
    model_to_payload,
    validate_model,
)
from tools.config.json_store import JsonStore


KEY_TESTS = "tests"
KEY_TEST_SETS = "test_sets"
KEY_DEFAULT_TEST_SET = "default_test_set"
KEY_CONTROLLERS = "controllers"
KEY_BINDINGS = "bindings"
KEY_AXES = "axes"
KEY_MANUFACTURERS = "manufacturers"
KEY_DEVICE_TYPES = "device_types"
KEY_MEMBERS = "members"
KEY_ENABLED = "enabled"
KEY_NAME = "name"
KEY_COMMAND = "command"
KEY_CONTROLLER = "controller"
KEY_INPUT = "input"
KEY_ID_STR = "id"
KEY_MODE = "mode"
KEY_TYPE = "type"
KEY_PORT = "port"
KEY_DEADBAND = "deadband"

DIRTY_PROFILES = "profiles"
DIRTY_GROUPS = "groups"
DIRTY_TESTS = "tests"
DIRTY_BINDINGS = "bindings"
DIRTY_CAN_MAPPINGS = "can-mappings"

SEVERITY_ERROR = "error"
SEVERITY_WARN = "warn"
LOCATION_PROFILES = "profiles"
LOCATION_TESTS = "tests"
LOCATION_BINDINGS = "bindings"
LOCATION_MAPPINGS = "can-mappings"

MESSAGE_MERGE_WARNING = (
    "Both root and deploy {label} exist; merged with root override: {root} over {deploy}"
)
MESSAGE_UNKNOWN_KEY = "Unknown key: {key}"
MESSAGE_TYPE_INVALID = "Invalid type for {key}"
MESSAGE_REQUIRED_FIELD = "Missing required field: {key}"
MESSAGE_DEVICE_DUPLICATE = "Duplicate device label: {label}"
MESSAGE_DEVICE_LABEL_REQUIRED = "Device label is required."
MESSAGE_DEVICE_INTERFACE_REQUIRED = "Device interface is required."
MESSAGE_DEVICE_INTERFACE_INVALID = "Device interface is invalid."
MESSAGE_DEVICE_INTERFACE_REQUIRED_FMT = "Device {label}: interface is required."
MESSAGE_DEVICE_INTERFACE_INVALID_FMT = "Device {label}: interface is invalid."
MESSAGE_DEVICE_MANUFACTURER_REQUIRED = "Device manufacturer is required."
MESSAGE_DEVICE_DEVICE_TYPE_REQUIRED = "Device deviceType is required."
MESSAGE_DEVICE_ID_REQUIRED = "Device id is required."
MESSAGE_DEVICE_DIO_REQUIRED = "Device dio is required."
MESSAGE_DEVICE_INVERT_REQUIRED = "Device invert is required."
MESSAGE_DEVICE_PWM_REQUIRED = "Device pwm is required."
MESSAGE_DEVICE_ANALOG_REQUIRED = "Device analog is required."
MESSAGE_DEVICE_MANUFACTURER_TYPE = "Device manufacturer must be int."
MESSAGE_DEVICE_DEVICE_TYPE_TYPE = "Device deviceType must be int."
MESSAGE_DEVICE_ID_TYPE = "Device id must be int."
MESSAGE_DEVICE_DIO_TYPE = "Device dio must be int."
MESSAGE_DEVICE_INVERT_TYPE = "Device invert must be bool."
MESSAGE_DEVICE_PWM_TYPE = "Device pwm must be int."
MESSAGE_DEVICE_ANALOG_TYPE = "Device analog must be int."
MESSAGE_DEVICE_MANUFACTURER_TYPE_FMT = "Device {label}: manufacturer must be int."
MESSAGE_DEVICE_DEVICE_TYPE_TYPE_FMT = "Device {label}: deviceType must be int."
MESSAGE_DEVICE_ID_TYPE_FMT = "Device {label}: id must be int."
MESSAGE_DEVICE_DIO_TYPE_FMT = "Device {label}: dio must be int."
MESSAGE_DEVICE_INVERT_TYPE_FMT = "Device {label}: invert must be bool."
MESSAGE_DEVICE_PWM_TYPE_FMT = "Device {label}: pwm must be int."
MESSAGE_DEVICE_ANALOG_TYPE_FMT = "Device {label}: analog must be int."
MESSAGE_REQUIRED_FIELD_FMT = "Device {label}: Missing required field: {key}"
MESSAGE_MISSING_DEVICE_REF = "Missing device in profile: {label}"
MESSAGE_MISSING_DEVICE_REF_PROFILE = "Profile {profile}: Missing device in profile: {label}"
MESSAGE_MISSING_ATTACHMENT_REF = "Device {label}: Missing attachment device: {attachment}"
MESSAGE_PROFILE_UNKNOWN = "Profile not found: {profile}"
MESSAGE_BINDINGS_CONTROLLER_DUP = "Duplicate controller name."
MESSAGE_BINDINGS_CONTROLLER_REQUIRED = "Controller name not found: {name}"
MESSAGE_BINDINGS_CONTROLLER_PORT = "Controller port must be int."
MESSAGE_BINDINGS_CONTROLLER_FIELDS = "Controller entry missing required fields."
MESSAGE_BINDINGS_BINDING_FIELDS = "Binding entry missing required fields."
MESSAGE_BINDINGS_AXIS_FIELDS = "Axis entry missing required fields."
MESSAGE_BINDINGS_INVERT_TYPE = "Axis invert must be bool."
MESSAGE_BINDINGS_DEADBAND_RANGE = "Axis deadband must be 0.0 to 1.0."
MESSAGE_MAPPINGS_KEY_TYPE = "Mapping id must be numeric string."
MESSAGE_MAPPINGS_VALUE_TYPE = "Mapping value must be non-empty string."
MESSAGE_TEST_ISSUE = "{name}: {message}"
MESSAGE_TEST_FIELD_ISSUE = "{name}.{field}: {message}"
MESSAGE_TEST_GENERIC = "{message}"
MESSAGE_TEST_PROFILE_PREFIX = "profile {profile}: {message}"
ATTR_TEST_NAME = "test_name"
ATTR_FIELD = "field"
ATTR_MESSAGE = "message"

DEVICE_REQUIRED_CAN = (KEY_INTERFACE, KEY_MANUFACTURER, KEY_DEVICE_TYPE, KEY_ID)
DEVICE_REQUIRED_DIO = (KEY_INTERFACE, KEY_DIO, KEY_INVERT)
DEVICE_REQUIRED_PWM = (KEY_INTERFACE, KEY_PWM)
DEVICE_REQUIRED_ANALOG = (KEY_INTERFACE, KEY_ANALOG)
DEVICE_REQUIRED_INTERNAL = (KEY_INTERFACE,)

ALLOWED_ROOT_KEYS = {
    KEY_SCHEMA_VERSION,
    KEY_DATA_VERSION,
    KEY_DATA_HASH,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICES,
    KEY_PROFILES,
    KEY_BRIDGE_CONFIG,
    KEY_DIAGRAM,
}
ALLOWED_TESTS_KEYS = {KEY_DEFAULT_TEST_SET, KEY_TEST_SETS, KEY_TESTS}
ALLOWED_BINDINGS_KEYS = {KEY_CONTROLLERS, KEY_BINDINGS, KEY_AXES, KEY_INPUT_ALIASES}
ALLOWED_MAPPINGS_KEYS = {KEY_MANUFACTURERS, KEY_DEVICE_TYPES}
ALLOWED_DEVICE_KEYS = {
    KEY_LABEL,
    KEY_INTERFACE,
    KEY_INTERFACE_LEGACY,
    KEY_MANUFACTURER,
    KEY_DEVICE_TYPE,
    KEY_ID,
    KEY_MODEL,
    KEY_TYPE,
    KEY_VENDOR,
    KEY_ROLE,
    KEY_NOTES,
    KEY_TAGS,
    KEY_TERMINATOR,
    KEY_LIMITS,
    KEY_BUS,
    KEY_DIO,
    KEY_INVERT,
    KEY_PWM,
    KEY_ANALOG,
    KEY_ATTACHMENTS,
}
ALLOWED_GROUP_KEYS = {KEY_NAME, KEY_ENABLED, KEY_MEMBERS, KEY_BINDINGS}
ALLOWED_MEMBER_KEYS = {KEY_DEVICE, KEY_ENABLED}

COUNT_ZERO = 0
COUNT_ONE = 1
COUNT_TWO = 2
DEADBAND_MIN = 0.0
DEADBAND_MAX = 1.0
EMPTY_STRING = ""
BOOL_TRUE = True
BOOL_FALSE = False

FILE_TESTS_ROOT = "bringup_tests.json"
FILE_BINDINGS_ROOT = "bringup_bindings.json"
FILE_CAN_MAPPINGS_ROOT = "can_mappings.json"
FILE_PROFILES = "bringup_system.json"
DIR_DATA = "data"
DIR_SRC = "src"
DIR_MAIN = "main"
DIR_DEPLOY = "deploy"
DOC_PROFILES = "profiles"
DOC_TESTS = "tests"
DOC_BINDINGS = "bindings"
DOC_MAPPINGS = "can-mappings"
DIRTY_DOC_MAP = {
    DIRTY_PROFILES: DOC_PROFILES,
    DIRTY_TESTS: DOC_TESTS,
    DIRTY_BINDINGS: DOC_BINDINGS,
    DIRTY_CAN_MAPPINGS: DOC_MAPPINGS,
}


@dataclass
class ValidationIssue:
    """
    NAME
        ValidationIssue - Validation warning or error record.
    """

    location: str
    message: str
    severity: str


@dataclass
class ValidationResult:
    """
    NAME
        ValidationResult - Aggregated validation output.
    """

    issues: List[ValidationIssue]

    def ok(self) -> bool:
        """
        NAME
            ok - Return True when no error-level issues exist.
        """

        return not self.errors()

    def errors(self) -> List[ValidationIssue]:
        """
        NAME
            errors - Return error-level issues.
        """

        return [issue for issue in self.issues if issue.severity == SEVERITY_ERROR]

    def warnings(self) -> List[ValidationIssue]:
        """
        NAME
            warnings - Return warning-level issues.
        """

        return [issue for issue in self.issues if issue.severity == SEVERITY_WARN]


class ConfigSchemaStore:
    """
    NAME
        ConfigSchemaStore - Schema-aware config store.

    DESCRIPTION
        Imports JSON configuration into a generic JSON store, provides
        validation, and exports to JSON on save. The store is CLI-agnostic
        and returns validation and merge warnings for the caller to render.
    """

    def __init__(self) -> None:
        """
        NAME
            __init__ - Initialize the store.
        """

        self._repo_root: Path = repo_root_path()
        self._db = JsonStore()
        self._tests_by_profile: Dict[str, TestAuthoringModel] = dict()
        self._dirty_flags: Dict[str, bool] = {
            DIRTY_PROFILES: BOOL_FALSE,
            DIRTY_GROUPS: BOOL_FALSE,
            DIRTY_TESTS: BOOL_FALSE,
            DIRTY_BINDINGS: BOOL_FALSE,
            DIRTY_CAN_MAPPINGS: BOOL_FALSE,
        }
        self._warnings: List[str] = list()

    def load(self, repo_root: Optional[Path] = None) -> List[str]:
        """
        NAME
            load - Import JSON files into the store.

        PARAMETERS
            repo_root - Optional repo root override.

        RETURNS
            List of merge warnings.
        """

        self._warnings = list()
        if repo_root is not None:
            self._repo_root = repo_root
        profiles_payload = self._load_profiles(self._profiles_path(self._repo_root))
        self._tests_by_profile = self._load_tests_from_profiles(profiles_payload)
        self._load_bindings(self._repo_root)
        self._load_mappings(self._repo_root)
        for key in self._dirty_flags:
            self._dirty_flags[key] = BOOL_FALSE
        return list(self._warnings)

    def set_repo_root(self, repo_root: Path) -> None:
        """
        NAME
            set_repo_root - Update the repository root path.
        """

        self._repo_root = repo_root

    def set_profiles_payload(self, payload: Dict[str, object]) -> None:
        """
        NAME
            set_profiles_payload - Replace the profiles payload.
        """

        self._db.set_payload(DOC_PROFILES, payload)

    def set_tests_model(self, profile: str, model: Optional[TestAuthoringModel]) -> None:
        """
        NAME
            set_tests_model - Replace tests authoring model for a profile.
        """

        if not profile:
            return
        if model is None:
            self._tests_by_profile.pop(profile, None)
            return
        self._tests_by_profile[profile] = model

    def set_bindings_payload(self, payload: Dict[str, object]) -> None:
        """
        NAME
            set_bindings_payload - Replace bindings payload.
        """

        self._db.set_payload(DOC_BINDINGS, payload)

    def set_mappings_payload(self, payload: Dict[str, object]) -> None:
        """
        NAME
            set_mappings_payload - Replace CAN mappings payload.
        """

        self._db.set_payload(DOC_MAPPINGS, payload)

    def mark_dirty(self, key: str, dirty: bool = BOOL_TRUE) -> None:
        """
        NAME
            mark_dirty - Update a dirty flag by key.
        """

        if key in self._dirty_flags:
            self._dirty_flags[key] = bool(dirty)
        doc_id = DIRTY_DOC_MAP.get(key)
        if doc_id:
            self._db.mark_dirty(doc_id, dirty)

    def set_dirty_flags(self, flags: Dict[str, bool]) -> None:
        """
        NAME
            set_dirty_flags - Replace dirty flags from a dict.
        """

        for key, value in flags.items():
            if key in self._dirty_flags:
                self._dirty_flags[key] = bool(value)
            doc_id = DIRTY_DOC_MAP.get(key)
            if doc_id:
                self._db.mark_dirty(doc_id, value)

    def root_payload(self) -> Dict[str, object]:
        """
        NAME
            root_payload - Return the profiles root payload.
        """

        return self._db.get_payload(DOC_PROFILES)

    def bridge_config(self) -> Dict[str, object]:
        """
        NAME
            bridge_config - Return bridgeConfig payload.
        """

        payload = self._db.get_payload(DOC_PROFILES).get(KEY_BRIDGE_CONFIG)
        if isinstance(payload, dict):
            return payload
        return dict()

    def profiles(self) -> Dict[str, object]:
        """
        NAME
            profiles - Return profiles mapping.
        """

        profiles = self._db.get_payload(DOC_PROFILES).get(KEY_PROFILES)
        if isinstance(profiles, dict):
            return profiles
        return dict()

    def devices(self) -> List[Dict[str, object]]:
        """
        NAME
            devices - Return device registry list.
        """

        devices = self._db.get_payload(DOC_PROFILES).get(KEY_DEVICES)
        if isinstance(devices, list):
            return devices
        return list()

    def device_by_label(self, label: str) -> Optional[Dict[str, object]]:
        """
        NAME
            device_by_label - Return device entry by label.
        """

        if not label:
            return None
        for entry in self.devices():
            if not isinstance(entry, dict):
                continue
            if entry.get(KEY_LABEL) == label:
                return entry
        return None

    def groups(self, profile: str) -> List[Dict[str, object]]:
        """
        NAME
            groups - Return groups for a profile name.
        """

        if not profile:
            return list()
        by_profile = self._bridge_by_profile()
        entry = by_profile.get(profile)
        if not isinstance(entry, dict):
            return list()
        groups = entry.get(KEY_BRIDGE_GROUPS)
        if isinstance(groups, list):
            return groups
        return list()

    def selected_device(self, profile: str) -> Dict[str, object]:
        """
        NAME
            selected_device - Return selectedDevice entry for a profile.
        """

        if not profile:
            return dict()
        by_profile = self._bridge_by_profile()
        entry = by_profile.get(profile)
        if not isinstance(entry, dict):
            return dict()
        selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE)
        if isinstance(selected, dict):
            return selected
        return dict()

    def tests_model(self, profile: Optional[str]) -> Optional[TestAuthoringModel]:
        """
        NAME
            tests_model - Return tests model for a profile.
        """

        if not profile:
            return None
        return self._tests_by_profile.get(profile)

    def bindings(self) -> Dict[str, object]:
        """
        NAME
            bindings - Return controller bindings payload.
        """

        return self._db.get_payload(DOC_BINDINGS)

    def can_mappings(self) -> Dict[str, object]:
        """
        NAME
            can_mappings - Return CAN mappings payload.
        """

        return self._db.get_payload(DOC_MAPPINGS)

    def dirty_flags(self) -> Dict[str, bool]:
        """
        NAME
            dirty_flags - Return dirty state per section.
        """

        flags = dict(self._dirty_flags)
        doc_flags = self._db.dirty_flags()
        for key, doc_id in DIRTY_DOC_MAP.items():
            if doc_id in doc_flags:
                flags[key] = bool(doc_flags[doc_id])
        return flags

    def validate(self, strict: bool = True) -> ValidationResult:
        """
        NAME
            validate - Validate the in-memory snapshot.

        PARAMETERS
            strict - True for strict unknown-key enforcement.

        RETURNS
            ValidationResult with errors and warnings.
        """

        issues: List[ValidationIssue] = list()
        self._validate_profiles(issues, strict)
        self._validate_tests(issues, strict)
        self._validate_bindings(issues, strict)
        self._validate_mappings(issues, strict)
        return ValidationResult(issues)

    def validate_profiles_only(
        self, strict: bool = True, profile_name: Optional[str] = None
    ) -> ValidationResult:
        """
        NAME
            validate_profiles_only - Validate profiles and bridge config only.
        """

        issues: List[ValidationIssue] = list()
        self._validate_profiles(issues, strict, profile_name=profile_name)
        return ValidationResult(issues)

    def validate_bindings_only(self, strict: bool = True) -> ValidationResult:
        """
        NAME
            validate_bindings_only - Validate controller bindings only.
        """

        issues: List[ValidationIssue] = list()
        self._validate_bindings(issues, strict)
        return ValidationResult(issues)

    def validate_mappings_only(self, strict: bool = True) -> ValidationResult:
        """
        NAME
            validate_mappings_only - Validate CAN mappings only.
        """

        issues: List[ValidationIssue] = list()
        self._validate_mappings(issues, strict)
        return ValidationResult(issues)

    def save_profiles(self, path: str | Path) -> None:
        """
        NAME
            save_profiles - Write profiles payload to a file.
        """

        payload = dict(self._db.get_payload(DOC_PROFILES))
        self._write_tests_into_profiles(payload)
        write_json(Path(path), payload)

    def save_bindings(self, path: str | Path) -> None:
        """
        NAME
            save_bindings - Write bindings payload to a file.
        """

        write_json(Path(path), self._db.get_payload(DOC_BINDINGS))

    def save_mappings(self, path: str | Path) -> None:
        """
        NAME
            save_mappings - Write CAN mappings payload to a file.
        """

        write_json(Path(path), self._db.get_payload(DOC_MAPPINGS))

    def _bridge_by_profile(self) -> Dict[str, object]:
        """
        NAME
            _bridge_by_profile - Return bridgeConfig.byProfile mapping.
        """

        bridge = self.bridge_config()
        by_profile = bridge.get(KEY_BRIDGE_BY_PROFILE)
        if isinstance(by_profile, dict):
            return by_profile
        return dict()

    def _profiles_path(self, repo_root: Path) -> Path:
        """
        NAME
            _profiles_path - Resolve bringup_system.json path.
        """

        return repo_root / DIR_DATA / FILE_PROFILES

    def _deploy_path(self, filename: str) -> Path:
        """
        NAME
            _deploy_path - Resolve deploy path for a filename.
        """

        return self._repo_root / DIR_SRC / DIR_MAIN / DIR_DEPLOY / filename

    def _load_profiles(self, path: Path) -> Dict[str, object]:
        """
        NAME
            _load_profiles - Load bringup_system.json.
        """
        self._db.load_document(DOC_PROFILES, path, None, None)
        payload = self._db.get_payload(DOC_PROFILES)
        if not isinstance(payload, dict) or not payload:
            payload = self._default_profiles_payload()
            self._db.set_payload(DOC_PROFILES, payload)
        self._ensure_bridge_config(payload)
        self._normalize_device_interface_keys(payload)
        self._db.set_payload(DOC_PROFILES, payload)
        return payload

    def _normalize_device_interface_keys(self, payload: Dict[str, object]) -> None:
        """
        NAME
            _normalize_device_interface_keys - Normalize legacy 'interface' -> deviceInterface.

        DESCRIPTION
            For backward compatibility, accept the legacy JSON key 'interface' in
            device registry entries and copy it into the canonical key
            deviceInterface when the canonical key is missing.
        """

        devices = payload.get(KEY_DEVICES)
        if not isinstance(devices, list):
            return
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            if entry.get(KEY_INTERFACE) is None and entry.get(KEY_INTERFACE_LEGACY) is not None:
                entry[KEY_INTERFACE] = entry.get(KEY_INTERFACE_LEGACY)

    def _default_profiles_payload(self) -> Dict[str, object]:
        """
        NAME
            _default_profiles_payload - Build default profiles payload.
        """

        return {
            KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
            KEY_DATA_VERSION: EMPTY_STRING,
            KEY_DATA_HASH: EMPTY_STRING,
            KEY_DEFAULT_PROFILE: EMPTY_STRING,
            KEY_DEVICES: list(),
            KEY_PROFILES: dict(),
            KEY_BRIDGE_CONFIG: {
                KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
                KEY_BRIDGE_GENERATED_AT: None,
                KEY_BRIDGE_BY_PROFILE: dict(),
            },
        }

    def _ensure_bridge_config(self, payload: Dict[str, object]) -> None:
        """
        NAME
            _ensure_bridge_config - Ensure bridgeConfig structure exists.
        """

        bridge = payload.get(KEY_BRIDGE_CONFIG)
        if not isinstance(bridge, dict):
            bridge = {
                KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
                KEY_BRIDGE_GENERATED_AT: None,
                KEY_BRIDGE_BY_PROFILE: dict(),
            }
            payload[KEY_BRIDGE_CONFIG] = bridge
        if KEY_BRIDGE_SCHEMA_VERSION not in bridge:
            bridge[KEY_BRIDGE_SCHEMA_VERSION] = BRIDGE_CONFIG_SCHEMA_VERSION
        if KEY_BRIDGE_GENERATED_AT not in bridge:
            bridge[KEY_BRIDGE_GENERATED_AT] = None
        if KEY_BRIDGE_BY_PROFILE not in bridge or not isinstance(
            bridge.get(KEY_BRIDGE_BY_PROFILE), dict
        ):
            bridge[KEY_BRIDGE_BY_PROFILE] = dict()
        if KEY_DEVICES not in bridge:
            bridge[KEY_DEVICES] = list()

    def _load_tests_from_profiles(
        self, profiles_payload: Dict[str, object]
    ) -> Dict[str, TestAuthoringModel]:
        """
        NAME
            _load_tests_from_profiles - Load tests models from bridgeConfig.byProfile.
        """

        tests_by_profile: Dict[str, TestAuthoringModel] = dict()
        bridge = profiles_payload.get(KEY_BRIDGE_CONFIG)
        if not isinstance(bridge, dict):
            return tests_by_profile
        by_profile = bridge.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return tests_by_profile
        for profile_name, entry in by_profile.items():
            if not isinstance(profile_name, str) or not isinstance(entry, dict):
                continue
            payload = entry.get(KEY_BRIDGE_TESTS)
            if not isinstance(payload, dict):
                continue
            try:
                tests_by_profile[profile_name] = model_from_payload(payload)
            except Exception:
                tests_by_profile[profile_name] = TestAuthoringModel()
        return tests_by_profile

    def _load_bindings(self, repo_root: Path) -> Dict[str, object]:
        """
        NAME
            _load_bindings - Load and merge controller bindings payloads.
        """

        root_path = repo_root / FILE_BINDINGS_ROOT
        deploy_path = self._deploy_path(FILE_BINDINGS_ROOT)
        warnings = self._db.load_document(DOC_BINDINGS, root_path, deploy_path, self._merge_bindings)
        self._warnings.extend(warnings)
        return self._db.get_payload(DOC_BINDINGS)

    def _load_mappings(self, repo_root: Path) -> Dict[str, object]:
        """
        NAME
            _load_mappings - Load CAN mappings payload.
        """

        path = self._deploy_path(FILE_CAN_MAPPINGS_ROOT)
        self._db.load_document(DOC_MAPPINGS, path, None, None)
        return self._db.get_payload(DOC_MAPPINGS)

    def _write_tests_into_profiles(self, payload: Dict[str, object]) -> None:
        """
        NAME
            _write_tests_into_profiles - Store tests models under bridgeConfig.byProfile.
        """

        bridge = payload.get(KEY_BRIDGE_CONFIG)
        if bridge is None:
            bridge = {}
            payload[KEY_BRIDGE_CONFIG] = bridge
        if not isinstance(bridge, dict):
            return
        by_profile = bridge.get(KEY_BRIDGE_BY_PROFILE)
        if by_profile is None:
            by_profile = {}
            bridge[KEY_BRIDGE_BY_PROFILE] = by_profile
        if not isinstance(by_profile, dict):
            return
        for profile_name, model in self._tests_by_profile.items():
            if not profile_name or model is None:
                continue
            entry = by_profile.get(profile_name)
            if not isinstance(entry, dict):
                entry = {}
                by_profile[profile_name] = entry
            entry[KEY_BRIDGE_TESTS] = model_to_payload(model)

    def _merge_bindings(
        self, root_payload: Dict[str, object], deploy_payload: Dict[str, object]
    ) -> Tuple[Dict[str, object], List[str]]:
        """
        NAME
            _merge_bindings - Merge root/deploy bindings payloads with warnings.
        """

        merged: Dict[str, object] = dict()
        warnings: List[str] = list()
        if deploy_payload:
            merged.update(deploy_payload)
        if root_payload:
            for key in (KEY_CONTROLLERS, KEY_BINDINGS, KEY_AXES):
                if key in root_payload and key in deploy_payload:
                    warnings.append(
                        MESSAGE_MERGE_WARNING.format(
                            label=key,
                            root=FILE_BINDINGS_ROOT,
                            deploy=str(self._deploy_path(FILE_BINDINGS_ROOT)),
                        )
                    )
                if key in root_payload:
                    merged[key] = root_payload.get(key)
        return merged, warnings

    def _validate_profiles(
        self,
        issues: List[ValidationIssue],
        strict: bool,
        profile_name: Optional[str] = None,
    ) -> None:
        """
        NAME
            _validate_profiles - Validate profiles and device registry.
        """

        payload = self._db.get_payload(DOC_PROFILES)
        if not isinstance(payload, dict):
            self._append_issue(issues, LOCATION_PROFILES, MESSAGE_TYPE_INVALID.format(key=KEY_PROFILES), SEVERITY_ERROR)
            return
        self._check_unknown_keys(payload, ALLOWED_ROOT_KEYS, LOCATION_PROFILES, issues, strict)
        devices = payload.get(KEY_DEVICES)
        if not isinstance(devices, list):
            self._append_issue(issues, LOCATION_PROFILES, MESSAGE_TYPE_INVALID.format(key=KEY_DEVICES), SEVERITY_ERROR)
            devices = list()
        target_profile = profile_name
        active_profile = None
        profiles = payload.get(KEY_PROFILES)
        if target_profile:
            if isinstance(profiles, dict):
                active_profile = profiles.get(target_profile)
            if not isinstance(active_profile, dict):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_PROFILE_UNKNOWN.format(profile=target_profile),
                    SEVERITY_ERROR,
                )
                active_profile = None
        catalog, duplicates = self._build_device_catalog(devices)
        active_labels: Optional[Set[str]] = None
        if target_profile and active_profile is None:
            active_labels = set()
        elif active_profile is not None:
            labels = active_profile.get(KEY_PROFILE_DEVICES)
            if isinstance(labels, list):
                active_labels = {str(label).strip().lower() for label in labels if isinstance(label, str)}
        for label in sorted(duplicates):
            if active_labels is not None and label.lower() not in active_labels:
                continue
            self._append_issue(
                issues,
                LOCATION_PROFILES,
                MESSAGE_DEVICE_DUPLICATE.format(label=label),
                SEVERITY_ERROR,
            )
        for entry in devices:
            if isinstance(entry, dict):
                label = str(entry.get(KEY_LABEL, "")).strip()
                if active_labels is not None and label.lower() not in active_labels:
                    continue
                self._check_unknown_keys(entry, ALLOWED_DEVICE_KEYS, LOCATION_PROFILES, issues, strict)
                self._validate_device_entry(entry, issues)
                attachments = entry.get(KEY_ATTACHMENTS)
                if isinstance(attachments, list):
                    for attachment in attachments:
                        if attachment not in catalog:
                            self._append_issue(
                                issues,
                                LOCATION_PROFILES,
                                MESSAGE_MISSING_ATTACHMENT_REF.format(
                                    label=label,
                                    attachment=attachment,
                                ),
                                SEVERITY_ERROR,
                            )
        if profiles is not None and not isinstance(profiles, dict):
            self._append_issue(issues, LOCATION_PROFILES, MESSAGE_TYPE_INVALID.format(key=KEY_PROFILES), SEVERITY_ERROR)
            profiles = dict()
        if isinstance(profiles, dict):
            for profile_name, profile in profiles.items():
                if target_profile is not None and profile_name != target_profile:
                    continue
                if not isinstance(profile, dict):
                    continue
                labels = profile.get(KEY_PROFILE_DEVICES)
                if labels is None:
                    continue
                if not isinstance(labels, list):
                    self._append_issue(
                        issues,
                        LOCATION_PROFILES,
                        MESSAGE_TYPE_INVALID.format(key=KEY_PROFILE_DEVICES),
                        SEVERITY_ERROR,
                    )
                    continue
                for label in labels:
                    if label not in catalog:
                        self._append_issue(
                            issues,
                            LOCATION_PROFILES,
                            MESSAGE_MISSING_DEVICE_REF_PROFILE.format(
                                profile=profile_name,
                                label=label,
                            ),
                            SEVERITY_ERROR,
                        )
        by_profile = self._bridge_by_profile()
        for profile_name, entry in by_profile.items():
            if target_profile is not None and profile_name != target_profile:
                continue
            if profile_name not in self.profiles():
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_PROFILE_UNKNOWN.format(profile=profile_name),
                    SEVERITY_WARN,
                )
            if not isinstance(entry, dict):
                continue
            groups = entry.get(KEY_BRIDGE_GROUPS)
            if isinstance(groups, list):
                for group in groups:
                    if isinstance(group, dict):
                        self._check_unknown_keys(group, ALLOWED_GROUP_KEYS, LOCATION_PROFILES, issues, strict)
                        self._validate_group_entry(group, catalog, issues, strict)
            selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE)
            if isinstance(selected, dict):
                device_label = selected.get(KEY_DEVICE)
                if device_label and device_label not in catalog:
                    self._append_issue(
                        issues,
                        LOCATION_PROFILES,
                        MESSAGE_MISSING_DEVICE_REF.format(label=device_label),
                        SEVERITY_ERROR,
                    )

    def _validate_tests(self, issues: List[ValidationIssue], strict: bool) -> None:
        """
        NAME
            _validate_tests - Validate tests model and device references.
        """

        _ = strict
        if not self._tests_by_profile:
            return
        controller_names = self._bindings_controller_names()
        for profile_name, model in self._tests_by_profile.items():
            if model is None:
                continue
            device_catalog, duplicate_labels = self._device_catalog_for_profile(profile_name)
            result = validate_model(
                model,
                controller_names=controller_names,
                device_catalog=device_catalog,
                duplicate_labels=duplicate_labels,
            )
            for issue in result.errors:
                message = self._format_test_issue(issue)
                self._append_issue(
                    issues,
                    LOCATION_TESTS,
                    MESSAGE_TEST_PROFILE_PREFIX.format(profile=profile_name, message=message),
                    SEVERITY_ERROR,
                )
            for issue in result.warnings:
                message = self._format_test_issue(issue)
                self._append_issue(
                    issues,
                    LOCATION_TESTS,
                    MESSAGE_TEST_PROFILE_PREFIX.format(profile=profile_name, message=message),
                    SEVERITY_WARN,
                )

    def _validate_bindings(self, issues: List[ValidationIssue], strict: bool) -> None:
        """
        NAME
            _validate_bindings - Validate bindings payload.
        """

        payload = self._db.get_payload(DOC_BINDINGS)
        if not isinstance(payload, dict):
            self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_TYPE_INVALID.format(key=KEY_BINDINGS), SEVERITY_ERROR)
            return
        self._check_unknown_keys(payload, ALLOWED_BINDINGS_KEYS, LOCATION_BINDINGS, issues, strict)
        controllers = payload.get(KEY_CONTROLLERS)
        if controllers is None:
            controllers = list()
        if not isinstance(controllers, list):
            self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_TYPE_INVALID.format(key=KEY_CONTROLLERS), SEVERITY_ERROR)
            controllers = list()
        controller_names: Set[str] = set()
        for entry in controllers:
            if not isinstance(entry, dict):
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_CONTROLLER_FIELDS, SEVERITY_ERROR)
                continue
            name = entry.get(KEY_NAME)
            port = entry.get(KEY_PORT)
            if not name or not isinstance(name, str):
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_CONTROLLER_FIELDS, SEVERITY_ERROR)
                continue
            if name in controller_names:
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_CONTROLLER_DUP, SEVERITY_ERROR)
            controller_names.add(name)
            if port is None or not isinstance(port, int):
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_CONTROLLER_PORT, SEVERITY_ERROR)
        bindings = payload.get(KEY_BINDINGS)
        if bindings is None:
            bindings = list()
        if not isinstance(bindings, list):
            self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_TYPE_INVALID.format(key=KEY_BINDINGS), SEVERITY_ERROR)
            bindings = list()
        for entry in bindings:
            if not isinstance(entry, dict):
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_BINDING_FIELDS, SEVERITY_ERROR)
                continue
            if not self._binding_has_fields(entry):
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_BINDING_FIELDS, SEVERITY_ERROR)
                continue
            controller_name = entry.get(KEY_CONTROLLER)
            if controller_name not in controller_names:
                self._append_issue(
                    issues,
                    LOCATION_BINDINGS,
                    MESSAGE_BINDINGS_CONTROLLER_REQUIRED.format(name=controller_name),
                    SEVERITY_ERROR,
                )
        axes = payload.get(KEY_AXES)
        if axes is None:
            axes = list()
        if not isinstance(axes, list):
            self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_TYPE_INVALID.format(key=KEY_AXES), SEVERITY_ERROR)
            axes = list()
        for entry in axes:
            if not isinstance(entry, dict):
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_AXIS_FIELDS, SEVERITY_ERROR)
                continue
            if not self._axis_has_fields(entry):
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_AXIS_FIELDS, SEVERITY_ERROR)
                continue
            controller_name = entry.get(KEY_CONTROLLER)
            if controller_name not in controller_names:
                self._append_issue(
                    issues,
                    LOCATION_BINDINGS,
                    MESSAGE_BINDINGS_CONTROLLER_REQUIRED.format(name=controller_name),
                    SEVERITY_ERROR,
                )
            invert = entry.get(KEY_INVERT)
            if invert is not None and not isinstance(invert, bool):
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_INVERT_TYPE, SEVERITY_ERROR)
            deadband = entry.get(KEY_DEADBAND)
            if deadband is not None:
                if not isinstance(deadband, (int, float)):
                    self._append_issue(
                        issues,
                        LOCATION_BINDINGS,
                        MESSAGE_TYPE_INVALID.format(key=KEY_DEADBAND),
                        SEVERITY_ERROR,
                    )
                elif deadband < DEADBAND_MIN or deadband > DEADBAND_MAX:
                    self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_DEADBAND_RANGE, SEVERITY_ERROR)

    def _validate_mappings(self, issues: List[ValidationIssue], strict: bool) -> None:
        """
        NAME
            _validate_mappings - Validate CAN mappings payload.
        """

        payload = self._db.get_payload(DOC_MAPPINGS)
        if not isinstance(payload, dict):
            self._append_issue(issues, LOCATION_MAPPINGS, MESSAGE_TYPE_INVALID.format(key=KEY_MANUFACTURERS), SEVERITY_ERROR)
            return
        self._check_unknown_keys(payload, ALLOWED_MAPPINGS_KEYS, LOCATION_MAPPINGS, issues, strict)
        for key in (KEY_MANUFACTURERS, KEY_DEVICE_TYPES):
            mapping = payload.get(key)
            if mapping is None:
                continue
            if not isinstance(mapping, dict):
                self._append_issue(issues, LOCATION_MAPPINGS, MESSAGE_TYPE_INVALID.format(key=key), SEVERITY_ERROR)
                continue
            for map_key, map_value in mapping.items():
                if not isinstance(map_key, str) or not map_key.isdigit():
                    self._append_issue(issues, LOCATION_MAPPINGS, MESSAGE_MAPPINGS_KEY_TYPE, SEVERITY_ERROR)
                if not isinstance(map_value, str) or not map_value.strip():
                    self._append_issue(issues, LOCATION_MAPPINGS, MESSAGE_MAPPINGS_VALUE_TYPE, SEVERITY_ERROR)

    def _binding_has_fields(self, entry: Dict[str, object]) -> bool:
        """
        NAME
            _binding_has_fields - Check required binding fields.
        """

        required = (KEY_COMMAND, KEY_CONTROLLER, KEY_INPUT, KEY_ID_STR, KEY_MODE)
        for key in required:
            value = entry.get(key)
            if value is None or value == EMPTY_STRING:
                return False
        return True

    def _axis_has_fields(self, entry: Dict[str, object]) -> bool:
        """
        NAME
            _axis_has_fields - Check required axis fields.
        """

        required = (KEY_COMMAND, KEY_CONTROLLER, KEY_ID_STR)
        for key in required:
            value = entry.get(key)
            if value is None or value == EMPTY_STRING:
                return False
        return True

    def _format_test_issue(self, issue: object) -> str:
        """
        NAME
            _format_test_issue - Format a test validation issue.
        """

        name = getattr(issue, ATTR_TEST_NAME, None)
        field = getattr(issue, ATTR_FIELD, None)
        message = getattr(issue, ATTR_MESSAGE, None)
        if name and field:
            return MESSAGE_TEST_FIELD_ISSUE.format(name=name, field=field, message=message)
        if name:
            return MESSAGE_TEST_ISSUE.format(name=name, message=message)
        return MESSAGE_TEST_GENERIC.format(message=message)

    def _device_catalog_for_profile(
        self, profile_name: str
    ) -> Tuple[Dict[str, object], Set[str]]:
        """
        NAME
            _device_catalog_for_profile - Build device catalog for a profile.
        """

        catalog: Dict[str, object] = dict()
        duplicates: Set[str] = set()
        profiles = self.profiles()
        devices = self.devices()
        if not profile_name or not isinstance(profiles, dict) or not isinstance(devices, list):
            return catalog, duplicates
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            return catalog, duplicates
        labels = profile.get(KEY_PROFILE_DEVICES)
        if not isinstance(labels, list):
            return catalog, duplicates
        registry: Dict[str, Dict[str, object]] = dict()
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            label = entry.get(KEY_LABEL)
            if not isinstance(label, str) or not label:
                continue
            registry[label.lower()] = entry
        seen: Set[str] = set()
        for label in labels:
            if not isinstance(label, str):
                continue
            clean = label.strip()
            if not clean:
                continue
            key = clean.lower()
            if key in seen:
                duplicates.add(clean)
                continue
            seen.add(key)
            entry = registry.get(key)
            if entry is None:
                continue
            catalog[clean] = entry
        return catalog, duplicates

    def _build_device_catalog(
        self, devices: List[Dict[str, object]]
    ) -> Tuple[Dict[str, object], Set[str]]:
        """
        NAME
            _build_device_catalog - Build label catalog and duplicates set.
        """

        catalog: Dict[str, object] = dict()
        duplicates: Set[str] = set()
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            label = entry.get(KEY_LABEL)
            if not label or not isinstance(label, str):
                continue
            if label in catalog:
                duplicates.add(label)
                continue
            catalog[label] = entry
        return catalog, duplicates

    def _validate_device_entry(self, entry: Dict[str, object], issues: List[ValidationIssue]) -> None:
        """
        NAME
            _validate_device_entry - Validate a device definition.
        """

        label = entry.get(KEY_LABEL)
        if not label or not isinstance(label, str):
            self._append_issue(issues, LOCATION_PROFILES, MESSAGE_DEVICE_LABEL_REQUIRED, SEVERITY_ERROR)
            return
        label_text = str(label).strip()
        interface = get_device_interface(entry)
        if interface is None and entry.get(KEY_INTERFACE_LEGACY) is not None:
            entry[KEY_INTERFACE] = entry.get(KEY_INTERFACE_LEGACY)
            interface = entry.get(KEY_INTERFACE)
        if not interface:
            self._append_issue(
                issues,
                LOCATION_PROFILES,
                MESSAGE_DEVICE_INTERFACE_REQUIRED_FMT.format(label=label_text),
                SEVERITY_ERROR,
            )
            return
        if not isinstance(interface, str):
            self._append_issue(
                issues,
                LOCATION_PROFILES,
                MESSAGE_DEVICE_INTERFACE_INVALID_FMT.format(label=label_text),
                SEVERITY_ERROR,
            )
            return
        required = self._required_fields_for_interface(interface)
        for key in required:
            if entry.get(key) is None:
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_REQUIRED_FIELD_FMT.format(label=label_text, key=key),
                    SEVERITY_ERROR,
                )
        if interface == INTERFACE_CAN:
            if not isinstance(entry.get(KEY_MANUFACTURER), int):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DEVICE_MANUFACTURER_TYPE_FMT.format(label=label_text),
                    SEVERITY_ERROR,
                )
            if not isinstance(entry.get(KEY_DEVICE_TYPE), int):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DEVICE_DEVICE_TYPE_TYPE_FMT.format(label=label_text),
                    SEVERITY_ERROR,
                )
            if not isinstance(entry.get(KEY_ID), int):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DEVICE_ID_TYPE_FMT.format(label=label_text),
                    SEVERITY_ERROR,
                )
        if interface == INTERFACE_DIO:
            if entry.get(KEY_DIO) is not None and not isinstance(entry.get(KEY_DIO), int):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DEVICE_DIO_TYPE_FMT.format(label=label_text),
                    SEVERITY_ERROR,
                )
            if entry.get(KEY_INVERT) is not None and not isinstance(entry.get(KEY_INVERT), bool):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DEVICE_INVERT_TYPE_FMT.format(label=label_text),
                    SEVERITY_ERROR,
                )
        if interface == INTERFACE_PWM:
            if entry.get(KEY_PWM) is not None and not isinstance(entry.get(KEY_PWM), int):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DEVICE_PWM_TYPE_FMT.format(label=label_text),
                    SEVERITY_ERROR,
                )
        if interface == INTERFACE_ANALOG:
            if entry.get(KEY_ANALOG) is not None and not isinstance(entry.get(KEY_ANALOG), int):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DEVICE_ANALOG_TYPE_FMT.format(label=label_text),
                    SEVERITY_ERROR,
                )
        if interface not in (
            INTERFACE_CAN,
            INTERFACE_DIO,
            INTERFACE_PWM,
            INTERFACE_ANALOG,
            INTERFACE_INTERNAL,
        ):
            self._append_issue(
                issues,
                LOCATION_PROFILES,
                MESSAGE_DEVICE_INTERFACE_INVALID_FMT.format(label=label_text),
                SEVERITY_ERROR,
            )
        attachments = entry.get(KEY_ATTACHMENTS)
        if attachments is not None and not isinstance(attachments, list):
            self._append_issue(
                issues,
                LOCATION_PROFILES,
                MESSAGE_TYPE_INVALID.format(key=KEY_ATTACHMENTS),
                SEVERITY_ERROR,
            )

    def _required_fields_for_interface(self, interface: str) -> Tuple[str, ...]:
        """
        NAME
            _required_fields_for_interface - Return required fields tuple.
        """

        if interface == INTERFACE_CAN:
            return DEVICE_REQUIRED_CAN
        if interface == INTERFACE_DIO:
            return DEVICE_REQUIRED_DIO
        if interface == INTERFACE_PWM:
            return DEVICE_REQUIRED_PWM
        if interface == INTERFACE_ANALOG:
            return DEVICE_REQUIRED_ANALOG
        if interface == INTERFACE_INTERNAL:
            return DEVICE_REQUIRED_INTERNAL
        return DEVICE_REQUIRED_INTERNAL

    def _validate_group_entry(
        self,
        group: Dict[str, object],
        catalog: Dict[str, object],
        issues: List[ValidationIssue],
        strict: bool,
    ) -> None:
        """
        NAME
            _validate_group_entry - Validate group member references.
        """

        members = group.get(KEY_MEMBERS)
        if not isinstance(members, list):
            return
        for member in members:
            if isinstance(member, dict):
                self._check_unknown_keys(member, ALLOWED_MEMBER_KEYS, LOCATION_PROFILES, issues, strict)
                label = member.get(KEY_DEVICE)
            else:
                label = member
            if label not in catalog:
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_MISSING_DEVICE_REF.format(label=label),
                    SEVERITY_ERROR,
                )

    def _bindings_controller_names(self) -> Optional[Set[str]]:
        """
        NAME
            _bindings_controller_names - Build controller name set.
        """

        payload = self._db.get_payload(DOC_BINDINGS)
        if not isinstance(payload, dict):
            return None
        controllers = payload.get(KEY_CONTROLLERS)
        if not isinstance(controllers, list):
            return None
        names: Set[str] = set()
        for entry in controllers:
            if isinstance(entry, dict):
                name = entry.get(KEY_NAME)
                if isinstance(name, str) and name:
                    names.add(name)
        return names

    def _append_issue(
        self,
        issues: List[ValidationIssue],
        location: str,
        message: str,
        severity: str,
    ) -> None:
        """
        NAME
            _append_issue - Append a validation issue.
        """

        issues.append(ValidationIssue(location=location, message=message, severity=severity))

    def _check_unknown_keys(
        self,
        payload: Dict[str, object],
        allowed: Set[str],
        location: str,
        issues: List[ValidationIssue],
        strict: bool,
    ) -> None:
        """
        NAME
            _check_unknown_keys - Validate payload keys against allowed set.
        """

        if not isinstance(payload, dict):
            return
        for key in payload.keys():
            if key not in allowed:
                severity = SEVERITY_ERROR if strict else SEVERITY_WARN
                self._append_issue(
                    issues,
                    location,
                    MESSAGE_UNKNOWN_KEY.format(key=key),
                    severity,
                )

