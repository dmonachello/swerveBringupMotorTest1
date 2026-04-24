from __future__ import annotations

"""
NAME
    service.py - Shared config lifecycle service implementation.

DESCRIPTION
    Owns host-side semantics for canonical/deploy profile paths, source
    reporting, and profile payload stamping/sync.
"""

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from tools.common.json_io import read_json, write_json
from tools.common.paths import profiles_canonical_path, profiles_deploy_path
from tools.common.profile_constants import KEY_DATA_HASH, KEY_DATA_VERSION, KEY_SCHEMA_VERSION
from tools.common.profile_io import compute_profiles_hash, default_profiles_schema_version
from tools.common.time_utils import timestamp_version

from .models import ConfigLifecyclePaths, ConfigLifecycleSourceEntry


KEY_NAME = "name"
KEY_PATH = "path"
KEY_EXISTS = "exists"
EMPTY_STRING = ""


class ConfigLifecycleService:
    """
    NAME
        ConfigLifecycleService - Shared profile/config lifecycle policy.
    """

    def default_paths(self) -> ConfigLifecyclePaths:
        """
        NAME
            default_paths - Resolve canonical/deploy profile paths.
        """
        return ConfigLifecyclePaths(
            canonical_profiles_path=profiles_canonical_path(),
            deploy_profiles_path=profiles_deploy_path(),
        )

    def build_source_entry(self, name: str, path: Optional[Path]) -> ConfigLifecycleSourceEntry:
        """
        NAME
            build_source_entry - Build one source record.
        """
        path_text = str(path) if path is not None else EMPTY_STRING
        exists = bool(path is not None and path.exists())
        return ConfigLifecycleSourceEntry(name=name, path=path_text, exists=exists)

    def collect_source_entries(self, sources: Iterable[tuple[str, Optional[Path]]]) -> List[ConfigLifecycleSourceEntry]:
        """
        NAME
            collect_source_entries - Build source records for display/JSON.
        """
        entries: List[ConfigLifecycleSourceEntry] = []
        for name, path in sources:
            entries.append(self.build_source_entry(name, path))
        return entries

    def source_entries_to_dicts(self, entries: Iterable[ConfigLifecycleSourceEntry]) -> List[Dict[str, object]]:
        """
        NAME
            source_entries_to_dicts - Convert source entries to JSON-friendly dicts.
        """
        return [
            {
                KEY_NAME: entry.name,
                KEY_PATH: entry.path,
                KEY_EXISTS: entry.exists,
            }
            for entry in entries
        ]

    def load_profiles_payload(self, path: Path) -> Dict[str, Any]:
        """
        NAME
            load_profiles_payload - Read profile payload from disk.
        """
        payload = read_json(path)
        if not isinstance(payload, dict):
            raise ValueError("Profiles payload root must be a JSON object.")
        return payload

    def stamp_profiles_payload(self, payload: Dict[str, Any], *, stamp: bool = True) -> Dict[str, Any]:
        """
        NAME
            stamp_profiles_payload - Apply schema/version/hash fields.
        """
        stamped = dict(payload)
        stamped[KEY_SCHEMA_VERSION] = default_profiles_schema_version()
        if stamp:
            stamped[KEY_DATA_VERSION] = timestamp_version()
            stamped[KEY_DATA_HASH] = compute_profiles_hash(stamped)
        return stamped

    def sync_profiles_payload(
        self,
        payload: Dict[str, Any],
        *,
        canonical_path: Optional[Path] = None,
        deploy_path: Optional[Path] = None,
        stamp: bool = True,
    ) -> Dict[str, Any]:
        """
        NAME
            sync_profiles_payload - Write canonical/deploy copies with shared semantics.
        """
        paths = self.default_paths()
        canonical = canonical_path if canonical_path is not None else paths.canonical_profiles_path
        deploy = deploy_path if deploy_path is not None else paths.deploy_profiles_path
        stamped = self.stamp_profiles_payload(payload, stamp=stamp)
        deploy.parent.mkdir(parents=True, exist_ok=True)
        write_json(canonical, stamped)
        write_json(deploy, stamped)
        return stamped

