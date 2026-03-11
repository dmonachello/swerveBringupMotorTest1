from __future__ import annotations

"""
NAME
    can_ports.py - Serial port discovery for CANable slcan.

SYNOPSIS
    from can_ports import list_ports, maybe_auto_channel

DESCRIPTION
    Enumerates serial ports via pyserial and selects a matching CANable
    interface, optionally prompting the user.
"""

from typing import List, Tuple


def list_ports() -> List[Tuple[str, str]]:
    """
    NAME
        list_ports - Return available serial ports and descriptions.

    RETURNS
        List of (device, description) tuples.

    ERRORS
        Raises RuntimeError when pyserial is missing or enumeration fails.
    """
    try:
        import serial.tools.list_ports  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pyserial is required for listing serial ports. "
            "Install it with: py -m pip install pyserial"
        ) from exc
    ports: List[Tuple[str, str]] = []
    try:
        for port in serial.tools.list_ports.comports():
            ports.append((port.device, port.description or ""))
    except Exception as exc:
        raise RuntimeError(f"Failed to enumerate serial ports: {exc}") from exc
    return ports


def auto_channel(match_text: str, prompt: bool) -> Tuple[str, str]:
    """
    NAME
        auto_channel - Select a serial port matching a description substring.

    PARAMETERS
        match_text: Substring to match in port descriptions.
        prompt: Whether to prompt when multiple matches exist.

    RETURNS
        (device, description) tuple for the selected port.

    ERRORS
        Raises RuntimeError when no matches or ambiguous matches are found.
    """
    try:
        import serial.tools.list_ports  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pyserial is required for auto-detecting the CANable port. "
            "Install it with: py -m pip install pyserial"
        ) from exc

    matches: List[Tuple[str, str]] = []
    try:
        for port in serial.tools.list_ports.comports():
            desc = port.description or ""
            if match_text.lower() in desc.lower():
                matches.append((port.device, desc))
    except Exception as exc:
        raise RuntimeError(f"Failed to enumerate serial ports: {exc}") from exc

    if not matches:
        raise RuntimeError(
            f"No serial ports matched '{match_text}'. "
            "Specify --channel explicitly (e.g., COM3)."
        )

    if len(matches) > 1:
        if not prompt:
            raise RuntimeError(
                "Multiple serial ports matched "
                f"'{match_text}': {', '.join(dev for dev, _ in matches)}. "
                "Specify --channel explicitly."
            )
        print("Multiple matching serial ports found:")
        for idx, (dev, desc) in enumerate(matches, start=1):
            print(f"  {idx}. {dev} ({desc})")
        choice = input("Select port by number: ").strip()
        if not choice.isdigit():
            raise RuntimeError("Invalid selection. Specify --channel explicitly.")
        index = int(choice) - 1
        if index < 0 or index >= len(matches):
            raise RuntimeError("Selection out of range. Specify --channel explicitly.")
        return matches[index]

    return matches[0]


def maybe_auto_channel(args) -> Tuple[str | None, str | None, int]:
    """
    NAME
        maybe_auto_channel - Resolve a CAN channel from args or auto-detect.

    PARAMETERS
        args: Parsed CLI args containing channel and auto-match settings.

    RETURNS
        (channel, description, status_code) where status_code is 0 on success.
    """
    channel = args.channel
    if channel:
        return channel, None, 0
    try:
        channel, channel_desc = auto_channel(args.auto_match, not args.no_prompt)
    except Exception as exc:
        print(f"ERROR: Failed to auto-detect CAN channel: {exc}")
        return None, None, 2
    print(f"Auto-detected CAN channel: {channel} ({channel_desc})")
    return channel, channel_desc, 0
