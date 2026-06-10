from __future__ import annotations

"""
NAME
    test_cross_surface_regression.py - Cross-surface bringup config regression checks.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import tools.can_topology.can_top_editor as can_top_editor
import tools.can_topology.tests.test_can_top_editor_profile_load as topology_profile_load_tests
from tools.can_nt.bridge_cli import BridgeCli
from tools.can_nt.status import SS__CONFIG__VALID
from tools.can_topology.validate_profiles import Reporter, load_profiles_json, validate_profiles
from tools.common.profile_constants import KEY_DEFAULT_PROFILE, KEY_PROFILES
from tools.config.schema_store import ConfigSchemaStore

REPO_ROOT_DEPTH = 3
PROFILE_NAME = "robot_2026_swerve"
BRINGUP_FILENAME = "bringup_system.json"
BRINGUP_BINDINGS_FILENAME = "bringup_bindings.json"
DIR_DATA = "data"
DIR_SRC = "src"
DIR_MAIN = "main"
DIR_DEPLOY = "deploy"
DIR_TESTS = "tests"
DIR_REGRESSION = "regression"
DIR_FIXTURES = "fixtures"
DIR_CONFIG_CATALOG = "config_catalog"
MESSAGE_VALIDATE_STORE = "cross-surface store validation errors"
MESSAGE_VALIDATE_PROFILE = "cross-surface profile validation errors"
MESSAGE_VALIDATE_CLI = "cross-surface CLI validation failed"
MESSAGE_TOPOLOGY_EMPTY = "cross-surface CLI topology lookup returned no device topology"
MESSAGE_NEIGHBORS_EMPTY = "cross-surface CLI topology lookup returned no neighbors"


class _SessionStub:
    """
    NAME
        _SessionStub - Minimal disconnected CLI session stand-in.
    """

    @staticmethod
    def is_connected() -> bool:
        return False

    @staticmethod
    def get_state_snapshot() -> dict:
        return {}

    @staticmethod
    def session_id() -> str:
        return ""

    @staticmethod
    def handshake_done() -> bool:
        return False

    @staticmethod
    def disconnect() -> None:
        return None

    @staticmethod
    def send_command(_name: str, _args: dict | None = None):
        return None


class CrossSurfaceRegressionTests(unittest.TestCase):
    """
    NAME
        CrossSurfaceRegressionTests - Ensure topology-editor output stays consumable across surfaces.
    """

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[REPO_ROOT_DEPTH]

    @classmethod
    def _source_profiles_path(cls) -> Path:
        return (
            cls._repo_root()
            / DIR_TESTS
            / DIR_REGRESSION
            / DIR_FIXTURES
            / DIR_CONFIG_CATALOG
            / PROFILE_NAME
            / BRINGUP_FILENAME
        )

    @classmethod
    def _source_bindings_path(cls) -> Path:
        return (
            cls._repo_root()
            / DIR_TESTS
            / DIR_REGRESSION
            / DIR_FIXTURES
            / DIR_CONFIG_CATALOG
            / PROFILE_NAME
            / BRINGUP_BINDINGS_FILENAME
        )

    @staticmethod
    def _temp_repo_paths(root: Path) -> tuple[Path, Path, Path, Path]:
        data_path = root / DIR_DATA / BRINGUP_FILENAME
        deploy_path = root / DIR_SRC / DIR_MAIN / DIR_DEPLOY / BRINGUP_FILENAME
        root_bindings_path = root / BRINGUP_BINDINGS_FILENAME
        deploy_bindings_path = root / DIR_SRC / DIR_MAIN / DIR_DEPLOY / BRINGUP_BINDINGS_FILENAME
        data_path.parent.mkdir(parents=True, exist_ok=True)
        deploy_path.parent.mkdir(parents=True, exist_ok=True)
        root_bindings_path.parent.mkdir(parents=True, exist_ok=True)
        deploy_bindings_path.parent.mkdir(parents=True, exist_ok=True)
        return data_path, deploy_path, root_bindings_path, deploy_bindings_path

    @staticmethod
    def _build_cli(payload: dict[str, object]) -> BridgeCli:
        cli = BridgeCli(_SessionStub(), batch=True)
        cli._local_root_payload = payload
        cli._groups_profile = None
        cli._profiles_dirty = False
        cli._active_group_members = []
        return cli

    @staticmethod
    def _topology_device_with_neighbors(cli: BridgeCli) -> dict[str, object]:
        payload = cli._local_root_payload
        if not isinstance(payload, dict):
            return {}
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            return {}
        profile_name = payload.get(KEY_DEFAULT_PROFILE)
        if not isinstance(profile_name, str) or profile_name not in profiles:
            profile_name = next(iter(profiles.keys()), "")
        entry = profiles.get(profile_name)
        if not isinstance(entry, dict):
            return {}
        labels = entry.get("devices")
        if not isinstance(labels, list):
            return {}
        for label in labels:
            topology = cli._local_device_topology(str(label))
            neighbor_ports = topology.get("neighborPorts")
            neighbor_links = topology.get("neighborLinks")
            if isinstance(neighbor_ports, list) and neighbor_ports:
                return topology
            if isinstance(neighbor_links, list) and neighbor_links:
                return topology
        return {}

    def test_topology_editor_roundtrip_stays_readable_by_cli_and_store(self) -> None:
        original_messagebox = can_top_editor.messagebox
        can_top_editor.messagebox = topology_profile_load_tests._MessageBoxStub
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_root = Path(temp_dir)
                (
                    temp_data_path,
                    temp_deploy_path,
                    temp_root_bindings_path,
                    temp_deploy_bindings_path,
                ) = self._temp_repo_paths(temp_root)
                shutil.copy2(self._source_profiles_path(), temp_data_path)
                shutil.copy2(self._source_bindings_path(), temp_root_bindings_path)
                shutil.copy2(self._source_bindings_path(), temp_deploy_bindings_path)

                editor = topology_profile_load_tests.TopologyEditorProfileLoadTests._headless_editor(
                    PROFILE_NAME
                )
                editor._load_profile_from_path(
                    str(self._source_profiles_path()),
                    ask_profile=False,
                    confirm_discard=False,
                    selected_name=PROFILE_NAME,
                )
                editor.entry_profile.set(PROFILE_NAME)
                editor.var_set_default.set(True)
                editor._save_profile_to_path(
                    temp_data_path,
                    prompt_replace=False,
                    update_source=True,
                )
                shutil.copy2(temp_data_path, temp_deploy_path)

                payload = load_profiles_json(temp_data_path)
                errors, warnings = validate_profiles(payload, Reporter(False))
                self.assertEqual([], errors, f"{MESSAGE_VALIDATE_PROFILE}: {errors}")
                self.assertEqual([], warnings, warnings)

                store = ConfigSchemaStore()
                store.load(repo_root=temp_root)
                result = store.validate(strict=True)
                self.assertTrue(
                    result.ok(),
                    f"{MESSAGE_VALIDATE_STORE}: {[issue.message for issue in result.errors()]}",
                )

                cli = self._build_cli(payload)
                ok, error, raw, parsed = cli._read_registry_raw(str(temp_data_path))
                self.assertTrue(ok, error)
                self.assertTrue(raw.strip())
                self.assertIsInstance(parsed, dict)
                assert isinstance(parsed, dict)
                valid, message = cli._validate_registry_payload(parsed, "")
                self.assertTrue(valid, f"{MESSAGE_VALIDATE_CLI}: {message}")

                topology = self._topology_device_with_neighbors(cli)
                self.assertTrue(topology, MESSAGE_TOPOLOGY_EMPTY)
                self.assertTrue(
                    topology.get("neighborPorts") or topology.get("neighborLinks"),
                    MESSAGE_NEIGHBORS_EMPTY,
                )

                reloaded_editor = (
                    topology_profile_load_tests.TopologyEditorProfileLoadTests._headless_editor(
                        PROFILE_NAME
                    )
                )
                reloaded_editor._load_profile_from_path(
                    str(temp_data_path),
                    ask_profile=False,
                    confirm_discard=False,
                    selected_name=PROFILE_NAME,
                )
                before_payload = (
                    topology_profile_load_tests.TopologyEditorProfileLoadTests._canonical_roundtrip_payload(
                        editor
                    )
                )
                after_payload = (
                    topology_profile_load_tests.TopologyEditorProfileLoadTests._canonical_roundtrip_payload(
                        reloaded_editor
                    )
                )
                self.assertEqual(before_payload, after_payload)
        finally:
            can_top_editor.messagebox = original_messagebox

    def test_cli_validate_file_accepts_topology_editor_saved_config(self) -> None:
        original_messagebox = can_top_editor.messagebox
        can_top_editor.messagebox = topology_profile_load_tests._MessageBoxStub
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / BRINGUP_FILENAME
                editor = topology_profile_load_tests.TopologyEditorProfileLoadTests._headless_editor(
                    PROFILE_NAME
                )
                editor._load_profile_from_path(
                    str(self._source_profiles_path()),
                    ask_profile=False,
                    confirm_discard=False,
                    selected_name=PROFILE_NAME,
                )
                editor.entry_profile.set(PROFILE_NAME)
                editor.var_set_default.set(True)
                editor._save_profile_to_path(
                    temp_path,
                    prompt_replace=False,
                    update_source=True,
                )

                cli = self._build_cli({})
                result = cli._validate_file(str(temp_path), repair=False)

                self.assertEqual(SS__CONFIG__VALID, result.code)
        finally:
            can_top_editor.messagebox = original_messagebox


if __name__ == "__main__":
    unittest.main()
