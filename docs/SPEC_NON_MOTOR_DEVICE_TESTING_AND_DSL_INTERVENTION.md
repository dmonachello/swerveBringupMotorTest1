# Spec: Non-Motor Device Testing And DSL Intervention

SPEC_STATUS: PROPOSED

## Purpose

Purpose: define a complete support model for non-motor CAN devices that need active testing, starting with CTRE CANCoder and CTRE Pigeon 2.0.

This spec answers one specific product question:

- how can a DSL test verify a sensor when the required stimulus must come from a human operator or an external robot-side fixture?

This spec does not implement the feature. It defines the implementation-ready contract that code, UI, CLI, topology tooling, and regressions should follow.

## Summary Finding

Purpose: capture the deep-dive result.

CANCoder and Pigeon are not mainly unknown-device-discovery problems.

The repo already has useful passive/profile awareness for both families:

- CANCoder appears in passive profile mapping, topology categories, Java CTRE registration, Java snapshots, and CANCoder text reports.
- Pigeon appears in passive profile mapping and topology categories, and has partial diagnostic inference awareness.

That does not reduce the importance of CAN-bus diagnosis.

These devices can be disconnected, intermittent, duplicated, stale, or electrically isolated by the same CAN-bus failures that affect motor controllers and power devices. Full support must still preserve passive CAN visibility, runtime presence checks, active probe evidence where applicable, and topology-aware fault localization.

The incomplete part is the shared behavioral contract:

- host DSL validation does not normalize inferred CANCoder/Pigeon profile entries into DSL device types
- CANCoder Java runtime reads position, but inferred type `CANCoder` does not match the current DSL type `encoderExternal`
- Pigeon has no complete Java wrapper, snapshot attachment, runtime-state field contract, or DSL signal provider
- UI/runtime helpers mostly understand motor attachments, not generic sensor telemetry
- current DSL has no native blocking prompt/response statement

The right design is a generic non-motor testing contract, not isolated one-off hacks for each device.

## CAN Connectivity Scope

Purpose: make clear that non-motor support still depends on CAN health.

CAN connectivity remains a first-class requirement for CANCoder and Pigeon support.

The statement that these devices are not mainly discovery problems means:

- the repo already knows enough to name and categorize their CAN identities
- the next missing work is semantic testing, runtime telemetry, DSL signals, and operator workflow

It does not mean:

- passive CAN evidence can be skipped
- CAN disconnection is less likely for sensors
- topology fault localization is less relevant for sensors
- runtime readiness can ignore stale or absent CAN traffic

Required behavior:

- passive visibility must show when the device is absent or stale
- runtime state must not publish fake live telemetry for disconnected devices
- DSL tests must fail or remain unrunnable when required devices are not active/testable
- CAN fault-localization evidence must treat sensor devices as normal CAN nodes

## Four-Level Support Contract

Purpose: keep each device family consistent across all bringup layers.

Every supported device family must define these four levels.

| Level | Requirement | CANCoder State | Pigeon 2.0 State |
| --- | --- | --- | --- |
| 1 | Profile/config recognition | Mostly present | Mostly present |
| 2 | Passive CAN visibility/topology | Mostly present | Mostly present |
| 3 | Robot runtime instantiation/snapshot/reporting | Partly present | Missing |
| 4 | DSL/manual workflow semantics and regressions | Incomplete | Missing |

Level 4 is required for a device to be considered testable, not merely visible.

## Current CANCoder State

Purpose: record what is already working and what is risky.

Existing support:

- passive mapping recognizes CTRE manufacturer `4`, device type `7` as `cancoders`
- topology rendering treats `cancoders` as sensor devices
- Java `CtreDeviceGroup` registers `CtreCANCoderDevice`
- Java `CtreCANCoderDevice` instantiates Phoenix 6 `CANcoder`
- Java snapshots include `EncoderAttachment` with absolute degrees
- CANCoder text reports exist
- `DeviceUnit.getPositionRotations()` lets the default DSL read path obtain position

Known gaps:

- Java profile inference returns device type `CANCoder`
- the DSL signal registry exposes external encoder signals under `encoderExternal`
- host DSL validation does not infer CTRE CANCoder entries as `encoderExternal` or as a CANCoder alias
- runtime start-relative `position_delta` semantics only apply to `motor` and `encoderExternal`
- UI runtime-field helpers read top-level and motor attachments, not generic encoder attachments

Implication:

- a CANCoder test may work only when the profile explicitly sets `type: "encoderExternal"`
- an inferred CANCoder can be present and instantiated but not validated or interpreted correctly by DSL tooling

