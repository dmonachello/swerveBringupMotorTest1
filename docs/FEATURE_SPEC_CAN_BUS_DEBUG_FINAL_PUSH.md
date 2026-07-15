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
- There is no small, explicit per-device scoring contract by device class.
- There is no explicit per-device transition/event model.
- There is no explicit dirty-device reevaluation contract.
- There is no explicit source freshness decay table.
- There is no explicit distinction between positive evidence, negative evidence, and out-of-scope evidence.
- The current evidence interpretation path has too many overlapping heuristics.
- Multi-observer data is collected but not yet used to localize a break.
- CTRE HTTP enrichment is not yet treated as a first-class CTRE device evidence contributor in the final status.
- REV USB/vendor enrichment is not complete.
- UI panels show facts but do not yet provide an ordered "check this first" recommendation.

## Product Behavior

Purpose: define the operator-facing behavior.

Add a `Run CAN Break Check` workflow. When run, the host captures a short, labeled observation window and produces a frozen diagnosis result.

The implementation must not rely on a full synchronous sweep of every device in one invocation. The host evaluator must update cached per-device results incrementally and only process a small number of devices per scheduler slice.

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

The UI should show the result in a dedicated tab:

- New tab: `CAN Fault Finder`

Evidence and Live Topology should remain supporting views. They may link to the active fault-finder result, but they should not become the main fault-diagnosis surface.

## Diagnosis Modes

Purpose: separate always-updating current-state diagnosis from historical known-good comparison so the operator can tell which lens produced the recommendation.

The product must support two explicit diagnosis modes:

- `Live Diagnosis`
  - uses current raw source snapshots and the current shared interpreted-device cache
  - optimized for current-state troubleshooting and watching a fault appear, persist, or recover
  - default mode
- `Baseline Compare Diagnosis`
  - uses the current observation plus one selected compatible known-good baseline snapshot
  - optimized for startup-in-broken-state troubleshooting when the problem existed before the app or robot was started
  - opt-in mode

Required UI rule:

- `CAN Fault Finder` must display which diagnosis mode produced the current result

Required explanation rule:

- the rendered result must clearly label live-source evidence separately from baseline-difference evidence

Required behavior rule:

- `Live Diagnosis` must remain usable when no baseline exists
- `Baseline Compare Diagnosis` must fail soft when no compatible baseline exists and must explain why comparison is unavailable

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

## Device Class Model

Purpose: define the first explicit device classes so evidence rules stay small and deterministic.

Device classes:

- `motion_device`
  - examples: TalonFX, Spark MAX, CANcoder, and other profile devices that participate in active motion tests
  - primary sources:
    - passive CAN
    - robot-local runtime presence snapshot
    - full probe
    - manual motion result
    - console
    - enrichment
- `infrastructure_device`
  - examples: `roborio`, `pdp`, `pdh`
  - primary sources:
    - passive CAN
    - singleton runtime telemetry
    - console
    - enrichment
    - full probe only as additive evidence
  - important rule:
    - absence from active motion scope is not definitive missing evidence
- `unprofiled_device`
  - examples: passive-only observed devices not in the selected profile
  - primary sources:
    - passive CAN
    - enrichment when available
  - important rule:
    - classify observed/unobserved and mismatch relevance before making stronger health claims

## Incremental Evaluation Model

Purpose: define an implementation that fits the scheduler time budget and still converges to a consistent shared result.

The evaluator must not run a full nested loop over all devices in one call.

Instead, it must keep a persistent cursor:

- current device class index
- current device index within that class
- cached per-device interpreted result
- last-updated timestamp per device

Each evaluator invocation should:

- process only a small fixed budget such as one or two devices
- gather only the evidence sources relevant for that device class
- compute one score per allowed source
- combine those scores into one presence-oriented device result
- store the updated result back on the device object/cache
- advance the cursor so the next invocation continues where the last one stopped

The diagnosis surfaces should read from that shared cached interpreted state instead of re-composing separate meanings independently.

The `Run CAN Break Check` workflow should freeze:

- the current raw source snapshots
- the current shared interpreted-device cache
- the evaluation timestamps/freshness for those cached device results

