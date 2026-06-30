# Device Type: limitSwitch

## Function

Digital or controller-backed limit switch devices used for pressed/not-pressed completion checks.

## Details

- Use this when a test needs a simple contact or pressed condition.
- This is commonly paired with `success` or `require` for end-stop tests.

## Examples

```dsl
device "lmtSw0"

main:
    success lmtSw0.pressed
```
