# Spec: Break and High-Error Operator Surfaces

Purpose: define how inferred break candidates and high-error conditions should be represented to operators in CLI and UI without changing existing protocol contracts.

## Status

Research/spec-only.

This document defines operator-facing behavior targets and additive payload shapes.

## Scope

In scope:

- operator-facing representation of inferred break candidates
- operator-facing representation of high-error conditions
- evidence and confidence display rules
- CLI and UI surface requirements
- additive publishing guidance

Out of scope:

- CAN transmit/active probing from PC-side tools
- replacement of existing bringup command or TCP protocol semantics
- non-additive contract changes to existing keys

## Current State Baseline

Purpose: anchor the spec to current implementation reality.

Implemented now:

- multi-source visibility snapshot and summary substrate (`tools/can_nt/visibility_provider.py`)
- UI visibility matrix and topology visibility overlay consumption (`tools/can_nt/bringup_ui.py`, `tools/can_topology/live_topology_view.py`)
- CAN analyzer summary and bus-health style counters (`tools/can_nt/can_analyzer.py`, `tools/can_nt/can_reporting.py`)
- console-derived bus-fault heuristic (`BUS_FAULT_SUSPECTED`) (`tools/can_nt/can_console_monitor.py`)

Not implemented now:

- operator-facing inferred break-candidate surface with evidence provenance
- operator-facing localized high-error candidate surface tied to topology regions
- unified candidate payload shared by CLI and UI for break/error inference

## Operator Surface Goals

Purpose: make outputs actionable and explainable.

- show ranked candidates instead of only raw counters
- show confidence and ambiguity explicitly
- show supporting and conflicting evidence
- show next-step checks per candidate
- keep raw diagnostics available for expert drill-down

## Candidate Model (Operator View)

Purpose: standardize what operators see regardless of surface.

Minimum candidate types:

- `possible_break_between_segments`
- `branch_localized_fault`
- `bus_wide_error_pressure`
- `device_local_fault_candidate`
- `inconsistent_visibility`

Minimum candidate fields:

- `type`
- `target`
- `confidence`
- `confidenceBand`
- `evidence`
- `conflicts`
- `nextSteps`

## CLI Surface Requirements

Purpose: define scriptable and human-readable CLI behavior.

Required views:

- candidate list view (ranked summary)
- candidate detail view (single candidate evidence/conflicts)
- condition summary view (`bus_wide_error_pressure`, availability notes)

Required output modes:

- table/text mode for operators
- JSON mode for automation/regression assertions

Required semantics:

- no confidence inflation when evidence conflicts
- explicit `unknown`/`insufficient_evidence` labeling when needed
- include provenance tags for each evidence item

## UI Surface Requirements

Purpose: define visual behavior for topology-centric troubleshooting.

Required capabilities:

- overlay candidate regions on topology view
- highlight disagreement edges/segments
- badge confidence level and ambiguity state
- show expandable evidence and conflict details
- show recommended next checks and capture prompts
- make topology right-click clue entry the primary operator clue workflow

Primary clue-entry interaction:

- select topology node or bus segment
- right-click to open predefined observations menu
- choose observation to create structured clue bound to selected target
- optionally add confidence and short note

Predefined menu requirement:

- provide separate predefined menus for node targets and segment targets
- prioritize high-frequency field observations (LED pattern, first-failed boundary, downstream-only failure, reseat effect)
- avoid requiring freeform text for common clues

Recommended capabilities:

- filter by candidate type
- timeline or recent-change view for intermittent faults
- side panel showing operator clues that influenced ranking

## High-Error Representation Rules

Purpose: avoid conflating global bus pressure with localized breaks.

- represent global pressure as `bus_wide_error_pressure`
- degrade localization confidence under sustained global pressure
- avoid presenting a localized break as high confidence unless boundary evidence is strong
- preserve raw metrics so advanced users can inspect underlying conditions

## Clue Integration Rules

Purpose: connect operator clue evidence to surface behavior.

Reference: `docs/SPEC_OPERATOR_CLUES_MODEL.md`

- clue-supported candidates must identify contributing clue IDs or clue summaries
- conflicting clues must lower confidence and appear in `conflicts`
- low-quality clues cannot suppress strong passive disagreement evidence

## Additive Publishing Guidance

Purpose: align with existing contract stability rules.

Suggested additive keys under `bringup/diag/can/...`:

- `can/faultCandidates/json`
- `can/faultConditions/json`
- `can/faultEvidenceSummary/json`

Contract rule:

- do not modify or remove existing keys used by current dashboards and reports

## Validation Strategy (Future)

Purpose: define acceptance checks for future implementation.

- CLI golden snapshots for candidate summary/detail JSON
- UI screenshot/state checks for overlay and confidence badges
- conflict scenarios verifying confidence reduction behavior
- high-error scenarios verifying `bus_wide_error_pressure` precedence behavior

## Tradeoffs

- Benefit: more actionable diagnosis for field operators
- Cost: higher UX and payload complexity
- Risk: overconfidence if evidence weighting is not conservative
- Mitigation: explicit ambiguity states and conflict reporting

## Future Extensions

- evidence timeline with change-point detection
- operator clue quick-pick templates by device family
- case export bundle (captures + candidates + clues + workflow outcomes)

## Related Docs

- `docs/SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md`
- `docs/SPEC_OPERATOR_CLUES_MODEL.md`
- `docs/FEATURE_SPEC_MULTI_OBSERVER_CAN_FAULT_LOCALIZATION.md`
- `docs/OPERATOR_SURFACES.md`
