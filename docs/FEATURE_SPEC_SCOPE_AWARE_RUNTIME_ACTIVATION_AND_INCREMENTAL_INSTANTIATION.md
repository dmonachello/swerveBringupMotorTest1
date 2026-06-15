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

First-pass operational rule:

- the scope selector is enabled only while runtime is inactive
- the scope selector is disabled while runtime is active
- changing runtime scope requires `Runtime Deactivate` first, then a new `Runtime Activate`

## UI Ownership And Robot Synchronization

The UI is authoritative for the requested activation scope.

Required behavior:

1. operator selects activation scope in the UI
2. UI sends `runtimeActivate` with explicit scope information
3. robot runtime applies that scope
4. UI reads back runtime state
5. if robot state does not match requested scope, UI must surface an error condition

The system must not silently allow UI and robot runtime scope state to diverge.

Under the first-pass operational model:

- requested scope and applied scope should normally be identical while runtime is active
- the operator does not edit scope live on an active runtime
- if the operator wants a different scope, they must deactivate runtime first

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

## Device Lifecycle FSM

Scope-aware activation decides which devices are intended to participate in the current runtime session.

The device lifecycle FSM decides what state each device is actually in relative to:

- config definition
- current presence evidence
- activation scope
- runtime instantiation
- explicit operator override for low-score bringup attempts

The FSM is the authoritative lifecycle truth for UI, reports, and command gating.

This FSM determines whether a device is eligible to become `testable`.

This FSM does not define final operational verdicts such as:

- `usable`
- `degraded`
- `failed`

Those remain a separate evidence/test-result interpretation layer.

### Naming Rules

- `present` means evidence-backed currently present.
- `stale` means previously present, but no longer currently present.
- manual override does not directly create true `present` state.
- manual override opens a controlled path to instantiation attempt.
- unknown or unprofiled devices may be observed, but they can never become `testable`.

### Revised Device State Table

