# Robot Test DSL User Guide

## 1. Purpose

Purpose: explain how to write Robot Diagnostic Test DSL source files that match the current implementation.

This guide is for people authoring `.dsl` tests.

It describes the DSL-authored test surface only. It does not define every quick-bind or code-backed robot testing workflow in this repo.

Use this document for:

- writing syntax
- authoring rules
- supported signal names
- practical examples

Use the execution spec for authoritative runtime semantics:

- [ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md](./ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md)
- [FEATURE_SPEC_DSL_CONDITION_STABILITY_AND_RANGE_OPERATORS.md](./FEATURE_SPEC_DSL_CONDITION_STABILITY_AND_RANGE_OPERATORS.md)

## 2. Writing Model

The DSL is not a top-to-bottom script.

It defines a live rule set evaluated every robot control loop.

The only user-visible sequence is:

1. `init`
2. `main`
3. `close`

Inside a phase, statement order in the source file does not define execution order.

That means these two tests mean the same thing:

```text
main:
    set "FALCON 9".output = 0.5
    until timer.elapsed >= 3.0
    require "FALCON 9".velocity > 1000
```

```text
main:
    require "FALCON 9".velocity > 1000
    set "FALCON 9".output = 0.5
    until timer.elapsed >= 3.0
```

## 3. Basic Structure

Minimal test:

```text
test "spin_up_motor1"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.5
    until timer.elapsed >= 3.0
    require "FALCON 9".velocity > 1000
```

General structure:

