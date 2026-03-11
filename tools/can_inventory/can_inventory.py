from __future__ import annotations

"""
NAME
    can_inventory.py - API inventory snapshot and diff helpers.

SYNOPSIS
    from tools.can_inventory.can_inventory import dump_api_inventory, print_inventory_diff

DESCRIPTION
    Builds a stable JSON inventory of observed (apiClass, apiIndex) pairs per
    device and compares inventories between runs.
"""

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEVICE_REGISTRY: Dict[Tuple[int, int], Dict[str, Any]] = {
    (4, 2): {
        "device_name": "TalonFX",
        "required_params": ["gear_ratio", "inverted"],
        "optional_params": ["current_limit"],
        "expected_frames": {
            "status_1": 10,
            "status_2": 20,
        },
    },
    (9, 1): {
        "device_name": "CANcoder",
        "required_params": [],
        "optional_params": [],
        "expected_frames": {
            "position": 20,
        },
    },
}


def dump_api_inventory(
    path: str,
    profile: str,
    interface: str,
    channel: str,
    bitrate: int,
    pairs: Dict[Tuple[int, int, int, int, int], Dict[str, float]],
) -> None:
    """
    NAME
        dump_api_inventory - Persist per-device API pair statistics.

    PARAMETERS
        path: Output JSON file path.
        profile: Active profile name.
        interface: CAN interface type (e.g., slcan).
        channel: CAN channel (e.g., COM port).
        bitrate: CAN bitrate in bps.
        pairs: Observed pair stats keyed by (mfg,type,id,apiClass,apiIndex).

    SIDE EFFECTS
        Writes a JSON file to disk.
    """
    devices: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
    for (mfg, dtype, did, api_class, api_index), stats in pairs.items():
        key = (mfg, dtype, did)
        duration = max(0.0, stats["last"] - stats["first"])
        fps = (stats["count"] / duration) if duration > 0 else 0.0
        entry = {
            "apiClass": api_class,
            "apiIndex": api_index,
            "count": int(stats["count"]),
            "firstSeen": stats["first"],
            "lastSeen": stats["last"],
            "fps": fps,
        }
        devices.setdefault(key, []).append(entry)

    payload = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
        "profile": profile,
        "interface": interface,
        "channel": channel,
        "bitrate": bitrate,
        "devices": [
            {
                "mfg": mfg,
                "type": dtype,
                "id": did,
                "pairs": sorted(pairs, key=lambda p: (p["apiClass"], p["apiIndex"])),
            }
            for (mfg, dtype, did), pairs in sorted(devices.items())
        ],
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as exc:
        print(f"ERROR: Failed to write API inventory '{path}': {exc}")


