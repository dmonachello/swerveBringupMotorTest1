SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Feature Spec: Bridge UI + CLI Test Authoring (No Direct JSON Editing)

## Purpose

Provide a Windows-side workflow to create and edit bringup tests via the Bridge UI and the Bridge CLI without requiring direct JSON editing. The UI must keep topology visible, allow multi-select device binding, validate tests locally before saving, and output a deployable unified config.

## Group and Targeting V1 Update (April 20, 2026)

Purpose: align authoring behavior with the finalized group/targeting contract.

- Name matching is exact and case-insensitive.
- Device and group names share one global namespace.
- `active` is a reserved group, always present, non-persistent, and reset on save/commit.
- Group membership is set-based with warning/no-op semantics for duplicate add and missing remove.
- Group/device deletion must fail when references still exist in tests/groups.
- Non-interactive copy to existing named groups must fail with no mutation.

SID_COMMENT: Implementation note (current repo)
- Tests are persisted inside `bringup_system.json` under `bridgeConfig.byProfile.<profile>.tests`.
- Standalone `bringup_tests.json` is treated as a legacy import/export format and is not the robotâ€™s primary input.

## Goals

* Eliminate manual JSON editing for test creation and updates.
* Allow creation and editing of tests from the Bridge UI.
* Provide a Cisco-style, context-sensitive CLI for the same operations.
* Validate test syntax and requirements on Windows before saving.
* Keep robot-side behavior and schemas unchanged.
* Prioritize common code and reuse across UI, CLI, validation, and serialization.

## Non-Goals

* RoboRIO-side editing or deployment automation.
* Renaming tests (deferred to a later release).
* Schema or runtime behavior changes on the robot.

---

## Editing and Persistence Model

`bringup_system.json` (bridgeConfig.byProfile.<profile>.tests) is the canonical persisted format.

The user does not edit JSON directly. Instead, the Bridge UI and Bridge CLI provide structured editing workflows that:

* load JSON into an in-memory test model
* allow editing through UI or CLI commands
* validate the edited model
* write JSON back out on save

### Requirements

* JSON remains the storage and interchange format
* UI and CLI must not require the user to hand-edit JSON
* UI and CLI must use the same parser, validation logic, and JSON writer
* Saving must always produce schema-compatible `bringup_system.json` (with tests embedded under bridgeConfig)

---

## Internal Test Model (Bridge)

All UI and CLI operations must operate on a shared in-memory test model.

The model is the single source of truth and is used by:

* UI editor
* CLI commands
* validation engine
* JSON serializer

### Test Object

* name (string, immutable in v1)
* type ("joystick" | "button" | "composite" | "deadbandSweep" | "deviceAction")
* devices (list of canonical device labels)
* binding:

  * joystick:

    * inputSource (string, required)
    * deadband (float)
  * button:

    * input source (string, required)
      * controller input or UI input
    * duty (float)
  * deadband sweep:

    * deadbandSweep fields (startDuty/maxDuty/stepDuty/stepHoldSec/motionThresholdRot/requiredSamples)
    * optional encoderKey/encoderSource/encoderCountsPerRev/encoderMotorIndex
  * device action:

    * action (`toggle_led` | `set_color`)
    * color (`#RRGGBB`, required for `set_color`)
    * pattern (`solid` only in v1)
    * brightness (0.0-1.0)
    * durationSec (seconds; optional)
* termination:

  * hold (bool)
  * time (seconds)
  * rotation (units consistent with robot schema)
  * limitSwitch (all fields supported by existing schema)

### Rules

* UI and CLI must never write JSON directly
* JSON is generated only via a serializer from this model
* Validation operates on this model, not raw JSON

---

## Test Name Rules

* Must be unique within the test set
* Allowed characters: A-Z, a-z, 0-9, underscore
* No spaces in v1
* Case-sensitive (recommended)

### CLI Behavior

* Duplicate name -> error
* Invalid name -> error

---

## Test Set Selection

* UI and CLI must allow choosing which test set to edit or create under `test_sets`.
* Selection determines where new tests are appended and which tests are shown for editing.
* `test set <name>` creates the set if it does not exist (no separate create command).

---

## Device Source (Windows)

* Use `src/main/deploy/bringup_system.json` as the source for device labels and mappings.
* The active profile determines the available device list.

---

## Device Identity Rules

* UI displays device labels
* Internal model stores device labels
* JSON output uses `motorLabels` derived from labels

### Requirements

* All device selection must resolve to labels before entering the model.
* Labels must be unique within the active profile; duplicates are errors.

---

## Device Selection Rules

* Devices may be selected via:

  * topology view
  * device list panel
* Both views must stay in sync
* Devices must be unique within a test
* Duplicate adds are rejected with warning

---

## Binding Semantics

### Joystick Binding

* Continuous control via inputSource
* Maps to:

  * `type: "joystick"`
* Parameters:

  * inputSource
  * deadband

### Button Binding

* Fixed output while active
* Maps to:

  * `type: "composite"`
* CLI accepts `type button` as an alias; JSON output remains `type: "composite"`.
* Must include:

  * duty (required)
  * input source (controller button or UI button)

### Device Action Tests

* Non-motor device actions (LEDs, indicators).
* Maps to:

  * `type: "deviceAction"`
* Required fields:

  * action (`toggle_led` | `set_color`)
* `set_color` fields:

  * color (`#RRGGBB`)
  * pattern (`solid` only in v1)
  * brightness (0.0-1.0)
  * durationSec (seconds; optional)

### Parameter Constraints

* duty must be between -1.0 and 1.0
* deadband must be between 0.0 and 1.0

---

## Input Definitions

### inputSource

* Format: `<controllerName>.<inputId>`
* Controller inputs use WPILib naming:
  * axes: `leftX`, `leftY`, `rightX`, `rightY`, `leftTrigger`, `rightTrigger`
  * buttons: `A`, `B`, `X`, `Y`, `LB`, `RB`, `LS`, `RS`, `START`, `BACK`, `D_UP`, `D_DOWN`, `D_LEFT`, `D_RIGHT`
* UI inputs use `ui.<id>` (arbitrary string)

---

## Termination Rules

Multiple termination conditions are allowed.

### Evaluation Rule

* Termination is satisfied when ANY condition is met (logical OR)
* UI presents termination blocks as independent options; enabling multiple blocks is allowed

### Parameters

* hold:

  * no parameters

* time:

  * duration (seconds, float)

* rotation:

  * target value

* limitSwitch:

  * all fields supported by existing schema

### Limit Switch Commands (CLI)

Purpose: configure limit switch termination behavior in test mode.

Commands:
1. `termination limitswitch [id]` enables the limit switch check (id is optional metadata).
2. `limitswitch onHit <pass|fail>` defines the result when triggered.
3. `limitswitch id <id>` sets or updates the optional id field.

Notes:
- The limit switch check triggers when any selected motor reports a closed forward or reverse limit.
- Limit switches are defined as DIO devices in `bringup_system.json` and referenced by label in `attachments` on the CAN device.
- Either `termination limitswitch` or `limitswitch onHit` enables the limit switch check.
- The optional id is stored in JSON but is not used by the robot runtime yet.
- Validation enforces `onHit` values (`pass` or `fail`) and non-empty ids when provided.

### Requirements

* At least one termination condition is required for button tests

---

## Validation Rules (Windows)

Must pass before saving:

* Required fields present for test type
* Non-empty device list
* Valid canonical device labels
* No duplicate devices
* Valid parameter ranges
* Valid termination configuration
* Valid limit switch configuration (`onHit` and optional `id`)

Warnings (do not block save):

* Device not found in active profile (config drift)

---

## Validation Behavior

* Immediate validation:

  * CLI validates inputs as entered
  * UI validates fields on change

* Pre-save validation:

  * Full validation before writing
  * Save blocked on failure

---

## File Output

