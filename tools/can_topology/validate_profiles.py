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
from tools.common.json_io import read_json
from tools.common.profile_constants import (
    EDGE_TYPE_ANALOG,
    EDGE_TYPE_CAN_DROP,
    EDGE_TYPE_CAN_TAP,
    EDGE_TYPE_CAN_TRUNK,
    EDGE_TYPE_DIO,
    EDGE_TYPE_POWER,
    EDGE_TYPE_PWM,
    EDGE_TYPE_UNKNOWN,
    EDGE_TYPE_VIRTUAL,
    INTERFACE_ANALOG,
    INTERFACE_CAN,
    INTERFACE_DIO,
    INTERFACE_INTERNAL,
    INTERFACE_PWM,
    KEY_ATTACHMENTS,
    KEY_BUS,
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICE_REF,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_DIO,
    KEY_EDGE_ID,
    KEY_EDGE_TYPE,
    KEY_FROM_NODE,
    KEY_FROM_PORT,
    KEY_ID,
    KEY_INTERFACE,
    KEY_INTERFACE_LEGACY,
    KEY_INVERT,
    KEY_LABEL,
    KEY_LAYOUT,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_NODE_KEY,
    KEY_NODE_TYPE,
    KEY_PROFILE_DEVICES,
    KEY_PROFILES,
    KEY_SCHEMA_VERSION,
    KEY_ANALOG,
    KEY_PWM,
    KEY_TO_NODE,
    KEY_TO_PORT,
    KEY_TOPOLOGY,
    KEY_TOPOLOGY_EDGES,
    KEY_TOPOLOGY_NODES,
    KEY_TOPOLOGY_PROFILES,
    KEY_VENDOR,
    LAYOUT_KEY_ROW,
    LAYOUT_KEY_X,
    NODE_TYPE_ANALYZER,
    NODE_TYPE_DEVICE,
    NODE_TYPE_JUNCTION,
    NODE_TYPE_POWER,
    NODE_TYPE_VIRTUAL,
    PROFILE_SCHEMA_VERSION,
    get_device_interface,
)
from tools.common.profile_io import compute_profiles_hash

DEFAULT_PATH = str(Path("data") / "bringup_system.json")

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
MSG_ERR_DEVICE_CAN_FIELDS = "Device '{label}' missing CAN fields: id/manufacturer/deviceType."
MSG_ERR_DEVICE_DIO_FIELDS = "Device '{label}' missing DIO fields: dio/invert."
MSG_ERR_DEVICE_PWM_FIELDS = "Device '{label}' missing PWM field: pwm."
MSG_ERR_DEVICE_ANALOG_FIELDS = "Device '{label}' missing ANALOG field: analog."
MSG_ERR_DEVICE_ATTACHMENTS = "Device '{label}' references unknown attachment '{attachment}'."
MSG_PASS_SCHEMA = "Root 'schema_version' matches expected version."
MSG_PASS_DATA_VERSION = "Root 'data_version' is present."
MSG_PASS_DATA_HASH = "Root 'data_hash' matches computed value."
MSG_PASS_PROFILES = "Root 'profiles' is a non-empty object."
MSG_PASS_DEFAULT_PROFILE = "Root 'default_profile' present in profiles."
MSG_WARN_TOPOLOGY_MISSING = "Root 'topology' missing; topology graph not authored."
MSG_ERR_TOPOLOGY_OBJECT = "Root 'topology' must be an object when present."
MSG_ERR_TOPOLOGY_PROFILES = "Root 'topology.profiles' must be an object."
MSG_ERR_TOPOLOGY_PROFILE_OBJECT = "Topology profile '{name}' must be an object."
MSG_ERR_TOPOLOGY_NODES = "Topology profile '{name}' missing nodes list."
MSG_ERR_TOPOLOGY_EDGES = "Topology profile '{name}' missing edges list."
MSG_ERR_TOPOLOGY_NODE_KEY_DUP = "Topology profile '{name}' has duplicate node key '{key}'."
MSG_ERR_TOPOLOGY_DEVICE_REF = "Topology profile '{name}' device node '{key}' missing deviceRef."
MSG_ERR_TOPOLOGY_DEVICE_UNKNOWN = "Topology profile '{name}' deviceRef '{label}' not found in devices."
MSG_ERR_TOPOLOGY_DEVICE_LABEL_DUP = "Topology profile '{name}' has multiple device nodes for '{label}'."
MSG_ERR_TOPOLOGY_NODE_LABEL = "Topology profile '{name}' node '{key}' missing label."
MSG_ERR_TOPOLOGY_EDGE_ID_DUP = "Topology profile '{name}' has duplicate edge id '{edge_id}'."
MSG_ERR_TOPOLOGY_EDGE_ENDPOINT = "Topology profile '{name}' edge '{edge_id}' references missing node endpoint."
MSG_ERR_TOPOLOGY_EDGE_PORT = "Topology profile '{name}' edge '{edge_id}' missing port names."
MSG_ERR_TOPOLOGY_PORT_REUSE = "Topology profile '{name}' reuses node '{node}' port '{port}'."
MSG_WARN_TOPOLOGY_EDGE_TYPE = "Topology profile '{name}' edge '{edge_id}' uses unknown edgeType '{edge_type}'."
MSG_WARN_TOPOLOGY_NODE_LAYOUT = "Topology profile '{name}' node '{key}' missing layout field '{field}'."

