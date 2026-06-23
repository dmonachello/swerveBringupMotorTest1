
# Controlled Lifecycle No-Battery Test Procedure

## Purpose

Provide one exact step-by-step procedure for verifying the controlled lifecycle feature when the roboRIO is powered but a drive battery is not installed.

This procedure is for June 22, 2026 style validation:

- roboRIO powered
- host PC connected to the robot network
- no real motor-power testing

## What This Procedure Verifies

This procedure verifies:

- lifecycle command routing
- UI and CLI connectivity
- disconnected / reconnect session behavior
- host-profile to robot-profile reconciliation on connect
- `showRuntimeState` and `showLifecycleState` readback
- VMS-style ACK status behavior for success and failure
- right-click manual-test popup behavior
- manual-duty command failure semantics
- profile-change blocking while lifecycle is active
- lifecycle active/inactive UI notice consistency

This procedure does not verify:

- actual motor spin
- current draw under load
- realistic bus voltage on motor controllers
- any behavior that requires a real battery

## Before You Start

You need:

- the repo on the Windows Driver Station or development PC
- the roboRIO powered on
- the PC connected to the robot network
- Python available in PowerShell

Typical robot IP in this repo:

- `172.22.11.2`

Repo root:

- `C:\Users\dmona\swerveBringupMotorTest1-main`

## Which Program To Run

There are two host-side programs used in this procedure.

1. Bridge CLI

This is the terminal program where you type commands such as:

```text
lifecycle activate active-group
show runtime-state --json --pretty
```

You start it with:

```powershell
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
```

2. Bringup Control UI

This is the desktop window with buttons, output pane, and Live Topology view.

You start it with:

```powershell
python tools\can_nt\can_nt_bridge.py --ui --rio 172.22.11.2
```

You will use both.

## Step 1: Open PowerShell In The Repo

Open PowerShell.

Change to the repo root:

```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
```

## Step 2: Start The CLI In Disconnected State

In the first PowerShell window, run:

```powershell
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
```

Wait for the CLI prompt.

Expected result before any connect attempt:

- the prompt is:

```text
bridge*(disconnected)>
```

- no host profile is implied yet
- no `Profile context -> ...` line is printed at startup

## Step 3: Verify Failed Connect While Robot Is Unavailable

If practical, do this once with the roboRIO unplugged from the network or powered off.

Type:

```text
connect
```

Expected result:

- the command fails cleanly
- the prompt remains:

```text
bridge*(disconnected)>
```

- no host profile is adopted

If the roboRIO is already connected and reachable, skip this step and note that it was not exercised in this run.

## Step 4: Connect The CLI To The Robot

Make sure the roboRIO is powered and reachable.

Type:

```text
connect
```

Expected result:

- the CLI connects to the robot
- if the robot already has a selected profile, the CLI immediately adopts that profile as host context
- a line similar to this is printed before the final prompt:

```text
Profile context -> test_minimal_25_9
```

- the prompt updates to include the adopted profile, for example:

```text
bridge*-profile-test_minimal_25_9>
```

## Step 5: Verify Basic Lifecycle Readback In CLI

Type these commands in the CLI exactly:

```text
show lifecycle-state --json --pretty
show runtime-state --json --pretty
```

Expected result:

- neither command reports unknown-command
- both commands return JSON output

Record whether you see these fields in `show runtime-state`:

- `runtimeActive`
- `controlledLifecycleActive`
- `selectedProfile`
- `activeRuntimeProfile`

## Step 6: Verify Local And Robot Profile Views After Connect

Type:

```text
show profiles local
show profiles robot
show profiles both
```

Expected result:

- `show profiles local` shows the adopted host profile context
- `show profiles robot` shows the robot-selected profile
- `show profiles both` shows both sources in one command
- after a successful connect-and-adopt flow, local and robot selected profiles should match

## Step 7: Activate Lifecycle In CLI

First make sure `active-group` is not empty and lifecycle is currently inactive.