* Save locally as `bringup_system.json` (tests embedded under `bridgeConfig.byProfile.<profile>.tests`)
* Default location: `src/main/deploy/bringup_system.json`
* New test name: appended to the selected test set without prompt
* Existing test name: warn and prompt before overwrite (UI and CLI)

---

## Migration Plan (Hard Switch to Labels)

Purpose: move from `motorKeys` to label-only identifiers without ambiguity.

Steps:
1. Update `src/main/deploy/bringup_system.json` to ensure all device labels are unique.
2. Update existing tests to use `motorLabels` only.
3. Deploy the updated `bringup_system.json` (tests embedded under `bridgeConfig.byProfile.<profile>.tests`).
4. Reject any remaining `motorKeys` entries; only `motorLabels` are supported.

Notes:
- Missing label mappings are treated as errors and must be resolved before saving.

---

## CLI Requirements (Cisco Style)

### Prompt and Mode Conventions

* Normal mode: `bringup>`
* Config mode: `bringup(config)#`
* Test config mode: `bringup(config-test-<name>)#`

---

## CLI Commands

Historical note:

- The interactive local authoring flow described below was superseded by DSL file import/export/validate.
- Current supported host-side authoring uses `test import`, `test export`, `test validate`, normalized `show` output, and `tools/can_nt/scripts/dsl_tests_config_tool.py`.

### Core Flow

1. `configure terminal`
2. `test set <name>` (selects or creates the set)
3. historical: `test create <name>` (removed)
4. historical: `test <name>` (removed as a live local editor)
5. historical: `type joystick|button|composite|deadbandSweep|deviceAction`
6. historical: `device add <device label>`
7. historical joystick only:

   * `inputSource <controller>.<inputId>`
   * `deadband <value>`
8. button only:

   * `inputSource <controller>.<inputId>`
   * or
   * `inputSource ui.<id>`
   * `duty <value>`
9. deviceAction only:

   * `action toggle_led|set_color`
   * `color #RRGGBB`
   * `pattern solid`
   * `brightness <value>`
   * `duration <seconds>`
10. termination:

   * `termination hold`
   * `termination time <seconds>`
   * `termination rotation <value>`
   * `termination limitswitch [id]`
   * `limitswitch onHit <pass|fail>`
11. `end`
12. `save config <path>`

### Deadband Sweep Commands (CLI)

Purpose: configure deadband sweep tests in test mode.

Commands:
1. `deadbandSweep startDuty <value>`
2. `deadbandSweep maxDuty <value>`
3. `deadbandSweep stepDuty <value>`
4. `deadbandSweep stepHoldSec <value>`
5. `deadbandSweep motionThresholdRot <value>`
6. `deadbandSweep requiredSamples <value>`
7. Optional encoder fields:
   - `deadbandSweep encoderKey <label|internal>`
   - `deadbandSweep encoderSource <internal|sparkmax_alt|external>`
   - `deadbandSweep encoderCountsPerRev <value>`
   - `deadbandSweep encoderMotorIndex <value>`

---

## Additional CLI Commands

* `test delete <name>`
* `show tests`
* `show test <name>`

---

## CLI Constraints

* Commands only valid in correct mode
* Invalid commands produce:

  * clear error message
  * no state mutation

Examples:

* `inputSource` only valid for joystick/button tests
* `duty` only valid for button tests

---

## Editing Behavior

Current behavior:

* edit DSL source files
* `test import <name> <path>` updates the stored test
* `test export <name> <path>` retrieves the stored source
* `test validate` checks the DSL-backed store

---

## UI/CLI Parity

* All UI operations must exist in CLI
* All CLI operations must be achievable in UI
* No divergence allowed

---

## Backward Compatibility

* JSON output must remain compatible with robot-side schema
* No changes to robot runtime behavior

---

## Tradeoffs

* Offline editing may drift from live robot state
* No rename in v1 requires delete/recreate

---

## Future Extensions

* Add test renaming
* Add direct deploy to roboRIO
* Live profile sync via NetworkTables
* Test templates and presets


