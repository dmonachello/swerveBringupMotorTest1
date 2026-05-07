# Robot Test DSL User Guide

Note: The signal-set deadband feature described in this guide was implemented with pi.

## 1. Purpose

Purpose: Explain how to write robot diagnostic tests using the Robot Test DSL.

This guide is for the person writing `.dsl` test files.

It covers:

- the writing model
- the syntax
- what each statement means
- the host-side workflow
- common mistakes
- many examples you can adapt

This guide is not the runtime contract. The execution semantics live in:

- [ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md](./ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md)

## 2. The Mental Model

The Robot Test DSL is not a script language.

It does not mean:

- line 1 runs
- then line 2 runs
- then line 3 runs

Instead, it defines live test rules.

A test tells the engine:

- what to command
- what to watch
- what should fail immediately
- what should pass immediately
- when normal observation ends
- what evidence must happen before normal stop

Think of each test as a live rule set evaluated every control-loop tick.

## 3. The Only User-Visible Sequencing

The only user-visible sequencing in v0.3 is:

1. `init`
2. `main`
3. `close`

That is the only authored sequence.

Inside a phase, statement order in the source file is not the execution order.

For example, these mean the same thing:

```text
main:
    set "FALCON 9".output = 0.5
    until timer.elapsed >= 3.0
    require "FALCON 9".velocity > 1000
```

and

```text
main:
    require "FALCON 9".velocity > 1000
    set "FALCON 9".output = 0.5
    until timer.elapsed >= 3.0
```

Why:

- the file describes rule buckets
- the engine applies its own fixed per-tick order

If you need true multi-stage sequencing, that is not in v0.3.

## 4. Basic Test Structure

Minimal test:

```text
test "spin_up_motor1"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.5
    until timer.elapsed >= 3.0
    require "FALCON 9".velocity > 1000
```

General shape:

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
- `device` declares every device the test uses
- `main` is required
- `init` is optional
- `close` is optional
- `timer` is built in and must not be declared

## 5. Device References

Every signal reference is explicit:

```text
device.signal
```

Examples:

```text
"FALCON 9".output
"FALCON 9".velocity
lmtSw0.pressed
timer.elapsed
```

Rules:

- devices must already exist in `bringup_system.json`
- devices must be declared in the test before use
- `timer` is built in and available automatically

Quotes are lexical only. They allow spaces or special characters in names.

These mean the same thing if the device name is valid both ways:

```text
"lmtSw0".pressed
lmtSw0.pressed
```

### 5.1 Signal Catalog

Purpose: list the device signals currently available to DSL authors.

Use these signal names in explicit `device.signal` references.

<!-- markdownlint-disable MD013 -->

| Device type | Signal | Value type | Readable | Writable | Clearable | Safe value | Unsafe exit | Runtime support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `motor` | `output` | number | no | yes | no | `0.0` | yes | yes |
| `motor` | `current` | number | yes | no | no | none | no | yes |
| `motor` | `temperature` | number | yes | no | no | none | no | yes |
| `motor` | `velocity` | number | yes | no | no | none | no | yes |
| `motor` | `position` | number | yes | no | no | none | no | yes |
| `motor` | `faults` | boolean | no | no | yes | none | no | yes for `clear` |
| `limitSwitch` | `pressed` | boolean | yes | no | no | none | no | yes |
| `encoderExternal` | `position` | number | yes | no | no | none | no | yes |
| `xboxController` | `A` | boolean | yes | no | no | none | no | yes |
| `xboxController` | `B` | boolean | yes | no | no | none | no | yes |
| `xboxController` | `leftY` | number | yes | no | no | none | no | yes |
| `xboxController` | `rightY` | number | yes | no | no | none | no | yes |
| `TestTimer` | `elapsed` | number | yes | no | no | none | no | yes |

<!-- markdownlint-enable MD013 -->

Notes:

- `timer.elapsed` is built in and does not require a `device` declaration.
- `motor.output` is the only writable signal currently defined.
- `motor.faults` is clearable with `clear`.
- `unsafe-exit` is currently allowed only for `motor.output`.
- Controller signals use the live controller snapshots passed into the
  robot-side test runtime.
- Controllers must be defined as configured devices in `bringup_system.json`
  and included in the active profile.
- Controller labels normally use `controller0`, `controller1`, and so on.

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

Purpose: one-time setup before live test execution starts.

Typical uses:

- clear faults
- set one-time startup state
- configure an output once and then observe

### 6.2 `main`

Purpose: the live test.

This phase runs every control-loop tick.

Typical uses:

- command motor output every tick
- watch for overcurrent
- define when to stop
- define what evidence must happen

### 6.3 `close`

Purpose: one-time cleanup after termination.

Typical uses:

- clear sticky state
- restore a mode
- issue cleanup writes that should happen before final safing

Important:

- `close` does not decide pass or fail
- by default, final safing still happens after `close`

## 7. Statement Reference

### 7.1 `set`

Syntax:

```text
set device.signal = value
set device.signal = source.signal scaled number default value
set device.signal = source.signal deadband number scaled number default value
```

Purpose:

- write a writable signal
- optionally drive a writable numeric signal from a readable numeric signal

Examples:

```text
set "FALCON 9".output = 0.15
set "FALCON 9".output = 0.5
set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0
set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
```

Meaning by phase:

- in `init`: write once before `main`
- in `main`: write every tick
- in `close`: write once during cleanup

This distinction matters.

Example: one-time setup

```text
init:
    set "FALCON 9".output = 0.15
```

Example: continuous ownership

```text
main:
    set "FALCON 9".output = 0.15
```

If you put a `set` in `main`, the engine reasserts it every tick.

Signal-driven `set` rules:

- the target must be a writable numeric signal
- the source must be a readable numeric signal
- the source value is whatever the device exposes at runtime
- `deadband` is optional
- when `deadband` is present, values with magnitude smaller than the deadband resolve to `0.0`
- deadband is applied before scaling
- `scaled` is required
- `default` is required
- if the source is unavailable in `init`, test startup fails
- if the source is unavailable in `main`, the runtime uses `default`
- if the source is unavailable in `close`, that write is skipped
- if fallback is still active when an `until` stops the test, the test fails
- runtime warnings are emitted while fallback is active

### 7.2 `abort`

Syntax:

```text
abort condition
```

Purpose:

- forbidden condition
- immediate failure

Example:

```text
abort "FALCON 9".current > 40
```

Meaning:

- if the condition becomes true at any tick, the test stops immediately
- result = `FAIL`

Use `abort` for:

- current too high
- temperature too high
- wrong switch hit
- mechanism moved into an unsafe region

### 7.3 `success`

Syntax:

```text
success condition
```

Purpose:

- immediate pass when one condition by itself is enough

Example:

```text
success lmtSw0.pressed
```

Meaning:

- if the condition becomes true, the test stops immediately
- result = `PASS`

Use `success` only when the condition itself proves success.

Avoid time-based `success` unless that is truly what you want.

### 7.4 `until`

Syntax:

```text
until condition
```

Purpose:

- normal stop boundary

Example:

```text
until timer.elapsed >= 3.0
```

Meaning:

- when the condition becomes true, the test stops normally
- then all `require` conditions are checked

Multiple `until` statements are OR.

That means:

```text
until timer.elapsed >= 3.0
until lmtSw0.pressed
```

stops when either condition becomes true.

### 7.5 `require`

Syntax:

```text
require condition
```

Purpose:

- evidence that must happen during `main`

Example:

```text
require "FALCON 9".velocity > 1000
```

Meaning:

- if the condition becomes true even once, that requirement becomes satisfied
- once satisfied, it stays satisfied for the rest of the run
- it is checked only when the test stops by `until`

This is a latched evidence rule.

It does not mean:

- true every tick
- true at the final tick only

