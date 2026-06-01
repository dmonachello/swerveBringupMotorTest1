SPEC_STATUS: RESEARCH_ONLY

# Feature Spec: Topology First-Pass Reframe

## Purpose

Refocus the next topology milestone around the topology, neighbor, CLI, editor, and live-visibility substrate that already exists in the repo.

This is not a rewrite spec.

It is a keep-tighten-add plan intended to avoid duplicate functionality and duplicate implementation paths while still delivering the first real topology-versus-live-CAN diagnostic milestone.

## Status

Research/spec-only.

This document is a planning baseline and gap analysis, not an implementation request by itself.

## Why Reframe

Earlier milestone planning assumed topology and neighbor support was still minimal.

That assumption is no longer accurate.

Current code already includes:

- canonical topology persistence using `nodes[]` and `edges[]`
- endpoint-based connection semantics using `fromNode/fromPort/toNode/toPort`
- derived neighbor views
- CLI topology show and edit commands
- topology validation
- live topology rendering
- live CAN visibility and observed-device tracking

A clean-sheet reimplementation would create avoidable risk:

- duplicate topology concepts
- duplicate neighbor logic
- duplicate command surfaces
- duplicate live observation logic
- contract drift between CLI, editor, and live views

So this milestone should be treated as an extension and hardening pass, not a rebuild.

## Current Baseline

### Canonical Topology Model

Purpose: identify the persisted topology source of truth that must be retained.

Current persisted topology already uses:

- `topology.profiles.<profile>.nodes[]`
- `topology.profiles.<profile>.edges[]`

This is the correct baseline and should remain canonical.

All persisted topology participants should be treated as first-class graph nodes.

Shared graph-node fields should include:

- `label`
- `objectType`
- `nodeType`
- `nodeClass`
- layout and edge participation

`nodeClass` is the shared split between:

- `device`
- `infrastructure`

This unifies graph treatment without forcing all nodes into runtime device identity.

Relevant code:

- `tools/common/topology_parse.py`
- `src/main/deploy/bringup_system.json`

Verification commands:

- show topology nodes local --json --pretty
- show topology edges local --json --pretty

### Endpoint-Based Connections

Purpose: confirm that current connections already match the desired authored relationship shape.

Current edges already encode:

- `fromNode`
- `fromPort`
- `toNode`
- `toPort`
- `edgeType`

That matches the desired `nodeA/portX -> nodeB/portY` model.

Verification commands:

- show topology edges local --json --pretty
- show neighbors <label> --json --pretty

### Neighbor Derivation

Purpose: identify existing reusable neighbor logic.

Current shared parsing already derives:

- `neighborPorts`
- `neighborLinks`

from the canonical edge list.

Relevant code:

- `tools/common/topology_parse.py`

Verification commands:

- show topology neighbors local
- show topology neighbors local --json --pretty
- show neighbors <label> --json --pretty

### CLI Topology Surface

Purpose: record the existing operator/debug commands that should be evolved, not replaced.

Current local CLI commands already include:

- `show topology local`
- `show topology --grouped local`
- `show topology nodes local`
- `show topology edges local`
- `show topology neighbors local`
- `show topology node <label>`
- `show neighbors <label>`
- `validate topology`
- `topology neighbor-ports set <node> <port> <neighbor> <neighborPort>`
- `topology neighbor-ports delete <node> <port>`
- `topology neighbor-ports clear <node>`
- `topology neighbor-auto all`
- `topology neighbor-auto all <label1,label2,...>`
- `topology neighbor-auto node <label>`

Relevant code:

- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/tests/test_bridge_cli_topology_show.py`

Verification commands:

- show topology local
- show topology --grouped local
- show topology nodes local --json --pretty
- show topology edges local --json --pretty
- show topology neighbors local
- show topology node <label>
- show neighbors <label>

### Validation Surface

Purpose: describe what current validation already covers.

Current topology validation already covers basic structural/config consistency such as:

- duplicate topology node keys
- missing `deviceRef`
- unknown node references in edges
- unknown edge types

Relevant code:

- `tools/can_topology/validate_profiles.py`
- `tools/can_topology/tests/test_validate_profiles_topology.py`

Verification commands:

- validate topology
- python tools/can_topology/validate_profiles.py --path src/main/deploy/bringup_system.json --verbose

### Live Observation Surface

Purpose: identify the existing live evidence pipeline that should remain canonical.

Current code already includes:

- a visibility provider
- observed-device freshness and last-seen tracking
- per-source visibility tables
- live topology overlay consumption
- UI visibility table consumption

Relevant code:

- `tools/can_nt/visibility_provider.py`
- `tools/can_nt/bringup_ui.py`
- `tools/can_topology/live_topology_view.py`

Verification commands:

- show visibility --json --pretty
- show visibility summary --json --pretty
- show visibility <label> --json --pretty

## Keep

### Keep the Canonical Graph

Do not introduce a second persisted topology model.

The canonical graph remains:

- topology nodes
- topology edges

All graph surfaces should consume the same shared node contract, including `nodeClass`.

### Keep Neighbor Data Derived

Do not persist a second authored neighbor table.

Neighbors remain derived from edges.

### Keep One Live Observation Substrate

Do not create a second independent “sniffer status” or “observed device” subsystem.

Topology comparison must build on the existing observation and visibility substrate.

### Keep Existing CLI Ownership

Do not fork a parallel command family if the current topology CLI surface can be evolved cleanly.

New behavior should extend or standardize the current command ownership.

## Tighten

### Tighten the Topology Interpretation

Purpose: constrain existing generalized topology support into a simple first-pass CAN-chain interpretation.

For milestone 1, interpretation should explicitly assume:

- CAN bus only
- one CAN segment
- no SWYFT devices
- no CANnect bridges
- no hidden downstream devices
- no branching allowed
- one connected chain

This should be a strict interpretation layer on top of the current graph, not a replacement graph.

Infrastructure nodes may still exist in the graph, but first-pass CAN-chain reasoning should be explicit about whether they are:

- chain participants
- observer placements
- ignored for a given interpretation

### Tighten Validation Semantics

Current validation is broader config/schema validation than first-pass chain correctness validation.

First-pass validation should explicitly distinguish:

Errors:

- broken references
- malformed endpoints
- branching
- multiple disconnected chains
- wrong-port connections
- duplicate fully qualified CAN identities

Warnings:

- unconnected devices
- duplicate raw CAN ids when fully qualified identities differ
- legal-but-ignored topology data outside first-pass semantics

### Tighten Device-Level Proof Output

Current neighbor output exists, but it should become more explicit and operator-readable.

For a selected device, the system should show:

- touching CAN connections
- inferred neighbors
- why each neighbor exists
- which edge created it
- local validation findings
- chain position when valid

### Tighten Expected-vs-Observed Matching

Expected devices for this first pass should come from topology truth only.

Matching should use fully qualified identity only:

- `manufacturer`
- `deviceType`
- `id`

Labels remain display handles, not the matching key.

## Add

### Shared First-Pass CAN Chain Interpreter

Add a shared interpretation layer that derives:

- ordered chain membership
- symmetric neighbors
- directed port neighbors
- provenance
- chain endpoints
- device-level and chain-level findings

This should be common code used by CLI, editor/debug views, and live comparison.

### Stronger Topology Debug Output

Add or standardize a stable debug contract for:

- device-level topology proof
- neighbor proof with provenance
- validation summary
- derived topology JSON dump

This should reuse current CLI ownership where possible.

### Topology-vs-Live-CAN Comparison

Add a comparison layer that combines:

- expected devices from topology truth
- observed devices from the existing visibility/observation substrate

Required outputs:

- expected count
- observed count
- missing expected devices
- unexpected observed devices
- duplicate fully qualified identities
- stale or intermittent devices
- last seen per device
- bus load and source health when available

### Simple Likely-Break Inference

For a valid single chain, add first-pass likely-break inference.

Example:

- A present
- B present
- C missing
- D missing

Candidate result:

- likely break between B and C

This must be explicitly probabilistic and limited to simple chain reasoning.

### Focused Regression Fixtures

Add regression coverage for:

- valid 3-device chain
- branching topology
- multiple disconnected chains
- broken references
- wrong-port connection
- duplicate fully qualified identity
- partial duplicate id warning
- unconnected device warning
- missing downstream observed device
- unexpected observed device
- intermittent or stale observed device

## Gap Matrix

Purpose: map the current codebase to the proposed milestone so work starts from verified ownership.

| Area | Current State | Milestone Disposition |
| --- | --- | --- |
| Canonical topology persistence | Already implemented with `nodes[]` and `edges[]` | Keep |
| Endpoint port-to-port connections | Already implemented | Keep |
| Shared neighbor derivation | Already implemented via `neighborPorts` / `neighborLinks` | Keep |
| CLI topology show/edit commands | Already implemented and usable | Keep, then standardize |
| Topology validation entry point | Already implemented | Keep, then tighten |
| Live observed-device / visibility substrate | Already implemented | Keep |
| Simple single-chain CAN interpretation | Not explicit today | Add |
| Validation for one chain / no branching / no multi-chain | Not explicit today | Add |
| Device-level proof with provenance and chain position | Partial today | Tighten |
| Stable derived topology debug dump | Not explicit today | Add |
| Topology-truth expected-vs-observed comparison | Not explicit today | Add |
| Simple likely-break inference | Not implemented | Add |
| Simple-chain regression fixtures | Partial generalized coverage exists | Add targeted coverage |

## Omitted in First Pass

These are intentionally deferred and should not distort first-pass implementation decisions.

- SWYFT devices
- CANnect bridges
- hidden downstream devices
- multiple CAN segments
- power-chain neighbors
- logical-group neighbors
- topology/discovery shared-truth merge
- bridge-aware or branch-aware path inference
- rich graphical fault overlays
- advanced confidence scoring and evidence fusion

## Recommended Next Steps

### Phase 1. Baseline Evaluation

Write a short implementation-trace document confirming:

- current shared topology interpreters
- current CLI ownership
- current validation ownership
- current observation ownership
- doc-versus-code mismatches

### Phase 2. Correctness Hardening

Implement:

- shared first-pass CAN-chain interpretation
- stricter validation
- per-device proof output
- targeted chain fixtures

### Phase 3. Live Comparison

Implement:

- topology-truth expected-versus-observed comparison
- missing/unexpected/stale reporting
- simple likely-break inference

## Definition of Done

This milestone is done when:

- no duplicate topology model was introduced
- no duplicate neighbor model was introduced
- no duplicate live observed-device model was introduced
- first-pass single-chain interpretation is shared and deterministic
- validation enforces the first-pass chain rules
- device-level topology proof is available
- expected-versus-observed comparison works against live evidence
- simple likely-break inference works for ordinary downstream-missing cases
- targeted regression fixtures lock the behavior down

## Appendix A. Future Features

### A.1 Advanced Topology Structures

- SWYFT support
- CANnect bridge support
- hidden downstream devices
- multiple CAN segments
- multi-path device reachability

### A.2 Additional Neighbor Classes

- power neighbors
- logical-group neighbors
- connector-region neighbors
- richer upstream and downstream semantics

### A.3 Discovery and Reconciliation

- merge discovery into expected topology workflows
- editor/runtime reconciliation tools
- topology repair suggestions from live evidence

### A.4 More Advanced Diagnosis

- stronger fault scoring
- anomaly classification
- richer intermittent heuristics
- wrong-segment detection
- evidence fusion with operator clues

### A.5 UI Expansion

- dedicated validation pane
- richer graphical overlays
- inline provenance callouts
- comparison dashboards
