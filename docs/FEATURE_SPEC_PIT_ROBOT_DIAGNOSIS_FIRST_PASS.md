SPEC_STATUS: RESEARCH_ONLY

# Feature Spec: Pit Robot Diagnosis (First Pass)

## Purpose

Define the first detailed product spec for a pit-side robot diagnosis capability built on:
- multiple passive CAN observers
- topology-aware inference
- operator-supplied field clues
- existing bring-up/diagnostic infrastructure in this repo

This is a first-pass feature spec. It is intended to consolidate the current discussion into one coherent product definition before implementation details are finalized.

## Problem Statement

When a robot fails in the pit, teams need answers quickly:
- Which part of the CAN network is likely broken?
- Is this a local device problem or a propagation/network problem?
- Which branch or segment should we inspect first?
- Which device failed first in sequence?
- What clues observed by humans matter, and how should they be combined with passive CAN evidence?

Today, the project already has many relevant foundations:
- passive CAN observation
- multi-source visibility support
- topology graph concepts (`neighborPorts`, `neighborLinks`, `deviceLinks`)
- workflow awareness
- CLI and UI surfaces
- diagnostics and reporting infrastructure

However, the full pit diagnosis capability is still too large and abstract as one giant feature. The project needs a staged product definition that turns the idea into smaller, coherent capabilities.

## Product Goal

Provide a pit-side diagnosis system that combines:
- topology-aware passive CAN observation from multiple observer points
- robot stimulus/tests when available
- operator-entered field clues

so the system can:
- summarize the evidence coherently
- detect meaningful disagreement and failure patterns
- narrow likely fault regions
- distinguish likely local-node problems from likely bus propagation problems
- recommend the next physical troubleshooting step

## Product Promise

Given:
- a topology model
- one or more passive CAN observers at known locations
- expected devices
- optional focused robot stimulus
- optional operator-observed clues

the system can:
- compare observer views of the same network
- explain disagreement using topology adjacency
- produce candidate fault regions rather than only missing-device lists
- include human field observations in the inference
- guide the operator to the next most useful physical check

## Non-Goals

This feature does not aim to:
- directly measure electrical-layer waveforms
- replace vendor firmware/config tools
- guarantee exact root cause from passive evidence alone
- overclaim certainty when evidence is ambiguous
- require custom low-level hardware beyond supported passive observers

## Feature Framing

This should not be treated as one monolithic implementation.
It is better understood as a ladder of capabilities:

1. Evidence unification
2. Pattern detection
3. Candidate fault localization
4. Workflow guidance
5. UI/visual overlay polish

The first implementation steps should prioritize 1 through 4.

## Core Product Concepts

## 1. Observer
An observer is a passive CAN sniffer attached at a known logical point in the network.

Examples:
- near the roboRIO
- downstream of a CANnect branch
- on a subsystem branch
- near the end of a trunk

Each observer must have:
- `observer_id`
- human-readable label
- attachment point in the topology graph
- availability state
- observation window / rolling metrics

## 2. Topology Graph
The topology graph is the explicit model of expected CAN connectivity.

This feature should use stored topology metadata, not screen coordinates, as semantic truth.

Primary graph data:
- `neighborPorts` (preferred)
- `neighborLinks` (lower-fidelity adjacency)
- `deviceLinks` (CANnect-derived adjacency source)

The graph must support:
- linear adjacency
- branch adjacency
- named ports such as `left`, `right`, `next`, `branch1`, `branch2`
- observer attachment points

Preferred inference graph:
- use `neighborPorts` as the primary graph for inference
- use `neighborLinks` as compatibility or fallback adjacency

## 3. Evidence
Evidence is the full body of information available during diagnosis.

This feature needs three evidence classes:

### A. Passive observed evidence
Examples:
- device visible/not visible by observer
- age/last seen
- message count
- frames per second
- visibility confidence
- bus summary / utilization if available
- visibility changes after stimulus

### B. Topology/model evidence
Examples:
- node adjacency
- branch boundaries
- observer locations
- expected device ordering
- source-of-truth device inventory and profile membership

### C. Operator-supplied clues
Examples:
- LED color/pattern
- first observed failed device in the bus sequence
- last known-good device in sequence
- branch or subtree affected
- symptom appeared after one action or impact
- reseating a connector changed behavior
- device has power but is non-responsive
- downstream devices fail after a specific point