That is important because motors and mechanisms usually need time to ramp up.

Multiple `require` statements are AND.

That means:

```text
require "FALCON 9".velocity > 1000
require "FALCON 9".current > 1.0
```

passes only if both requirements became satisfied before normal stop.

### 7.6 `clear`

Syntax:

```text
clear device.signal
```

Purpose:

- invoke a device-specific clear operation

Example:

```text
init:
    clear "FALCON 9".faults
```

Rules:

- valid only in `init` and `close`
- valid only for signals marked clearable

`clear` is not shorthand for:

```text
set device.signal = 0
```

Use it only for signals with real clear semantics such as faults or sticky state.

### 7.7 `unsafe-exit`

Syntax:

```text
unsafe-exit device.signal
```

Purpose:

- exempt one writable signal from final safe-state handling at test exit

Default behavior:

- after `close`, the engine safes writable outputs

`unsafe-exit` is the explicit opt-out.

Example:

```text
unsafe-exit "FALCON 9".output
```

Meaning:

- after `close`, do not apply final safe-state to `output`

Use this sparingly.

If you do not need a signal to remain non-safe after the test, do not use `unsafe-exit`.

## 8. Conditions

v0.3 supports simple conditions only.

Allowed forms:

```text
device.signal > value
device.signal >= value
device.signal < value
device.signal <= value
device.signal == value
device.signal != value
device.signal
```

Bare reference form:

```text
lmtSw0.pressed
```

Meaning:

- valid only for boolean signals
- treated as boolean truth
- equivalent to `lmtSw0.pressed == true`

Examples:

```text
"FALCON 9".velocity > 1000
"FALCON 9".current > 1.0
"FALCON 9".temperature >= 80
lmtSw0.pressed
timer.elapsed >= 3.0
```

Not supported in v0.3:

- `and`
- `or`
- arithmetic expressions
- functions
- nested expressions

## 9. Per-Tick Engine Order

Inside `main`, the engine does this each tick:

1. apply all `set`
2. sample signals
3. evaluate `abort`
4. evaluate `success`
5. evaluate `until`
6. update and latch `require`

Priority:

```text
abort > success > until
```

This means:

- `abort` always wins if true
- `success` passes immediately if no `abort` fired first
- `until` performs normal stop and then `require` determines pass/fail

## 10. Pass, Fail, and Interrupted

### 10.1 Pass

A test passes when:

- a `success` condition becomes true

or

- an `until` condition becomes true
- and all `require` conditions have become satisfied

### 10.2 Fail

A test fails when:

- an `abort` condition becomes true

or

- an `until` condition becomes true
- and one or more `require` conditions were never satisfied

### 10.3 Interrupted

A test is interrupted when it stops externally, for example:

- robot disable
- estop
- manual stop

In that case:

- `close` still runs
- final safing still happens unless exempted by `unsafe-exit`
- result = `INTERRUPTED`

## 11. Host-Side Workflow

The host-side model is source-authoritative.

That means:

- you write source text
- the host compiles it
- normalized JSON is stored alongside it
- the robot executes normalized JSON only

Recommended workflow:

1. create a `.dsl` file
2. import it into local config
3. validate it
4. inspect source and normalized output
5. save config
6. deploy updated config and robot code
7. run the saved test on the robot

CLI flow:

```text
merge config data\bringup_system.json
configure terminal
profile dsl_demo_050426
test import spin_up_motor1 temp_test.dsl set default
test validate spin_up_motor1 --json --pretty
end
show test spin_up_motor1
show test spin_up_motor1 normalized --json --pretty
```

Set management:

```text
test set create diagnostics
test set add diagnostics spin_up_motor1
test set default diagnostics
show test sets --json --pretty
```

## 12. Syntax Reference

This section is the quick reference for day-to-day writing.

