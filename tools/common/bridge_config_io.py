from __future__ import annotations

"""
NAME
    bridge_config_io.py - Shared bridgeConfig normalization helpers.

DESCRIPTION
    Owns host-side bridgeConfig serialization policy so CLI, topology editor,
    and shared config lifecycle code do not each invent their own key-ordering
    and generatedAt behavior.
"""

import time
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from tools.common.profile_constants import (
    BRIDGE_CONFIG_SCHEMA_VERSION,
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_GENERATED_AT,
    KEY_BRIDGE_SCHEMA_VERSION,
)


def bridge_generated_at_now() -> str:
    """
    NAME
        bridge_generated_at_now - Return current UTC bridgeConfig timestamp.
    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def default_bridge_config() -> Dict[str, Any]:
    """
    NAME
        default_bridge_config - Return the empty bridgeConfig payload.
    """
    return {
        KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
        KEY_BRIDGE_GENERATED_AT: None,
        KEY_BRIDGE_BY_PROFILE: {},
    }


def normalize_bridge_config(
    config: Optional[Mapping[str, Any]],
    *,
    stamp_generated_at: bool = False,
) -> Dict[str, Any]:
    """
    NAME
        normalize_bridge_config - Return ordered bridgeConfig payload.

    DESCRIPTION
        Applies the shared bridgeConfig output contract:
        - stable key order
        - default schemaVersion
        - optional generatedAt stamping
        - shallow mapping copy for byProfile
    """
    normalized = default_bridge_config()
    if isinstance(config, Mapping):
        schema_version = config.get(KEY_BRIDGE_SCHEMA_VERSION)
        if schema_version is not None:
            normalized[KEY_BRIDGE_SCHEMA_VERSION] = schema_version
        normalized[KEY_BRIDGE_GENERATED_AT] = config.get(KEY_BRIDGE_GENERATED_AT)
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if isinstance(by_profile, Mapping):
            normalized[KEY_BRIDGE_BY_PROFILE] = dict(by_profile)
    if stamp_generated_at:
        normalized[KEY_BRIDGE_GENERATED_AT] = bridge_generated_at_now()
    return normalized


def single_profile_bridge_config(
    profile_name: str,
    profile_entry: Mapping[str, Any],
    *,
    stamp_generated_at: bool = False,
) -> Dict[str, Any]:
    """
    NAME
        single_profile_bridge_config - Build bridgeConfig for one profile entry.
    """
    return normalize_bridge_config(
        {
            KEY_BRIDGE_BY_PROFILE: {
                profile_name: deepcopy(dict(profile_entry)),
            }
        },
        stamp_generated_at=stamp_generated_at,
    )
