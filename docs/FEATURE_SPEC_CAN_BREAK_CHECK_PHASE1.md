# Feature Spec: CAN Break Check Phase 1

## Purpose

Define the first implementation contract for pit-first CAN bus break diagnosis.

This phase is not the full long-term CAN troubleshooting product.

It is the first production-quality slice that must be reliable, student-usable, and built on one shared diagnosis engine before richer diagram rendering and offline analysis are expanded further.

## Status

SPEC_STATUS: IMPLEMENTATION_READY

## Product Goal

When a student in the pit or back at school runs `Run CAN Break Check`, the system should capture a bounded live observation window, freeze the result, and produce a ranked diagnosis that helps the student inspect the right CAN device or bus region first.

The primary success outcome is:

- identify a single disconnected device when one device is physically removed from the CAN bus
- identify the downstream missing-device set when the CAN bus is clearly broken at a point in the chain

## Primary User

The primary user for this phase is a student operator.

The output must be understandable without requiring an expert to interpret raw passive CAN evidence, console spam, or topology internals.

## Priority Order

Phase-1 development priority is:

1. shared low-level diagnosis correctness
2. operator-facing text output correctness
3. diagram highlighting driven by the same shared diagnosis result
4. baseline/offline compare as a secondary workflow

## Scope

Phase 1 is in scope for:

- pit-first live diagnosis
- manual `Run CAN Break Check`
- bounded observation window with frozen results
- shared diagnosis output consumed by `CAN Fault Finder`, `Evidence`, and `Live Topology`
- ranked top-3 candidates
- missing-device-list output
- incomplete-topology degradation messaging
- topology-backed primary and secondary suspect regions for later diagram rendering

Phase 1 is not in scope for:

- continuous live auto-updating diagnosis
- making operator clues required for the first pass
- relying on a saved baseline for the primary pit workflow
- replacing raw evidence views
- CAN transmission from the PC tool
- overclaiming exact electrical root cause beyond the evidence

## Input Sources

Phase-1 diagnosis combines these sources:

- passive CAN visibility
- topology/profile expected device graph
- robot console evidence
- robot runtime evidence

Operator clues are intentionally deferred to a later phase.

## Evidence Weighting

Until passive CAN message semantics are better understood, robot console/runtime evidence should be treated as more accurate than passive CAN when the sources disagree.

Rules:

- preserve disagreement explicitly
- do not hide the weaker source
- reduce confidence when sources conflict
- prefer console/runtime evidence when ranking candidates

Important exception:

- robot loop-overrun warnings are not direct CAN-break evidence

Loop overruns indicate robot software/runtime timing pressure such as periodic code exceeding the 20 ms control budget.

They may be preserved as runtime-health context, but they must not by themselves promote:

- `bus_path_fault`
- `device_local_fault`
- `bus_wide_error_pressure`

If loop overruns appear alongside true CAN evidence, they may be shown as secondary context only.

## Trigger Model

Diagnosis is triggered manually by the operator through `Run CAN Break Check`.

Phase 1 must not continuously mutate diagnosis in the background.

## Observation Window

`Run CAN Break Check` captures a bounded observation window, then freezes the result.

Phase-1 behavior:

- collect evidence for a short fixed window
- analyze after the window closes
- present a frozen result until the operator runs the check again

SID_COMMENT: The exact default window duration should remain implementation-configurable, but the intended first-pass behavior is approximately 10 seconds.

## Shared-State Rule

`CAN Fault Finder`, `Evidence`, and `Live Topology` must all consume the same shared interpreted-device state and the same shared diagnosis result.

Hard rule:

- no surface may independently recompute the meaning of CAN break candidates
- no surface may invent its own candidate ranking
- no surface may derive separate red/yellow suspect regions from raw evidence outside the shared diagnosis engine

## Fault Classes In Scope

Phase 1 must reason about these fault classes:

- `single_device_unreachable`
- `possible_branch_isolation`
- `possible_trunk_break`
- `possible_controller_side_isolation`
- `bus_wide_error_pressure`
- `intermittent_or_stale_visibility`
- `topology_or_profile_mismatch`

## Unified Diagnosis Model

Phase 1 must use one shared diagnosis engine.

The system should not be split into an independent bus-break detector and an independent device-failure detector that are merged later.

Reason:

- the same evidence often supports both bus-path and device-local explanations
- the same missing-device symptom can come from either category
- separate engines would duplicate logic and make ranking conflicts harder to reason about

Required model:

- one shared evidence model
- one shared inference engine
- one ranked candidate list
- one shared result consumed by all operator surfaces

## Candidate Categories

Although diagnosis should be unified, candidates must still preserve their meaning category.

Phase-1 candidates should include a top-level category such as:

- `bus_path_fault`
- `device_local_fault`
- `configuration_fault`

The exact field name is an implementation detail, but the category meaning must be part of the shared diagnosis contract.

Examples:

- `possible_trunk_break` is a `bus_path_fault`
- `possible_branch_isolation` is a `bus_path_fault`
- `possible_controller_side_isolation` is a `bus_path_fault`
- `bus_wide_error_pressure` is a `bus_path_fault`
- `single_device_unreachable` is usually a `device_local_fault`, unless future evidence explicitly promotes it to a bus-path explanation
- `topology_or_profile_mismatch` is a `configuration_fault`

## Why Categories Matter

The system should not collapse bus-path and device-local explanations into one undifferentiated list.

Students need to know whether the primary recommendation means:

- inspect a bus segment, branch, or controller-side path
- inspect one device and its local connector/power
- verify profile or topology configuration

This keeps operator guidance clear without forcing the implementation into multiple separate reasoning systems.

## Operator Output

The primary operator output is short text first, with later diagram rendering driven by the same result.

The top-level text should answer:

- what the most likely break region is
- which devices appear affected
- why that conclusion was reached
- what to inspect next

Example shape:

```text
Most likely break region: between SPARKMAX/NEO 25 and PDP.
Affected devices: SPARKMAX/NEO 25, CANcoder 26, PDP.
Why: console timeouts and passive visibility agree that devices downstream of SPARKMAX/NEO 25 are missing.
Check next: inspect the CAN connector before SPARKMAX/NEO 25, then rerun CAN Break Check.
```

## Explainability Requirement

Phase 1 must support operator and developer inspection of how a diagnosis was determined.

The system should not return only a final verdict.

It must also preserve an explanation trace that answers:

- what raw inputs were used
- what normalized/interpreted inputs were derived from them
- what intermediate calculations or grouping steps were performed
- which candidate rules matched
- why one candidate ranked above another
- what conflicting evidence reduced confidence

The goal is that a user can ask how the diagnosis was calculated and receive a concrete, inspectable answer rather than a vague summary.

## Explainability Surfaces

Phase-1 explainability should exist at two levels:

- operator-facing explanation
- developer/debug explanation

Operator-facing explanation should remain short and practical.

Developer/debug explanation may be longer and more structured.

Example operator-facing questions:

- Why did it think this was a branch break?
- Why was this only medium confidence?
- Why did it choose a bus-path fault over a device-local fault?

Example developer/debug questions:

- Which evidence rows were considered affected?
- Which sources were missing?
- Which topology grouping step created this region?
- Which rule promoted this candidate to rank 1?
- Which rule demoted another candidate?

## Ranked Candidates

Phase 1 must return multiple ranked candidates rather than forcing one answer.

Default UI behavior:

- show top 3 candidates
- candidate 1 is the primary suspect
- candidates 2 and 3 are secondary suspects

Each candidate must include:

- fault class
- confidence
- suspected region
- affected devices
- supporting evidence
- conflicting evidence
- recommended checks

## Diagram Intent

The diagram is not the first verification surface, but the diagnosis output must already support it.

Required future-facing fields:

- one or more primary suspect regions for red highlighting
- zero or more secondary suspect regions for yellow highlighting

Rules:

- primary suspect regions are red
- secondary suspect regions are yellow
- do not force only one highlighted region when the evidence supports multiple ranked candidates

## Degraded and Incomplete Modes

The system must still run in degraded mode.

If passive CAN is unavailable but console/runtime evidence exists:

- still run diagnosis
- degrade confidence
- explain that passive CAN evidence was unavailable

If console/runtime evidence is unavailable but passive CAN exists:

- still run diagnosis
- degrade confidence
- explain that robot-side evidence was unavailable

If topology is incomplete or wrong:

- still show text candidates
- degrade confidence
- show a clear note:

```text
topology incomplete; region localization limited
```

If the observation window is too weak to localize:

- show top 3 low-confidence candidates when possible
- recommend a concrete bus adjustment before rerunning

Examples of acceptable next-step guidance:

- reseat the connector before the first missing device
- inspect the branch cable at the CANnect node
- verify profile/topology selection
- move the observer or improve robot-side evidence if one source is missing

## Baseline Compare

Baseline compare is a secondary, separately triggered workflow.

Phase-1 interaction model:

- `Run CAN Break Check` is the primary pit workflow
- `Compare To Baseline` is a separate secondary action when a known-good baseline exists

The primary pit diagnosis must not depend on baseline availability.

## Phase-1 Shared Result Contract

The shared diagnosis engine must return one frozen diagnosis object containing:

- overall status
- summary text
- ranked candidates
- affected-device list
- missing-device list
- observation metadata
- source availability and degradation notes
- topology-localization note when applicable
- primary suspect regions
- secondary suspect regions
- explainability trace data

The exact field names are an implementation detail, but the contract must support all of those meanings without requiring per-surface recomputation.

## Explainability Trace Contract

The shared diagnosis result must include enough structured trace data to reconstruct the diagnosis.

At minimum, the trace must preserve:

- raw input summary
  - passive CAN availability and key observations
  - console/runtime availability and key observations
  - topology availability and quality
- normalized per-device state
  - present/missing/degraded/conflicted state
  - relevant source scores or source verdicts
  - reasons attached to that state
- topology-derived calculations
  - affected device grouping
  - connected-region or disconnected-region reasoning
  - missing-device-list derivation
