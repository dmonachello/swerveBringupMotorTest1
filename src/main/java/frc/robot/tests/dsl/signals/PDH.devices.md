# Device Type: PDH

## Function

REV power distribution device with supply and per-channel telemetry similar to PDP-style checks.

## Details

- Use this for REV PDH voltage, current, fault, and switchable-channel evidence.
- Per-channel signals follow the generated catalog naming such as `channel0_current` and `channel0_fault`.

## Examples

```dsl
device "pdh"

main:
    require "pdh".voltage > 11.5
```
