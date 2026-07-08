# Remove NT Phase 2 Inventory

## Purpose

Inventory the remaining NetworkTables usage after the first NT removal pass, classify each surface by ownership and risk, and define the safest removal order for branch `remove_nt_2`.

## Current State

The main bringup UI control path is now REST-driven for:

- runtime state
- tests state
- session state
- command submit/status/output

NetworkTables is still present in the repo, but the remaining code is no longer one single category. It now falls into four groups:

- legacy robot UI command/output transport
- legacy robot tests/runtime publish surfaces
- robot diagnostics fed from PC-side NT publishing
- Python-side NT publishing and compatibility helpers

Because of that split, the safe removal path is by ownership slice, not by deleting all `NetworkTable` references at once.

## Inventory

### Java NT Reads

#### 1. Legacy UI command ingress

Files:

- `src/main/java/frc/robot/BridgeUiCommandHandler.java`

Reads:

- `uiTable.getEntry("cmd/seq")`
- `uiTable.getEntry("cmd/name")`
- `uiTable.getEntry("cmd/args/json")`
- `uiTable.getEntry("cmd/ts")`
- `uiTable.getEntry("cmd/clientId")`

Classification:

- `compatibility/legacy`

Notes:

- This is the old NT command ingestion path.
- The supported UI and CLI now use REST.
- This path should be removable once we confirm nothing still emits NT UI commands in normal workflows.

#### 2. PC diagnostics/report input

Files:

- `src/main/java/frc/robot/DiagnosticsReporter.java`
- `src/main/java/frc/robot/diag/probe/ActiveDevicePresenceProbe.java`

Reads:

- `diagTable.getEntry("can/pc/openOk")`
- `diagTable.getEntry("can/pc/framesPerSec")`
- `diagTable.getEntry("can/pc/framesTotal")`
- `diagTable.getEntry("can/pc/readErrors")`
- `diagTable.getEntry("can/pc/lastFrameAgeSec")`
- `diagTable.getEntry("busErrorCount")`
- `diagTable.getSubTable("console")...`
- `diagTable.getEntry("dev/<labelKey>/...")`

Classification:

- `diagnostic/reporting`

Notes:

- This is the largest remaining real NT dependency.
- It is still functional, not dead.
- `printNTdiag` is directly tied to this path.
- Some active presence probe evidence still reads console diagnostics from this table.

### Java NT Writes

#### 3. Legacy robot UI state and test state publish

Files:

- `src/main/java/frc/robot/BridgeUiCommandHandler.java`

Writes:

- `ui/state/...`
- `tests/...`
- tests row subtables
- test run snapshot fields

Classification:

- `compatibility/legacy`

Notes:

- The current host UI does not need these NT surfaces for the supported path.
- They were retained for the old host-side UI table model and backward compatibility.

#### 4. Legacy UI ack/output publish

Files:

- `src/main/java/frc/robot/BridgeUiOutputFacade.java`
- `src/main/java/frc/robot/BridgeUiCommandHandler.java`

Writes:

- `ack/...`
- `out/...`
- `state/lastAckSeq`
- `state/lastAckMs`
- `state/sessionId`
- `state/protocolVersion`
- `state/activeClientId`

Classification:

- `compatibility/legacy`

Notes:

- This is the old robot-to-host UI output transport.
- REST command output now owns the supported workflow.

#### 5. UI protocol session state publish

Files:

- `src/main/java/frc/robot/BridgeUiSessionCommands.java`

Writes:

- `uiProtocolTable connected/enabled state`

Classification:

- `compatibility/legacy`

Notes:

- This supports the old NT handshake/session indicator path.

### Java NT Infrastructure Holders

#### 6. Robot and runtime NT roots

Files:

- `src/main/java/frc/robot/RobotV2.java`
- `src/main/java/frc/robot/Robot.java`
- `src/main/java/frc/robot/BringupRuntime.java`
- `src/main/java/frc/robot/BringupCore.java`

Responsibilities:

- construct `bringup/diag`
- pass `diagTable` into runtime/core/diagnostics/probes

Classification:

- `infrastructure`

Notes:

- Do not remove these first.
- They fall away naturally after diagnostics/reporting and probe consumers are removed or replaced.

### Python NT Publishers / Writers

#### 7. PC CAN diagnostics publishing

Files:

- `tools/can_nt/can_nt_client.py`
- `tools/can_nt/can_console_monitor.py`
- `tools/can_nt/can_reporting.py`

Classification:

- `diagnostic/reporting`

Notes:

- This phase deletes the NT publisher path after phase 2D removes the robot NT readers.
- Host visibility and console evidence remain supported, but they are now sourced from:
  - `VisibilityProvider`
  - `ConsoleMonitor`
- `--no-nt` remains compatibility-only on the bridge parser for one iteration.

#### 8. Legacy host-to-robot NT UI command sender

Files:

- `tools/can_nt/can_nt_bridge.py`

