# DSL Language Pack For AI

## 1. Purpose

Purpose: give an AI model one concise, current document pack for understanding the Robot Diagnostic Test DSL in this repo.

If you hand one file to ChatGPT first, use this one.

This pack is a high-signal summary of the implemented language.

Canonical sources behind this pack:

- [ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md](./ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md)
- [USER_GUIDE_ROBOT_TEST_DSL.md](./USER_GUIDE_ROBOT_TEST_DSL.md)
- [FEATURE_SPEC_DSL_CONDITION_STABILITY_AND_RANGE_OPERATORS.md](./FEATURE_SPEC_DSL_CONDITION_STABILITY_AND_RANGE_OPERATORS.md)
- [SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md](./SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md)
- [tools/common/generated/robot_test_dsl_signals.json](../tools/common/generated/robot_test_dsl_signals.json)

## 2. What The Language Is

The Robot Diagnostic Test DSL is a small live-rule language for bringup and diagnostic tests.

It is not a general-purpose scripting language.

It is used to:

- command motors or other writable signals
- observe sensor and controller inputs
- define immediate fail conditions
- define immediate pass conditions
- define bounded observation windows
- require evidence before normal pass

## 3. Core Mental Model

Each test has three phases:

1. `init`
2. `main`
3. `close`

Only those phases are sequenced.

Inside `main`, the runtime evaluates a live rule set every robot control-loop tick.

Interpret the keywords like this:

- `set`: command or derive a signal value
- `abort`: forbidden condition, fail immediately
- `success`: sufficient proof, pass immediately
- `until`: normal stop boundary
- `require`: evidence that must happen at least once before normal stop
- `clear`: device-specific clear action
- `unsafe-exit`: skip final safing for one writable signal

## 4. Authoring Shape

General shape:

```text
test "<name>"

device "<configured_device_label>"

unsafe-exit <device>.<signal>

init:
    set <device>.<signal> = <value>
    clear <device>.<signal>

main:
    set <device>.<signal> = <value>
    set <device>.<signal> = <source>.<signal> scaled <number> default <value>
    set <device>.<signal> = <source>.<signal> deadband <number> scaled <number> default <value>
    abort <condition>
    success <condition>
    until <condition>
    require <condition>

close:
    set <device>.<signal> = <value>
    clear <device>.<signal>
```

Rules:

- `main` is required
- `init` and `close` are optional
- every configured device reference must be declared
- `timer` is built in and must not be declared

## 5. Condition Forms

Supported condition forms:

```text
device.signal > literal
device.signal >= literal
device.signal < literal
device.signal <= literal
device.signal == literal
device.signal != literal
device.signal between low high
device.signal outside low high
device.signal
<condition> stable seconds
```

Important rules:

- bare `device.signal` is only valid for boolean signals
- bare boolean reference means `device.signal == true`
- `between` is inclusive at both ends
- `outside` excludes both endpoints
- `stable` delays truth until the raw condition has remained continuously true for the authored duration
- compound expressions are not supported
- `and`, `or`, nested expressions, and function calls are not supported

## 6. Implemented Tick Order

Inside `main`, the current runtime does this every tick:

1. apply all `set`
2. sample all condition signals
3. evaluate raw conditions
4. update `stable` filters
5. latch `require`
6. evaluate `abort`
7. evaluate `success`
8. evaluate `until`

Priority is:

```text
abort > success > until
```

Important nuance:

- `require` latching happens before `abort`, `success`, and `until` on the same tick

## 7. Result Semantics

`PASS`:

- any `success` condition becomes true

or:

- an `until` condition becomes true
- all `require` conditions are already satisfied
- no signal-set fallback is active on that tick

`FAIL`:

- any `abort` condition becomes true

or:

- an `until` condition becomes true before all `require` conditions are satisfied

or:

- an `until` condition becomes true while signal-set fallback is active

`INTERRUPTED`:

- robot disable
- estop
- manual cancel

## 8. The Most Important Semantics To Not Misread

### 8.1 `require` is latched evidence

This:

```text
require "FALCON 9".velocity > 1000
```

means:

- velocity must exceed `1000` at least once before normal stop

It does not mean:

- velocity must stay above `1000`
- velocity is checked only on the final tick

With:

```text
require "FALCON 9".velocity > 1000 stable 0.1
```

the condition must remain continuously true for `0.1` seconds before the latch is satisfied.

### 8.2 `main set` means continuous ownership

This:

```text
main:
    set "FALCON 9".output = 0.2
```

