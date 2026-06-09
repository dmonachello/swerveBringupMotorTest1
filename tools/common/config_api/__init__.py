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
    raise AttributeError(name)
