SPEC_STATUS: PROPOSED

# DSL Selected-Test Device Activation

**Purpose**

Define a DSL-specific device activation workflow that prepares the exact instantiated scope required by the selected DSL test without changing the existing `active-group` workflow used for right-click and manual-duty testing.

## Goal

**Purpose**

Make selected-test DSL execution understandable and repeatable.

- A selected DSL test should declare the devices it needs.
- The operator should be able to activate exactly those devices before running the test.
- Re-running the same test should not require repeating activation.
- Trying a different test should fail before motion starts if the current instantiated scope is insufficient.
- The existing `active-group` workflow for right-click/manual tests must remain independent.

## Non-Goals

**Purpose**

Clarify what this feature does not change.

- Do not replace `active-group` for topology-driven manual tests.
- Do not auto-run a test as part of activation.
- Do not silently merge unrelated devices into the current controlled session.
- Do not require the operator to edit `active-group` for DSL tests.
- Do not change the passive CAN tool or NetworkTables contracts outside additive test-status fields.

## Problem Statement

**Purpose**

Capture the current operator confusion.

- The DSL/test engine already knows when a test is blocked because a required device is not instantiated.
- The operator surfaces do not make the required scope obvious before `Run Selected`.
- `active-group` is currently motor-centric and is not a good operator model for support devices such as `controller0` or `lmtSw0`.
- The same selected test can be known to the robot while the UI still looks like no usable test scope has been prepared.

## Core Contract

**Purpose**

Define the new operator-facing behavior.

- A selected DSL test has a derived `requiredDevices` set.
- A DSL test is runnable only when every required device is instantiated in the current controlled session.
- The system adds a DSL-specific scope-preparation action:
  - CLI: `activate selected-test-devices`
  - UI: `Activate Test Devices`
- This action prepares the controlled session for the currently selected DSL test.
- `Run Selected` uses the current instantiated controlled scope as-is.
- `Run Selected` must never auto-reconfigure scope.
- `Run Selected` must fail before motion starts when required devices are missing.

## Conservative Execution Rule

**Purpose**

Make selected-test execution deterministic and non-surprising.

- Entering the `Tests` tab must not change hardware state.
- Selecting a different DSL test must not change hardware state.
- `Activate Test Devices` is the only DSL-tab action that may reconfigure the controlled scope.
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

## Scope Ownership

**Purpose**

Define how the system distinguishes manual and DSL-controlled scopes.

- The controlled session must expose a logical `scopeOwner`.
- Valid initial owners for this feature are:
  - `manual-active-group`
  - `selected-test:<test-name>`
- The owner describes why the current controlled scope was activated.
- Scope ownership is runtime state, not UI-tab state.

## Tab Switching Rule

**Purpose**

Prevent destructive behavior during normal UI navigation.

- Switching between `Live Topology` and `Tests` must not deactivate devices.
- Simply viewing another tab must not reconfigure scope.
- Tab switching is presentation-only and must not change hardware state.

## Activation Semantics

**Purpose**

Define what `activate selected-test-devices` actually does.

When invoked for the currently selected test:

1. Resolve the selected DSL test.
2. Compute the required device closure for that test.
3. Deactivate the current controlled session if one is active.
4. Preserve singleton infrastructure according to singleton policy.
5. Deinstantiate non-singleton devices that are not required by the selected test.
6. Instantiate exactly the required test devices.
7. Activate the resulting controlled session.
8. Report the final activated device set.

The action must not start the test.

For this DSL-specific activation path:

- non-singleton devices not required by the selected test must be removed from the controlled scope
- singleton infrastructure may remain according to singleton policy
- no `active-group` mutation is allowed

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

Examples of likely singleton infrastructure:

- `roborio`
- `pdp` or equivalent power device

Examples of test-scoped support devices that are not automatically singleton-preserved unless policy says so:

- `controller0`
- `lmtSw0`

## Repeated Runs

**Purpose**

