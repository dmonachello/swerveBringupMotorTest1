SPEC_STATUS: PROPOSED

# Feature Spec: CAN Device Evidence Source Contracts

## Purpose

Purpose: define the first-pass source contracts for all device-level CAN evidence before any combined fusion mechanism is built.

This spec hardens four evidence sources independently:

- passive CAN visibility
- console-derived diagnostics
- robot-local active vendor probe
- manual stimulus-response test evidence

The goal is to make each source explicit about:

- what it knows
- what it does not know
- how fresh its evidence must be
- how strong its claims are allowed to be
- how its result is represented for later fusion

This document is intentionally pre-fusion. It does not define the final combined scoring mechanism.

## Design Summary

Purpose: state the intended architecture in one compact view.

All four sources gather evidence differently but expose the same consumer-facing result shape.

That means:

- source-specific collection logic remains different
- source-specific semantics remain different
- source-specific result objects remain separate
- the top-level interface presented to consumers is shared

This shared interface allows later analysis code to consume all sources uniformly without flattening their provenance.

The contract standardizes structure, not meaning.

Different sources are still allowed to:

- use different collection methods
- apply different freshness rules
- make different claim strengths
- expose different source-specific evidence rows

## Problem Statement

The project wants one later mechanism that can state with high confidence what devices are on the CAN bus and how they are operating.

That later mechanism will be unreliable if the source semantics remain vague.

Today, the project has multiple useful evidence streams, but they are not yet locked down as formal source contracts:

- passive observation from the PC-side CANable tool
- host-parsed roboRIO console diagnostics
- robot-local vendor API probing
- operator-triggered manual tests such as right-click motor tests

Without source contracts, there is risk of:

- overclaiming what one source can prove
- mixing stale and fresh evidence
- treating absence of evidence as evidence of absence
- collapsing strong negative evidence and weak positive evidence into the same score
- losing provenance when the final fusion layer is added

## Why One Source Is Not Enough

Purpose: explain why the project needs multiple evidence sources rather than searching for one supposed source of truth.

No single source available in this system can reliably answer all three target questions:

- does the expected device exist
- is it operating correctly
- is it the intended device or mapping

for every supported device class and failure mode.

Passive CAN visibility is valuable because it is broad, non-invasive, and always-on when the host observer is present. However, it only tells us that traffic was seen. It does not reliably prove that the expected device is healthy, responsive to control, or even the exact intended mechanism. A device can still produce periodic traffic while being misconfigured, degraded, disconnected from its mechanism, or mapped to the wrong place in the robot.

Console diagnostics are also valuable because they often originate from vendor or HAL code rather than our own interpretation logic. That makes timely parsed console messages high-trust negative evidence in many cases. But console output is still incomplete as a universal truth source. It only tells us about failure modes that produce a message, it depends on parser coverage, and silence in the console is not proof of health. Console is therefore strong for certain failure indications but weak as a complete positive existence or operability source.

Robot-local active vendor probing is stronger for defined-node existence and communication freshness because it queries the expected configured device directly through vendor APIs. Even that is not enough by itself. Vendor APIs differ in quality across device classes, some telemetry can be stale or default-like, some classes are only conservative for absence detection, and a device that answers API calls still may not be the correct physical mechanism or mapping. Active probing tells us a lot about communication and basic status, but not the entire real-world behavior picture.

Manual stimulus-response testing closes an important gap because it introduces intentional causality: we command a target and observe what actually responds. That makes it the strongest source for operability and identity/mapping. Even so, it is not sufficient as the only source because it is operator-driven, not always running, limited to the exercised scenario, and can miss faults that only appear in other modes, loads, or time windows.

The practical conclusion is that there is no single available source in this project that is simultaneously broad, timely, non-invasive, class-agnostic, mapping-aware, and behaviorally conclusive. Reliability therefore comes from combining sources with different strengths and weaknesses, not from pretending one source can do everything. That is why this spec defines separate source contracts first: each source must be explicit about what it can prove before a later fusion layer can combine them responsibly.

## Goal

