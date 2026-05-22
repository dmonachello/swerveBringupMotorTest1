SPEC_STATUS: RESEARCH_ONLY

# Spec: Topology Fault Inference Model

Purpose: define the research-to-implementation model for inferring break candidates and high-error fault regions from passive CAN observation, topology metadata, and operator clues.

## Status

Research/spec-only.

No code changes are required by this document.

## Research Summary (Current Repo)

Purpose: capture what is currently implemented versus spec-level.

Implemented substrate:

- Topology adjacency model in profile metadata (`neighborPorts`, `neighborLinks`) with parser support.
- Multi-observer visibility provider with per-source visibility and summary counts (`all/some/none`).
- CAN summary metrics including missing/stale lists and derived bus-load/reporting fields.
- Console-derived fault heuristic (`BUS_FAULT_SUSPECTED`) based on timeout clustering.

Missing today:

- A unified inference engine that emits explicit break candidates (for example `possible_break_between_segments`).
- A stable result model that fuses passive, topology, and clue evidence with confidence.
- Operator-facing CLI/UI surfaces for break-candidate output and evidence provenance.

## Problem Statement

Passive observation alone can identify visibility disagreement, missing devices, and high bus load, but it cannot always localize likely break regions with actionable confidence.

A dedicated inference layer is required to combine:

1. Passive observed evidence
2. Topology/model evidence
3. Operator-supplied clues

## Inputs

Purpose: define canonical evidence inputs for inference.

### Passive Observation Inputs

- per-device, per-source visibility matrix
- per-source availability and timeout state
- frame-rate and freshness/staleness metrics
- missing/seen status transitions
- bus summary metrics (utilization proxy, dropped/read/pcap errors when available)

### Topology Inputs

- node graph
- `neighborPorts` (preferred)
- branch/segment relationships
- observer attachment points

### Operator Clue Inputs

Reference: `docs/SPEC_OPERATOR_CLUES_MODEL.md`

- structured clue records with confidence and timestamps
- device-local clues
- sequence/branch boundary clues
- event/timing clues

## Evidence Model

Purpose: normalize heterogeneous signals into one scoring model.

Proposed internal evidence classes:

- `VisibilityEvidence`
- `TopologyBoundaryEvidence`
- `TrafficHealthEvidence`
- `OperatorClueEvidence`

Each evidence item should include:

- `kind`
- `target` (device/edge/segment/branch/system)
- `strength` (normalized numeric score)
- `confidence`
- `timestampMs`
- `provenance`

## Candidate Types

Purpose: define output classes for operator-facing diagnostics.

Minimum candidate types:

- `possible_break_between_segments`
- `branch_localized_fault`
- `bus_wide_error_pressure`
- `device_local_fault_candidate`
- `inconsistent_visibility`

Each candidate should include:

- candidate type
- likely region (edge/segment/branch/device)
- confidence score and confidence band
- supporting evidence list
- conflicting evidence list
- suggested next observation/stimulus actions

## Inference Flow (Proposed)

Purpose: define deterministic processing stages.

1. Build normalized visibility snapshot and source-health snapshot.
2. Build topology adjacency graph and observer placement map.
3. Build clue evidence set from structured operator clues.
4. Generate candidate regions from visibility disagreements and topology boundaries.
5. Score candidates using weighted evidence fusion.
6. Penalize candidates with strong conflicting evidence.
7. Emit ranked candidate list with provenance.

## Scoring Model (Proposed)

Purpose: standardize confidence behavior.

Base score components:

- passive score
- topology consistency score
- clue alignment score
- bus-pressure modifier

Confidence bands:

- `low` (0.00 to <0.40)
- `medium` (0.40 to <0.75)
- `high` (0.75 to 1.00)

Suggested weighting defaults:

- passive evidence: 0.45
- topology evidence: 0.30
- clue evidence: 0.25

SID_QUESTION: Should clue evidence be capped so low-quality operator input cannot dominate strong passive disagreement signals?

## High Error Rate Representation

Purpose: separate localized breaks from global bus pressure.

High error-rate conditions should produce dedicated candidates, not only raw counters.

Proposed condition:

- `bus_wide_error_pressure`

Inputs:

- utilization proxy (`bus_load_pct`)
- read/pcap/dropped errors
- stale/missing growth trend
- console-derived timeout clusters

Interpretation:

- high global pressure lowers confidence of fine-grain localization unless boundary clues strongly agree.

## Output Contract (Proposed)

Purpose: define stable inference payload for CLI/UI consumption.

```json
{
  "inferenceVersion": 1,
  "timestampMs": 1714000000000,
  "candidates": [
    {
      "type": "possible_break_between_segments",
      "target": { "from": "PDH", "to": "FL TURN" },
      "confidence": 0.81,
      "confidenceBand": "high",
      "evidence": ["visibility_disagreement", "sequence_boundary_clue"],
      "conflicts": [],
      "nextSteps": ["re-seat connector between PDH and FL TURN", "re-run focused test"]
    }
  ],
  "systemConditions": ["bus_wide_error_pressure"]
}
```

## Validation Strategy (Future)

Purpose: establish evidence quality before implementation.

- replay-based synthetic scenarios (known break boundaries)
- multi-observer disagreement scenarios
- high-bus-load without physical break scenarios
- clue-conflict scenarios

Success criteria:

- localization narrows candidate regions relative to passive-only baselines
- confidence calibration is monotonic with evidence quality
- false certainty is minimized under conflicting evidence

## Tradeoffs

- Benefit: more actionable and explainable fault localization.
- Cost: additional model complexity and tuning effort.
- Risk: overfitting to clue patterns or observer placement assumptions.

## Future Extensions

- branch-aware probabilistic graph model
- historical clue reliability calibration
- automatic experiment suggestions based on candidate entropy

## Related Docs

- `docs/SPEC_OPERATOR_CLUES_MODEL.md`
- `docs/SPEC_BREAK_AND_ERROR_OPERATOR_SURFACES.md`
- `docs/SPEC_BREAK_ERROR_IMPLEMENTATION_TRACE.md`
- `docs/CAN Bus DIagnostic Feature Specification.md`
- `docs/FEATURE_SPEC_MULTI_ANALYZER_VISIBILITY_MATRIX.md`
- `docs/WORKFLOW_01_NEW_ROBOT_BRINGUP.md`

