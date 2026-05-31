# User Guide: Add A Robot Local Command

## Purpose

Show the current end-to-end path for adding a new robot-local command that can be triggered from a controller and, if desired, exposed in the host UI.

This guide uses `genericCmd` as the example. In the current codebase, `genericCmd` is intentionally cloned from `addAll` so it acts as a safe template rather than a new robot behavior.

## What A Robot Local Command Is

A robot-local command is a named Java command that:

- is validated against the canonical Java registry
- can be requested from controller bindings on the robot
- can also be requested from the host UI over TCP when allowed
- runs through the shared robot-local command executor
- may finish immediately or remain active across multiple loops
- can always be stopped safely

Examples already in the system:

- `addMotor`
- `addAll`
- `genericCmd`
- `clearFaults`
- `runTest`
- `runAllTests`
- `printState`
- `uiHandshake`

## Current Architecture

The active path is:

1. Java command id and behavior are defined under `src/main/java/frc/robot/commands/local/`.
2. `RobotLocalCommandRegistry` holds the canonical table of command definitions.
3. `BindingsManager` validates controller binding command names against that registry.
4. `RobotV2` samples controller inputs and submits command requests through `BridgeUiCommandHandler`.
5. `RobotLocalCommandExecutor` runs one active command and at most one queued command.
6. `BridgeUiCommandHandler` provides the shared host/runtime services used by command implementations.
7. Optional host-UI button metadata is generated from the Java registry into Python artifacts.

Important current boundary:

- The active `RobotV2` plus host-UI path uses the unified registry and executor.
- Legacy classes such as `Robot.java` and `BringupCommandRouter.java` still exist in the tree, but they are no longer the model to copy for new work.

## The Short Version

To add a new command like `genericCmd`, you usually do this:

1. Add a registry row in `RobotLocalCommandRegistry`.
2. Add or update the command behavior in the appropriate grouped Java source file.
4. If needed, extend `RobotLocalCommandHost` and `BridgeUiCommandHandler`.
5. If controller-triggered, add a binding in `src/main/deploy/bringup_bindings.json`.
6. Regenerate the Python host-UI artifacts.
7. Add or update focused Java tests.
8. Run Java and maintained regressions.

## File Map

Canonical Java command model:

- [RobotLocalCommandDefinition.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandDefinition.java)
- [RobotLocalCommandRegistry.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java)
- [RobotLocalCommand.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommand.java)
- [RobotLocalCommandRequest.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandRequest.java)
- [RobotLocalCommandParams.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandParams.java)
- [RobotLocalCommandExecutor.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandExecutor.java)
- [RobotLocalCommandHost.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandHost.java)

Grouped command source files:

- [RobotLocalRuntimeCommandGroup.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalRuntimeCommandGroup.java)
- [RobotLocalReportCommandGroup.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalReportCommandGroup.java)
- [RobotLocalTestCommandGroup.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalTestCommandGroup.java)
- [RobotLocalLegacyUiCommandGroup.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalLegacyUiCommandGroup.java)

Robot integration:

- [RobotV2.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/RobotV2.java)
- [BridgeUiCommandHandler.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java)
- [BindingsManager.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/input/BindingsManager.java)
- [bringup_bindings.json](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/deploy/bringup_bindings.json)

Host-UI generation path:

- [RobotLocalCommandInventoryMain.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandInventoryMain.java)
- [build.gradle](C:/Users/dmona/swerveBringupMotorTest1-main/build.gradle)
- [generate_robot_local_command_artifacts.py](C:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/scripts/generate_robot_local_command_artifacts.py)
- [robot_local_command_inventory.json](C:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/generated/robot_local_command_inventory.json)
- [robot_local_commands_generated.py](C:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/generated/robot_local_commands_generated.py)
- [bringup_ui.py](C:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py)

Test coverage:

- [RobotLocalCommandRegistryTest.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/test/java/frc/robot/RobotLocalCommandRegistryTest.java)

## Worked Example: `genericCmd`

## Step 1: Add The Registry Row

Add the new wire-visible command name and metadata directly in `RobotLocalCommandRegistry`.

Current example:

```java
register(rows, runtimeDefinition(
    COMMAND_GENERIC_CMD,
    "",
    "genericCmd",
    "Example controller/local command cloned from addAll.",
    false,
    false,
    new RobotLocalHostVoidCommand(
        true,
        REASON_PROFILE_ACTIVATE,
        MESSAGE_PROFILE_INACTIVE_ADD,
        METHOD_RUN_GENERIC,
        "Ran genericCmd.")));
```

What this does:

- defines the canonical command name seen by bindings and host UI
- gives the registry all policy and UI metadata in one place
- keeps the Java registry and the generated Python artifacts tied to one source of truth

