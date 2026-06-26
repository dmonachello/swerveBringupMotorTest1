# DSL Selected-Test Active Group V2 Test Procedure

**Purpose**

Provide a complete connected-system validation procedure for the V2 group-only behavior defined in [FEATURE_SPEC_DSL_SELECTED_TEST_DEVICE_ACTIVATION_V2.md](FEATURE_SPEC_DSL_SELECTED_TEST_DEVICE_ACTIVATION_V2.md).

This procedure verifies the current intended contract:

- the user only deals with groups, not scope
- `active-group` is the one dynamic group
- the `Tests` tab temporarily owns `active-group` from the selected DSL test
- non-Tests tabs restore and manage the remembered manual `active-group`
- crossing the `Tests` / non-Tests boundary always deactivates the active group
- `Activate Group` and `Deactivate Group` are the top shared controls
- the `Active Group` panel is read-only in `Tests`
- required singleton/support devices are shown as locked rows
- `Run Selected` stays blocked until the loaded test-driven group is activated

## Status

**Purpose**

Describe how this procedure should be used.

- Use this as the authoritative validation procedure for V2 behavior.
- Do not use the older scope-based procedure as the final acceptance procedure for V2.
- This plan is written to expose:
  - implementation bugs
  - operator confusion points
  - remaining mismatches between the V2 spec and live behavior

## References

**Purpose**

List the documents this procedure validates against.

- [FEATURE_SPEC_DSL_SELECTED_TEST_DEVICE_ACTIVATION_V2.md](FEATURE_SPEC_DSL_SELECTED_TEST_DEVICE_ACTIVATION_V2.md)
- [TEST_PROCEDURE_ZERO_CONFIG.md](TEST_PROCEDURE_ZERO_CONFIG.md) when helpful for base bringup expectations
- [TEST_PROCEDURE_CONTROLLED_LIFECYCLE_NO_BATTERY.md](TEST_PROCEDURE_CONTROLLED_LIFECYCLE_NO_BATTERY.md) when lifecycle behavior needs comparison

## What This Procedure Verifies

**Purpose**

Define the exact behavior under test.

- top-bar buttons use group language
- `active-group` is the only operator-facing dynamic group
- selecting a DSL test loads `active-group` from that test
- library selection is the one authoritative current-test selection in the `Tests` tab
- the source editor follows that same current-test selection
- `Current Test` display matches the selected library row
- the `Active Group` panel in `Tests` shows test-owned members, locked support rows, and inactive/active state clearly
- manual `active-group` membership is remembered when entering `Tests`
- leaving `Tests` restores remembered manual membership and leaves it inactive
- boundary crossing always deactivates the active group
- within `Tests`, switching to a non-matching test deactivates and reloads but does not activate
- within `Tests`, switching to a matching test does not force unnecessary teardown
- `Activate Group` activates exactly the displayed test-driven `active-group` plus required singleton/support devices
- `Deactivate Group` tears down active non-singleton group members and gives a harmless reminder if already inactive
- `Run Selected` is blocked before activation and enabled only when the loaded test-driven group is active and valid
- last result and test activity surfaces reflect pass/fail/running status
- `printState`, `showLifecycleState`, and other test-surface outputs appear in the visible UI logs

## What This Procedure Does Not Verify

**Purpose**

Keep the pass/fail boundary clear.

- electrical correctness of every device on every robot
- all DSL scripts in the repository
- no-battery behavior
- multi-operator ownership races
- performance beyond practical observation of obvious loop overruns
- every non-Tests report surface unrelated to DSL or `active-group`

## Preconditions

**Purpose**

Create one consistent starting point.

- repo deployed with the current V2 implementation
- host UI restarted after the latest host-side changes
- robot reachable at the expected IP
- Driver Station available
- robot can be enabled in teleop when required
- selected profile exists on host and robot
- the selected profile includes at least:
  - `FALCON 9`
  - `SPARKMAX/NEO 25`
  - `controller0`
  - `lmtSw0`
  - `roborio`
  - `pdp`

Recommended profile:

- `test_minimal_25_9`

Recommended tests:

- motor-only:
  - `falcon9_move_150_rotations`
- limit-switch:
  - `falcon9_to_limit`