## Current Pigeon 2.0 State

Purpose: record what exists before implementation.

Existing support:

- passive mapping recognizes CTRE manufacturer `4`, device type `4` as `pigeon`
- topology rendering treats `pigeon` as a singleton sensor device
- Java profile inference can return `Pigeon`
- diagnostic LED inference recognizes `Pigeon` and `Pigeon2`
- a proposed Pigeon-specific spec already exists

Known gaps:

- no complete Java `Pigeon2` device wrapper was found
- no Pigeon snapshot attachment exists
- no runtime-state field flattening exists for yaw, pitch, roll, angular velocity, or acceleration
- no DSL signal provider exists for IMU signals
- no host DSL type normalization exists for Pigeon
- no connected manual test procedure exists for Pigeon behavior

Implication:

- Pigeon can be modeled, but it is not yet a first-class bringup runtime or DSL-testable device

## Topo Editor Contract

Purpose: make the profile/topology authoring work explicit.

Topo editor support is part of this feature, not a separate nice-to-have.

Current observed support:

- `can_top_models.py` includes `cancoders` in bucket categories
- `can_top_models.py` includes `pigeon` in singleton categories
- `can_top_editor.py` maps CAN device type `7` to category `cancoders`
- `can_top_editor.py` maps CAN device type `4` to category `pigeon`
- `can_top_editor.py` renders CTRE encoder devices as `CANCoder`
- `can_top_editor.py` renders CTRE gyro devices as `Pigeon`
- `can_top_editor.py` recognizes `CANCODER`, `ENCODER`, `PIGEON`, `IMU`, and `GYRO` text when deriving CAN device type IDs
- `can_top_editor.py` treats `cancoders` and `pigeon` as low-power CAN endpoint categories
- `can_top_editor.py` includes `cancoders` and `pigeon` in sensor layout grouping
- `live_topology_view.py` and shared topology rendering already classify these categories as sensors

Known Topo editor gaps:

- Pigeon/IMU/Gyro names do not yet map to the canonical DSL device type `imu`
- manual Add Node behavior still needs explicit regression coverage for CANCoder and Pigeon
- inventory drag/drop into a profile needs explicit regression coverage for CANCoder and Pigeon
- save/load round-trip must preserve manufacturer, CAN device type, CAN ID, model, category, tags, and singleton behavior
- live topology details must display runtime sensor fields once the runtime-state contract adds them
- CAN table import currently creates label-only placeholder entries, so it cannot be treated as full CANCoder/Pigeon identity support without enrichment or editor follow-up

Required Topo editor behavior:

- operators can create or load a CANCoder node with CTRE manufacturer, device type `7`, sensor category, CAN ID, and optional tags
- operators can create or load a Pigeon node with CTRE manufacturer, device type `4`, singleton sensor category, CAN ID, and optional tags
- CANCoder and Pigeon nodes can be placed on the CAN bus and linked in topology like other CAN nodes
- CANCoder and Pigeon nodes can receive low-power wiring links where that workflow applies
- Pigeon singleton replacement behavior remains explicit and does not silently create duplicate Pigeon singleton nodes
- generated profile entries remain compatible with Java runtime, host DSL validation, and passive visibility
- topology save/load does not rewrite CANCoder into a generic encoder in a way that loses vendor identity
- topology save/load does not rewrite Pigeon into a generic gyro in a way that loses vendor identity

Regression requirement:

- add tests for CANCoder and Pigeon manual node creation payloads
- add tests for CANCoder and Pigeon profile load/save round-trip
- add tests for inventory drop or imported-profile flows when those paths are used
- add tests for live topology category, vendor, device type, and runtime overlay fields

## Vendor Signal Reality

Purpose: align the first-pass contract with the current vendor API surface.

Phoenix 6 exposes enough first-pass telemetry for both devices through robot-side Java APIs.

CANCoder first-pass signals:

- absolute position
- relative position
- velocity
- supply voltage and fault metadata when needed

Pigeon 2.0 first-pass signals:

- yaw
- pitch
- roll
- world-frame angular velocity
- device-frame angular velocity when useful
- acceleration including gravity
- supply voltage and fault metadata when needed

Design rule:

- active test semantics should read these through robot-side wrappers and the DSL signal interface
- passive CAN decoding should remain discovery/evidence only unless a later reverse-engineering stage explicitly promotes decoded fields

## DSL Fit

Purpose: explain what the existing DSL can and cannot do.

The current DSL is a live rule set, not a blocking script.

It already supports:

- `init`, `main`, and `close` phases
- per-tick conditions
- `require`, `until`, `success`, and `abort`
- boolean operator confirmation through existing input devices, such as `controller0.A`
- run-scoped aggregate signals such as `position_delta_max_abs`

It does not support:

- `prompt`
- `wait for operator`
- arithmetic expressions
- nested expressions
- function calls such as `abs(...)`
- ordered step-by-step user interactions inside `main`

Conclusion:

- first-pass non-motor tests should use derived signals instead of expanding the expression grammar
- examples must not use `abs(...)` unless the DSL expression layer is intentionally extended first

## Human Intervention Model

Purpose: define how human or fixture stimulus should interact with DSL tests.

Some non-motor devices cannot prove behavior unless something external moves them.

Examples:

- rotate a CANCoder shaft or swerve module by hand
- rotate the robot about vertical axis to test Pigeon yaw
- tip the robot or sensor mount to test Pigeon pitch and roll

The DSL should not block the robot control loop waiting for UI input.

First-pass model:

- UI/CLI/test description presents the operator action before or during the test
- the DSL observes live sensor signals
- pass/fail is based on objective signal evidence only
- operator confirmation is not part of the first-pass sensor test contract

Later model:

- add normalized prompt metadata if operator prompts need to become first-class test artifacts
- keep prompt state outside the 20 ms robot loop
- make the UI/CLI own rendering and acknowledgement transport
- keep the robot test engine evaluating signals every tick

## Prompt And Instructions

Purpose: define how operator instructions appear without changing the DSL into a blocking script.

The first implementation does not add a blocking DSL `prompt` statement.

Required first-pass behavior:

- operator instructions may be carried as test metadata or UI/CLI presentation metadata
- UI/CLI should display the required human action before or during the run
- sensor tests still pass only from live hardware evidence
- lack of operator acknowledgement is not a success path

Possible later extension:

- add first-class normalized prompt metadata if the workflow needs UI acknowledgement during an active run
- keep prompt state outside the 20 ms robot loop
- do not convert the DSL into a blocking script

## Device Type Normalization

Purpose: prevent Java runtime, host validation, UI, and docs from disagreeing about the same device.

The system needs a shared alias policy.

Chosen policy:

- `encoderExternal` is the canonical DSL family for CANCoder-style external encoder behavior
- `CANCoder` is a vendor/device alias that maps to `encoderExternal` for DSL signal validation and delta semantics
- `imu` is the canonical DSL family for Pigeon-style IMU behavior
- `Pigeon` and `Pigeon2` are vendor/device aliases that map to `imu`

Rules:

- use canonical semantic types with explicit aliases
- keep vendor/product identity in `manufacturer`, `deviceType`, and `model`
- keep vendor-facing names in display labels, topology surfaces, and reports
- keep the saved config `type` field semantic, not vendor-branded, when normalization is available

## Proposed Signal Contract

Purpose: expose useful non-motor signals without expanding the DSL expression grammar first.

### CANCoder

Use the existing external encoder signal family:

| Signal | Value type | Meaning |
| --- | --- | --- |
| `position` | number | test-start-relative position in rotations |
| `position_actual` | number | absolute current position in rotations |
| `position_delta` | number | test-start-relative position in rotations |
| `position_delta_max_abs` | number | largest absolute position delta observed during the run |
| `velocity` | number | current velocity in rotations per second |
| `velocity_max_abs` | number | largest absolute velocity observed during the run |

Compatibility rule:

- `velocity` is part of the first-pass contract
- do not fake velocity from successive position samples unless a shared sampled-signal contract owns it

### Pigeon 2.0

Use a new IMU signal family:

| Signal | Value type | Meaning |
| --- | --- | --- |
| `yaw` | number | current yaw in degrees |
| `pitch` | number | current pitch in degrees |
| `roll` | number | current roll in degrees |
| `yaw_delta` | number | yaw minus test-start yaw |
| `pitch_delta` | number | pitch minus test-start pitch |
| `roll_delta` | number | roll minus test-start roll |
| `yaw_delta_max_abs` | number | largest absolute yaw delta observed during the run |
| `pitch_delta_max_abs` | number | largest absolute pitch delta observed during the run |
| `roll_delta_max_abs` | number | largest absolute roll delta observed during the run |
| `angular_velocity_x` | number | world-frame X angular velocity in degrees per second |
| `angular_velocity_y` | number | world-frame Y angular velocity in degrees per second |
| `angular_velocity_z` | number | world-frame Z angular velocity in degrees per second |
| `accel_x` | number | X acceleration in g, including gravity unless documented otherwise |
| `accel_y` | number | Y acceleration in g, including gravity unless documented otherwise |
| `accel_z` | number | Z acceleration in g, including gravity unless documented otherwise |
| `supply_voltage` | number | supply voltage when available |
| `faults` | boolean | readable and clearable fault summary using the same semantics as existing supported devices |

