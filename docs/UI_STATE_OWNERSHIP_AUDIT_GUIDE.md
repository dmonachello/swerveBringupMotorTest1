SPEC_STATUS: UNIMPLEMENTED_ROLLBACK_REFERENCE

# UI State Ownership Audit Guide

## Implementation Status

Purpose: Record how this guide should be used after rollback.

- This guide is preserved as a debugging/reference document.
- It describes failure patterns and audit locations for the attempted feature work.
- Do not interpret it as proof that the referenced behavior is implemented in the rollback baseline.

## Purpose

Show where to look when the Bringup Control UI behaves as if user changes are being overwritten, reverted, or ignored.

## Core Rule

For operator-editable controls:

- the control itself is the local input
- the robot runtime-state payload is the committed truth
- background refresh must not overwrite an editable control while it is acting as local input

If behavior violates that rule, start with the hotspots below.

## Main Hotspots

## 1. Periodic Poll And Refresh

Purpose: This is where background updates are initiated.

Primary file:

- [bringup_ui.py](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py)

Primary functions:

- [`_poll_nt()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:6226)
- [`_poll_live_overlay()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:6396)
- [`_request_runtime_state_refresh()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:5587)

What to inspect:

- whether polling is blocked while a command is pending
- whether runtime-state refresh is being requested too early
- whether `after_idle(...)` refreshes are being scheduled from too many places

Warning signs:

- `showRuntimeState` being sent while an edit command is still unresolved
- forced refresh after `ACK` instead of `OUT`
- multiple refresh paths for the same action

## 2. Command Lifecycle Handling

Purpose: This is where `ACK` and `OUT` are interpreted.

Primary files:

- [bringup_ui.py](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py)
- [bridge_session.py](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_session.py)
- [command_workflow_service.py](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/command_workflow_service.py)

Primary functions:

- [`_handle_tcp_response()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:6754)
- [`poll_events()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_session.py:418)
- [`send_tracked_command()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/command_workflow_service.py:57)

What to inspect:

- whether a control-affecting command is considered resolved on `ACK`
- whether the command result payload is actually merged into the UI
- whether pending state blocks conflicting follow-up actions

Warning signs:

- UI behavior changes on `ACK`
- `OUT` payload exists but is ignored
- raw `_send_tcp_command(...)` used where tracked command flow should be used

## 3. Runtime-State Apply Paths

Purpose: This is where robot-authoritative state is pushed into the UI.

Primary file:

- [bringup_ui.py](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py)

Primary function:

- [`_apply_runtime_state_payload()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:6556)

What to inspect:

- any direct `.set(...)`, `.configure(...)`, or widget-variable update inside runtime-state apply
- whether editable controls are being overwritten even while they are meant to be local input
- whether the code distinguishes between:
  - editable input controls
  - readback/status controls

Warning signs:

- combobox `.set(...)` from runtime-state while runtime is inactive
- checkbox variables rewritten from poll state immediately after a user click
- status text that contradicts the actual editable control value

## 4. Local Control Event Handlers

Purpose: This is where user intent first enters the system.

Primary file:

- [bringup_ui.py](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py)

Examples:

- [`_on_runtime_scope_selected()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:2439)
- [`_runtime_activate_from_ui()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:6108)
- [`_on_active_group_member_toggled()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:2570)

What to inspect:

- whether disallowed edits are blocked before command send
- whether handler code mutates UI state that cannot be confirmed later
- whether handler code depends on hidden local caches instead of the widget value itself

Warning signs:

- local shadow state created just to “remember” what the control should mean
- optimistic local state that has no explicit robot confirmation path
- edit handlers that immediately schedule unrelated background refresh

## 5. Live Topology Side Panel Controls

Purpose: The live topology view can behave like both a renderer and a control surface.

Primary file:

- [live_topology_view.py](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/live_topology_view.py)

Primary functions:

- [`update_runtime_state()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/live_topology_view.py:1415)
- [`apply_runtime_group()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/live_topology_view.py:1557)
- [`_render_active_group_rows()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/live_topology_view.py:2535)
- [`_on_active_group_member_checkbox_toggled()`](c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/live_topology_view.py:2719)

What to inspect:

- whether side-panel controls are disabled when edits are not allowed
- whether row rendering is using committed runtime groups or stale local assumptions
- whether renderer code is also trying to own operator intent

Warning signs:

- checkboxes staying enabled while runtime is active
- renderer rewriting checkbox variables while a command is in flight
- view-local membership caches that can drift from robot state

## 6. Robot Authoritative State Builder

Purpose: This is the committed truth the UI is supposed to mirror.

Primary Java files:

- [BridgeUiCommandHandler.java](c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java)
- [BridgeUiGroupCommands.java](c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiGroupCommands.java)

Primary functions:

- [`buildRuntimeStateJson()`](c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java:3363)
- `groupAddDevice(...)`
- `groupRemoveDevice(...)`

What to inspect:

- whether runtime-state JSON includes the actual confirmed state
- whether command result payloads include enough data for immediate UI reconciliation
- whether lock rules are enforced at the robot boundary

Warning signs:

- command succeeds but runtime-state JSON still shows old values
- command result omits the changed object payload
- UI is forced to guess state because robot output is incomplete

## Known Risk Patterns

## Direct Widget Overwrite From Poll

Most common symptom:

- user changes a control
- next poll sets it back

Pattern to search:

- `.set(`
- `.configure(state=`
- widget variable `.set(...)`

inside:

- `_apply_runtime_state_payload(...)`
- other `*_payload(...)` adapters

## Shadow Local State

Most common symptom:

- UI and robot both appear “correct” in different places
- later refresh reveals a mismatch

Pattern to search:

- local fields that duplicate editable control meaning
- dictionaries/lists storing “pending edits” beyond a single explicit command lifecycle

Examples of risky names:

- `draft`
- `cached`
- `override`
- `pending_*` that outlive one command result

These are not automatically wrong, but they should be treated as suspicion points.

## Renderer Also Acting As Controller

Most common symptom:

- a side panel or overlay both displays and owns control state

Pattern to search:

- view class stores runtime state and local editable state together
- `update_runtime_state(...)` and click handlers both mutate the same widget variables

## Practical Audit Checklist

When a UI control reverts unexpectedly:

1. Identify the editable control.
2. Find its user event handler.
3. Find all places that can write back into that control or its bound variable.
4. Check whether a background poll can run before command `OUT`.
5. Check whether `OUT` payload is being applied.
6. Check whether the robot runtime-state JSON actually confirms the new value.
7. Remove any hidden state that tries to outsmart the robot truth unless it is strictly transient and command-scoped.

## Grep Shortcuts

Useful searches:

```powershell
rg -n "_apply_.*payload|showRuntimeState|after_idle\\(_request_runtime_state_refresh|send_tracked_command|_tracker.is_pending|\\.set\\(" tools/can_nt
```

```powershell
rg -n "buildRuntimeStateJson|groupAddDevice|groupRemoveDevice|requestedScopeMode|appliedScopeMode" src/main/java/frc/robot
```

```powershell
rg -n "Checkbutton|Combobox|update_runtime_state|apply_runtime_group" tools/can_topology tools/can_nt
```

## Preferred Fix Direction

When fixing these issues:

- prefer one authoritative robot state source
- prefer disabling disallowed edits before click
- prefer tracked commands over raw sends
- prefer serial command completion over speculative merge logic
- prefer explicit readback from robot-confirmed state over hidden UI caches

If a fix requires local temporary state, keep it:

- short-lived
- command-scoped
- obvious
- cleared on resolution

## Future Extension

This guide should be updated whenever a new UI control both:

- accepts operator edits
- and is also refreshed from runtime-state or NT background updates

That is the highest-risk combination for overwrite and drift behavior.