Writes:

- `bringup/ui/cmd/name`
- `bringup/ui/cmd/args/json`
- `bringup/ui/cmd/ts`
- `bringup/ui/cmd/seq`

Classification:

- `compatibility/legacy`

Notes:

- This is the old NT command sender.
- The current supported host UI and CLI use REST.
- Remove only after confirming no supported recovery workflow still depends on it.

### Tests and Docs

#### 9. NT-specific tests, registry rows, and docs

Files:

- `src/test/java/frc/robot/BridgeUiSessionCommandsTest.java`
- `src/test/java/frc/robot/BridgeUiReportCommandsTest.java`
- `tools/can_nt/generated/robot_local_commands_generated.py`
- `tools/can_nt/README.txt`
- `tools/can_nt/README_CAN_NT.md`
- status surface inventories referencing `printNTdiag` and `bringup/diag`

Classification:

- `compatibility/legacy`

Notes:

- These must be updated in the same slice as their owning feature removal.

## Proposed Ownership Replacement

### Already Owned By REST

- runtime state
- tests state
- session state
- command execution status
- command output

### Should Stay Host-Owned

- CAN visibility
- CAN bus summaries
- console-monitor evidence derived from host-collected data

### Should Move To Structured REST If Still Needed By Robot/Host

- robot-local diagnostics summaries now only available through robot report text
- any host-visible robot health detail that still depends on NT-only report composition

## Safe Removal Order

### Phase 2A: Remove legacy NT UI command/output path

Targets:

- `BridgeUiCommandHandler.handleUiCommands()`
- `BridgeUiOutputFacade`
- `BridgeUiSessionCommands` UI protocol table publishing
- old host NT command sender in `can_nt_bridge.py`

Why first:

- This is mostly compatibility transport now.
- It is lower risk than removing diagnostics evidence first.
- It reduces dual-control-path confusion.

Exit criteria:

- supported UI and CLI still work over REST only
- no supported workflow emits or consumes `bringup/ui/...` NT commands

### Phase 2B: Remove legacy NT tests/runtime publish tables

Targets:

- `BridgeUiCommandHandler` NT writes under `ui/state/...`
- `BridgeUiCommandHandler` NT writes under `tests/...`

Why second:

- The current host UI already reads REST `/runtime/state` and `/tests/state`.
- These NT tables are now compatibility surfaces, not primary ownership.

Exit criteria:

- no supported UI or script reads these NT tables
- tests updated to use REST behavior only

### Phase 2C: Remove `printNTdiag` and robot NT diagnostics report dependency

Targets:

- `printNTdiag`
- NT diagnostics report text in `DiagnosticsReporter`
- NT diagnostics command metadata and docs

Why third:

- This removes the biggest remaining misleading user-facing NT surface.
- We already replaced the left-rail `CAN Bus` workflow with a host-owned combined report.

Exit criteria:

- no user-facing surface depends on the old NT diagnostics report
- command registry/help/generated artifacts updated

### Phase 2D: Remove robot reads of host `bringup/diag` NT data

Targets:

- `DiagnosticsReporter` PC snapshot and console reads
- `ActiveDevicePresenceProbe.applyConsoleEvidence(...)`

Why fourth:

- This is where remaining real diagnostic functionality still lives.
- Removing it earlier would break evidence paths.

Exit criteria:

- replacement evidence/report path exists, or feature is intentionally retired
- probe/report regressions updated

### Phase 2E: Remove Python-side NT publishing helpers

Targets:

- NT write portions of `can_nt_client.py`
- `can_console_monitor.publish(...)`
- remaining NT key inventory docs
- compatibility parser/help surfaces for explicit NT key inventory options

Why last:

- These are still the upstream producers for the robot NT diagnostics path.
- Once all robot NT consumers are removed, these become dead.

Exit criteria:

- no supported consumer reads `bringup/diag/...`
- docs and generated inventories updated
- host visibility still works from shared in-process data only

## Things That Should Not Be Done First

- Do not remove `diagTable` from `RobotV2` or `BringupRuntime` first.
- Do not delete `NetworkTable` imports repo-wide first.
- Do not remove Python NT publishing before removing robot NT readers.
- Do not leave partial duplicate REST and NT ownership for the same surviving feature.

## Recommended Immediate Work On `remove_nt_2`

1. Remove the legacy NT UI command/output transport.

2. Remove NT runtime/tests publish tables from `BridgeUiCommandHandler`.

3. Remove `printNTdiag` and its generated/docs/test surfaces.

4. Re-run targeted regressions after each slice, not only at the end.

## Regression Expectations

Every bug fix or removal step must add or update the narrowest meaningful regression test for that slice.

At minimum for this branch:

- UI tests for REST-only runtime/tests state
- Java tests for REST server and UI command handler behavior
- generated artifact sync checks where command inventory changes
- doc/help updates in the same change when user-facing behavior changes
