SPEC_STATUS: PROPOSED

# Feature Spec: Profile Input/Sensor State Report

## Purpose

Purpose: define a shared, profile-scoped report and UI model for current-profile devices that provide state into bringup decisions and DSL tests.

This spec replaces the narrow mental model of `printInputs` as only a controller-axis report.

The intended meaning is:

- current profile only
- supported input/sensor device families only
- operator-readable state before and during bringup
- no output/actuation devices unless they expose explicit input-side state that belongs to this contract

This spec does not implement the feature. It defines the contract for robot report text, UI placement, shared state ownership, and regression expectations.

## Problem

Purpose: capture why the current behavior is insufficient.

The old `printInputs` behavior was hardcoded around motor-family summaries and did not follow the configured profile device list.

The current first-pass fix is better, but it is still incomplete:

- it currently covers only `xboxController` and `limitSwitch`
- it does not yet include other test-relevant sensor families such as `cancoder`, `pigeon`, and `robotController`
- it does not provide enough evidence for risky pre-DSL decisions, especially for limit switches
- its UI presence is effectively limited to `Output`, which makes it harder to inspect alongside other evidence

The operator question this feature must answer is:

- what current-profile devices are providing test-relevant state right now, and does that state look trustworthy enough to proceed?

## Summary Decision

Purpose: state the top-level product decision.

This feature will define `printInputs` as a broader input/sensor state report for the current profile.

It will include these device families in the first supported set:

- `xboxController`
- `limitSwitch`
- `cancoder`
- `pigeon`
- `robotController`

It will not include power devices such as `pdp` and `pdh` in this report.

Those devices remain part of health/power reporting, not input/sensor state reporting.

## Why These Families Belong

Purpose: justify the family selection.

These families all provide state that can influence bringup interpretation or DSL success/failure without being direct actuation targets:

- `xboxController`
  - operator-driven runtime inputs
  - useful for confirming mappings, deadband behavior, and manual control readiness
- `limitSwitch`
  - discrete contact input used directly by DSL completion and safety logic
  - needs stronger pre-test confidence signals than only `pressed=true/false`
- `cancoder`
  - position sensor input used by tests and alignment logic
  - must be visible as current sensor state, not only in a separate encoder-specific text report
- `pigeon`
  - IMU input used for yaw/rotation-based tests and sanity checks
  - belongs in the same high-level “state feeding decisions” surface
- `robotController`
  - platform-local controller state such as input voltage, brownout, CAN status readability, and rail health
  - affects whether the robot-side readings should be trusted at all

## Out Of Scope

Purpose: make the boundary explicit.

Out of scope for this spec:

- adding a new top-level tab
- removing the existing `Health` report
- removing the existing `CANcoder` report
- changing passive CAN truth semantics
- changing DSL signal names or meaning
- adding `pdp` or `pdh` to this report
- implementing SystemCore-specific fields beyond the shared `robotController` family contract

## Contract Name

Purpose: define the operator-facing meaning.

The canonical operator-facing concept is:

- `Inputs` means current-profile input and sensor state relevant to bringup and DSL decisions

It does not mean:

- only human operator controls
- only raw electrical inputs
- all configured devices

It specifically means:

- configured current-profile devices that feed state into tests, evidence, or runtime readiness

## Scope Rule

Purpose: define which devices are included.

The report and UI panel must be scoped to:

- the current profile context used by the robot/runtime
- only supported device families in this contract

The system must not:

- walk unrelated profiles
- include all devices just because they are present in runtime
- include unsupported families as placeholder rows

If a supported family has zero configured devices in the current profile, the corresponding section may be omitted or shown as empty according to the selected surface layout.

## Shared-State Rule

Purpose: prevent drift across surfaces.

The report text and non-`Output` UI surface must consume the same shared state model.

The implementation must not create:

- one formatter for `printInputs`
- one separate host-only panel model for `Evidence`
- one separate ad hoc robot-side state interpretation path

