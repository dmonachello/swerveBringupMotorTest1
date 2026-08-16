# Experimental CAN Replay PoC

## Purpose

Provide an isolated laboratory proof of concept for replaying timestamped frames
on a live CAN bus.

This tool is not part of the supported bringup bridge. The supported bridge is
passive and never imports this package.

## Safety

Live replay can move mechanisms, interfere with robot controllers, and damage
hardware. Use an isolated, powered-down-mechanism lab setup with appropriate
termination. Never connect this tool to an enabled competition robot.

Transmission is disabled unless `--tx-allow` is provided for the current
invocation.

## Example

```powershell
python -m tools.can_tx_poc.replay --channel COM3 --sequence frames.txt --tx-allow
```

Sequence rows may use either of these formats:

- Tab-delimited: timestamp, arbitration ID, payload length, hexadecimal payload.
- Comma-delimited: timestamp, arbitration ID, hexadecimal payload.

## Tradeoffs

The PoC intentionally does not share the supported bridge runtime or its source
configuration. This duplication keeps accidental transmission out of normal
diagnostics workflows.

## Future Extensions

Any promotion beyond PoC status requires a separate safety and architecture
review.