def load_inventory(path: str) -> Dict[Tuple[int, int, int, int, int], float]:
    """
    NAME
        load_inventory - Load inventory JSON into a keyed fps map.

    PARAMETERS
        path: Inventory JSON file path.

    RETURNS
        Mapping of (mfg,type,id,apiClass,apiIndex) -> fps.

    ERRORS
        Prints a warning and returns empty map on read/parse failures.
    """
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: Failed to load inventory file '{path}': {exc}")
        return {}
    result: Dict[Tuple[int, int, int, int, int], float] = {}
    for dev in payload.get("devices", []):
        try:
            mfg = int(dev.get("mfg"))
            dtype = int(dev.get("type"))
            did = int(dev.get("id"))
        except Exception:
            continue
        for pair in dev.get("pairs", []):
            try:
                api_class = int(pair.get("apiClass"))
                api_index = int(pair.get("apiIndex"))
                fps = float(pair.get("fps", 0.0))
            except Exception:
                continue
            result[(mfg, dtype, did, api_class, api_index)] = fps
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
        mfg, dtype, did, api_class, api_index = key
        print(f"  + mfg={mfg} type={dtype} id={did} apiClass={api_class} apiIndex={api_index}")
    if len(new_pairs) > top_n:
        print(f"  ... {len(new_pairs) - top_n} more")

    print(f"Missing pairs: {len(missing_pairs)}")
    for key in missing_pairs[:top_n]:
        mfg, dtype, did, api_class, api_index = key
        print(f"  - mfg={mfg} type={dtype} id={did} apiClass={api_class} apiIndex={api_index}")
    if len(missing_pairs) > top_n:
        print(f"  ... {len(missing_pairs) - top_n} more")

    print(f"Biggest rate changes (top {top_n}):")
    for _, delta, key, fps_a, fps_b in deltas[:top_n]:
        mfg, dtype, did, api_class, api_index = key
        print(
            "  "
            f"mfg={mfg} type={dtype} id={did} apiClass={api_class} apiIndex={api_index} "
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
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
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


def normalize_device_type_name(name: str) -> str:
    """
    NAME
        normalize_device_type_name - Normalize a device type for placeholder names.

    PARAMETERS
        name: Device name string.

    RETURNS
        Uppercase name with non-alphanumeric characters replaced by underscores.
    """
    out = []
    for ch in name.upper():
        out.append(ch if ch.isalnum() else "_")
    return "".join(out).strip("_") or "UNKNOWN"


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


def lookup_registry_by_ids(
    manufacturer_id: Optional[int],
    device_type_id: Optional[int],
) -> Optional[Dict[str, Any]]:
    """
    NAME
        lookup_registry_by_ids - Lookup registry entry by numeric IDs.

    PARAMETERS
        manufacturer_id: Manufacturer ID.
        device_type_id: Device type ID.

    RETURNS
        Registry entry dict or None if not found.
    """
    if manufacturer_id is None or device_type_id is None:
        return None
    return DEVICE_REGISTRY.get((manufacturer_id, device_type_id))


def lookup_registry_by_name(device_type: str) -> Optional[Dict[str, Any]]:
    """
    NAME
        lookup_registry_by_name - Lookup registry entry by device type name.

    PARAMETERS
        device_type: Device type string.

    RETURNS
        Registry entry dict or None if not found.
    """
    if not device_type:
        return None
    for entry in DEVICE_REGISTRY.values():
        if entry.get("device_name") == device_type:
            return entry
    return None


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
    unrecognized: List[Dict[str, Any]] = []
    config_devices: List[Dict[str, Any]] = []

    for dev in devices:
        try:
            can_id = int(dev.get("can_id"))
        except Exception:
            can_id = None
        manufacturer_id = dev.get("manufacturer_id")
        device_type_id = dev.get("device_type_id")
        registry = lookup_registry_by_ids(
            int(manufacturer_id) if manufacturer_id is not None else None,
            int(device_type_id) if device_type_id is not None else None,
        )
        device_name = dev.get("device_name") or (registry.get("device_name") if registry else None) or "UNKNOWN"
        normalized = normalize_device_type_name(device_name)
        config_entry = {
            "can_id": can_id,
            "type": device_name,
            "name": f"UNNAMED_{normalized}_{can_id}" if can_id is not None else f"UNNAMED_{normalized}",
            "parameters": {},
            "frame_data": dev.get("frame_data", {}) if isinstance(dev, dict) else {},
        }
        if registry:
            for param in registry.get("required_params", []):
                config_entry["parameters"][param] = None
        else:
            unrecognized.append(dev)
        config_devices.append(config_entry)

    metadata = {
        "robot_name": profile_name,
        "generated_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inventory_source": inventory_path,
        "inventory_hash": compute_inventory_hash(inventory_path),
        "inventory_metadata": inventory.get("metadata", {}),
    }

    return {
        "metadata": metadata,
        "devices": config_devices,
        "subsystems": {},
        "unrecognized_devices": unrecognized,
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
    current_keys = set()
    previous_keys = set()
    current_by_type: Dict[Tuple[int, int], List[int]] = {}
    previous_by_type: Dict[Tuple[int, int], List[int]] = {}

    def add_device(device: Dict[str, Any], keys: set, by_type: Dict[Tuple[int, int], List[int]]) -> None:
        try:
            can_id = int(device.get("can_id"))
            mfg = int(device.get("manufacturer_id"))
            dtype = int(device.get("device_type_id"))
        except Exception:
            return
        keys.add((mfg, dtype, can_id))
        by_type.setdefault((mfg, dtype), []).append(can_id)

    for dev in current_devices:
        if isinstance(dev, dict):
            add_device(dev, current_keys, current_by_type)
    for dev in previous_devices:
        if isinstance(dev, dict):
            add_device(dev, previous_keys, previous_by_type)

    added = sorted(current_keys - previous_keys)
    removed = sorted(previous_keys - current_keys)

    print("=== Inventory Comparison ===")
    print(f"Devices added: {len(added)}")
    for mfg, dtype, can_id in added:
        print(f"  + mfg={mfg} type={dtype} can_id={can_id}")
    print(f"Devices removed: {len(removed)}")
    for mfg, dtype, can_id in removed:
        print(f"  - mfg={mfg} type={dtype} can_id={can_id}")

    id_changes = []
    for key in set(current_by_type.keys()) | set(previous_by_type.keys()):
        before = set(previous_by_type.get(key, []))
        after = set(current_by_type.get(key, []))
        added_ids = sorted(after - before)
        removed_ids = sorted(before - after)
        if added_ids and removed_ids:
            id_changes.append((key, added_ids, removed_ids))
    print(f"CAN ID changes: {len(id_changes)}")
    for (mfg, dtype), added_ids, removed_ids in id_changes:
        print(f"  * mfg={mfg} type={dtype} added={added_ids} removed={removed_ids}")


def validate_config(
    config: Dict[str, Any],
    tolerance_percent: float,
) -> Tuple[bool, List[str], List[str], List[Dict[str, Any]]]:
    """
    NAME
        validate_config - Validate a robot configuration dict.

    PARAMETERS
        config: Parsed config dict to validate.
        tolerance_percent: Frame timing tolerance as percentage.

    RETURNS
        (is_valid, errors, warnings, unrecognized_devices).
    """
    errors: List[str] = []
    warnings: List[str] = []
    unrecognized: List[Dict[str, Any]] = []

    devices = config.get("devices", [])
    if not isinstance(devices, list):
        errors.append("Config devices must be a list.")
        return False, errors, warnings, unrecognized

    seen_can_ids = set()
    for device in devices:
        if not isinstance(device, dict):
            errors.append("Device entry must be an object.")
            continue
        can_id = device.get("can_id")
        device_type = device.get("type", "")
        name = device.get("name", "")
        parameters = device.get("parameters", {})
        frame_data = device.get("frame_data", {})

        if can_id is None:
            errors.append(f"Device '{name}' missing can_id.")
        else:
            if can_id in seen_can_ids:
                errors.append(f"Duplicate CAN ID {can_id}.")
            seen_can_ids.add(can_id)

        if isinstance(name, str) and name.startswith("UNNAMED_"):
            errors.append(f"Device '{name}' has placeholder name.")

        registry = lookup_registry_by_name(device_type)
        if registry is None:
            unrecognized.append(device)
            warnings.append(f"Unrecognized device type '{device_type}'.")
            continue

        required = registry.get("required_params", [])
        for param in required:
            if not isinstance(parameters, dict) or parameters.get(param) is None:
                errors.append(f"Device '{name}' missing required parameter '{param}'.")

        expected_frames = registry.get("expected_frames", {})
        if expected_frames and isinstance(frame_data, dict):
            for frame_name, expected_period in expected_frames.items():
                frame = frame_data.get(frame_name)
                if not isinstance(frame, dict):
                    continue
                actual = frame.get("period_ms")
                if actual is None:
                    continue
                try:
                    actual_val = float(actual)
                    expected_val = float(expected_period)
                except Exception:
                    continue
                if expected_val <= 0:
                    continue
                deviation = abs(actual_val - expected_val) / expected_val * 100.0
                if deviation > tolerance_percent:
                    warnings.append(
                        f"Frame '{frame_name}' for device '{name}' deviates by "
                        f"{deviation:.1f}% (expected {expected_val}ms, got {actual_val}ms)."
                    )

    is_valid = len(errors) == 0
    return is_valid, errors, warnings, unrecognized


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
        Path(path).write_text(json.dumps(config, indent=2), encoding="utf-8")
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
        return json.loads(Path(path).read_text(encoding="utf-8"))
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

    recognized = len(config["devices"]) - len(config["unrecognized_devices"])
    print("Inventory scan complete")
    print(f"Devices detected: {len(config['devices'])}")
    print(f"Recognized: {recognized}")
    print(f"Unrecognized: {len(config['unrecognized_devices'])}")
    print(f"Config file written to {output_path}")
    return 0


def run_validate(args: Dict[str, Any]) -> int:
    """
    NAME
        run_validate - Run config validation workflow.
    """
    config_path = args.get("input")
    tolerance = args.get("timing_tolerance_percent")
    if tolerance is None:
        return 2
    if config_path is None:
        print("ERROR: --validate requires --input.")
        return 2
    config = read_config(config_path)
    if config is None:
        return 2
    is_valid, errors, warnings, unrecognized = validate_config(config, tolerance)
    if unrecognized:
        config["unrecognized_devices"] = unrecognized
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
    print("Validation passed")
    return 0


def run_interactive(args: Dict[str, Any]) -> int:
    """
    NAME
        run_interactive - Prompt for inputs and run generate + validate.
    """
    inventory_path = input("Inventory file path: ").strip()
    output_path = input("Output config path: ").strip()
    profile_name = input("Robot profile name: ").strip()
    args["input"] = inventory_path
    args["output"] = output_path
    args["profileName"] = profile_name
    result = run_generate(args)
    if result != 0:
        return result
    args["input"] = output_path
    return run_validate(args)


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
