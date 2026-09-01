# Current UI And Runtime Rules

  

## Purpose

  

Describe how the UI and robot currently behave as implemented in code on July 27, 2026.

  

This document is intentionally descriptive, not normative.

  

- It records what the code does now.

- It does not describe the older intended designs.

- It does not try to resolve whether every rule is ideal.

- It is the current behavior baseline for UI/runtime changes.

- New code that changes these behaviors should update this document in the same change.

  

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

- User-defined groups exist and work as named groups.

- `Runtime Activate` does two separate things:

  - it activates the selected profile runtime

  - it attempts to activate the controlled lifecycle session for `active-group`

- Runtime instantiation and active scope are different concepts.

  

The current code treats them this way:

  

- profile runtime activation stages the selected profile runtime and restores `active-group` membership

- non-singleton instantiation is limited to the selected/needed scope instead of broad profile-wide creation

- `active-group` controls which devices are in the active controlled session

- manual and DSL operations are expected to act on the currently eligible subset of that scope

  

Current implication:

  

- singleton-backed infrastructure devices may still exist outside the currently selected controlled scope

- non-singleton devices should not be broadly instantiated just because the profile runtime is active

- no, the current controlled-lifecycle model does not intentionally allow `Scope Active: yes` while the device is not instantiated

- selected manual/test scope, not bare profile activation, is the authority for non-singleton runtime creation

## Diagnostics Surface Semantics

Purpose: Capture the current shared meaning for runtime report and Evidence-tab diagnostics details.

- Robot-side queued bringup output generated through `BringupPrinter` is now delivered to the in-process line-listener/UI log path without being mirrored to stdout by default.

- This affects bringup-owned queued status/warning text only; direct WPILib/vendor console output may still appear on NetConsole until those sources are migrated separately.

- Profile/config/runtime `type` now represents the shared classifier device class, not the product model.

- The current NI controller therefore uses `type=robotController` across config, runtime JSON/text, host UI available-device displays, topology/category surfaces, and classifier-derived host views.

- Concrete product identity remains separate in fields such as `model`, so the current hardware may still show `model=roboRIO` while a future controller may show `model=SystemCore`.

- DSL uses the same shared `robotController` family name directly and continues to accept compatibility aliases such as `roboRIO`, `roborio`, and `SystemCore` during device-type normalization.

- Virtual singleton infrastructure devices such as `roborio` are reported as present in robot-local runtime snapshots even though they do not allocate a vendor CAN API object.

- Report, dump, and Evidence surfaces should therefore treat `roborio` presence as a virtual-runtime truth, not as proof of observed CAN traffic.

- The active presence probe now supports `roborio` as a controller-family target using robot-local controller telemetry evidence rather than observed CAN traffic or a vendor CAN motor/sensor handle.

- `roborio` active-probe results are therefore expected to reflect controller-local health such as input voltage, brownout state, CAN status readability, and rail health, while still remaining distinct from passive CAN-observer proof of on-bus traffic.

- The `activePresenceProbe` command now runs as a multi-cycle robot-local command with bounded per-step work instead of attempting to finish the entire probe in one scheduler slice.

- The final probe JSON/text payload remains unchanged in shape, but it is now emitted only when the incremental run completes.

- Runtime JSON report entries for controller-family devices now remain attachment-first but also add a shared `family=robotController` summary shape with nested controller `power`, `bus`, and `rails` sections when those shared attachments are present.

- The human-readable CAN diagnostics report no longer stops at `virtual, no API` for `roborio`; it now summarizes the same shared controller-family power, CAN-controller, and rail telemetry exposed by the runtime snapshot.

- Runtime/report surfaces now expose motor-spec match state from the shared `motorSpec` attachment instead of relying on console-only warnings.

- When a configured motor label/model does not resolve to a `motor_specs.json` entry, operator-visible text/report surfaces should show an explicit missing-spec warning and the requested model text when available.

- The shared Selection inspector for runtime-backed topology devices now exposes motor-spec match state from the same `motorSpec` attachment, including the requested model text when the spec lookup is missing.

- CAN/fault suspicion wording must distinguish active fault state from sticky-only fault state when the underlying telemetry provides both.

- A sticky-only condition should not be collapsed into the same operator-facing wording as an active fault.

## Evidence Input/Sensor State

