from __future__ import annotations

"""
NAME
    query_api.py - Shared config API query views.

DESCRIPTION
    Provides query helpers on top of loaded config payloads so applications do
    not need to reimplement profile/test discovery or source precedence rules.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from tools.common.profiles import list_profile_names
from tools.common.robot_test_dsl import resolve_profile_test_names, store_from_root_payload
from tools.common.tests_domain import collect_available_tests
from tools.common.tests_io import load_tests_payload
from tools.common.paths import tests_deploy_path
from tools.common.paths import repo_root


PROFILE_NONE = "(none)"
ConfigSchemaStore = None


class ProfilesQueryApi:
    """
    NAME
        ProfilesQueryApi - Read-only profile queries for one config payload.
    """

    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def list_names(self) -> List[str]:
        """
        NAME
            list_names - Return the sorted profile names.
        """
        return list_profile_names(self._payload)

    def selectable_names(self, none_label: str = PROFILE_NONE) -> List[str]:
        """
        NAME
            selectable_names - Return profile names plus a UI empty-selection label.
        """
        return [none_label] + self.list_names()


@dataclass(frozen=True)
class DslTestQueryEntry:
    """
    NAME
        DslTestQueryEntry - Profile-scoped DSL test query record.
    """

    name: str
    enabled: bool


class DslTestsQueryApi:
    """
    NAME
        DslTestsQueryApi - Read-only test inventory queries for one config payload.
    """

    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def list_test_names(self, profile_name: str) -> List[str]:
        """
        NAME
            list_test_names - Resolve test names for one profile using shared precedence.
        """
        clean_profile = str(profile_name or "").strip()
        if not clean_profile or clean_profile == PROFILE_NONE:
            return []
        dsl_names = self._dsl_test_names(clean_profile)
        if dsl_names is not None:
            return dsl_names
        store_names = self._store_test_names(clean_profile)
        if store_names is not None:
            return store_names
        return self._legacy_test_names()

    def list_test_entries(self, profile_name: str) -> List[DslTestQueryEntry]:
        """
        NAME
            list_test_entries - Resolve ordered DSL test entries for one profile.
        """
        clean_profile = str(profile_name or "").strip()
        if not clean_profile or clean_profile == PROFILE_NONE:
            return []
        dsl_entries = self._dsl_test_entries(clean_profile)
        if dsl_entries is not None:
            return dsl_entries
        return [
            DslTestQueryEntry(name=name, enabled=True)
            for name in self.list_test_names(clean_profile)
        ]

    def _dsl_test_names(self, profile_name: str) -> List[str] | None:
        dsl_payload = self._payload.get("dslTests")
        if not isinstance(dsl_payload, dict):
            return None
        return resolve_profile_test_names(self._payload, profile_name)

    def _dsl_test_entries(self, profile_name: str) -> List[DslTestQueryEntry] | None:
        dsl_payload = self._payload.get("dslTests")
        if not isinstance(dsl_payload, dict):
            return None
        store = store_from_root_payload(self._payload)
        names = resolve_profile_test_names(self._payload, profile_name)
        entries: List[DslTestQueryEntry] = []
        for name in names:
            entry = store.tests_by_name.get(name)
            if entry is None:
                continue
            entries.append(DslTestQueryEntry(name=name, enabled=bool(entry.enabled)))
        return entries

    @staticmethod
    def _store_test_names(profile_name: str) -> List[str] | None:
        store_cls = ConfigSchemaStore
        if store_cls is None:
            from tools.config.schema_store import ConfigSchemaStore as store_cls

        store = store_cls()
        try:
            store.load(repo_root())
        except Exception:
            return None
        model = store.tests_model(profile_name)
        if model is None:
            return None
        names: List[str] = []
        for test_set in model.test_sets.values():
            for test in test_set.tests:
                name = test.name
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())
        return sorted(set(names))

    @staticmethod
    def _legacy_test_names() -> List[str]:
        try:
            payload = load_tests_payload(tests_deploy_path())
        except Exception:
            return []
        if not isinstance(payload, dict):
            return []
        return collect_available_tests(payload)
