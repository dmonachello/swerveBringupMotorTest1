from __future__ import annotations

import types
import unittest
from unittest.mock import patch

from tools.passive_discovery_poc.live_sources import capture_live_rev_serial, capture_live_slcan, resolve_rev_serial_port


class _FakeCanMessage:
    def __init__(self, timestamp, arbitration_id, data, is_extended_id=True, is_remote_frame=False):
        self.timestamp = timestamp
        self.arbitration_id = arbitration_id
        self.data = data
        self.is_extended_id = is_extended_id
        self.is_remote_frame = is_remote_frame


class _FakeBus:
    def __init__(self, messages):
        self._messages = list(messages)
        self._index = 0

    def recv(self, timeout=None):
        _ = timeout
        if self._index >= len(self._messages):
            return None
        value = self._messages[self._index]
        self._index += 1
        return value

    def shutdown(self):
        return None


class _FakeSerialHandle:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self._index = 0

    def read(self, size):
        _ = size
        if self._index >= len(self._chunks):
            return b""
        value = self._chunks[self._index]
        self._index += 1
        return value

    def close(self):
        return None


class _FakePortInfo:
    def __init__(self, device, description="", manufacturer="", product="", interface="", hwid=""):
        self.device = device
        self.description = description
        self.manufacturer = manufacturer
        self.product = product
        self.interface = interface
        self.hwid = hwid


class PassiveDiscoveryLiveSourceTests(unittest.TestCase):
    """
    NAME
        PassiveDiscoveryLiveSourceTests - Validate live acquisition adapters with fakes.
    """

    def test_capture_live_slcan_normalizes_messages(self) -> None:
        fake_can = types.SimpleNamespace(
            Bus=lambda interface, channel, bitrate: _FakeBus(
                [
                    _FakeCanMessage(1.0, int("0205B819", 16), bytes.fromhex("00008E0600188000")),
                    _FakeCanMessage(1.1, int("02042C49", 16), bytes.fromhex("0000006000000000")),
                ]
            )
        )
        with patch.dict("sys.modules", {"can": fake_can}):
            frames = capture_live_slcan(channel="COM3", bitrate=1000000, duration_sec=0.01)

        self.assertEqual(2, len(frames))
        self.assertEqual(5, frames[0].manufacturer)
        self.assertEqual(4, frames[1].manufacturer)

    def test_capture_live_rev_serial_reassembles_ascii_frames(self) -> None:
        fake_serial_module = types.SimpleNamespace(
            Serial=lambda port, baudrate, timeout: _FakeSerialHandle(
                [
                    b"T0205B819800008E0",
                    b"600188000\rT02042C4980000006000000000\r",
                ]
            )
        )
        with patch.dict("sys.modules", {"serial": fake_serial_module}):
            frames = capture_live_rev_serial(port="COM7", baudrate=115200, duration_sec=0.01)

        self.assertEqual(2, len(frames))
        self.assertEqual(5, frames[0].manufacturer)
        self.assertEqual(4, frames[1].manufacturer)

    def test_resolve_rev_serial_port_auto_detects_single_usb_serial_device(self) -> None:
        fake_serial_module = types.SimpleNamespace(
            tools=types.SimpleNamespace(
                list_ports=types.SimpleNamespace(
                    comports=lambda: [
                        _FakePortInfo(
                            device="COM5",
                            description="USB Serial Device",
                            manufacturer="STMicroelectronics",
                            product="USB Serial Device",
                            interface="Spark MAX",
                            hwid="USB\\VID_0483&PID_A30E\\206933694E55",
                        )
                    ]
                )
            )
        )
        with patch.dict("sys.modules", {"serial": fake_serial_module, "serial.tools": fake_serial_module.tools, "serial.tools.list_ports": fake_serial_module.tools.list_ports}):
            resolved = resolve_rev_serial_port(explicit_port="auto", auto_match="REV")

        self.assertEqual("COM5", resolved)

    def test_resolve_rev_serial_port_rejects_single_unmatched_serial_device(self) -> None:
        fake_serial_module = types.SimpleNamespace(
            tools=types.SimpleNamespace(
                list_ports=types.SimpleNamespace(
                    comports=lambda: [
                        _FakePortInfo(
                            device="COM3",
                            description="CANable 2.0",
                            manufacturer="CANable",
                            product="CANable",
                            interface="slcan",
                            hwid="USB\\VID_AD50&PID_60C4\\1234",
                        )
                    ]
                )
            )
        )
        with patch.dict(
            "sys.modules",
            {
                "serial": fake_serial_module,
                "serial.tools": fake_serial_module.tools,
                "serial.tools.list_ports": fake_serial_module.tools.list_ports,
            },
        ):
            with self.assertRaises(RuntimeError) as raised:
                resolve_rev_serial_port(explicit_port="auto", auto_match="REV")

        self.assertIn("Could not uniquely auto-detect a REV serial source", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
