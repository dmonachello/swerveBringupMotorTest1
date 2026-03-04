# Adding New Motor Hardware (New Device Type)

Step-by-step guide for adding a **new motor type** (not just a new CAN ID list) to this project.

Scope: this document covers changes in the Java robot code, profile JSON, and optional PC tool updates.

## Before You Start
Purpose: decide scope, bucket, and whether you need code changes.
- Identify the vendor SDK you will use (REV, CTRE, other?).
- Decide which existing device category this most closely matches:
  - REV: Spark Max (NEO, NEO 550), Spark Flex (Vortex)
  - CTRE: Talon FX (Kraken, Falcon), CANdle, CANCoder
- Decide whether you need a new **device wrapper** (new class) or just a new **motor model** (data-only).

If you are only adding a new motor model for an existing wrapper, skip to **Step 6**.

Current profile buckets (bringup_profiles.json):
- REV: `neos`, `neo550s`, `flexes`
- CTRE: `krakens`, `falcons`, `cancoders`, `candles`
- Singletons: `pdh`, `pigeon`, `roborio`
- Generic: `devices` (vendor/type/id; for non-standard entries)

## Template Reference (Recommended Starting Point)
Purpose: point to safe skeletons for new device work.
If you want a cloneable skeleton, use these template classes:
- `src/main/java/frc/robot/devices/template/TemplateMotorDevice.java`
- `src/main/java/frc/robot/manufacturers/TemplateDeviceGroup.java`

They compile as-is and are intentionally no-op. Clone and replace the internals
with the new vendor SDK calls.

## Step 1: Add a Manufacturer Group (new vendor)
Purpose: register a new vendor-wide device owner.
If this is a **new vendor** (not REV or CTRE), add a manufacturer group that owns all devices for that vendor.

1. Create a new group class:
   - `src/main/java/frc/robot/manufacturers/<Vendor>DeviceGroup.java`
2. Implement the `ManufacturerGroup` interface.
3. Wire it into the bringup flow (see Step 3).

If the vendor already exists (REV/CTRE), skip this step.

## Step 2: Add a Device Wrapper (if the motor needs new SDK calls)
Purpose: implement the SDK-specific device wrapper and diagnostics.
Create a new device wrapper class under:
- `src/main/java/frc/robot/devices/rev/` or
- `src/main/java/frc/robot/devices/ctre/`

For a new vendor, add a new folder:
- `src/main/java/frc/robot/devices/<vendor>/`

Use an existing wrapper as a template:
- REV: `RevSparkMaxNeoDevice`, `RevSparkMaxNeo550Device`, `RevFlexVortexDevice`
- CTRE: `CtreTalonFxDevice`, `CtreCANCoderDevice`, `CtreCANdleDevice`

Checklist for the wrapper:
- Create/close the hardware safely (`ensureCreated()`, `close()`).
- Implement `setDuty()`, `stop()`, `clearFaults()`.
- Build a `DeviceSnapshot` with currents, duty, and status where available.
- Implement the required `RegistrationHeader` (`DeviceUnit.getHeader()`).

If the device has vendor-specific diagnostics, add a reader and attachment under:
- `src/main/java/frc/robot/manufacturers/<vendor>/diag/`
Examples:
- REV: `RevSparkMaxReader`, `RevSparkFlexReader`, `RevMotorAttachment`
- CTRE: `CtreTalonFxReader`, `CtreCANCoderReader`, `CtreCandleReader`, `CtreMotorAttachment`

## Step 3: Register the New Device in the Manufacturer Group
Purpose: make the new device discoverable to BringupCore.
Update the manufacturer group that owns the device type:
- Existing vendors: `RevDeviceGroup`, `CtreDeviceGroup`
- New vendor: your new `<Vendor>DeviceGroup`

Typical changes:
- Add a `DeviceRegistration` entry that references the device header and factory.
- Choose a `DeviceRole` (MOTOR, ENCODER, MISC).
- Set `requiresMotorSpec` if you want warnings for missing motor specs.

## Step 4: BringupCore Integration
Purpose: decide whether BringupCore needs updates for new manufacturer behavior.
BringupCore no longer needs per-device edits once the device is registered in the
manufacturer group. It consumes the registered device list generically.

Only update `src/main/java/frc/robot/BringupCore.java` if you add a new **manufacturer**
group or want custom output (e.g., a new encoder-specific status printout).

