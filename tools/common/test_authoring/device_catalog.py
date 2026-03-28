from __future__ import annotations

"""
NAME
    device_catalog.py - Load device lists for test authoring.

SYNOPSIS
    from tools.common.test_authoring.device_catalog import load_profile_devices

DESCRIPTION
    Loads device metadata from bringup_system.json via the existing profile
    loader and exposes canonical device keys for validation and UI lists.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from tools.can_nt.can_profiles import get_profile, reload_profiles
from tools.common.paths import repo_root


KEY_VENDOR = "vendor"
KEY_TYPE = "type"
KEY_ID = "id"
KEY_LABEL = "label"
KEY_CONTROLLERS = "controllers"
KEY_NAME = "name"
KEY_PORT = "port"
KEY_SEPARATOR = ":"
EMPTY_STRING = ""
DEFAULT_CONTROLLER_PREFIX = "controller"
DEFAULT_CONTROLLER_COUNT = 6


@dataclass
class DeviceInfo:
    """
    NAME
        DeviceInfo - Canonical device info entry.
    """

    key: str
    label: str
    vendor: str
    device_type: str
    can_id: int


def load_profile_devices(profile_name: str) -> Dict[str, DeviceInfo]:
    """
    NAME
        load_profile_devices - Load canonical device map for a profile.

    PARAMETERS
        profile_name - Profile name to load.

    RETURNS
        Mapping of canonical key to DeviceInfo.
    """

    reload_profiles()
    devices, _dup_ids = get_profile(profile_name)
    catalog: Dict[str, DeviceInfo] = {}
    for entry in devices:
        vendor = str(entry.get(KEY_VENDOR, EMPTY_STRING)).strip()
        device_type = str(entry.get(KEY_TYPE, EMPTY_STRING)).strip()
        can_id = entry.get(KEY_ID)
        if not vendor or not device_type or not isinstance(can_id, int):
            continue
        key = f"{vendor}{KEY_SEPARATOR}{device_type}{KEY_SEPARATOR}{can_id}"
        label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip() or key
        catalog[key] = DeviceInfo(
            key=key,
            label=label,
            vendor=vendor,
            device_type=device_type,
            can_id=can_id,
        )
    return catalog


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
