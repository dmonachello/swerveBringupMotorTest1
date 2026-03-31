# Motor Diagnosis Spec (CLI)

## Purpose
Purpose: Define a motor-only diagnosis feature that explains why a motor is not running using existing bringup telemetry.

## Scope
Purpose: Constrain this feature to motor devices and existing telemetry only.
- Motors only (REV/CTRE motor controllers).
- Read-only analysis; no robot state changes.
- Uses existing snapshots/attachments (no new telemetry required).
- Include encoder-based motion checks (internal encoder) in v1.

## Goals
Purpose: Establish the outcomes the feature must deliver.
- Provide a clear, ranked list of likely causes.
- Always show evidence for each conclusion.
- Work with partial data; never crash on missing fields.
- Be deterministic and explainable.

## Non-Goals
Purpose: Prevent scope creep.
- No automatic fixes or control actions.
- No ML or probabilistic inference.
- No non-motor device diagnosis in v1.

## User Experience
Purpose: Define the CLI contract.
- Command:
  - `diagnose motor <label>`
  - `diagnose device <label>` (alias)
- Output:
  - Ranked list of likely causes with confidence and evidence.
  - If insufficient data, return a single `UNKNOWN` conclusion with missing-data notes.

## Label Resolution
Purpose: Make name lookup deterministic and predictable.
- Match order:
  - Exact label match (case-sensitive).
  - Exact label match (case-insensitive).
- If multiple matches remain:
  - Fail and list candidates.
- If no match:
  - Fail with "device not found".
- Canonical key support is reserved for a future extension.

## Data Flow
Purpose: Establish the three-layer analysis pipeline.
1) Raw snapshots (vendor attachments)
2) Normalized motor telemetry (vendor-agnostic)
3) Diagnosis rules (consume normalized data only)

## Power Distribution Integration (PDH/PDP)
Purpose: Define how PDH/PDP telemetry fits the same three-layer pipeline.

### Layer 1: Raw Attachments
Purpose: Capture vendor-specific PDH/PDP snapshots.

- PDH (REV): `pdhStatus` attachment
  - voltage, totalCurrent, temperature
  - switchableEnabled
  - faults + sticky faults
  - per-channel current + breaker faults
- PDP (CTRE): `pdpStatus` attachment
  - voltage, totalCurrent, temperature
  - switchableEnabled
  - faults + sticky faults
  - per-channel current + breaker faults

### Layer 2: Normalized Power Telemetry
Purpose: Present a unified power distribution record.

Normalized fields (common):
- `busV`
- `totalCurrentA`
- `channelCurrentA[]`

Optional fields:
- `temperatureC` (PDH)
- `faultFlags[]`, `stickyFaultFlags[]` (PDH)
- `switchableEnabled` (PDH)

### Layer 3: Power Diagnosis Rules
Purpose: Enable system-level power diagnosis using normalized data.

Planned causes (future):
- `SYSTEM_BROWNOUT`
  - Trigger: low `busV` or PDH/PDP brownout fault.
- `BREAKER_TRIP`
  - Trigger: per-channel breaker fault for a mapped motor channel.
- `POWER_DISTRIBUTION_FAULT`
  - Trigger: PDH/PDP hardware fault flags.

Impact on motor diagnosis:
- Distinguish controller fault vs. power distribution fault.
- Separate "no CAN" from "no power" by checking channel current.
- Correlate motor issues to system brownout conditions.

## Normalized Motor Telemetry
Purpose: Define the vendor-agnostic data contract consumed by diagnosis.

