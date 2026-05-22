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
    KEY_DEFAULT_PROFILE,
    KEY_DEVICES,
    KEY_INTERFACE,
    KEY_LABEL,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
    KEY_TYPE,
    INTERFACE_USB,
    TYPE_XBOX_CONTROLLER,
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


def load_controller_names(
    bindings_path: Optional[Path] = None,
    payload: Optional[Dict[str, object]] = None,
    profile_name: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> Set[str]:
    """
    NAME
        load_controller_names - Load configured controller names.

    PARAMETERS
        bindings_path - Optional bindings path used to discover sibling deploy config.
        payload - Optional already-loaded bringup_system.json payload.
        profile_name - Optional profile name used to limit labels to one profile.
        config_path - Optional explicit bringup_system.json path.

    RETURNS
        Set of controller names for validation.
    """

    names = _controller_names_from_profiles_payload(payload, profile_name)
    if names:
        return names

    profile_path = config_path
    if profile_path is None and bindings_path is not None:
        candidate = bindings_path.parent / "bringup_system.json"
        if candidate.exists():
            profile_path = candidate
    if profile_path is None:
        profile_path = profiles_canonical_path()
        if not profile_path.exists():
            profile_path = legacy_profiles_canonical_path()
    if profile_path.exists():
        try:
            loaded_payload = json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception:
            loaded_payload = {}
        names = _controller_names_from_profiles_payload(loaded_payload, profile_name)
        if names:
            return names

    path = bindings_path or bindings_deploy_path()
    legacy_payload: Dict[str, object] = {}
    if path.exists():
        try:
            legacy_payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            legacy_payload = {}
    controllers = legacy_payload.get(KEY_CONTROLLERS) if isinstance(legacy_payload, dict) else None
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


def _controller_names_from_profiles_payload(
    payload: Optional[Dict[str, object]],
    profile_name: Optional[str],
) -> Set[str]:
    """
    NAME
        _controller_names_from_profiles_payload - Extract configured controller names.
    """

    if not isinstance(payload, dict):
        return set()
    devices = payload.get(KEY_DEVICES)
    profiles = payload.get(KEY_PROFILES)
    if not isinstance(devices, list):
        return set()
    selected_profile = profile_name
    if not selected_profile and isinstance(payload.get(KEY_DEFAULT_PROFILE), str):
        selected_profile = str(payload.get(KEY_DEFAULT_PROFILE)).strip() or None
    allowed_labels: Optional[Set[str]] = None
    if selected_profile and isinstance(profiles, dict):
        profile = profiles.get(selected_profile)
        if isinstance(profile, dict):
            labels = profile.get(KEY_PROFILE_DEVICES)
            if isinstance(labels, list):
                allowed_labels = {
                    str(label).strip().lower()
                    for label in labels
                    if isinstance(label, str) and str(label).strip()
                }
    names: Set[str] = set()
    for entry in devices:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
        if not label:
            continue
        if allowed_labels is not None and label.lower() not in allowed_labels:
            continue
        if str(entry.get(KEY_TYPE, EMPTY_STRING)).strip() != TYPE_XBOX_CONTROLLER:
            continue
        if str(entry.get(KEY_INTERFACE, EMPTY_STRING)).strip() != INTERFACE_USB:
            continue
        names.add(label)
    return names
