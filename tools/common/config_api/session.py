from __future__ import annotations

"""
NAME
    session.py - Shared config API mutable edit session.

DESCRIPTION
    Provides a controlled mutable working session for config changes while
    preserving centralized save/sync ownership in the repository.
"""

from typing import Any, Dict

from .models import ConfigSource
from .query_api import DslTestsQueryApi, ProfilesQueryApi
from .snapshot import ConfigSnapshot


class ConfigEditSession:
    """
    NAME
        ConfigEditSession - Mutable config working session.
    """

    def __init__(self, payload: Dict[str, Any], source: ConfigSource) -> None:
        self._payload = dict(payload)
        self._source = source
        self._dirty = False

    @property
    def source(self) -> ConfigSource:
        """
        NAME
            source - Return source metadata for this edit session.
        """
        return self._source

    @property
    def dirty(self) -> bool:
        """
        NAME
            dirty - Return whether the session has unsaved mutations.
        """
        return self._dirty

    def mark_dirty(self) -> None:
        """
        NAME
            mark_dirty - Mark the session as modified.
        """
        self._dirty = True

    def profiles(self) -> ProfilesQueryApi:
        """
        NAME
            profiles - Return the profile query view for the current payload.
        """
        return ProfilesQueryApi(self._payload)

    def dsl_tests(self) -> DslTestsQueryApi:
        """
        NAME
            dsl_tests - Return the DSL test query view for the current payload.
        """
        return DslTestsQueryApi(self._payload)

    def to_payload(self) -> Dict[str, Any]:
        """
        NAME
            to_payload - Return the mutable root payload.
        """
        return self._payload

    def snapshot(self) -> ConfigSnapshot:
        """
        NAME
            snapshot - Build a read-only snapshot from the current session payload.
        """
        return ConfigSnapshot(self._payload, self._source)
