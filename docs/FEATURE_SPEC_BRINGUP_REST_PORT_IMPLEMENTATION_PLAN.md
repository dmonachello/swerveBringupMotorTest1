# Bringup REST Port Implementation Plan

SPEC_STATUS: PROPOSED

## Purpose

Turn [FEATURE_SPEC_BRINGUP_PORT_FROM_REST_COMMAND_CHANNEL_POC.md](/c:/Users/dmona/swerveBringupMotorTest1-main/docs/FEATURE_SPEC_BRINGUP_PORT_FROM_REST_COMMAND_CHANNEL_POC.md) into a concrete bringup migration plan based on the current codebase.

This document is an implementation-planning artifact only. It does not authorize coding work out of order.

## Goal

Replace the current robot TCP command path with a real robot-side REST server and shared Python REST client, while preserving one canonical Java command registry and one shared robot-local executor structure for both controller and host-originated commands.

The final state is:

- no TCP command server on the robot
- no TCP command client on the host
- strict half-duplex command execution
- PoC lifecycle naming
- PoC external state naming
- bounded drained output model
- all host robot-control surfaces migrated to the shared REST client

## Inspected Current Bringup Structures

### Java Robot-Local Command Model

Inspected files:

- [src/main/java/frc/robot/commands/local/RobotLocalCommandExecutor.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandExecutor.java)
- [src/main/java/frc/robot/commands/local/RobotLocalCommand.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommand.java)
- [src/main/java/frc/robot/commands/local/RobotLocalCommandDefinition.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandDefinition.java)
- [src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java)
- [src/main/java/frc/robot/commands/local/RobotLocalCommandRequest.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalCommandRequest.java)
- [src/main/java/frc/robot/commands/local/RobotLocalExecutionState.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalExecutionState.java)
- [src/main/java/frc/robot/commands/local/RobotLocalExecutionResult.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalExecutionResult.java)
- [src/main/java/frc/robot/commands/local/RobotLocalDispatchMode.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalDispatchMode.java)
- [src/main/java/frc/robot/commands/local/RobotLocalDispatchStatus.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalDispatchStatus.java)
- [src/main/java/frc/robot/commands/local/RobotLocalControllerGateway.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalControllerGateway.java)
- [src/main/java/frc/robot/commands/local/RobotLocalValueProvider.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalValueProvider.java)

Observed current behavior:

- the registry is already canonical Java source of truth
- the executor still has one queued slot
- the executor still supports `QUEUE` and `INTERRUPT` dispatch modes
- the lifecycle interface still uses older names:
  - `init`
  - `execute`
  - `interrupt`
  - `finished`
  - `isFinished`
- external execution states still use older names:
  - `RUNNING`
  - `COMPLETE`
  - `FAILED`
  - `INTERRUPTED`
  - `REJECTED`
- `stopCommand` is implemented as a special executor case
- the request object already carries useful migration fields:
  - `clientId`
  - `timestampSec`
  - source
  - args
  - live `valueProvider`

### Java Command Families

Inspected files:

- [src/main/java/frc/robot/commands/local/RobotLocalRuntimeCommandGroup.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalRuntimeCommandGroup.java)
- [src/main/java/frc/robot/commands/local/RobotLocalReportCommandGroup.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalReportCommandGroup.java)
- [src/main/java/frc/robot/commands/local/RobotLocalTestCommandGroup.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalTestCommandGroup.java)
- [src/main/java/frc/robot/commands/local/RobotLocalLegacyUiCommandGroup.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/commands/local/RobotLocalLegacyUiCommandGroup.java)

Observed current behavior:

- runtime commands are partly direct host calls and partly legacy-UI delegation
- report commands mostly call host-side void/report helpers
- test commands mix:
  - direct executor-aware behavior
  - long-running polling against `isActiveTestRunning()`
  - legacy UI delegation for some cases
- a substantial compatibility bridge already exists in `RobotLocalLegacyUiCommandGroup`

### Java Host And TCP Ingress

Inspected files:

- [src/main/java/frc/robot/BridgeUiCommandHandler.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java)
- [src/main/java/frc/robot/BridgeUiSessionCommands.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiSessionCommands.java)
- [src/main/java/frc/robot/ui/TcpUiServer.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/ui/TcpUiServer.java)
- [docs/TCP_UI_PROTOCOL.md](/c:/Users/dmona/swerveBringupMotorTest1-main/docs/TCP_UI_PROTOCOL.md)
- [docs/TCP_UI_PROTOCOL_QUICK_REF.md](/c:/Users/dmona/swerveBringupMotorTest1-main/docs/TCP_UI_PROTOCOL_QUICK_REF.md)

Observed current behavior:

- `BridgeUiCommandHandler` is still the dominant host ingress and orchestration owner
- current TCP server is a line-delimited JSON socket server with one client connection at a time
- current session and protocol commands include:
  - `uiHandshake`
  - `uiDisconnect`
  - `uiPing`
  - `uiMonitorEnable`
  - `uiMonitorDisable`
  - `uiPollLog`
- current protocol uses:
  - `seq`
  - `ACK`
  - `OUT`
  - `sessionId`
  - state payloads embedded in responses
- current TCP host path also owns:
  - client lock ownership
  - timeout and keepalive behavior
  - duplicate-response behavior
  - protocol monitor publication
  - log drain behavior

### Python Host Transport And Surfaces

Inspected files:

- [tools/can_nt/bridge_session.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_session.py)
- [tools/can_nt/bridge_ops.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_ops.py)
- [tools/can_nt/bridge_robot_control_facade.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_robot_control_facade.py)
- [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py)
- [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py)
- [tools/can_nt/can_nt_bridge.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/can_nt_bridge.py)
- [tools/can_nt/scripts/bridge_cli_robot_non_motion_regression.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/scripts/bridge_cli_robot_non_motion_regression.py)

Observed current behavior:

- `BridgeSession` is the shared TCP client for CLI and UI
- `bridge_ops.py` is the shared command wrapper layer on top of TCP
- `BridgeCli` depends on:
  - handshake
  - ping keepalive
  - `seq`-based send and wait
  - ACK and OUT event handling
- `BringupControlUI` depends on:
  - explicit handshake/disconnect
  - `BridgeSession`
  - tracker logic built around current TCP events
- `can_nt_bridge.py` can spawn CLI/UI paths that currently depend on `BridgeSession`
- connected regressions are explicitly written against the TCP path today

## Structural Mismatches To Resolve

### Mismatch 1: Queueing Exists

Current code still contains:

- queued slot state in `RobotLocalCommandExecutor`
- `RobotLocalDispatchMode.QUEUE`
- `RobotLocalDispatchStatus.QUEUED`
- registry metadata field `queueable`

Target requirement:

- no queued slot
- no queued dispatch mode
- no queued external behavior

### Mismatch 2: Lifecycle Naming Does Not Match PoC

Current lifecycle names:

- `init`
- `interrupt`
- `finished`

Target lifecycle names:

- `initialize()`
- `execute()`
- `isFinished()`
- `end(interrupted)`

This is a structural migration across:

- command interface
- executor
- command family implementations
- any tests referencing old names

### Mismatch 3: External State Vocabulary Does Not Match PoC

Current external execution states:

- `COMPLETE`
- `INTERRUPTED`

Target external execution states:

- `FINISHED`
- `STOPPED`

This change affects:

- Java result/state model
- any JSON surfaced from host endpoints
- Python host-side status interpretation
- generated host metadata when state names are exposed

### Mismatch 4: Output Model Is Still Final-Block Or Immediate-RPC Oriented

Current command results still assume:

- per-step `message`
- optional `outText`
- optional `outJson`
- immediate RPC-style final return to host

Current reports also still rely heavily on:

- `BringupPrinter.enqueue(...)`
- UI log drain
- final or immediate text emission rather than command-owned chunk queues

Target requirement:

- status is separate from output
- output is bounded and drained incrementally through:
  - `GET /commands/{id}/output`

### Mismatch 5: Host Ingress Is TCP-Specific

Current host ingress depends on:

- `TcpUiServer`
- `BridgeSession`
- `BridgeEvent`
- `seq`
- ACK/OUT parsing
- handshake and keepalive logic

Target requirement:

- real robot-side REST server
- shared Python REST client
- all host apps migrated
- TCP command path removed

### Mismatch 6: Session/Protocol Work Is Mixed Into TCP-Specific Structures