Purpose: Describe the current shared `Input/Sensor State` behavior in the `Evidence` tab.

- The robot runtime-state JSON now includes `inputSensorState`, built from the same robot-owned shared model used by `printInputs`.

- The shared `inputSensorState` model is current-profile-only and currently includes:
  - `xboxController`
  - `limitSwitch`
  - `cancoder` / external encoder
  - `pigeon` / IMU
  - `robotController`

- The `Evidence` tab now includes an `Input/Sensor State` subpanel that shows all supported current-profile rows grouped by family instead of only the currently selected device.

- The currently selected Evidence device is highlighted in that panel when present.

- Clicking an `Input/Sensor State` device row updates the shared Evidence selected device and synchronizes the existing summary-table and topology selections.

## Evidence Interpretation

Purpose: Describe the current selected-device interpretation fields in the `Evidence` tab.

- The selected-device `Final Interpretation` block in the `Evidence` tab is now a read-only mixed surface:
  - `Overall`
  - `Existence`
  - `Communication`
  - `Operability`
  - `Identity`
  - `Confidence`

- `Overall`, `Existence`, `Communication`, `Operability`, and `Identity` are now populated from the shared host-side evidence-fusion shadow snapshot for the selected current-profile device.

- `Confidence` remains the existing interpreted-row confidence field during this slice and is not yet replaced by a fusion-native overall-confidence field.

- The surrounding Evidence subpanels such as Console, Manual, Enrichment, and Notes remain read-only explanatory companions and are not yet fully re-authored to the fusion-native contract.

- The `Evidence` tab now exposes persistent subpanel visibility checkboxes for:
  - summary
  - topology
  - passive
  - console
  - enrichment
  - inspector
  - input/sensor state

- Those subpanel visibility toggles are stored in host UI preferences, not in profile/config data or robot runtime state.

- The `CAN Bus Health (System Console)` Evidence subpanel now summarizes all active normalized console events, including device-targeted timeout/fault lines, rather than only `system`-scoped events.

- Its `Active Events` count therefore reflects the normalized active console event set across both system and device scopes, while still presenting one overall CAN-bus health interpretation.

## CAN Visibility Selection

Purpose: Describe the current Selection-pane behavior in the CAN Visibility tab.

- Defined visibility rows still use topology-node-backed selection when a matching profile node exists.

- Unrecognized visibility rows now populate the `Selection` pane with a synthetic passive-only detail view when no topology node matches.

- That synthetic detail view may show passive observer facts such as label, observed CAN ID, passive source, and last-seen timing.

- When the shared passive analyzer can resolve an unrecognized row by passive identity, the synthetic Selection view should reuse that shared passive presence result instead of showing a placeholder passive score/status.

- Runtime-owned fields such as scope state, group membership, instantiation, and overrides remain `--` when the device is not mapped into the profile/runtime model.

- The `Shared Passive CAN Deep Dive` pane may show a `Guesses` section for unrecognized passive devices.

- Every item in that section must be labeled as a guess and must stay conservative: manufacturer/device-type family and profile-missing hypotheses are allowed, but topology position, attached mechanism, and exact hardware model beyond available evidence are not treated as fact.

- Unrecognized passive devices use structured default labels derived from passive identity when available:
  - manufacturer token
  - device-type token
  - CAN ID

- Example default label:
  - `REV_MOTORCONTROLLER_07`

- Double-clicking an `Unrecognized Nodes` row offers `Rename Discovered Device` for passive/discovery labeling before config promotion.

- Double-clicking a `Defined Nodes` row offers `Rename Defined Device` for the current local config session.

- Rename is still local to the discovery/passive UI state at that point; it does not write to `bringup_system.json` by itself.

- Renaming from `Defined Nodes` updates the current local config session immediately, including profile membership references that point at that device label, but still does not write to disk until `Save Config`.

- Renaming from `Defined Nodes` also updates saved topology `deviceRef` labels in the current local config session so the Visibility/Live Topology diagram stays aligned with the defined-device catalog after the next save.

- The rename flow rejects empty labels and duplicate labels before applying the passive/discovery rename.

- The defined-device rename flow also rejects empty labels and duplicate labels before applying the in-memory config rename.

- Right-clicking an `Unrecognized Nodes` row now offers `Create Device Definition...`.

- That action never creates anything implicitly and always requires an explicit confirmation dialog before staging a device definition.

