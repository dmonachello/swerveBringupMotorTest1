"""
NAME
    test_evidence_fusion_replay_scenarios.py - Regression coverage for the offline evidence-fusion replay harness.
"""

import unittest

from tools.common.evidence_fusion.replay_scenarios import (
    _load_scenario_payload,
    _run_scenario_payload,
    _scenario_paths,
)

SCENARIO_PRESENT_ONLY = "present_only"
SCENARIO_HEALTHY_FULL_PROOF = "healthy_full_proof"
SCENARIO_POWERED_MULTI = "can_bus_powered_healthy_multi_device"
SCENARIO_UNPOWERED_MULTI = "can_bus_unpowered_multi_device"
SCENARIO_RIO_ALIVE_BRANCH_DEAD = "roborio_alive_can_devices_dead"
SCENARIO_REPEAT_TIMEOUT = "single_device_timeout_repeated"
SCENARIO_PASSIVE_CONSOLE_CONFLICT = "passive_present_console_failed_conflict"
SCENARIO_EXPIRY_TO_UNKNOWN = "expiry_to_unknown"
SCENARIO_COMMUNICATION_CONFLICT = "communication_conflict"
DEVICE_LABEL_FALCON = "FALCON 9"
DEVICE_LABEL_SPARK7 = "SPARKMAX/NEO 7"
DEVICE_LABEL_RIO = "roborio"
DEVICE_LABEL_CANCODER = "cancoder"