One shared input/sensor state view-model must own:

- current-profile device inclusion
- family grouping
- per-family fields
- state wording
- unknown/unavailable formatting

Surface-specific code may only handle layout and presentation.

## Data Model

Purpose: define the shared row model independent of any one surface.

Each included device row must provide these base fields:

- `label`
- `family`
- `model` when available
- `present`
- `stateConfidence`
- `notes`
- `selected`

Definitions:

- `label`
  - configured device label from the current profile
- `family`
  - shared family name such as `xboxController`, `limitSwitch`, `cancoder`, `pigeon`, `robotController`
- `model`
  - concrete hardware model when available
- `present`
  - robot/runtime-local availability for that family
- `stateConfidence`
  - shared operator-facing confidence token for whether the reported state is trustworthy enough to use
- `notes`
  - short explanatory phrases when state is incomplete, stale, degraded, or not yet proven
- `selected`
  - whether this row matches the current selection in `Evidence`

## State Confidence

Purpose: define one shared confidence vocabulary for this feature.

Allowed values:

- `HIGH`
- `MEDIUM`
- `LOW`
- `UNKNOWN`

Interpretation:

- `HIGH`
  - the device is present and the relevant state is currently readable and sufficiently corroborated for normal bringup use
- `MEDIUM`
  - the device is present and partially trustworthy, but one or more expected corroborations are missing
- `LOW`
  - the device is present or partially present, but the state should not be trusted for risky test decisions
- `UNKNOWN`
  - the system cannot yet determine enough to rate the state

This confidence is not passive CAN presence confidence.

It is a state-interpretation confidence for this input/sensor-state feature.

## Per-Family Fields

Purpose: define the full first-pass data contract.

## Current DSL Coverage

Purpose: record which families already have usable DSL type/signal support and where this spec goes beyond that current contract.

The first-pass device families in this spec are already supported in the DSL type system, either directly or through canonical type aliases.

Current DSL coverage:

- `xboxController`
  - native DSL type: `xboxController`
  - current signal coverage includes:
    - buttons
    - D-pad directions
    - stick axes
    - trigger axes
- `limitSwitch`
  - native DSL type: `limitSwitch`
  - current signal coverage includes:
    - `pressed`
- `cancoder`
  - current DSL normalization accepts `CANCoder` and maps it to canonical type `encoderExternal`
  - current signal coverage includes:
    - `position`
    - `position_actual`
    - `position_delta`
    - `position_delta_max_abs`
    - `velocity`
    - `velocity_actual`
    - `velocity_actual_max_abs`
- `pigeon`
  - current DSL normalization accepts `Pigeon` and maps it to canonical type `imu`
  - current signal coverage includes:
    - `yaw`
    - `pitch`
    - `roll`
    - delta variants
    - max-abs delta variants
    - angular velocity signals
    - acceleration signals
    - `supply_voltage`
    - `faults`
- `robotController`
  - native DSL type: `robotController`
  - compatibility aliases currently include:
    - `roboRIO`
    - `SystemCore`
  - current signal coverage includes:
    - `input_voltage`
    - `brownout`
    - `brownout_voltage`
    - CAN utilization and counter signals
    - 3.3V / 5V / 6V rail voltage signals
    - 3.3V / 5V / 6V rail enabled signals
    - 3.3V / 5V / 6V rail fault-count signals

Important distinction:

- current DSL support means tests can already read relevant core signals from these families
- this spec goes further than the current DSL contract by defining a richer shared report/UI state model
- not every field in this spec is currently exposed as a DSL signal, and that is acceptable

Examples of fields that are part of this spec but not implied by current DSL support:

- `limitSwitch.transitionCountSinceActivate`
- `limitSwitch.lastChangeSec`
- `limitSwitch.proofState`
- shared per-row `stateConfidence`
- report/UI-specific `notes`

Therefore implementation must not assume:

