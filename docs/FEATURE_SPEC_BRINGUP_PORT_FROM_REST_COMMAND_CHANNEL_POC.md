# Bringup Porting Spec From REST Command Channel PoC

SPEC_STATUS: PROPOSED

## Purpose

Provide the source specification for porting the REST Command Channel PoC architecture into the bringup project.

This document is for another engineer or coding agent working inside the bringup repository who needs enough context to produce a concrete implementation plan without re-discovering the PoC design decisions.

This document is not a line-by-line port guide. It is a structural and behavioral specification for what the bringup project should adopt from the PoC.

## Porting Goal

Port the PoC command/control mechanism into the bringup project so that:

- the bringup project uses the same robot-local command lifecycle and external command states
- the bringup project uses strict half-duplex command execution
- the bringup project can expose the same REST-style command lifecycle contract
- the bringup project preserves its canonical Java command registry model
- the port requires only caller and integration changes rather than deep redesign of the new command mechanism

## Source Of Truth

The source architecture is the PoC in:

- `C:\Users\dmona\robotREST_PoC\robot_REST_PoC\docs\poc-requirements.md`
- `C:\Users\dmona\robotREST_PoC\robot_REST_PoC\docs\poc-wire-contract.md`
- `C:\Users\dmona\robotREST_PoC\robot_REST_PoC\docs\poc-robot-implementation-design.md`
- `C:\Users\dmona\robotREST_PoC\robot_REST_PoC\docs\poc-host-implementation-design.md`
- `C:\Users\dmona\robotREST_PoC\robot_REST_PoC\docs\poc-bringup-alignment-refactor-plan.md`

The current PoC implementation also matters, especially:

- `C:\Users\dmona\robotREST_PoC\robot_REST_PoC\src\main\java\frc\robot\diag\command\RobotLocalCommandExecutor.java`
- `C:\Users\dmona\robotREST_PoC\robot_REST_PoC\src\main\java\frc\robot\diag\command\RobotLocalCommandRegistry.java`
- `C:\Users\dmona\robotREST_PoC\robot_REST_PoC\src\main\java\frc\robot\diag\comm\DiagHttpRouter.java`
- `C:\Users\dmona\robotREST_PoC\robot_REST_PoC\src\main\java\frc\robot\diag\comm\DiagHttpServer.java`

Bringup-local compatibility surfaces that must be inspected during planning include:

- [docs/TCP_UI_PROTOCOL.md](/c:/Users/dmona/swerveBringupMotorTest1-main/docs/TCP_UI_PROTOCOL.md)
- [docs/TCP_UI_PROTOCOL_QUICK_REF.md](/c:/Users/dmona/swerveBringupMotorTest1-main/docs/TCP_UI_PROTOCOL_QUICK_REF.md)
- [docs/FEATURE_SPEC_HOST_TCP_COMMAND_SERIALIZATION_LAYER.md](/c:/Users/dmona/swerveBringupMotorTest1-main/docs/FEATURE_SPEC_HOST_TCP_COMMAND_SERIALIZATION_LAYER.md)
- [docs/FEATURE_SPEC_POC_LOCAL_COMMAND_MECHANISM.md](/c:/Users/dmona/swerveBringupMotorTest1-main/docs/FEATURE_SPEC_POC_LOCAL_COMMAND_MECHANISM.md)

## Locked Decisions For Bringup

These decisions are already made and should not be re-opened during planning unless explicitly directed by the user:

- bringup adopts a real REST-style server on the robot
- REST becomes the canonical and only host-to-robot command transport for this mechanism
- no backward compatibility is required for the current TCP command channel
- existing host apps will be migrated to use the shared REST client layer
- queued commands are eliminated
- execution is strict half-duplex
- only one active command may exist at a time
- the next command is rejected until the current command reaches a terminal state
- bringup adopts the PoC lifecycle method naming:
  - `initialize()`
  - `execute()`
  - `isFinished()`
  - `end(interrupted)`
- bringup adopts the PoC and REST lifecycle states:
  - `ACCEPTED`
  - `RUNNING`
  - `FINISHED`
  - `FAILED`
  - `STOPPED`
  - `REJECTED`
  - `UNKNOWN`
