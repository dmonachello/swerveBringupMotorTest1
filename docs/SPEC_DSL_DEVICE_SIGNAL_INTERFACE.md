SPEC_STATUS: IMPLEMENTED

# DSL Device Signal Interface Spec

## 1. Purpose

Purpose: define the current robot-side device/signal contract used by the Robot Diagnostic Test DSL runtime.

This document covers:

- the DSL-visible signal registry
- device-owned read, write, and clear behavior
- built-in timer behavior
- how execution reads differ from reporting snapshots

This document does not define:

- CLI command syntax
- UI presentation
- NetworkTables publication
- non-DSL reporting payload layout

## 2. Current Architecture

The DSL execution path is now device-owned.

The runtime uses three core pieces:

1. a canonical signal registry:
   - [src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java:1)
2. device-level execution methods on `DeviceUnit`
3. the DSL runtime engine in:
   - [src/main/java/frc/robot/tests/dsl/DslBringupTest.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/dsl/DslBringupTest.java:1)

The current model is:

- the registry defines stable DSL signal names and capabilities
- each device owns how those signals are read, written, or cleared
- the DSL engine owns lifecycle, evaluation order, and verdict logic

## 3. Terms

### 3.1 DSL-visible signal

A DSL-visible signal is a named read/write endpoint intentionally exposed to test authors.

Examples:

- `FALCON 9.output`
- `FALCON 9.velocity`
- `controller0.leftY`
- `lmtSw0.pressed`
- `timer.elapsed`

### 3.2 Snapshot

A snapshot is a diagnostic/reporting record produced by the robot-side device model.

Snapshots are still important for:

- reports
- UI state
- diagnostics
- runtime visibility

But snapshots are not the DSL execution API.

### 3.3 Device signal interface

The device signal interface is the device-owned runtime API the DSL engine uses to:

- read signal values
- write writable signals
- clear clearable signals

## 4. Canonical Registry

The canonical DSL signal registry lives in:

- [src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java:1)

Provider classes define the per-device-type signal surfaces:

- [MotorSignalProvider.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/dsl/signals/MotorSignalProvider.java:1)
- [LimitSwitchSignalProvider.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/dsl/signals/LimitSwitchSignalProvider.java:1)
- [EncoderExternalSignalProvider.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/dsl/signals/EncoderExternalSignalProvider.java:1)
- [XboxControllerSignalProvider.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/dsl/signals/XboxControllerSignalProvider.java:1)
- [TestTimerSignalProvider.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/dsl/signals/TestTimerSignalProvider.java:1)

The generated host-side artifact is:

- [tools/common/generated/robot_test_dsl_signals.json](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/common/generated/robot_test_dsl_signals.json:1)

That generated file is the machine-readable contract consumed by host tooling and documentation.

## 5. Execution Read Path

The runtime reads DSL-visible signals through device-owned signal APIs.

The central runtime behavior in `DslBringupTest.readSignalValue(...)` is limited to:

- built-in `timer.elapsed`
- device lookup
- invoking `device.readDslSignal(signalName)`
- translating position-like signals into delta-from-start behavior for:
  - `motor.position`
  - `motor.position_delta`
  - `encoderExternal.position`
  - `encoderExternal.position_delta`

That means:

- snapshots are no longer the execution fallback path
- per-device telemetry extraction is not supposed to live in the DSL engine

## 6. Execution Write Path

The runtime writes DSL signals through device-owned write APIs.

The engine:

- resolves the authored `set`
- validates range and fallback behavior
- calls `device.writeDslSignal(signalName, value)`

The device owns whether the signal is actually writable and how the command is applied.

## 7. Execution Clear Path

The runtime clears DSL signals through device-owned clear APIs.

The engine:

- validates that the signal is marked clearable in metadata
- calls `device.clearDslSignal(signalName)`

The device owns the meaning of the clear operation.

## 8. Built-In Timer

The timer is a special built-in DSL source.

Authored DSL uses:

```text
timer.elapsed
```

Internally, the registry uses device type:

```text
TestTimer
```

The timer:

- is readable only
- is not declared as a configured device
- returns seconds since test start

## 9. Supported Signal Surface

### 9.1 Motor

Current DSL-visible motor signals:

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

### 9.2 Limit Switch

Current DSL-visible limit-switch signal:

- `pressed`

### 9.3 External Encoder

Current DSL-visible external-encoder signals:

- `position`
- `position_actual`
- `position_delta`

### 9.4 Xbox Controller

Current DSL-visible Xbox controller signals:

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

### 9.5 Built-In Timer

Current DSL-visible timer signal:

- `elapsed`

## 10. Capability Model

Each signal in the registry declares:

- `valueType`
- `readable`
- `writable`
- `clearable`
- `safeValue`
- `safeProvider`
- `unsafeExitAllowed`

These capability flags drive:

- host validation
- runtime safing
- `unsafe-exit` eligibility
- `clear` eligibility

## 11. Range Rules

The current host-side validator enforces known writable ranges for:

- `motor.output`
- `motor.output_percent_cmd`

Current range:

- `-1.0` to `1.0`

Runtime devices still own the final acceptance check through:

- `device.isDslWritableValueInRange(...)`

## 12. Signal-Driven Set Rules

Signal-driven `set` uses this model:

- target must be writable numeric
- source must be readable numeric
- source unavailability in `main` triggers the authored `default`
- source unavailability in `init` fails startup
- source unavailability in `close` skips the write

Important current restriction:

- motor-device source signals are rejected by host validation for signal-driven `set`

So today, typical signal-driven sources are:

- controller axes
- other non-motor numeric device signals

## 13. Delta Position Semantics

The runtime treats these as start-relative values:

- `motor.position`
- `motor.position_delta`
- `encoderExternal.position`
- `encoderExternal.position_delta`

At test start:

- the runtime captures the starting position when available

During execution:

- the DSL-visible value returned to conditions is current position minus starting position

This means authored tests should read these as test-relative motion, not absolute lifetime position.

## 14. Snapshots vs DSL Execution

Snapshots and DSL execution are intentionally different layers.

Snapshots are for:

- operator visibility
- live runtime reporting
- fault and telemetry attachments
- post-run inspection

DSL execution is for:

- condition evaluation
- command writes
- clear operations
- test verdict logic

A snapshot field is not automatically part of the DSL language just because it exists in reporting.

## 15. Observability

Even though execution is device-owned, the runtime still surfaces useful details through run reporting:

- last sampled values
- last resolved `set` values
- signal-set fallback activity
- `require` satisfaction timing
- declared `unsafe-exit` entries

That keeps the system debuggable without putting snapshot-attachment knowledge back into the DSL engine.

## 16. Tradeoffs

Benefits:

- one canonical signal registry
- device-owned signal semantics
- less central special-case logic in the DSL engine
- easier extension for new device types

Costs:

- every new device type must implement signal behavior deliberately
- documentation must stay synchronized with the registry
- some runtime semantics, such as delta-position normalization, still live centrally by design

## 17. Future Extensions

Likely future directions:

- stronger typed read/write result objects
- automatic doc generation from the registry
- broader range metadata in the generated artifact
- more normalized signal aliases where two vendor surfaces mean the same thing
