from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.common.config_api import ConfigEditSession, ConfigRepository
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


if __name__ == "__main__":
    unittest.main()
