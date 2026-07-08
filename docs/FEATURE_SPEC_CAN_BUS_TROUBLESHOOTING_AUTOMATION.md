SPEC_STATUS: RESEARCH_ONLY

# Feature Spec: CAN Bus Troubleshooting Automation

## Purpose

Define a practical, evidence-driven CAN bus troubleshooting workflow for finding likely loose wires, open segments, branch isolation, intermittent connectors, and bus-wide error conditions.

This spec builds on the existing multi-observer, topology, evidence, and operator-clue work, but narrows the problem into a field workflow that can guide a student operator toward the next physical check.

## Prior Project Work Scanned

The following project docs and notes already contain pieces of this design:

- `docs/FEATURE_SPEC_MULTI_OBSERVER_CAN_FAULT_LOCALIZATION.md`
- `docs/SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md`
- `docs/SPEC_OPERATOR_CLUES_MODEL.md`
- `docs/SPEC_BREAK_AND_ERROR_OPERATOR_SURFACES.md`
- `docs/SPEC_BREAK_ERROR_IMPLEMENTATION_TRACE.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`
- `docs/FEATURE_SPEC_CAN_EVIDENCE_UI.md`
- `docs/FEATURE_SPEC_PIT_ROBOT_DIAGNOSIS_FIRST_PASS.md`
- `notes/research/can_evidence/TEST_WORKFLOW_TASK1.md`
- `notes/research/can_evidence/reviews/CONSOLE_MESSAGE_FAMILY_INVENTORY_TASK2.md`
- `notes/research/can_evidence/reviews/REPRESENTATIVE_TEST_OBSERVATIONS_TASK8.md`
- `notes/research/can_evidence/reviews/FIRST_PASS_DEVICE_CLASS_COVERAGE_TASK4.md`
- `notes/research/can_evidence/run_notes/2026-06-03_profile_test_minimal_25_9_all_connected_baseline.md`
- `notes/research/can_evidence/run_notes/2026-06-03_profile_test_minimal_25_9_pdp_disconnected_startup.md`
- `notes/research/can_evidence/run_notes/2026-06-03_profile_test_minimal_25_9_falcon_9_disconnected_startup.md`
- `notes/research/can_evidence/run_notes/2026-06-03_profile_test_minimal_25_9_sparkmax_disconnected_startup.md`
- `notes/research/can_evidence/run_notes/2026-06-03_profile_test_minimal_25_9_roborio_isolated_from_can_bus.md`

The important design constraints inherited from those docs are:

- use `neighborPorts` as the preferred semantic topology graph
- preserve `neighborLinks` only as a lower-fidelity fallback
- keep passive CAN tools read-only
- treat operator clues as weighted evidence, not truth
- output candidate fault regions with evidence provenance
- avoid claiming exact electrical root cause from passive evidence alone
- keep raw visibility and interpreted evidence as separate operator views

## Problem Statement

When a CAN wire comes loose, the observed symptom is rarely just "one device missing."

Depending on where the loose connection is, the robot may show:

- one device missing
- all devices downstream of a point missing
- one CANnect branch missing
- intermittent stale/recover cycles
- bus-off or error-spike behavior
- multiple device-specific timeout families at the same time
- a mismatch between what the roboRIO sees and what a PC-side passive observer sees

The current system has raw ingredients for diagnosis, but it still needs a workflow that answers:

- What physical region should I inspect first?
- Is this more likely one dead device or a bus propagation problem?
- Is this likely a local branch, trunk segment, controller-side isolation, or global bus health problem?
- What evidence supports that answer?
- What should I do next to reduce ambiguity?

## Product Goal

Given a known profile, topology, expected device list, passive CAN visibility, robot-side console/runtime evidence, and optional operator clues, produce a ranked troubleshooting result:

- likely fault class
- likely fault region
- confidence band
- supporting evidence
- conflicting evidence
- next physical checks
- suggested follow-up observation or test

The tool should help a high-school student inspect the right connector or segment first, while remaining honest about uncertainty.

