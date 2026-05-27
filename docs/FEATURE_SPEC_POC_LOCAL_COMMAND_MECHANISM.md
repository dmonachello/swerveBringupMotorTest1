# PoC Local Command Mechanism

SPEC_STATUS: PROPOSED

## Purpose

Describe the current robot-local command mechanism in this repo so another project can implement the same structure and later run the same local Java command model.

## Summary

The local command mechanism is a unified robot-side command system with these properties:

- Java owns the canonical command registry.
- Every command is looked up by wire name from that registry.
- Controller-triggered and host-triggered commands use the same executor.
- Only one command may be active at a time.
- At most one additional command may be queued.
- A running command may be interrupted explicitly.
- Host UI metadata is generated from the Java registry instead of being hand-maintained separately.

The intent is to separate:

- command identity and metadata
- execution policy
- command behavior
- host/session integration

## High-Level Structure

The mechanism is built from these layers:

1. Command registry
2. Command request and execution model
3. Executor
4. Command behavior groups
5. Command host interface
6. Input/value provider
7. Host metadata generation

## Core Components

### 1. Canonical Registry

Purpose: One Java source of truth for all robot-local commands.

Primary file:

- [src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java:1)

The registry owns:

- wire command name
- logical group
- invocation kind
- whether controller invocation is allowed
- whether host UI invocation is allowed
- whether queueing is allowed
- whether source-loss auto-stop applies
- host UI visibility and labeling metadata
- the Java command implementation object

The registry also generates host-facing inventory JSON used by Python surfaces.

### 2. Command Definition Row

Purpose: One immutable definition object per command.

Primary file:

- [src/main/java/frc/robot/commands/local/RobotLocalCommandDefinition.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandDefinition.java:1)

Each definition contains:

- `wireName`
- `group`
- `invocationKind`
- `controllerAllowed`
- `hostUiAllowed`
- `queueable`
- `autoStopOnSourceLoss`
- `showInHostUi`
- `uiSection`
- `uiLabel`
- `uiDescription`
- `uiArgsJson`
- `command`

This is the contract the PoC should mirror if it wants later compatibility with generated host metadata and unified dispatch.

### 3. Command Interface

Purpose: Standard lifecycle contract for any executable local command.

Primary file:

- [src/main/java/frc/robot/commands/local/RobotLocalCommand.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommand.java:1)

Lifecycle methods:

- `init(params)` optional one-time setup
- `execute(params)` required per-step behavior
- `interrupt(params, reason)` optional forced-stop hook
- `finished(params, result)` optional terminal cleanup hook
- `isFinished(params)` optional finish predicate

This is deliberately command-based in style, but lighter than full WPILib command scheduling.

### 4. Request Object

Purpose: Normalize command submission regardless of source.

Primary file:

- [src/main/java/frc/robot/commands/local/RobotLocalCommandRequest.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandRequest.java:1)

Fields:

- command `name`
- `source`
- `dispatchMode`
- JSON `args`
- `valueProvider`
- `clientId`
- `timestampSec`
- `tcp`

The PoC should keep this separation between:

- command identity
- execution policy
- runtime arguments
- live input/value source
- transport/session metadata

### 5. Execution Result

Purpose: Return per-step and terminal command state through one common object.

Primary file:

- [src/main/java/frc/robot/commands/local/RobotLocalExecutionResult.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalExecutionResult.java:1)

States are represented separately from success:

- `RUNNING`
- `COMPLETE`
- `FAILED`
- `INTERRUPTED`
- `REJECTED`

The result also carries:

- `ok`
- `message`
- `outText`
- `outJson`

This makes the same command model usable for:

- controller commands
- host UI commands
- report commands
- config/show commands

### 6. Executor

Purpose: Enforce the one-active-command model.

Primary file:

- [src/main/java/frc/robot/commands/local/RobotLocalCommandExecutor.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandExecutor.java:1)

Current rules:

- one active command maximum
- one queued command maximum
- immediate commands reject when busy
- interrupt commands preempt the active command
- queue mode only works when the definition is queueable
- controller-originated commands may auto-stop on source loss
- immediately completed commands now release the active slot immediately during `submit(...)`

This last rule is important for host TCP behavior because multiple host commands may arrive during one robot loop.

