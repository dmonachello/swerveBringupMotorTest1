from __future__ import annotations

"""
NAME
    device_catalog.py - Load device lists for test authoring.

SYNOPSIS
    from tools.common.test_authoring.device_catalog import load_profile_devices

DESCRIPTION
    Loads device metadata from bringup_system.json via the existing profile
    loader and exposes device labels for validation and UI lists.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from tools.can_nt.can_profiles import reload_profiles
from tools.common.paths import bindings_deploy_path
from tools.common.profile_constants import (
    KEY_DEVICES,
    KEY_LABEL,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
)
from tools.common.json_io import read_json
from tools.common.paths import legacy_profiles_canonical_path, profiles_canonical_path


KEY_CONTROLLERS = "controllers"
KEY_NAME = "name"
KEY_PORT = "port"
EMPTY_STRING = ""
DEFAULT_CONTROLLER_PREFIX = "controller"
DEFAULT_CONTROLLER_COUNT = 6


def load_profile_devices(profile_name: str) -> Tuple[Dict[str, Dict[str, object]], Set[str]]:
    """
    NAME
        load_profile_devices - Load device label map for a profile.

    PARAMETERS
        profile_name - Profile name to load.

    RETURNS
        Tuple of:
        - Mapping of label to device entry dict.
        - Set of duplicate labels detected in the profile.
    """

    reload_profiles()
    catalog: Dict[str, Dict[str, object]] = {}
    duplicates: Set[str] = set()
    path = profiles_canonical_path()
    if not path.exists():
        path = legacy_profiles_canonical_path()
    if not path.exists():
        return catalog, duplicates
    try:
        payload = read_json(path)
    except Exception:
        return catalog, duplicates
    if not isinstance(payload, dict):
        return catalog, duplicates
    profiles = payload.get(KEY_PROFILES)
    devices = payload.get(KEY_DEVICES)
    if not isinstance(profiles, dict) or not isinstance(devices, list):
        return catalog, duplicates
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        return catalog, duplicates
    labels = profile.get(KEY_PROFILE_DEVICES)
    if not isinstance(labels, list):
        return catalog, duplicates
    registry: Dict[str, Dict[str, object]] = {}
    for entry in devices:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
        if not label:
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
        catalog[clean] = dict(entry)
    return catalog, duplicates


def load_controller_names(bindings_path: Optional[Path] = None) -> Set[str]:
    """
    NAME
        load_controller_names - Load controller names from bringup_bindings.json.

    PARAMETERS
        bindings_path - Optional path override for bindings file.

    RETURNS
        Set of controller names for validation.
    """

    path = bindings_path or bindings_deploy_path()
    names: Set[str] = set()
    payload: Dict[str, object] = {}
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    controllers = payload.get(KEY_CONTROLLERS) if isinstance(payload, dict) else None
    if isinstance(controllers, list):
        for entry in controllers:
            if not isinstance(entry, dict):
                continue
            name = entry.get(KEY_NAME)
            if isinstance(name, str) and name:
                names.add(name)
                continue
            port = entry.get(KEY_PORT)
            if isinstance(port, int) and 0 <= port < DEFAULT_CONTROLLER_COUNT:
                names.add(f"{DEFAULT_CONTROLLER_PREFIX}{port}")
    if names:
        return names
    return {f"{DEFAULT_CONTROLLER_PREFIX}{idx}" for idx in range(DEFAULT_CONTROLLER_COUNT)}
