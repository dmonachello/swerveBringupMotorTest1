# Spec: Complete NetworkTables Removal

SPEC_STATUS: PROPOSED

## Purpose

Define the end-state architecture and migration plan to remove NetworkTables from the bringup system entirely, including old tools, legacy command paths, protocol monitor surfaces, and robot-side consumers of PC-published NT data.

This spec is intentionally broader than "move the UI off NT." The goal is zero operational dependence on NT anywhere in the host or robot bringup workflow.

## Scope

Purpose: Define what this spec changes and what it does not.

In scope:

- host-to-robot UI command transport
- robot-to-host runtime state publication used by UI/CLI
- tests state publication used by UI/CLI
- protocol monitor surfaces
- PC CAN diagnostics publication currently written to `bringup/diag/...`
- robot-side consumers of NT-published PC diagnostics
- legacy NT-based helper tools and compatibility paths
- documentation and operator guidance that currently reference NT as an active transport

Out of scope:

- FRC dashboard usage unrelated to bringup workflows
- generic WPILib NT usage outside bringup unless it blocks removal
- CAN transport itself
- changing bringup operator-visible services or workflows unless explicitly required by transport replacement

## Problem Statement

Purpose: Explain why complete NT removal is being proposed.

The current system uses NT for more than status display:

- legacy host-to-robot command transport under `bringup/ui/cmd/...`
- command acknowledgements and outputs under `bringup/ui/ack/...` and `bringup/ui/out/...`
- protocol monitor state under `bringup/ui_tcp/...`
- robot runtime and tests state consumed by host UI/CLI
- PC-side CAN diagnostics published under `bringup/diag/...`
- robot-side diagnostics and probe logic that consume those PC-published keys

This creates several problems:

- shared mutable keyspace instead of explicit request/response contracts
- stale-value ambiguity
- mixed transport and application semantics
- hidden coupling between host and robot code
- difficult session ownership reasoning
- hard-to-audit old tools and compatibility writers

The system already has a stronger architectural direction:

- REST-style command/session transport
- explicit command lifecycle
- explicit JSON payloads
- shared host-side services rather than key-by-key interpretation

This spec completes that direction by removing NT entirely.

## Goals

Purpose: Define the required outcomes.

- No bringup host or robot code depends on NT at runtime.
- No supported tool writes or reads bringup keys through NT.
- Existing user-visible bringup services and workflows remain available.
- Host/robot command, session, state, tests, diagnostics, and logs all use explicit transport contracts.
- Old NT-based tools are either removed or replaced by REST-based equivalents.
- Robot-side diagnostics still fail soft when the PC CAN tool is absent.

## Non-Goals

Purpose: Avoid accidental scope creep.

- Replacing all uses of HTTP polling with WebSockets in the first pass.
- Redesigning DSL semantics, lifecycle semantics, or group semantics.
- Changing operator-facing command names unless required by removing NT-only implementation details.
- Preserving backward compatibility with NT-based bringup tools indefinitely.

## Current NT Usage Inventory

Purpose: State what must be removed.

### Legacy UI Command Transport

Current keys under `bringup/ui/...` are used as a request/response protocol:

- host writes:
  - `cmd/name`
  - `cmd/args/json`
  - `cmd/ts`
  - `cmd/seq`
  - `cmd/clientId` where applicable
- robot publishes:
  - `ack/seq`
  - `ack/status`
  - `ack/code`
  - `ack/codeText`
  - `ack/message`
  - `ack/name`
  - `ack/ts`
  - `out/seq`
  - `out/name`
  - `out/text`
  - `out/ts`
  - `out/json`
  - `state/lastAckSeq`
  - `state/lastAckMs`
  - `state/sessionId`
  - `state/protocolVersion`
  - `state/activeClientId`

### Protocol Monitor Surfaces

Current keys under `bringup/ui_tcp/...` expose protocol-monitor state:

- `enabled`
- `connected`
- `lastSeq`
- `lastName`
- `lastStatus`
- `lastMessage`
- `activeClientId`

