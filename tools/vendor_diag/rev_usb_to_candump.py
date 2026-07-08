from __future__ import annotations

"""
NAME
    rev_usb_to_candump.py - Convert REV USB gateway captures into CAN pcapng.

SYNOPSIS
    python tools/vendor_diag/rev_usb_to_candump.py input.pcapng output.pcapng

DESCRIPTION
    Reads a USBPcap capture containing REV USB CDC traffic, extracts ASCII
    SLCAN-like CAN frame records, and writes a Wireshark-readable SocketCAN
    pcapng capture.
"""

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional

REPO_ROOT_UP_LEVELS = 2
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if REPO_ROOT not in sys.path:
    sys.path.insert(INT_ZERO if "INT_ZERO" in globals() else 0, REPO_ROOT)

from tools.can_nt.can_logging import _PcapngWriter


DEFAULT_TSHARK_WINDOWS_PATH = r"C:\Program Files\Wireshark\tshark.exe"
ENV_TSHARK = "TSHARK"
EXT_PCAPNG = ".pcapng"
ENC_ASCII = "ascii"
ERR_IGNORE = "ignore"
FIELD_SEPARATOR = "|"
USB_DIRECTION_HOST = "host"
USB_DIRECTION_IN = "in"
USB_DIRECTION_OUT = "out"
USB_DIRECTION_BOTH = "both"
USB_PAYLOAD_DISPLAY_FILTER = "usbcom.data.in_payload || usbcom.data.out_payload"
USB_FIELDS = (
    "frame.time_epoch",
    "usb.device_address",
    "usb.src",
    "usbcom.data.in_payload",
    "usbcom.data.out_payload",
)
RECORD_PREFIX_EXT = "T"
RECORD_PREFIX_STD = "t"
RECORD_PREFIX_EXT_RTR = "R"
RECORD_PREFIX_STD_RTR = "r"
CHAR_CR = "\r"
CHAR_LF = "\n"
TEXT_EMPTY = ""
INT_ZERO = 0
INT_ONE = 1
INT_TWO = 2
INT_THREE = 3
INT_EIGHT = 8
INT_SIXTEEN = 16
CAN_ID_HEX_LEN_EXT = 8
CAN_ID_HEX_LEN_STD = 3
DIRECTION_CHOICES = (USB_DIRECTION_IN, USB_DIRECTION_OUT, USB_DIRECTION_BOTH)


@dataclass(frozen=True)
class UsbPayloadRecord:
    """
    NAME
        UsbPayloadRecord - One USB payload row extracted from tshark.
    """

    timestamp_s: float
    device_address: int
    direction: str
    ascii_text: str


@dataclass(frozen=True)
class CanFrameRecord:
    """
    NAME
        CanFrameRecord - One parsed CAN frame record from the USB ASCII stream.
    """

    timestamp_s: float
    arb_id: int
    data: bytes
    is_extended: bool
    is_rtr: bool


def build_parser() -> argparse.ArgumentParser:
    """
    NAME
        build_parser - Construct the command-line parser.
    """
    parser = argparse.ArgumentParser(
        description="Convert REV USB gateway captures into CAN pcapng."
    )
    parser.add_argument("input", help="Input USBPcap .pcapng capture path.")
    parser.add_argument("output", help="Output CAN .pcapng path.")
    parser.add_argument(
        "--device-address",
        type=int,
        default=INT_ZERO,
        help="USB device address to extract. Default auto-detects busiest USB CDC payload source.",
    )
    parser.add_argument(
        "--direction",
        choices=DIRECTION_CHOICES,
        default=USB_DIRECTION_BOTH,
        help="Which USB payload direction to convert.",
    )
    parser.add_argument(
        "--tshark",
        default=TEXT_EMPTY,
        help="Path to tshark. Defaults to TSHARK env var, PATH lookup, then Wireshark default install path.",
    )
    return parser


def resolve_tshark_path(cli_value: str) -> str:
    """
    NAME
        resolve_tshark_path - Resolve a usable tshark executable path.
    """
    candidates: List[str] = []
    if cli_value.strip():
        candidates.append(cli_value.strip())
    env_value = os.environ.get(ENV_TSHARK, TEXT_EMPTY).strip()
    if env_value:
        candidates.append(env_value)
    which_value = shutil.which("tshark")
    if which_value:
        candidates.append(which_value)
    candidates.append(DEFAULT_TSHARK_WINDOWS_PATH)
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("Unable to locate tshark. Use --tshark or set TSHARK.")


