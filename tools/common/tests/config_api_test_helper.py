from __future__ import annotations

"""
NAME
    config_api_test_helper.py - Shared test helpers for bringup_system.json fixtures.

DESCRIPTION
    Keeps tests on the same load/save contract as production host surfaces by
    routing valid bringup_system.json fixture I/O through ConfigRepository.
"""

from pathlib import Path
from typing import Any, Dict

from tools.common.config_api.repository import ConfigRepository


def write_profiles_payload(path: Path, payload: Dict[str, Any], *, stamp: bool = False) -> None:
    """
    NAME
        write_profiles_payload - Persist a valid bringup_system.json payload through ConfigRepository.
    """
    repository = ConfigRepository()
    session = repository.session_for_payload(path, payload)
    repository.save(session, path=path, stamp=stamp)


def load_profiles_payload(path: Path) -> Dict[str, Any]:
    """
    NAME
        load_profiles_payload - Load a bringup_system.json payload through ConfigRepository.
    """
    return ConfigRepository().load_path(path).to_payload()