- The confirmation dialog shows the proposed canonical fields and marks guessed fields with `*`.

- Confirming that dialog adds the device only to Bringup Control's in-memory selected-profile config for the current UI session.

- The new device should then refresh into `Defined Nodes` immediately in that same UI session even though nothing has been written to disk yet.

- Persisting those pending profile edits now requires an explicit `Save Config` action in Bringup Control; `Create Device Definition...` does not write to disk by itself.

- Bringup Control now exposes `File -> New Blank Config...`, `Open Config...`, `Save Config`, and `Save Config As...` for the local config-editing session.

- `New Blank Config...` supports both:
  - an in-memory unsaved config session
  - an immediately file-backed blank config

- A freshly created blank config session is truly empty:
  - no predefined profile
  - no predefined `default_profile`
  - no predefined device inventory row beyond the empty top-level containers

- `New Blank Config...` is also a scratch-session reset for passive CAN visibility/discovery memory:
  - previously observed `Defined Nodes` / `Unrecognized Nodes` rows are cleared
  - cached passive identity/discovered-label state is cleared
  - cached passive raw-frame history is cleared
  - bridge-side profile-derived CAN label context is cleared, so newly observed passive rows do not immediately reuse the prior config's device labels while the local profile context remains `(none)`

- If discovery-based device creation needs a profile and the current local config session does not have a usable default profile, Bringup Control auto-creates and selects `default` for local authoring.

- `Open Config...` switches the host UI's local config session to the selected `bringup_system.json` path for profile browsing and local edits only; it does not push config to the robot or activate runtime by itself.

- When the UI is connected and the robot-selected profile differs from the local UI profile context, the UI must not silently switch profiles.

- If the robot-selected profile exists in the currently open local config session, the UI prompts explicitly:
  - `Yes`: switch the local UI profile context to the robot-selected profile
  - `No`: keep the current local UI profile context
  - `Cancel`: dismiss without changing local UI profile context

- If the robot-selected profile is missing from the currently open local config session, the UI warns and keeps the current local UI profile context unchanged.

- While connected, the UI treats mismatched local-vs-robot profile/test context as an explicit `Out Of Sync` state instead of silently switching either side.

- In `Out Of Sync` state, Bringup Control shows a compact LED-only header sync indicator beside the profile dropdown instead of a text warning sentence.

  - green: host and robot context match
  - red: host and robot context differ
  - neutral: transport or handshake state is not ready yet

- `Resolve...` offers only explicit operator choices:
  - `Yes`: use robot context in the UI only
  - `No`: apply the current UI profile to the robot by deactivating runtime first and then sending profile selection
  - `Cancel`: keep editing locally without changing either side

- The compact sync indicator stays visible in the header at all times.

- The UI does not auto-open the mismatch popup just because robot/runtime state changed; the dialog opens only from a blocked action that requires mismatch resolution.

- `Out Of Sync` does not auto-reactivate runtime after robot-side profile selection.

- Motion-capable actions are blocked while `Out Of Sync` remains unresolved:
  - `Runtime Activate`
  - `Active Add`
  - `Active Next`
  - manual motor duty entry

- `Run Selected` is a special case:
  - if the selected profile/runtime context already matches and only the selected test name differs, the UI first sends `selectTestByName`
  - after that test-only alignment, the normal selected-test readiness rules decide whether the button remains enabled and whether the run may proceed
  - required-device mismatch is not resolved through the `Out Of Sync` popup

- `Runtime Deactivate` remains available during `Out Of Sync` as the safe recovery action.

- `Save Config` writes pending local profile/device edits to the currently loaded config path when the session is file-backed.

- Before writing, `Save Config` repairs saved topology device nodes against the current profile/device catalog: it removes stale unknown `deviceRef` entries and adds missing profile devices so the diagram stays aligned with the current config.

- That topology repair is persisted even when there are no ordinary pending local profile edits; `Save Config` is not treated as a no-op if metadata cleanup is still needed.

- If the local config session exists only in memory, `Save Config` routes through a save-path choice first.

- `Save Config As...` writes the full current local config payload to a new path and keeps the UI session anchored to that new path after the save completes.

- If the user attempts `Open Config...`, `New Blank Config...`, or closes Bringup Control while local config edits are unsaved, the UI prompts with save/discard/cancel instead of silently dropping discovery-created work.

