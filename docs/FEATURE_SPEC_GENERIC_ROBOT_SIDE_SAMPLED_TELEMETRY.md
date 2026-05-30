# Feature Spec: Generic Robot-Side Sampled Telemetry

## Purpose

Define a generic robot-side sampled-telemetry system for bursty or timing-sensitive device signals so operator surfaces consume stable processed telemetry instead of sparse instantaneous samples.

## Status

SPEC_STATUS: PROPOSED

## Problem

The current bringup runtime largely reports device telemetry as point-in-time snapshot values.

That works well for slow-changing signals such as:

- temperature
- bus voltage
- presence
- applied duty
- commanded duty

It works poorly for bursty signals such as:

- motor current under low duty or low mechanical load
- future edge-triggered or intermittent fault-like analog signals

Recent testing on a `SPARKMAX/NEO 25` device showed:

- the REV Hardware Client graph displayed non-zero but spiky current
- robot-side `getOutputCurrent()` snapshots often returned `0.0`
- at higher duty the same telemetry path began returning non-zero current

Reference capture:

![REV Hardware Client current graph](</c:/Users/dmona/Pictures/Screenshots/Screenshot 2026-05-30 133943.png>)

That means the root issue is not that Spark current is unsupported.

The root issue is that a single instantaneous sample is the wrong abstraction for operator-facing current telemetry.

The system currently risks misleading operators by over-interpreting sparse samples.

Examples:

- `current_actual = 0.0` at one instant does not prove the motor is drawing no current
- `current_actual > threshold right now` is too brittle for low-duty diagnostics
- UI-side heuristics cannot fix a sampling model problem after the fact

## Goals

- Define a generic sampled-telemetry capability at the robot/device layer.
- Move timing-sensitive telemetry interpretation to the roboRIO, not the host UI.
- Support rolling-window aggregates for any sampled signal, not just Spark current.
- Keep operator surfaces additive and backward-compatible where possible.
- Preserve the distinction between:
  - raw instantaneous values
  - processed recent-window values
- Allow the same processed telemetry to be reused across:
  - runtime-state JSON
  - live topology selection panel
  - future reports
  - future DSL/diagnostics logic
- Keep sampling cost bounded and safe for the 20 ms robot loop.

## Non-Goals

- Do not move signal sampling to the host UI or CLI.
- Do not add a host-side interpretation layer that invents aggregates after transport.
- Do not replace the existing snapshot/report pipeline for all telemetry in one step.
- Do not change NetworkTables ownership rules or CAN sniffer responsibilities.
- Do not treat sampled telemetry as proof of hardware correctness by itself.

## Key Framing

The feature is not "Spark current support."

The feature is "generic robot-side sampled telemetry for signals whose meaning depends on a recent time window rather than a single instantaneous read."

Spark current is the motivating case, not the final scope boundary.

## Design Principles

### Robot Owns Sampling

Purpose: place timing-sensitive signal capture where the real device API and loop timing live.

- The roboRIO owns all sampled telemetry collection.
- The host consumes already-processed values.
- The UI must display processed telemetry and must not derive windowed meaning from sparse instantaneous samples.

### Signal-Centric, Not Vendor-Centric

Purpose: avoid hardcoded per-vendor special cases.

- The system models sampled telemetry as named signals exposed by devices.
- The shared sampler owns windowing and aggregation.
- Device wrappers only provide raw single-read signal suppliers.

This avoids a design like:

- `sampleSparkCurrent()`
- `sampleFalconCurrent()`

Instead the design is:

- device exposes `current_actual`
- device exposes `velocity_actual`
- device exposes `temperature_actual`

The shared sampler treats these generically.

### Aggregates Are First-Class Telemetry

Purpose: define stable operator-facing values for bursty signals.

For sampled signals, processed windowed values are first-class outputs, not ad hoc debug extras.

Examples:

- `currentInstantA`
- `currentAvgA`
- `currentPeakA`
- `currentNonzeroRatio`
- `currentSampleCount`

### Additive Rollout

Purpose: avoid breaking existing surfaces and consumers.

