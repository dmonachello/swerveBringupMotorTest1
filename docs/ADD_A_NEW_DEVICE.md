# Add a New Device (Unknown/New Vendor First)

## Purpose
Describe the steps that are specific to integrating a brand-new device (new vendor/controller or new sensor API). After that, show how to add it to normal Windows config.

## Scope
- **Phase A**: Unknown/new device integration (roboRIO + schema).
- **Phase B**: Standard config once the device is supported.

---

# Phase A: Unknown/New Device Integration (roboRIO + Schema)

## A1) Gather Vendor Facts
Purpose: Collect the minimum info to implement a new controller API.

- Vendor CAN manufacturer ID
- Device type (motor, encoder, gyro, etc.)
- Vendor SDK / WPILib vendor JSON
- Required telemetry signals (current, temperature, position, faults)

---

## A2) Add Vendor Library (roboRIO)
Purpose: Make the vendor API available in Java.

- Add vendor JSON to `vendordeps/`.
- GradleRIO already includes vendor deps via `wpi.java.vendor.java()`.

---

## A3) Create Device Wrapper (roboRIO)
Purpose: Wrap the controller so bringup can drive it.

Create:
- `src/main/java/frc/robot/devices/<vendor>/<VendorDevice>.java`

Implement:
- `DeviceUnit`
- `ensureCreated()`, `close()`
- `snapshot()` and relevant outputs (`setDuty()` for motors, `getPositionRotations()` for encoders, etc.)

Template:
- `src/main/java/frc/robot/devices/template/TemplateMotorDevice.java`

---

## A4) Add Telemetry Attachment + Reader (roboRIO)
Purpose: Normalize vendor telemetry into bringup snapshots.

Create:
- `src/main/java/frc/robot/manufacturers/<vendor>/diag/<Vendor>Attachment.java`
- `src/main/java/frc/robot/manufacturers/<vendor>/diag/<Vendor>Reader.java`

Reference:
- `RevMotorAttachment`, `RevSparkMaxReader`
- `CtreMotorAttachment`, `CtreTalonFxReader`

---

## A5) Register the Vendor (roboRIO)
Purpose: Plug the vendor into the bringup manufacturer system.

1) Add a new manufacturer group:
- `src/main/java/frc/robot/manufacturers/<Vendor>DeviceGroup.java`

2) Register device types via `DeviceRegistration`.

3) Add the group to:
- `src/main/java/frc/robot/manufacturers/ManufacturerRegistry.java`

---

## A6) Add Vendor ID Mapping (roboRIO)
Purpose: Map manufacturer ID to vendor string for routing/labeling.

Edit:
- `src/main/java/frc/robot/BringupUtil.java`

Update:
- Manufacturer ID constants
- Vendor map defaults
- `resolveDeviceVendor(...)`

---

## A7) Optional: Motor Specs (roboRIO)
Purpose: Enable current/health comparisons for motors.

File: `src/main/deploy/motor_specs.json`

Example:
```json
{
  "model": "NovaDrive X1",
  "nominalVoltage": 12.0,
  "freeCurrentA": 2.1,
  "stallCurrentA": 130.0,
  "source": "NovaDrive X1 datasheet"
}
```

---

## A8) Optional: Health/LED/Report Hooks (roboRIO)
Purpose: Surface vendor-specific faults in reports and LEDs.

Update if needed:
- `src/main/java/frc/robot/BringupHealthFormat.java`
- `src/main/java/frc/robot/diag/led/LedStatusInference.java`
- `src/main/java/frc/robot/diag/report/ReportTextBuilder.java`
- `src/main/java/frc/robot/BridgeUiCommandHandler.java`

---

## A9) Verify the New Vendor in Code
Purpose: Confirm the new vendor path works before adding config.

Checklist:
- Device wrapper instantiates successfully.
- Telemetry fields populate in snapshots.
- No vendor API errors on startup.

---

# Phase B: Add the Device to Normal Config (Windows)

## B1) Add Manufacturer Mapping (Windows)
Purpose: Make vendor IDs readable in CLI/UI output.

File: `src/main/deploy/can_mappings.json`

Example:
```json
"manufacturers": {
  "21": "NovaDrive"
}
```

---

## B2) Add Device to Registry (Windows)
Purpose: Define the device once and reference it by label everywhere.

File: `data/bringup_system.json`

Example device entry (motor):
```json
{
  "label": "NovaDrive X1 21",
  "deviceInterface": "CAN",
  "manufacturer": 21,
  "deviceType": 2,
  "id": 21,
  "model": "NovaDrive X1",
  "type": "motor"
}
```

---

## B3) Add Device to a Profile (Windows)
Purpose: Activate the device in a profile.

File: `data/bringup_system.json`

```json
"profiles": {
  "home_030226": {
    "devices": [
      "NovaDrive X1 21"
    ]
  }
}
```

---

## B4) Optional: Add to a Group (Windows)
Purpose: Expose the device in a CLI/UI group.

File: `data/bringup_system.json`

```json
"bridgeConfig": {
  "byProfile": {
    "home_030226": {
      "groups": [
        {
          "name": "motors",
          "enabled": true,
          "members": [
            { "device": "NovaDrive X1 21", "enabled": true }
          ],
          "bindings": []
        }
      ]
    }
  }
}
```

---

## B5) Optional: Add to Tests (Windows)
Purpose: Use the device in bringup tests.

File: `data/bringup_system.json` (under `bridgeConfig.byProfile.<profile>.tests`)

```json
{
  "name": "Spin NovaDrive",
  "enabled": false,
  "motorLabels": ["NovaDrive X1 21"],
  "type": "composite",
  "inputSource": "controller0.A",
  "duty": 0.2,
  "time": { "timeoutSec": 1.0, "onTimeout": "pass" }
}
```

Optional fast path (safe smoke test template for motors):
```powershell
py -m tools.bringup_test_wizard.gen_bringup_tests --profile home_030226 --devices "NovaDrive X1 21" --test-set smoke --replace
python -m tools.validate_sync
```

---

# Sensor Example (Unknown Vendor Encoder)
Purpose: Show what changes for a non-motor device.

### New sensor wrapper (Phase A)
- Implement `getPositionRotations()` in your `DeviceUnit`.
- No `setDuty()` required.
- Telemetry attachment focuses on position/velocity/faults.

### Windows config (Phase B)
```json
{
  "label": "NovaSense Encoder 42",
  "deviceInterface": "CAN",
  "manufacturer": 21,
  "deviceType": 7,
  "id": 42,
  "model": "NovaSense E1",
  "type": "encoderExternal"
}
```

---

## Validation
Purpose: Verify config and runtime behavior.

Windows:
```powershell
python -m tools.validate_sync
```

roboRIO:
- Add device via UI/CLI
- Confirm output changes
- Confirm telemetry fields populate

---

## Tradeoffs
- New vendors require Java integration work.
- Telemetry fields vary by vendor and may require extra adapters.

---

## Future Extensions
- A shared device adapter interface for vendor wrappers.
- UI wizard to add devices without JSON edits.
- Automated vendor ID import for `can_mappings.json`.
