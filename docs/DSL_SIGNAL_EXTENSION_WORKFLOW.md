# DSL Signal Extension Workflow

## Purpose

Define the required process for adding or changing DSL-visible device signals.

## Ownership Model

DSL signal declarations are split by device type.

- Shared metadata model: `src/main/java/frc/robot/tests/dsl/signals/DslSignalMeta.java`
- Shared provider contract: `src/main/java/frc/robot/tests/dsl/signals/DslDeviceSignalProvider.java`
- Per-device providers live in `src/main/java/frc/robot/tests/dsl/signals/`
- Aggregation/export lives in `src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java`
- Runtime device contract lives in `src/main/java/frc/robot/devices/DeviceUnit.java`
- Shared runtime helper lives in `src/main/java/frc/robot/devices/DeviceDslSupport.java`

## Current Providers

- `MotorSignalProvider`
- `LimitSwitchSignalProvider`
- `EncoderExternalSignalProvider`
- `XboxControllerSignalProvider`
- `TestTimerSignalProvider`

## Required Steps

1. Choose the owning device type.
2. Update that device type's provider class only.
3. Update the owning runtime device implementation.
   Example: `readDslSignal`, `setDuty`, `clearFaults`, or other device-specific hooks.
4. Regenerate or update `tools/common/generated/robot_test_dsl_signals.json`.
5. Add or update tests.

## Required DeviceUnit Methods

Every runtime device must define the same DSL-facing methods:

- `readDslSignal(String signalName)`
- `writeDslSignal(String signalName, double value)`
- `clearDslSignal(String signalName)`
- `isDslWritableValueInRange(String signalName, double value)`

For simple devices, delegate to `DeviceDslSupport`.

For custom devices, implement the logic directly if the shared helper is not sufficient.

## Naming Rules

- Reuse existing repo signal names when possible.
- Use boolean-style names for discrete controls.
  Examples: `A`, `LB`, `D_UP`, `pressed`
- Use lower camel case for numeric axes/measurements.
  Examples: `leftY`, `rightTrigger`, `velocity`
- Do not create alternate aliases for the same signal in the DSL registry.

## Capability Rules

- `readable=true` means the runtime can observe the signal.
- `writable=true` means the DSL may target the signal in a `set`.
- `clearable=true` means the DSL may target the signal in a `clear`.
- `safeValue` must be set for writable signals unless `safeProvider=true`.
- `unsafeExitAllowed=true` is reserved for signals that may intentionally remain active at exit.

## Adding a New Device Type

1. Add the device type constant in `DslSignalRegistry.java` if needed.
2. Create a new `...SignalProvider` class under `src/main/java/frc/robot/tests/dsl/signals/`.
3. Register the provider in `DslSignalRegistry.PROVIDERS`.
4. Implement runtime signal behavior for that device type.
5. Update the generated signal catalog.
6. Add tests for validation and runtime use.

## Verification

Minimum verification after a DSL signal change:

- Python:
  - `python -m unittest tools.can_nt.tests.test_robot_test_dsl tools.can_nt.tests.test_bridge_cli_robot_test_dsl_cli`
- Java:
  - `.\gradlew.bat compileJava`

## Notes

- `DslSignalRegistry.java` should remain an aggregator and export surface, not the place where individual device types define all of their signals.
- New signal work is incomplete unless the generated artifact and tests are updated in the same change.
