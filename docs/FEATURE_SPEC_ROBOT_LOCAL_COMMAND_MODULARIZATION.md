SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Feature Spec: Unified Robot Local Command Executor

## Purpose

Define one canonical command system for robot-local commands invoked from controller bindings and from the host UI remote-command path.

The goal is to replace scattered string-based command handling with one registry, one lookup path, one executor, and one standardized command interface shared across robot-local command surfaces.

## Summary

This spec replaces the current per-loop "check many commands and run whichever branches match" model with a single-command execution model.

At the end of this work:

- Java is the canonical source of truth for robot-local commands.
- Every robot-local command is defined in one static Java registry table.
- Simple host-backed commands should be definable directly from that registry without a separate command-id file.
- Command behavior should live in grouped Java source files such as runtime, reports, tests, and session/group adapters.
- All controller-triggered and host-UI-triggered robot-local commands use the same lookup and execution path.
- Only one command may execute at a time.
- At most one additional command may be queued.
- Any running command may be interrupted or stopped safely at any time.
- Python host-UI artifacts are generated from the Java registry as much as possible.

This spec is only about the robot-local command system.

This spec is not about the DSL command model.

## Current Implementation Snapshot

Purpose: Record what is already migrated on `main` so readers do not confuse this spec with a wholly future design.

Implemented on the active `RobotV2` plus host-UI path:

- canonical Java command registry in `RobotLocalCommandRegistry`
- single-active plus one-queued executor in `RobotLocalCommandExecutor`
- shared request/result model under `src/main/java/frc/robot/commands/local/`
- reusable helper commands for common host-method-backed runtime and report commands
- grouped runtime/report/test/legacy command source files referenced by the registry
- controller submission through `RobotV2` and `BridgeUiCommandHandler`
- host-UI command submission through the same executor path
- generated JSON inventory and generated Python host-UI metadata from the Java registry
- host-UI section/button construction from generated artifacts

Still not fully cleaned up:

- `Robot.java` remains in the tree as a legacy path
- `BringupCommandRouter` remains in the tree as compatibility scaffolding
- `BridgeUiRuntimeCommands` still exists as a compatibility surface even though active command execution has moved into the unified executor

That is why this spec is tagged `PARTIALLY_IMPLEMENTED` instead of `IMPLEMENTED`.

## User Outcome

Users and developers should be able to:

- add one new robot-local command in one obvious place
- add a simple command without updating a second Java name-definition file
- bind it to a controller input
- expose it in the host UI if desired
- know exactly how it is invoked and stopped
- avoid independent command-name lists drifting across Java and Python

## Scope

Includes:

- robot-local controller commands
- robot-side remote host-UI commands
- report commands
- test-selection and test-execution commands
- runtime/system commands
- UI/session/protocol commands currently treated as robot commands
- generated Python artifacts for host-UI button construction

Excludes:

- DSL command execution semantics
- Python CLI command refactors in the first pass
- NetworkTables contract redesign
- controller binding syntax redesign
- dynamic registration or plugin loading

## Current Problem

The current command system is spread across too many places.

Command names and behavior are currently split across:

- [BindingsManager.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/input/BindingsManager.java)
- [BringupCommandRouter.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupCommandRouter.java)
- [Robot.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/Robot.java)
- [RobotV2.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/RobotV2.java)
- [BridgeUiRuntimeCommands.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiRuntimeCommands.java)
- Python UI helpers such as:
  - [bridge_ops.py](C:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_ops.py)
  - [bringup_ui.py](C:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py)

Effects:

- command-name lists can drift
- controller and host UI can accidentally evolve separate semantic models
- tracing a command from string name to implementation is harder than it should be
- safety-stop and interrupt behavior is not centralized
- Python has to repeat robot command names manually

## Design Goals

- One canonical Java registry table owns robot-local command definitions.
- One lookup routine resolves commands by string name.
- One executor runs commands regardless of whether they came from controller bindings or the host UI.
- All commands implement one standardized Java command interface.
- Simple commands should be definable as registry rows backed by reusable command helpers.
- The common add-command path should be one grouped command source file plus one registry-row edit.
- Only one command executes at a time.
- A running command can always be stopped or interrupted safely.
- Host UI artifacts should be generated from the Java command registry as much as practical.
- Adding a new command should require minimal handwritten changes outside the Java registry and the command implementation itself.

## Non-Goals