- that every `printInputs` field needs to become a DSL signal
- or that existing DSL support alone is sufficient to satisfy this spec's report/UI contract

### Xbox Controller

Required now:

- `usbPort`
- `present`
- `leftY`
- `rightY`
- `leftX`
- `rightX`
- `leftTrigger`
- `rightTrigger`
- `A`
- `B`
- `X`
- `Y`
- `LB`
- `RB`
- `BACK`
- `START`
- `LS`
- `RS`
- `D_UP`
- `D_RIGHT`
- `D_DOWN`
- `D_LEFT`
- `stateConfidence`
- `notes`

Justification:

- this is the complete practical control-state set already used by the runtime/binding model
- the operator should be able to verify mappings and deadband direction without guessing

### Limit Switch

Required now:

- `dioChannel`
- `present`
- `pressed`
- `invert`
- `lastChangeSec`
- `transitionCountSinceActivate`
- `changedSinceActivate`
- `proofState`
- `stateConfidence`
- `notes`

Allowed `proofState` values:

- `UNPROVEN`
- `PARTIAL`
- `PROVEN`
- `STUCK`
- `UNKNOWN`

Justification:

- plain `pressed=true/false` is not enough before a DSL test depends on the switch
- this family needs explicit “does it seem to be working” data

Meaning:

- `lastChangeSec`
  - seconds since the last observed state transition
- `transitionCountSinceActivate`
  - count of observed state transitions since runtime activation
- `changedSinceActivate`
  - boolean shorthand for whether any edge has been seen
- `proofState`
  - operator-facing summary of whether the switch has been behaviorally proven in the current session

### CANcoder

Required now:

- `canId`
- `present`
- `absolutePositionDeg`
- `absolutePositionRot`
- `velocityRps` when available
- `lastError`
- `stateConfidence`
- `notes`

Justification:

- tests often care that the encoder is alive and producing plausible motion/position state
- the family belongs in this report as a sensor input, not only in a specialized `CANcoder` action

### Pigeon

Required now:

- `canId`
- `present`
- `yawDeg`
- `pitchDeg`
- `rollDeg`
- `angularVelocityXDps` when available
- `angularVelocityYDps` when available
- `angularVelocityZDps` when available
- `accelXG` when available
- `accelYG` when available
- `accelZG` when available
- `lastError`
- `stateConfidence`
- `notes`

Justification:

- bringup often needs one place to check whether the IMU is alive and changing
- the family is input-side telemetry feeding DSL and readiness decisions

### Robot Controller

Required now:

- `present`
- `model`
- `inputVoltage`
- `brownout`
- `brownoutVoltage`
- `canUtilizationPct`
- `canRxErrorCount`
- `canTxErrorCount`
- `canBusOffCount`
- `canTxFullCount`
- `rail3v3Voltage`
- `rail3v3Current`
- `rail3v3Enabled`
- `rail3v3FaultCount`
- `rail5vVoltage`
- `rail5vCurrent`
- `rail5vEnabled`
- `rail5vFaultCount`
- `rail6vVoltage`
- `rail6vCurrent`
- `rail6vEnabled`
- `rail6vFaultCount`
- `stateConfidence`
- `notes`

Justification:

- this family provides the foundation for trusting robot-local readings at all
- it belongs in the same state report because it affects whether sensor readings should be trusted

## Text Report Contract

Purpose: define the `printInputs` output shape.

The report must be grouped by family section, not by raw device list order alone.

Proposed shape:

```text
Inputs:
  Operator Controls:
  controller0 usb=0 present=YES leftY=0.05 rightY=0.06 leftX=0.00 rightX=0.00 LT=0.00 RT=0.00 A=NO B=NO X=NO Y=NO LB=NO RB=NO BACK=NO START=NO LS=NO RS=NO D_UP=NO D_RIGHT=NO D_DOWN=NO D_LEFT=NO confidence=HIGH

  Contact Inputs:
  lmtSw0 DIO=0 present=YES pressed=NO invert=YES changedSinceActivate=YES transitions=3 lastChange=1.2s proof=UNPROVEN confidence=MEDIUM

  Position Sensors:
  cancoder CAN=18 present=YES absDeg=45.2 absRot=0.1256 velRps=0.00 lastErr=OK confidence=HIGH

  IMU Sensors:
  pigeon 2 CAN=19 present=YES yaw=37.1 pitch=0.3 roll=-0.1 velZ=0.0 accelX=0.00 accelY=0.01 accelZ=1.00 lastErr=OK confidence=HIGH

  Controller State:
  roborio present=YES model=roboRIO inputV=12.04 brownout=NO canUtil=18.2% canRxErr=0 canTxErr=0 canBusOff=0 canTxFull=0 rail6vEnabled=YES rail6vFaults=0 confidence=HIGH
```

Rules:

- omit unsupported families entirely
- omit sections with no configured rows, or show them as empty consistently across surfaces
- keep line ordering stable within a family, preferably profile order
- prefer compact values with explicit units

## Evidence Tab Integration

Purpose: define where this appears outside `Output`.

The main non-`Output` home for this feature will be the `Evidence` tab.

This requires `Evidence` to support operator-controlled subpanel visibility so the new panel can fit without forcing all existing panels to remain visible at once.

### New Evidence Subpanel

Purpose: define the added panel.

Add one new Evidence subpanel:

- `Input/Sensor State`

This panel must show:

- all current-profile supported input/sensor devices from this spec
- grouped by family
- with the currently selected device visually highlighted

The panel must not be a selected-device-only view.

It is a current-profile rollup with selection highlighting.

### Evidence Toggle Checkboxes

Purpose: define the visibility-control model.

The Evidence tab must add checkboxes for subpanel visibility.

The target set is:

- Evidence summary table
- Evidence topology/diagram
- Passive CAN evidence text
- Console evidence text
- Enrichment evidence text
- Selected device detail inspector
- Input/Sensor State

These toggles must be:

- remembered in UI preferences
- restored on next UI launch
- independent of profile/config data

They must not be:

- session-only
- stored in robot runtime state
- stored per config or per profile

### Evidence Layout Behavior

Purpose: define how panel layout should behave.

The Evidence tab layout must reflow when panels are hidden.

Required behavior:

- hiding panels should reclaim space for remaining panels
- the new `Input/Sensor State` panel must be able to occupy meaningful vertical space
- the panel should support scrolling when the current profile has many rows
- selected-device highlight must stay synchronized with existing Evidence selection

Recommended behavior:

- preserve current Evidence row/table selection as the authoritative selected device
- clicking a row in `Input/Sensor State` should synchronize selection back into the shared Evidence selected device

## Relationship To Existing Surfaces

Purpose: avoid duplication and contradiction.

### Output

`printInputs` remains the text report command/output path for this feature.

### Evidence

`Evidence` becomes the main persistent visual home outside `Output`.

### Health

`Health` remains focused on faults, currents, temperatures, and low-level health summaries.

It should not become the primary home for this feature.

### CANcoder Action

The specialized `CANcoder` action may remain for focused encoder-only debugging.

It must not disagree with the shared `Input/Sensor State` model on overlapping fields.

## Selection And Synchronization

Purpose: define shared selection ownership.

The authoritative selected device remains the shared Evidence selected device.

The new `Input/Sensor State` panel must:

- highlight the current shared selection when that device is included in the panel
- update the shared selection when the operator clicks a row in the panel

If the selected device is not a supported family in this panel:

- no row is highlighted
- the panel still shows the current-profile rollup

## Failure Handling

Purpose: define degraded-mode behavior.

If a supported family is configured but cannot provide all required fields:

- still show the row
- mark unavailable fields explicitly as unknown or unavailable
- lower `stateConfidence` appropriately
- add a short explanatory note

Examples:

- a `limitSwitch` row with no transition history yet should still show `pressed`, but may remain `proof=UNPROVEN`
- a `pigeon` row missing angular velocity fields may still show yaw/pitch/roll and a note
- a `robotController` row with partial telemetry attachment loss may still show remaining fields with degraded confidence

## Implementation Guidance

Purpose: define the preferred implementation direction.

Implementation should proceed in slices:

1. shared input/sensor state view-model
2. expand `printInputs` to all first-pass families
3. add limit-switch transition/proof state
4. add Evidence subpanel visibility checkboxes with UI-preference persistence
5. add the new `Input/Sensor State` Evidence panel
6. synchronize Evidence selection with the new panel

The order matters because the panel must not invent its own data model.

## Testing Strategy

Purpose: define the verification plan.

### Java Tests

- verify `printInputs` is scoped to current-profile supported families only
- verify unsupported families are omitted
- verify section ordering and per-family field formatting
- verify limit-switch proof and transition-state formatting

### Host UI Tests

- verify Evidence subpanel checkboxes show/hide the correct panels
- verify checkbox state persists in UI preferences
- verify the new `Input/Sensor State` panel uses the shared selected device
- verify clicking the panel changes the shared selected device

### Cross-Surface Tests

- verify `printInputs` and the Evidence panel agree on field meaning and current values
- verify the CANcoder specialized action does not contradict the shared panel on overlapping fields

### Connected Manual Tests

- controller present and button/axis changes appear live
- limit switch changes update `pressed`, transition count, and last-change age
- CANcoder motion updates position values
- Pigeon motion updates yaw or rate values
- robot controller state shows voltage/brownout/rail fields
- Evidence checkbox preferences survive UI restart

## Tradeoffs

Purpose: document deliberate choices.

- Keeping this feature in `Evidence` avoids adding another major top-level surface, but it requires Evidence layout controls.
- Including `robotController` broadens the concept beyond “operator inputs,” but it better matches the real bringup question of whether state feeding decisions is trustworthy.
- Excluding `pdp` and `pdh` keeps the feature focused even though they also produce telemetry.
- Maintaining both a text report and an Evidence panel is acceptable only because they must share one view-model contract.

## Future Extensions

Purpose: record logical follow-ons without expanding current scope.

- add SystemCore-specific `robotController` model fields once hardware-specific support exists
- add additional encoder families beyond `cancoder`
  - examples: integrated motor encoders, external absolute encoders, and future vendor-specific encoder wrappers
  - likely first-pass fields:
    - `present`
    - `positionDeg` when applicable
    - `positionRot`
    - `velocityRps`
    - `lastError`
    - `stateConfidence`
    - `notes`
- add camera and vision-input families
  - examples: USB camera, Limelight-class vision device, and future coprocessor-published vision sources
  - likely first-pass fields:
    - `present`
    - `streamHealthy`
    - `pipeline` or active mode
    - `targetDetected`
    - `latencyMs`
    - `fps` when available
    - `lastError`
    - `stateConfidence`
    - `notes`
  - camera/vision rows should remain state-summary rows in this panel, not full image viewers
- add analog-input families when the product uses them
- add explicit stale-state timers where appropriate for input/sensor state confidence
- add optional sorting or family collapse controls inside the Evidence panel
- add one-click manual prove workflows for limit switches from the new panel

## Definition Of Done

Purpose: define completion for the implemented feature later.

The feature is done when:

- `printInputs` reflects current-profile supported input/sensor families only
- first-pass family coverage exists for `xboxController`, `limitSwitch`, `cancoder`, `pigeon`, and `robotController`
- limit-switch rows include transition/proof-oriented fields defined here
- Evidence has remembered subpanel visibility checkboxes in UI preferences
- Evidence contains a shared `Input/Sensor State` panel showing all current-profile supported rows with selected-device highlight
- shared selection stays synchronized between the new panel and the rest of Evidence
- cross-surface regressions prove the text report and Evidence panel agree on meaning
