# Feature Spec: Multi-Observer Topology-Aware CAN Fault Localization

## Purpose

Define the product-level concept, diagnostic model, workflow, and architectural requirements for using multiple passive CAN observers to localize breaks, segmentation faults, and high-error regions on the robot CAN network.

This is a conceptual feature spec. It defines what the system should mean and how operators should use it before deeper implementation details are finalized.

## Problem Statement

Today, a single CAN observer can answer questions like:
- Is a device visible on the bus?
- Is traffic present or stale?
- Is utilization high?
- Are expected devices missing?

A single observer is much weaker at answering:
- Where along the topology is traffic disappearing?
- Which branch is isolated?
- Whether a device is transmitting locally but not propagating through the bus.
- Whether a likely break exists between two physical observation points.
- Whether high error behavior is localized to part of the topology.

The goal of this feature is to move from generic visibility reporting to topology-aware fault localization.

## Product Promise

Given:
- a topology model
- one or more passive CAN observers placed at known topology points
- expected devices and optional robot stimulus

the system can:
- compare what each observer sees
- identify inconsistent visibility patterns
- narrow the likely fault region to a topology segment, branch, or observer interval
- distinguish likely local-device issues from likely propagation/network issues
- recommend the next physical troubleshooting step

## Scope

In scope:
- passive observation only
- multiple observer sources
- topology-aware inference using diagram neighbor data
- localization of likely fault regions
- support for brand new robot bring-up and troubleshooting workflows
- CLI/UI/topology-view presentation of observer disagreement and inferred fault regions

Out of scope:
- electrical-layer measurements with custom hardware
- direct CAN transmission for diagnosis by default
- replacing vendor tools for firmware/configuration
- claiming certainty when evidence is ambiguous

## Core Concepts

## 1. Observer
An observer is a passive CAN sniffer attached at a known logical position in the topology.

Examples:
- a CANable attached near the roboRIO
- a CANable attached downstream of a CANnect branch
- a passive observer attached to a subsystem segment

Each observer must have:
- a stable source ID
- a human-readable label
- an attachment point in the topology model
- availability state
- an observation window or rolling state

## 2. Topology Graph
The topology graph is the logical connectivity model of the CAN system.

This feature should use explicit topology metadata, not screen position, as the source of truth.

Primary graph inputs:
- `neighborPorts` (preferred)
- `neighborLinks` (legacy/simple adjacency)
- `deviceLinks` for CANnect-derived port relationships

The graph should support:
- linear edges
- branches
- named ports such as `left`, `right`, `next`, `branch1`, `branch2`
- analyzer/observer attachment points

## 3. Observation Window
A comparison should be based on a defined observation window.

The system may support:
- rolling windows
- fixed capture windows
- windows before/after stimulus

The observation window is used to compare:
- traffic presence
- rates
- missing devices
- stale devices
- change after stimulus

## 4. Stimulus
Stimulus is an optional controlled robot action used to provoke expected traffic or behavior.

Examples:
- run one motor at low duty
- enable one subsystem
- run one focused test

Stimulus improves inference by letting the system compare:
- expected affected nodes
- observed traffic changes by observer

## 5. Fault Region
A fault region is the smallest topology interval or branch the system can credibly identify from the evidence.

It may be represented as:
- between observer A and observer B
- between node X and node Y
- on branch `branch1` of node N
- downstream of segment S
- not localizable beyond “subtree rooted at node N”

The system should avoid pretending to know more than the evidence supports.

## User Problems Solved

This feature is intended to help with:
- likely CAN trunk break
- likely branch break or isolation
- partial visibility where some devices are seen only from some observers
- traffic present downstream but not upstream
- traffic present upstream but absent downstream
- ambiguous topology or source placement mismatch
- localized high-load or high-error suspicion region
- distinguishing device-local silence from network propagation failure

## Non-Goals And Limits

This feature cannot directly prove:
- exact electrical root cause
- exact physical connector failure without corroborating evidence
- true line-level error counters if the hardware/software stack does not expose them
- exact fault location when observer coverage is too sparse
- exact cause when multiple overlapping failures are present

It should instead produce:
- candidate diagnoses
- confidence levels
- evidence summaries
- recommended next checks

## Supported Diagnostic Classes

The system should support at least these diagnosis classes:

### Node-Level
- `present`
- `missing`
- `stale`
- `responding_to_stimulus`
- `not_responding_to_stimulus`
- `unexpected_node_or_id`

### Topology/Observer-Level
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

Note: `high_error_region_suspected` may initially be inferred indirectly from observer disagreement, staleness, visibility instability, or transport-exposed health signals. It does not require line-level electrical measurement.

## Required Inputs