First-pass contract:

- implement the full signal list above
- `yaw`, `pitch`, and `roll` are absolute live readings from the device
- `yaw_delta`, `pitch_delta`, and `roll_delta` are current reading minus the value captured at test start
- acceleration is first-pass DSL-visible and is expressed in `g`

## Runtime-State Contract

Purpose: keep UI, CLI, and DSL evidence consistent.

Runtime state should continue to expose every device through the common `devices[]` model.

Add generic sensor telemetry in one shared way:

- top-level fields that reuse the exact DSL-style names
- attachments for structured device-family telemetry
- one shared host helper that can read top-level fields and sensor attachments

Required attachments:

- `encoder` for CANCoder-style encoder telemetry
- `imu` for Pigeon-style orientation and inertial telemetry

Required CANCoder top-level fields:

- `position`
- `position_actual`
- `position_delta`
- `position_delta_max_abs`
- `velocity`
- `velocity_max_abs`
- `lastError`
- `faults`

Required Pigeon top-level fields:

- `yaw`
- `pitch`
- `roll`
- `yaw_delta`
- `pitch_delta`
- `roll_delta`
- `yaw_delta_max_abs`
- `pitch_delta_max_abs`
- `roll_delta_max_abs`
- `angular_velocity_x`
- `angular_velocity_y`
- `angular_velocity_z`
- `accel_x`
- `accel_y`
- `accel_z`
- `supply_voltage`
- `lastError`
- `faults`

Rule:

- do not add one private interpretation path in UI and another path in CLI
- a shared runtime device-field helper must understand the new sensor attachments
- runtime-state field keys should reuse the exact DSL-style names everywhere they are surfaced

## Runnable State Contract

Purpose: define when sensor tests may start and which state owner wins.

`UNRUNNABLE` means the runtime path cannot talk to one or more required devices well enough to start the test safely.

Runnable state is owned by runtime readiness, not passive evidence.

Required pre-run conditions:

- selected test devices active
- device instantiated
- device testable
- recent CAN presence
- fresh runtime telemetry sample
- no stale/error flag blocking communication

Rules:

- runtime evidence wins over passive evidence for runnable state
- generic readiness is enough before launch; no pre-run threshold on a sensor-specific value is required
- the freshness threshold for a runtime telemetry sample is `250 ms` maximum age
- if generic runtime communication is not available before launch, the test is `UNRUNNABLE`
- if the device was runnable enough to start but required live signals later go null, stale, or unreadable, the run result is `FAIL_NO_SENSOR_RESPONSE`

## Result And State Contract

Purpose: define the shared top-level DSL test state and result vocabulary.

Top-level states and results:

- `UNRUNNABLE`
- `READY_TO_RUN`
- `RUNNING`
- `PASS_SENSOR_PROVEN`
- `PASS`
- `FAIL_NO_SENSOR_RESPONSE`
- `FAIL_ABORT_CONDITION`
- `FAIL_REQUIRE_NOT_MET`
- `FAIL_UNTIL_TIMEOUT`
- `FAIL_SET_FALLBACK_ACTIVE`
- `FAIL_DEVICE_NOT_FOUND`
- `FAIL_UNSUPPORTED_SIGNAL`
- `FAIL_RUNTIME_COMMUNICATION`
- `FAIL_CLEAR_FAULTS`
- `INTERRUPTED`

Rules:

- `UNRUNNABLE` is both a visible pre-run state and a possible attempted-run outcome
- `READY_TO_RUN` means the shared runnable-state rules currently allow launch
- `RUNNING` means the test has been accepted and started
- `PASS_SENSOR_PROVEN` is the normal success result for objective hardware/device evidence across all device families
- `PASS` remains available for non-hardware or non-sensor-proof success paths when they legitimately exist
- `FAIL_ABORT_CONDITION` means an authored `abort` fired
- `FAIL_REQUIRE_NOT_MET` means a normal stop occurred without all `require` conditions latching
- `FAIL_UNTIL_TIMEOUT` means the run hit its bounded end without the expected evidence pattern and the failure is not better classified elsewhere
- `FAIL_SET_FALLBACK_ACTIVE` means a signal-driven `set` remained on fallback at the decisive stop point
- `FAIL_DEVICE_NOT_FOUND` means a declared device could not be resolved
- `FAIL_UNSUPPORTED_SIGNAL` means the authored signal/read/write/clear path is unsupported at runtime
- `FAIL_RUNTIME_COMMUNICATION` means generic runtime communication failed in a way not better classified as sensor no-response
- `FAIL_NO_SENSOR_RESPONSE` means the run started, but required live sensor signals were missing, stale, or stopped responding
- `FAIL_CLEAR_FAULTS` means a fault-clear action failed
- `INTERRUPTED` remains reserved for disable, estop, or external/manual stop

