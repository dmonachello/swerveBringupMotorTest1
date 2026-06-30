# Test Plan: NT Removal Control-Plane Checkpoint 2026-06-28

## Purpose

Provide an exact, operator-executable validation procedure for the current `NT_Removal` checkpoint.

This checkpoint is intended to prove that the bringup control plane now works through REST without depending on NetworkTables for:

- host-to-robot commands
- session ownership
- runtime state used by the UI and CLI
- tests state used by the UI and CLI

This plan is intentionally written as a real procedure, not a checklist. Each phase includes:

- exact launch commands
- exact button presses or CLI commands
- exact expected outcomes

## Scope

This plan validates:

- Bringup UI control workflow
- Bridge CLI control workflow
- REST session acquisition and release
- runtime-state visibility
- tests-state visibility
- DS disable/enable behavior after REST-only control-plane migration
- host restart, robot restart, and explicit session reset behavior

This plan does not yet validate full removal of `bringup/diag/...`.

Out of scope:

- robot-side diagnostics/probe migration off NT
- removal of every diagnostics-side NT helper or doc
- full acceptance of [SPEC_REMOVE_NETWORKTABLES_COMPLETE.md](/c:/Users/dmona/swerve3/docs/SPEC_REMOVE_NETWORKTABLES_COMPLETE.md)

## Branch Under Test

- branch: `NT_Removal`
- spec: [SPEC_REMOVE_NETWORKTABLES_COMPLETE.md](/c:/Users/dmona/swerve3/docs/SPEC_REMOVE_NETWORKTABLES_COMPLETE.md)

## Checkpoint Definition

At this checkpoint, the expected architecture is:

- UI and CLI commands go through REST only
- UI and CLI runtime state comes from REST only
- UI and CLI tests state comes from REST only
- robot control workflow no longer requires `bringup/ui/...`, `bringup/tests/...`, or `bringup/ui_tcp/...`
- diagnostics-side NT usage may still exist

## Preconditions

- repo root is `C:\Users\dmona\swerve3`
- branch is `NT_Removal`
- roboRIO is reachable at `172.22.11.2`
- Driver Station is available
- the robot is deployed with the current branch build
- a small known profile exists, preferably `test_minimal_25_9`
- the active profile contains at least:
  - `FALCON 9`
  - `SPARKMAX/NEO 25`
  - `controller0`
  - `lmtSw0`
  - `roborio`
  - `pdp`

SID_COMMENT: CLI validation that involves typing while the robot is enabled should eventually be repeated from a second PC, not the Driver Station machine. Using the DS keyboard during enabled testing can interfere with timely disable / E-stop handling and can invalidate operator-flow timing observations.

## Safety

- put wheels off ground or otherwise secure the robot before any actuation
- keep the Driver Station disable button immediately available
- keep manual motor duty tests low

## Evidence To Capture

For each failed step, capture:

- screenshot of the active surface
- the exact command or button sequence used
- visible output text
- DS mode at the time of failure
- whether the failure reproduces after restarting only the host

## Phase 0: Local Gates

## Step 0.1: Open PowerShell at Repo Root

Run:

```powershell
cd C:\Users\dmona\swerve3
git branch --show-current
```

Expected:

- branch output is `NT_Removal`

## Step 0.2: Run Host UI Python Tests

Run:

```powershell
python -m pytest tools/can_nt/tests/test_bringup_ui_actions.py -q
```

Expected:

- command exits successfully
- no failing tests

## Step 0.3: Run REST Java Tests

Run:

```powershell
.\gradlew.bat test --tests frc.robot.rest.BringupRestServerTest --tests frc.robot.BridgeUiSessionCommandsTest
```

Expected:

- build is successful
- no compile failures
- both test classes pass

If either Step 0.2 or Step 0.3 fails:

- stop this procedure
- fix the branch before connected validation

## Phase 1: Bringup UI REST Startup

## Step 1.1: Launch UI

Open a new PowerShell window and run:

```powershell
cd C:\Users\dmona\swerve3
python tools\can_nt\can_nt_bridge.py --ui --rio 172.22.11.2
```

Expected:

- Bringup Control window opens
- UI does not print an error that `--ui` requires NT
- UI does not fail immediately at startup

## Step 1.2: Verify Initial Top Bar

Without pressing any buttons yet, inspect the top-right status label and the top command row.

Expected:

- status label uses `REST Connected (...)` or `REST Disconnected (...)`
- status label does not depend on `NT OK` / `NT Disconnected` wording for control-plane readiness
- `Activate Group`, `Deactivate Group`, `Show Runtime State`, and `Show Lifecycle State` are visible

