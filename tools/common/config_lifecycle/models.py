from __future__ import annotations

"""
NAME
    models.py - Data models for config lifecycle services.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConfigLifecyclePaths:
    """
    NAME
        ConfigLifecyclePaths - Canonical/deploy profile path ownership.
    """

    canonical_profiles_path: Path
    deploy_profiles_path: Path


@dataclass(frozen=True)
class ConfigLifecycleSourceEntry:
    """
    NAME
        ConfigLifecycleSourceEntry - One source visibility record.
    """

    name: str
    path: str
    exists: bool

