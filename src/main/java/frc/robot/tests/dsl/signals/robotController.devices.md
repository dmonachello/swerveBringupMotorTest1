# Device Type: robotController

## Function

Shared robot-controller device family for roboRIO and future SystemCore health, rail, and CAN-controller evidence.

## Details

- Use this for the active robot controller selected by the current profile.
- Prefer shared controller signals when you want a test to stay portable across roboRIO and future SystemCore support.
- Current shared signals cover input power, brownout state, controller-local CAN health counters, and the 3.3V / 5V / 6V user rails.

## Examples

```dsl
device "roborio"

main:
    require "roborio".input_voltage > 11.5
    require "roborio".brownout == false
    require "roborio".rail_6v_enabled == true
```
