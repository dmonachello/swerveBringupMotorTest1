# Architecture

Purpose: the system architecture defines structure, data flow, and stable contracts for the robot bringup harness and PC-side tools (CAN bridge, UI, CLI, topology tooling).

## System Overview
Purpose: the system is a client/server architecture with a robot-side server and multiple clients.

- Robot-side WPILib Java bringup harness runs motors/sensors and produces local health + reports (server).
- PC-side Python tool passively listens on the CAN bus and publishes diagnostics to NetworkTables.
- The robot consumes PC diagnostics via NetworkTables under `bringup/diag/...` and must fail soft if the PC tool is absent.
- Operator commands and report output now flow over the TCP command channel; NetworkTables remains for state/diagnostics visibility only.
- The PC tool also includes console monitoring, capture utilities, and offline analysis helpers.
- The topology editor and live topology view are part of the PC-side solution and share the same profile JSON contract.
- See OPERATOR_SURFACES.md for a focused view of CLI/GUI/topology surface responsibilities.
- See COMMAND_HANDLER_ARCHITECTURE.md for the detailed command parsing/execution split used by the Python CLI and Java UI handler.
- The Xbox controller input is a local client of the robot server (same process, local transport).

## 1000-Foot View
Purpose: the system has a high-level map of components, data sources, and safety boundaries.

The system is a client/server architecture. The robot hosts the bringup server and is authoritative for actuation and local health. PC-side tools act as clients for commands, logs, and state/diagnostics, while remaining observational on CAN and supporting offline analysis. The Xbox controller is treated as a local client of the robot server.

Key roles:
- Robot server (roboRIO, Java): creates devices, runs tests, commands outputs, and reports local health using vendor APIs.
- PC tool (Windows PC, Python): listens to CAN traffic via CANable, publishes diagnostics to NetworkTables, and records evidence (PCAP, inventory, diffs).
- PC tool (Windows PC, Python): listens to the roboRIO TCP console stream (NetConsole) to extract warnings/errors.
- PC operator surfaces: CLI, Bringup Control UI (TCP command channel), and live topology view (clients).
- PC topology tooling: topology editor that authors `bringup_system.json` and diagram metadata.
- Xbox controller input: local client interface feeding the robot server.

Data sources and trust boundaries:
- Robot-local telemetry comes only from vendor APIs on the roboRIO.
- CAN-bus telemetry comes only from the PC tool via NetworkTables.
- TCP command/output is a control/log channel, not a telemetry source.
- The two telemetry sources are kept distinct in reporting and APIs.

Host vs Robot Context
Purpose: prevent confusion between host-local editing context and robot runtime state.

- Host context: PC-side tools and operator surfaces selecting an "active profile" for local editing and inspection.
- Robot context: the roboRIO runtime "active profile" and selected test used for actuation.
- Rule: host context MUST NOT change robot context unless an explicit TCP robot command is executed (for example `profiles activate <name>`).

## Client/Server Boundary
Purpose: define the ownership and responsibilities across the robot server and PC clients.

Server (robot):
- Owns all actuation, device creation, and test execution.
- Owns authoritative local telemetry and safety checks.
- Hosts the TCP command server for UI/CLI clients.

Clients (PC tools + local Xbox):
- PC tools act as TCP clients for commands and logs.
- PC tools act as NT publishers for CAN-derived diagnostics.
- Xbox controller is a local client feeding the server loop.

Contracts across the boundary:
- TCP command protocol: command/ACK/OUT exchange for UI/CLI.
- TCP protocol details (wire framing, schemas, and examples): `docs/TCP_UI_PROTOCOL.md`.
- NetworkTables: diagnostics/state only under `bringup/diag/...`.
- JSON config: `bringup_system.json` is the shared input (profiles + devices table + diagram + tests under bridgeConfig).

## Safety Rules (Client/Server)
Purpose: keep networked control safe and deterministic.