means the runtime reasserts that command every tick.

### 8.3 Source line order inside a phase is not execution order

The file defines rule buckets, not a procedural instruction list.

## 9. Signal-Driven Set

Supported forms:

```text
set target.signal = source.signal scaled number default literal
set target.signal = source.signal deadband number scaled number default literal
```

Current semantics:

- target must be writable and numeric
- source must be readable and numeric
- `scaled` is required
- `default` is required
- `deadband` is optional
- deadband is applied before scaling
- source unavailable in `main` writes the authored default
- source unavailable in `init` fails startup
- source unavailable in `close` skips the write
- fallback active on the `until` tick fails the test

Current restriction:

- motor-device source signals are rejected for signal-driven `set`

Practical current sources are:

- controller axes
- other non-motor numeric sources

## 10. Supported Device Types And Signals

High-level supported families:

- `motor`
- `limitSwitch`
- `encoderExternal`
- `xboxController`
- built-in `timer`

Important currently visible signals:

- motor:
  - `output`
  - `output_percent_cmd`
  - `output_percent_applied`
  - `current`
  - `current_actual`
  - `temperature`
  - `temperature_actual`
  - `velocity`
  - `velocity_actual`
  - `position`
  - `position_actual`
  - `position_delta`
  - `faults`
- limit switch:
  - `pressed`
- external encoder:
  - `position`
  - `position_actual`
  - `position_delta`
- Xbox controller:
  - `A`, `B`, `X`, `Y`
  - `LB`, `RB`, `BACK`, `START`
  - `LS`, `RS`
  - `D_UP`, `D_RIGHT`, `D_DOWN`, `D_LEFT`
  - `leftX`, `leftY`, `rightX`, `rightY`
  - `leftTrigger`, `rightTrigger`
- timer:
  - `elapsed`

Use the generated JSON artifact when exact machine-readable signal capability details matter.

## 11. Timer Rules

The built-in timer is authored as:

```text
timer.elapsed
```

Rules:

- readable only
- not declared with `device`
- returns seconds since test start

## 12. Safety Rules

The runtime owns startup safing and final safing.

At start:

- writable DSL signals are forced to their safe values before `main`

At stop:

- `close` runs
- then writable DSL signals are returned to their safe values
- except signals named by `unsafe-exit`

## 13. Good Default Pattern

For a first motor bringup test, start here:

```text
test "<name>"
device "<motor>"

main:
    set "<motor>".output = <small_duty>
    abort "<motor>".current > <limit>
    until timer.elapsed >= <seconds>
    require "<motor>".velocity > <threshold>
```

Why:

- bounded time
- explicit fail condition
- explicit motion evidence
- easy to reason about

## 14. Common Wrong Assumptions

Do not assume:

- the DSL is procedural
- `require` means steady-state truth
- line order inside a phase defines runtime order
- every reporting field is a DSL-visible signal
- `clear` means `set = 0`
- every readable numeric signal can be used as a signal-driven source today

## 15. Examples

Fixed motor smoke test:

```text
test "spin_up_motor1"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.15
    abort "FALCON 9".current > 40
    until timer.elapsed >= 2.0
    require "FALCON 9".velocity > 100
```

Stable range check:

```text
test "encoder_window"
device "encoder1"

main:
    require encoder1.position between 100 120 stable 0.1
    abort encoder1.position outside 90 130 stable 0.05
    until timer.elapsed >= 2.0
```

Controller-driven smoke test:

```text
test "falcon_axis_drive"
device "FALCON 9"
device "controller0"

main:
    set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
    abort "FALCON 9".current > 35
    abort "FALCON 9".temperature > 80
    until timer.elapsed >= 3.0
```

Operator-confirmed test:

```text
test "operator_confirms_sensor"
device "controller0"

main:
    success controller0.A
    abort controller0.B
    abort timer.elapsed >= 10.0
```

## 16. Best Hand-Off Guidance For Another AI

If another model is asked to interpret or generate this DSL, tell it:

- use `ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md` as the runtime truth
- use `USER_GUIDE_ROBOT_TEST_DSL.md` for examples and authoring rules
- use `FEATURE_SPEC_DSL_CONDITION_STABILITY_AND_RANGE_OPERATORS.md` for rationale and extended examples
- use `tools/common/generated/robot_test_dsl_signals.json` for the exact signal catalog
- treat `require` as latched evidence
- treat `stable` as a condition suffix, not as a blocking wait
- treat `main set` as continuous command ownership
- do not invent unsupported compound expressions or staged syntax
