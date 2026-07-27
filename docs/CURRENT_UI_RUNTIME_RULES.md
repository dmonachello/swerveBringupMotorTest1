# Current UI And Runtime Rules

## Purpose

Describe how the UI and robot currently behave as implemented in code on July 27, 2026.

This document is intentionally descriptive, not normative.

- It records what the code does now.
- It does not describe the older intended designs.
- It does not try to resolve whether every rule is ideal.

## Primary Code Owners

Purpose: Identify the code paths that currently define behavior.

- Host UI interaction and ownership:
  - `tools/can_nt/bringup_ui.py`
  - `tools/can_nt/host_ui_state_service.py`
  - `tools/common/group_contract.py`
  - `tools/can_topology/live_topology_view.py`
- Robot runtime activation and lifecycle:
  - `src/main/java/frc/robot/BringupRuntime.java`
  - `src/main/java/frc/robot/BridgeUiProfileCommands.java`
  - `src/main/java/frc/robot/BridgeUiCommandHandler.java`
  - `src/main/java/frc/robot/BridgeUiGroupCommands.java`
  - `src/main/java/frc/robot/BringupCore.java`
- Singleton allocation persistence:
  - `src/main/java/frc/robot/BringupUtil.java`
  - `src/main/java/frc/robot/devices/DeviceUnit.java`
  - singleton-backed device wrappers such as `CtrePdpDevice`, `RoboRioDevice`, and `XboxControllerDevice`

## Core Model

Purpose: State the main runtime model the code currently uses.

- `active-group` is the shared execution group used by manual bringup and by DSL test flows.
- User-defined groups still exist and still work as named groups.
- `Runtime Activate` does two separate things:
  - it activates the selected profile runtime
  - it attempts to activate the controlled lifecycle session for `active-group`
- Runtime instantiation and active scope are different concepts.

The current code treats them this way:

- profile runtime activation instantiates the selected profile's devices broadly
- `active-group` controls which devices are in the active controlled session
- manual and DSL operations are expected to act on the currently eligible subset of that scope

## Scope Terminology

Purpose: Define the words used by the current implementation.

- `Instantiated`
  - the robot has a live runtime device object or a persisted singleton-backed allocation
- `Scope Active`
  - the device is part of the currently active controlled lifecycle session
- `Group Member`
  - the device is a member of the current `active-group`
- `Testable`
  - the runtime payload currently marks the device as eligible for motion/test actions outside a controlled active session

Important current distinction:

- a device can be `Instantiated: yes` and `Scope Active: no`
- this means the runtime object exists, but the device is not inside the current active controlled scope

## Runtime Activate And Runtime Deactivate

Purpose: Document what those top-bar actions currently do.

### Runtime Activate

Current path:

- `BridgeUiProfileCommands.executeProfileActivate(...)`
- `BringupRuntime.activateSelectedProfile(...)`
- `BringupRuntime.resetAndInstantiateForProfile(...)`

Current behavior:

- requires enabled teleop for the UI `runtimeActivate` path
- keeps the already-selected profile if the requested profile name matches the current selection
- performs a profile runtime rebuild
- preserves and restores `active-group`
- calls `core.addAllDevicesCommand()`
- initializes and refreshes lifecycle state
- then activates `active-group` in `READ_ONLY` lifecycle mode

Practical result:

- `Runtime Activate` is not incremental allocation
- it instantiates the active profile broadly
- then it tries to activate the current `active-group`

### Runtime Deactivate

Current path:

- `BridgeUiProfileCommands.executeRuntimeDeactivate(...)`
- `deactivateRuntimeActiveGroup()`
- `deactivateActiveProfile()`

Current behavior:

- deactivates the active controlled lifecycle session
- deactivates the active profile runtime
- does not rely on tab-specific deactivate behavior

## Active-Group Ownership

Purpose: Explain who currently owns `active-group`.

The current UI has two owner modes:

- `manual`
- `selected test`

Current tab rule:

- in `Live Topology` and other non-Tests tabs, the scope context is `manual`
- in the `Tests` tab, the scope context is `selected test`

Current transition rule in `bringup_ui.py`:

- entering the `Tests` tab sets owner mode to `selected test`
- entering `Tests` immediately loads the selected test's required devices into robot `active-group`
- leaving `Tests` changes owner mode back to `manual`
- leaving `Tests` does not automatically tear down the shared active scope

Important current fact:

- the `Tests` tab no longer runs against a separate hidden scope model
- it now loads its selected-test device set into the same robot `active-group`

## How Selected Tests Affect Active-Group

Purpose: Record the current DSL-selected-test workflow.

When the operator selects a test in the `Tests` tab:

- the UI sends `selectTestByName`
- the UI resolves required devices from robot-reported test metadata, with local DSL fallback when needed
- the UI replaces robot `active-group` membership with the selected test devices by calling `groupReplaceMembers`

Current implication:

- the selected test owns the robot `active-group` while the operator is working in the `Tests` tab
- `Selected Test Devices` is a presentation of that selected-test-derived membership and runtime state

## User-Defined Groups

Purpose: Clarify what changed and what did not.

Current behavior:

- user-defined groups still exist in the runtime group model
- they can still be shown and used for manual/group interactions
- they are not the default controlled execution scope

The current system centers execution on:

- `active-group`

Other groups remain:

- named operator groupings
- binding containers
- manual run targets where allowed

## Membership Editing Rules

Purpose: Record when membership can and cannot be changed.

Current host-side edit rule:

- `active-group` membership editing is allowed only when:
  - TCP is connected
  - no tracked command is pending
  - the controlled lifecycle session is not active
  - the shared scope-control state says editing is allowed