- controller-driven:
  - `test_minimal_25_9_spark25_leftY`
- multi-device:
  - `mtrs_limit`

## Required Tools

**Purpose**

Make the operator surfaces explicit.

Use:

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

Keep failures diagnosable.

For each phase, capture:

- a screenshot of the active tab
- relevant `CMD`, `ACK`, and `OUT` lines
- `showLifecycleState`
- `showRuntimeState`

For failures, also record:

- selected profile
- current tab
- current test name
- visible `Active Group Source` label
- whether the robot was enabled or disabled
- whether the issue reproduced after UI restart

## Phase 1: Baseline Manual Group

**Purpose**

Confirm the non-Tests manual workflow still behaves predictably.

### Step 1.1: Start Clean

1. Launch the UI.
2. Confirm connection.
3. Select the intended profile.
4. Open `Live Topology`.

Expected result:

- top bar uses `Activate Group` / `Deactivate Group`
- top bar shows manual ownership text, for example `Active Group Source: manual`
- no test-owned status appears in the main workflow

### Step 1.2: Deactivate Any Existing Group

1. Click `Deactivate Group`.
2. Run:

```text
showLifecycleState
showRuntimeState
```

Expected result:

- harmless success even if already inactive
- no active non-singleton group members remain instantiated
- manual checkbox state remains selected exactly as before

### Step 1.3: Activate Manual Group

1. In a non-Tests tab, choose a simple manual `active-group`.
2. Click `Activate Group`.
3. Run:

```text
showLifecycleState
showRuntimeState
```

Expected result:

- requested label is `active-group`
- selected manual members are instantiated
- unrelated non-singleton devices are not instantiated

### Step 1.4: Verify Manual Actuation

1. Use a safe right-click/manual action on an active member.

Expected result:

- manual/right-click still works

Pass criteria:

- manual behavior remains intact before testing DSL behavior

## Phase 2: Enter Tests And Load Test-Owned Active Group

**Purpose**

Verify that `Tests` takes over the displayed `active-group` model.

### Step 2.1: Cross Into Tests

1. Switch from a non-Tests tab into `Tests`.

Expected result:

- current active group is deactivated
- old manual displayed group is cleared from the current visible context
- remembered manual membership is preserved internally for later restoration
- no automatic activation occurs

### Step 2.2: Select A Profile Test

1. Click a test in `Profile Tests`.

Expected result:

- `Current Test` label updates to that test
- source editor loads that same test
- `Active Group` panel loads the devices declared by that test
- those rows are shown as not instantiated until activation
- `Run Selected` remains disabled

### Step 2.3: Verify Single Selection Model

1. Click a different test in `Global Library`.
2. Then click a different test in `Config Library`.
3. Then click a different test in `Profile Tests`.

Expected result each time:

- the clicked row becomes the one authoritative current test
- `Current Test` updates
- source editor updates to the same test
- `Active Group` panel updates to the same test
- there is no second independent selected-test control to keep in sync manually

Pass criteria:

- the user never has to track two different current tests

## Phase 3: Test-Owned Active Group Contents

**Purpose**

Verify the displayed group contents are correct before activation.

### Step 3.1: Motor-Only Test

1. Select `falcon9_move_150_rotations`.

Expected result:

- `Active Group` shows `FALCON 9`
- it is marked enabled and not instantiated
- no unrelated devices are shown

### Step 3.2: Limit-Switch Test

1. Select `falcon9_to_limit`.

Expected result:

- `Active Group` shows:
  - `FALCON 9`
  - `lmtSw0`
- `lmtSw0` is shown as locked if treated as a support row in the current implementation
- neither row is instantiated yet

### Step 3.3: Controller-Driven Test

1. Select `test_minimal_25_9_spark25_leftY`.

Expected result:

- `Active Group` shows:
  - `SPARKMAX/NEO 25`
  - `controller0`
- `controller0` is shown as locked
- rows are loaded but not instantiated

### Step 3.4: Invalid Device Reporting

1. If safely reproducible, create or select a test with a device not valid for the current profile.

Expected result:

- invalid device is reported in Validate Status
- invalid device is visibly indicated in the `Active Group` panel
- activation remains blocked

