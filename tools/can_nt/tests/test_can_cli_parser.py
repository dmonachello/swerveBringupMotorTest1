from __future__ import annotations

import unittest

from tools.can_nt.can_cli import build_parser


class CanCliParserTests(unittest.TestCase):
    """
    NAME
        CanCliParserTests - Validate current supported bridge parser options.
    """

    def test_no_nt_is_accepted_for_compatibility(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["--no-nt"])

        self.assertTrue(args.no_nt)

    def test_list_keys_and_dump_nt_options_are_removed(self) -> None:
        parser = build_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(["--list-keys"])
        with self.assertRaises(SystemExit):
            parser.parse_args(["--dump-nt", "keys.json"])

    def test_live_can_transmit_options_are_not_supported(self) -> None:
        parser = build_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(["--tx-seq", "frames.txt", "--tx-allow"])


if __name__ == "__main__":
    unittest.main()
