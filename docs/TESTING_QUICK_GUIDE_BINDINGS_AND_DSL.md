# Testing Quick Guide: Bindings and DSL

## Purpose

Provide a short current-state guide for choosing the right testing surface when working on bringup controls, controller mappings, and authored tests.

This version is aligned to the current CLI, current config files, and current regression coverage in this repo.

For the next DSL-focused testing pass, prefer the Bringup Control UI whenever the UI can perform the step.

Important UI boundary:

- the Bringup Control UI is still mainly read-only for general config
- the UI is not a broad profile/device editor
- current UI write paths are narrow exceptions such as `Import DSL Test`, `Validate DSL Tests`, config push/download, and runtime/test control actions

Use the CLI only for the remaining source-authoritative inspection tasks the UI does not yet expose directly:

- inspecting normalized DSL output

## Quick Intro

There are five practical ways to do bind-like connection work in this repo:

1. Group-local `bind ...` connects a live controller input to the currently selected runtime group for fast manual bringup.
2. Global `bindings ...` connects a controller input to a named robot-local command in `bringup_bindings.json`.
3. DSL import/validate connects declared devices and signals into an authored repeatable test definition.
4. The Bringup Control UI right-click manual-duty popup connects a temporary slider control to one motor directly.
5. Test execution commands such as `tests select ...` and `tests run ...` connect a saved test definition to actual runtime execution on the robot.

These five paths sound similar, but they solve different problems and use different stored data.

## Current Model

There are four different surfaces that often get lumped together:

1. Group-local runtime bindings with `bind ...`
2. Persistent global controller bindings with `bindings ...`
3. DSL-authored tests imported with `test import ...`
4. UI manual motor control from the right-click slider popup

They are related, but they are not interchangeable.

They differ in:

- where the data lives
- whether the behavior is temporary or durable
- whether the surface is manual-control oriented or test oriented
- whether pass/fail semantics exist

## Surface 1: Group-Local Runtime Bindings

### Purpose

Use group `bind` for the fastest local manual-control check of a runtime group.

This is the right surface when the question is:

- does this live input move the intended group right now
- is the sign or stick direction correct
- does a hold, toggle, or jog binding behave as expected
- does the current group membership behave correctly on the active profile

### What It Edits

Group-local runtime bindings live in the profile bridge config under group data, not in `bringup_bindings.json`.

This is separate from global controller-command bindings.

### Typical Use

```text
configure terminal
group diag
member assign "SPARKMAX/NEO 25"
bind controller0.leftY analog
show bindings
```

Button-style group bindings use explicit behavior and value:

```text
bind controller0.A hold 0.15
bind controller0.B toggle 0.10
bind controller0.X jog-forward 0.08
bind controller0.Y jog-reverse 0.08
```

### Diagnostics

Current group binding diagnostics are:

- `bind list`
- `bind explain <index-or-input>`
- `bind test <index-or-input>`

These are useful when a binding exists but does not resolve or activate the way you expect.

### Good Fit

- quick bringup checks
- one-off live debugging
- staged single-motor motion checks
- verifying group membership and runtime response

### Not A Good Fit

- persistent controller mapping design
- robot-local command inventory maintenance
- explicit pass/fail test authoring
- regression-ready authored procedures

## Surface 2: Persistent Global Controller Bindings

### Purpose

Use `bindings ...` when you want durable controller inventory plus durable controller-to-command mappings.

This is the right surface when the question is:

- is the controller inventory defined correctly
- do controller labels and ports validate
- does a robot-local command binding serialize correctly
- does the saved bindings file match the current schema

### What It Edits

This surface edits `src/main/deploy/bringup_bindings.json`.

Current bindings are stored in a unified schema:

- `schema_version: 5`
- `controllers[]`
- `bindings[]`
- `inputAliases`

Axis mappings are no longer a separate top-level `axes[]` section.

### Typical Use