Why this matters:

- `BindingsManager` validation depends on the registry
- host-UI generation also depends on the registry
- for many commands, this is now the only place where the command name has to be added manually

## Step 2: Choose The Command Implementation Style

Add or update the behavior in the grouped command source file for the command family.

That is the current `genericCmd` path. It means a simple runtime/report command often needs only:

- one registry row
- one grouped command source file update
- no extra switch branch
- no extra command-id file

If the command is not simple enough for the helper classes, implement a custom `RobotLocalCommand`.

Current grouped examples:

- [RobotLocalRuntimeCommandGroup.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalRuntimeCommandGroup.java)
- [RobotLocalReportCommandGroup.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalReportCommandGroup.java)
- [RobotLocalTestCommandGroup.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalTestCommandGroup.java)
- [RobotLocalLegacyUiCommandGroup.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalLegacyUiCommandGroup.java)

Every custom command must support:

- `execute(...)`

Optional lifecycle hooks are:

- `init(...)`
- `interrupt(...)`
- `finished(...)`
- `isFinished(...)`

For `genericCmd`, the behavior intentionally mirrors `addAll`.

For the common case, the grouped file can use shared helpers internally when the command:

- optionally ensures an active profile
- calls one no-argument host method
- finishes immediately with a fixed success message

Implement a custom command when the command:

- has multi-loop behavior
- needs `init(...)`, `interrupt(...)`, or `isFinished(...)`
- needs non-trivial argument handling
- is acting as a bridge to the legacy UI/session/group command surface

If a new family becomes necessary, add a new grouped owner class and point registry rows at it.

What the registry row owns:

- command wire name
- group
- invocation kind
- controller allowed
- host UI allowed
- queueable policy
- auto-stop-on-source-loss policy
- host-UI visibility and label metadata
- default UI args JSON
- Java command implementation owner

Why this matters:

- this table is the canonical lookup surface
- controller validation and host-UI generation both consume it
- adding a new command should be obvious by searching the registry
- the old extra command-id file is gone, so command-name ownership does not drift between two Java files

## Step 3: Add Host Services If Needed

If the command needs host/runtime capabilities that the command implementation cannot already access, extend:

- [RobotLocalCommandHost.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandHost.java)
- [BridgeUiCommandHandler.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java)

Use this step when the command needs a new shared service such as:

- a new runtime action
- a new report emission path
- a new profile or session operation
- a new safety stop or cleanup behavior

If the command can reuse existing host methods cleanly, do not add a new one just to mirror the command name.

## Step 4: Bind It To A Controller Input

If the command should be controller-triggered, add an entry to [bringup_bindings.json](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/deploy/bringup_bindings.json).

Example:

```json
{
  "command": "genericCmd",
  "controller": "controller0",
  "input": "button",
  "id": "Y"
}
```

What matters:

- `command` must match the Java registry wire name
- the controller and input fields must already be valid for `BindingsManager`
- the invocation shape should match the registry row

If you add the binding before the registry row exists, the robot will reject the command name as unknown.

## Step 5: Generate Host-UI Artifacts

If the command should be mirrored to the host UI, set the UI metadata in the Java registry row and then regenerate the Python artifacts.

Run:

```powershell
python tools/can_nt/scripts/generate_robot_local_command_artifacts.py
```

What this does:

- runs the Gradle `emitRobotLocalCommandInventory` task
- emits JSON inventory from `RobotLocalCommandRegistry`
- regenerates the Python metadata module used by `bringup_ui.py`

The user should not hand-write Python command metadata, button lists, or tooltip maps for this workflow.

## Step 6: Add Focused Java Coverage

Add or update a focused Java test.

Current example:

- [RobotLocalCommandRegistryTest.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/test/java/frc/robot/RobotLocalCommandRegistryTest.java)

Minimum useful coverage:

- the registry knows the command name
- the lookup returns the expected row
- the command can be dispatched through the executor

If the command has non-trivial behavior, also add a test near the actual runtime behavior or host integration.

## Step 7: Run Validation

For this repo, the normal checks are:

```powershell
./gradlew.bat test
python tools/can_nt/scripts/run_regressions.py --suite all
```

If you changed only generated host-UI artifacts and Java registry metadata, still run both checks before treating the change as complete.

## Full Trace For `genericCmd`

This is the current controller path.

