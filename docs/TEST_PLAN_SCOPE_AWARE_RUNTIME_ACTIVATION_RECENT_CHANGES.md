
# Scope-Aware Runtime Activation Test Plan

## Purpose

Validate the recent scope-aware runtime activation changes across robot runtime, Bridge CLI, and Bringup UI.

## Focus

This plan targets the recent changes only:

- scoped `runtime activate` command forms
- UI runtime scope selector and deactivate-before-change workflow
- runtime lockouts while active
- `active-group` edit rejection while runtime is active
- runtime-state/reporting exposure of requested scope, applied scope, and lock state
- out-of-scope device gray-blue coloring and legend behavior in the live topology
- clarified first-pass group-run semantics

## Out Of Scope

- motion-quality validation of physical hardware behavior under load
- a new partial executor for multi-device DSL tests
- unrelated diagnostics, topology, or changelog workflows

## Recent Changes Under Test

1. Robot-side `runtimeActivate` accepts explicit `scopeMode` and `group`.
2. Robot runtime instantiates by selected scope instead of unconditionally instantiating everything.
3. `active-group` edits are blocked while runtime is active.
4. CLI supports:
   - `runtime activate`
   - `runtime activate <profile>`
   - `runtime activate scope all`
   - `runtime activate scope group <group>`
   - `runtime activate <profile> scope all`
   - `runtime activate <profile> scope group <group>`
   - `runtime deactivate`
5. Bringup UI exposes a runtime scope selector and disables scope changes while runtime is active.
6. Runtime-state/reporting exposes:
   - requested scope
   - applied scope
   - scope lock state
   - per-device `inScope`
   - per-device `notTestableReason`
7. Live topology uses a distinct gray-blue visual treatment for out-of-scope devices and explains it in the legend.
8. Group-run semantics are explicit:
   - ad hoc group runs may run eligible members and skip ineligible ones
   - multi-device DSL tests remain all-required

## Preconditions

- Repo is on the intended branch with this feature merged locally.
- `JAVA_HOME` points to the WPILib JDK root.
- Python environment can run repo scripts on Windows.
- For connected checks:
  - roboRIO reachable over REST UI port
  - non-motion validation only
  - safe test profile available

## Test Layers

Run in this order:

1. local syntax and unit coverage
2. local CLI workflow regression
3. manual Bringup UI verification
4. connected robot non-motion validation

## Layer 1: Local Automated Checks

### 1. Java Unit Tests

Command:

```powershell
.\gradlew.bat test
```

Verify:

- `BridgeUiProfileCommandsTest` passes for scoped `runtimeActivate`
- `BridgeUiGroupCommandsTest` passes for active-group lockouts
- `RobotLocalCommandRegistryTest` passes for updated command inventory metadata

Expected result:

- full Java test suite passes

### 2. CLI Runtime Scope Regression

Command:

```powershell
python tools/can_nt/scripts/bridge_cli_runtime_scope_regression.py
```

Verify:

- parser accepts all supported scoped activation forms
- CLI forwards `scopeMode=all`
- CLI forwards `scopeMode=group` with `group=<name>`

Expected result:

- script exits `0`

### 3. Python Syntax Check For UI And Topology Renderer

Command:

```powershell
python -m py_compile tools/can_nt/bringup_ui.py tools/can_topology/live_topology_view.py
```

Verify:

- no syntax error after adding runtime scope UI wiring
- no syntax error after adding out-of-scope color handling in the topology renderer

Expected result:

- command exits `0`

## Layer 2: Local CLI Workflow Validation

Purpose:

Exercise the CLI surface and local semantics without requiring a robot.

### 4. Parser Acceptance

Run interactively or through small command snippets and confirm these parse:

```text
runtime activate
runtime activate test_minimal_25_9
runtime activate scope all
runtime activate scope group active-group
runtime activate test_minimal_25_9 scope all
runtime activate test_minimal_25_9 scope group motors
runtime deactivate
```

Verify:

- no grammar/parser rejection for valid forms
- invalid forms still reject clearly

Negative examples:

```text
runtime activate scope
runtime activate scope group
runtime activate test_minimal_25_9 scope bogus
```

Expected result:

- valid forms parse
- invalid forms fail with explicit runtime syntax errors

### 5. Lockout Contract For Active Group Editing

Method:

- use Java test coverage as the automated proof
- optionally verify by sending robot-side commands in a stubbed/manual environment

Verify:

- `active add` rejected while runtime active
- `groupAddDevice active-group <label>` rejected while runtime active
- `groupRemoveDevice active-group <label>` rejected while runtime active
- named non-active groups remain editable

Expected result:

- rejection message: `Deactivate runtime to edit active-group membership.`

## Layer 3: Manual UI Verification

Purpose:

Confirm the operator-facing workflow is clear and consistent.

### 6. Runtime Scope Selector Presence

Steps:

1. Launch Bringup UI.
2. Observe top header controls.

Verify:

- `Runtime Scope` dropdown exists beside profile/runtime controls
- available choices include:
  - `All`
  - `Group: active-group`
  - other named groups from the selected profile when present

Expected result:

- dropdown is visible and populated from local config

### 7. Runtime Scope Locking

Steps:

1. Connect UI to robot or test endpoint.
2. Ensure runtime is inactive.
3. Confirm scope dropdown is editable.
4. Activate runtime.
5. Attempt to change scope.

Verify:

- dropdown becomes disabled while runtime is active
- `Runtime Activate` is disabled while runtime is active
- `Runtime Deactivate` is enabled while runtime is active

