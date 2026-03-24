from __future__ import annotations

"""
NAME
    profile_io.py - bringup_system.json helpers.

SYNOPSIS
    from tools.common.profile_io import compute_profiles_hash

DESCRIPTION
    Shared helpers for profile payload hashing and normalization. These are
    intentionally small and do not enforce policy beyond schema checks.
"""

import hashlib
import json
from typing import Any, Dict, Tuple


def compute_profiles_hash(payload: Dict[str, Any]) -> str:
    """
    NAME
        compute_profiles_hash - Compute a stable hash for profile payloads.

    DESCRIPTION
        Hashes the JSON with data_hash set to an empty string and sorted keys,
        so formatting differences do not affect the checksum. bridgeConfig is
        excluded so local group edits do not invalidate profiles integrity.
    """
    normalized = dict(payload)
    normalized["data_hash"] = ""
    if "bridgeConfig" in normalized:
        normalized.pop("bridgeConfig", None)
    blob = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def validate_profiles_schema(payload: Dict[str, Any], schema_version: int) -> Tuple[bool, str]:
    """
    NAME
        validate_profiles_schema - Validate schema_version for profiles payload.

    RETURNS
        (ok, error_message). error_message is empty when ok is True.
    """
    if payload.get("schema_version") != schema_version:
        return (
            False,
            "Profile schema_version mismatch: "
            f"expected {schema_version}, got {payload.get('schema_version')}",
        )
    return (True, "")
