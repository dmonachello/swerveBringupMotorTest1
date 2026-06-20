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
            test_names_for_profile - Resolve local runnable test names for one profile using shared source precedence.

        DESCRIPTION
            Precedence is:
            1. top-level dslTests in bringup_system.json
            2. schema-store tests model for the profile
            3. legacy tests deploy payload
        """
        return self._repository.load_canonical().dsl_tests().list_test_names(profile_name)

    def profile_test_names(self, profile_name: str) -> List[str]:
        """
        NAME
            profile_test_names - Resolve all saved profile-owned DSL test names.
        """
        return self._repository.load_canonical().dsl_tests().list_profile_test_names(profile_name)

    def profile_test_runnable_map(self, profile_name: str) -> Dict[str, bool]:
        """
        NAME
            profile_test_runnable_map - Resolve per-test runnable status for one profile.
        """
        return self._repository.load_canonical().dsl_tests().profile_test_runnable_map(profile_name)

    def config_library_test_runnable_map(self, profile_name: str) -> Dict[str, bool]:
        """
        NAME
            config_library_test_runnable_map - Resolve per-test runnable status for the config-scoped shared library.
        """
        return self._repository.load_canonical().dsl_tests().config_library_test_runnable_map(profile_name)

    def external_library_test_runnable_map(self, profile_name: str) -> Dict[str, bool]:
        """
        NAME
            external_library_test_runnable_map - Resolve per-test runnable status for the external shared library.
        """
        return self._repository.load_canonical().dsl_tests().external_library_test_runnable_map(profile_name)

    def global_test_names(self) -> List[str]:
        """
        NAME
            global_test_names - Resolve shared global-library DSL test names from canonical local config.
        """
        return self._repository.load_canonical().dsl_tests().list_global_test_names()

    def profile_test_set_name(self, profile_name: str) -> str:
        """
        NAME
            profile_test_set_name - Resolve the explicitly bound runnable DSL set for one profile.
        """
        return self._repository.load_canonical().dsl_tests().profile_test_set_name(profile_name)

    def profile_device_catalog(self, profile_name: str) -> Dict[str, Dict[str, Any]]:
        """
        NAME
            profile_device_catalog - Resolve the full DSL-usable device catalog for one selected profile.
        """
        return self._repository.load_canonical().dsl_tests().profile_device_catalog(profile_name)
