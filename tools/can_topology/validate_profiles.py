from __future__ import annotations

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

"""
NAME
    validate_profiles.py - Validate bringup_system.json compatibility.

SYNOPSIS
    python tools\\can_topology\\validate_profiles.py [--path PATH] [--strict]

DESCRIPTION
    Checks bringup_system.json for schema errors, duplicate labels, and
    interface-specific required fields so output is compatible with tooling.
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.common.cli_helpers import add_path_arg
from tools.common.config_api.repository import ConfigRepository
from tools.common.device_definition_rules import format_device_required_field_issue
from tools.common.profile_constants import (
    INTERFACE_ANALOG,
    INTERFACE_CAN,
    INTERFACE_DIO,
    INTERFACE_INTERNAL,
    INTERFACE_PWM,
    INTERFACE_USB,
    KEY_ATTACHMENTS,
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_ID,
    KEY_INTERFACE,
    KEY_INTERFACE_LEGACY,
    KEY_INVERT,
    KEY_LABEL,
    KEY_MANUFACTURER,
    KEY_PROFILE_DEVICES,
    KEY_PROFILES,
    KEY_SCHEMA_VERSION,
    KEY_TOPOLOGY,
    KEY_TOPOLOGY_PROFILES,
    KEY_TOPOLOGY_NODES,
    KEY_TOPOLOGY_EDGES,
    KEY_NODE_KEY,
    KEY_OBJECT_TYPE,
    KEY_NODE_TYPE,
    KEY_DEVICE_REF,
    KEY_FROM_NODE,
    KEY_TO_NODE,
    KEY_EDGE_TYPE,
    KEY_EDGE_ID,
    KEY_ANALOG,
    KEY_PWM,
    NODE_TYPE_DEVICE,
    EDGE_TYPE_ANALOG,
    EDGE_TYPE_CAN_DROP,
    EDGE_TYPE_CAN_TAP,
    EDGE_TYPE_CAN_TRUNK,
    EDGE_TYPE_DIO,
    EDGE_TYPE_POWER,
    EDGE_TYPE_PWM,
    EDGE_TYPE_UNKNOWN,
    EDGE_TYPE_VIRTUAL,
    PROFILE_SCHEMA_VERSION,
    get_device_interface,
    get_object_type,
)
from tools.common.profile_io import compute_profiles_hash

DEFAULT_PATH = str(Path("src") / "main" / "deploy" / "bringup_system.json")

MSG_ERR_FILE_MISSING = "File not found: {path}"
MSG_ERR_JSON_PARSE = "Failed to parse JSON: {error}"
MSG_ERR_SCHEMA = "Root 'schema_version' mismatch: expected {expected}, got {found}"
MSG_ERR_DATA_VERSION = "Root 'data_version' missing or empty."
MSG_ERR_DATA_HASH = "Root 'data_hash' missing or empty."
MSG_ERR_HASH_MISMATCH = "Root 'data_hash' mismatch (run python -m tools.validate_sync)."
MSG_ERR_DEVICES = "Root 'devices' must be a non-empty list."
MSG_ERR_PROFILES = "Root 'profiles' must be a non-empty object."
MSG_WARN_DEFAULT_PROFILE = "Root 'default_profile' is missing or empty."
MSG_WARN_DEFAULT_PROFILE_MISSING = "Root 'default_profile' '{profile}' not found in profiles."
MSG_ERR_DEVICE_LABEL = "Device entry missing label."
MSG_ERR_DEVICE_LABEL_DUP = "Duplicate device label in registry: {label}"
MSG_ERR_DEVICE_INTERFACE = "Device '{label}' missing interface."
MSG_ERR_PROFILE_OBJECT = "Profile '{name}' must be an object."
MSG_ERR_PROFILE_DEVICES = "Profile '{name}' missing devices list."
MSG_ERR_PROFILE_LABEL_UNKNOWN = "Profile '{name}' references unknown device label '{label}'."
MSG_ERR_PROFILE_LABEL_DUP = "Profile '{name}' has duplicate label '{label}'."
MSG_ERR_DEVICE_ATTACHMENTS = "Device '{label}' references unknown attachment '{attachment}'."
MSG_ERR_TOPOLOGY_NODE_KEY_DUP = "Profile '{profile}' topology duplicate node key: {key}."
MSG_ERR_TOPOLOGY_DEVICE_REF = "Profile '{profile}' topology node {key} missing deviceRef."
MSG_ERR_TOPOLOGY_DEVICE_UNKNOWN = (
    "Profile '{profile}' topology node {key} references unknown deviceRef '{label}'."
)
MSG_ERR_TOPOLOGY_EDGE_ENDPOINT = (
    "Profile '{profile}' topology edge '{edge}' references missing node endpoint."
)
MSG_WARN_TOPOLOGY_EDGE_TYPE = "Profile '{profile}' topology edge '{edge}' unknown edgeType '{edge_type}'."
MSG_PASS_SCHEMA = "Root 'schema_version' matches expected version."
MSG_PASS_DATA_VERSION = "Root 'data_version' is present."
MSG_PASS_DATA_HASH = "Root 'data_hash' matches computed value."
MSG_PASS_PROFILES = "Root 'profiles' is a non-empty object."
MSG_PASS_DEFAULT_PROFILE = "Root 'default_profile' present in profiles."

KNOWN_EDGE_TYPES = {
    EDGE_TYPE_ANALOG,
    EDGE_TYPE_CAN_DROP,
    EDGE_TYPE_CAN_TAP,
    EDGE_TYPE_CAN_TRUNK,
    EDGE_TYPE_DIO,
    EDGE_TYPE_POWER,
    EDGE_TYPE_PWM,
    EDGE_TYPE_UNKNOWN,
    EDGE_TYPE_VIRTUAL,
}


def _compute_data_hash(payload: Dict[str, Any]) -> str:
    """
    NAME
        _compute_data_hash - Compute a stable hash for profile payloads.
    """
    return compute_profiles_hash(payload)



def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    NAME
        parse_args - Parse CLI arguments.

    RETURNS
        argparse.Namespace with parsed args.
    """
    parser = argparse.ArgumentParser(description="Validate bringup_system.json compatibility.")
    add_path_arg(
        parser,
        default=DEFAULT_PATH,
        help_text="Path to bringup_system.json",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print pass/fail/warn for each validation check.",
    )
    return parser.parse_args(argv)



