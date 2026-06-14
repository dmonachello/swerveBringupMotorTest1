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

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from tools.common.config_api.repository import ConfigRepository
from tools.common.bridge_config_io import default_bridge_config
from tools.common.json_io import write_json
from tools.common.paths import repo_root as repo_root_path
from tools.common.profile_io import compute_profiles_hash
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
    KEY_BRIDGE_BINDINGS,
    KEY_BUS,
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DEFAULT_PROFILE,
    KEY_DSL_TESTS,
    KEY_DIAGRAM,
    KEY_DEVICE,
    KEY_DEVICE_REF,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_FROM_NODE,
    KEY_ID,
    KEY_INTERFACE,
    KEY_INVERT,
    KEY_LABEL,
    KEY_LIMITS,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_NODE_KEY,
    KEY_OBJECT_TYPE,
    KEY_NOTES,
    KEY_INPUT_ALIASES,
    KEY_PROFILE_DEVICES,
    KEY_PROFILES,
    KEY_PWM,
    KEY_ROLE,
    KEY_SCHEMA_VERSION,
    KEY_TOPOLOGY_VERSION,
    KEY_TOPOLOGY,
    KEY_TOPOLOGY_EDGES,
    KEY_TOPOLOGY_NODES,
    KEY_TOPOLOGY_PROFILES,
    KEY_TO_NODE,
    KEY_TAGS,
    KEY_TERMINATOR,
    KEY_TYPE,
    KEY_VENDOR,
    INTERFACE_ANALOG,
    INTERFACE_CAN,
    INTERFACE_DIO,
    INTERFACE_INTERNAL,
    INTERFACE_PWM,
    INTERFACE_USB,
    PROFILE_SCHEMA_VERSION,
    TYPE_XBOX_CONTROLLER,
    get_device_interface,
    get_group_member_label,
    get_object_type,
    make_group_member,
)
from tools.common.test_authoring import (
    TestAuthoringModel,
    model_from_payload,
    model_to_payload,
    validate_model,
)
from tools.common.test_authoring.validator import AXIS_INPUTS, BUTTON_INPUTS
from tools.common.topology_validate import (
    ISSUE_DEVICE_REF_REQUIRED,
    ISSUE_DEVICE_REF_UNKNOWN,
    SEVERITY_ERROR as TOPOLOGY_SEVERITY_ERROR,
    validate_topology_profile,
)
from tools.config.json_store import JsonStore


KEY_TESTS = "tests"
KEY_TEST_SETS = "test_sets"
KEY_DEFAULT_TEST_SET = "default_test_set"
KEY_CONTROLLERS = "controllers"
KEY_BINDINGS = "bindings"
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
INPUT_KIND_BUTTON = "button"
INPUT_KIND_DPAD = "dpad"
INPUT_KIND_COMBO = "combo"
INPUT_KIND_AXIS = "axis"
MODE_ANALOG = "analog"
DPAD_INPUTS = {"UP", "RIGHT", "DOWN", "LEFT"}
BINDINGS_EMPTY_PAYLOAD = {
    KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
    KEY_CONTROLLERS: list(),
    KEY_BINDINGS: list(),
    KEY_INPUT_ALIASES: dict(),
}

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
MESSAGE_DEVICE_INVERT_REQUIRED = "Device invert is required."
MESSAGE_DEVICE_PWM_REQUIRED = "Device pwm is required."
MESSAGE_DEVICE_ANALOG_REQUIRED = "Device analog is required."
MESSAGE_DEVICE_MANUFACTURER_TYPE = "Device manufacturer must be int."
MESSAGE_DEVICE_DEVICE_TYPE_TYPE = "Device deviceType must be int."
MESSAGE_DEVICE_ID_TYPE = "Device id must be int."
MESSAGE_DEVICE_INVERT_TYPE = "Device invert must be bool."
MESSAGE_DEVICE_PWM_TYPE = "Device pwm must be int."
MESSAGE_DEVICE_ANALOG_TYPE = "Device analog must be int."
MESSAGE_DEVICE_MANUFACTURER_TYPE_FMT = "Device {label}: manufacturer must be int."
MESSAGE_DEVICE_DEVICE_TYPE_TYPE_FMT = "Device {label}: deviceType must be int."
MESSAGE_DEVICE_ID_TYPE_FMT = "Device {label}: id must be int."
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
MESSAGE_BINDINGS_INVERT_TYPE = "Axis invert must be bool."
MESSAGE_BINDINGS_DEADBAND_RANGE = "Axis deadband must be 0.0 to 1.0."
MESSAGE_BINDINGS_INPUT_KIND = "Binding input kind is invalid."
MESSAGE_BINDINGS_AXIS_MODE = "Axis bindings must use mode=analog."
MESSAGE_BINDINGS_AXIS_FIELDS = "Axis binding entry missing required fields."
MESSAGE_BINDINGS_AXIS_EXTRAS = "Axis bindings require invert and deadband."
MESSAGE_BINDINGS_NON_AXIS_EXTRAS = "Only axis bindings may define invert or deadband."
MESSAGE_BINDINGS_ID_INVALID = "Binding id is invalid for input kind."
MESSAGE_BINDINGS_SCHEMA_VERSION = "schema_version mismatch: expected {expected}, got {found}"
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
DEVICE_REQUIRED_DIO = (KEY_INTERFACE, KEY_ID, KEY_INVERT)
DEVICE_REQUIRED_PWM = (KEY_INTERFACE, KEY_PWM)
DEVICE_REQUIRED_ANALOG = (KEY_INTERFACE, KEY_ANALOG)
DEVICE_REQUIRED_INTERNAL = (KEY_INTERFACE,)
DEVICE_REQUIRED_USB = (KEY_INTERFACE, KEY_ID)

ALLOWED_ROOT_KEYS = {
    KEY_SCHEMA_VERSION,
    KEY_DATA_VERSION,
    KEY_DATA_HASH,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICES,
    KEY_PROFILES,
    KEY_DSL_TESTS,
    KEY_BRIDGE_CONFIG,
    KEY_DIAGRAM,
    KEY_TOPOLOGY,
}
ALLOWED_TESTS_KEYS = {KEY_DEFAULT_TEST_SET, KEY_TEST_SETS, KEY_TESTS}
ALLOWED_BINDINGS_KEYS = {KEY_SCHEMA_VERSION, KEY_CONTROLLERS, KEY_BINDINGS, KEY_INPUT_ALIASES}
ALLOWED_MAPPINGS_KEYS = {KEY_MANUFACTURERS, KEY_DEVICE_TYPES}
ALLOWED_DEVICE_KEYS = {
    KEY_LABEL,
    KEY_INTERFACE,
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
    KEY_INVERT,
    KEY_PWM,
    KEY_ANALOG,
    KEY_ATTACHMENTS,
}
ALLOWED_GROUP_KEYS = {KEY_NAME, KEY_ENABLED, KEY_MEMBERS, KEY_BINDINGS}
ALLOWED_MEMBER_KEYS = {KEY_LABEL, KEY_DEVICE, KEY_ENABLED}