The evaluator may continue running after the freeze is produced, but the frozen diagnosis result must remain tied to the exact cache/snapshot version that existed when the run started.

## Known-Good Baseline Model

Purpose: support startup-in-broken-state diagnosis by comparing the current observation to a previously confirmed healthy snapshot.

The system must support saving one or more known-good baseline snapshots per profile.

Each baseline snapshot must include:

- profile name
- topology/profile version or compatibility fingerprint
- capture timestamp
- raw source snapshots needed for comparison
- shared interpreted-device cache snapshot
- per-device freshness metadata
- per-device source scores
- infrastructure summary
- operator label indicating that the run was confirmed healthy

The current observation bundle may compare against a compatible baseline snapshot and emit additive baseline-difference evidence.

Baseline comparison is required to answer questions like:

- which devices were visible in the known-good state but are missing now
- which infrastructure devices had valid singleton telemetry in the known-good state but not now
- which branches had visible downstream devices in the known-good state but not now
- which console warning families are new relative to the known-good state

Baseline comparison must be additive evidence only.

Required rule:

- a baseline snapshot must never override fresh direct evidence from the current run

Mode rule:

- baseline comparison belongs to `Baseline Compare Diagnosis`, not the default `Live Diagnosis` lens

Compatibility rules:

- baseline comparison is valid only when the selected profile matches
- topology/profile compatibility must be checked before using a baseline
- if the compatibility check fails, the UI must say the baseline is incompatible and must not use it for scoring
- if the baseline is old enough to be suspicious, the UI may still use it but must mark the baseline as aging or stale

First-pass operator workflow:

- add an action to mark the current run as `Known Good`
- add a way to see which baseline is currently selected for comparison
- add a way to clear or replace the baseline for the selected profile
- add a way to enter `Baseline Compare Diagnosis` explicitly
- add a way to return to `Live Diagnosis`

## Baseline Difference Evidence

Purpose: define the exact comparison outputs that the device combiner and fault inference layer may consume.

For each device, the baseline comparison layer may emit:

- `baselinePresentThenMissing`
- `baselineMissingThenPresent`
- `baselineStateMatch`
- `baselineIncompatible`
- `baselineUnknown`

Per-device baseline evidence should include:

- baseline presence state
- baseline operability state
- current presence state
- current operability state
- difference summary
- baseline age/freshness

Required combiner rules:

- `baselinePresentThenMissing` may raise the priority of a current missing/conflict device
- `baselineMissingThenPresent` may lower suspicion if the baseline was not actually healthy for that device
- `baselineStateMatch` may slightly increase confidence in the current interpretation
- `baselineIncompatible` may not contribute to device scoring

Required fault-inference rule:

- when two candidate regions are otherwise similar, the one that better explains the difference from the known-good baseline should rank higher

## Device Status Model

Purpose: define the exact shared per-device state object that every surface must consume.

Each expected profile device must have one shared interpreted-device object with at least these fields:

- `label`
- `deviceType`
- `presenceScore`
- `presenceState`
- `operabilityState`
- `freshnessState`
- `confidence`
- `lastKnownGoodAt`
- `lastSeenPresentAt`
- `lastSeenMissingAt`
- `lastStateChangeAt`
- `lastEvaluationAt`
- `changeReason`
- `dirty`
- `dirtyReasons`
- `supportingEvidence`
- `conflictingEvidence`
- `sourceScores`

Required enumerations:

- `presenceState`
  - `present`
  - `missing`
  - `unknown`
  - `conflict`
- `operabilityState`
  - `ok`
  - `degraded`
  - `failed`
  - `unknown`
- `freshnessState`
  - `fresh`
  - `aging`
  - `stale`

Interpretation rule:

- `presenceState` answers whether the device appears to exist on the CAN/runtime path.
- `operabilityState` answers whether the device appears usable even if present.
- `freshnessState` answers whether the current conclusion is based on recent enough evidence to trust.

Surface rule:

- `Evidence`, `Live Topology`, `CAN Fault Finder`, and any compact summary surface must all read this same shared interpreted-device object.

## Source Semantics Contract

