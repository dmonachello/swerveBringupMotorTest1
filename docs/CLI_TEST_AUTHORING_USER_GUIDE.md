# CLI Test Authoring User Guide

## Purpose
Provide a step-by-step, no-JSON workflow for creating and editing bringup tests using Robot Test DSL import/export/validate through the Bridge CLI.

## Group and Targeting V1 Update (April 20, 2026)

Purpose: document test-authoring assumptions that now depend on finalized group/targeting behavior.

- Target name lookup is exact and case-insensitive.
- Device and group names share one global namespace.
- `active` is reserved, always available, non-persistent, and resets on save/commit.
- Group membership is set-based with warning/no-op semantics for duplicates/missing removals.
- Group and device deletion must fail while references remain in tests/groups.
- Non-interactive copy into existing named groups must fail with no mutation.

## Audience
Operators and developers who want to add tests without editing JSON.

## Before You Start
Purpose: ensure the CLI can resolve devices and save tests correctly.

Checklist:
1. Use a working copy of the repo on Windows.
2. Confirm `src/main/deploy/bringup_system.json` matches the profile you want to use.
3. Confirm `src/main/deploy/bringup_bindings.json` defines controller names you want to reference.
4. Decide which test set under `test_sets` you will edit or create.
5. Decide where to save the updated unified config (usually `src/main/deploy/bringup_system.json`).
6. If you are testing a new device label, add it to the active profile first (see “Add a Device to the Active Profile” below).

## Core Concepts
Purpose: explain the minimum mental model for authoring.

Key ideas:
1. The CLI imports and validates DSL-backed tests against the in-memory config model.
2. Tests are persisted inside `bringup_system.json` under `bridgeConfig.byProfile.<profile>.tests`.
3. Devices are chosen from `src/main/deploy/bringup_system.json`.
4. Test names are unique within a test set.
5. Inputs use a unified `inputSource` format: `controllerName.inputId`.
6. `show workspace` reveals which tests file is loaded and whether it is dirty.
7. `validate tests --active-set` limits validation to the current test set.

## Modes and Prompts
Purpose: show how the CLI indicates context.

Prompts:
- `bringup>` is normal mode.
- `bringup(config)#` is config mode.
- Test authoring does not use a live local `config-test` edit mode anymore.
- Use DSL source files plus `test import` and `show test ... normalized`.

## Command Syntax Notation
Purpose: explain required vs optional parameters in examples.

Notation:
- `<name>` required value.
- `[name]` optional value.
- `{item}` repeatable value (zero or more).
- `|` choice between options.

Example:
- `termination limitswitch [id]` means the id is optional.

## Selecting a Test Set
Purpose: ensure tests are created in the intended set.

Commands:
1. `test set <name>` selects a test set.

Notes:
- If the set does not exist, the CLI creates it automatically.
- New tests are appended to the selected set.
- Existing tests in other sets are not modified unless selected.

## Templates and Loading
Purpose: start from a template or load an existing tests file.

Commands:
1. `tests templates` lists available templates.
2. `tests load template <name>` loads a template into the editor.
3. `tests load <path>` loads an existing tests JSON.
4. `save config <path>` writes `bringup_system.json` with the edited tests included.

Notes:
- Templates live under `tools/test_template_wizard/test_templates`.
- Loading replaces the in-memory tests model.

## Device Selection
Purpose: bind tests to device labels from the active profile.

Rules:
1. Devices are referenced by their label from `bringup_system.json`.
2. The CLI resolves labels from `src/main/deploy/bringup_system.json`.
3. Duplicate device adds are rejected with a warning.
4. Duplicate labels in the active profile are errors.
5. A device must exist in the active profile with required fields (CAN: `deviceInterface`, `manufacturer`, `deviceType`, `id`) before tests can reference it.

Examples:
1. `device add SPARKMAX/NEO 25`
2. `device add FALCON 9`

## Input Sources
Purpose: define how tests are started or controlled.

Format:
- `inputSource <controllerName>.<inputId>`