Current robot-side edit rule:

- if the active controlled lifecycle session is running, `active-group` membership is locked
- membership commands should be rejected until the scope is deactivated

Practical workflow:

1. `Runtime Deactivate`
2. edit `active-group` membership
3. `Runtime Activate`

## Singleton Rules

Purpose: Describe the current singleton policy as implemented.

Current singleton labels used by the shared host-side contract:

- `controller0`
- `roborio`
- `pdp`

Current intended singleton behavior:

- singleton-backed devices may be added to `active-group`
- once they have been instantiated at least once, they should remain allocated at app lifetime
- they should continue to appear in the `active-group` subpanes
- after first allocation, their checkboxes should be locked/greyed

Current robot truth for singleton allocation:

- singleton allocation persistence is tracked through the app-singleton registry in `BringupUtil`
- lifecycle publication now treats a singleton-backed device as instantiated when either:
  - its current wrapper is created
  - or its app-singleton registry entry exists, even if no wrapper is currently attached

Current UI lock rule:

- host-side row locking comes from shared `group_contract` resolution
- singleton rows lock when the runtime payload confirms instantiation

## Instantiation Versus Membership

Purpose: Document a non-obvious current rule.

Current runtime behavior is profile-wide enough that:

- removing a device from `active-group` does not necessarily free its runtime object immediately
- `active-group` membership is primarily a scope/actuation rule
- it is not a strict object-allocation rule

Current consequence:

- a device may be instantiated even while not selected in `active-group`
- if it is not in scope, it still should not be eligible for controlled-scope manual actuation

## Manual Right-Click And Manual Duty Rules

Purpose: Describe the current manual run rules used by the UI and robot.

### Single-device manual duty

Current robot-side blocking rules:

- robot must be enabled
- robot must not be E-stopped
- a DSL test must not currently be running
- if controlled lifecycle is active, the target device must be active in that controlled scope

Current host-side blocking rules:

- REST/TCP must be connected
- runtime state must be present
- no scope transition may still be pending
- robot must not be disabled or E-stopped
- if the target runtime state already confirms readiness, some stale/busy host conditions are tolerated

### Group manual duty

Current robot-side behavior:

- `manualGroupDutySet` attempts to run enabled motor members of the named group
- members that are currently ineligible are skipped
- the command succeeds if at least one eligible member accepts duty
- the command fails only when the runnable subset is empty

Current implication:

- whole-group rejection because one other member is out of scope is not the current intended behavior
- the effective runnable subset is what matters

## Run Selected Rules

Purpose: Describe how the `Run Selected` button is currently gated.

Current host-side rule in `resolve_scope_control_state(...)`:

`Run Selected` is enabled only when all of these are true:

- runtime UI is ready
- no tracked command is pending
- scope transition is not pending
- current scope kind is `selected test`
- the selected test is not already running
- there is no selected-test runtime block reason
- the selected test is currently ready

Current meaning of selected-test ready:

- the selected test devices are loaded into `active-group`
- the scope is active for that selected-test-owned set
- the robot state does not show a blocking condition for that selected test

## Runnable State Panels

Purpose: Explain what the green/yellow panels are based on.

Current status panels are computed host-side from:

- connection state
- runtime-state visibility
- stale-state flags
- transition-pending flags
- robot enabled / estop status
- current scope kind
- current selected test state
- `active-group` membership and presence

Current important consequence:

- the panel text is not raw robot text
- it is a host-side interpretation of robot runtime state plus host command/transition state

## Active Group Subpanes

Purpose: Describe what the right-side group panels actually show.

### Live Topology Active Group

Current behavior:

- shows all eligible profile devices, not only current members
- checked rows are current `active-group` members
- unchecked rows are candidate profile devices not currently in the group
- singleton rows should remain visible even when locked

### Tests Selected Test Devices

Current behavior:

- shows the selected test's required devices
- rows are resolved through the shared group/member-state contract
- `Instantiated` and `Scope Active` come from current runtime state, not from the DSL source alone

## Binding And Group Effects

Purpose: Describe the current relationship between group bindings and manual runs.

Current behavior:

- group bindings do not own exclusive actuation authority for manual single-device right-click runs
- overlapping group bindings should not, by themselves, block manual right-click popups
- manual/group duty is still subject to runtime eligibility and active-scope rules

## Current Non-Obvious Consequences

Purpose: Capture behaviors that follow from the current implementation and may surprise operators.

- `Runtime Activate` is not one-device-at-a-time bringup.
- DSL tests currently work by replacing `active-group` membership with the selected test device set.
- Leaving the `Tests` tab does not automatically tear down the shared active scope.
- A device being unchecked in `active-group` does not necessarily mean its runtime object was freed.
- Singleton lock state depends on robot-published instantiation truth, not just on the last visible checkbox state.

## Code-Derived Summary

Purpose: Provide one compact statement of the current system.

As the code currently works:

- profile activation instantiates the selected profile broadly
- `active-group` is the shared execution scope used by both manual workflows and DSL tests
- the `Tests` tab temporarily owns `active-group` by replacing its membership with the selected test device set
- controlled lifecycle activation determines `Scope Active`
- singletons are intended to remain allocated once first instantiated and then become locked in membership UIs
- manual and group runs should operate on the currently eligible subset, not fail because of unrelated ineligible members

## Future Use

Purpose: Explain how this document should be used.

This document is a current-state reference.

Use it to:

- understand today’s behavior before changing it
- compare future code changes against the current contract
- identify where implementation and operator expectation still diverge

Do not use it as proof that the current behavior is the final desired design.