Expected result:

- deactivate-before-change workflow is enforced visually

### 8. Active-Group Edit Locking In UI

Steps:

1. Activate runtime.
2. In the live topology side panel, toggle one `active-group` membership checkbox.

Verify:

- UI does not send a successful edit flow
- operator sees:
  - `Deactivate runtime to edit active-group membership.`

Expected result:

- no live membership mutation while active

### 9. Runtime Scope Status Readout

Steps:

1. Before activation, choose `Group: active-group`.
2. Observe header status text.
3. Activate runtime.
4. Observe status again.
5. Deactivate runtime and switch to `All`.

Verify:

- header shows requested scope
- header shows applied scope
- header shows `editable` while inactive and `locked` while active
- requested/applied values track the selected scope correctly

Expected result:

- scope status is understandable without opening raw JSON

### 10. Show Runtime State From UI

Steps:

1. Click `Show Runtime State`.
2. Inspect output or any raw JSON path used by the UI.

Verify top-level fields:

- `requestedScopeMode`
- `requestedScopeGroup`
- `appliedScopeMode`
- `appliedScopeGroup`
- `requestedScope`
- `appliedScope`
- `scopeLocked`
- `activeGroupEditLocked`

Expected result:

- runtime-state matches the current UI state and runtime status

### 11. Device Detail Reasons In Live Topology

Steps:

1. Activate in a narrow scope such as `Group: active-group`.
2. Select a device outside scope in the live topology.
3. Inspect the device detail/inspector panel.

Verify:

- lifecycle fields indicate the device is not in scope or not instantiated
- `notTestableReason` is visible
- operator can distinguish:
  - out of scope
  - uninstantiated
  - not present

Expected result:

- device-level reason is explicit, not ambiguous

### 12. Out-Of-Scope Node Color And Legend

Steps:

1. Activate in a narrow scope such as `Group: active-group`.
2. Ensure at least one defined device is outside the applied scope.
3. Observe that device in the live topology.
4. Open the UI `Color Key` help/legend window.

Verify:

- an out-of-scope device uses the dedicated gray-blue fill treatment in the live topology
- the device remains visible rather than disappearing from the topology
- the color key includes an entry explaining the out-of-scope color
- the legend wording makes it clear that the device is defined but outside the applied runtime scope
- the out-of-scope color is distinguishable from:
  - red `missing / none`
  - amber `stale / low confidence`
  - green `present / high confidence`

Expected result:

- out-of-scope is visually obvious on the canvas and explained in the legend

## Layer 4: Connected Robot Non-Motion Validation

Purpose:

Prove the command and runtime-state contract against a live robot endpoint without commanding motion-heavy validation.

### 13. Activate In `All` Scope

Steps:

1. Select a known test profile.
2. Run:

```text
runtime activate <profile> scope all
show runtime-state robot --json --pretty
```

Verify:

- runtime becomes active
- applied scope reports `all`
- scope-controlled devices in the profile appear instantiated
- infrastructure devices remain present in runtime-state

Expected result:

- runtime-state and activation behavior match `all` scope

### 14. Deactivate Then Activate In `Group: active-group`

Steps:

1. Run:

```text
runtime deactivate
group member assign active-group <device-a>
runtime activate <profile> scope group active-group
show runtime-state robot --json --pretty
```

Verify:

- runtime deactivates cleanly
- reactivation succeeds
- applied scope reports `group:active-group`
- only expected scoped devices are instantiated

Expected result:

- scoped activation is honored on live robot state

### 15. Reject Active-Group Edits While Active

Steps:

1. Leave runtime active in `Group: active-group`.
2. Attempt:

```text
group member assign active-group <device-b>
```

Verify:

- command is rejected clearly
- existing runtime-state does not change

Expected result:

- lockout contract holds on the live endpoint

### 16. Group-Run Semantics Check

Setup:

- `X` is in `active-group`
- `Y` is in named group `motors`
- runtime is active in `Group: active-group`

Steps:

1. Run a group operation against `motors`.
2. Run a multi-device DSL test that requires both `X` and `Y`.

Verify:

- ad hoc group-run path does not silently widen runtime scope
- out-of-scope member behavior is explicit
- multi-device DSL test remains blocked/all-required rather than silently running partial devices

Expected result:

- group-run and DSL semantics match the documented first-pass contract

## Reporting Checklist

For each test pass, record:

- command used
- selected profile
- selected scope
- whether runtime was active or inactive
- requested scope reported
- applied scope reported
- any device `notTestableReason` seen
- whether out-of-scope devices rendered with the gray-blue fill
- whether the legend entry was present and understandable
- whether rejection/lockout messaging was clear

## Pass Criteria

The recent scope-aware activation changes pass when all of the following are true:

- all local automated checks pass
- UI can select and display scope correctly
- UI enforces deactivate-before-change
- CLI accepts and forwards all supported scoped activation forms
- runtime-state exposes requested/applied scope and lock state
- active-group edits are blocked while runtime is active
- connected robot non-motion validation confirms scoped activation behavior
- group-run semantics match the documented first-pass boundary

## Failure Triage

If a failure occurs, classify it first:

- parser/grammar drift
- CLI forwarding bug
- UI wiring/state bug
- robot runtime scope bug
- runtime-state reporting bug
- group-run semantic mismatch
- stale generated command metadata

Use that classification before changing behavior, so the fix stays narrow and does not blur contract boundaries.