Cross-surface rule:

- the Run button state and the test-state panel must stay in sync
- both must use the same shared rule code

## Operator Workflow Scenarios

Purpose: define common workflows that implementation and tests must cover.

### Scenario 1: CANCoder Presence Without Activation

Operator action:

- select a profile containing a CANCoder
- do not activate runtime scope

Expected behavior:

- topology/profile surfaces show the configured CANCoder
- runtime state does not claim it is instantiated
- DSL tests requiring it are not runnable until the selected-test scope is active

Regression requirement:

- host and Java tests must assert profile visibility does not imply instantiation

### Scenario 2: CANCoder Manual Rotation

Operator action:

- activate the selected-test scope containing the CANCoder
- rotate the encoder shaft or module by hand

Expected behavior:

- runtime state shows the CANCoder active/instantiated
- `position_delta_max_abs` increases
- test passes only after objective position movement evidence is observed

Regression requirement:

- Java DSL runtime test must prove CANCoder aliasing uses encoder delta semantics
- host validator test must accept a CTRE device type `7` CANCoder as an encoder test device

### Scenario 3: Pigeon Presence Without Activation

Operator action:

- select a profile containing Pigeon 2.0
- do not activate runtime scope

Expected behavior:

- topology/profile surfaces show the configured Pigeon
- runtime state does not claim it is instantiated
- runnable-state logic stays identical to other selected-test devices

Regression requirement:

- host tests must assert Pigeon visibility and selected-test readiness use the same shared active-scope rules

### Scenario 4: Pigeon Yaw Turn

Operator action:

- activate the selected-test scope containing Pigeon 2.0
- rotate the robot or sensor about the vertical axis

Expected behavior:

- runtime state shows yaw changing
- `yaw_delta_max_abs` crosses the authored threshold
- the test can pass without `abs(...)`

Regression requirement:

- Java DSL runtime test must prove IMU delta aggregate semantics
- host DSL validation must accept the same signal names exported by Java

### Scenario 5: Pigeon Pitch/Roll Tilt

Operator action:

- activate the selected-test scope containing Pigeon 2.0
- tilt the robot or sensor in the documented direction

Expected behavior:

- runtime state shows pitch or roll changing
- directional tests can run without expression functions
- max-absolute delta tests can prove movement independent of sign

Regression requirement:

- Java DSL runtime test must prove `pitch_delta_max_abs` and `roll_delta_max_abs`
- operator procedure must define the physical direction used for any sign-sensitive test

## Regression Lockstep Rule

Purpose: prevent the spec and regression coverage from drifting.

Every scenario in `Operator Workflow Scenarios` must have a matching named entry in the regression plan before implementation is called complete.

The names should stay aligned:

| Spec Scenario | Required Regression Entry |
| --- | --- |
| CANCoder Presence Without Activation | CANCoder Presence Without Activation |
| CANCoder Manual Rotation | CANCoder Manual Rotation |
| Pigeon Presence Without Activation | Pigeon Presence Without Activation |
| Pigeon Yaw Turn | Pigeon Yaw Turn |
| Pigeon Pitch/Roll Tilt | Pigeon Pitch/Roll Tilt |

If one list changes, the other must change in the same commit.

Recommended automated guard:

- add a lockstep unit test similar to the UI runtime workflow lockstep guard
- compare scenario headings in this spec with headings in the regression runner guide or a dedicated non-motor regression plan

## Regression Plan

Purpose: define the tests that should land with implementation.

### Java Unit Tests

Required tests:

- DSL registry includes the CANCoder/encoder and IMU signal contracts
- CANCoder inferred type or alias maps to encoder delta semantics
- Pigeon/Pigeon2 alias maps to the IMU signal provider
- IMU delta and max-absolute aggregate signals are run-scoped
- runtime-state shaping includes CANCoder encoder fields
- runtime-state shaping includes Pigeon orientation fields
- Pigeon wrapper does not instantiate on profile selection
- top-level result/state enums follow the shared contract above

