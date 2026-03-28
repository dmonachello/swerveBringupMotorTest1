# Feature Spec: Bridge UI + CLI Test Authoring (No Direct JSON Editing)

## Purpose

Provide a Windows-side workflow to create and edit `bringup_tests.json` via the Bridge UI and the Bridge CLI without requiring direct JSON editing. The UI must keep topology visible, allow multi-select device binding, validate tests locally before saving, and output a deployable tests file. The CLI must be context-sensitive (Cisco style) with explicit prompts that reflect the current mode.

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

`bringup_tests.json` remains the canonical persisted format.

The user does not edit JSON directly. Instead, the Bridge UI and Bridge CLI provide structured editing workflows that:

* load JSON into an in-memory test model
* allow editing through UI or CLI commands
* validate the edited model
* write JSON back out on save

### Requirements

* JSON remains the storage and interchange format
* UI and CLI must not require the user to hand-edit JSON
* UI and CLI must use the same parser, validation logic, and JSON writer
* Saving must always produce schema-compatible `bringup_tests.json`

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
* type ("joystick" | "button")
* devices (list of canonical device keys)
* binding:

  * joystick:

    * inputSource (string, required)
    * deadband (float)
  * button:

    * input source (string, required)
      * controller input or UI input
    * duty (float)
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
* Allowed characters: A?Z, a?z, 0?9, underscore
* No spaces in v1
* Case-sensitive (recommended)

### CLI Behavior

* Duplicate name ? error
* Invalid name ? error

---

## Test Set Selection

* UI and CLI must allow choosing which test set to edit or create under `test_sets`.
* Selection determines where new tests are appended and which tests are shown for editing.

---

## Device Source (Windows)

* Use `data/bringup_system.json` as the canonical source for device labels and mappings.
* The active profile determines the available device list.

---

## Device Identity Rules

* UI displays device labels
* Internal model stores canonical key: `VENDOR:TYPE:ID`
* JSON output uses `motorKeys` derived from canonical keys

### Requirement

All device selection must resolve to canonical keys before entering the model.

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
* Must include:

  * duty (required)
  * input source (controller button or UI button)

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

### Requirements

* At least one termination condition is required for button tests

---

## Validation Rules (Windows)

Must pass before saving:

* Required fields present for test type
* Non-empty device list
* Valid canonical device keys
* No duplicate devices
* Valid parameter ranges
* Valid termination configuration

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

* Save locally as `bringup_tests.json`
* Default location: repository root (configurable)
* New test name: append to the selected test set without prompt
* Existing test name: warn and prompt before overwrite (UI and CLI)

---

## CLI Requirements (Cisco Style)

### Prompt and Mode Conventions

* Normal mode: `bringup>`
* Config mode: `bringup(config)#`
* Test config mode: `bringup(config-test-<name>)#`

---

## CLI Commands

### Core Flow

1. `conf t`
2. `test create <name>`
3. `test <name>`
4. `type joystick|button`
5. `device add <vendor:type:id>`
6. joystick only:

   * `inputSource <controller>.<inputId>`
   * `deadband <value>`
7. button only:

   * `inputSource <controller>.<inputId>`
   * or
   * `inputSource ui.<id>`
   * `duty <value>`
8. termination:

   * `termination hold`
   * `termination time <seconds>`
   * `termination rotation <value>`
   * `termination limitswitch <id>`
9. `end`
10. `write tests <path>`

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

* `test create <name>` creates a new test
* `test <name>` enters edit mode
* Changes apply to in-memory model
* `end` exits edit mode without saving
* `write tests` persists all changes

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