1. `bringup_bindings.json` binds `"genericCmd"` to a controller input.
2. `BindingsManager` loads that entry and validates the name against `RobotLocalCommandRegistry`.
3. `RobotV2.teleopPeriodic()` samples bindings and passes the binding state to `BridgeUiCommandHandler.submitControllerBindings(...)`.
4. The handler creates a `RobotLocalCommandRequest` for the new active command input.
5. `RobotLocalCommandExecutor.submit(...)` performs registry lookup and admission control.
6. `RobotLocalCommandExecutor.step()` drives the active command lifecycle.
7. The runtime command group executes `genericCmd` against `RobotLocalCommandHost`.
8. `BridgeUiCommandHandler` supplies the shared runtime implementation used by the command.

This is the current host-UI path.

1. The Java registry row exposes `showInHostUi` and other UI metadata for robot-backed actions.
2. `generate_robot_local_command_artifacts.py` emits the generated JSON and Python metadata for those robot-backed actions.
3. `tools/can_nt/host_ui_actions.py` defines host-local UI actions that are not robot commands.
4. `bringup_ui.py` merges the robot metadata and host-local metadata into one action model and builds UI sections from that merged view.
5. For robot-backed actions, the UI sends the same command name over TCP.
6. `BridgeUiCommandHandler` adapts the TCP request into a `RobotLocalCommandRequest`.
7. The same `RobotLocalCommandExecutor` and command implementation run the command.

Host-local actions stay inside the desktop UI process. They share the same render and preference pipeline, but they do not go through the robot command registry.

## Common Mistakes

### Binding Before Registry

If the binding file uses a command name that is not in the Java registry, the robot rejects it as unknown.

### Putting Common Behavior In The Registry Instead Of The Group File

The registry should own command metadata and lookup policy. Keep the actual command behavior in the grouped source file.

### Copying Old Router Or Dispatcher Patterns

Do not use `BringupCommandRouter`, old context hooks, or the earlier dispatcher/family flow as the template for new commands. The active path is the registry plus executor model.

### Hand-Writing Python Host-UI Command Code

Do not add a new button list entry or tooltip map by hand as the primary path. Put the metadata in Java and regenerate the mirrored artifacts.

### Reusing `addAll` By Name Instead Of By Pattern

Do not point a new button at `addAll` just because the new behavior is close. Add a distinct command id if the product meaning is different.

That is why `genericCmd` exists.

## When To Skip A New Command

Do not add a new robot-local command if:

- an existing command already matches the intended product behavior
- the change only affects host-side presentation
- the command really belongs in DSL behavior instead of the robot-local command system

The point of this pattern is clarity, not command-name sprawl.

## Appendix A: Expose The Command In The Host UI

Purpose: Show the current host-UI path without requiring the user to hand-write Python-side command definitions.

To expose a command in the host UI:

1. Set `hostUiAllowed` to `true` in the Java registry row.
2. Set `showInHostUi` to `true`.
3. Fill in:
   - `uiSection`
   - `uiLabel`
   - `uiDescription`
   - `uiArgsJson` when needed
4. Regenerate the host-UI artifacts:

```powershell
python tools/can_nt/scripts/generate_robot_local_command_artifacts.py
```

5. Start the UI and confirm the button appears in the generated section list.

The UI button list is built from:

- [robot_local_command_inventory.json](C:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/generated/robot_local_command_inventory.json)
- [robot_local_commands_generated.py](C:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/generated/robot_local_commands_generated.py)
- [bringup_ui.py](C:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py)

Per-command visibility preferences are stored in:

- `backup_data/ui/bringup_ui_command_prefs.json`

User rule:

- the user should not need to edit Python to expose a new robot-local command

## Appendix B: Current Checklist For Adding A New Command

Purpose: Provide a concise checklist aligned with the current registry and executor model.

- Add a registry row in [RobotLocalCommandRegistry.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java).
- Add or update the behavior in the appropriate grouped command source file under [src/main/java/frc/robot/commands/local](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local).
- If needed, extend [RobotLocalCommandHost.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandHost.java) and implement the new methods in [BridgeUiCommandHandler.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java).
- If controller-triggered, add or update the binding in [bringup_bindings.json](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/deploy/bringup_bindings.json).
- If host-UI-visible, set the UI metadata in the Java registry row.
- Regenerate the host-UI artifacts with `python tools/can_nt/scripts/generate_robot_local_command_artifacts.py`.
- Add or update focused Java tests.
- Run `./gradlew.bat test`.
- Run `python tools/can_nt/scripts/run_regressions.py --suite all`.

## Appendix C: What You Do Not Need To Edit

- The user does not need to hand-write Python button code in `bringup_ui.py`.
- The user does not need to maintain a separate Python command-name list.
- The user does not need to hand-author tooltip maps for robot-local commands.
- The user does not need to update a separate Java command-id file.

Those Python-side artifacts are generated from the Java registry and consumed by the UI.
