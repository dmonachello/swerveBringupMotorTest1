SPEC_STATUS: UNIMPLEMENTED_ROLLBACK_REFERENCE

# Feature Spec: UI Serialized State And Edit Ownership

## Implementation Status

Purpose: Record the current implementation state after rollback planning.

- This document is being preserved during rollback.
- The behavior described here is not the current implemented baseline after rollback.
- Treat this document as design/reference work to be reapplied deliberately later.

## Purpose

Define a serialized state/update contract for the Bringup Control UI so user edits are not overwritten by background refresh, command lifecycle events, or runtime-state redraws.

## Problem

The current UI mixes three different kinds of state:

- local widget state
- command in-flight state
- robot-authoritative runtime state

That creates visible conflicts:

- a runtime scope dropdown selection can revert to the previous robot value
- an active-group checkbox can appear checked and then clear itself
- a control can appear editable even when robot rules do not allow the change

These are not isolated widget bugs. They are consequences of an unclear ownership model.

The current system allows all of these to act on the same controls:

- user click handlers
- periodic `showRuntimeState` refresh
- command `ACK`
- command `OUT`
- NT status updates
- redraw code

Even though Tk work is mostly single-threaded, the UI behaves as if multiple actors are concurrently mutating the same controls.

## Goals

- Make user edits the highest-priority visible state.
- Prevent background refresh from overwriting local user changes.
- Serialize all UI state mutation through one ordered event pipeline.
- Distinguish clearly between:
  - committed robot state
  - local draft state
  - pending command state
- Disable controls before edit when robot rules do not allow the change.
- Keep runtime-state polling, command lifecycle handling, and widget redraw behavior compatible with existing REST command paths.
- Make control ownership rules explicit enough that future UI changes do not bypass them accidentally.

## Non-Goals

- Replace the REST command protocol.
- Redesign the topology editor.
- Redesign robot runtime scope semantics.
- Remove periodic runtime-state polling.
- Convert the entire application to a different GUI framework.

## User Outcome

An operator should be able to:

1. change a UI control without that change being silently overwritten
2. see when a change is only local draft state
3. see when a change is pending robot confirmation
4. see when a change is rejected and why
5. avoid attempting edits that are currently disallowed by runtime rules

## Current Behavior

The current UI allows a background runtime-state refresh to reapply robot-authoritative values directly into editable controls.

Examples:

- runtime scope combobox
  - local selection changes immediately
  - next `showRuntimeState` payload can set it back to robot `requestedScopeMode`
- active-group checkbox
  - local checkmark appears immediately
  - next runtime-state redraw can clear it if robot membership payload still shows old state

This means the same control is acting as both:

- a local editor
- a live robot-state mirror

That dual meaning is the root conflict.

## Core Design

## Serialized Event Pipeline

All state-changing UI processing must be serialized.

The UI must process one event at a time through one common path:

1. receive event
2. classify event
3. update internal state model
4. recompute derived control state
5. render controls from that model

No event source may write directly to widget values outside that pipeline.

Relevant event sources include:

- user control events
- command `ACK`
- command `OUT`
- runtime-state poll responses
- NT state updates that affect control availability

## State Layers

The UI state model must separate these layers.

### Committed State

Purpose: Hold the last robot-confirmed state.

Examples:

- runtime active true/false
- requested scope from robot
- applied scope from robot
- active-group membership from robot
- selected profile from robot

Committed state is updated only from robot-authoritative payloads or confirmed command results.

### Draft State

Purpose: Hold local user edits not yet committed to the robot.

Examples:

- a newly selected runtime scope before `Runtime Activate`
- any future editable control whose action is explicitly staged before apply

Draft state belongs to the UI and must not be overwritten by background runtime-state polling.

### Pending State

Purpose: Hold commands sent to the robot but not yet resolved by terminal output.

Examples:

- `groupAddDevice`
- `groupRemoveDevice`
- `runtimeActivate`
- `runtimeDeactivate`

Pending state has higher precedence than both draft and committed state for rendering.

## Precedence Rules

When rendering one editable control, precedence must be:

1. pending state
2. draft state
3. committed state

Background refresh must be lowest priority for editable controls.

Robot-authoritative refresh may update committed state at any time, but it must not directly overwrite:

- pending edits
- local draft edits

unless the user explicitly cancels the draft or the command is explicitly rejected.

## Control Modes

Every editable control must be represented in one of these modes:

- `disabled`
- `draft`
- `pending`
- `committed`

### Disabled

The user is not allowed to edit the control now.

Required behavior:

- control is visibly disabled before click
- UI shows why the edit is blocked
- UI does not allow optimistic local toggling

### Draft

The user may change the control locally, but the change is not yet committed to the robot.

### Pending

The UI has sent a command and is waiting for final robot output.

Required behavior:

- the local user change remains visible
- the control is locked against conflicting edits until resolved
- background poll may update committed state only

### Committed

The control is showing the last robot-confirmed value.

## Ownership Rules

## General Rule

Editable controls must be editors first and status mirrors second.

If a control allows local editing, then a user edit must remain visible until one of these happens:

- the user cancels it
- the robot confirms it
- the robot rejects it with an explicit failure

The control must never silently revert because a background poll arrived first.

## Polling Rule

Periodic `showRuntimeState` refresh must update committed state only.

It must not:

- directly set editable widgets
- clear local draft state
- clear pending visual state

Rendering must always go through the merged state model.

## Command Rule

Command lifecycle handling must update pending state explicitly.

Required behavior:

- `ACK`
  - marks command accepted
  - does not resolve the edit
- `OUT`
  - resolves the pending edit
  - may update committed state from returned payload
  - may schedule confirmation refresh after resolution

`ACK` must not be treated as final state.

## Per-Control Contract

## Runtime Scope Selector

Purpose: Choose the next runtime activation scope.

Required behavior:

- acts as a draft control while runtime is inactive
- local user selection remains visible after change
- background runtime-state refresh does not overwrite the draft selection
- `Runtime Activate` submits the current draft scope
- after successful activation:
  - pending clears
  - draft clears
  - committed requested/applied scope becomes visible
- after rejected activation:
  - draft remains visible
  - failure reason is shown explicitly

While runtime is active:

- scope selector is disabled
- UI explains that runtime must be deactivated before changing scope

The selector must not act as a live mirror while it is serving as a local draft editor.

## Active-Group Membership Checkboxes

Purpose: Edit `active-group` membership while runtime is inactive.

Required behavior:

- when runtime is active:
  - checkboxes are disabled
  - UI explains that active-group membership can only change while runtime is inactive
- when runtime is inactive:
  - click creates pending add/remove state for that device
  - checkbox remains visually aligned with the requested edit while pending
  - background runtime-state refresh does not clear that pending checkbox state
- on successful command `OUT`:
  - returned group payload or follow-up committed state confirms membership
- on failed command `OUT`:
  - checkbox reverts intentionally
  - failure reason is shown explicitly

## Non-Editable Live Mirrors

Controls that are pure robot-status mirrors may continue to redraw directly from committed state, but they must not share widget state with draft-capable controls.

Examples:

- runtime active indicator
- applied scope status text
- selected device lifecycle fields

## Rendering Contract

UI surfaces must render from the shared state model, not from ad hoc direct widget mutation.

For any control governed by this spec:

- poll handlers update committed state
- command handlers update pending/committed state
- user handlers update draft/pending state
- one render path decides what the widget shows

This contract applies across:

- main controls
- live topology side panel
- status text near runtime controls

## Error And Rejection Behavior

When a user action is disallowed by rules:

- prevent the edit up front when possible
- disable the control
- show a concise reason

When a user action is allowed locally but rejected by the robot:

- do not silently erase the edit
- mark the action as failed
- either:
  - preserve the draft for correction
  - or intentionally revert with an explicit failure notice

Internal invariant failures in this flow must be surfaced as internal UI state bugs, not as generic operator syntax/config errors.

## Serialization Requirements

The UI must treat all control-affecting events as one serialized stream.

This means:

- no direct widget writes from background poll outside the reducer/render path
- no command result path that bypasses the shared state update path
- no local event handler that mutates a widget and also expects later redraw to infer intent

The practical implementation may remain Tk-based and single-threaded, but behavior must match a serialized event queue.

## Suggested Internal Model

One acceptable implementation is a central UI state object with sections such as:

- `committed`
- `draft`
- `pending`
- `capabilities`

And one reducer-style transition path:

- `reduce(state, event) -> new_state`

followed by:

- `render(new_state)`

Equivalent designs are acceptable if they preserve the same ownership and precedence rules.

## Examples

## Example: Runtime Scope Draft

Initial state:

- committed requested scope = `All`
- committed applied scope = `All`
- runtime inactive

Operator action:

- selects `Group: active-group`

Required result:

- widget shows `Group: active-group`
- draft scope = `Group: active-group`
- committed robot scope remains `All`
- background `showRuntimeState` must not reset the widget to `All`

Then:

- operator clicks `Runtime Activate`

Required result:

- pending activation state begins
- on success, committed requested/applied scope updates to `Group: active-group`

## Example: Active-Group Checkbox While Runtime Active

Initial state:

- runtime active = true
- `active-group` membership editing not allowed

Required result:

- checkbox is disabled before click
- UI shows reason such as:
  - `Deactivate runtime to edit active-group membership.`

No optimistic local checkmark should appear.

## Example: Active-Group Checkbox While Runtime Inactive

Initial state:

- runtime active = false
- device not in `active-group`

Operator action:

- checks device box

Required result:

- checkbox remains visibly selected while command is pending
- background poll does not clear it
- command success confirms membership
- command failure intentionally reverts it with explicit notice

## Tradeoffs

- This adds UI state-model complexity compared with direct widget mutation.
- The implementation will require a small refactor of current event and redraw paths.
- Some current controls that look live-editable will need explicit draft semantics or explicit disabling.

These tradeoffs are acceptable because silent overwrite of user edits is a worse operator outcome.

## Compatibility

This spec is compatible with existing:

- REST command names
- `ACK` / `OUT` lifecycle
- periodic `showRuntimeState` polling
- runtime scope activation semantics
- active-group lock semantics while runtime is active

The required change is in UI ownership and rendering behavior, not in the operator-facing command API.

## Implementation Notes

- Prefer incremental adoption starting with:
  - runtime scope selector
  - active-group membership checkboxes
- Add explicit invariant checks at:
  - poll-to-state adapter
  - command-result merge path
  - render path for editable controls
- If a runtime-state payload attempts to overwrite pending or draft state directly, surface that as an internal contract bug.

## Test Requirements

Add or update UI tests to prove:

- runtime scope draft survives background runtime-state polls while runtime is inactive
- runtime scope control disables while runtime is active
- active-group checkboxes are disabled while runtime is active
- active-group checkbox pending state survives background polls until command resolution
- command `ACK` alone does not resolve editable state
- command `OUT` resolves pending state
- failed edits are surfaced explicitly rather than silently reverted

Add connected validation covering:

- runtime inactive active-group edit
- runtime active active-group lockout
- runtime scope draft selection before activation
- runtime scope confirmation after activation

## Future Extensions

- Apply the same draft/pending/committed model to other editable UI controls.
- Add explicit visual styling differences for draft vs pending vs committed state.
- Add a user-visible `Apply` / `Cancel Draft` model for controls beyond runtime scope.
- Unify other UI surfaces around the same reducer/render contract if additional edit conflicts are discovered.