## Non-Goals

This feature does not:

- directly measure CAN-H/CAN-L waveforms
- replace an oscilloscope or vendor diagnostic tool
- transmit CAN frames from the PC tool
- guarantee exact root cause from one passive observer
- blame a device solely because its vendor timeout message appeared
- hide raw evidence from advanced users

## Key Principle

The system should diagnose regions and evidence patterns before it diagnoses parts.

For example, if Spark and PDP timeouts appear in the same window while stale-message spam is heavy, that is stronger evidence for a broader communication separation than for two unrelated failed devices.

## Fault Mode Taxonomy

Purpose: define the physical fault classes the workflow should reason about.

## 1. Single Device Local Loss

Typical causes:

- device unplugged from CAN
- device unpowered
- failed local connector
- wrong CAN ID
- device firmware/config problem

Expected evidence:

- one expected device missing or stale
- other nearby topology devices remain visible
- device-specific console timeout may appear
- bus-wide errors may be absent or mild

Candidate output:

- `single_device_unreachable`

Confidence rule:

- can reach medium or high only when neighboring devices are visible and no broad communication evidence dominates

Recommended checks:

- inspect the device CAN connector
- verify device power
- verify configured CAN ID
- rerun a short observation window after reseating

## 2. Trunk Open Before Downstream Devices

Typical causes:

- loose connector between two trunk devices
- broken CAN-H or CAN-L wire in a chain
- unplugged segment upstream of several devices

Expected evidence:

- a contiguous downstream run of expected devices becomes missing or stale
- upstream devices remain visible
- console may show multiple device timeout families
- passive observer placement strongly affects what is visible

Candidate output:

- `possible_trunk_open_before_device`
- `possible_break_between_segments`

Confidence rule:

- with one observer, confidence should usually be capped at medium
- with two observers on opposite sides of the suspected region, confidence may rise

Recommended checks:

- inspect the connector immediately before the first missing downstream device
- inspect both ends of the segment between the last visible device and first missing device
- rerun the observation window after reseating that segment

## 3. Branch Isolation

Typical causes:

- CANnect branch cable loose
- subsystem branch disconnected
- branch termination or splice problem

Expected evidence:

- devices on one branch are missing or unstable
- devices on other branches remain visible
- topology `neighborPorts` points to a common branch port
- operator may report one subsystem is dead while the rest of the robot works

Candidate output:

- `possible_branch_isolation`
- `branch_localized_fault`

Confidence rule:

- confidence increases when affected devices share one topology branch and unaffected devices on sibling branches remain healthy

Recommended checks:

- inspect the branch cable at the hub/CANnect side
- inspect the first device connector on the affected branch
- compare branch LED or power clues if available

## 4. Controller-Side Isolation

Typical causes:

- roboRIO CAN connection loose
- CAN adapter/harness disconnected near the controller
- upstream trunk break near the controller

Expected evidence:

- robot console sees multiple device families timing out together
- passive PC observer may still see downstream traffic if attached downstream
- roboRIO-side active probes fail broadly
- many downstream devices may look unreachable from the robot at once

Candidate output:

- `possible_controller_side_isolation`

Confidence rule:

- do not report several unrelated device failures when many device classes fail in the same window
- prefer a broad controller-side candidate unless topology/passive evidence proves otherwise

Recommended checks:

- inspect roboRIO CAN high/low connections
- inspect first trunk segment after the controller
- compare passive observer visibility against robot-local probe results

## 5. Intermittent Connector Or Vibration Fault

Typical causes:

- partially seated connector
- weak crimp
- broken conductor making occasional contact
- failure only under movement or load

Expected evidence:

- repeated stale/recover cycles
- age and rate fluctuate for one device, segment, or branch
- bus-off or error-spike events may occur
- operator may report that touching or moving a cable changes behavior

Candidate output:

- `possible_intermittent_segment`
- `unstable_visibility_region`

Confidence rule:

- confidence should depend on repeated observations over a defined window
- one stale sample is not enough

Recommended checks:

- gently move the suspected harness while observing visibility
- inspect crimps and strain relief
- capture before/after windows around a reseat

## 6. Bus-Wide Error Pressure

Typical causes:

- termination problem
- CAN-H/CAN-L short or near-short
- noise or bad wiring quality
- excessive traffic or startup pressure
- severe intermittent fault causing repeated retries

Expected evidence:

- `BUS_OFF_EVENT`
- `CAN_ERROR_SPIKE`
- repeated stale-message families
- broad visibility instability
- high utilization or recovery messages may appear

Candidate output:

- `bus_wide_error_pressure`

Confidence rule:

- do not localize to a segment unless topology evidence also identifies a boundary
- degrade confidence for local break candidates while global pressure is active

Recommended checks:

- verify termination resistance with robot powered off
- inspect for CAN-H/CAN-L shorts
- inspect recent wiring changes first
- compare baseline all-connected behavior against the current run

## 7. Topology Or Configuration Mismatch

Typical causes:

- expected topology does not match the physical robot
- wrong CAN ID in profile
- device moved to a different branch
- stale host/robot profile mismatch

Expected evidence:

- passive traffic exists for an unexpected ID
- expected device is missing but a similar unknown device is visible
- manual stimulus moves the wrong device
- topology-inference result conflicts with operator observation

Candidate output:

- `possible_topology_model_mismatch`
- `possible_id_or_profile_mismatch`

Confidence rule:

- keep this candidate active whenever evidence does not fit the topology graph cleanly

Recommended checks:

- compare profile expected devices with live passive IDs
- run identity/mapping stimulus where safe
- verify host and robot selected profiles match

## Evidence Inputs

Purpose: define the information the troubleshooting workflow should combine.

## Diagnostic Capability Model

Purpose: define the internal vendor-neutral diagnostic object model the system wishes FRC devices exposed.

This project cannot assume a real cross-vendor FRC diagnostic standard exists.

However, the troubleshooting system should still define a canonical internal model that acts like a virtual FRC MIB.

That model serves three purposes:

- give the inference layer one stable vocabulary
- let each vendor/device adapter map into the same fields
- make gaps in vendor support explicit instead of implicit

This is not a claim that every device can provide every field.

It is the target schema that each device family should populate as fully as possible, with provenance and confidence preserved.

## Core Canonical Fields

Recommended baseline fields:

- `device.identity.vendor`
- `device.identity.model`
- `device.identity.deviceClass`
- `device.identity.canId`
- `device.identity.firmwareVersion`
- `device.presence.present`
- `device.presence.lastSeenAgeMs`
- `device.power.powered`
- `device.power.powerStateConfidence`
- `device.can.healthy`
- `device.can.participating`
- `device.can.rxFresh`
- `device.can.txExpected`
- `device.can.errorState`
- `device.can.errorCountersAvailable`
- `device.runtime.enabled`
- `device.runtime.controlMode`
- `device.runtime.operable`
- `device.runtime.faulted`
- `device.runtime.warnings`
- `device.indicator.color`
- `device.indicator.pattern`
- `device.indicator.meaning`
- `device.indicator.sourceType`

These fields should be treated as logically distinct.

For example:

- `powered` is not the same as `present`
- `present` is not the same as `operable`
- `can.participating` is not the same as `runtime.enabled`
- `indicator.meaning` is not the same as literal LED color/pattern

## Source Types

The canonical model should support multiple source types feeding the same logical field set.

Initial source types:

- `passiveCanObservation`
- `robotRuntimeProbe`
- `consoleDerivedEvent`
- `operatorLedObservation`
- `apiDerivedStatusEquivalent`
- `vendorNetworkDiagnostics`
- `vendorUsbGatewayDiagnostics`
- `manualStimulusResult`

Important rule:

- `operatorLedObservation` is literal human-observed LED state
- `apiDerivedStatusEquivalent` is machine-derived status that may map to LED-like meaning

The system must not pretend those are the same source.

If a vendor API status is mapped to indicator meaning, that mapping must be explicit, per-device-family, and testable.