```text
test "<name>"

device "<device_name>"
device "<device_name>"

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

- `test` names the test
- `device` declares every configured device the test references
- `main` is required
- `init` is optional
- `close` is optional
- `timer` is built in and must not be declared

## 4. Device References

Every signal reference uses:

```text
device.signal
```

Examples:

```text
"FALCON 9".output
"FALCON 9".velocity
lmtSw0.pressed
controller0.leftY
timer.elapsed
```

Rules:

- the device must exist in `bringup_system.json`
- the device must be declared in the test before use
- `timer` is built in and available automatically

Quoted names are lexical only. They let you reference labels with spaces or special characters.

These are equivalent if the device name is valid both ways:

```text
"lmtSw0".pressed
lmtSw0.pressed
```

## 5. Signal Catalog

Purpose: list the DSL-visible signals available to test authors today.

The canonical machine-readable source is:

- [tools/common/generated/robot_test_dsl_signals.json](../tools/common/generated/robot_test_dsl_signals.json)

That generated file is exported from the robot-side DSL signal registry and should match the host-side validator and runtime.

The table below is the human-readable summary.

<!-- markdownlint-disable MD013 -->

| Device type | Signal | Value type | Readable | Writable | Clearable | Safe value | Unsafe exit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `motor` | `output` | number | no | yes | no | `0.0` | yes |
| `motor` | `output_percent_cmd` | number | yes | yes | no | safe provider | yes |
| `motor` | `output_percent_applied` | number | yes | no | no | none | no |
| `motor` | `current` | number | yes | no | no | none | no |
| `motor` | `current_actual` | number | yes | no | no | none | no |
| `motor` | `temperature` | number | yes | no | no | none | no |
| `motor` | `temperature_actual` | number | yes | no | no | none | no |
| `motor` | `velocity` | number | yes | no | no | none | no |
| `motor` | `velocity_actual` | number | yes | no | no | none | no |
| `motor` | `position` | number | yes | no | no | none | no |
| `motor` | `position_actual` | number | yes | no | no | none | no |
| `motor` | `position_delta` | number | yes | no | no | none | no |
| `motor` | `faults` | boolean | no | no | yes | none | no |
| `limitSwitch` | `pressed` | boolean | yes | no | no | none | no |
| `encoderExternal` | `position` | number | yes | no | no | none | no |
| `encoderExternal` | `position_actual` | number | yes | no | no | none | no |
| `encoderExternal` | `position_delta` | number | yes | no | no | none | no |
| `xboxController` | `A` | boolean | yes | no | no | none | no |
| `xboxController` | `B` | boolean | yes | no | no | none | no |
| `xboxController` | `X` | boolean | yes | no | no | none | no |
| `xboxController` | `Y` | boolean | yes | no | no | none | no |
| `xboxController` | `LB` | boolean | yes | no | no | none | no |
| `xboxController` | `RB` | boolean | yes | no | no | none | no |
| `xboxController` | `BACK` | boolean | yes | no | no | none | no |
| `xboxController` | `START` | boolean | yes | no | no | none | no |
| `xboxController` | `LS` | boolean | yes | no | no | none | no |
| `xboxController` | `RS` | boolean | yes | no | no | none | no |
| `xboxController` | `D_UP` | boolean | yes | no | no | none | no |
| `xboxController` | `D_RIGHT` | boolean | yes | no | no | none | no |
| `xboxController` | `D_DOWN` | boolean | yes | no | no | none | no |
| `xboxController` | `D_LEFT` | boolean | yes | no | no | none | no |
| `xboxController` | `leftX` | number | yes | no | no | none | no |
| `xboxController` | `leftY` | number | yes | no | no | none | no |
| `xboxController` | `rightX` | number | yes | no | no | none | no |
| `xboxController` | `rightY` | number | yes | no | no | none | no |
| `xboxController` | `leftTrigger` | number | yes | no | no | none | no |
| `xboxController` | `rightTrigger` | number | yes | no | no | none | no |
| `TestTimer` | `elapsed` | number | yes | no | no | none | no |

<!-- markdownlint-enable MD013 -->

Notes:

- in authored DSL, the built-in timer is referenced as `timer.elapsed`
- `motor.output` is the main direct motor command signal
- `motor.output_percent_cmd` is also writable and readable, but authors should prefer `output` unless they specifically want the percent-command surface
- `unsafe-exit` is currently meaningful only for writable signals
- controller devices must be configured devices in the active profile
- controller labels usually look like `controller0`, `controller1`, and so on

Example configured controller device:

```json
{
  "label": "controller0",
  "type": "xboxController",
  "deviceInterface": "USB"
}
```

## 6. Phases

### 6.1 `init`

Purpose: one-time setup before live execution.

Typical uses:

- clear faults
- set startup state once
- stage one-time setup before observation

### 6.2 `main`

Purpose: the live rule phase.

This phase runs every control-loop tick.

Typical uses:

- command motor output continuously
- watch for overcurrent or overtemperature
- define stop boundaries
- define required evidence

### 6.3 `close`

Purpose: one-time cleanup after the result has already been decided.

Typical uses:

- clear sticky state
- perform cleanup writes before final safing

Important:

- `close` does not decide pass or fail
- final safing still happens after `close` unless a signal is named by `unsafe-exit`

## 7. Statement Reference

### 7.1 `set`

Supported forms:

```text
set device.signal = value
set device.signal = source.signal scaled number default value
set device.signal = source.signal deadband number scaled number default value
```

Examples:

```text
set "FALCON 9".output = 0.15
set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0
set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
```

Phase meaning:

- in `init`: write once
- in `main`: write every tick
- in `close`: write once during cleanup

Signal-driven `set` rules:

- target must be writable and numeric
- source must be readable and numeric
- `deadband` is optional
- `scaled` is required
- `default` is required
- source unavailability in `main` uses the authored default
- if fallback is still active when `until` fires, the test fails

Important current restriction:

- signal-driven `set` does not currently allow motor-device source signals
- practical sources are controller axes and other non-motor numeric signals

### 7.2 `abort`

Syntax:

```text
abort condition
```

Use `abort` for forbidden conditions.

Example:

```text
abort "FALCON 9".current > 40
```

### 7.3 `success`

Syntax:

```text
success condition
```

Use `success` only when the condition alone proves the test should pass immediately.

Example:

```text
success lmtSw0.pressed
```

### 7.4 `until`

Syntax:

```text
until condition
```

Use `until` to define a normal stop boundary.

Multiple `until` statements are OR'd.

Example:

```text
until timer.elapsed >= 3.0
until lmtSw0.pressed
```

### 7.5 `require`

Syntax:

```text
require condition
```

`require` means latched evidence.

Once the condition becomes true, it remains satisfied for the rest of the run.

Example:

```text
require "FALCON 9".velocity > 1000
```

Do not read `require` as a steady-state assertion.

### 7.6 `clear`

Syntax:

```text
clear device.signal
```

Use `clear` only for signals marked clearable.

This is a real device-specific clear action, not shorthand for:

```text
set device.signal = 0
```

### 7.7 `unsafe-exit`

Syntax:

```text
unsafe-exit device.signal
```

Use this only when you intentionally want a writable signal to skip final safe-state handling.

This is advanced and usually not appropriate for ordinary bringup tests.

## 8. Conditions

Supported condition forms:

```text
device.signal > value
device.signal >= value
device.signal < value
device.signal <= value
device.signal == value
device.signal != value
device.signal between low high
device.signal outside low high
device.signal
<condition> stable seconds
```

Bare form rules:

- valid only for boolean signals
- equivalent to `device.signal == true`
- `between` is inclusive at both endpoints
- `outside` excludes both endpoints
- `stable` is an optional condition suffix that requires the raw condition to remain continuously true for the authored duration before it counts as true

Examples:

```text
"FALCON 9".velocity > 1000
"FALCON 9".current > 1.0
"FALCON 9".temperature >= 80
encoder1.position between 100 120
"FALCON 9".current outside 0 40 stable 0.25
lmtSw0.pressed
controller0.A
timer.elapsed >= 3.0
```

Not supported:

- `and`
- `or`
- arithmetic expressions
- nested expressions
- function calls

## 9. Per-Tick Engine Order

Inside `main`, the runtime does this every tick:

1. apply all `set`
2. sample condition signals
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

Important:

- `require` latching happens before the result checks on the same tick

## 10. Result Model

### 10.1 `PASS`

A test passes when:

- a `success` condition becomes true

or:

- an `until` condition becomes true
- and all `require` conditions were satisfied
- and no signal-set fallback is active that tick

### 10.2 `FAIL`

A test fails when:

- an `abort` condition becomes true

or:

- normal `until` stop happens without all `require` conditions satisfied

or:

- normal `until` stop happens while signal-set fallback is active

### 10.3 `INTERRUPTED`

A test is interrupted when it is stopped externally, such as:

- robot disable
- estop
- manual cancel

In that case:

- `close` still runs
- final safing still runs unless exempted by `unsafe-exit`

## 11. Host-Side Workflow

The host-side model is source-authoritative.

That means:

- you author DSL source text
- the host compiler produces normalized JSON
- source and normalized JSON are stored together
- the robot executes normalized JSON only

Recommended flow:

1. create a `.dsl` file
2. import it into config
3. validate it
4. inspect source and normalized output
5. save config
6. deploy
7. run the saved test on the robot

Example CLI flow:

```text
merge config src\main\deploy\bringup_system.json
configure terminal
profile dsl_demo_050426
test import spin_up_motor1 temp_test.dsl set default
test validate spin_up_motor1 --json --pretty
end
show test spin_up_motor1
show test spin_up_motor1 normalized --json --pretty
```

Robot-side execution then uses the selected-test runner:

```text
tests select spin_up_motor1
tests run --wait --timeout 10
```

## 12. Examples

### 12.1 Timed motor observation

```text
test "spin_up_motor1"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.5
    until timer.elapsed >= 3.0
    require "FALCON 9".velocity > 1000
