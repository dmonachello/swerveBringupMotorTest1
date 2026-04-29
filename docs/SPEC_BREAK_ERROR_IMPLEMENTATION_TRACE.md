# Spec: Break and Error Implementation Trace

Purpose: provide a code-path reality map for break/high-error diagnostics so future implementation work starts from verified ownership and avoids doc-vs-code drift.

## Status

Research/spec-only.

This file is a trace document, not an implementation request by itself.

## Research Method

Purpose: summarize how this trace was derived.

- inspected CLI docs for claimed commands
- inspected Python CLI implementation for matching handlers
- inspected visibility/topology/diagnostics code paths used by UI and bridge runtime
- inspected current fault heuristic sources

## Code-Path Findings

Purpose: list validated findings with implementation ownership.

### Topology and Neighbor Substrate

- Schema keys exist and are centralized (`tools/common/profile_constants.py`):
  - `neighborLinks`
  - `neighborPorts`
- Parser support exists for both forms (`tools/common/topology_parse.py`).
- Topology architecture docs define `neighborPorts` as preferred for inference (`tools/can_topology/ARCHITECTURE.md`).

### Visibility Substrate

- Multi-source visibility matrix provider exists (`tools/can_nt/visibility_provider.py`).
- Bridge runtime ingests and publishes visibility snapshots (`tools/can_nt/can_nt_bridge.py`).
- UI consumes visibility snapshots and colors topology nodes (`tools/can_nt/bringup_ui.py`, `tools/can_topology/live_topology_view.py`).

### Error/Fault Heuristics

- Console monitor emits derived `BUS_FAULT_SUSPECTED` events (`tools/can_nt/can_console_monitor.py`).
- Analyzer/reporting paths expose rates, missing/stale, and load-style metrics (`tools/can_nt/can_analyzer.py`, `tools/can_nt/can_reporting.py`).

### CLI Surface Drift Risk

Docs claim topology/visibility show commands, including neighbor operations:

- `show topology neighbors ...`
- `show visibility ...`
- `topology neighbor-ports ...`

Claim locations:

- `docs/CLI_REFERENCE_MANUAL.md`
- `docs/BRIDGE_CLI_FULL_SPEC.md`

Current implementation observation:

- `tools/can_nt/bridge_cli.py` does not currently show concrete handler ownership for topology/neighbor/visibility show commands.
- `tools/can_nt/bridge_cli_constants_gen.py` still lists `visibility` and `topology` show targets.

Interpretation:

- this appears to be a documentation/grammar-intent vs runtime-handler mismatch that should be resolved in a dedicated pass.

## Gap Classification

Purpose: separate substrate-complete from surface-incomplete areas.

Substrate-complete enough for next phase:

- topology adjacency model
- multi-source visibility matrix
- baseline bus-health diagnostics

Surface-incomplete:

- break-candidate inference output
- localized high-error candidate output
- stable CLI and UI surface contracts for those outputs

Consistency-incomplete:

- CLI docs/spec claims for topology/visibility commands vs observed runtime command ownership

## Recommended Sequencing

Purpose: reduce risk while adding operator-facing capability.

1. Contract pass

- define additive candidate payload schema and keys
- mark doc-only or not-yet-implemented CLI commands explicitly where needed

2. Inference pass

- build candidate generator from visibility + topology + clue evidence
- emit ranked candidates and conditions

3. Surface pass

- wire CLI summary/detail views
- wire UI overlays and candidate evidence panel

4. Regression pass

- golden JSON snapshots for candidate output
- targeted UI checks for overlay/confidence rendering

## Definition of Done for This Trace

Purpose: define when this research trace no longer reflects reality.

This trace should be revised when any of the following happen:

- topology/visibility CLI handlers are implemented or removed from docs
- inferred candidate payloads are published or consumed
- UI gains break/high-error candidate rendering
- operator clues are integrated into ranking outputs

## Related Docs

- `docs/SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md`
- `docs/SPEC_BREAK_AND_ERROR_OPERATOR_SURFACES.md`
- `docs/SPEC_OPERATOR_CLUES_MODEL.md`
- `docs/CLI_REFERENCE_MANUAL.md`
- `docs/BRIDGE_CLI_FULL_SPEC.md`

