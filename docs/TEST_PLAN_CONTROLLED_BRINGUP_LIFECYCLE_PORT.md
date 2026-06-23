## Purpose

Provide one exact step-by-step rollout plan for the controlled bringup lifecycle port on branch `feature/controlled-bringup-lifecycle`.

This plan is intentionally phase-gated:

- implement one narrow slice
- run the exact commands listed here
- perform the manual connected checks listed here
- stop if any gate fails
- only then move to the next slice

This is designed to avoid repeating the earlier large-change runtime failure.

## Current Status

These port slices are already implemented on `feature/controlled-bringup-lifecycle`:

- lifecycle core model and tests
- fake factory and activation manager tests
- profile/topology adapter
- real `DeviceUnit` lifecycle factory bridge
- robot REST/UI lifecycle commands
- robot local command registry lifecycle commands
- host CLI lifecycle commands
- host UI lifecycle buttons

What is not complete yet:

- connected manual validation of the new lifecycle path
- decision and implementation of any migration from legacy runtime semantics to lifecycle semantics
- compatibility validation when both old runtime controls and new lifecycle controls are exercised in the same build
- final decision on whether to keep both surfaces permanently or retire legacy runtime controls later

## Rules

- Do not proceed to the next phase until the current phase passes.
- If a manual connected check fails, stop and fix that failure before implementing the next slice.
- Keep the old runtime path working until an explicit migration phase says otherwise.
- Do not remove legacy commands during this plan.
- Record results inline in this file under `TESTING_RESULTS:` blocks.

## Branches

- stable baseline branch: `restore-from-a580839`
- lifecycle port branch: `feature/controlled-bringup-lifecycle`

## Environment

- repo root:
  - `C:\Users\dmona\swerveBringupMotorTest1-main`
- Java:
  - `C:\Users\Public\wpilib\2026\jdk`
- typical robot IP:
  - `172.22.11.2`

## Phase 1

### Goal

Connected validation of the already-ported additive lifecycle path.

No new implementation in this phase unless a validation failure requires a targeted fix.

### Exact Commands

From PowerShell at repo root:

```powershell
$env:JAVA_HOME='C:\Users\Public\wpilib\2026\jdk'
.\gradlew.bat test --tests frc.robot.BridgeUiLifecycleCommandsTest --tests frc.robot.RobotLocalCommandRegistryTest --tests frc.robot.commands.local.RobotLocalCommandExecutorTest --tests frc.robot.diag.lifecycle.labels.GlobalLabelRegistryTest --tests frc.robot.diag.lifecycle.labels.LabelResolverTest --tests frc.robot.diag.lifecycle.devices.DeviceCatalogTest --tests frc.robot.diag.lifecycle.groups.GroupCatalogTest --tests frc.robot.diag.lifecycle.factory.FakeDeviceFactoryTest --tests frc.robot.diag.lifecycle.activation.ActivationManagerTest --tests frc.robot.diag.lifecycle.integration.LifecycleProfileTopologyAdapterTest --tests frc.robot.diag.lifecycle.integration.DeviceUnitLifecycleFactoryTest --tests frc.robot.diag.lifecycle.integration.ControlledBringupLifecycleRuntimeTest
```

If Java tests pass, deploy the robot code using the team’s normal WPILib deploy flow.

For host Python validation:

```powershell
python -m py_compile tools/can_nt/bridge_ops.py tools/can_nt/bridge_cli.py tools/can_nt/bringup_ui.py
python -m unittest tools.can_nt.tests.test_bridge_cli_visibility.BridgeCliVisibilityTests.test_parser_accepts_lifecycle_commands tools.can_nt.tests.test_bridge_cli_visibility.BridgeCliVisibilityTests.test_lifecycle_activate_uses_lifecycle_command_path tools.can_nt.tests.test_bridge_cli_visibility.BridgeCliVisibilityTests.test_lifecycle_deactivate_uses_lifecycle_command_path tools.can_nt.tests.test_bridge_cli_visibility.BridgeCliVisibilityTests.test_lifecycle_deactivate_active_uses_lifecycle_command_path tools.can_nt.tests.test_bridge_cli_visibility.BridgeCliVisibilityTests.test_show_lifecycle_state_routes_to_robot_command_path
python -m unittest tools.can_nt.tests.test_bringup_ui_actions
```

