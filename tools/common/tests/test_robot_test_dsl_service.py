from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.common.robot_test_dsl import (
    create_blank_test_in_root_payload,
    copy_test_into_root_payload,
    cleanup_stale_tests_in_store,
    delete_external_library_test,
    delete_test_from_root_payload,
    import_test_into_root_payload,
    rename_external_library_test,
    rename_test_in_root_payload,
    resolve_runnable_profile_test_names,
    resolve_profile_device_dsl_type,
    render_validation_text,
    resolve_global_library_test_names,
    resolve_profile_test_names,
    resolve_profile_test_set_name,
    signal_catalog,
    store_from_root_payload,
    update_test_source_in_root_payload,
    validate_store_for_profile,
)
from tools.common.generate_robot_test_dsl_reference import generate_reference_payload


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

    def test_resolve_profile_device_dsl_type_infers_power_distribution_types(self) -> None:
        self.assertEqual(
            "PDP",
            resolve_profile_device_dsl_type(
                {
                    "manufacturer": 4,
                    "deviceType": 8,
                    "model": "PDP",
                    "type": "",
                }
            ),
        )

    def test_resolve_profile_device_dsl_type_normalizes_cancoder_alias_and_inference(self) -> None:
        self.assertEqual(
            "encoderExternal",
            resolve_profile_device_dsl_type(
                {
                    "manufacturer": 4,
                    "deviceType": 7,
                    "model": "CANCoder",
                    "type": "",
                }
            ),
        )

    def test_resolve_profile_device_dsl_type_normalizes_pigeon_alias_and_inference(self) -> None:
        self.assertEqual(
            "imu",
            resolve_profile_device_dsl_type(
                {
                    "manufacturer": 4,
                    "deviceType": 4,
                    "model": "Pigeon 2",
                    "type": "",
                }
            ),
        )
        self.assertEqual(
            "imu",
            resolve_profile_device_dsl_type(
                {
                    "manufacturer": 4,
                    "deviceType": 4,
                    "model": "Pigeon 2",
                    "type": "Pigeon",
                }
            ),
        )
        self.assertEqual(
            "encoderExternal",
            resolve_profile_device_dsl_type(
                {
                    "manufacturer": 4,
                    "deviceType": 7,
                    "model": "CANCoder",
                    "type": "CANCoder",
                }
            ),
        )

    def test_signal_catalog_includes_power_distribution_channel_signals(self) -> None:
        catalog = signal_catalog()

        self.assertIn("channel0_current", catalog["PDP"])
        self.assertIn("channel15_sticky_fault", catalog["PDP"])
        self.assertNotIn("channel16_current", catalog["PDP"])
        self.assertIn("channel23_current", catalog["PDH"])
        self.assertNotIn("channel24_fault", catalog["PDH"])
        self.assertEqual(
            "PDH",
            resolve_profile_device_dsl_type(
                {
                    "manufacturer": 5,
                    "deviceType": 8,
                    "model": "PDH",
                    "type": "",
                }
            ),
        )

    def test_signal_catalog_includes_run_scoped_aggregate_motor_signals(self) -> None:
        catalog = signal_catalog()

        self.assertIn("current_actual_max", catalog["motor"])
        self.assertIn("velocity_actual_max_abs", catalog["motor"])
        self.assertIn("position_delta_max_abs", catalog["motor"])
        self.assertIn("velocity_actual_max_abs", catalog["encoderExternal"])
        self.assertIn("position_delta_max_abs", catalog["encoderExternal"])
        self.assertIn("yaw_delta_max_abs", catalog["imu"])
        self.assertIn("angular_velocity_z", catalog["imu"])
        self.assertIn("accel_z", catalog["imu"])
        self.assertIn("supply_voltage", catalog["imu"])
        self.assertIn("faults", catalog["imu"])

    def test_generated_dsl_reference_payload_includes_device_docs_and_signals(self) -> None:
        payload = generate_reference_payload()

        topics = payload["topics"]
        topic_map = {}

        def _walk(nodes):
            for node in nodes:
                topic_id = str(node.get("id", "")).strip()
                if topic_id:
                    topic_map[topic_id] = node
                children = node.get("children")
                if isinstance(children, list):
                    _walk(children)

        _walk(topics)
        motor_topic = topic_map["topic_device_type_motor"]
        self.assertIn("Motor controller devices", motor_topic["summary"])
        self.assertTrue(any("current_actual_max" in line for line in motor_topic["signals"]))
        self.assertTrue(str(motor_topic.get("sourcePath", "")).endswith("motor.devices.md"))
        imu_topic = topic_map["topic_device_type_imu"]
        self.assertIn("orientation evidence", imu_topic["summary"])
        self.assertTrue(any("yaw_delta_max_abs" in line for line in imu_topic["signals"]))
        self.assertTrue(any("angular_velocity_z" in line for line in imu_topic["signals"]))
        self.assertTrue(any("supply_voltage" in line for line in imu_topic["signals"]))
        self.assertTrue(str(imu_topic.get("sourcePath", "")).endswith("imu.devices.md"))
        comments_topic = topic_map["topic_comments"]
        self.assertIn("# character starts a comment", " ".join(comments_topic["details"]))
        self.assertIn('device "cancoder"  # inline comment', comments_topic["syntax"])

    def test_import_test_into_root_payload_without_explicit_set_uses_profile_owned_set(self) -> None:
        payload = self._root_payload(include_controller=True)
        payload["profiles"]["demo"].pop("dslTestSet", None)
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

            result = import_test_into_root_payload(payload, "demo", "spin_up", source_path)

        self.assertTrue(result.ok())
        store = store_from_root_payload(payload)
        self.assertEqual("demo", result.set_name)
        self.assertEqual(["spin_up"], store.test_sets["demo"])
        self.assertEqual("demo", resolve_profile_test_set_name(payload, "demo"))

    def test_copy_test_into_root_payload_creates_profile_owned_copy(self) -> None:
        payload = self._root_payload(include_controller=True)
        payload["profiles"]["demo"].pop("dslTestSet", None)
        payload["dslTests"] = {
            "schemaVersion": 1,
            "defaultSet": "global_library",
            "testSets": {
                "global_library": ["swerve_global"],
            },
            "testsByName": {
                "swerve_global": {
                    "source": (
                        'test "swerve_global"\n'
                        'device "FALCON 9"\n'
                        'device "controller0"\n\n'
                        "main:\n"
                        '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
                        "    until timer.elapsed >= 1.0\n"
                    ),
                    "sourceHash": "",
                    "normalized": {
                        "name": "swerve_global",
                        "devices": [{"name": "FALCON 9"}, {"name": "controller0"}],
                        "unsafeExit": [],
                        "init": {},
                        "main": {},
                        "close": {},
                    },
                }
            },
        }

        result = copy_test_into_root_payload(payload, "demo", "swerve_global", "demo_spin")

        self.assertTrue(result.ok())
        store = store_from_root_payload(payload)
        self.assertEqual(["swerve_global"], resolve_global_library_test_names(payload))
        self.assertEqual(["demo_spin"], store.test_sets["demo"])
        self.assertEqual(["demo_spin"], resolve_profile_test_names(payload, "demo"))
        self.assertEqual("demo_spin", store.tests_by_name["demo_spin"].normalized.name)

    def test_create_blank_test_in_root_payload_creates_minimal_profile_test(self) -> None:
        payload = self._root_payload(include_controller=True)
        payload["profiles"]["demo"].pop("dslTestSet", None)

        result = create_blank_test_in_root_payload(payload, "demo", "fresh_test")

        self.assertTrue(result.ok(), render_validation_text(result.validation, store_from_root_payload(payload)))
        store = store_from_root_payload(payload)
        self.assertEqual("demo", result.set_name)
        self.assertIn("fresh_test", store.tests_by_name)
        self.assertIn('test "fresh_test"', store.tests_by_name["fresh_test"].source)
        self.assertEqual(["fresh_test"], resolve_profile_test_names(payload, "demo"))
        self.assertEqual("demo", resolve_profile_test_set_name(payload, "demo"))

    def test_update_test_source_in_root_payload_rewrites_profile_owned_source(self) -> None:
        payload = self._root_payload(include_controller=True)
        source = (
            'test "profile_test"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 1.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "profile_test.dsl"
            source_path.write_text(source, encoding="utf-8")
            import_result = import_test_into_root_payload(payload, "demo", "profile_test", source_path, set_name="pit")
        self.assertTrue(import_result.ok())

        updated_source = (
            'test "wrong_name"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY scaled 0.5 default 0.0\n'
            "    until timer.elapsed >= 1.0\n"
        )
        result = update_test_source_in_root_payload(payload, "demo", "profile_test", updated_source)

        self.assertTrue(result.ok(), render_validation_text(result.validation, store_from_root_payload(payload)))
        store = store_from_root_payload(payload)
        entry = store.tests_by_name["profile_test"]
        self.assertIn('test "profile_test"', entry.source)
        self.assertIn("scaled 0.5", entry.source)
        self.assertEqual("profile_test", entry.normalized.name)

    def test_rename_and_delete_config_backed_test_archives_source(self) -> None:
        payload = self._root_payload(include_controller=True)
        source = (
            'test "profile_test"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 1.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "profile_test.dsl"
            source_path.write_text(source, encoding="utf-8")
            import_test_into_root_payload(payload, "demo", "profile_test", source_path, set_name="pit")
            renamed = rename_test_in_root_payload(payload, "profile_test", "renamed_test")
            self.assertEqual("renamed_test", renamed.name)
            self.assertIn("renamed_test", store_from_root_payload(payload).tests_by_name)
            self.assertEqual(["renamed_test"], resolve_profile_test_names(payload, "demo"))
            with patch("tools.common.robot_test_dsl.service.dsl_test_archive_dir", return_value=Path(temp_dir) / "archive"):
                archive_path = delete_test_from_root_payload(payload, "renamed_test")
            self.assertTrue(archive_path.exists())
            self.assertNotIn("renamed_test", store_from_root_payload(payload).tests_by_name)

    def test_rename_and_delete_external_library_test_archives_source(self) -> None:
        source = (
            'test "global_test"\n'
            'device "FALCON 9"\n'
            "main:\n"
            "    until timer.elapsed >= 1.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            library_dir = Path(temp_dir) / "library"
            library_dir.mkdir(parents=True, exist_ok=True)
            archive_dir = Path(temp_dir) / "archive"
            (library_dir / "global_test.dsl").write_text(source, encoding="utf-8")
            renamed_path = rename_external_library_test("global_test", "renamed_global", library_dir)
            self.assertTrue(renamed_path.exists())
            self.assertFalse((library_dir / "global_test.dsl").exists())
            with patch("tools.common.robot_test_dsl.service.dsl_test_archive_dir", return_value=archive_dir):
                archived_path = delete_external_library_test("renamed_global", library_dir)
            self.assertTrue(archived_path.exists())
            self.assertFalse((library_dir / "renamed_global.dsl").exists())

    def test_update_test_source_in_root_payload_reports_multiple_compile_errors(self) -> None:
        payload = self._root_payload(include_controller=True)
        payload["devices"].append(
            {
                "label": "SPARKMAX/NEO 25",
                "manufacturer": 2,
                "deviceType": 2,
                "id": 25,
                "model": "SPARK MAX",
                "type": "motor",
                "deviceInterface": "CAN",
            }
        )
        payload["profiles"]["demo"]["devices"] = ["SPARKMAX/NEO 25", "controller0"]
        source = (
            'test "profile_test"\n'
            'device "SPARKMAX/NEO 25"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "SPARKMAX/NEO 25".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 1.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "profile_test.dsl"
            source_path.write_text(source, encoding="utf-8")
            import_result = import_test_into_root_payload(payload, "demo", "profile_test", source_path, set_name="pit")
        self.assertTrue(import_result.ok())

        bad_source = (
            'test "profile_test"\n'
            'device "SPARKMAX/NEO 25"\n'
            'device "controller0"\n\n'
            "init:\n"
            "    xxx:\n\n"
            "main:\n"
            '    set "SPARKMAX/NEO 25".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0\n'
            '    set "bogus".output_speed = 0.75\n'
            '    set "SPARKMAX/NEO 25".output_nonexistant_cmd = controller0.leftY\n'
            "    until timer.elapsed >= 1.0\n\n"
            "bogus:\n"
            "\nclosed:\n"
        )

        result = update_test_source_in_root_payload(payload, "demo", "profile_test", bad_source)
        text = render_validation_text(result.validation, store_from_root_payload(payload), entries_override={"profile_test": result.entry})

        self.assertFalse(result.ok())
        self.assertIn("Compile error at line 6: unknown phase header: xxx:", text)
        self.assertNotIn('Compile error at line 6: unknown phase header: xxx: (line 1:', text)
        self.assertIn('undeclared device reference (line 10: set "bogus".output_speed = 0.75)', text)
        self.assertIn('unknown signal on device "bogus": output_speed (line 10: set "bogus".output_speed = 0.75)', text)
        self.assertIn(
            'unknown signal on device "SPARKMAX/NEO 25": output_nonexistant_cmd '
            '(line 11: set "SPARKMAX/NEO 25".output_nonexistant_cmd = controller0.leftY)',
            text,
        )
        self.assertIn("Compile error at line 14: unknown phase header: bogus:", text)
        self.assertIn("Compile error at line 16: unknown phase header: closed:", text)
        store = store_from_root_payload(payload)
        self.assertIn("profile_test", resolve_profile_test_names(payload, "demo"))
        self.assertEqual([], resolve_runnable_profile_test_names(payload, "demo"))
        self.assertFalse(store.tests_by_name["profile_test"].runnable)

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

    def test_resolve_profile_test_names_requires_explicit_profile_set(self) -> None:
        payload = self._root_payload(include_controller=True)
        payload["profiles"]["demo"].pop("dslTestSet", None)
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

        self.assertEqual([], resolve_profile_test_names(payload, "demo"))

    def test_resolve_runnable_profile_test_names_excludes_invalid_saved_tests(self) -> None:
        payload = self._root_payload(include_controller=True)
        source = (
            'test "profile_test"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 1.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "profile_test.dsl"
            source_path.write_text(source, encoding="utf-8")
            import_result = import_test_into_root_payload(payload, "demo", "profile_test", source_path, set_name="pit")
        self.assertTrue(import_result.ok())
        bad_source = (
            'test "profile_test"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".missing_output = controller0.leftY\n'
            "    until timer.elapsed >= 1.0\n"
        )
        update_result = update_test_source_in_root_payload(payload, "demo", "profile_test", bad_source)
        self.assertFalse(update_result.ok())
        self.assertEqual(["profile_test"], resolve_profile_test_names(payload, "demo"))
        self.assertEqual([], resolve_runnable_profile_test_names(payload, "demo"))

    def test_validate_store_for_profile_reports_unknown_profile(self) -> None:
        payload = self._root_payload(include_controller=True)
        store = store_from_root_payload(payload)

        result = validate_store_for_profile(payload, store, "missing")

        self.assertFalse(result.ok())
        self.assertIn("unknown profile: missing", render_validation_text(result, store))

    def test_validate_store_for_profile_ignores_global_library_tests(self) -> None:
        payload = self._root_payload(include_controller=True)
        source = (
            'test "profile_test"\n'
            'device "FALCON 9"\n\n'
            "main:\n"
            "    require timer.elapsed >= 0.0\n"
            "    until timer.elapsed >= 1.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "profile_test.dsl"
            source_path.write_text(source, encoding="utf-8")
            import_result = import_test_into_root_payload(
                payload,
                "demo",
                "profile_test",
                source_path,
                set_name="pit",
            )
        self.assertTrue(import_result.ok(), render_validation_text(import_result.validation, store_from_root_payload(payload)))
        payload["dslTests"]["defaultSet"] = "global_library"
        payload["dslTests"]["testSets"]["global_library"] = ["swerve_global"]
        payload["dslTests"]["testsByName"]["swerve_global"] = {
            "source": (
                'test "swerve_global"\n'
                'device "Missing Device"\n\n'
                "main:\n"
                "    until timer.elapsed >= 1.0\n"
            ),
            "sourceHash": "",
            "normalized": {
                "name": "swerve_global",
                "devices": [{"name": "Missing Device"}],
                "unsafeExit": [],
                "init": {},
                "main": {
                    "untils": [
                        {
                            "id": "1",
                            "kind": "until",
                            "text": "timer.elapsed >= 1.0",
                            "reference": {
                                "device": "timer",
                                "signal": "elapsed",
                                "text": "timer.elapsed",
                            },
                            "mode": "comparison",
                            "operator": ">=",
                            "literal": {"value": 1.0, "valueType": "number"},
                        }
                    ]
                },
                "close": {},
            },
        }
        store = store_from_root_payload(payload)

        result = validate_store_for_profile(payload, store, "demo")
        text = render_validation_text(result, store)

        self.assertTrue(result.ok(), text)
        self.assertEqual("OK", text)

    def test_render_validation_text_includes_line_numbers_for_warnings_and_meta_errors(self) -> None:
        payload = self._root_payload(include_controller=True)
        source = (
            'test "warn_test"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 1.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "warn_test.dsl"
            source_path.write_text(source, encoding="utf-8")
            import_result = import_test_into_root_payload(payload, "demo", "warn_test", source_path, set_name="pit")
        self.assertTrue(import_result.ok())
        warning_text = render_validation_text(
            import_result.validation,
            store_from_root_payload(payload),
            entries_override={"warn_test": import_result.entry},
        )
        self.assertIn("line 7: until timer.elapsed >= 1.0", warning_text)

        store = store_from_root_payload(payload)
        entry = store.tests_by_name.get("warn_test")
        self.assertIsNotNone(entry)
        payload["dslTests"]["testsByName"]["warn_test"]["normalized"]["name"] = "wrong_name"
        mismatch_store = store_from_root_payload(payload)
        mismatch_result = validate_store_for_profile(payload, mismatch_store, "demo")
        self.assertFalse(mismatch_result.ok())
        mismatch_text = render_validation_text(mismatch_result, mismatch_store)
        self.assertIn('line 1: test "warn_test"', mismatch_text)

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
