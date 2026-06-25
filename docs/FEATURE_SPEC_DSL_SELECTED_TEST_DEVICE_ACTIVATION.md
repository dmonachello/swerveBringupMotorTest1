SPEC_STATUS: PROPOSED

# Scope State And Lifecycle Reconciliation

**Purpose**

Define the shared scope-state model and explicit lifecycle reconciliation behavior used across both DSL-selected-test and non-DSL `active-group` workflows.

## Goal

**Purpose**

Make device-scope selection, lifecycle reconciliation, and test execution understandable and repeatable across all bringup surfaces.

- The system should expose one explicit `Scope State` model across DSL and non-DSL surfaces.
- A selected DSL test should declare the devices it needs.
- The operator should be able to activate exactly the desired scope before running a test or manual workflow.
- Re-running the same test or reusing the same manual scope should not require repeating activation.
- Trying a different test or switching to a different manual scope should fail before motion starts if the current instantiated scope is insufficient or inconsistent.
- The existing `active-group` workflow for right-click/manual tests must remain valid as a first-class source mode.

## Non-Goals

**Purpose**

Clarify what this feature does not change.

- Do not replace `active-group` for topology-driven manual tests.
- Do not auto-run a test as part of lifecycle activation.
- Do not silently merge unrelated devices into the current controlled session.
- Do not require the operator to edit `active-group` for DSL tests.
- Do not let any UI surface maintain an independent scope model outside the shared `Scope State`.
- Do not change the passive CAN tool or NetworkTables contracts outside additive scope/test-status fields.

## Problem Statement

**Purpose**

Capture the current operator confusion.

- The system has multiple visible surfaces that imply scope, but they do not yet expose one canonical scope state.
- The DSL/test engine already knows when a test is blocked because a required device is not instantiated.
- The operator surfaces do not make the desired scope obvious before `Run Selected`.
- `active-group` is currently motor-centric and is not a complete operator model for support devices such as `controller0` or `lmtSw0`.
- The same selected test can be known to the robot while the UI still looks like no usable test scope has been prepared.
- The non-DSL tabs also imply a desired working set, but that desired scope is not yet surfaced as a first-class model.

## Core Contract

**Purpose**

Define the new operator-facing behavior.

- The system owns one shared `Scope State` model.
- The model supports at least two source modes:
  - `selected-test`
  - `active-group`
- A selected DSL test has a derived `requiredDevices` set.
- A DSL test is runnable only when every required device is instantiated in the current controlled session.
- A non-DSL manual workflow is runnable only when the instantiated controlled scope matches the apparent active-group-driven candidate scope closely enough to be safe and unambiguous.
- The system adds an explicit scope-preparation action:
  - CLI: `activate selected-test-devices`
  - UI: `Activate Scope` from the `Tests` tab
- This action prepares the controlled session for the currently visible source mode.
- `Run Selected` uses the current instantiated controlled scope as-is.
- `Run Selected` must never auto-reconfigure scope.
- `Run Selected` must fail before motion starts when required devices are missing.

## Conservative Execution Rule

**Purpose**

Make selected-test execution deterministic and non-surprising.

- Entering the `Tests` tab must not change hardware state.
- Selecting a different DSL test must not change hardware state.
- `Activate Scope` and `Deactivate Scope` are the only `Tests`-tab actions that may reconfigure the controlled scope.
- `Run Selected` must not deactivate, instantiate, or reconcile devices automatically.
- If the current controlled scope does not satisfy the selected test, `Run Selected` must block before motion and report the missing devices.

## Separation From `active-group`

**Purpose**

Prevent cross-surface confusion.

- `active-group` remains the working set for right-click/manual duty workflows.
- `active-group` membership and progression semantics do not change because of this feature.
- The DSL selected-test activation path must not rewrite `active-group`.
- Right-click/manual group tests continue to use the current `active-group` and existing manual-duty rules.
- Switching UI tabs must not change instantiated devices or deactivate the current controlled session.

## Source Modes

**Purpose**

Define DSL and non-DSL behavior as sibling source modes under one scope model.

