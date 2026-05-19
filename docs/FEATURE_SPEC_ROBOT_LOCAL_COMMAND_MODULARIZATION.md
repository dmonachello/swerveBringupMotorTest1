# Feature Spec: Robot Local Command Modularization

## Purpose

Make robot-local binding commands easy to find, easy to modify, and easy to extend by replacing scattered string-based handling with explicit command ownership and one obvious implementation path per command.

## Scope

Includes:

- Robot-local commands triggered by controller bindings
- The command-name registry used to validate bindings
- The runtime dispatch path for those commands
- Traceability from command name to Java implementation
- Tests for command registration and dispatch coverage
- The relationship between robot-local commands and the host UI shell that remotely invokes them

Excludes:

- Python CLI command refactors
- TCP UI command protocol redesign
- NetworkTables key changes
- New controller binding syntax
- New robot behavior beyond restructuring existing command ownership

This spec is only about robot-local commands such as:

- `addMotor`
- `addAll`
- `printState`
- `printHealth`
- `printCANcoder`
- `printNTdiag`
- `printCANdiag`
- `printInputs`
- `printBindings`
- `printTestsInfo`
- `printTestsOverview`
- `printNextTest`
- `clearFaults`
- `dumpReport`
- `toggleDashboard`
- `profileToggle`
- `canSweep`
- `selectTestPrev`
- `selectTestNext`
- `toggleTest`
- `runTest`
- `runAllTests`
- `fixedSpeed25`
- `fixedSpeed50`
- `fixedSpeed75`
- `fixedSpeed100`

Important boundary:

- the host UI is primarily a GUI shell that remotely executes robot-side
  commands
- it should not evolve a separate semantic command model for this same command surface
- this spec therefore treats robot-local command ownership as the primary
  source of truth, even when commands are triggered remotely from the host

## Current Problem

The current robot-local command path is difficult to reason about because
command ownership is split across multiple places:

- command-name validation in [BindingsManager.java](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/src/main/java/frc/robot/input/BindingsManager.java)
- mixed dispatch logic in [BringupCommandRouter.java](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/src/main/java/frc/robot/BringupCommandRouter.java)
- additional behavior in [RobotV2.java](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/src/main/java/frc/robot/RobotV2.java)
- overlapping UI-side command families in:
  - [BridgeUiRuntimeCommands.java](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/src/main/java/frc/robot/BridgeUiRuntimeCommands.java)
  - [BridgeUiReportCommands.java](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/src/main/java/frc/robot/BridgeUiReportCommands.java)
  - [BridgeUiTestCommands.java](/c:/Users/dmona/swerveBringupMotorTest/swerveBringupMotorTest1/src/main/java/frc/robot/BridgeUiTestCommands.java)

Effects:

- adding a command is not a single-step change
- it is not obvious where the real behavior lives
- some commands are handled in the router while others are partially embedded in
  `RobotV2`
- the string list and the runtime implementation can drift
- tracing a command from binding entry to behavior takes too much code reading
- the host UI relationship is easy to misread, because some command-family code
  looks local to the UI even though the real product meaning is "remotely invoke
  robot behavior"

## Design Goals

- Each robot-local command has one obvious Java owner.
- Each command name is declared once in a canonical registry.
- Each command is traceable to one dedicated Java function.
- The binding validator should consume the same canonical registry used by the
  runtime dispatcher.
- The host UI should be able to present and invoke the same command surface
  without redefining command meaning.
- Adding a new command should follow a short, defined process.
- Removing or renaming a command should fail clearly if bindings still reference
  it.

## Non-Goals

- Replacing the current bindings config model
- Moving robot-local commands into Python
- Eliminating the existing UI command families in the same pass
- Rewriting `BringupRuntime` or `BringupCore` unless needed for ownership
- General Java architecture cleanup outside this command surface

## Current-State Inventory

Purpose: Record the concrete command surface that this spec is addressing.

Observed command registry source:

- `BindingsManager.validateBindings()`

Observed command execution surfaces:

- `BringupCommandRouter.applyCommon(...)`
- `RobotV2.teleopPeriodic()`
- `BridgeUi*Commands` families for UI-driven equivalents

Observed mismatch pattern:

- Some commands are cleanly routed in `BringupCommandRouter`
- Some commands still depend on special-case logic in `RobotV2`
- Some commands have parallel UI-family implementations with similar names
- The host UI path is conceptually a remote shell over robot-local commands, but
  that ownership is not explicit enough in the code structure

Example:

- `runTest` is validated in `BindingsManager`, dispatched in
  `BringupCommandRouter`, and also has UI-side handling elsewhere
- `fixedSpeed25` is validated in `BindingsManager`, but the robot-local behavior
  is embedded in `RobotV2.teleopPeriodic()` rather than owned by a dedicated
  command function

## Why These Commands Exist

Purpose: Justify the robot-local command layer as a product need, not just an
implementation detail.

These robot-resident commands are important because they are the lowest-level
operator-facing execution layer above the actual hardware and vendor APIs.

They exist to provide a direct robot-side control surface that can:

- instantiate and target devices
- trigger focused bringup actions
- drive tests and test selection
- exercise runtime behavior without requiring the full higher-level workflow
  stack
- keep the execution path close to the actual hardware wrappers, runtime, and
  vendor APIs

This matters because higher-level testing surfaces depend on this layer.

Examples of higher-level surfaces that build on or parallel this command layer:

- controller bindings
- host UI remote command execution
- CLI-driven robot actions
- bringup test execution and selection workflows

So these commands are not just "extra shortcuts." They are the base execution
layer that lets the system perform higher-level bringup and testing behavior.

## Primary Product Value

The primary reason this command layer exists is to support higher-level bringup
and testing, while still staying close to the robot-side hardware/runtime path.

That gives two major benefits:

1. Higher-level workflows have a stable robot-side execution substrate.
2. Operators and developers can still drive behavior close to the hardware and
   vendor API layer when they need focused control.

It also provides an important operational fallback:

- using these commands, tests can be run directly from a controller on the
  robot
- this bypasses the extra host and network layers
- that may be necessary when the overall system is not fully functioning yet,
  or when the remote command path is degraded during bringup

This is especially important in bringup and diagnostics work, where we often
need:

- minimal indirection
- predictable execution ownership
- a clear path from operator action to robot-side behavior

## Command Importance Tiers

Not every robot-local command is equally important.

### Tier 1: Core bringup and test-execution commands

These are the commands that most strongly justify the existence of the layer.

Examples:

- `addMotor`
- `addAll`
- `runTest`
- `runAllTests`
- `toggleTest`
- `selectTestPrev`
- `selectTestNext`
- `clearFaults`
- `canSweep`

These commands are core because they directly support bringup workflows, device
control readiness, or test execution.

### Tier 2: Secondary but useful report/inspection commands

These are useful, but they are not the primary reason this layer exists.

Examples:

- `printState`
- `printHealth`
- `printCANcoder`
- `printNTdiag`
- `printCANdiag`
- `printInputs`
- `printBindings`
- `printTestsInfo`
- `printTestsOverview`
- `printNextTest`
- `dumpReport`

These commands support visibility and inspection. They matter, but they are
supporting surfaces around the core actuation/test mission of the command layer.

### Tier 3: Convenience or narrow-purpose commands

These commands may still be valuable, but they are weaker justification for the
layer and should not dominate the architecture.

Examples:

- `fixedSpeed25`
- `fixedSpeed50`
- `fixedSpeed75`
- `fixedSpeed100`
- `toggleDashboard`
- `profileToggle`

These may remain, but they should not define the structure of the command
system. If anything is simplified or parameterized later, this tier is the most
likely place to do it.

## Proposed Direction

### Core Rule

Every robot-local command must have:

1. one canonical command identifier constant
2. one canonical registry entry
3. one dedicated Java function that implements the command behavior
4. one explicit dispatch mapping from identifier to function

For commands exposed through the host UI:

5. the UI-side surface must resolve to that same canonical command definition,
   not a separate semantic implementation

### Proposed Package Shape

Create a dedicated robot-local command area, for example:

- `src/main/java/frc/robot/commands/local/`

Suggested classes:

- `RobotLocalCommandId`
- `RobotLocalCommandRegistry`
- `RobotLocalCommandContext`
- `RobotLocalCommandDispatcher`
- one class or one method group per command family

Possible family split:

- `RobotLocalDeviceCommands`
- `RobotLocalReportCommands`
- `RobotLocalTestCommands`
- `RobotLocalDriveCommands`
- `RobotLocalUiToggleCommands`

SID_QUESTION: Do we want one class per command family, or one class per command?

Recommendation:

- use family classes with one method per command
- keep the dispatcher and registry separate

That gives cleaner file count without losing traceability.

## Canonical Command Model

### Command Id

Each command should be declared as a symbolic constant or enum value in one
place.

Preferred direction:

- `enum RobotLocalCommandId`

Each enum entry should define:

- wire/config name, for example `runTest`
- family/category, for example `tests`
- execution mode, for example `pressed` or `held`
- optional notes about side effects

Example shape:

- `ADD_MOTOR("addMotor", Family.DEVICE, TriggerMode.PRESSED)`
- `FIXED_SPEED_25("fixedSpeed25", Family.DRIVE, TriggerMode.HELD)`

This lets `BindingsManager` validate against the same registry the runtime uses.

### Command Context

A command function should not need to reach arbitrarily into `RobotV2`.

Instead, create a small context object that exposes only the dependencies needed
for robot-local commands, such as:

- `BringupRuntime`
- `BindingsManager.BindingState`
- printer/report callbacks
- diagnostics/report access
- profile toggle action
- dashboard toggle action
- fixed-speed setters or drive-request mutators

The context should be explicit enough that command code is easy to test.

## Dispatch Model

### Dispatcher Ownership

`BringupCommandRouter` should stop being a long list of string checks mixed with
behavior.

Target structure:

- `BringupCommandRouter` collects current input state
- `RobotLocalCommandDispatcher` evaluates registered commands
- each command handler method performs one command action

### Pressed vs Held

The registry should explicitly say whether a command is:

- edge-triggered
- hold-triggered
- special hybrid behavior

This matters because commands like `fixedSpeed25` are hold-driven while commands
like `runTest` are edge-triggered.

SID_QUESTION: Do we want to support mixed commands that expose both `pressed`
and `held` semantics under one name, or should those always be split?

## Host UI Relationship

Purpose: Clarify the ownership boundary between robot-local commands and the
host-side GUI shell.

The host UI is fundamentally a remote execution surface for robot-local
commands, not a separate command product.

Implications:

- the robot-local command registry should be the semantic source of truth
- host UI command-family wrappers should resolve to that same command model
- if a command exists in the GUI, bindings, and other robot-local triggers, its
  behavior should still be owned by the robot-local command layer

This does not require the first implementation pass to unify every UI class.
It does require the design to avoid locking in a second independent command
model.

## Dedicated Function Rule

Each command entry should map to one dedicated Java function.

Examples:

- `addMotor()`  
  family: device commands

- `addAll()`  
  family: device commands

- `printState()`  
  family: report commands

- `printHealth()`  
  family: report commands

- `clearFaults()`  
  family: maintenance commands

- `runTest()`  
  family: test commands

- `runAllTests()`  
  family: test commands

- `fixedSpeed25()`  
  family: drive commands

- `fixedSpeed50()`  
  family: drive commands

- `fixedSpeed75()`  
  family: drive commands

- `fixedSpeed100()`  
  family: drive commands

This does not mean every command needs its own class. It means every command
needs its own obvious method.

## Traceability Requirement

Purpose: Make code navigation obvious for maintainers.

Required trace path:

1. binding entry references command name
2. registry resolves command id
3. dispatcher resolves command handler
4. handler method performs behavior

This should be obvious in code search.

A maintainer searching for `fixedSpeed25` should quickly find:

- registry declaration
- dispatcher mapping
- implementation method

and should not need to inspect `RobotV2.teleopPeriodic()` line-by-line to infer
the behavior.

## Proposed Migration Plan

### Phase 1: Registry First

- introduce `RobotLocalCommandId`
- move the known-command list out of `BindingsManager`
- make `BindingsManager` validate against the canonical registry
- no behavior change yet

### Phase 2: Dispatcher Extraction

- introduce `RobotLocalCommandDispatcher`
- move current router string checks into explicit command methods
- keep behavior the same

### Phase 3: Remove `RobotV2` Special Cases

- extract robot-local command behavior that still lives directly in
  `RobotV2.teleopPeriodic()`
- especially fixed-speed and print-inputs logic
- leave only high-level orchestration in `RobotV2`

### Phase 4: Harden Tests

- add registry completeness tests
- add dispatcher coverage tests
- add traceability tests where useful

## Testing Requirements

Automated tests should cover:

- every registered command name is unique
- every registered command name is accepted by binding validation
- every registered command has a dispatcher mapping
- every dispatcher mapping points at a callable handler
- family-specific behavior for key commands:
  - `runTest`
  - `runAllTests`
  - `toggleTest`
  - `selectTestPrev`
  - `selectTestNext`
  - `fixedSpeed25`
  - `fixedSpeed50`
  - `fixedSpeed75`
  - `fixedSpeed100`

Manual/robot-side verification should cover:

- controller bindings still trigger the same robot behavior
- hold-style commands still behave continuously while held
- report commands still use the shared report runner
- fixed-speed commands still override drive inputs correctly

## Backward Compatibility

The command names in config should remain stable during this refactor unless a
separate compatibility plan is approved.

That means:

- `addMotor` stays `addMotor`
- `runTest` stays `runTest`
- `fixedSpeed25` stays `fixedSpeed25`

This refactor is about ownership and traceability, not operator-facing command
renames.

## Tradeoffs

### Benefits

- easier to add commands safely
- easier to find command code
- lower risk of registry/runtime drift
- cleaner tests
- thinner `RobotV2` and thinner `BringupCommandRouter`

### Costs

- more classes than the current flat string-check style
- one-time migration effort
- some commands may need small context adapters before they fit cleanly

## Open Questions

SID_QUESTION: Should command ids be a Java `enum`, or constants plus registry
records?

SID_QUESTION: Should fixed-speed commands remain four separate commands, or
become one parameterized command internally while preserving the current
external names?

SID_QUESTION: Should UI-side command families eventually consume the same
registry/dispatcher model, or should this first spec stay strictly robot-local?

SID_COMMENT: The host UI should be treated as a remote shell over robot-local
commands. Even if the first implementation pass does not fully unify UI command
families, the long-term architecture should avoid separate semantic ownership
for the same command names.

SID_QUESTION: Should `printInputs` be treated as a normal report command in the
same family as `printState` and `printHealth`, or remain closer to drive/input
logic because it reflects live stick interpretation?

## Recommendation

Start with a narrow first implementation pass:

1. canonical command registry
2. registry-backed validation in `BindingsManager`
3. dedicated dispatcher with one method per command
4. extract fixed-speed commands out of `RobotV2`

That gets the biggest clarity improvement without trying to unify every Java
command surface at once.
