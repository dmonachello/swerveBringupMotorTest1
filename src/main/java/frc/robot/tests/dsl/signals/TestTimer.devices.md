# Device Type: TestTimer

## Function

Built-in timing source used for timeouts and elapsed-time gating.

## Details

- The DSL timer is available without a device declaration, but it is still part of the supported signal model.
- Use `timer.elapsed` in `until`, `require`, `abort`, or `success` conditions.

## Examples

```dsl
main:
    until timer.elapsed >= 10.0
    require timer.elapsed >= 0.5
```