| Current State | Event | Next State | Meaning |
| --- | --- | --- | --- |
| `unknown` | `define` | `defined` | Device exists in config |
| `unknown` | `discover` | `unknown-present` | Device seen on bus, but not defined |
| `unknown-present` | `define` | `defined-present` | Seen and now matched to config |
| `unknown-present` | `lost-presence` | `unknown-stale` | Unknown device was present, but is not currently present |
| `unknown-stale` | `discover` | `unknown-present` | Unknown device is present again |
| `defined` | `discover` | `defined-present` | Configured device is currently present |
| `defined` | `enter-scope` | `in-scope` | Defined device is needed by the active profile/test, but not currently present |
| `defined-present` | `lost-presence` | `defined-stale` | Defined device was present, but is not currently present |
| `defined-present` | `enter-scope` | `in-scope-present` | Defined device is needed and currently present |
| `defined-stale` | `discover` | `defined-present` | Defined device is present again |
| `defined-stale` | `enter-scope` | `in-scope-stale` | Defined device is needed, was seen before, but is not currently present |
| `in-scope` | `discover` | `in-scope-present` | Needed device is now currently present |
| `in-scope` | `instantiate` | `instantiated-not-present` | Runtime object created, but no current presence evidence |
| `in-scope` | `manual-override-instantiate` | `override-instantiation-pending` | Operator explicitly authorizes an instantiation attempt despite low score |
| `in-scope` | `exit-scope` | `defined` | Device is no longer needed |
| `in-scope-present` | `lost-presence` | `in-scope-stale` | Needed device was present, but is not currently present |
| `in-scope-present` | `instantiate` | `instantiated-present` | Runtime object created and device is currently present. **TEST-ELIGIBLE** |
| `in-scope-present` | `exit-scope` | `defined-present` | Device is no longer needed, but is still currently present |
| `in-scope-stale` | `discover` | `in-scope-present` | Needed device is present again |
| `in-scope-stale` | `instantiate` | `instantiated-not-present` | Runtime object created, but no current presence evidence |
| `in-scope-stale` | `manual-override-instantiate` | `override-instantiation-pending` | Operator explicitly authorizes an instantiation attempt despite low score |
| `in-scope-stale` | `exit-scope` | `defined-stale` | Device is no longer needed and remains stale |
| `override-instantiation-pending` | `discover` | `in-scope-present` | Presence recovered before instantiation completed |
| `override-instantiation-pending` | `instantiate` | `instantiated-not-present-override` | Runtime object created under override, but no current presence evidence |
| `override-instantiation-pending` | `instantiate-and-discover` | `instantiated-present-override` | Runtime object created under override and the device is now currently present. **TEST-ELIGIBLE** |
| `override-instantiation-pending` | `instantiate-failed` | `override-instantiation-failed` | Override instantiation attempt failed and the failure is latched until cleared |
| `override-instantiation-pending` | `manual-override-clear` | `in-scope-stale` | Operator cancels override before instantiation succeeds |
| `override-instantiation-pending` | `exit-scope` | `defined-stale` | Device is no longer needed |
| `override-instantiation-failed` | `manual-override-clear` | `in-scope-stale` | Operator clears the latched override failure and may try again |
| `override-instantiation-failed` | `exit-scope` | `defined-stale` | Device is no longer needed and the latched override failure is cleared by teardown |
| `instantiated-present` | `lost-presence` | `instantiated-not-present` | Runtime object exists, but the device stopped responding |
| `instantiated-present` | `exit-scope` | `defined-present` | Runtime released, device still currently present |
| `instantiated-not-present` | `discover` | `instantiated-present` | Runtime object exists and the device is present again. **TEST-ELIGIBLE** |
| `instantiated-not-present` | `exit-scope` | `defined-stale` | Runtime released, device remains stale |
| `instantiated-not-present-override` | `discover` | `instantiated-present-override` | Device became present after override path. **TEST-ELIGIBLE** |
| `instantiated-not-present-override` | `manual-override-clear` | `instantiated-not-present` | Override status removed; runtime object still exists, but device is not currently present |
| `instantiated-not-present-override` | `exit-scope` | `defined-stale` | Runtime released, device remains stale |
| `instantiated-present-override` | `lost-presence` | `instantiated-not-present-override` | Runtime object exists, but presence was lost after override path |
| `instantiated-present-override` | `exit-scope` | `defined-present` | Runtime released, device still currently present |

### State Meanings

| State | Meaning |
| --- | --- |
| `unknown` | No config, no evidence |
| `unknown-present` | Device is currently seen, but not defined |
| `unknown-stale` | Unknown device was seen before, but is not currently present |
| `defined` | Config says device should exist, but it has never been seen |
| `defined-present` | Defined and currently present |
| `defined-stale` | Defined, seen before, but not currently present |
| `in-scope` | Defined, needed now, never seen |
| `in-scope-present` | Defined, needed now, currently present |
| `in-scope-stale` | Defined, needed now, seen before, but not currently present |
| `override-instantiation-pending` | In scope, low-score or stale, and operator explicitly forced an instantiation attempt |
| `override-instantiation-failed` | Override instantiation failed and the failure remains latched until the operator clears it |
| `instantiated-present` | Runtime object exists and device is currently present. **TEST-ELIGIBLE** |
| `instantiated-not-present` | Runtime object exists, but device is not currently present |
| `instantiated-not-present-override` | Runtime object exists due to manual override, but device still lacks current presence evidence |
| `instantiated-present-override` | Runtime object exists from the override path and the device is now currently present. **TEST-ELIGIBLE** |

### Lifecycle Events

| Event | Generated when |
| --- | --- |
| `define` | Config contains device |
| `discover` | Existence probability crosses the enter-present threshold upward |
| `lost-presence` | Existence probability crosses the exit-present threshold downward |
| `enter-scope` | Active profile/test requires this device |
| `exit-scope` | Active profile/test no longer requires this device |
| `instantiate` | Runtime wrapper/object is created |
| `instantiate-and-discover` | Instantiation succeeds and presence evidence is immediately available in the same bringup step |
| `instantiate-failed` | Runtime wrapper/object creation attempt fails |
| `manual-override-instantiate` | Operator explicitly forces a low-score device to be eligible for an instantiation attempt |
| `manual-override-clear` | Operator clears the override state |

### Operational Notes

- `present` remains evidence-backed.
- Override does not fake true presence. It only opens a controlled path to instantiation and testing.
- The only testable states are:
  - `instantiated-present`
  - `instantiated-present-override`
- Override provenance is session-scoped and survives until runtime deactivation/teardown.
- Override failure is latched until the operator explicitly clears it.
- A running manual or DSL test may finish even if presence score later falls below threshold; the system must warn rather than revoke the running test.

## Presence Threshold Configuration

Presence threshold hysteresis is configured in profile/config and consumed by the robot runtime FSM.

Required default values:

- `discover` threshold: `0.80`
- `lost-presence` threshold: `0.60`

Required behavior:

- `discover` is emitted when `presenceScore >= discoverThreshold`
- `lost-presence` is emitted when `presenceScore < lostPresenceThreshold`
- threshold evaluation is robot-owned
- the host consumes the resulting state and score

First-pass configuration ownership:

- thresholds are profile/config data
- thresholds are not hardcoded in UI surfaces
- thresholds apply to all device classes unless and until a later schema revision introduces per-class overrides

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
- participate in the same FSM model where possible
- reject invalid lifecycle events with explicit errors

## Scope-Controlled Devices

The following devices are controlled by activation scope:

- motors
- optional sensors/devices added incrementally
- other non-required bringup devices

Examples:

- `FALCON 9`
- `SPARKMAX/NEO 25`
- optional limit switches

First-pass rule:

- only `roborio` and `pdp/pdh` are always-instantiated infrastructure
- all other profile-defined device classes are scope-controlled by default

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

`active-group` is a runtime-managed working set for incremental bringup.

Required behavior:

- `active-group` exists only at runtime and is not persisted into profile/config data
- `active-group` state is maintained for the current host-app session
- `active-group` membership may be edited only while runtime is inactive
- `active-group` membership editor is disabled while runtime is active
- membership changes do not silently instantiate or free devices on their own
- membership changes take effect only on the next `Runtime Activate`
- always-instantiated infrastructure devices are unaffected by `active-group` membership edits

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
- the system reports the currently applied active set plainly, even when that set contains zero scoped devices
- the empty scoped set is a normal runtime state, not a special-case failure

## Group Membership Change Semantics

Editing group membership and changing runtime instantiation are related, but they are not the same action.

Required rule:

- group membership edits update the future activation scope membership only
- runtime instantiation does not change while runtime is active
- changing membership that should affect runtime requires deactivation first
- the next `Runtime Activate` uses the current membership as part of scope selection

Example:

1. `active-group` currently contains `SPARKMAX/NEO 25`
2. runtime is inactive
3. operator adds `FALCON 9` to `active-group`
4. operator activates runtime in `Group: active-group`
5. runtime instantiates `SPARKMAX/NEO 25` and `FALCON 9`

Removal example:

1. `active-group` currently contains `SPARKMAX/NEO 25` and `FALCON 9`
2. runtime is active in `Group: active-group`
3. operator wants to remove `FALCON 9`
4. operator must deactivate runtime first
5. operator removes `FALCON 9` from `active-group`
6. operator activates runtime again in `Group: active-group`
7. runtime instantiates only `SPARKMAX/NEO 25`

This separation is required so the operator can edit membership deliberately without causing surprise hardware/runtime churn on every list change, and so the runtime shape remains stable for the full active session.

## Eligibility Rules

A device is eligible for scope-based instantiation when all of these are true:

- it is defined in the selected profile
- it belongs to the selected activation scope, or the scope is `All`
- it is enabled in that scope membership
- it is not part of the always-instantiated infrastructure category
- it is not excluded by an unsupported device class rule
- it is not blocked by a hard safety rule

