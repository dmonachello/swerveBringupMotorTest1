SPEC_STATUS: IMPLEMENTED

# Robot Test DSL Signal Set Feature Spec

## 1. Purpose

Purpose: record the implemented signal-driven `set` feature for the Robot Test DSL.

This is a supporting implementation-history document.

For the current canonical language contract, use:

- [ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md](./ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md)
- [USER_GUIDE_ROBOT_TEST_DSL.md](./USER_GUIDE_ROBOT_TEST_DSL.md)
- [SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md](./SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md)

## 2. Implemented Syntax

Current supported forms are:

```text
set device.signal = literal
set device.signal = source.signal scaled number default literal
set device.signal = source.signal deadband number scaled number default literal
```

Example:

```text
set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0
```

## 3. Implemented Semantics

Current behavior:

- the target must be writable and numeric
- the source must be readable and numeric
- `scaled` is required
- `default` is required
- `deadband` is optional
- source unavailability in `main` uses the authored default
- source unavailability in `init` fails startup
- source unavailability in `close` skips the write
- fallback active on the `until` tick causes the test to fail

## 4. Current Constraints

Current validation and runtime constraints include:

- motor-device source signals are rejected for signal-driven `set`
- writable target range checks still apply
- the DSL engine owns fallback semantics
- devices own the actual write behavior

## 5. Notes

This feature is now part of the normal language and should not be treated as a sidecar extension when documenting or reasoning about authored tests.
