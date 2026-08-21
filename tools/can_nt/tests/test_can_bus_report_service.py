from __future__ import annotations

import unittest

from tools.can_nt.can_bus_report_service import build_host_can_bus_report


class _FakeSession:
    def __init__(self, runtime_state):
        self._runtime_state = dict(runtime_state)

    def fetch_runtime_state(self):
        return dict(self._runtime_state)


class _FakeVisibilityProvider:
    def snapshot(self, _scope: str, _now_ms: int):
        return {
            "sources": [
                {"id": "src0", "label": "can analyzer 1", "available": True},
            ],
            "devices": [
                {
                    "label": "FALCON 9",
                    "identityKey": "4:2:9",
                    "unexpected": False,
                    "metrics": {
                        "lastSeenMs": 99000,
                        "msgCount": 1200,
                        "framesPerSec": 50.0,
                    },
                    "rawIds": [{"arbId": 1}],
                },
                {
                    "label": "UNPROFILED_DEVICE_5",
                    "identityKey": "4:8:5",
                    "unexpected": True,
                    "metrics": {
                        "lastSeenMs": 98500,
                        "msgCount": 75,
                        "framesPerSec": 3.0,
                    },
                    "rawIds": [],
                },
            ],
        }

    def summary(self, _scope: str, _now_ms: int):
        return {
            "devicesShown": 2,
            "visibleAll": 1,
            "visibleSome": 0,
            "visibleNone": 1,
        }


class CanBusReportServiceTests(unittest.TestCase):
    def test_build_host_can_bus_report_combines_visibility_bus_and_runtime_devices(self) -> None:
        runtime_state = {
            "canBus": {
                "valid": True,
                "utilizationPct": 12.5,
                "rxErrors": 0,
                "txErrors": 1,
                "rxDelta": 0,
                "txDelta": 1,
                "txFull": 0,
                "txFullDelta": 0,
                "busOff": 0,
                "busOffDelta": 0,
                "sampleAgeSec": 0.03,
            },
            "devices": [
                {
                    "label": "FALCON 9",
                    "vendor": "CTRE",
                    "type": "FALCON",
                    "id": 9,
                    "instantiated": True,
                    "lifecycleState": "controlled-active",
                    "testable": True,
                    "presenceConfidence": 1.0,
                    "velRpm": 0.0,
                    "positionRot": 0.5,
                    "attachments": [
                        {
                            "type": "ctreMotor",
                            "cmdDuty": 0.3,
                            "appliedDuty": 0.3,
                            "appliedV": 3.6,
                            "busV": 12.0,
                            "motorCurrentA": 5.4,
                            "tempC": 31.0,
                        },
                        {
                            "type": "motorSpec",
                            "matched": False,
                            "requestedModel": "Unknown Motor",
                        },
                    ],
                }
            ],
        }
        report = build_host_can_bus_report(
            _FakeSession(runtime_state),
            _FakeVisibilityProvider(),
            now=100.0,
        )
        self.assertIn("=== CAN Bus Report (Host Assembled) ===", report)
        self.assertIn("Host Visibility:", report)
        self.assertIn("Defined Nodes:", report)
        self.assertIn("Unrecognized Nodes:", report)
        self.assertIn("Robot CAN Bus Health:", report)
        self.assertIn("utilization=12.5%", report)
        self.assertIn("FALCON 9 identity=4:2:9", report)
        self.assertIn("UNPROFILED_DEVICE_5 identity=4:8:5", report)
        self.assertIn("Robot Runtime Devices:", report)
        self.assertIn("vendor=CTRE type=FALCON id=9", report)
        self.assertIn("cmdDuty=0.30", report)
        self.assertIn("motorSpec: matched=NO requestedModel=Unknown Motor", report)

    def test_build_host_can_bus_report_handles_missing_bus_and_provider(self) -> None:
        report = build_host_can_bus_report(_FakeSession({"devices": []}), None, now=100.0)
        self.assertIn("Host Visibility:", report)
        self.assertIn("Status: unavailable", report)
        self.assertIn("Robot CAN Bus Health:", report)
        self.assertIn("Robot Runtime Devices:", report)