TOPOLOGY_NODE_TYPES = {
    NODE_TYPE_DEVICE,
    NODE_TYPE_JUNCTION,
    NODE_TYPE_ANALYZER,
    NODE_TYPE_POWER,
    NODE_TYPE_VIRTUAL,
}
TOPOLOGY_EDGE_TYPES = {
    EDGE_TYPE_CAN_TRUNK,
    EDGE_TYPE_CAN_DROP,
    EDGE_TYPE_CAN_TAP,
    EDGE_TYPE_DIO,
    EDGE_TYPE_PWM,
    EDGE_TYPE_ANALOG,
    EDGE_TYPE_POWER,
    EDGE_TYPE_VIRTUAL,
    EDGE_TYPE_UNKNOWN,
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
        return read_json(path)
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

    topology_errors, topology_warnings = validate_topology(payload, profiles, registry, reporter)
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
        if interface == INTERFACE_CAN:
            if not _has_can_fields(entry):
                msg = MSG_ERR_DEVICE_CAN_FIELDS.format(label=label)
                errors.append(msg)
                reporter.fail(msg)
        elif interface == INTERFACE_DIO:
            if not _has_dio_fields(entry):
                msg = MSG_ERR_DEVICE_DIO_FIELDS.format(label=label)
                errors.append(msg)
                reporter.fail(msg)
        elif interface == INTERFACE_PWM:
            if not _has_pwm_fields(entry):
                msg = MSG_ERR_DEVICE_PWM_FIELDS.format(label=label)
                errors.append(msg)
                reporter.fail(msg)
        elif interface == INTERFACE_ANALOG:
            if not _has_analog_fields(entry):
                msg = MSG_ERR_DEVICE_ANALOG_FIELDS.format(label=label)
                errors.append(msg)
                reporter.fail(msg)
        elif interface == INTERFACE_INTERNAL:
            pass

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
    profiles: Dict[str, Any],
    registry: Dict[str, Dict[str, Any]],
    reporter: "Reporter",
) -> Tuple[List[str], List[str]]:
    """
    NAME
        validate_topology - Validate the root topology graph when present.
    """
    errors: List[str] = []
    warnings: List[str] = []
    topology = payload.get(KEY_TOPOLOGY)
    if topology is None:
        warnings.append(MSG_WARN_TOPOLOGY_MISSING)
        reporter.warn(MSG_WARN_TOPOLOGY_MISSING)
        return errors, warnings
    if not isinstance(topology, dict):
        errors.append(MSG_ERR_TOPOLOGY_OBJECT)
        reporter.fail(MSG_ERR_TOPOLOGY_OBJECT)
        return errors, warnings
    topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
    if not isinstance(topology_profiles, dict):
        errors.append(MSG_ERR_TOPOLOGY_PROFILES)
        reporter.fail(MSG_ERR_TOPOLOGY_PROFILES)
        return errors, warnings
    for name, entry in topology_profiles.items():
        if name not in profiles:
            continue
        profile_errors, profile_warnings = validate_topology_profile(name, entry, registry, reporter)
        errors.extend(profile_errors)
        warnings.extend(profile_warnings)
    return errors, warnings