def _run_tshark_fields(
    tshark_path: str,
    input_path: str,
    display_filter: str,
    fields: Iterable[str],
) -> str:
    """
    NAME
        _run_tshark_fields - Execute tshark and return delimited field output.
    """
    command = [tshark_path, "-r", input_path]
    if display_filter.strip():
        command.extend(["-Y", display_filter])
    command.extend(["-T", "fields"])
    for field_name in fields:
        command.extend(["-e", field_name])
    command.extend(["-E", f"separator={FIELD_SEPARATOR}"])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding=ENC_ASCII,
        errors=ERR_IGNORE,
        check=True,
    )
    return completed.stdout


def detect_device_address(tshark_path: str, input_path: str) -> int:
    """
    NAME
        detect_device_address - Pick the USB device address with the most CDC payload rows.
    """
    output = _run_tshark_fields(
        tshark_path=tshark_path,
        input_path=input_path,
        display_filter=USB_PAYLOAD_DISPLAY_FILTER,
        fields=("usb.device_address", "usbcom.data.in_payload", "usbcom.data.out_payload"),
    )
    counts: Dict[int, int] = {}
    for line in output.splitlines():
        parts = line.split(FIELD_SEPARATOR)
        if len(parts) < INT_THREE:
            continue
        address_text = parts[INT_ZERO].strip()
        if not address_text:
            continue
        payload_in = parts[INT_ONE].strip()
        payload_out = parts[INT_ONE + INT_ONE].strip()
        if not payload_in and not payload_out:
            continue
        address = int(address_text)
        counts[address] = counts.get(address, INT_ZERO) + INT_ONE
    if not counts:
        raise RuntimeError("No USB CDC payload rows found in capture.")
    return max(counts.items(), key=lambda item: item[INT_ONE])[INT_ZERO]


def iter_usb_payload_records(
    tshark_path: str,
    input_path: str,
    device_address: int,
    direction: str,
) -> Iterator[UsbPayloadRecord]:
    """
    NAME
        iter_usb_payload_records - Yield decoded ASCII USB payload records.
    """
    display_filter = (
        f"usb.device_address == {device_address} && ({USB_PAYLOAD_DISPLAY_FILTER})"
    )
    output = _run_tshark_fields(
        tshark_path=tshark_path,
        input_path=input_path,
        display_filter=display_filter,
        fields=USB_FIELDS,
    )
    for line in output.splitlines():
        parts = line.split(FIELD_SEPARATOR)
        if len(parts) < len(USB_FIELDS):
            continue
        timestamp_text = parts[INT_ZERO].strip()
        address_text = parts[INT_ONE].strip()
        src_text = parts[INT_ONE + INT_ONE].strip()
        payload_in_hex = parts[INT_THREE].strip()
        payload_out_hex = parts[INT_THREE + INT_ONE].strip()
        payload_hex = payload_in_hex or payload_out_hex
        if not timestamp_text or not address_text or not payload_hex:
            continue
        payload_direction = (
            USB_DIRECTION_OUT if src_text == USB_DIRECTION_HOST else USB_DIRECTION_IN
        )
        if direction != USB_DIRECTION_BOTH and payload_direction != direction:
            continue
        ascii_text = bytes.fromhex(payload_hex).decode(ENC_ASCII, errors=ERR_IGNORE)
        yield UsbPayloadRecord(
            timestamp_s=float(timestamp_text),
            device_address=int(address_text),
            direction=payload_direction,
            ascii_text=ascii_text,
        )


def _split_complete_lines(
    buffers: Dict[str, str],
    direction: str,
    text: str,
) -> List[str]:
    """
    NAME
        _split_complete_lines - Reassemble CR/LF-terminated ASCII records.
    """
    current = buffers.get(direction, TEXT_EMPTY) + text
    current = current.replace(CHAR_LF, CHAR_CR)
    pieces = current.split(CHAR_CR)
    buffers[direction] = pieces[-INT_ONE]
    return [piece for piece in pieces[:-INT_ONE] if piece]