def load_profiles_json(path: Path) -> Dict[str, Any]:
    """
    NAME
        load_profiles_json - Load JSON payload from disk.

    RETURNS
        Parsed JSON dict.

    ERRORS
        Raises ValueError when the file is missing or invalid.
    """
    if not path.exists():
        raise ValueError(MSG_ERR_FILE_MISSING.format(path=path))
    try:
        return ConfigRepository().load_path(path).to_payload()
    except Exception as exc:
        raise ValueError(MSG_ERR_JSON_PARSE.format(error=exc)) from exc



def validate_profiles(payload: Dict[str, Any], reporter: "Reporter") -> Tuple[List[str], List[str]]:
    """
    NAME
        validate_profiles - Validate the root payload and each profile.

    RETURNS
        (errors, warnings) lists.
    """
    errors: List[str] = []
    warnings: List[str] = []

    schema_version = payload.get(KEY_SCHEMA_VERSION)
    if schema_version != PROFILE_SCHEMA_VERSION:
        msg = MSG_ERR_SCHEMA.format(expected=PROFILE_SCHEMA_VERSION, found=schema_version)
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings
    reporter.pass_(MSG_PASS_SCHEMA)

    data_version = payload.get(KEY_DATA_VERSION)
    if not isinstance(data_version, str) or not data_version.strip():
        msg = MSG_ERR_DATA_VERSION
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings
    reporter.pass_(MSG_PASS_DATA_VERSION)

    data_hash = payload.get(KEY_DATA_HASH)
    if not isinstance(data_hash, str) or not data_hash.strip():
        msg = MSG_ERR_DATA_HASH
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings
    computed_hash = _compute_data_hash(payload)
    if data_hash != computed_hash:
        msg = MSG_ERR_HASH_MISMATCH
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings
    reporter.pass_(MSG_PASS_DATA_HASH)

    devices = payload.get(KEY_DEVICES)
    if not isinstance(devices, list) or not devices:
        msg = MSG_ERR_DEVICES
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings

    registry, registry_errors, registry_warnings = validate_device_registry(devices, reporter)
    errors.extend(registry_errors)
    warnings.extend(registry_warnings)
    if registry_errors:
        return errors, warnings

    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict) or not profiles:
        msg = MSG_ERR_PROFILES
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings
    reporter.pass_(MSG_PASS_PROFILES)

    default_profile = payload.get(KEY_DEFAULT_PROFILE)
    if not isinstance(default_profile, str) or not default_profile:
        msg = MSG_WARN_DEFAULT_PROFILE
        warnings.append(msg)
        reporter.warn(msg)
    elif default_profile not in profiles:
        msg = MSG_WARN_DEFAULT_PROFILE_MISSING.format(profile=default_profile)
        warnings.append(msg)
        reporter.warn(msg)
    else:
        reporter.pass_(MSG_PASS_DEFAULT_PROFILE)

    for name, profile in profiles.items():
        profile_errors, profile_warnings = validate_profile(name, profile, registry, reporter)
        errors.extend(profile_errors)
        warnings.extend(profile_warnings)

    topology_errors, topology_warnings = validate_topology(payload, registry, reporter)
    errors.extend(topology_errors)
    warnings.extend(topology_warnings)

    return errors, warnings



