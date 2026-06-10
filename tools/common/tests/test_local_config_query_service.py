from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.common.config_lifecycle import LocalConfigQueryService


class LocalConfigQueryServiceTests(unittest.TestCase):
    """
    NAME
        LocalConfigQueryServiceTests - Validate shared local config query semantics.
    """

    def test_list_profiles_uses_canonical_payload(self) -> None:
        payload = {
            "profiles": {
                "beta": {},
                "alpha": {},
            }
        }

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        service = LocalConfigQueryService(_FakeLifecycleService())

        self.assertEqual(["alpha", "beta"], service.list_profiles())

    def test_selectable_profiles_prefixes_none_label(self) -> None:
        payload = {
            "profiles": {
                "home": {},
            }
        }

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        service = LocalConfigQueryService(_FakeLifecycleService())

        self.assertEqual(["(none)", "home"], service.selectable_profiles())

    def test_test_names_for_profile_prefers_dsl_store(self) -> None:
        payload = {
            "profiles": {
                "home": {
                    "devices": [],
                    "dslTestSet": "pit",
                }
            },
            "dslTests": {
                "schemaVersion": 1,
                "defaultSet": "default",
                "testSets": {
                    "default": ["default_test"],
                    "pit": ["pit_one", "pit_two"],
                },
                "testsByName": {
                    "default_test": {"source": "", "sourceHash": "", "normalized": {}, "enabled": True},
                    "pit_one": {"source": "", "sourceHash": "", "normalized": {}, "enabled": False},
                    "pit_two": {"source": "", "sourceHash": "", "normalized": {}, "enabled": True},
                },
            },
        }

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        service = LocalConfigQueryService(_FakeLifecycleService())

        self.assertEqual(["pit_one", "pit_two"], service.test_names_for_profile("home"))

    def test_test_entries_for_profile_preserve_enabled_flags(self) -> None:
        payload = {
            "profiles": {
                "home": {
                    "devices": [],
                    "dslTestSet": "pit",
                }
            },
            "dslTests": {
                "schemaVersion": 1,
                "defaultSet": "default",
                "testSets": {
                    "pit": ["pit_one", "pit_two"],
                },
                "testsByName": {
                    "pit_one": {"source": "", "sourceHash": "", "normalized": {}, "enabled": False},
                    "pit_two": {"source": "", "sourceHash": "", "normalized": {}, "enabled": True},
                },
            },
        }

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        service = LocalConfigQueryService(_FakeLifecycleService())

        entries = service.test_entries_for_profile("home")

        self.assertEqual(["pit_one", "pit_two"], [entry.name for entry in entries])
        self.assertEqual([False, True], [entry.enabled for entry in entries])

    def test_test_names_for_profile_falls_back_to_store_model(self) -> None:
        payload = {
            "profiles": {
                "home": {
                    "devices": [],
                }
            },
        }

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        class _FakeTest:
            def __init__(self, name: str) -> None:
                self.name = name

        class _FakeSet:
            def __init__(self, names: list[str]) -> None:
                self.tests = [_FakeTest(name) for name in names]

        class _FakeModel:
            def __init__(self) -> None:
                self.test_sets = {"default": _FakeSet(["alpha", "beta"])}

        class _FakeStore:
            def load(self, _root):
                return None

            def tests_model(self, profile_name):
                return _FakeModel() if profile_name == "home" else None

        service = LocalConfigQueryService(_FakeLifecycleService())
        with patch("tools.common.config_api.query_api.ConfigSchemaStore", lambda: _FakeStore()):
            self.assertEqual(["alpha", "beta"], service.test_names_for_profile("home"))


if __name__ == "__main__":
    unittest.main()