### Robot Runtime And Tests State

Current keys under `bringup/ui/state/...` and `bringup/tests/...` are consumed by host UI/CLI for:

- robot enabled / disabled / e-stop / mode
- selected profile
- active runtime profile
- selected test
- active test
- run state / run message / run result
- test rows and required devices

### PC CAN Diagnostics Publication

Current keys under `bringup/diag/...` are written by the PC tool and read by robot diagnostics/probe logic:

- per-device presence and ages
- CAN PC health
- console evidence counters and events
- optional summary JSON

### Legacy Tools To Remove Or Replace

This spec explicitly covers old NT-based tools and compatibility layers, including:

- NT command writers in Python
- NT command readers/bridges on the robot
- NT protocol monitor commands
- any CLI or UI mode that assumes `bringup/ui/...` command mutation
- any helper docs or scripts that tell users to inspect NT keys for bringup control

## Source Of Truth

Purpose: Define the replacement transport model.

The system after migration has two explicit transport families.

### 1. Host <-> Robot Bringup Control Plane

Transport:

- REST for command/session endpoints
- either REST polling or SSE/WebSocket for pushed state and logs

Responsibilities:

- session establishment and ownership
- command submission
- command status/result
- output drain
- runtime state
- tests state
- protocol monitor / transport diagnostics

### 2. PC CAN Tool -> Host/Robot Diagnostics Data Plane

Transport:

- HTTP JSON endpoint exposed by the PC tool
- optional SSE/WebSocket stream for updates in a later phase

Responsibilities:

- per-device diagnostics snapshots
- PC capture health
- console evidence events and counters
- additive diagnostic summaries

The robot bringup code consumes this data through an explicit adapter, not directly from NT.

## End-State Architecture

Purpose: Describe the target architecture after NT is gone.

### Host UI And CLI

All host bringup surfaces use shared transport/services for:

- `session_service`
- `command_service`
- `runtime_state_service`
- `tests_state_service`
- `protocol_monitor_service`
- `pc_diagnostics_service`

No host surface reads robot state from NT directly.

No host surface writes commands by mutating NT keys.

### Robot

The robot exposes:

- REST session endpoints
- REST command submit/status/output endpoints
- REST runtime-state endpoint
- REST tests-state endpoint
- REST lifecycle-state endpoint
- REST protocol-monitor endpoint

Robot diagnostics/probe code does not read NT for PC diagnostics. It reads through a transport-neutral provider interface backed by HTTP snapshot fetches.

### PC CAN Tool

The PC CAN tool exposes:

- local UI if requested
- HTTP snapshot endpoints for diagnostics data
- optional summary endpoints
- optional evidence/event endpoints

The PC CAN tool does not publish bringup state into NT.

## Required Replacement Contracts

Purpose: Make the replacement explicit.

### Session

Required endpoints:

- `POST /ui/connect`
- `POST /ui/disconnect`
- `POST /ui/ping`
- `POST /ui/monitor`
- `GET /ui/session`

Required fields:

- `clientId`
- `sessionId`
- `protocolVersion`
- `lastAckSeq`
- `minNextSeq`
- ownership status

### Commands

Required endpoints:

- `POST /commands`
- `GET /commands/{id}`
- `GET /commands/{id}/output`
- `POST /commands/{id}/stop`

Required behavior:

- explicit request/response semantics
- no NT ACK/OUT mirror required
- output drain is read-and-clear

### Runtime State

Required endpoint:

- `GET /runtime/state`

Must include at minimum:

- robot enabled
- robot estopped
- robot mode
- selected profile
- active runtime profile
- runtimeActive
- controlledLifecycleActive
- groups
- devices
- selected device

### Tests State

Required endpoint:

- `GET /tests/state`

Must include at minimum:

- selected test
- active test
- run state
- run result
- run message
- row metadata including required devices and runnable status

### Protocol Monitor

Required endpoint:

- `GET /ui/protocol-monitor`