### Shape
```
{
  "label": "Feeder Motor",
  "vendor": "REV|CTRE|UNKNOWN",
  "present": true,
  "power": {
    "busV": 12.1,
    "appliedDuty": 0.20,
    "appliedV": 2.40,
    "cmdDuty": 0.20,
    "motorV": 2.40
  },
  "load": {
    "motorCurrentA": 0.03,
    "tempC": 24.5
  },
  "controller": {
    "lastError": "kOk|...",
    "faultsRaw": 0,
    "stickyFaultsRaw": 0,
    "warningsRaw": 0,
    "stickyWarningsRaw": 0,
    "faultFlags": [],
    "stickyFaultFlags": [],
    "warningFlags": [],
    "stickyWarningFlags": [],
    "faultStatus": "",
    "stickyStatus": "",
    "reset": false
  },
  "limits": [
    { "label": "Feeder Limit", "dio": 0, "invert": false, "closed": true }
  ],
  "encoder": {
    "absDeg": 123.4,
    "velRpm": 0.0,
    "lastError": ""
  },
  "spec": {
    "model": "NEO",
    "nominalV": 12.0,
    "freeCurrentA": 1.3,
    "stallCurrentA": 105.0
  },
  "notes": {
    "healthNote": "lowBusV|lastErr=...",
    "lowCurrentNote": "lowCurrent",
    "snapshotNote": ""
  }
}
```

### Mapping Rules
Purpose: Map vendor attachments into the normalized record.

#### Base snapshot
- `label` ? `DeviceSnapshot.label`
- `vendor` ? `DeviceSnapshot.vendor`
- `present` ? `DeviceSnapshot.present`
- `notes.snapshotNote` ? `DeviceSnapshot.note`

#### REV (`revMotor`)
- `controller.lastError` ? `RevMotorAttachment.lastError`
- `controller.faultsRaw` ? `RevMotorAttachment.faultsRaw`
- `controller.stickyFaultsRaw` ? `RevMotorAttachment.stickyFaultsRaw`
- `controller.warningsRaw` ? `RevMotorAttachment.warningsRaw`
- `controller.stickyWarningsRaw` ? `RevMotorAttachment.stickyWarningsRaw`
- `controller.faultFlags[]` ? `RevMotorAttachment.faultFlags[]`
- `controller.stickyFaultFlags[]` ? `RevMotorAttachment.stickyFaultFlags[]`
- `controller.warningFlags[]` ? `RevMotorAttachment.warningFlags[]`
- `controller.stickyWarningFlags[]` ? `RevMotorAttachment.stickyWarningFlags[]`
- `controller.reset` ? `RevMotorAttachment.reset`
- `power.busV` ? `RevMotorAttachment.busV`
- `power.appliedDuty` ? `RevMotorAttachment.appliedDuty`
- `power.appliedV` ? `RevMotorAttachment.appliedV`
- `power.cmdDuty` ? `RevMotorAttachment.cmdDuty`
- `load.motorCurrentA` ? `RevMotorAttachment.motorCurrentA`
- `load.tempC` ? `RevMotorAttachment.tempC`
- `notes.healthNote` ? `RevMotorAttachment.healthNote`
- `notes.lowCurrentNote` ? `RevMotorAttachment.lowCurrentNote`

#### CTRE (`ctreMotor`)
- `controller.faultsRaw` ? `CtreMotorAttachment.faultsRaw`
- `controller.stickyFaultsRaw` ? `CtreMotorAttachment.stickyFaultsRaw`
- `controller.faultFlags[]` ? `CtreMotorAttachment.faultFlags[]`
- `controller.stickyFaultFlags[]` ? `CtreMotorAttachment.stickyFaultFlags[]`
- `controller.faultStatus` ? `CtreMotorAttachment.faultStatus`
- `controller.stickyStatus` ? `CtreMotorAttachment.stickyStatus`
- `power.busV` ? `CtreMotorAttachment.busV`
- `power.appliedDuty` ? `CtreMotorAttachment.appliedDuty`
- `power.appliedV` ? `CtreMotorAttachment.appliedV`
- `power.motorV` ? `CtreMotorAttachment.motorV`
- `load.motorCurrentA` ? `CtreMotorAttachment.motorCurrentA`
- `load.tempC` ? `CtreMotorAttachment.tempC`

#### Limits (`limits`)
- `limits[]` ? `LimitsAttachment.switches[]`
- `limits[].label` ? `LimitSwitchState.label`
- `limits[].dio` ? `LimitSwitchState.dio`
- `limits[].invert` ? `LimitSwitchState.invert`
- `limits[].closed` ? `LimitSwitchState.closed`

#### Encoder (`encoder`)
- `encoder.absDeg` ? `EncoderAttachment.absDeg`
- `encoder.velRpm` ? `EncoderAttachment.velRpm`
- `encoder.lastError` ? `EncoderAttachment.lastError`