Inputs:
- Axes: `leftX`, `leftY`, `rightX`, `rightY`, `leftTrigger`, `rightTrigger`
- Buttons: `A`, `B`, `X`, `Y`, `LB`, `RB`, `LS`, `RS`, `START`, `BACK`, `D_UP`, `D_DOWN`, `D_LEFT`, `D_RIGHT`

Examples:
1. `inputSource controller0.leftY`
2. `inputSource controller1.A`
3. `inputSource tech.D_LEFT`

Notes:
- Controller names come from `bringup_bindings.json`.
- Default controller names are `controller0` through `controller5` when omitted in bindings.
- In the current workflow, this input form is expressed inside DSL source or normalized output, not as a live local `inputSource` edit command.

## Add a Device to the Active Profile
Purpose: ensure a new device label is usable in tests.

Example (new REV NEO motor on CAN ID 26):
```
configure terminal
profile home_tests_033026
device "Feeder Motor"
set interface CAN
set manufacturer 5
set deviceType 2
set id 26
set model "REV NEO"
set type motor
exit
save profiles src/main/deploy/bringup_system.json
```

Notes:
- Use numeric manufacturer/deviceType IDs (REV=5, MotorController=2).
- If this step is skipped, imported DSL tests that reference `"Feeder Motor"` will fail validation because the label is not present in the active profile.

## Current Workflow

Purpose: explain the supported workflow before listing examples.

Legacy local interactive test authoring was removed.

The current supported workflow is:

1. Write or edit a `.dsl` source file.
2. Import it with `test import`.
3. Validate it with `test validate`.
4. Inspect it with `show test <name>` and `show test <name> normalized`.

Use `tools/can_nt/scripts/dsl_tests_config_tool.py` for import/export/validate helper workflows.

Do not use the following removed workflow as if it were current:

- `test create <name>`
- `test <name>` as a live local editor
- `type ...`
- `device add ...`
- `inputSource ...`
- `deadband ...`
- `duty ...`
- `termination ...`

## Test Types

Purpose: choose the correct DSL pattern for the behavior you want.

Joystick-like tests:
- Use `set <device>.<signal> = controller.input deadband ... scaled ... default ...`.

Button-like tests:
- Use fixed-value `set` statements with `abort`, `require`, `success`, and `until` conditions.

Deadband sweep tests:
- Use the dedicated DSL/runtime support documented in the DSL guides and normalized output.

Device action tests:
- Use DSL plus the supported device signal/action model exposed by the current runtime.

Deadband sweep fields:
- `deadbandSweep startDuty <value>`
- `deadbandSweep maxDuty <value>`
- `deadbandSweep stepDuty <value>`
- `deadbandSweep stepHoldSec <value>`
- `deadbandSweep motionThresholdRot <value>`
- `deadbandSweep requiredSamples <value>`
- Optional encoder fields:
  - `deadbandSweep encoderKey <label|internal>`
  - `deadbandSweep encoderSource <internal|sparkmax_alt|external>`
  - `deadbandSweep encoderCountsPerRev <value>`
  - `deadbandSweep encoderMotorIndex <value>`

## Termination Conditions
Purpose: define how a button test ends.

Rules:
- Any termination condition ends the test.
- Multiple termination blocks are allowed.

Commands:
1. `termination hold`
2. `termination time <seconds>`
3. `termination rotation <value>`
4. `termination limitswitch [id]`

Notes:
- At least one termination is required for button tests.
- Use values consistent with existing bringup test schema.

### Limit Switch Termination
Purpose: terminate a test when a limit switch is hit.

Commands:
1. `termination limitswitch [id]` enables limit switch termination.
2. `limitswitch onHit <pass|fail>` defines the result when the switch triggers.
3. `limitswitch id <label>` sets the required limit switch label.

Example:
```
bringup(config-test-IntakePulse)# termination limitswitch
bringup(config-test-IntakePulse)# limitswitch onHit fail
```

Notes:
- The limit switch check triggers when any selected motor reports a closed forward or reverse limit.
- Limit switches are defined as DIO devices in `bringup_system.json` and referenced by label in `attachments` on the CAN device.
- Either `termination limitswitch` or `limitswitch onHit` enables the limit switch check.
- The optional id is stored in JSON but is not used by the robot runtime yet.
- Validation enforces `onHit` values (`pass` or `fail`) and non-empty ids when provided.