Define a stable first-pass source contract for each of the four evidence sources so a later combined mechanism can be built on top of known, testable semantics.

Each source contract must define:

- ownership
- timing and freshness rules
- allowed claims for `existence`, `operability`, and `identity/mapping`
- output schema
- limitations and ambiguity rules

## Non-Goals

This spec does not:

- define the final fused confidence algorithm
- define one collapsed cross-source score
- replace current diagnostics outputs immediately
- require that all sources have equal evidence quality
- require that all sources can answer all three target questions strongly

## Target Questions

Each source contract is defined against the same three per-device questions.

### Existence

Purpose: determine whether the expected configured device is actually present on the bus right now.

### Operability

Purpose: determine whether the expected device is functioning, degraded, failing, or non-responsive.

### Identity/Mapping

Purpose: determine whether the observed or responding device is the intended configured device rather than the wrong device, wrong branch, or wrong mechanism.

## Workflow Model

The source contracts are not peer-equal in workflow order.

### Phase 1: Automated First Pass

Purpose: produce the initial per-device view without requiring operator intervention.

Sources in this phase:

- passive CAN visibility
- console-derived diagnostics
- robot-local active vendor probe

This phase should produce an initial structured assessment with explicit gaps where automation cannot justify a stronger claim.

### Phase 2: Manual Refinement Pass

Purpose: add higher-value stimulus-response evidence after the automated first pass.

Sources in this phase:

- manual stimulus-response tests
- operator-observed outcomes
- topology-context outcomes associated with the manual test

This phase is allowed to confirm, downgrade, correct, or sharpen the automated first-pass view.

## Common Result Envelope

Each source keeps its own result object.

The project must not use one mutable all-sources blob as the source-of-truth contract.

Each source-specific result should use this common top-level envelope shape:

```json
{
  "sourceType": "passiveVisibility",
  "sourceVersion": 1,
  "deviceKey": "fl_drive",
  "label": "FL DRIVE",
  "vendor": "REV",
  "model": "SPARK_MAX",
  "canId": 2,
  "capturedAtMs": 1714000000000,
  "windowStartMs": 1713999995000,
  "windowEndMs": 1714000000000,
  "existenceAssessment": {},
  "operabilityAssessment": {},
  "identityAssessment": {},
  "confidence": {},
  "evidence": [],
  "conflicts": [],
  "limitations": []
}
```

### Required Top-Level Fields

- `sourceType`
- `sourceVersion`
- `deviceKey`
- `label`
- `vendor`
- `model`
- `canId`
- `capturedAtMs`
- `windowStartMs`
- `windowEndMs`
- `existenceAssessment`
- `operabilityAssessment`
- `identityAssessment`
- `confidence`
- `evidence`
- `conflicts`
- `limitations`

## Consumer Contract

Purpose: define what a later analyzer, report builder, UI surface, or DSL surface can ask of any source result.

Every source result must allow a consumer to answer the same top-level questions:

- what device is this result about
- when was it captured
- what does this source claim about `existence`
- what does this source claim about `operability`
- what does this source claim about `identity/mapping`
- how strong is each claim
- what evidence supports the claim
- what conflicts or limitations apply

This is the core reason the result envelope is shared across all four sources.

The consumer contract must not imply that all sources mean the same thing.

It only guarantees that all sources can be consumed through the same structural interface.

### Assessment Shape

Each of `existenceAssessment`, `operabilityAssessment`, and `identityAssessment` should use the same internal shape:

```json
{
  "value": "unknown",
  "strength": "weak",
  "reason": "source-specific short explanation"
}
```

### Assessment Value Conventions

Recommended first-pass values:

- existence: `present`, `absent`, `unknown`
- operability: `operable`, `degraded`, `failed`, `unknown`
- identity/mapping: `correct`, `wrong_device`, `wrong_branch`, `unknown`

### Strength Conventions

Recommended first-pass values:

- `strong`
- `moderate`
- `weak`
- `none`

### Evidence Row Shape

Each evidence row should include:

- `code`
- `question`
- `supports`
- `strength`
- `message`
- `observedValue`
- `sourceTimestampMs`