class EvidenceFusionReplayScenarioTests(unittest.TestCase):
    def test_scenario_directory_contains_committed_replay_fixtures(self) -> None:
        paths = _scenario_paths()

        self.assertGreaterEqual(len(paths), 11)

    def test_present_only_fixture_runs_and_yields_unproven_operability(self) -> None:
        payload = _load_scenario_payload(SCENARIO_PRESENT_ONLY)

        report = _run_scenario_payload(payload, verbose=False)
        device_result = report["snapshot"]["configured_devices"][DEVICE_LABEL_FALCON]

        self.assertEqual("PRESENT", device_result["dimensions"]["existence"]["value"])
        self.assertEqual("UNPROVEN", device_result["dimensions"]["operability"]["value"])
        self.assertEqual("CAUTION", device_result["overallState"])

    def test_healthy_full_proof_fixture_runs_and_yields_healthy_overall_state(self) -> None:
        payload = _load_scenario_payload(SCENARIO_HEALTHY_FULL_PROOF)

        report = _run_scenario_payload(payload, verbose=False)
        device_result = report["snapshot"]["configured_devices"][DEVICE_LABEL_FALCON]

        self.assertEqual("HEALTHY", device_result["overallState"])
        self.assertEqual("HEALTHY", device_result["dimensions"]["communication"]["value"])
        self.assertEqual("WORKING", device_result["dimensions"]["operability"]["value"])
        self.assertEqual("MATCHING", device_result["dimensions"]["identity"]["value"])

    def test_unpowered_single_device_fixture_runs_and_yields_failed_communication(self) -> None:
        payload = _load_scenario_payload("can_bus_unpowered_single_device")

        report = _run_scenario_payload(payload, verbose=False)
        device_result = report["snapshot"]["configured_devices"][DEVICE_LABEL_SPARK7]

        self.assertEqual("PRESENT", device_result["dimensions"]["existence"]["value"])
        self.assertEqual("FAILED", device_result["dimensions"]["communication"]["value"])
        self.assertEqual("FAILED", device_result["overallState"])

    def test_powered_multi_device_fixture_runs_and_keeps_all_devices_present(self) -> None:
        payload = _load_scenario_payload(SCENARIO_POWERED_MULTI)

        report = _run_scenario_payload(payload, verbose=False)
        configured_devices = report["snapshot"]["configured_devices"]

        self.assertEqual("PRESENT", configured_devices[DEVICE_LABEL_FALCON]["dimensions"]["existence"]["value"])
        self.assertEqual("HEALTHY", configured_devices[DEVICE_LABEL_FALCON]["dimensions"]["communication"]["value"])
        self.assertEqual("PRESENT", configured_devices[DEVICE_LABEL_SPARK7]["dimensions"]["existence"]["value"])
        self.assertEqual("HEALTHY", configured_devices[DEVICE_LABEL_SPARK7]["dimensions"]["communication"]["value"])
        self.assertEqual("PRESENT", configured_devices[DEVICE_LABEL_RIO]["dimensions"]["existence"]["value"])
        self.assertEqual("HEALTHY", configured_devices[DEVICE_LABEL_RIO]["dimensions"]["communication"]["value"])
        self.assertEqual("HEALTHY", configured_devices[DEVICE_LABEL_FALCON]["overallState"])
        self.assertEqual("HEALTHY", configured_devices[DEVICE_LABEL_SPARK7]["overallState"])
        self.assertEqual("HEALTHY", configured_devices[DEVICE_LABEL_RIO]["overallState"])

    def test_unpowered_multi_device_fixture_runs_and_marks_branch_devices_failed(self) -> None:
        payload = _load_scenario_payload(SCENARIO_UNPOWERED_MULTI)

        report = _run_scenario_payload(payload, verbose=False)
        configured_devices = report["snapshot"]["configured_devices"]

        self.assertEqual("FAILED", configured_devices[DEVICE_LABEL_FALCON]["dimensions"]["communication"]["value"])
        self.assertEqual("FAILED", configured_devices[DEVICE_LABEL_SPARK7]["dimensions"]["communication"]["value"])
        self.assertEqual("FAILED", configured_devices[DEVICE_LABEL_CANCODER]["dimensions"]["communication"]["value"])

    def test_roborio_alive_branch_dead_fixture_preserves_controller_health(self) -> None:
        payload = _load_scenario_payload(SCENARIO_RIO_ALIVE_BRANCH_DEAD)

        report = _run_scenario_payload(payload, verbose=False)
        configured_devices = report["snapshot"]["configured_devices"]

        self.assertEqual("HEALTHY", configured_devices[DEVICE_LABEL_RIO]["dimensions"]["communication"]["value"])
        self.assertEqual("HEALTHY", configured_devices[DEVICE_LABEL_RIO]["overallState"])
        self.assertEqual("FAILED", configured_devices[DEVICE_LABEL_SPARK7]["dimensions"]["communication"]["value"])

    def test_repeated_timeout_fixture_collapses_to_one_failed_dimension_result(self) -> None:
        payload = _load_scenario_payload(SCENARIO_REPEAT_TIMEOUT)

        report = _run_scenario_payload(payload, verbose=False)
        configured_devices = report["snapshot"]["configured_devices"]
        device_result = configured_devices[DEVICE_LABEL_SPARK7]

        self.assertEqual("FAILED", device_result["dimensions"]["communication"]["value"])
        self.assertEqual(1, device_result["dimensions"]["communication"]["independentGroups"])
        self.assertEqual(2, device_result["evidenceCount"])
        self.assertEqual("FAILED", device_result["overallState"])

    def test_passive_console_conflict_fixture_sets_conflict_flag(self) -> None:
        payload = _load_scenario_payload(SCENARIO_PASSIVE_CONSOLE_CONFLICT)

        report = _run_scenario_payload(payload, verbose=False)
        configured_devices = report["snapshot"]["configured_devices"]
        communication_result = configured_devices[DEVICE_LABEL_SPARK7]["dimensions"]["communication"]

        self.assertTrue(communication_result["conflict"])
        self.assertEqual("CAUTION", configured_devices[DEVICE_LABEL_SPARK7]["overallState"])

    def test_expiry_fixture_falls_back_to_unknown_after_support_expires(self) -> None:
        payload = _load_scenario_payload(SCENARIO_EXPIRY_TO_UNKNOWN)

        report = _run_scenario_payload(payload, verbose=False)
        configured_devices = report["snapshot"]["configured_devices"]
        communication_result = configured_devices[DEVICE_LABEL_FALCON]["dimensions"]["communication"]

        self.assertEqual("UNKNOWN", communication_result["value"])
        self.assertEqual(0.0, communication_result["confidence"])

    def test_communication_conflict_fixture_uses_caution_overall_state(self) -> None:
        payload = _load_scenario_payload(SCENARIO_COMMUNICATION_CONFLICT)

        report = _run_scenario_payload(payload, verbose=False)
        configured_devices = report["snapshot"]["configured_devices"]

        self.assertTrue(configured_devices[DEVICE_LABEL_FALCON]["dimensions"]["communication"]["conflict"])
        self.assertEqual("CAUTION", configured_devices[DEVICE_LABEL_FALCON]["overallState"])
