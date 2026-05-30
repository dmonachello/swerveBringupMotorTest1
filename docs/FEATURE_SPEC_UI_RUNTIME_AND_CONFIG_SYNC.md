SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Feature Spec: UI Runtime Activation and Config Sync

## Purpose

Add explicit runtime activation controls and robot-config synchronization to the Bringup Control UI so the UI can manage selected profile, active runtime, and robot config state without falling back to CLI-only steps.

## Problem

The older UI flow could:

- select a profile
- run incremental bringup actions such as `Add Motor` and `Add All`
- issue direct manual motor commands

But it left critical gaps:

- runtime activation was not exposed as a first-class button
- runtime deactivation was not exposed as a first-class button
- robot-to-host config download was not exposed in the main control surface
- host-to-robot config push was not exposed in the main control surface

That creates operator confusion because:

- selecting a profile in the UI does not activate it
- `Add All` can be mistaken for runtime activation even though it is a different action
- the UI can drift from the robot’s selected profile and current config
- users must return to the CLI for config and runtime actions the UI should own directly

## Goals

- Add explicit `Runtime Activate` and `Runtime Deactivate` actions to the UI.
- Make the UI use the same REST command path as CLI for runtime activation.
- Add a `Download Current Config` action to the UI.
- Add a `Push Config` action to the UI.
- Make runtime activation behavior unmistakable in the UI.
- Make `(none)` the default startup profile selection in the UI unless an explicit preference restores old behavior.
- Keep `Add Motor` and `Add All` as separate incremental bringup tools.
- Make selected profile and active runtime profile visible and easy to distinguish in the UI.
- Reduce operator confusion during handoff from CLI push to UI testing.

## Non-Goals

- Replace the topology editor.
- Add a full UI config editor in this change.
- Remove CLI support for config push or runtime commands.
- Redesign the REST command lifecycle.

## Current Behavior

The UI now supports:

- profile selection through `selectProfile`
- explicit `Runtime Activate`
- explicit `Runtime Deactivate`
- explicit `Push Config`
- explicit `Download Current Config`
- live runtime polling
- direct manual motor actions
- incremental instantiation through `Add Motor` and `Add All`

The UI now treats these as separate actions:

- profile selection
- config push
- runtime activation
- runtime deactivation
- incremental bringup through `Add Motor` and `Add All`

The UI help text must reflect that profile selection alone is not activation and that `Add Motor` or `Add All` remain incremental bringup tools rather than activation surrogates.

## Desired Contract

The UI must expose these explicit operator actions:

1. `Select Profile`
2. `Runtime Activate`
3. `Runtime Deactivate`
4. `Download Current Config`
5. `Push Config`

These must be modeled as different actions with different meanings.

### Select Profile

- updates the robot’s selected profile
- does not activate runtime
- does not instantiate devices

Default startup behavior for the UI profile dropdown must be:

- `(none)` selected

Optional preference:

- `Auto-select default profile on startup`

This preference must be:

- off by default
- selection-only when enabled
- never an activation trigger

### Runtime Activate

- activates the currently selected profile unless an explicit profile name is supplied
- uses the same REST command path as CLI:
  - `POST /commands` with `name: "runtimeActivate"`
- must not be implemented as a UI-only shortcut
- must only happen from an explicit operator button press
- must never happen by default
- must never happen as a side effect of profile selection
- must never happen as a side effect of config push
- must never happen as a side effect of opening the UI or switching tabs

### Runtime Deactivate

- deactivates the active runtime
- uses the same REST command path as CLI:
  - `POST /commands` with `name: "runtimeDeactivate"`

### Download Current Config

- retrieves the robot’s current canonical config payload
- updates the host/UI config model from robot data
- updates visible profile/config state in the UI
- does not activate runtime by itself

### Push Config

- pushes the current host/UI config payload to the robot
- uses the same staged config-apply path as CLI
- selects the pushed profile on the robot
- does not activate runtime unless an explicit UI activate action follows
- must not use a private UI-only config apply shortcut

## UI Behavior

### Runtime Controls

The UI should add a small runtime control section with:

- `Runtime Activate`
- `Runtime Deactivate`
- selected profile indicator
- active runtime profile indicator
- runtime active indicator

Recommended semantics:

- `Runtime Activate`
  - targets the currently selected profile from the UI profile dropdown
- `Runtime Deactivate`
  - deactivates current runtime regardless of selected profile

The runtime control area must be visually explicit enough that an operator can tell:

- which profile is merely selected
- whether runtime is currently inactive
- exactly which button activates runtime

Recommended UI treatment:

- a dedicated `Runtime Activate` button
- a dedicated `Runtime Deactivate` button
- nearby text showing:
  - `Selected Profile`
  - `Active Runtime Profile`
  - `Runtime Active: YES/NO`
- an explicit inactive indicator when no runtime is active

### Config Controls

The UI should add a config synchronization section with:

- `Download Current Config`
- `Push Config`

`Download Current Config` should:

- replace the current local UI config model with robot config
- refresh profile dropdown contents if needed
- refresh topology and group views
- show the selected profile from robot state after load

`Push Config` should:

- push the current host/UI config payload to the robot
- refresh selected-profile state from robot response
- leave runtime inactive unless the operator separately clicks `Runtime Activate`
- make config push and runtime activation visibly separate actions
- never auto-press, auto-chain, or silently trigger runtime activation

### Profile and Runtime Status

The UI must visibly distinguish:

- selected profile
- active runtime profile
- runtime active true/false

These must not be collapsed into a single ambiguous profile label.

The UI must visibly support:

- selected profile = `(none)`

### Interaction Rules

### After CLI Config Push

If the operator pushes config from the CLI and then switches to the UI:

- the UI must be able to refresh from robot state
- the operator must be able to activate runtime from the UI
- the operator must not need to return to the CLI just to activate runtime
- the UI must clearly show that runtime is still inactive until the operator explicitly presses `Runtime Activate`

### Right-Click Manual Motor Run

Right-click manual motor run should require that the target device is instantiated.

The intended UI flow becomes:

1. select profile
2. activate runtime
3. verify runtime state
4. right-click motor run

`Add Motor` and `Add All` remain valid alternatives for incremental bringup, but they must not be treated as the only UI path to usable motor control.

The UI must not imply that right-click motor control is ready immediately after:

- profile selection
- config push
- UI startup

unless runtime has already been explicitly activated or incremental bringup has explicitly instantiated the device.

## REST Requirements

The UI must use existing REST command infrastructure.

Required command usage:

- `selectProfile`
- `runtimeActivate`
- `runtimeDeactivate`
- `profilesApply` or the canonical config-push REST path used by CLI

Required config-download support:

- robot exposes `GET /config/current` for canonical config download suitable for UI reload

Required config-push support:

- robot must accept the canonical config payload through the same staged apply contract used by CLI

Required polling behavior:

- the UI live topology overlay defaults to `2 Hz`
- routine live overlay polling uses a lighter runtime-state snapshot path than full diagnostics polling
- light polling prefers cheaper fields and avoids noisier optional REV reads when possible

## Error Handling

The UI must show clear failures for:

- runtime activation attempted while selected profile is `(none)`
- runtime activation blocked because robot is disabled, if that policy remains
- runtime activation failed because selected profile is invalid
- config download failed because robot is unavailable
- downloaded config could not be parsed into the host model
- config push failed because the local UI config is invalid
- config push failed during transfer, apply, or post-apply verification

The UI should also clearly distinguish:

- config push succeeded but runtime is still inactive
- runtime activation failed
- config download succeeded but changed the local UI model

The UI must also show clear non-failure state for:

- no profile selected
- profile selected but runtime inactive
- config pushed successfully but runtime inactive

The UI must not silently treat:

- `Add All`
- profile selection
- or live overlay polling

as substitutes for runtime activation.

## Status and Messaging

The UI should surface concise status messages for:

- no profile selected
- profile selected
- runtime activated
- runtime deactivated
- config downloaded
- config pushed
- config download failed
- config push failed
- runtime inactive pending explicit activation

The wording must distinguish:

- selected profile
- active runtime
- downloaded config source

## Acceptance Criteria

- The UI exposes `Runtime Activate` and `Runtime Deactivate`.
- Those controls use the same REST command path as CLI.
- The UI exposes `Download Current Config`.
- The UI exposes `Push Config`.
- `Push Config` uses the same staged config-apply path as CLI.
- Runtime activation only occurs from an explicit `Runtime Activate` button press.
- Runtime activation never occurs automatically from selection, push, startup, reconnect, or tab/view changes.
- Driver Station `Disable` deactivates current runtime and frees runtime-owned resources.
- After Driver Station `Disable`, the next motion attempt requires a fresh explicit `Runtime Activate`.
- The UI starts with selected profile = `(none)` by default unless the startup auto-select preference is explicitly enabled.
- After CLI `config push`, the operator can switch to the UI and complete runtime activation there without returning to CLI.
- The operator can also complete the full config push and runtime activation flow entirely from the UI.
- The UI clearly shows selected profile, active runtime profile, and runtime active state.
- `Live Topology` visibly surfaces operator-blocking state such as runtime inactive, robot disabled, and robot E-Stop without requiring the `Output` tab.
- `Add Motor` and `Add All` remain available as separate incremental bringup actions.
- Right-click manual motor test can be reached through a UI-only path after config push and UI runtime activation.

## Example Operator Flow

1. UI:
  - optional `Download Current Config`
   - verify startup selection is `(none)`
   - select profile `test_minimal_25_9`
   - click `Push Config`
   - verify selected profile is `test_minimal_25_9`
   - click `Runtime Activate`
   - verify runtime active state
   - right-click `SPARKMAX/NEO 25`
   - run manual duty test

## Tradeoffs

- Adding runtime controls to the UI increases surface complexity slightly.
- Downloading and pushing config in the UI adds another synchronization path that must stay aligned with CLI and topology/editor semantics.
- The benefit is a clearer and more self-contained operator workflow.

## Future Extensions

- Add explicit `Reload Robot State` and `Reload Local File` controls.
- Add a visible indicator when UI config differs from robot config.
- Add a one-step UI workflow for:
  - select profile
  - push config
  - activate runtime
