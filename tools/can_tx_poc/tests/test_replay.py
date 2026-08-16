from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from tools.can_tx_poc import replay


class _CanModuleStub:
    bus_open_count = 0

    @classmethod
    def Bus(cls, **_kwargs):
        cls.bus_open_count += 1
        raise AssertionError("bus must not open without authorization")


class CanReplayPocTests(unittest.TestCase):
    """Verify the PoC authorization boundary and sequence parsing."""

    def test_run_refuses_to_open_bus_without_explicit_authorization(self) -> None:
        args = argparse.Namespace(
            tx_allow=False,
            sequence="unused.txt",
            interface="slcan",
            channel="COM3",
            bitrate=1_000_000,
            scale=1.0,
            loop=False,
            verbose=False,
        )
        _CanModuleStub.bus_open_count = 0

        result = replay.run(args, can_module=_CanModuleStub)

        self.assertEqual(replay.EXIT_ERROR, result)
        self.assertEqual(0, _CanModuleStub.bus_open_count)

    def test_parse_sequence_accepts_tab_and_csv_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sequence_path = Path(temp_dir) / "frames.txt"
            sequence_path.write_text(
                "0.0\t0x101\t2\tAABB\n0.1,0x102,CCDD\n",
                encoding="utf-8",
            )

            frames = replay.parse_sequence(str(sequence_path))

        self.assertEqual(
            [(0.0, 0x101, bytes.fromhex("AABB")), (0.1, 0x102, bytes.fromhex("CCDD"))],
            frames,
        )


if __name__ == "__main__":
    unittest.main()
