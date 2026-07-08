from __future__ import annotations

import unittest

from tools.vendor_diag.rev_usb_to_candump import (
    CAN_ID_HEX_LEN_EXT,
    CAN_ID_HEX_LEN_STD,
    RECORD_PREFIX_EXT,
    RECORD_PREFIX_EXT_RTR,
    RECORD_PREFIX_STD,
    USB_DIRECTION_IN,
    iter_can_frames,
    parse_ascii_can_record,
    UsbPayloadRecord,
)


class RevUsbToCandumpTests(unittest.TestCase):
    def test_parse_extended_data_record(self) -> None:
        line = "T0205B819800008E0600188000"

        record = parse_ascii_can_record(line=line, timestamp_s=1.25)

        self.assertIsNotNone(record)
        assert record is not None
        self.assertTrue(record.is_extended)
        self.assertFalse(record.is_rtr)
        self.assertEqual(record.arb_id, int("0205B819", 16))
        self.assertEqual(record.data, bytes.fromhex("00008E0600188000"))

    def test_parse_standard_data_record(self) -> None:
        line = "t1232A1B2"

        record = parse_ascii_can_record(line=line, timestamp_s=2.0)

        self.assertIsNotNone(record)
        assert record is not None
        self.assertFalse(record.is_extended)
        self.assertFalse(record.is_rtr)
        self.assertEqual(record.arb_id, int("123", 16))
        self.assertEqual(record.data, bytes.fromhex("A1B2"))

    def test_parse_extended_remote_record(self) -> None:
        line = "R0205B8190"

        record = parse_ascii_can_record(line=line, timestamp_s=3.0)

        self.assertIsNotNone(record)
        assert record is not None
        self.assertTrue(record.is_extended)
        self.assertTrue(record.is_rtr)
        self.assertEqual(record.data, b"")

    def test_parse_rejects_non_frame_line(self) -> None:
        self.assertIsNone(parse_ascii_can_record(line="garbage", timestamp_s=0.0))

    def test_iter_can_frames_reassembles_split_lines(self) -> None:
        payloads = [
            UsbPayloadRecord(
                timestamp_s=1.0,
                device_address=50,
                direction=USB_DIRECTION_IN,
                ascii_text="T0205B819800008E0",
            ),
            UsbPayloadRecord(
                timestamp_s=1.1,
                device_address=50,
                direction=USB_DIRECTION_IN,
                ascii_text="600188000\r\nT02052C80100\r\n",
            ),
        ]

        frames = list(iter_can_frames(payloads))

        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0].arb_id, int("0205B819", 16))
        self.assertEqual(frames[0].data, bytes.fromhex("00008E0600188000"))
        self.assertEqual(frames[1].arb_id, int("02052C80", 16))
        self.assertEqual(frames[1].data, bytes.fromhex("00"))


if __name__ == "__main__":
    unittest.main()