- The robot is the server and owns all actuation authority.
- PC tools are clients; Xbox is a local client with highest priority.
- Both Xbox and TCP clients can be active at the same time.
- Xbox always wins on conflicts.
- A stop/disable/abort command sets a stop latch.
- The stop latch can be set by TCP or Xbox, but only Xbox can clear it.
- When the stop latch is set, TCP start/enable/run commands are rejected.
- TCP connection loss triggers a safe stop and sets the stop latch.
- Xbox disconnect triggers a safe stop and sets the stop latch.
- Driver Station enable/disable/E-stop overrides all client commands.
- NetworkTables is diagnostics/state only; TCP is command/log output only.

Control flow summary:
1. Operators author profiles and diagram metadata with the topology editor.
2. Operators select a profile and tests via JSON files and controller inputs.
3. Robot server instantiates devices and runs tests inside the 20ms loop.
4. PC tool listens on CAN, classifies frames, and publishes `bringup/diag/...` keys.
5. Robot server reads PC diagnostics separately and fails soft if the PC tool is absent.
6. Operator clients (UI/CLI) issue TCP commands and consume log output; NT remains for state/diagnostics visibility only.
7. Xbox controller acts as a local client feeding commands into the server loop.

Outputs:
- Console reports with throttled, chunked printing (emitted over TCP for UI/CLI and to local console).
- Console report tables are fixed-width, right-justified, and dot-padded; values truncate to column width.
- Robot JSON report (`bringup_report.json`).
- PC evidence artifacts (PCAP/PCAPNG, inventory JSON, inventory diffs).
- Topology artifacts: `bringup_system.json` (profiles + diagram metadata) and optional Shuffleboard layouts.

Safety invariants:
- PC tool is read-only on CAN and must never transmit frames.
- NetworkTables keys are a stable API contract across robot and PC.
- Large console output is throttled to protect the 20ms control loop.

### Console Error/Warning Signals (TCP Console)
Purpose: the robot console stream is a primary source of warnings and errors for DUTs.

The roboRIO console can be consumed over the TCP console service, and the PC tool can
parse console output to surface warnings/errors from the device under test (DUT).
Use this channel to catch vendor SDK faults, watchdog warnings, and other runtime
messages that are not on the CAN bus.

Notes:
- TCP console port: 1740.
- Treat console-derived signals as supplemental to CAN and local API telemetry.
- Console parsing should never block the 20ms loop; it belongs on the PC tool.

Message format:
- NetConsole TCP frames are 2-byte big-endian length-prefixed records.
- Payloads contain binary metadata plus printable text; text is decoded as UTF-8 (errors ignored).
- The parser splits payloads into lines and matches each line against regex rules.

## Layered Architecture (System-Wide)
Purpose: describe the full-system layering model across robot code, PC tools, workflows, and operator surfaces.

The project is best understood as two cooperating stacks (robot-side and PC-side) constrained by shared contracts. Across both sides, the system can be described in six layers:

### 1) Hardware and Transport Layer
Purpose: define the physical devices and raw communication channels the software depends on.

Includes:
- Robot hardware: motors, encoders, CAN devices, power devices, gyro, roboRIO, controller input.
- PC hardware: CANable and Windows host.
- Raw transports: CAN bus, serial/slcan, TCP, NetworkTables, filesystem.

Responsibilities:
- Real-world I/O.
- Physical device communication.
- Socket, serial, and table transport.

Examples:
- roboRIO + Xbox controller.
- CANable over COM/slcan.
- TCP UI socket.
- NetworkTables transport.

### 2) Adapter and Protocol Layer
Purpose: convert raw transport/vendor behavior into stable internal interfaces and parsed payloads.

Robot-side examples:
- Device wrappers over vendor SDKs.
- Manufacturer grouping abstractions.
- UI ingress parsing and protocol adaptation.

PC-side examples:
- CAN ID decoding.
- TCP ACK/OUT parsing.
- Profile/config loading.
- Console-monitor parsing.

Responsibilities:
- Hide raw vendor and wire details.
- Parse and normalize protocol payloads.
- Present a more stable surface to domain logic.

Examples:
- `devices/ctre/...`, `devices/rev/...`
- `manufacturers/...`
- `BridgeUiIngressPolicy`
- `bridge_session.py`
- `can_profiles.py`
- `visibility_provider.py`

### 3) Domain Logic Layer
Purpose: own the meaning of commands, profiles, tests, diagnostics, groups, and safety rules.

