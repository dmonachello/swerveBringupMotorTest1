# DSL Condition Stability and Range Operators

## Purpose

Add two condition capabilities to the Robot Diagnostic Test DSL:

1. Optional condition stability filtering with `stable`
2. Numeric range operators with `between` and `outside`

These additions improve robustness when testing noisy real hardware while preserving the current live-rule execution model.

The DSL remains non-procedural. This change does not add loops, variables, callbacks, compound expressions, blocking waits, or general expression evaluation.

## 1. Feature Summary

### 1.1 `stable`

`stable` is an optional condition suffix.

It may be attached to any DSL clause that uses a condition:

```text
abort <condition> stable <seconds>
success <condition> stable <seconds>
require <condition> stable <seconds>
until <condition> stable <seconds>
```

The condition is considered logically true only after its raw condition has remained continuously true for at least the specified duration.

Example:

```text
require "FALCON 9".velocity > 100 stable 0.100
```

This means the raw condition:

```text
"FALCON 9".velocity > 100
```

must remain true continuously for `0.100` seconds before the `require` becomes satisfied.

`stable` modifies condition truth, not clause priority or phase order.

### 1.2 `between`

`between` checks whether a numeric signal is inside an inclusive numeric range.

```text
require encoder1.position between 10 20
```

Meaning:

```text
encoder1.position >= 10
encoder1.position <= 20
```

Both endpoints are included.

### 1.3 `outside`

`outside` checks whether a numeric signal is outside an inclusive numeric range.

```text
abort motor1.current outside 0 40
```

Meaning:

```text
motor1.current < 0
motor1.current > 40
```

Values exactly equal to the endpoints are considered inside the range, not outside.

## 2. Goals

This feature should support:

- switch debounce
- operator button confirmation
- noisy analog sensor validation
- noisy velocity or current filtering
- transient spike rejection
- readable numeric range checks
- bounded tests that are less sensitive to one-tick glitches

## 3. Non-Goals

This feature does not add:

```text
and
or
not
if
else
while
for
```

It does not add nested expressions:

```text
require (encoder1.position > 10)
```

It does not add compound expressions:

```text
require velocity > 100 and current < 20
```

It does not add mutable variables, callbacks, procedural waits, or a general-purpose expression evaluator.

## 4. Syntax

### 4.1 Existing Condition Forms

Existing forms remain valid:

```text
device.signal > literal
device.signal >= literal
device.signal < literal
device.signal <= literal
device.signal == literal
device.signal != literal
device.signal
```

Bare `device.signal` remains valid only for boolean signals.

### 4.2 Stable Condition Suffix

New optional suffix:

```text
<condition> stable <seconds>
```

Examples:

```text
require controller0.A stable 0.100
abort "FALCON 9".current > 40 stable 0.250
success limit1.pressed stable 0.050
until limit1.pressed stable 0.050
```

Rules:

- `seconds` is a positive numeric literal
- authoring unit is seconds
- `stable` appears at the end of the condition
- at most one `stable` suffix is allowed per condition

Invalid examples:

```text
require controller0.A stable 0
require controller0.A stable -0.1
require controller0.A stable 0.1 stable 0.2
```

### 4.3 Range Conditions

New numeric-only condition forms:

```text
device.signal between <low> <high>
device.signal outside <low> <high>
```

Examples:

```text
require encoder1.position between 10 20
abort motor1.current outside 0 40
```

Rules:

- `low` and `high` are numeric literals
- `low <= high`
- these operators are valid only on numeric signals

### 4.4 Stable Range Conditions

`stable` may also modify range conditions:

```text
require encoder1.position between 10 20 stable 0.100
abort motor1.current outside 0 40 stable 0.250
```

## 5. Condition Model

Each authored condition has two conceptual layers:

1. Raw condition
2. Effective condition

The raw condition is the immediate boolean result for the current tick.

The effective condition is:

- the raw result directly, when no `stable` suffix is present
- the stability-filtered result, when `stable` is present

Examples of raw conditions:

```text
controller0.A
"FALCON 9".current > 40
encoder1.position between 10 20
```

Clause behavior such as `abort`, `success`, `require`, and `until` uses the effective condition result.

## 6. Stable Filter Semantics

### 6.1 Basic Behavior

If no `stable` suffix is present, the effective condition equals the raw condition.

If `stable <seconds>` is present, the runtime tracks continuous raw-true duration for that condition.

The effective condition becomes true only when the raw condition has been continuously true for at least the stable duration.

### 6.2 Reset Behavior

When the raw condition transitions from false to true, stability timing begins.

While the raw condition remains true, elapsed stable time increases.

If the raw condition becomes false before the stable duration is reached:

- the stable timer resets
- elapsed stable time resets to zero
- the effective condition is false

If the raw condition becomes false after the stable duration had already been reached:

- the stable timer resets
- elapsed stable time resets to zero
- the effective condition becomes false again

Exception:

- a `require` that has already latched satisfied remains latched satisfied after that point, consistent with existing `require` semantics

### 6.3 Timing Basis