```text
bindings controller add driver0 XBOX 0
bindings binding add stop driver0 button A pressed
bindings binding add drive driver0 axis leftY analog invert on deadband 0.12
bindings show bindings
bindings validate
```

### Current Canonical Commands

Common current commands are:

- `bindings show`
- `bindings show controllers`
- `bindings show bindings`
- `bindings show --all --json --pretty`
- `bindings controller add <name> <type> <port>`
- `bindings controller set <name> <field> <value>`
- `bindings controller rename <old> <new>`
- `bindings no controller <name>`
- `bindings binding add <command> <controller> button <id> <mode>`
- `bindings binding add <command> <controller> axis <id> analog invert <on|off> deadband <value>`
- `bindings binding set <index> <field> <value>`
- `bindings binding delete <index>`
- `bindings load <path>`
- `bindings save <path>`
- `bindings validate`
- `bindings validate <path>`

### Important Limits

- `bindings show` is local-only
- global bindings and group-local bindings are separate data sets
- `show bindings --all` is the visibility surface that shows both without conflating them

### Good Fit

- maintaining reusable controller mapping data
- validating saved controller/binding config
- wiring robot-local commands to controller inputs
- checking schema and serialization behavior

### Not A Good Fit

- immediate ad hoc manual motor checks
- rich multi-step pass/fail procedures
- device evidence checks such as velocity/current/limit-switch assertions

## Surface 3: DSL-Authored Tests

### Purpose

Use DSL tests when the behavior should be explicit, reviewable, repeatable, and capable of real pass/fail semantics.

This is the right surface when the question is:

- does this authored test compile and validate against the active profile
- does the test declare the right devices and signals
- does the test define the right stop, abort, success, and require behavior
- should this become part of durable regression or a repeatable bringup procedure

### What It Edits

The current maintained authoring path is source-authoritative:

1. write a `.dsl` file
2. import it with the UI `Import DSL Test` action or `test import ...`
3. validate it with the UI `Validate DSL Tests` action or `test validate`
4. inspect normalized output

The imported source and normalized representation live under `dslTests` in the local profile config model.

Current practical split:

- source file editing and normalized inspection remain outside the UI
- import/validation can now be done from the UI
- selecting, running, and observing runtime DSL behavior should be UI-first where possible
- broader profile/device config editing is still outside the UI

### Typical Use

Create a file such as `temp_test.dsl`:

```text
test "spin_up_motor1"
device "FALCON 9"
device "controller0"

main:
    set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
    abort "FALCON 9".current > 35
    until timer.elapsed >= 3.0
    require "FALCON 9".velocity > 1000
```

Import and inspect it:

```text
Bringup Control UI -> Import DSL Test
Bringup Control UI -> Validate DSL Tests
show test spin_up_motor1
show test spin_up_motor1 normalized --json --pretty
```

### Current Notes

- controller devices such as `controller0` are valid DSL devices when present in the active profile
- signal-driven `set` supports `deadband`, `scaled`, and `default`
- qualified signal names such as `output_percent_cmd`, `current_actual`, and `velocity_actual` are accepted
- `test cleanup stale` removes invalid imported tests from the active profile store
- the UI now exposes `Import DSL Test` and `Validate DSL Tests` as host-local actions
- UI test controls cover selected-test execution and test-set/runtime observation better than source editing
- those UI DSL actions are exceptions; they do not make the UI a general writable config editor

### About Legacy Interactive Test Editing

The CLI grammar still contains legacy interactive `test ...` editing verbs.

That is not the current maintained authoring workflow for new local tests.

For current work, prefer:

- `.dsl` source files
- UI `Import DSL Test`
- UI `Validate DSL Tests`
- `show test ... normalized`

### Good Fit

- repeatable bringup procedures
- explicit pass/fail logic
- reviewable test definitions
- controller-driven or sensor-driven authored tests
- regression-friendly coverage
- UI-driven reruns of already imported tests
- UI-driven import and validation of local DSL tests

### Not A Good Fit

- very fast live movement checks
- tiny one-off manual experiments where authoring overhead is not justified

