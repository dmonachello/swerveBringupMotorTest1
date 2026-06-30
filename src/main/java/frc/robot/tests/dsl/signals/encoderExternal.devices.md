# Device Type: encoderExternal

## Function

External encoder devices used to measure rotation and accumulated position change.

## Details

- Use this when motion proof comes from an external encoder instead of an integrated motor sensor.
- The aggregate `position_delta_max_abs` signal is useful for proving motion over the whole run.

## Examples

```dsl
device "driveEncoder0"

main:
    until timer.elapsed >= 3.0
    require "driveEncoder0".position_delta_max_abs > 5.0
```