## Quick Start (Import a Joystick-Style Test)

Purpose: create a simple joystick-driven test using the supported DSL import workflow.

Create a file such as `tools\can_nt\logs\DriveFrontLeft.dsl`:

```text
test "DriveFrontLeft"
device "SPARKMAX/NEO 25"
device "controller0"

main:
    set "SPARKMAX/NEO 25".output = controller0.leftY deadband 0.12 scaled 0.25 default 0.0
    until timer.elapsed >= 3.0
```

Then run:

```text
configure terminal
test import DriveFrontLeft tools/can_nt/logs/DriveFrontLeft.dsl set default
test validate DriveFrontLeft --json --pretty
end
show test DriveFrontLeft
show test DriveFrontLeft normalized --json --pretty
```

## Quick Start (Import a Button-Style Test)

Purpose: create a fixed-duty test with termination rules using DSL import.

Create a file such as `tools\can_nt\logs\IntakePulse.dsl`:

```text
test "IntakePulse"
device "FALCON 9"
device "controller1"

main:
    set "FALCON 9".output = 0.2
    abort controller1.B
    until timer.elapsed >= 1.5
```

Then run:

```text
configure terminal
test import IntakePulse tools/can_nt/logs/IntakePulse.dsl set default
test validate IntakePulse --json --pretty
end
show test IntakePulse normalized --json --pretty
```

## Editing Existing Tests

Purpose: update a test by editing DSL source and re-importing it.

Steps:
1. `test export <existingName> <path>`
2. Edit the exported `.dsl` file.
3. `configure terminal`
4. `test import <existingName> <path> set <set_name>`
5. `test validate <existingName> --json --pretty`
6. `end`
7. `show test <existingName> normalized --json --pretty`

## Validation and Errors
Purpose: show what stops a save.

Validation failures:
1. Missing required fields.
2. No devices selected.
3. Invalid ranges such as duty outside -1.0 to 1.0.
4. Invalid or duplicate test names.
5. Invalid limit switch configuration (`onHit` or missing/unknown `id`).

Warnings:
- Device not found in the active profile.

## Saving Output
Purpose: persist tests in the deployable unified config.

Commands:
- `test import <name> <path> [set <set_name>]`
- `test export <name> <path>`
- `test validate [<name>] [--json] [--pretty]`

Notes:
- Test content is persisted through the DSL-backed store in `bringup_system.json`.
- After config changes, run `python -m tools.validate_sync` so `src/main/deploy/bringup_system.json` stays in sync.

## Example: CANdle LED Tests
Purpose: create deviceAction tests for a CANdle LED controller.

Toggle LED:
```text
test "CandleToggle"
device "candle"

main:
    until timer.elapsed >= 0.1
```

Set solid color:
```text
test "CandleBlue"
device "candle"

main:
    until timer.elapsed >= 2.0
```

Import flow:

```text
configure terminal
test import CandleToggle tools/can_nt/logs/CandleToggle.dsl set default
test import CandleBlue tools/can_nt/logs/CandleBlue.dsl set default
test validate CandleToggle --json --pretty
test validate CandleBlue --json --pretty
end
```

## Example Session (Full)

Purpose: show a complete supported import/validate/show flow.

```text
bringup> configure terminal
bringup(config)# test import IntakePulse tools/can_nt/logs/IntakePulse.dsl set default
bringup(config)# test validate IntakePulse --json --pretty
bringup(config)# end
bringup> show test IntakePulse
bringup> show test IntakePulse normalized --json --pretty
```

## Troubleshooting
Purpose: resolve common issues quickly.

Issues:
1. Unknown device label. Check `src/main/deploy/bringup_system.json` for the device label.
2. Invalid command in this mode. Confirm the prompt matches the mode you expect.
3. Save blocked by validation. Use `show test <name>` and correct missing fields.
4. Tests not seen on robot. Run `python -m tools.validate_sync` and deploy the updated `src/main/deploy/bringup_system.json`.

