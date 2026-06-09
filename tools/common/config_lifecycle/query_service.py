from __future__ import annotations

"""
NAME
    query_service.py - Shared local config query helpers for host surfaces.

DESCRIPTION
    Provides a higher-level query layer on top of config lifecycle path/loading
    semantics so CLI/UI surfaces can resolve local profiles and local test
    availability from one shared service instead of duplicating source
    precedence rules.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.common.config_api import ConfigRepository
from .service import ConfigLifecycleService


PROFILE_NONE = "(none)"


class LocalConfigQueryService:
    """
    NAME
        LocalConfigQueryService - Shared query layer for local bringup config and tests.
    """

    def __init__(self, lifecycle: Optional[ConfigLifecycleService] = None) -> None:
        self._repository = ConfigRepository(lifecycle if lifecycle is not None else ConfigLifecycleService())

    def canonical_profiles_path(self) -> Path:
        """
        NAME
            canonical_profiles_path - Return the canonical local bringup_system.json path.
        """
        return self._repository.canonical_path()

    def load_canonical_payload(self) -> Dict[str, Any]:
        """
        NAME
            load_canonical_payload - Load the canonical local bringup_system.json payload.
        """
        return self._repository.load_canonical().to_payload()

    def sync_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        NAME
            sync_payload - Persist a local root payload through shared sync semantics.
        """
        session = self._repository.begin_canonical_edit()
        session.to_payload().clear()
        session.to_payload().update(payload)
        self._repository.sync(session)
        return session.to_payload()

    def list_profiles(self) -> List[str]:
        """
        NAME
            list_profiles - Return the sorted local profile names.
        """
        return self._repository.load_canonical().profiles().list_names()

    def selectable_profiles(self, none_label: str = PROFILE_NONE) -> List[str]:
        """
        NAME
            selectable_profiles - Return local profiles plus the empty UI selection entry.
        """
        return self._repository.load_canonical().profiles().selectable_names(none_label)

    def test_names_for_profile(self, profile_name: str) -> List[str]:
        """
        NAME
            test_names_for_profile - Resolve local test names for one profile using shared source precedence.

        DESCRIPTION
            Precedence is:
            1. top-level dslTests in bringup_system.json
            2. schema-store tests model for the profile
            3. legacy tests deploy payload
        """
        return self._repository.load_canonical().dsl_tests().list_test_names(profile_name)
