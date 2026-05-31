SPEC_STATUS: IMPLEMENTED

# Xbox Controller as DSL Device Feature Spec

## 1. Purpose

Purpose: record the implemented support for using configured Xbox controllers as Robot Test DSL devices.

This is a supporting implementation-history document.

For the current canonical language contract, use:

- [ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md](./ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md)
- [USER_GUIDE_ROBOT_TEST_DSL.md](./USER_GUIDE_ROBOT_TEST_DSL.md)
- [SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md](./SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md)

## 2. Implemented Outcome

The current implementation supports:

- declaring controller devices with:

```text
device "controller0"
```

- reading controller signals in conditions
- using controller numeric signals as sources for signal-driven `set`
- treating controller inputs as robot-local runtime inputs, not CAN or NetworkTables data

## 3. Current Signal Surface

Current DSL-visible Xbox controller signals are:

- `A`
- `B`
- `X`
- `Y`
- `LB`
- `RB`
- `BACK`
- `START`
- `LS`
- `RS`
- `D_UP`
- `D_RIGHT`
- `D_DOWN`
- `D_LEFT`
- `leftX`
- `leftY`
- `rightX`
- `rightY`
- `leftTrigger`
- `rightTrigger`

## 4. Current Constraints

Current constraints remain:

- controller signals are read-only
- controller devices must be configured devices in the active profile
- controller labels are usually `controller0`, `controller1`, and so on
- controller values are consumed from the robot-local controller snapshot path

## 5. Example

Condition example:

```text
main:
    success controller0.A
    abort controller0.B
```

Signal-driven set example:

```text
main:
    set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
```

## 6. Notes

This feature is no longer a partial special case.

Controller signals are part of the same canonical DSL signal registry used by the rest of the language.
