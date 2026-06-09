from __future__ import annotations

"""
NAME
    config_lifecycle - Shared config/profile lifecycle services.

DESCRIPTION
    Centralized host-side ownership for canonical/deploy/runtime source
    semantics, source reporting, and profile payload lifecycle helpers.
"""

from .models import ConfigLifecycleSourceEntry, ConfigLifecyclePaths
from .service import ConfigLifecycleService

__all__ = [
    "ConfigLifecyclePaths",
    "ConfigLifecycleService",
    "ConfigLifecycleSourceEntry",
    "LocalConfigQueryService",
]


def __getattr__(name: str):
    """
    NAME
        __getattr__ - Lazily expose query helpers to avoid package import cycles.
    """
    if name == "LocalConfigQueryService":
        from .query_service import LocalConfigQueryService

        return LocalConfigQueryService
    raise AttributeError(name)
