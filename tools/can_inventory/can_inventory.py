from __future__ import annotations

"""
NAME
    can_inventory.py - CAN inventory snapshot, config generation, and diff helpers.

SYNOPSIS
    from tools.can_inventory.can_inventory import dump_api_inventory, print_inventory_diff

DESCRIPTION
    Builds a JSON inventory of observed CAN devices and frame timing data,
    generates a robot config template, validates configs, and compares
    inventories between runs.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.common.json_io import read_json, write_json

KEY_METADATA = "metadata"
KEY_DEVICES = "devices"
KEY_LABEL = "label"
KEY_FRAME_DATA = "frame_data"
KEY_CAPTURE_TIMESTAMP = "capture_timestamp"
KEY_SOURCE = "source"
KEY_ROBOT_IP = "robot_ip"
KEY_PARAMETERS = "parameters"
KEY_NAME = "name"
KEY_DIO_DEVICES = "dio_devices"
KEY_EXTERNAL_ENCODERS = "external_encoders"
KEY_LINKED_DEVICE = "linked_device"
ENCODER_DEFAULT_TYPE = "through_bore"
DIO_EXAMPLE_NAME = "limit_switch_example"
ENCODER_EXAMPLE_NAME = "encoder_example"


def dump_api_inventory(
    path: str,
    profile: str,
    interface: str,
    channel: str,
    bitrate: int,
    pairs: Dict[Tuple[str, int, int], Dict[str, float]],
    source: str = "can_nt_bridge",
    robot_ip: Optional[str] = None,
) -> None:
    """
    NAME
        dump_api_inventory - Persist per-device inventory with frame timing.

    PARAMETERS
        path: Output JSON file path.
        profile: Active profile name.
        interface: CAN interface type (e.g., slcan).
        channel: CAN channel (e.g., COM port).
        bitrate: CAN bitrate in bps.
        pairs: Observed pair stats keyed by (label,apiClass,apiIndex).
        source: Inventory source label.
        robot_ip: Robot IP address string.

    SIDE EFFECTS
        Writes a JSON file to disk.
    """
    devices: Dict[str, Dict[str, Any]] = {}
    for (label, api_class, api_index), stats in pairs.items():
        key = str(label)
        duration = max(0.0, stats["last"] - stats["first"])
        fps = (stats["count"] / duration) if duration > 0 else 0.0
        period_ms = (1000.0 / fps) if fps > 0 else None
        frame_name = build_frame_name(api_class, api_index)
        frame_entry = {
            "period_ms": period_ms,
        }
        if key not in devices:
            devices[key] = {
                KEY_LABEL: key,
                KEY_FRAME_DATA: {},
            }
        devices[key][KEY_FRAME_DATA][frame_name] = frame_entry

    payload = {
        KEY_METADATA: {
            KEY_CAPTURE_TIMESTAMP: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            KEY_SOURCE: source,
            KEY_ROBOT_IP: robot_ip,
        },
        KEY_DEVICES: [devices[key] for key in sorted(devices.keys())],
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as exc:
        print(f"ERROR: Failed to write API inventory '{path}': {exc}")


def load_inventory(path: str) -> Dict[Tuple[str, int, int], float]:
    """
    NAME
        load_inventory - Load inventory JSON into a keyed fps map.

    PARAMETERS
        path: Inventory JSON file path.

    RETURNS
        Mapping of (label,apiClass,apiIndex) -> fps.

    ERRORS
        Prints a warning and returns empty map on read/parse failures.
    """
    try:
        payload = read_json(Path(path))
    except Exception as exc:
        print(f"ERROR: Failed to load inventory file '{path}': {exc}")
        return {}
    result: Dict[Tuple[str, int, int], float] = {}
    for dev in payload.get(KEY_DEVICES, []):
        label = str(dev.get(KEY_LABEL, "")).strip()
        if not label:
            continue
        frame_data = dev.get(KEY_FRAME_DATA, {})
        if not isinstance(frame_data, dict):
            continue
        for frame_name, frame in frame_data.items():
            api_class, api_index = parse_frame_name(frame_name)
            if api_class is None or api_index is None:
                continue
            try:
                period_ms = float(frame.get("period_ms"))
                fps = 1000.0 / period_ms if period_ms > 0 else 0.0
            except Exception:
                fps = 0.0
            result[(label, api_class, api_index)] = fps
    return result


def print_inventory_diff(path_a: str, path_b: str, top_n: int) -> None:
    """
    NAME
        print_inventory_diff - Print a concise diff between inventories.

    PARAMETERS
        path_a: Baseline inventory JSON.
        path_b: Comparison inventory JSON.
        top_n: Number of rows to print for each section.

    SIDE EFFECTS
        Writes a human-readable diff to stdout.
    """
    a = load_inventory(path_a)
    b = load_inventory(path_b)
    keys_a = set(a.keys())
    keys_b = set(b.keys())

    new_pairs = sorted(keys_b - keys_a)
    missing_pairs = sorted(keys_a - keys_b)
    deltas = []
    for key in sorted(keys_a & keys_b):
        fps_a = a.get(key, 0.0)
        fps_b = b.get(key, 0.0)
        delta = fps_b - fps_a
        deltas.append((abs(delta), delta, key, fps_a, fps_b))
    deltas.sort(reverse=True)

    print("=== Inventory Diff ===")
    print(f"New pairs: {len(new_pairs)}")
    for key in new_pairs[:top_n]:
        label, api_class, api_index = key
        print(f"  + label={label} apiClass={api_class} apiIndex={api_index}")
    if len(new_pairs) > top_n:
        print(f"  ... {len(new_pairs) - top_n} more")

    print(f"Missing pairs: {len(missing_pairs)}")
    for key in missing_pairs[:top_n]:
        label, api_class, api_index = key
        print(f"  - label={label} apiClass={api_class} apiIndex={api_index}")
    if len(missing_pairs) > top_n:
        print(f"  ... {len(missing_pairs) - top_n} more")

    print(f"Biggest rate changes (top {top_n}):")
    for _, delta, key, fps_a, fps_b in deltas[:top_n]:
        label, api_class, api_index = key
        print(
            "  "
            f"label={label} apiClass={api_class} apiIndex={api_index} "
            f"fps={fps_a:.2f} -> {fps_b:.2f} (delta {delta:+.2f})"
        )


def load_inventory_snapshot(path: str) -> Optional[Dict[str, Any]]:
    """
    NAME
        load_inventory_snapshot - Load a CAN inventory snapshot JSON file.

    PARAMETERS
        path: Inventory JSON file path.

    RETURNS
        Parsed inventory dict, or None on failure.

    ERRORS
        Prints a concise error and returns None on load/parse failure.
    """
    try:
        payload = read_json(Path(path))
    except Exception as exc:
        print(f"ERROR: Failed to load inventory file '{path}': {exc}")
        return None
    if not isinstance(payload, dict) or "devices" not in payload:
        print(f"ERROR: Invalid inventory schema in '{path}'.")
        return None
    return payload


def compute_inventory_hash(path: str) -> str:
    """
    NAME
        compute_inventory_hash - Compute a stable hash for an inventory file.

    PARAMETERS
        path: Inventory JSON file path.

    RETURNS
        Hex SHA-256 of the raw file bytes.
    """
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()


def build_frame_name(api_class: int, api_index: int) -> str:
    """
    NAME
        build_frame_name - Build a stable frame name for inventory JSON.

    PARAMETERS
        api_class: API class identifier.
        api_index: API index identifier.

    RETURNS
        Frame name string.
    """
    return f"apiClass_{api_class}_apiIndex_{api_index}"


def parse_frame_name(frame_name: str) -> Tuple[Optional[int], Optional[int]]:
    """
    NAME
        parse_frame_name - Extract apiClass/apiIndex from a frame name.

    PARAMETERS
        frame_name: Frame key string.

    RETURNS
        (api_class, api_index) tuple or (None, None) on failure.
    """
    if not isinstance(frame_name, str):
        return None, None
    parts = frame_name.split("_")
    if len(parts) != 4:
        return None, None
    if parts[0] != "apiClass" or parts[2] != "apiIndex":
        return None, None
    try:
        api_class = int(parts[1])
        api_index = int(parts[3])
    except Exception:
        return None, None
    return api_class, api_index


def discover_devices(inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    NAME
        discover_devices - Enumerate device entries from an inventory snapshot.

    PARAMETERS
        inventory: Parsed inventory snapshot dict.

    RETURNS
        List of device dicts.
    """
    devices = inventory.get("devices", [])
    return devices if isinstance(devices, list) else []