#### Motor spec (`motorSpec`)
- `spec.model` ? `MotorSpecAttachment.model`
- `spec.nominalV` ? `MotorSpecAttachment.nominalV`
- `spec.freeCurrentA` ? `MotorSpecAttachment.freeCurrentA`
- `spec.stallCurrentA` ? `MotorSpecAttachment.stallCurrentA`

## Diagnosis Engine
Purpose: Define deterministic rules that consume normalized telemetry.

### Output Structure
```
[
  {
    "cause": "CAN_BUS_ISSUE|CONTROLLER_FAULT|NO_POWER|LOW_CURRENT|STALL|LIMIT_ACTIVE|NOT_COMMANDED|CONFIG_MISMATCH|UNKNOWN",
    "confidence": "high|medium|low",
    "evidence": ["field=value", ...]
  }
]
```

### Evidence Formatting
Purpose: Keep evidence concise and testable.
- Evidence must be short, atomic `field=value` entries.
- Avoid prose in evidence lists.
- Use string values for lists when needed (e.g., `faultFlags=[Brownout]`).

### Rules
Purpose: List explicit cause triggers.

#### A) CAN bus issue
- Trigger: `present == false`
- Output: `CAN_BUS_ISSUE` (high)
- Evidence: `present=false`

#### B) Controller fault
- Trigger: any controller error/fault flag/status present
  - `controller.lastError` non-empty and not `kOk`
  - `controller.faultFlags[]` not empty
  - `controller.stickyFaultFlags[]` not empty
  - `controller.faultStatus` or `controller.stickyStatus` non-blank
- Output: `CONTROLLER_FAULT` (high)
- Evidence: include `lastError=...` and flag/status lists

#### C) Not commanded
- Trigger: `power.cmdDuty == 0` AND `power.appliedDuty == 0` AND `power.appliedV == 0`
- Output: `NOT_COMMANDED` (high)
- Evidence: `cmdDuty=0`, `appliedDuty=0`, `appliedV=0`

#### D) Limit switch active
- Trigger: motor not running AND any `limits[].closed == true`
- Output: `LIMIT_ACTIVE` (medium)
- Evidence: `limit=<label>`
- Notes: Confidence remains medium unless an explicit interlock is declared.

#### E) Low current under drive
- Guard: Requires drive evidence (at least one of `appliedV`, `appliedDuty`, or `cmdDuty` present).
- Trigger:
  - `power.appliedV >= 1.0`
  - AND `load.motorCurrentA <= lowCurrentThreshold`
- Threshold:
  - If `spec.freeCurrentA` exists: `lowCurrentThreshold = 0.3 * freeCurrentA`
  - Else: `lowCurrentThreshold = 0.05`
- Output: `LOW_CURRENT` (medium)
- Evidence: `appliedV=...`, `motorCurrentA=...`, `threshold=...`

#### F) Stall / mechanical block
- Guard: Requires drive evidence (at least one of `appliedV`, `appliedDuty`, or `cmdDuty` present).
- Trigger:
  - `power.appliedV >= 1.0`
  - AND `load.motorCurrentA >= stallThreshold`
- Threshold:
  - If `spec.stallCurrentA` exists: `stallThreshold = 0.6 * stallCurrentA`
  - Else: fixed fallback
- Output: `STALL` (medium)
- Evidence: `appliedV=...`, `motorCurrentA=...`, `threshold=...`

#### G) No motion under drive (encoder)
- Guard: Requires drive evidence AND encoder velocity present.
- Trigger:
  - `power.appliedV >= 1.0`
  - AND `encoder.velRpm` present
  - AND `abs(encoder.velRpm) <= 1.0`
- Output: `NO_MOTION` (medium)
- Evidence: `appliedV=...`, `velRpm=...`

#### H) No power feed
- Trigger: `power.busV < 6.0` OR `notes.healthNote` contains `lowBusV`
- Output: `NO_POWER` (high)
- Evidence: `busV=...` or `healthNote=lowBusV`

#### I) Config mismatch (additional finding)
- Trigger: label exists on CAN but not in active profile list
- Output: `CONFIG_MISMATCH` (medium)
- Evidence: `profileMissing=true`
- Notes: This is reported as an additional finding, not a primary cause.

