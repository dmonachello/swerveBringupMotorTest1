SPEC_STATUS: NOT_IMPLEMENTED

# Feature Spec: CLI Wizards for Student Operators

## Summary

This spec defines an additive wizard layer for the Bridge CLI that guides student operators through common bringup tasks without requiring command grammar knowledge. The existing CLI remains intact and authoritative. The wizard layer collects answers interactively, generates exact CLI commands, shows a human-readable summary, and only applies changes after explicit confirmation.

The first version includes three subcommands:

- `wizard device`
- `wizard test`
- `wizard sync`

The first version does not change robot-side behavior, NetworkTables contracts, or existing CLI command semantics outside the new `wizard` family.

## Problem Statement

The current CLI is powerful but still too difficult for novice operators to use safely and efficiently.

Common failures today include:

- entering commands in the wrong mode
- missing required fields or valid values
- forgetting required follow-up steps
- confusing local config state with robot runtime state
- building partial configs that validate poorly or fail later

The existing CLI should remain available as the bottom-level interface. The missing piece is a guided layer that narrows the workflow, asks the next required question, and generates correct CLI operations from operator intent.

## Goals

- Enable a student operator to add supported devices and create supported tests without reading the full CLI manual.
- Keep the existing CLI grammar and mode structure intact.
- Generate exact CLI commands so the wizard behavior is transparent and teachable.
- Require explicit confirmation before any local state is changed or any robot push occurs.
- Use the current active profile only and fail clearly if no active profile is set.
- Keep the wizard implementation data-driven and incremental so new device/test flows can be added later.

## Non-Goals

- Replacing or simplifying the underlying CLI grammar.
- Adding natural-language free-form parsing.
- Changing robot-side test execution semantics.
- Changing NetworkTables key contracts.
- Supporting every device type or every test family in the first version.
- Adding a full-screen TUI or menu system.

## Scope

In scope:

- host-side Bridge CLI behavior for the new `wizard` command family
- interactive prompting
- batch generation and preview
- execution of generated batch commands inside the CLI process
- documentation updates for wizard usage

Out of scope for v1:

- `wizard run`
- inline multi-line batch editing inside the CLI
- robot-side protocol changes
- topology editor changes
- UI changes

## Persona and Success Bar

Primary persona:

- student operator doing first-time bringup or incremental hardware additions

Secondary persona:

- bringup developer using the wizard to generate correct command sequences quickly

Success bar:

- a new user can create a two-motor profile and a test without reading docs or knowing grammar

## Locked Product Decisions

- The existing CLI remains unchanged except for the addition of the `wizard` command family.
- The wizard is additive and implemented on top of existing CLI commands.
- The wizard operates only on the current active profile.
- If no active profile is set, wizard commands fail with a direct fix message.
- The wizard collects answers first, then shows a preview, then asks for final confirmation.
- The preview must include both a human-readable summary and the exact CLI commands to be executed.
- The wizard materializes a batch script internally and executes that batch only after confirmation.
- Batch modification is supported in v1 by writing the generated batch to a file for external editing and re-running it manually. Inline editing inside the wizard is out of scope for v1.

## Command Surface

Purpose: define the new top-level command family and its parse behavior.

Canonical surface:

- `wizard device`
- `wizard test`
- `wizard sync`

Optional seeded forms are allowed where they reduce prompting:

- `wizard device <seed...>`
- `wizard test <seed...>`

Examples:

```text
wizard device
wizard device motor
wizard device motor rev neo 25
wizard test
wizard test composite
wizard sync
```

Parse rules:

- `wizard` with no subcommand prints short usage and the valid subcommands.
- Unknown subcommands hard-error with canonical replacements where possible.
- Seeded arguments are hints only. If any seeded value is invalid, the wizard fails immediately and does not enter the interactive flow.
- Missing seeded values are collected interactively.

## Wizard Interaction Model

Purpose: define the shared behavior used by all wizard subcommands.

Each wizard subcommand follows the same high-level lifecycle:

1. Validate preconditions.
2. Parse any seeded arguments.
3. Ask only for missing required values.
4. Validate the collected plan in memory.
5. Generate:
   - a human-readable summary
   - an exact CLI batch
6. Present preview actions:
   - confirm and execute
   - cancel
   - write batch to file and stop
7. If confirmed, execute the generated batch internally and surface success or failure.

The wizard must not mutate CLI state during questioning. State changes begin only after final confirmation and batch execution.

## Common Preconditions

Purpose: define requirements that apply to all wizard subcommands.

For all `wizard` subcommands:

- an active profile must exist
- current CLI context must allow command execution
- the underlying CLI must not already be inside a wizard session

Error when no active profile is set:

```text
ERROR: No active profile.
Fix: use `profile <name>` or `profile create <name>` first.
```

The wizard must report the active profile name at the start of the session so the operator is clear about the destination.

## Supported Device Classes in v1

Purpose: define the bounded set of device workflows supported in the first version.

Supported device flows:

- CAN motor controller with attached motor
- PDP
- PDH
- roboRIO
- limit switch

Supported CAN motor families:

- REV Spark MAX / NEO
- REV Spark MAX / NEO 550
- CTRE Falcon 500

SID_COMMENT: The exact manufacturer and device-type identifiers must come from the existing mapping/config sources at implementation time. The wizard must not introduce a second hard-coded mapping table if an authoritative one already exists.

Unsupported device classes in v1 must fail clearly and point the operator back to the standard CLI.

## Supported Test Classes in v1

Purpose: define the bounded set of test authoring workflows supported in the first version.

Supported test flows:

- composite tests
- joystick/button-driven tests

Unsupported test families must fail clearly and point the operator back to the standard CLI.

## Wizard Device

Purpose: guide the operator through adding one supported device to the active profile.

### User Outcome

The operator adds one device to the active profile with all required fields populated and can immediately save or continue to additional steps.

### Inputs Collected

The exact prompts depend on the device class.

For CAN motors:

- device family
- label
- CAN ID
- vendor
- controller type
- motor model
- inversion
- optional tags

For PDP or PDH:

- device kind
- label
- CAN ID
- optional tags

For roboRIO:

- label
- optional tags

For limit switches:

- label
- electrical interface
- channel number
- normal polarity
- optional tags

### Seeded Argument Behavior

Seeded values are matched left-to-right against the chosen device flow.

Example:

```text
wizard device motor rev neo 25
```

This may prefill:

- class = motor
- vendor family = REV
- motor model = NEO
- CAN ID = 25

The wizard still prompts for any missing required fields such as label or inversion.

### Validation Rules

- labels must be unique within the active profile
- CAN IDs must be validated against the existing profile and device rules
- required fields must be present before preview
- any enumerated values must come from the authoritative CLI/config sources

### Generated Batch Shape

Purpose: standardize the output pattern for device creation.

The generated batch should use canonical underlying CLI commands and edit the active profile only.

Example pattern:

```text
configure terminal
profile <active-profile>
device "<label>"
set <field> <value>
...
exit
```

If the implementation chooses device submode versus one-line `set` commands, it must stay consistent across all generated wizard output for the same release.

### Preview Content

The preview must include:

- active profile name
- device class and label
- fields that will be written
- any warnings
- exact CLI commands

### Confirmation Outcomes

Options:

- `confirm`
- `cancel`
- `write <path>`

`write <path>` writes the generated batch to a file and exits the wizard without executing it.

## Wizard Test

Purpose: guide the operator through creating one supported test in the active profile.

### User Outcome

The operator creates a supported test against one or more existing devices with valid settings and can preview the exact CLI changes before they are applied.

### Preconditions

- active profile exists
- at least one device exists in the active profile

If no devices exist:

```text
ERROR: No devices available in active profile.
Fix: use `wizard device` or add devices with the standard CLI first.
```

### Inputs Collected

The wizard must first ask for test family:

- composite
- joystick/button-driven

Then it must ask for the list of participating devices.

For composite tests:

- test name
- list of device labels
- actuation style supported by existing CLI/test model
- duty or other required output magnitude
- timeout or other termination settings
- pass/fail behavior on timeout if applicable
- initial enabled state