- robot output must not be accumulated indefinitely for later one-shot return
- command output must be drained incrementally through:
  - `GET /commands/{id}/output`

## Behavioral Contract To Preserve

### Command Submission

- `POST /commands` returns immediately
- accepted commands return `ACCEPTED`
- rejected commands return `REJECTED`
- duplicate submission retries with the same `requestId` must replay the original submission result

### Command Execution

- robot-side command execution is non-blocking
- execution advances incrementally across repeated robot loop passes
- `initialize()` runs once at start
- `execute()` runs once per service loop while active
- `isFinished()` is checked once per service loop after `execute()`
- `end(interrupted)` runs once at terminal completion

### Stop Behavior

- stop is explicit
- stop is requested through `POST /commands/{id}/stop`
- a stop request does not fake instant completion
- the observed state may temporarily remain `RUNNING` with stop requested
- terminal stopped state becomes `STOPPED`

### Output Behavior

- output is separate from lifecycle status
- output is ephemeral
- output is drained through `GET /commands/{id}/output`
- drain is read-and-clear
- the robot may keep only a bounded output queue
- output queue overflow should be detectable by the client

### Unknown Command Behavior

- unknown `commandId` for status or output returns `UNKNOWN`
- unknown `commandId` for stop returns `UNKNOWN`

## REST Control-Plane Requirements

The PoC lifecycle is being adopted for robot-active work, and bringup will expose a real REST server on the robot.

The planning work must explicitly define REST equivalents for current host-to-robot control-plane responsibilities such as:

- session establishment and teardown
- liveness and connectivity checks
- stop and recovery behavior
- log polling or log retrieval
- monitor enable and disable behavior
- health and observability endpoints
- connection and client tracking where still required

The planning work must explicitly preserve the separation between:

- robot-active commands that consume the one active command slot
- session or protocol operations that are part of the REST control plane rather than robot-active work

`stopCommand` must retain priority interrupt behavior and must not be blocked behind normal session establishment in a way that can deadlock recovery.

Because backward compatibility is not required, the old TCP command-wire semantics do not constrain the new design. Planning should not preserve TCP-specific concepts such as:

- `ACK` and `OUT` response framing
- `seq` request-response matching
- cached duplicate-response replay by client and sequence
- current TCP-specific status, code, and message shapes

Those concerns should be replaced by the PoC-style REST request, command-id, status, stop, and output-drain contract.

## Architectural Shape Bringup Should Adopt

The bringup implementation plan should target this structure:

1. canonical Java command registry
2. immutable command definition rows
3. normalized local command request object
4. one active-command executor with no queue
5. robot-local command host abstraction boundary
6. optional live value provider for long-running source-driven commands
7. REST adapter layer over the local command model
8. output drain endpoint
9. generated host metadata from the Java registry

## Required Structural Porting Changes In Bringup

The implementation plan in the bringup project should account for these specific deltas from the older bringup structure.

### Remove Queueing

The current bringup design historically allowed:

- one active command
- at most one queued command

That must be removed.

Target behavior:

- one active command only
- new command while active becomes `REJECTED` unless explicit interrupt semantics are supported for that command class

### Adopt PoC Lifecycle Names

Any bringup-local command interface using older names such as:

- `init`
- `finished`
- `interrupt`

should be updated or adapted to the PoC names:

- `initialize()`
- `execute()`
- `isFinished()`
- `end(interrupted)`

The implementation plan should identify:

- where the old lifecycle names exist
- whether direct renaming is safe
- where adapters are temporarily required

### Adopt PoC External States

Older bringup result-state vocabulary such as:

- `COMPLETE`
- `INTERRUPTED`

should be replaced or mapped to:

- `FINISHED`
- `STOPPED`

The port plan should define:

- where these states are currently modeled
- what code paths, UI layers, and host tooling assume the old names

### Separate Status From Output

Any command or report mechanism that currently assumes final retained text output should be refactored so that:

- status remains available from command status endpoints
- output is drained incrementally from `GET /commands/{id}/output`

The port plan must identify:

- which existing commands currently emit report text
- whether they can emit chunked output instead
- where the bringup host surfaces currently expect final aggregated text

## Target REST Contract For Bringup

The bringup implementation plan should assume these endpoints:

- `GET /health`
- `POST /commands`
- `GET /commands/{id}`
- `GET /commands/{id}/output`
- `POST /commands/{id}/stop`

Optional helper endpoints:

- command inventory endpoint derived from registry metadata
- session or liveness endpoints if needed by the final REST control-plane design

## Internal Bringup Model To Aim For

The bringup project does not need to copy PoC filenames exactly, but it should converge on equivalent concepts:

- `RobotLocalCommandDefinition`
- `RobotLocalCommandRegistry`
- `RobotLocalCommandRequest`
- `RobotLocalCommandSource`
- `RobotLocalDispatchMode`
- `RobotLocalCommandHost`
- `RobotLocalValueProvider`
- `RobotLocalCommandExecutor`
- output chunk record
- output drain snapshot

## Existing Bringup Ideas That Still Matter

The following existing bringup concepts are still important and should be preserved where they fit:

- canonical Java registry
- grouped command behavior files
- unified executor for controller and host requests
- host metadata generation from the registry
- host abstraction boundary
- live value provider for long-running source-driven commands

The port should preserve those strengths while changing:

- queueing policy
- lifecycle naming
- external state naming
- output delivery semantics

## Porting Existing Bringup Commands

The implementation plan in the bringup project must explicitly address how the existing bringup commands will be migrated into the new structure.

The goal is not to rewrite every command at once. The goal is to classify each existing command correctly and move it into the new architecture with minimal disruption.

### Command Classification Rules

Each existing bringup command should be classified into one of these categories:

- robot-active runtime command
- robot-active long-running command
- robot-active report or output command
- robot-active interrupt or stop command
- session or protocol command
- legacy compatibility bridge command

This classification is important because not all existing commands should consume the one active robot command slot.

### Commands That Should Use The Active Command Slot

Commands should go through the unified active-command executor if they:

- change robot runtime behavior
- run over multiple loop iterations
- need explicit stop or interruption behavior
- represent operator-triggered runtime actions
- represent report or test actions that should be serialized with other robot-active work

Typical examples include:

- runtime or system commands
- long-running test commands
- actuation-style commands
- report commands that should run through the unified lifecycle

### Commands That Should Not Use The Active Command Slot

Commands should remain outside the active command slot if they are really session or protocol operations rather than robot-active work.

Typical examples include:

- handshake and setup commands
- disconnect and teardown commands
- protocol polling commands
- metadata and inventory retrieval commands
- other control-plane commands that should not block robot-active execution

The bringup implementation plan should identify which current commands fall into this category and preserve that separation explicitly.

### Lifecycle Mapping Rules For Existing Commands

Existing bringup commands using older lifecycle names should be migrated to the PoC lifecycle naming.

Target lifecycle:

- `initialize()`
- `execute()`
- `isFinished()`
- `end(interrupted)`

Mapping guidance:

- old `init(...)` logic should move to `initialize()`
- old per-step execution logic should remain in `execute()`
- old finish predicate logic should move to `isFinished()`
- old interruption and completion cleanup should be reconciled into `end(interrupted)`

The bringup implementation plan should identify commands where:

- interruption cleanup and successful completion cleanup are currently separate
- direct renaming is not enough
- an adapter layer is temporarily safer than an immediate rewrite

### Output Migration Rules For Existing Commands

Any existing bringup command that currently emits text or reports should be reviewed for output behavior.

If it currently assumes:

- accumulated final output
- single final text block
- retained report text after completion

then it must be adapted to the new model:

- emit output chunks as they are produced
- surface them through `GET /commands/{id}/output`
- do not rely on indefinite robot-side retention

The implementation plan should identify:

- which existing commands are report-heavy
- which ones need chunked output emission
- which host surfaces currently assume final retained text

### Live Value Provider Migration Rules