#### J) Unknown
- Trigger: none of the above
- Output: `UNKNOWN` (low)
- Evidence: `insufficientEvidence=true`

### Ranking Rules
Purpose: Define ordering when multiple causes trigger.
1. `CAN_BUS_ISSUE`
2. `CONTROLLER_FAULT`
3. `NO_POWER`
4. `LIMIT_ACTIVE`
5. `NO_MOTION`
6. `LOW_CURRENT`
7. `STALL`
8. `NOT_COMMANDED`
9. `UNKNOWN`

### Output Boundaries
Purpose: Prevent noisy output.
- Return all triggered causes internally.
- CLI prints top 3 by default.
- Additional findings (like `CONFIG_MISMATCH`) are printed separately.

### Truthfulness Note
Purpose: Avoid false certainty.
- Multiple causes may be simultaneously true.
- Ranking is operator guidance, not proof.

### Missing Data Handling
Purpose: Ensure graceful output.
- If a field is missing, skip rules that depend on it.
- If all rules are skipped, return `UNKNOWN` with missing-data notes.

## CLI Output Format
Purpose: Provide human-readable output for operators.
```
Likely causes:
1) CONTROLLER_FAULT (high)
   Evidence: lastError=kError, faultFlags=[Brownout]
2) LOW_CURRENT (medium)
   Evidence: appliedV=2.4, motorCurrentA=0.03, threshold=0.39

Additional findings:
- CONFIG_MISMATCH (medium)
  Evidence: profileMissing=true
```

## Examples
Purpose: Ground each conclusion in an example.

### Example: Controller fault
```
Likely causes:
1) CONTROLLER_FAULT (high)
   Evidence: lastError=kError, faultFlags=[Brownout]
```

### Example: Limit switch active
```
Likely causes:
1) LIMIT_ACTIVE (medium)
   Evidence: limit=Feeder Limit
```

### Example: Low current
```
Likely causes:
1) LOW_CURRENT (medium)
   Evidence: appliedV=2.4, motorCurrentA=0.03, threshold=0.39
```

## Tradeoffs
Purpose: Make explicit the intentional compromises.
- Deterministic rules are explainable but may miss nuanced failures.
- Thresholds may need tuning per motor/controller.
- Diagnosis is best-effort and can be wrong when telemetry is incomplete.

## Cause Reference
Purpose: Provide detailed explanations for each diagnosis cause.

### CAN_BUS_ISSUE
Purpose: Explain when the device is not visible on the CAN bus.

Meaning:
- The runtime snapshot reports the device as not present.
- This typically indicates missing CAN traffic for the device.

Data used:
- `present=false` (or `presenceConfidence=0.0`) in runtime-state.

Common reasons:
- Loose/incorrect CAN wiring or termination.
- Device powered off or brownout on the controller.
- Duplicate CAN ID causing collisions.
- Bus traffic is present, but the device is physically disconnected.

What to check:
- Physical CAN chain continuity.
- Power to the controller.
- CAN ID conflicts in the profile.

### CONTROLLER_FAULT
Purpose: Explain controller-reported faults.

Meaning:
- The controller reported a fault, warning, or lastError.
- Includes sticky faults that persist after the event.

Data used:
- `lastError` not equal to `kOk`.
- `faultFlags[]` or `stickyFaultFlags[]` non-empty.
- `warningFlags[]` or `stickyWarningFlags[]` non-empty.
- `faultStatus` or `stickyStatus` non-blank.

Common reasons:
- Brownout or undervoltage events.
- Overcurrent or thermal warnings.
- Controller reset events.

What to check:
- Controller LEDs / vendor fault status.
- Bus voltage and current draw under load.
- Recent resets or power interruptions.

### NO_POWER
Purpose: Explain low bus voltage conditions.

Meaning:
- Bus voltage is below the minimum threshold for reliable operation.

Data used:
- `busV < 6.0`
- or `healthNote` contains `lowBusV` (vendor health note).

Common reasons:
- PDH/PDH breaker off or tripped.
- Severe brownout under load.
- Power wiring issues or loose connections.

What to check:
- PDH/PDH breaker status.
- Bus voltage in runtime state.
- Power distribution wiring.

