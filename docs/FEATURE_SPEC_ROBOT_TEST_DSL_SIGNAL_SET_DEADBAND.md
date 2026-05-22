SPEC_STATUS: IMPLEMENTED

# Robot Test DSL Signal-Set Deadband Feature Spec

Note: This spec was created with pi.

Note: This feature implementation was also done with pi.

## 1. Purpose

Purpose: define the requirements, design, and implementation plan for adding
optional deadband behavior to signal-driven Robot Test DSL `set` statements.

This feature extends the existing signal-set capability:

```text
set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0
```

and is now implemented in the host compiler/validator/serializer, Java runtime,
and example DSL content in this repo.

with an optional deadband clause:

```text
set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
```

The immediate use case is joystick-driven bring-up where small controller noise
or stick drift should not command unintended motor output.

## 2. Problem

The current signal-set feature lets one readable numeric signal drive one
writable numeric signal with explicit scaling and fallback behavior.

It does not let the test author suppress small-magnitude source values near
zero.

That causes two practical issues:

- small controller drift may produce unintended output
- authors must currently solve deadband outside the DSL runtime

The DSL should support this in an explicit, test-authored way.

## 3. Goals

- Add optional deadband to signal-driven `set` statements.
- Keep existing literal and signal-set syntax backward compatible.
- Keep the feature explicit and narrow.
- Apply deadband before scaling.
- Preserve current fallback behavior for unavailable sources.
- Keep host compiler, validator, normalized JSON, and Java runtime aligned.
- Keep first-pass semantics simple and deterministic.

## 4. Non-Goals

This feature does not add:

- general arithmetic expressions
- clamp syntax
- post-deadband rescaling to preserve full output span
- multi-source mixing
- user-defined transforms
- per-device implicit deadband defaults
- special controller-only syntax

## 5. User-Facing Requirements

### 5.1 Supported Syntax

Existing forms remain valid:

```text
set motor.output = 0.15
set motor.output = controller0.leftY scaled 0.25 default 0.0
```

New form:

```text
set motor.output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
```

### 5.2 Deadband Semantics

For a signal-driven `set` with source value `x`:

1. If the source is unavailable, use the existing phase-specific fallback rules.
2. If the source is available and `deadband` is present:
   - if `abs(x) < deadband`, use `0.0`
   - otherwise use `x`
3. Multiply the result by `scale`.
4. Validate the resolved target-domain value.
5. Write the target signal.

Important:

- deadband applies only when a source value exists
- deadband is applied before scaling
- deadband does not modify fallback/default behavior
- deadband does not change literal `set` behavior

### 5.3 First-Pass Boundary Rule

The first pass uses zeroing deadband only.

That means values outside the deadband are not remapped or rescaled.

Example with `deadband 0.08`:

- `0.03` becomes `0.0`
- `-0.05` becomes `0.0`
- `0.10` remains `0.10`
- `-0.40` remains `-0.40`

## 6. Syntax Design

### 6.1 Grammar Shape

Signal-driven set syntax becomes:

```text
set <target> = <source> [deadband <number>] scaled <number> default <value>
```

Rules:

- `deadband` is optional
- `scaled` remains required for signal-driven writes
- `default` remains required for signal-driven writes
- `deadband` may appear only once
- `deadband` appears before `scaled`

### 6.2 Examples

No deadband:

```text
set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0
```

With deadband:

```text
set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
```

Reverse direction with deadband:

```text
set "FALCON 9".output = controller0.leftY deadband 0.05 scaled -0.20 default 0.0
```

## 7. Validation Requirements

Host-side validation must continue to enforce all existing signal-set rules.

For deadband specifically:

- deadband must be numeric when present
- deadband must satisfy `0.0 <= deadband <= 1.0`
- deadband is only valid on signal-driven `set`
- deadband is not allowed on literal-only `set`

Validation must also preserve existing checks for:

- declared target device
- declared source device unless built in
- writable numeric target
- readable numeric source
- source device restrictions
- required numeric scale
- required numeric default
- default target-domain range validity

## 8. Normalized JSON Design

### 8.1 Model Change

Signal-driven `set` statements gain an optional `deadband` field.

Example:

```json
{
  "id": "set_1",
  "text": "set \"FALCON 9\".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0",
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
  "deadband": 0.08,
  "scale": 0.25,
  "defaultLiteral": {
    "value": 0.0,
    "valueType": "number"
  }
}
```

### 8.2 Compatibility Rules

- `deadband` is optional
- payloads without `deadband` remain valid
- literal-only `set` payloads remain unchanged
- `literal` and `source` remain mutually exclusive

## 9. Runtime Design

### 9.1 Java Runtime Behavior

Robot-side execution must preserve current runtime flow for signal-set
statements:

1. resolve source availability
2. apply fallback behavior when unavailable
3. when available, optionally apply deadband
4. apply scale
5. perform range checks
6. write target

### 9.2 Phase Behavior

Deadband does not alter phase-specific unavailable-source behavior.

Current behavior remains:

- `init`: unavailable source fails startup
- `main`: unavailable source uses authored default
- `close`: unavailable source skips the signal-driven write

When the source is available, deadband applies in all three phases.

### 9.3 Domain Rules

Deadband acts in the source domain.

For controller-like source signals this means:

- deadband is evaluated against the raw numeric source value returned by the
  runtime device signal path
- the post-deadband result is then multiplied by `scale`

Range checking remains on the final resolved target value after scaling.

### 9.4 No Implicit Clamping

First-pass runtime behavior remains:

- no silent clamping
- no silent saturation
- out-of-range resolved target values remain runtime errors

## 10. Implementation Requirements

### 10.1 Python Host Model

Update:

- `tools/common/robot_test_dsl/model.py`

Add optional field to `RobotTestDslSetStatement`:

- `deadband: Optional[float] = None`

### 10.2 Python Serializer

Update:

- `tools/common/robot_test_dsl/serializer.py`

Requirements:

- deserialize `deadband` into the in-memory model
- serialize `deadband` when present
- preserve backward compatibility when absent

### 10.3 Python Compiler

Update:

- `tools/common/robot_test_dsl/compiler.py`

Requirements:

- parse existing signal-set syntax unchanged
- parse optional `deadband <number>` before `scaled`
- populate normalized set statement `deadband` when present
- preserve authored source text in `text`

### 10.4 Python Validator

Update:

- `tools/common/robot_test_dsl/validator.py`

Requirements:

- reject non-numeric deadband
- reject deadband values outside `[0.0, 1.0]`
- reject deadband on literal-only `set`
- preserve all current signal-set validations

### 10.5 Java Normalized Model

Update:

- `src/main/java/frc/robot/tests/dsl/DslModels.java`

Requirements:

- add optional `Double deadband` to `DslSetStatement`
- keep JSON mapping compatible with absent field

### 10.6 Java Runtime

Update:

- `src/main/java/frc/robot/tests/dsl/DslBringupTest.java`

Requirements:

- when a source value is available, apply optional deadband before scaling
- keep fallback behavior unchanged when source is unavailable
- keep existing result/status behavior unchanged except for the resolved value
- continue enforcing target-domain range checks after scaling

Recommended helper:

```text
applyDeadband(value, deadband)
```

Behavior:

- if `deadband` is absent, return value unchanged
- if `abs(value) < deadband`, return `0.0`
- otherwise return value unchanged

## 11. Testing Requirements

### 11.1 Python Tests

Add or update tests for:

- compile signal-set without deadband
- compile signal-set with deadband
- serializer round-trip with deadband
- validator accepts valid deadband
- validator rejects negative deadband
- validator rejects deadband greater than `1.0`
- backward compatibility for existing payloads

### 11.2 Java Tests

Add or update tests for:

- source inside deadband resolves to `0.0`
- source outside deadband resolves normally
- deadband is applied before scaling
- unavailable source still uses existing fallback logic
- old signal-set behavior without deadband remains unchanged
- out-of-range post-scale value still fails as before

## 12. Documentation Requirements

Update:

- `docs/FEATURE_SPEC_ROBOT_TEST_DSL_SIGNAL_SET.md`
- `docs/USER_GUIDE_ROBOT_TEST_DSL.md`
- example DSL files as appropriate

Documentation must state:

- syntax
- source-domain semantics
- pre-scale application order
- unchanged fallback behavior
- backward compatibility

## 13. Backward Compatibility

The feature must be additive.

Required compatibility:

- literal `set` syntax unchanged
- existing signal-set syntax unchanged
- existing normalized payloads without `deadband` remain valid
- existing tests without deadband behave exactly as before

## 14. Tradeoffs

Adding optional deadband solves a real bring-up problem while keeping the DSL
small and explicit.

Tradeoffs:

- authors still cannot express clamp or remap behavior
- zeroing deadband is simpler but less expressive than rescaled deadband
- explicit syntax is slightly more verbose but much safer and clearer

## 15. Future Extensions

Possible future work:

- explicit clamp syntax
- rescaled deadband semantics
- named transforms
- per-signal transform chaining
- profile-defined reusable transform presets

## 16. Definition of Done

The feature is done when:

- the DSL accepts optional `deadband` in signal-driven `set`
- normalized JSON preserves `deadband`
- host validation enforces deadband bounds
- Java runtime applies deadband before scaling
- existing behavior without deadband is unchanged
- unit tests cover parse, validate, serialize, and runtime behavior
- user-facing docs and examples are updated