## Step 1.3: Reclaim Session

In the left panel, under `Session`, click:

1. `Reconnect UI Session`

Expected:

- no ownership error remains stuck
- UI becomes command-capable after reconnect
- if a session message is shown in output, it indicates reconnect/reset success rather than NT state changes

## Phase 2: UI Runtime-State Validation

## Step 2.1: Select Profile

In the top bar:

1. Open the `Profile` dropdown
2. Select `test_minimal_25_9`

Expected:

- selected profile text updates
- no stale profile from a previous host session remains forced in the UI

## Step 2.2: Open Live Topology

Click the `Live Topology` tab.

Expected:

- topology view loads
- runtime/runnable card appears
- active group panel appears on the right

## Step 2.3: Check Disabled State

On Driver Station:

1. leave robot disabled

In the UI:

1. observe the top bar robot state
2. observe the runnable-state card

Expected:

- robot state indicates disabled
- runnable-state card is not `READY TO RUN`
- card text reflects disabled robot state accurately

## Step 2.4: Check Teleop State

On Driver Station:

1. select `TeleOperated`
2. click `Enable`

Expected:

- top bar robot state changes to teleop
- UI reflects enabled teleop promptly

## Step 2.5: Check Manual Not-Activated State

With robot enabled in teleop and before activating a group:

1. stay on `Live Topology`
2. inspect the runnable-state card

Expected:

- card is not `READY TO RUN` unless a group is actually active
- if `active-group` is not active, the card says `Activate Group first.` or equivalent manual-mode wording
- card must not mention teleop as a blocker if the UI already knows teleop is active

## Phase 3: UI Manual Active-Group Flow

## Step 3.1: Ensure Manual Ownership

Look at the top bar label.

Expected:

- it shows `Active Group Source: manual`

## Step 3.2: Add Devices to Active Group

In the left panel under `Groups`:

1. click `Active Add`
2. click `Active Add` again

Expected:

- the `Active Group` panel on the right now shows two devices
- no checkbox or group membership flicker occurs
- membership does not self-revert a second later

## Step 3.3: Activate Group

Click:

1. `Activate Group`

Expected:

- command is accepted
- runnable-state card changes to `READY TO RUN`
- the active-group panel shows devices as active/instantiated where appropriate

## Step 3.4: Deactivate Group

Click:

1. `Deactivate Group`

Expected:

- command is accepted
- runnable-state card returns to not-runnable manual wording
- no stale active impression remains

## Step 3.5: Reactivate Group

Click:

1. `Activate Group`

Expected:

- system returns to a good runnable manual state
- no need to change tabs or switch profiles to recover

## Phase 4: UI Tests-State Validation

## Step 4.1: Open Tests Tab

Click:

1. `Tests`

Expected:

- tests libraries and current test surfaces load
- `Test State` panel is visible in the upper-right area

## Step 4.2: Select a Known Test

In the `Profile Tests` list, click one known test, for example:

- `falcon9_move_150_rotations`

Expected:

- `Current Test` text matches the selected row
- the source editor, if visible, matches the selected test
- test-state panel updates

## Step 4.3: Run Selected

If the UI says the test is blocked because the group is not active:

1. click `Activate Group`

Then click:

1. `Run Selected`

Expected:

- test starts
- test result appears in the Tests activity/output surface
- selected test and result state remain aligned

## Step 4.4: Run All

Click:

1. `Run All`

Expected:

- batch starts normally
- tests state updates
- run-all completion is visible
- UI stays responsive

## Phase 5: UI DS Disable/Enable Transition

## Step 5.1: Establish Known Good Runnable State

Return to `Live Topology`.

Expected immediately after leaving `Tests`:

- `Active Group Source: manual`
- the remembered manual `active-group` membership is restored
- the restored manual group is inactive
- the runnable-state card does not claim ready

Then:

1. click `Activate Group`

Ensure:

1. robot is in enabled teleop
2. active-group is active
3. runnable-state card says `READY TO RUN`

## Step 5.2: Disable From Driver Station

On Driver Station:

1. click `Disable`

Expected:

- UI promptly shows disabled
- runnable-state card stops claiming runnable

## Step 5.3: Re-Enable From Driver Station

On Driver Station:

1. click `Enable`

Expected:

- UI returns to teleop state
- if activation was torn down by disable, UI now clearly says re-activation is required
- UI must not falsely remain runnable if a fresh `Activate Group` is actually needed