## Dispatch Modes

Primary file:

- [src/main/java/frc/robot/commands/local/RobotLocalDispatchMode.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalDispatchMode.java:1)

Supported modes:

- `IMMEDIATE`
- `QUEUE`
- `INTERRUPT`

Meaning:

- `IMMEDIATE`: run now if idle, otherwise reject
- `QUEUE`: queue if one command is active and queue slot is free
- `INTERRUPT`: stop current command and run this one now

## Command Sources

Primary file:

- [src/main/java/frc/robot/commands/local/RobotLocalCommandSource.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandSource.java:1)

Supported sources:

- `CONTROLLER`
- `HOST_UI`

The current system uses one registry and one executor for both.

That is a key part of the structure the PoC should preserve.

## Live Value Provider

Purpose: Let long-running active commands read current inputs without resubmission every loop.

Primary file:

- [src/main/java/frc/robot/commands/local/RobotLocalValueProvider.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalValueProvider.java:1)

Current capabilities:

- determine whether the triggering source is still active
- read axis values by command name
- expose latest request args when needed

This is how hold-style and axis-driven commands work without reissuing commands each loop.

## Host Interface

Purpose: Keep command behavior decoupled from the concrete robot runtime.

Primary file:

- [src/main/java/frc/robot/commands/local/RobotLocalCommandHost.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandHost.java:1)

The host interface provides runtime services such as:

- profile activation checks
- adding devices
- printing reports
- running tests
- clearing stop latch
- applying command stop
- delegating legacy UI-family commands

This means command implementations do not directly depend on `RobotV2` or `BringupCore` internals.

For the PoC, this host boundary is one of the most important structural pieces to keep.

## Command Behavior Grouping

Purpose: Keep the registry canonical while keeping behavior files readable.

Current grouped behavior files:

- [RobotLocalRuntimeCommandGroup.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalRuntimeCommandGroup.java:1)
- [RobotLocalReportCommandGroup.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalReportCommandGroup.java:1)
- [RobotLocalTestCommandGroup.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalTestCommandGroup.java:1)
- [RobotLocalLegacyUiCommandGroup.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalLegacyUiCommandGroup.java:1)

Pattern:

- registry owns names and metadata
- grouped command files own behavior creation
- simple commands often use reusable helper classes
- complex or compatibility commands may still delegate into older command-family surfaces

## Command Families In Practice

### Runtime/System

Examples:

- `addMotor`
- `addAll`
- `clearFaults`
- `clearStopLatch`
- `canSweep`
- `toggleDashboard`
- `profileToggle`
- `stopCommand`

These are primarily backed by runtime command group logic plus host methods.

### Reports

Examples:

- `printState`
- `printHealth`
- `printCANdiag`
- `dumpReport`

These often complete immediately and mostly delegate into report emitters.

### Tests

Examples:

- `selectTestPrev`
- `toggleTest`
- `runTest`
- `runAllTests`

These may be immediate or long-running depending on the command.

### Profile / Session / Group / Show

Examples:

- `profileActivate`
- `profilesApply`
- `showDevices`
- `showProfiles`
- `uiHandshake`
- `uiDisconnect`

In the current repo, many of these still bridge through the legacy UI command families, but they still enter the same registry and executor path.

## Host Apps That Use This Mechanism

### 1. Controller Binding Layer

Purpose: Robot-side physical control input path.

How it uses the mechanism:

- detects a control becoming active
- builds a `RobotLocalCommandRequest`
- submits into the executor
- provides a live `RobotLocalValueProvider`

Important behavior:

- controller commands may auto-stop on source loss

### 2. Robot TCP UI Command Path

Purpose: Host-to-robot remote command path.

Key integration owner:

- [src/main/java/frc/robot/BridgeUiCommandHandler.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java:1)

How it uses the mechanism:

- parses incoming TCP command
- validates ingress/session rules
- builds a `RobotLocalCommandRequest`
- submits into the same executor used by controller commands
- converts `RobotLocalExecutionResult` into UI/TCP responses

Important current nuance:

- some session/protocol commands such as `uiHandshake` and `uiPollLog` now bypass the executor because they are not supposed to occupy the active robot command slot

### 3. Python Host Apps

Purpose: Build operator UI and CLI surfaces without duplicating Java command metadata manually.