## Why This Matters

Without a canonical diagnostic capability model, the project will drift into per-vendor special cases everywhere:

- inference logic
- UI rendering
- report output
- clue handling
- device support growth

With a canonical model, the project can keep one shared troubleshooting contract even when vendor support is uneven.

That means:

- some devices may only provide passive presence
- some may provide strong runtime/fault details
- some may support machine-derived indicator equivalents
- all can still participate in one consistent troubleshooting workflow

## LED State In This Model

LED state should be treated as one part of the larger diagnostic capability model, not as a standalone feature.

Recommended representation:

- `device.indicator.color`
- `device.indicator.pattern`
- `device.indicator.meaning`
- `device.indicator.sourceType`

Interpretation flow:

1. acquire raw LED or equivalent status evidence
2. normalize it into canonical indicator fields
3. attach vendor-specific interpretation metadata
4. feed the interpreted meaning into candidate scoring as device-local evidence

This keeps raw observation and interpreted meaning separate, which is necessary for debugging and trust.

## First Project Rule

For this project, the required baseline should be:

- manual/operator LED observation support is universal
- API-derived equivalent status is optional per device family
- provenance is always preserved in the evidence model

This keeps the architecture stable even if vendor automation support is inconsistent.

## Vendor Diagnostic Backchannels

Purpose: define the non-passive vendor-specific acquisition paths that can provide stronger real-time device status than raw CAN observation alone.

For the motor controllers, these vendor backchannels should be treated as first-class evidence sources, not as optional nice-to-have tooling.

The highest-priority device families are:

- `CTRE` motor controllers
- `REV` motor controllers

The practical reason is simple:

- they are high-value actuators
- they are common root-cause candidates in student troubleshooting
- they already expose richer status than passive CAN alone

## CTRE Network Diagnostics

Observed path:

- Phoenix Tuner talks to a roboRIO-hosted HTTP service on TCP port `1250`

Verified examples:

- `/?action=getdevices`
- `/?action=getversion`
- `/?action=blink&model=Talon%20FX&id=9&canbus=rio`

Implications:

- CTRE provides a machine-friendly network diagnostic surface
- device inventory, version, and at least some targeted actions are remotely queryable
- future read-only CTRE actions such as self-test or richer status should be treated as high-value acquisition targets

Troubleshooting role:

- inventory and identity confirmation
- live device-local status and fault evidence
- machine-derived evidence stronger than passive visibility for CTRE devices

## REV USB Gateway Diagnostics

Observed path:

- REV Hardware Client uses a USB connection
- one directly connected REV device can expose visibility into other REV devices on the robot

Implications:

- REV should not be modeled as only a single-device local USB tool
- the directly connected device appears to function as a vendor gateway into a broader REV device view
- this is a different transport than CTRE, but it may still provide multi-device vendor diagnostics

Troubleshooting role:

- REV inventory and identity confirmation
- REV-local fault/warning/status acquisition
- gateway-mediated status for other reachable REV devices

## Transport Difference Rule

The troubleshooting system must separate:

- `transport`
- `evidence meaning`

Examples:

- CTRE may deliver diagnostics through a network service
- REV may deliver diagnostics through a USB-accessed gateway
- passive CAN may deliver only visibility/freshness

These must normalize into the same canonical evidence model instead of creating separate troubleshooting logic per vendor transport.

## Acquisition Priority Rule

The project should prioritize vendor backchannel acquisition in this order:

1. machine-readable read-only vendor diagnostics for CTRE and REV motor controllers
2. robot-local runtime and vendor API evidence
3. passive CAN visibility and topology correlation
4. operator-entered LED and field clues

This ordering is about evidence strength, not user importance.

Operator clues still matter, but when a vendor already exposes direct real-time device status, the system should fully use it.

## First-Pass Project Requirement

For CTRE and REV motor controllers, the troubleshooting architecture should explicitly plan to consume the strongest available vendor-side real-time status path in addition to passive CAN.

That means:

- CTRE network diagnostics should be considered a primary evidence source candidate
- REV USB/gateway diagnostics should be considered a primary evidence source candidate
- passive CAN alone is not sufficient when richer vendor status is available

## Capability Enumeration Requirement

Purpose: require systematic discovery of all vendor-exposed diagnostic data before relying on hand-picked fields.

The project needs a full enumeration pass for each vendor backchannel.

Without this, the system will drift into:

- using only the fields already noticed manually
- missing high-value status and fault signals
- rebuilding partial discovery repeatedly
- creating per-vendor blind spots in troubleshooting

## Enumeration Goals

For each vendor acquisition path, the project should discover and record:

- reachable devices
- supported actions
- read-only versus mutating actions
- response schemas
- field names
- field types
- field value ranges or enums when observable
- update cadence if the data is polled or streaming
- device-family capability differences

This is discovery work first, interpretation work second.

## Required Enumeration Outputs

Each enumeration pass should produce a structured inventory artifact.

Recommended contents:

- `vendor`
- `transport`
- `deviceFamily`
- `deviceModel`
- `deviceId`
- `busName`
- `actionName`
- `actionSafetyClass`
- `responseFieldPath`
- `responseFieldType`
- `responseFieldExample`
- `observedEnumValues`
- `supportsPolling`
- `supportsSubscription`
- `notes`

This inventory is the backchannel equivalent of a field catalog or MIB walk.

## Action Safety Classes

Every discovered vendor action should be classified before it is used by the troubleshooting system:

- `read_only`
- `read_like_but_stateful`
- `visible_side_effect`
- `configuration_mutating`
- `unsafe_unknown`

Examples:

- `getdevices` is `read_only`
- `getversion` is `read_only`
- `blink` is `visible_side_effect`

No action should be used automatically until its safety class is known.

## CTRE Enumeration Direction

For CTRE, enumeration should start from the known discovery endpoint:

- `/?action=getdevices`

Then continue by observing Phoenix Tuner traffic to identify:

- additional `action=` values
- required parameters such as `model`, `id`, and `canbus`
- per-action JSON schemas
- which actions are read-only and safe to automate

The output should include both:

- server-global actions
- device-targeted actions

## REV Enumeration Direction

For REV, enumeration should start from the USB/gateway path used by REV Hardware Client.

The initial goal is to determine:

- whether the transport is serial-like or binary
- how devices are enumerated through the gateway
- what per-device status, fault, and identity fields are exposed
- whether the gateway exposes multi-device queries or only device-local queries

Because REV appears to use a gateway-style transport, enumeration should record both:

- gateway-level capabilities
- downstream device-level capabilities

## Canonical Mapping Rule

Enumeration and canonical mapping must stay separate.

Sequence:

1. enumerate vendor-visible fields and actions
2. record them in a raw inventory
3. classify safety and semantics
4. map stable fields into the canonical diagnostic model

This prevents premature normalization from hiding vendor-specific detail that may later matter.

## Inventory Artifact Requirement

The project should maintain machine-readable inventory artifacts for vendor backchannels, similar in spirit to CAN frame inventory work.

Recommended artifact types:

- vendor action inventory JSON
- vendor field inventory JSON
- before/after diff report when tool or firmware versions change

That enables:

- regression checking
- firmware-version comparison
- support-matrix generation
- explicit identification of newly exposed diagnostic fields

## First-Pass Project Requirement For Enumeration

For CTRE and REV motor controllers, the project should not stop at proving one or two useful endpoints.

The first serious integration pass should include:

- a repeatable enumeration workflow
- a saved inventory artifact
- safety classification for discovered actions
- a shortlist of stable read-only fields mapped into the troubleshooting evidence model

## Passive CAN Visibility

Source examples:

- `tools/can_nt/visibility_provider.py`
- CANable/slcan passive observation
- per-device age, FPS, message count, source visibility
- unknown/unrecognized raw node visibility

Use:

- existence and freshness evidence
- topology-contiguous missing/stale patterns
- observer disagreement when multiple observers exist

