# Spec: Operator Clues Model for Fault Localization

Purpose: define a structured operator-clue evidence model for topology-aware CAN fault localization.

## Status

Research/spec-only.

No implementation is required by this document.

## Why This Exists

Passive observation and topology inference are necessary but not sufficient for many real failures.

Operators often observe high-value evidence that passive telemetry cannot directly encode, such as LED patterns, first-failure boundary points, and connector-touch effects.

This spec defines how those field observations become structured evidence instead of freeform notes only.

## Scope

In scope:

- clue taxonomy
- clue schema and validation rules
- confidence model
- inference integration behavior
- workflow prompting behavior
- CLI/UI input contract proposals
- storage/lifecycle semantics

Out of scope:

- implementation details in Java/Python code
- protocol redesign
- replacement of passive diagnostics with manual clues

## Product Concept Update

The system concept should be treated as:

`multi-observer, topology-aware CAN fault localization with operator-supplied field clues`

Evidence is now a three-class model:

1. passive observed evidence
2. topology/model evidence
3. operator-supplied clue evidence

## Design Principles

- Clues are optional but encouraged.
- Structured clues are preferred over freeform text.
- Freeform notes remain available as fallback.
- Clues must never be required for base operation.
- Workflow prompts should appear only when useful (ambiguity/low confidence).
- Clues must be attributable (source, time, confidence).

## Clue Taxonomy

Purpose: define first-class clue types with predictable semantics.

### A. Device-Local Clues

Attach to a specific device label or key.

Examples:

- LED color/pattern abnormal
- power present but no traffic
- intermittent local reset
- motion failure or wrong direction
- abnormal heating/noise/clicking

### B. Sequence/Topology Boundary Clues

Attach to graph boundaries (device order, branch, segment).

Examples:

- first observed failed device
- last known-good device before boundary
- only one branch affected
- downstream-only failure from node/port

### C. Event/Timing Clues

Attach to temporal events.

Examples:

- failure began after enable/test start
- failure appears under load only
- reseating connector changed behavior
- failure after impact/vibration

### D. Global/System Clues

System-level observations without a single device target.

Examples:

- bus-wide flicker/instability
- high-latency control response
- subsystem-wide degradation pattern

## Canonical Clue Schema (Proposed)

```json
{
  "clueId": "clue-uuid",
  "clueType": "led_pattern",
  "targetKind": "device",
  "targetId": "FL TURN",
  "value": {
    "color": "red",
    "pattern": "blink_fast"
  },
  "confidence": "medium",
  "source": "operator",
  "timestampMs": 1713999000000,
  "notes": "Observed during runTest"
}
```

Required fields:

- `clueType`
- `confidence`
- `source`

Conditionally required fields:

- `targetKind` and `targetId` for targetable clue types

Recommended fields:

- `timestampMs`
- `notes`

Allowed confidence values:

- `low`
- `medium`
- `high`

## Example Structured Clues

### LED Pattern

```json
{
  "clueType": "led_pattern",
  "targetKind": "device",
  "targetId": "FL DRIVE",
  "value": { "color": "red", "pattern": "blink" },
  "confidence": "medium",
  "source": "operator"
}
```

### Sequence Boundary

```json
{
  "clueType": "sequence_boundary",
  "targetKind": "segment",
  "value": {
    "lastKnownGood": "PDH",
    "firstFailed": "FL TURN"
  },
  "confidence": "high",
  "source": "operator"
}
```

### Branch-Limited Failure

```json
{
  "clueType": "branch_scope",
  "targetKind": "branch",
  "targetId": "branch1",
  "value": { "affected": true, "otherBranchesHealthy": true },
  "confidence": "medium",
  "source": "operator"
}
```

## Inference Integration Rules (Proposed)

Purpose: make clues actionable instead of passive note storage.

- Treat clues as weighted evidence, not truth.
- Weight by confidence (`high > medium > low`).
- Weight by recency when timestamps exist.
- Allow conflicting clues; lower confidence when conflicts exist.
- Never suppress passive evidence; combine with clues.

Candidate scoring concept:

- passive score + topology score + clue score = final candidate rank

Output should include evidence provenance:

- which clues contributed
- confidence impact
- conflict notes when applicable

## Workflow Prompting Rules (Proposed)

Purpose: request clues only when they materially improve diagnosis.

Prompt for clues when:

- observer disagreement is high
- candidate region is broad/ambiguous
- confidence is below threshold
- repeated retries do not improve localization

Suggested prompt set:

- What was the first device observed to fail?
- Did any device show abnormal LED color/pattern?
- Did failures appear only on one branch?
- Did reseating any connector change behavior?
- Did failure start after enabling/running a specific test?

## CLI Input Contract (Proposed)

Purpose: allow fast field entry in terminal workflows.

Examples:

- `clue add led-pattern --device "FL DRIVE" --color red --pattern blink --confidence medium`
- `clue add sequence-boundary --last-good "PDH" --first-failed "FL TURN" --confidence high`
- `clue add branch-scope --branch branch1 --affected true --confidence medium`
- `clue list`
- `clue delete <clueId>`
- `clue clear`

Output behavior:

- explicit validation errors for missing required fields
- JSON-capable listing for scriptability

## UI Input Contract (Proposed)

Purpose: support guided and visual clue entry.

Primary input rule:

- UI is the primary clue-entry surface.
- Primary interaction is topology selection of a node or bus segment followed by a right-click menu.
- Right-click menus should present predefined observation choices first, with optional freeform notes as fallback.

Proposed UI patterns:

- quick-entry clue panel with clue type selector
- topology-click targeting for `targetId`
- right-click context menu on node/segment for rapid clue entry
- confidence picker (`low/medium/high`)
- optional freeform notes field
- prompt-driven clue dialogs when diagnosis confidence is low

## Predefined Observation Menus (Proposed)

Purpose: keep clue entry fast, consistent, and inference-friendly.

Node menu examples:

- LED pattern abnormal
- power present/no CAN activity
- motion failed or intermittent
- first observed failed device
- first observed recovered device

Bus segment menu examples:

- likely break between endpoints
- downstream devices failed
- reseat changed behavior
- branch-only failure observed

Interaction rules:

- menus should emit structured clue payloads directly
- labels should map to canonical `clueType` + `targetKind` + `value` fields
- freeform notes should be optional and non-blocking

## Storage and Lifecycle (Proposed)

Two storage scopes:

1. session clues (ephemeral troubleshooting run)
2. persisted clues (optional saved case/evidence bundle)

Retention guidance:

- keep session clues lightweight and clearable
- persist only when operator explicitly saves diagnostics/evidence

## Safety and Usability Constraints

- Do not overload operators with mandatory forms.
- Keep clue entry optional and fast.
- Keep one-command/one-form minimum entry paths.
- Preserve current behavior when no clues exist.

## Spec-Level Deliverables (Future Implementation)

- shared clue schema definition
- validation rules for clue types
- clue-to-inference weighting policy
- CLI and UI contract alignment
- regression tests for clue parsing/validation

## Tradeoffs

- Benefit: stronger real-world diagnosis with field evidence.
- Cost: additional UX and schema complexity.
- Risk: unstructured/low-quality clues can add noise.
- Mitigation: confidence weighting + optional usage + provenance reporting.

## Future Extensions

- vendor-specific LED pattern catalogs
- clue confidence calibration by historical outcomes
- automatic prompting tuned by ambiguity class
- export/import clue bundles with captures and summaries

Related inference/surface specs:

- `docs/SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md`
- `docs/SPEC_BREAK_AND_ERROR_OPERATOR_SURFACES.md`
- `docs/SPEC_BREAK_ERROR_IMPLEMENTATION_TRACE.md`

## Open Questions

SID_QUESTION: Should persisted clues live inside `bringup_system.json` metadata, or in separate run artifacts to avoid config churn?

SID_QUESTION: Should clue confidence be operator-entered only, or partially auto-derived from clue type and consistency checks?

SID_QUESTION: Should topology boundary clues allow both label targets and node-key targets, or normalize to one canonical ID form?