### Conflict Row Shape

Each conflict row should include:

- `code`
- `question`
- `message`
- `severity`

### Limitation Row Shape

Each limitation row should include:

- `code`
- `message`

## Source 1: Passive CAN Visibility

### Purpose

Purpose: infer bus presence and visibility from passively observed CAN traffic on the PC-side host.

### Ownership

Owned and published by the Python host-side tool under `bringup/diag/dev/...` and related `bringup/diag/can/...` paths.

### Timing And Freshness

Freshness is owned by host observation time and rolling last-seen/rate windows.

Primary timing fields:

- host-observed `lastSeen`
- device message counts
- rolling traffic age
- rolling status age where available

This source must never rely on robot-local wall-clock assumptions.

### Allowed Claims

Purpose: define what passive visibility may and may not conclude by itself.

Allowed:

- moderate `existence` claims when device-specific traffic is seen recently and consistently
- weak `operability` claims based on staleness, chatter loss, or suspicious traffic patterns
- weak `identity/mapping` claims when observed traffic aligns with the expected label/device identity contract

Not allowed:

- strong standalone `operability` claims from passive traffic alone
- strong `identity/mapping` claims without stimulus-response evidence
- definitive positive health claims solely from background traffic

### Strength Profile

- existence: moderate positive, moderate negative when expected traffic disappears long enough, otherwise weak
- operability: weak
- identity/mapping: weak

### Source-Specific Evidence Examples

- recent status traffic seen
- recent control traffic seen
- message rate stable
- traffic stale
- expected device missing from observation window
- unexpected label/device observed on the bus

### Source Limitations

- passive traffic does not prove the device is basically operable
- background traffic may persist even when a mechanism is not functioning
- a silent or low-rate device class can produce false absence if timing is poorly tuned
- this source does not by itself prove that the intended mechanism is the one that will respond

## Source 2: Console-Derived Diagnostics

### Purpose

Purpose: surface timely vendor/HAL-originated communication and timeout evidence from roboRIO console output.

### Ownership

Parsed and published by the Python host-side tool.

Consumed by robot-side and UI/report surfaces through `bringup/diag/console/...`.

### Timing And Freshness

Freshness is owned by robot-local receipt timing of the structured console events, not host-origin log timestamps.

First-pass freshness bands:

- `fresh`: `<= 2.0 s`
- `aging`: `> 2.0 s` and `<= 10.0 s`
- `stale`: `> 10.0 s`

Rules:

- fresh console events are high-trust negative evidence when vendor/HAL-originated and specific
- aging events still matter, but with reduced strength
- stale events must not continue to strongly penalize a device
- repeated identical active warnings should be deduplicated for source-level interpretation

### Allowed Claims

Allowed:

- strong negative `operability` claims when fresh vendor/HAL-originated timeout/disconnect/error messages are present
- moderate negative `existence` claims for message classes that strongly imply missing or unreachable device communication
- weak `identity/mapping` claims when a console message names the wrong device class or wrong target identity

Not allowed:

- strong positive `existence` claims from silence alone
- strong positive `operability` claims because console is quiet
- broad claims about devices not referenced by the message or its derived scope

### Strength Profile

- existence: strong negative only for specific fresh message classes, otherwise weak
- operability: strong negative when fresh and specific
- identity/mapping: weak to moderate negative for explicit wrong-device-type messages

### Source-Specific Evidence Examples

- `CAN_TIMEOUT`
- `SPARK_STATUS_TIMEOUT`
- `SPARK_FW_QUERY_FAIL`
- `SPARK_WRONG_DEVICE`
- `HAL_CAN_RECEIVE_TIMEOUT`
- `PDP_STATUS_READER_TIMEOUT`
- `PDH_STATUS_READER_TIMEOUT`
- derived `BUS_FAULT_SUSPECTED`

### Source Limitations

- this source is only as complete as the parser rule set
- wording changes in vendor/HAL output can reduce coverage
- lack of a console event is not proof that the device is healthy
- some messages indicate system-wide pressure rather than one isolated device failure