Instantiation eligibility is not the same as testability.

Rules:

- scope eligibility controls whether runtime may instantiate the device
- lifecycle state controls whether the device is `testable`
- health/usability evidence does not directly remove `testable`
- hard safety rules outside this FSM may still block actuation if necessary

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

The UI must also provide an explicit override control for devices in eligible low-score states:

- explicit override button
- immediate `manual-override-instantiate` event on click
- explicit clear action for latched override failure

Control enable/disable rules:

- when runtime is inactive:
  - `Runtime Activate` enabled
  - scope dropdown enabled
  - `Runtime Deactivate` disabled
- when runtime is active:
  - `Runtime Activate` disabled
  - scope dropdown disabled
  - `Runtime Deactivate` enabled

If runtime is active, the UI must make the lock explicit rather than only greying out controls.

Required operator messaging examples:

- `Scope locked while runtime is active. Deactivate runtime to change scope.`
- `Deactivate runtime to edit active-group membership.`

## Group Membership Visibility And Editing

The UI must plainly show current membership for:

- runtime-managed `active-group`
- any named group selected as the current activation scope

Named groups are read-only in the UI.

The operator may manipulate membership only for `active-group`.

Minimum first-pass capabilities:

- view the full member list for the currently viewed group
- see which defined devices are not currently in `active-group`
- add a device to `active-group`
- remove a device from `active-group`
- understand whether the panel is editable or locked for the current runtime state

The UI should make these distinctions visible:

- group member
- in current activation scope
- currently instantiated
- currently present

If runtime is active, the UI must state clearly that membership editing is locked until deactivation.

## Lower-Right Group Membership Panel

The UI should use the lower-right panel as the primary first-pass group membership editor.

Required first-pass behavior:

- the panel lists all devices in the selected profile when editing `active-group`
- named-group views may show membership, but they are read-only in the UI
- each listed device has a checkbox representing desired membership in `active-group` for the current app run
- checked means the device is a member of that group
- unchecked means the device is not a member of that group

For example, when the operator is working with `active-group`:

- the panel shows all devices in the selected profile
- the checkbox state indicates current `active-group` membership for each device
- checking a device changes the next activation's membership
- unchecking a device changes the next activation's membership
- checkbox state is runtime/session state only and is not persisted into profile/config data

The panel must also show enough adjacent state to keep membership editing understandable.

Minimum required per-device columns or indicators:

- device display name
- device type or class
- membership checkbox for the selected group
- current instantiated state
- current present state
- current testable state

Checkbox edits update future activation membership only, and they do not directly instantiate or free runtime resources.

Checkboxes must be disabled/greyed-out when runtime is active.

Additional first-pass disabled/greyed-out reasons include:

- out of selected profile
- unsupported device class
- always-instantiated infrastructure
- hard safety block

The panel must clearly separate:

- `active-group` membership
- applied runtime scope state
- actual instantiated state

The panel should show a lock reason while runtime is active, for example:

- `Deactivate runtime to edit active-group membership.`

## Diagram Requirements

The diagram must always show all defined topology devices.

The diagram must also visually indicate:

- in current activation scope
- instantiated now
- present now

These states must remain synchronized with the right-side panel.

The diagram must not hide devices simply because they are out of scope or uninstantiated.

Any surface that uses devices must consume the robot-owned FSM state rather than reconstructing device testability locally.

## Right-Side Panel Requirements

The right-side panel must expose the same three concepts explicitly:

- `in scope`
- `instantiated`
- `present`

This should apply to:

- selected device details
- active group / named group summaries
- group run inspector views when active

Normal device-facing surfaces should show at minimum:

- `presenceScore`
- `testable`

`testable` is a composed state that depends on both robot-side and host-side data.

First-pass rule:

- robot-side lifecycle/instantiation state is necessary but not sufficient
- host-side evidence/presence/observation state is necessary but not sufficient
- UI and CLI surfaces must consume the resulting composed `testable` state rather than reconstructing it independently

