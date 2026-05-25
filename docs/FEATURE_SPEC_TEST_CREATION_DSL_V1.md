SPEC_STATUS: NOT_IMPLEMENTED

# Feature Spec: Test Creation DSL V1

## Purpose

Define a device-centric DSL for declaring bringup tests without requiring direct JSON editing.

This spec defines test declaration syntax and test-definition semantics only.

## Scope

Includes:

- One unified DSL test model
- Test object structure
- Device binding and pseudo-device lifecycle
- Signal reference syntax
- Test-wide input binding syntax
- Command semantics
- Stop and expectation semantics
- Validation rules

Excludes:

- Execution engine behavior beyond declaration-time semantics
- Staged or multi-step execution
- Provider or hardware API details
- Network transport, dashboard, or UI behavior
- Logging and report rendering
- E-stop or interrupted-run reporting surfaces

## Goals

- Keep the test model device-centric and internally consistent
- Replace the old test-type split with one DSL model
- Eliminate free-floating signal namespaces
- Make expansion behavior deterministic
- Separate configured devices from test-local pseudo-devices
- Provide strict validation for ambiguous or unsafe test definitions

## Non-Goals

- Redesign the existing robot-side runtime
- Define signal provider implementations
- Replace the current persisted schema in this spec
- Add arbitrary pseudo-device types in v1
- Support staged procedures or deadband sweep in v1

## Core Model

- There is one DSL test model for v1.
- All signals belong to device types.
- All signal references resolve through device instances.
- There are no free-floating signals.
- Quotes are lexical only. They allow spaces or special characters in names and do not change meaning.
- Quoted and unquoted names both refer to device instances.
- Tests are flat single-body definitions in v1.
- V1 does not define separate test types such as `composite`, `joystick`, `button`, `deadbandSweep`, or `deviceAction`.
- Old functionality must be expressed through the DSL constructs defined here, not through type-specific behavior.

Examples:

- `lmtSw1.pressed`
- `"lmtSw1".pressed`
- `FALCON9.velocity_actual`
- `"FALCON 9".current_actual`

## Device Model

### Configured Devices

Configured devices come from the active profile in `bringup_system.json`.

These devices are added to a test by binding to an existing configured device instance:

```text
device add "<name>"
device add "<name>" role primary
device add "<name>" role observer
```

Rules:

- `device add` binds only to an existing configured device instance.
- `device add` with an unknown name is an error.
- `device add` does not create new hardware device instances.

### Test-Local Pseudo-Devices

Test-local pseudo-devices are created explicitly:

```text
device create "<name>" type TestTimer
```

Rules:

- `device create` creates a test-local pseudo-device instance.
- V1 supports only `TestTimer`.
- Creating an unsupported pseudo-device type is an error.
- A created pseudo-device name must not collide with:
  - another created pseudo-device
  - a configured device name already bound into the test
  - the reserved built-in device `timer`

### Built-In Devices

Each test automatically includes:

```text
timer   type TestTimer
```

Rules:

- `timer` is reserved.
- `timer` is always available.
- `timer` cannot be redefined, rebound, or shadowed.

## Device Roles

### Primary

Configured devices added with:

```text
device add "<name>"
```

default to:

```text
role primary
```

Primary devices participate in bare unqualified signal expansion.

### Observer

Configured devices added with:

```text
device add "<name>" role observer
```

do not participate in bare signal expansion.

Observer devices may be referenced only through explicit dotted references.

Examples:

- `device add "FALCON 9"`
- `device add "lmtSw1" role observer`
- `device add "encoder1" role observer`

## Signals

### Forms

Signals are referenced as:

```text
<signal>
<device_name>.<signal>
```

`<device_name>` may be quoted when needed.

Examples:

- `velocity_actual`
- `"FALCON 9".current_actual`
- `lmtSw1.pressed`
- `timer.elapsed`

### Resolution Rules

#### Explicit Dotted References

Any dotted reference:

```text
<device_name>.<signal>
```

always means a device-instance reference and never expands.

Examples:

- `lmtSw1.pressed`
- `"FALCON 9".current_actual`
- `timer.elapsed`

#### Bare Unqualified References

A bare unqualified signal:

```text
<signal>
```

expands only across primary devices in the test.

Observer devices do not participate in expansion.

Expansion examples:

- `velocity_actual > 100`
- `current_actual > 0.5`
- `output_percent_cmd`

Non-expanding examples:

- `timer.elapsed >= 4.0`
- `lmtSw1.pressed == true`
- `"FALCON 9".current_actual > 30`

### Unsupported Expanded Signals

If an unqualified signal expands across primary devices and one or more primary devices do not support that signal, validation fails.

This is an error, not a runtime false.

## Time Model

`timer.elapsed` is the number of seconds since test start, measured using monotonic test runtime time.

Additional timers may be created with:

```text
device create "timer2" type TestTimer
```

and are referenced as:

```text
timer2.elapsed
```

## Position Model

For any device type that exposes position:

- `position_actual` is the device's raw position signal
- `position_delta` is `position_actual - position_at_test_start`

Initialization:

- `position_delta = 0` at test start

Using `position_actual` or `position_delta` on a device that does not support position is an error.

## Test Structure

Historical note:

- The interactive `test create` / `device add` / `input bind` command shape below is preserved as a historical design record.
- Current implementation uses DSL source text plus `test import` / `test export` / `test validate`.

A test is defined using:

```text
test create <name>

device add "<device_name>" [role primary|observer]
device create "<device_name>" type TestTimer

input bind <input_source> -> <signal> [scale <number>] [deadband <number>]
input bind <input_source> -> <signal> when-pressed <value> [when-released <value>]

command <signal> = <value>

until <condition>
expect <condition>
success <condition>
abort <condition>

passive true|false
manual_stop true|false
enabled true|false

exit
```

Only `test create <name>` is required to declare a test object.

Additional rules for runnable tests are defined below.

V1 test bodies are flat. There are no `step` blocks or staged sub-sections in this release.

## Input Bindings

Input bindings map live operator input to writable command signals.

Forms:

```text
input bind <input_source> -> <signal>
input bind <input_source> -> <signal> scale <number> deadband <number>
input bind <input_source> -> <signal> when-pressed <value> [when-released <value>]
```

Examples:

- `input bind xbox1.leftY -> output_percent_cmd`
- `input bind xbox1.leftY -> output_percent_cmd scale -1.0 deadband 0.12`
- `input bind xbox1.A -> output_percent_cmd when-pressed 0.25 when-released 0.0`

Rules:

- Input bindings are test-wide.
- Input bindings target writable command signals only.
- An input binding may use an unqualified signal, which expands across primary devices.
- All targeted devices must support the bound command signal.
- Input shaping is optional. Defaults should be applied by the implementation when shaping terms are omitted.
- V1 does not support step-local or staged input bindings.

## Conditions

Conditions use the form:

```text
<signal> <operator> <value>
```

Allowed operators:

```text
>
>=
<
<=
==
!=
```

Boolean values must be explicit:

```text
== true
== false
```

Examples:

- `velocity_actual > 100`
- `current_actual > 0.5`
- `lmtSw1.pressed == true`
- `timer.elapsed >= 4.0`

## Commands

Commands assign values to writable command signals:

```text
command <signal> = <value>
```

Examples:

- `command output_percent_cmd = 0.25`
- `command "FALCON 9".output_percent_cmd = 0.25`

Rules:

- `command` writes a latched setpoint at test start.
- The runtime holds that setpoint until stop or shutdown.
- `command` is not a momentary pulse.
- An unqualified command applies to all primary devices.
- All targeted primary devices must support the command signal.
- Commanding a read-only signal is an error.
- Commanding an unsupported signal on any targeted device is an error.

## Stop and Result Conditions

### abort

```text
abort <condition>
```

Meaning:

- stop immediately
- result = FAIL
- `expect` is not evaluated

Multiple `abort` lines are OR'd.

### success

```text
success <condition>
```

Meaning:

- stop immediately
- result = PASS
- `expect` is not evaluated

Multiple `success` lines are OR'd.

Constraint:

- `success` should be used only when the condition itself proves success.
- `success timer.elapsed >= ...` is allowed but should raise a warning.

### until

```text
until <condition>
```

Meaning:

- normal stop condition
- stop and evaluate `expect`

Multiple `until` lines are OR'd.

### expect

```text
expect <condition>
```

Meaning:

- evaluated only when the test stops via `until`
- all `expect` conditions must be true

Multiple `expect` lines are AND'd.

## Evaluation Order

Within each loop:

1. Sample all signals.
2. Evaluate `abort`.
3. Evaluate `success`.
4. Evaluate `until`.
5. If `until` matched, evaluate all `expect` conditions against the same sampled loop snapshot.

Priority:

```text
abort > success > until
```

If more than one condition becomes true in the same loop, priority decides the outcome.

## Runnable Test Requirements

### Required for Declaration

- `test create <name>`

### Required for Execution

A runnable test must satisfy all of the following:

- it must include at least one declared stop condition:
  - `abort`
  - `success`
  - `until`
- unless `manual_stop true`
- it must include at least one command or input binding unless `passive true`
- it must include device bindings if device signals are used

### passive

```text
passive true
```

means no command is required.

`passive` does not waive the declared stop-condition requirement.
`passive` also means no input binding is required.

### manual_stop

```text
manual_stop true
```

means a declared stop condition is not required.

`manual_stop` does not waive validation for device references, commands, or signal support.

## Validation Rules

Errors:

- unknown device in `device add`
- unknown signal
- explicit reference to a device not bound into the test
- device signal used without a bound device
- `expect` without `until`
- command on read-only signal
- unsupported command on a targeted device
- input binding on read-only signal
- unsupported input-bound signal on a targeted device
- unsupported expanded signal
- mixed primary-device support for an unqualified signal
- invalid operator
- ambiguous reference
- `device create` with unsupported type
- duplicate pseudo-device name
- collision with reserved built-in `timer`

Warnings:

- `until` without `expect`
- `success` using `timer.elapsed`
- no declared stop condition when `manual_stop true`

## Examples

### Simple Manual Run

```text
test create manual_spin
device add "FALCON 9"

input bind xbox1.leftY -> output_percent_cmd scale -1.0 deadband 0.12

manual_stop true
enabled true
exit
```

### Observed Timed Test

```text
test create spin_4s
device add "FALCON 9"

command output_percent_cmd = 0.25

until timer.elapsed >= 4.0

expect velocity_actual > 100
expect current_actual > 0.5

abort current_actual > 30

exit
```

### Move 25 Rotations

```text
test create move_25_rotations
device add "FALCON 9"

command output_percent_cmd = 0.2

until position_delta > 25.0

expect velocity_actual > 50
expect current_actual > 0.5

abort current_actual > 30

exit
```

### Limit Switch Stop

```text
test create to_limit
device add "FALCON 9"
device add "lmtSw1" role observer

command output_percent_cmd = 0.2

until lmtSw1.pressed == true

expect position_delta > 1.0

abort current_actual > 30

exit
```

### Limit Switch Must Not Trigger

```text
test create no_limit
device add "FALCON 9"
device add "lmtSw1" role observer

command output_percent_cmd = 0.2

until timer.elapsed >= 4.0

expect velocity_actual > 100

abort lmtSw1.pressed == true

exit
```

### External Encoder Validation

```text
test create external_encoder_test
device add "FALCON 9"
device add "encoder1" role observer

command "FALCON 9".output_percent_cmd = 0.25

until timer.elapsed >= 4.0

expect encoder1.position_delta > 1.0
expect "FALCON 9".current_actual > 0.5

exit
```

### Two Motors Same Behavior

```text
test create dual_spin
device add "FALCON 9"
device add "FALCON 10"

command output_percent_cmd = 0.25

until timer.elapsed >= 4.0

expect velocity_actual > 100

exit
```

### Per-Device Expectations

```text
test create dual_compare
device add "FALCON 9"
device add "FALCON 10"

command output_percent_cmd = 0.25

until timer.elapsed >= 4.0

expect "FALCON 9".velocity_actual > 100
expect "FALCON 10".velocity_actual > 200

exit
```

### Timeout as Failure

```text
test create must_hit_limit
device add "FALCON 9"
device add "lmtSw1" role observer

command output_percent_cmd = 0.2

success lmtSw1.pressed == true

abort timer.elapsed >= 10.0
abort current_actual > 30

exit
```

### Passive Sensor Test

```text
test create sensor_check
device add "encoder1" role observer

passive true

until timer.elapsed >= 5.0

expect encoder1.position_actual >= 0

exit
```

### Additional Timer

```text
test create staged_timeout
device add "FALCON 9"
device create "timer2" type TestTimer

command output_percent_cmd = 0.25

until timer.elapsed >= 4.0

expect velocity_actual > 100

abort timer2.elapsed >= 10.0

exit
```

## Implementation Notes

Purpose: Keep this spec aligned with the current layered architecture and existing test model.

- This DSL is a declaration layer, not a replacement for the execution engine.
- The parser and validator should resolve all device references before serialization.
- Expansion should be performed against the test's primary-device set only.
- Signal capability checks should occur during validation, not deferred to runtime where avoidable.
- V1 execution shape is a flat single-body test. Staged execution is deferred beyond this release.
- `timer` behavior belongs to the test-definition contract; interrupted-run rendering does not.

## Tradeoffs

- Requiring explicit observer roles keeps expansion deterministic, but adds authoring verbosity for sensor devices.
- Restricting `device create` to `TestTimer` keeps lifecycle simple in v1, but defers richer pseudo-device scenarios.
- Folding manual-input workflows into the DSL keeps the model unified, but requires input binding semantics in addition to latched startup commands.
- Treating unsupported expanded signals as errors avoids silent narrowing of intent at the cost of stricter authoring.

## Future Extensions

Features intentionally pushed beyond v1 are tracked in [FEATURE_SPEC_TEST_CREATION_DSL_POST_V1.md](./FEATURE_SPEC_TEST_CREATION_DSL_POST_V1.md).

Known post-v1 areas include:

- Explicit `step` blocks
- Staged procedures
- Deadband sweep replacement
- Step-local `abort`
- Additional approved pseudo-device types
- Richer condition operators such as ranges or tolerances

