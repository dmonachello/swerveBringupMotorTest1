# DSL Selected-Test Scope Activation Test Procedure

**Purpose**

Provide a detailed validation procedure for the selected-test scope activation feature described in [FEATURE_SPEC_DSL_SELECTED_TEST_DEVICE_ACTIVATION.md](/abs/path/c:/Users/dmona/swerveBringupMotorTest1-main/docs/FEATURE_SPEC_DSL_SELECTED_TEST_DEVICE_ACTIVATION.md).

This procedure verifies that:

- manual/right-click bringup still uses `active-group`
- DSL-selected tests use explicit selected-test scope activation
- `Activate Scope` and `Deactivate Scope` dispatch by tab context
- selected test readiness is shown correctly
- `Run Selected` stays conservative and never auto-reconfigures
- singleton policy for `controller0` is coherent
- leaving DSL scope and returning to manual scope works cleanly

**Scope**

This procedure is for the first implementation slice that added:

- robot commands:
  - `activateSelectedTestDevices`
  - `deactivateSelectedTestDevices`
- shared UI top-bar buttons:
  - `Activate Scope`
  - `Deactivate Scope`
- top-bar context label:
  - `Scope Context: active-group`
  - `Scope Context: selected test`

This procedure assumes the current selected profile includes at least:

- `FALCON 9`
- `SPARKMAX/NEO 25`
- `controller0`
- `lmtSw0`

## What This Procedure Verifies

**Purpose**

List the exact behaviors under test.

- manual `active-group` activation still works
- right-click/manual duty still works after reactivating manual scope
- Tests-tab `Activate Scope` uses selected-test required devices
- Tests-tab `Deactivate Scope` clears selected test readiness and selection UI
- `Run Selected` is disabled when selected test is not ready
- DSL scope activation removes non-required non-singleton devices
- `controller0` is treated as preserved support infrastructure, not test-churn hardware
- selected-test and manual scope ownership do not silently overwrite each other

## What This Procedure Does Not Verify

**Purpose**

Keep this test focused on the implemented slice.

- final scope-state popup window content
- grammar/manual updates for text CLI parsing of `activate selected-test-devices`
- every DSL test variant in the repo
- multi-operator/session ownership races
- no-battery behavior

## Preconditions

**Purpose**

Ensure one consistent starting point.

- repo is up to date with the selected-test scope activation implementation
- robot is reachable at the expected IP
- Driver Station is available
- Bringup UI launches successfully
- the selected profile is present on both host and robot
- at least one right-click/manual motor test already works with `active-group`
- at least one DSL motor test exists that requires only a motor
- at least one DSL joystick/input test exists that requires `controller0`
- robot can be placed in enabled teleop when scope activation is attempted

Recommended profile during this procedure:

- `test_minimal_25_9`

Recommended DSL tests:

- motor-only test:
  - `falcon9_move_150_rotations`
  - or equivalent direct motor motion test
- joystick/input-driven test:
  - `test_minimal_25_9_spark25_leftY`
  - or equivalent test that references `controller0`

## Required Programs

**Purpose**

Make the operator surfaces explicit.

You will use both:

1. Bringup UI

```powershell
python tools\can_nt\can_nt_bridge.py --ui --rio 172.22.11.2
```

2. Bridge CLI

```powershell
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
```

## Evidence To Capture

**Purpose**

Keep the test run diagnosable after the fact.

For each major step, capture:

- screenshot of the active UI tab
- relevant `ACK` / `OUT` lines
- `show lifecycle-state`
- `show runtime-state --json --pretty`

For failures, also record:

- selected profile
- selected test
- current tab
- top-bar scope context label
- whether robot was enabled teleop

## Phase 1: Baseline Manual Scope

**Purpose**

Verify the pre-existing manual workflow still behaves correctly.

### Step 1.1: Start Clean

1. Launch the Bringup UI.
2. Confirm the robot is connected.
3. Select the intended profile.
4. Open the `Live Topology` tab.

Expected result:

- top bar shows `Scope Context: active-group`
- `Activate Scope` and `Deactivate Scope` are visible
- no DSL-specific readiness message is required in this tab

### Step 1.2: Deactivate Any Existing Scope

1. Click `Deactivate Scope`.
2. In CLI, run:

```text
show lifecycle-state
show runtime-state --json --pretty
```

Expected result:

- UI output includes `scope deactivated`
- lifecycle state is inactive
- non-singleton controlled devices are no longer active
- singleton infrastructure may remain available
- `active-group` checkboxes remain selected exactly as before

### Step 1.3: Activate Manual Scope

1. Stay in `Live Topology`.
2. Confirm desired `active-group` members are checked.
3. Click `Activate Scope`.
4. In CLI, run:

```text
show lifecycle-state
show runtime-state --json --pretty
```

Expected result:

- UI output includes `selected active-group scope active - ready to run`
- `show lifecycle-state` reports `state=ACTIVE`
- requested label is `active-group`
- runtime devices in the checked `active-group` are `controlled-active`
- unrelated non-singleton devices are not active

### Step 1.4: Verify Manual Motor Actuation

1. Right-click a motor that is in `active-group`.
2. Apply a small safe duty.
3. Confirm motor response.

Expected result:

- the right-click/manual path still works
- no unexpected DSL-related blocking occurs
- runtime readback shows command/applied movement for the targeted device

Pass criteria:

- manual workflow behaves the same as before except for updated top-bar wording

## Phase 2: DSL Scope Activation From Tests Tab

**Purpose**

Verify that selected-test activation uses selected-test requirements rather than `active-group`.

### Step 2.1: Switch To Tests Context

1. Open the `Tests` tab.

Expected result:

- top bar now shows `Scope Context: selected test`
- the shared `Activate Scope` button now applies to the selected test, not `active-group`
- no hardware state changes occur from switching tabs

### Step 2.2: Select A Motor-Only DSL Test

1. Select a motor-only test in the selected-test dropdown.
2. Do not press `Activate Scope` yet.

Expected result:

- selected test remains selected
- readiness line shows:
  - `selected test inactive - <specific reason>`
- `Run Selected` is disabled
- no hardware state changes occur

### Step 2.3: Attempt To Run Without Scope Activation

1. Confirm `Run Selected` is disabled.
2. If there is any alternate path to send `runTest`, use CLI:

```text
runTest
```

Expected result:

- UI path does not allow execution
- robot-side path blocks before motion if directly invoked
- no auto-activation occurs

### Step 2.4: Activate Selected-Test Scope

1. Keep the same test selected.
2. Click `Activate Scope`.
3. In CLI, run:

```text
show lifecycle-state
show runtime-state --json --pretty
```

Expected result:

- UI output includes `selected test scope active - ready to run`
- lifecycle state becomes active
- runtime owner/label corresponds to selected-test scope
- required non-singleton device set for the test is active
- non-required non-singleton devices from prior manual scope are removed
- `active-group` checkbox state is unchanged in the UI model

### Step 2.5: Run The Motor-Only Test

1. Click `Run Selected`.

Expected result:

- test starts and completes successfully
- motor motion occurs only if expected by the selected test
- no missing-device block occurs for the required motor

Pass criteria:

- the test runs without needing to edit `active-group`

## Phase 3: Repeated DSL Runs

**Purpose**

Verify no unnecessary reactivation is required.

### Step 3.1: Re-Run The Same Test

1. Without changing tabs or selection, click `Run Selected` again.

Expected result:

- test runs again
- no reactivation is required
- no scope rebuild occurs

### Step 3.2: Select Another Compatible DSL Test

1. Select a second test that uses the same required devices.

Expected result:

- if current instantiated scope already satisfies it, readiness may become ready without reactivation
- otherwise it remains inactive and requires explicit activation
- in either case, no hardware state changes occur on selection alone

## Phase 4: Controller0 Behavior

**Purpose**

Verify the Xbox controller singleton/support policy is coherent.

### Step 4.1: Select A Controller-Driven Test

1. In the `Tests` tab, select a test that references `controller0`.
2. Observe the readiness message before activation.

Expected result:

- the test may report inactive/not ready before activation
- the reason text should mention the missing resource or readiness reason when appropriate

### Step 4.2: Activate Scope For The Controller-Driven Test

1. Click `Activate Scope`.
2. In CLI, run:

```text
show lifecycle-state
show runtime-state --json --pretty
```

Expected result:

- UI output includes `selected test scope active - ready to run`
- the required motor device becomes active
- `controller0` remains available according to preserved-support policy
- `controller0` is not being treated like a normal churned motor device

### Step 4.3: Run The Controller-Driven Test

1. Move the Xbox control as required by the test.
2. Click `Run Selected` if that test requires explicit start.

Expected result:

- if the controller is truly available and mapped, the test runs
- the failure mode, if any, should now be a real controller-availability problem, not stale instantiation churn

Pass criteria:

- controller-driven tests are not blocked merely because `controller0` was torn down as a normal scope device

## Phase 5: DSL Deactivation Semantics

**Purpose**

Verify `Deactivate Scope` in the `Tests` tab does the DSL-specific cleanup.

### Step 5.1: Deactivate From Tests

1. Stay in the `Tests` tab with a selected-test scope active.
2. Click `Deactivate Scope`.