## 4. Pattern
A pattern is an intermediate diagnostic finding based on evidence.

Examples:
- device visible at observer A but not observer B
- branch-only visibility loss
- first failed device is downstream of X
- all downstream devices from node Y affected
- high utilization coincides with observer disagreement
- LED clue conflicts with expected device state

Patterns are not final diagnoses. They are structured intermediate findings.

## 5. Candidate Fault Region
A candidate fault region is the smallest interval or branch the system can credibly identify.

Possible forms:
- between observer A and observer B
- between node X and node Y
- downstream of node X on port `branch1`
- on subtree rooted at node N
- localized only to a branch, not the whole bus

The system should always express fault regions at the highest confidence level the evidence supports, and no stronger.

## 6. Workflow Guidance
The system should not stop at evidence or patterns.
It should recommend the next practical action.

Examples:
- inspect connector between node X and node Y
- verify branch1 cable seating
- move observer to downstream branch
- run one focused motor stimulus on device Z
- confirm LED state on the first failed device
- reseat the suspected connector and rerun observation window

## Supported Diagnostic Classes

The feature should support these major classes of diagnosis.

### Node-Level
- `present`
- `missing`
- `stale`
- `responding_to_stimulus`
- `not_responding_to_stimulus`
- `unexpected_node_or_id`

### Observer/Topology-Level
- `inconsistent_visibility`
- `possible_break_between_observers`
- `possible_break_between_segments`
- `possible_branch_isolation`
- `possible_topology_model_mismatch`
- `insufficient_observer_coverage`

### Bus-Condition-Level
- `high_bus_utilization`
- `localized_high_load_suspected`
- `high_error_region_suspected`
- `diagnostics_ambiguous`

### Clue-Driven Interpretation Classes
- `first_failure_boundary_observed`
- `last_known_good_boundary_observed`
- `led_state_consistent_with_fault_region`
- `led_state_conflicts_with_visibility`
- `branch_symptom_boundary_observed`

## Supported Operator Clue Types

Operator clues should be structured where possible.

## A. Device-local clues
Examples:
- LED color
- LED pattern
- power present / absent
- device hot / warm / cold unexpectedly
- local motion failure
- intermittent response
- wrong-direction response
- reboot/reset observed

## B. Sequence / boundary clues
Examples:
- first observed failed device in sequence
- last known-good device in sequence
- all devices downstream of X affected
- branch `branch1` affected, `branch2` healthy
- first recovered device after reseating connector

## C. Event / timing clues
Examples:
- failure started after enabling
- failure started after one stimulus/test
- failure started after impact
- reseating connector changed behavior
- failure occurs only under movement/load

## D. System/global clues
Examples:
- only one subsystem affected
- multiple devices flicker together
- power stayed on while CAN behavior degraded
- control degraded before visibility fully disappeared

## Operator Clue Model

Clues should not be only freeform notes.
A structured model should exist.

Conceptual shape:

```python
@dataclass
class OperatorClue:
    clue_type: str
    target_kind: str | None      # device / segment / branch / observer / system
    target_id: str | None
    value: str | dict | list
    confidence: str              # low / medium / high
    timestamp_ms: int | None
    notes: str = ""
```

Examples:

```json
{
  "clue_type": "first_failure_in_sequence",
  "target_kind": "device",
  "target_id": "FL TURN",
  "value": "first_failed",
  "confidence": "medium"
}
```

```json
{
  "clue_type": "led_pattern",
  "target_kind": "device",
  "target_id": "FL DRIVE",
  "value": {
    "color": "red",
    "pattern": "blink"
  },
  "confidence": "high"
}
```

Freeform notes are still allowed as fallback, but structured clues should be preferred whenever the UI/CLI can guide the user.

## Inputs Required

## A. Topology inputs
- topology graph
- observer attachment points
- expected devices
- branch/port relationships
- source-of-truth profile context

## B. Observation inputs
Per observer:
- source ID
- availability
- observed device visibility
- age
- message count
- frames per second
- optional bus summary/utilization metrics

## C. Optional stimulus inputs
- selected test or action
- expected affected devices or segments
- observation window before and after stimulus

## D. Optional auxiliary inputs
- robot-local diagnostics
- console-derived warnings/errors
- selected/active runtime context
- operator clues

