# Robot Test DSL Signal Set Feature Spec

## 1. Purpose

Purpose: Define a first-pass extension that lets a DSL test command one signal
from another signal value.

The immediate use case is joystick-controlled motor bring-up:

```text
set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0
```

This lets a configured Xbox controller axis drive a known motor output while
the DSL still owns safety checks, stop conditions, and final safing.

## 2. Problem

The current DSL supports only literal writes:

```text
set "FALCON 9".output = 0.12
```

That is enough for fixed-output smoke tests, but it cannot express:

- operator-controlled motor speed
- sensor-following tests
- input-device-to-output diagnostic tests

Controller signals can be read in conditions today:

```text
require controller0.leftY > 0.5
```

They cannot be used as the value side of a `set`.

## 3. Goals

- Allow a writable signal to be driven from a readable signal.
- Keep the feature deterministic inside the existing per-tick engine order.
- Require explicit scaling for safety when writing motor output from an axis.
- Keep v0.3 behavior unchanged for existing literal `set` statements.
- Store the compiled form in normalized JSON.
- Validate source, generated JSON, device declarations, signal types, and
  write/read permissions before saving a test.

## 3.1 First-Pass Scope

First-pass implementation scope:

- allow any writable numeric target signal
- allow any readable numeric source signal
- use the source value exactly as exposed by the source device at runtime
- reject source signals from motor devices

Reason:

- the feature should work across the existing readable/writable metadata model
- the first pass should avoid open-loop feedback from motor telemetry
- no DSL-specific transform layer should be invented yet

## 4. Non-Goals

This first pass does not add:

- arithmetic expressions
- functions
- compound expressions
- signal inversion syntax beyond scaling with a negative factor
- deadband syntax
- clamping syntax
- unit conversion syntax
- multi-source mixing
- PID or closed-loop control

Those can be future extensions after the simple signal-to-signal path is
working.

## 5. Proposed Syntax

### 5.1 Literal Set

Existing syntax remains valid:

```text
set "FALCON 9".output = 0.12
```

### 5.2 Signal Set

New syntax:

```text
set <target_device>.<target_signal> = <source_device>.<source_signal>
    scaled <scale> default <default_value>
```

Example:

```text
set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0
```

Meaning:

- read `controller0.leftY`
- multiply by `0.25`
- write the result to `"FALCON 9".output`
- repeat every tick when used in `main`

If the source value is unavailable:

- use `0.0` instead
- keep the test running
- issue rate-limited warnings that fallback is active

### 5.3 Required Scaling

For the first pass, `scaled <scale>` is required for signal-valued writes.

Reason:

- controller axes usually range from `-1.0` to `1.0`
- motor output also accepts that range
- requiring scale makes the author explicitly choose the maximum output

Example safe first-pass motor limit:

```text
scaled 0.25
```

Example reversed direction:

```text
scaled -0.25
```

### 5.4 Required Default

For the first pass, `default <default_value>` is required for signal-valued
writes.

Reason:

- controller and runtime inputs may be temporarily unavailable
- the DSL needs a deterministic fallback command value
- fallback behavior should be authored explicitly, not inferred implicitly

Example:

```text
default 0.0
```

## 6. Semantics

Signal-valued `set` follows the same phase rules as literal `set`.

In `init`:

- sample the source once
- if the source is available, compute the scaled value
- otherwise fail test startup
- write the target once

In `main`:

- sample the source every tick
- if the source is available, compute the scaled value every tick
- otherwise use the authored default value every tick
- write the target every tick

In `close`:

- sample the source once
- if the source is available, compute the scaled value
- otherwise skip the write
- write the target once

The normal final safe-state behavior is unchanged.

Using the default value does not change the test result by itself.

### 6.1 Phase Failure Rules

Source unavailable behavior by phase:

- `init`: fail test startup
- `main`: use the authored default value
- `close`: skip the signal-driven write

Startup failure status:

```text
Signal set source unavailable at startup: controller0.leftY
```