COUNT_ZERO = 0
COUNT_ONE = 1
COUNT_TWO = 2
DEADBAND_MIN = 0.0
DEADBAND_MAX = 1.0
EMPTY_STRING = ""
BOOL_TRUE = True
BOOL_FALSE = False
KEY_DIAGRAM_PROFILES = "profiles"
KEY_DIAGRAM_NODES = "nodes"
KEY_NODE_TYPE = "nodeType"
NODE_TYPE_DEVICE = "device"
MESSAGE_DEVICE_LABEL_DUPLICATE_CASEFOLD = "Duplicate device label: {label}"
MESSAGE_DIAGRAM_NODE_DEVICE_LABEL_REQUIRED = (
    "Profile {profile} diagram node {key}: device label is required."
)
MESSAGE_DIAGRAM_NODE_DEVICE_UNKNOWN = (
    "Profile {profile} diagram node {key}: device label not found: {label}"
)
MESSAGE_DIAGRAM_NODE_DEVICE_ID_FORBIDDEN = (
    "Profile {profile} diagram node {key}: device id is not allowed: {label}"
)
MESSAGE_TOPOLOGY_NODE_DEVICE_REF_REQUIRED = (
    "Profile {profile} topology node {key}: deviceRef is required."
)
MESSAGE_TOPOLOGY_NODE_DEVICE_UNKNOWN = (
    "Profile {profile} topology node {key}: deviceRef not found: {label}"
)
MESSAGE_PROFILE_DEVICES_TYPE_INVALID = "Profile {profile}: Invalid type for devices"
MESSAGE_SALVAGE_PAYLOAD_RESET = "Dropped invalid {section} payload; starting empty."
MESSAGE_SALVAGE_DEVICE_DROPPED = "Dropped invalid device '{label}': {reason}"
MESSAGE_SALVAGE_DEVICE_DROPPED_INDEX = "Dropped invalid device at index {index}: {reason}"
MESSAGE_SALVAGE_PROFILE_DROPPED = "Dropped invalid profile '{profile}': {reason}"
MESSAGE_SALVAGE_PROFILE_DEVICE_REF = "Dropped missing device '{label}' from profile '{profile}'."
MESSAGE_SALVAGE_DEFAULT_PROFILE = "Dropped invalid default profile '{profile}'."
MESSAGE_SALVAGE_GROUP_DROPPED = "Dropped invalid group in profile '{profile}': {reason}"
MESSAGE_SALVAGE_GROUP_MEMBER_DROPPED = (
    "Dropped invalid group member '{label}' in profile '{profile}' group '{group}'."
)
MESSAGE_SALVAGE_SELECTED_DEVICE_RESET = (
    "Dropped invalid selected device '{label}' in profile '{profile}'."
)
MESSAGE_SALVAGE_TESTS_DROPPED = "Dropped invalid tests payload in profile '{profile}'."
MESSAGE_SALVAGE_TOPOLOGY_PROFILE_DROPPED = "Dropped invalid topology profile '{profile}'."
MESSAGE_SALVAGE_TOPOLOGY_NODE_DROPPED = (
    "Dropped invalid topology node in profile '{profile}' with key '{key}'."
)
MESSAGE_SALVAGE_DIAGRAM_PROFILE_DROPPED = "Dropped invalid diagram profile '{profile}'."
MESSAGE_SALVAGE_DIAGRAM_NODE_DROPPED = (
    "Dropped invalid diagram node in profile '{profile}' with key '{key}'."
)
MESSAGE_SALVAGE_BINDINGS_CONTROLLER_DROPPED = (
    "Dropped invalid controller '{name}': {reason}"
)
MESSAGE_SALVAGE_BINDINGS_BINDING_DROPPED = "Dropped invalid binding at index {index}: {reason}"
MESSAGE_SALVAGE_BINDINGS_AXIS_DROPPED = "Dropped invalid binding at index {index}: {reason}"
MESSAGE_SALVAGE_MAPPINGS_ENTRY_DROPPED = (
    "Dropped invalid {section} mapping '{key}': {reason}"
)

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
        self._config_repository = ConfigRepository()
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
        session = self._config_repository.session_for_payload(Path(path), payload)
        target = Path(path).resolve()
        canonical = self._config_repository.canonical_path().resolve()
        deploy = self._config_repository.deploy_path().resolve()
        if target == canonical or target == deploy:
            self._config_repository.sync(session)
        else:
            self._config_repository.save(session, path=Path(path))

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

        return self._config_repository.canonical_path()

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
        payload = self._config_repository.load_path(path).to_payload()
        sanitized, warnings, _changed = self.sanitize_profiles_payload(payload)
        self._warnings.extend(warnings)
        self._db.set_payload(DOC_PROFILES, sanitized)
        return sanitized

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
            KEY_TOPOLOGY: {
                KEY_TOPOLOGY_VERSION: COUNT_ONE,
                KEY_TOPOLOGY_PROFILES: dict(),
            },
            KEY_BRIDGE_CONFIG: {
                KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
                KEY_BRIDGE_GENERATED_AT: None,
                KEY_BRIDGE_BY_PROFILE: dict(),
            },
        }

    def sanitize_profiles_payload(
        self, payload: object
    ) -> Tuple[Dict[str, object], List[str], bool]:
        """
        NAME
            sanitize_profiles_payload - Retain valid profile config and drop bad portions.
        """

        warnings: List[str] = list()
        changed = BOOL_FALSE
        if not isinstance(payload, dict):
            warnings.append(
                MESSAGE_SALVAGE_PAYLOAD_RESET.format(section=DOC_PROFILES)
            )
            return self._default_profiles_payload(), warnings, BOOL_TRUE
        sanitized = deepcopy(payload)
        base = self._default_profiles_payload()
        for key, value in base.items():
            sanitized.setdefault(key, deepcopy(value))
        self._ensure_bridge_config(sanitized)
        devices_input = sanitized.get(KEY_DEVICES)
        profiles_input = sanitized.get(KEY_PROFILES)
        valid_devices: List[Dict[str, object]] = list()
        valid_labels: Set[str] = set()
        if not isinstance(devices_input, list):
            devices_input = list()
            warnings.append(
                MESSAGE_SALVAGE_PAYLOAD_RESET.format(section=KEY_DEVICES)
            )
            changed = BOOL_TRUE
        for index, entry in enumerate(devices_input):
            if not isinstance(entry, dict):
                warnings.append(
                    MESSAGE_SALVAGE_DEVICE_DROPPED_INDEX.format(
                        index=index, reason=MESSAGE_TYPE_INVALID.format(key=KEY_DEVICE)
                    )
                )
                changed = BOOL_TRUE
                continue
            candidate = {
                key: value
                for key, value in entry.items()
                if key in ALLOWED_DEVICE_KEYS
            }
            label = str(candidate.get(KEY_LABEL, EMPTY_STRING)).strip()
            if not label:
                warnings.append(
                    MESSAGE_SALVAGE_DEVICE_DROPPED_INDEX.format(
                        index=index, reason=MESSAGE_DEVICE_LABEL_REQUIRED
                    )
                )
                changed = BOOL_TRUE
                continue
            folded = label.casefold()
            if folded in valid_labels:
                warnings.append(
                    MESSAGE_SALVAGE_DEVICE_DROPPED.format(
                        label=label, reason=MESSAGE_DEVICE_DUPLICATE.format(label=label)
                    )
                )
                changed = BOOL_TRUE
                continue
            interface = get_device_interface(candidate)
            if not isinstance(interface, str) or not interface.strip():
                warnings.append(
                    MESSAGE_SALVAGE_DEVICE_DROPPED.format(
                        label=label, reason=MESSAGE_DEVICE_INTERFACE_REQUIRED_FMT.format(label=label)
                    )
                )
                changed = BOOL_TRUE
                continue
            required = self._required_fields_for_interface(interface)
            if required is None:
                warnings.append(
                    MESSAGE_SALVAGE_DEVICE_DROPPED.format(
                        label=label, reason=MESSAGE_DEVICE_INTERFACE_INVALID_FMT.format(label=label)
                    )
                )
                changed = BOOL_TRUE
                continue
            invalid_reason = self._device_salvage_error(candidate, label, required)
            if invalid_reason is not None:
                warnings.append(
                    MESSAGE_SALVAGE_DEVICE_DROPPED.format(label=label, reason=invalid_reason)
                )
                changed = BOOL_TRUE
                continue
            valid_labels.add(folded)
            valid_devices.append(candidate)
        sanitized[KEY_DEVICES] = valid_devices
        valid_device_names = {entry[KEY_LABEL] for entry in valid_devices if KEY_LABEL in entry}
        valid_profiles: Dict[str, Dict[str, object]] = dict()
        if not isinstance(profiles_input, dict):
            profiles_input = dict()
            warnings.append(
                MESSAGE_SALVAGE_PAYLOAD_RESET.format(section=KEY_PROFILES)
            )
            changed = BOOL_TRUE
        for profile_name, entry in profiles_input.items():
            if not isinstance(profile_name, str) or not profile_name.strip():
                changed = BOOL_TRUE
                continue
            if not isinstance(entry, dict):
                warnings.append(
                    MESSAGE_SALVAGE_PROFILE_DROPPED.format(
                        profile=profile_name,
                        reason=MESSAGE_TYPE_INVALID.format(key=KEY_PROFILE),
                    )
                )
                changed = BOOL_TRUE
                continue
            profile_entry = dict(entry)
            labels = profile_entry.get(KEY_PROFILE_DEVICES)
            if not isinstance(labels, list):
                warnings.append(
                    MESSAGE_SALVAGE_PROFILE_DROPPED.format(
                        profile=profile_name,
                        reason=MESSAGE_PROFILE_DEVICES_TYPE_INVALID.format(profile=profile_name),
                    )
                )
                changed = BOOL_TRUE
                continue
            kept_labels: List[str] = list()
            seen_labels: Set[str] = set()
            for raw_label in labels:
                if not isinstance(raw_label, str):
                    changed = BOOL_TRUE
                    continue
                label = raw_label.strip()
                if not label:
                    changed = BOOL_TRUE
                    continue
                folded = label.casefold()
                if folded in seen_labels:
                    changed = BOOL_TRUE
                    continue
                seen_labels.add(folded)
                if label not in valid_device_names:
                    warnings.append(
                        MESSAGE_SALVAGE_PROFILE_DEVICE_REF.format(
                            label=label, profile=profile_name
                        )
                    )
                    changed = BOOL_TRUE
                    continue
                kept_labels.append(label)
            profile_entry[KEY_PROFILE_DEVICES] = kept_labels
            valid_profiles[profile_name] = profile_entry
        sanitized[KEY_PROFILES] = valid_profiles
        default_profile = sanitized.get(KEY_DEFAULT_PROFILE)
        if not isinstance(default_profile, str) or default_profile not in valid_profiles:
            if isinstance(default_profile, str) and default_profile.strip():
                warnings.append(
                    MESSAGE_SALVAGE_DEFAULT_PROFILE.format(profile=default_profile)
                )
            sanitized[KEY_DEFAULT_PROFILE] = (
                next(iter(valid_profiles.keys())) if valid_profiles else EMPTY_STRING
            )
            changed = BOOL_TRUE
        bridge = sanitized.get(KEY_BRIDGE_CONFIG)
        if not isinstance(bridge, dict):
            bridge = deepcopy(base[KEY_BRIDGE_CONFIG])
            sanitized[KEY_BRIDGE_CONFIG] = bridge
            changed = BOOL_TRUE
        self._ensure_bridge_config(sanitized)
        by_profile = bridge.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            by_profile = dict()
            bridge[KEY_BRIDGE_BY_PROFILE] = by_profile
            changed = BOOL_TRUE
        valid_bridge: Dict[str, Dict[str, object]] = dict()
        for profile_name in valid_profiles.keys():
            entry = by_profile.get(profile_name)
            if not isinstance(entry, dict):
                entry = dict()
                changed = BOOL_TRUE
            profile_entry = dict(entry)
            valid_object_labels = self._profile_object_label_set_from_payload(sanitized, profile_name)
            profile_entry[KEY_BRIDGE_GROUPS], groups_changed, group_warnings = self._sanitize_groups_payload(
                profile_name,
                profile_entry.get(KEY_BRIDGE_GROUPS),
                valid_object_labels,
            )
            if groups_changed:
                changed = BOOL_TRUE
            warnings.extend(group_warnings)
            selected = profile_entry.get(KEY_BRIDGE_SELECTED_DEVICE)
            if not isinstance(selected, dict):
                selected = {KEY_DEVICE: EMPTY_STRING, KEY_ENABLED: BOOL_FALSE}
                changed = BOOL_TRUE
            selected_label = selected.get(KEY_DEVICE)
            if not isinstance(selected_label, str) or selected_label not in valid_profiles.get(profile_name, {}).get(KEY_PROFILE_DEVICES, []):
                if isinstance(selected_label, str) and selected_label.strip():
                    warnings.append(
                        MESSAGE_SALVAGE_SELECTED_DEVICE_RESET.format(
                            label=selected_label, profile=profile_name
                        )
                    )
                selected = {KEY_DEVICE: EMPTY_STRING, KEY_ENABLED: BOOL_FALSE}
                changed = BOOL_TRUE
            else:
                selected = {
                    KEY_DEVICE: selected_label,
                    KEY_ENABLED: bool(selected.get(KEY_ENABLED)),
                }
            profile_entry[KEY_BRIDGE_SELECTED_DEVICE] = selected
            tests_payload = profile_entry.get(KEY_BRIDGE_TESTS)
            if isinstance(tests_payload, dict):
                try:
                    profile_entry[KEY_BRIDGE_TESTS] = model_to_payload(
                        model_from_payload(tests_payload)
                    )
                except Exception:
                    profile_entry.pop(KEY_BRIDGE_TESTS, None)
                    warnings.append(
                        MESSAGE_SALVAGE_TESTS_DROPPED.format(profile=profile_name)
                    )
                    changed = BOOL_TRUE
            elif KEY_BRIDGE_TESTS in profile_entry:
                profile_entry.pop(KEY_BRIDGE_TESTS, None)
                warnings.append(
                    MESSAGE_SALVAGE_TESTS_DROPPED.format(profile=profile_name)
                )
                changed = BOOL_TRUE
            valid_bridge[profile_name] = profile_entry
        bridge[KEY_BRIDGE_BY_PROFILE] = valid_bridge
        topology_changed, topology_warnings = self._sanitize_topology_payload(
            sanitized, valid_device_names, set(valid_profiles.keys())
        )
        if topology_changed:
            changed = BOOL_TRUE
        warnings.extend(topology_warnings)
        diagram_changed, diagram_warnings = self._sanitize_diagram_payload(
            sanitized, valid_device_names, set(valid_profiles.keys())
        )
        if diagram_changed:
            changed = BOOL_TRUE
        warnings.extend(diagram_warnings)
        if not isinstance(sanitized.get(KEY_SCHEMA_VERSION), int):
            sanitized[KEY_SCHEMA_VERSION] = PROFILE_SCHEMA_VERSION
            changed = BOOL_TRUE
        if not isinstance(sanitized.get(KEY_DATA_VERSION), str):
            sanitized[KEY_DATA_VERSION] = EMPTY_STRING
            changed = BOOL_TRUE
        computed_hash = compute_profiles_hash(sanitized)
        if sanitized.get(KEY_DATA_HASH) != computed_hash:
            sanitized[KEY_DATA_HASH] = computed_hash
            changed = BOOL_TRUE
        changed = BOOL_TRUE if sanitized != payload else BOOL_FALSE
        return sanitized, warnings, changed

    def sanitize_bindings_payload(
        self, payload: object
    ) -> Tuple[Dict[str, object], List[str], bool]:
        """
        NAME
            sanitize_bindings_payload - Retain valid controller bindings and drop bad entries.
        """

        warnings: List[str] = list()
        changed = BOOL_FALSE
        sanitized = deepcopy(BINDINGS_EMPTY_PAYLOAD)
        if not isinstance(payload, dict):
            warnings.append(
                MESSAGE_SALVAGE_PAYLOAD_RESET.format(section=DOC_BINDINGS)
            )
            return sanitized, warnings, BOOL_TRUE
        controllers_in = payload.get(KEY_CONTROLLERS)
        bindings_in = payload.get(KEY_BINDINGS)
        aliases_in = payload.get(KEY_INPUT_ALIASES)
        if not isinstance(controllers_in, list):
            controllers_in = list()
            changed = BOOL_TRUE
        if not isinstance(bindings_in, list):
            bindings_in = list()
            changed = BOOL_TRUE
        if "axes" in payload:
            changed = BOOL_TRUE
        valid_controllers: List[Dict[str, object]] = list()
        known_controller_names: Set[str] = {
            name.casefold() for name in self._profile_controller_names()
        }
        legacy_controller_names: Set[str] = set()
        for entry in controllers_in:
            if not isinstance(entry, dict):
                changed = BOOL_TRUE
                continue
            name = str(entry.get(KEY_NAME, EMPTY_STRING)).strip()
            ctrl_type = str(entry.get(KEY_TYPE, EMPTY_STRING)).strip()
            port = entry.get(KEY_PORT)
            if not name or not ctrl_type or not isinstance(port, int):
                warnings.append(
                    MESSAGE_SALVAGE_BINDINGS_CONTROLLER_DROPPED.format(
                        name=name or EMPTY_STRING,
                        reason=MESSAGE_BINDINGS_CONTROLLER_FIELDS,
                    )
                )
                changed = BOOL_TRUE
                continue
            folded = name.casefold()
            if folded in legacy_controller_names:
                warnings.append(
                    MESSAGE_SALVAGE_BINDINGS_CONTROLLER_DROPPED.format(
                        name=name, reason=MESSAGE_BINDINGS_CONTROLLER_DUP
                    )
                )
                changed = BOOL_TRUE
                continue
            legacy_controller_names.add(folded)
            known_controller_names.add(folded)
            valid_controllers.append({KEY_NAME: name, KEY_TYPE: ctrl_type, KEY_PORT: port})
        valid_bindings: List[Dict[str, object]] = list()
        sanitized[KEY_CONTROLLERS] = valid_controllers
        for index, entry in enumerate(bindings_in):
            if not isinstance(entry, dict):
                changed = BOOL_TRUE
                continue
            normalized, reason = self._sanitize_binding_entry(entry, known_controller_names)
            if normalized is None:
                warnings.append(
                    MESSAGE_SALVAGE_BINDINGS_BINDING_DROPPED.format(
                        index=index,
                        reason=reason,
                    )
                )
                changed = BOOL_TRUE
                continue
            valid_bindings.append(normalized)
        sanitized[KEY_BINDINGS] = valid_bindings
        sanitized[KEY_INPUT_ALIASES] = aliases_in if isinstance(aliases_in, dict) else dict()
        if not isinstance(aliases_in, dict) and aliases_in is not None:
            changed = BOOL_TRUE
        if sanitized.get(KEY_SCHEMA_VERSION) != PROFILE_SCHEMA_VERSION:
            sanitized[KEY_SCHEMA_VERSION] = PROFILE_SCHEMA_VERSION
            changed = BOOL_TRUE
        return sanitized, warnings, changed

    def sanitize_mappings_payload(
        self, payload: object
    ) -> Tuple[Dict[str, object], List[str], bool]:
        """
        NAME
            sanitize_mappings_payload - Retain valid CAN mappings and drop bad entries.
        """

        warnings: List[str] = list()
        changed = BOOL_FALSE
        sanitized = {
            KEY_MANUFACTURERS: dict(),
            KEY_DEVICE_TYPES: dict(),
        }
        if not isinstance(payload, dict):
            warnings.append(
                MESSAGE_SALVAGE_PAYLOAD_RESET.format(section=DOC_MAPPINGS)
            )
            return sanitized, warnings, BOOL_TRUE
        for section in (KEY_MANUFACTURERS, KEY_DEVICE_TYPES):
            entries = payload.get(section)
            if not isinstance(entries, dict):
                changed = BOOL_TRUE
                continue
            kept: Dict[str, str] = dict()
            for key, value in entries.items():
                key_str = str(key).strip()
                value_str = str(value).strip() if isinstance(value, str) else EMPTY_STRING
                if not key_str.isdigit():
                    warnings.append(
                        MESSAGE_SALVAGE_MAPPINGS_ENTRY_DROPPED.format(
                            section=section, key=key_str, reason=MESSAGE_MAPPINGS_KEY_TYPE
                        )
                    )
                    changed = BOOL_TRUE
                    continue
                if not value_str:
                    warnings.append(
                        MESSAGE_SALVAGE_MAPPINGS_ENTRY_DROPPED.format(
                            section=section, key=key_str, reason=MESSAGE_MAPPINGS_VALUE_TYPE
                        )
                    )
                    changed = BOOL_TRUE
                    continue
                kept[key_str] = value_str
            sanitized[section] = kept
        return sanitized, warnings, changed

    def _ensure_bridge_config(self, payload: Dict[str, object]) -> None:
        """
        NAME
            _ensure_bridge_config - Ensure bridgeConfig structure exists.
        """

        bridge = payload.get(KEY_BRIDGE_CONFIG)
        if not isinstance(bridge, dict):
            bridge = default_bridge_config()
            payload[KEY_BRIDGE_CONFIG] = bridge
        if KEY_BRIDGE_SCHEMA_VERSION not in bridge:
            bridge[KEY_BRIDGE_SCHEMA_VERSION] = BRIDGE_CONFIG_SCHEMA_VERSION
        if KEY_BRIDGE_GENERATED_AT not in bridge:
            bridge[KEY_BRIDGE_GENERATED_AT] = None
        if KEY_BRIDGE_BY_PROFILE not in bridge or not isinstance(
            bridge.get(KEY_BRIDGE_BY_PROFILE), dict
        ):
            bridge[KEY_BRIDGE_BY_PROFILE] = dict()

    def _required_fields_for_interface(self, interface: object) -> Optional[Tuple[str, ...]]:
        """
        NAME
            _required_fields_for_interface - Return required fields for a device interface.
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
        if interface == INTERFACE_USB:
            return DEVICE_REQUIRED_USB
        return None

    def _device_salvage_error(
        self, entry: Dict[str, object], label: str, required: Tuple[str, ...]
    ) -> Optional[str]:
        """
        NAME
            _device_salvage_error - Return salvage failure reason for a device entry.
        """

        for field in required:
            if field not in entry:
                return MESSAGE_REQUIRED_FIELD_FMT.format(label=label, key=field)
        if KEY_MANUFACTURER in required and not isinstance(entry.get(KEY_MANUFACTURER), int):
            return MESSAGE_DEVICE_MANUFACTURER_TYPE_FMT.format(label=label)
        if KEY_DEVICE_TYPE in required and not isinstance(entry.get(KEY_DEVICE_TYPE), int):
            return MESSAGE_DEVICE_DEVICE_TYPE_TYPE_FMT.format(label=label)
        if KEY_ID in required and not isinstance(entry.get(KEY_ID), int):
            return MESSAGE_DEVICE_ID_TYPE_FMT.format(label=label)
        if KEY_INVERT in required and not isinstance(entry.get(KEY_INVERT), bool):
            return MESSAGE_DEVICE_INVERT_TYPE_FMT.format(label=label)
        if KEY_PWM in required and not isinstance(entry.get(KEY_PWM), int):
            return MESSAGE_DEVICE_PWM_TYPE_FMT.format(label=label)
        if KEY_ANALOG in required and not isinstance(entry.get(KEY_ANALOG), int):
            return MESSAGE_DEVICE_ANALOG_TYPE_FMT.format(label=label)
        return None

    def _sanitize_groups_payload(
        self, profile_name: str, groups_payload: object, valid_labels: Set[str]
    ) -> Tuple[List[Dict[str, object]], bool, List[str]]:
        """
        NAME
            _sanitize_groups_payload - Retain valid groups and drop bad members.
        """

        warnings: List[str] = list()
        changed = BOOL_FALSE
        if not isinstance(groups_payload, list):
            return list(), BOOL_TRUE, warnings
        groups: List[Dict[str, object]] = list()
        for entry in groups_payload:
            if not isinstance(entry, dict):
                changed = BOOL_TRUE
                continue
            name = str(entry.get(KEY_NAME, EMPTY_STRING)).strip()
            if not name:
                warnings.append(
                    MESSAGE_SALVAGE_GROUP_DROPPED.format(
                        profile=profile_name, reason=MESSAGE_REQUIRED_FIELD.format(key=KEY_NAME)
                    )
                )
                changed = BOOL_TRUE
                continue
            members_payload = entry.get(KEY_MEMBERS)
            if not isinstance(members_payload, list):
                warnings.append(
                    MESSAGE_SALVAGE_GROUP_DROPPED.format(
                        profile=profile_name, reason=MESSAGE_REQUIRED_FIELD.format(key=KEY_MEMBERS)
                    )
                )
                changed = BOOL_TRUE
                continue
            kept_members: List[Dict[str, object]] = list()
            for member in members_payload:
                if not isinstance(member, dict):
                    changed = BOOL_TRUE
                    continue
                label = get_group_member_label(member)
                if not label or label.casefold() not in valid_labels:
                    warnings.append(
                        MESSAGE_SALVAGE_GROUP_MEMBER_DROPPED.format(
                            label=str(label or EMPTY_STRING),
                            profile=profile_name,
                            group=name,
                        )
                    )
                    changed = BOOL_TRUE
                    continue
                kept_members.append(make_group_member(label, bool(member.get(KEY_ENABLED))))
            groups.append(
                {
                    KEY_NAME: name,
                    KEY_ENABLED: bool(entry.get(KEY_ENABLED)),
                    KEY_MEMBERS: kept_members,
                    KEY_BRIDGE_BINDINGS: entry.get(KEY_BRIDGE_BINDINGS, [])
                    if isinstance(entry.get(KEY_BRIDGE_BINDINGS), list)
                    else [],
                }
            )
        return groups, changed, warnings

    def _sanitize_topology_payload(
        self,
        payload: Dict[str, object],
        valid_device_names: Set[str],
        valid_profiles: Set[str],
    ) -> Tuple[bool, List[str]]:
        """
        NAME
            _sanitize_topology_payload - Drop invalid topology profiles and device nodes.
        """

        warnings: List[str] = list()
        changed = BOOL_FALSE
        topology = payload.get(KEY_TOPOLOGY)
        if topology is None:
            return changed, warnings
        if not isinstance(topology, dict):
            payload[KEY_TOPOLOGY] = {
                KEY_TOPOLOGY_VERSION: COUNT_ONE,
                KEY_TOPOLOGY_PROFILES: dict(),
            }
            warnings.append(
                MESSAGE_SALVAGE_PAYLOAD_RESET.format(section=KEY_TOPOLOGY)
            )
            return BOOL_TRUE, warnings
        profiles = topology.get(KEY_TOPOLOGY_PROFILES)
        if not isinstance(profiles, dict):
            topology[KEY_TOPOLOGY_PROFILES] = dict()
            return BOOL_TRUE, warnings
        kept_profiles: Dict[str, Dict[str, object]] = dict()
        for profile_name, entry in profiles.items():
            if profile_name not in valid_profiles or not isinstance(entry, dict):
                warnings.append(
                    MESSAGE_SALVAGE_TOPOLOGY_PROFILE_DROPPED.format(profile=profile_name)
                )
                changed = BOOL_TRUE
                continue
            nodes = entry.get(KEY_TOPOLOGY_NODES)
            if not isinstance(nodes, list):
                warnings.append(
                    MESSAGE_SALVAGE_TOPOLOGY_PROFILE_DROPPED.format(profile=profile_name)
                )
                changed = BOOL_TRUE
                continue
            kept_nodes: List[Dict[str, object]] = list()
            kept_keys: Set[object] = set()
            for node in nodes:
                if not isinstance(node, dict):
                    changed = BOOL_TRUE
                    continue
                node_key = node.get(KEY_NODE_KEY)
                node_type = get_object_type(node)
                if node_type == NODE_TYPE_DEVICE:
                    device_ref = node.get(KEY_DEVICE_REF)
                    if not isinstance(device_ref, str) or device_ref not in valid_device_names:
                        warnings.append(
                            MESSAGE_SALVAGE_TOPOLOGY_NODE_DROPPED.format(
                                profile=profile_name,
                                key=node_key,
                            )
                        )
                        changed = BOOL_TRUE
                        continue
                kept_node = dict(node)
                if node_type:
                    kept_node[KEY_OBJECT_TYPE] = node_type
                    kept_node[KEY_NODE_TYPE] = node_type
                kept_nodes.append(kept_node)
                kept_keys.add(node_key)
            edges = entry.get(KEY_TOPOLOGY_EDGES)
            kept_edges: List[Dict[str, object]] = list()
            if isinstance(edges, list):
                for edge in edges:
                    if not isinstance(edge, dict):
                        changed = BOOL_TRUE
                        continue
                    if edge.get(KEY_FROM_NODE) not in kept_keys or edge.get(KEY_TO_NODE) not in kept_keys:
                        changed = BOOL_TRUE
                        continue
                    kept_edges.append(dict(edge))
            kept_entry = dict(entry)
            kept_entry[KEY_TOPOLOGY_NODES] = kept_nodes
            kept_entry[KEY_TOPOLOGY_EDGES] = kept_edges
            kept_profiles[profile_name] = kept_entry
        topology[KEY_TOPOLOGY_PROFILES] = kept_profiles
        topology.setdefault(KEY_TOPOLOGY_VERSION, COUNT_ONE)
        return changed, warnings

    def _sanitize_diagram_payload(
        self,
        payload: Dict[str, object],
        valid_device_names: Set[str],
        valid_profiles: Set[str],
    ) -> Tuple[bool, List[str]]:
        """
        NAME
            _sanitize_diagram_payload - Drop invalid diagram profiles and device nodes.
        """

        warnings: List[str] = list()
        changed = BOOL_FALSE
        diagram = payload.get(KEY_DIAGRAM)
        if diagram is None:
            return changed, warnings
        if not isinstance(diagram, dict):
            payload.pop(KEY_DIAGRAM, None)
            warnings.append(
                MESSAGE_SALVAGE_PAYLOAD_RESET.format(section=KEY_DIAGRAM)
            )
            return BOOL_TRUE, warnings
        profiles = diagram.get(KEY_DIAGRAM_PROFILES)
        if not isinstance(profiles, dict):
            payload.pop(KEY_DIAGRAM, None)
            return BOOL_TRUE, warnings
        kept_profiles: Dict[str, Dict[str, object]] = dict()
        for profile_name, entry in profiles.items():
            if profile_name not in valid_profiles or not isinstance(entry, dict):
                warnings.append(
                    MESSAGE_SALVAGE_DIAGRAM_PROFILE_DROPPED.format(profile=profile_name)
                )
                changed = BOOL_TRUE
                continue
            nodes = entry.get(KEY_DIAGRAM_NODES)
            if not isinstance(nodes, list):
                warnings.append(
                    MESSAGE_SALVAGE_DIAGRAM_PROFILE_DROPPED.format(profile=profile_name)
                )
                changed = BOOL_TRUE
                continue
            kept_nodes: List[Dict[str, object]] = list()
            for node in nodes:
                if not isinstance(node, dict):
                    changed = BOOL_TRUE
                    continue
                node_type = get_object_type(node)
                if node_type == NODE_TYPE_DEVICE:
                    label = node.get(KEY_LABEL)
                    if not isinstance(label, str) or label not in valid_device_names:
                        warnings.append(
                            MESSAGE_SALVAGE_DIAGRAM_NODE_DROPPED.format(
                                profile=profile_name, key=node.get(KEY_NODE_KEY)
                            )
                        )
                        changed = BOOL_TRUE
                        continue
                kept_node = dict(node)
                if node_type:
                    kept_node[KEY_OBJECT_TYPE] = node_type
                    kept_node[KEY_NODE_TYPE] = node_type
                kept_nodes.append(kept_node)
            kept_entry = dict(entry)
            kept_entry[KEY_DIAGRAM_NODES] = kept_nodes
            kept_profiles[profile_name] = kept_entry
        diagram[KEY_DIAGRAM_PROFILES] = kept_profiles
        return changed, warnings

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
        payload = self._db.get_payload(DOC_BINDINGS)
        sanitized, sanitize_warnings, _changed = self.sanitize_bindings_payload(payload)
        self._warnings.extend(sanitize_warnings)
        self._db.set_payload(DOC_BINDINGS, sanitized)
        return sanitized

    def _load_mappings(self, repo_root: Path) -> Dict[str, object]:
        """
        NAME
            _load_mappings - Load CAN mappings payload.
        """

        path = self._deploy_path(FILE_CAN_MAPPINGS_ROOT)
        self._db.load_document(DOC_MAPPINGS, path, None, None)
        payload = self._db.get_payload(DOC_MAPPINGS)
        sanitized, warnings, _changed = self.sanitize_mappings_payload(payload)
        self._warnings.extend(warnings)
        self._db.set_payload(DOC_MAPPINGS, sanitized)
        return sanitized

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
            for key in (KEY_CONTROLLERS, KEY_BINDINGS, KEY_INPUT_ALIASES):
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
        catalog_keys = {str(label).strip().lower() for label in catalog.keys()}
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
                        if str(attachment).strip().lower() not in catalog_keys:
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
                        MESSAGE_PROFILE_DEVICES_TYPE_INVALID.format(profile=profile_name),
                        SEVERITY_ERROR,
                    )
                    continue
                for label in labels:
                    if str(label).strip().lower() not in catalog_keys:
                        self._append_issue(
                            issues,
                            LOCATION_PROFILES,
                            MESSAGE_MISSING_DEVICE_REF_PROFILE.format(
                                profile=profile_name,
                                label=label,
                            ),
                            SEVERITY_ERROR,
                        )
        diagram = payload.get(KEY_DIAGRAM)
        if isinstance(diagram, dict):
            diagram_profiles = diagram.get(KEY_DIAGRAM_PROFILES)
            if isinstance(diagram_profiles, dict):
                for profile_name, diagram_profile in diagram_profiles.items():
                    if target_profile is not None and profile_name != target_profile:
                        continue
                    if not isinstance(diagram_profile, dict):
                        continue
                    self._validate_diagram_profile(diagram_profile, catalog, issues, profile_name)
        topology = payload.get(KEY_TOPOLOGY)
        if isinstance(topology, dict):
            topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
            if isinstance(topology_profiles, dict):
                for topology_profile_name, topology_profile in topology_profiles.items():
                    if target_profile is not None and topology_profile_name != target_profile:
                        continue
                    if not isinstance(topology_profile, dict):
                        continue
                    self._validate_topology_profile(
                        topology_profile,
                        catalog,
                        issues,
                        topology_profile_name,
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
            object_catalog = {
                label: object()
                for label in self._profile_object_label_set_from_payload(payload, profile_name)
            }
            groups = entry.get(KEY_BRIDGE_GROUPS)
            if isinstance(groups, list):
                for group in groups:
                    if isinstance(group, dict):
                        self._check_unknown_keys(group, ALLOWED_GROUP_KEYS, LOCATION_PROFILES, issues, strict)
                        self._validate_group_entry(group, object_catalog, issues, strict)
            selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE)
            if isinstance(selected, dict):
                device_label = selected.get(KEY_DEVICE)
                if device_label and str(device_label).strip().lower() not in catalog_keys:
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
        if not isinstance(payload, dict) or not payload:
            payload = dict(BINDINGS_EMPTY_PAYLOAD)
        self._check_unknown_keys(payload, ALLOWED_BINDINGS_KEYS, LOCATION_BINDINGS, issues, strict)
        schema_version = payload.get(KEY_SCHEMA_VERSION)
        if schema_version != PROFILE_SCHEMA_VERSION:
            self._append_issue(
                issues,
                LOCATION_BINDINGS,
                MESSAGE_BINDINGS_SCHEMA_VERSION.format(
                    expected=PROFILE_SCHEMA_VERSION,
                    found=schema_version,
                ),
                SEVERITY_ERROR,
            )
        controllers = payload.get(KEY_CONTROLLERS)
        if controllers is None:
            controllers = list()
        if not isinstance(controllers, list):
            self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_TYPE_INVALID.format(key=KEY_CONTROLLERS), SEVERITY_ERROR)
            controllers = list()
        controller_names = self._bindings_controller_names()
        legacy_controller_names: Set[str] = set()
        for entry in controllers:
            if not isinstance(entry, dict):
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_CONTROLLER_FIELDS, SEVERITY_ERROR)
                continue
            name = entry.get(KEY_NAME)
            port = entry.get(KEY_PORT)
            if not name or not isinstance(name, str):
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_CONTROLLER_FIELDS, SEVERITY_ERROR)
                continue
            if isinstance(name, str) and name in legacy_controller_names:
                self._append_issue(issues, LOCATION_BINDINGS, MESSAGE_BINDINGS_CONTROLLER_DUP, SEVERITY_ERROR)
            if isinstance(name, str) and name:
                legacy_controller_names.add(name)
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
            reason = self._binding_validation_error(entry, controller_names)
            if reason is not None:
                self._append_issue(
                    issues,
                    LOCATION_BINDINGS,
                    reason,
                    SEVERITY_ERROR,
                )

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

    def _sanitize_binding_entry(
        self,
        entry: Dict[str, object],
        known_controller_names: Set[str],
    ) -> Tuple[Optional[Dict[str, object]], str]:
        """
        NAME
            _sanitize_binding_entry - Normalize one unified binding entry.
        """

        command = entry.get(KEY_COMMAND)
        controller = entry.get(KEY_CONTROLLER)
        input_name = entry.get(KEY_INPUT)
        binding_id = entry.get(KEY_ID_STR)
        mode = entry.get(KEY_MODE)
        if not all(isinstance(value, str) and str(value).strip() for value in (command, controller, input_name, binding_id, mode)):
            return None, MESSAGE_BINDINGS_BINDING_FIELDS
        controller_text = str(controller).strip()
        if controller_text.casefold() not in known_controller_names:
            return None, MESSAGE_BINDINGS_CONTROLLER_REQUIRED.format(name=controller)
        normalized: Dict[str, object] = {
            KEY_COMMAND: str(command).strip(),
            KEY_CONTROLLER: controller_text,
            KEY_INPUT: str(input_name).strip(),
            KEY_ID_STR: str(binding_id).strip(),
            KEY_MODE: str(mode).strip(),
        }
        invert = entry.get(KEY_INVERT)
        deadband = entry.get(KEY_DEADBAND)
        input_kind = str(input_name).strip()
        if input_kind == INPUT_KIND_AXIS:
            if not isinstance(invert, bool):
                return None, MESSAGE_BINDINGS_INVERT_TYPE
            if not isinstance(deadband, (int, float)) or deadband < DEADBAND_MIN or deadband > DEADBAND_MAX:
                return None, MESSAGE_BINDINGS_DEADBAND_RANGE
            normalized[KEY_INVERT] = invert
            normalized[KEY_DEADBAND] = float(deadband)
        return normalized, EMPTY_STRING

    def _binding_validation_error(
        self,
        entry: Dict[str, object],
        controller_names: Set[str],
    ) -> Optional[str]:
        """
        NAME
            _binding_validation_error - Validate one unified binding entry.
        """

        if not self._binding_has_fields(entry):
            return MESSAGE_BINDINGS_BINDING_FIELDS
        input_kind = str(entry.get(KEY_INPUT, EMPTY_STRING)).strip()
        binding_id = str(entry.get(KEY_ID_STR, EMPTY_STRING)).strip()
        controller_name = entry.get(KEY_CONTROLLER)
        if controller_name not in controller_names:
            return MESSAGE_BINDINGS_CONTROLLER_REQUIRED.format(name=controller_name)
        if input_kind not in {INPUT_KIND_BUTTON, INPUT_KIND_DPAD, INPUT_KIND_COMBO, INPUT_KIND_AXIS}:
            return MESSAGE_BINDINGS_INPUT_KIND
        if input_kind == INPUT_KIND_BUTTON and binding_id not in BUTTON_INPUTS:
            return MESSAGE_BINDINGS_ID_INVALID
        if input_kind == INPUT_KIND_DPAD and binding_id not in DPAD_INPUTS:
            return MESSAGE_BINDINGS_ID_INVALID
        if input_kind == INPUT_KIND_COMBO:
            combo_parts = [part.strip() for part in binding_id.split("+") if part.strip()]
            if not combo_parts or any(part not in BUTTON_INPUTS for part in combo_parts):
                return MESSAGE_BINDINGS_ID_INVALID
        if input_kind == INPUT_KIND_AXIS and binding_id not in AXIS_INPUTS:
            return MESSAGE_BINDINGS_ID_INVALID
        invert = entry.get(KEY_INVERT)
        deadband = entry.get(KEY_DEADBAND)
        mode = str(entry.get(KEY_MODE, EMPTY_STRING)).strip()
        if input_kind == INPUT_KIND_AXIS:
            if mode != MODE_ANALOG:
                return MESSAGE_BINDINGS_AXIS_MODE
            if not isinstance(invert, bool):
                return MESSAGE_BINDINGS_INVERT_TYPE
            if not isinstance(deadband, (int, float)):
                return MESSAGE_TYPE_INVALID.format(key=KEY_DEADBAND)
            if deadband < DEADBAND_MIN or deadband > DEADBAND_MAX:
                return MESSAGE_BINDINGS_DEADBAND_RANGE
            return None
        if invert is not None or deadband is not None:
            return MESSAGE_BINDINGS_NON_AXIS_EXTRAS
        return None

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
        label_by_key: Dict[str, str] = dict()
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            label = entry.get(KEY_LABEL)
            if not label or not isinstance(label, str):
                continue
            clean = label.strip()
            if not clean:
                continue
            key = clean.lower()
            prior = label_by_key.get(key)
            if prior is not None:
                duplicates.add(prior)
                duplicates.add(clean)
                continue
            label_by_key[key] = clean
            catalog[clean] = entry
        return catalog, duplicates

    def _profile_object_label_set_from_payload(
        self, payload: Dict[str, object], profile_name: str
    ) -> Set[str]:
        """
        NAME
            _profile_object_label_set_from_payload - Build object-label set for one profile.

        DESCRIPTION
            Includes profile device labels plus labeled topology and diagram
            objects for the same profile. Device topology nodes contribute
            their deviceRef label so groups can reference one shared label set.
        """

        labels: Set[str] = set()
        profiles = payload.get(KEY_PROFILES)
        if isinstance(profiles, dict):
            profile = profiles.get(profile_name)
            if isinstance(profile, dict):
                device_labels = profile.get(KEY_PROFILE_DEVICES)
                if isinstance(device_labels, list):
                    for label in device_labels:
                        if isinstance(label, str) and label.strip():
                            labels.add(label.strip().casefold())
        topology = payload.get(KEY_TOPOLOGY)
        if isinstance(topology, dict):
            topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
            topology_profile = topology_profiles.get(profile_name) if isinstance(topology_profiles, dict) else None
            if isinstance(topology_profile, dict):
                nodes = topology_profile.get(KEY_TOPOLOGY_NODES)
                if isinstance(nodes, list):
                    for node in nodes:
                        if not isinstance(node, dict):
                            continue
                        label_text = EMPTY_STRING
                        if get_object_type(node) == NODE_TYPE_DEVICE:
                            value = node.get(KEY_DEVICE_REF)
                            if isinstance(value, str):
                                label_text = value.strip()
                        else:
                            value = node.get(KEY_LABEL)
                            if isinstance(value, str):
                                label_text = value.strip()
                        if label_text:
                            labels.add(label_text.casefold())
        diagram = payload.get(KEY_DIAGRAM)
        if isinstance(diagram, dict):
            diagram_profiles = diagram.get(KEY_DIAGRAM_PROFILES)
            diagram_profile = diagram_profiles.get(profile_name) if isinstance(diagram_profiles, dict) else None
            if isinstance(diagram_profile, dict):
                nodes = diagram_profile.get(KEY_DIAGRAM_NODES)
                if isinstance(nodes, list):
                    for node in nodes:
                        if not isinstance(node, dict):
                            continue
                        value = node.get(KEY_LABEL)
                        if isinstance(value, str) and value.strip():
                            labels.add(value.strip().casefold())
        return labels

    def _validate_diagram_profile(
        self,
        diagram_profile: Dict[str, object],
        catalog: Dict[str, object],
        issues: List[ValidationIssue],
        profile_name: str,
    ) -> None:
        """
        NAME
            _validate_diagram_profile - Validate device-node diagram references.
        """

        catalog_keys = {str(label).strip().lower() for label in catalog.keys()}
        nodes = diagram_profile.get(KEY_DIAGRAM_NODES)
        if not isinstance(nodes, list):
            return
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = get_object_type(node)
            if node_type != NODE_TYPE_DEVICE:
                continue
            node_key = node.get(KEY_NODE_KEY, "?")
            label = node.get(KEY_LABEL)
            if not isinstance(label, str) or not label.strip():
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DIAGRAM_NODE_DEVICE_LABEL_REQUIRED.format(
                        profile=profile_name,
                        key=node_key,
                    ),
                    SEVERITY_ERROR,
                )
                continue
            label_text = label.strip()
            if label_text.lower() not in catalog_keys:
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DIAGRAM_NODE_DEVICE_UNKNOWN.format(
                        profile=profile_name,
                        key=node_key,
                        label=label_text,
                    ),
                    SEVERITY_ERROR,
                )
            if KEY_ID in node:
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DIAGRAM_NODE_DEVICE_ID_FORBIDDEN.format(
                        profile=profile_name,
                        key=node_key,
                        label=label_text,
                    ),
                    SEVERITY_ERROR,
                )

    def _validate_topology_profile(
        self,
        topology_profile: Dict[str, object],
        catalog: Dict[str, object],
        issues: List[ValidationIssue],
        profile_name: str,
    ) -> None:
        """
        NAME
            _validate_topology_profile - Validate device-node topology references.
        """
        for issue in validate_topology_profile(
            topology_profile,
            profile_name=profile_name,
            registry_keys={str(label).strip().lower() for label in catalog.keys()},
            normalize_nodes=True,
        ):
            message = issue.message
            if issue.code == ISSUE_DEVICE_REF_REQUIRED:
                message = MESSAGE_TOPOLOGY_NODE_DEVICE_REF_REQUIRED.format(
                    profile=profile_name,
                    key=issue.details.get("key", "?"),
                )
            elif issue.code == ISSUE_DEVICE_REF_UNKNOWN:
                message = MESSAGE_TOPOLOGY_NODE_DEVICE_UNKNOWN.format(
                    profile=profile_name,
                    key=issue.details.get("key", "?"),
                    label=issue.details.get("label", ""),
                )
            self._append_issue(
                issues,
                LOCATION_PROFILES,
                message,
                SEVERITY_ERROR if issue.severity == TOPOLOGY_SEVERITY_ERROR else SEVERITY_WARN,
            )

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
            if not isinstance(entry.get(KEY_ID), int):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DEVICE_ID_TYPE_FMT.format(label=label_text),
                    SEVERITY_ERROR,
                )
            if entry.get(KEY_INVERT) is not None and not isinstance(entry.get(KEY_INVERT), bool):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DEVICE_INVERT_TYPE_FMT.format(label=label_text),
                    SEVERITY_ERROR,
                )
        if interface == INTERFACE_USB:
            if not isinstance(entry.get(KEY_ID), int):
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_DEVICE_ID_TYPE_FMT.format(label=label_text),
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
            INTERFACE_USB,
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
        if interface == INTERFACE_USB:
            return DEVICE_REQUIRED_USB
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
                label = get_group_member_label(member)
            else:
                label = member
            catalog_keys = {str(name).strip().casefold() for name in catalog.keys()}
            if not isinstance(label, str) or label.strip().casefold() not in catalog_keys:
                self._append_issue(
                    issues,
                    LOCATION_PROFILES,
                    MESSAGE_MISSING_DEVICE_REF.format(label=label),
                    SEVERITY_ERROR,
                )

    def _profile_controller_names(self) -> Set[str]:
        """
        NAME
            _profile_controller_names - Build controller names from profile devices.
        """

        names: Set[str] = set()
        payload = self._db.get_payload(DOC_PROFILES)
        profiles = payload.get(KEY_PROFILES) if isinstance(payload, dict) else None
        if not isinstance(profiles, dict):
            return names
        for profile_name in profiles.keys():
            device_catalog, _ = self._device_catalog_for_profile(profile_name)
            for name, entry in device_catalog.items():
                if not isinstance(name, str) or not isinstance(entry, dict):
                    continue
                interface = get_device_interface(entry)
                if interface != INTERFACE_USB:
                    continue
                if str(entry.get(KEY_TYPE, EMPTY_STRING)).strip() != TYPE_XBOX_CONTROLLER:
                    continue
                names.add(name)
        return names

    def _bindings_controller_names(self) -> Set[str]:
        """
        NAME
            _bindings_controller_names - Build controller names from profiles plus legacy bindings.
        """

        names = set(self._profile_controller_names())
        payload = self._db.get_payload(DOC_BINDINGS)
        if not isinstance(payload, dict):
            return names
        controllers = payload.get(KEY_CONTROLLERS)
        if not isinstance(controllers, list):
            return names
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

