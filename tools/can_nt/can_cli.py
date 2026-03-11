from __future__ import annotations

"""
NAME
    can_cli.py - CLI definition for the CAN bringup diagnostics tool.

SYNOPSIS
    from tools.can_nt.can_cli import build_parser

DESCRIPTION
    Defines the argument parser for the Python CAN sniffer/bridge. Keeps
    options centralized so other modules can import consistent defaults.
"""

import argparse
from pathlib import Path

from .can_profiles import get_default_profile


def build_parser() -> argparse.ArgumentParser:
    """
    NAME
        build_parser - Construct the argparse parser for the tool.

    SYNOPSIS
        parser = build_parser()

    DESCRIPTION
        Returns a fully configured ArgumentParser with all CLI flags used by
        the CAN diagnostics runner.

    RETURNS
        argparse.ArgumentParser instance with bringup options.
    """
    parser = argparse.ArgumentParser(description="FRC CAN bringup diagnostics")

    parser.add_argument("--profile", default=get_default_profile())

    parser.add_argument("--interface", default="slcan")
    parser.add_argument(
        "--channel",
        default="",
        help="CAN channel (for slcan, the COM port like COM3). "
        "If omitted, attempts auto-detect by description.",
    )
    parser.add_argument("--bitrate", type=int, default=1_000_000)
    parser.add_argument(
        "--auto-match",
        default="USB Serial Device",
        help="Substring to match when auto-detecting serial ports",
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Disable port selection prompt when multiple matches are found",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List available serial ports and exit",
    )

    parser.add_argument("--rio", default="172.22.11.2")
    parser.add_argument(
        "--no-nt",
        action="store_true",
        help="Disable NetworkTables publishing (capture/logging only).",
    )

    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--publish-period", type=float, default=0.2)

    parser.add_argument("--publish-can-summary", action="store_true")
    parser.add_argument(
        "--print-summary-period",
        type=float,
        default=0.0,
        help="Print CAN summary to console every N seconds (0 disables).",
    )
    parser.add_argument(
        "--console-monitor",
        action="store_true",
        help="Enable roboRIO NetConsole monitoring and NT publish.",
    )
    parser.add_argument(
        "--console-transport",
        default="tcp",
        choices=["tcp", "udp"],
        help="NetConsole transport to use (default: tcp).",
    )
    parser.add_argument(
        "--console-port",
        type=int,
        default=1740,
        help="NetConsole port (default: 1740 for tcp, 6666 for udp).",
    )
    parser.add_argument(
        "--console-host",
        default="",
        help="Override NetConsole host (default: --rio).",
    )
    parser.add_argument(
        "--console-rules",
        default=str(Path(__file__).with_name("console_rules.json")),
        help="Path to console_rules.json for NetConsole regex matching.",
    )
    parser.add_argument(
        "--console-timeout",
        type=float,
        default=10.0,
        help="Seconds of inactivity before console entries go inactive.",
    )
    parser.add_argument(
        "--console-rate",
        type=float,
        default=2.0,
        help="Console NT publish rate (Hz).",
    )
    parser.add_argument(
        "--console-debug-log",
        default="",
        help="Optional path to log raw NetConsole lines (rotating file).",
    )
    parser.add_argument(
        "--console-reset-on-start",
        action="store_true",
        help="Clear console counters and entries on startup.",
    )
    parser.add_argument(
        "--console-log-max-mb",
        type=int,
        default=5,
        help="Max size (MB) per console debug log file.",
    )
    parser.add_argument(
        "--console-log-max-files",
        type=int,
        default=5,
        help="Max number of rotated console debug log files.",
    )
    parser.add_argument(
        "--startup-summary-after",
        type=float,
        default=0.0,
        help=(
            "Print a one-time startup confirmation and summary after N seconds "
            "(0 disables)."
        ),
    )
    parser.add_argument(
        "--print-publish",
        action="store_true",
        help="Print when a device transitions from missing to seen.",
    )
    parser.add_argument("--stale-s", type=float, default=0.75)
    parser.add_argument("--top-n", type=int, default=15)

    parser.add_argument("--dump-can-expected-ids", default="")
    parser.add_argument("--dump-after", type=float, default=3.0)

    parser.add_argument(
        "--list-keys",
        action="store_true",
        help="Print the NetworkTables keys this tool publishes and exit.",
    )
    parser.add_argument(
        "--dump-nt",
        default="",
        help="Write a JSON description of published NetworkTables keys and exit.",
    )
    parser.add_argument(
        "--publish-unknown",
        action="store_true",
        help="Publish devices seen on the bus that are not in the profile as UNKNOWN.",
    )
    parser.add_argument(
        "--dump-profile",
        default="",
        help=(
            "Write a bringup_profiles.json file generated from observed CAN IDs "
            "and exit."
        ),
    )
    parser.add_argument(
        "--dump-profile-name",
        default="",
        help=(
            "Profile name to use when writing --dump-profile output. "
            "If omitted, a timestamped name is generated."
        ),
    )
    parser.add_argument(
        "--dump-profile-after",
        type=float,
        default=3.0,
        help="Seconds to wait before writing --dump-profile output.",
    )
    parser.add_argument(
        "--dump-profile-include-unknown",
        action="store_true",
        help="Include unknown devices in the generated profile output.",
    )
    parser.add_argument(
        "--dump-api-inventory",
        default="",
        help="Write a JSON inventory of CAN devices and frame timing data and exit.",
    )
    parser.add_argument(
        "--dump-api-inventory-after",
        type=float,
        default=3.0,
        help="Seconds to wait before writing --dump-api-inventory output.",
    )
    parser.add_argument(
        "--dump-can-config",
        default="",
        help=(
            "Write a can_nt_config.json-style file from the selected profile and exit."
        ),
    )
    parser.add_argument(
        "--diff-inventory",
        nargs=2,
        metavar=("A.json", "B.json"),
        help="Diff two inventory JSON files and print deltas.",
    )
    parser.add_argument(
        "--diff-top",
        type=int,
        default=10,
        help="Number of rows to show for new/missing/changed pairs.",
    )

    parser.add_argument("--pcap", default="", help="Write all CAN frames to a .pcapng/.pcap file")
    parser.add_argument(
        "--pcap-pipe",
        default="",
        help=(
            "Write live pcapng to a Windows named pipe for Wireshark. "
            "Example: FRC_CAN or \\\\.\\pipe\\FRC_CAN"
        ),
    )
    parser.add_argument(
        "--marker-id",
        type=lambda s: int(s, 0),
        default=0x1FFC0D00,
        help="Arbitration ID for synthetic marker frames (29-bit extended).",
    )
    parser.add_argument(
        "--enable-markers",
        dest="enable_markers",
        action="store_true",
        help="Enable keyboard marker injection (PCAPNG only).",
    )
    parser.add_argument(
        "--disable-markers",
        dest="enable_markers",
        action="store_false",
        help="Disable keyboard marker injection.",
    )
    parser.set_defaults(enable_markers=True)
    parser.add_argument(
        "--capture-note",
        default="",
        help="Append a note to the PCAPNG section header comment.",
    )

    parser.add_argument(
        "--tx-seq",
        default="",
        help="Replay CAN frames from a captured sequence file.",
    )
    parser.add_argument(
        "--tx-allow",
        action="store_true",
        help="Allow --tx-seq transmission (safety interlock).",
    )
    parser.add_argument(
        "--tx-scale",
        type=float,
        default=1.0,
        help="Scale the TX timing (1.0 = realtime).",
    )
    parser.add_argument(
        "--tx-loop",
        action="store_true",
        help="Loop the TX sequence until stopped.",
    )
    parser.add_argument(
        "--tx-verbose",
        action="store_true",
        help="Print TX progress (first few frames and every 100 frames).",
    )
    parser.add_argument(
        "--print-status",
        action="store_true",
        help="Print status frames as they are received.",
    )
    parser.add_argument(
        "--print-control",
        action="store_true",
        help="Print control frames as they are received.",
    )
    parser.add_argument(
        "--print-any",
        action="store_true",
        help="Print all frames (ignores status/control classification).",
    )
    parser.add_argument(
        "--print-can-id",
        type=lambda s: int(s, 0),
        default=-1,
        help="Only print frames matching this arbitration ID (hex or dec).",
    )
    parser.add_argument(
        "--print-device-id",
        type=int,
        default=-1,
        help="Only print frames matching this device ID (low 6 bits of arbitration ID).",
    )
    parser.add_argument(
        "--print-mfg",
        type=int,
        default=-1,
        help="Only print frames matching this manufacturer ID.",
    )
    parser.add_argument(
        "--print-type",
        type=int,
        default=-1,
        help="Only print frames matching this device type.",
    )

    return parser