Current consumers:

- Bringup Control UI
- CLI/help/bridge ops surfaces

How they use the mechanism:

- not by executing Java directly
- instead by consuming generated artifacts derived from the Java registry

Current generated outputs:

- [tools/can_nt/generated/robot_local_command_inventory.json](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/generated/robot_local_command_inventory.json:1)
- [tools/can_nt/generated/robot_local_commands_generated.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/generated/robot_local_commands_generated.py:1)

Generator:

- [tools/can_nt/scripts/generate_robot_local_command_artifacts.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/scripts/generate_robot_local_command_artifacts.py:1)

This means the PoC should preserve a path where host metadata can be generated from the canonical Java registry instead of copied manually.

## Typical Execution Flow

### Controller-Initiated

1. Controller binding becomes active.
2. Robot builds `RobotLocalCommandRequest`.
3. Executor resolves command from `RobotLocalCommandRegistry`.
4. Executor starts command if idle, interrupts, queues, or rejects based on dispatch mode.
5. Active command runs through `init -> execute -> isFinished -> finished`.
6. Source-loss auto-stop may interrupt controller-originated commands.

### Host-Initiated

1. Host sends TCP command name plus args.
2. Robot validates ingress/session policy.
3. Robot either:
   - bypasses executor for session/protocol commands, or
   - builds `RobotLocalCommandRequest` and submits through executor
4. Result is translated into ACK/OUT response payloads.

## Important Behavioral Rules To Preserve In The PoC

If the PoC wants the same structure, it should preserve these rules:

- Java registry is the canonical command inventory.
- One executor owns active/queued command policy.
- Controller and host requests use the same request model.
- Command behavior is grouped by concern, not spread across the registry itself.
- Host-facing metadata is generated from the registry.
- Long-running commands read live values from a provider instead of being resent every loop.
- Interrupt semantics are explicit, not implicit.

## What The PoC Does Not Need To Copy Exactly

The PoC does not need to duplicate every command name or every current compatibility adapter.

It only needs to preserve the architecture:

- canonical registry
- immutable command definition rows
- standardized command interface
- normalized request/result objects
- one executor
- grouped behavior sources
- host abstraction
- generated metadata path

## Minimal PoC Implementation Set

For a compatible proof of concept, implement at least:

1. `RobotLocalCommand`
2. `RobotLocalCommandDefinition`
3. `RobotLocalCommandRegistry`
4. `RobotLocalCommandRequest`
5. `RobotLocalExecutionResult`
6. `RobotLocalDispatchMode`
7. `RobotLocalCommandSource`
8. `RobotLocalValueProvider`
9. `RobotLocalCommandHost`
10. `RobotLocalCommandExecutor`

Recommended first command groups:

- runtime
- report
- test
- session

## Suggested PoC Command Set

To prove the structure, the PoC should implement a small representative set:

- one immediate runtime command
- one immediate report command
- one long-running hold/axis command
- one interrupt command
- one session command

Example minimal set:

- `addAll`
- `printState`
- `leftDrive`
- `stopCommand`
- `uiHandshake`

## Differences Between This Repo And A Clean PoC

This repo still contains some compatibility adaptation:

- legacy UI command family bridges
- session/protocol bypass rules in the TCP path
- generated host UI artifacts tied to current Python surfaces

The PoC may implement the same structure more cleanly by:

- starting with the unified registry/executor model from day one
- avoiding compatibility adapters unless needed
- separating session commands from robot-active commands from the start

## Tradeoffs

- One-active-command execution is simpler and safer, but requires explicit command classification.
- Generated host metadata reduces drift, but adds an artifact generation step.
- Grouped behavior files improve readability, but require disciplined registry ownership.
- Compatibility adapters ease migration, but are not ideal long-term architecture.

## Definition Of Done For The PoC

- commands are defined from one Java registry
- controller and host paths use the same request/result/executor structure
- command behavior is not hard-coded in scattered string-switch layers
- host metadata can be generated from the Java registry
- at least one immediate, one long-running, and one interrupt command work through the unified model

## Future Extensions

- richer command class separation for session versus actuation commands
- common host-side TCP serialization layer across all host apps
- richer queueing policies
- command introspection and active-command reporting