A debug panel must expose the full per-device FSM contract:

- `lifecycleState`
- `presenceScore`
- `testable`
- `overrideActive`
- `overrideOriginated`
- `overrideFailure`
- `lastEvent`
- `lastTransitionTimeMs`
- `notTestableReason`

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
- requested activation scope
- current applied activation scope
- scope members
- instantiated devices
- present devices
- per-device lifecycle FSM fields

Per-device required runtime-state fields:

- `lifecycleState`
- `presenceScore`
- `testable`
- `overrideActive`
- `overrideOriginated`
- `overrideFailure`
- `lastEvent`
- `lastTransitionTimeMs`
- `notTestableReason`

The UI must read this back after activation and verify it matches the requested scope.

`showRuntimeState` is the canonical source for this contract.

Other host surfaces may mirror or cache these values, but they must not become a competing source of truth.

## CLI Command Surface

The CLI must support this feature through commands that cleanly separate:

- inactive-session group membership editing
- runtime activation
- runtime deactivation
- runtime-state inspection

The CLI must not overload membership-edit commands so that they silently mutate runtime instantiation state.

## Existing CLI Commands That Remain Relevant

The existing CLI already provides command families that remain part of the workflow:

- `runtime activate [<profile>]`
- `runtime deactivate`
- `show runtime-state [robot|local|both] [--json] [--pretty]`
- `show group <name>`
- `show groups`
- `group member assign <group> <label>`
- `group member remove <group> <label>`
- `copy group <src> <dst>`
- `active show`
- `active add`
- `active next`

These existing commands continue to matter, but they must be interpreted consistently under the scope-aware model.

## Required CLI Semantics

Required rule:

- group membership commands edit desired membership only
- runtime activation commands activate runtime under an explicit scope
- runtime scope may not change while runtime is active
- changing scope requires deactivation first
- runtime-state inspection commands verify applied state

Under this model:

- `group member assign ...` does not directly instantiate a device
- `group member remove ...` does not directly free a device
- `active add` does not directly instantiate a device
- `active next` does not directly instantiate a device
- `active-group` remains a runtime/session construct even when edited from the CLI
- editing `active-group` while runtime is active must be rejected clearly

## New Scope-Aware CLI Commands

The CLI should add a small explicit runtime-scope activation form without introducing a separate live scope-apply workflow.

Implemented command forms:

- `runtime activate`
- `runtime activate <profile>`
- `runtime activate scope all`
- `runtime activate scope group <group>`
- `runtime activate <profile> scope all`
- `runtime activate <profile> scope group <group>`
- `runtime deactivate`

This keeps one runtime activation family while preserving the operational rule that scope changes require `runtime deactivate` first.

## CLI Workflow Examples

### Example 1: Activate In `All` Scope

```text
runtime activate test_minimal_25_9 scope all
show runtime-state robot --json --pretty
```

Expected behavior:

- runtime activates using the selected profile
- all eligible scope-controlled devices are instantiated
- always-instantiated infrastructure devices are instantiated
- `show runtime-state` reports applied scope `all`

### Example 2: Activate In `active-group` Scope

```text
runtime activate test_minimal_25_9 scope group active-group
show group active-group
show runtime-state robot --json --pretty
```

Expected behavior:

- runtime activates in group scope
- only eligible `active-group` members are instantiated
- always-instantiated infrastructure devices are instantiated
- `show runtime-state` reports applied scope `group` with `active-group`

### Example 3: Edit Membership Then Activate

```text
group member assign active-group SPARKMAX/NEO_25
group member assign active-group FALCON_9
show group active-group
runtime activate test_minimal_25_9 scope group active-group
show runtime-state robot --json --pretty
```

Expected behavior:

- the membership edits update desired `active-group` contents
- no runtime mutation happens before activation
- activation instantiates the current `active-group` members
- runtime-state output reflects the applied membership

