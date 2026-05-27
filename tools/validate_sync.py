from __future__ import annotations

"""
NAME
    validate_sync.py - Validate and stamp the deploy-owned bringup_system.json.

SYNOPSIS
    python -m tools.validate_sync [--lenient] [--no-stamp] [--validate-deploy] [--no-write]

DESCRIPTION
    Provides a single "validate + sync" gate for device configuration and tests.

    Validates the unified config:
      src/main/deploy/bringup_system.json

    Validation covers:
    - Schema version and required root fields.
    - Semantic references across profiles, device registry, attachments, and
      bridgeConfig tests (per-profile).

    On success, optionally stamps:
    - data_version
    - data_hash

    Then writes:
    - src/main/deploy/bringup_system.json

SIDE EFFECTS
    Writes JSON files when --no-write is not set.

ERRORS
    Exits nonzero on validation errors or write failures.
"""

import argparse
from pathlib import Path
from typing import List

from tools.common.json_io import read_json
from tools.common.paths import repo_root as repo_root_path
from tools.common.config_lifecycle import ConfigLifecycleService
from tools.common.profile_constants import (
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_SCHEMA_VERSION,
    PROFILE_SCHEMA_VERSION,
)
from tools.common.profile_io import compute_profiles_hash, validate_profiles_schema
from tools.common.time_utils import timestamp_version
from tools.config.schema_store import (
    ConfigSchemaStore,
    LOCATION_PROFILES,
    LOCATION_TESTS,
    SEVERITY_ERROR,
)


# Constants (CLI).
ARG_LENIENT = "--lenient"
ARG_NO_STAMP = "--no-stamp"
ARG_VALIDATE_DEPLOY = "--validate-deploy"
ARG_NO_WRITE = "--no-write"
ARG_WARNINGS = "--warnings"

# Constants (messages).
MSG_ERROR = "ERROR"
MSG_WARNING = "WARNING"
MSG_ERR_READ = "ERROR: failed to read {path}: {error}"
MSG_ERR_ROOT_OBJECT = "ERROR: {path} root must be a JSON object."
MSG_ERR_SCHEMA_INVALID = "ERROR: schema invalid: {error}"
MSG_ERR_WRITE = "ERROR: failed to write outputs: {error}"
MSG_OK_VALIDATED_NO_WRITE = "OK: validated (no write)."
MSG_OK_SYNCED = "OK: validated and synced -> {path}"
MSG_ERR_DEPLOY_READ = "ERROR: failed to read deploy copy {path}: {error}"
MSG_ERR_DEPLOY_SCHEMA = "ERROR: deploy schema invalid: {error}"
MSG_FMT_ISSUE = "{level} [{location}]: {message}"

# Constants (exit codes).
EXIT_OK = 0
EXIT_ERROR = 2


def _parse_args() -> argparse.Namespace:
    """
    NAME
        _parse_args - Parse CLI args.
    """

    parser = argparse.ArgumentParser(
        description="Validate and stamp the deploy-owned bringup_system.json."
    )
    parser.add_argument(
        ARG_LENIENT,
        action="store_true",
        help="Lenient validation (unknown keys become warnings).",
    )
    parser.add_argument(
        ARG_NO_STAMP,
        action="store_true",
        help="Do not update data_version/data_hash; only validate and sync.",
    )
    parser.add_argument(
        ARG_VALIDATE_DEPLOY,
        action="store_true",
        help="Validate the deploy copy after writing (schema + hash).",
    )
    parser.add_argument(
        ARG_NO_WRITE,
        action="store_true",
        help="Validate only; do not write any files.",
    )
    parser.add_argument(
        ARG_WARNINGS,
        action="store_true",
        help="Print validation warnings (default: only errors).",
    )
    return parser.parse_args()


def _filter_profile_test_issues(issues) -> List[object]:
    """
    NAME
        _filter_profile_test_issues - Keep issues for profiles/tests only.
    """

    keep = {LOCATION_PROFILES, LOCATION_TESTS}
    return [issue for issue in issues if getattr(issue, "location", None) in keep]


def main() -> int:
    """
    NAME
        main - Validate and sync entry point.
    """

    args = _parse_args()
    repo_root = repo_root_path()
    lifecycle = ConfigLifecycleService()
    lifecycle_paths = lifecycle.default_paths()
    canonical_path = lifecycle_paths.canonical_profiles_path
    deploy_path = lifecycle_paths.deploy_profiles_path

    store = ConfigSchemaStore()
    store.load(repo_root)
    strict = not bool(args.lenient)
    result = store.validate(strict=strict)

    issues = _filter_profile_test_issues(result.issues)
    errors = [issue for issue in issues if getattr(issue, "severity", None) == SEVERITY_ERROR]
    warnings = [issue for issue in issues if getattr(issue, "severity", None) != SEVERITY_ERROR]

    if errors:
        for issue in errors:
            location = getattr(issue, "location", "unknown")
            message = getattr(issue, "message", "")
            print(MSG_FMT_ISSUE.format(level=MSG_ERROR, location=location, message=message))
        if args.warnings and warnings:
            for issue in warnings:
                location = getattr(issue, "location", "unknown")
                message = getattr(issue, "message", "")
                print(MSG_FMT_ISSUE.format(level=MSG_WARNING, location=location, message=message))
        return EXIT_ERROR

    if args.warnings and warnings:
        for issue in warnings:
            location = getattr(issue, "location", "unknown")
            message = getattr(issue, "message", "")
            print(MSG_FMT_ISSUE.format(level=MSG_WARNING, location=location, message=message))

    try:
        payload = read_json(canonical_path)
    except Exception as exc:
        print(MSG_ERR_READ.format(path=canonical_path, error=exc))
        return EXIT_ERROR
    if not isinstance(payload, dict):
        print(MSG_ERR_ROOT_OBJECT.format(path=canonical_path))
        return EXIT_ERROR

    ok, err = validate_profiles_schema(payload, PROFILE_SCHEMA_VERSION)
    if not ok:
        print(MSG_ERR_SCHEMA_INVALID.format(error=err))
        return EXIT_ERROR

    if not args.no_stamp:
        payload[KEY_SCHEMA_VERSION] = PROFILE_SCHEMA_VERSION
        payload[KEY_DATA_VERSION] = timestamp_version()
        payload[KEY_DATA_HASH] = compute_profiles_hash(payload)

    if args.no_write:
        print(MSG_OK_VALIDATED_NO_WRITE)
        return EXIT_OK

    try:
        lifecycle.sync_profiles_payload(
            payload,
            canonical_path=canonical_path,
            deploy_path=deploy_path,
            stamp=False,
        )
    except Exception as exc:
        print(MSG_ERR_WRITE.format(error=exc))
        return EXIT_ERROR

    if args.validate_deploy:
        try:
            deployed = read_json(deploy_path)
        except Exception as exc:
            print(MSG_ERR_DEPLOY_READ.format(path=deploy_path, error=exc))
            return EXIT_ERROR
        if not isinstance(deployed, dict):
            print(MSG_ERR_ROOT_OBJECT.format(path=deploy_path))
            return EXIT_ERROR
        ok, err = validate_profiles_schema(deployed, PROFILE_SCHEMA_VERSION)
        if not ok:
            print(MSG_ERR_DEPLOY_SCHEMA.format(error=err))
            return EXIT_ERROR

    print(MSG_OK_SYNCED.format(path=deploy_path))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