Type:

```text
show lifecycle-state
show runtime-state --json --pretty
```

In `show lifecycle-state`, look for:

```text
state=INACTIVE
```

If lifecycle is already active, deactivate it first.

Type:

```text
lifecycle deactivate-active
show lifecycle-state
```

Do not continue until `show lifecycle-state` reports:

```text
state=INACTIVE
```

Then check the active group membership in `show runtime-state --json --pretty`.

Look for:

```text
"groups": [
  {
    "name": "active-group",
    "members": []
  }
]
```

If `members` is empty, populate the group before trying lifecycle activation.

Type:

```text
active add
show runtime-state --json --pretty
```

If `members` is still empty, repeat `active add` once more and re-run:

```text
show runtime-state --json --pretty
```

Do not continue until both of these are true:

- `show lifecycle-state` reports `state=INACTIVE`
- `active-group.members` contains at least one device label

Then type:

```text
lifecycle activate active-group
show lifecycle-state --json --pretty
show runtime-state --json --pretty
```

Expected result:

- `show lifecycle-state` reports `state=INACTIVE` before activation
- `active-group.members` is not empty before activation
- `lifecycle activate active-group` succeeds
- `show lifecycle-state` shows an active session
- `show runtime-state` shows:
  - `controlledLifecycleActive: true`
  - active session/group information for the in-scope devices

## Step 8: Verify Profile Change Is Blocked While Lifecycle Is Active

While lifecycle is still active, type:

```text
profile test_minimal_25_9
```

Expected result:

- command is rejected
- the message says profile change is blocked while controlled lifecycle is active

This is a behavior check only.

It should fail with an error status, not a fake success.

## Step 9: Verify Manual-Duty Failure Semantics In CLI

Still in the CLI, type these exact commands:

```text
manualDeviceDutyClear name="does-not-exist"
manualGroupDutyClear
manualGroupDutyClear group="does-not-exist"
```

What these mean:

- `manualDeviceDutyClear name="does-not-exist"`
  - asks the robot to clear manual duty for a device label that should not exist
- `manualGroupDutyClear`
  - intentionally omits the required `group` argument
- `manualGroupDutyClear group="does-not-exist"`
  - asks the robot to clear a group name that should not exist

Expected result for all three:

- ACK status is an error, not `ok`
- the message is specific

Expected message text:

- `Unknown device: does-not-exist`
- `manualGroupDutyClear requires args.group.`
- `Group not found: does-not-exist`

What should not happen:

- `ACK ... ok`
- generic `OUT OK`

## Step 10: Verify A Known-Good Manual Clear Shape In CLI

Type:

```text
manualGroupDutyClear group="active-group"
```

Expected result:

- command succeeds if `active-group` exists and has already been created/populated in Step 4
- the command returns success status
- message is similar to:

```text
Manual group duty cleared.
```

This does not prove motor behavior.

It only proves the command shape and status behavior.

## Step 11: Deactivate Lifecycle In CLI

Type:

```text
lifecycle deactivate active-group
show lifecycle-state --json --pretty
show runtime-state --json --pretty
```

Expected result:

- lifecycle deactivation succeeds
- `show lifecycle-state` returns inactive state
- `controlledLifecycleActive` becomes `false`

## Step 12: Verify Disconnect And Reconnect CLI Session Behavior

Type:

```text
disconnect
```

Expected result:

- the CLI disconnects cleanly
- the prompt returns to:

```text
bridge*(disconnected)>
```

Then type:

```text
connect
```

Expected result:

- the CLI reconnects cleanly
- the robot-selected profile is immediately adopted again
- the prompt returns to the profile-qualified form, for example:

```text
bridge*-profile-test_minimal_25_9>
```

## Step 13: Start The UI

Open a second PowerShell window.

Change to the repo root:

```powershell
cd C:\Users\dmona\swerveBringupMotorTest1-main
```

Start the UI:

```powershell
python tools\can_nt\can_nt_bridge.py --ui --rio 172.22.11.2
```