- Existing instantaneous fields may remain during migration.
- New processed fields are added alongside existing fields.
- Surfaces can migrate deliberately from instantaneous to processed values.

## Scope

### Initial In-Scope Signals

Purpose: define the first signals the generic sampler must support.

Initial required support:

- motor current

Initial recommended support when convenient:

- motor velocity
- applied duty
- bus voltage

Velocity, duty, and voltage are not currently the motivating issue, but using the same generic contract for them keeps the design coherent.

### Initial In-Scope Devices

Purpose: define which device families must participate first.

Required first implementation:

- REV Spark MAX / NEO
- REV Spark MAX / NEO 550

Recommended next implementations:

- REV Spark Flex / Vortex
- CTRE TalonFX family

The shared contract must be generic from the start even if only Spark devices implement it initially.

## Proposed Architecture

### Device Capability Layer

Purpose: let devices declare which sampled signals they can provide.

Introduce an optional device capability for sampled telemetry.

Conceptually:

- a device can expose zero or more sampled signals
- each sampled signal has:
  - a canonical signal name
  - a raw single-sample read function
  - optional metadata such as units and validity behavior

Candidate interface shape:

```java
interface SampledSignalProvider {
  Map<String, SampledSignalReader> getSampledSignals();
}
```

Where `SampledSignalReader` conceptually provides:

- `Double readNow()`
- metadata such as units or value kind

The exact Java type names are implementation details.

The important architectural rule is:

- device wrappers provide raw signal reads only
- devices do not own rolling-window math

### Shared Sampler Service

Purpose: own cadence, windows, and aggregate computation in one place.

Add a robot-side service, conceptually:

- `SampledTelemetrySampler`

Responsibilities:

- register `(device, signal)` pairs
- sample them on robot cadence
- maintain rolling windows
- compute processed aggregates
- expose current aggregate values to the rest of robot code

The sampler must be reusable across surfaces and command families.

It must not be embedded inside:

- the UI handler
- the live topology view
- a one-off Spark wrapper helper that bypasses common code

### Runtime Lifecycle Integration

Purpose: align sampling with explicit runtime activation semantics.

The sampler must follow the active runtime lifecycle.

When runtime activates:

- runtime-owned devices that support sampled signals are registered
- app-owned singleton-service devices may also register sampled signals when explicitly included in active runtime reporting

When runtime deactivates or DS disable tears runtime down:

- runtime-owned device registrations are removed
- rolling windows for runtime-owned devices are cleared

This keeps sampled telemetry aligned with the current explicit runtime model.

### Surface Integration

Purpose: keep all operator surfaces using the same processed values.

Initial consumers:

- `showRuntimeState`
- live topology selection panel

Later consumers:

- health/report output
- robot-local diagnostic rules
- DSL/runtime checks where appropriate

The UI should never compute aggregates itself.

## Canonical Signal Names

Purpose: define shared names for sampled telemetry.

Initial canonical names:

- `current_actual`
- `velocity_actual`
- `temperature_actual`
- `bus_voltage`
- `output_percent_applied`

These names should align with existing DSL and runtime vocabulary where possible.

If a surface needs device-type-specific naming, that is an adapter concern.

The sampled telemetry service should use canonical internal names.

## Window and Aggregates

### Window Length

Purpose: define the initial rolling-window behavior.

Initial recommended default window:

- 500 ms

Allowable alternatives during implementation evaluation:

- 250 ms
- 1000 ms

The final default should be documented explicitly in code constants.

The window must be robot-side configurable via constants, not string or numeric literals in executable paths.

### Required Aggregates

Purpose: define the minimum processed outputs per sampled signal.

For current signals, the required outputs are:

- `currentInstantA`
- `currentAvgA`
- `currentPeakA`
- `currentNonzeroRatio`
- `currentSampleCount`

Definitions:

- `currentInstantA`
  - latest raw sample
- `currentAvgA`
  - arithmetic mean over the current rolling window
- `currentPeakA`
  - max absolute current value in the rolling window
- `currentNonzeroRatio`
  - fraction of samples above a nonzero threshold within the window
- `currentSampleCount`
  - number of samples currently represented in the window

