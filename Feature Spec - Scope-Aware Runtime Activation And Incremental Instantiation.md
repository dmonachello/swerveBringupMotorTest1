SPEC_STATUS: PROPOSED

  

# Feature Spec: Scope-Aware Runtime Activation And Incremental Instantiation

  

## Purpose

  

Define a runtime activation model that supports both:

  

- full all-in robot bringup

- incremental bringup using `active-group` or another named group

  

without requiring the runtime to instantiate every defined profile device at activation time.

  

## Problem

  

The system currently mixes three different concerns:

  

- full topology definition

- runtime activation

- device instantiation

  

That coupling is acceptable for an already-wired robot, but it breaks the intended one-device-at-a-time bringup methodology.

  

In the incremental workflow, teams often want all of these to be true at once:

  

- the profile/topology defines the full intended robot

- only a subset of devices is physically connected today

- only a subset of devices should be instantiated and used in the active bringup session

- always-present infrastructure devices such as `roborio` and `pdp/pdh` should still be available

  

Today, the main activation path still behaves like an all-in path:

  

- `runtimeActivate`

- active profile reload

- instantiate all configured active-profile devices

  

That creates operator confusion and makes incremental bringup harder than it should be.

  

## Goals

  

- Keep the full defined topology visible at all times.

- Separate `runtime activation` from `instantiation scope`.

- Allow the operator to choose activation scope explicitly from the UI.

- Support these activation scopes:

  - `All`

  - `Group: active-group`

  - `Group: <any named group>`

- Treat the UI as the controlling authority for chosen activation scope.

- Require the robot runtime to synchronize to the scope requested by the UI or report an error.

- Preserve incremental bringup where only selected devices are instantiated.

- Preserve all-in bringup where all eligible profile devices are instantiated.

- Always instantiate/deactivate required infrastructure devices such as:

  - `roborio`

  - `pdp/pdh`

- Show clear, synchronized operator state for:

  - full topology

  - current activation scope

  - instantiated state

  - present/telemetry-observed state

  

## Non-Goals

  

- Redesign the profile schema.

- Hide undefined or unconnected devices from the topology.

- Infer activation scope automatically from DS mode.

- Preserve current behavior for backward compatibility.

- Solve every future category rule for every non-motor device in this spec.

  

## User Outcome

  

An operator should be able to:

  

1. define the full robot topology up front

2. activate runtime in either `All` or `Group` mode

3. bring up only the intended subset of devices

4. see exactly which devices are:

   - defined

   - in scope

   - instantiated

   - actually present

5. move between incremental and all-in workflows without changing profile data

  

## Current Behavior

  

Current behavior is split across two models.

  

### Model A: Full Activation

  

`runtimeActivate` currently drives full runtime activation and full instantiation.

  

Effective flow:

  

1. selected profile activation

2. runtime reset/rebuild

3. instantiate all active-profile devices

  

Relevant code paths include:

  

- `BringupRuntime.activateSelectedProfile(...)`

- `BringupRuntime.resetAndInstantiateForProfile(...)`

- `BringupCore.reloadActiveProfileRuntime(...)`

  

### Model B: Incremental Bringup

  

A separate incremental flow already exists:

  

- stage selected profile for bringup

- add next motor

- add all devices

- populate and use `active-group`

  

Relevant code paths include:

  

- `BringupUtil.stageSelectedProfileForBringup()`

- `BridgeUiRuntimeCommands.ensureBringupProfileStaged(...)`

- `BringupCore.addNextMotorCommand()`

- `BringupCore.addAllDevicesCommand()`

  

These two models are not yet aligned.

  

## Core Design

  

## Runtime Activation Must Become Scope-Aware

  

`Runtime Activate` must no longer mean only:

  

- activate selected profile

- instantiate everything

  

It must mean:

  

- activate selected profile runtime

- apply the chosen instantiation scope

- instantiate only the devices allowed by that scope

- always instantiate required infrastructure devices

  

## Scope Selector

  

The UI must place the activation scope selector next to the `Runtime Activate` button.

  

Allowed values:

  

- `All`

- `Group: active-group`

- `Group: <any named group>`

  

The selected value is the requested activation scope for the next `Runtime Activate` action.

  

## UI Ownership And Robot Synchronization

  

The UI is authoritative for the requested activation scope.

  

Required behavior:

  

1. operator selects activation scope in the UI