```text
test "<name>"

device "<device_name>"

unsafe-exit <device>.<signal>

init:
    set <device>.<signal> = <value>
    set <device>.<signal> = <source>.<signal> scaled <number> default <value>
    clear <device>.<signal>

main:
    set <device>.<signal> = <value>
    set <device>.<signal> = <source>.<signal> scaled <number> default <value>
    abort <condition>
    success <condition>
    until <condition>
    require <condition>

close:
    set <device>.<signal> = <value>
    set <device>.<signal> = <source>.<signal> scaled <number> default <value>
    clear <device>.<signal>
```

Condition forms:

```text
<device>.<signal> > <value>
<device>.<signal> >= <value>
<device>.<signal> < <value>
<device>.<signal> <= <value>
<device>.<signal> == <value>
<device>.<signal> != <value>
<device>.<signal>
```

## 13. Examples

### 13.1 Timed motor observation test

```text
test "spin_up_motor1"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.5
    until timer.elapsed >= 3.0
    require "FALCON 9".velocity > 1000
```

Meaning:

- command 50% output every tick
- stop at 3 seconds
- pass only if velocity exceeded 1000 at least once before 3 seconds

### 13.2 Safer first-pass spin test

```text
test "spin_up_motor1_safe"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.15
    until timer.elapsed >= 2.0
    require "FALCON 9".velocity > 100
```

Use this first on real hardware.

### 13.3 One-time setup in `init`

```text
test "spin_once_then_observe"
device "FALCON 9"

init:
    set "FALCON 9".output = 0.2

main:
    until timer.elapsed >= 2.0
    require "FALCON 9".velocity > 100
```

Meaning:

- one setup write before `main`
- no continuous reassertion in `main`

### 13.4 Abort on overcurrent

```text
test "spin_abort_overcurrent"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.3
    abort "FALCON 9".current > 40
    until timer.elapsed >= 3.0
    require "FALCON 9".velocity > 300
```

Meaning:

- fail immediately on overcurrent
- otherwise stop at 3 seconds
- require some motion evidence

### 13.5 Abort on temperature

```text
test "spin_abort_temperature"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.2
    abort "FALCON 9".temperature > 80
    until timer.elapsed >= 2.0
    require "FALCON 9".velocity > 100
```

### 13.6 Multiple required evidence conditions

```text
test "spin_require_speed_and_current"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.25
    until timer.elapsed >= 3.0
    require "FALCON 9".velocity > 500
    require "FALCON 9".current > 1.0
```

Meaning:

- motion must occur
- some current draw must occur
- both must happen before the test passes

### 13.7 Limit switch success

```text
test "run_to_limit"
device "FALCON 9"
device "lmtSw0"

main:
    set "FALCON 9".output = 0.2
    abort "FALCON 9".current > 40
    success lmtSw0.pressed
```

Meaning:

- drive the motor
- pass immediately when the limit switch is hit
- fail immediately on overcurrent

### 13.8 Timed limit switch observation

```text
test "limit_switch_observe"
device "lmtSw0"

main:
    until timer.elapsed >= 5.0
    require lmtSw0.pressed
```

Meaning:

- observe for 5 seconds
- pass only if the switch became pressed at least once

### 13.9 Fault clear before test

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

### 13.10 Cleanup in `close`

```text
test "spin_and_cleanup"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.2
    until timer.elapsed >= 2.0
    require "FALCON 9".velocity > 100

close:
    clear "FALCON 9".faults
```

Meaning:

- cleanup happens after the verdict is already determined

### 13.11 Retain motor output after exit

```text
test "retain_motor_output_advanced"
device "FALCON 9"
unsafe-exit "FALCON 9".output

main:
    set "FALCON 9".output = 0.05
    until timer.elapsed >= 0.5
```

Meaning:

- test ends normally
- final safe-state does not stop motor output
- the last commanded output may remain active after the test exits

Do not use this for normal motor bringup tests.

### 13.12 Forever test with manual stop

```text
test "manual_spin"
device "FALCON 9"

main:
    set "FALCON 9".output = 0.15
    abort "FALCON 9".current > 40
```