- Preserve backward compatibility with the current local-command implementation structure.
- Keep old parallel command-family ownership in place.
- Clean up every Python CLI command reference in the same pass.
- Build a dynamic runtime registration system.

## Command Sources

Purpose: Define which inputs feed the unified executor.

The unified executor must support command requests from:

- controller bindings on the robot
- host UI remote commands
- host UI session/protocol commands currently treated as command names

Controller and host UI are different request sources, but they must use the same registry lookup and the same executor.

## Command Types

Purpose: Define the kinds of commands the system must support.

The unified registry must support all of these:

- button/edge commands
- hold-style commands
- axis/value-driven commands
- report commands
- test commands
- runtime/system commands
- UI/session/protocol commands

Examples include:

- `addMotor`
- `addAll`
- `genericCmd`
- `printState`
- `printHealth`
- `printBindings`
- `printTestsOverview`
- `runTest`
- `runAllTests`
- `clearFaults`
- `canSweep`
- `toggleDashboard`
- `profileToggle`
- `leftDrive`
- `rightDrive`
- `uiHandshake`
- `uiDisconnect`
- `uiMonitorEnable`
- `uiMonitorDisable`

## Execution Model

Purpose: Replace the old multi-branch polling behavior with a single active command model.

### Old Behavior

Previously, the robot sampled a `BindingState` every loop and independently evaluated many command branches.

That meant multiple command behaviors could occur in one loop if several conditions were true.

### New Behavior

The new system uses a command-request and command-executor model.

Behavior:

1. A command request arrives.
2. The command name is looked up in the canonical registry table.
3. Standardized command params are built.
4. The executor starts, queues, interrupts, or rejects the request based on executor state and request mode.
5. One active command instance executes until it completes, fails, is stopped, or is interrupted.

Only one command may be active at a time.

At most one additional command may be queued.

More than one queued command is rejected.

The currently active command may always be interrupted or stopped safely.

## Request Dispatch Modes

Purpose: Define what the caller can ask the executor to do when a new request arrives.

Every command request includes a dispatch mode.

Initial dispatch modes:

- `IMMEDIATE`
- `QUEUE`
- `INTERRUPT`

Expected behavior:

- `IMMEDIATE`
  - start now if idle
  - reject if another command is active
- `QUEUE`
  - queue if one command is active and no queued command exists
  - reject if queue slot is already occupied
- `INTERRUPT`
  - interrupt the active command immediately
  - clean it up safely
  - run the new command now

## Controller Semantics

Purpose: Define how controller inputs submit requests into the unified executor.

Controller-triggered commands no longer run by directly branching over binding names.

Instead:

- the controller layer detects a new active input condition
- it creates one command request
- it submits that request into the same executor used by host UI

For hold and axis/value-driven commands:

- the controller submits one request when the input becomes active
- the running command reads live values through a provider in standardized params
- the command is not resubmitted every loop

Controller-originated commands auto-stop on source loss.

That means:

- if the triggering controller input is no longer active
- the executor stops the active controller-originated command automatically

## Queueing Rules

Purpose: Keep command behavior predictable and safe.

Queue rules:

- one active command maximum
- one queued command maximum
- further queued requests are rejected
- queued commands refresh their live input/provider state at start time

Interrupt rules:

- the active command can always be interrupted
- interrupt immediately stops the active command and runs the new command
- interrupt must not be blocked by the queue slot already being occupied

## Stop and Interrupt Safety

Purpose: Guarantee that no command can run indefinitely without a stop path.

The system must support:

- a named stop command in the registry
- a direct executor interrupt/stop mechanism

On interrupt or stop, the system must:

- stop motor outputs
- set the safety latch
- report interrupted status
- release or replace the active command slot as appropriate
- evaluate whether the queued command should run next

No command may rely on "the operator will eventually let go" as the only stop mechanism.

## Standardized Java Command Interface

Purpose: Ensure every command can be managed generically.

Every command must implement one standardized interface.

Required method:

- `execute(...)`

Optional lifecycle methods:

- `init(...)`
- `interrupt(...)`
- `finished(...)`
- `isFinished(...)`

This model may borrow heavily from FRC command-based semantics.

Intent:

- `init(...)` runs once before active execution
- `execute(...)` runs during active execution
- `isFinished(...)` reports whether the command has completed
- `finished(...)` handles normal cleanup or completion-side effects
- `interrupt(...)` handles forced stop/cleanup