def generate_config(
    inventory: Dict[str, Any],
    inventory_path: str,
    profile_name: str,
) -> Dict[str, Any]:
    """
    NAME
        generate_config - Generate a robot config template from inventory.

    PARAMETERS
        inventory: Parsed inventory snapshot dict.
        inventory_path: Source inventory file path.
        profile_name: Robot profile name to embed in metadata.

    RETURNS
        Generated configuration dict.
    """
    devices = discover_devices(inventory)
    config_devices: List[Dict[str, Any]] = []

    for dev in devices:
        label = str(dev.get(KEY_LABEL, "")).strip()
        if not label:
            continue
        config_entry = {
            KEY_LABEL: label,
            KEY_NAME: label,
            KEY_PARAMETERS: {},
            KEY_FRAME_DATA: dev.get(KEY_FRAME_DATA, {}) if isinstance(dev, dict) else {},
        }
        config_devices.append(config_entry)

    metadata = {
        "robot_name": profile_name,
        "generated_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inventory_source": inventory_path,
        "inventory_hash": compute_inventory_hash(inventory_path),
    }

    return {
        KEY_METADATA: metadata,
        KEY_DEVICES: config_devices,
        KEY_DIO_DEVICES: [
            {
                KEY_NAME: DIO_EXAMPLE_NAME,
                "port": None,
                "inverted": None,
                KEY_LINKED_DEVICE: None,
            }
        ],
        KEY_EXTERNAL_ENCODERS: [
            {
                KEY_NAME: ENCODER_EXAMPLE_NAME,
                "type": ENCODER_DEFAULT_TYPE,
                "port": None,
                "offset": None,
                KEY_LINKED_DEVICE: None,
            }
        ],
    }


