# Architecture

Purpose: describe the system structure, data flow, and stable contracts for the robot bringup harness and PC CAN tool.

## System Overview
Purpose: summarize the two cooperating parts and how they interact.

- Robot-side WPILib Java bringup harness runs motors/sensors and produces local health + reports.
- PC-side Python tool passively listens on the CAN bus and publishes diagnostics to NetworkTables.
- The robot consumes PC diagnostics via NetworkTables under `bringup/diag/...` and must fail soft if the PC tool is absent.

## Layered Design (Robot)
Purpose: show the internal layers and their responsibilities.

### 1) Device-Specific Layer (lowest)
Purpose: isolate vendor SDK calls and device-specific behavior.

- Each device type has a wrapper that only talks to vendor APIs.
- The wrapper exposes a small API: create, stop, clear faults, snapshot, set duty, optional encoder read.
- No report formatting or NetworkTables work occurs here.

Examples:
- REV: `RevSparkMaxNeoDevice`, `RevSparkMaxNeo550Device`, `RevFlexVortexDevice`
- CTRE: `CtreTalonFxDevice`, `CtreCANCoderDevice`, `CtreCANdleDevice`

### 2) Manufacturer Layer (middle)
Purpose: group device types by vendor and centralize shared logic.

- Owns lists of device wrappers for the vendor.
- Adds shared helpers (spec lookup, health notes, low-current checks).
- Exposes operations: add next, add all, set duty, stop, snapshot.
- All manufacturer groups implement `ManufacturerGroup`.

Examples:
- `RevDeviceGroup`
- `CtreDeviceGroup`

### 3) Bringup Core + Test Orchestration (top)
Purpose: orchestrate input actions, testing, and reporting without vendor coupling.

- `BringupCore` handles add/add-all, test selection/run-all, and local prints.
- `BringupTestRegistry` loads tests from JSON and supports a runtime override path.
- Tests are data-driven: composite and joystick tests with rotation/time/limit/hold checks.
- `BringupCommandRouter` maps bindings to core actions.

## Input + Bindings
Purpose: keep controller bindings data-driven and stable.

- `bringup_bindings.json` defines controllers (type/port/role) plus command bindings/axes.
- `BindingsManager` resolves bindings and axes each loop.

## Configuration Layer
Purpose: document the JSON inputs that define behavior.

- `bringup_profiles.json`: hardware profiles (devices + IDs). Includes stable `example_default`.
- `bringup_tests.json`: test definitions (composite/joystick) grouped into test sets.
- `motor_specs.json`: motor current specs for health checks.
- `can_mappings.json`: manufacturer/device type names for CAN decoding.

## PC CAN Tool (tools/)
Purpose: describe passive CAN capture + diagnostics publishing.

- `tools/can_nt/can_nt_bridge.py` listens on CANable (SLCAN) and publishes `bringup/diag` keys.
- PC tool output includes PCAP/PCAPNG capture, inventory JSON, and diffs.
- Live Wireshark capture uses a Windows named pipe (`\\.\pipe\FRC_CAN`) via `--pcap-pipe`.
  - Details live in `tools/can_nt/README_CAN_NT.md` and the Wireshark section in `README.md`.
- NetworkTables publishing is additive; existing keys must remain stable.
- The PC tool must remain read-only on CAN (no frame transmission).

## Data Flow
Purpose: explain how data moves through the system.

### A) Startup + Configuration Load
Purpose: show how profiles, bindings, and tests are loaded.

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
Purpose: show how controller inputs become actions.

1. Each loop, `BindingsManager` samples controller inputs.
2. `BringupCommandRouter` maps bindings to actions:
   - Add motor / add all / print state / print health.
   - Test selection, run, run-all, and enable toggle.
3. `BringupCore` performs the action:
   - Instantiates devices and updates internal lists.
   - For tests, starts and updates the active test state.

### C) Local Device Telemetry (Robot-only)
Purpose: show how device health and snapshots are produced.

1. Device wrappers read vendor APIs into `DeviceSnapshot` objects.
2. Manufacturer groups enrich snapshots with:
   - Motor specs and current sanity checks.
   - Health notes and attachments (e.g., encoder, limit switches).
3. `BringupCore` formats and prints local summaries and JSON.

### D) Test Execution Loop
Purpose: show how tests run and terminate.

1. Composite or joystick tests start from `BringupTestRegistry` configs.
2. Each loop:
   - For composite tests, checks run conditions (rotation/time/limit/hold).
   - For joystick tests, the selected axis drives configured motors.
3. When a condition triggers, the test stops motors and records PASS/FAIL.

### E) PC Tool Capture + NetworkTables Publish
Purpose: show how CAN bus traffic becomes diagnostics.

1. `tools/can_nt/can_nt_bridge.py` reads frames from CANable (SLCAN).
2. It writes optional PCAP/PCAPNG, and builds inventory statistics.
3. It publishes `bringup/diag/...` keys to NetworkTables:
   - Device presence, age, counts, and PC tool health.
4. The PC tool never transmits CAN frames (passive only).

### F) Robot Consumption of PC Diagnostics
Purpose: show how the robot uses PC tool data safely.

1. Robot reads `bringup/diag/...` NetworkTables keys.
2. PC diagnostics are displayed separately from local telemetry.
3. The system fails soft if PC tool is absent (stale or missing keys).

### G) Reports + Outputs
Purpose: show what outputs are produced and where.

- Console prints: local health, test status, and PC diagnostics summaries.
- JSON report: `bringup_report.json` (robot-local snapshot + PC diagnostics).
- PCAP/PCAPNG captures (PC tool).
- Inventory and diff JSON files (PC tool).

## Stable Contracts
Purpose: list the interfaces that must not change without coordination.

- NetworkTables keys under `bringup/diag/...` (robot and PC tool must stay in sync).
- JSON schemas for `bringup_profiles.json` and `bringup_tests.json`.
- Report output fields in `bringup_report.json`.

## Examples
Purpose: provide concrete, minimal examples.

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
Purpose: highlight outputs and contracts that should not change lightly.

- Console output ordering and field names.
- JSON report schema and field names.
- NetworkTables key paths and types.
- Profile JSON schema.

## Tradeoffs
Purpose: show known costs of the design.

- More classes than a monolith, but isolation is stronger and safer.
- Some duplication across wrappers, but vendor API changes stay localized.
- Data-driven tests add JSON complexity, but reduce code churn and keep behavior stable.

## Future Extensions
Purpose: list likely next steps without breaking contracts.

- Add decoder registry for CAN reverse engineering outputs.
- Add more controller types in `bringup_bindings.json` (beyond Xbox).
- Add new test check types without changing existing JSON fields.
- Add dashboard widgets for live test status and PC tool health.