- `selected-test` mode:
  - source is the selected DSL test
  - candidate scope comes from the selected DSL file's declared device list
  - required scope is derived from the candidate scope plus DSL closure
- `active-group` mode:
  - source is `active-group.members`
  - candidate scope comes from the current active-group membership
  - required scope may be identical to the candidate scope unless additional runtime policy requires preserved singletons
- Both modes feed the same lifecycle reconciliation mechanism.
- Both modes must report through the same `Scope State` contract.

## Shared Device-List Model

**Purpose**

Define one shared vocabulary for device-selection state across manual and DSL surfaces.

- The system distinguishes four lists:
  - `availableDevices`
  - `candidateDevices`
  - `instantiatedDevices`
  - `active-group.members`
- `availableDevices` is the profile-scoped pool of devices that may be referenced while authoring or inspecting DSL tests in the `Tests` tab.
- `candidateDevices` is the app-surface working set that activation reconciles toward runtime state.
- `instantiatedDevices` is the current runtime truth for controlled bringup lifecycle state.
- `active-group.members` remains the manual bringup working set for topology/right-click/manual-duty flows.
- These lists may overlap, but they are not interchangeable and must not be conflated in UI text, CLI output, or runtime logic.

## Scope State Contract

**Purpose**

Define the canonical state object that implementation must own and all operator surfaces must render.

This feature must be implemented around one shared scope-state model.

Minimum fields:

- `profile`
  - active profile name
- `sourceKind`
  - one of:
    - `none`
    - `active-group`
    - `selected-test`
- `sourceName`
  - empty when `sourceKind=none`
  - `active-group` when `sourceKind=active-group`
  - selected test name when `sourceKind=selected-test`
- `scopeOwner`
  - one of:
    - `none`
    - `manual-active-group`
    - `selected-test:<test-name>`
- `availableDevices[]`
  - selected-profile device pool used for authoring/reference in the `Tests` tab
- `candidateDevices[]`
  - apparent desired device set for the current visible surface
- `requiredDevices[]`
  - activation-time closure derived from `candidateDevices`
- `instantiatedDevices[]`
  - devices currently live in the controlled runtime
- `missingDevices[]`
  - required devices not present in `instantiatedDevices`
- `preservedSingletonDevices[]`
  - singleton devices intentionally retained outside the visible required set
- `lifecycleState`
  - runtime lifecycle state for this scope model
- `lastReconciledSourceKind`
  - source kind most recently used to produce the active instantiated scope
- `lastReconciledSourceName`
  - source name most recently used to produce the active instantiated scope
- `lastReconciledAt`
  - timestamp or equivalent monotonic readback indicating when explicit reconciliation last completed
- `stateConsistency`
  - one of:
    - `consistent`
    - `stale`
    - `ambiguous`
    - `inconsistent`
- `stateConsistencyReason`
  - human-readable reason when `stateConsistency != consistent`

Normative rules:

- `Scope State` is the single source of truth for source, candidate, required, and instantiated scope reporting.
- The pop-up window, `Tests` tab, and non-DSL tabs must render the same underlying `Scope State`.
- No surface may invent an independent candidate list or instantiated list outside this contract.
- A field may be cached for presentation, but its semantic owner must be the shared `Scope State`.

## Scope State Boundaries

**Purpose**

Keep this feature narrow enough to remain stable when later discovery and debugging features are added.

- `Scope State` answers only:
  - what source currently defines the desired scope
  - what candidate scope is currently visible to the operator
  - what required scope lifecycle reconciliation would act on
  - what instantiated scope currently exists in runtime
  - whether those states are consistent enough to permit test execution
- `Scope State` is not the general CAN discovery model.
- `Scope State` is not the general CAN debugging or evidence model.
- `Scope State` is not the generalized fault-diagnosis model.
- Future features may contribute better readback, confidence, or consistency reasons, but they must not replace the core `Scope State` field meanings.
- Future source kinds may be added without changing the basic contract shape.

Examples of acceptable future extension:

- add a new `sourceKind`
- add richer `stateConsistencyReason`
- add stronger runtime readback for `instantiatedDevices[]`

Examples of unacceptable drift:

- replacing `candidateDevices[]` with a discovery-only concept
- redefining `instantiatedDevices[]` to mean inferred presence rather than actual controlled runtime instantiation
- making the pop-up window or one tab the only authoritative source for scope state

## Scope State Mutation Rules

**Purpose**

Define exactly when each `Scope State` field may change.

Field ownership:

- `availableDevices[]`
  - owned by selected-profile config state
- `candidateDevices[]`
  - owned by current visible-surface source selection rules
- `requiredDevices[]`
  - owned by activation/readiness computation from `candidateDevices`
- `instantiatedDevices[]`
  - owned by runtime lifecycle reconciliation and runtime readback
- `scopeOwner`
  - owned by successful explicit lifecycle activation/deactivation
- `stateConsistency` and `stateConsistencyReason`
  - owned by validation of visible UI state against robot-confirmed/runtime-confirmed scope state

Allowed mutations:

- profile change:
  - may change `profile`
  - may change `availableDevices[]`
  - may change `candidateDevices[]` according to the visible surface's source rule
  - must not directly change `instantiatedDevices[]` without explicit lifecycle action
- entering the `Tests` tab:
  - may change `sourceKind` to `selected-test`
  - may change `sourceName` to the selected test
  - may change `candidateDevices[]`
  - must not directly change `instantiatedDevices[]`
- selecting a different DSL test:
  - may change `sourceName`
  - may change `candidateDevices[]`
  - may change `requiredDevices[]` after recomputation
  - must not directly change `instantiatedDevices[]`
- leaving the `Tests` tab for a non-DSL tab:
  - may change `sourceKind` to `active-group`
  - may change `sourceName` to `active-group`
  - may change `candidateDevices[]`
  - must not directly change `instantiatedDevices[]`
- editing `active-group.members`:
  - may change non-DSL `candidateDevices[]`
  - must not directly change `instantiatedDevices[]`
- `Activate Scope`:
  - may change `requiredDevices[]`
  - may change `instantiatedDevices[]`
  - may change `missingDevices[]`
  - may change `preservedSingletonDevices[]`
  - may change `scopeOwner`
  - may change `lastReconciledSourceKind`
  - may change `lastReconciledSourceName`
  - may change `lastReconciledAt`
- `Deactivate Scope`:
  - may change `instantiatedDevices[]`
  - may change `missingDevices[]`
  - may change `scopeOwner`
  - may change `lastReconciledAt`
  - must not clear selected test or `active-group.members`

Forbidden mutations:

- `Run Selected` must not change `candidateDevices[]`
- `Run Selected` must not change `instantiatedDevices[]`
- tab switching alone must not change `instantiatedDevices[]`
- `active-group` editing alone must not change `instantiatedDevices[]`
- viewing the scope-state pop-up must not mutate any `Scope State` field

## Layering Rules

**Purpose**

Keep implementation aligned so future features consume this model instead of re-implementing it.

- Implementation must separate:
  - source selection
  - candidate scope construction
  - required scope derivation
  - lifecycle reconciliation
  - consistency evaluation
  - operator presentation
- The pop-up window must be a pure view of the shared `Scope State`.
- The `Tests` tab and non-DSL tabs may present different subsets of the model, but they must not maintain different meanings for the same fields.
- Lifecycle commands may mutate scope state, but UI presentation code must not directly mutate runtime scope.
- Discovery/debug features added later may read from `Scope State` and contribute to consistency evaluation, but they must not bypass lifecycle reconciliation rules.

## Tests-Tab Available Devices

**Purpose**

Define the role of the `Tests`-tab available-device table.

- The `Tests`-tab available-device table shows `availableDevices`, not `candidateDevices`.
- `availableDevices` is loaded from the selected profile's device list.
- `availableDevices` is the potential pool of devices that a DSL test may reference.
- `availableDevices` is an authoring/reference surface for test creation, inspection, and source editing helpers.
- `availableDevices` must not be interpreted as the set of devices that the selected test will use.
- Activation and runnability checks must not treat the full `availableDevices` pool as the selected-test scope.