def compare_inventories(current: Dict[str, Any], previous: Dict[str, Any]) -> None:
    """
    NAME
        compare_inventories - Print device-level differences between inventories.

    PARAMETERS
        current: Current inventory snapshot.
        previous: Previous inventory snapshot.

    SIDE EFFECTS
        Prints a concise diff summary to stdout.
    """
    current_devices = discover_devices(current)
    previous_devices = discover_devices(previous)
    current_labels = set()
    previous_labels = set()

    def add_device(device: Dict[str, Any], labels: set) -> None:
        label = str(device.get(KEY_LABEL, "")).strip()
        if label:
            labels.add(label)

    for dev in current_devices:
        if isinstance(dev, dict):
            add_device(dev, current_labels)
    for dev in previous_devices:
        if isinstance(dev, dict):
            add_device(dev, previous_labels)

    added = sorted(current_labels - previous_labels)
    removed = sorted(previous_labels - current_labels)

    print("=== Inventory Comparison ===")
    print(f"Devices added: {len(added)}")
    for label in added:
        print(f"  + label={label}")
    print(f"Devices removed: {len(removed)}")
    for label in removed:
        print(f"  - label={label}")


def validate_config(
    config: Dict[str, Any],
    tolerance_percent: float,
    inventory_path: Optional[str],
) -> Tuple[bool, List[str], List[str]]:
    """
    NAME
        validate_config - Validate a robot configuration dict.

    PARAMETERS
        config: Parsed config dict to validate.
        tolerance_percent: Frame timing tolerance as percentage.
        inventory_path: Optional inventory file path for hash validation.

    RETURNS
        (is_valid, errors, warnings).
    """
    errors: List[str] = []
    warnings: List[str] = []

    devices = config.get(KEY_DEVICES, [])
    if not isinstance(devices, list):
        errors.append("Config devices must be a list.")
        return False, errors, warnings

    seen_labels = set()
    for device in devices:
        if not isinstance(device, dict):
            errors.append("Device entry must be an object.")
            continue
        label = str(device.get(KEY_LABEL, "")).strip()
        name = device.get(KEY_NAME, "")
        if not label:
            errors.append("Device entry missing label.")
            continue
        if label in seen_labels:
            errors.append(f"Duplicate device label '{label}'.")
        seen_labels.add(label)
        if not isinstance(name, str) or not name:
            warnings.append(f"Device '{label}' missing display name.")

    for device in config.get(KEY_DIO_DEVICES, []) or []:
        if not isinstance(device, dict):
            errors.append("DIO device entry must be an object.")
            continue
        linked = device.get(KEY_LINKED_DEVICE)
        if linked is not None and linked not in seen_labels:
            errors.append(f"DIO device '{device.get(KEY_NAME)}' links to unknown label '{linked}'.")

    for device in config.get(KEY_EXTERNAL_ENCODERS, []) or []:
        if not isinstance(device, dict):
            errors.append("External encoder entry must be an object.")
            continue
        linked = device.get(KEY_LINKED_DEVICE)
        if linked is not None and linked not in seen_labels:
            errors.append(f"External encoder '{device.get(KEY_NAME)}' links to unknown label '{linked}'.")

    if inventory_path:
        try:
            current_hash = compute_inventory_hash(inventory_path)
            config_meta = config.get("metadata") or {}
            config_hash = config_meta.get("inventory_hash")
            if not config_hash:
                warnings.append("Config metadata missing inventory_hash.")
            elif config_hash != current_hash:
                warnings.append(
                    "Inventory hash does not match provided inventory file "
                    f"({config_hash} != {current_hash})."
                )
            config_source = config_meta.get("inventory_source")
            if config_source and config_source != inventory_path:
                warnings.append(
                    f"inventory_source '{config_source}' does not match provided inventory path '{inventory_path}'."
                )
        except Exception as exc:
            warnings.append(f"Failed to compute inventory hash: {exc}")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def write_config(path: str, config: Dict[str, Any]) -> bool:
    """
    NAME
        write_config - Write a config dict to disk.

    PARAMETERS
        path: Output JSON file path.
        config: Config dict to serialize.

    RETURNS
        True on success, False on failure.
    """
    try:
        write_json(Path(path), config, indent=2, trailing_newline=False)
        return True
    except Exception as exc:
        print(f"ERROR: Failed to write config '{path}': {exc}")
        return False