Expected result:

- UI output includes `scope deactivated`
- selected test dropdown is cleared to `(none)`
- test-list selections are cleared
- readiness returns to inactive / no selected test
- `Run Selected` is disabled
- `active-group` checkbox state remains preserved for manual use later

### Step 5.2: Verify Runtime After DSL Deactivation

1. In CLI, run:

```text
show lifecycle-state
show runtime-state --json --pretty
```

Expected result:

- no selected-test-owned non-singleton scope remains active
- singleton infrastructure may still remain available

Pass criteria:

- DSL deactivation clears test readiness but does not destroy manual selection state

## Phase 6: Return To Manual Bringup

**Purpose**

Verify the operator can move back to right-click/manual work cleanly.

### Step 6.1: Switch Back To Live Topology

1. Open `Live Topology`.

Expected result:

- top bar shows `Scope Context: active-group`
- previously selected `active-group` checkboxes are still checked
- switching tabs alone does not instantiate anything

### Step 6.2: Reactivate Manual Scope

1. Click `Activate Scope`.
2. In CLI, run:

```text
show lifecycle-state
show runtime-state --json --pretty
```

Expected result:

- UI output includes `selected active-group scope active - ready to run`
- runtime returns to the manual `active-group` scope
- selected-test DSL scope no longer owns runtime

### Step 6.3: Re-Verify Right-Click Manual Test

1. Right-click one active-group motor again.
2. Apply a safe command.

Expected result:

- right-click/manual test still works
- no stale DSL ownership conflict remains

Pass criteria:

- the exact manual workflow can be resumed after DSL use

## Phase 7: Negative And Failure Cases

**Purpose**

Exercise the intended blocked/failed paths.

### Step 7.1: Empty Manual Selection

1. Clear all `active-group` selections.
2. Stay in manual/topology context.
3. Click `Activate Scope`.

Expected result:

- activation fails
- message clearly indicates empty/invalid manual scope
- no unexpected activation occurs

### Step 7.2: No Selected Test

1. Go to `Tests`.
2. Ensure no test is selected.

Expected result:

- `Activate Scope` is disabled
- `Run Selected` is disabled
- status indicates no selected test

### Step 7.3: Partial DSL Failure

1. Choose a test whose required non-singleton device cannot instantiate, if safely reproducible.
2. Click `Activate Scope`.

Expected result:

- activation fails
- message includes:
  - `scope activation failed - partial activation remains`
  - or the lower-level lifecycle failure text
- DSL `Run Selected` remains blocked

### Step 7.4: Manual Partial Scope Tolerance

1. Create a manual selection where one device can activate and another cannot, if safely reproducible.
2. Activate manual scope.

Expected result:

- manual activation may leave partial activation
- checkbox selections remain
- right-click/manual action may still work on the valid active member(s)
- state should be visible elsewhere in the UI/readback

## Phase 8: CLI Spot Checks

**Purpose**

Verify explicit robot command paths in addition to the UI.

Use CLI or REST-backed command surfaces that can send the following commands directly.

### Step 8.1: Activate Selected-Test Devices

With a test selected on the robot:

```text
activateSelectedTestDevices
show lifecycle-state
```

Expected result:

- activation succeeds
- lifecycle owner/label changes to selected-test scope

### Step 8.2: Deactivate Selected-Test Devices

With selected-test scope active:

```text
deactivateSelectedTestDevices
show lifecycle-state
```

Expected result:

- deactivation succeeds
- no selected-test scope remains active

### Step 8.3: Wrong Scope Owner Failure

1. Activate manual `active-group`.
2. Then invoke:

```text
deactivateSelectedTestDevices
```

Expected result:

- command fails
- message is equivalent to:
  - `wrong scope owner - active-group is active`

## Final Pass Criteria

**Purpose**

Define when this feature is acceptable for this implementation slice.

All of the following must be true:

- a selected DSL test can be made ready using `Activate Scope`
- `Run Selected` succeeds for at least one motor-only DSL test
- a controller-driven test does not fail because `controller0` was incorrectly churned as a normal scope device
- `Deactivate Scope` from `Tests` clears test readiness and selection state
- `active-group` checkboxes survive DSL activation/deactivation unchanged
- returning to `Live Topology` and reactivating manual scope restores right-click/manual bringup
- right-click manual test still works after DSL scope use

## Record Sheet

**Purpose**

Make manual runs easy to archive.

Record for each run:

- Date:
- Operator:
- Robot IP:
- Selected profile:
- Manual test used:
- DSL motor-only test used:
- DSL controller-driven test used:
- Build/revision:
- Result:
  - PASS
  - FAIL
- Notes:
