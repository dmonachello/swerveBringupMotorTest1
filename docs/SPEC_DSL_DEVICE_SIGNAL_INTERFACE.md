SPEC_STATUS: PARTIALLY_IMPLEMENTED

# DSL Device Signal Interface Spec

Purpose: define the boundary between snapshots, DSL-visible signals, and the per-device read/write contract used by robot diagnostic tests.

## 1. Scope

This spec covers only:

- robot-side snapshots
- the DSL-visible signal surface
- the device read/write contract used by DSL execution

This spec includes:

- current behavior
- current architectural problems
- target architecture
- migration steps

This spec does not define:

- CLI syntax
- UI layout or operator workflow
- NetworkTables publication format
- non-DSL reporting payloads outside the snapshot model

## 2. Goal

Purpose: make DSL execution use one well-defined device interface instead of multiple device-specific fallback paths.

Target outcome:

- every DSL-visible read goes through one per-device signal API
- every DSL-visible write goes through one per-device signal API
- snapshots remain for reporting and diagnostics
- snapshots are no longer the long-term fallback mechanism for DSL execution

## 3. Terms

### 3.1 Snapshot

A snapshot is a point-in-time diagnostic record for one robot-side device.

Snapshots are:

- produced by `DeviceUnit.snapshot()`
- robot-local
- intended for reporting, status, and UI/CLI visibility
- allowed to contain more information than the DSL surface

Snapshots are not the long-term execution interface for DSL evaluation.

### 3.2 DSL-visible signal

A DSL-visible signal is a named read or write endpoint intentionally exposed to test authors.

Examples:

- `FALCON 9.output`
- `FALCON 9.velocity`
- `controller0.leftY`
- `lmtSw0.pressed`
- `timer.elapsed`

DSL-visible signals are the stable contract for authored tests.

### 3.3 Device signal interface

The device signal interface is the per-device runtime API used by the DSL engine to:

- read signal values
- write signal values
- optionally clear writable/latched signals

## 4. Current State

Purpose: document how the system works today.

Current behavior is mixed.

### 4.1 Reads

Today, DSL reads come from more than one path:

1. `DeviceUnit.readDslSignal(signalName)` for some devices
2. central fallback logic in `DslBringupTest.readSignalValue(...)`
3. snapshot attachments such as:
   - `RevMotorAttachment`
   - `CtreMotorAttachment`
   - `LimitsAttachment`
4. device helper methods such as:
   - `getPositionRotations()`

Examples:

- Xbox controller inputs are device-native reads through `readDslSignal`
- motor velocity/current/temperature are currently read through central snapshot-based fallback logic
- limit switch `pressed` was originally inferred via snapshot/fallback behavior and later required a standalone runtime device

### 4.2 Writes

Today, DSL writes are also mixed.

The main example is:

- motor output writes are handled centrally in `DslBringupTest.writeTargetSignal(...)`
- this is currently device-type-aware logic in the DSL engine

### 4.3 Snapshots

Today, snapshots serve two roles:

1. their intended role:
   - reporting and diagnostics
2. an execution fallback role:
   - central DSL read logic extracts values from snapshot attachments

That second role is the architectural problem this spec addresses.

## 5. Current Problems

Purpose: explain why the current mixed design should be changed.

### 5.1 Central DSL runtime knows too much about device types

`DslBringupTest` currently knows about:

- motor telemetry attachments
- limit-switch attachment structure
- encoder behavior
- controller behavior through partial direct reads

That causes device-specific logic to accumulate in the DSL engine.

### 5.2 The execution path is not uniform

The current model mixes:

- direct device reads
- snapshot-derived reads
- ad hoc helper methods

This makes it harder to reason about:

- what the authoritative runtime signal source is
- where a new signal should be implemented
- how to debug signal resolution failures

### 5.3 Snapshots and execution are coupled

Snapshots should be free to evolve as reporting artifacts.

If DSL execution depends on snapshot structure:

- snapshot changes become execution changes
- reporting and execution cannot evolve independently

### 5.4 Adding new standalone device types is harder than it should be

Recent controller and limit-switch work showed the failure mode:

- config can describe a valid device
- DSL can reference the device
- runtime support still fails unless central logic and group construction both happen to understand it

That is a sign the execution contract is not explicit enough.

## 6. Design Principles

Purpose: define the rules for the target architecture.

### 6.1 One execution read path

All DSL-visible reads must go through a per-device signal API.

### 6.2 One execution write path

All DSL-visible writes must go through a per-device signal API.

### 6.3 Snapshots are for reporting

Snapshots remain useful, but their primary role is:

- diagnostics
- health/status reporting
- UI/CLI visibility

Snapshots should not be the long-term fallback path for DSL execution.

### 6.4 Small but sufficient DSL surface

The DSL surface should contain:

- stable
- test-relevant
- semantically clear

signals.

It should not expose every internal telemetry field just because that field exists.

### 6.5 Device-owned signal semantics

Each device implementation should own:

- what DSL-visible signals it supports
- how those signals are read
- how writable signals are applied

The DSL engine should evaluate conditions and lifecycle semantics, not device internals.

## 7. Target Architecture

Purpose: define the desired end state.

### 7.1 DeviceUnit execution interface

The robot-side device execution contract should be expanded to support DSL-visible signals directly.

Target shape:

```java
Object readDslSignal(String signalName)
boolean writeDslSignal(String signalName, Object value)
boolean clearDslSignal(String signalName)
```

Notes:

- `readDslSignal` returns `null` when unsupported or unavailable
- `writeDslSignal` returns `true` only when the device accepted the write
- `clearDslSignal` is for explicit clearable signals only

Exact return types may be refined later, but the contract must be explicit and device-owned.

### 7.2 DslBringupTest responsibilities

`DslBringupTest` should do only:

- test lifecycle
- condition evaluation
- phase ordering
- signal metadata checks
- run-status bookkeeping

`DslBringupTest` should not contain per-device telemetry extraction logic once migration is complete.

### 7.3 Snapshot responsibilities

Snapshots should provide:

- human/operator visibility
- machine-readable diagnostic reports
- detailed telemetry attachments
- post-run and live-state reporting

Snapshots should not be required for DSL signal evaluation.

## 8. Signal Surface Rules

Purpose: define what belongs on the DSL surface.

### 8.1 DSL-visible signals should be included when they are

- useful in test logic
- stable enough to document
- understandable to test authors
- meaningful for the device type

### 8.2 Signals should usually stay out of the DSL surface when they are

- only reporting notes
- low-level internal bookkeeping
- unstable vendor-specific artifacts
- redundant duplicates of clearer signals

### 8.3 Examples of good DSL-visible signals

- motor:
  - `output`
  - `velocity`
  - `current`
  - `temperature`
  - `position`
  - `faults`
- limit switch:
  - `pressed`
- controller:
  - `A`
  - `B`
  - `leftY`
  - `rightY`
- timer:
  - `elapsed`

### 8.4 Examples of values that may stay outside the DSL surface

- generic report `note` strings
- diagnostic suspicion scores
- raw attachment-only implementation fields
- every vendor-specific sticky-fault field unless intentionally normalized

## 9. Read Contract

Purpose: define the runtime rules for DSL reads.

### 9.1 Read success

A read succeeds when:

- the device exists in runtime
- the device supports the requested signal
- the signal value is currently available

### 9.2 Read unavailable

A read is unavailable when:

- the device does not support the signal
- the underlying resource is not created
- the signal cannot currently be sampled

Unavailable reads should be represented explicitly so fallback/default semantics remain controlled by the DSL engine, not hidden inside device code.

### 9.3 Boolean shortcut semantics

Bare boolean conditions such as:

```text
success lmtSw0.pressed
```

must remain valid.

That means `readDslSignal("pressed")` for a limit switch must return a boolean-compatible value.

## 10. Write Contract