This step is a key acceptance point for this checkpoint.

## Phase 6: UI Tab-Bounce Stability

## Step 6.1: Bounce Across Tabs

After at least one test run, click these tabs in order:

1. `Output`
2. `Live Topology`
3. `Tests`
4. `Evidence`
5. `Visibility`
6. back to `Tests`
7. back to `Live Topology`

Expected:

- state cards stay coherent
- selected test stays aligned
- runtime state does not disappear unexpectedly while staying within the same ownership mode
- entering `Tests` may switch ownership to `selected test`
- leaving `Tests` may restore the remembered manual group inactive
- after returning to `Live Topology`, `NOT RUNNABLE` with `Activate Group first.` is acceptable if the bounce crossed the `Tests` boundary and manual ownership was restored inactive
- no NT-only stale state behavior reappears

## Phase 7: CLI REST Validation

## Step 7.1: Launch CLI

Open a new PowerShell window and run:

```powershell
cd C:\Users\dmona\swerve3
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
```

Expected:

- CLI starts
- no `--ui requires NetworkTables` style control-plane error appears

## Step 7.2: Reconnect Session

At the CLI prompt, run:

```text
connect
```

Expected:

- connect succeeds
- CLI acquires the REST session and performs the UI handshake
- ownership/session errors are cleared

## Step 7.3: Read Runtime State

Run:

```text
show runtime-state
```

Expected:

- command succeeds
- selected profile matches the UI
- output reflects current enabled/disabled state and current DS mode independently
- `mode=teleop` with `enabled=false` is acceptable when Driver Station is set to Teleop but the robot is currently disabled
- before activation, expect:
  - `runtimeActive=false`
  - `controlledLifecycleActive=false`
  - empty `activeRuntimeProfile`
  - devices not instantiated
- output reflects current groups/devices

## Step 7.4: Read Tests State

Run:

```text
show tests
```

Expected:

- command succeeds
- output lists the current DSL test library for the selected profile context
- the list includes known tests for `test_minimal_25_9`
- this command is a library/listing surface; it does not need to show selected-test or run-state detail

## Step 7.5: Manual Group Commands

Run:

```text
active add
active add
show runtime-state
```

Expected:

- both adds succeed or produce sane messages if already populated
- runtime state shows the same active-group membership visible in the UI

## Step 7.6: Test Command

Run:

```text
show tests
tests select falcon9_move_150_rotations
tests run --wait
```

Expected:

- commands succeed
- test selection is acknowledged before the run
- test result is reported
- no NT dependency is visible in command flow
- do not use plain `tests run` here if the procedure expects completion output; the default CLI behavior is asynchronous and requires `tests wait` or `tests run --wait` for the completion summary
- do not use `run test` here; that is a different command path and can fail with group-oriented errors such as `defaultGroup`

!!!SID!!! 6/28/26 - start testing more here next time!!!

## Step 7.7: Run All

Run:

```text
tests run-all --wait --timeout 120
```

Expected:

- batch runs normally
- blocked or skipped tests are reported sanely if hardware is missing
- use the `tests` command family here so the CLI waits for and prints the completion summary

## Phase 8: Restart and Reset Behavior

## Step 8.1: Host-Only Restart

1. close the UI
2. relaunch the UI using the same command from Step 1.1
3. click `Reconnect UI Session`

Expected:

- host restart does not require NT state to recover
- session/state re-establish cleanly

## Step 8.2: Robot-Code Restart

1. restart robot code
2. leave the UI open
3. wait for reconnect behavior

Expected:

- REST disconnect/reconnect is reflected
- session can be reacquired
- stale control-plane state is not dragged forward

## Step 8.3: Explicit Session Reset

In the UI:

1. click `Reset UI Session`
2. if needed, click `Reconnect UI Session`

Expected:

- session id rotates
- old state is invalidated
- commands still work after reconnect

## Pass Criteria

This checkpoint passes only if all are true:

- UI command flow works without NT control/state dependence
- CLI command flow works without NT control/state dependence
- runtime state is accurate in both UI and CLI
- tests state is accurate in both UI and CLI
- DS disable/enable does not leave false runnable state
- restart and reset behavior remains coherent

## Known Non-Goal At This Checkpoint

The following are not checkpoint failures by themselves:

- diagnostics-side NT plumbing still exists
- `bringup/diag/...` still exists in robot diagnostics/probe code
- docs still describing diagnostics-side NT behavior have not all been removed yet

Those belong to the next phase of complete NT removal.