Keep the operator workflow efficient.

- If the selected test has already had its devices activated, the operator may run it repeatedly without re-running activation.
- If the operator selects a different test and the currently instantiated scope still satisfies that test, it may run immediately.
- If the selected test requires devices outside the current instantiated scope, `Run Selected` must block before motion starts and explain which devices are missing.

## UI Behavior

**Purpose**

Define the expected UI behavior in the Tests tab.

Add a new button near `Run Selected`:

- `Activate Test Devices`

Add selected-test preflight status:

- `Required Devices`
- `Missing Devices`
- `Runnable Now`
- `Current Instantiated Test Scope`

`Run Selected` behavior:

- enabled when the selected test exists
- if missing devices exist, robot-side execution returns a blocked result before motion
- UI should display the blocked reason directly
- `Run Selected` must not implicitly perform `Activate Test Devices`

`Activate Test Devices` behavior:

- disabled when no selected test exists
- sends the DSL-specific scope-preparation command
- does not change `active-group`

Cross-mode UI behavior:

- entering the `Tests` tab must not deactivate a manual `active-group` scope
- entering the `Live Topology` tab must not deactivate a DSL selected-test scope
- attempting a right-click/manual-duty action from a DSL-owned scope may require an explicit scope transition
- attempting `Run Selected` from a manual-owned scope may require an explicit scope transition

Suggested UI status line:

- `Current scope owner: manual active-group`
- `Current scope owner: selected test <name>`

## CLI Behavior

**Purpose**

Define the matching CLI surface.

Add a new command:

```text
activate selected-test-devices
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

- `requiredDevices`
- `missingDevices`
- `runnableNow`
- `instantiatedScopeMatchesSelectedTest`

This may be published through additive UI/JSON status fields.

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
2. Click `Activate Test Devices`.
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
- `Activate Test Devices` re-prepares the scope for the new test

### Example 4: Switching Tabs Without Reconfiguration

Current scope owner:

- `selected-test:test_minimal_25_9_spark25_leftY`

Operator action:

- click `Live Topology`

Behavior:

- no devices are deactivated
- no scope is reconfigured
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

After `Activate Test Devices`:

- `FALCON 9` is removed from the DSL controlled scope because it is not required and is not a preserved singleton
- `SPARKMAX/NEO 25` remains
- `controller0` is instantiated
- singleton infrastructure remains according to policy

## Acceptance Criteria

**Purpose**

Provide concrete completion conditions.

- The user can activate devices for the currently selected DSL test without editing `active-group`.
- Right-click/manual-duty workflows continue to use `active-group` unchanged.
- Switching tabs alone never deactivates devices or reconfigures scope.
- `Run Selected` never auto-reconfigures scope.
- Re-running the same selected test does not require reactivation.
- Running a different test with a compatible current scope succeeds without reactivation.
- Running a different test with an incompatible scope blocks before motion and reports missing devices.
- Support devices such as `controller0` and `lmtSw0` can be instantiated through the selected-test activation path.
- Non-singleton devices not required by the selected DSL test are removed when `Activate Test Devices` runs.
- Cross-mode manual-vs-DSL conflicts are resolved only through explicit scope transition, never by silent tab-switch side effects.

## Tradeoffs

**Purpose**

Record the main design tradeoffs.

- This adds another activation entry point, but it is easier to reason about than overloading `active-group`.
- The robot must compute required device closure from DSL tests reliably.
- Singleton policy must be explicit so operators understand what is preserved versus test-owned.
- Explicit scope-transition prompts add UX work, but they are safer and less confusing than hidden deactivation on tab changes.

## Future Extensions

**Purpose**

List additive follow-on ideas.

- `Activate Test Devices` preview dialog before reconfiguring scope
- `Activate And Run` convenience action after the base workflow is stable
- persistent recent selected-test scopes for repeated bench sessions
- richer per-test UI badges for `Runnable`, `Blocked`, and `Missing Devices`
