# Architecture

This project is organized in explicit layers so it is easy to add or change hardware without rewriting bringup logic. The design keeps vendor-specific SDK calls isolated, keeps test orchestration simple, and preserves stable report output.

## Why This Design

### Goals
- Make it easy for teams to add or remove hardware by editing data, not rewriting code.
- Keep vendor SDK calls isolated so failures are contained and changes are localized.
- Preserve stable console output, JSON schema, and NetworkTables keys.
- Keep bringup actions simple, repeatable, and safe for field use.

### Key Advantages
- **Isolation of vendor SDKs**: Vendor API changes are confined to device wrappers.
- **Clear ownership**: Each layer has a single responsibility, which makes the code easier to navigate.
- **Predictable outputs**: Reports and JSON are built from snapshots, so output stays consistent even as hardware changes.
- **Faster onboarding**: Adding hardware follows a small checklist instead of a full code search.
- **Safer refactors**: Testing logic can evolve without touching vendor calls or report formatting.

## Layered Design

### 1) Device-Specific Layer (lowest)
Purpose: isolate vendor SDK calls and device-specific behavior.
- Each device type has a small wrapper class that only talks to the vendor API.
- The wrapper exposes a consistent API: create, stop, clear faults, snapshot, set duty.
- The wrapper never formats output and never knows about reports.
- Each wrapper supplies a required `RegistrationHeader` (metadata and provenance).

Examples:
- REV:
  - `RevSparkMaxNeoDevice`
  - `RevSparkMaxNeo550Device`
  - `RevFlexVortexDevice`
- CTRE:
  - `CtreTalonFxDevice`
  - `CtreCANCoderDevice`
  - `CtreCANdleDevice`

### 2) Manufacturer Layer (middle)
Purpose: group device types by vendor and centralize shared vendor logic.
- Builds and owns the list of device wrappers for that vendor.
- Provides shared helpers (spec lookup, health notes, low-current tracking).
- Exposes simple operations: add next, add all, set duty, stop, snapshot.
- All manufacturer groups implement `ManufacturerGroup`.
- Vendor-specific diagnostics (readers + attachments) live under
  `src/main/java/frc/robot/manufacturers/<vendor>/diag/`.
- Device registration is data-driven via `DeviceRegistration` entries; adding a new
  device type only requires adding a new registration entry.

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
1. Device wrappers read raw vendor data into `DeviceSnapshot`.
2. Manufacturer groups enrich snapshots (specs, health notes, low-current flags).
3. `BringupCore` prints reports and publishes JSON using the snapshot list.

This keeps all reporting consistent, even if device implementations change.

## What Stays Stable
- Console output text and ordering.
- JSON report field names.
- NetworkTables keys and paths.
- Profile JSON schema (`bringup_profiles.json`).

## Adding New Hardware
For a step-by-step guide (new motor/controller types), see:
- `ADDING_HARDWARE.md`

## Tradeoffs
- More classes than a single-file approach, but each class is smaller and easier to reason about.
- Some repetition in wrappers, but it keeps vendor details isolated.

## Future Extensions
- Add additional manufacturer groups without changing `BringupCore` behavior.
- Add new report formats without touching device logic.
- Add more device types with minimal risk to existing outputs.