## Candidate List Ownership

**Purpose**

Define which app surface owns `candidateDevices`.

- `candidateDevices` is a surface-local projection that changes when the owning surface changes its apparent desired scope.
- In the `Tests` tab, `candidateDevices` changes when:
  - the UI enters the `Tests` tab
  - the selected DSL test changes
  - the selected DSL source/test definition is refreshed
- In the `Tests` tab, `candidateDevices` is read directly from the selected DSL file's declared device list for the selected test.
- In non-DSL tabs, `candidateDevices` is copied from `active-group.members`.
- In non-DSL tabs, `candidateDevices` must refresh when:
  - the UI switches from the `Tests` tab into a non-DSL tab
  - the `active-group` subpanel membership changes
- Repopulating `candidateDevices` from tab changes, test-selection changes, or active-group edits must not instantiate devices, deactivate devices, or otherwise change hardware state.
- While the `Tests` tab is visible, `availableDevices` may remain profile-scoped even though `candidateDevices` is selected-test-scoped.
- Changing the selected DSL test updates the DSL-tab candidate view, but does not change `instantiatedDevices` until explicit activation.
- Editing `active-group` refreshes the non-DSL candidate source, but does not itself force lifecycle activation.

## Scope Ownership

**Purpose**

Define how the system distinguishes manual and DSL-controlled scopes.

- The controlled session must expose a logical `scopeOwner`.
- Valid initial owners for this feature are:
  - `manual-active-group`
  - `selected-test:<test-name>`
- The owner describes why the current controlled scope was activated.
- Scope ownership is runtime state, not UI-tab state.
- The owner also explains which candidate source was last reconciled into `instantiatedDevices`.

## Tab Switching Rule

**Purpose**

Prevent destructive behavior during normal UI navigation.

- Switching between `Live Topology` and `Tests` must not deactivate devices.
- Simply viewing another tab must not reconfigure scope.
- Tab switching is presentation-only and must not change hardware state.

## Operator-Visible Consistency Rule

**Purpose**

Prevent tests from running when the screen and runtime tell inconsistent stories.

- The UI should make the apparent source, candidate scope, and instantiated scope legible to the operator.
- Lifecycle actions should make runtime state match the apparent desired scope shown on screen.
- If the visible selected test, visible source, `candidateDevices`, `instantiatedDevices`, or `scopeOwner` are ambiguous, stale, or materially inconsistent, the test must not run.
- The system must prefer blocking before motion over making hidden assumptions about scope.

## Lifecycle Activation Semantics

**Purpose**

Define what `Activate Scope` in the `Tests` tab and `activate selected-test-devices` in the CLI actually do.

When invoked for the currently selected test:

1. Resolve the selected DSL test.
2. Read `candidateDevices` directly from the selected DSL file for that test.
3. Deactivate the current controlled session if one is active.
4. Preserve singleton infrastructure according to singleton policy.
5. Compute the activation-time required device closure from `candidateDevices` and DSL references.
6. Reconcile `instantiatedDevices` against that required set.
7. Deinstantiate non-singleton devices that are not required by the selected test.
8. Instantiate exactly the required test devices.
9. Mark the resulting scope owner as the selected test.
10. Activate the resulting controlled session.
11. Report the final activated device set.

The action must not start the test.

The action that triggers this reconciliation is explicit:

- UI: `Activate Scope` from the shared top bar while the `Tests` tab is selected
- CLI: `activate selected-test-devices`
- merely selecting a test or viewing a tab must not reconcile runtime state

The reconciliation rule is:

- activation compares the DSL-derived required activation set to `instantiatedDevices`
- required missing devices are instantiated
- non-singleton instantiated devices outside the required activation set are deinstantiated
- singleton-preserved devices may remain instantiated even when absent from the required activation set

For this DSL-specific activation path:

- `candidateDevices` comes directly from the selected DSL file for the selected test
- activation may extend beyond `candidateDevices` only when DSL references require additional closure devices
- non-singleton devices not required by the selected test must be removed from the controlled scope
- singleton infrastructure may remain according to singleton policy
- no `active-group` mutation is allowed

For manual/diagram-driven activation paths:

- `candidateDevices` comes from `active-group.members`
- reconciliation rules are the same, but ownership remains `manual-active-group`
- DSL selected-test metadata must not be rewritten by manual activation

## Lifecycle Deactivation Semantics

**Purpose**

Define what `Deactivate Scope` does to runtime state versus candidate state.

- Deactivation shuts down or deactivates all non-singleton `instantiatedDevices`.
- Deactivation clears the active controlled session.
- Deactivation clears selected-test UI selection state in the `Tests` tab.
- Deactivation does not clear `active-group.members`.
- Deactivation may leave singleton-preserved infrastructure instantiated according to policy.
- After deactivation, a tab may still show its own `candidateDevices`, but runtime `instantiatedDevices` must reflect the deactivated state.
- In the `Tests` tab, `Deactivate Scope` is the explicit control that tears down the selected-test-owned instantiated scope.

## Cross-Mode Conflict Handling

**Purpose**

Define what happens when the user tries to use a different control mode than the one that owns the current scope.

- A right-click/manual action attempted while the current scope owner is `selected-test:<test-name>` must trigger scope-compatibility preflight.
- A DSL `Run Selected` attempted while the current scope owner is `manual-active-group` must trigger scope-compatibility preflight.
- If the attempted action is already satisfied by the current instantiated scope, it may proceed without reactivation.
- If the attempted action is not satisfied by the current instantiated scope, the system must block before motion and offer an explicit scope transition.

Example operator prompt:

- `Current scope belongs to selected test test_minimal_25_9_spark25_leftY.`
- `Deactivate current scope and restore active-group scope?`

or

- `Current scope belongs to manual active-group bringup.`
- `Deactivate current scope and activate selected test devices?`

Automatic deactivation on tab switch is not allowed.

## Required Device Closure

**Purpose**

Define which devices count as required for activation.

The required set includes:

- devices explicitly declared by the DSL test
- devices referenced by DSL signals
- support/input devices referenced by expressions
- termination devices such as limit switches

Examples:

- joystick motor test:
  - `SPARKMAX/NEO 25`
  - `controller0`
- limit-terminated motor test:
  - `FALCON 9`
  - `lmtSw0`
- group motor test:
  - every addressed motor
  - any referenced support devices

## Singleton Policy

**Purpose**

Define how singleton devices behave during DSL-specific activation.

- Singleton infrastructure devices may remain instantiated outside the visible selected-test scope.
- Singleton preservation must be policy-driven and deterministic.
- The operator-visible activation result should distinguish:
  - required test devices
  - preserved singleton infrastructure

Examples of preserved singleton infrastructure:

- `roborio`
- `pdp` or equivalent power device
- `controller0`

Examples of test-scoped support devices that are not automatically singleton-preserved unless policy says so:

- `lmtSw0`

Normative `controller0` rule:

- `controller0` is preserved support infrastructure.
- `controller0` is not part of `active-group` membership semantics.
- `controller0` is not removed by `Deactivate Scope`.
- `controller0` may still appear in a DSL test's declared or derived required set for readiness/explanation purposes.
- A joystick or button DSL test must still report `controller0` in required-resource/readiness output.
- However, `controller0` availability is not satisfied by test-specific instantiation churn; it is satisfied by preserved-support policy plus actual controller availability/readiness.
- `Activate Scope` for a selected DSL test must not tear down `controller0` simply because another selected test does not reference it.
- `Run Selected` may still block on `controller0` when the controller is unavailable, disconnected, or otherwise not usable by runtime policy.

## Repeated Runs

**Purpose**

Keep the operator workflow efficient.

- If the selected test has already had its devices activated, the operator may run it repeatedly without re-running activation.
- If the operator selects a different test and the currently instantiated scope still satisfies that test, it may run immediately.
- If the selected test requires devices outside the current instantiated scope, `Run Selected` must block before motion starts and explain which devices are missing.