- If `Push Config` is requested while the local config session exists only in memory or still has unsaved local config edits, the UI saves that local config first and only then pushes the resulting file-backed artifact.

- `Refresh` reloads the currently loaded local config path rather than silently snapping back to the canonical deploy file.

## Topology Editor Device Deletion

Purpose: Describe the current deletion behavior in the topology editor.

- The topology editor now distinguishes profile-scoped removal from app-wide deletion.

- `Remove From Profile` is the default removal action for selected topology devices and profile-scoped inventory items.

- `Delete` / `Backspace` in the topology editor is profile-scoped and removes selected devices/callouts from the current profile instead of deleting the shared device definition from the app.

- `Remove From Profile` removes the device from the active profile being edited and prunes active-profile topology/editor references.

- `Remove From Profile` does not delete the shared device definition and does not remove the device from other profiles.

- `Delete From App Entirely` is a separate explicit action for shared device definitions.

- `Delete From App Entirely` removes the shared device definition from app config, removes it from all profiles on save, and prunes related saved-topology and label-based editor references.

- `Delete From App Entirely` is intended for a single shared device definition at a time and is not the default meaning of canvas deletion.

## Topology Editor Config Save Paths

Purpose: Describe the current file-save behavior in the topology editor.

- `Open Config...` loads a full multi-profile `bringup_system.json` from the selected path and makes that file the active source path for later saves.

- `Save Config` writes the full current multi-profile config back to the active source path that was loaded by `Open Config...` or startup default loading.

- `Save Config As...` writes the full current multi-profile config to a new path and then makes that new file the active source path.

- `Save Profile As...` exports a standalone one-profile config file rather than rewriting the full currently loaded multi-profile config.

- Topology-editor-written exports now include canonical root `topology.profiles.<profile>` data so Bringup Control Live Topology and the topology editor can both read the saved graph from the same file.

- Exported files may still retain legacy `diagram.profiles.<profile>` data for compatibility while legacy read fallback remains in place.

- `Save to Deploy` remains an explicit write to the canonical deploy config path.

## Topology Editor DIO Wiring

Purpose: Describe the current DIO-wiring behavior in the topology editor.

- DIO wiring now targets the shared controller-family node rather than a `roboRIO`-named special case.

- The topology editor still persists the existing DIO-link structure for compatibility, but the operator-facing workflow is phrased against the generic robot controller.

- DIO warnings and wiring prompts therefore refer to the robot controller as the required infrastructure node.

  

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

  

Current manual-run consequence:

  

- if controlled lifecycle is active, single-device manual duty still requires the device to be active in that controlled scope

- if controlled lifecycle is inactive, the device may still be manually runnable when the runtime payload marks it testable

- running a device does not itself add the device to `active-group` or make it `Scope Active: yes`

  

## Runtime Activate And Runtime Deactivate

  

Purpose: Document what those top-bar actions currently do.

  

### Runtime Activate

  

Current path:

  

- top-bar `Runtime Activate` resolves the current UI-owned scope first

- both `manual` and `selected test` contexts use the same top-bar runtime activation path

- the host sends `runtimeActivate` with the selected profile when activation is allowed

- robot-side runtime activation rebuilds/stages the selected profile, then activates `active-group` through the shared lifecycle path

  

Current behavior:

  

- requires enabled teleop for the UI activation path

- does not use a separate selected-test activation command path

- uses the current `active-group` membership as the activation authority

- allows `selected test` activation only when the selected test's required devices are already contained in the current `active-group`

- reports `scope swap required` when a selected test would need different membership instead of activating through a separate path

  

Current rebuild details:

  

- reset current core/runtime state

- replace the core

- clear runtime-scoped bridge/group state

- rebuild runtime groups from the current profile config

- restore preserved `active-group` membership

- refresh lifecycle publication before controlled activation without broad profile-wide instantiation

  

Practical result:

  

- `Runtime Activate` is a shared controlled-scope activation action

- `manual` and `selected test` now converge on the same activation authority

- non-singleton devices are created only when that selected scope actually needs them

- it is not an incremental add-members path

  

### Runtime Deactivate

  

Current path:

  

- top-bar `Runtime Deactivate` sends `runtimeDeactivate`

  

Current behavior:

  

- deactivates the active controlled lifecycle session

- deactivates the active profile runtime