## Surface 3A: UI-First DSL Execution

### Purpose

Use the Bringup Control UI as the primary surface for running and observing DSL tests once they already exist in config.

This is the right surface when the question is:

- can I select the intended imported test and run it from the operator UI
- does the runtime state look correct before and after the run
- does the selected test result match what the operator sees on hardware
- can I rerun the same imported DSL test quickly without dropping back to CLI

### What It Uses

This surface uses the robot runtime's selected-test state plus the UI host actions for local DSL workflow support.

It does not replace DSL source editing or normalized inspection.

It also does not imply broad writable control over profile/device config.

### Typical Use

In the Bringup Control UI:

1. Confirm the correct profile/runtime is active.
2. Use `Import DSL Test` when a new `.dsl` file needs to be loaded into local config.
3. Use `Validate DSL Tests` to check the local imported tests for the selected profile.
4. Use the test controls to select the desired test.
5. Use `Run Selected` for one test or `Run All` for the enabled set.
6. Review the selected test result, tests overview, and source/report surfaces as needed.

### Current Notes

- `Run Selected` is the primary UI surface for executing one selected DSL test
- `Run All` is available for enabled-test batch execution
- `Toggle Enabled` is available from the UI test controls
- `Import DSL Test` imports a `.dsl` file into local `bringup_system.json`
- `Validate DSL Tests` runs the current DSL compiler/validator against the selected profile's local DSL store
- selected test source and tests overview are available through the robot-local report surfaces
- only one bringup test runs at a time
- editing the `.dsl` source file still happens outside the UI today
- profile/device editing in the general case still happens outside the UI today

### Good Fit

- repeated reruns of imported DSL tests
- operator-driven hardware validation
- observing selected-test behavior in the same surface used for runtime activation and topology checks
- keeping the testing pass centered on UI execution instead of CLI commands
- keeping DSL import and validation in the same UI workflow when possible

### Not A Good Fit

- creating new DSL source files
- normalized JSON inspection
- validation-error debugging that needs exact parser/validator output

## Surface 4: UI Manual Motor Control

### Purpose

Use the Bringup Control UI right-click slider when you want temporary direct control of one motor from the live topology view.

This is the right surface when the question is:

- does this one motor move at all from a simple manual command
- does the motor direction look correct
- can I quickly nudge one motor without setting up a group binding or DSL test
- do I want a UI-driven single-motor check instead of a controller-driven path

### What It Edits

This path does not edit `bringup_bindings.json`, group binding config, or DSL test definitions.

It is a temporary UI command path that sends:

- `manualDeviceDutySet`
- `manualDeviceDutyClear`

### Typical Use

In the Bringup Control UI:

1. Open `Live Topology`.
2. Right-click a motor node.
3. Move the popup slider slowly.
4. Return toward zero.
5. Left-click the topology view or close the popup to clear manual duty.

### Important Limits

- this is UI-only, not a CLI `bind` command
- it controls one motor directly, not a group
- it is temporary and not persisted
- runtime must be active
- robot must be enabled
- the target device must exist

### Good Fit

- quick single-motor smoke checks
- UI-driven live actuation checks
- confirming one motor without creating durable config

### Not A Good Fit

- persistent control mapping
- group behavior validation
- repeatable pass/fail procedures
- regression-friendly authored testing

## How To Choose

### If You Need Speed Right Now

Use group `bind`.

This is the fastest route for immediate live response checks.

If you only need to move one motor from the UI, use the right-click manual-duty slider instead.

### If You Need Durable Controller Mapping

Use `bindings ...`.

This is the right surface for saved controller inventory and controller-to-command mappings.

### If You Need Real Test Semantics

Use DSL tests.

This is the right surface when the behavior needs stop conditions, abort conditions, success criteria, required evidence, and rerunnable authored structure.

If the test already exists, prefer running it from the Bringup Control UI before reaching for CLI execution commands.

If the test does not exist yet, prefer the UI `Import DSL Test` and `Validate DSL Tests` actions before dropping to CLI.