## Source 3: Robot-Local Active Vendor Probe

### Purpose

Purpose: actively query expected configured devices through runtime-owned vendor APIs without commanding motion.

### Ownership

Owned and generated on the robot side.

This source should surface through canonical runtime/device/manufacturer-owned structures and not only through UI-only output.

### Timing And Freshness

Freshness is owned by the probe session plus vendor/device-class-specific freshness gates.

Rules:

- a probe session is a bounded evidence window
- telemetry-derived positive evidence must be freshness-gated
- stale/default-like values must not earn positive points
- disconnected or failed status refresh must block strong positive conclusions

### Allowed Claims

Allowed:

- strong `existence` claims for supported device classes with healthy freshness and direct vendor communication evidence
- moderate-to-strong `operability` claims when the source can distinguish healthy communication from faults, warnings, or failed reads
- weak-to-moderate `identity/mapping` claims when model/vendor/class alignment is explicit

Not allowed:

- command-motion inference
- strong `identity/mapping` claims about mechanism-level correctness without stimulus-response evidence
- stronger absence claims for device classes whose APIs are known to be weak, such as first-pass `PDP` and `PDH`

### Strength Profile

- existence: strong for validated device classes, conservative for weaker classes
- operability: moderate to strong
- identity/mapping: weak to moderate

### Source-Specific Evidence Examples

- vendor object/handle success
- status refresh success or failure
- communication freshness gate pass/fail
- disconnect indications
- plausible bus voltage/current/temperature
- fault and warning state
- console timeout evidence attached during the probe session when intentionally incorporated

### Source Limitations

- some vendor APIs are stronger than others
- runtime ownership means no claim is possible when runtime is inactive
- this source proves more about device communication and telemetry than about full mechanism correctness
- power-distribution classes require more conservative handling than motor controllers

## Source 4: Manual Stimulus-Response Test Evidence

### Purpose

Purpose: record the result of intentional device- or mechanism-targeted stimulus and the observed response.

This includes right-click/manual motor tests and related targeted manual interventions.

### Ownership

Owned on the robot side as a test-run record.

This source may be augmented by host-side passive and console observations collected during the same test window, but the test run itself is robot-owned.

### Timing And Freshness

Freshness is owned by an explicit test-run window.

Each result must record:

- pre-window start
- command-window start
- command-window end
- post-window end

Any host-side passive or console augmentation used for this source must be tied to the same test window.

### Allowed Claims

Allowed:

- strong `existence` claims when a targeted device responds coherently during the test
- strong `operability` claims when expected command and observed response align
- strong `identity/mapping` claims when the correct mechanism responds or when the wrong mechanism/device/branch responds instead

This source may use:

- machine-observed response
- operator-entered outcome
- topology-context outcome

### Strength Profile

- existence: strong
- operability: strong
- identity/mapping: strong

### Source-Specific Evidence Examples

- commanded duty/voltage/test action issued
- applied duty or applied output observed
- current rose as expected
- velocity or position changed as expected
- no response occurred
- wrong mechanism moved
- wrong branch responded
- intermittent/stuttering response
- operator explicitly confirmed correct target response

### Source Limitations

- this source is only valid when the test target and observation window are recorded clearly
- operator-entered evidence is valuable but must remain structured rather than freeform-only
- some failures may only appear under load or in directions not exercised by the test
- a passing manual test does not prove every mode of the device is healthy

## Implementation Layering

Purpose: define the intended code layering that produces and consumes these source contracts.

The architecture should be layered as follows.

### 1. Device-Dependent Adapters

Purpose: isolate vendor-specific and device-class-specific raw data access.

Examples:

- CTRE motor-controller probe readers
- REV motor-controller probe readers
- PDP and PDH readers
- device-specific telemetry readers used during manual tests

This layer knows how to talk to one device class safely.

It must not own top-level inference.

### 2. Source Orchestrators

Purpose: drive one evidence-gathering workflow for one source.

Examples:

- passive observation windows
- console ingest and event-window handling
- one-shot active probe sessions
- manual stimulus-response test windows

