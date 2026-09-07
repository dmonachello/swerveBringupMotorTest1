# UI Robot Status Sync Explained

## Purpose

Explain how the Python Bringup UI stays in sync with robot runtime state, including mode and enable state driven by Driver Station.

## Scope

This document explains the current supported flow:

- Driver Station changes robot control state
- roboRIO Java code reads that state locally through WPILib
- the robot REST server publishes runtime snapshots
- the host UI polls those snapshots
- the UI converts them into typed state objects
- shared UI state logic derives the operator-facing status

This document is descriptive. It does not change behavior rules.

## Short Answer

The UI does not treat Driver Station as the direct source of truth.

The source of truth for robot state is the roboRIO process, because it reads WPILib and Driver Station state locally, then publishes the resulting runtime snapshot through the robot REST server. The host UI polls that REST state and rebuilds its local typed UI state from each fresh response.

## End-To-End Flow

### 1. Driver Station changes robot control state

Driver Station or FMS drives the robot control state seen by WPILib.

Examples:

- enabled vs disabled
- teleop vs autonomous vs test
- E-stop state

These changes do not go first to the PC UI. They go to the robot control stack on the roboRIO.

### 2. Robot code reads the state locally

The Java robot code reads the current robot state through WPILib on the roboRIO.

Typical state includes:

- `enabled`
- `estopped`
- `mode`
- current active runtime/lifecycle state
- selected profile
- active runtime profile
- instantiated devices
- active scope membership

This matters because the roboRIO is the only place where local robot truth and device lifecycle truth come together.

### 3. The robot REST server publishes runtime snapshots

The robot exposes runtime state through REST.

The important payload families are:

- session snapshot
- runtime state snapshot
- tests state snapshot

The runtime state snapshot contains the current robot-facing truth that the UI needs for operator decisions.

Examples:

- whether runtime is active
- whether the robot is enabled
- whether the robot is in teleop
- which devices are instantiated
- which devices are active in the current scope
- what profile the robot currently has selected

### 4. The host UI polls the robot REST server

The Python UI in `tools/can_nt/bringup_ui.py` periodically polls the robot session for current REST state.

The poll reads current snapshots rather than relying on old cached flags as truth.

This is important for two reasons:

- the robot can change state without the user pressing a UI button
- Driver Station can change the robot mode independently of the UI

Examples:

- the robot becomes disabled
- the robot leaves teleop
- the robot E-stops
- runtime deactivates
- the selected test on the robot changes

### 5. Raw REST JSON is normalized immediately

The UI no longer treats REST as a fake table.

Instead, raw payloads are converted immediately into typed snapshot objects.

Current typed snapshot families include:

- `SessionSnapshot`
- `RuntimeSnapshot`
- `TestsSnapshot`
- `RestUiSnapshots`

This normalization step is the transport boundary.

After this point, the UI should work from typed state, not raw JSON shape and not fake table adapters.

### 6. Shared UI state logic derives operator meaning

Typed snapshots alone are not the final operator-facing answer.

Shared logic in `tools/can_nt/host_ui_state_service.py` combines current runtime facts into UI decisions such as:

- runnable vs not runnable
- selected test readiness
- scope activation/deactivation allowed
- profile sync or mismatch state
- context sync prompts
- active-group and selected-test device row states

This shared logic exists so multiple tabs do not independently recompute the same meaning.

That follows the repo rule:

- one shared-state rule
- no cached-truth rule

### 7. Tabs render from shared current state

The tabs do not each own a separate truth model.

They render from the latest shared state derived from the latest REST snapshots and local context.

Examples:

- the Runnable State box
- selected test devices
- active-group panel
- button enabled/disabled state
- profile sync indicator
- live topology annotations that depend on runtime state

## Driver Station Specific Details

### Ultimate source of DS-driven state

For DS-driven state, the ultimate source is WPILib on the roboRIO.

The host UI does not directly query Driver Station for operator-facing truth.

Instead:

1. Driver Station changes the robot control state
2. WPILib exposes that state on the roboRIO
3. robot Java code reads it
4. robot REST publishes it
5. host UI polls it
6. shared UI state is recomputed

### What the UI learns from DS-driven changes

When DS changes state, the UI eventually updates:

- `enabled` / `disabled`
- `teleop` / `autonomous` / `test`
- `estopped`
- whether actions are currently allowed
- whether a selected test is runnable
- whether a manual scope can be activated

### Timing model

The update is poll-based, not push-based.

That means a DS change is reflected in the UI on the next successful REST poll cycle.

Because of that, the UI may briefly show the previous state until the next fresh runtime snapshot is received.

### Why the roboRIO must be authoritative

Using the roboRIO as the authoritative runtime source avoids a bad split-brain model.

If the host UI tried to infer robot control truth from local host assumptions, it could easily disagree with:

- the actual robot mode
- runtime activation state
- device instantiation state
- test selection state
- scope activation state

The current design prevents that by making the roboRIO runtime snapshot authoritative for robot-facing truth.

## Host Local State vs Robot State

Not all state comes from the robot.

The host still owns some local context, such as:

- temporary UI selection intent
- pending sync prompts
- viewport and widget state
- host-local preferences
- host-only evidence displays

But host-local state is not allowed to become the steady-state truth for robot runtime conditions when current robot state is available.

That is the practical meaning of the repo’s no-cached-truth rule.

## Example Walkthrough

Example: Driver Station disables the robot while the UI is open.

1. Driver Station sends a disable transition.
2. WPILib on the roboRIO reflects `enabled=false`.
3. Robot runtime state generation includes `enabled=false`.
4. The REST runtime snapshot returns that new value.
5. The host UI poll ingests the new snapshot.
6. Typed runtime state is updated.
7. Shared UI state logic recalculates action permissions.
8. The UI updates:
   - Runnable/Test State may become blocked
   - activation or run actions may disable
   - any status panels that depend on enabled state change accordingly

## Failure and Drift Cases

### Robot REST unavailable

If the host cannot poll the robot REST server, the UI cannot confirm fresh robot runtime truth.

In that condition, the UI must treat the connection as stale or unavailable rather than inventing robot truth locally.

### Host selection differs from robot selection

The host can temporarily hold a local selection that has not yet been applied on the robot.

That is a context mismatch, not a new source of truth.

The robot-selected profile or robot-selected test remains authoritative for robot runtime state until a successful command changes it.

### Driver Station changes state without UI interaction

This is normal.

The polling model exists specifically so the UI can track changes that happened outside a direct UI button press.

## Key Files

- `tools/can_nt/bringup_ui.py`
- `tools/can_nt/rest_ui_snapshot_service.py`
- `tools/can_nt/rest_ui_state_models.py`
- `tools/can_nt/host_ui_state_service.py`
- `src/main/java/frc/robot/Robot.java`
- `src/main/java/frc/robot/rest/BringupRestServer.java`

## Tradeoffs

- Polling is simpler than a live push stream, but it means updates are not instantaneous.
- Centralized typed normalization improves correctness, but it requires discipline to keep raw REST parsing out of tabs.
- Host-local UI intent is useful for workflows, but it must not override fresh robot runtime truth.

## Future Extensions

- Add a compact sequence diagram that shows DS -> WPILib -> runtime snapshot -> REST -> UI.
- Add exact method references for runtime snapshot construction and host poll ingestion.
- Add a troubleshooting section for stale UI state vs stale REST vs host-local pending context.