## Recommended Workflow

### Purpose

Move from quick experimentation to durable coverage without overbuilding too early.

Recommended sequence:

1. Start with group `bind` to confirm the device moves and the input direction is sane.
2. Use the UI right-click manual-duty slider when you want a one-motor live topology check without controller binding setup.
3. Promote the behavior to a DSL test if it needs explicit pass/fail logic or repeated execution value.
4. Use the Bringup Control UI `Import DSL Test` action to load the `.dsl` file into local config.
5. Use the Bringup Control UI `Validate DSL Tests` action to check the selected profile's DSL tests.
6. Use CLI only when you need normalized inspection output.
7. Return to the Bringup Control UI to select, run, rerun, and observe the imported test.
8. Move to `bindings ...` only if a controller mapping should become durable robot-local command config outside the DSL test itself.

For the next pass, the practical bias should be:

- UI for import, validation, runtime activation, selected-test execution, reruns, and observation
- CLI only for normalized DSL inspection and later CLI-focused coverage

Do not read that as "UI-first for all config changes."

The narrower statement is:

- UI-first for DSL test workflow steps the UI explicitly supports
- mostly read-only UI for broader config structure

## Runtime Interaction

Important current behavior:

- scripted tests and group bindings are separate mechanisms
- while a bringup test is running, group bindings do not drive outputs

That means group bindings are for manual runtime control, while DSL tests own output behavior during a test run.

## Exact CLI Syntax

### Purpose

List the exact current command shapes for connecting controller inputs, devices, groups, and tests.

These commands fall into four different connection models:

- group-local runtime binding: controller input to runtime group
- persistent global binding: controller input to robot-local command
- DSL-authored test: declared devices to authored test behavior
- UI manual motor control: popup slider to one motor directly

### Group-Local Runtime Binding

Enter config mode and select a group:

```text
configure terminal
group <groupName>
```

Add devices to the current group:

```text
member assign <deviceLabel>
member assign all
member assign next
```

Bind controller input to the current group:

```text
bind <controllerLabel>.<axisName> analog
bind <controllerLabel>.<buttonName> hold <value>
bind <controllerLabel>.<buttonName> toggle <value>
bind <controllerLabel>.<buttonName> jog-forward <value>
bind <controllerLabel>.<buttonName> jog-reverse <value>
```

Inspect or debug group bindings:

```text
show bindings
bind list
bind explain <index-or-input>
bind test <index-or-input>
no bind
```

Example:

```text
configure terminal
group diag
member assign "SPARKMAX/NEO 25"
bind controller0.leftY analog
show bindings
```

### Persistent Global Controller Binding

These commands edit `src/main/deploy/bringup_bindings.json`.

Manage controller inventory:

```text
bindings controller add <name> <type> <port>
bindings controller set <name> <field> <value>
bindings controller rename <old> <new>
bindings no controller <name>
bindings show controllers
```

Bind controller input to a robot-local command:

```text
bindings binding add <command> <controller> button <id> <mode>
bindings binding add <command> <controller> axis <id> analog invert <on|off> deadband <value>
```

Inspect, edit, and validate:

```text
bindings show
bindings show bindings
bindings show --all --json --pretty
bindings binding set <index> <field> <value>
bindings binding delete <index>
bindings save <path>
bindings load <path>
bindings validate
bindings validate <path>
```

Example:

```text
bindings controller add driver0 XBOX 0
bindings binding add stop driver0 button A pressed
bindings binding add drive driver0 axis leftY analog invert on deadband 0.12
bindings show bindings
bindings validate
```

### DSL Test Authoring And Inspection

Primary UI path for local DSL config work:

```text
Bringup Control UI -> Import DSL Test
Bringup Control UI -> Validate DSL Tests
```

CLI path when needed:

Import a `.dsl` file:

```text
test import <testName> <path>
test import <testName> <path> set <setName>
```

Validate and inspect imported tests:

```text
test validate
test validate <testName>
test validate <testName> --json --pretty
show test <testName>
show test <testName> normalized --json --pretty
show test sets --json --pretty
```

Manage test sets:

```text
test set create <setName>
test set delete <setName>
test set add <setName> <testName>
test set remove <setName> <testName>
test set default <setName>
```

Cleanup or remove tests:

```text
test delete <testName>
test cleanup stale
```

Example:

```text
configure terminal
test import spin_up_motor1 temp_test.dsl set default
test validate spin_up_motor1 --json --pretty
end
show test spin_up_motor1
show test spin_up_motor1 normalized --json --pretty
```

### UI Manual Motor Control

This path is driven from the Bringup Control UI rather than the CLI command line.

Operator flow:

```text
Open Bringup Control UI
Open Live Topology
Right-click motor node
Move popup slider
Left-click topology or close popup to clear
```

Robot-side commands used by the UI:

```text
manualDeviceDutySet
manualDeviceDutyClear
```

Current behavior:

- right-click opens the popup only for motor nodes
- slider motion sends throttled manual duty updates
- clearing or closing the popup stops the motor
- this path requires runtime active and robot enabled

### Running Tests

Primary UI-first path:

- use the Bringup Control UI test controls to select the test
- use `Run Selected` to execute one imported DSL test
- use `Run All` only after individual tests are already known-good
- use tests overview and selected test source/report surfaces to understand what the UI is running

CLI fallback path when needed:

```text
tests select <testName>
tests run
tests run --wait
tests run --timeout <seconds>
tests run --wait --timeout <seconds>
```

Run all tests:

```text
tests run-all
tests run-all --wait
tests run-all --timeout <seconds>
```

Wait for completion:

```text
tests wait
tests wait --run <runId>
tests wait --timeout <seconds>
tests wait --run <runId> --timeout <seconds>
```

There is also a group-context direct run form:

```text
run test
run test <testName>
```

Use `tests select ...` plus `tests run ...` as the primary robot-side DSL execution path.

`run test [name]` is a current-group command surface and should be treated as a narrower direct form, not the main selected-test workflow.

### Quick Mapping

Use this rule:

- `bind ...` means controller input drives a runtime group of devices
- `bindings ...` means controller input drives a named robot-local command
- right-click manual-duty popup means a UI slider drives one motor directly
- UI `Import DSL Test` means load DSL source into local config
- UI `Validate DSL Tests` means run local DSL compiler/validator checks for the selected profile
- `test import ...` means the CLI form of the same local DSL import workflow
- Bringup Control UI test controls mean run and observe an already imported DSL test
- `tests select ...` plus `tests run ...` means execute the selected robot-side saved/imported test
- `run test ...` means use the current-group direct test run form

## Regression Relationship

### Purpose

Clarify which regression surfaces protect each layer today.

- Group/targeting behavior is covered by:
  - `python tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py`
  - `python tools/can_nt/scripts/bridge_cli_group_targeting_4m2g3t_regression.py`
- DSL import, compile, validate, and show behavior is covered by:
- UI host-action coverage for DSL import/validate should stay aligned with the same shared implementation path
  - `python -m unittest tools.can_nt.tests.test_robot_test_dsl -q`
  - `python -m unittest tools.can_nt.tests.test_bridge_cli_robot_test_dsl_cli -q`
- Broader maintained regression entrypoint:

```text
python tools/can_nt/scripts/run_regressions.py --suite dsl
python tools/can_nt/scripts/run_regressions.py --suite local
```

## Rule Of Thumb

Use:

- `bind` for immediate local movement experiments
- right-click manual-duty popup for immediate one-motor UI actuation
- `bindings ...` for durable controller-command mappings in `bringup_bindings.json`
- DSL for authored procedures with real test semantics
- the Bringup Control UI as the default import, validation, and execution surface for DSL tests when the UI supports the step

If the check needs a real verdict, stop condition, evidence requirement, or durable reviewable procedure, it probably belongs in the DSL layer instead of staying as a binding-only workflow.