def read_config(path: str) -> Optional[Dict[str, Any]]:
    """
    NAME
        read_config - Load a config JSON file.

    PARAMETERS
        path: Config JSON file path.

    RETURNS
        Parsed config dict, or None on failure.
    """
    try:
        return read_json(Path(path))
    except Exception as exc:
        print(f"ERROR: Failed to load config file '{path}': {exc}")
        return None


def print_help() -> None:
    """
    NAME
        print_help - Print CLI usage information.
    """
    print("Usage:")
    print("  python -m tools.can_inventory.can_inventory --generate --input <inventory.json> --output <config.json> --profileName <name>")
    print("       [--compare <inventory.json>] [--timing-tolerance-percent <percent>]")
    print("  python -m tools.can_inventory.can_inventory --validate --input <config.json> [--timing-tolerance-percent <percent>]")
    print("       [--inventory <inventory.json>] [--update-hash]")
    print("  python -m tools.can_inventory.can_inventory --interactive")
    print("  python -m tools.can_inventory.can_inventory --help")


def parse_args(argv: List[str]) -> Dict[str, Any]:
    """
    NAME
        parse_args - Parse CLI arguments into a dict.
    """
    args: Dict[str, Any] = {
        "mode": None,
        "input": None,
        "output": None,
        "profileName": None,
        "compare": None,
        "timing_tolerance_percent": 10.0,
        "inventory": None,
        "update_hash": False,
    }
    it = iter(argv)
    for token in it:
        if token == "--generate":
            args["mode"] = "generate"
        elif token == "--validate":
            args["mode"] = "validate"
        elif token == "--interactive":
            args["mode"] = "interactive"
        elif token == "--help":
            args["mode"] = "help"
        elif token == "--input":
            args["input"] = next(it, None)
        elif token == "--output":
            args["output"] = next(it, None)
        elif token == "--profileName":
            args["profileName"] = next(it, None)
        elif token == "--compare":
            args["compare"] = next(it, None)
        elif token == "--inventory":
            args["inventory"] = next(it, None)
        elif token == "--update-hash":
            args["update_hash"] = True
        elif token == "--timing-tolerance-percent":
            value = next(it, None)
            try:
                args["timing_tolerance_percent"] = float(value)
            except Exception:
                print(f"ERROR: Invalid timing tolerance percent '{value}'.")
                args["timing_tolerance_percent"] = None
        else:
            print(f"ERROR: Unknown argument '{token}'.")
            args["mode"] = "help"
            return args
    return args