The feature requires these input classes:

## A. Topology Inputs
- topology graph
- expected devices
- neighbor adjacency
- branch/port metadata
- observer attachment points

## B. Observation Inputs
Per observer:
- source ID
- observer availability
- observed device visibility
- last seen age
- message counts
- frames per second
- optional bus summary/utilization signals

## C. Optional Stimulus Inputs
- test ID
- command/action name
- expected affected devices or segments
- observation window before and after stimulus

## D. Optional Auxiliary Inputs
- robot-local diagnostics
- console-derived warnings/errors
- runtime profile context
- expected active profile

## Observer Attachment Model

Observers must be represented explicitly in the topology model.

An observer attachment should include:
- observer ID
- observer label
- attached node or segment
- optional attached port
- expected scope or notes

Example conceptual shape:

```json
{
  "id": "observer_front_trunk",
  "label": "Front Trunk Observer",
  "attachNode": "PDH",
  "attachPort": "right"
}
```

If topology precision is lower, attachment may be to a segment or bus region instead of a specific port.

## Evidence Model

The feature needs a richer evidence model than simple missing/present flags.

Per device, per observer, evidence should include:
- visible now / not visible now / unknown
- last seen age
- frames per second
- message count
- visibility confidence
- expected visibility based on topology and stimulus

System-level evidence should include:
- observer coverage map
- disagreement matrix
- bus summary metrics
- topology intervals where observations diverge
- optional before/after stimulus differences

## Inference Model

The inference engine should answer:
- which devices are visible from which observers?
- which observer disagreements are topology-consistent?
- which observer disagreements imply a likely fault interval?
- whether the issue is more likely local-device, propagation, branch, or global bus related
- whether the result is too ambiguous for a strong claim

## Core Inference Patterns

### Pattern 1: Seen upstream, missing downstream
Interpretation:
- possible break or propagation failure between those observation points
- possible branch isolation if topology indicates a branch boundary

### Pattern 2: Seen downstream, missing upstream
Interpretation:
- topology mismatch
- observer placement misunderstanding
- inconsistent propagation assumptions
- possible segmentation not represented in model

### Pattern 3: Seen only by local observer near one branch
Interpretation:
- branch may be isolated from main trunk
- local devices may still be transmitting on a segmented sub-bus

### Pattern 4: Missing at all observers
Interpretation:
- likely local device issue
- wrong ID or wrong expected topology
- device powered off or not transmitting

### Pattern 5: Unstable visibility across observers
Interpretation:
- possible high-error region
- intermittent connector/segment issue
- noisy or overloaded segment
- ambiguous if observation windows differ too much

### Pattern 6: Stimulus produces local change only in one observer region
Interpretation:
- stimulus reached local device but expected propagation visibility is inconsistent
- possible segmented bus or branch isolation

## Fault Localization Output Model

The system should produce structured outputs that are useful both to humans and other tools.

### Candidate diagnosis output
Each diagnosis should include:
- diagnosis type
- fault region
- confidence
- evidence list
- ambiguity notes
- recommended next checks

Example conceptual output:

```json
{
  "type": "possible_break_between_observers",
  "region": {
    "betweenObservers": ["observer_mid", "observer_end"]
  },
  "confidence": "medium",
  "evidence": [
    "Device FL TURN visible at observer_mid but not observer_end",
    "Device FL CANCODER visible at observer_mid but not observer_end",
    "Observer_end sees local branch devices only"
  ],
  "recommendedChecks": [
    "Inspect connector between CANnect A branch1 and branch cable",
    "Verify topology observer placement",
    "Rerun observation after reseating branch connector"
  ]
}
```

## Confidence Model

The system should support qualitative confidence levels:
- `low`
- `medium`
- `high`

Confidence should depend on factors such as:
- number of agreeing observers
- number of affected devices
- topology clarity
- observer placement certainty
- presence/absence of stimulus correlation
- ambiguity due to insufficient coverage

The system should prefer conservative confidence over overclaiming.

## Ambiguity Handling

Ambiguity is a first-class result, not a failure.

The system should explicitly return ambiguity when:
- observer coverage is too sparse
- topology is incomplete or inconsistent
- multiple failure classes explain the same evidence
- observers disagree in ways that suggest model error, not just network failure
- the evidence window is too small or stale

Example ambiguity classes:
- `insufficient_observer_coverage`
- `possible_topology_model_mismatch`
- `multiple_candidate_fault_regions`

## Workflow Model

This feature should be a workflow, not just a raw report.

## Workflow: Multi-Observer CAN Fault Localization