Must replace current `bringup/ui_tcp/...` visibility with explicit JSON fields.

### PC Diagnostics Snapshot

Required endpoint:

- `GET /pc-diagnostics/snapshot`

Must cover the same semantic payloads currently consumed from `bringup/diag/...`:

- PC open/heartbeat/frames/errors/age
- per-device presence and traffic ages
- console evidence counters and active events
- optional summary JSON

## Removal Rules

Purpose: Prevent accidental partial migration.

The following are mandatory completion rules.

- No supported host UI path may read robot state from NT.
- No supported host UI path may write commands to NT.
- No supported CLI path may read robot state from NT.
- No supported CLI path may write commands to NT.
- No supported robot code path may publish bringup control-plane state only to NT.
- No supported robot code path may read PC bringup diagnostics only from NT.
- No old NT compatibility shims remain enabled by default.
- Any temporary compatibility adapter must be explicitly documented, feature-flagged, and deleted before this spec is considered complete.

## Migration Phases

Purpose: Provide an implementation order that keeps the system working.

### Phase 1: Remove Legacy NT Command Transport

Replace entirely:

- `bringup/ui/cmd/...`
- `bringup/ui/ack/...`
- `bringup/ui/out/...`
- `bringup/ui/state/...` as command/session protocol metadata
- `bringup/ui_tcp/...`

Actions:

- host UI and CLI use REST session/command transport only
- robot command handler no longer polls NT command keys
- protocol monitor becomes REST-backed
- remove `uiMonitorEnable` / `uiMonitorDisable` as NT-only concepts or remap them to REST monitor control

### Phase 2: Move Host Runtime And Tests State Off NT

Replace:

- host reads of `bringup/ui/state/...`
- host reads of `bringup/tests/...`

Actions:

- add shared REST state readers
- move UI and CLI gating/state logic to those readers
- remove NT state read code from host bringup surfaces

### Phase 3: Move PC Diagnostics Off NT

Replace:

- `bringup/diag/...` writer path in the PC tool
- robot-side readers of `bringup/diag/...`

Actions:

- define HTTP snapshot schema
- implement PC diagnostics HTTP server surfaces
- add robot-side diagnostics data provider abstraction
- migrate `DiagnosticsReporter` and `ActiveDevicePresenceProbe`

### Phase 4: Remove Old Tools And Compatibility Layers

Delete or replace:

- NT-based command send helpers
- NT-based protocol monitor helpers
- NT bringup docs that describe operational use
- old scripts whose only purpose is NT transport interaction

### Phase 5: Hard Removal

After all consumers are migrated:

- delete NT contract docs that no longer apply to bringup transport
- remove NT key constants and unused table setup
- remove NT inventory/reporting paths that exist only for bringup control flow

## Detailed File-Level Direction

Purpose: Point implementation planning at the main code areas.

### Host Python

Primary expected changes:

- [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerve3/tools/can_nt/bringup_ui.py)
- [tools/can_nt/bridge_session.py](/c:/Users/dmona/swerve3/tools/can_nt/bridge_session.py)
- [tools/can_nt/bridge_ops.py](/c:/Users/dmona/swerve3/tools/can_nt/bridge_ops.py)
- [tools/can_nt/can_nt_bridge.py](/c:/Users/dmona/swerve3/tools/can_nt/can_nt_bridge.py)
- any host CLI or helper reading `bringup/ui` or `bringup/tests` via NT

### Robot Java

Primary expected changes:

- [src/main/java/frc/robot/BridgeUiCommandHandler.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/BridgeUiCommandHandler.java)
- [src/main/java/frc/robot/BridgeUiOutputFacade.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/BridgeUiOutputFacade.java)
- [src/main/java/frc/robot/BridgeUiSessionCommands.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/BridgeUiSessionCommands.java)
- [src/main/java/frc/robot/DiagnosticsReporter.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/DiagnosticsReporter.java)
- [src/main/java/frc/robot/diag/probe/ActiveDevicePresenceProbe.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/diag/probe/ActiveDevicePresenceProbe.java)
- [src/main/java/frc/robot/RobotV2.java](/c:/Users/dmona/swerve3/src/main/java/frc/robot/RobotV2.java) where NT tables are initialized for bringup control flow