### Example 4: Change Membership After A Prior Active Session

```text
runtime deactivate
group member remove active-group FALCON_9
show group active-group
runtime activate test_minimal_25_9 scope group active-group
show runtime-state robot --json --pretty
```

Expected behavior:

- the operator must deactivate runtime first
- the membership edit changes the next activation membership
- the next activation instantiates only the remaining scoped members

## `active-group` Helper Command Semantics

`active show`, `active add`, and `active next` remain useful for incremental bringup workflows.

Under this feature, their semantics must be explicit:

- `active show` reports current desired `active-group` membership
- `active add` grows desired `active-group` membership using the next eligible device
- `active next` advances the guided active-device workflow or selection logic without implicitly widening instantiated runtime scope

If these commands are attempted while runtime is active:

- the UI and CLI should reject the mutation clearly
- the runtime shape must remain unchanged

## Runtime Inspection Commands

`show runtime-state` remains the canonical CLI inspection command for this feature.

That view should report at minimum:

- requested activation scope
- applied activation scope
- active group name when scope mode is `group`
- applied scoped membership
- runtime active or inactive

## Grammar And Help Synchronization

If these CLI commands are implemented:

- `tools/can_nt/bridge_cli_ebnf.txt` must be updated in the same change
- parser/help text must be updated in the same change
- regression coverage must include scope activation and deactivate-before-change flows

This CLI contract is operator-facing behavior and must not drift between grammar, help, parser, and runtime implementation.

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

## Invalid Event Handling

If an invalid event is given to a device or device class:

- the robot runtime must surface an explicit error
- the event must not be silently ignored
- the condition must be treated as a bug in the caller or runtime logic

Examples:

- giving a non-applicable override event to a device that cannot support that path
- asking an impossible transition from the current state
- trying to promote an unknown/unprofiled device toward `testable`

## Group Run Behavior

Group behavior is derived from member device states.

Rules:

- groups do not own a separate lifecycle FSM in this first pass
- each member uses its own device FSM
- runnable members run
- non-runnable members are skipped explicitly
- skip reasons must be shown to the operator

This applies to:

- right-click group runs
- active-group runs
- ad hoc device-group execution paths that enumerate members one by one

First-pass rule:

- group-run eligibility uses the applied runtime scope
- the operator must be able to tell whether a skipped or blocked device is out of runtime scope versus merely absent/not testable

Out of scope for this feature:

- introducing a new member-wise partial executor for multi-device DSL tests
- changing a multi-device DSL test so it silently runs only a subset of its required devices

Current contract:

- ad hoc group runs may run eligible members and skip ineligible members with explicit reasons
- multi-device DSL tests remain all-required unless a later spec explicitly introduces partial-execution semantics

## Runtime Deactivation And Config Change Behavior

Runtime deactivation must remove instantiation state and return each device to the non-instantiated state implied by:

- current config definition
- current scope membership
- current presence evidence

Override provenance and override failure are cleared on runtime deactivation because they are current-runtime-session state.

When profile/config changes:

- affected runtime state is invalid
- runtime is torn down
- config is re-read
- FSM state is rebuilt from config plus current evidence
- runtime must be explicitly reactivated by the user

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

## System Impact

## Runtime Behavior Impact

Implementing this feature changes the meaning of runtime activation.

`Runtime Activate` can no longer mean only:

- load the selected profile
- rebuild runtime
- instantiate every configured device

It must instead mean:

- activate the selected profile under an explicit activation scope
- instantiate always-instantiated infrastructure devices
- instantiate only devices eligible under the applied scope
- preserve explicit distinction between full defined topology and current runtime scope

This means the robot runtime must own and keep synchronized:

- selected activation scope
- applied runtime scope
- instantiated device set
- always-instantiated infrastructure devices
- per-device lifecycle state
- locked/unlocked control state while runtime is active or inactive

Existing full-activation and incremental bringup paths must converge on one lifecycle model rather than remaining as partially independent flows.

## UI And Operator Workflow Impact