def validate_device_registry(
    devices: List[Any],
    reporter: "Reporter",
) -> Tuple[Dict[str, Dict[str, Any]], List[str], List[str]]:
    """
    NAME
        validate_device_registry - Validate the devices registry entries.

    RETURNS
        (registry_map, errors, warnings).
    """
    errors: List[str] = []
    warnings: List[str] = []
    registry: Dict[str, Dict[str, Any]] = {}

    for entry in devices:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, "")).strip()
        if not label:
            msg = MSG_ERR_DEVICE_LABEL
            errors.append(msg)
            reporter.fail(msg)
            continue
        key = label.lower()
        if key in registry:
            msg = MSG_ERR_DEVICE_LABEL_DUP.format(label=label)
            errors.append(msg)
            reporter.fail(msg)
            continue
        registry[key] = entry
        interface = get_device_interface(entry)
        if interface is None and entry.get(KEY_INTERFACE_LEGACY) is not None:
            entry[KEY_INTERFACE] = entry.get(KEY_INTERFACE_LEGACY)
            interface = entry.get(KEY_INTERFACE)
        if not isinstance(interface, str) or not interface:
            msg = MSG_ERR_DEVICE_INTERFACE.format(label=label)
            errors.append(msg)
            reporter.fail(msg)
            continue
        issue = format_device_required_field_issue(label, entry)
        if issue is not None:
            errors.append(issue)
            reporter.fail(issue)

    for entry in devices:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, "")).strip()
        if not label:
            continue
        attachments = entry.get(KEY_ATTACHMENTS)
        if attachments is None:
            continue
        if not isinstance(attachments, list):
            msg = MSG_ERR_DEVICE_ATTACHMENTS.format(label=label, attachment="<invalid>")
            errors.append(msg)
            reporter.fail(msg)
            continue
        for att in attachments:
            if not isinstance(att, str) or not att.strip():
                msg = MSG_ERR_DEVICE_ATTACHMENTS.format(label=label, attachment="<invalid>")
                errors.append(msg)
                reporter.fail(msg)
                continue
            if att.strip().lower() not in registry:
                msg = MSG_ERR_DEVICE_ATTACHMENTS.format(label=label, attachment=att)
                errors.append(msg)
                reporter.fail(msg)

    return registry, errors, warnings