### Documentation

Primary expected changes:

- [docs/NT_CONTRACT.md](/c:/Users/dmona/swerve3/docs/NT_CONTRACT.md)
- [docs/TCP_UI_PROTOCOL.md](/c:/Users/dmona/swerve3/docs/TCP_UI_PROTOCOL.md)
- [docs/TCP_UI_PROTOCOL_QUICK_REF.md](/c:/Users/dmona/swerve3/docs/TCP_UI_PROTOCOL_QUICK_REF.md)
- user guides that mention NT as required runtime transport

## Compatibility Policy

Purpose: Define whether partial compatibility is allowed.

Preferred end-state:

- no NT compatibility mode

Permitted during migration only:

- temporary feature-flagged compatibility adapters

Requirements for any temporary adapter:

- disabled by default once replacement path is proven
- documented with explicit removal owner
- removed before declaring this spec complete

## Risks

Purpose: Surface the hard parts.

- Robot-side diagnostics/probe code currently assumes direct NT availability.
- Host tools may still have hidden NT state reads outside main UI paths.
- Operator workflows may implicitly depend on NT timing behavior.
- Removing shared-keyspace transport can expose stale-state assumptions that were previously masked.
- PC tool availability from the robot must be fail-soft and timeout-bounded.

## Tradeoffs

Purpose: State the design tradeoffs openly.

- REST and JSON make contracts easier to reason about than NT key mutation.
- Polling can be less elegant than pushed state, but it is still clearer than shared-key transport.
- Removing NT entirely may require more deliberate endpoint design now, but it reduces long-term ambiguity and maintenance cost.
- Host/robot decoupling improves auditability at the cost of more explicit service code.

## Testing Requirements

Purpose: Define what must be proven before completion.

### Command And Session

- host UI can connect, own session, send commands, receive outputs, and disconnect without NT
- duplicate request handling still behaves correctly
- stop behavior still works
- protocol monitor visibility still exists through REST

### Runtime And Tests State

- UI and CLI state gating still works with REST-only state
- startup / reconnect / session reset behavior still works
- selected-test and manual active-group workflows still behave the same

### Diagnostics

- robot diagnostics reports still show PC CAN evidence when PC tool is present
- robot diagnostics fail soft when PC tool is absent
- active presence probe still produces equivalent behavior without NT

### Tool Removal

- no old NT command writers remain in supported workflows
- no old docs tell users to rely on NT for bringup control

## Definition Of Done

Purpose: Make completion auditable.

This spec is done only when all are true:

- no supported bringup host workflow requires NT
- no supported bringup robot workflow requires NT
- no supported old tool requires NT
- all bringup command/session/state/diagnostics services have non-NT replacements
- old NT command and protocol-monitor paths are deleted
- robot-side diagnostics/probe consumers no longer read bringup NT data
- updated docs describe the new transport architecture as canonical

## Open Questions

Purpose: Capture decisions still needed before implementation.

SID_QUESTION: Should the PC diagnostics replacement be pure polling JSON first, or should this spec require SSE/WebSocket from the start?

SID_QUESTION: Should the robot ever initiate HTTP polling to the PC tool directly, or should the host act as the broker and forward PC diagnostics to the robot REST server?

SID_QUESTION: Do we want one combined host/robot REST surface for runtime, tests, and diagnostics, or separate service endpoints owned by distinct modules?

## Recommended First Implementation Step

Purpose: Keep the first step concrete and low risk.

Start with Phase 1 only:

- remove legacy NT command transport and protocol monitor surfaces
- move all supported host UI and CLI command traffic to REST
- leave `bringup/diag/...` replacement for a later phase

That step gives the system one canonical control-plane transport before attacking the harder diagnostics-data-plane migration.