### Host Unit Tests

Required tests:

- `resolve_profile_device_dsl_type` maps CTRE device type `7` to the CANCoder/encoder DSL type
- `resolve_profile_device_dsl_type` maps CTRE device type `4` to the IMU DSL type
- host signal catalog exposes exactly the Java-exported non-motor signals
- validator accepts valid CANCoder and Pigeon examples
- validator rejects `abs(...)` examples until expression support is intentionally added
- UI runtime-field helper reads encoder and IMU attachments through shared code
- `UNRUNNABLE` disables run actions and drives the test-state panel through the same shared rule code

### Topology And Cross-Surface Tests

Required tests:

- topology editor keeps CANCoder and Pigeon category/type mappings stable
- topology editor can create CANCoder and Pigeon nodes without losing CTRE manufacturer/device type identity
- topology editor save/load round-trip preserves CANCoder and Pigeon CAN ID, model, category, singleton/bucket behavior, and tags
- topology inventory-drop or import paths preserve CANCoder and Pigeon identities when source data provides those identities
- live topology details render configured and runtime sensor values consistently
- CLI, UI, and profile loader agree on labels, vendor, type, and id

### Connected Manual Tests

Required procedures:

- CANCoder manual shaft/module rotation
- Pigeon yaw turn
- Pigeon pitch/roll tilt
- disabled/activated lifecycle teardown for both devices

Connected tests should be marked hardware-required unless they can run against a fake runtime-state fixture.

## Candidate DSL Examples

Purpose: show what valid first-pass tests should look like.

### CANCoder Movement

```text
test "cancoder_manual_rotation"
device "swerve-front-left-cancoder"

main:
    until timer.elapsed >= 5.0
    require "swerve-front-left-cancoder".position_delta_max_abs > 0.05
```

### Pigeon Yaw

```text
test "pigeon_yaw_turn"
device "IMU (Pigeon2)"

main:
    until timer.elapsed >= 8.0
    require "IMU (Pigeon2)".yaw_delta_max_abs > 15.0
```

### Pigeon Pitch

```text
test "pigeon_pitch_tilt"
device "IMU (Pigeon2)"

main:
    until timer.elapsed >= 8.0
    require "IMU (Pigeon2)".pitch_delta_max_abs > 5.0
```

## Combined DSL Examples

Purpose: show how the new devices should combine with existing motors, limit switches, controllers, and power devices in authored tests.

These examples are target authored DSL examples for the implemented contract in this spec.

### Falcon And CANCoder Agree On Rotation

```text
test "falcon_and_cancoder_agree_on_rotation"
device "FALCON 9"
device "swerve-front-left-cancoder"

main:
    set "FALCON 9".output = 0.12
    abort "FALCON 9".current_actual > 25
    until timer.elapsed >= 2.5
    require "FALCON 9".position_delta_max_abs > 0.20
    require "swerve-front-left-cancoder".position_delta_max_abs > 0.05
    require "swerve-front-left-cancoder".velocity_max_abs > 0.02
```

### Spark And CANCoder Manual Rotation

```text
test "spark_and_cancoder_manual_rotation"
device "SPARKMAX/NEO 25"
device "swerve-front-right-cancoder"

main:
    set "SPARKMAX/NEO 25".output = 0.10
    abort "SPARKMAX/NEO 25".current_actual > 20
    until timer.elapsed >= 2.0
    require "SPARKMAX/NEO 25".position_delta_max_abs > 0.15
    require "swerve-front-right-cancoder".position_delta_max_abs > 0.05
```

### Pigeon Yaw While Driving

```text
test "pigeon_yaw_while_driving"
device "FALCON 9"
device "IMU (Pigeon2)"

main:
    set "FALCON 9".output = 0.10
    abort "FALCON 9".current_actual > 25
    until timer.elapsed >= 4.0
    require "FALCON 9".position_delta_max_abs > 0.25
    require "IMU (Pigeon2)".yaw_delta_max_abs > 10.0
    require "IMU (Pigeon2)".angular_velocity_z > 1.0
```

### Pigeon Pitch Changes When Robot Tilts

```text
test "pigeon_pitch_changes_when_robot_tilts"
device "IMU (Pigeon2)"
device "controller0"

main:
    abort timer.elapsed >= 8.0
    success "IMU (Pigeon2)".pitch_delta_max_abs > 5.0
```

### Run To Limit With Pigeon Monitor

