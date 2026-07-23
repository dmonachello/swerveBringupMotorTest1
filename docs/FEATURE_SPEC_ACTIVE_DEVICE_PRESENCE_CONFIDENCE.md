SPEC_STATUS: PROPOSED

# Feature Spec: Active Device Presence Confidence

## Purpose

Purpose: define how the bringup project should port in the validated parts of the CAN device presence probe PoC as a new robot-side confidence source for configured CAN nodes.

This feature adds a new source of evidence alongside the existing passive visibility and console-derived diagnostics. It does not replace those existing paths.

## Problem Statement

The current bringup system already has useful CAN-health evidence, but that evidence is incomplete for one important operator question:

"Is the specific configured hardware device I expect in this profile actually present and basically operable right now?"

Today, the project has two important but insufficient sources for that question:

- passive CAN visibility from the PC-side CANable observer
- host-parsed console diagnostics surfaced through explicit host-side diagnostics paths

Those sources are valuable, but neither one alone is a strong defined-node existence test:

- passive traffic does not prove a specific node is healthy
- object construction in vendor APIs does not prove the device exists
- different vendors expose different failure signatures
- stale or cached telemetry can create false positives

The PoC in `C:\Users\dmona\robotDiagPoCs\CAN_bus_test1\CAN_bus_test1\` showed that vendor API probing can be a useful third source when it is:

- non-motion
- freshness-gated
- device-class-specific
- conservative about `unknown`

## Goal

Add a bringup feature that performs a non-motion, robot-side active presence probe for configured CAN nodes and produces a structured confidence result for each target device.

The feature must:

- use the main project's shared VMS status-code system
- remain separate from passive visibility as its own evidence source
- integrate through canonical bringup device/manufacturer layers
- expose reusable signals and evidence to DSL, reports, UI, and other test surfaces
- stay conservative when the evidence does not justify `present` or `absent`
- start as a one-shot UI-triggered operation before any continuous mode is enabled

## Non-Goals

This first bringup feature does not aim to:

- replace the passive CAN visibility system
- perform automatic device discovery
- command motor motion
- add reverse-engineered PC-side CAN decoding as part of the active probe
- guarantee perfect electrical truth from a single probe call
- make `PDP` or `PDH` absence claims stronger than the evidence supports

## Current Sources

The bringup project already has these relevant evidence sources:

### Passive Visibility

Purpose: infer bus/node visibility from the PC-side CANable listener.

Current source:

- host-side visibility provider and related host diagnostics summaries

Strengths:

- live topology awareness
- passive observation
- useful for stale/last-seen/rate-style evidence

Limitations:

- not a reliable defined-node operability test by itself

### Console Diagnostics

Purpose: surface host-parsed roboRIO NetConsole evidence as structured diagnostics.

Current split:

- host parses raw console output
- host stores structured console evidence in explicit host-side diagnostics models
- supported bringup workflows do not depend on NetworkTables transport for this source

Strengths:

- can expose vendor/HAL timeouts and communication warnings
- especially useful when direct API freshness is weak

Limitations:

- not currently the same thing as a direct device API probe
- depends on host-side parser availability and freshness

### New Active Probe Source

Purpose: actively query expected configured devices through vendor APIs without moving hardware.

This feature adds that third source.

## Product Definition

The active device presence confidence feature is a robot-side defined-node probe for expected CAN devices from the loaded bringup configuration.

For each target device, the feature gathers multiple vendor-visible evidence items and assigns one final bucket:

- `present`
- `degraded`
- `absent`
- `unknown`

The result is not a claim of certainty. It is a structured confidence result based on active vendor-side evidence, later designed to be combined with passive visibility and console evidence.

Initial operator workflow:

- operator presses a new UI button to run the active probe once
- results are shown in the right-side UI panel
- no continuous per-loop execution is enabled yet

Later operator workflow:

- after one-shot behavior is debugged and trusted, the mode may be enabled to run every robot 20 ms loop pass like the project's other live modes
- later still, the resulting confidence may become an input to node coloring in the topology diagram

## First-Pass Scope

The first bringup pass should port in the validated one-shot probe behavior only.

In scope:

- one-shot operator-triggered probe behavior from a new UI button
- robot-side vendor API evidence gathering
- per-device structured results
- VMS status-code integration
- canonical device/manufacturer-layer surfacing of reusable evidence
- right-side UI panel output for the new mode
- report and signal exposure for later UI and DSL use

Supported first-pass device classes:

- CTRE `TalonFX`
- REV `SparkMax`
- REV `SparkFlex`
- CTRE `PDP`
- REV `PDH`

Out of scope for this pass:

- automatic background scanning
- passive CAN-sniffer merge logic as part of the probe execution itself
- new host-side CAN transport work
- using the new probe result as the node-color source in the topology diagram
- reverse-engineering unknown CAN frames

## Core Rules

### No Motion

The probe must never command motor motion.

Allowed:

- object construction
- read-only telemetry/status/fault queries
- benign non-motion calls such as sticky-fault clear where the call cannot energize hardware

Disallowed:

- duty-cycle commands
- voltage commands
- closed-loop position or velocity commands
- any API path that could energize a motor

### Freshness Gating Is Mandatory

Telemetry values must not count as positive evidence unless communication freshness for that device class is healthy.

Rules:

- stale/default telemetry must not earn positive points
- known transport failure must block `present`
- weak evidence must be able to land in `unknown`

### Use Shared VMS Status Codes

This feature must use the bringup project's canonical shared status-code pipeline.

It must not keep PoC-local status catalogs as the integration path.

Any required new codes must be added through the main status-code source and regenerated artifacts.

### Surface Evidence Through Canonical Device Layers

When this feature is ported into bringup, any resulting evidence or confidence signal that must be visible to DSL, reports, UI, or other test surfaces must be surfaced through the canonical manufacturer/device layer and directory structure.

The feature must not strand reusable evidence inside:

- a private PoC helper
- a one-off report-only formatter
- a UI-only data path
- a DSL-only shadow implementation

If the current signal set is insufficient, the new signals must be added in the proper manufacturer/device-owned implementation path.

### Runtime Activation Owns Handle Lifetime

Probe device-handle lifetime must be owned by the existing bringup runtime activation and deactivation lifecycle, not by individual probe invocations.

Rules:

- `Runtime Activate` opens and prepares the runtime-owned device handles needed by the probe
- `Runtime Deactivate` closes and releases those runtime-owned device handles
- one-shot probe execution must use the existing active runtime/device ownership path
- continuous every-loop probe execution must reuse the already-open runtime-owned handles
- the probe must not close and reopen devices on each invocation or on each robot loop pass

If the runtime is inactive, the probe action must fail soft rather than temporarily opening its own private handles.

## Source Of Truth

This feature spec is based on two sources together:

- the PoC implementation in `C:\Users\dmona\robotDiagPoCs\CAN_bus_test1\CAN_bus_test1\`
- the completed PoC behavioral/spec text captured during the PoC effort

For port-back decisions, PoC code is treated as the strongest source for:

- what was actually validated
- what failure modes were really observed
- which parts already have workable logic

The PoC text remains the behavioral and architectural intent source.

## Proven PoC Findings

The bringup port should treat these PoC outcomes as established:

- `TalonFX` is PoC-validated for `present` versus `absent`
- `SparkMax` is PoC-validated for `present` versus `absent`
- `SparkFlex` should follow the same REV communication/freshness model, but still needs its own bringup validation pass
- `PDP` is only conservatively valid as `present` versus `unknown`
- `PDH` should be treated analogously to `PDP` until equivalent validation proves a stronger classification

The port must preserve the conservative rule:

- do not strengthen `PDP` or `PDH` from weak/inconclusive evidence into a confident `absent` result without stronger evidence integration

## Architecture

### 1. Defined-Node Target Resolution

Purpose: probe configured devices, not arbitrary ad hoc IDs.

The bringup integration should resolve probe targets from the loaded configuration and current profile membership rather than from hidden hardcoded probe tables.

Minimum target identity:

- `label`
- `vendor`
- `canId`
- `model`

The current PoC target shape is acceptable as the minimal contract:

```java
public record DeviceProbeTarget(
    String label,
    int canId,
    String vendor,
    String model
) {}
```

The production bringup path may adapt from existing config/runtime types such as `BringupUtil.DeviceEntry`, but the active probe should still operate on an explicit per-device resolved target contract.

### 2. Probe Dispatcher

Purpose: keep scoring/orchestration separate from vendor-specific evidence gathering.

The bringup implementation should preserve the PoC split:

- one transport-neutral result model
- one probe dispatcher
- one vendor/device-specific implementation per supported device class

Recommended device-class ownership:

- CTRE motor-controller probe logic under CTRE-owned bringup/manufacturer paths
- REV motor-controller probe logic under REV-owned bringup/manufacturer paths
- power-distribution probe logic under the canonical power-distribution integration path already used by bringup

### 3. Result Model

Purpose: produce one stable, reusable machine-readable contract.

Each per-device result should include at minimum:

- `code`
- `status`
- `message`
- `label`
- `vendor`
- `model`
- `canId`
- `bucket`
- `score`
- `maxScore`
- `evidence[]`
- `warnings[]`
- `errors[]`

Bucket values:

- `present`
- `degraded`
- `absent`
- `unknown`

First-pass score thresholds:

- `present` if score `>= 70`
- `degraded` if score `>= 35` and `< 70`
- `absent` if score `< 35`
- `unknown` when evidence is too weak or stale for a defensible presence call and no stronger hard-failure rule applies

The score is a normalized confidence score, not a probability.

### 4. Surfacing Path

Purpose: make the probe reusable across reports, UI, and DSL.

The bringup port must surface active-probe evidence through common robot-side models rather than isolated feature-specific output strings.

Expected integration surfaces:

- device/manufacturer-owned attachments in diagnostic snapshots
- report JSON emitted from canonical report paths
- DSL-visible signals where the evidence is useful for tests
- UI surfaces that already consume canonical report/runtime data

The feature should prefer extending existing attachment and snapshot structures over creating a parallel per-device reporting tree.

### 5. Evidence Sources

Purpose: define what the active probe may use now and later.

First-pass active probe evidence:

- vendor API construction success
- vendor status-code freshness
- read-only telemetry plausibility
- fault/warning state
- communication timeout/disconnect indicators exposed by APIs

Later mergeable evidence:

- host-parsed console diagnostics from `bringup/diag/console/...`
- passive visibility/topology evidence from the CANable path

The active probe must remain useful even when host-side console evidence is absent.

## Device-Class Rules

### TalonFX

Purpose: use Phoenix signal freshness as the hard gate.

Port the PoC's strong rule set:

- gather a fixed set of Phoenix status signals
- refresh them together
- inspect each signal status
- only allow telemetry-derived points when the critical statuses are `OK`

Expected positive evidence includes:

- successful refresh
- `StatusCode.OK`
- plausible bus voltage
- plausible temperature
- plausible current
- valid position read
- no active faults
- no sticky faults after optional preclear

If the critical Phoenix signal freshness is not healthy, the result must not claim `present`.

### SparkMax And SparkFlex

Purpose: use REV communication status and disconnect behavior as the hard gate.

Port the PoC's REV pattern:

- use safe direct reads already considered acceptable in bringup
- use `getLastError()` and related failure behavior as primary communication evidence
- treat `kCANDisconnected` and equivalent communication failures as strong negative evidence
- only allow telemetry-derived points when communication freshness is healthy

Active and sticky fault/warning data should contribute to `degraded` behavior more than to `absent`, unless communication evidence itself is bad.

### PDP And PDH

Purpose: keep the first pass conservative.

The PoC showed that power-distribution APIs are weaker for definitive absence claims.

Therefore the bringup port should:

- support `PDP` and `PDH`
- allow `present`
- allow `unknown`
- avoid overclaiming `absent` from weak API-only evidence

Until stronger evidence is merged, these classes should remain more conservative than the motor-controller cases.

## Console Evidence Integration

The bringup system already parses raw console output on the host side and publishes structured diagnostics to `bringup/diag/console/...`.

That existing architecture remains correct.

For this feature:

- first-pass active probing may run without console-score fusion
- robot-local visibility of current console evidence is still useful
- later scoring fusion may use host-parsed console events as a second evidence stream

When console evidence is consumed by the robot-side probe or related scoring:

- freshness must be based on robot-local receipt timing
- host/robot wall-clock synchronization must not be required
- repeated identical warnings should be deduplicated in the final result

This is especially important for `PDP` and `PDH`, where console/HAL timeout evidence may be required to move beyond weak API-only classification.

## Status-Code Plan

The bringup port should use the existing status system shape:

- shared status-code source
- generated Java status catalog
- generated status-message mapping
- `StatusRuntime`

Recommended additions:

- session-level `EXECUTOR` completion-with-warnings support if not already present
- per-device `DEVICE` final outcomes for:
  - `PRESENT`
  - `DEGRADED`
  - `ABSENT`
- per-device detail codes for:
  - unsupported model
  - invalid target
  - timeout
  - communication weak/disconnected
  - telemetry invalid
  - faults active
  - warnings active
  - probe exception

The main project should not keep the PoC-local status catalog as the long-term integration path.

## Execution Model

The PoC proved the value of the feature, but it also exposed a performance constraint:

- missing or unpowered devices can make one-shot probing slow enough to overrun if placed naively in `teleopInit()`

Therefore the bringup port must not treat the PoC's `teleopInit()` location as the production design.

Production-first-pass guidance:

- operator-triggered one-shot action from a new UI button
- runtime must already be active
- bounded execution path
- output routed through the shared report runner when printed
- no burst-printing that risks stalling the 20 ms loop

Power-distribution handle lifetime should remain singleton-style and reusable rather than repeatedly constructing and destroying those objects on every probe call.

Inactive-runtime behavior:

- if the operator triggers the probe while runtime is inactive, reject the action with a status/error
- do not auto-activate runtime
- do not open private probe-only device handles as a fallback
- use the existing operator-facing status/banner style already used for conditions such as inactive runtime or disabled robot

Continuous-mode guidance for a later pass:

- continuous execution is not the first integration step
- only enable continuous execution after the one-shot mode is debugged on real hardware
- when enabled, the mode may run every robot 20 ms loop pass like other live robot-side modes
- continuous-mode implementation must still respect loop-budget constraints and may require staged or incremental work rather than a full blocking probe on every pass
- continuous mode must reuse runtime-owned active device handles instead of reopening devices every pass

## UI And Operator Model

This feature should become a new confidence source for defined nodes in the system.

It should remain conceptually distinct from:

- passive live visibility
- topology rendering
- host console parsing

The intended operator model is:

- one-shot active existence/operability test for expected configured devices, triggered from a new UI button
- ongoing passive visibility/topology monitoring from the existing CANable path
- later fused confidence when the evidence-merging rules are mature enough

First-pass UI behavior:

- add a new button that runs the active probe once
- show the resulting structured output in the right-side UI panel
- keep this source visually separate from passive visibility and existing topology coloring
- if runtime is inactive, show an existing-style status/error response instead of running the probe

Later UI behavior:

- reuse this confidence source for node colors in the topology diagram
- optionally combine it with passive visibility and console evidence once the merge semantics are mature

UI surfaces may show these sources separately or in a fused view later, but the data model must preserve source distinction.

## Port-Back Contract

The bringup project should port back these ideas from the PoC:

- per-device active probe contract
- vendor-specific freshness gating
- structured evidence model
- score-and-bucket result model
- explicit `unknown` handling
- separation between one-shot active probing and passive live monitoring

The bringup project should not blindly copy:

- PoC-only filenames
- hardcoded test-target wrappers as the production API
- PoC-local status catalog classes
- print-oriented output paths as the system of record

## Definition Of Done

This feature is done for its first bringup pass when all of the following are true:

- configured target devices can be resolved into an active probe run
- `TalonFX`, `SparkMax`, `SparkFlex`, `PDP`, and `PDH` are supported through canonical bringup ownership paths
- the probe never commands motor motion
- results use the shared bringup VMS status-code model
- reusable evidence is surfaced through canonical manufacturer/device layers
- the result model is available to reports and can be consumed by UI and DSL surfaces without a parallel shadow contract
- `TalonFX` and `SparkMax` preserve PoC-validated `present` versus `absent` behavior
- `PDP` and `PDH` remain conservative when evidence is weak
- missing devices do not crash the run
- probe-triggered output respects the shared report runner and does not rely on burst console printing

## Tradeoffs

- Active probing provides stronger defined-node evidence than passive traffic alone, but it is not passive and can incur timeout cost.
- Conservative `unknown` outcomes are less satisfying to operators than false certainty, but they are more defensible.
- Keeping source distinction between passive visibility, console evidence, and active probe results is more complex than a single fused score, but it preserves diagnostic meaning.
- Surfacing evidence through canonical device/manufacturer paths requires more deliberate integration work up front, but it prevents long-term feature fragmentation.

## Future Extensions

- bounded multi-loop probe windows instead of single blocking probe calls
- continuous enabled mode that runs every robot loop pass
- explicit score fusion with host-parsed console diagnostics
- explicit score fusion with passive visibility/topology evidence
- node-color sourcing from active presence confidence in the topology diagram
- DSL predicates and signals that consume active presence confidence directly
- richer per-device attachments for probe evidence provenance
- stronger `PDP` and `PDH` classification once console and other transport-health evidence are integrated
