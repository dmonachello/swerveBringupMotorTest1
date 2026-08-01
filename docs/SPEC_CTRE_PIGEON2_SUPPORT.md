# Spec: CTRE Pigeon 2.0 Support

SPEC_STATUS: PROPOSED

## Purpose

Define the first complete bringup-system implementation of CTRE Pigeon 2.0 support.

The generic non-motor testing and operator-intervention contract lives in:

- [SPEC_NON_MOTOR_DEVICE_TESTING_AND_DSL_INTERVENTION.md](./SPEC_NON_MOTOR_DEVICE_TESTING_AND_DSL_INTERVENTION.md)

This spec is intentionally scoped to a useful first slice:

- robot-side device presence and telemetry support
- runtime-state / UI / CLI exposure
- DSL signal availability for test authoring
- exact operator test procedure shape

This spec does not attempt to solve every IMU feature in one pass.

## Scope

Purpose: Define what this spec changes and what it does not.

In scope:

- recognize `Pigeon` / `Pigeon2` as a first-class CTRE IMU device in robot bringup
- instantiate and snapshot the device through the robot-side lifecycle/runtime system
- expose core IMU signals in runtime-state and DSL
- show Pigeon state coherently in UI and CLI
- provide exact manual validation steps
- preserve existing command and status contracts

Out of scope:

- full pose estimation
- fused heading / odometry integration
- advanced mount-calibration workflows
- replacing arbitrary gyro APIs across the codebase
- passive CAN reverse engineering of Pigeon traffic on the PC tool
- non-CTRE IMU support

## Problem Statement

Purpose: Explain the current gap.

The repo already has partial awareness of Pigeon devices:

- topology/category support for `pigeon`
- profile/type recognition in some config paths
- LED/status inference code that recognizes `Pigeon` / `Pigeon2`

But the bringup system does not yet provide a complete operator-facing device path:

- no obvious robot-side Pigeon device wrapper / snapshot path
- no runtime-state telemetry contract for Pigeon signals
- no DSL signal contract for IMU-based tests
- no exact test procedure for validating the sensor

This leaves a hole in the system:

- teams can model a Pigeon in topology/config
- but they cannot use the bringup workflow to verify its live behavior in a disciplined way

## Non-Negotiable Constraints

Purpose: Preserve current system expectations.

- No user-facing service should regress for existing motor, encoder, controller, PDH/PDP, or roboRIO workflows.
- Pigeon support must be additive.
- NetworkTables contracts must not be changed for unrelated devices.
- REST runtime/tests control-plane behavior must remain unchanged.
- The Python CAN tool remains read-only on CAN.
- No changes should require runtime activation on profile select alone.
- No device should be instantiated solely because a profile is selected.
- Documentation and operator procedures must be exact and executable.

## Current Repo State

Purpose: Record the current baseline relevant to this feature.

Observed partial support:

- [src/main/java/frc/robot/BringupUtil.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/BringupUtil.java)
  - recognizes `Pigeon` as a device type
- [tools/can_topology/live_topology_view.py](/c:/Users/dmona/swerve3/tools/can_topology/live_topology_view.py)
  - has a `pigeon` category for topology surfaces
- [tools/common/topology_render.py](/c:/Users/dmona/swerve3/tools/common/topology_render.py)
  - has Pigeon-oriented topology rendering/category logic
- [src/main/java/frc/robot/diag/led/LedStatusInference.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/diag/led/LedStatusInference.java)
  - recognizes `Pigeon` / `Pigeon2` in diagnostic inference

Observed missing or incomplete support:

- no obvious dedicated robot-side `Pigeon2` device wrapper in current manufacturer/device packages
- no explicit Pigeon runtime-state fields in the shared runtime JSON contract
- no Pigeon signal rows in the DSL signal table documentation
- no Pigeon-specific lifecycle/manual validation procedure

## Product Goal

Purpose: State the operator-facing outcome.

After this feature:

- a configured Pigeon 2.0 can be selected, activated, instantiated, and observed through the existing bringup lifecycle model
- the operator can verify:
  - presence
  - basic liveness
  - yaw movement
  - pitch/roll tilt response
  - basic angular-rate behavior
- DSL tests can reference a small stable first-pass IMU signal set
- UI and CLI surfaces show the same coherent Pigeon state

## Design Principles

Purpose: Keep the feature understandable and maintainable.

- Start with a small, valuable signal contract.
- Prefer explicit named signals over clever generalized IMU abstractions.
- Reuse existing device lifecycle and runtime-state patterns.
- Make IMU support testable by hand before optimizing for automation breadth.
- Use common code for shared signal naming and runtime shaping.
- Do not invent a second sensor-contract path just for Pigeon.

## First-Pass Device Contract

Purpose: Define the exact first slice of supported behavior.

### Supported Device Identity

The first pass supports CTRE Pigeon 2.0 devices represented in config/profile data as:

- vendor: `CTRE`
- type: `Pigeon` or `Pigeon2`
- category: `pigeon`

Compatibility rule:

- host and robot normalization should treat `Pigeon` and `Pigeon2` as the same first-pass bringup device family unless a future need requires a stricter split

### Supported Runtime Signals

The first pass must expose these signals when the device is instantiated and readable:

- `yaw`
- `pitch`
- `roll`
- `angular_velocity_x`
- `angular_velocity_y`
- `angular_velocity_z`
- `accel_x`
- `accel_y`
- `accel_z`

Optional first-pass runtime metadata when available through the wrapper:

- `temp_c`
- `supply_v`
- basic fault summary / last-error text

### Not In First Pass

Not part of the initial contract:

- fused heading
- compass heading / magnetometer-heavy paths
- mount-pose write/config operations
- bias/calibration controls
- gravity-vector/world-frame variants
- arbitrary quaternion output

## Runtime-State Contract

Purpose: Define how Pigeon appears in shared runtime-state.

Pigeon devices must appear in the same `devices[]` runtime-state array used by other devices.

Required first-pass fields for a Pigeon entry:

- existing common fields:
  - `label`
  - `vendor`
  - `type`
  - `id`
  - `instantiated`
  - `lifecycleState`
  - `testable`
  - `presenceConfidence`
  - `lastSeenMs` when available
- Pigeon-specific numeric fields when instantiated/readable:
  - `yawDeg`
  - `pitchDeg`
  - `rollDeg`
  - `angularVelocityXDegPerSec`
  - `angularVelocityYDegPerSec`
  - `angularVelocityZDegPerSec`
  - `accelXMps2`
  - `accelYMps2`
  - `accelZMps2`

Optional fields:

- `tempC`
- `supplyV`
- `lastError`

Rules:

- When the device is not instantiated, these fields must be absent or left empty by existing runtime-state conventions.
- Do not publish fake zero values as if they were live telemetry.
- Presence/liveness must still use the existing runtime snapshot model.

## DSL Signal Contract

Purpose: Define the exact first-pass signal names visible to test DSL.

The first pass should add these canonical signal names for `Pigeon` / `Pigeon2` devices:

- `yaw`
- `pitch`
- `roll`
- `angular_velocity_x`
- `angular_velocity_y`
- `angular_velocity_z`
- `accel_x`
- `accel_y`
- `accel_z`

Signal types:

- all of the above are numeric

Example DSL usage:

```text
test "pigeon_yaw_turn"

device "IMU (Pigeon2)"

main:
    until timer.elapsed >= 8.0
    require "IMU (Pigeon2)".yaw_delta_max_abs > 15.0
```

```text
test "pigeon_pitch_tilt"

device "IMU (Pigeon2)"

main:
    until timer.elapsed >= 8.0
    require "IMU (Pigeon2)".pitch_delta_max_abs > 5.0
```

First-pass rule:

- signal names must be stable and documented in [docs/USER_GUIDE_ROBOT_TEST_DSL.md](/c:/Users/dmona/swerve3/docs/USER_GUIDE_ROBOT_TEST_DSL.md)
- do not add multiple redundant aliases in the first slice
- the current DSL does not support function calls such as `abs(...)`; use derived max-absolute delta signals for sign-independent movement tests

## UI Surfaces

Purpose: Define host-side operator visibility requirements.

### Live Topology

When a Pigeon is present in the selected profile/topology:

- it must render as a normal singleton sensor device in the topology view
- it must participate in active/runnable lifecycle state the same way other lifecycle-owned singleton devices do
- when selected, the details panel must show:
  - presence status
  - lifecycle state
  - yaw/pitch/roll
  - angular velocity fields
  - acceleration fields when available

### Tests Tab

When a selected test references the Pigeon:

- the device must appear in the selected-test active group / available devices surfaces
- test state must remain coherent with Pigeon lifecycle activation

### Runnable-State / Activation Messaging

Pigeon support must not create new special-case readiness messaging.

The existing lifecycle rules remain:

- selected profile alone does not instantiate
- activation is explicit
- DS disable tears runtime down
- readiness comes from robot state plus activation state

## CLI Surfaces

Purpose: Define CLI expectations.

Existing commands should expose Pigeon through the standard paths:

- `show devices`
- `show device <label>`
- `show runtime-state`
- `show lifecycle-state`
- `tests select ...`
- `tests run --wait`

No new CLI verbs are required for first-pass support.

Optional later CLI additions:

- `show device <label> --json` with richer Pigeon-specific fields if not already visible

## Robot-Side Implementation Shape

Purpose: Define the expected implementation structure.

### New Robot-Side Wrapper

Add a dedicated CTRE Pigeon 2.0 wrapper in the CTRE manufacturer/device layer.

Responsibilities:

- construct the Phoenix 6 `Pigeon2` hardware object
- read first-pass signals
- build a device snapshot consistent with existing device-snapshot conventions
- surface faults / last-error text when reasonable

### Lifecycle Integration

The wrapper must integrate with the existing lifecycle model:

- no creation on profile selection alone
- instantiate when runtime or controlled lifecycle scope owns the device
- singleton/support policy, if applied, must still respect the current “not before first real activation” rule

### Snapshot Integration

The Pigeon snapshot should follow existing sensor-device patterns:

- one shared snapshot object
- attachments only when justified
- no separate UI-only signal path

### Signal Publishing

Shared signal naming must come from common robot-side signal shaping used by runtime-state and DSL.

Do not:

- hand-roll one set of names for runtime-state
- another set for DSL
- another set for CLI text

One common signal contract must own all of them.

## Test Strategy

Purpose: Define the exact verification layers.

### Java Unit Tests

Add tests for:

- device-type/model normalization for `Pigeon` / `Pigeon2`
- runtime-state shaping for a Pigeon snapshot
- DSL signal exposure / catalog inclusion
- lifecycle activation behavior for a Pigeon in controlled scope

### Host Regression Checks

Add or extend tests for:

- live topology details rendering with Pigeon runtime fields
- CLI/runtime-state text showing Pigeon values coherently

### Connected Manual Validation

Create a dedicated procedure, for example:

- `docs/TEST_PROCEDURE_CTRE_PIGEON2_SUPPORT_FIRST_PASS.md`

It should include exact steps for:

1. Presence while inactive
- select profile with Pigeon
- verify not instantiated before activation

2. Activation
- enable teleop
- activate the owning scope
- verify instantiated and visible in runtime-state

3. Static sanity
- robot flat and still
- yaw/pitch/roll are readable
- angular velocities are near zero

4. Yaw motion
- manually rotate robot about vertical axis
- verify yaw changes in the expected direction

5. Tilt motion
- gently tip robot
- verify pitch and/or roll changes

6. Disable/enable teardown
- DS disable
- verify lifecycle/runtime deactivates coherently

## Acceptance Criteria

Purpose: Define done.

The feature is complete when all of these are true:

- a configured Pigeon 2.0 can be selected without errors
- it is not instantiated before explicit activation
- it instantiates on activation through existing lifecycle/runtime paths
- runtime-state exposes the first-pass signal set
- UI details show the signal set coherently
- CLI `show runtime-state` and `show device` reflect the device coherently
- DSL can reference the documented first-pass signal names
- a connected manual procedure passes on real hardware
- no existing non-Pigeon workflows regress

## Risks

Purpose: Surface likely trouble areas early.

- Pigeon API surface may expose multiple frame/reference variants for similar signals
- signal naming can drift if runtime-state and DSL are implemented separately
- calibration state can make “flat robot” expectations look wrong if the procedure is too strict
- singleton/support policy can regress if the device is treated like a plain selected-profile singleton
- CTRE wrappers may encourage over-collection of telemetry and create unnecessary loop cost

## Tradeoffs

Purpose: Explain the chosen first-pass boundary.

Chosen tradeoff:

- implement a narrow, well-tested IMU slice first

Benefits:

- easier to understand
- easier to test by hand
- lower lifecycle/runtime risk
- faster operator value

Cost:

- no advanced heading/fusion/calibration workflow in the first pass
- some teams may want more IMU fields immediately

## Future Extensions

Purpose: Record likely follow-on work.

- add richer fault/status attachments
- expose mount-pose and calibration state readout
- add additional angular/acceleration frame variants if justified
- add reusable IMU abstractions only if more than one IMU family needs them
- add Pigeon-focused DSL examples and templates in the test authoring UI

## Source Notes

Purpose: Record the primary references used for this spec.

Primary vendor references:

- CTRE Phoenix 6 Java API `CorePigeon2`
  - https://api.ctr-electronics.com/phoenix6/stable/java/com/ctre/phoenix6/hardware/core/CorePigeon2.html
- CTRE Phoenix 6 status-signal migration guide
  - https://v6.docs.ctr-electronics.com/en/2025/docs/migration/migration-guide/status-signals-guide.html
- CTRE Pigeon calibration / Tuner documentation
  - https://v6.docs.ctr-electronics.com/en/latest/docs/tuner/pigeon-cal.html

Repo references:

- [src/main/java/frc/robot/BringupUtil.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/BringupUtil.java)
- [src/main/java/frc/robot/BridgeUiCommandHandler.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/BridgeUiCommandHandler.java)
- [src/main/java/frc/robot/BringupRuntime.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/BringupRuntime.java)
- [tools/can_topology/live_topology_view.py](/c:/Users/dmona/swerve3/tools/can_topology/live_topology_view.py)
- [docs/USER_GUIDE_ROBOT_TEST_DSL.md](/c:/Users/dmona/swerve3/docs/USER_GUIDE_ROBOT_TEST_DSL.md)