This is where the product's real semantics live.

Responsibilities:
- Command-family behavior.
- Profile/test/group/runtime semantics.
- Safety rules such as stop latch, disabled gating, and ownership/lock behavior.
- Diagnostics meaning such as visible vs missing vs stale.

Robot-side examples:
- `BringupCore`
- `BridgeGroupManager`
- `RobotLocalCommandRegistry`
- `RobotLocalCommandExecutor`
- `BridgeUiCommandHandler`
- `BridgeUiSessionCommands`
- `BridgeUiProfileCommands`
- `BridgeUiTestCommands`
- `BridgeUiGroupCommands`
- `BridgeUiReportCommands`
- `BridgeUiRuntimeCommands` (legacy compatibility surface; active command semantics are moving into the unified robot-local executor)

PC-side examples:
- `bridge_ops.py`
- `bridge_robot_control_facade.py`
- profile/test validation logic
- diagnostics normalization

### 4) Workflow and Application Service Layer
Purpose: coordinate domain actions into repeatable operator workflows.

This layer answers questions like:
- How does a user bring up a brand new robot one component at a time?
- How does a user edit config, validate it, sync it, deploy it, and verify behavior?
- How does a user capture evidence after a failure?

Responsibilities:
- Sequence domain actions into supported workflows.
- Reduce tool-by-tool ambiguity.
- Make the product feel like a system of workflows, not just a set of features.

Current examples are split across:
- workflow docs
- validate/sync scripts
- CLI/UI command sequences
- test-authoring paths

Current shared service examples:

- `tools/common/workflows/workflow01_service.py`
- `tools/common/config_lifecycle/service.py`
- `tools/common/tests_domain/semantics.py`
- `tools/common/diagnostics/normalize.py`

Important note:
- This is the layer the project still needs to strengthen the most in code. The primary example today is `docs/WORKFLOW_01_NEW_ROBOT_BRINGUP.md`.

### 5) Presentation and Operator Surface Layer
Purpose: provide the user-facing surfaces for interaction, control, and visualization.

Includes:
- Bridge CLI.
- Bringup Control UI.
- Topology editor.
- Live topology view.
- Robot-side printed reports.
- Dashboards.

Responsibilities:
- Collect user intent.
- Render results.
- Present status, diagnostics, and workflow guidance.

Rule:
- Presentation surfaces should stay as thin as possible. They should ask for outcomes, not re-own business semantics.

### 6) Contract and Specification Layer
Purpose: define the stable contracts that constrain both implementations and operator expectations.

Includes:
- TCP UI protocol.
- NetworkTables contract.
- Config/profile schema.
- Status code catalog.
- Architecture, workflow, and readiness specs.

Responsibilities:
- Keep Java, Python, tests, and docs aligned.
- Define what is stable and shared.
- Provide the source of truth for cross-language/cross-process behavior.

Examples:
- `docs/TCP_UI_PROTOCOL.md`
- `docs/NT_CONTRACT.md`
- `docs/COMMAND_HANDLER_ARCHITECTURE.md`
- `docs/WORKFLOW_01_NEW_ROBOT_BRINGUP.md`
- `docs/RELEASE_1_0_READINESS.md`

## Layered Design (Robot Server)
Purpose: the robot server architecture uses internal layers with clear responsibilities.

### 1) Device-Specific Layer (lowest)
Purpose: vendor SDK calls and device-specific behavior are isolated in this layer.

- Each device type has a wrapper that only talks to vendor APIs.
- The wrapper exposes a small API: create, stop, clear faults, snapshot, set duty, optional encoder read.
- No report formatting or NetworkTables work occurs here.

Examples:
- REV: `RevSparkMaxNeoDevice`, `RevSparkMaxNeo550Device`, `RevFlexVortexDevice`
- CTRE: `CtreTalonFxDevice`, `CtreCANCoderDevice`, `CtreCANdleDevice`

### 2) Manufacturer Layer (middle)
Purpose: vendor grouping centralizes shared logic across device types.

- Owns lists of device wrappers for the vendor.
- Adds shared helpers (spec lookup, health notes, low-current checks).
- Exposes operations: add next, add all, set duty, stop, snapshot.
- All manufacturer groups implement `ManufacturerGroup`.