def validate_topology_profile(
    name: str,
    entry: Any,
    registry: Dict[str, Dict[str, Any]],
    reporter: "Reporter",
) -> Tuple[List[str], List[str]]:
    """
    NAME
        validate_topology_profile - Validate one profile topology graph.
    """
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(entry, dict):
        msg = MSG_ERR_TOPOLOGY_PROFILE_OBJECT.format(name=name)
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings
    nodes = entry.get(KEY_TOPOLOGY_NODES)
    edges = entry.get(KEY_TOPOLOGY_EDGES)
    if not isinstance(nodes, list):
        msg = MSG_ERR_TOPOLOGY_NODES.format(name=name)
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings
    if not isinstance(edges, list):
        msg = MSG_ERR_TOPOLOGY_EDGES.format(name=name)
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings

    node_by_key: Dict[int, Dict[str, Any]] = {}
    seen_device_refs: Dict[str, int] = {}
    for raw in nodes:
        if not isinstance(raw, dict):
            continue
        key = raw.get(KEY_NODE_KEY)
        if not isinstance(key, int):
            continue
        if key in node_by_key:
            msg = MSG_ERR_TOPOLOGY_NODE_KEY_DUP.format(name=name, key=key)
            errors.append(msg)
            reporter.fail(msg)
            continue
        node_by_key[key] = raw
        node_type = str(raw.get(KEY_NODE_TYPE, "")).strip()
        layout = raw.get(KEY_LAYOUT)
        layout_dict = layout if isinstance(layout, dict) else {}
        for field_name in (KEY_BUS, LAYOUT_KEY_ROW, LAYOUT_KEY_X):
            if field_name not in layout_dict:
                msg = MSG_WARN_TOPOLOGY_NODE_LAYOUT.format(name=name, key=key, field=field_name)
                warnings.append(msg)
                reporter.warn(msg)
        if node_type == NODE_TYPE_DEVICE:
            device_ref = str(raw.get(KEY_DEVICE_REF, "")).strip()
            if not device_ref:
                msg = MSG_ERR_TOPOLOGY_DEVICE_REF.format(name=name, key=key)
                errors.append(msg)
                reporter.fail(msg)
                continue
            device_key = device_ref.lower()
            if device_key not in registry:
                msg = MSG_ERR_TOPOLOGY_DEVICE_UNKNOWN.format(name=name, label=device_ref)
                errors.append(msg)
                reporter.fail(msg)
                continue
            seen_device_refs[device_key] = seen_device_refs.get(device_key, 0) + 1
            if seen_device_refs[device_key] > 1:
                msg = MSG_ERR_TOPOLOGY_DEVICE_LABEL_DUP.format(name=name, label=device_ref)
                errors.append(msg)
                reporter.fail(msg)
        else:
            label = str(raw.get(KEY_LABEL, "")).strip()
            if not label:
                msg = MSG_ERR_TOPOLOGY_NODE_LABEL.format(name=name, key=key)
                errors.append(msg)
                reporter.fail(msg)

    seen_edge_ids: set[str] = set()
    used_ports: set[Tuple[int, str]] = set()
    for raw in edges:
        if not isinstance(raw, dict):
            continue
        edge_id = str(raw.get(KEY_EDGE_ID, "")).strip()
        if not edge_id:
            edge_id = "<missing>"
        if edge_id in seen_edge_ids:
            msg = MSG_ERR_TOPOLOGY_EDGE_ID_DUP.format(name=name, edge_id=edge_id)
            errors.append(msg)
            reporter.fail(msg)
            continue
        seen_edge_ids.add(edge_id)
        from_node = raw.get(KEY_FROM_NODE)
        to_node = raw.get(KEY_TO_NODE)
        from_port = raw.get(KEY_FROM_PORT)
        to_port = raw.get(KEY_TO_PORT)
        if not isinstance(from_node, int) or not isinstance(to_node, int):
            msg = MSG_ERR_TOPOLOGY_EDGE_ENDPOINT.format(name=name, edge_id=edge_id)
            errors.append(msg)
            reporter.fail(msg)
            continue
        if from_node not in node_by_key or to_node not in node_by_key:
            msg = MSG_ERR_TOPOLOGY_EDGE_ENDPOINT.format(name=name, edge_id=edge_id)
            errors.append(msg)
            reporter.fail(msg)
            continue
        if not isinstance(from_port, str) or not from_port.strip() or not isinstance(to_port, str) or not to_port.strip():
            msg = MSG_ERR_TOPOLOGY_EDGE_PORT.format(name=name, edge_id=edge_id)
            errors.append(msg)
            reporter.fail(msg)
            continue
        for port_key in ((from_node, from_port.strip()), (to_node, to_port.strip())):
            if port_key in used_ports:
                msg = MSG_ERR_TOPOLOGY_PORT_REUSE.format(name=name, node=port_key[0], port=port_key[1])
                errors.append(msg)
                reporter.fail(msg)
            used_ports.add(port_key)
        edge_type = str(raw.get(KEY_EDGE_TYPE, "")).strip()
        if edge_type not in TOPOLOGY_EDGE_TYPES:
            msg = MSG_WARN_TOPOLOGY_EDGE_TYPE.format(name=name, edge_id=edge_id, edge_type=edge_type)
            warnings.append(msg)
            reporter.warn(msg)

    return errors, warnings


def _has_can_fields(entry: Dict[str, Any]) -> bool:
    manufacturer = entry.get(KEY_MANUFACTURER)
    device_type = entry.get(KEY_DEVICE_TYPE)
    device_id = entry.get(KEY_ID)
    return isinstance(manufacturer, int) and isinstance(device_type, int) and isinstance(device_id, int)



def _has_dio_fields(entry: Dict[str, Any]) -> bool:
    dio = entry.get(KEY_DIO)
    invert = entry.get(KEY_INVERT)
    return isinstance(dio, int) and isinstance(invert, bool)



def _has_pwm_fields(entry: Dict[str, Any]) -> bool:
    pwm = entry.get(KEY_PWM)
    return isinstance(pwm, int)



def _has_analog_fields(entry: Dict[str, Any]) -> bool:
    analog = entry.get(KEY_ANALOG)
    return isinstance(analog, int)


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
