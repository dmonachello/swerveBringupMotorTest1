from __future__ import annotations

from typing import List, Tuple


def list_ports() -> List[Tuple[str, str]]:
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
