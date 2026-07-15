SPEC_STATUS: IMPLEMENTATION_READY

  

# Feature Spec: CAN Bus Debug Final Push

  

## Purpose

  

Define the final implementation push needed to turn the CAN evidence work into a useful pit-side bus debugging tool.

  

The system already collects useful device evidence from passive CAN, robot-local runtime snapshots, console warnings, manual tests, full probes, topology, and enrichment. The missing piece is a shared diagnosis layer that converts those facts into ranked physical troubleshooting guidance.

  

## Goal

  

When a CAN bus problem is present, the operator should get a clear answer to:

  

- Which devices are affected?

- Is this likely a single-device issue, a branch issue, a trunk break, stale evidence, or bus-wide pressure?

- What physical region should be inspected first?

- Which evidence supports that recommendation?

- Which evidence conflicts with it?

- What should be run next to reduce uncertainty?

  

## Non-Goals

  

This feature does not:

  

- transmit CAN frames from the PC-side tool

- replace vendor tools, a CAN analyzer, or electrical measurement tools

- claim exact root cause from passive evidence alone

- hide raw evidence from advanced users

- merge robot-local data and passive CAN data without labeling the source lens

  

## Current State

  

Purpose: summarize what exists before the final push.

  

Implemented pieces:

  

- Passive CAN device discovery detects recurring device-emitted CAN traffic.

- Evidence UI displays per-device final interpretation.

- Live Topology displays profile devices, visibility, groups, and selected-device details.

- Robot-local runtime snapshots report active lifecycle/device presence.

- Full Probe performs active robot-side one-shot checks for devices in the active lifecycle scope.

- Console warning parsing surfaces CAN/device timeout warnings.

- Enrichment can run from the host and contribute additional evidence.

- Manual motion results are included in final device interpretation.

- Evidence panels now label new versus legacy source paths.

  

Important gaps:

  

- There is no explicit fault-candidate result model.

- There is no topology-aware break inference service.

- There is no frozen observation window for a single diagnosis run.

- Multi-observer data is collected but not yet used to localize a break.

- CTRE HTTP enrichment is not yet treated as a first-class CTRE device evidence contributor in the final status.

- REV USB/vendor enrichment is not complete.

- UI panels show facts but do not yet provide an ordered "check this first" recommendation.

  

## Product Behavior

  

Purpose: define the operator-facing behavior.

  

Add a `Run CAN Break Check` workflow. When run, the host captures a short, labeled observation window and produces a frozen diagnosis result.

  

The result should include:

  

- observation window start/end time

- evidence source freshness

- affected expected devices

- visible expected devices

- stale devices

- fault candidates ranked by confidence

- suggested next physical check

- source-specific supporting evidence

- source-specific conflicting evidence

  

The UI should show the result in two places:

  

- Evidence tab: `CAN Fault Candidates [NEW]`

- Live Topology tab: highlighted affected devices or suspected region

  

## Fault Candidate Model

  

Purpose: define the minimum output schema.

  

Each candidate should include:

  

- `faultClass`

- `confidence`

- `summary`

- `affectedDevices`

- `suspectedRegion`

- `supportingEvidence`

- `conflictingEvidence`

- `recommendedChecks`

- `sourceAges`

  

Initial `faultClass` values:

  

- `single_device_unreachable`

- `possible_branch_isolation`

- `possible_trunk_break`

- `possible_controller_side_isolation`

- `bus_wide_error_pressure`

- `intermittent_or_stale_visibility`

- `topology_or_profile_mismatch`

- `insufficient_evidence`

  

## Evidence Inputs

  

Purpose: list the inputs the inference service should consume.

  

Required inputs:

  

- profile expected device list

- topology graph, preferring `neighborPorts`

- passive CAN discovery rows

- robot-local runtime presence snapshot

- console warning snapshot

- robot CAN bus health snapshot

- manual motion result snapshot

- full probe snapshot

- enrichment snapshot

  

Optional inputs:

  

- CTRE HTTP device inventory and fault state

- REV USB/vendor diagnostic inventory

- multiple passive observer visibility snapshots

- operator clues

  

## Source Lens Rules

  

Purpose: prevent misleading conclusions.

  

Every fact must keep its source lens:

  

- `passive_can`: PC-side CANable or gateway observation

- `robot_local`: roboRIO runtime/device lifecycle view

- `full_probe`: active robot-side one-shot diagnostic

- `console`: robot or host console warning stream

- `manual`: operator/motion result

- `ctre_http`: CTRE vendor HTTP source

- `rev_usb`: REV vendor USB/gateway source

- `topology`: profile-defined physical model

  

The final candidate may combine sources, but the UI must keep the evidence provenance visible.

  

## Inference Rules

  

Purpose: define the first useful heuristic layer.

  

Single device unreachable:

  

- one expected device has failed or missing evidence

- nearby expected devices remain visible

- bus-wide health does not show severe pressure

- topology does not imply multiple downstream devices should be affected

  

Possible branch isolation:

  

- devices in one topology branch are missing or stale

- devices outside the branch remain visible

- passive CAN or vendor evidence supports the same branch boundary

  

Possible trunk break:

  

- multiple downstream expected devices are missing or stale

- upstream expected devices remain visible

- affected devices share a topology path after a common edge or segment

  