Purpose: make each source claim small and explicit so the combiner does not guess.

Each source must emit one of these claim types for a device:

- `positive`
  - the source observed evidence supporting presence or operability
- `negative`
  - the source observed evidence supporting missing or failed status
- `not_applicable`
  - the source does not apply to this device class or current session
- `out_of_scope`
  - the source could have applied in general but this device was not in scope for the current run
- `stale`
  - the source has historical evidence, but it is too old to act as current truth
- `unknown`
  - the source ran or was consulted, but it did not produce a meaningful claim

Additional additive comparison source:

- `baseline_compare`
  - compares current shared interpreted-device state against the selected known-good baseline
  - may only add comparison evidence; it may not replace live-source semantics

Required rule:

- `out_of_scope` is never equivalent to `negative`.

Per-source first-pass meaning:

- `passive_can`
  - `positive`: fresh packets or fresh last-seen evidence for the specific device
  - `negative`: explicit fresh observer-side missing signal if available
  - `stale`: historical packets without fresh last-seen evidence
- `robot_local`
  - `positive`: runtime snapshot explicitly reports device present or singleton infrastructure telemetry is fresh
  - `negative`: runtime snapshot explicitly reports device absent and this lens is valid for the device class
  - `out_of_scope`: active motion/lifecycle scope does not include the device
- `full_probe`
  - `positive`: fresh probe result says present or usable
  - `negative`: fresh probe result says absent or failed
  - `out_of_scope`: probe did not include the device in the current run
  - `stale`: probe result exists but is older than the freshness threshold
- `console`
  - `positive`: usually not used as the primary presence source
  - `negative`: fresh device-specific timeout/fault/error text tied to the device or a strong system-wide CAN failure signal
  - `unknown`: no relevant message in the current window
- `manual`
  - `positive`: observed correct response
  - `negative`: observed no response / wrong response / wrong target based on the vocabulary
  - `not_applicable`: no manual test was run
- `ctre_http` / `rev_usb` / enrichment
  - `positive`: vendor-side source found the device and returned valid telemetry
  - `negative`: vendor-side source explicitly could not find the device or returned definitive fault state
  - `unknown`: source did not run or returned unsupported

## Source Freshness Policy

Purpose: define when a source is considered current enough to influence state changes.

Each source score must carry:

- `state`
- `claimType`
- `score`
- `observedAt`
- `freshnessState`
- `reason`

If a baseline comparison source score exists, it must also carry:

- `baselineCapturedAt`
- `baselineCompatibility`

First-pass freshness policy:

- passive CAN
  - `fresh`: seen within the short live-observer freshness window
  - `aging`: older than fresh but still recent enough to show history
  - `stale`: older than the passive stale threshold
- singleton runtime telemetry
  - `fresh`: telemetry timestamp within the short infrastructure/runtime freshness window
  - `aging`: recent but not current
  - `stale`: too old to support current presence
- full probe
  - `fresh`: within the active probe freshness window
  - `aging`: recent enough to show historical result
  - `stale`: cannot override fresher passive/runtime evidence
- console
  - `fresh`: error/warning occurred within the current diagnosis window
  - `aging`: recent but no longer sufficient to drive a strong claim alone
  - `stale`: historical only
- manual
  - `fresh`: from the current operator test workflow
  - `aging`: recent but not current
  - `stale`: historical only
- baseline comparison
  - `fresh`: baseline is recent and profile/topology-compatible
  - `aging`: baseline is compatible but old enough to deserve caution
  - `stale`: baseline is too old to contribute more than weak comparison context

Required combiner rule:

- a stale `positive` source must never block a fresh `negative` source from forcing reevaluation
- a stale `negative` source must never override a fresh `positive` source

Implementation note:

- exact second values may live in constants/config, but the source ordering and freshness semantics above are part of the contract

## Dirty Device Reevaluation Model

Purpose: make status-change detection event-driven instead of waiting for a full sweep.

Each device must maintain:

- `dirty`
- `dirtyReasons`
- `lastDirtyAt`

The evaluator must process dirty devices before continuing the normal cursor walk.

Events that must mark a device dirty immediately:

- passive CAN fresh last-seen transition to missing/stale
- passive CAN fresh reappearance after being missing/stale
- runtime presence transition
- singleton infrastructure telemetry transition
- full probe result change
- full probe freshness aging to stale
- manual result change
- new device-specific console timeout/error
- new system-wide CAN console error affecting a mapped device set
- active-group activation/deactivation or lifecycle scope change affecting the device
- profile reload or topology reload
- baseline selection, replacement, or clear for the active profile

Dirty-queue priority:

1. devices with fresh negative evidence
2. devices with fresh positive reappearance after missing/conflict
3. devices with fresh device-specific console events
4. devices affected by scope/profile changes
5. devices whose baseline comparison result changed
6. normal cursor continuation

Required rule:

- `Run CAN Break Check` must perform a bounded catch-up over dirty devices first before freezing the result

## Device Transition Model

Purpose: detect and explain status changes explicitly instead of only recomputing a snapshot.

Each evaluation of a device must compare the newly combined result against the prior shared result.

Transitions that must be recorded explicitly:

- `present -> missing`
- `missing -> present`
- `present -> conflict`
- `conflict -> present`
- `present -> unknown`
- `unknown -> present`
- `ok -> degraded`
- `degraded -> ok`
- `degraded -> failed`
- `fresh -> aging`
- `aging -> stale`

Each transition record must include:

- `deviceLabel`
- `oldPresenceState`
- `newPresenceState`
- `oldOperabilityState`
- `newOperabilityState`
- `oldFreshnessState`
- `newFreshnessState`
- `at`
- `source`
- `reason`

Required state update rules:

- when a device becomes `present`, update `lastSeenPresentAt`
- when a device becomes `missing`, update `lastSeenMissingAt`
- when a device becomes `present` from a previously non-present state, update `lastKnownGoodAt`
- when any state changes, update `lastStateChangeAt` and `changeReason`

Baseline comparison may strengthen confidence in a transition explanation, but it may not invent a transition that was not observed in the current shared device state.

## Class-Based Source Priority Rules

Purpose: remove vague override behavior and replace it with small deterministic rules by device class.

### Motion Devices

Allowed primary sources:

- passive CAN
- robot-local runtime presence
- full probe
- manual

Allowed additive sources:

- console
- enrichment
- baseline comparison

Required first-pass rules:

- fresh agreement between any two primary sources may produce `present` or `missing`
- one fresh strong negative primary source with no fresh positive primary source may produce `missing`
- one fresh strong positive primary source with no contradiction may produce `present`
- disagreement between fresh primary sources produces `conflict`
- additive sources may downgrade confidence or operability, but may not alone upgrade `unknown` to `present`

### Infrastructure Devices

Allowed primary sources:

- passive CAN
- singleton runtime telemetry

Allowed additive sources:

- console
- enrichment
- full probe
- baseline comparison

Required first-pass rules:

- active motion-scope absence or probe out-of-scope may never by itself produce `missing`
- fresh passive CAN plus fresh singleton runtime telemetry may produce `present`
- fresh loss of both passive CAN and singleton runtime telemetry after previously being present may produce `missing` or `conflict` depending on disagreement history
- fresh console/controller-side failures may downgrade operability or push toward `conflict`
- stale passive or stale singleton runtime evidence may not keep the device in `present`

### Unprofiled Devices

Allowed primary sources:

- passive CAN
- enrichment

Allowed additive sources:

- baseline comparison

Required first-pass rules:

- classify primarily as observed / not observed / stale / mismatch-relevant
- do not claim healthy operability from passive presence alone
- surface as topology/profile mismatch evidence when relevant to a missing expected device

## Device Event Log

Purpose: preserve a short explainable history for debugging and operator trust.

Maintain a short rolling per-device event log with entries:

- `at`
- `source`
- `eventType`
- `oldValue`
- `newValue`
- `reason`

First-pass required event types:

- `presence_gained`
- `presence_lost`
- `operability_degraded`
- `operability_recovered`
- `freshness_became_stale`
- `console_fault_seen`
- `probe_result_changed`
- `scope_changed`

UI requirement:

- the event log may stay secondary/collapsed in first pass, but it must exist in the shared state so inconsistent behavior can be debugged without guessing

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

Class-specific interpretation rule:

- For `infrastructure_device`, the `robot_local` active motion-scope absence lens may downgrade confidence, but it must not by itself produce a definitive missing claim.

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

Device scoring rule:

- Per-device interpretation should first converge on a shared device result from class-specific source scores before the fault-candidate layer tries to infer branch, trunk, or controller-side hypotheses.

## UI Requirements

Purpose: make the result useful during pit debugging.

CAN Fault Finder tab:

- Add a new top-level UI tab named `CAN Fault Finder`.
- Put `Run CAN Break Check` at the top of the tab.
- Show run state, run age, observation window duration, and source freshness.
- Show the top candidate first.
- Show all ranked candidates below the top candidate.
- Show affected devices, suspected region, supporting evidence, conflicting evidence, and recommended checks.
- Include a compact topology preview or selected-candidate device list if space allows.
- Keep raw source details collapsed or secondary so this tab stays focused on action.

Evidence tab:

- Keep per-device evidence interpretation as the primary purpose.
- Add only a compact reference to the active fault-finder result when the selected device is part of the top candidate.
- Do not add large fault-candidate panels to this already crowded tab.

Live Topology tab:

- Highlight affected devices for the selected top candidate.
- If a suspected region is known, highlight the candidate edge or branch.
- If exact edge highlighting is not implemented yet, highlight the affected node set and print the suspected region text.
- Do not add the full fault-candidate explanation to this already crowded tab.

Device Summary table:

- Add a compact candidate indicator when a selected device is part of the top candidate.
- Do not replace per-device evidence columns.

## Implementation Plan

Purpose: define the short sequence for the final push.

### Step 1: Shared Device-Class Scoring Service

Create `tools/can_nt/can_fault_inference.py`.

The service should be pure Python with no UI dependency.

The service should:

- define device classes
- define allowed evidence sources by class
- define per-source scoring helpers
- define score-combination rules by class
- define freshness/decay rules by source
- define dirty-device trigger rules
- define explicit transition/event recording
- define baseline snapshot compatibility and difference helpers
- define the final shared interpreted per-device result object
- accept incremental updates for one device at a time
- return a cached interpreted device map that other surfaces can consume

The service must support a persistent evaluation cursor so it can continue where it left off on the next invocation instead of rescoring the full device list every time.

Add unit tests for:

- motion device healthy
- motion device missing
- infrastructure device visible through passive CAN only
- infrastructure device visible through singleton runtime telemetry only
- infrastructure device outside active scope but not treated as missing
- infrastructure device previously present, then passively/runtime missing, becomes missing or conflict after freshness expiry
- stale full-probe result downgraded below fresh passive/runtime evidence
- unprofiled device observed on passive CAN
- device-specific console error marks the target device dirty immediately
- fresh negative evidence is evaluated before normal cursor continuation
- `present -> missing` transition updates transition metadata and event log
- `missing -> present` transition updates recovery metadata and event log
- compatible known-good baseline raises confidence for a current missing device that used to be present
- incompatible baseline does not affect scoring
- cursor resumes correctly and only evaluates the configured per-tick budget

### Step 2: Observation Window

Add a host-side `Run CAN Break Check` action.

The action should freeze a short observation bundle instead of reading every panel from live rolling state independently.

The action must not force a full synchronous per-device evaluation pass in one UI event.

The frozen bundle should include:

- passive discovery snapshot
- runtime presence snapshot
- console snapshot
- CAN bus health snapshot
- latest full probe snapshot
- latest manual result snapshot
- latest enrichment snapshot
- topology/profile snapshot
- shared interpreted per-device cache snapshot
- per-device interpreted-result freshness
- dirty-device queue snapshot or equivalent dirty-state metadata
- per-device recent transition/event records needed to explain the run
- selected known-good baseline metadata and compatibility state when available
- evaluation cursor generation/timestamp metadata as needed to label the run honestly

If the implementation performs a bounded catch-up pass before freezing, that catch-up must still respect the scheduler slice budget and remain explicitly bounded.

