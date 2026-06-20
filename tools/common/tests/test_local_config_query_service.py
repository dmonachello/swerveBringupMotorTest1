from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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
                    "default_test": {"source": "", "sourceHash": "", "normalized": {}},
                    "pit_one": {"source": "", "sourceHash": "", "normalized": {}},
                    "pit_two": {"source": "", "sourceHash": "", "normalized": {}},
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

    def test_test_names_for_profile_requires_explicit_dsl_test_set(self) -> None:
        payload = {
            "profiles": {
                "home": {
                    "devices": [],
                }
            },
            "dslTests": {
                "schemaVersion": 1,
                "defaultSet": "default",
                "testSets": {
                    "default": ["default_test"],
                },
                "testsByName": {
                    "default_test": {"source": "", "sourceHash": "", "normalized": {}},
                },
            },
        }

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        service = LocalConfigQueryService(_FakeLifecycleService())

        self.assertEqual([], service.test_names_for_profile("home"))

    def test_global_test_names_reads_default_library_set(self) -> None:
        payload = {
            "profiles": {
                "home": {
                    "devices": [],
                }
            },
            "dslTests": {
                "schemaVersion": 1,
                "defaultSet": "global_library",
                "testSets": {
                    "global_library": ["alpha", "beta"],
                    "home": ["gamma"],
                },
                "testsByName": {
                    "alpha": {"source": "", "sourceHash": "", "normalized": {}},
                    "beta": {"source": "", "sourceHash": "", "normalized": {}},
                    "gamma": {"source": "", "sourceHash": "", "normalized": {}},
                },
            },
        }

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        service = LocalConfigQueryService(_FakeLifecycleService())

        self.assertEqual(["alpha", "beta"], service.global_test_names())

    def test_profile_test_set_name_reads_explicit_binding(self) -> None:
        payload = {
            "profiles": {
                "home": {
                    "devices": [],
                    "dslTestSet": "home",
                }
            },
            "dslTests": {
                "schemaVersion": 1,
                "defaultSet": "global_library",
                "testSets": {
                    "global_library": ["alpha"],
                    "home": ["gamma"],
                },
                "testsByName": {
                    "alpha": {"source": "", "sourceHash": "", "normalized": {}},
                    "gamma": {"source": "", "sourceHash": "", "normalized": {}},
                },
            },
        }

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        service = LocalConfigQueryService(_FakeLifecycleService())

        self.assertEqual("home", service.profile_test_set_name("home"))

    def test_profile_test_names_and_runnable_map_include_invalid_saved_tests(self) -> None:
        payload = {
            "profiles": {
                "home": {
                    "devices": [],
                    "dslTestSet": "home",
                }
            },
            "dslTests": {
                "schemaVersion": 1,
                "defaultSet": "global_library",
                "testSets": {
                    "global_library": ["alpha"],
                    "home": ["good", "bad"],
                },
                "testsByName": {
                    "alpha": {"source": "", "sourceHash": "", "normalized": {}, "runnable": True},
                    "good": {"source": "", "sourceHash": "", "normalized": {}, "runnable": True},
                    "bad": {"source": "", "sourceHash": "", "normalized": {}, "runnable": False},
                },
            },
        }

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        service = LocalConfigQueryService(_FakeLifecycleService())

        self.assertEqual(["good"], service.test_names_for_profile("home"))
        self.assertEqual(["good", "bad"], service.profile_test_names("home"))
        self.assertEqual({"good": True, "bad": False}, service.profile_test_runnable_map("home"))
        self.assertEqual({"alpha": False}, service.config_library_test_runnable_map("home"))

    def test_profile_device_catalog_includes_non_can_profile_devices(self) -> None:
        payload = {
            "profiles": {
                "home": {
                    "devices": ["SPARKMAX/NEO 25", "controller0", "lmtSw0"],
                    "dslTestSet": "home",
                }
            },
            "devices": [
                {
                    "label": "SPARKMAX/NEO 25",
                    "manufacturer": 2,
                    "deviceType": 2,
                    "id": 25,
                    "model": "SPARK MAX",
                    "type": "motor",
                    "deviceInterface": "CAN",
                },
                {
                    "label": "controller0",
                    "manufacturer": 1,
                    "deviceType": 1,
                    "id": 0,
                    "model": "Xbox Controller",
                    "type": "xboxController",
                    "deviceInterface": "USB",
                },
                {
                    "label": "lmtSw0",
                    "manufacturer": 1,
                    "deviceType": 0,
                    "id": 0,
                    "model": "Limit Switch",
                    "type": "limitSwitch",
                    "deviceInterface": "DIO",
                },
            ],
            "dslTests": {"schemaVersion": 1, "defaultSet": "global_library", "testSets": {}, "testsByName": {}},
        }

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        service = LocalConfigQueryService(_FakeLifecycleService())
        catalog = service.profile_device_catalog("home")

        self.assertEqual(["SPARKMAX/NEO 25", "controller0", "lmtSw0"], sorted(catalog.keys()))
        self.assertEqual("limitSwitch", catalog["lmtSw0"]["type"])

    def test_external_library_test_runnable_map_uses_selected_profile_context(self) -> None:
        payload = {
            "profiles": {
                "home": {
                    "devices": ["SPARKMAX/NEO 25", "controller0"],
                    "dslTestSet": "home",
                }
            },
            "devices": [
                {
                    "label": "SPARKMAX/NEO 25",
                    "manufacturer": 2,
                    "deviceType": 2,
                    "id": 25,
                    "model": "SPARK MAX",
                    "type": "motor",
                    "deviceInterface": "CAN",
                },
                {
                    "label": "controller0",
                    "manufacturer": 1,
                    "deviceType": 1,
                    "id": 0,
                    "model": "Xbox Controller",
                    "type": "xboxController",
                    "deviceInterface": "USB",
                },
            ],
            "dslTests": {"schemaVersion": 1, "defaultSet": "global_library", "testSets": {}, "testsByName": {}},
        }

        source = (
            'test "spark25_leftY"\n'
            'device "SPARKMAX/NEO 25"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "SPARKMAX/NEO 25".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 10.0\n"
        )

        class _FakeLifecycleService:
            def default_paths(self):
                return SimpleNamespace(canonical_profiles_path=Path("ignored.json"))

            def load_profiles_payload(self, _path):
                return payload

        service = LocalConfigQueryService(_FakeLifecycleService())
        with TemporaryDirectory() as temp_dir:
            library_dir = Path(temp_dir)
            (library_dir / "spark25_leftY.dsl").write_text(source, encoding="utf-8")
            with patch("tools.common.robot_test_dsl.service.dsl_global_library_dir", return_value=library_dir):
                self.assertEqual({"spark25_leftY": True}, service.external_library_test_runnable_map("home"))

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