```text
test "run_to_limit_with_pigeon_monitor"
device "FALCON 9"
device "lmtSw0"
device "IMU (Pigeon2)"

main:
    set "FALCON 9".output = 0.15
    abort "FALCON 9".current_actual > 30
    abort "IMU (Pigeon2)".roll_delta_max_abs > 8.0
    success lmtSw0.pressed
    require "FALCON 9".position_delta_max_abs > 0.10
```

### CANCoder Fault Clear Then Manual Check

```text
test "cancoder_fault_clear_then_manual_check"
device "swerve-back-left-cancoder"

init:
    clear "swerve-back-left-cancoder".faults

main:
    until timer.elapsed >= 6.0
    require "swerve-back-left-cancoder".position_delta_max_abs > 0.05
```

### Pigeon Static Sanity

```text
test "pigeon_static_sanity"
device "IMU (Pigeon2)"
device "pdp"

main:
    abort pdp.channel0_fault
    abort "IMU (Pigeon2)".faults
    until timer.elapsed >= 2.0
    require "IMU (Pigeon2)".angular_velocity_z between -1.0 1.0
    require "IMU (Pigeon2)".accel_z between 0.8 1.2
```

## Implementation Slices

Purpose: define a safe order of work.

### Slice 1: CANCoder DSL Normalization

Scope:

- centralize CANCoder aliasing to `encoderExternal` or another chosen canonical type
- make host validation and Java runtime agree
- ensure `position_delta` and `position_delta_max_abs` are start-relative for inferred CANCoder devices
- add narrow Java and Python regressions

Why first:

- CANCoder already has the most runtime support
- this is the smallest slice that proves the alias pattern

### Slice 1A: Topo Editor Authoring Audit

Scope:

- verify CANCoder manual Add Node, inventory drop, profile load, and profile save
- verify Pigeon manual Add Node, inventory drop, profile load, and profile save
- add missing topology-editor regressions before changing runtime semantics
- add Pigeon DSL type mapping to the canonical `imu` type

Why early:

- profile/topology authoring must preserve vendor identity before runtime and DSL layers can rely on it

### Slice 2: Generic Sensor Runtime Helpers

Scope:

- add shared runtime-state helpers for encoder and IMU attachments
- update UI helpers to read non-motor attachments through common code
- avoid device-specific UI branches when fields can be normalized

Why second:

- Pigeon should plug into a generic path instead of creating its own UI-only path

### Slice 3: Pigeon Wrapper And Snapshot

Scope:

- add a CTRE Pigeon 2.0 wrapper
- register it in CTRE device group
- add an IMU attachment
- read first-pass Phoenix status signals
- expose presence, faults, and core orientation signals

Why third:

- wrapper output shape should be guided by the generic sensor runtime contract

### Slice 4: IMU DSL Signal Provider

Scope:

- add canonical IMU DSL type
- add Pigeon/Pigeon2 aliases
- add yaw/pitch/roll and delta aggregate signals
- update generated host signal artifact
- update DSL docs

Why fourth:

- the runtime wrapper and host catalog must agree on exact signal names

### Slice 5: Operator Workflow And Regression Docs

Scope:

- add exact manual procedures
- add lockstep regression entries
- add an automated guard for scenario/regression heading alignment

Why fifth:

- tests for human-intervention devices are incomplete without procedures

## Failure Modes

Purpose: define what the operator should be able to distinguish.

Common non-motor failure modes:

- configured but not present on CAN
- visible passively but not robot-instantiable
- instantiated but status signal stale
- wrong CAN ID or duplicate CAN ID
- wrong physical sensor moved
- correct sensor moved in opposite direction from procedure
- CANCoder absolute position changes but delta semantics are not test-relative
- Pigeon yaw/pitch/roll values exist but mounting calibration makes sign expectations wrong
- a future workflow accidentally reintroduces operator-confirmation success for tests that should remain sensor-proven

UI/CLI should make these separable where practical.

## Acceptance Criteria

Purpose: define done for full support.

Full CANCoder support is done when:

- CANCoder appears in profile, topology, passive visibility, runtime-state, UI details, CLI reports, DSL validation, and DSL runtime with one coherent device type policy
- `position_delta_max_abs` can prove manual rotation from a selected-test DSL run
- profile selection alone never instantiates the device
- regression coverage exists for the matching workflow scenarios

Full Pigeon 2.0 support is done when:

- Pigeon appears in profile, topology, passive visibility, runtime-state, UI details, CLI reports, DSL validation, and DSL runtime with one coherent device type policy
- yaw, pitch, and roll tests can pass from objective signal movement without `abs(...)`
- activation and deactivation follow the same lifecycle rules as other selected-test devices
- regression coverage exists for the matching workflow scenarios