```

### 12.2 Safer first-pass motor smoke test

```text
test "spin_up_motor1_safe"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.15
    abort "FALCON 9".current > 40
    until timer.elapsed >= 2.0
    require "FALCON 9".velocity > 100
```

### 12.3 Fault clear before run

```text
test "clear_faults_then_spin"
device "FALCON 9"

init:
    clear "FALCON 9".faults

main:
    set "FALCON 9".output = 0.2
    until timer.elapsed >= 2.0
    require "FALCON 9".velocity > 100
```

### 12.4 Controller axis drives motor

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

### 12.5 Limit switch success

```text
test "run_to_limit"
device "FALCON 9"
device "lmtSw0"

main:
    set "FALCON 9".output = 0.2
    abort "FALCON 9".current > 40
    success lmtSw0.pressed
```

### 12.6 Controller confirmation

```text
test "operator_confirms_sensor"
device "controller0"

main:
    success controller0.A
    abort controller0.B
    abort timer.elapsed >= 10.0
```

### 12.7 Debounced limit switch

```text
test "run_to_limit_debounced"
device "FALCON 9"
device "lmtSw0"

main:
    set "FALCON 9".output = 0.2
    abort "FALCON 9".current outside 0 40 stable 0.15
    success lmtSw0.pressed stable 0.05
```

### 12.8 Stable encoder window

```text
test "encoder_window"
device "encoder1"

main:
    require encoder1.position between 100 120 stable 0.1
    abort encoder1.position outside 90 130 stable 0.05
    until timer.elapsed >= 2.0
```

## 13. Common Mistakes

### 13.1 Treating the file like a script

Wrong mental model:

- line 1 runs
- then line 2
- then line 3

Correct mental model:

- the file defines rule buckets
- the engine owns the per-tick order

### 13.2 Treating `require` like steady-state truth

Wrong assumption:

```text
require "FALCON 9".velocity > 1000
```

means velocity must remain above `1000`.

Actual meaning:

- velocity must exceed `1000` at least once before normal stop

### 13.3 Using `success` for timed pass

Avoid:

```text
success timer.elapsed >= 3.0
```

Prefer:

```text
until timer.elapsed >= 3.0
require "FALCON 9".velocity > 1000
```

### 13.4 Putting `clear` in `main`

Not allowed.

Use `clear` only in:

- `init`
- `close`

### 13.5 Forgetting that `main set` reasserts every tick

Use `init` for one-time setup.

Use `main` for continuous ownership.

### 13.6 Forgetting to declare a configured device

This is invalid:

```text
test "bad_test"

main:
    set "FALCON 9".output = 0.2
```

Because `"FALCON 9"` was never declared with:

```text
device "FALCON 9"
```

### 13.7 Using a bare non-boolean signal

This is invalid:

```text
require "FALCON 9".velocity
```

Use an explicit comparison:

```text
require "FALCON 9".velocity > 100
```

### 13.8 Reading `stable` like a blocking delay

Wrong assumption:

```text
success controller0.A stable 0.1
```

means the test pauses for `0.1` seconds and then checks the button.

Actual meaning:

- the button condition is still evaluated every tick
- the condition becomes true only after it has remained continuously true for `0.1` seconds

## 14. Recommended Starting Pattern

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

Why this works:

- bounded run time
- explicit failure condition
- explicit evidence of motion
- simple behavior
- easy to tune safely

## 15. Summary

Keep these rules in mind:

- only `init`, `main`, and `close` are sequenced
- every signal reference is explicit
- `init set` writes once
- `main set` writes every tick
- `abort` fails immediately
- `success` passes immediately
- `until` defines normal stop
- `require` means evidence that must happen at least once before normal stop
- `clear` is a real clear operation
- `unsafe-exit` is the explicit exception to final safing