1. Load topology and expected devices.
2. Register observer sources and attachment points.
3. Confirm observer availability.
4. Collect observation window.
5. Optionally run focused stimulus/test.
6. Compare visibility by observer.
7. Infer candidate fault region(s).
8. Present evidence and next checks.
9. Allow operator to re-run after physical changes.

This workflow should support both:
- troubleshooting an already-built robot
- incremental bring-up of a new robot/subsystem

## CLI Surface Requirements

The CLI should support:
- listing observers and attachment points
- showing visibility by observer
- showing disagreement summaries
- showing inferred fault regions
- showing ambiguity reasons
- dumping structured JSON for analysis/regression

Examples of output types, not final command names:
- observer summary
- topology neighbor view with observer overlays
- differential visibility table
- localization summary
- evidence dump

## UI Surface Requirements

The UI/live topology view should support:
- showing observer placement on the topology
- highlighting devices visible by each observer
- highlighting disagreement regions
- showing inferred fault region overlays
- showing recommended next checks
- clearly distinguishing:
  - missing from all observers
  - visible only from some observers
  - stale/uncertain visibility

## Data Model Requirements

The implementation should support data shapes conceptually like:

### Observer definition
```python
@dataclass
class CanObserver:
    observer_id: str
    label: str
    attach_node: str | None
    attach_port: str | None
    available: bool
```

### Per-device observation
```python
@dataclass
class DeviceObservation:
    observer_id: str
    device_key: str
    visible: bool | None
    age_ms: int | None
    frames_per_sec: float
    msg_count: int
```

### Differential comparison
```python
@dataclass
class VisibilityComparison:
    device_key: str
    by_observer: dict[str, bool | None]
    pattern: str
    notes: list[str]
```

### Fault localization candidate
```python
@dataclass
class FaultLocalizationCandidate:
    type: str
    region: dict[str, object]
    confidence: str
    evidence: list[str]
    recommended_checks: list[str]
```

These shapes are conceptual and may be implemented differently.

## Architectural Fit

This feature fits the layered architecture as follows:

### Hardware and Transport Layer
- multiple passive sniffers
- CAN frame capture
- transport availability

### Adapter and Protocol Layer
- per-observer ingestion
- source normalization
- topology parsing (`neighborPorts`, `deviceLinks`)

### Domain Logic Layer
- visibility semantics
- differential inference
- candidate fault localization
- confidence and ambiguity logic

### Workflow and Application Service Layer
- multi-observer fault-localization workflow
- observer setup/readiness
- stimulus + observation orchestration
- recommended next-step guidance

### Presentation Layer
- CLI summaries/tables/JSON
- UI topology overlays
- operator guidance and evidence review

### Contract Layer
- topology schema for observers/neighbors
- diagnostics result schema
- consistent meanings for visibility, fault region, and confidence

## Existing Project Foundations To Reuse

This feature should build on existing foundations rather than inventing parallel models.

Existing relevant pieces include:
- topology neighbor metadata (`neighborPorts`, `neighborLinks`, `deviceLinks`)
- topology parsing helpers
- multi-source visibility provider
- workflow-oriented bring-up direction
- topology/live-view surfaces
- diagnostics/reporting infrastructure

Preferred inference graph:
- use `neighborPorts` as the primary topology-aware inference graph
- treat `neighborLinks` as lower-fidelity compatibility data

## Success Criteria

This feature is successful if it can:
- compare multiple passive observers coherently
- identify observer disagreement patterns consistently
- narrow likely fault regions beyond simple missing-device reporting
- distinguish likely local-node issues from likely propagation issues
- present ambiguity honestly when evidence is insufficient
- give the operator a concrete next physical troubleshooting step

## Risks And Tradeoffs

- Incorrect observer placement metadata can produce false localization.
- Incomplete topology models can make good evidence look contradictory.
- Sparse observer coverage limits localization precision.
- High utilization and true CAN error behavior may be only partially observable without lower-level hardware support.
- Overclaiming confidence is more dangerous than underclaiming.

## Open Design Questions

These questions should be resolved before final implementation details are frozen:
- How are observer attachment points persisted in the topology/config schema?
- Is the unit of localization an edge, segment, branch subtree, or observer interval?
- How should topology-model uncertainty be represented?
- What bus-condition signals beyond utilization/fps/age are realistically available from current observer hardware/software?
- How should the UI visually represent confidence and ambiguity?
- How much workflow orchestration should be automated versus advisory?

## Recommended Next Step

Before implementation detail specs, define:
- observer attachment schema
- fault taxonomy and confidence rules
- result/output schema for localization candidates
- CLI/UI surface behaviors
- test scenarios using representative topology examples

Related detail specs:

- `docs/SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md`
- `docs/SPEC_OPERATOR_CLUES_MODEL.md`
