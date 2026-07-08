from __future__ import annotations

"""
NAME
    config_api - Shared repository-owned config access API.

DESCRIPTION
    Central entrypoint for bringup_system.json access used by major host
    applications and shared services.
"""

from .models import ConfigSaveResult, ConfigSource

__all__ = [
    "ConfigEditSession",
    "ConfigRepository",
    "ConfigSaveResult",
    "ConfigSnapshot",
    "ConfigSource",
    "DslTestsQueryApi",
    "ProfilesQueryApi",
    "blank_profile_payload",
    "blank_topology_entry",
    "create_blank_profile",
    "delete_profile",
    "ensure_profile_topology_entry",
    "rename_profile",
    "replace_profile_devices",
    "replace_profile_topology_entry",
    "set_default_profile",
    "upsert_profile",
]


def __getattr__(name: str):
    """
    NAME
        __getattr__ - Lazily expose config API types to avoid package import cycles.
    """
    if name == "ConfigRepository":
        from .repository import ConfigRepository

        return ConfigRepository
    if name == "ConfigEditSession":
        from .session import ConfigEditSession

        return ConfigEditSession
    if name == "ConfigSnapshot":
        from .snapshot import ConfigSnapshot

        return ConfigSnapshot
    if name == "DslTestsQueryApi":
        from .query_api import DslTestsQueryApi

        return DslTestsQueryApi
    if name == "ProfilesQueryApi":
        from .query_api import ProfilesQueryApi

        return ProfilesQueryApi
    if name == "replace_profile_devices":
        from .mutations import replace_profile_devices

        return replace_profile_devices
    if name == "blank_profile_payload":
        from .mutations import blank_profile_payload

        return blank_profile_payload
    if name == "blank_topology_entry":
        from .mutations import blank_topology_entry

        return blank_topology_entry
    if name == "create_blank_profile":
        from .mutations import create_blank_profile

        return create_blank_profile
    if name == "upsert_profile":
        from .mutations import upsert_profile

        return upsert_profile
    if name == "rename_profile":
        from .mutations import rename_profile

        return rename_profile
    if name == "delete_profile":
        from .mutations import delete_profile

        return delete_profile
    if name == "replace_profile_topology_entry":
        from .mutations import replace_profile_topology_entry

        return replace_profile_topology_entry
    if name == "ensure_profile_topology_entry":
        from .mutations import ensure_profile_topology_entry

        return ensure_profile_topology_entry
    if name == "set_default_profile":
        from .mutations import set_default_profile

        return set_default_profile
    raise AttributeError(name)