### LIMIT_ACTIVE
Purpose: Explain limit switch preventing motion.

Meaning:
- A limit switch is closed while motion is expected.
- This may indicate a hard stop or interlock.

Data used:
- `limits[].closed == true`
- Evaluated only when motor is not running (`velRpm` near 0).

Common reasons:
- Mechanism already at its limit.
- Wired limit switch inverted or misconfigured.
- Limit switch intended to be normally-closed.

What to check:
- Physical limit switch state.
- DIO channel mapping and inversion.
- Whether the limit is intended to stop that motor.

### NO_MOTION
Purpose: Explain no encoder movement despite drive command.

Meaning:
- The motor is commanded, but encoder velocity is near zero.
- Indicates commanded drive without measurable motion.

Data used:
- Drive evidence present: `appliedV`, `appliedDuty`, or `cmdDuty` non-zero.
- `abs(velRpm) <= 1.0`

Common reasons:
- Mechanical jam or hard stop.
- Encoder not connected or misconfigured.
- Controller output disabled by internal faults.

What to check:
- Encoder wiring or internal encoder status.
- Mechanical linkage and free rotation.
- Controller status and faults.

### LOW_CURRENT
Purpose: Explain unusually low current while driving.

Meaning:
- Applied voltage is present, but current draw is below expected.
- Indicates the controller is trying to drive, but load is minimal.

Data used:
- Drive evidence present.
- `appliedV >= 1.0`
- `motorCurrentA <= threshold`
  - `threshold = 0.3 * freeCurrentA` if motor spec present
  - otherwise `threshold = 0.05`

Common reasons:
- Motor disconnected from mechanism.
- Broken shaft or coupling.
- Open circuit in motor wiring.

What to check:
- Motor leads and connectors.
- Mechanical coupling to the load.
- Compare to expected free-current for the motor model.

### STALL
Purpose: Explain abnormally high current while driving.

Meaning:
- Applied voltage is present, and current is near stall threshold.
- Indicates the motor is heavily loaded or blocked.

Data used:
- Drive evidence present.
- `appliedV >= 1.0`
- `motorCurrentA >= threshold`
  - `threshold = 0.6 * stallCurrentA` when motor spec present

Common reasons:
- Mechanical jam or hard stop.
- Incorrect gearing or binding.
- Motor stalled against a fixed constraint.

What to check:
- Mechanical obstruction.
- Gearbox alignment.
- Current vs. known stall/current curves.

### NOT_COMMANDED
Purpose: Explain lack of drive command.

Meaning:
- No command duty or applied duty is present.
- The controller is not being asked to move.

Data used:
- `cmdDuty == 0`
- `appliedDuty == 0`
- `appliedV == 0`

Common reasons:
- Test not active or not selected.
- Command never issued or cancelled.
- Driver station disabled.

What to check:
- Test selection state.
- Robot enabled state.
- Controller command source.

### CONFIG_MISMATCH
Purpose: Explain device label not in the active profile.

Meaning:
- Device appears in telemetry but is not present in the profile list.
- Indicates a configuration mismatch rather than a hardware failure.

Data used:
- `label` not found in active profile device list.

Common reasons:
- Wrong profile loaded.
- Device label renamed without updating profile.
- Runtime snapshot from a different robot.

What to check:
- Active profile name.
- bringup_system.json device list.
- Consistency of labels across files.

### UNKNOWN
Purpose: Explain insufficient telemetry.

Meaning:
- There was not enough data to trigger any rule.

Data used:
- One or more required fields are missing (e.g., `appliedV`, `motorCurrentA`, `velRpm`).

Common reasons:
- Missing telemetry fields in the snapshot.
- Device not reporting specific attachments.
- Incomplete or stale data.

What to check:
- Presence of runtime-state attachments.
- Whether the controller reports applied duty/current.
- Whether the encoder is configured for velocity.

## Future Extensions
Purpose: Capture likely next steps.
- Add encoder motion correlation (appliedV but no encoder change).
- Add trend analysis (delta current/temperature over time).
- Add profile-specific thresholds (motor spec based defaults).
- Extend to non-motor devices once motor flow is stable.
- Add scripted analysis plug-ins (post-normalization rule packs or DSL).

