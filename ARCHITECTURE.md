# Architecture

Purpose: the system architecture defines structure, data flow, and stable contracts for the robot bringup harness and PC CAN tool.

## System Overview
Purpose: the system has two cooperating parts with a defined interaction boundary.

- Robot-side WPILib Java bringup harness runs motors/sensors and produces local health + reports.
- PC-side Python tool passively listens on the CAN bus and publishes diagnostics to NetworkTables.
- The robot consumes PC diagnostics via NetworkTables under `bringup/diag/...` and must fail soft if the PC tool is absent.

## 1000-Foot View
Purpose: the system has a high-level map of components, data sources, and safety boundaries.

The system is a two-part bringup stack: robot code that actively drives hardware and a PC tool that passively observes the CAN bus. The robot side is authoritative for actuation and local health, while the PC side is observational and augments diagnostics.

Key roles:
- Robot (roboRIO, Java): creates devices, runs tests, commands outputs, and reports local health using vendor APIs.
- PC tool (Windows PC, Python): listens to CAN traffic via CANable, publishes diagnostics to NetworkTables, and records evidence (PCAP, inventory, diffs).
- PC tool (Windows PC, Python): listens to the roboRIO TCP console stream (NetConsole) to extract warnings/errors.

Data sources and trust boundaries:
- Robot-local telemetry comes only from vendor APIs on the roboRIO.
- CAN-bus telemetry comes only from the PC tool via NetworkTables.
- The two data sources are kept distinct in reporting and APIs.

Control flow summary:
1. Operators select a profile and tests via JSON files and controller inputs.
2. Robot code instantiates devices and runs tests inside the 20ms loop.
3. PC tool listens on CAN, classifies frames, and publishes `bringup/diag/...` keys.
4. Robot reads PC diagnostics separately and fails soft if the PC tool is absent.

Outputs:
- Console reports with throttled, chunked printing.
- Console report tables are fixed-width, right-justified, and dot-padded; values truncate to column width.
- Robot JSON report (`bringup_report.json`).
- PC evidence artifacts (PCAP/PCAPNG, inventory JSON, inventory diffs).

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

## Layered Design (Robot)
Purpose: the robot architecture uses internal layers with clear responsibilities.

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

### 3) Bringup Core + Test Orchestration (top)
Purpose: input actions, testing, and reporting are orchestrated without vendor coupling.

- `BringupCore` handles add/add-all, test selection/run-all, and local prints.
- `BringupTestRegistry` loads tests from JSON and supports a runtime override path.
- Tests are data-driven: composite and joystick tests with rotation/time/limit/hold checks.
- `BringupCommandRouter` maps bindings to core actions.

## Input + Bindings
Purpose: controller bindings remain data-driven and stable.

- `bringup_bindings.json` defines controllers (type/port/role) plus command bindings/axes.
- `BindingsManager` resolves bindings and axes each loop.

## Configuration Layer
Purpose: JSON inputs define behavior and runtime configuration.

- `bringup_profiles.json`: hardware profiles (devices + IDs). Includes stable `example_default`.
- `bringup_tests.json`: test definitions (composite/joystick) grouped into test sets.
- `motor_specs.json`: motor current specs for health checks.
- `can_mappings.json`: manufacturer/device type names for CAN decoding.

## PC CAN Tool (tools/)
Purpose: passive CAN capture feeds diagnostics publishing.

- `tools/can_nt/can_nt_bridge.py` listens on CANable (SLCAN) and publishes `bringup/diag` keys.
- `tools/can_nt/can_console_monitor.py` listens to the roboRIO NetConsole TCP stream and publishes console-derived warning/error counters.
- PC tool output includes PCAP/PCAPNG capture, inventory JSON, and diffs.
- Live Wireshark capture uses a Windows named pipe (`\\.\pipe\FRC_CAN`) via `--pcap-pipe`.
  - Details live in `tools/can_nt/README_CAN_NT.md` and the Wireshark section in `README.md`.
- NetworkTables publishing is additive; existing keys must remain stable.
- The PC tool must remain read-only on CAN (no frame transmission).

## Data Flow
Purpose: data moves through defined stages from inputs to reports.

### A) Startup + Configuration Load
Purpose: profiles, bindings, and tests load in a predictable order.

1. Robot starts (`Robot` or `RobotV2`) and applies the active CAN profile:
   - `bringup_profiles.json` is loaded via `BringupUtil`.
   - `default_profile` is selected unless `--bringup-profile=...` is provided.
2. Tests are loaded by `BringupTestRegistry`:
   - Default: `bringup_tests.json` from deploy dir.
   - Active set: `default_test_set` inside `bringup_tests.json`.
   - Override: `--bringup-tests=...` if provided (loads another JSON file).
3. Input configuration is loaded:
   - `bringup_bindings.json` defines controller roles, bindings, and axes.

### B) Input -> Action -> Device Command
Purpose: controller inputs translate into bringup actions each loop.

1. Each loop, `BindingsManager` samples controller inputs.
2. `BringupCommandRouter` maps bindings to actions:
   - Add motor / add all / print state / print health.
   - Test selection, run, run-all, and enable toggle.
3. `BringupCore` performs the action:
   - Instantiates devices and updates internal lists.
   - For tests, starts and updates the active test state.

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
Purpose: the robot consumes PC tool data safely and fails soft when absent.

1. Robot reads `bringup/diag/...` NetworkTables keys.
2. PC diagnostics are displayed separately from local telemetry.
3. The system fails soft if PC tool is absent (stale or missing keys).

### G) Reports + Outputs
Purpose: outputs are produced as console reports, JSON, and capture artifacts.

- Console prints: local health, test status, and PC diagnostics summaries.
- JSON report: `bringup_report.json` (robot-local snapshot + PC diagnostics).
- PCAP/PCAPNG captures (PC tool).
- Inventory and diff JSON files (PC tool).

## Stable Contracts
Purpose: stable interfaces are identified to prevent uncoordinated changes.

- NetworkTables keys under `bringup/diag/...` (robot and PC tool must stay in sync).
- JSON schemas for `bringup_profiles.json` and `bringup_tests.json`.
- Report output fields in `bringup_report.json`.

## Examples
Purpose: concrete examples anchor the JSON patterns.

Composite test (rotation + time):
```json
{
  "type": "composite",
  "name": "Rotation + Time",
  "enabled": true,
  "motorKeys": ["REV:NEO:10"],
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
  "motorKeys": ["REV:NEO:10"],
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

- Add decoder registry for CAN reverse engineering outputs.
- Add more controller types in `bringup_bindings.json` (beyond Xbox).
- Add new test check types without changing existing JSON fields.
- Add dashboard widgets for live test status and PC tool health.
