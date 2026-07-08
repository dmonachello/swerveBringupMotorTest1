from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.common.config_api import (
    blank_profile_payload,
    blank_topology_entry,
    ConfigEditSession,
    ConfigRepository,
    create_blank_profile,
    delete_profile,
    ensure_profile_topology_entry,
    rename_profile,
    replace_profile_devices,
    replace_profile_topology_entry,
    set_default_profile,
    upsert_profile,
)
from tools.common.config_lifecycle import ConfigLifecycleService


class ConfigApiRepositoryTests(unittest.TestCase):
    """
    NAME
        ConfigApiRepositoryTests - Validate the first shared config API repository slice.
    """

    def test_load_path_returns_snapshot_queries(self) -> None:
        service = ConfigLifecycleService()
        payload = {
            "schema_version": 1,
            "profiles": {
                "beta": {},
                "alpha": {},
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bringup_system.json"
            service.sync_profiles_payload(
                payload,
                canonical_path=path,
                deploy_path=path,
                stamp=False,
            )
            repo = ConfigRepository(service)
            snapshot = repo.load_path(path)
            self.assertEqual(["alpha", "beta"], snapshot.profiles().list_names())
            self.assertEqual(path, snapshot.source.path)

    def test_sync_updates_canonical_and_deploy(self) -> None:
        service = ConfigLifecycleService()
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            canonical = base / "canonical.json"
            deploy = base / "deploy" / "bringup_system.json"
            payload = {
                "schema_version": 1,
                "profiles": {
                    "home": {},
                },
            }
            service.sync_profiles_payload(
                payload,
                canonical_path=canonical,
                deploy_path=deploy,
                stamp=False,
            )

            class _FakeLifecycleService(ConfigLifecycleService):
                def default_paths(self_inner):
                    return type(
                        "Paths",
                        (),
                        {
                            "canonical_profiles_path": canonical,
                            "deploy_profiles_path": deploy,
                        },
                    )()

            repo = ConfigRepository(_FakeLifecycleService())
            session = repo.begin_canonical_edit()
            self.assertIsInstance(session, ConfigEditSession)
            session.to_payload()["default_profile"] = "home"
            session.mark_dirty()

            result = repo.sync(session, stamp=False)

            self.assertTrue(result.synced)
            self.assertTrue(canonical.exists())
            self.assertTrue(deploy.exists())
            self.assertEqual("home", repo.load_canonical().to_payload()["default_profile"])

    def test_replace_profile_devices_preserves_profile_metadata(self) -> None:
        profile = {
            "devices": ["oldMotor"],
            "dslTestSet": "test_minimal_25_9",
            "notes": "keep me",
        }

        updated = replace_profile_devices(profile, ["newMotor", "controller0", "newMotor"])

        self.assertEqual(["newMotor", "controller0"], updated["devices"])
        self.assertEqual("test_minimal_25_9", updated["dslTestSet"])
        self.assertEqual("keep me", updated["notes"])

    def test_blank_profile_and_topology_payloads_use_canonical_shapes(self) -> None:
        self.assertEqual({"devices": []}, blank_profile_payload())
        self.assertEqual(
            {
                "version": 1,
                "source": "local",
                "nodes": [],
                "edges": [],
            },
            blank_topology_entry(),
        )

    def test_upsert_profile_sets_default_and_preserves_unrelated_entries(self) -> None:
        payload = {
            "profiles": {
                "existing": {"devices": ["motor0"]},
            },
            "topology": {
                "version": 1,
                "source": "local",
                "profiles": {
                    "existing": {"nodes": [{"deviceRef": "motor0"}], "edges": []},
                },
            },
        }

        upsert_profile(
            payload,
            "alpha",
            {"devices": ["motor1"], "dslTestSet": "alpha"},
            topology_entry={"nodes": [{"deviceRef": "motor1"}], "edges": []},
            diagram_entry={"nodes": [{"key": 1}]},
            set_default_if_missing=True,
        )

        self.assertEqual("alpha", payload["default_profile"])
        self.assertEqual(["motor0"], payload["profiles"]["existing"]["devices"])
        self.assertEqual("alpha", payload["profiles"]["alpha"]["dslTestSet"])
        self.assertEqual(
            {"nodes": [{"deviceRef": "motor1"}], "edges": []},
            payload["topology"]["profiles"]["alpha"],
        )
        self.assertEqual({"nodes": [{"key": 1}]}, payload["diagram"]["profiles"]["alpha"])

    def test_rename_profile_updates_profile_topology_diagram_and_default(self) -> None:
        payload = {
            "default_profile": "alpha",
            "profiles": {
                "alpha": {"devices": ["motor1"]},
            },
            "topology": {
                "version": 1,
                "source": "local",
                "profiles": {
                    "alpha": {"nodes": [{"deviceRef": "motor1"}], "edges": []},
                },
            },
            "diagram": {
                "profiles": {
                    "alpha": {"nodes": [{"key": 1}]},
                },
            },
        }

        rename_profile(payload, "alpha", "beta")

        self.assertEqual("beta", payload["default_profile"])
        self.assertNotIn("alpha", payload["profiles"])
        self.assertIn("beta", payload["profiles"])
        self.assertIn("beta", payload["topology"]["profiles"])
        self.assertIn("beta", payload["diagram"]["profiles"])

    def test_delete_profile_removes_shared_entries_and_default(self) -> None:
        payload = {
            "default_profile": "alpha",
            "profiles": {
                "alpha": {"devices": ["motor1"]},
                "beta": {"devices": ["motor2"]},
            },
            "topology": {
                "version": 1,
                "source": "local",
                "profiles": {
                    "alpha": {"nodes": [{"deviceRef": "motor1"}], "edges": []},
                    "beta": {"nodes": [{"deviceRef": "motor2"}], "edges": []},
                },
            },
            "diagram": {
                "profiles": {
                    "alpha": {"nodes": [{"key": 1}]},
                    "beta": {"nodes": [{"key": 2}]},
                },
            },
        }

        delete_profile(payload, "alpha")

        self.assertNotIn("default_profile", payload)
        self.assertNotIn("alpha", payload["profiles"])
        self.assertNotIn("alpha", payload["topology"]["profiles"])
        self.assertNotIn("alpha", payload["diagram"]["profiles"])
        self.assertIn("beta", payload["profiles"])

    def test_replace_profile_topology_entry_preserves_other_profiles(self) -> None:
        payload = {
            "profiles": {
                "alpha": {"devices": ["motor1"]},
                "beta": {"devices": ["motor2"]},
            },
            "topology": {
                "version": 1,
                "source": "local",
                "profiles": {
                    "alpha": {"nodes": [{"deviceRef": "motor1"}], "edges": []},
                    "beta": {"nodes": [{"deviceRef": "motor2"}], "edges": []},
                },
            },
        }

        replace_profile_topology_entry(
            payload,
            "alpha",
            {"nodes": [{"deviceRef": "motor1"}, {"deviceRef": "controller0"}], "edges": []},
        )

        self.assertEqual(
            {"nodes": [{"deviceRef": "motor2"}], "edges": []},
            payload["topology"]["profiles"]["beta"],
        )
        self.assertEqual(
            {"nodes": [{"deviceRef": "motor1"}, {"deviceRef": "controller0"}], "edges": []},
            payload["topology"]["profiles"]["alpha"],
        )

    def test_create_blank_profile_and_set_default_are_shared_operations(self) -> None:
        payload = {
            "profiles": {},
        }

        create_blank_profile(payload, "alpha", set_default_if_missing=True)
        set_default_profile(payload, "alpha")

        self.assertEqual("alpha", payload["default_profile"])
        self.assertEqual({"devices": []}, payload["profiles"]["alpha"])
        self.assertEqual(
            {
                "version": 1,
                "source": "local",
                "nodes": [],
                "edges": [],
            },
            payload["topology"]["profiles"]["alpha"],
        )

    def test_ensure_profile_topology_entry_normalizes_missing_lists(self) -> None:
        payload = {
            "profiles": {
                "alpha": {"devices": []},
            },
            "topology": {
                "version": 1,
                "source": "local",
                "profiles": {
                    "alpha": {"nodes": "bad", "edges": "bad"},
                },
            },
        }

        entry = ensure_profile_topology_entry(payload, "alpha")

        self.assertEqual([], entry["nodes"])
        self.assertEqual([], entry["edges"])


if __name__ == "__main__":
    unittest.main()
