# Device Type: motor

## Function

Motor controller devices used for commanded output, motion, current, and temperature evidence.

## Details

- Use this for controllable motors such as Falcons, Krakens, and Spark MAX / NEO devices.
- Most motion-oriented DSL tests read position, velocity, current, and temperature signals from this device type.
- Run-scoped aggregate signals such as `current_actual_max` and `position_delta_max_abs` prove that something happened sometime during the run, not just at the final sample.

## Examples

```dsl
device "FALCON 9"
device "SPARKMAX/NEO 25"

main:
    set "FALCON 9".output_percent_cmd = 0.15
    require "SPARKMAX/NEO 25".position_delta_max_abs > 1.0
```
