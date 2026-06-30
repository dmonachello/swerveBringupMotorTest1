# Device Type: xboxController

## Function

Operator input device used as a live signal source for axes, buttons, triggers, and D-pad state.

## Details

- Use this when a DSL test reads operator input and feeds it into a writable output signal.
- Controller signals are read-only sources; they are not writable test targets.

## Examples

```dsl
device "controller0"
device "SPARKMAX/NEO 25"

main:
    set "SPARKMAX/NEO 25".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
```