Recommended additional fields:

- `currentLastNonzeroA`
- `currentWindowMs`
- `currentTelemetryHealthy`

These are optional in the first implementation.

### Threshold Semantics

Purpose: make nonzero-ratio logic stable and explicit.

The sampler must use a symbolic threshold constant for "nonzero current."

Example concept:

- `CURRENT_NONZERO_THRESHOLD_A`

This threshold is part of the sampling contract and must not be redefined independently by each UI surface.

## Data Contract

### Runtime-State JSON

Purpose: define the robot-to-host contract for sampled telemetry.

Additive fields for motor devices should include:

- `currentInstantA`
- `currentAvgA`
- `currentPeakA`
- `currentNonzeroRatio`
- `currentSampleCount`

Backward-compatible temporary fields may include:

- existing `motorCurrentA`

Recommended migration meaning:

- `motorCurrentA`
  - remains the raw instantaneous reading for compatibility
- `currentInstantA`
  - explicit new name for the same concept
- `currentAvgA`
  - preferred operator-facing stable current field
- `currentPeakA`
  - preferred diagnostic clue for "did current happen recently"

### Selection Panel Contract

Purpose: define what the live topology selection panel should display.

For motor current display:

- the UI should prefer `currentAvgA` or `currentPeakA` according to the chosen operator rule
- the UI may still expose raw instantaneous current in deeper diagnostics later

Recommended first operator-facing rule:

- display `currentAvgA`

Rationale:

- easier to read than `peak`
- less misleading than instantaneous zero

Optional future enhancement:

- show both `avg` and `peak`

Example:

- `Current Avg (A): 1.83`
- `Current Peak (A): 3.11`

### Report Contract

Purpose: define future report alignment.

When integrated into reports, sampled telemetry should be presented as processed windowed values, not as single raw snapshots only.

This is especially important for AI-assisted diagnostics and printed operator interpretation.

## Behavior Rules

### Sampling Cadence

Purpose: keep load bounded and predictable.

The sampler should run once per robot cycle by default.

That means:

- one raw signal read per registered signal per cycle

The sampler must avoid:

- ad hoc burst sampling on every UI request
- request-driven extra reads for host surfaces

### Low-Load and Low-Duty Interpretation

Purpose: avoid invalid conclusions from instantaneous zeros.

The system must not treat:

- `currentInstantA == 0`

as proof that current telemetry is broken or that the motor is inactive.

Instead:

- `currentPeakA > threshold` over the window means current was recently observed
- `currentAvgA` indicates typical recent load
- `currentNonzeroRatio` indicates how often current was observed above threshold

### Moving vs Current Seen

Purpose: support stable higher-level diagnostics later.

Recommended future derived concepts:

- `moving = abs(velRpm) > MOVING_THRESHOLD`
- `currentSeen = currentPeakA > CURRENT_SEEN_THRESHOLD over the active window`

The system should not define:

- `currentSeen = currentInstantA > threshold right now`

### Zero-While-Moving Counters

Purpose: keep the current debug clue in correct context.

The existing "zero while moving" type counters are still useful as a clue that sparse or bursty sampling exists.

They must not be treated as proof that the underlying vendor current telemetry is broken.

## Performance and Safety

### Robot Load

Purpose: clarify where the cost lives.

The additional load is on the roboRIO, not the host.

Expected robot-side cost:

- one raw telemetry read per sampled signal per 20 ms cycle
- small rolling-window bookkeeping

Expected host-side cost:

- none beyond receiving the already-processed values in normal runtime-state payloads

### Loop Safety

Purpose: keep the 20 ms loop budget protected.

The sampler must:

- avoid allocations in the hot path where practical
- use bounded data structures
- avoid console output in the per-cycle path
- avoid request-driven sampling bursts

If later evidence shows the full signal set is too expensive every cycle, the system may:

- sample different signals at different fixed cadences
- but cadence ownership must remain in the shared sampler service

### Failure Behavior

Purpose: keep telemetry fail-soft.

If a raw signal read fails:

- the sampler should preserve system operation
- the specific sampled signal should become unavailable or stale
- runtime-state should fail soft rather than crash command handling