Close-phase source unavailability does not change the verdict.

## 7. Tick Order

The current main tick order is:

1. apply all `set`
2. sample signals
3. evaluate `abort`
4. evaluate `success`
5. evaluate `until`
6. update and latch `require`

Signal-valued `set` needs a source sample before the command write.

Proposed updated order:

1. sample source signals needed by signal-valued `set`
2. apply all `set`
3. sample condition signals
4. evaluate `abort`
5. evaluate `success`
6. evaluate `until`
7. update and latch `require`

This preserves the rule that command writes happen before condition evaluation.

SID_QUESTION: Should condition sampling reuse the source samples from step 1
when the same signal appears in a condition, or should conditions always sample
after command writes? First-pass recommendation: condition sampling should
happen after command writes, even if that means the same source signal may be
read twice in one tick.

## 8. Validation

Validation must reject a signal-valued `set` when:

- the target device is not declared
- the source device is not declared, unless it is built in
- the target device does not exist in the active profile
- the source device does not exist in the active profile
- the target signal is not writable
- the source signal is not readable
- the target value type is not `number`
- the source value type is not `number`
- the source device type is `motor`
- the scale is missing
- the scale is not numeric
- the default is missing
- the default is not numeric
- the absolute scale is greater than the configured maximum

First-pass maximum scale:

```text
1.0
```

This prevents accidental amplification above full command range.

Validation must also reject a signal-valued `set` when the authored default
value is outside the valid runtime range for the target signal.

SID_QUESTION: Should motor output targets require an even smaller default
maximum scale such as `0.5` unless an explicit unsafe opt-in is added?

## 9. Normalized JSON

The normalized JSON should distinguish literal writes from signal writes.

Existing literal set:

```json
{
  "id": "set_1",
  "text": "set \"FALCON 9\".output = 0.12",
  "target": {
    "device": "FALCON 9",
    "signal": "output",
    "text": "FALCON 9.output"
  },
  "literal": {
    "value": 0.12,
    "valueType": "number"
  }
}
```

Proposed signal set:

```json
{
  "id": "set_1",
  "text": "set \"FALCON 9\".output = controller0.leftY scaled 0.25 default 0.0",
  "target": {
    "device": "FALCON 9",
    "signal": "output",
    "text": "FALCON 9.output"
  },
  "source": {
    "device": "controller0",
    "signal": "leftY",
    "text": "controller0.leftY"
  },
  "scale": 0.25,
  "defaultLiteral": {
    "value": 0.0,
    "valueType": "number"
  }
}
```

Rules:

- `literal` and `source` are mutually exclusive.
- `scale` is required when `source` exists.
- `defaultLiteral` is required when `source` exists.
- old normalized payloads without `source` remain valid.

## 10. Java Runtime

Robot-side execution must:

- read the source signal through the same device signal path used by conditions
- use the exact source value returned by the source device
- multiply source by scale
- use the authored default value when the source is unavailable
- write the target signal through the existing write path
- apply normal final safing after test exit

Runtime unavailable-source behavior:

- result does not change by itself
- the runtime uses the authored default value
- a warning should identify target and source references
- warnings should be rate-limited so they do not spam the 20 ms loop

Example warning:

```text
Signal set fallback active: target=FALCON 9.output source=controller0.leftY default=0.0
```

First-pass warning cadence:

- emit once when fallback first becomes active
- re-emit no more often than once every 1 second while fallback remains active
- emit once when the source recovers

Fallback verdict behavior:

- fallback use is ignored for `abort` termination
- fallback use is ignored for `success` termination
- fallback use affects verdict only on normal `until` termination
- on normal `until` termination, the test fails if fallback is active at the
  final stop tick

## 10.1 Numeric Domain Rules

The runtime must reject signal-driven writes when the computed write value is
outside the valid domain of the target signal.

First-pass behavior:

- no runtime clamping
- no silent saturation
- out-of-range computed value is a runtime error
- out-of-range default value is a validation error

Example runtime error:

```text
Signal set produced out-of-range value: target=FALCON 9.output value=1.25
```

## 11. Host Compiler

The host compiler must parse both forms:

```text
set device.signal = value
set device.signal = device.signal scaled number default number
```

The compiler should preserve author text in normalized `text` fields so CLI
inspection shows exactly what was imported.

The host compiler and robot-side normalized model must both support:

- literal-valued `set`
- signal-valued `set`
- source reference
- scale
- default literal

## 12. User Guide Example

Example DSL:

```text
test "falcon9_xbox_leftY_drive"
device "FALCON 9"
device "controller0"

init:
    clear "FALCON 9".faults

main:
    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0
    abort "FALCON 9".current > 35
    abort "FALCON 9".temperature > 80
    abort controller0.B
    until timer.elapsed >= 5.0
    require controller0.A

close:
    clear "FALCON 9".faults
```

Meaning:

- left Y controls Falcon output up to 25 percent
- if the left Y source is unavailable, output falls back to `0.0`
- pressing B fails immediately
- pressing A at least once is required before the 5 second timer ends
- current and temperature still protect the motor
- final safing still returns motor output to `0.0`

## 13. Safety

Signal-driven motor output is higher risk than fixed-output tests.

Required safety rules:

- every motor signal-driven test should have an `until` time limit
- every motor signal-driven test should have a current `abort`
- every motor signal-driven test should have a temperature `abort`
- motor output signal sets must require explicit scale
- motor output signal sets must require an explicit default
- final safing must remain enabled by default

Recommended warnings:

- no `until` on a signal-driven motor test
- no current `abort` on a signal-driven motor test
- no temperature `abort` on a signal-driven motor test

Recommended first-pass authoring pattern:

```text
main:
    set "<motor>".output = <controller>.<axis> scaled <small_scale> default 0.0
    abort "<motor>".current > <current_limit>
    abort "<motor>".temperature > <temperature_limit>
    abort <controller>.B
    until timer.elapsed >= <seconds>
```

## 14. Tradeoffs

Keeping the first pass to `scaled` signal writes has a narrow implementation
surface and avoids creating a general expression language too early.

The tradeoff is that authors cannot directly express common input cleanup such
as deadband or clamp. Those can be added later with explicit syntax and clear
runtime semantics.

Requiring scale is slightly verbose, but it makes motor-output risk visible in
the source file.

Requiring a default adds more syntax, but it avoids hidden fallback behavior and
keeps loss-of-input handling explicit in the authored test.

Rejecting motor-device source signals is conservative, but it keeps the first
pass away from accidental feedback loops and leaves closed-loop semantics for a
future design.

## 15. Future Extensions

Potential extensions:

- optional `deadband <value>`
- optional `clamp <min> <max>`
- named transform profiles
- boolean-to-number mapping
- multiple Xbox signals: `X`, `Y`, bumpers, triggers, POV, stick buttons
- richer signal metadata for units and command ranges
- lint warnings for missing safety statements in motor-output tests
- device-specific transforms if direct device-exposed values are not enough
- future support for safe non-motor signal sources that need filtering

## 16. Acceptance Criteria

The feature is complete when:

- host compiler accepts signal-valued `set`
- host validator rejects invalid signal-valued `set`
- normalized JSON stores source and scale
- normalized JSON stores source, scale, and default literal
- robot runtime executes signal-valued `set` every tick
- robot runtime uses the authored default when source reads fail
- robot runtime emits rate-limited warnings while fallback is active
- robot runtime fails startup when an `init` signal source is unavailable
- robot runtime skips signal-driven `close` writes when the source is unavailable
- robot runtime rejects out-of-range computed target values
- host validator rejects motor-device source signals
- existing literal `set` tests continue to pass unchanged
- `falcon9_xbox_leftY_drive` imports and validates
- Java unit tests cover source unavailable, scaling, and normal safing
- Python DSL tests cover parsing, serialization, validation, and stale
  normalized payload detection
- user guide documents syntax, safety rules, and examples