If a frozen run does not evaluate all dirty devices before the freeze deadline, the run must not claim `no_fault_detected` with high confidence. It must instead surface stale/incomplete evaluation language explicitly.

Mode-specific freeze rule:

- `Live Diagnosis` freezes only current-run evidence and current shared interpreted-device state
- `Baseline Compare Diagnosis` freezes both the current-run evidence and the selected baseline metadata/difference outputs used for the comparison

### Step 3: CAN Fault Finder UI Integration

Add a new `CAN Fault Finder` tab.

The tab should display:

- diagnosis mode
- run state
- top candidate summary
- confidence
- affected devices
- suspected region
- supporting evidence
- conflicting evidence
- recommended checks
- ranked candidate list
- compact source freshness summary
- baseline comparison status when a compatible known-good snapshot is selected

Mode-specific UI rules:

- `Live Diagnosis` should emphasize current evidence freshness and recent transitions
- `Baseline Compare Diagnosis` should emphasize current-vs-baseline differences and baseline compatibility/freshness
- the UI must not present baseline-derived findings as if they were live direct observations

Keep Evidence and Live Topology integrations small:

- Evidence can show whether the selected device is part of the active top candidate.
- Live Topology can highlight affected nodes or regions.
- Both surfaces must consume the same shared interpreted-device result path used by the fault finder.

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

Add scheduler-slice sanity expectations:

- evaluator processes only the configured per-tick device budget
- evaluator resumes at the next device on the next invocation
- diagnosis surfaces remain readable while the evaluator is converging

## Acceptance Criteria

Purpose: define when the final push is complete.

The work is complete when:

- UI includes a dedicated `CAN Fault Finder` tab.
- `Run CAN Break Check` produces a timestamped frozen diagnosis result.
- A disconnected motor produces a clear candidate that says the selected motor or local branch is suspect.
- Multiple missing downstream devices produce a branch or trunk candidate instead of independent single-device guesses.
- Infrastructure devices are not marked missing from active motion-scope absence alone.
- Stale full-probe evidence is visibly downgraded and cannot mask fresh failed evidence.
- CTRE HTTP enrichment contribution is visible when run and clearly marked when not run.
- Live Topology can highlight affected nodes for the top candidate.
- Evidence tab remains primarily a per-device evidence view and does not become the main fault-finder surface.
- Unit tests cover the inference service.
- The sanity test document includes the physical break workflow.
- The evaluator updates devices incrementally without requiring a full synchronous sweep that would overrun the scheduler slice.
- `CAN Fault Finder`, `Evidence`, and `Live Topology` all read the same shared interpreted-device state.
- Fresh disconnect and reconnect events change the affected device state within the bounded dirty-device catch-up behavior.
- A stale cached `present` result cannot survive after both primary infrastructure sources have aged out.
- A device-specific console fault causes the target device to be reevaluated before a normal low-priority cursor device.
- The system records enough transition/event metadata to explain why a device changed state.
- The system can compare the current run to a compatible known-good baseline without letting the baseline override fresh direct evidence.
- A startup-in-broken-state run can still use baseline differences to raise suspicion on devices or regions that were previously healthy.
- The operator can tell whether the current `CAN Fault Finder` result came from `Live Diagnosis` or `Baseline Compare Diagnosis`.

## Tradeoffs

The first implementation should prefer honest, useful uncertainty over aggressive root-cause claims.

Node highlighting is acceptable before edge-level highlighting because it is easier to implement safely and still helps the operator.

A short frozen observation window is more important than continuously updating candidate text because CAN faults are easier to debug when every panel is describing the same time range.

An incremental cursor-based evaluator is preferable to a one-shot full sweep because the host must respect scheduler time budgets. The tradeoff is that a full-device picture converges over several slices, so freshness metadata must remain visible and honest.

## Future Extensions

Future work can add:

- multi-observer source placement metadata
- edge-level confidence scoring
- Bayesian fusion after the deterministic source semantics are stable
- automatic baseline recommendation / expiration policy
- operator clue weighting
- before/after repair comparison
- REV USB enrichment
- guided student checklist mode
- exportable fault diagnosis JSON reports