For joystick/button-driven tests:

- test name
- list of device labels
- input source type
- specific controller/input binding values required by the existing test model
- actuation parameters
- termination or hold behavior
- initial enabled state

### Device Selection Rules

- the wizard must present only device labels from the active profile
- multi-select must be supported for test membership
- duplicate device selection is rejected
- unsupported device/test combinations must be blocked before preview

### Validation Rules

- test name must be unique in the active profile
- at least one device must be selected
- all required family-specific fields must be collected
- any selected controller/input names must come from existing supported bindings/input vocabularies

### Generated Batch Shape

Purpose: standardize the output pattern for test creation.

Example pattern:

```text
configure terminal
profile <active-profile>
SID_COMMENT: legacy local interactive test authoring was removed; replace wizard output with DSL file creation plus `test import`.
type <test-family>
device add "<label-1>"
device add "<label-2>"
...
<family-specific settings>
enabled <on|off>
exit
```

The exact commands must use the canonical existing CLI forms supported in the target release.

### Preview Content

The preview must include:

- active profile name
- test name and family
- selected devices
- key behavioral settings
- exact CLI commands

### Confirmation Outcomes

Options:

- `confirm`
- `cancel`
- `write <path>`

`write <path>` writes the generated batch to a file and exits the wizard without executing it.

## Wizard Sync

Purpose: guide the operator through the full local-to-robot sync workflow for the active profile.

### User Outcome

The operator can synchronize the canonical local config, save local sources, push the config to the robot, and activate the active profile without memorizing the exact sequence.

### Locked Sequence

The wizard must perform this sequence in order:

1. local validate/sync using `python -m tools.validate_sync`
2. save local sources
3. `config push <canonical-config-path> --activate <active-profile>`

The wizard must not reorder these steps.

### Preconditions

- active profile exists
- canonical config path is known
- CLI has sufficient runtime context to run save and push commands

If connected robot context is required and unavailable, the wizard must fail before preview with a direct fix message.

### Generated Plan

Purpose: define the multi-stage preview for a workflow that mixes shell and CLI actions.

The preview must separate:

- host shell command(s)
- local CLI command(s)
- robot-targeted CLI command(s)

Example preview:

```text
Shell:
  python -m tools.validate_sync

CLI:
  configure terminal
  save sources
  config push data\bringup_system.json --activate <active-profile>
  end
```

### Execution Rules

- the shell step must complete successfully before CLI save/push begins
- if `validate_sync` fails, the wizard stops and reports the failure
- if save fails, push must not run
- if push fails, the wizard reports failure and does not claim synchronization succeeded

### Confirmation Outcomes

Options:

- `confirm`
- `cancel`
- `write <path>`

For `wizard sync`, `write <path>` writes both:

- a `.cli` batch for CLI steps
- a short companion text block or comment header for the required shell command

## Generated Batch Contract

Purpose: define how wizard output becomes an executable artifact.

The wizard must materialize a batch artifact in memory before execution.

Requirements:

- the artifact must preserve exact command order
- the artifact must use canonical command forms only
- the artifact must be printable to the console in preview
- the artifact must be writable to disk on request

Batch file conventions for v1:

- file extension: `.cli`
- include a short generated header comment if the CLI batch format supports comments
- include the active profile name in the file content or header
- include generation timestamp if the batch format supports comments

If comments are not supported in batch execution, metadata may be shown in preview only and omitted from the saved file.

## Optional Modification Path

Purpose: define the approved v1 interpretation of "modify if possible."

V1 behavior:

- the wizard does not provide inline editing
- the operator may choose `write <path>` to save the generated batch without execution
- the operator may edit that file externally and run it later through the normal CLI batch path

Rationale:

- this preserves preview-first behavior
- this avoids introducing an in-wizard editor before the core flows are stable
- this still satisfies the requirement that the generated command script can be inspected and modified

## Error Handling

Purpose: define required failure behavior.

Wizard errors must be:

- short
- explicit about which step failed
- actionable
- non-destructive