- does not rely on tab-specific deactivate behavior

  

Current consequence:

  

- profile runtime devices are deactivated with the active profile runtime

- app-owned singleton-backed allocations may still remain allocated at app lifetime

- robot-side selected-test state is cleared as part of the runtime/core reset path

- after `Runtime Deactivate`, no robot-selected test may remain armed until the operator explicitly selects or runs one again

- there is not intended to be a separate class of active non-profile runtime devices left untouched by this path

  

## Activate And Deactivate Button Rules

  

Purpose: State the intended host-side button-state contract for `Runtime Activate` and `Runtime Deactivate`.

  

The guiding rule is:

  

- a button should be enabled only when pressing it can succeed without first needing some other operator step

  

Current shared prerequisites for both buttons:

  

- TCP/REST connection is live

- runtime state is present

- no tracked command is pending unless the target action is already confirmed ready from runtime state

- no scope/runtime transition confirmation is pending

- a profile is selected

  

Additional prerequisites for `Runtime Activate`:

  

- robot is in `teleop`

- robot is enabled

- robot is not E-stopped

- the current scope owner has a legal activation request for the current state

  

Additional prerequisites for `Runtime Deactivate`:

  

- runtime profile or controlled scope is currently active

- no DSL test is currently running

  

### Decision Table

  

| Scope owner     | Runtime active now | Controlled scope active now | Membership/source change required before next activate | Robot enabled + teleop + not estopped | Selected test valid/ready | `Runtime Activate` | `Runtime Deactivate`                                     | Notes                                                                                      |
| --------------- | ------------------ | --------------------------- | ------------------------------------------------------ | ------------------------------------- | ------------------------- | ------------------ | -------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `manual`        | no                 | no                          | no                                                     | yes                                   | n/a                       | disabled           | disabled                                                 | Nothing to activate when `active-group` is empty or unchanged.                             |
| `manual`        | no                 | no                          | yes                                                    | yes                                   | n/a                       | enabled            | disabled                                                 | Typical case after editing `active-group` while deactivated.                               |
| `manual`        | yes                | yes                         | no                                                     | yes                                   | n/a                       | disabled           | enabled                                                  | Scope already active and nothing new needs to be applied.                                  |
| `manual`        | yes                | yes                         | yes                                                    | yes                                   | n/a                       | disabled           | enabled                                                  | Must deactivate before changing membership, then reactivate.                               |
| `selected test` | no                 | no                          | no                                                     | yes                                   | no                        | disabled           | disabled                                                 | No valid selected test scope to activate.                                                  |
| `selected test` | no                 | no                          | yes                                                    | yes                                   | yes                       | enabled            | disabled                                                 | `Runtime Activate` may first load the selected test's required devices into `active-group`, then activate through the shared lifecycle path. |
| `selected test` | yes                | yes                         | no                                                     | yes                                   | yes                       | enabled            | enabled                                                  | Re-activate is allowed only when the selected test already matches current `active-group`. |
| `selected test` | yes                | yes                         | yes                                                    | yes                                   | yes                       | disabled           | enabled                                                  | Must deactivate before replacing `active-group` membership.                                |
| any             | any                | any                         | any                                                    | no                                    | any                       | disabled           | disabled unless something active can be safely torn down | Disabled, non-teleop, or E-stop blocks activation.                                         |
| any             | any                | any                         | any                                                    | any                                   | any                       | disabled           | disabled                                                 | Also disabled whenever command tracking or transition resync is still pending.             |

  

### Manual Rules

  

Purpose: Record the intended `manual` ownership rules.

  

`Runtime Activate` should be enabled in `manual` scope only when all of these are true:

  

- shared connection/runtime prerequisites are satisfied

- robot enabled-state prerequisites are satisfied

- `active-group` is not empty

- pressing activate would apply a meaningful scope/runtime change

  

`Runtime Activate` should be disabled in `manual` scope when any of these are true:

  

- `active-group` is empty

- the same manual `active-group` scope is already active and no membership change is pending

- membership would need to change while controlled scope is already active

  

`Runtime Deactivate` should be enabled in `manual` scope only when:

  

- shared connection/runtime prerequisites are satisfied

- runtime profile or controlled scope is active

  

### Selected-Test Rules

  

Purpose: Record the intended `selected test` ownership rules.

  

