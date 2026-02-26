# Architecture

This project is organized in explicit layers so it is easy to add new hardware without rewriting bringup logic.

## Layered Design

### 1) Device-Specific Layer (lowest)
Purpose: isolate vendor SDK calls and device-specific behaviors in one place.
- Each device type has a small wrapper class that only talks to the vendor API.
- The wrapper exposes a consistent API: create, stop, clear faults, and snapshot.

Examples:
- REV:
  - `RevSparkMaxNeoDevice`
  - `RevSparkMaxNeo550Device`
  - `RevFlexVortexDevice`
- CTRE:
  - `CtreTalonFxDevice`
  - `CtreCANCoderDevice`
  - `CtreCANdleDevice`

### 2) Manufacturer layer (middle)\nPurpose: group device types by vendor and centralize shared vendor logic. All manufacturer groups implement ManufacturerGroup.
- Builds and owns the list of device wrappers for that vendor.
- Provides shared helpers (spec lookup, health notes, low-current tracking).
- Exposes simple operations: add next, add all, set duty, stop, snapshot.

Examples:
- `ManufacturerGroup` (interface)
- `RevDeviceGroup`
- `CtreDeviceGroup`

### 3) Testing Layer (top)
Purpose: orchestrate bringup actions and output without vendor coupling.
- Handles input logic (add, add-all, nudge, print).
- Builds the human-readable output and JSON reports.
- Uses only manufacturer layer APIs.

Example:
- `BringupCore`

## Data Flow
- Device wrappers read raw vendor data into `DeviceSnapshot`.
- Manufacturer groups add notes/specs to snapshots.
- `BringupCore` prints and publishes reports using the snapshot list.

## Adding New Hardware
Add new devices in this order:
1. Add a device wrapper class for the new hardware.
2. Register it in the correct manufacturer group.
3. Add profile support in `bringup_profiles.json` (and update labels/mappings if needed).
4. Verify reports show the new device type.

This keeps the rest of the system stable and avoids spreading vendor logic across the codebase.