The wizard must not leave partial state changes from the question/preview phase.

If batch execution starts and a command fails:

- execution stops at the first failed command
- the error is surfaced with the failing generated command
- the wizard reports that the flow completed partially

Example:

```text
ERROR: Wizard execution stopped.
Failed command: config push data\bringup_system.json --activate demo_board
Fix: resolve the reported push error, then re-run `wizard sync` or execute the saved batch manually.
```

## Help and Discoverability

Purpose: define minimum operator guidance.

The following help surfaces must be updated when the feature is implemented:

- `help`
- `wizard ?`
- `wizard device ?`
- `wizard test ?`
- `wizard sync ?`
- CLI user/reference documentation

Help text must:

- explain that the wizard is additive
- explain that it operates on the active profile only
- show one short example per subcommand
- point advanced users to the standard CLI for unsupported cases

## Acceptance Criteria

Purpose: define what must be true before implementation is considered complete.

- `wizard device`, `wizard test`, and `wizard sync` parse correctly from the CLI top level.
- Each wizard hard-errors cleanly if no active profile is set.
- Each wizard collects required fields without mutating state before confirmation.
- Each wizard shows both a human-readable summary and exact generated CLI commands.
- `write <path>` saves a usable artifact without executing it.
- `confirm` executes the generated plan and surfaces errors precisely.
- Supported device and test flows succeed end-to-end on the active profile.
- Unsupported flows fail cleanly and point to the standard CLI.
- Existing CLI commands continue to behave exactly as before when the wizard is not used.
- CLI grammar, parser artifacts, help text, and docs are updated together.

## Test Plan

Purpose: define the minimum verification for the feature.

### Parser and Help

- verify `wizard`, `wizard device`, `wizard test`, and `wizard sync` grammar
- verify bad subcommands hard-error cleanly
- verify seeded-argument parse success and failure cases
- verify `?` output and help text match the canonical forms

### Local Wizard Behavior

- verify no-active-profile failure
- verify cancel leaves no state changes
- verify write-only path produces the expected batch artifact
- verify preview output includes summary plus exact commands

### Device Flows

- add REV NEO motor
- add REV NEO 550 motor
- add Falcon 500 motor
- add PDP
- add PDH
- add roboRIO
- add limit switch

### Test Flows

- create composite test for one motor
- create composite test for multiple motors
- create joystick/button-driven test using supported input names
- verify duplicate/invalid device selections are rejected

### Sync Flow

- verify `validate_sync` failure stops the workflow
- verify save failure stops push
- verify push failure is reported accurately
- verify successful sync performs all steps in order

### Regression Safety

- verify existing non-wizard CLI workflows still pass
- verify generated wizard commands are accepted by the standard CLI outside wizard mode

## Documentation Deliverables

Purpose: define the required doc updates that must land with the feature.

At minimum update:

- `docs/CLI_USER_MANUAL.md`
- `docs/CLI_REFERENCE_MANUAL.md`
- the main bringup workflow doc if wizard becomes part of the recommended path

Documentation must include:

- when to use wizard versus standard CLI
- supported v1 device flows
- supported v1 test flows
- sample preview output
- sample save-only batch workflow

## Tradeoffs

Purpose: make the costs explicit.

- Pro: lowers activation energy for novice operators without taking power away from expert users.
- Pro: keeps the existing CLI as the single source of truth for actual operations.
- Pro: generated commands make the wizard teachable and debuggable.
- Con: wizard coverage will initially be narrower than the full CLI.
- Con: preview-first plus external edit path is slower than direct command entry for experienced users.
- Con: mixed shell plus CLI sync flows are more complex than pure CLI flows.

## Future Extensions

Purpose: capture safe follow-on work after the first release.

- add `wizard run` with automatic pre-run preparation:
  - instantiate devices
  - clear stop latch if needed
  - ensure selected test is enabled
  - run and wait
- add inline batch editing before confirmation
- add multi-device authoring flows in one wizard session
- add profile creation or profile selection wizard flows
- add richer validation hints using device-type and test-type metadata
- add export of generated wizard plans as reusable named procedures