## Lifecycle Ownership Interaction

Purpose: align sampled telemetry with the new device lifecycle ownership model.

Runtime-owned / re-creatable devices:

- sampling registrations are created on runtime activation
- sampling registrations are removed on runtime teardown
- rolling windows are cleared on teardown

App-owned singleton-service devices:

- may expose sampled signals if needed
- but runtime registration still follows active runtime inclusion rules
- the existence of an app-owned singleton must not imply that telemetry remains logically active after runtime deactivation

This preserves the distinction between:

- app-owned underlying service lifetime
- runtime-owned operational telemetry state

## Examples

### Example: Spark MAX Current

Purpose: illustrate the motivating case.

Raw instantaneous samples over 500 ms might be:

```text
0.0, 0.0, 1.8, 0.0, 0.9, 0.0, 3.1, 0.0
```

Meaningful exports:

- `currentInstantA = 0.0`
- `currentAvgA = 0.73`
- `currentPeakA = 3.1`
- `currentNonzeroRatio = 0.375`
- `currentSampleCount = 8`

The operator should not conclude "no current" from the instantaneous zero.

### Example: Diagnostics Rule

Purpose: illustrate future usage.

Bad rule:

```text
if moving and currentInstantA == 0 then current telemetry broken
```

Better rule:

```text
if moving and currentPeakA <= threshold over 500 ms then no meaningful current seen recently
```

That is still not proof of root cause, but it is a much stronger and less misleading clue.

## Rollout Plan

### Phase 1

Purpose: introduce the generic contract and current aggregates.

- add sampled-signal capability at the device layer
- add shared robot-side sampler
- implement current sampling for Spark MAX / NEO devices
- export additive runtime-state fields
- update live topology selection panel to consume processed current telemetry

### Phase 2

Purpose: expand to additional devices and surfaces.

- add Spark Flex
- add TalonFX
- integrate into health/report output
- optionally expose both avg and peak in UI

### Phase 3

Purpose: use sampled telemetry in higher-level diagnostics.

- AI diagnosis/report interpretation
- operator failure explanations
- DSL/runtime heuristics where justified

## Testing Plan

### Unit/Local Validation

Purpose: verify math and contract stability without hardware.

- rolling-window average math
- peak tracking
- nonzero ratio behavior
- sample count bounds
- teardown clears runtime-owned windows

### Robot Validation

Purpose: validate on real hardware with bursty current.

For Spark MAX / NEO:

- run low duty / low load
- run moderate duty / moderate load
- compare runtime-state aggregates against REV Hardware Client graphs

Expected outcomes:

- `currentInstantA` may still hit zero
- `currentAvgA` and `currentPeakA` should track visible current activity
- selection panel should be meaningfully informative at both low and higher duty

### Regression Expectations

Purpose: avoid breaking existing surfaces.

- runtime-state JSON remains valid JSON and additive
- live topology remains responsive
- no loop overrun regressions attributable to the sampler
- no host-side dependency added for current interpretation

## Tradeoffs

### Pros

- correct abstraction for bursty signals
- reusable across vendors and signals
- consistent robot-side meaning across UI/CLI/reports
- less operator confusion than sparse instantaneous reads

### Cons

- additional robot-side sampling cost
- more stateful telemetry infrastructure
- more payload fields in runtime-state
- requires disciplined contract naming to avoid field sprawl

## Open Questions

SID_QUESTION: Should the primary UI current field display `currentAvgA` or `currentPeakA` by default, or should both be shown explicitly?

SID_QUESTION: Should the initial default window be 250 ms or 500 ms for operator-facing current telemetry?

SID_QUESTION: Should the existing `motorCurrentA` field remain indefinitely as the raw instantaneous compatibility field, or be deprecated once all consumers migrate to explicit sampled-current names?

## Future Extensions

- sampled telemetry for voltage, velocity, and temperature on the same service
- stale/validity metadata per sampled signal
- per-signal cadence classes
- sampled telemetry in `bringup_report.json`
- reusable AI/operator diagnosis helpers built on processed windows instead of snapshots