If a command does not need one of the optional methods, it may ignore it or use the default interface implementation.

## Standardized Command Params

Purpose: Give every command one shared execution contract.

Every command receives one standardized params object.

The params object should contain whatever is needed for generic invocation.

Expected contents include:

- command name
- request source
- dispatch mode
- request id and timestamp
- runtime/core access
- output/report sinks
- profile-activation helpers
- safety helpers
- live-value provider
- source-loss state
- optional host-UI/session fields

Commands may ignore unused params.

The important rule is that all commands receive the same standardized interface.

## Live Value Provider

Purpose: Support axis, hold, and real-time value-driven commands without resubmitting requests every loop.

The standardized params object must contain a live-value provider.

This provider is used for:

- controller axis values
- hold state
- source-active checks
- other command-specific live input queries

Axis commands must use the same command system as all other commands.

They are not a separate special-case path.

## Standardized Results

Purpose: Separate "was this request accepted" from "what happened while executing."

The system needs two result layers.

### Immediate Dispatch Result

Returned when a request is submitted.

Examples:

- accepted and started
- accepted and queued
- rejected because busy
- rejected because queue full
- accepted and interrupted prior command
- rejected because command unknown

### Runtime Execution Result

Owned by the active/finished command execution.

Examples:

- running
- completed
- failed
- interrupted
- canceled

These are separate on purpose.

A request can be accepted immediately but still fail later during execution.

## Canonical Java Registry Table

Purpose: Make the registry the single source of truth for both execution and artifact generation.

The first pass uses a static hardcoded Java registry table.

Each row in the table should hold all metadata and policy needed for generic invocation.

At minimum, each row should support:

- command name
- group/family
- invocation kind
- source allowances
- dispatch policy
- queueability
- interruptibility
- source-loss auto-stop behavior
- whether safety-clear is required before start
- host-UI visibility metadata
- descriptive text for generated artifacts
- the Java command implementation reference

The registry should be organized so new groups can be added later without redesigning the whole system.

## Lookup Routine

Purpose: Resolve command names consistently from all sources.

The registry must provide one lookup routine that:

- takes the command name string
- finds the matching registry row
- returns the full command definition

This is the canonical lookup path for:

- controller-submitted command requests
- host-UI remote command requests
- generated Python inventory/export steps

## Unified Executor

Purpose: Centralize command lifecycle, queueing, and interrupt behavior.

The executor owns:

- active command slot
- queued command slot
- command initialization
- per-loop execution
- completion handling
- interrupt handling
- source-loss auto-stop
- transition to queued command

The executor is the only place that should make decisions about:

- whether a command starts now
- whether it is queued
- whether it interrupts another command
- whether it is rejected

## Java Ownership Structure

Purpose: Keep commands grouped and extensible without scattering behavior.

Commands should remain grouped into owner classes.

Examples:

- `RobotLocalDeviceCommands`
- `RobotLocalReportCommands`
- `RobotLocalTestCommands`
- `RobotLocalUiCommands`

New groups may be added later if needed.

The registry points at command implementations in these grouped owners.

The system should avoid lambdas.

Method references or concrete command implementation objects are acceptable.

## Host UI Integration

Purpose: Ensure host UI uses the same command model as controller-triggered execution.

Host UI robot commands must stop owning parallel semantic behavior.

That means Java-side host runtime command handling should become a thin adapter over the unified registry and executor.

The current separate behavior ownership in [BridgeUiRuntimeCommands.java](C:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiRuntimeCommands.java) should be removed or reduced to request adaptation.

The host UI path should:

- build a command request
- perform lookup through the same registry
- submit through the same executor
- receive the same standardized results

UI/session/protocol commands that are currently treated as robot commands are in scope for this unification.

## Python Generation

Purpose: Reduce duplicated handwritten command definitions on the host side.

Java is the source of truth.

Python mirrors Java.

The user must not need to write Python-side code to add or maintain a robot-local command.

Python-side command maintenance is tool-owned.

The system should generate:

- a JSON inventory exported from Java
- generated Python code derived from the Java registry

First-pass Python target:

- host UI command/button generation

First-pass non-goal:

- broad Python CLI refactor

The generated artifacts should carry enough information to let the Python host UI build command controls with minimal handwritten decisions.

The intended workflow is:

1. the user adds or edits Java-side command definitions or implementations
2. Codex or repo tooling generates the Python-side mirrored artifacts
3. the host UI updates from those generated artifacts without requiring handwritten Python command maintenance from the user