Examples:
- `RevDeviceGroup`
- `CtreDeviceGroup`

### Adding a Manufacturer
Purpose: document the single edit point and the required implementation pattern.

Steps:
1. Implement a new `ManufacturerGroup` in `src/main/java/frc/robot/manufacturers/` (or vendor package).
2. Register it in `src/main/java/frc/robot/manufacturers/ManufacturerRegistry.java`.
3. Use standard `DeviceRegistration` + `DeviceTypeBucket` APIs inside the group.

Example manufacturer entry:
```java
new ManufacturerFactory("ACME", AcmeDeviceGroup::new)
```

### 3) Bringup Core + Test Orchestration (top)
Purpose: input actions, testing, and reporting are orchestrated without vendor coupling.

- `BringupCore` handles add/add-all, test selection/run-all, and local prints.
- `BringupTestRegistry` loads tests from JSON and supports a runtime override path.
- Tests are data-driven: composite and joystick tests with rotation/time/limit/hold checks.
- `RobotLocalCommandRegistry` owns the canonical local-command table.
- `RobotLocalCommandExecutor` owns single-active-command execution with one queued slot.
- `BridgeUiCommandHandler` hosts the active command path used by both controller bindings and TCP host UI.
- `BringupCommandRouter` remains legacy compatibility scaffolding and should not be treated as the primary extension path for new robot-local commands.

## Input + Bindings (Local Client)
Purpose: controller bindings remain data-driven and stable for the local Xbox client.

- `bringup_bindings.json` defines controllers (type/port/role) plus command bindings/axes.
- `BindingsManager` resolves bindings and axes each loop.
- Binding command names are validated against `RobotLocalCommandRegistry`.
- `RobotV2` submits newly active controller commands into the shared robot-local executor.

## Configuration Layer
Purpose: JSON inputs define behavior and runtime configuration.

- `bringup_system.json`: unified system config (profiles + diagram + bridgeConfig.byProfile). Active repo-owned copy lives in `src/main/deploy/`.
- Requires `schema_version` (4), `data_version`, and `data_hash` at the root.
- Profiles reference devices by label only; the devices table owns the CAN identity fields.
- Tests are stored inside `bringup_system.json` under `bridgeConfig.byProfile.<profile>.tests`.
- `motor_specs.json`: motor current specs for health checks.
- `can_mappings.json`: manufacturer/device type names for CAN decoding.

## PC Tools (clients)
Purpose: PC-side tools cover CAN capture, operator surfaces, and offline analysis.

- `tools/can_nt/can_nt_bridge.py` listens on CANable (SLCAN) and publishes `bringup/diag` keys.
- `tools/can_nt/can_console_monitor.py` listens to the roboRIO NetConsole TCP stream and publishes console-derived warning/error counters.
- `tools/can_nt/bridge_cli.py` provides a command-line interface for TCP UI commands and log polling.
- `tools/can_nt/bringup_ui.py` provides a Windows-friendly GUI that mirrors bringup commands and log output over TCP. Its robot-local button inventory is generated from the Java command registry; NT remains state/diag only.
- `tools/can_nt/bridge_session.py` centralizes TCP command/session behavior for GUI and CLI.
- PC tool output includes PCAP/PCAPNG capture, inventory JSON, and diffs.
- Live Wireshark capture uses a Windows named pipe (`\\.\pipe\FRC_CAN`) via `--pcap-pipe`.
  - Details live in `tools/can_nt/README_CAN_NT.md` and the Wireshark section in `README.md`.
- NetworkTables publishing is additive; existing keys must remain stable.
- The PC tool must remain read-only on CAN (no frame transmission).

## PC Operator Surfaces
Purpose: describe the operator-facing surfaces beyond the core CAN bridge.

- Bringup Control UI (TCP): issues commands, displays log output, and can poll runtime state.
- Bringup Control UI command buttons are built from generated Python artifacts derived from the Java robot-local command registry.
- Bridge CLI (TCP): scriptable command interface for bringup actions and reports.
- Command handler split details for these surfaces live in `docs/COMMAND_HANDLER_ARCHITECTURE.md`.
- NetConsole monitor: surfaces warnings/errors and health cues not present on CAN.
- Live topology view: read-only diagram view with runtime overlays driven by robot state.