def run_generate(args: Dict[str, Any]) -> int:
    """
    NAME
        run_generate - Run config generation workflow.
    """
    inventory_path = args.get("input")
    output_path = args.get("output")
    profile_name = args.get("profileName")
    compare_path = args.get("compare")

    if not inventory_path or not output_path or not profile_name:
        print("ERROR: --generate requires --input, --output, and --profileName.")
        return 2
    inventory = load_inventory_snapshot(inventory_path)
    if inventory is None:
        return 2

    if compare_path:
        previous = load_inventory_snapshot(compare_path)
        if previous:
            compare_inventories(inventory, previous)

    config = generate_config(inventory, inventory_path, profile_name)
    if not write_config(output_path, config):
        return 2

    print("Inventory scan complete")
    print(f"Devices detected: {len(config['devices'])}")
    print(f"Config file written to {output_path}")
    return 0


def run_validate(args: Dict[str, Any]) -> int:
    """
    NAME
        run_validate - Run config validation workflow.
    """
    config_path = args.get("input")
    tolerance = args.get("timing_tolerance_percent")
    inventory_path = args.get("inventory")
    update_hash = args.get("update_hash", False)
    if tolerance is None:
        return 2
    if config_path is None:
        print("ERROR: --validate requires --input.")
        return 2
    config = read_config(config_path)
    if config is None:
        return 2
    if update_hash and not inventory_path:
        print("ERROR: --update-hash requires --inventory.")
        return 2
    is_valid, errors, warnings = validate_config(config, tolerance, inventory_path)
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        print("NOTE: Frame timing tolerance defaults to 10% and may need tuning.")
    if not is_valid:
        print("Validation failed")
        for error in errors:
            print(f"  - {error}")
        return 2
    if update_hash and inventory_path:
        try:
            config.setdefault("metadata", {})
            config["metadata"]["inventory_hash"] = compute_inventory_hash(inventory_path)
            config["metadata"]["inventory_source"] = inventory_path
            if not write_config(config_path, config):
                return 2
            print("Updated inventory hash in config.")
        except Exception as exc:
            print(f"ERROR: Failed to update inventory hash: {exc}")
            return 2
    print("Validation passed")
    return 0


def run_interactive(args: Dict[str, Any]) -> int:
    """
    NAME
        run_interactive - Stub interactive workflow.
    """
    print("Interactive mode is not implemented yet.")
    return 2


def main(argv: List[str]) -> int:
    """
    NAME
        main - CLI entry point for config generation and validation.
    """
    args = parse_args(argv)
    mode = args.get("mode")
    if mode == "help" or mode is None:
        print_help()
        return 0
    if mode == "generate":
        return run_generate(args)
    if mode == "validate":
        return run_validate(args)
    if mode == "interactive":
        return run_interactive(args)
    print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