def iter_can_frames(payload_records: Iterable[UsbPayloadRecord]) -> Iterator[CanFrameRecord]:
    """
    NAME
        iter_can_frames - Parse CAN frame records from the USB ASCII stream.
    """
    buffers: Dict[str, str] = {}
    for payload in payload_records:
        for line in _split_complete_lines(buffers, payload.direction, payload.ascii_text):
            parsed = parse_ascii_can_record(line=line, timestamp_s=payload.timestamp_s)
            if parsed is not None:
                yield parsed


def parse_ascii_can_record(line: str, timestamp_s: float) -> Optional[CanFrameRecord]:
    """
    NAME
        parse_ascii_can_record - Parse one SLCAN-like ASCII CAN frame line.
    """
    if not line:
        return None
    prefix = line[INT_ZERO]
    if prefix not in (
        RECORD_PREFIX_EXT,
        RECORD_PREFIX_STD,
        RECORD_PREFIX_EXT_RTR,
        RECORD_PREFIX_STD_RTR,
    ):
        return None
    is_extended = prefix in (RECORD_PREFIX_EXT, RECORD_PREFIX_EXT_RTR)
    is_rtr = prefix in (RECORD_PREFIX_EXT_RTR, RECORD_PREFIX_STD_RTR)
    can_id_len = CAN_ID_HEX_LEN_EXT if is_extended else CAN_ID_HEX_LEN_STD
    minimum_len = INT_ONE + can_id_len + INT_ONE
    if len(line) < minimum_len:
        return None
    can_id_text = line[INT_ONE : INT_ONE + can_id_len]
    dlc_text = line[INT_ONE + can_id_len]
    try:
        arb_id = int(can_id_text, INT_SIXTEEN)
        dlc = int(dlc_text, INT_SIXTEEN)
    except ValueError:
        return None
    data_hex = line[minimum_len:]
    if is_rtr:
        data_bytes = b""
    else:
        expected_hex_len = dlc * INT_TWO
        if len(data_hex) < expected_hex_len:
            return None
        try:
            data_bytes = bytes.fromhex(data_hex[:expected_hex_len])
        except ValueError:
            return None
    return CanFrameRecord(
        timestamp_s=timestamp_s,
        arb_id=arb_id,
        data=data_bytes,
        is_extended=is_extended,
        is_rtr=is_rtr,
    )


def write_can_pcapng(output_path: str, frames: Iterable[CanFrameRecord], comment: str) -> int:
    """
    NAME
        write_can_pcapng - Emit SocketCAN pcapng output.
    """
    writer = _PcapngWriter(path=output_path, comment=comment)
    writer.start()
    count = INT_ZERO
    try:
        for frame in frames:
            writer.write_can_frame(
                timestamp_s=frame.timestamp_s,
                arb_id=frame.arb_id,
                data_bytes=frame.data,
                is_extended=frame.is_extended,
                is_rtr=frame.is_rtr,
                is_error=False,
            )
            count += INT_ONE
    finally:
        writer.stop()
    return count


def build_comment(input_path: str, device_address: int, direction: str) -> str:
    """
    NAME
        build_comment - Build a pcapng comment describing the conversion.
    """
    return (
        f"Generated from REV USB gateway capture {input_path}; "
        f"usb.device_address={device_address}; direction={direction}"
    )


def validate_args(args: argparse.Namespace) -> None:
    """
    NAME
        validate_args - Validate command-line arguments.
    """
    if not os.path.exists(args.input):
        raise FileNotFoundError(f"Input capture not found: {args.input}")
    if os.path.splitext(args.output)[INT_ONE].lower() != EXT_PCAPNG:
        raise ValueError("Output path must end with .pcapng")


def main(argv: Optional[List[str]] = None) -> int:
    """
    NAME
        main - CLI entrypoint.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(args)
    tshark_path = resolve_tshark_path(args.tshark)
    device_address = args.device_address or detect_device_address(
        tshark_path=tshark_path,
        input_path=args.input,
    )
    payload_records = iter_usb_payload_records(
        tshark_path=tshark_path,
        input_path=args.input,
        device_address=device_address,
        direction=args.direction,
    )
    count = write_can_pcapng(
        output_path=args.output,
        frames=iter_can_frames(payload_records),
        comment=build_comment(
            input_path=args.input,
            device_address=device_address,
            direction=args.direction,
        ),
    )
    print(
        f"Wrote {count} CAN frames to {args.output} "
        f"(usb.device_address={device_address}, direction={args.direction})"
    )
    return INT_ZERO


if __name__ == "__main__":
    sys.exit(main())
