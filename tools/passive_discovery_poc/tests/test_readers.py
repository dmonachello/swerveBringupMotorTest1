from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.passive_discovery_poc.capture import read_candump, read_pcapng


FIXTURE_USB_CAP_8 = Path("tools/vendor_diag/usbCap8_socketcan.pcapng")
TEXT_CANDUMP_SAMPLE = "(1.000000) slcan0 0205B819#00008E0600188000 R"


class PassiveDiscoveryReaderTests(unittest.TestCase):
    """
    NAME
        PassiveDiscoveryReaderTests - Validate offline frame ingestion.
    """

    def test_read_socketcan_fixture_yields_frames(self) -> None:
        frames = read_pcapng(str(FIXTURE_USB_CAP_8))

        self.assertGreater(len(frames), 100)
        self.assertTrue(any(frame.manufacturer == 5 for frame in frames))
        self.assertTrue(any(frame.manufacturer == 4 for frame in frames))

    def test_read_candump_text_yields_normalized_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.log"
            path.write_text(TEXT_CANDUMP_SAMPLE + "\n", encoding="utf-8")

            frames = read_candump(str(path))

        self.assertEqual(1, len(frames))
        frame = frames[0]
        self.assertEqual(5, frame.manufacturer)
        self.assertEqual(2, frame.device_type)
        self.assertEqual(25, frame.device_id)
        self.assertEqual("00008e0600188000", frame.data_hex)


if __name__ == "__main__":
    unittest.main()
