"""
NAME
    test_can_fault_inference.py - Tests for host-side CAN fault candidates.
"""

from __future__ import annotations

import unittest

from tools.can_nt.can_fault_inference import (
    CATEGORY_BUS_PATH,
    CATEGORY_DEVICE_LOCAL,
    FAULT_CLASS_BRANCH,
    FAULT_CLASS_CONTROLLER_SIDE,
    FAULT_CLASS_INSUFFICIENT,
    FAULT_CLASS_SINGLE_DEVICE,
    STATUS_NO_FAULT,
    build_fault_diagnosis,
    render_fault_diagnosis,
)


class CanFaultInferenceTests(unittest.TestCase):
    def test_no_fault_when_all_rows_are_healthy(self) -> None:
        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "FALCON 9",
                    "existence": "PRESENT",
                    "operability": "OK",
                    "identity": "MATCHING",
                    "confidence": "HIGH",
                    "state": "ok",
                }
            ],
            now_s=10.0,
        )

        self.assertEqual(STATUS_NO_FAULT, result["status"])
        self.assertEqual([], result["candidates"])

    def test_single_missing_device_becomes_single_device_candidate(self) -> None:
        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "FALCON 9",
                    "existence": "ABSENT",
                    "operability": "FAILED",
                    "confidence": "HIGH",
                    "state": "missing",
                    "passive": "presence=none",
                    "notesText": "Runtime snapshot did not observe device.",
                },
                {
                    "label": "SPARKMAX/NEO 25",
                    "existence": "PRESENT",
                    "operability": "OK",
                    "confidence": "HIGH",
                    "state": "ok",
                },
            ],
            now_s=10.0,
        )

        self.assertEqual(FAULT_CLASS_SINGLE_DEVICE, result["candidates"][0]["faultClass"])
        self.assertEqual(CATEGORY_DEVICE_LOCAL, result["candidates"][0]["candidateCategory"])
        self.assertEqual(["FALCON 9"], result["candidates"][0]["affectedDevices"])
        self.assertEqual(["FALCON 9"], result["candidates"][0]["missingDevices"])
        self.assertEqual(["FALCON 9"], result["primarySuspectRegions"])
        self.assertIn("trace", result)
        self.assertIn("candidateTrace", result["trace"])

    def test_multiple_connected_affected_devices_become_branch_candidate(self) -> None:
        topology = {
            "nodes": [
                {"key": 1, "objectType": "device", "deviceRef": "FALCON 9"},
                {"key": 2, "objectType": "device", "deviceRef": "SPARKMAX/NEO 25"},
                {"key": 3, "objectType": "device", "deviceRef": "pdp"},
            ],
            "edges": [
                {"edgeType": "can_trunk", "fromNode": 1, "toNode": 2},
                {"edgeType": "can_trunk", "fromNode": 2, "toNode": 3},
            ],
        }

        result = build_fault_diagnosis(
            evidence_rows=[
                {"label": "FALCON 9", "existence": "ABSENT", "operability": "FAILED", "state": "missing"},
                {"label": "SPARKMAX/NEO 25", "existence": "ABSENT", "operability": "FAILED", "state": "missing"},
                {"label": "pdp", "existence": "PRESENT", "operability": "UNKNOWN", "state": "degraded"},
            ],
            topology_profile=topology,
            now_s=10.0,
        )

        self.assertEqual(FAULT_CLASS_BRANCH, result["candidates"][0]["faultClass"])
        self.assertEqual(CATEGORY_BUS_PATH, result["candidates"][0]["candidateCategory"])
        self.assertEqual(
            ["FALCON 9", "SPARKMAX/NEO 25"],
            result["candidates"][0]["affectedDevices"],
        )
        self.assertEqual(
            ["FALCON 9", "SPARKMAX/NEO 25"],
            result["candidates"][0]["missingDevices"],
        )

    def test_strong_current_positive_motor_evidence_suppresses_stale_branch_candidate(self) -> None:
        topology = {
            "nodes": [
                {"key": 1, "objectType": "device", "deviceRef": "FALCON 9"},
                {"key": 2, "objectType": "device", "deviceRef": "SPARKMAX/NEO 25"},
            ],
            "edges": [
                {"edgeType": "can_trunk", "fromNode": 1, "toNode": 2},
            ],
        }

        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "FALCON 9",
                    "existence": "CONFLICT",
                    "operability": "OK",
                    "confidence": "HIGH",
                    "state": "degraded",
                    "manual": "Rotation detected",
                    "manualText": "autoResult=Rotation detected\nmotionCheck=pass",
                    "sourceScores": {
                        "runtime": {"score": 90, "state": "present", "reason": "Runtime presence snapshot present."},
                        "probe": {"score": 95, "state": "present", "reason": "Fresh Full Probe present."},
                        "manual": {"score": 60, "state": "present", "reason": "Manual evidence recorded."},
                        "passive": {"score": 85, "state": "present", "reason": "Passive CAN visibility."},
                        "console": {"score": 50, "state": "unknown", "reason": "No console warn/error evidence."},
                    },
                },
                {
                    "label": "SPARKMAX/NEO 25",
                    "existence": "ABSENT",
                    "operability": "UNKNOWN",
                    "confidence": "MEDIUM",
                    "state": "missing",
                    "manual": "Rotation detected",
                    "manualText": "autoResult=Rotation detected\nmotionCheck=pass",
                    "sourceScores": {
                        "runtime": {"score": 90, "state": "present", "reason": "Runtime presence snapshot present."},
                        "probe": {"score": 95, "state": "present", "reason": "Fresh Full Probe present."},
                        "manual": {"score": 60, "state": "present", "reason": "Manual evidence recorded."},
                        "passive": {"score": 85, "state": "present", "reason": "Passive CAN visibility."},
                        "console": {"score": 50, "state": "unknown", "reason": "No console warn/error evidence."},
                    },
                },
            ],
            topology_profile=topology,
            now_s=10.0,
        )

        self.assertEqual(STATUS_NO_FAULT, result["status"])
        self.assertEqual([], result["candidates"])

    def test_passive_observer_presence_prevents_scope_absence_from_becoming_fault(self) -> None:
        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "pdp",
                    "existence": "ABSENT",
                    "operability": "UNKNOWN",
                    "confidence": "MEDIUM",
                    "state": "missing",
                    "passive": "source=passive_discovery_poc | presence=medium | score=78/100 | packets=4306",
                    "notesText": "Runtime snapshot did not observe device present.",
                },
                {
                    "label": "roborio",
                    "existence": "ABSENT",
                    "operability": "UNKNOWN",
                    "confidence": "LOW",
                    "state": "missing",
                    "passive": "observer=CANable | lastSeen=0.0s | packets=18011",
                    "notesText": "Runtime snapshot did not observe device present.",
                },
            ],
            now_s=10.0,
        )

        self.assertEqual(STATUS_NO_FAULT, result["status"])
        self.assertEqual([], result["candidates"])
        infrastructure = result["observation"]["infrastructure"]
        self.assertEqual(["pdp", "roborio"], infrastructure["visible"])
        self.assertEqual([], infrastructure["conflict"])
        self.assertEqual([], infrastructure["stale"])

    def test_explicit_failed_operability_still_becomes_fault_with_passive_presence(self) -> None:
        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "FALCON 9",
                    "existence": "PRESENT",
                    "operability": "FAILED",
                    "confidence": "HIGH",
                    "state": "degraded",
                    "passive": "presence=medium | score=78/100",
                    "manual": "result=No rotation detected",
                }
            ],
            now_s=10.0,
        )

        self.assertEqual(FAULT_CLASS_SINGLE_DEVICE, result["candidates"][0]["faultClass"])
        self.assertEqual(["FALCON 9"], result["candidates"][0]["affectedDevices"])

    def test_console_driven_conflicted_presence_still_becomes_fault_candidate(self) -> None:
        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "FALCON 9",
                    "existence": "CONFLICT",
                    "operability": "FAILED",
                    "confidence": "MEDIUM",
                    "state": "failed",
                    "conflicted": True,
                    "presenceState": "conflict",
                    "console": "[WARN] TALON_STATUS_SIGNAL_STALE",
                    "notesText": "Device-targeted stale/timeout console evidence present.",
                }
            ],
            now_s=10.0,
        )

        self.assertEqual(FAULT_CLASS_SINGLE_DEVICE, result["candidates"][0]["faultClass"])
        self.assertEqual(["FALCON 9"], result["candidates"][0]["affectedDevices"])

    def test_empty_evidence_returns_insufficient_candidate(self) -> None:
        result = build_fault_diagnosis(evidence_rows=[], now_s=10.0)

        self.assertEqual(FAULT_CLASS_INSUFFICIENT, result["candidates"][0]["faultClass"])

    def test_render_includes_next_check(self) -> None:
        result = build_fault_diagnosis(
            evidence_rows=[
                {"label": "FALCON 9", "existence": "ABSENT", "operability": "FAILED", "state": "missing"}
            ],
            now_s=10.0,
        )

        text = render_fault_diagnosis(result)

        self.assertIn("infrastructure:", text)
        self.assertIn("single_device_unreachable", text)
        self.assertIn("category=device_local_fault", text)
        self.assertIn("missing=FALCON 9", text)
        self.assertIn("Inspect power and CAN connectors at FALCON 9 first.", text)

    def test_missing_infrastructure_device_becomes_candidate(self) -> None:
        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "pdp",
                    "deviceType": "infrastructure_device",
                    "existence": "ABSENT",
                    "operability": "UNKNOWN",
                    "confidence": "MEDIUM",
                    "state": "missing",
                    "presenceState": "missing",
                    "presenceScore": 0,
                    "sourceScores": {
                        "runtime": {"score": 0, "state": "missing", "reason": "Runtime presence snapshot absent."}
                    },
                }
            ],
            now_s=10.0,
        )

        self.assertEqual("ok", result["status"])
        self.assertEqual("single_device_unreachable", result["candidates"][0]["faultClass"])
        self.assertEqual(["pdp"], result["candidates"][0]["affectedDevices"])

    def test_chain_break_identifies_downstream_missing_devices_and_boundary(self) -> None:
        topology = {
            "nodes": [
                {"key": 1, "objectType": "device", "deviceRef": "roborio"},
                {"key": 2, "objectType": "device", "deviceRef": "FALCON 9"},
                {"key": 3, "objectType": "device", "deviceRef": "SPARKMAX/NEO 25"},
                {"key": 4, "objectType": "device", "deviceRef": "CANCODER 26"},
            ],
            "edges": [
                {"edgeType": "can_trunk", "fromNode": 1, "toNode": 2},
                {"edgeType": "can_trunk", "fromNode": 2, "toNode": 3},
                {"edgeType": "can_trunk", "fromNode": 3, "toNode": 4},
            ],
        }

        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "roborio",
                    "existence": "PRESENT",
                    "operability": "OK",
                    "confidence": "HIGH",
                    "state": "ok",
                    "console": "[INFO] runtime healthy",
                },
                {
                    "label": "FALCON 9",
                    "existence": "PRESENT",
                    "operability": "OK",
                    "confidence": "HIGH",
                    "state": "ok",
                    "console": "[INFO] motor healthy",
                },
                {
                    "label": "SPARKMAX/NEO 25",
                    "existence": "ABSENT",
                    "operability": "FAILED",
                    "confidence": "HIGH",
                    "state": "missing",
                    "console": "[WARN] SPARK_STATUS_TIMEOUT",
                },
                {
                    "label": "CANCODER 26",
                    "existence": "ABSENT",
                    "operability": "FAILED",
                    "confidence": "HIGH",
                    "state": "missing",
                    "console": "[WARN] CANCODER timeout",
                },
            ],
            topology_profile=topology,
            now_s=10.0,
        )

        self.assertEqual(FAULT_CLASS_BRANCH, result["candidates"][0]["faultClass"])
        self.assertEqual(CATEGORY_BUS_PATH, result["candidates"][0]["candidateCategory"])
        self.assertEqual(
            ["SPARKMAX/NEO 25", "CANCODER 26"],
            result["candidates"][0]["missingDevices"],
        )
        self.assertEqual(
            ["SPARKMAX/NEO 25", "CANCODER 26"],
            result["missingDevices"],
        )
        self.assertIn(
            "between FALCON 9 and SPARKMAX/NEO 25",
            result["candidates"][0]["primarySuspectRegions"],
        )
        self.assertIn("boundaryPairs", result["trace"]["topology"])
        self.assertIn(
            "between FALCON 9 and SPARKMAX/NEO 25",
            result["trace"]["topology"]["boundaryPairs"],
        )

    def test_controller_side_break_prefers_roborio_boundary_candidate(self) -> None:
        topology = {
            "nodes": [
                {"key": 1, "objectType": "device", "deviceRef": "roborio"},
                {"key": 2, "objectType": "device", "deviceRef": "SPARKMAX/NEO 25"},
                {"key": 3, "objectType": "device", "deviceRef": "FALCON 9"},
                {"key": 4, "objectType": "device", "deviceRef": "pdp"},
            ],
            "edges": [
                {"edgeType": "can_tap", "fromNode": 1, "toNode": 2},
                {"edgeType": "can_trunk", "fromNode": 2, "toNode": 3},
                {"edgeType": "can_trunk", "fromNode": 3, "toNode": 4},
            ],
        }

        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "roborio",
                    "existence": "PRESENT",
                    "operability": "OK",
                    "confidence": "HIGH",
                    "state": "ok",
                },
                {
                    "label": "SPARKMAX/NEO 25",
                    "existence": "ABSENT",
                    "operability": "FAILED",
                    "confidence": "HIGH",
                    "state": "missing",
                },
                {
                    "label": "FALCON 9",
                    "existence": "ABSENT",
                    "operability": "FAILED",
                    "confidence": "HIGH",
                    "state": "missing",
                },
                {
                    "label": "pdp",
                    "existence": "ABSENT",
                    "operability": "FAILED",
                    "confidence": "HIGH",
                    "state": "missing",
                },
            ],
            topology_profile=topology,
            now_s=10.0,
        )

        self.assertEqual(FAULT_CLASS_CONTROLLER_SIDE, result["candidates"][0]["faultClass"])
        self.assertEqual(CATEGORY_BUS_PATH, result["candidates"][0]["candidateCategory"])
        self.assertEqual(
            "between roborio and SPARKMAX/NEO 25",
            result["candidates"][0]["primarySuspectRegions"][0],
        )

    def test_bus_wide_candidate_does_not_mark_visible_infrastructure_as_missing(self) -> None:
        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "pdp",
                    "existence": "PRESENT",
                    "operability": "UNKNOWN",
                    "confidence": "LOW",
                    "state": "degraded",
                    "passive": "presence=medium | score=78/100 | packets=4306",
                },
                {
                    "label": "roborio",
                    "existence": "PRESENT",
                    "operability": "UNKNOWN",
                    "confidence": "LOW",
                    "state": "degraded",
                    "passive": "presence=medium | score=82/100 | packets=6201",
                },
            ],
            console_snapshot={
                "systemConflict": True,
                "systemText": "Multiple system CAN warnings observed.",
            },
            now_s=10.0,
        )

        self.assertEqual("bus_wide_error_pressure", result["candidates"][0]["faultClass"])
        self.assertEqual([], result["candidates"][0]["affectedDevices"])
        self.assertEqual([], result["candidates"][0]["missingDevices"])
        text = render_fault_diagnosis(result)
        self.assertIn("affected=none", text)
        self.assertIn("missing=none", text)
        self.assertIn("why:", text)

    def test_infrastructure_only_degradation_with_healthy_motion_does_not_raise_bus_fault(self) -> None:
        result = build_fault_diagnosis(
            evidence_rows=[
                {
                    "label": "FALCON 9",
                    "existence": "PRESENT",
                    "operability": "OK",
                    "confidence": "HIGH",
                    "state": "ok",
                },
                {
                    "label": "SPARKMAX/NEO 25",
                    "existence": "PRESENT",
                    "operability": "OK",
                    "confidence": "HIGH",
                    "state": "ok",
                },
                {
                    "label": "pdp",
                    "existence": "PRESENT",
                    "operability": "DEGRADED",
                    "confidence": "MEDIUM",
                    "state": "degraded",
                },
                {
                    "label": "roborio",
                    "existence": "PRESENT",
                    "operability": "DEGRADED",
                    "confidence": "MEDIUM",
                    "state": "degraded",
                },
            ],
            now_s=10.0,
        )

        self.assertEqual(STATUS_NO_FAULT, result["status"])
        self.assertEqual([], result["candidates"])
        self.assertEqual(
            ["FALCON 9", "SPARKMAX/NEO 25"],
            result["observation"]["healthyMotionDevices"],
        )


if __name__ == "__main__":
    unittest.main()