## Resolved Decisions

Purpose: record the implementation choices fixed by design review.

- `CANCoder` remains an alias of canonical DSL type `encoderExternal`
- `Pigeon` and `Pigeon2` remain aliases of canonical DSL type `imu`
- exact DSL-style names are reused across DSL, runtime-state, UI, CLI, and generated artifacts
- Pigeon acceleration is first-pass DSL-visible
- sensor tests use objective evidence only; operator confirmation is not part of the first-pass pass criteria
- runnable state is owned by runtime readiness
- the runtime telemetry freshness threshold for runnable gating is `250 ms`
- a test is `UNRUNNABLE` before launch when runtime communication is not good enough to talk to the device
- a started test becomes `FAIL_NO_SENSOR_RESPONSE` if required live sensor signals later go missing or stale
- fault semantics and fault clearing should match existing supported-device behavior
- fault-clear failure result is `FAIL_CLEAR_FAULTS`
- `clear faults` remains restricted the same way existing devices are restricted
- top-level result/state enums change now; no backward-compatibility layer is required
- Run button state and the test-state panel must stay in sync through the same shared rule code

## Tradeoffs

Purpose: make the design choice explicit.

Preferred tradeoff:

- add derived signal names and metadata before adding a richer expression language

Benefits:

- lower parser/schema risk
- easier host validation
- easier Java runtime testing
- no `abs(...)` support required for common manual movement tests

Cost:

- the signal catalog grows
- advanced test authors may eventually want real expressions

Alternative tradeoff:

- add expression functions such as `abs(...)`

Benefits:

- fewer derived signal names
- more expressive DSL

Cost:

- parser, normalized schema, validator, Java execution, examples, and regression fixtures all change together
- more opportunities for host/robot disagreement

## Future Extensions

Purpose: record work that should not block first-pass support.

Possible later improvements:

- first-class `prompt` or `instruction` DSL metadata
- UI acknowledgement transport for active tests
- richer IMU calibration and mount-orientation reporting
- Pigeon magnetometer signal support after calibration workflow exists
- generic sensor trend panels in the UI
- passive CAN semantic decoding for Pigeon/CANCoder after controlled capture experiments

## Source References

Purpose: record the main evidence used for this audit.

Repo references:

- [docs/SPEC_CTRE_PIGEON2_SUPPORT.md](/c:/Users/dmona/swerve3/docs/SPEC_CTRE_PIGEON2_SUPPORT.md)
- [docs/SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md](/c:/Users/dmona/swerve3/docs/SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md)
- [docs/USER_GUIDE_ROBOT_TEST_DSL.md](/c:/Users/dmona/swerve3/docs/USER_GUIDE_ROBOT_TEST_DSL.md)
- [docs/ADD_A_NEW_DEVICE.md](/c:/Users/dmona/swerve3/docs/ADD_A_NEW_DEVICE.md)
- [src/main/java/frc/robot/BringupUtil.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/BringupUtil.java)
- [src/main/java/frc/robot/manufacturers/CtreDeviceGroup.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/manufacturers/CtreDeviceGroup.java)
- [src/main/java/frc/robot/devices/ctre/CtreCANCoderDevice.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/devices/ctre/CtreCANCoderDevice.java)
- [src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java)
- [src/main/java/frc/robot/tests/dsl/DslBringupTest.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/tests/dsl/DslBringupTest.java)
- [tools/common/robot_test_dsl/service.py](/c:/Users/dmona/swerve3/tools/common/robot_test_dsl/service.py)
- [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerve3/tools/can_nt/bringup_ui.py)
- [tools/can_topology/live_topology_view.py](/c:/Users/dmona/swerve3/tools/can_topology/live_topology_view.py)

Vendor references:

- CTRE Phoenix 6 Pigeon2 Java API: <https://api.ctr-electronics.com/phoenix6/stable/java/com/ctre/phoenix6/hardware/core/CorePigeon2.html>
- CTRE Phoenix 6 CANcoder Java API: <https://api.ctr-electronics.com/phoenix6/latest/java/com/ctre/phoenix6/hardware/core/CoreCANcoder.html>
- CTRE Pigeon 2.0 hardware reference: <https://v6.docs.ctr-electronics.com/en/stable/docs/hardware-reference/pigeon2/index.html>
- CTRE Pigeon 2.0 calibration reference: <https://v6.docs.ctr-electronics.com/en/latest/docs/tuner/pigeon-cal.html>