Current control-plane behavior exists, but only in TCP-specific form:

- connect and disconnect
- session ownership
- timeout release
- ping keepalive
- log polling
- monitor enable and disable

Target requirement:

- explicit REST session endpoints
- explicit reset semantics
- explicit ownership conflict semantics
- polling logs over REST
- robot-global monitor toggles over REST

### Mismatch 7: Host Metadata Generation Is Still Coupled To Host-UI Assumptions

Current generated metadata includes host-UI-facing fields such as:

- `showInHostUi`
- `uiSection`
- `uiLabel`
- `uiDescription`
- `uiArgsJson`

These remain useful, but the host-side code generation path will need to move off the TCP command stack and onto the shared REST client model.

## Command Classification For Planning

This is the current planning classification, not the final code mapping.

### Robot-Active Runtime Commands

Examples:

- instantiate and runtime commands
- group actuation commands
- selected-device runtime changes
- manual device duty commands

These consume the active command slot.

### Robot-Active Long-Running Commands

Examples:

- `runTest`
- future hold-style or continuously evaluated commands

These consume the active command slot and need:

- explicit stop behavior
- explicit status lifecycle
- optional live value provider support

### Robot-Active Report And Output Commands

Examples:

- report-style print and dump commands
- show-style commands that should be canonical command executions rather than ad hoc RPC stubs

These consume the active command slot if they are treated as command executions rather than metadata reads.

### Robot-Active Interrupt And Stop Commands

Examples:

- `stopCommand`

These need priority semantics and must interrupt active work.

### Session Or Protocol Commands

Current examples:

- `uiHandshake`
- `uiDisconnect`
- `uiPing`
- `uiPollLog`
- `uiMonitorEnable`
- `uiMonitorDisable`

These should not be modeled as ordinary robot-active commands in the one-active-command slot.

### Legacy Compatibility Bridge Commands

Current examples:

- any command still implemented through `RobotLocalLegacyUiCommandGroup`
- any command whose actual behavior is still delegated to `BridgeUiCommandHandler.executeLegacyUiCommand(...)`

These are migration adapters and should be systematically eliminated.

## Target REST Endpoint Mapping

Confirmed first-pass target endpoints:

- `GET /health`
- `POST /session/connect`
- `POST /session/disconnect`
- `POST /session/reset`
- `POST /session/ping`
- `GET /session`
- `POST /commands`
- `GET /commands/{id}`
- `GET /commands/{id}/output`
- `POST /commands/{id}/stop`
- `GET /logs?after=<seq>`
- `POST /monitor/enable`
- `POST /monitor/disable`
- `GET /inventory/commands`

Confirmed session rules:

- one control client at a time
- second client gets `409 Conflict`
- `clientId` is required as session identity
- duplicate `requestId` replay is only within owning client
- `commandId` is globally unique across uptime
- `POST /session/reset`:
  - interrupts active command
  - clears owner
  - clears replay cache
  - resets command-id allocator
  - clears output buffers
  - clears log cursor/session sequencing state
  - leaves robot-global monitor state alone
- `POST /session/disconnect`:
  - implicitly stops active command
  - releases owner
- session timeout:
  - same effect as disconnect

## Ordered Implementation Plan

### Phase 1: Freeze The Target Contract In Codebase Docs

Purpose: Make the migration target unambiguous before editing runtime code.

Work:

- keep the porting spec authoritative
- add this implementation plan
- ensure any future work references:
  - REST endpoint set
  - session rules
  - lifecycle/state vocabulary
  - no-TCP/no-compatibility decision

Output:

- approved implementation plan and chunk list

### Phase 2: Refactor The Java Local Command Core To PoC Semantics

Purpose: Align the executor and command interface before transport replacement.

Work:

- remove executor queue slot
- remove `QUEUE` dispatch mode
- remove `QUEUED` dispatch status
- rename lifecycle methods:
  - `init` -> `initialize`
  - `interrupt` and `finished` -> `end(interrupted)`
- rename external states:
  - `COMPLETE` -> `FINISHED`
  - `INTERRUPTED` -> `STOPPED`
- preserve controller and host requests sharing one executor

Files likely touched:

- `src/main/java/frc/robot/commands/local/*`

Key risk:

- do not break controller-driven commands while changing lifecycle names

