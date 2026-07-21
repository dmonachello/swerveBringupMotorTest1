# Feature Spec: Runnable Vs Observed Device Scope

## Purpose

Define a shared device-scope model that separates lifecycle-controlled runnable devices from observed-only diagnostic devices.

This spec is a follow-on to the shared UI context / centralized control refactor. It exists to stop runnable-scope limitations from incorrectly degrading Evidence, Fault Finder, and other diagnostic surfaces for infrastructure devices such as `pdp`.

## Status

SPEC_STATUS: PROPOSED

Implementation sequencing:

- finish Codex thread disaster recovery and refactor-state recovery first
- complete the current shared UI context / centralized control refactor boundary
- then implement this scope-classification model as the next shared-state step

## Problem

The current host-side behavior still conflates several different ideas:

- active-group membership
- lifecycle activation eligibility
- passive observability
- probe-signal availability
- evidence-surface usefulness

That conflation causes bad operator behavior for infrastructure devices.

Examples:

- `pdp` is visible in passive CAN evidence and singleton runtime telemetry, but Evidence tab text still says it was not probed in the current motion-test scope
- `pdp` can show a false-looking conflict merely because it is outside the current active lifecycle scope
- evidence-style tabs inherit runnable-scope limitations that should only apply to control actions

The result is that evidence surfaces understate useful diagnostic information for devices that are not supposed to be part of the active group.

## Goal

Create one shared device classification model so that:

- lifecycle control remains restricted to runnable devices
- evidence and diagnostic surfaces remain useful for observed devices
- scope-based warnings only appear when the device actually depends on lifecycle scope
- UI, topology, CLI, and evidence surfaces consume the same classification contract

## Non-Goals

- making every device eligible for active-group membership
- weakening lifecycle/control safety rules for manual duty or right-click actions
- pretending an observed device has a device-specific active probe result when it does not
- changing robot-side signal availability unless needed to expose an existing signal path cleanly

## Core Principle

Active-group membership gates control.

It does not gate passive observability.

If a device exposes useful diagnostic signals, those signals should be used by evidence/probe flows even when that device is not runnable and is not eligible for active-group membership.

## Proposed Shared Model

### 1. Device Control Scope Kind

Purpose: classify whether a device participates in lifecycle-controlled runnable scope.

Required values:

- `runnable`
- `observed`

Meaning:

- `runnable`
  - eligible for active-group membership
  - eligible for lifecycle activation/deactivation semantics
  - subject to manual/right-click/run gating
- `observed`
  - not eligible for active-group membership
  - still eligible for evidence/diagnostic interpretation
  - must not inherit runnable-only warnings in evidence surfaces

### 2. Device Diagnostic Capability State

Purpose: describe what diagnostic inputs are meaningful for the device.

Fields should include:

- `controlScopeKind`
- `activeGroupEligible`
- `supportsProbeSignals`
- `supportsPassiveEvidence`
- `requiresActiveScopeForProbe`
- `signalRichness`

Recommended `signalRichness` values:

- `none`
- `binary`
- `telemetry`
- `telemetry_faults`

### 3. Device Interpretation Inputs

Purpose: make probe/evidence messaging depend on actual data availability rather than on active-group membership alone.

Shared interpretation should consider:

- passive CAN evidence availability
- singleton runtime telemetry availability
- device-specific probe result availability
- whether the device class is expected to live outside lifecycle scope
- freshness and conflicts across sources

## Classification Rules

### Runnable Devices

Examples:

- motors
- test-scoped actuators
- devices whose right-click/manual/runtime operations are lifecycle-controlled
- limit switches when they are part of runnable test scope

Rules:

- may be included in active-group membership
- may show scope-based probe limitations when the probe truly depends on activation
- keep current manual/right-click safety gating

### Observed Devices

Examples:

- `pdp`
- `pdh`
- `roborio`
- other singleton/global infrastructure devices that expose useful telemetry but are not lifecycle-controlled

Rules:

- not eligible for active-group membership
- remain fully usable in Evidence, Fault Finder, and similar diagnostic surfaces
- do not emit “outside current motion-test scope” as a conflict or limitation unless a specific probe path truly requires scope

## Probe Rules

Purpose: decouple diagnostic signal use from active-group membership.

Required behavior:

- if a device has usable signals, probe/evidence flows should use them
- active-group membership must not be the general gate for consuming those signals
- only show “requires active scope” messaging when that specific probe path actually depends on lifecycle activation

Implications:

- `pdp` should use singleton runtime telemetry and passive evidence even though it is not runnable
- a binary device such as a limit switch may still have a low-richness but valid probe/evidence path

## Evidence Surface Rules

Purpose: stop runnable-only restrictions from degrading evidence surfaces for observed devices.

### For Runnable Devices

Evidence surfaces may say things like:

- device not probed in current motion-test scope
- probe requires activation
- device outside active scope membership

But only when those statements are actually relevant to the probe path being shown.

### For Observed Devices

Evidence surfaces must not frame lack of active-scope membership as a problem by itself.

For example, this kind of text should be removed for `pdp`:

- `Not probed in current motion-test scope.`
- `...even though the current motion-test scope did not include this device`

Instead, messages should describe the real situation:

- no device-specific Full Probe result is available
- singleton runtime telemetry is available
- passive CAN evidence is available, stale, or limited
- current interpretation relies primarily on runtime telemetry or passive evidence

## Conflict And Notes Rules

Purpose: distinguish true conflicts from expected source-layout differences.

### True Conflicts

Examples:

- fresh passive evidence disagrees with fresh runtime/device-specific evidence
- strong device-targeted fault evidence invalidates stale support evidence
- runnable device should have been in scope but was not

### Not A Conflict

For an observed device, this is not a conflict:

- singleton runtime telemetry exists while the device is outside current motion-test scope

That should instead be represented as a source-coverage note.

Example desired wording for `pdp`:

- singleton runtime telemetry is present
- passive CAN observation is stale or limited
- current interpretation relies primarily on runtime telemetry

## UI Surface Requirements

Purpose: keep all surfaces on one shared meaning.

### Active Group / Manual Control Surfaces

- only `runnable` devices are eligible for active-group membership
- `Active Add`, `Active Next`, right-click instantiation, and manual duty remain gated by runnable eligibility

### Evidence Tab

- observed devices remain fully diagnosable
- runnable-only scope limitation text is suppressed for observed devices
- source-coverage messaging must come from shared classification/interpreted state

### CAN Fault Finder

- consume the same shared device classification and interpreted state as Evidence tab
- do not penalize observed devices merely for being outside lifecycle scope

### Topology / Selection Panels

- may show that observed devices are not active-group members
- must not imply that they are diagnostically useless

### CLI

- when surfacing evidence/probe state, use the same runnable-vs-observed semantics
- do not emit scope-based diagnostic warnings for observed devices unless a specific probe path requires scope

## Examples

### Example 1: PDP

Classification:

- `controlScopeKind = observed`
- `activeGroupEligible = false`
- `supportsProbeSignals = true`
- `supportsPassiveEvidence = true`
- `requiresActiveScopeForProbe = false`
- `signalRichness = telemetry_faults`

Expected behavior:

- Evidence tab uses runtime telemetry and passive CAN evidence
- no motion-scope warning just because `pdp` is outside active group
- conflict text focuses on source freshness/coverage, not scope exclusion

### Example 2: Limit Switch

Classification:

- usually `controlScopeKind = runnable`
- `activeGroupEligible = true`
- `supportsProbeSignals = true`
- `supportsPassiveEvidence = limited` by implementation path
- `requiresActiveScopeForProbe = depends on signal path`
- `signalRichness = binary`

Expected behavior:

- may still participate in active-group semantics
- evidence/probe wording should stay narrow and reflect that its signal surface is small, not absent

## Architectural Requirements

### Requirement 1: Shared Classification Owns The Contract

The runnable-vs-observed distinction must be computed in shared code.

No individual surface may maintain its own ad hoc list of “special infrastructure devices.”

### Requirement 2: Evidence Surfaces Must Consume Shared Interpretation

Evidence, Fault Finder, topology side panels, and CLI outputs must consume the same classification and interpretation contract.

### Requirement 3: Control Gating And Diagnostic Gating Must Be Separate

Control gating may depend on active-group membership.

Diagnostic visibility and interpretation must depend on diagnostic capability, not on lifecycle scope alone.

## Implementation Direction

Purpose: sequence the work without mixing it into the still-active recovery/refactor boundary.

### Phase 1: Finish Recovery And Current Refactor Boundary

- finish Codex thread disaster recovery artifacts and recovery confidence work
- complete the current shared UI context / centralized control slice already in progress
- do not mix this device-scope feature into that unstable boundary

### Phase 2: Add Shared Device Capability Classification

Add shared host-side state/service code that classifies each device by:

- control scope kind
- active-group eligibility
- probe-signal support
- passive-evidence support
- active-scope requirement
- signal richness

### Phase 3: Route Evidence Messaging Through Shared Classification

Move Evidence-tab limitation/conflict text behind the shared device capability/interpreted state.

### Phase 4: Align Other Surfaces

Update:

- CAN Fault Finder
- topology selection/details
- CLI evidence/probe reporting

So they all follow the same contract.

## Validation Requirements

Required regression coverage:

- `pdp` is classified as `observed` and not active-group eligible
- Evidence tab for `pdp` does not show current-motion-scope limitation text
- `pdp` conflict/notes text reports source freshness/coverage without treating out-of-scope as a conflict
- runnable devices still preserve existing active-scope gating
- low-richness devices such as limit switches still produce narrow, correct evidence messaging

## Tradeoffs

- Benefit: evidence surfaces become much more useful for infrastructure devices
- Benefit: active-group semantics stay strict for control safety
- Cost: one more shared classification layer to maintain
- Risk: partial implementation could create inconsistent surface behavior
- Mitigation: keep all message decisions in shared state and land regression tests with the first implementation pass

## Related Docs

- `docs/FEATURE_SPEC_SHARED_UI_CONTEXT_AND_CENTRALIZED_CONTROL.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`
- `docs/FEATURE_SPEC_ACTIVE_DEVICE_PRESENCE_CONFIDENCE.md`
- `docs/SPEC_BREAK_AND_ERROR_OPERATOR_SURFACES.md`