- candidate-generation trace
  - which rules generated each candidate
  - which evidence supported each candidate
  - which evidence conflicted with each candidate
- ranking trace
  - why candidate A ranked above candidate B
  - what increased confidence
  - what reduced confidence

The trace may be represented as structured JSON, structured Python mappings, or both.

The trace must be additive and inspectable.

Hard rule:

- no diagnosis step should exist only in transient local code with no traceable output when that step materially affects ranking or confidence

## Explainability Output Modes

The system should support at least these output modes over time:

- concise result summary
- expanded human-readable explanation
- structured machine-readable trace

Phase 1 does not require every UI surface to expose the full trace immediately, but the shared engine must produce it so surfaces can reveal it without recomputing diagnosis logic.

## Candidate Ranking Rules

Phase-1 ranking rules:

1. prefer targeted single-device or localized chain/branch explanations when evidence is strong
2. prefer broader controller-side or bus-wide explanations when many devices fail together
3. preserve conflicts rather than collapsing them into false certainty
4. lower confidence when topology is incomplete
5. lower confidence when only one major evidence source is available
6. when console/runtime and passive CAN disagree, keep both but weight console/runtime more heavily
7. allow bus-path and device-local explanations to compete in the same ranked list rather than evaluating them in isolation
8. do not claim a device-local hardware failure when the broader evidence better matches a bus-path failure shape

## Must-Pass Real-World Scenarios

These are the first required pass cases for Phase 1.

### 1. Single Device Disconnect

Scenario:

- physically disconnect any one device from the CAN bus

Expected result:

- the diagnosis identifies that device as the primary affected device
- the primary candidate is device-local or the immediate local connector region when topology supports that claim
- the recommended next check points at that device or its immediate connector

### 2. Chain Break With Downstream Loss

Scenario:

- clearly break the CAN bus at one point in the chain

Expected result:

- the diagnosis identifies the downstream missing-device set
- the candidate list reflects a chain/trunk/branch-style failure, not unrelated independent failures
- the recommended next check points near the last-visible / first-missing boundary

## Test Strategy

Phase-1 work should proceed bottom-up.

Required order:

1. strengthen the shared diagnosis engine
2. add automated tests for diagnosis behavior
3. expose that tested diagnosis through text output
4. update diagram rendering to consume the same tested result
5. validate on real robot fault scenarios

Automated tests must cover at minimum:

- healthy baseline
- single missing device
- downstream chain break with missing-device list
- branch isolation
- controller-side isolation
- bus-wide pressure
- incomplete topology
- degraded-source availability
- source disagreement with console/runtime preferred

## Student Usability Bar

Phase 1 is not done until a student can:

1. run `Run CAN Break Check`
2. read the primary text result
3. identify the first connector, device, or bus segment to inspect
4. rerun after an adjustment without expert interpretation of raw evidence

## Definition Of Done

Phase 1 is done when all of the following are true:

- the shared inference engine is the single source of truth for CAN break diagnosis
- `CAN Fault Finder`, `Evidence`, and `Live Topology` consume the same diagnosis result
- top 3 ranked candidates are stable and sensible for the required fault scenarios
- single-device disconnects are identified reliably
- chain breaks identify the downstream missing-device set reliably
- incomplete-topology and degraded-source cases are explained clearly
- baseline compare exists as a separate trigger, even if still simple

## Related Docs

- [FEATURE_SPEC_CAN_BUS_TROUBLESHOOTING_AUTOMATION.md](/c:/Users/dmona/swerve3/docs/FEATURE_SPEC_CAN_BUS_TROUBLESHOOTING_AUTOMATION.md)
- [FEATURE_SPEC_CAN_BUS_DEBUG_FINAL_PUSH.md](/c:/Users/dmona/swerve3/docs/FEATURE_SPEC_CAN_BUS_DEBUG_FINAL_PUSH.md)
- [FEATURE_SPEC_CONSOLE_EVIDENCE_PRIMARY_FAULT_SOURCE.md](/c:/Users/dmona/swerve3/docs/FEATURE_SPEC_CONSOLE_EVIDENCE_PRIMARY_FAULT_SOURCE.md)
- [SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md](/c:/Users/dmona/swerve3/docs/SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md)
- [TEST_PLAN_CAN_FAULT_FINDER_LIVE_MODE_PHASE1.md](/c:/Users/dmona/swerve3/docs/TEST_PLAN_CAN_FAULT_FINDER_LIVE_MODE_PHASE1.md)

## Tradeoffs

- Text-first verification slows visual polish, but it reduces the risk of building attractive wrong answers.
- Manual-trigger frozen diagnosis is less dynamic than live auto-update, but it is easier to reason about in the pit.
- Preferring console/runtime evidence improves current reliability, but it must remain explicit that this is a temporary evidence-weighting choice rather than a permanent truth about all CAN evidence.

## Future Extensions

- operator-clue integration
- stronger passive CAN message semantics
- baseline compare promotion beyond secondary workflow
- richer red/yellow topology overlays
- multi-observer diagnosis
- before/after comparison bundles for reseat and wiggle tests