2. UI sends `runtimeActivate` with explicit scope information

3. robot runtime applies that scope

4. UI reads back runtime state

5. if robot state does not match requested scope, UI must surface an error condition

  

The system must not silently allow UI and robot runtime scope state to diverge.

  

## State Model

  

The operator surface must show these concepts separately.

  

### 1. Defined Topology

  

- all profile-defined devices

- always visible in the diagram

  

### 2. Activation Scope

  

- which devices are intended to participate in this runtime session

- determined by:

  - `All`

  - `Group: active-group`

  - `Group: <named group>`

  

### 3. Instantiated State

  

- whether the robot runtime has actually created the runtime wrapper/device instance

  

### 4. Present State

  

- whether runtime telemetry/passive evidence indicates the device is actually present/responding

  

These must not be collapsed into one overloaded status.

  

## Device Categories

  

## Always-Instantiated Infrastructure

  

Some devices are required for runtime operation and should always activate/deactivate with runtime regardless of chosen scope.

  

Initial category:

  

- `roborio`

- `pdp/pdh`

  

These devices must:

  

- instantiate on every successful runtime activation

- deactivate on runtime deactivation

- remain visible even if not part of the selected activation scope

  

## Scope-Controlled Devices

  

The following devices are controlled by activation scope:

  

- motors

- optional sensors/devices added incrementally

- other non-required bringup devices

  

Examples:

  

- `FALCON 9`

- `SPARKMAX/NEO 25`

- optional limit switches

  

SID_QUESTION: The exact default category rules for non-motor optional devices such as `limitSwitch`, `CANcoder`, `Pigeon`, and controllers need a follow-up rule table. This spec only locks the initial principle: some are always-instantiated infrastructure, others are scope-controlled.

  

## Activation Scope Semantics

  

## Scope = `All`

  

When the operator chooses `All`, runtime activation must:

  

- instantiate all eligible scope-controlled devices from the selected profile

- instantiate all always-instantiated infrastructure devices

  

This is the all-in bringup mode.

  

## Scope = `Group: active-group`

  

When the operator chooses `Group: active-group`, runtime activation must:

  

- instantiate all eligible members of `active-group`

- instantiate all always-instantiated infrastructure devices

- leave all other scope-controlled devices uninstantiated

  

This is the primary incremental bringup mode.

  

## Scope = `Group: <named group>`

  

When the operator chooses another named group, runtime activation must:

  

- instantiate all eligible enabled members of that group

- instantiate all always-instantiated infrastructure devices

- leave all other scope-controlled devices uninstantiated

  

This allows named subsystem bringup beyond `active-group`.

  

## Empty Group Behavior

  

If the selected group is empty, activation must be a no-op for scope-controlled devices.

  

Required behavior:

  

- runtime activation still succeeds for always-instantiated infrastructure devices

- no scope-controlled devices are instantiated

- the operator receives a clear informational warning

  

Example message:

  

- `Activation scope group is empty. No scoped devices were instantiated.`

  

This is not a fatal error by itself.

  

## Eligibility Rules

  

A device is eligible for scope-based instantiation when all of these are true:

  

- it is defined in the selected profile

- it belongs to the selected activation scope, or the scope is `All`

- it is enabled in that scope membership

- it is not part of the always-instantiated infrastructure category

  

SID_QUESTION: This spec intentionally does not yet decide whether scope eligibility should also consider test-specific readiness, vendor/API support, or selected-device mode flags at activation time. That needs a narrower follow-up decision.

  

## UI Requirements

  

## Activation Controls

  

The UI must provide:

  

- `Runtime Activate`

- `Runtime Deactivate`

- activation scope dropdown directly next to `Runtime Activate`

  

The scope dropdown must display:

  

- `All`

- `Group: active-group`

- `Group: <any named group>`

  

## Diagram Requirements

  

The diagram must always show all defined topology devices.

  

The diagram must also visually indicate:

  

- in current activation scope

- instantiated now

- present now

  

These states must remain synchronized with the right-side panel.

  

The diagram must not hide devices simply because they are out of scope or uninstantiated.

  

## Right-Side Panel Requirements

  

The right-side panel must expose the same three concepts explicitly:

  

- `in scope`

- `instantiated`

- `present`

  

This should apply to:

  

- selected device details

- active group / named group summaries

- group run inspector views when active

  

## Synchronization Rule

  