### Phase 3: Introduce Command Identity, Status Records, And Output Drain Model

Purpose: Make the robot-local executor expose the PoC lifecycle contract.

Work:

- add command-id allocation
- add request-id replay cache scoped to owning session client
- add command status snapshot model
- add bounded output chunk buffer
- add read-and-clear output drain snapshots
- add dropped-output indication

New concepts needed:

- output chunk record
- output drain snapshot
- command status record
- session replay record

Key risk:

- current `BringupPrinter` and UI log mechanisms must not be confused with command-owned output drains

### Phase 4: Build The Robot REST Server And REST Control Plane

Purpose: Replace `TcpUiServer` and TCP-specific session control.

Work:

- add robot HTTP server
- add:
  - `/health`
  - `/session/*`
  - `/commands/*`
  - `/logs`
  - `/monitor/*`
  - `/inventory/commands`
- enforce one control client
- enforce `409 Conflict` on second client
- implement timeout/disconnect/reset semantics
- map current log polling to `GET /logs?after=<seq>`

Files likely added:

- new REST server/router package under `src/main/java/frc/robot/...`

Files likely removed later:

- `src/main/java/frc/robot/ui/TcpUiServer.java`

### Phase 5: Migrate BridgeUiCommandHandler Responsibilities

Purpose: Shrink or remove the TCP-centric orchestration layer.

Work:

- identify what remains as reusable host/runtime services
- move transport-neutral services behind the new REST layer or command host boundary
- remove TCP-specific concerns:
  - ACK/OUT building
  - seq handling
  - socket callbacks
  - TCP lease handling
- preserve any still-needed host services used by command implementations

Key risk:

- `BridgeUiCommandHandler` currently mixes:
  - transport
  - session
  - command ingress
  - runtime host services
- that must be disentangled without losing command behavior

### Phase 6: Generate Host Metadata For REST Client Use

Purpose: Keep Java registry as the source of truth for host-visible command metadata.

Work:

- keep generation from `RobotLocalCommandRegistry`
- revise generated artifacts so host apps consume them through the new REST client path
- remove TCP-specific assumptions from generated consumer code

### Phase 7: Build Shared Python REST Client

Purpose: Replace `BridgeSession` with one shared host communication layer.

Work:

- add low-level REST client:
  - connect
  - disconnect
  - reset
  - ping
  - submit command
  - get command status
  - get output drain
  - stop command
  - get logs
  - monitor enable/disable
  - inventory fetch
- add blocking helpers:
  - connect-and-own-session
  - run-command-blocking
  - wait-for-terminal-status
  - drain-output-until-terminal

Files likely added:

- new Python REST client module under `tools/can_nt/`

Files likely removed later:

- `tools/can_nt/bridge_session.py`

### Phase 8: Migrate Shared Python Operations Layer

Purpose: Keep one shared host-side behavior layer above transport.

Work:

- port `bridge_ops.py` from TCP send wrappers to REST client wrappers
- port `bridge_robot_control_facade.py` to REST status/output model
- preserve common code ownership of host robot-control semantics

### Phase 9: Migrate Host Apps And Scripts

Purpose: Move every host robot-control surface to REST.

Work:

- migrate CLI
- migrate Bringup UI
- migrate topology/live host actions
- migrate connected regression scripts
- migrate automation entrypoints in `can_nt_bridge.py`

Files likely touched:

- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/bringup_ui.py`
- `tools/can_topology/live_topology_view.py`
- `tools/can_nt/scripts/*connected*`
- any direct `BridgeSession` callers

### Phase 10: Delete TCP Command Path And Clean Up Docs

Purpose: Finish the migration cleanly.

Work:

- delete `TcpUiServer`
- delete Python TCP session client
- delete TCP command protocol docs or replace them with REST docs
- update architecture and user guides
- update regression docs and connected-test assumptions

## Concrete Issue And Chunk List

### Chunk 1: Inventory And Contract Freeze

- finalize plan docs
- create a current-state inventory appendix if needed
- list every TCP caller to be migrated

### Chunk 2: Remove Queueing And Rename Lifecycle Core

- remove executor queue support
- rename lifecycle methods
- rename external states
- update affected tests

### Chunk 3: Add Command Record Model

- add command-id model
- add request replay model
- add status snapshot model
- add output chunk buffer and drain snapshot model

### Chunk 4: Add Robot REST Server Skeleton

- add HTTP server
- add `GET /health`
- add `POST /session/connect`
- add `POST /session/disconnect`
- add `POST /session/reset`
- add `POST /session/ping`
- add `GET /session`

### Chunk 5: Add Command REST Endpoints

- add `POST /commands`
- add `GET /commands/{id}`
- add `GET /commands/{id}/output`
- add `POST /commands/{id}/stop`
- wire them to the executor and command record model

### Chunk 6: Add Log, Monitor, And Inventory Endpoints

- add `GET /logs?after=<seq>`
- add `POST /monitor/enable`
- add `POST /monitor/disable`
- add `GET /inventory/commands`

### Chunk 7: Extract Transport-Neutral Robot Host Services

- reduce `BridgeUiCommandHandler` to reusable runtime services or replace it
- remove TCP-specific responsibilities from robot-side command ingress

### Chunk 8: Build Shared Python REST Client

- low-level non-blocking API
- blocking convenience API
- session ownership handling
- timeout and reset handling

### Chunk 9: Port Shared Python Operations

- migrate `bridge_ops.py`
- migrate `bridge_robot_control_facade.py`
- keep one common host behavior layer

### Chunk 10: Port CLI

- replace `BridgeSession` usage
- replace ACK/OUT waiting with REST status/output polling
- replace ping keepalive with REST session or ping semantics

### Chunk 11: Port Bringup UI

- replace handshake/disconnect/session tracker logic
- replace command tracker plumbing
- migrate manual motor duty and other runtime actions to REST
- migrate log polling to `GET /logs`

### Chunk 12: Port Topology/Live Host Actions

- move any direct robot command calls to shared REST client
- remove transport duplication

### Chunk 13: Port Connected Regressions And Automation Entry Points

- migrate connected regression scripts
- migrate `can_nt_bridge.py` robot-control entrypoints
- update connected test assumptions from TCP to REST

### Chunk 14: Delete TCP Command Path

- delete Java TCP server
- delete Python TCP client
- remove TCP command protocol docs
- remove dead tests

### Chunk 15: Full Validation And Cleanup

- run Java tests
- run Python unit tests
- run CLI regressions
- run connected robot non-motion regression via REST
- run manual Bringup UI smoke test

## First End-To-End Proof Requirement

Per the locked decision for this planning pass, the first proof command required through the new structure is only:

- one immediate read command end-to-end

Recommended first proof command:

- current `showDevices`

Reason:

- already widely used by CLI and UI
- read-only
- exercises:
  - session ownership
  - command submission
  - command status
  - output retrieval
  - host client migration

This proof should be completed before expanding to:

- long-running command proof
- stop-path proof
- output-heavy command proof

## Risks And Planning Notes

### Risk: BridgeUiCommandHandler Is Too Central

It currently mixes:

- session state
- transport state
- host command ingress
- reusable runtime host services
- output and monitoring

The plan should assume deliberate extraction rather than small cosmetic edits.

### Risk: Report Commands May Not Fit The New Output Model Without Real Refactoring

Many current report paths are optimized for:

- `BringupPrinter`
- UI log mirroring
- single final or immediate text return

Those will need command-owned output semantics, not just transport replacement.

### Risk: Controller Path Must Not Regress

Controller commands stay local, but they must share the same executor and command structure after migration. The lifecycle rename and state rename work must not silently break those flows.

### Risk: Host Code Is Widely Coupled To BridgeSession

`BridgeSession` is used directly or indirectly across:

- CLI
- UI
- regression scripts
- automation helpers

The REST client migration must replace shared transport centrally rather than one-off per surface.

## Validation Gates

Required validation gates for the finished migration:

- `.\gradlew.bat test`
- relevant Python unit tests
- CLI regressions updated and passing
- at least one connected robot non-motion regression through REST
- manual Bringup UI smoke test

## Definition Of Planning Done

This planning pass is done when:

- the inspected current-state inventory is captured
- the structural mismatches are explicitly listed
- the endpoint and session contract is explicit
- the migration phases are ordered
- the issue and chunk list is concrete enough to execute without guessing
- the first end-to-end proof command is identified