Start the CLI:

```powershell
python tools/can_nt/bridge_cli.py --rio 172.22.11.2
```

### Manual CLI Checks

Run these exact CLI commands:

```text
connect
show lifecycle-state --json --pretty
lifecycle activate active-group
show lifecycle-state --json --pretty
lifecycle deactivate active-group
show lifecycle-state --json --pretty
lifecycle activate active-group mode READ_ONLY
show lifecycle-state --json --pretty
lifecycle deactivate-active
show lifecycle-state --json --pretty
runtime deactivate
show runtime-state --json --pretty
disconnect
```

### Expected CLI Results

- `show lifecycle-state` returns a valid response, not an unknown-command error.
- `lifecycle activate active-group` does not create duplicate device instances.
- `lifecycle deactivate active-group` or `lifecycle deactivate-active` returns the lifecycle state to inactive.
- `runtime deactivate` still works through the old path.
- Neither command family causes the other to disappear or crash.

### Manual UI Checks

Start the UI using the team’s normal launch method.

With the UI connected to the robot:

1. Click `Show Lifecycle State`.
2. Click `Lifecycle Activate`.
3. Click `Show Lifecycle State`.
4. Click `Lifecycle Deactivate`.
5. Click `Show Lifecycle State`.
6. Click `Runtime Activate`.
7. Click `Show Runtime State`.
8. Click `Runtime Deactivate`.
9. Click `Show Runtime State`.

### Expected UI Results

- the new lifecycle buttons send commands successfully
- the output pane shows `lifecycleActivate`, `lifecycleDeactivate`, and `showLifecycleState`
- the old runtime buttons still work
- no UI exception occurs
- no duplicate device instance errors occur on the robot

### Exit Criteria

- all targeted automated tests pass
- CLI manual checks pass
- UI manual checks pass
- no duplicate device instance errors
- no unexpected forced stop caused by the lifecycle command path

### TESTING_RESULTS:

- pending

## Phase 2

### Goal

Decide and implement the first compatibility bridge from the legacy runtime surface to lifecycle semantics, but only for one narrow path.

Recommended first migration target:

- `active-group` bringup activation/deactivation behavior

Do not migrate all runtime behavior at once.

### Implementation Slice

Choose exactly one of these and stop after it:

1. make one legacy runtime command delegate internally to lifecycle for `active-group` only
2. add readback cross-links so `showRuntimeState` clearly reports lifecycle ownership when lifecycle is active

Preferred order:

1. readback clarity first
2. command delegation second

### Exact Commands Before Coding

```powershell
git checkout feature/controlled-bringup-lifecycle
git status --short
```

### Exact Commands After Coding

```powershell
$env:JAVA_HOME='C:\Users\Public\wpilib\2026\jdk'
.\gradlew.bat test --tests frc.robot.BridgeUiLifecycleCommandsTest --tests frc.robot.BridgeUiProfileCommandsTest --tests frc.robot.RobotLocalCommandRegistryTest --tests frc.robot.commands.local.RobotLocalCommandExecutorTest
python -m py_compile tools/can_nt/bridge_cli.py tools/can_nt/bringup_ui.py
python -m unittest tools.can_nt.tests.test_bridge_cli_visibility tools.can_nt.tests.test_bringup_ui_actions
```

### Manual Connected Checks

In CLI:

```text
connect
show runtime-state --json --pretty
show lifecycle-state --json --pretty
lifecycle activate active-group
show runtime-state --json --pretty
show lifecycle-state --json --pretty
runtime deactivate
show runtime-state --json --pretty
show lifecycle-state --json --pretty
disconnect
```

### Expected Results

- if lifecycle is active, the operator can tell that from readback
- legacy runtime actions do not silently corrupt lifecycle state
- lifecycle readback and runtime readback are internally consistent enough to diagnose ownership

### Exit Criteria

- no contradictory active/inactive state between runtime and lifecycle readback
- no duplicate device instance errors
- no loss of legacy runtime command availability

### TESTING_RESULTS:

- pending

## Phase 3

### Goal

Add one more integration slice only after Phase 2 passes.

Preferred target:

- controlled exposure of lifecycle state in the host UI beyond the current top-bar buttons

Examples:

- dedicated lifecycle status panel
- lifecycle session label display
- lifecycle state text in an existing status surface

Do not redesign the full UI in this phase.

### Exact Commands After Coding

```powershell
python -m py_compile tools/can_nt/bringup_ui.py
python -m unittest tools.can_nt.tests.test_bringup_ui_actions
```

If Java changed too:

```powershell
$env:JAVA_HOME='C:\Users\Public\wpilib\2026\jdk'
.\gradlew.bat test --tests frc.robot.BridgeUiLifecycleCommandsTest --tests frc.robot.RobotLocalCommandRegistryTest --tests frc.robot.commands.local.RobotLocalCommandExecutorTest
```

### Manual Connected Checks

1. open the UI
2. connect the UI session
3. activate lifecycle through UI
4. confirm the new lifecycle status surface updates
5. deactivate lifecycle through UI
6. confirm the new lifecycle status surface updates
7. run one old runtime command and confirm it still updates its own surface correctly

### Exit Criteria

- UI lifecycle state is visible and understandable
- no second hidden state model is introduced on the host
- old runtime UI remains usable during migration

### TESTING_RESULTS:

- pending

## Phase 4

### Goal

Compatibility hardening with both sides enabled together.

This is the first phase where the broader Python side should be left running during lifecycle tests so coexistence issues show up.

### Exact Commands

Start the passive Python side in the team’s normal way.

Then run:

```powershell
python tools/can_nt/bridge_cli.py --rio 172.22.11.2
```

In CLI:

```text
connect
show lifecycle-state --json --pretty
lifecycle activate active-group
show lifecycle-state --json --pretty
show runtime-state --json --pretty
lifecycle deactivate-active
show lifecycle-state --json --pretty
disconnect
```

### Manual Checks

- passive diagnostics side remains up
- UI session still works
- no command starvation or pending-state deadlock
- no NT/readback confusion severe enough to mislead the operator

### Exit Criteria

- lifecycle command path coexists with the passive Python diagnostics side
- no regression in existing UI handshake or polling behavior

### TESTING_RESULTS:

- pending

## Phase 5

### Goal

Decide whether to:

- keep both runtime and lifecycle command families long term
- or migrate legacy runtime controls to lifecycle-backed behavior

This is a product decision phase, not just an implementation phase.

### Decision Inputs

- results from Phases 1 through 4
- operator clarity
- compatibility burden
- whether legacy runtime semantics still provide unique value

### If Keeping Both

Implement:

- clear operator docs describing the difference
- explicit ownership/readback language
- tests that cover coexistence

### If Migrating to Lifecycle

Implement one small migration step at a time:

1. one runtime readback field
2. one runtime action path
3. one UI button group

Never migrate all legacy runtime behavior in one change.

### Exact Commands After Each Migration Step

```powershell
$env:JAVA_HOME='C:\Users\Public\wpilib\2026\jdk'
.\gradlew.bat test
python -m unittest tools.can_nt.tests.test_bridge_cli_visibility tools.can_nt.tests.test_bringup_ui_actions
```

Then rerun the Phase 1 manual checks exactly as written.

### Exit Criteria

- operator workflow is clear
- no duplicate command surfaces with conflicting meanings
- old path either remains intentionally supported or is retired deliberately and documented

### TESTING_RESULTS:

- pending

## Completion Criteria

The controlled bringup lifecycle implementation is complete when all of these are true:

- robot lifecycle core is stable under connected manual use
- CLI lifecycle commands work on real hardware
- UI lifecycle controls work on real hardware
- coexistence with the old runtime path is either:
  - intentionally supported and documented
  - or intentionally migrated and documented
- coexistence with the passive Python diagnostics side is tested
- operator docs are updated to explain the final workflow

## Final Workflow Target

When this port is complete, the intended operator workflow should be:

1. select or author the desired profile/group/device on the host side
2. activate lifecycle explicitly by label
3. inspect lifecycle state and runtime evidence
4. deactivate explicitly when done

The robot owns:

- hardware object lifetime
- session serialization
- rollback behavior

The host owns:

- label/group selection
- command submission
- operator-facing readback and tooling