The diagram and right-side panel must be in sync.

  

That means:

  

- same activation scope

- same instantiated state

- same present state

  

If they disagree, that is a bug or synchronization error condition.

  

## Command/Contract Requirements

  

## Runtime Activate Command

  

`runtimeActivate` must accept explicit activation scope information.

  

Required logical arguments:

  

- selected profile or current selected profile

- scope mode:

  - `all`

  - `group`

- group name when scope mode is `group`

  

Example logical forms:

  

- `runtimeActivate(profile=test_minimal_25_9, scope=all)`

- `runtimeActivate(profile=test_minimal_25_9, scope=group, group=active-group)`

- `runtimeActivate(profile=test_minimal_25_9, scope=group, group=motors)`

  

## Runtime State Surface

  

Runtime state must expose:

  

- selected profile

- active runtime profile

- runtime declared active

- current applied activation scope

- scope members

- instantiated devices

- present devices

  

The UI must read this back after activation and verify it matches the requested scope.

  

## Error Handling

  

## UI/Robot Scope Mismatch

  

If the UI requests one scope and the robot reports another applied scope, the UI must show an explicit error condition.

  

Example:

  

- `Runtime activation scope mismatch: UI requested Group: active-group, robot reports All.`

  

## Empty Group

  

If a selected scope group is empty:

  

- no-op for scope-controlled devices

- informative operator message

- not a crash

  

## Unknown Group

  

If the UI requests a named group that does not exist:

  

- activation must fail clearly

- runtime must not silently fall back to `All`

  

## Required Infrastructure Failure

  

If always-instantiated infrastructure devices cannot be brought up:

  

- runtime activation must surface that condition explicitly

- the operator must be able to see that this is different from “scope group was empty”

  

## Examples

  

## Example 1: All-In Bringup

  

Selected profile defines:

  

- `roborio`

- `pdp`

- `FALCON 9`

- `SPARKMAX/NEO 25`

- `lmtSw0`

  

Operator chooses:

  

- `Runtime Activate`

- scope = `All`

  

Expected outcome:

  

- `roborio` and `pdp` instantiated

- `FALCON 9`, `SPARKMAX/NEO 25`, and other eligible scope-controlled devices instantiated

- diagram still shows every device

- right panel shows all of them in scope

  

## Example 2: Incremental Bringup Using `active-group`

  

Selected profile defines full robot topology.

  

`active-group` contains only:

  

- `SPARKMAX/NEO 25`

  

Operator chooses:

  

- `Runtime Activate`

- scope = `Group: active-group`

  

Expected outcome:

  

- `roborio` and `pdp` instantiated

- `SPARKMAX/NEO 25` instantiated

- `FALCON 9` shown in topology but out of scope and uninstantiated

- right panel clearly distinguishes:

  - `SPARKMAX/NEO 25`: in scope, instantiated, present

  - `FALCON 9`: defined, out of scope, not instantiated

  

## Example 3: Empty `active-group`

  

Operator chooses:

  

- `Runtime Activate`

- scope = `Group: active-group`

  

`active-group` has no members.

  

Expected outcome:

  

- `roborio` and `pdp` instantiated

- no other devices instantiated

- UI displays:

  - `Activation scope group is empty. No scoped devices were instantiated.`

  

## Tradeoffs

  

- This model is more explicit but adds operator-visible state and choices.

- It reduces accidental hardware activation but requires clearer UI messaging.

- It avoids conflating “defined in config” with “currently instantiated.”

- It requires a stronger runtime-state contract between UI and robot.

  

## Future Extensions

  

- per-category policy table for optional non-motor devices

- profile defaults for preferred activation scope

- CLI support for explicit scope-aware runtime activation

- scope-aware test filtering and test gating

- richer diagram legend for `defined`, `scoped`, `instantiated`, `present`

  

## Definition Of Done

  

This feature is done when:

  

- `Runtime Activate` accepts explicit scope choice from the UI

- `All`, `Group: active-group`, and `Group: <named group>` are supported

- `roborio` and `pdp/pdh` always instantiate/deactivate with runtime

- empty selected groups no-op cleanly with a clear message

- the diagram still shows all defined devices

- the diagram and right-side panel both show:

  - in scope

  - instantiated

  - present

- the UI detects and reports UI/robot activation scope mismatch

- incremental bringup no longer requires full-device instantiation just to make runtime usable