The DSL authors stable durations in seconds.

Runtime implementations may internally use either:

- absolute time in seconds
- equivalent tick-based accumulation

The externally visible semantics must match authored seconds.

The implementation must not allocate a blocking timer per rule.

## 7. Per-Clause Semantics

### 7.1 `require`

Without `stable`:

```text
require velocity > 100
```

The requirement latches as soon as the raw condition is true on any tick.

With `stable`:

```text
require velocity > 100 stable 0.100
```

The requirement latches only after the raw condition has remained true continuously for at least `0.100` seconds.

Once latched, existing `require` behavior remains unchanged.

### 7.2 `abort`

Without `stable`:

```text
abort current > 40
```

The test fails as soon as the raw condition is true.

With `stable`:

```text
abort current > 40 stable 0.250
```

The test fails only after the raw condition has remained true continuously for at least `0.250` seconds.

This allows short spikes to be ignored.

### 7.3 `success`

Without `stable`:

```text
success controller0.A
```

The test passes as soon as the raw condition is true.

With `stable`:

```text
success controller0.A stable 0.100
```

The test passes only after the raw condition has remained true continuously for at least `0.100` seconds.

This allows intentional operator confirmation rather than accidental taps.

### 7.4 `until`

Without `stable`:

```text
until limit1.pressed
```

Normal stop begins as soon as the raw condition is true.

With `stable`:

```text
until limit1.pressed stable 0.050
```

Normal stop begins only after the raw condition has remained true continuously for at least `0.050` seconds.

This is useful for switch-based termination and noisy threshold crossings.

A stable timer condition is allowed:

```text
until timer.elapsed >= 2.0 stable 0.100
```

Because `timer.elapsed >= 2.0` remains true once crossed, this is effectively a delayed stop. It is legal for consistency, but is expected to be uncommon.

## 8. Tick Processing

Current runtime order:

```text
1. apply all set
2. sample all condition signals
3. latch require
4. evaluate abort
5. evaluate success
6. evaluate until
```

New runtime order:

```text
1. apply all set
2. sample all condition signals
3. evaluate raw conditions
4. update stable filters
5. latch require
6. evaluate abort
7. evaluate success
8. evaluate until
```

Priority remains unchanged:

```text
abort > success > until
```

Important rule:

`require` latching still happens before `abort`, `success`, and `until` evaluation on the same tick.

The only change is that a condition with `stable` does not become logically true until its stable filter is satisfied.

## 9. Validation Rules

The parser or compiler must reject:

```text
stable 0
stable -1
```

The parser or compiler must reject range expressions where:

```text
low > high
```

The parser or compiler must reject `between` or `outside` on non-numeric signals.

The parser or compiler must reject bare numeric signal usage:

```text
require encoder1.position
```

Existing rule remains unchanged: bare signal conditions are only valid for boolean signals.

The parser or compiler should reject malformed range forms such as:

```text
require encoder1.position between
require encoder1.position outside 10
require encoder1.position between 10 controller0.A
```

## 10. Diagnostics and Reporting

For each condition using `stable`, runtime diagnostics should expose at least:

- raw condition value
- stable elapsed time
- stable target time
- stable satisfied flag

For latched `require` conditions, diagnostics should also make the latched state visible.

Example:

```text
condition: "FALCON 9".current > 40 stable 0.250
raw: true
stableElapsed: 0.120
stableTarget: 0.250
stableSatisfied: false
```

This is important for debugging noisy sensors, debounced inputs, and confusing pass or fail outcomes.

## 11. Internal Representation Guidance

A normalized condition should retain authored condition intent.

Conceptually it may need to represent:

- reference
- operator kind
- literal or range bounds
- optional stable duration

Stable runtime progress state should not be treated as authored DSL data.

Runtime-only state may include fields such as:

```text
lastRawValue
stableStartSec
stableElapsedSec
stableSatisfied
```

or equivalent tick-count fields.

This section is guidance, not a wire-format mandate.

## 12. Recommended Implementation Order

1. Add parser support for `between`, `outside`, and optional trailing `stable <seconds>`.
2. Extend normalized condition representation to preserve the authored condition shape.
3. Add validator rules for positive stable durations, numeric-only range operators, and `low <= high`.
4. Add runtime stable-filter evaluation.
5. Add unit tests for stable true, stable false, reset-on-false, and require latch behavior.
6. Add diagnostics for stable filter status.
7. Update user-facing documentation and examples.

## 13. Open Questions

### 13.1 Should stable durations use seconds only?

Recommendation:

Yes.

Do not add `ms` syntax in this version. Keep authored durations aligned with `timer.elapsed`.

### 13.2 Should stable be allowed on timer conditions?

Recommendation:

Yes.

It is usually unnecessary, but it keeps the rule model uniform.

### 13.3 Should stable state be reset when a `require` has already latched?

Recommendation:

The stable filter state may reset normally, but the `require` latch must remain satisfied once latched.

The important externally visible rule is that latched `require` behavior remains unchanged.

### 13.4 Should `between` and `outside` be allowed on boolean signals?