def validate_profile(
    name: str,
    profile: Any,
    registry: Dict[str, Dict[str, Any]],
    reporter: "Reporter",
) -> Tuple[List[str], List[str]]:
    """
    NAME
        validate_profile - Validate one profile section.

    RETURNS
        (errors, warnings) lists.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(profile, dict):
        msg = MSG_ERR_PROFILE_OBJECT.format(name=name)
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings

    devices = profile.get(KEY_PROFILE_DEVICES)
    if not isinstance(devices, list):
        msg = MSG_ERR_PROFILE_DEVICES.format(name=name)
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings

    seen: Dict[str, int] = {}
    for label in devices:
        if not isinstance(label, str) or not label.strip():
            continue
        key = label.strip().lower()
        if key not in registry:
            msg = MSG_ERR_PROFILE_LABEL_UNKNOWN.format(name=name, label=label)
            errors.append(msg)
            reporter.fail(msg)
            continue
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            msg = MSG_ERR_PROFILE_LABEL_DUP.format(name=name, label=label)
            errors.append(msg)
            reporter.fail(msg)

    return errors, warnings


def validate_topology(
    payload: Dict[str, Any],
    registry: Dict[str, Dict[str, Any]],
    reporter: "Reporter",
) -> Tuple[List[str], List[str]]:
    """
    NAME
        validate_topology - Validate topology graph references.

    RETURNS
        (errors, warnings) lists.
    """
    errors: List[str] = []
    warnings: List[str] = []
    topology = payload.get(KEY_TOPOLOGY)
    if not isinstance(topology, dict):
        return errors, warnings
    topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
    if not isinstance(topology_profiles, dict):
        return errors, warnings
    registry_keys = {label.strip().lower() for label in registry.keys()}
    for profile_name, topology_profile in topology_profiles.items():
        if not isinstance(topology_profile, dict):
            continue
        nodes = topology_profile.get(KEY_TOPOLOGY_NODES)
        if not isinstance(nodes, list):
            continue
        node_keys: set[int] = set()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_key = node.get(KEY_NODE_KEY)
            if isinstance(node_key, int):
                if node_key in node_keys:
                    msg = MSG_ERR_TOPOLOGY_NODE_KEY_DUP.format(
                        profile=profile_name,
                        key=node_key,
                    )
                    errors.append(msg)
                    reporter.fail(msg)
                node_keys.add(node_key)
            object_type = get_object_type(node)
            if KEY_OBJECT_TYPE not in node and object_type:
                node[KEY_OBJECT_TYPE] = object_type
            if KEY_NODE_TYPE not in node and object_type:
                node[KEY_NODE_TYPE] = object_type
            if object_type != NODE_TYPE_DEVICE:
                continue
            device_ref = node.get(KEY_DEVICE_REF)
            if not isinstance(device_ref, str) or not device_ref.strip():
                msg = MSG_ERR_TOPOLOGY_DEVICE_REF.format(
                    profile=profile_name,
                    key=node_key if isinstance(node_key, int) else "?",
                )
                errors.append(msg)
                reporter.fail(msg)
                continue
            if device_ref.strip().lower() not in registry_keys:
                msg = MSG_ERR_TOPOLOGY_DEVICE_UNKNOWN.format(
                    profile=profile_name,
                    key=node_key if isinstance(node_key, int) else "?",
                    label=device_ref,
                )
                errors.append(msg)
                reporter.fail(msg)
        edges = topology_profile.get(KEY_TOPOLOGY_EDGES)
        if not isinstance(edges, list):
            continue
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            edge_id = edge.get(KEY_EDGE_ID, "?")
            from_node = edge.get(KEY_FROM_NODE)
            to_node = edge.get(KEY_TO_NODE)
            if not isinstance(from_node, int) or not isinstance(to_node, int):
                msg = MSG_ERR_TOPOLOGY_EDGE_ENDPOINT.format(
                    profile=profile_name,
                    edge=edge_id,
                )
                errors.append(msg)
                reporter.fail(msg)
                continue
            if from_node not in node_keys or to_node not in node_keys:
                msg = MSG_ERR_TOPOLOGY_EDGE_ENDPOINT.format(
                    profile=profile_name,
                    edge=edge_id,
                )
                errors.append(msg)
                reporter.fail(msg)
            edge_type = edge.get(KEY_EDGE_TYPE)
            if isinstance(edge_type, str) and edge_type not in KNOWN_EDGE_TYPES:
                msg = MSG_WARN_TOPOLOGY_EDGE_TYPE.format(
                    profile=profile_name,
                    edge=edge_id,
                    edge_type=edge_type,
                )
                warnings.append(msg)
                reporter.warn(msg)
    return errors, warnings

class Reporter:
    """
    NAME
        Reporter - Emit verbose pass/fail/warn lines when enabled.
    """

    def __init__(self, enabled: bool) -> None:
        self._enabled = enabled

    def pass_(self, msg: str) -> None:
        if self._enabled:
            print(f"PASS: {msg}")

    def fail(self, msg: str) -> None:
        if self._enabled:
            print(f"FAIL: {msg}")

    def warn(self, msg: str) -> None:
        if self._enabled:
            print(f"WARN: {msg}")



def main(argv: Optional[List[str]] = None) -> int:
    """
    NAME
        main - CLI entry point.

    RETURNS
        Process exit code (0 on success).
    """
    args = parse_args(argv)
    try:
        payload = load_profiles_json(Path(args.path))
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    reporter = Reporter(args.verbose)
    errors, warnings = validate_profiles(payload, reporter)
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
        return 2 if args.strict or errors else 0
    if args.strict and warnings:
        print("Strict mode: warnings treated as errors.")
        return 2
    print("Validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