Limitation:

- passive visibility alone does not prove operability or identity/mapping

## Robot-Local Console And Runtime Evidence

Source examples:

- NetConsole messages parsed by `tools/can_nt/can_console_monitor.py`
- robot runtime state
- active vendor probe results when available

Use:

- device-specific timeout families
- bus-off and error-spike evidence
- broad roboRIO-to-bus communication failures

Limitation:

- multiple device-specific timeout messages can be consequences of one upstream communication separation

## Topology Evidence

Source examples:

- `neighborPorts`
- `neighborLinks`
- expected profile devices
- branch/port metadata

Use:

- identify contiguous affected regions
- identify branch-only failures
- identify last-visible and first-missing boundaries

Limitation:

- a wrong topology model can make correct observations look contradictory

## Operator Clues

Source examples:

- first failed device
- last known-good device
- LED color/pattern
- branch affected
- reseat changed behavior
- failure began after impact or motion

Use:

- improve candidate ranking
- reduce ambiguity when passive evidence is broad
- guide next physical check

Limitation:

- clues are weighted evidence, not truth

## Manual Stimulus And Test Results

Source examples:

- right-click motor control outcomes
- DSL test results
- manual motion observations

Use:

- operability evidence
- identity/mapping evidence
- before/after comparison after a physical change

Limitation:

- motion tests must remain robot-owned and safety-gated

## Inference Workflow

Purpose: define the staged reasoning path for the first implementation.

## Stage 1: Build Expected Graph

Inputs:

- selected host profile
- robot selected profile if connected
- topology graph
- expected device list

Outputs:

- normalized node list
- preferred `neighborPorts` graph
- fallback `neighborLinks` graph
- explicit graph quality warnings

Failure behavior:

- if topology is missing, fall back to device-list diagnosis and report `topology_unavailable`

## Stage 2: Collect Observation Window

Inputs:

- passive CAN visibility window
- console/runtime evidence window
- optional manual test/stimulus markers
- optional operator clues

Outputs:

- time-bounded evidence bundle

Rules:

- do not compare stale windows as if they are simultaneous
- record source freshness and source availability
- preserve raw evidence references

## Stage 3: Normalize Device States

Each expected device should receive a normalized state:

- `visible`
- `missing`
- `stale`
- `unstable`
- `unknown`
- `unrecognized_possible_match`

Each state should keep source-specific details instead of flattening them.

## Stage 4: Detect Topology Patterns

Pattern examples:

- one missing device with visible neighbors
- contiguous downstream missing run
- branch-only missing set
- multiple independent missing islands
- broad all-device timeout family cluster
- passive-visible but robot-local unreachable
- unknown ID near expected missing device

Patterns are intermediate findings, not final diagnoses.

## Stage 5: Generate Candidates

Candidate types:

- `single_device_unreachable`
- `possible_trunk_open_before_device`
- `possible_break_between_segments`
- `possible_branch_isolation`
- `possible_controller_side_isolation`
- `possible_intermittent_segment`
- `bus_wide_error_pressure`
- `possible_id_or_profile_mismatch`
- `possible_topology_model_mismatch`
- `insufficient_evidence`

Each candidate must include:

- target region
- confidence band
- evidence
- conflicts
- recommended checks

## Stage 6: Score Conservatively

Scoring inputs:

- number of affected devices
- topology contiguity
- source agreement
- source freshness
- console family specificity
- operator clue consistency
- manual stimulus result
- graph quality

Rules:

- broad simultaneous failures reduce confidence in isolated device candidates
- bus-wide error pressure reduces confidence in narrow localization
- topology mismatch conflicts reduce confidence in topology-derived candidates
- multiple observers can raise confidence when their attachment points are known

## Stage 7: Recommend The Next Check

The output must be actionable.

Good next checks:

- inspect connector between `lastVisible` and `firstMissing`
- reseat branch cable on `branch1`
- verify power and CAN ID on one local missing device
- move passive observer downstream and rerun
- run one non-motion or safe focused stimulus
- collect operator clue for first failed device