Meaning:

- test has no normal end condition
- it runs until externally stopped
- external stop yields `INTERRUPTED`

### 13.13 Observe one sensor while driving another device

```text
test "spin_until_external_switch"
device "FALCON 9"
device "lmtSw0"

main:
    set "FALCON 9".output = 0.2
    until lmtSw0.pressed
    require "FALCON 9".velocity > 100
```

### 13.14 Two normal stop boundaries

```text
test "time_or_switch_stop"
device "FALCON 9"
device "lmtSw0"

main:
    set "FALCON 9".output = 0.2
    until timer.elapsed >= 3.0
    until lmtSw0.pressed
    require "FALCON 9".velocity > 100
```

Meaning:

- stop when the timer expires or the switch is hit

### 13.15 Controller button success

```text
test "operator_confirms_sensor"
device "controller0"

main:
    success controller0.A
    abort controller0.B
    abort timer.elapsed >= 10.0
```

Meaning:

- pass immediately when `controller0` button `A` is pressed
- fail immediately when `controller0` button `B` is pressed
- fail after 10 seconds if neither button is pressed

### 13.16 Controller axis threshold

```text
test "operator_axis_threshold"
device "controller0"

main:
    success controller0.leftY > 0.5
    abort timer.elapsed >= 5.0
```

Meaning:

- pass if the left Y axis rises above `0.5`
- otherwise fail after 5 seconds

### 13.17 Controller axis drives motor output

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

Meaning:

- motor output follows the device-exposed `controller0.leftY` value times `0.25`
- values with magnitude smaller than `0.08` resolve to `0.0` before scaling
- if the controller signal is unavailable during `main`, output falls back to `0.0`
- if fallback is still active at the normal stop boundary, the test fails

## 14. Common Authoring Mistakes

### 14.1 Thinking it runs top-to-bottom

Wrong mental model:

- line 1 runs
- then line 2
- then line 3

Correct mental model:

- the phase declares rules
- the engine applies its own fixed order each tick

### 14.2 Using `require` like a steady-state assertion

Wrong assumption:

- `require velocity > 1000` means velocity must stay above 1000

Actual meaning:

- velocity only needs to exceed 1000 once before normal stop

### 14.3 Using `success` for timed pass

Avoid:

```text
success timer.elapsed >= 3.0
```

That means:

- pass after 3 seconds whether or not anything useful happened

Use instead:

```text
until timer.elapsed >= 3.0
require "FALCON 9".velocity > 1000
```

### 14.4 Putting `clear` in `main`

Not allowed.

Use `clear` only in:

- `init`
- `close`

### 14.5 Forgetting that `main set` reasserts every tick

If you want one-time setup, use `init`.

If you want continuous control, use `main`.

### 14.6 Forgetting to declare a device

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

### 14.7 Using a bare non-boolean signal

This is invalid:

```text
require "FALCON 9".velocity
```

Use an explicit comparison instead:

```text
require "FALCON 9".velocity > 100
```

## 15. Recommended Starting Pattern

For a first motor bring-up test, start with this shape:

```text
test "<name>"
device "<motor>"

main:
    set "<motor>".output = <small_duty>
    abort "<motor>".current > <limit>
    until timer.elapsed >= <seconds>
    require "<motor>".velocity > <threshold>
```

Why this shape works well:

- bounded run time
- explicit failure condition
- explicit motion evidence
- simple to reason about
- easy to tune safely

## 16. Summary

Keep these rules in mind:

- only `init`, `main`, and `close` are sequenced
- every signal reference is explicit
- `init set` writes once
- `main set` writes every tick
- `abort` fails immediately
- `success` passes immediately
- `until` defines normal stop
- `require` means evidence that must happen at least once before normal stop
- `clear` is a real clear operation, not a zero assignment
- `unsafe-exit` is the explicit exception to final safing

If you write tests with that model in mind, the DSL stays predictable.
