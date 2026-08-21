# Feature Spec: Robot Controller Device Family

Purpose: define a first-class `robotController` device family that treats controller hardware the same way the system treats mixed-vendor motor controllers and sensors.

## Status

- Spec/research only.
- No runtime behavior changes are implemented by this document.
- This spec assumes exactly one active robot-controller device per runtime/profile.
- This spec allows multiple controller definitions to exist in one config so future profiles can switch between them.

## Goal

Purpose: make roboRIO and future controller hardware plug-and-play through the same manufacturer-backed device contract.

The system currently treats `roborio` as a special virtual singleton. That is sufficient for basic presence in reports, but it does not scale to a second controller platform. The target state is:

- one generic device family: `robotController`
- multiple concrete manufacturer/model implementations
- one shared probe/snapshot/health/test contract
- one active controller per profile/runtime
- profile-driven controller selection without code surgery

The first two implementations are:

- NI `roboRIO`
- Limelight `SystemCore`

This spec is based in part on the Limelight SystemCore specifications PDF dated June 15, 2025, alpha status, with later revision notes shown in the document header. The document explicitly states that alpha features are subject to change.

Source:

- <https://downloads.limelightvision.io/documents/systemcore_specifications_june15_2025_alpha.pdf>

## Non-Goals

Purpose: keep the first pass narrow enough to implement safely.

- Do not replace the roboRIO runtime today.
- Do not assume simultaneous active operation of roboRIO and SystemCore in one runtime.
- Do not define a transport/control-plane migration in this spec.
- Do not change supported PC CAN diagnostics from passive to active transmission.
- Do not require SystemCore hardware-specific telemetry fields until real hardware is available to confirm them.

## Requirements

Purpose: capture the hard requirements that shape the architecture.

- The controller device must be modeled like other first-class devices.
- Manufacturer differences must live behind shared contracts, not in ad hoc `if roborio` branching.
- The shared config must be allowed to define multiple controller devices.
- Exactly one controller device may be active in a selected runtime profile.
- Existing CAN identity fields remain authoritative for concrete hardware identity:
  - `manufacturer`
  - `deviceType`
  - `id`
- The semantic device family should be generic:
  - `type: robotController`
- Concrete hardware remains model-specific:
  - example `model: roboRIO`
  - example `model: SystemCore`
- All controller-family implementations must support the same top-level capability categories, even when individual fields are unavailable on one platform.

## Design Summary

Purpose: describe the top-level shape of the new controller-family model.

The system should treat controller hardware exactly like mixed-vendor motor-controller support:

- common semantic family above vendor implementations
- manufacturer-specific wrappers and readers below
- shared runtime/device contracts in the middle

The controller family therefore becomes:

- semantic family: `robotController`
- vendor/manufacturer implementations:
  - `NI`
  - `Limelight`
- concrete models:
  - `roboRIO`
  - `SystemCore`

This follows the same design pattern already used for:

- CTRE motor controllers
- REV motor controllers
- CTRE and REV power devices
- CTRE sensors such as CANCoder and Pigeon

## Config Model

Purpose: define how controller devices are represented in `bringup_system.json`.

### Shared Rules

- Controller devices live in the shared `devices[]` inventory like other devices.
- Profiles select controller devices by label via `profiles.<name>.devices[]`.
- A profile may define zero or more controller labels in raw config.
- Runtime activation must reject profiles that resolve to more than one active controller device.
- Runtime activation may accept zero controller devices only for explicitly controllerless simulation or future offline modes; normal robot profiles should contain exactly one.

### Required Fields

Each controller device definition should include:

- `label`
- `deviceInterface`
- `manufacturer`
- `deviceType`
- `id`
- `model`
- `type`

For controller-family devices:

- `type` must be `robotController`
- `model` identifies the concrete implementation
- `manufacturer`, `deviceType`, and `id` preserve concrete bus identity

### Example

