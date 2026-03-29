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

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from tools.can_nt.can_profiles import get_profile, reload_profiles
from tools.common.paths import repo_root
from tools.common.profile_constants import KEY_LABEL


KEY_CONTROLLERS = "controllers"
KEY_NAME = "name"
KEY_PORT = "port"
EMPTY_STRING = ""
DEFAULT_CONTROLLER_PREFIX = "controller"
DEFAULT_CONTROLLER_COUNT = 6


@dataclass
class DeviceInfo:
    """
    NAME
        DeviceInfo - Canonical device info entry.
    """

    label: str


def load_profile_devices(profile_name: str) -> Tuple[Dict[str, DeviceInfo], Set[str]]:
    """
    NAME
        load_profile_devices - Load device label map for a profile.

    PARAMETERS
        profile_name - Profile name to load.

    RETURNS
        Tuple of:
        - Mapping of label to DeviceInfo.
        - Set of duplicate labels detected in the profile.
    """

    reload_profiles()
    devices, _dup_ids = get_profile(profile_name)
    catalog: Dict[str, DeviceInfo] = {}
    duplicates: Set[str] = set()
    for entry in devices:
        label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
        if not label:
            continue
        if label in catalog:
            duplicates.add(label)
            continue
        catalog[label] = DeviceInfo(label=label)
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

    path = bindings_path or (repo_root() / "src" / "main" / "deploy" / "bringup_bindings.json")
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