## UI Behavior

**Purpose**

Define the expected UI behavior in the `Tests` tab and in non-DSL tabs.

`Tests`-tab shared controls:

- `Activate Scope`
- `Deactivate Scope`
- `Open Scope State` or equivalent action to open the read-only scope-state pop-up window

Add selected-test preflight status:

- `Available Devices`
- `Source`
- `Scope Owner`
- `Candidate Devices`
- `Required Devices`
- `Missing Devices`
- `Runnable Now`
- `Current Instantiated Test Scope`

`Run Selected` behavior:

- enabled only when the selected test is ready
- if missing devices exist, robot-side execution returns a blocked result before motion
- UI should display the blocked reason directly
- `Run Selected` must not implicitly perform lifecycle activation or deactivation
- `Run Selected` must block when visible state and robot-confirmed state are inconsistent in a way that could mislead the operator

`Activate Scope` behavior in the `Tests` tab:

- disabled when no selected test exists
- sends the DSL-specific scope-preparation command
- populates the DSL-tab `candidateDevices` view from the selected test
- reconciles runtime `instantiatedDevices` to that candidate set
- does not change `active-group`

`Deactivate Scope` behavior in the `Tests` tab:

- deactivates the selected-test-owned instantiated scope
- clears the selected DSL test and related test-list selections
- leaves the selected test not ready to run
- does not clear `active-group`

Non-DSL tab behavior:

- the active-group subpanel is the primary UI surface for managing `active-group.members`
- the active-group subpanel must be scrollable and usable on laptop-sized screens
- changing active-group membership refreshes the non-DSL `candidateDevices` projection
- changing active-group membership alone must not instantiate or de-instantiate hardware

Scope-state pop-up behavior:

- the first implementation should be a separate pop-up window
- the pop-up window should be read-only
- the pop-up window should show the current shared scope model, not a copied or independently maintained state
- the pop-up window should be concise enough for laptop use

Suggested list presentation:

- `Available Devices`
- `Source`
- `Scope Owner`
- `Candidate Devices`
- `Instantiated Devices`
- `Missing From Instantiated Scope`
- `Preserved Singleton Infrastructure`

List meaning:

- `Available Devices` = selected-profile device pool that the DSL author may use
- `Candidate Devices` = devices declared by the selected DSL file for the selected test
- `Instantiated Devices` = devices currently live in the controlled runtime
- `Missing From Instantiated Scope` = candidate or required-closure devices not currently instantiated

Cross-mode UI behavior:

- entering the `Tests` tab must not deactivate a manual `active-group` scope
- entering the `Live Topology` tab must not deactivate a DSL selected-test scope
- attempting a right-click/manual-duty action from a DSL-owned scope may require an explicit scope transition
- attempting `Run Selected` from a manual-owned scope may require an explicit scope transition

Top-bar context line:

- `Scope Context: active-group`
- `Scope Context: selected test`

## CLI Behavior

**Purpose**

Define the matching CLI surface.

Add a new command:

```text
activate selected-test-devices
```

Add the matching explicit deactivation command:

```text
deactivate selected-test-devices
```

Optional future additive command:

```text
activate test-devices <test-name>
```

Expected CLI result fields:

- selected test name
- required device labels
- preserved singleton labels
- activated device labels
- blocked/error reason when activation cannot be completed

`run test` / selected-test execution behavior:

- uses the current instantiated controlled scope exactly as it exists
- does not auto-activate missing devices
- blocks before motion when required devices are missing

## Status and Reporting

**Purpose**

Make selected-test runnability explicit.

Selected-test status should expose:

- `source`
- `scopeOwner`
- `candidateDevices`
- `requiredDevices`
- `instantiatedDevices`
- `missingDevices`
- `runnableNow`
- `instantiatedScopeMatchesSelectedTest`

This may be published through additive UI/JSON status fields.

## Scope State Window

**Purpose**

Provide one explicit operator-readable scope surface without forcing the user to infer state from multiple tabs.

The first implementation should be a separate pop-up window.

Minimum fields:

- `Profile`
- `Source`
- `Scope Owner`
- `Lifecycle State`
- `Available Devices`
- `Candidate Devices`
- `Instantiated Devices`
- `Missing From Instantiated`

Additional compact fields when available:

- `Preserved Singleton Infrastructure`
- `Last Reconciled From`

Behavior:

- The window is read-only.
- The window must render the same underlying state model used by the main UI.
- The window must not become an independent editor or alternate source of truth.
- The window should be concise enough for laptop use.
- Future additive variants may allow the same content to appear as a shrinkable panel or pop-out from a shared model, but the first implementation is the separate pop-up window.

## Failure Behavior

**Purpose**

Define safe failure outcomes.

- No selected test:
  - activation command fails with a clear selected-test error
- Unknown test on robot:
  - activation command fails with a test-not-found error
- Missing required device definition:
  - activation command fails and reports the missing label
- Robot not in an allowed control mode:
  - activation command fails using the same control-mode gating as controlled-session activation
- `Run Selected` with missing devices:
  - returns blocked before any actuation
- `Run Selected` with ambiguous or inconsistent visible scope state:
  - returns blocked before any actuation
  - response explains which visible state elements were inconsistent
- Cross-mode conflict with insufficient scope:
  - attempted action blocks before motion
  - response explains current scope owner and missing or incompatible devices

## Compatibility

**Purpose**

Protect existing workflows while adding the new one.

- Existing right-click/manual-duty behavior remains bound to `active-group`.
- Existing `lifecycle activate active-group` behavior remains valid.
- Existing selected-test execution remains blocked when scope is insufficient.
- This feature adds a better scope-preparation path; it does not weaken current safety checks.

## Examples

**Purpose**

Show intended operator workflows.

### Example 1: Joystick Test

Selected test:

- `test_minimal_25_9_spark25_leftY`

Required devices:

- `SPARKMAX/NEO 25`
- `controller0`

Workflow:

1. Select the test.
2. Click `Activate Scope` from the `Tests` tab.
3. The system activates the selected-test scope.
4. Run the test repeatedly as needed.

If the operator skips Step 2:

- `Run Selected` blocks before motion
- reports the missing required devices

### Example 2: Switch-Terminated Test

Selected test:

- `falcon9_to_limit`

Required devices:

- `FALCON 9`
- `lmtSw0`

If `lmtSw0` is not instantiated, `Run Selected` must block and explain that `lmtSw0` is missing.

### Example 3: Switching Tests

Current instantiated test scope:

- `SPARKMAX/NEO 25`
- `controller0`

New selected test requires:

- `FALCON 9`
- `lmtSw0`

Behavior:

- `Run Selected` blocks before motion
- `Activate Scope` re-prepares the scope for the new test

### Example 3A: Shared List Interpretation

Tests tab state:

- `availableDevices`:
  - `SPARKMAX/NEO 25`
  - `FALCON 9`
  - `controller0`
  - `lmtSw0`
- `candidateDevices`:
  - `FALCON 9`
  - `lmtSw0`
- `instantiatedDevices` before activation:
  - `SPARKMAX/NEO 25`
  - `controller0`

Behavior:

- `availableDevices` is the broader profile device pool and does not imply use by the selected test
- `Run Selected` blocks because `instantiatedDevices` does not satisfy `candidateDevices`
- `Activate Scope` reconciles runtime state to the test candidate set
- after activation, non-singleton prior devices not in the test candidate set are removed

### Example 4: Switching Tabs Without Reconfiguration

Current scope owner:

- `selected-test:test_minimal_25_9_spark25_leftY`

Operator action:

- click `Live Topology`

Behavior:

- no devices are deactivated
- no scope is reconfigured
- the visible candidate list may repopulate because the UI moved into or out of the `Tests` tab
- right-click/manual action later may require explicit transition back to `manual-active-group`

### Example 5: Returning to Manual Bringup

Current scope owner:

- `selected-test:test_minimal_25_9_spark25_leftY`

Operator action:

- right-click a motor for manual-duty control

Behavior:

- system checks whether current scope is valid for manual workflow
- if not, block before motion
- offer explicit transition back to `manual-active-group`

### Example 6: Extra Devices Present Before DSL Activation

Current manual scope contains:

- `FALCON 9`
- `SPARKMAX/NEO 25`

Selected DSL test requires:

- `SPARKMAX/NEO 25`
- `controller0`

After `Activate Scope`:

- `FALCON 9` is removed from the DSL controlled scope because it is not required and is not a preserved singleton
- `SPARKMAX/NEO 25` remains
- `controller0` remains available according to preserved-support singleton policy
- singleton infrastructure remains according to policy

### Example 7: Manual Candidate Refresh Outside Tests

Current non-DSL surface:

- `Live Topology`

Current `active-group.members`:

- `FALCON 9`
- `SPARKMAX/NEO 25`

Operator action:

- add `controller0` in the active-group subpanel only if manual workflow explicitly wants it listed there

Behavior:

- non-DSL `candidateDevices` refreshes from `active-group.members`
- no hardware state changes yet
- explicit lifecycle activation is still required to reconcile runtime state

## Acceptance Criteria

**Purpose**

Provide concrete completion conditions.

- The user can activate devices for the currently selected DSL test without editing `active-group`.
- Right-click/manual-duty workflows continue to use `active-group` unchanged.
- Switching tabs alone never deactivates devices or reconfigures scope.
- `Run Selected` never auto-reconfigures scope.
- `Run Selected` blocks when visible scope state is ambiguous or inconsistent.
- Re-running the same selected test does not require reactivation.
- Running a different test with a compatible current scope succeeds without reactivation.
- Running a different test with an incompatible scope blocks before motion and reports missing devices.
- Preserved support infrastructure such as `controller0` remains available across scope changes according to singleton policy.
- Test-scoped support devices such as `lmtSw0` can be instantiated through the selected-test activation path.
- Non-singleton devices not required by the selected DSL test are removed when `Activate Scope` runs from the `Tests` tab.
- Cross-mode manual-vs-DSL conflicts are resolved only through explicit scope transition, never by silent tab-switch side effects.
- A read-only scope-state pop-up window shows `Source`, `Scope Owner`, `Candidate Devices`, and `Instantiated Devices` from the shared model.

## Implementation Readiness

**Purpose**

State what is now sufficiently specified to begin implementation and what constraints must hold during implementation.

This spec is intended to be implementation-ready for the `Scope State And Lifecycle Reconciliation` feature.

Implementation should proceed in this order:

1. Define the shared `Scope State` model in code.
2. Define the source-selection and candidate-construction paths for:
   - `selected-test`
   - `active-group`
3. Define required-scope derivation and lifecycle reconciliation against the shared model.
4. Define consistency evaluation and `Run Selected` blocking against the shared model.
5. Render the read-only scope-state pop-up window directly from the shared model.

Implementation must not:

- start from the pop-up window and invent a separate state cache
- hard-code DSL-specific assumptions into the base `Scope State` contract
- hard-code `active-group` assumptions into the base lifecycle reconciliation contract
- add future discovery/debug concerns into this feature unless they are strictly consumed through the existing `Scope State` boundaries

## Tradeoffs

**Purpose**

Record the main design tradeoffs.

- This adds another activation entry point, but it is easier to reason about than overloading `active-group`.
- The robot must compute required device closure from DSL tests reliably.
- Singleton policy must be explicit so operators understand what is preserved versus test-owned.
- Explicit scope-transition prompts add UX work, but they are safer and less confusing than hidden deactivation on tab changes.
- A separate pop-up window is easier to deliver first, but it consumes more screen space than an inline panel on laptops.

## Future Extensions

**Purpose**

List additive follow-on ideas.

- scope-state window as shrinkable panel or pop-out from the same shared model
- `Activate Scope` preview dialog before reconfiguring scope
- `Activate And Run` convenience action after the base workflow is stable
- persistent recent selected-test scopes for repeated bench sessions
- richer per-test UI badges for `Runnable`, `Blocked`, and `Missing Devices`