```json
{
  "label": "main-controller-rio",
  "deviceInterface": "CAN",
  "manufacturer": 1,
  "deviceType": 1,
  "id": 0,
  "model": "roboRIO",
  "type": "robotController"
}
```

```json
{
  "label": "main-controller-systemcore",
  "deviceInterface": "CAN",
  "manufacturer": 0,
  "deviceType": 0,
  "id": 0,
  "model": "SystemCore",
  "type": "robotController"
}
```

SID_COMMENT: the SystemCore example uses placeholder `manufacturer`, `deviceType`, and `id` values until actual bus identity is confirmed on real hardware. The schema and runtime must support the same fields, but the literal values must not be guessed into production mappings without verification.

## Runtime Selection Rules

Purpose: define how the active controller is selected and validated.

- Config may define both roboRIO and SystemCore devices.
- A selected profile may include either controller definition.
- A selected profile must not activate more than one controller-family device at a time.
- The active runtime should expose the chosen controller as the single controller instance for:
  - snapshots
  - active presence probe
  - runtime health reporting
  - DSL signal access
  - topology/runtime surfaces

Validation behavior:

- zero controller devices in a normal robot profile:
  - warning or failure depending on runtime mode
- more than one controller device in an active profile:
  - hard validation failure
- unknown controller model:
  - config loads
  - activation/probe support fails soft with explicit unsupported status

## Architecture Changes

Purpose: describe the code-structure changes required to support the family cleanly.

### Device Wrapper Layer

Existing:

- `devices/ni/RoboRioDevice` is a virtual singleton wrapper

Target:

- retain controller-specific wrappers under `devices/...`
- make wrappers represent concrete controller implementations under a shared family

Expected first-pass wrappers:

- `src/main/java/frc/robot/devices/ni/RoboRioDevice.java`
- `src/main/java/frc/robot/devices/limelight/SystemCoreDevice.java`

Shared expectation:

- both implement `DeviceUnit`
- both report `getDeviceType()` semantics through the generic family contract
- both support a richer controller snapshot than today's virtual-only roboRIO snapshot

### Manufacturer Layer

Purpose: organize controller-family manufacturer logic the same way other vendor families are organized.

Expected packages:

- `src/main/java/frc/robot/manufacturers/ni/`
- `src/main/java/frc/robot/manufacturers/ni/diag/`
- `src/main/java/frc/robot/manufacturers/ni/util/`
- `src/main/java/frc/robot/manufacturers/limelight/`
- `src/main/java/frc/robot/manufacturers/limelight/diag/`
- `src/main/java/frc/robot/manufacturers/limelight/util/`

Split of responsibilities:

- `manufacturers/<vendor>/`
  - registration
  - group construction
  - vendor-level device-family wiring
- `manufacturers/<vendor>/util/`
  - low-level reader/adapters
  - raw platform/API telemetry collection
- `manufacturers/<vendor>/diag/`
  - diagnostic attachments
  - health evaluation
  - operator-facing evidence and report shaping

### Registry Layer

Purpose: register controller vendors the same way other families register device groups.

The manufacturer registry should be extended so controller-family implementations are first-class participants in:

- device creation
- snapshot capture
- fault clearing where applicable
- diagnostics reporting
- lifecycle handling

The long-term system should not need to special-case `roborio` in places that already dispatch through manufacturer/device wrappers.

## Shared Controller Capability Contract

Purpose: define the common controller-family contract that all controller implementations must expose.

All controller-family implementations must support these capability categories.

### 1. Identity

- manufacturer name
- concrete model name
- configured label
- configured bus identity
- optional firmware/software version strings
- optional serial/build identifiers

### 2. Presence

- controller present / degraded / absent / unknown classification
- active presence probe result
- evidence list
- operator-facing message

### 3. Power Health

- input voltage
- brownout state
- sticky brownout state if available
- protection/undervoltage state if available

### 4. Bus Health

- CAN status/health from the active controller
- error counters or equivalent evidence when available
- utilization or bus-pressure indicators when available

### 5. Rail and Peripheral Power Health

