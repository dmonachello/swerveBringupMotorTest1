from __future__ import annotations

"""
NAME
    models.py - Shared config API models.

DESCRIPTION
    Defines lightweight structured result and metadata objects for the shared
    config API entrypoints.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ConfigSource:
    """
    NAME
        ConfigSource - Source metadata for one config snapshot or edit session.
    """

    kind: str
    path: Path
    exists: bool
    writable: bool


@dataclass(frozen=True)
class ConfigSaveResult:
    """
    NAME
        ConfigSaveResult - Result of saving or syncing config through the repository.
    """

    path: Path
    deploy_path: Optional[Path]
    synced: bool
