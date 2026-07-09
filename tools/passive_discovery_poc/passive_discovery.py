from __future__ import annotations

"""
NAME
    passive_discovery.py - Standalone-first CLI for the passive discovery PoC.

SYNOPSIS
    python tools/passive_discovery_poc/passive_discovery.py --input <capture>

DESCRIPTION
    Runs offline passive CAN analysis, optional bringup-profile comparison, and
    optional CTRE HTTP enrichment. Emits one canonical JSON artifact per run and
    prints a compact device/evidence table for verification.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.passive_discovery_poc.capture import (
    load_expected_rows,
    observe_rev_serial_session,
    observe_slcan_session,
    read_capture,
)
from tools.passive_discovery_poc.constants import (
    APP_DESCRIPTION,
    APP_NAME,
    DEFAULT_AUTO_MATCH,
    DEFAULT_CAN_BITRATE,
    DEFAULT_LIVE_DURATION_SEC,
    DEFAULT_REV_AUTO_MATCH,
    DEFAULT_REV_SERIAL_BAUD,
    DEFAULT_SLCAN_INTERFACE,
    DEFAULT_OUTPUT_SUFFIX,
    EXT_JSON,
)
from tools.passive_discovery_poc.discovery import analyze_frames
from tools.passive_discovery_poc.enrichment import enrich_result_with_ctre, enrich_result_with_topology
from tools.passive_discovery_poc.json_api import write_json_result
from tools.passive_discovery_poc.models import RunResult
from tools.passive_discovery_poc.profile import apply_profile_labels, resolve_label_rows
from tools.passive_discovery_poc.render import render_full_dump_result, render_summary_table


def build_parser() -> argparse.ArgumentParser:
    """
    NAME
        build_parser - Construct the PoC command-line parser.
    """
    parser = argparse.ArgumentParser(prog=APP_NAME, description=APP_DESCRIPTION)
    parser.add_argument("--input", default="", help="Offline capture input (.pcapng or candump/text).")
    parser.add_argument("--live-slcan", action="store_true", help="Capture live passive traffic from a CANable/slcan source.")
    parser.add_argument("--live-rev-serial", nargs="?", const="auto", default="", help="Capture live passive traffic from a REV serial bridge COM port. Use without a value to auto-detect.")
    parser.add_argument("--channel", default="", help="slcan COM port, for example COM3.")
    parser.add_argument("--auto-match", default=DEFAULT_AUTO_MATCH, help="Substring used to auto-detect the CANable serial port.")
    parser.add_argument("--interface", default=DEFAULT_SLCAN_INTERFACE, help="Live CAN interface type. Default is slcan.")
    parser.add_argument("--bitrate", type=int, default=DEFAULT_CAN_BITRATE, help="CAN bitrate for live slcan capture.")
    parser.add_argument("--duration", type=float, default=DEFAULT_LIVE_DURATION_SEC, help="Live capture duration in seconds.")
    parser.add_argument("--rev-baud", type=int, default=DEFAULT_REV_SERIAL_BAUD, help="Baud rate for direct REV serial bridge capture.")
    parser.add_argument("--rev-auto-match", default=DEFAULT_REV_AUTO_MATCH, help="Substring used to auto-detect the REV serial bridge port.")
    parser.add_argument("--profile-path", default="", help="Path to bringup_system.json for expected inventory.")
    parser.add_argument("--profile-name", default="", help="Explicit profile name to use from the bringup profile file.")
    parser.add_argument("--ctre-base-url", default="", help="Optional CTRE diagnostic HTTP base URL, for example http://172.22.11.2:1250")
    parser.add_argument("--output", default="", help="Output JSON artifact path.")
    parser.add_argument("--full-dump", action="store_true", help="Print richer evidence details to stdout.")
    return parser


def main() -> int:
    """
    NAME
        main - CLI entrypoint for the passive discovery PoC.
    """
    args = build_parser().parse_args()
    passive_source_count = _count_passive_sources(args)
    if passive_source_count > 1:
        raise SystemExit("ERROR: Select only one passive source: --input, --live-slcan, or --live-rev-serial.")
    if not _has_any_source(args):
        raise SystemExit("At least one source is required: --input, --live-slcan, --live-rev-serial, or --ctre-base-url.")
    expected_rows = {}
    resolved_profile = ""
    if args.profile_path.strip():
        try:
            resolved_profile, expected_rows = load_expected_rows(
                profile_path=args.profile_path,
                profile_name=args.profile_name,
            )
        except ValueError as exc:
            raise SystemExit(f"ERROR: {exc}") from exc
    label_rows = resolve_label_rows(
        expected_rows=expected_rows,
        profile_name=args.profile_name,
    )
    try:
        run_result = collect_result(
            args=args,
            expected_rows=expected_rows,
            resolved_profile=resolved_profile,
            label_rows=label_rows,
        )
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    output_path = resolve_output_path(input_path=args.input, explicit_output=args.output)
    write_json_result(path=output_path, result=run_result)
    if run_result.warnings:
        print("Warnings:")
        for warning in run_result.warnings:
            print(f"- {warning}")
        print("")
    print(render_summary_table(run_result))
    print(f"\nWrote {output_path}")
    if args.full_dump:
        print("")
        print(render_full_dump_result(run_result))
    return 0


def resolve_output_path(input_path: str, explicit_output: str) -> str:
    """
    NAME
        resolve_output_path - Choose the canonical JSON artifact path.
    """
    if explicit_output.strip():
        return explicit_output.strip()
    if input_path.strip():
        return f"{input_path}{DEFAULT_OUTPUT_SUFFIX}"
    return f"{APP_NAME}{EXT_JSON}"


def _has_any_source(args) -> bool:
    """
    NAME
        _has_any_source - Determine whether the user selected any input source.
    """
    return bool(
        args.input.strip()
        or bool(args.live_slcan)
        or args.live_rev_serial.strip()
        or args.ctre_base_url.strip()
    )


def _count_passive_sources(args) -> int:
    """
    NAME
        _count_passive_sources - Count selected passive acquisition inputs.
    """
    return int(bool(args.input.strip())) + int(bool(args.live_slcan)) + int(bool(args.live_rev_serial.strip()))


def collect_result(args, expected_rows, resolved_profile, label_rows) -> RunResult:
    """
    NAME
        collect_result - Collect one public result from offline or live CLI options.
    """
    run_metadata = {
        "timestampUtc": datetime.now(timezone.utc).isoformat(),
        "input": args.input,
        "liveSlcan": bool(args.live_slcan),
        "liveRevSerial": str(args.live_rev_serial).strip(),
        "channel": str(args.channel).strip(),
        "durationSec": float(args.duration),
        "profilePath": args.profile_path,
        "profileName": resolved_profile,
        "ctreBaseUrl": args.ctre_base_url,
    }
    if args.input.strip():
        result = analyze_frames(
            read_capture(args.input),
            expected_rows=expected_rows,
            run_metadata=run_metadata,
        )
    elif args.live_slcan:
        session = observe_slcan_session(
            channel=args.channel,
            auto_match=args.auto_match,
            bitrate=args.bitrate,
            interface=args.interface,
            duration_sec=args.duration,
            expected_rows=expected_rows,
        )
        session.start()
        session.wait(timeout=float(args.duration) + 2.0)
        result = session.snapshot()
    elif args.live_rev_serial.strip():
        session = observe_rev_serial_session(
            port=args.live_rev_serial,
            auto_match=args.rev_auto_match,
            baudrate=args.rev_baud,
            duration_sec=args.duration,
            expected_rows=expected_rows,
        )
        session.start()
        session.wait(timeout=float(args.duration) + 2.0)
        result = session.snapshot()
    else:
        result = analyze_frames([], expected_rows=expected_rows, run_metadata=run_metadata)
    if args.ctre_base_url.strip():
        result = enrich_result_with_ctre(result, args.ctre_base_url)
    if args.profile_path.strip():
        result = enrich_result_with_topology(
            result,
            profile_path=args.profile_path,
            profile_name=args.profile_name,
        )
    if label_rows:
        result = apply_profile_labels(result, expected_rows=label_rows)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