## Topology Tooling
Purpose: document the profile authoring and diagram pipeline.

- Topology editor (`tools/can_topology/`) edits profiles, tags, and diagram layout.
- Outputs `bringup_system.json` (profiles + diagram metadata + bridgeConfig.byProfile groups).
- Diagram metadata is editor-only; robot and CAN bridge ignore it.
- Live topology view reads the same profile JSON for overlays.

## Data Flow
Purpose: data moves through defined stages from inputs to reports and operator surfaces.

### H) Initialization Flow (Robot)
Purpose: document the one-time startup sequence and core object construction.

1. `Main` calls `RobotBase.startRobot(RobotV2::new)` to launch the active harness.
2. `RobotV2.robotInit()` runs once:
   - Applies the active CAN profile (`BringupUtil.applyProfileFromArgs()`).
   - Loads tests from `bringup_system.json` (`bridgeConfig.byProfile.<profile>.tests`) when present.
   - Constructs `BringupCore` (see below) and `DiagnosticsReporter`.
   - Applies dashboard state, prints startup info, and validates CAN IDs.
3. `BringupCore` construction:
   - Builds manufacturer groups via `ManufacturerRegistry.buildGroups()`.
   - Builds `BringupTestContext` from the group list.
   - Loads tests via `BringupTestRegistry.loadTests()`.
   - Initializes selectable tests and test device lists.

### A) Startup + Configuration Load
Purpose: profiles, bindings, and tests load in a predictable order.

1. Robot starts (`Robot` or `RobotV2`) and applies the active CAN profile:
   - `bringup_system.json` is loaded via `BringupUtil` (deploy copy; data is canonical).
   - `default_profile` is selected unless `--bringup-profile=...` is provided.
2. Tests are loaded from `bringup_system.json`:
   - Source: `bridgeConfig.byProfile.<profile>.tests`.
   - Active set: `default_test_set` inside that per-profile tests block.
   - Note: `bringup_tests.json`-only workflows are legacy and not used by the robot.
3. Input configuration is loaded:
   - `bringup_bindings.json` defines controller roles, bindings, and axes.

### B) Input -> Action -> Device Command
Purpose: controller inputs translate into bringup actions each loop.

1. Each loop, `BindingsManager` samples controller inputs.
2. `RobotV2` and `BridgeUiCommandHandler` detect newly active controller commands and create `RobotLocalCommandRequest` objects.
3. `RobotLocalCommandExecutor` performs registry lookup and admission control:
   - one active command maximum
   - one queued command maximum
   - interrupt or stop when requested
4. The selected grouped command implementation runs against `RobotLocalCommandHost`.
5. `BringupCore` and related runtime services perform the actual add/report/test/profile work behind that host interface.

### C) Local Device Telemetry (Robot-only)
Purpose: device health and snapshots are produced from vendor APIs and enrichments.

1. Device wrappers read vendor APIs into `DeviceSnapshot` objects.
2. Manufacturer groups enrich snapshots with:
   - Motor specs and current sanity checks.
   - Health notes and attachments (e.g., encoder, limit switches).
3. `BringupCore` formats and prints local summaries and JSON.

### D) Test Execution Loop
Purpose: tests run in a loop and terminate on explicit conditions.

1. Composite or joystick tests start from `BringupTestRegistry` configs.
2. Each loop:
   - For composite tests, checks run conditions (rotation/time/limit/hold).
   - For joystick tests, the selected axis drives configured motors.
3. When a condition triggers, the test stops motors and records PASS/FAIL.

### E) PC Tool Capture + NetworkTables Publish
Purpose: CAN bus traffic becomes diagnostics through classification and publishing.

1. `tools/can_nt/can_nt_bridge.py` reads frames from CANable (SLCAN).
2. It writes optional PCAP/PCAPNG, and builds inventory statistics.
3. It publishes `bringup/diag/...` keys to NetworkTables:
   - Device presence, age, counts, and PC tool health.
4. The PC tool never transmits CAN frames (passive only).