Pass criteria:

- the displayed test-driven `active-group` matches the selected test declaration

## Phase 4: Activation And Run Gating

**Purpose**

Verify `Activate Group` and `Run Selected` behavior in `Tests`.

### Step 4.1: Pre-Activation Gating

1. Select a test.
2. Do not click `Activate Group`.

Expected result:

- status text indicates loaded but not activated
- `Run Selected` is disabled

### Step 4.2: Activate A Motor-Only Test

1. Select `falcon9_move_150_rotations`.
2. Click `Activate Group`.
3. Run:

```text
showLifecycleState
showRuntimeState
```

Expected result:

- `active-group` becomes active
- `FALCON 9` is instantiated
- required singleton/support devices follow policy
- `Run Selected` becomes enabled

### Step 4.3: Run A Motor-Only Test

1. Click `Run Selected`.

Expected result:

- test starts and runs
- `Running` and `Last Result` update in the `Tests` header
- activity output shows command/result lines

### Step 4.4: Activate A Limit-Switch Test

1. Select `falcon9_to_limit`.
2. Click `Activate Group`.
3. Run:

```text
showLifecycleState
showRuntimeState
```

Expected result:

- `FALCON 9` and `lmtSw0` are both in the test-driven group model
- if the implementation is correct, both required non-singleton members are activated or the UI clearly shows why not
- `Run Selected` enables only when readiness is genuinely satisfied

### Step 4.5: Run A Limit-Switch Test

1. Click `Run Selected`.

Expected result:

- if the switch is reachable and functioning, the test may pass on switch press
- `Last Result` shows PASS or FAIL in the Tests header
- result lines appear in `Test Activity`

### Step 4.6: Activate A Controller-Driven Test

1. Select `test_minimal_25_9_spark25_leftY`.
2. Click `Activate Group`.

Expected result:

- motor row activates
- `controller0` is not treated as a random missing profile device
- `Run Selected` enables only when the test is truly runnable

Pass criteria:

- no auto-run occurs
- no auto-activation occurs
- `Run Selected` is enabled only after valid activation

## Phase 5: Within-Tests Switching Rules

**Purpose**

Verify switching tests inside `Tests` obeys the V2 contract.

### Step 5.1: Switch To A Non-Matching Test While Active

1. Activate one test-driven group.
2. While remaining in `Tests`, select a different test with different membership.

Expected result:

- current active group is deactivated
- displayed `active-group` rows are repopulated for the new test
- group remains inactive
- `Run Selected` becomes disabled again until activation

### Step 5.2: Switch To A Matching Test

1. From an already loaded test, select another test with identical required membership, if available.

Expected result:

- no unnecessary rebuild is required
- no unnecessary hardware churn occurs

Pass criteria:

- non-matching changes force reload and inactivity
- matching changes do not force needless churn

## Phase 6: Deactivate Group In Tests

**Purpose**

Verify deactivation semantics while remaining in `Tests`.

### Step 6.1: Deactivate An Active Test-Driven Group

1. With a test-driven group active, click `Deactivate Group`.

Expected result:

- group deactivates
- current test may remain displayed
- loaded test-driven rows remain visible unless changed by later selection or tab boundary behavior
- `Run Selected` becomes disabled

### Step 6.2: Deactivate Again While Already Inactive

1. Click `Deactivate Group` again.

Expected result:

- harmless reminder that nothing changed
- no error dialog

Pass criteria:

- inactive deactivation is safe and explicit

## Phase 7: Return To Non-Tests

**Purpose**

Verify remembered manual membership restoration.

### Step 7.1: Leave Tests

1. Switch from `Tests` to `Live Topology`.

Expected result:

- active test-driven group is deactivated
- remembered manual `active-group` membership is restored in the panel
- restored group is inactive

### Step 7.2: Verify Restored Manual Group

1. Inspect the `Active Group` panel in the non-Tests tab.

Expected result:

- the same manual members from before entering `Tests` are back
- they are not active until explicit activation

### Step 7.3: Reactivate Manual Group

1. Click `Activate Group`.
2. Perform one safe manual/right-click action again.

Expected result:

- manual workflow works again
- no stale test-owned interference remains

Pass criteria:

- remembered manual group survives a `Tests` session and returns inactive

## Phase 8: Source Editor Consistency

**Purpose**

Verify the editor follows the one authoritative current test.

### Step 8.1: Library Selection Drives Editor

1. Click one test in `Global Library`.
2. Observe the source editor.
3. Repeat with one test in `Config Library`.
4. Repeat with one test in `Profile Tests`.

Expected result:

- source editor always loads the same current test shown in `Current Test`
- there is no mismatch where one test runs and a different test source is displayed

### Step 8.2: Save/Revert/Validate Still Act On The Current Test

1. With a profile test selected, edit DSL text if safe.
2. Use `Validate Source`.
3. Use `Revert Source`.

Expected result:

- operations clearly apply to the visible current test

Pass criteria:

- editor ownership is not ambiguous

## Phase 9: Output Surfaces

**Purpose**

Verify report and result surfaces in the UI.

### Step 9.1: Test Activity Mirrors Test Commands

1. Use:
  - `State`
  - `Tests Overview`
  - `Print Next`
  - `Test Source`
  - `Show Lifecycle State`

Expected result:

- these appear in `Test Activity`
- `Show Lifecycle State` also appears in main `Output`

### Step 9.2: Test Result Visibility

1. Run at least one passing test.
2. Run at least one blocked or failing test if safely reproducible.

Expected result:

- header `Last Result` updates
- `Test Activity` shows result lines
- operator can see success/failure without watching only the robot console

### Step 9.3: Clear Output

1. Use the `Clear Output` control in the `Tests` activity area.

Expected result:

- `Test Activity` clears
- main `Output` behavior remains unaffected unless that specific control is meant to clear both

Pass criteria:

- test-related feedback is visible in the UI, not only on the robot console

## Phase 10: Negative Cases

**Purpose**

Exercise the expected blocked paths.

### Step 10.1: No Current Test

1. Reach a state with no current test selected, if the UI allows it.

Expected result:

- `Activate Group` is disabled or effectively blocked
- `Run Selected` is disabled

### Step 10.2: Empty Active Group Activation

1. If a path still produces an empty test-driven `active-group`, click `Activate Group`.

Expected result:

- activation is blocked with a clear empty-group message

### Step 10.3: Invalid Test Device

1. Use a test with a missing profile device, if safely reproducible.

Expected result:

- invalid row visible
- run blocked
- validation shows the mismatch

### Step 10.4: Busy/Not Connected

1. Attempt one test action while disconnected or while another command is pending, if safely reproducible.

Expected result:

- clear blocked message in UI output
- no silent failure

## Phase 11: Performance Sanity

**Purpose**

Catch obvious regressions that would make the feature impractical.

### Step 11.1: Disabled Idle

1. Leave the robot disabled and connected with the UI open.
2. Observe the robot console for at least one minute.

Expected result:

- no repeated `Loop time of 0.02s overrun` spam
- if occasional overruns still happen, capture them as a defect

### Step 11.2: Tests Interaction

1. Select tests repeatedly.
2. Activate/deactivate repeatedly.
3. Run at least two tests.

Expected result:

- no obvious runaway UI lag
- no repeated overrun flood caused by the Tests tab itself

## Final Pass Criteria

**Purpose**

Define when this feature is acceptable.

The feature passes this procedure only if all of the following are true:

- the user does not need to understand a separate `scope` concept
- `active-group` is the one visible dynamic group
- the `Tests` tab owns and displays test-driven `active-group` membership
- non-Tests tabs restore remembered manual `active-group`
- boundary crossing always deactivates
- `Current Test`, source editor, activation target, and run target all point at the same test
- support devices and singletons are shown correctly as locked rows when required
- `Run Selected` is blocked before activation and enabled after valid activation
- test result visibility is present in the UI
- manual/right-click behavior still works after returning from `Tests`
- no severe loop-overrun regression remains

## Failure Recording Template

**Purpose**

Make failures easy to compare and triage.

Record each failure as:

```text
Phase:
Step:
Profile:
Current tab:
Current test:
Expected:
Actual:
ACK/OUT lines:
showLifecycleState summary:
showRuntimeState summary:
Screenshot:
Notes:
```

