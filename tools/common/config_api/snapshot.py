from __future__ import annotations

"""
NAME
    snapshot.py - Shared config API snapshot models.

DESCRIPTION
    Provides read-only structured views of loaded config payloads.
"""

from typing import Any, Dict

from tools.common.profile_constants import KEY_DATA_HASH, KEY_DATA_VERSION, KEY_SCHEMA_VERSION

from .models import ConfigSource
from .query_api import DslTestsQueryApi, ProfilesQueryApi


class ConfigSnapshot:
    """
    NAME
        ConfigSnapshot - Read-only view of one loaded config payload.
    """

    def __init__(self, payload: Dict[str, Any], source: ConfigSource) -> None:
        self._payload = dict(payload)
        self._source = source

    @property
    def source(self) -> ConfigSource:
        """
        NAME
            source - Return source metadata for this snapshot.
        """
        return self._source

    @property
    def schema_version(self) -> int | None:
        return self._payload.get(KEY_SCHEMA_VERSION)

    @property
    def data_version(self) -> str:
        return str(self._payload.get(KEY_DATA_VERSION, "") or "")

    @property
    def data_hash(self) -> str:
        return str(self._payload.get(KEY_DATA_HASH, "") or "")

    def profiles(self) -> ProfilesQueryApi:
        """
        NAME
            profiles - Return the profile query view.
        """
        return ProfilesQueryApi(self._payload)

    def dsl_tests(self) -> DslTestsQueryApi:
        """
        NAME
            dsl_tests - Return the DSL test query view.
        """
        return DslTestsQueryApi(self._payload)

    def to_payload(self) -> Dict[str, Any]:
        """
        NAME
            to_payload - Return a compatibility copy of the root payload.
        """
        return dict(self._payload)