`Runtime Activate` should be enabled in `selected test` scope only when all of these are true:

  

- shared connection/runtime prerequisites are satisfied

- robot enabled-state prerequisites are satisfied

- a test is selected

- the selected test is valid

- all required devices are resolvable

- one of these is true:

  - selected-test scope is currently inactive

  - or selected-test required membership is already contained in the current `active-group`

  

`Runtime Activate` should be disabled in `selected test` scope when any of these are true:

  

- no test is selected

- the selected test is invalid

- one or more required devices are unavailable

- the selected test is already running

- runtime block reason exists for that selected test

- selected test activation would require replacing `active-group` membership while controlled scope is already active

  

This last rule is the important limit-switch case:

  

- if the newly selected test requires one more device than the currently active scope has, the button should be disabled until the operator first uses `Runtime Deactivate`
  
- when selected-test scope is inactive, `Runtime Activate` may load the selected test's required devices into `active-group` before activating the shared lifecycle scope

  

`Runtime Deactivate` should be enabled in `selected test` scope only when:

  

- shared connection/runtime prerequisites are satisfied

- runtime profile or controlled scope is active

- no test is currently running

  

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
- entering `Tests` refreshes `Selected Test Devices` from the selected DSL test and compares that required set against the current robot-backed active scope membership
- entering `Tests` does not automatically rewrite robot `active-group` membership

- leaving `Tests` changes owner mode back to `manual`

- leaving `Tests` does not automatically tear down the shared active scope

  

Important current fact:

  

- the `Tests` tab no longer runs against a separate hidden scope model
- it evaluates the selected test against the shared active scope using required-device containment, not exact membership equality

  

## How Selected Tests Affect Active-Group

  

Purpose: Record the current DSL-selected-test workflow.

  

When the operator selects a test in the `Tests` tab:

  

- the UI sends `selectTestByName`

- the UI resolves required devices from robot-reported test metadata, with local DSL fallback when needed
- the UI refreshes `Selected Test Devices` from the selected test and checks whether all required devices are already present in the current robot-backed active scope

  

Current implication:

  

- extra devices in the active scope are acceptable as long as every device required by the selected test is already included

- `Selected Test Devices` is a presentation of the selected test's required device set overlaid with runtime state, not proof that the host rewrote robot `active-group`

  

## User-Defined Groups

  

Purpose: Clarify what changed and what did not.

  

Current behavior:

  

- user-defined groups still exist in the runtime group model

- they can still be shown and used for manual/group interactions

- they are not the default controlled execution scope

  

Current DSL relation:

  

- `Run Selected` and selected-test activation do not directly execute against an arbitrary user-defined group

- instead, the selected test device set is loaded into `active-group`

- user-defined groups can still be used elsewhere for manual/group workflows

  

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

  

Current singleton classification rule:

  

- shared host-side surfaces treat a device as singleton-backed when the robot runtime payload publishes `lifecycleKind = SINGLETON`

- the host does not rely on hard-coded device labels for singleton locking

  

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

- singleton rows lock when the runtime payload confirms both:

  - singleton lifecycle kind

  - instantiated state

  

## Instantiation Versus Membership

  

Purpose: Document a non-obvious current rule.

  

Current runtime behavior is profile-wide enough that:

  

- removing a device from `active-group` does not necessarily free its runtime object immediately

- `active-group` membership is primarily a scope/actuation rule

- it is not a strict object-allocation rule

  

Current consequence:

  

- a device may be instantiated even while not selected in `active-group`

- if it is not in scope, it still should not be eligible for controlled-scope manual actuation

  

Current meaning of "in scope" for runtime actions:

  

- when controlled lifecycle is active, "in scope" means the runtime device is inside the currently active controlled session

- in host-side runtime payload terms, that usually appears as `lifecycleState=controlled-active`

- when controlled lifecycle is inactive, the system falls back to broader runtime/testable rules instead of a strict active-scope membership requirement

  

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

- this is required for one-device-at-a-time bringup flows and other partial-subset runs

  

Current success rule:

  

- the current implementation treats group manual duty as successful if one or more eligible selected members accepted the duty request

- it does not require every configured member of the named group to run successfully

  

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

  

- the selected test's required devices are already contained in `active-group`

- the scope is active for that selected-test-owned set

- the robot state does not show a blocking condition for that selected test

  