This feature makes the operator workflow more explicit.

The UI must now surface and keep synchronized:

- full defined topology
- selected activation scope
- group membership
- applied runtime scope
- instantiated state
- present state
- testable state

This increases UI state complexity, but it removes ambiguity that currently exists between:

- defined in config
- intended for current bringup
- instantiated now
- physically present now

The host UI must treat robot runtime state as the authoritative applied-state source.

Host-side surfaces may stage edits and cache views, but they must not invent competing interpretations of:

- scope membership
- instantiated state
- testability

## Group Editing And Runtime Locking Impact

Group membership editing becomes an explicit desired-state workflow.

Operationally, this means:

- changing a group membership checkbox does not immediately instantiate or free runtime resources
- membership edits are allowed only while runtime is inactive
- changing runtime scope or `active-group` membership requires deactivation first

This affects system behavior in an intentional way:

- the operator can safely edit group membership without causing surprise runtime churn
- the active runtime shape remains stable for the duration of the session
- logs and operator reasoning stay simpler because there is only one committed runtime shape at a time

This model is required for predictable incremental bringup, especially when the operator is assembling or revising the next working set device-by-device and needs strong confidence that the runtime shape is not drifting live.

## Test Execution And Command Gating Impact

Tests and group runs must stop assuming that runtime-active implies all profile devices are available.

Execution paths must distinguish between at least these cases:

- defined but out of scope
- in scope but not instantiated
- instantiated but not present
- instantiated and present

This affects:

- selected-test execution
- group runs
- skip-reason reporting
- testability gating
- operator-facing summaries

The system must report these distinctions plainly so operators understand whether a device is unavailable because it:

- was not selected into the active scope
- failed instantiation
- is instantiated but lacks current presence evidence

## Config And Lifecycle Impact

This feature does not require a profile schema redesign, but it does tighten config and lifecycle semantics.

In practice:

- group membership becomes a stronger part of runtime behavior
- `active-group` editing becomes an inactive-session workflow
- runtime deactivation must clear instantiation state cleanly
- profile/config changes must invalidate and rebuild runtime state

After config changes:

- existing applied runtime scope may no longer be valid
- current instantiation state may no longer match the edited config
- runtime must be torn down and explicitly reactivated

This is stricter than an implicitly self-healing model, but it is less ambiguous and easier to reason about.

## Command And Contract Impact

This feature requires stronger robot/host command contracts.

At minimum, the system must define explicit contract fields for:

- requested activation scope
- applied activation scope
- scope membership
- instantiated device set
- per-device lifecycle state
- per-device testability and not-testable reason
- whether scope/membership controls are currently locked

Without this stronger contract, the robot, UI, CLI, and reports will tend to drift into separate interpretations of the same runtime state.

## Partial-Implementation Risk

The main operational risk is partial implementation.

If only runtime activation changes, but the rest of the system does not change with it, the result will be operator confusion and state drift.

Examples of incomplete implementation risk:

- scope-aware activation exists, but runtime-state reporting does not expose applied scope clearly
- group membership can still be edited while runtime is active
- test execution still assumes all runtime-active profile devices are available
- diagram and side panels display different interpretations of instantiation or scope

Therefore this feature should be implemented as one coordinated behavior change across:

- robot runtime activation/deactivation
- runtime-state reporting
- UI scope selection and group editing
- command gating and test eligibility
- operator-facing summaries and mismatch reporting

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
- the scope dropdown is disabled while runtime is active
- `active-group` membership editing is disabled while runtime is active
- the UI tells the operator to deactivate runtime before changing scope or membership
- `roborio` and `pdp/pdh` always instantiate/deactivate with runtime
- empty selected groups no-op cleanly with a clear message
- the diagram still shows all defined devices
- the diagram and right-side panel both show:
  - in scope
  - instantiated
  - present
- the UI detects and reports UI/robot activation scope mismatch
- incremental bringup no longer requires full-device instantiation just to make runtime usable
