# Xbox Controller as DSL Device Feature Spec

## 1. Purpose

Purpose: Specify the implemented support for treating an Xbox controller as a
configured Robot Test DSL device.

This feature lets DSL tests declare controller devices the same way they
declare motors and sensors:

```text
device "controller0"
```

It also lets test conditions read selected Xbox controller signals:

```text
abort controller0.B
require controller0.A
require controller0.leftY > 0.5
```

## 2. Current Implementation Status

Status: implemented first pass.

Implemented code paths:

- `src/main/java/frc/robot/manufacturers/microsoft/MicrosoftDeviceGroup.java`
- `src/main/java/frc/robot/manufacturers/microsoft/XboxControllerDevice.java`
- `src/main/java/frc/robot/manufacturers/ManufacturerRegistry.java`
- `src/main/java/frc/robot/BringupUtil.java`
- `src/main/java/frc/robot/BringupCore.java`
- `src/main/java/frc/robot/Robot.java`
- `src/main/java/frc/robot/RobotV2.java`
- `src/main/java/frc/robot/devices/DeviceUnit.java`
- `src/main/java/frc/robot/tests/dsl/DslBringupTest.java`

## 3. Goals

- Make Xbox controllers profile-configured devices.
- Keep controller DSL references explicit with `device.signal` syntax.
- Use the same device lifecycle as other bringup devices.
- Keep host-side validation source-authoritative.
- Keep controller reads robot-local and read-only.
- Avoid special-casing controller names in host validation.

## 4. Non-Goals

This feature does not:

- expose every Xbox input as a DSL signal
- make controller signals writable
- make controller input a motor command source
- define deadband, scaling, or transforms for DSL writes
- replace `bringup_bindings.json` controller binding behavior
- publish controller signals through NetworkTables
- require CAN identity fields for USB controller devices

Signal-driven motor commands are covered separately in:

- [FEATURE_SPEC_ROBOT_TEST_DSL_SIGNAL_SET.md](./FEATURE_SPEC_ROBOT_TEST_DSL_SIGNAL_SET.md)

## 5. Config Model

Xbox controllers are defined in `bringup_system.json` as normal devices.

Example:

```json
{
  "label": "controller0",
  "type": "xboxController",
  "deviceInterface": "USB",
  "id": 0,
  "model": "Xbox Controller"
}
```

Profile membership is required:

```json
{
  "profiles": {
    "dsl_demo_050426": {
      "devices": [
        "FALCON 9",
        "controller0"
      ]
    }
  }
}
```

Rules:

- `label` is the DSL device name.
- `type` must be `xboxController`.
- `deviceInterface` must be `USB`.
- `id` is the controller port or configured identifier.
- the controller must be present in the active profile to be used by a DSL test.

## 6. Manufacturer Model

The implementation adds a Microsoft manufacturer group:

```text
frc.robot.manufacturers.microsoft.MicrosoftDeviceGroup
```

Vendor:

```text
Microsoft
```

Device type:

```text
xboxController
```

The group registers:

```text
XboxControllerDevice
```

with role:

```text
MISC
```

The manufacturer registry includes the Microsoft group so controllers are
instantiated through the same registry path as REV, CTRE, and NI devices.

## 7. Device Lifecycle

`XboxControllerDevice` implements `DeviceUnit`.

Lifecycle behavior:

- `ensureCreated()` marks the device present for the test lifecycle.
- `close()` marks the device not present.
- `clearFaults()` is a no-op.
- `setDuty()` is not supported.
- `stopAll()` has no controller effect.

Snapshots:

- vendor: `Microsoft`
- device type: `xboxController`
- CAN ID field: the configured `id`
- label: configured label
- present: current created state
- note: `driverStationInput`

SID_COMMENT: The snapshot still uses the common `canId` field even though the
controller is USB. That matches the current shared `DeviceSnapshot` shape.

## 8. DSL Signal Catalog

The first pass exposes these DSL signals:

<!-- markdownlint-disable MD013 -->

| Device type | Signal | Value type | Readable | Writable | Clearable |
| --- | --- | --- | --- | --- | --- |
| `xboxController` | `A` | boolean | yes | no | no |
| `xboxController` | `B` | boolean | yes | no | no |
| `xboxController` | `leftY` | number | yes | no | no |
| `xboxController` | `rightY` | number | yes | no | no |

<!-- markdownlint-enable MD013 -->

Runtime support:

- `A` and `B` are returned as booleans.
- `leftY` and `rightY` are returned as numbers.
- unavailable signals return no value and conditions evaluate false.

The runtime snapshot builder also captures these additional raw inputs for
internal use:

- `leftX`
- `rightX`
- `leftTrigger`
- `rightTrigger`

Those additional inputs are not currently part of the DSL signal registry.

## 9. Runtime Input Flow

`Robot` and `RobotV2` build controller snapshots every periodic cycle through:

```text
XboxControllerDevice.buildControllerInputs(...)
```

`BringupCore.setTestInputs(...)` forwards those snapshots to:

```text
XboxControllerDevice.setControllerInputs(...)
```

`DslBringupTest` reads controller signals through the generic device path:

```text
DeviceUnit.readDslSignal(...)
```

`XboxControllerDevice.readDslSignal(...)` then resolves the value for its own
configured label.

## 10. Processed Axis Behavior

For `controller0`, the runtime snapshot stores processed drive values for:

- `leftY`
- `rightY`

Those processed values are the same `leftDrive` and `rightDrive` values used by
the robot bringup loop.

Current behavior:

- `controller0.leftY` uses processed `leftDrive`
- `controller0.rightY` uses processed `rightDrive`
- other controller labels use raw WPILib axis reads

SID_QUESTION: Should DSL controller axis signals use raw physical controller
values or processed bringup drive values? The current implementation uses
processed values for `controller0.leftY` and `controller0.rightY`.

## 11. Host Validation

Host-side DSL validation requires:

- controller device exists in `devices[]`
- controller device is included in the active profile
- referenced controller signal exists in the generated signal catalog
- controller signals are used only as readable values
- controller signals are not used in `set`, `clear`, or `unsafe-exit`

The host does not synthesize default controllers for DSL validation.

This is intentional:

- configured devices are source-authoritative
- DSL tests must declare the same device labels the robot will instantiate
- missing profile membership fails before a test is saved

## 12. Example DSL

```text
test "falcon9_xbox_controller_smoke"
device "FALCON 9"
device "controller0"

init:
    clear "FALCON 9".faults

main:
    set "FALCON 9".output = 0.12
    abort "FALCON 9".current > 35
    abort "FALCON 9".temperature > 80
    abort controller0.B
    until timer.elapsed >= 3.0
    require controller0.A
    require "FALCON 9".current > 1.0
    require "FALCON 9".velocity > 100

close:
    clear "FALCON 9".faults
```

Meaning:

- command the Falcon at fixed low output
- fail immediately if `B` is pressed
- require `A` to be pressed at least once before normal timeout
- require current draw and velocity as motor evidence
- clear Falcon faults before and after the test

## 13. Safety

Controller signals are read-only in the current DSL.

This keeps first-pass controller support lower risk:

- a controller button can abort a test
- a controller button can be required as operator confirmation
- a controller axis can be used as observed evidence
- a controller axis cannot directly command motor output yet

Motor output remains controlled by literal `set` values in v0.3.

## 14. Tradeoffs

Treating controllers as configured devices adds some setup friction because
`controller0` must be present in `bringup_system.json`.

The benefit is consistency:

- host validation and robot runtime use the same profile device list
- DSL source does not rely on hidden default controller names
- controller signals use the same `device.signal` model as motors and sensors

The first-pass signal list is intentionally small. It supports the current DSL
test needs without committing to a full Xbox input surface before naming,
metadata, and safety semantics are settled.

## 15. Future Extensions

Potential extensions:

- expose `X`, `Y`, bumpers, stick buttons, start, back, and POV signals
- expose triggers as numeric DSL signals
- decide raw-axis versus processed-axis semantics
- add live controller connection status as a readable signal
- add signal-valued `set` so axes can command motor output with explicit scale
- improve snapshots so USB devices do not report through a CAN-specific field

## 16. Acceptance Criteria

This implemented first pass is complete when:

- `controller0` can be defined in `bringup_system.json`
- `controller0` can be included in an active profile
- `device "controller0"` is valid in DSL source
- `controller0.A`, `controller0.B`, `controller0.leftY`, and
  `controller0.rightY` validate as readable signals
- robot runtime instantiates the controller through `MicrosoftDeviceGroup`
- DSL runtime reads controller values through `DeviceUnit.readDslSignal`
- controller signals can be used in `abort`, `success`, `until`, and `require`
- controller signals cannot be written, cleared, or used with `unsafe-exit`
- Java tests cover button and axis reads
- Python CLI tests cover configured controller import and validation