### F) Robot Consumption of PC Diagnostics
Purpose: the robot server consumes PC tool data safely and fails soft when absent.

1. Robot reads `bringup/diag/...` NetworkTables keys.
2. PC diagnostics are displayed separately from local telemetry.
3. The system fails soft if PC tool is absent (stale or missing keys).

### G) Reports + Outputs
Purpose: outputs are produced as console reports, JSON, and capture artifacts.

- Console prints: local health, test status, and PC diagnostics summaries (delivered over TCP for UI/CLI and to local console).
- JSON report: `bringup_report.json` (robot-local snapshot + PC diagnostics).
- PCAP/PCAPNG captures (PC tool).
- Inventory and diff JSON files (PC tool).

### I) Topology Authoring + Diagram Pipeline
Purpose: profiles and diagram metadata are authored offline and consumed at runtime.

1. The topology editor updates profiles, tags, and diagram layout.
2. The editor writes `bringup_system.json` with profile data and diagram metadata.
3. Robot and CAN bridge consume profiles; diagram metadata is editor/UI-only.

### J) Operator Command Channel (TCP)
Purpose: operator clients send commands without blocking the 20ms loop.

1. UI/CLI sends TCP commands to the robot bringup server.
2. The robot server responds with ACK/OUT events; UI/CLI render outputs.
3. NetworkTables remains the channel for diagnostics and state visibility only.

## Stable Contracts
Purpose: stable interfaces are identified to prevent uncoordinated changes.

- NetworkTables keys under `bringup/diag/...` (robot and PC tool must stay in sync).
- JSON schema for `bringup_system.json` (including bridgeConfig tests).
- Report output fields in `bringup_report.json`.
- TCP command protocol (UI/CLI) and log output formats.

## Data Integrity Rules
Purpose: define how runtime and offline tools enforce profile integrity.
- Runtime tools (roboRIO + CAN bridge) must hard-fail on `schema_version` (4), `data_version`, or `data_hash` mismatch.
- Offline tools (topology editor) may open mismatched files for repair after prompting the user.
- The topology editor always recomputes `data_hash` on save.

## Examples
Purpose: concrete examples anchor the JSON patterns.

Composite test (rotation + time):
```json
{
  "type": "composite",
  "name": "Rotation + Time",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 10"],
  "duty": 0.2,
  "rotation": { "limitRot": 10.0, "encoderKey": "internal", "encoderMotorIndex": 0 },
  "time": { "timeoutSec": 2.0, "onTimeout": "fail" }
}
```

Through-bore via SparkMax alternate encoder:
```json
{
  "type": "composite",
  "name": "Through-bore rotation (SparkMax)",
  "enabled": true,
  "motorLabels": ["SPARKMAX/NEO 10"],
  "duty": 0.2,
  "rotation": {
    "limitRot": 5.0,
    "encoderKey": "through_bore",
    "encoderSource": "sparkmax_alt",
    "encoderCountsPerRev": 8192,
    "encoderMotorIndex": 0
  }
}
```

## What Stays Stable
Purpose: outputs and contracts are highlighted as stability targets.

- Console output ordering and field names.
- JSON report schema and field names.
- NetworkTables key paths and types.
- Profile JSON schema.

## Tradeoffs
Purpose: known design costs are acknowledged explicitly.

- More classes than a monolith, but isolation is stronger and safer.
- Some duplication across wrappers, but vendor API changes stay localized.
- Data-driven tests add JSON complexity, but reduce code churn and keep behavior stable.

## Future Extensions
Purpose: future extensions are identified without breaking contracts.

- Add decoder table for CAN reverse engineering outputs.
- Add more controller types in `bringup_bindings.json` (beyond Xbox).
- Add new test check types without changing existing JSON fields.
- Add dashboard widgets for live test status and PC tool health.
- Add support for additional device families:
  - CTRE Pigeon 2, CANrange, CANdi, and legacy TalonSRX/VictorSPX.
  - REV PDH, PH, and SparkMax alternate encoder paths.
  - WPILib I/O (DIO, analog input, relay) and roboRIO health signals.
  - Third-party CAN encoders and IMUs (WCP CANandmag, navX, etc.).