## Observation Windows

Comparisons should be tied to a defined observation window.

Supported modes may include:
- rolling recent window
- fixed capture window
- pre/post stimulus window
- manual rerun comparison window

The system should avoid comparing observers from mismatched or stale windows without warning.

## Evidence Unification Layer

The first implementation milestone should unify evidence into a single model.

This layer should:
- collect per-observer visibility
- collect observer metadata and attachment points
- collect operator clues
- collect optional stimulus context
- collect optional local runtime diagnostics
- normalize the evidence into one coherent diagnostic input object

This layer does not need to diagnose anything yet.
It should make the evidence trustworthy and reusable.

## Pattern Detection Layer

After evidence unification, the next stage should detect intermediate patterns.

Examples:
- visible at A but not B
- local branch-only visibility
- first failure downstream of a branch point
- operator clue boundary matches observer disagreement
- elevated bus utilization during failure window
- observer disagreement inconsistent with topology assumptions

Pattern output should be explicit and structured.

## Candidate Fault Localization Layer

This stage turns evidence + patterns into candidate fault regions.

The inference layer should answer:
- Is the issue more likely local device or propagation issue?
- Is there a likely break interval between observers or topology nodes?
- Is a branch likely isolated?
- Is the result more likely a topology-model mismatch than a physical break?
- Is there enough evidence to recommend a next physical check?

This stage should be conservative and ambiguity-aware.

## Workflow Layer

This feature must be expressed as a workflow, not just as reports.

## Workflow: Pit Robot Diagnosis

1. Load topology and expected devices.
2. Confirm observer source locations.
3. Start or refresh observation window.
4. Optionally run one focused stimulus/test.
5. Enter any observed field clues.
6. Build evidence summary.
7. Detect patterns.
8. Infer candidate fault region(s).
9. Present next recommended checks.
10. Let the operator rerun after physical changes.

The workflow should support both:
- active pit diagnosis on a troubled robot
- structured subsystem diagnosis during bring-up or after repairs

## Workflow States

The pit diagnosis workflow should expose states such as:
- `ready`
- `insufficient_observer_coverage`
- `awaiting_clues`
- `awaiting_stimulus`
- `analysis_ready`
- `ambiguous`
- `candidate_region_found`

## CLI Requirements

The CLI should eventually support:
- listing observers and attachment points
- showing observer-by-device visibility matrix
- showing topology neighbor view with observer context
- entering structured operator clues
- showing detected patterns
- showing candidate fault regions
- dumping structured JSON for regression and analysis
- rerunning after physical changes

Important CLI product requirement:
- operator clues should be easy to enter, not cumbersome
- the CLI should guide the user toward structured clues when possible

## UI Requirements

The UI/live topology view should eventually support:
- observer placement display
- per-observer visibility overlays
- branch/segment disagreement highlighting
- candidate fault-region highlighting
- clue entry forms or compact dialogs
- display of recommended next physical checks
- display of ambiguity/confidence clearly

## Output Model

The system should produce structured outputs useful to both humans and tools.

Each candidate diagnosis should include:
- diagnosis type
- fault region
- confidence
- evidence list
- ambiguity notes
- operator clue contributions
- recommended next checks

Conceptual output shape:

```json
{
  "type": "possible_break_between_segments",
  "region": {
    "from": "CANNECT_A.branch1",
    "to": "observer_end"
  },
  "confidence": "medium",
  "evidence": [
    "FL TURN visible at observer_mid but not observer_end",
    "First observed failed device in sequence: FL TURN",
    "Devices on branch2 still visible and responsive"
  ],
  "clues": [
    "Operator reported blinking red LED on FL TURN"
  ],
  "recommendedChecks": [
    "Inspect branch1 connector after CANnect A",
    "Reseat branch1 cable and rerun 10-second observation window"
  ]
}
```

## Confidence Model

Confidence should be qualitative at first:
- `low`
- `medium`
- `high`

Confidence should consider:
- number of agreeing observers
- number of affected devices
- topology clarity
- observer placement certainty
- consistency of operator clues
- presence/absence of stimulus correlation
- ambiguity caused by sparse or conflicting evidence

The system should prefer conservative confidence.

## Ambiguity Handling

Ambiguity is a first-class result.

The system should explicitly report ambiguity when:
- observer coverage is too sparse
- topology model is incomplete or uncertain
- operator clues conflict strongly with passive evidence
- multiple fault regions fit the same evidence
- observer placement is uncertain
- high error behavior is suspected but not localizable

Example ambiguity classes:
- `insufficient_observer_coverage`
- `possible_topology_model_mismatch`
- `multiple_candidate_fault_regions`
- `clue_conflict_requires_manual_review`

## High Error Rates And Bus Stress

The system should treat high error behavior as a supported diagnosis area even when the underlying hardware does not expose full electrical-layer details.

At first, `high_error_region_suspected` may be inferred from:
- unstable visibility across observers
- repeated stale/recover cycles
- elevated utilization
- inconsistent visibility after stimulus
- console/runtime warnings if available
- operator clues such as intermittent branch behavior or LED fault patterns

This means the first implementation can support useful suspicion without pretending to measure true wire-level error counters.

## MVP Definition

The first useful pit diagnosis MVP should include:

1. Multiple observer definitions and attachment points
2. Observer-by-device visibility comparison
3. Structured operator clue entry for:
   - first failed device
   - last known-good device
   - affected branch/subtree
   - LED color/pattern clues
4. Candidate fault region output
5. Recommended next physical checks

This MVP does **not** need:
- perfect UI polish
- full automatic confidence modeling
- every possible clue type
- perfect high-error localization

## Architecture Fit

### Hardware and Transport Layer
- multiple passive observers
- CAN frame capture
- observer availability

### Adapter and Protocol Layer
- per-observer ingestion
- topology parsing
- observer attachment parsing
- clue normalization

### Domain Logic Layer
- evidence normalization
- pattern detection
- candidate region inference
- confidence and ambiguity logic

### Workflow and Application Service Layer
- pit diagnosis workflow
- observer readiness
- clue collection guidance
- rerun-after-change guidance

### Presentation Layer
- CLI matrices and summaries
- UI/topology overlays
- clue-entry surfaces
- next-step guidance

### Contract Layer
- topology observer-attachment schema
- clue schema
- diagnostic output schema
- stable meaning for candidate fault region, confidence, and ambiguity

## Existing Project Foundations To Reuse

This feature should build on existing foundations rather than invent a parallel system.

Relevant existing foundations include:
- topology adjacency (`neighborPorts`, `neighborLinks`, `deviceLinks`)
- topology parsing helpers
- multi-source visibility concepts
- operator surfaces (CLI/UI)
- reporting/diagnostics infrastructure
- workflow direction already established for bring-up

Preferred graph for inference:
- `neighborPorts`

Preferred overall architectural pattern:
- shared evidence model
- shared pattern model
- shared candidate diagnosis model
- workflow-driven presentation

## Risks And Tradeoffs

- Incorrect observer placement metadata can produce false localization.
- Incomplete topology can make correct observations look contradictory.
- Too much freeform clue input reduces inference quality.
- Too much required structured clue input makes the feature too cumbersome in the pit.
- Confidence must remain conservative.
- The first implementation should not overreach into unsupported certainty.

## Success Criteria

This feature is successful if it can:
- unify multi-observer evidence coherently
- incorporate operator clues as structured evidence
- detect meaningful topology-aware disagreement patterns
- narrow likely fault regions more than simple missing-device reporting
- distinguish likely local device issues from likely propagation issues in many cases
- recommend the next physical troubleshooting step
- remain honest when evidence is insufficient or ambiguous

## Open Design Questions

These should be resolved before implementation details are fully frozen:
- How are observer attachment points stored in the source-of-truth config?
- What is the primary unit of localization: edge, segment, branch subtree, or observer interval?
- Which clue types are required in the MVP versus later phases?
- How should the UI present confidence and ambiguity?
- How should clues be edited, persisted, and cleared across reruns?
- How much workflow automation is desirable versus guided/manual?

## Recommended Next Step

Before implementation-architecture work begins, define:
1. observer attachment schema
2. operator clue schema
3. unified evidence model
4. pattern vocabulary
5. candidate diagnosis output schema
6. CLI/UI first-pass workflow behavior

After that, implementation can proceed in staged milestones:
- evidence unification
- clue integration
- pattern detection
- candidate fault localization
- pit guidance surfaces

