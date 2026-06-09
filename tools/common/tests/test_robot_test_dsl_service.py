from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.common.robot_test_dsl import (
    cleanup_stale_tests_in_store,
    import_test_into_root_payload,
    render_validation_text,
    resolve_profile_test_names,
    store_from_root_payload,
    validate_store_for_profile,
)


class RobotTestDslServiceTests(unittest.TestCase):
    """
    NAME
        RobotTestDslServiceTests - Validate shared host-side DSL workflow service behavior.
    """

    def _root_payload(self, include_controller: bool = True) -> dict[str, object]:
        devices = [
            {
                "label": "FALCON 9",
                "manufacturer": 4,
                "deviceType": 2,
                "id": 9,
                "model": "FALCON 500",
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
        ]
        profile_devices = ["FALCON 9"]
        if include_controller:
            profile_devices.append("controller0")
        return {
            "schema_version": 5,
            "default_profile": "demo",
            "profiles": {
                "demo": {
                    "devices": profile_devices,
                    "dslTestSet": "pit",
                }
            },
            "devices": devices,
        }

    def test_import_test_into_root_payload_updates_store_and_profile_set(self) -> None:
        payload = self._root_payload(include_controller=True)
        source = (
            'test "spin_up"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 3.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "spin_up.dsl"
            source_path.write_text(source, encoding="utf-8")

            result = import_test_into_root_payload(payload, "demo", "spin_up", source_path, set_name="pit")

        self.assertTrue(result.ok())
        store = store_from_root_payload(payload)
        self.assertIn("spin_up", store.tests_by_name)
        self.assertEqual(["spin_up"], store.test_sets["pit"])
        self.assertEqual("pit", payload["profiles"]["demo"]["dslTestSet"])

    def test_import_test_into_root_payload_blank_set_uses_profile_set(self) -> None:
        payload = self._root_payload(include_controller=True)
        source = (
            'test "spin_up"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 3.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "spin_up.dsl"
            source_path.write_text(source, encoding="utf-8")

            result = import_test_into_root_payload(payload, "demo", "spin_up", source_path, set_name=None)

        self.assertTrue(result.ok())
        self.assertEqual("pit", result.set_name)
        store = store_from_root_payload(payload)
        self.assertEqual(["spin_up"], store.test_sets["pit"])
        self.assertEqual("pit", payload["profiles"]["demo"]["dslTestSet"])

    def test_resolve_profile_test_names_prefers_profile_set(self) -> None:
        payload = self._root_payload(include_controller=True)
        payload["dslTests"] = {
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
        }

        self.assertEqual(["pit_one", "pit_two"], resolve_profile_test_names(payload, "demo"))

    def test_validate_store_for_profile_reports_unknown_profile(self) -> None:
        payload = self._root_payload(include_controller=True)
        store = store_from_root_payload(payload)

        result = validate_store_for_profile(payload, store, "missing")

        self.assertFalse(result.ok())
        self.assertIn("unknown profile: missing", render_validation_text(result, store))

    def test_validate_store_for_profile_only_checks_selected_profile_set(self) -> None:
        payload = self._root_payload(include_controller=True)
        payload["profiles"]["demo"]["dslTestSet"] = "pit"
        with tempfile.TemporaryDirectory() as temp_dir:
            good_path = Path(temp_dir) / "pit_good.dsl"
            good_path.write_text(
                'test "pit_good"\n'
                'device "FALCON 9"\n'
                'device "controller0"\n\n'
                "main:\n"
                '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
                "    until timer.elapsed >= 1.0\n",
                encoding="utf-8",
            )
            import_result = import_test_into_root_payload(payload, "demo", "pit_good", good_path, set_name="pit")
        self.assertTrue(import_result.ok())
        payload["dslTests"]["defaultSet"] = "robot_2026_swerve"
        payload["dslTests"]["testSets"]["robot_2026_swerve"] = ["swerve_only"]
        payload["dslTests"]["testsByName"]["swerve_only"] = {
            "source": 'test "swerve_only"\ndevice "Missing Device"\n\nmain:\n    until timer.elapsed >= 1.0\n',
            "sourceHash": "",
            "normalized": {
                "name": "swerve_only",
                "devices": [{"name": "Missing Device"}],
                "unsafeExit": [],
                "init": {},
                "main": {
                    "sets": [],
                    "clears": [],
                    "aborts": [],
                    "successes": [],
                    "untils": [{
                        "conditionId": "u1",
                        "kind": "until",
                        "text": "timer.elapsed >= 1.0",
                        "reference": {"device": "timer", "signal": "elapsed", "text": "timer.elapsed"},
                        "mode": "comparison",
                        "operator": ">=",
                        "literal": {"value": 1.0, "valueType": "number"},
                    }],
                    "requires": [],
                },
                "close": {"sets": [], "clears": [], "aborts": [], "successes": [], "untils": [], "requires": []},
            },
        }
        store = store_from_root_payload(payload)

        result = validate_store_for_profile(payload, store, "demo")

        self.assertTrue(result.ok(), render_validation_text(result, store))

    def test_import_warning_points_to_specific_until_line(self) -> None:
        payload = self._root_payload(include_controller=True)
        source = (
            'test "two_untils"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
            '    until "FALCON 9".position_delta > 150.0\n'
            "    until timer.elapsed >= 60.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "two_untils.dsl"
            source_path.write_text(source, encoding="utf-8")

            result = import_test_into_root_payload(payload, "demo", "two_untils", source_path, set_name="pit")

        self.assertTrue(result.ok())
        self.assertEqual(2, len(result.validation.warnings))
        text = render_validation_text(result.validation, store_from_root_payload(payload), entries_override={"two_untils": result.entry})
        self.assertIn("line 7: until \"FALCON 9\".position_delta > 150.0", text)
        self.assertIn("line 8: until timer.elapsed >= 60.0", text)

    def test_cleanup_stale_tests_removes_invalid_entries(self) -> None:
        payload = self._root_payload(include_controller=False)
        with tempfile.TemporaryDirectory() as temp_dir:
            good_path = Path(temp_dir) / "good_test.dsl"
            good_path.write_text(
                'test "good_test"\n'
                'device "FALCON 9"\n\n'
                "main:\n"
                "    until timer.elapsed >= 1.0\n",
                encoding="utf-8",
            )
            import_result = import_test_into_root_payload(payload, "demo", "good_test", good_path)
        self.assertTrue(import_result.ok())
        payload["dslTests"]["testSets"]["default"] = ["bad_test", "good_test"]
        payload["dslTests"]["testsByName"]["bad_test"] = {
            "source": 'test "bad_test"\ndevice "Missing Device"\n\nmain:\n    until timer.elapsed >= 1.0\n',
            "sourceHash": "",
            "normalized": {
                "name": "bad_test",
                "devices": [{"name": "Missing Device"}],
                "unsafeExit": [],
                "init": {},
                "main": {"untils": [{"id": "1", "kind": "until", "text": "timer.elapsed >= 1.0", "reference": {"device": "timer", "signal": "elapsed", "text": "timer.elapsed"}, "mode": "comparison", "operator": ">=", "literal": {"value": 1.0, "valueType": "number"}}]},
                "close": {},
            },
        }
        store = store_from_root_payload(payload)

        removed = cleanup_stale_tests_in_store(payload, store, "demo")

        self.assertEqual(["bad_test"], removed)
        self.assertIn("good_test", store.tests_by_name)
        self.assertNotIn("bad_test", store.tests_by_name)


if __name__ == "__main__":
    unittest.main()