Ideal first-pass user choice:

- decide whether a command's button should be shown or hidden in the UI

## Host UI Button Inventory

Purpose: Replace handwritten command-button lists with generated command metadata.

The generated Python artifacts should support:

- building the host UI button list from the generated inventory
- carrying labels and descriptions
- honoring a `showInHostUi`-style policy
- storing UI preferences for enable/disable or show/hide behavior

The UI should include a preferences mechanism for enabling or disabling buttons.

The goal is to remove handwritten command lists like the current action sections in [bringup_ui.py](C:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py) as much as possible.

UI visibility should be controlled by Java-side metadata and generated artifacts, not by requiring the user to hand-edit Python UI code.

## Python Scope Boundary

Purpose: Keep first-pass rollout realistic.

In the first pass:

- host UI should consume generated command inventory/code
- Python CLI should not be reworked yet

This means Python CLI command-name cleanup is explicitly out of scope for the first implementation pass.

## Failure Modes

Purpose: Define expected behavior under error or contention.

The system must handle:

- unknown command name
- request rejected because active command already exists
- request rejected because queue slot is full
- request interrupted by newer command
- command fails during `init(...)`
- command fails during `execute(...)`
- command never naturally completes
- controller-originated command loses source input
- host-UI stop command interrupts active command

Expected behavior:

- failures are explicit and structured
- active slot and queued slot remain internally consistent
- interrupted commands run cleanup
- no command keeps actuating hardware after stop/interrupt cleanup

## Observability

Purpose: Make command lifecycle visible for debugging and operator feedback.

The system should report:

- command accepted/rejected/queued/interrupted
- active command name
- queued command name
- completion/failure/interrupted status
- safety-latch effects from stop/interrupt

The exact reporting surface may vary, but the lifecycle must be inspectable.

## Migration Plan

Purpose: Define how the current implementation is replaced.

First pass migration targets:

1. Replace current robot-local controller command dispatch with the unified registry and executor.
2. Replace Java host runtime command family ownership with the same unified path.
3. Keep DSL execution out of scope.
4. Generate Python host-UI inventory/code from Java registry data.
5. Remove obsolete parallel command-name tables and ownership paths.

Backward compatibility with the old internal structure is not required.

This is a full replacement of the current robot-local command path, not a compatibility shim exercise.

## Testing Strategy

Purpose: Ensure the new execution model is safe and traceable.

Testing should cover:

- registry lookup by command name
- standardized request construction
- active/queued slot behavior
- interrupt behavior
- stop command behavior
- source-loss auto-stop
- immediate dispatch result correctness
- runtime execution result correctness
- host UI and controller reaching the same executor path
- generated Python artifact correctness for host UI

Expected verification layers:

- Java unit tests for registry, executor, queueing, and interrupt behavior
- regression coverage for maintained local bundles
- focused UI-generation tests on the Python side

## Tradeoffs

Purpose: Record the main cost/benefit decisions.

Benefits:

- one obvious command source of truth
- one lifecycle model
- centralized safety handling
- easier Python mirroring
- no required user-authored Python work when adding a robot-local command
- easier to add new commands predictably

Costs:

- larger initial refactor
- command model becomes more formal than the current ad hoc loop branching
- some very simple commands may look heavier because they now live inside a standardized lifecycle

## Future Extensions

Purpose: Record likely follow-up work without forcing it into first pass.

Potential later work:

- broader generated Python support beyond host UI
- CLI adoption of generated command inventory
- dynamic registration instead of static hardcoded registry
- richer command capability metadata
- command history/audit output
- command timeout policies
- command grouping and filtering in host UI preferences

## Definition Of Done

- One static Java registry table is the canonical source of truth for robot-local commands.
- One lookup routine resolves commands by string name.
- One unified executor handles controller and host-UI command execution.
- Only one active command and one queued command are allowed.
- Interrupt/stop path is implemented and safe.
- Controller-originated commands auto-stop on source loss.
- Java host runtime command handling no longer owns a separate semantic command path.
- Generated JSON inventory and generated Python host-UI code are produced from the Java registry.
- Host UI button list is built from generated artifacts with preferences-based enable/disable control.
- The user does not need to hand-write Python code to add or maintain robot-local commands.
- DSL execution remains outside this refactor.
- Relevant Java tests and maintained regressions pass.