## Step 5: Extend Profile Schema in BringupUtil
Purpose: add profile parsing and runtime wiring for the new device bucket.
Update:
- `src/main/java/frc/robot/BringupUtil.java`

Add:
- New ID arrays and label arrays (if a new device list is introduced).
- Parsing support in the `CanProfileConfig` JSON model.
- `setActiveCanProfile()` wiring to populate arrays/labels/motor models/limits.
- `buildDeviceConfigs()` registration for the new bucket or generic type.

## Step 6: Add Manufacturer and Device Type Names
Purpose: keep printed tables readable with human names.
Update:
- `src/main/deploy/can_mappings.json`

If the new device has a new **manufacturer** or **CAN device type**:
- Add the manufacturer ID to `manufacturers`.
- Add the device type ID to `device_types`.

This keeps table output readable.

## Step 7: Add Motor Specs (for health/expectations)
Purpose: provide electrical expectations for health reporting.
Update:
- `src/main/deploy/motor_specs.json`

Add a new motor entry with:
- `model`
- `nominalVoltage`
- `freeCurrentA`
- `stallCurrentA`
- `source`

Then reference that motor model in your profile entry (see Step 8).

## Step 8: Add Profile Entries
Purpose: define the device IDs and labels for a profile.
Update:
- `src/main/deploy/bringup_profiles.json`

Add the new device list under the correct profile name.
Example pattern:
```json
{
  "label": "MY MOTOR 1",
  "id": 42,
  "motor": "My Motor Model Name"
}
```

For new device types that do not fit an existing bucket, prefer the generic `devices` list:
```json
{
  "vendor": "REV",
  "type": "NEO",
  "label": "Example NEO",
  "id": 1,
  "motor": "REV NEO",
  "limits": { "fwdDio": 0, "revDio": 1, "invert": false }
}
```
Set `"invert": true` for normally-closed limit switches so CLOSED/OPEN reads correctly.

If this is a new device category, also update:
- `src/main/deploy/bringup_profiles.template.json`

## Step 9: Update Diagnostics Reporting (if needed)
Purpose: include the new device in text/JSON reporting when required.
If your new device type should appear in new sections or tables, update:
- `src/main/java/frc/robot/DiagnosticsReporter.java`
- `src/main/java/frc/robot/BringupPrinter.java`
- `src/main/java/frc/robot/diag/report/ReportTextBuilder.java`
- `src/main/java/frc/robot/diag/report/ReportJsonBuilder.java`

Keep output schema stable unless you're intentionally adding fields.
If you add telemetry fields, include them under `devices[].attachments` in the JSON report.

## Step 10: Update the PC CAN Tool (optional)
Purpose: add optional PC-side tracking for the new device.
If you want the PC tool to track the new device by default:
- `tools/can_nt_config.json` (recommended)
- `tools/can_profiles.py` bucket mapping (if you add a new profile bucket)

This is not required for robot-side bringup, but helps with CAN visibility.
The PC tool uses `bringup_profiles.json` when `--profile` is specified.

## Step 11: Update Docs
Purpose: keep user-facing documentation consistent.
Update any relevant docs:
- `README.md`
- `ARCHITECTURE.md`
- `tools/README_CAN_NT.md`
- `TESTING.md`

## Step 12: Sanity Checks
Purpose: confirm the new device works end-to-end.
At minimum:
- Run the robot code and verify it prints the new device.
- Confirm the CAN ID validation catches duplicates.
- Verify the diagnostic report includes the new device snapshots.

Optional:
- Set the active profile using one of:
  - JVM property: `-Dbringup.profile=<name>`
  - Env var: `BRINGUP_PROFILE=<name>`
  - CLI flag: `--bringup-profile=<name>`
- Update `tools/can_nt_config.json` and verify PC tool output includes the device.

## Common Pitfalls
Purpose: avoid common integration mistakes.
- Forgetting to add the new device type to profile parsing in `BringupUtil`.
- Updating device wrappers but not adding them to `ManufacturerGroup`.
- Adding new fields without updating JSON schema or docs.
- Forgetting to add motor specs for new current thresholds.

## Quick Decision Guide
Purpose: choose the smallest viable change set.
- New **motor model** but same controller SDK?  
  Data-only: `motor_specs.json` + profile entry.

- New **controller type** or different SDK calls?  
  Code changes: new wrapper + manufacturer group + BringupCore + profile schema.

- New **vendor**?  
  Code changes: new manufacturer group + new device wrappers + can_mappings.json.