Recommendation:

No.

Range operators are numeric only.

### 13.5 Are range endpoints inclusive?

Recommendation:

Yes.

`between low high` is inclusive at both ends.

`outside low high` excludes both endpoints.

That rule should remain explicit in the user guide and examples.

## 14. Summary

This feature keeps the DSL small while improving real-world robustness:

- `stable` filters noisy truth transitions without changing clause priority
- `between` and `outside` improve readability for numeric checks
- `require` remains latched evidence
- `abort`, `success`, and `until` remain live-rule decisions
- no procedural or compound-expression features are introduced

## Appendix A. Detailed DSL Examples

### A.1 Motor Spin Acceptance With Noise-Tolerant Velocity and Overcurrent Filtering

```text
test "falcon_spin_acceptance"

device "FALCON 9"

main:
    set "FALCON 9".output = 0.18

    abort "FALCON 9".current_actual outside 0 35 stable 0.200
    abort "FALCON 9".temperature outside 0 85 stable 0.200

    until timer.elapsed >= 2.5

    require "FALCON 9".velocity_actual > 120 stable 0.100
    require "FALCON 9".current_actual between 0.5 20 stable 0.100
```

Purpose:

- Verify that a motor spins up and sustains a plausible operating region.

Why it uses the new features:

- `outside 0 35 stable 0.200` rejects brief current spikes while still failing sustained overcurrent.
- `between 0.5 20 stable 0.100` requires current to enter and hold a believable loaded range.
- `velocity_actual > 120 stable 0.100` prevents one noisy fast sample from counting as proof.

### A.2 Debounced Limit-Switch Stop With Operator Cancel

```text
test "limit_seek_with_debounce"

device "SPARKMAX/NEO 25"
device "lmtSw0"
device "controller0"

main:
    set "SPARKMAX/NEO 25".output_percent_cmd = 0.12

    abort controller0.B stable 0.100
    abort "SPARKMAX/NEO 25".current_actual outside 0 30 stable 0.150

    success lmtSw0.pressed stable 0.050

    require "SPARKMAX/NEO 25".velocity_actual > 40 stable 0.100
```

Purpose:

- Drive toward a limit switch, stop on a debounced hit, and allow intentional operator cancel.

Why it uses the new features:

- `success lmtSw0.pressed stable 0.050` debounces the switch before declaring success.
- `abort controller0.B stable 0.100` requires a deliberate cancel press rather than a tap.
- `abort current_actual outside 0 30 stable 0.150` tolerates short load spikes during contact.

### A.3 Encoder Window Verification With Inner Proof Band and Outer Fail Band

```text
test "elevator_encoder_window_check"

device "elevatorMotor"
device "elevatorEncoder"

main:
    set elevatorMotor.output = 0.10

    abort elevatorEncoder.position outside 90 130 stable 0.050
    abort timer.elapsed >= 4.0

    until timer.elapsed >= 2.0

    require elevatorEncoder.position between 100 120 stable 0.150
    require elevatorMotor.current_actual between 0.5 18 stable 0.100
```

Purpose:

- Confirm that an encoder enters and stays within an acceptable travel window while remaining electrically plausible.

Why it uses the new features:

- `between 100 120 stable 0.150` defines the narrow proof window.
- `outside 90 130 stable 0.050` defines a wider guard band that fails clear excursions.
- The stable suffix prevents threshold jitter from causing flapping pass or fail behavior.

### A.4 Operator-Confirmed Sensor Test With Intentional Press-and-Hold

```text
test "operator_confirmed_sensor_check"

device "controller0"
device "limit1"

main:
    success controller0.A stable 0.150
    abort controller0.B stable 0.150
    abort timer.elapsed >= 10.0

    require limit1.pressed stable 0.050
```

Purpose:

- Let an operator verify a physical sensor and explicitly confirm or cancel the test.

Why it uses the new features:

- `success controller0.A stable 0.150` requires an intentional confirmation press.
- `abort controller0.B stable 0.150` applies the same intentional-hold rule to cancel.
- `require limit1.pressed stable 0.050` debounces the sensed event before it counts as evidence.

### A.5 Joystick-Driven Manual Exercise With Stable Stop Region

```text
test "joystick_drive_to_safe_zone"

device "armMotor"
device "controller0"
device "armEncoder"

main:
    set armMotor.output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0

    abort controller0.B stable 0.100
    abort armMotor.current_actual outside 0 25 stable 0.150
    abort armEncoder.position outside -15 95 stable 0.050

    until armEncoder.position between 40 50 stable 0.200

    require armEncoder.position between 10 80 stable 0.050
```

Purpose:

- Let the operator manually drive a mechanism into a target zone while preserving safety bounds.

Why it uses the new features:

- `until armEncoder.position between 40 50 stable 0.200` requires the mechanism to remain in the target zone rather than merely crossing it.
- `abort armEncoder.position outside -15 95 stable 0.050` protects against sustained overtravel.
- `require armEncoder.position between 10 80 stable 0.050` proves meaningful motion inside a reasonable operating region.
