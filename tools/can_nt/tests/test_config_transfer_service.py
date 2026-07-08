"""
NAME
    test_config_transfer_service.py - Regression tests for shared config push workflows.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.can_nt.bridge_session import BridgeEvent
from tools.can_nt.config_transfer_service import push_config
from tools.common.profile_constants import (
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DEVICES,
    KEY_ID,
    KEY_LABEL,
    KEY_MANUFACTURER,
    KEY_NAME,
    KEY_PROFILES,
    KEY_TYPE,
    PROFILE_SCHEMA_VERSION,
)
from tools.common.profile_io import compute_profiles_hash
from tools.common.tests.config_api_test_helper import write_profiles_payload


class _Plan:
    def __init__(self, ok: bool = True, message: str = "", commands=None) -> None:
        self.ok = ok
        self.message = message
        self.commands = list(commands or [])


class _Command:
    def __init__(self, name: str, args: dict) -> None:
        self.name = name
        self.args = args


class _FakeSession:
    def __init__(self, out_events: list[BridgeEvent]) -> None:
        self._out_events = list(out_events)
        self.sent: list[tuple[str, dict]] = []
        self._seq = 1

    def send_command(self, name: str, args: dict | None = None) -> int:
        self.sent.append((name, dict(args or {})))
        seq = self._seq
        self._seq += 1
        return seq

    def poll_events(self):
        if not self._out_events:
            return []
        event = self._out_events.pop(0)
        return [
            BridgeEvent(
                type=event.type,
                seq=len(self.sent),
                name=event.name,
                status=event.status,
                message=event.message,
                text=event.text,
                json_text=event.json_text,
                ts=event.ts,
                session_id=event.session_id,
                state=event.state,
                raw=event.raw,
            )
        ]


def _out_event(status: str = "ok", message: str = "", json_text: str = "") -> BridgeEvent:
    return BridgeEvent(
        type="out",
        seq=0,
        name="cmd",
        status=status,
        message=message,
        text="",
        json_text=json_text,
        ts=0.0,
        session_id="",
        state={},
        raw={},
    )


def _valid_payload() -> dict:
    payload = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        KEY_DATA_VERSION: "test-version",
        KEY_DATA_HASH: "",
        KEY_DEVICES: [
            {
                KEY_LABEL: "FALCON 9",
                KEY_MANUFACTURER: 1,
                KEY_TYPE: "FALCON",
                KEY_ID: 9,
            }
        ],
        KEY_PROFILES: {
            "test_minimal_25_9": {
                KEY_NAME: "test_minimal_25_9",
                KEY_DEVICES: ["FALCON 9"],
            }
        },
    }
    payload[KEY_DATA_HASH] = compute_profiles_hash(payload)
    return payload


class ConfigTransferServiceTests(unittest.TestCase):
    def test_push_config_emits_staged_status_and_returns_apply_payload(self) -> None:
        payload = _valid_payload()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bringup_system.json"
            write_profiles_payload(path, payload, stamp=False)
            apply_json = json.dumps(
                {
                    "message": "Config pushed to robot.",
                    "transferCheck": {"ok": True, "message": "transfer ok"},
                    "contentValidation": {"ok": True, "message": "content ok"},
                    "apply": {"ok": True, "message": "apply ok"},
                    "postApplyCheck": {"ok": True, "message": "post ok"},
                }
            )
            session = _FakeSession(
                [
                    _out_event(json_text=apply_json),
                    _out_event(message="Selected profile"),
                    _out_event(message="group import"),
                ]
            )
            progress: list[str] = []

            from tools.can_nt import config_transfer_service as service

            original_fetch_groups = service.fetch_groups_payload
            service.fetch_groups_payload = lambda *_args, **_kwargs: {"groups": []}
            try:
                result = push_config(
                    session,
                    str(path),
                    "test_minimal_25_9",
                    "error",
                    plan_loader=lambda *_args: _Plan(commands=[_Command("groupImport", {"name": "g"})]),
                    status_callback=progress.append,
                )
            finally:
                service.fetch_groups_payload = original_fetch_groups

        self.assertTrue(result.ok())
        self.assertEqual(
            [
                "Push Config: load local config",
                "Push Config: validate local config",
                "Push Config: upload registry",
                "Push Config: select profile",
                "Push Config: clear robot groups",
                "Push Config: import groups and bindings",
                "Push Config: complete",
            ],
            progress,
        )
        self.assertIsInstance(result.payload, dict)
        self.assertEqual("Config pushed to robot.", result.message)
        self.assertEqual("Config pushed to robot.", result.payload["apply"]["message"])


if __name__ == "__main__":
    unittest.main()
