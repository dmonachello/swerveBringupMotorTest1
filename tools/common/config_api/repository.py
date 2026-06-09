from __future__ import annotations

"""
NAME
    repository.py - Shared config API repository entrypoint.

DESCRIPTION
    Owns path resolution, loading, and save/sync semantics for
    bringup_system.json so major host applications do not access the file
    directly.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from tools.common.config_lifecycle.service import ConfigLifecycleService

from .models import ConfigSaveResult, ConfigSource
from .session import ConfigEditSession
from .snapshot import ConfigSnapshot


SOURCE_KIND_CANONICAL = "canonical"
SOURCE_KIND_EXPLICIT_PATH = "explicit_path"


class ConfigRepository:
    """
    NAME
        ConfigRepository - Shared repository for bringup_system.json access.
    """

    def __init__(self, lifecycle: Optional[ConfigLifecycleService] = None) -> None:
        self._lifecycle = lifecycle if lifecycle is not None else ConfigLifecycleService()

    def canonical_path(self) -> Path:
        """
        NAME
            canonical_path - Return the canonical config path.
        """
        return self._lifecycle.default_paths().canonical_profiles_path

    def deploy_path(self) -> Path:
        """
        NAME
            deploy_path - Return the deploy config path.
        """
        return self._lifecycle.default_paths().deploy_profiles_path

    def load_canonical(self) -> ConfigSnapshot:
        """
        NAME
            load_canonical - Load the canonical config as a snapshot.
        """
        path = self.canonical_path()
        return self.load_path(path, source_kind=SOURCE_KIND_CANONICAL)

    def load_path(self, path: Path, *, source_kind: str = SOURCE_KIND_EXPLICIT_PATH) -> ConfigSnapshot:
        """
        NAME
            load_path - Load an explicit config path as a snapshot.
        """
        payload = self._lifecycle.load_profiles_payload(path)
        return ConfigSnapshot(payload, self._source_for(path, source_kind))

    def begin_canonical_edit(self) -> ConfigEditSession:
        """
        NAME
            begin_canonical_edit - Open a mutable edit session for the canonical config.
        """
        path = self.canonical_path()
        return self.begin_path_edit(path, source_kind=SOURCE_KIND_CANONICAL)

    def begin_path_edit(
        self,
        path: Path,
        *,
        source_kind: str = SOURCE_KIND_EXPLICIT_PATH,
    ) -> ConfigEditSession:
        """
        NAME
            begin_path_edit - Open a mutable edit session for an explicit config path.
        """
        payload = self._lifecycle.load_profiles_payload(path)
        return ConfigEditSession(payload, self._source_for(path, source_kind))

    def session_for_payload(
        self,
        path: Path,
        payload: Dict[str, Any],
        *,
        source_kind: str = SOURCE_KIND_EXPLICIT_PATH,
    ) -> ConfigEditSession:
        """
        NAME
            session_for_payload - Build a mutable edit session from an in-memory payload and source path.
        """
        return ConfigEditSession(dict(payload), self._source_for(path, source_kind))

    def save(
        self,
        session: ConfigEditSession,
        *,
        path: Path,
        stamp: bool = True,
    ) -> ConfigSaveResult:
        """
        NAME
            save - Save a session payload to one explicit path.
        """
        stamped = self._lifecycle.stamp_profiles_payload(session.to_payload(), stamp=stamp)
        from tools.common.json_io import write_json

        write_json(path, stamped)
        session.to_payload().clear()
        session.to_payload().update(stamped)
        return ConfigSaveResult(path=path, deploy_path=None, synced=False)

    def sync(self, session: ConfigEditSession, *, stamp: bool = True) -> ConfigSaveResult:
        """
        NAME
            sync - Sync a session payload through shared canonical/deploy semantics.
        """
        stamped = self._lifecycle.sync_profiles_payload(session.to_payload(), stamp=stamp)
        session.to_payload().clear()
        session.to_payload().update(stamped)
        session.mark_dirty()
        return ConfigSaveResult(
            path=self.canonical_path(),
            deploy_path=self.deploy_path(),
            synced=True,
        )

    def _source_for(self, path: Path, kind: str) -> ConfigSource:
        return ConfigSource(
            kind=kind,
            path=path,
            exists=path.exists(),
            writable=True,
        )