Wait for the Bringup Control UI window to open.

## Step 14: Verify Initial UI Session State

Before the UI reaches the robot session:

1. confirm the robot IP is `172.22.11.2`
2. confirm the top status area makes it clear whether the UI is connected or disconnected

Expected result:

- the disconnected state is explicit
- the UI does not imply that it is already using a live robot profile before connection

## Step 15: Connect The UI

In the UI, connect the REST session if it is not already connected.

Expected result:

- the output pane starts showing ACK and OUT entries
- UI actions become available
- if the robot already has a selected profile and the UI local profile context is empty, the UI adopts the robot profile
- if the UI already has a different host profile context, the UI prompts whether to switch to the robot profile

## Step 16: Verify Lifecycle Buttons In UI

In the UI, click these in order:

1. `Show Lifecycle State`
2. `Lifecycle Activate`
3. `Show Lifecycle State`
4. `Show Runtime State`

Expected result:

- the output pane shows commands including:
  - `showLifecycleState`
  - `lifecycleActivate`
  - `showRuntimeState`
- no crash or exception occurs

## Step 17: Verify The Lifecycle/Runtime Notice Consistency In UI

After lifecycle is active:

1. open the Live Topology area
2. look for any warning banner or runtime-state notice

Expected result:

- the UI should not show:

```text
Runtime inactive. Click Runtime Activate.
```

just because legacy runtime is inactive while controlled lifecycle is active.

That warning is only allowed when controlled lifecycle is not active.

## Step 18: Verify Right-Click Manual Test Popup Behavior

With lifecycle active in the UI:

1. in Live Topology, right-click a motor node
2. if available, also right-click a group

Expected result:

- the manual-duty popup opens
- the action is not blocked only because legacy runtime is inactive

Allowed blocking cases:

- robot disabled
- E-stop
- stale robot state

Not allowed blocking case:

- lifecycle active but legacy runtime inactive

## Step 19: Verify Lifecycle Deactivate In UI

In the UI, click:

1. `Lifecycle Deactivate`
2. `Show Lifecycle State`
3. `Show Runtime State`

Expected result:

- lifecycle deactivation succeeds
- `controlledLifecycleActive` becomes false

After that, if runtime is inactive, the UI may show:

```text
Runtime inactive. Click Runtime Activate.
```

That is correct after lifecycle is no longer active.

## Step 20: Optional CLI Cross-Check After UI Actions

Return to the CLI window and type:

```text
show lifecycle-state --json --pretty
show runtime-state --json --pretty
```

Expected result:

- the CLI readback matches the UI actions you just performed

## Pass/Fail Summary

Mark the procedure as passed if all of these are true:

- CLI `show lifecycle-state` works
- CLI `show runtime-state` works
- CLI starts disconnected with a neutral prompt
- CLI `connect` fails cleanly when the robot is unavailable
- CLI `connect` adopts the robot-selected profile immediately when the robot is reachable
- CLI `disconnect` returns the prompt to disconnected state
- lifecycle activate/deactivate works in CLI and UI
- profile change is blocked while lifecycle is active
- bad manual clear commands return error status with specific messages
- good manual clear command shape succeeds
- UI does not show misleading runtime-inactive warning during active lifecycle
- right-click popup opens while lifecycle is active

## What To Save In Your Notes

Capture:

- one startup screenshot or log showing the disconnected CLI prompt
- one failed `connect` output if you exercised the unavailable-robot case
- one successful `connect` output showing `Profile context -> ...`
- one `show lifecycle-state --json --pretty` output while active
- one `show runtime-state --json --pretty` output while active
- one screenshot of the UI while lifecycle is active
- the exact ACK/error text for the three bad manual-clear commands

## What To Test Later With The Battery

After the battery arrives, run a separate real-motor test pass for:

- actual motor spin
- real current draw
- real bus voltage
- motion/no-motion evidence behavior
- manual group/device duty under real load
