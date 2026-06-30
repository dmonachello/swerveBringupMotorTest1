# Device Type: PDP

## Function

Legacy CTRE power distribution device with voltage, current, temperature, and per-channel signals.

## Details

- Use this for power-distribution checks, brownout guards, and per-channel load evidence.
- Per-channel signals follow the generated catalog naming such as `channel0_current` and `channel0_fault`.

## Examples

```dsl
device "pdp"

main:
    abort "pdp".brownout == true
    require "pdp".channel0_current > 0.2
```