Purpose: define the runtime rules for DSL writes.

### 10.1 Write success

A write succeeds when:

- the device exists in runtime
- the signal is writable
- the value is type-valid and range-valid
- the device accepted the command

### 10.2 Write failure

A write must fail explicitly when:

- the signal is unsupported
- the signal is read-only
- the value type is wrong
- the value is out of range
- the device rejects the write

The DSL engine should surface that failure directly in run status/details.

### 10.3 Range and type validation

Central metadata may still define:

- value type
- writable/readable
- clearable
- safe value

But the actual write is device-owned.

## 11. Clear Contract

Purpose: define how clearable signals should behave.

Some signals may support an explicit clear operation.

Examples:

- latched faults
- sticky flags
- device-specific resettable states

If a signal is clearable, the device implementation should own the clear behavior through the standardized clear contract.

## 12. Snapshot Model After Refactor

Purpose: keep snapshots useful after DSL execution stops depending on them.

Snapshots remain first-class for:

- `show devices`
- reports
- run summaries
- health views
- debugging

Snapshots may still include:

- attachments
- notes
- command-side telemetry such as `cmdDuty` or `appliedDuty`
- detailed fault structures

But those fields are reporting artifacts, not automatically part of the DSL language.

## 13. Migration Plan

Purpose: define a practical path from current mixed behavior to the target architecture.

### Phase 1: Freeze the target contract

- document the device-owned signal interface
- treat snapshot-backed DSL reads as legacy behavior

### Phase 2: Migrate standalone devices first

Migrate devices whose signals are clearly not snapshot-derived, such as:

- controllers
- standalone limit switches
- standalone external encoders

These should fully implement the device signal API.

### Phase 3: Migrate motor reads

Move motor DSL-visible reads into motor device implementations:

- `velocity`
- `current`
- `temperature`
- `position`
- `faults`

After this, `DslBringupTest` should stop reading those values from snapshot attachments.

### Phase 4: Migrate motor writes

Move writable signals such as:

- `output`

into device-owned write handlers.

After this, `DslBringupTest.writeTargetSignal(...)` should stop containing device-type-specific write branches.

### Phase 5: Remove legacy execution fallback

Once all DSL-visible signals are device-owned:

- remove snapshot-backed read fallback from `DslBringupTest`
- remove central device-type signal extraction branches

## 14. Failure Handling

Purpose: define how the runtime should behave when signal access fails.

### 14.1 Unsupported signal

- validation should reject it where possible
- runtime should still fail loudly if an invalid compiled test slips through

### 14.2 Device missing

- pre-run gating should block the test
- the missing device list should use the same required-device contract used by the test

### 14.3 Device present but signal unavailable

- reads should surface as unavailable
- write attempts should fail explicitly
- DSL fallback/default semantics should remain visible in run details

## 15. Observability

Purpose: keep debugging strong while simplifying execution.

Even after refactoring to a device-owned execution API, runtime reporting should still expose:

- last sampled DSL values
- last command writes
- write failures
- require satisfaction timing
- final decision samples

This improves diagnosis without forcing snapshots to remain the execution source.

## 16. Non-Goals

Purpose: avoid overreaching the refactor.

This spec does not require:

- exposing every telemetry field in DSL
- removing snapshots
- changing CLI syntax
- changing test phase semantics
- changing NetworkTables ownership

## 17. Tradeoffs

Purpose: record the main engineering tradeoffs.

Benefits:

- one execution contract
- less central special-case logic
- clearer device ownership
- easier addition of new device types

Costs:

- more implementation work in device classes
- temporary duplication during migration
- need to document DSL-visible signals more explicitly

## 18. Future Extensions

Purpose: identify likely extensions once the interface is unified.

Possible future work:

- richer normalized writable signals such as `appliedDuty` or `busVoltage`
- structured read/write result types instead of raw `Object` and `boolean`
- signal capability introspection directly from devices
- stronger runtime detail fields such as `lastCommandWrites`