- user rail voltage/current when supported
- rail enabled/disabled status when supported
- overcurrent/fault status when supported
- peripheral power fault reporting when supported

### 6. Built-In Telemetry and Faults

- device-local fault summary
- sticky fault summary
- platform warning summary
- controller-specific protection/fault states

### 7. Built-In Sensors and I/O

- IMU telemetry when present
- I/O subsystem status when present
- I2C subsystem status when present
- subsystem overcurrent/fault status when present

### 8. Reporting and Serialization

- JSON attachment support
- text report support
- topology/runtime surface compatibility
- stable status-code mapping

## Probe Contract

Purpose: define how the active presence probe must treat controller-family devices.

The controller family must become a supported active presence probe target.

Unlike motor controllers and sensors, controller-family probing does not prove "CAN presence" in the exact same electrical sense. Instead, it proves controller telemetry health through the controller's own runtime/platform APIs. That is still valid under the same top-level device-family framework.

Shared probe outputs must include:

- `bucket`
- `score`
- `maxScore`
- `warnings`
- `errors`
- `evidence[]`
- `durationMs`
- stage timing breakdown

### NI roboRIO First-Pass Evidence

Expected evidence candidates:

- controller telemetry API reachable
- input voltage valid
- not browned out
- CAN status readable
- 3.3V rail healthy
- 5V rail healthy
- 6V rail healthy

### Limelight SystemCore First-Pass Evidence

Expected evidence candidates, subject to hardware/API confirmation:

- controller telemetry API reachable
- input voltage valid
- brownout/protection state readable
- CAN interface status readable
- power rail fault state readable
- I/O subsystem fault state readable
- I2C subsystem fault state readable
- IMU telemetry readable

SID_COMMENT: the SystemCore specification lists multiple CAN interfaces, configurable brownout behavior, fault reporting via robot telemetry/onboard indicators, I/O subsystem status, I2C ports, and IMU outputs. Actual field names and software access paths must be verified against real hardware/software APIs before finalizing the probe reader implementation.

## Snapshot Contract

Purpose: define the shared device snapshot shape for controller-family devices.

Controller-family snapshots should stop using "virtual presence only" as the whole contract. They should instead produce a first-class snapshot with controller attachments.

Expected shared attachment families:

- `robotControllerPower`
- `robotControllerBus`
- `robotControllerRails`
- `robotControllerFaults`
- `robotControllerImu`
- `robotControllerIo`

Field availability rules:

- fields unsupported on a given controller may be omitted or null
- unsupported must not be silently converted into healthy
- reports must distinguish:
  - unavailable
  - unsupported
  - healthy
  - faulted

## DSL and Test Contract

Purpose: ensure controller-family devices participate in the same higher-level testing model as other device families.

Controller-family devices should become addressable in the DSL and runtime signal system through a shared signal contract.

Initial shared signal families should include:

- `input_voltage`
- `brownout`
- `can_utilization`
- `can_tx_error_count`
- `can_rx_error_count`
- `rail_3v3_voltage`
- `rail_5v_voltage`
- `rail_6v_voltage`
- `imu_yaw`
- `imu_pitch`
- `imu_roll`

Platform-specific signals may exist, but shared signals should be preferred for cross-controller portability.

## Topology and UI Contract

Purpose: keep operator-facing device identity and behavior consistent.

- Topology/config authoring must treat controller-family devices as normal device nodes.
- The topology editor should allow creating both controller implementations in the shared inventory.
- Profiles should choose the active controller by including exactly one controller label.
- Runtime/state surfaces should refer to the semantic family as `robotController`.
- Vendor/model details remain visible as metadata, just as with motors and sensors.

This preserves:

- generic workflows
- vendor-specific diagnosis
- profile-level hardware swaps

## NI roboRIO Implementation Direction

Purpose: describe the first implementation target for the new family.

The roboRIO implementation should be refactored from a special virtual singleton into a full NI controller-family implementation.

Expected additions:

- NI manufacturer group support under `manufacturers/ni`
- NI raw status reader under `manufacturers/ni/util`
- NI diagnostic attachment definitions under `manufacturers/ni/diag`
- active presence probe support for roboRIO
- richer roboRIO snapshot attachments
- DSL signal exposure for controller health

The roboRIO may remain singleton-backed in lifecycle ownership, but that singleton behavior must be an implementation detail, not the semantic family definition.

## Limelight SystemCore Implementation Direction

Purpose: define how future SystemCore support should land without a second architecture rewrite.

SystemCore should be added as a second controller-family implementation under the same contract.

Expected additions:

- Limelight manufacturer group support under `manufacturers/limelight`
- raw telemetry readers under `manufacturers/limelight/util`
- diagnostic attachments under `manufacturers/limelight/diag`
- controller-family snapshot support
- controller-family active presence probe support
- DSL signal exposure mapped to the shared controller contract

The implementation must reuse the same top-level controller abstractions already built for roboRIO. The SystemCore path must not introduce a second special-case controller architecture.

## Migration Plan

Purpose: describe a safe, staged path from today's roboRIO special case to the target family model.

### Stage 1: Generic Family Contract

- introduce semantic `type: robotController`
- define shared attachment and probe contracts
- add profile validation for exactly one active controller

### Stage 2: NI Refactor

- move roboRIO support into manufacturer-backed NI reader/diag structure
- keep behavior compatible with existing profiles where practical
- retain fail-soft behavior for unavailable fields

### Stage 3: Probe and Snapshot Expansion

- add roboRIO controller-family active probe support
- replace virtual-only snapshot behavior with structured controller attachments
- add controller DSL signals

### Stage 4: SystemCore Implementation

- add a second controller-family implementation
- verify real hardware identity fields
- map SystemCore-specific telemetry into shared controller contract

### Stage 5: Profile and Topology Authoring Support

- allow both controller definitions in shared config
- enforce single active controller per selected profile
- update docs/examples/templates

## Test Strategy

Purpose: define the minimum meaningful regression coverage for this family.

Automated tests should cover:

- config validation rejects more than one active controller per profile
- config allows multiple controller definitions globally
- runtime selection resolves exactly one active controller
- active presence probe supports roboRIO controller-family devices
- unsupported fields fail soft, not hard
- snapshot serialization remains stable when some controller fields are unavailable
- DSL shared controller signals resolve correctly
- manufacturer registry creates the right implementation by concrete model/vendor

When SystemCore hardware is available, add:

- hardware-backed probe verification
- hardware-backed snapshot verification
- field-presence matrix tests for supported/unsupported telemetry

## Tradeoffs

Purpose: record the main costs and benefits of this direction.

Benefits:

- future controller swap becomes profile/config work instead of architecture surgery
- controller hardware becomes visible and diagnosable like other devices
- one shared probe and reporting model reduces operator confusion
- vendor-specific growth stays contained in manufacturer packages

Costs:

- roboRIO support becomes more complex than today's virtual singleton
- some controller semantics are not true "CAN device presence" and need careful wording
- SystemCore API details are not yet verified in this repo
- profile validation becomes stricter

## Future Extensions

Purpose: leave space for later growth without blocking the first implementation.

- simultaneous defined-but-inactive controller entries in config tools
- richer controller firmware/build/version reporting
- controller-side storage/network/USB subsystem reporting
- controller IMU and I/O diagnostics in the UI
- offline controller capability matrix by model
- controller-family topology rendering refinements

## Definition of Done for the First Implementation Pass

Purpose: define the minimum bar for calling the controller family real rather than aspirational.

- `robotController` exists as a semantic device family in config/runtime contracts
- roboRIO is implemented through a manufacturer-backed NI path
- the active presence probe supports roboRIO as a controller-family device
- roboRIO snapshots expose structured controller health data beyond virtual presence
- profiles may define multiple controller devices globally
- runtime rejects more than one active controller in the selected profile
- SystemCore support has a documented slot in the same architecture, with no second special-case design required
