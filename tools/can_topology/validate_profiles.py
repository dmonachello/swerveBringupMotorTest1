from __future__ import annotations

"""
NAME
    validate_profiles.py - Validate bringup_profiles.json compatibility.

SYNOPSIS
    python tools\\can_topology\\validate_profiles.py [--path PATH] [--strict]

DESCRIPTION
    Checks bringup profile JSON for schema errors, duplicate CAN IDs, and
    invalid limits so that output is compatible with the robot and PC tools.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BUCKET_CATEGORIES = [
    "neos",
    "neo550s",
    "flexes",
    "krakens",
    "falcons",
    "cancoders",
    "candles",
]
SINGLETON_CATEGORIES = ["pdh", "pdp", "pigeon", "roborio"]
GENERIC_CATEGORY = "devices"
ALLOWED_PROFILE_KEYS = set(BUCKET_CATEGORIES + SINGLETON_CATEGORIES + [GENERIC_CATEGORY, "notes", "unknown"])


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    NAME
        parse_args - Parse CLI arguments.

    RETURNS
        argparse.Namespace with parsed args.
    """
    parser = argparse.ArgumentParser(description="Validate bringup_profiles.json compatibility.")
    parser.add_argument(
        "--path",
        default=str(Path("src") / "main" / "deploy" / "bringup_profiles.json"),
        help="Path to bringup_profiles.json",
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
        raise ValueError(f"File not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to parse JSON: {exc}") from exc


def validate_profiles(payload: Dict[str, Any], reporter: "Reporter") -> Tuple[List[str], List[str]]:
    """
    NAME
        validate_profiles - Validate the root payload and each profile.

    RETURNS
        (errors, warnings) lists.
    """
    errors: List[str] = []
    warnings: List[str] = []

    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        msg = "Root 'profiles' must be a non-empty object."
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings
    reporter.pass_("Root 'profiles' is a non-empty object.")

    default_profile = payload.get("default_profile")
    if not isinstance(default_profile, str) or not default_profile:
        msg = "Root 'default_profile' is missing or empty."
        warnings.append(msg)
        reporter.warn(msg)
    elif default_profile not in profiles:
        msg = f"Root 'default_profile' '{default_profile}' not found in profiles."
        warnings.append(msg)
        reporter.warn(msg)
    else:
        reporter.pass_("Root 'default_profile' present in profiles.")

    for name, profile in profiles.items():
        profile_errors, profile_warnings = validate_profile(name, profile, reporter)
        errors.extend(profile_errors)
        warnings.extend(profile_warnings)

    return errors, warnings


def validate_profile(name: str, profile: Any, reporter: "Reporter") -> Tuple[List[str], List[str]]:
    """
    NAME
        validate_profile - Validate one profile section.

    RETURNS
        (errors, warnings) lists.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(profile, dict):
        msg = f"Profile '{name}' must be an object."
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings
    reporter.pass_(f"Profile '{name}' is an object.")

    for key in profile.keys():
        if key not in ALLOWED_PROFILE_KEYS:
            msg = f"Profile '{name}' has unknown key '{key}'."
            warnings.append(msg)
            reporter.warn(msg)

    seen_ids: Dict[int, str] = {}

    for category in BUCKET_CATEGORIES:
        entries = profile.get(category, [])
        if entries is None:
            continue
        if not isinstance(entries, list):
            msg = f"Profile '{name}' category '{category}' must be a list."
            errors.append(msg)
            reporter.fail(msg)
            continue
        reporter.pass_(f"Profile '{name}' category '{category}' is a list.")
        for entry in entries:
            entry_errors, entry_warnings, can_id = validate_entry(
                name, category, entry, reporter
            )
            errors.extend(entry_errors)
            warnings.extend(entry_warnings)
            if can_id is not None and can_id >= 0:
                register_can_id(seen_ids, errors, reporter, name, can_id, entry)

    for category in SINGLETON_CATEGORIES:
        entry = profile.get(category)
        if entry is None:
            continue
        if not isinstance(entry, dict):
            msg = f"Profile '{name}' category '{category}' must be an object."
            errors.append(msg)
            reporter.fail(msg)
            continue
        reporter.pass_(f"Profile '{name}' category '{category}' is an object.")
        entry_errors, entry_warnings, can_id = validate_entry(
            name, category, entry, reporter
        )
        errors.extend(entry_errors)
        warnings.extend(entry_warnings)
        if can_id is not None and can_id >= 0:
            register_can_id(seen_ids, errors, reporter, name, can_id, entry)

    entries = profile.get(GENERIC_CATEGORY, [])
    if entries is not None:
        if not isinstance(entries, list):
            msg = f"Profile '{name}' category '{GENERIC_CATEGORY}' must be a list."
            errors.append(msg)
            reporter.fail(msg)
        else:
            reporter.pass_(f"Profile '{name}' category '{GENERIC_CATEGORY}' is a list.")
            for entry in entries:
                entry_errors, entry_warnings, can_id = validate_entry(
                    name,
                    GENERIC_CATEGORY,
                    entry,
                    reporter,
                    require_vendor_type=True,
                )
                errors.extend(entry_errors)
                warnings.extend(entry_warnings)
                if can_id is not None and can_id >= 0:
                    register_can_id(seen_ids, errors, reporter, name, can_id, entry)

    return errors, warnings


def register_can_id(
    seen_ids: Dict[int, str],
    errors: List[str],
    reporter: "Reporter",
    profile_name: str,
    can_id: int,
    entry: Dict[str, Any],
) -> None:
    """
    NAME
        register_can_id - Track CAN IDs and flag duplicates.
    """
    label = entry.get("label") or f"id {can_id}"
    if can_id in seen_ids:
        other = seen_ids[can_id]
        msg = f"Profile '{profile_name}' duplicate CAN ID {can_id} ({other}, {label})."
        errors.append(msg)
        reporter.fail(msg)
        return
    seen_ids[can_id] = str(label)
    reporter.pass_(f"Profile '{profile_name}' CAN ID {can_id} unique.")


def validate_entry(
    profile_name: str,
    category: str,
    entry: Any,
    reporter: "Reporter",
    require_vendor_type: bool = False,
) -> Tuple[List[str], List[str], Optional[int]]:
    """
    NAME
        validate_entry - Validate a single device entry.

    RETURNS
        (errors, warnings, can_id) tuple.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(entry, dict):
        msg = f"Profile '{profile_name}' category '{category}' entries must be objects."
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings, None
    reporter.pass_(f"Profile '{profile_name}' category '{category}' entry is an object.")

    can_id = entry.get("id")
    if not isinstance(can_id, int):
        msg = f"Profile '{profile_name}' entry '{entry}' missing integer 'id'."
        errors.append(msg)
        reporter.fail(msg)
        return errors, warnings, None
    reporter.pass_(f"Profile '{profile_name}' entry id {can_id} has integer CAN ID.")
    if can_id < -1 or can_id > 62:
        msg = (
            f"Profile '{profile_name}' entry '{entry.get('label')}' has invalid CAN ID {can_id}."
        )
        errors.append(msg)
        reporter.fail(msg)
    else:
        reporter.pass_(f"Profile '{profile_name}' entry id {can_id} is in range.")

    label = entry.get("label")
    if label is not None and not isinstance(label, str):
        msg = f"Profile '{profile_name}' entry id {can_id} has non-string label."
        errors.append(msg)
        reporter.fail(msg)
    else:
        reporter.pass_(f"Profile '{profile_name}' entry id {can_id} label type ok.")

    if require_vendor_type:
        vendor = entry.get("vendor")
        device_type = entry.get("type")
        if not isinstance(vendor, str) or not vendor.strip():
            msg = f"Profile '{profile_name}' entry id {can_id} missing vendor."
            errors.append(msg)
            reporter.fail(msg)
        else:
            reporter.pass_(f"Profile '{profile_name}' entry id {can_id} vendor set.")
        if not isinstance(device_type, str) or not device_type.strip():
            msg = f"Profile '{profile_name}' entry id {can_id} missing type."
            errors.append(msg)
            reporter.fail(msg)
        else:
            reporter.pass_(f"Profile '{profile_name}' entry id {can_id} type set.")

    limits = entry.get("limits")
    if limits is not None:
        if not isinstance(limits, dict):
            msg = f"Profile '{profile_name}' entry id {can_id} limits must be an object."
            errors.append(msg)
            reporter.fail(msg)
        else:
            reporter.pass_(f"Profile '{profile_name}' entry id {can_id} limits is object.")
            validate_limits(profile_name, can_id, limits, errors, warnings, reporter)

    terminator = entry.get("terminator")
    if terminator is not None and not isinstance(terminator, bool):
        msg = f"Profile '{profile_name}' entry id {can_id} terminator must be boolean."
        errors.append(msg)
        reporter.fail(msg)
    elif terminator is not None:
        reporter.pass_(f"Profile '{profile_name}' entry id {can_id} terminator is boolean.")

    tags = entry.get("tags")
    if tags is not None:
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
            msg = f"Profile '{profile_name}' entry id {can_id} tags must be a list of non-empty strings."
            errors.append(msg)
            reporter.fail(msg)
        else:
            reporter.pass_(f"Profile '{profile_name}' entry id {can_id} tags are valid.")

    return errors, warnings, can_id


def validate_limits(
    profile_name: str,
    can_id: int,
    limits: Dict[str, Any],
    errors: List[str],
    warnings: List[str],
    reporter: "Reporter",
) -> None:
    """
    NAME
        validate_limits - Validate limit switch fields for an entry.
    """
    for key in ("fwdDio", "revDio"):
        value = limits.get(key, -1)
        if not isinstance(value, int):
            msg = f"Profile '{profile_name}' entry id {can_id} {key} must be an integer."
            errors.append(msg)
            reporter.fail(msg)
        elif value < -1:
            msg = (
                f"Profile '{profile_name}' entry id {can_id} {key} must be -1 or greater."
            )
            errors.append(msg)
            reporter.fail(msg)
        else:
            reporter.pass_(f"Profile '{profile_name}' entry id {can_id} {key} ok.")
    invert = limits.get("invert")
    if invert is not None and not isinstance(invert, bool):
        msg = f"Profile '{profile_name}' entry id {can_id} invert must be boolean."
        errors.append(msg)
        reporter.fail(msg)
    elif invert is not None:
        reporter.pass_(f"Profile '{profile_name}' entry id {can_id} invert is boolean.")
    if invert is None:
        msg = f"Profile '{profile_name}' entry id {can_id} limits missing 'invert' flag."
        warnings.append(msg)
        reporter.warn(msg)


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