This layer knows when evidence is gathered and what window it belongs to.

It must not directly expose ad hoc output contracts to consumers.

### 3. Source Normalizers

Purpose: convert source-specific raw data into the shared source-result contract.

Examples:

- normalize passive visibility metrics into assessment fields plus evidence rows
- normalize console event sets into assessment fields plus evidence rows
- normalize active probe outputs into assessment fields plus evidence rows
- normalize manual test results into assessment fields plus evidence rows

This layer is the boundary that makes later analysis uniform and testable.

### 4. Normalized Source Result Store

Purpose: retain normalized source results for UI, reports, DSL, logging, and later analysis.

This layer should:

- keep source results separate
- preserve provenance
- expose latest result by source and device
- expose result windows and freshness

This prevents top-level analysis from having to re-read raw vendor or transport data directly.

### 5. Top-Level Analysis

Purpose: consume normalized per-source results and perform higher-level reasoning.

Examples:

- compare agreement and disagreement across sources
- build later combined per-device views
- detect ambiguity and conflicts
- support later fault-localization and recommendation logic

This layer must consume normalized source contracts rather than device-specific APIs or raw console text directly.

## Per-Source Claim Matrix

| Source | Existence | Operability | Identity/Mapping |
| --- | --- | --- | --- |
| Passive visibility | Moderate at best | Weak | Weak |
| Console diagnostics | Strong negative for specific fresh messages, otherwise weak | Strong negative when fresh and specific | Weak to moderate negative for explicit wrong-device clues |
| Active vendor probe | Strong for supported classes | Moderate to strong | Weak to moderate |
| Manual stimulus-response | Strong | Strong | Strong |

## Ambiguity Rules

Each source must be allowed to emit `unknown`.

`unknown` is the correct output when:

- evidence is stale
- the source cannot speak strongly to the question asked
- the source has insufficient coverage for the device class
- the source produced contradictory internal evidence
- the source window is missing or invalid

The source contract must prefer conservative `unknown` over false certainty.

## Provenance Rules

The project must preserve source distinction all the way through the pre-fusion stage.

Requirements:

- no source may overwrite another source's result object
- later combined views must reference source-specific evidence rows
- negative evidence and positive evidence must keep their origin tags
- stale results must remain attributable to their original source and window

## Current Gaps To Close Before Fusion

Purpose: identify remaining work before a reliable combined mechanism is built.

- Passive visibility freshness and absence thresholds need explicit per-device-class review.
- Console parser coverage needs a maintained inventory of known CAN-health-related message families.
- Active vendor probe needs hardware validation and class-specific confidence calibration.
- Manual stimulus-response results need a stable machine-readable test-run contract.
- Identity/mapping evidence vocabulary needs standard codes for wrong target, wrong branch, and no response.

## Definition Of Done

This source-contract stage is done when:

- all four sources have explicit allowed-claim boundaries
- all four sources use the same top-level result envelope
- freshness ownership is defined for each source
- `existence`, `operability`, and `identity/mapping` are defined for each source
- the automated-first-pass then manual-refinement workflow is explicit
- source limitations and ambiguity behavior are documented
- the project can implement later normalization and fusion without guessing source semantics

## Tradeoffs

- Separate source contracts add more up-front structure, but they prevent false certainty later.
- Strong source provenance makes the later combined mechanism more explainable, but it is more work than one quick blended score.
- Manual stimulus-response evidence is operationally heavier than passive automation, but it is the strongest source for operability and identity/mapping.

## Future Extensions

- Add a generated schema artifact for the common source-result envelope.
- Add per-device-class threshold tables for passive absence and active probe freshness.
- Add a source coverage report showing which console message families are currently parsed.
- Define the later normalization layer that turns these four result objects into one combined view.

## Related Docs

- `docs/FEATURE_SPEC_ACTIVE_DEVICE_PRESENCE_CONFIDENCE.md`
- `docs/FEATURE_SPEC_PIT_ROBOT_DIAGNOSIS_FIRST_PASS.md`
- `docs/SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md`
- `docs/NT_CONTRACT.md`
