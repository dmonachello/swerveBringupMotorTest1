# CLI Test Authoring User Guide

## Purpose
Provide a step-by-step, no-JSON workflow for creating and editing bringup tests using the Bridge CLI.

## Audience
Operators and developers who want to add tests without editing JSON.

## Before You Start
Purpose: ensure the CLI can resolve devices and save tests correctly.

Checklist:
1. Use a working copy of the repo on Windows.
2. Confirm `data/bringup_system.json` matches the profile you want to use.
3. Confirm `src/main/deploy/bringup_bindings.json` defines controller names you want to reference.
4. Decide which test set under `test_sets` you will edit or create.
5. Decide where to save `bringup_tests.json` on your Windows machine.
6. If you are testing a new device label, add it to the active profile first (see “Add a Device to the Active Profile” below).

## Core Concepts
Purpose: explain the minimum mental model for authoring.

Key ideas:
1. The CLI edits an in-memory model, not JSON directly.
2. `write tests` validates and writes the JSON.
3. Devices are chosen from `data/bringup_system.json`.
4. Test names are unique within a test set.
5. Inputs use a unified `inputSource` format: `controllerName.inputId`.

## Modes and Prompts
Purpose: show how the CLI indicates context.

Prompts:
- `bringup>` is normal mode.
- `bringup(config)#` is config mode.
- `bringup(config-test-<name>)#` is test edit mode.

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
4. `tests save` writes back to the currently loaded tests file.

Notes:
- Templates live under `tools/test_template_wizard/test_templates`.
- Loading replaces the in-memory tests model.

## Device Selection
Purpose: bind tests to device labels from the active profile.

Rules:
1. Devices are referenced by their label from `bringup_system.json`.
2. The CLI resolves labels from `data/bringup_system.json`.
3. Duplicate device adds are rejected with a warning.
4. Duplicate labels in the active profile are errors.
5. A device must exist in the active profile with required fields (CAN: `interface`, `manufacturer`, `deviceType`, `id`) before tests can reference it.

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
save profiles data/bringup_system.json
```

Notes:
- Use numeric manufacturer/deviceType IDs (REV=5, MotorController=2).
- If this step is skipped, `device add "Feeder Motor"` in test mode will fail with “device label not found in active profile.”

## Test Types
Purpose: choose the correct type for the behavior you want.

Joystick tests:
- Use joystick axes for live control.
- Required fields: `type joystick`, `device add`, `inputSource`, `deadband`.

Button tests:
- Apply fixed duty while active.
- Required fields: `type button`, `device add`, `inputSource`, `duty`, and at least one `termination`.
- `type composite` is accepted and behaves the same as `type button` in JSON output.

Deadband sweep tests:
- Sweep duty to find motion thresholds.
- Required fields: `type deadbandSweep`, `device add`, and deadband sweep fields.
- `inputSource` is not used for deadband sweep tests.

Device action tests:
- `type deviceAction`
- `action toggle_led | set_color`
- `color #RRGGBB` (required for `set_color`)
- `pattern solid` (only supported value in v1)
- `brightness <0.0-1.0>`
- `duration <seconds>` (optional; 0 or omitted means immediate)

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

## Quick Start (Create a Joystick Test)
Purpose: create a simple joystick-driven test in a few commands.

Steps:
1. Start the bridge with CLI enabled.
2. Enter config mode: `configure terminal`
3. Choose a test set: `test set default`
4. Create a test (enters test mode): `test create DriveFrontLeft`
5. Set type: `type joystick`
6. Add devices: `device add SPARKMAX/NEO 25`
7. Set input: `inputSource controller0.leftY`
8. Set deadband: `deadband 0.12`
9. Exit test mode: `end`
10. Save: `write tests bringup_tests.json`

Expected:
- No parse errors.
- Prompt changes to `bringup(config-test-DriveFrontLeft)#` while editing.
- The file `bringup_tests.json` is updated or created.

## Quick Start (Create a Button Test)
Purpose: create a fixed-duty test with termination rules.

Steps:
1. Enter config mode: `configure terminal`
2. Choose a test set: `test set default`
3. Create a test (enters test mode): `test create IntakePulse`
4. Set type: `type button`
5. Add devices: `device add FALCON 9`
6. Set input: `inputSource controller1.A`
7. Set duty: `duty 0.2`
8. Add termination: `termination time 1.5`
9. Add termination: `termination hold`
10. Exit test mode: `end`
11. Save: `write tests bringup_tests.json`

Expected:
- The test runs when the bound button is pressed.
- The test ends when any termination condition is met.

## Editing Existing Tests
Purpose: update a test without writing JSON.

Steps:
1. `configure terminal`
2. `test set <name>`
3. `test <existingName>` (existing tests only)
4. Change fields as needed.
5. `end`
6. `write tests bringup_tests.json`

Notes:
- Use `show tests` to list all tests in the active set.
- Use `show test <name>` to inspect a specific test.

Overwrite behavior:
- Only `test create <name>` can overwrite. The CLI warns and prompts before replacing an existing test.

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
Purpose: write a deployable tests file.

Command:
- `write tests <path>`

Notes:
- Output is a standard `bringup_tests.json`.
- Copy it to `src/main/deploy/bringup_tests.json` before deploying robot code.

## Example: CANdle LED Tests
Purpose: create deviceAction tests for a CANdle LED controller.

Toggle LED:
```
configure terminal
test set default
test create CandleToggle
test CandleToggle
type deviceAction
device add "candle"
action toggle_led
enabled true
end
write tests bringup_tests.json
```

Set solid color:
```
configure terminal
test set default
test create CandleBlue
test CandleBlue
type deviceAction
device add "candle"
action set_color
color #0080FF
pattern solid
brightness 0.7
duration 2.0
enabled true
end
write tests bringup_tests.json
```

## Example Session (Full)
Purpose: show a complete authoring flow.

```
bringup> configure terminal
bringup(config)# test set default
bringup(config)# test create IntakePulse
bringup(config-test-IntakePulse)# type button
bringup(config-test-IntakePulse)# device add FALCON 9
bringup(config-test-IntakePulse)# inputSource controller1.A
bringup(config-test-IntakePulse)# duty 0.2
bringup(config-test-IntakePulse)# termination time 1.5
bringup(config-test-IntakePulse)# end
bringup(config)# write tests bringup_tests.json
```

## Troubleshooting
Purpose: resolve common issues quickly.

Issues:
1. Unknown device label. Check `data/bringup_system.json` for the device label.
2. Invalid command in this mode. Confirm the prompt matches the mode you expect.
3. Save blocked by validation. Use `show test <name>` and correct missing fields.
4. Tests not seen on robot. Deploy the updated `src/main/deploy/bringup_tests.json`.