Bad next checks:

- vague "check CAN wiring"
- blaming one device when the evidence shows a broad separation
- asking for multiple unrelated checks at once

## Output Contract

Purpose: define a first-pass structured result shape.

```json
{
  "inferenceVersion": 1,
  "profile": "test_minimal_25_9",
  "generatedAtMs": 1783380000000,
  "window": {
    "startMs": 1783379990000,
    "endMs": 1783380000000,
    "sourceFreshness": {
      "passiveCan": "fresh",
      "robotConsole": "fresh",
      "robotRuntime": "fresh"
    }
  },
  "graph": {
    "source": "neighborPorts",
    "quality": "complete",
    "warnings": []
  },
  "deviceStates": [
    {
      "label": "SPARKMAX/NEO 25",
      "state": "missing",
      "sources": {
        "passiveCan": "missing",
        "robotConsole": "spark_status_timeout",
        "robotRuntime": "unreachable"
      }
    }
  ],
  "conditions": [
    {
      "type": "bus_wide_error_pressure",
      "severity": "medium",
      "evidence": ["BUS_OFF_EVENT", "CAN_ERROR_SPIKE"]
    }
  ],
  "candidates": [
    {
      "id": "candidate-1",
      "type": "possible_branch_isolation",
      "target": {
        "kind": "branch",
        "from": "CANNECT_A.branch1",
        "to": "branch1_subtree"
      },
      "confidence": "medium",
      "evidence": [
        {
          "source": "topology",
          "text": "All missing devices share branch1."
        },
        {
          "source": "passiveCan",
          "text": "Sibling branch devices remained visible."
        }
      ],
      "conflicts": [],
      "nextSteps": [
        "Inspect and reseat branch1 cable at CANNECT_A.",
        "Rerun a 10 second observation window."
      ]
    }
  ]
}
```

## Operator Surfaces

Purpose: define where the result should appear.

## CLI

The CLI should eventually provide:

- candidate summary
- candidate detail JSON
- observer/source freshness
- affected topology region
- next-step checks

Example operator text:

```text
Likely CAN fault: possible branch isolation on frontLeft branch
Confidence: medium
Why: 3 devices on the same branch are stale; sibling branch remains visible.
Check next: reseat the frontLeft branch cable at CANnect and rerun 10 second observe.
```

## UI

The UI should eventually provide:

- candidate banner in the Evidence or Live Topology view
- highlighted fault region on the topology graph
- expandable evidence and conflict details
- one-click "rerun observation window" workflow
- guided clue entry when confidence is low

## Reports

Reports should include:

- raw visibility snapshot
- raw console message family summary
- interpreted candidate list
- recommended next checks
- ambiguity notes

## Single-Observer First Pass

Purpose: define useful automation before multiple observers exist.

One passive observer can still be useful when combined with:

- topology graph
- expected device list
- robot-local console/runtime evidence
- controlled before/after windows
- operator clues

However, one passive observer usually cannot prove exact break location.

First-pass confidence caps:

- passive-only local missing device: low to medium
- passive plus device-specific console timeout: medium
- topology-contiguous missing run plus robot-local broad timeout cluster: medium
- exact segment localization without observer separation: usually not high

## Multi-Observer Later Pass

Multiple observers should raise confidence when:

- observers are attached at known topology points
- observation windows are aligned
- one observer sees a device/segment and another does not
- disagreement matches a specific topology boundary

This spec does not replace the multi-observer spec. It uses that work as the higher-confidence future path.

## Test Scenarios

Purpose: define concrete validation cases.

## Baseline

Scenario:

- all expected devices connected

Expected result:

- no fault candidate above low confidence
- transient `CAN_BUS_UTIL_HIGH` should not fail the diagnosis by itself

## PDP Disconnected

Observed prior evidence:

- `PDP_STATUS_READER_TIMEOUT`
- `HAL_CAN_RECEIVE_TIMEOUT`
- PDP topology/visibility loss

Expected result:

- candidate `single_device_unreachable` for PDP
- confidence medium-to-high if surrounding devices remain visible

## SparkMax Disconnected

Observed prior evidence:

- Spark ID 25 timeout families
- stale-message warnings
- bus-off/error-spike messages

Expected result:

- candidate `single_device_unreachable` for Spark if topology/passive evidence shows only Spark affected
- candidate `bus_wide_error_pressure` should also be reported when bus-off/error-spike evidence exists

## Falcon Disconnected

Observed prior evidence:

- FALCON missing passively
- stale-message spam
- bus-off event
- less device-specific console attribution than Spark/PDP

Expected result:

- candidate should preserve ambiguity between local FALCON loss and path-level/bus-health issue
- confidence should not be inflated from console evidence alone

## roboRIO Isolated From CAN Bus

Observed prior evidence:

- Spark timeout family
- PDP timeout family
- dense stale-message spam
- broad roboRIO-to-bus communication failure

Expected result:

- candidate `possible_controller_side_isolation`
- avoid reporting independent Spark and PDP root faults as the primary result

## Branch Isolation

Scenario:

- one branch unplugged from hub or CANnect

Expected result:

- candidate `possible_branch_isolation`
- affected devices share one branch in `neighborPorts`
- sibling branches remain visible

## Intermittent Connector

Scenario:

- loose connector toggles visibility during a wiggle/reseat test

Expected result:

- candidate `possible_intermittent_segment`
- evidence includes stale/recover cycles and timing around operator clue or capture marker

## Topology Mismatch

Scenario:

- expected profile says one CAN ID/location, passive traffic shows a different ID or branch

Expected result:

- candidate `possible_id_or_profile_mismatch`
- candidate `possible_topology_model_mismatch`
- do not force a physical break conclusion

## First Implementation Slice

Purpose: define the safest first code milestone when this moves from spec to implementation.

Recommended first slice:

- add a shared domain module for candidate generation
- input only synthetic topology and visibility evidence at first
- output candidate JSON only
- no UI changes in the first slice
- no CAN transmit behavior

Suggested module:

- `tools/can_nt/can_fault_inference.py`

Suggested tests:

- synthetic all-connected baseline
- synthetic single-device missing
- synthetic downstream missing run
- synthetic branch-isolated set
- synthetic broad controller-side isolation
- synthetic topology mismatch

The first slice should prove inference semantics before any UI or CLI presentation work.

## Documentation Requirements

Because this workflow is for students, every implemented surface should explain:

- what the system saw
- what it thinks that means
- why confidence is limited
- what to check next
- what to do after the check

Avoid expert-only phrases without explanation.

Example:

```text
The tool sees traffic from devices before SPARKMAX/NEO 25, but not from SPARKMAX/NEO 25 or devices after it. That often means the CAN wire is loose at the connector just before SPARKMAX/NEO 25. Inspect that connector first.
```

## Tradeoffs

- Conservative confidence may feel less decisive, but avoids dangerous false certainty.
- Topology-aware diagnosis is more useful than missing-device lists, but depends on accurate topology data.
- Structured operator clues improve inference, but too much required input slows pit work.
- Single-observer diagnosis can be useful, but high-confidence localization usually needs more evidence.

## Future Extensions

- observer placement editor
- capture bundle export with raw frames, console, topology, clues, and candidates
- before/after comparison after reseating a connector
- student-friendly guided wizard
- known LED pattern catalogs per vendor/device type
- automatic test suggestions based on ambiguity class
- multi-observer synchronized capture
- historical fault case library for training and regression

## Open Questions

SID_QUESTION: Should the first implementation expose this as a new CLI command, a report section, a UI Evidence panel, or candidate JSON only?

SID_QUESTION: What is the minimum topology data required before the UI should claim branch-level localization?

SID_QUESTION: Should operator clue entry be implemented before first-pass inference, or should the first implementation operate on passive/topology/console evidence only?

SID_QUESTION: How should observation windows be started and stopped in the UI so a student understands what evidence is being compared?