Existing hold-style, axis-driven, or source-live commands should not be repeatedly resubmitted every loop.

They should instead use the live value provider pattern.

The implementation plan should identify:

- which existing controller-driven commands rely on live values
- how those values are currently sourced
- how to map them into the unified value-provider abstraction

### Temporary Compatibility Adapter Guidance

It is acceptable for the bringup implementation plan to use temporary adapters while migrating existing commands.

Examples:

- wrappers that adapt old lifecycle names to the new interface
- bridge definitions that let old command implementations register in the new registry
- compatibility handlers for commands that still delegate into older command-family code

However, the plan should clearly distinguish:

- temporary migration adapters
- desired steady-state architecture

### Minimum Migration Output Expected From Bringup Planning

The implementation plan produced in the bringup project should include:

- a list of existing command families
- a classification of each family into the categories above
- identification of which commands consume the active slot
- identification of which commands are session or protocol commands
- identification of which commands need output-drain adaptation
- identification of which commands need value-provider support
- identification of which commands can be directly ported versus temporarily adapted

## What Another Codex Should Inspect In Bringup

When producing the implementation plan inside the bringup project, Codex should inspect at least:

- current local command interface and lifecycle names
- current command definition and registry structures
- current executor policy and any queue handling
- current host UI and TCP command ingress path, to identify what must move to REST
- current controller-triggered command ingress path
- current result-state vocabulary
- current output and report emission model
- current metadata generation path for Python surfaces
- places where session or protocol commands bypass the executor

## Questions The Bringup Plan Must Answer

The implementation plan produced in the bringup project should explicitly answer:

1. Where does queueing exist now, and how will it be removed cleanly?
2. Where are older lifecycle method names defined, and how will they be migrated?
3. Where are old external states assumed by host UI, TCP, and Python surfaces?
4. Which commands currently depend on retained final output rather than drained chunk output?
5. Which commands should remain robot-active commands and which should be session or protocol commands outside the active slot?
6. How will controller and host requests continue to share one executor after the port?
7. How will output chunks be represented, drained, and surfaced to host tools?
8. How will the registry continue to generate host-facing metadata after the port?
9. Which existing TCP control-plane behaviors move to REST, and what are their REST equivalents?

## Output Endpoint Requirements

The bringup implementation plan should include an explicit design for `GET /commands/{id}/output`.

Required properties:

- read-and-clear semantics
- bounded buffering on robot
- sequence numbers on chunks
- dropped-output indication if overflow occurs

Recommended response shape:

- `commandId`
- `status`
- `nextSequence`
- `dropped`
- `chunks`
- `reason`

## Porting Priority Order

The bringup implementation plan should generally prefer this order:

1. inspect current bringup structures and map them to PoC concepts
2. remove queueing assumptions
3. align lifecycle names
4. align external state vocabulary
5. add or adapt executor to strict half-duplex behavior
6. add output-drain model
7. add the robot REST server and control-plane endpoints
8. adapt host and controller ingress paths
8. adapt metadata generation
9. adapt host-side tools and UI surfaces to the shared REST client

## Definition Of Done For The Bringup Port

The implementation plan should target this end state:

- one canonical Java command registry
- one active command only
- no queued command support
- real REST server on the robot
- PoC lifecycle naming adopted
- PoC and REST lifecycle states adopted
- host and controller requests still use the same executor structure
- output drains through `GET /commands/{id}/output`
- host metadata still generated from the Java registry
- existing host apps use the shared REST client layer rather than the old TCP command path
- at least one immediate command, one long-running command, one interrupt or stop path, and one output-producing command work through the new structure

## Planning Instruction For Another Codex

If you are Codex inside the bringup project, do not start by implementing.

First:

- inspect the current command registry, executor, request and result model, and host ingress layers
- map each current concept to the required PoC-aligned target architecture
- identify structural mismatches
- produce an implementation plan ordered to preserve bringup functionality while migrating incrementally

The goal is not to clone filenames from the PoC. The goal is to port the architecture and behavioral contract into the bringup codebase with minimal disruption to its existing responsibilities.