Current meaning of selected-test scope selection:

  

- there is not a separate selected-test runtime scope object anymore

- the `Tests` tab evaluates readiness against the current robot-backed `active-group`

- `Runtime Activate` then activates that `active-group`

- After one terminal `Run Selected` result, the Test Activity tab appends a per-`require` summary for that single test run:
  - one line per `require`
  - pass/fail state
  - sampled signal value when available

- That extra per-`require` summary is suppressed for `Run All`.

  

## Runnable State Panels

  

Purpose: Explain what the green/yellow/red panels are based on.

  

Current status panels are computed host-side from:

  

- connection state

- runtime-state visibility

- stale-state flags

- transition-pending flags

- robot enabled / estop status

- current scope kind

- current selected test state

- `active-group` membership and presence

- host-vs-robot context mismatch state

  

Current simplified decision flow:

  

1. If the UI is disconnected or waiting for runtime state, show a waiting/not-runnable state.

2. If a scope transition is pending, show a resync/not-runnable state.

3. If host-vs-robot profile context is mismatched, the panel remains one of the primary operator-facing places to explain that mismatch.

4. If the robot is E-stopped, disabled, stale, or blocked by scope/test rules, show not-runnable with that reason.

4. If the current scope kind is `selected test`, evaluate selected-test readiness rules.

5. If the current scope kind is `manual`, evaluate `active-group` membership, scope activation, and presence rules.

6. If the relevant scope is active and the required members are acceptable, show ready.

  

Current important consequence:

  

- the panel text is not raw robot text

- it is a host-side interpretation of robot runtime state plus host command/transition state

  

## Active Group Subpanes

  

Purpose: Describe what the right-side group panels actually show.

## Live Topology Lenses

Purpose: Describe the current truth source for each Live Topology lens.

Current behavior:

- `Evidence` is the device-truth lens shared with `CAN Fault Finder` device conclusions.

- `CAN Fault Finder` may add fault-region ranking, suspect boundaries, and next-step detail, but it should not disagree with the Live Topology `Evidence` lens about per-device present/missing/conflict truth.

- In the Live Topology `Evidence` lens, `conflict` is a caution state rather than a hard-failure state:
  - `present` renders green
  - `conflict` renders orange/yellow
  - `missing` and `failed` render red

- `Runtime` is the raw robot-local runtime/presence lens.

- `CAN Visibility` is the raw passive observer visibility lens.

  

### Live Topology Active Group

  

Current behavior:

  

- shows all eligible profile devices, not only current members

- checked rows are current `active-group` members

- unchecked rows are candidate profile devices not currently in the group

- singleton rows should remain visible even when locked

- singleton rows are intended to be non-editable once first-instantiated truth is present in the runtime payload

  

### Tests Selected Test Devices

  

Current behavior:

  

- shows the selected test's required devices

- rows are resolved through the shared group/member-state contract

- `Instantiated` and `Scope Active` come from current runtime state, not from the DSL source alone

### Tests Last Result Header

Current behavior:

- the `Last Result` header in the `Tests` tab shows the terminal `runResult` value when one is present

- passed DSL runs therefore surface precise result names such as `PASS_SENSOR_PROVEN`

- failed DSL runs therefore surface precise result names such as `FAIL_REQUIRE_NOT_MET`

- the success or failure detail text still comes from the shared run payload status/details formatting path

  

## Binding And Group Effects

  

Purpose: Describe the current relationship between group bindings and manual runs.

  

Current behavior:

  

- group bindings do not own exclusive actuation authority for manual single-device right-click runs

- overlapping group bindings should not, by themselves, block manual right-click popups

- manual/group duty is still subject to runtime eligibility and active-scope rules

  

## Current Non-Obvious Consequences

  

Purpose: Capture behaviors that follow from the current implementation and may surprise operators.

  

- `Runtime Activate` is not one-device-at-a-time bringup.

- It is profile-wide runtime activation plus activation of the current `active-group`.

- DSL tests currently work by validating required-device containment against the current `active-group` and then using the same shared activation path.

- Leaving the `Tests` tab does not automatically tear down the shared active scope.

- The `active-group` checkboxes are expected to reflect robot-backed group membership state, not simply current runtime object allocation.

- A device being unchecked in `active-group` does not necessarily mean its runtime object was freed.