Controller-side isolation:

  

- robot-local evidence disagrees strongly with passive observer evidence

- roboRIO-local health or console warnings indicate broad CAN trouble

- passive observer sees devices that robot-local runtime cannot use, or the reverse

  

Bus-wide error pressure:

  

- bus-off, TX full, RX/TX error deltas, or high timeout clustering is observed

- multiple unrelated topology regions report degraded behavior in the same window

  

Intermittent or stale visibility:

  

- devices transition between present and missing across recent windows

- evidence ages are high or inconsistent

- stale full-probe or stale runtime snapshots conflict with fresh passive evidence

  

Topology or profile mismatch:

  

- observed devices are not in the profile

- expected devices are absent but unexpected IDs with similar manufacturer/type are present

- topology has insufficient neighbor data to support region inference

  

## UI Requirements

  

Purpose: make the result useful during pit debugging.

  

Evidence tab:

  

- Add `CAN Fault Candidates [NEW]` near the top of the evidence details.

- Show the top candidate first.

- Show `Run CAN Break Check` status and age.

- Show source freshness in plain language.

- Keep raw evidence panels available below the candidate summary.

  

Live Topology tab:

  

- Highlight affected devices for the selected top candidate.

- If a suspected region is known, highlight the candidate edge or branch.

- If exact edge highlighting is not implemented yet, highlight the affected node set and print the suspected region text.

  

Device Summary table:

  

- Add a compact candidate indicator when a selected device is part of the top candidate.

- Do not replace per-device evidence columns.

  

## Implementation Plan

  

Purpose: define the short sequence for the final push.

  

### Step 1: Shared Fault Inference Service

  

Create `tools/can_nt/can_fault_inference.py`.

  

The service should be pure Python with no UI dependency. It should accept a normalized observation bundle and return a candidate result object.

  

Add unit tests for:

  

- all expected devices healthy

- one motor disconnected

- one downstream branch disconnected

- PDP-like power device visible only through passive CAN

- stale full-probe result conflicting with fresh passive evidence

- console timeout cluster

- bus-wide error pressure

- profile/topology mismatch

  

### Step 2: Observation Window

  

Add a host-side `Run CAN Break Check` action.

  

The action should freeze a short observation bundle instead of reading every panel from live rolling state independently.

  

The frozen bundle should include:

  

- passive discovery snapshot

- runtime presence snapshot

- console snapshot

- CAN bus health snapshot

- latest full probe snapshot

- latest manual result snapshot

- latest enrichment snapshot

- topology/profile snapshot

  

### Step 3: Evidence UI Integration

  

Add the candidate panel to the Evidence tab.

  

The panel should display:

  

- run state

- top candidate summary

- confidence

- affected devices

- suspected region

- supporting evidence

- conflicting evidence

- recommended checks

  

### Step 4: Topology Highlighting

  

Connect the top candidate to the topology renderer.

  

First pass:

  

- color affected nodes with the candidate severity

- show a selected-candidate summary in the right-side details

  

Second pass:

  

- highlight suspected branch or edge when topology data is specific enough

  

### Step 5: Enrichment Contribution

  

Finish host enrichment contribution for CTRE devices.

  

Minimum CTRE behavior:

  

- record whether CTRE HTTP ran

- record whether the CTRE device was found

- record faults/sticky faults when available

- record unsupported/unreachable states distinctly

- feed that result into final device status and fault candidates

  

REV behavior can remain future work unless the REV USB source is available in the same session.

  

### Step 6: Sanity Test Document

  

Update the sanity test document with physical fault cases:

  

- all-connected baseline

- disconnect FALCON 9 CAN wire

- reconnect FALCON 9 CAN wire

- disconnect SPARKMAX/NEO 25 CAN wire

- reconnect SPARKMAX/NEO 25 CAN wire

- disconnect PDP branch or power device

- stale full-probe case

- CTRE enrichment ran and did not run

  

Each case should list expected candidate output, expected device summary output, and expected topology coloring.

  

## Acceptance Criteria

  

Purpose: define when the final push is complete.

  

The work is complete when:

  

- Evidence tab shows a `CAN Fault Candidates [NEW]` panel.

- `Run CAN Break Check` produces a timestamped frozen diagnosis result.

- A disconnected motor produces a clear candidate that says the selected motor or local branch is suspect.

- Multiple missing downstream devices produce a branch or trunk candidate instead of independent single-device guesses.

- Stale full-probe evidence is visibly downgraded and cannot mask fresh failed evidence.

- CTRE HTTP enrichment contribution is visible when run and clearly marked when not run.

- Live Topology can highlight affected nodes for the top candidate.

- Unit tests cover the inference service.

- The sanity test document includes the physical break workflow.

  

## Tradeoffs

  

The first implementation should prefer honest, useful uncertainty over aggressive root-cause claims.

  

Node highlighting is acceptable before edge-level highlighting because it is easier to implement safely and still helps the operator.

  

A short frozen observation window is more important than continuously updating candidate text because CAN faults are easier to debug when every panel is describing the same time range.

  

## Future Extensions

  

Future work can add:

  

- multi-observer source placement metadata

- edge-level confidence scoring

- operator clue weighting

- before/after repair comparison

- REV USB enrichment

- guided student checklist mode

- exportable fault diagnosis JSON reports