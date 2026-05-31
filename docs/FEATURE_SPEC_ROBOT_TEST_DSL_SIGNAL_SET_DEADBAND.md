SPEC_STATUS: IMPLEMENTED

# Robot Test DSL Signal-Set Deadband Feature Spec

## 1. Purpose

Purpose: record the implemented optional deadband behavior for signal-driven Robot Test DSL `set` statements.

This is a supporting implementation-history document.

For the current canonical language contract, use:

- [ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md](./ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md)
- [USER_GUIDE_ROBOT_TEST_DSL.md](./USER_GUIDE_ROBOT_TEST_DSL.md)
- [SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md](./SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md)

## 2. Implemented Syntax

Current supported deadband form:

```text
set device.signal = source.signal deadband number scaled number default literal
```

Example:

```text
set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
```

## 3. Implemented Semantics

Current behavior:

- deadband is optional
- deadband is applied before scaling
- if `abs(source) < deadband`, the resolved source becomes `0.0`
- the rest of signal-driven `set` semantics remain unchanged

## 4. Current Constraints

Current validation constraints include:

- deadband must be numeric
- deadband must be in range `0.0` to `1.0`
- deadband is not allowed on literal-only `set`

## 5. Notes

Deadband is now a standard part of the implemented language, not a proposal-only feature.