- For singleton-backed devices, the intended allocation rule is "allocate once, then persist"; for non-singletons, runtime object lifetime is more rebuild/deactivate-driven.

- Singleton lock state depends on robot-published instantiation truth, not just on the last visible checkbox state.

  

## Code-Derived Summary

  

Purpose: Provide one compact statement of the current system.

  

As the code currently works:

  

- profile activation instantiates the selected profile broadly

- `active-group` is the shared execution scope used by both manual workflows and DSL tests

- the `Tests` tab does not get a separate activation path; it evaluates and activates through the shared `active-group` scope

- controlled lifecycle activation determines `Scope Active`

- singletons are intended to remain allocated once first instantiated and then become locked in membership UIs

- manual and group runs should operate on the currently eligible subset, not fail because of unrelated ineligible members

  

## Common Workflows

  

Purpose: Describe common operator scenarios and the code-driven behavior they should follow.

  

### Manual Scope Activation While Inactive

  

- `Runtime Activate` sends the full runtime activation command, which activates the current `active-group` through the shared lifecycle activation path.

- `selected test` uses that same path once its required devices are already contained in the current `active-group`.

- This is a controlled-scope activation path, not an incremental add-members path.

  

### Manual Membership Change While Scope Is Active

  

- `active-group` membership is locked while a controlled scope session is active.

- Manual membership edits that would change the active controlled scope require scope deactivation before the membership change can take effect.

  

### Selected-Test Activation When Scope Is Inactive

  

- The selected test can be selected and edited offline or while scope is inactive without rewriting `active-group`.

- When the operator highlights a test in the Tests tab, that local choice remains the authoritative `Current Test` in the UI even if the connected robot has not loaded that test into its current runnable test set.

- Runtime/core reset paths do not preserve the robot-side selected test; the host may still show the local current test, but robot-side selection must return to none until an explicit command reloads it.

- In that robot-unknown case, the UI must not keep an older robot-known test as `Current Test`; it should keep the newly selected local test visible and block robot-side selection/run actions with the explicit `not loaded on robot` reason.

- When scope is inactive, the selected-test panel should report `not activated` rather than claiming required devices are unavailable solely because the host has not pushed membership.

- The host UI should present the resulting readiness and action state through shared selected-test readiness logic.

  

### Selected-Test Activation When The Active Scope Has The Wrong Membership

  

- If a selected test requires one or more devices that are missing from the currently active locked scope, the host UI must report that a scope swap is required.

- If the currently active locked scope already contains every required selected-test device, the host must treat that as a match even when the scope also contains extra devices.

- The host must not automatically issue `groupReplaceMembers` while a locked active scope session is running just because the operator selected a different test in the `Tests` tab.

  

### Selected-Test Run After Ready

  

- When selected-test readiness says the test is runnable, `Run Selected` must be enabled under that same shared truth.

- The readiness panel and the action button must not use separate gating rules.

- If only the selected test name differs between host and robot while profile/runtime context already matches, pressing `Run Selected` must first align the robot-selected test with `selectTestByName`, then immediately reevaluate readiness under the same shared rules.

- If required devices are not allocated, `Run Selected` must be disabled rather than routing the operator through the `Out Of Sync` popup.

  

### Leaving The Tests Tab

  

- Leaving test-owned flows must not strand `active-group` ownership or leave the UI in a stale selected-test-only interpretation.

- Ownership restoration and boundary transitions must be handled by the same shared state model used by the UI surfaces.

  

### Manual Right-Click Or Group Duty While Scope Is Active

  

- Manual duty actions remain constrained by the active controlled scope while scope control is active.

- The UI must not expose manual actuation paths that contradict the current active-scope eligibility rules.

  

### Singleton Devices Across Repeated Workflows

  

- Singleton-backed devices keep distinct lifecycle behavior from normal runtime-owned devices across repeated activate/deactivate workflows.

- UI lock/editability state for singleton-backed devices must come from shared runtime lifecycle semantics, not local label heuristics.

  

## Future Use

  

Purpose: Explain how this document should be used.

  

This document is a current-state reference.

  

Use it to:

  

- provide the current behavioral baseline for humans and Codex before changing UI/runtime logic

- understand today’s behavior before changing it

- compare future code changes against the current contract

- identify where implementation and operator expectation still diverge

  

Do not use it as proof that the current behavior is the final desired design.
