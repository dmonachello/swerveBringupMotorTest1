SPEC_STATUS: PROPOSED

# Feature Spec: Authoritative Evidence Fusion

## Purpose

Purpose: define a reliable, explainable Evidence engine that combines all relevant diagnostic facts into the most accurate current picture the system can justify.

The Evidence engine is the project's authoritative fused interpretation. It consumes current and historical facts from passive CAN observation, robot runtime state, active probes, console diagnostics, manual and DSL tests, configuration, topology, power relationships, enrichment sources, and source-health metadata.

The engine must remain conservative. It must use all relevant information without treating every source as equally strong, double-counting correlated facts, or allowing stale observations to remain current truth.

This document reviews the algorithms in use as of 2026-08-24 and defines the target contract for hardening them.

## Status And Authority

This is a proposed behavior specification. It describes the intended Evidence engine and identifies differences from the current implementation.

Implementation of this spec will require an approved update to the Evidence-related rules in `Current UI And Runtime Rules - V2.md`. That rules document remains the current behavior baseline until an implementation slice explicitly updates it.

This spec supersedes earlier documents only for the final cross-source fusion algorithm. Source-specific collection contracts, UI layout requirements, topology inference rules, and safety constraints remain valid unless this document explicitly refines them.

## Goal

The Evidence engine must use all relevant available information to produce the most accurate, current, and reproducible assessment possible for every configured device and for the system as a whole.

The result must answer these questions separately:

- Does the expected device exist?
- Can the system currently communicate with it?
- Has its relevant function been proven, failed, degraded, or not yet proven?
- Does the observed device or mechanism match the configured identity and mapping?
- How confident is each conclusion?
- Which exact facts support and oppose each conclusion?
- Which facts are current, decaying, expired, unavailable, or historical only?
- Is the conclusion direct, corroborated, inferred, or unresolved?

## User Outcome

An operator looking at the Evidence lens should see the best current conclusion the system can justify from all sources.

The operator must be able to drill into any conclusion and determine:

- what was observed
- where it was observed
- when it was observed
- whether the observation is still current
- how much influence it had
- whether another source disagrees
- why the final state and color were selected
- what additional action would resolve remaining uncertainty

The Evidence lens must never appear more certain than the underlying facts support.

## Lens Boundaries

Purpose: preserve the distinct diagnostic value of the three Live Topology lenses.

### Runtime Lens

The Runtime lens remains the robot-local interpretation of current runtime, lifecycle, scope, instantiation, and robot-side telemetry.

It may use its own source-specific rules. It is not required to agree with CAN Visibility when the sources genuinely disagree.

### CAN Visibility Lens

The CAN Visibility lens remains the host passive-observer interpretation of CAN traffic.

It may use its own source-specific rules. It reports what the selected passive observer can currently see, not full device operability.

### Evidence Lens

The Evidence lens performs the complete cross-source analysis.

It must consume the underlying structured facts used by Runtime and CAN Visibility. Their rendered colors or summary verdicts may be included for traceability, but they must not be counted as independent corroboration when they are derived from facts already present in the fusion input.

### CAN Fault Finder

CAN Fault Finder must start from the same authoritative per-device Evidence snapshot.

It may add:

- topology-aware fault-region inference
- shared-cause candidates
- suspect boundaries
- ranking explanations
- recommended physical checks

It must not independently redefine the per-device existence, communication, operability, identity, conflict, or confidence conclusions.

## Scope

This spec covers:

- normalized evidence observations
- source availability and source health
- freshness and influence decay
- per-dimension fusion
- source trust and claim limits
- correlation and duplicate suppression
- conflict detection
- indirect system and topology inference
- confidence calculation
- overall state and node-color selection
- current versus historical evidence
- deterministic evidence capture and replay
- common Evidence snapshot ownership
- cross-surface agreement
- scheduling, starvation prevention, and observability
- unit, replay, cross-surface, and hardware verification

## Non-Goals

This spec does not:

- make Runtime and CAN Visibility use the same interpretation
- claim that passive CAN traffic proves mechanical operability
- claim that a quiet console proves health
- treat configuration as proof that hardware exists
- permit supported host diagnostics to transmit CAN frames
- automatically command motion to gather evidence
- guarantee exact electrical fault localization from passive evidence alone
- replace device-specific collection adapters with one generic collector
- hide disagreement by averaging all sources into one opaque number
- use AI output as primary device truth

## Reliability Principles

### Use All Relevant Facts

No relevant source should be ignored merely because it is inconvenient to combine.

Using all facts does not mean giving all facts equal weight. Source capability, freshness, specificity, directness, observation quality, and independence determine influence.

### Separate Questions

Existence, communication, operability, and identity are different questions.

A device can exist but fail communication. It can communicate but fail mechanically. It can operate but be mapped to the wrong mechanism. A single health score cannot represent those distinctions reliably.

### Current Truth Is Recomputed

The authoritative result must be derived from the current observation ledger and current evaluation time.

Cached host flags may retain history or pending workflow intent, but they must not remain authoritative when current observations disagree or expire.

### Staleness Reduces Influence

Evidence influence must decay as evidence ages.

Expired evidence remains visible as history but contributes no current-state weight.

### Strong Claims Need Strong Evidence

Red is reserved for current, high-confidence absence or failure.

Indirect or system-level evidence may produce a red device conclusion only when corroborated by another independent relevant source. Otherwise it produces a probable or uncertain state.

### Preserve Conflict

Meaningful disagreement must be shown as conflict. It must not be silently resolved by source ordering or hidden inside a midpoint score.

### Avoid Double Counting

Multiple messages, surfaces, or derived summaries that originate from the same underlying event are one correlated evidence group, not multiple independent confirmations.

### Explain Every Result

Every conclusion must be reproducible from a structured list of supporting, opposing, ignored, decayed, and expired observations.

### Prefer Unknown To False Certainty

Insufficient evidence produces `UNKNOWN` or `UNPROVEN`, not a guessed healthy or failed result.

## State Model

Purpose: define the authoritative per-device result without conflating distinct diagnostic dimensions.

### Existence

Allowed values:

- `PRESENT`
- `ABSENT`
- `UNKNOWN`

Existence answers whether the expected physical CAN or local device is currently present in the relevant system.

Conflict is not an existence value. It is separate metadata indicating that credible observations support incompatible values.

### Communication

Allowed values:

- `HEALTHY`
- `DEGRADED`
- `FAILED`
- `UNKNOWN`

Communication answers whether the applicable control and telemetry path is currently functioning.

For a CAN device, this includes the CAN path and vendor API communication. For a local DIO or USB device, it means the applicable local runtime path.

### Operability

Allowed values:

- `WORKING`
- `DEGRADED`
- `FAILED`
- `UNPROVEN`
- `UNKNOWN`

`UNPROVEN` means the device may be present and communicating but has not received a sufficiently recent functional stimulus-response test.

`UNPROVEN` is not itself a fault. The overall node may remain green when current existence and communication are strongly supported and there is no negative functional evidence. The inspector must still say that full function has not been proven.

### Identity

Allowed values:

- `MATCHING`
- `MISMATCHED`
- `UNKNOWN`

Identity includes vendor, FRC CAN device type, CAN ID, model, configured label, and mechanism or branch mapping where those can be tested.

### Confidence

Each dimension has:

- a numeric confidence from `0.0` through `1.0`
- a qualitative band: `HIGH`, `MEDIUM`, or `LOW`
- winning support
- strongest opposing support
- support margin
- independent source count
- direct-source count
- inference-only flag
- conflict flag

The numeric value is a calibrated decision confidence, not a probability that the device is healthy.

### Overall State

Allowed values:

- `HEALTHY`
- `CAUTION`
- `PROBABLE_FAULT`
- `IDENTITY_FAULT`
- `FAILED`
- `UNKNOWN`

The overall state is derived after the four dimensions are evaluated. It is not independently scored.

### Node Colors

Required mapping:

- green: strong current evidence supports expected baseline health
- yellow: meaningful conflict, reduced confidence, or a caution requiring review
- orange: confirmed identity/mapping fault or probable/inferred degradation that is not yet a proven absence or functional failure
- red: current high-confidence absence or failure
- gray: insufficient current evidence

Red must not result from one broad system warning, one indirect clue, source silence while the source is unavailable, or stale cached evidence.

## System-Level State

Purpose: represent bus and infrastructure evidence without incorrectly attaching every system event to every device.

The Evidence snapshot also contains system dimensions:

- robot controller reachability
- passive observer availability
- robot REST/runtime availability
- CAN bus communication health
- CAN utilization pressure
- receive/transmit error pressure
- bus-off or TX-full state
- likely CAN power-domain state
- console parser health
- profile and runtime-context agreement
- observation-window coherence

System findings can influence device confidence and shared-cause inference. They do not automatically become device-specific faults.

## Current Implementation Review

Purpose: document the algorithms and limitations that exist before this spec is implemented.

### Current Data Flow

The current host path is approximately:

1. `VisibilityProvider` tracks passive frame metrics.
2. `passive_discovery_poc` classifies recent frames into device-emitted families and derives passive scores.
3. Runtime payloads provide lifecycle state, local presence checks, telemetry, and cached full-probe attachments.
4. Console events are normalized into device and system snapshots.
5. Manual and enrichment snapshots are indexed by device label.
6. `build_interpreted_device_state()` applies sequential source-specific overrides.
7. `_collect_device_source_scores()` creates display and downstream source-score rows after the conclusion has already been chosen.
8. Live Topology receives a reduced Evidence state map for coloring.
9. CAN Fault Finder receives frozen interpreted rows and performs additional affected-device and topology inference.

### Current Source Inventory

| Source | Current useful facts | Current primary limitation |
| --- | --- | --- |
| Profile/config | Expected label, vendor, model, CAN identity, bus, interface | Defines expectation, not physical truth |
| Passive CAN | Device-emitted families, last seen, packet count, rate, observer visibility | Historical frames and current frames are not represented uniformly |
| Runtime presence | Presence attachment, score, source, update time, lifecycle fields | Some fallbacks treat untimed presence as fresh |
| Runtime telemetry | Bus voltage, current, position, velocity, faults, local inputs | Instantiation and plausible defaults can be mistaken for live communication |
| Robot CAN status | Utilization, receive/transmit error counters, bus-off, controller power state | Primarily system-level; absolute counters need time deltas |
| Full Probe | One-shot vendor result, score, bucket, warnings, errors | Cached result uses hard age buckets and may not cover all devices |
| Console | Structured targeted and system faults, severity, repeats, age, parser confidence | Parser coverage and attribution vary; silence is not positive evidence |
| Manual test | Operator outcome and recent motion observation | Current and historical meaning are mixed through fixed windows |
| Enrichment | CTRE HTTP, topology, parsed output-log evidence | One-shot data can outlive its value as current truth |
| Topology | Device adjacency, branches, infrastructure placement | Inference quality depends on topology correctness and power-domain detail |
| Fault Finder | Affected-device and region inference | Reinterprets some Evidence fields and parses presentation text |

### Current Freshness Rules

The current implementation uses several independent hard thresholds:

| Fact | Current rule |
| --- | --- |
| Runtime presence | Fresh for approximately 2 seconds |
| Infrastructure runtime telemetry | Fresh for approximately 3 seconds |
| Passive support used by Evidence | Fresh for approximately 3 seconds and requires non-zero rate |
| Visibility source | Visible within the source timeout, default approximately 1 second |
| Visibility observed-row retention | Retained approximately 10 seconds |
| Passive rate | Exponential rate decay with approximately 3-second time constant |
| Console | Fresh through 5 seconds, aging through 15 seconds, then stale |
| Full Probe | Fresh through 15 seconds, aging through 60 seconds, then stale |
| Manual operability | Current for 120 seconds |
| Manual identity | Current for 900 seconds |

These rules are useful first-pass safeguards, but they do not form one coherent decay model.

### Current Passive Algorithm

`VisibilityProvider` tracks per-device, per-source:

- `lastSeenMs`
- cumulative `msgCount`
- decaying `framesPerSec`
- raw arbitration ID metrics
- observer availability

Visibility is currently a timeout decision based mainly on `lastSeenMs` and source timeout.

The passive discovery classifier groups the bounded recent-frame buffer by manufacturer, device type, device ID, API class, and API index. It classifies families as primary status, secondary status, heartbeat/housekeeping, controller command, shared bus control, or unknown.

Current passive presence scores are fixed categorical values. Examples include:

- enrichment plus primary and secondary families: `100`
- primary and secondary families: `92`
- primary only: `78`
- secondary only: `55`
- otherwise classified families: `25`

Important limitations:

- the recent-frame buffer is bounded by frame count, not solely by time
- old frames can remain in the passive classifier input when traffic stops
- high-rate devices can dominate a count-bounded window
- passive family score does not itself decay continuously
- current Evidence must separately consult visibility age and rate to determine whether the passive score is still live
- a cumulative packet count is history and must not be interpreted as current presence

### Current Runtime Algorithm

Runtime facts are normalized from robot snapshots and attachments.

Fresh `presenceCheck` evidence can set existence to present or absent. Infrastructure classes receive special handling. Passive evidence can override runtime absence in some cases, and runtime infrastructure telemetry can override scope-related absence.

Important limitations:

- runtime lifecycle scope, instantiation, and presence are closely adjacent and can be mistaken for one another
- a runtime device with `presenceConfidence` but no timing metadata may be treated as fresh
- a local snapshot can reflect a successfully instantiated wrapper rather than independently prove current CAN communication
- current classification uses broad device classes: infrastructure, unprofiled, and motion
- sensors and other non-motor classes do not yet have equally precise fusion policies

### Current Probe Algorithm

The heavy Full Probe is a one-shot robot-side vendor API operation. It produces a per-device bucket, score, status, warnings, errors, and detailed evidence.

Current fusion behavior includes:

- fresh `present` may establish existence and operability
- fresh `absent` may establish absence or conflict with runtime presence
- aging results lower a qualitative confidence band
- stale results are mostly historical
- fresh console failures can invalidate aging or stale positive probe results

Important limitations:

- score meanings vary by device adapter
- no continuous decay is applied inside the fusion result
- coverage and service fairness are not part of the final confidence
- one-shot cache state can be visually confused with current evidence

### Current Console Algorithm

Console rules normalize messages into device-targeted, system-level, or unclassified events.

The current structured model includes:

- event type and fault family
- device label and CAN ID when resolved
- scope
- severity
- repeat count and rate
- first and last seen
- freshness bucket
- parser confidence
- raw message example

Fresh or aging targeted fault families can strongly reduce operability and sometimes existence. Repeated targeted messages can demote a plain present result. System-level conflicts are applied only when relevant to the device or infrastructure path.

Important limitations:

- the console monitor's active-event timeout and the fusion layer's freshness buckets are separate policies
- parser rules can fail when vendor wording or text encoding changes
- multiple messages from one underlying timeout can be counted as multiple apparent clues
- broad system faults need topology and source-health context before they affect a specific device

### Current Manual And Motion Algorithm

Manual evidence can record correct response, no response, wrong device, wrong branch, intermittent response, degraded response, or operator uncertainty.

Runtime motion inference also considers commanded duty, applied duty or voltage, velocity, position delta, current, and bus voltage.

Important limitations:

- a no-motion result can indicate mechanism binding, output-path failure, bad mapping, disabled output, or communication loss; it does not prove absence by itself
- current manual windows are hard cutoffs
- a historical successful test can remain influential longer than it should for current existence or communication
- DSL require results are not yet a first-class normalized fusion source

### Current Fusion Algorithm

The current `build_interpreted_device_state()` implementation is a sequential rule cascade.

Sources can set or overwrite:

- existence
- operability
- identity
- qualitative confidence
- evidence state
- conflict flag

Later rules can change decisions made by earlier rules. The final result therefore depends partly on evaluation order.

The current `sourceScores` map is created after the final categorical result. Those scores provide useful diagnostics and are consumed by portions of Fault Finder, but they are not the mathematical inputs that produced the final row.

Current source-score examples include:

- passive current visibility: `70` or `85`
- fresh runtime presence: `90`
- fresh Full Probe presence: `95`
- console error: `20`
- quiet console: `50`
- recent manual evidence: `60`
- enrichment present: `65`
- no evidence for several sources: `25`

These values mix presence, quality, and absence of information in one direction. They cannot be safely combined as probabilities or as dimension-specific support.

### Current Final Presence Mapping

The current numeric presence score is derived from the already-selected final row:

- present with high confidence: `100`
- present with medium confidence: `75`
- present with low confidence: `55`
- conflict: `40`
- unknown: `25`
- absent: `0`

This score summarizes the decision. It does not independently validate or calibrate that decision.

### Current Fault Finder Algorithm

Fault Finder freezes interpreted rows and then applies additional rules to decide whether rows are affected, degraded, missing, or infrastructure-visible.

It currently examines:

- final Evidence fields
- source-score entries
- manual summary text
- passive summary tokens such as last seen, rate, and existence packets
- system console state
- topology connectivity

Important limitations:

- parsing rendered passive strings is fragile
- downstream affected-device logic can diverge from the Evidence engine
- current versus historical passive data is reconstructed from display tokens
- fault-location inference and per-device truth are not fully separated

### Current Strengths To Preserve

The current system already has important foundations:

- source-specific collection remains separated
- passive CAN remains read-only
- current versus stale checks exist for several sources
- direct device-targeted console faults can outrank stale positives
- conflicts are visible rather than always hidden
- the robot controller is treated differently from CAN-powered downstream devices
- Runtime, CAN Visibility, and Evidence have distinct lens roles
- Evidence and Fault Finder already share a frozen-row path for a run
- manual motion testing captures valuable causal evidence
- topology inference is separate from raw collection
- unit tests cover several recent failure modes

## Main Reliability Gaps

Purpose: identify what must change before the Evidence lens can be treated as dependable.

### Order-Sensitive Overrides

Sequential mutation makes precedence difficult to reason about and test. Adding one rule can unintentionally undo another source's conclusion.

### Scores Do Not Drive Conclusions

Displayed source scores are post-hoc summaries. The final result cannot be reconstructed from them.

### Mixed Score Meaning

One numeric direction currently mixes presence support, communication quality, fault severity, and missing information.

### Hard Freshness Buckets

Several sources jump abruptly from influential to stale. Influence does not consistently decrease as observations age.

### Historical Data Leakage

Count-bounded passive history, one-shot probe caches, manual results, and enrichment can remain visible after they stop representing current state.

### Incomplete Source-Health Gating

Silence is meaningful only when the observer was available, healthy, correctly attached, and observed for long enough. That context is not uniformly enforced.

### Correlated Evidence Double Counting

One electrical failure can produce passive silence, repeated vendor errors, HAL errors, probe failures, and runtime failures. These are useful corroboration, but repeated derivatives of one event must not create unlimited confidence.

### Missing Communication Dimension

Current output has existence, operability, and identity, but communication failures are often forced into existence or operability.

### Device-Class Coverage

Motor, power, sensor, controller, local input, and infrastructure devices have different observable behavior. Current broad classes do not express all of those differences.

### Duplicate Downstream Interpretation

Fault Finder applies additional per-device affected logic and parses presentation strings. This violates the intended single shared-state rule.

### Limited Replayability

There is no complete deterministic capture containing all source facts, source health, timestamps, profile revision, topology revision, and expected decisions.

### Limited Calibration

Confidence values are not yet calibrated against a labeled hardware scenario corpus.

## Target Architecture

Purpose: establish one shared fusion path while retaining independent source collectors and raw lenses.

The target layers are:

1. Source collectors gather raw facts.
2. Source adapters normalize facts into immutable observations.
3. An observation ledger stores current-window and historical observations.
4. The Evidence engine evaluates all devices from one coherent snapshot epoch.
5. The Evidence snapshot publishes per-device and system conclusions plus provenance.
6. Evidence UI and Live Topology Evidence consume the snapshot directly.
7. Fault Finder consumes the same snapshot and adds only topology/shared-cause inference.
8. Capture and replay tools serialize the exact fusion inputs and outputs.

The UI must not own fusion rules.

## Observation Contract

Purpose: normalize all sources without erasing source-specific meaning.

Each observation is immutable and assertion-specific.

Recommended shape:

```json
{
  "schemaVersion": 1,
  "observationId": "host-passive:COM3:5:2:25:status0:81234",
  "sourceType": "passiveCan",
  "sourceInstance": "canable:COM3",
  "sourceSessionId": "capture-2026-08-24T14:51:00",
  "profileRevision": "sha256:...",
  "topologyRevision": "sha256:...",
  "scope": "device",
  "deviceKey": "5:2:25",
  "label": "SPARKMAX/NEO 25",
  "dimension": "communication",
  "assertion": "healthy",
  "polarity": "support",
  "claimStrength": 0.85,
  "specificity": 1.0,
  "directness": 0.9,
  "quality": 1.0,
  "independenceGroup": "passive:COM3:5:2:25",
  "correlationId": "frame-family:5:2:25:6:2",
  "observedAtMonotonicMs": 81234,
  "receivedAtMonotonicMs": 81235,
  "windowStartMonotonicMs": 80234,
  "windowEndMonotonicMs": 81234,
  "expectedCadenceMs": 20,
  "freshnessProfile": "periodicCanStatus",
  "sourceAvailable": true,
  "sourceHealthy": true,
  "value": {
    "rateHz": 49.8,
    "existencePackets": 50,
    "lastSeenAgeMs": 1
  },
  "reasonCode": "PASSIVE_DEVICE_STATUS_CURRENT",
  "rawReferences": ["arb:0x..."],
  "limitations": []
}
```

### Required Observation Fields

- schema version
- stable observation ID
- source type and source instance
- source session or generation ID
- profile and topology revisions
- device, system, region, or unknown scope
- canonical device key when resolved
- target dimension
- assertion and polarity
- base claim strength
- specificity
- directness
- observation quality
- independence group and correlation ID
- observation and receipt timing
- observation window
- freshness profile
- source availability and health
- structured observed values
- symbolic reason code
- raw-reference links
- limitations

### Observation Rules

- One observation should make one primary assertion about one dimension.
- A raw event may produce multiple linked observations when it legitimately informs multiple dimensions.
- Linked observations retain one correlation ID so they cannot be mistaken for independent evidence.
- Rendered text is never parsed back into a fact.
- Unknown or unsupported data is represented explicitly.
- Missing timestamps prevent an observation from making a strong current claim.
- Profile or topology revision mismatch prevents an observation from applying automatically to the new context.

## Evidence Ingestion Contract

Purpose: allow any producer, including the fusion clock, to submit a typed block that causes a deterministic state review.

The engine exposes one logical ingestion boundary:

```text
submitEvidenceBlock(block) -> acceptance result and affected evaluation ID
```

An `EvidenceBlock` is the external event envelope. A normalized observation is one possible result of processing that envelope. Keeping the two concepts separate prevents scheduling, source-lifecycle, and context events from being mistaken for device evidence.

Recommended envelope:

```json
{
  "schemaVersion": 1,
  "blockId": "host-clock:session-42:tick:81250",
  "sourceType": "systemClock",
  "sourceInstance": "fusionHostMonotonicClock",
  "sourceSessionId": "session-42",
  "majorType": "clockTick",
  "scope": "system",
  "target": null,
  "observedAtMonotonicMs": 81250,
  "receivedAtMonotonicMs": 81250,
  "correlationId": null,
  "payload": {
    "reasonCode": "SCHEDULED_FRESHNESS_REVIEW"
  }
}
```

### Block Types

The initial major types are:

- `observation`: source-specific facts that an adapter may normalize into one or more dimension assertions
- `sourceState`: source availability, health, delay, saturation, connection, and session state
- `contextRevision`: profile, topology, runtime-generation, or policy changes
- `clockTick`: trusted monotonic-time advancement and freshness reevaluation request
- `retraction`: explicit withdrawal of a previously submitted fact or source generation
- `recovery`: explicit end of a fault or unavailable-source condition when the source can prove recovery

Each `sourceType` and `majorType` pair has a versioned payload validator and normalizer. Unsupported pairs are retained for diagnostics when safe but do not affect fused state.

### Clock Tick Semantics

The fusion process's monotonic clock submits `clockTick` blocks even when no device source publishes new facts. A valid tick causes the engine to reevaluate observations against the new evaluation time so that current evidence can become decaying, historical, or expired without requiring another hardware event.

A clock tick:

- carries no assertion, polarity, claim strength, reliability, or device-health value
- never creates a normalized device observation
- never counts as independent corroboration
- never directly changes existence, communication, operability, identity, or confidence
- may change a result only because prior observations have lost freshness or expired
- uses monotonic time, not wall-clock time, for aging
- cannot move the engine's evaluation time backward
- is rejected or ignored when its source session is invalid or its timestamp is out of order

The scheduler may reevaluate every current-profile device on each accepted tick, or it may use a deadline queue to reevaluate only devices whose decay, expiry, confidence, or display boundary can change. Both implementations must produce the same result for the same ledger and evaluation time.

The default tick cadence is policy-driven and independent of UI repaint rate. UI polling must not be the mechanism that ages evidence.

### Processing Flow

For every accepted block, the engine must:

1. Validate the common envelope and the source-specific payload.
2. Verify source session, target scope, revisions, and monotonic ordering.
3. Deduplicate by stable block ID and correlate related facts.
4. Normalize evidence-bearing payloads into immutable observations, or apply the non-evidence control event.
5. Update the bounded ledger and mark affected devices, regions, or the system dirty.
6. Freeze a coherent evaluation context and reevaluate affected state.
7. Publish a new immutable Evidence snapshot only when the evaluation result or trace epoch changes.

Producers do not assign final trust, freshness, confidence, or color. They report source facts and timing; fusion policy owns interpretation.

### Ordering And Concurrency

- Receipt order is recorded but does not overwrite observation time.
- A late block may be retained as history but cannot replace a newer current fact from the same source generation.
- Duplicate blocks are idempotent.
- Source restart creates a new source session and prevents old-session facts from becoming current again.
- Context revision events invalidate incompatible mappings before the next snapshot is published.
- Retraction removes current influence but preserves an auditable historical trace.
- Recovery is new evidence or source state, not deletion of the prior fault history.
- Ingestion and evaluation may be asynchronous, but each published snapshot is derived from one frozen ledger revision and one evaluation time.

## Source Contracts

Purpose: define how every relevant source may influence each dimension.

### Configuration And Profile

Configuration supplies:

- expected label
- vendor
- model
- FRC CAN manufacturer
- FRC CAN device type
- CAN ID
- bus
- interface
- enabled state
- profile membership
- expected capabilities

Configuration establishes expectations and identity hypotheses. It contributes no positive existence or operability evidence by itself.

An invalid or unmatched model is a configuration fault and an identity-risk observation. Motor-spec lookup failure, including failure to match the canonical `motor_specs.json` model data, must be explicit and visible.

### Topology And Power Domains

Topology supplies:

- CAN adjacency
- preferred `neighborPorts` graph
- compatibility `neighborLinks` graph when necessary
- bus segments and analyzer attachment points
- power-source and power-domain relationships
- controller-side and branch-side boundaries
- bus terminators
- device groups and mechanisms

Topology is inference context. It cannot prove a device exists.

Indirect topology or power evidence may mark a device failed or absent only when corroborated by independent relevant evidence. Without corroboration it may produce `PROBABLE_FAULT`, lower confidence, or a region-level finding.

The roboRIO or future robot controller may be powered while downstream CAN devices are unpowered. Controller-local health must not be treated as proof that the CAN-device power domain is energized.

### Passive CAN Observation

Passive CAN is strongest for current existence and CAN communication when qualifying device-emitted traffic is observed.

Required rules:

- Only frames classified as device-emitted may update device presence `Last Seen`.
- Controller requests or commands sent toward a device must not prove that the device exists.
- `Packets` is cumulative history and does not prove current presence.
- `Existence Packets` is a sliding-window count of qualifying device-emitted frames.
- `Rate` is a current-window or decayed current rate, not a lifetime average.
- `Last Seen`, `Existence Packets`, and `Rate` must be derived from the same coherent evaluation window.
- Silence is negative evidence only when the observer is available and healthy and the device class is expected to emit within the completed observation window.
- Unknown frame classification can support weak bus activity but not strong identity or device presence.
- Multi-observer disagreement must retain observer provenance.

For a known periodic device such as a motor controller or CANcoder, all of the following form strong negative communication evidence:

- `Existence Packets == 0`
- `Rate == 0`
- aging `Last Seen`
- healthy passive observer
- completed observation window long enough for the expected cadence

This is not automatically enough to prove mechanical failure. It is strong absence or CAN-communication evidence.

### Runtime And Lifecycle

Runtime supplies:

- runtime active state
- lifecycle state
- wrapper instantiation
- scope active state
- current local presence check
- vendor status and telemetry
- faults and warnings
- input and sensor values
- controller-local state
- per-device update and service timing

Required rules:

- `instantiated` proves that a software wrapper exists, not that hardware exists.
- `scopeActive` proves that a runtime scope owns the device, not that communication is healthy.
- runtime presence is current only when its update generation and age are valid.
- plausible default telemetry does not prove communication.
- device-specific vendor status freshness is required for strong communication evidence.
- robot-local controller telemetry is direct evidence for the robot controller, not passive evidence for downstream CAN devices.
- runtime deactivation invalidates current runtime observations but retains them as history.
- every device must expose last-service time, service count, skipped-cycle count, and maximum service lag when periodic servicing is expected.

### CAN Bus And Robot-Controller Health

Robot-controller and vendor bus APIs may supply:

- CAN utilization
- receive error count
- transmit error count
- bus-off count or state
- TX-full count or state
- brownout state
- controller input voltage
- controller local rail state
- loop-overrun and scheduler pressure

Required rules:

- these facts are system-scoped unless a vendor API explicitly targets a device
- error-counter deltas and rates are more meaningful than lifetime totals
- counter reset, robot restart, and runtime generation must be tracked
- high utilization lowers timing confidence but does not prove device failure
- bus-off or a rapidly increasing error rate strongly supports system communication failure
- healthy controller voltage does not prove downstream CAN-device power
- controller brownout or low input voltage may explain broad failures but remains indirect device evidence
- loop overruns reduce confidence in timing and service coverage, not physical existence by themselves

### Active Full Probe

Full Probe supplies direct, read-only vendor API evidence for supported devices.

Required rules:

- probe output remains source-specific and structured
- vendor communication status gates telemetry-derived positives
- unsupported or weak device APIs produce `UNKNOWN`, not forced absence
- probe coverage is recorded per target
- an unprobed device is not a failed device
- result age decays by dimension
- a stale successful probe is historical proof only
- repeated probe attempts are correlated unless separated by a meaningful new session or state change
- probing remains non-motion and respects runtime-owned handle lifetime

### Console Diagnostics

Console diagnostics supply high-value negative evidence when vendor, HAL, or application messages are normalized correctly.

Required rules:

- exact device-targeted faults receive more influence than broad system faults
- parser confidence affects observation quality
- device mapping confidence affects specificity
- repeat count strengthens a finding only to a saturation limit
- identical repeated warnings do not become unlimited independent evidence
- `Active Events` means currently active deduplicated event entries inside the configured inactivity window, not a lifetime event total
- system-level faults remain system-scoped unless additional evidence maps them to a device or region
- console silence is neutral
- malformed or encoding-damaged text is retained as low-quality raw evidence, not silently discarded
- explicit recovery messages may add positive recovery evidence but do not erase unrelated failures

### Manual Stimulus-Response

Manual tests provide causal evidence when command, target, observation, and timing windows are recorded.

Required rules:

- correct response strongly supports operability and identity during the test window
- wrong-device or wrong-branch response strongly supports identity mismatch
- no response strongly opposes operability but does not prove absence by itself
- commanded current with no motion may indicate stall or binding
- command with little current may indicate electrical or output-path failure
- operator-entered outcomes retain operator identity and confidence
- current existence and communication influence decays rapidly after the test
- operability and identity proof remains available longer as historical evidence

### DSL Test Results

DSL runs must become a first-class structured evidence source rather than only console text or a final pass/fail label.

Required facts include:

- test name and run ID
- target devices
- runtime/profile revision
- start and finish times
- commanded actions
- every `until` result
- every `require` expression
- sampled signal value
- comparison operator and expected value or range
- pass/fail outcome
- maximum, minimum, delta, or stability evidence used
- abort, unsafe-exit, timeout, or operator-stop reason

A passing requirement contributes only to the dimension it proves. For example, motor position change can support operability, while robot-controller input voltage supports controller power health.

A test-level pass must not be copied as equal positive evidence to every declared device.

### Input And Sensor State

Current-profile input and sensor state can provide:

- current value
- validity and vendor status
- transition count
- changed-since-activation state
- last-change age
- position or orientation change
- sample age
- out-of-range or implausible value

A current valid value supports communication. A meaningful transition or controlled change supports operability. A static value alone may be insufficient to prove function.

### Enrichment

Enrichment sources may include CTRE HTTP inventory, device metadata, topology inspection, and explicitly captured console-log analysis.

Required rules:

- every enrichment run has a session ID and capture time
- enrichment proves only what that source directly observed
- one-shot inventory data decays for current existence and communication
- stable manufacturing metadata may remain useful for identity longer
- enrichment derived from console text shares correlation with the original console event

### Operator Clues

Future operator clues may include LED state, known unpowered branch, reseated connector, intermittent behavior, or physical mechanism response.

Operator clues are weighted observations, not unquestioned truth. They must include author, time, target scope, confidence, and structured clue type.

### Source Availability And Health

Every source must publish whether it is:

- available
- healthy
- delayed
- saturated
- disconnected
- unsupported
- not run

Source silence is negative evidence only when the source was available, healthy, and observed for a sufficient window.

Examples:

- CANable disconnected means passive absence is `UNKNOWN`, not `ABSENT`.
- REST disconnected means runtime observations decay and expire.
- runtime inactive means active probe unavailable, not failed.
- parser disabled means no console evidence, not a quiet healthy console.
- high CAN utilization reduces timing confidence but does not automatically mark all devices failed.

## Fusion Algorithm

Purpose: define a deterministic, dimension-specific, correlation-aware evaluation.

### Step 1: Freeze Evaluation Context

Each evaluation uses one immutable context containing:

- evaluation ID
- evaluation monotonic time
- profile revision
- topology revision
- runtime activation generation
- source session IDs
- source availability and health
- observation-window boundaries

Facts from incompatible profile, topology, runtime, or source generations are historical only unless explicitly migrated.

### Step 2: Select Eligible Observations

For each device and dimension, classify observations as:

- current and eligible
- decaying and eligible
- historical only
- invalid for this context
- duplicate or correlated
- unsupported for this device class

No rendering string participates in this step.

### Step 3: Calculate Freshness Influence

Each source and dimension has:

- `fullStrengthUntil`
- `hardExpiryAt`
- optional cadence-derived timing

Recommended decay function:

```text
age <= fullStrengthUntil:
    freshness = 1.0

age >= hardExpiryAt:
    freshness = 0.0

otherwise:
    x = (age - fullStrengthUntil) / (hardExpiryAt - fullStrengthUntil)
    freshness = 1 - (3*x*x - 2*x*x*x)
```

This smoothstep decay has no abrupt slope change at the start or end of the decay window.

Cadence-aware sources should derive windows from expected update cadence:

```text
fullStrengthUntil = max(minimumFreshWindow, expectedCadence * freshPeriods)
hardExpiryAt = max(minimumExpiryWindow, expectedCadence * expiryPeriods)
```

All production values must be symbolic constants or data-driven policy values.

### Initial Freshness Profiles

These are starting policies to validate against replay and hardware data, not universal physical truths.

| Source and dimension | Full strength | Hard expiry | Historical use |
| --- | --- | --- | --- |
| Periodic passive CAN existence/communication | Cadence-aware | Cadence-aware, normally a few seconds | Traffic history only |
| Runtime presence/communication | Approximately 0.5 seconds | Approximately 2 seconds | Prior runtime state |
| Robot-controller local telemetry | Approximately 0.5 seconds | Approximately 3 seconds | Prior controller state |
| Targeted console failure | Approximately 5 seconds | Approximately 15 seconds | Fault history |
| System console failure | Approximately 5 seconds | Approximately 15 seconds | Bus-event history |
| Full Probe existence/communication | Approximately 15 seconds | Approximately 60 seconds | Prior probe result |
| Manual/DSL current existence/communication | Approximately 2 seconds after run | Approximately 15 seconds after run | Test history |
| Manual/DSL operability | Approximately 30 seconds | Approximately 120 seconds | Historical proof |
| Manual/DSL identity | Approximately 120 seconds | Approximately 900 seconds | Historical mapping proof |
| Enrichment current existence/communication | Approximately 15 seconds | Approximately 120 seconds | Inventory history |
| Configuration/topology | Valid for matching revision | Invalidated by revision change | Expected model only |

Device-class policy may shorten or extend these values based on known message cadence and API behavior.

### Step 4: Calculate Observation Influence

For observation `i`:

```text
influence_i =
    baseReliability_i
    * freshness_i
    * specificity_i
    * directness_i
    * quality_i
    * sourceHealth_i
```

Each factor is bounded from `0.0` through `1.0`.

Factor meanings:

- `baseReliability`: validated capability of this source for this assertion, dimension, and device class
- `freshness`: age-based influence from the source policy
- `specificity`: exact device match versus region or system scope
- `directness`: direct observation versus inference
- `quality`: parser confidence, status quality, sample validity, or operator confidence
- `sourceHealth`: observer and transport health during the observation window

### Initial Trust Direction

Recommended qualitative ordering:

| Evidence | Strongest dimensions | Initial trust direction |
| --- | --- | --- |
| Correct causal manual/DSL response | Operability, identity | Very high during test window |
| Fresh successful device-specific active probe | Communication, existence | High for validated device classes |
| Fresh device-emitted passive traffic | Existence, CAN communication | High when identity and cadence are known |
| Fresh vendor runtime status | Communication, existence | High when status freshness is proven |
| Repeated exact targeted vendor/HAL fault | Communication, operability | High negative evidence |
| Valid sensor transition | Operability | High for the exercised behavior |
| Enrichment inventory | Identity, existence at capture | Moderate to high at capture |
| Broad system console fault | System communication | High system evidence, weak device-specific evidence |
| Topology or power inference | Region or shared cause | Moderate inference, not standalone device proof |
| Configuration | Expected identity | No physical presence influence |
| Console silence | None | Neutral |
| Wrapper instantiation | Software lifecycle | No physical presence influence by itself |

### Step 5: Collapse Correlated Observations

Observations in the same correlation group are combined with saturation, not simple addition.

Recommended same-group combination:

```text
groupSupport = 1 - product(1 - influence_i)
groupSupport = min(groupSupport, groupCap)
```

Examples of correlated evidence:

- repeated copies of one console warning
- a raw console message and enrichment parsed from the same message
- Runtime lens verdict and the runtime attachment that produced it
- CAN Visibility verdict and its underlying last-seen/rate facts
- multiple telemetry fields from one failed vendor refresh
- repeated probe rows from one probe session

Independent observations from different physical or software paths may corroborate one another.

### Step 6: Aggregate Per Hypothesis

For each dimension, aggregate support for each allowed value from independent groups:

```text
support(hypothesis) = 1 - product(1 - groupSupport_j)
```

The engine records:

- winning hypothesis
- winning support
- strongest competing support
- support margin
- independent group count
- direct group count
- inference-only status

### Step 7: Apply Semantic Gates

Weighted evidence cannot override source semantics.

Required semantic gates include:

- configuration alone cannot support presence
- console silence cannot support health
- controller-emitted CAN traffic cannot support target-device presence
- instantiation alone cannot support hardware presence
- no-motion alone cannot prove absence
- a source marked unavailable cannot infer absence from silence
- stale evidence cannot support a current red state
- indirect evidence alone cannot support red
- unsupported device-class probe absence cannot become high-confidence absence
- identity mismatch cannot be averaged into matching

### Step 8: Detect Conflict

Conflict exists when credible current support remains for incompatible hypotheses.

Recommended initial conflict criteria:

- winning and opposing support are both at least moderate
- support margin is below a configured conflict margin
- the disagreement is not explained by incompatible observation windows or an already-expired source

Conflict lowers confidence and produces yellow unless a separate proven failure dimension requires red.

The snapshot must identify the exact opposing observations.

### Step 9: Apply Indirect Inference

System, topology, and power evidence can generate inferred device observations.

Required rules:

- inferred observations retain their upstream provenance
- inference strength is lower than direct observation strength
- one upstream event cannot be counted once as system evidence and again as independent device evidence
- a device may become red from indirect evidence only with independent corroboration
- without corroboration, inferred failure produces orange or yellow

Example:

```text
Known CAN branch power removed
+ passive observer healthy
+ zero qualifying device-emitted traffic for every device in the branch
+ repeated targeted runtime or console failures
= high-confidence branch communication failure
```

The independently powered robot controller may remain healthy in the same snapshot.

### Step 10: Calculate Confidence

Confidence should reflect evidence quality and decision separation, not only winning support.

Recommended calculation inputs:

- winning support
- support margin
- number of independent groups
- number of direct groups
- source coverage for the device class
- source-health penalty
- inference penalty
- conflict penalty
- observation-window coherence

Recommended conceptual form:

```text
confidence =
    winningSupport
    * marginFactor
    * coverageFactor
    * sourceHealthFactor
    * inferenceFactor
    * conflictFactor
```

Initial qualitative bands:

- `HIGH`: calibrated confidence at or above `0.80`
- `MEDIUM`: calibrated confidence at or above `0.55` and below `0.80`
- `LOW`: below `0.55`

These thresholds must be calibrated against labeled replay and hardware scenarios before authoritative rollout.

### Step 11: Derive Overall State

Required precedence:

1. Red `FAILED` when a current high-confidence required dimension is absent or failed and the red-evidence rules are satisfied.
2. Orange `IDENTITY_FAULT` when current high-confidence evidence proves the wrong device, model, mechanism, or branch responded.
3. Orange `PROBABLE_FAULT` when failure is probable or inferred but not proven enough for red.
4. Yellow `CAUTION` for meaningful conflict, degraded communication, reduced confidence, or explicit review-required state.
5. Gray `UNKNOWN` when current coverage is insufficient.
6. Green `HEALTHY` when current existence and applicable communication are strongly supported, identity is not mismatched, and no current failure evidence exists.

Operability `UNPROVEN` does not automatically prevent green. The UI must distinguish `HEALTHY COMMUNICATION / FUNCTION UNPROVEN` from a recent fully proven functional result.

### Step 12: Recovery And Hysteresis

Recovery must be evidence-driven.

Required rules:

- a red state cannot remain red solely because it was red previously
- as negative evidence decays without replacement, the state moves toward orange, yellow, or gray
- fresh positive evidence can establish recovery
- one transient positive sample should not immediately erase repeated current negative evidence
- enter and exit thresholds may differ to reduce flicker
- hysteresis is implemented through recent observation windows and thresholds, not an unbounded cached truth flag
- state transition reason and time are recorded

## Device-Class Policies

Purpose: avoid applying motor assumptions to every device.

Each supported class must define:

- expected passive frame families and cadence
- allowed runtime freshness indicators
- active-probe capabilities
- functional signals
- strong and weak absence rules
- operability proof requirements
- identity proof capabilities
- source limitations
- required dimensions for baseline green

Initial classes:

- robot controller
- motor controller
- external encoder or CANcoder
- IMU
- power distribution
- USB operator controller
- DIO limit switch
- PWM device
- analog input or sensor
- camera or vision processor
- generic/unknown CAN device

Unknown classes use conservative policies and cannot receive strong positive operability or identity claims without direct evidence.

## Common Scenario Rules

Purpose: lock down expected behavior for known failure and recovery cases.

### All Downstream CAN Devices Unpowered

Given:

- robot controller powered from an independent source
- passive observer connected and healthy
- robot-controller traffic visible
- downstream device `Existence Packets == 0`
- downstream rate `0`
- downstream last-seen aging or absent
- targeted or broad CAN communication errors present

Expected:

- robot controller remains present and healthy if its local evidence is fresh
- downstream known periodic CAN devices become absent or communication-failed with high confidence after corroboration
- runtime wrapper presence cannot rescue downstream devices
- broad system faults support a shared power or bus candidate
- unrelated DIO or USB devices do not become red solely because CAN is down

### One CAN Device Disconnected

Expected:

- qualifying passive traffic stops for that device
- targeted vendor, runtime, probe, or console evidence increases confidence
- only the affected device becomes red when evidence is sufficient
- neighbors remain green unless topology evidence supports a shared branch issue
- Fault Finder ranks device-local and adjacent-boundary candidates without changing per-device truth

### Passive Observer Disconnected

Expected:

- CAN Visibility becomes unavailable or unknown
- passive silence has zero negative influence
- Evidence continues from runtime, console, probe, and test facts
- confidence reflects missing passive coverage

### Runtime Deactivated

Expected:

- runtime observations decay and expire
- passive evidence continues independently
- active probe becomes unavailable, not failed
- prior manual and DSL results become historical
- no test can run without explicit activation and command

### Device Recovery

Expected:

- fresh device-emitted traffic and/or vendor status establishes communication recovery
- old negative observations decay
- conflict may appear briefly while current positive and aging negative evidence overlap
- state becomes green only after configured recovery evidence is sufficient
- recovery latency is measurable

### Wrong Configured CAN ID Or Model

Expected:

- expected device may be absent
- unexpected identity may be visible
- config/model mismatch is explicit
- passive traffic to a different identity does not rescue the expected device
- identity becomes mismatched only when evidence can link the observed response to the intended target or mechanism

### High Utilization Or Error Storm

Expected:

- system communication health degrades
- timing-based conclusions lose confidence
- exact fresh device-targeted facts retain more weight than broad pressure
- all devices do not become red merely because utilization is high
- UI remains responsive under console-message bursts

### More Than 20 Devices

Expected:

- every device is serviced by a real round-robin scheduler
- no device is permanently skipped because one 20 ms loop cannot service all targets
- per-device service age and count are observable
- Evidence confidence is reduced when service lag exceeds policy
- replay and hardware tests prove bounded maximum service lag

## Authoritative Snapshot Contract

Purpose: provide one stable machine-readable result for UI, CLI, replay, tests, and later AI diagnosis.

Recommended top-level shape:

```json
{
  "schemaVersion": 1,
  "engineVersion": "evidence-fusion-v1",
  "evaluationId": "eval-000123",
  "evaluatedAtMonotonicMs": 90000,
  "profile": "test_minimal_25_9",
  "profileRevision": "sha256:...",
  "topologyRevision": "sha256:...",
  "runtimeGeneration": 12,
  "sourceHealth": {},
  "system": {},
  "devices": [],
  "regions": [],
  "metrics": {},
  "policyRevision": "sha256:..."
}
```

### Per-Device Result

Each result must include:

- canonical device key
- configured label and identity
- device class and capability policy
- existence result
- communication result
- operability result
- identity result
- overall state and color token
- confidence per dimension
- conflict details
- current supporting observations
- current opposing observations
- ignored and expired observations with reasons
- inference chain
- source coverage
- current-versus-historical distinction
- state transition metadata
- recommended next evidence action

### Evidence Trace

For every dimension, the trace must include:

- winning hypothesis
- winning support
- competing hypotheses
- support margin
- contributing observation IDs
- effective influence per observation
- decay factor per observation
- correlation groups and caps
- semantic gates applied
- inference rules applied
- final confidence factors

## Shared Ownership And Surfaces

Purpose: enforce one Evidence meaning across all operator-facing consumers.

The shared Evidence service owns the full authoritative snapshot contract.

Required consumers:

- Evidence tab summary table
- Evidence tab topology
- Evidence selected-device inspector
- Live Topology Evidence lens
- CAN Fault Finder input
- textual evidence report
- CLI evidence JSON
- replay and regression tools
- later AI diagnosis input

These consumers may filter or format the snapshot. They must not recompute device truth independently.

Runtime and CAN Visibility remain independent raw lenses and are explicitly exempt from matching the Evidence conclusion.

## Fault Finder Contract

Purpose: separate device truth from fault-location inference.

Fault Finder receives:

- authoritative device conclusions
- authoritative system conclusions
- structured observations and provenance
- topology and power graphs
- operator clues

Fault Finder may derive:

- affected set
- shared-cause patterns
- candidate regions
- candidate boundaries
- ranked physical checks
- ambiguity and competing candidates

Fault Finder must not:

- parse Evidence presentation text
- assign a different per-device present/missing/conflict state
- treat stale Evidence observations as current
- count one Evidence observation again as independent fault evidence

## Scheduling And Performance

Purpose: ensure reliability does not degrade as device count or error volume grows.

### Robot-Side Collection

Periodic collection must use bounded per-loop work and real round-robin scheduling.

Required per-device service statistics:

- last attempted service time
- last successful service time
- service attempt count
- service success count
- consecutive failures
- skipped-cycle count
- current service lag
- maximum service lag
- expected maximum lag from policy

No report may burst-print directly from the 20 ms loop. Existing shared report-runner rules remain mandatory.

### Host-Side Evaluation

Host evaluation must:

- run outside blocking Tk callbacks
- accept all source and clock updates through the common `EvidenceBlock` ingestion boundary
- schedule trusted monotonic `clockTick` blocks independently of UI polling
- freeze input snapshots before evaluating
- batch UI updates
- bound event history
- deduplicate console storms
- avoid reparsing rendered text
- expose evaluation duration and queue lag
- remain responsive when the CAN bus is unpowered and errors are frequent

### Dirty Priority And Fairness

New targeted faults may mark a device dirty for priority reevaluation.

Priority must not starve ordinary devices. The scheduler must combine:

- high-priority dirty queue
- bounded dirty budget
- persistent round-robin cursor
- maximum-age override

## No-Cached-Truth Rules

Purpose: prevent prior state from masquerading as current hardware truth.

- Cached observations retain immutable timestamps and source generation.
- Current results are recomputed against current time.
- Expired observations contribute zero current weight.
- Profile changes invalidate device mapping for old observations.
- Topology changes invalidate old inferred regions.
- Runtime restart or activation change invalidates old runtime-local current claims.
- CAN-sniffer restart begins a new passive source session.
- UI restart must not revive a prior current state without current facts.
- Historical evidence remains inspectable but visibly separate.
- No cached color, selected row, or previous final state is an Evidence input.

## Capture And Replay

Purpose: make every fusion decision deterministic and regression-testable.

An evidence capture must contain:

- profile and hash
- topology and hash
- policy and hash
- source session metadata
- source availability and health timeline
- submitted `EvidenceBlock` envelopes in accepted ingestion order
- normalized observations
- raw-reference excerpts where permitted
- evaluation timestamps
- authoritative output snapshots
- operator actions
- expected ground-truth labels when known

Ground-truth labels should record independently controlled physical facts where available:

- device powered or unpowered
- CAN conductors connected or disconnected
- configured identity correct or intentionally wrong
- mechanism free, bound, disconnected, or intentionally mismapped
- passive observer attached or detached
- runtime connected, disconnected, active, or inactive
- exact operator action and observation window
- expected result per dimension

Replay requirements:

- deterministic output for the same capture, policy, and evaluation times
- replay through the production `submitEvidenceBlock()` ingestion path
- adjustable virtual time to test decay and expiry
- source removal to test missing-source behavior
- observation mutation to test conflicts
- before/after engine comparison
- machine-readable decision diff

Capture files must not require NetworkTables. Supported workflows remain host-local and REST-driven.

## Offline Block Harness

Purpose: test the complete production fusion algorithm without a robot, CAN interface, REST endpoint, UI, or real-time delays.

The Evidence engine must be a host-local library whose required inputs are configuration, policy, and `EvidenceBlock` values. Hardware collectors and live transports are producers outside the fusion core; they are not dependencies of the algorithm.

The offline harness must:

- instantiate the production ledger, ingestion service, fusion policy, and snapshot publisher
- submit blocks through the same `submitEvidenceBlock()` method used by live sources
- accept one block, an ordered block stream, or a capture file
- use explicit `clockTick` blocks as its virtual monotonic clock
- avoid `sleep`, wall-clock waits, hardware APIs, network connections, UI objects, and background polling
- return the acceptance result and resulting evaluation ID for every submitted block
- expose the complete immutable snapshot and decision trace after any step
- support reset to a known empty ledger and source-session state
- produce byte-for-byte stable machine-readable output for identical inputs and policy versions

The harness may provide scenario-building conveniences, but those helpers may only construct valid production blocks. They must not call private scoring functions, mutate the ledger directly, skip validation, or create a second test-only interpretation path.

### Scenario Format

A scenario contains:

- scenario schema version
- profile, topology, and policy inputs or stable references and hashes
- initial source-session state
- ordered `EvidenceBlock` values
- optional checkpoints after any block
- expected per-device dimensions, confidence, overall state, color, and reason codes
- expected system state and source-health conclusions
- optional ground truth kept separate from engine inputs

Example sequence:

```text
1. Submit profile and topology revision blocks.
2. Submit passive-source available and healthy state.
3. Submit current passive CAN observations for all configured devices.
4. Submit a clock tick and assert a healthy snapshot.
5. Submit later clock ticks with no new CAN observations.
6. Assert monotonic decay, then expiry, without submitting a device fault.
7. Submit fresh recovery observations and assert recovery.
```

### Repository Fixture Files

Development tools must create, validate, edit, and replay version-controlled evidence fixtures. The standard layout is:

```text
tests/regression/fixtures/evidence_fusion/<scenario>/manifest.json
tests/regression/fixtures/evidence_fusion/<scenario>/blocks.jsonl
tests/regression/fixtures/evidence_fusion/<scenario>/profile.json
tests/regression/fixtures/evidence_fusion/<scenario>/topology.json
tests/regression/fixtures/evidence_fusion/<scenario>/policy.json
tests/regression/expected/evidence_fusion/<scenario>.expected.json
```

`blocks.jsonl` contains exactly one complete production `EvidenceBlock` JSON object per non-empty line. Blocks appear in submission order. The replay harness must submit each decoded object without translating it into a test-only representation.

`manifest.json` contains:

- scenario schema version and stable scenario ID
- short purpose and controlled ground-truth description
- fixture provenance: synthetic, captured, captured-and-sanitized, or manually edited
- relative paths and hashes for profile, topology, policy, block stream, and expected output
- checkpoint names mapped to block IDs
- required engine schema and policy versions
- optional tags such as powered, unpowered, conflict, recovery, or large-device-count

The expected file contains checkpoint assertions and canonical snapshots. It is never supplied to the engine as evidence. Ground truth is test metadata and must also remain outside the submitted block stream.

Scenario-relative monotonic time starts from a documented value, normally zero. Fixtures must not depend on the developer machine's wall clock, timezone, random identifiers, thread timing, UI refresh cadence, or input file path. Any generated identifiers must be deterministic from scenario content or recorded explicitly.

### Fixture Development Tool

A repository tool must support these operations without requiring robot connectivity:

- create an empty scenario package from a named template
- append or insert a schema-valid evidence block
- generate common synthetic source, observation, context, clock, retraction, and recovery blocks
- import a live or saved capture and convert accepted events into canonical blocks
- sanitize machine-specific ports, sessions, absolute paths, and wall-clock metadata while preserving causal order
- advance virtual time by appending one or more `clockTick` blocks
- clone and mutate a scenario to create fault, conflict, stale-data, and recovery variants
- validate schemas, hashes, block IDs, references, ordering, sessions, revisions, and checkpoints
- replay through production ingestion and write an actual-results file
- compare actual results with expected snapshots and emit a machine-readable decision diff
- explicitly record or update expected results after human review

Expected results must never update automatically during an ordinary regression run. Updating expected results is a separate explicit command so an algorithm regression cannot silently bless itself.

Captured fixtures must record provenance and may retain links to raw artifacts, but the checked-in regression must remain runnable using only repository files. Sensitive or machine-specific raw data must be removed before check-in without changing the normalized claims being tested.

The fixture tool and replay library must be usable from unit tests and from the repository regression runner. Adding a scenario must be data work, not a new hard-coded test function.

### Required Offline Cases

The harness must support deterministic tests for:

- healthy evidence arrival in every possible source order
- time-only decay and expiry
- stale positive evidence versus fresh negative evidence
- source disconnection before and after device silence
- duplicate and correlated blocks
- out-of-order blocks
- invalid payloads and unsupported source/type pairs
- source restart and old-session rejection
- profile, topology, runtime-generation, and policy revision changes
- explicit retraction and recovery
- indirect evidence with and without independent corroboration
- unpowered downstream CAN while the robot controller remains powered
- more than 20 devices with fair evaluation and no order-dependent result

Robot-connected tests remain necessary for validating source collectors and calibrated policy assumptions. They are not required to exercise fusion mechanics once representative blocks have been captured or constructed.

## Observability

Purpose: make algorithm quality and starvation visible during development and field use.

Required engine metrics:

- evaluation count
- evaluation duration
- maximum evaluation lag
- devices evaluated per pass
- oldest device evaluation age
- observation counts by source and freshness state
- parser attribution rate
- unclassified console-event count
- duplicate/correlated event count
- source availability durations
- conflict count and age
- unknown count and age
- state-transition count
- red, orange, yellow, green, and gray counts
- recovery latency
- per-device service lag

Required quality metrics for labeled scenarios:

- false-green rate
- false-red rate
- missing-device detection latency
- healthy-device recovery latency
- wrong-device attribution rate
- cross-surface disagreement count
- replay nondeterminism count
- starvation violations

False green is the highest-severity classification error for safety-sensitive bringup decisions. False red is also important because it destroys operator trust and can send troubleshooting in the wrong direction.

## Algorithm Alternatives Reviewed

Purpose: explain why the proposed hybrid model is preferred.

### Sequential Rule Cascade

Advantages:

- simple to add one case
- easy to read locally
- already implemented

Disadvantages:

- order-sensitive
- difficult to calibrate
- hard to reconstruct
- new rules can silently override old rules
- conflict handling becomes scattered

Decision: retain semantic gates but replace mutable sequential conclusion building.

### Simple Weighted Average

Advantages:

- easy to calculate
- easy to display

Disadvantages:

- mixes incompatible questions
- treats missing information as a numeric direction
- hides conflict
- double-counts correlated sources
- cannot express source claim limits

Decision: reject as the primary algorithm.

### Pure Bayesian Model

Advantages:

- principled probabilistic interpretation
- supports updating beliefs over time

Disadvantages:

- requires trustworthy priors and likelihoods not yet available
- source dependencies violate naive independence assumptions
- difficult to explain correctly to pit operators
- misleading precision is likely before substantial calibration data exists

Decision: defer until a labeled corpus can justify probability claims.

### Dempster-Shafer Evidence Theory

Advantages:

- explicitly represents ignorance and conflicting evidence
- suitable for multi-source evidence

Disadvantages:

- combination behavior can be unintuitive under high conflict
- source dependence still requires explicit handling
- operational explanation is more difficult

Decision: useful reference model, but not selected for the first authoritative implementation.

### Rule-Gated Evidence Mass

Advantages:

- preserves source semantics
- supports continuous freshness decay
- exposes support and opposition
- handles correlation explicitly
- remains deterministic and explainable
- can be calibrated incrementally

Disadvantages:

- more policy data is required
- incorrect weights can still bias conclusions
- requires a replay corpus and careful device-class policies

Decision: selected target algorithm.

## Implementation Plan

Purpose: introduce the new model without destabilizing working diagnostics.

### Slice 0: Baseline Captures

- capture current powered, unpowered, selective-disconnect, recovery, and conflict scenarios
- preserve current outputs and known expected truth
- add captures for more than 20 devices or a deterministic synthetic equivalent

Checkpoint: current behavior is reproducible before fusion changes.

### Slice 1: Observation Model

- add the versioned `EvidenceBlock` ingestion envelope and handler registry
- implement the fusion core as a hardware-, transport-, and UI-independent library
- add the offline block harness using the production ingestion and snapshot path
- add schema-validating fixture creation, mutation, replay, comparison, and explicit expected-result recording tools
- register evidence-fusion fixtures with the repository regression runner
- add shared observation and source-health schemas
- build adapters for existing passive, runtime, probe, console, manual, DSL, enrichment, config, and topology facts
- add source-state, context-revision, retraction, recovery, and monotonic clock-tick control blocks
- retain current Evidence output behavior
- prohibit rendered-text parsing in new adapters

Checkpoint: observation capture and replay round-trip exactly.

### Slice 2: Freshness And Correlation

- add policy-driven decay profiles
- drive decay and expiry from trusted clock-tick reevaluation rather than new device events or UI polling
- add source session and revision invalidation
- add correlation IDs and duplicate caps
- expose current, decaying, expired, and historical observations

Checkpoint: virtual-time tests prove monotonic decay and zero current influence after expiry.

### Slice 3: Dimension Fusion In Shadow Mode

- implement existence, communication, operability, and identity fusion
- retain current engine as the visible result
- record old/new decision diffs
- add confidence traces and semantic gates

Checkpoint: no unexplained decision differences; known current bugs improve in replay.

### Slice 4: Common Evidence Snapshot

- publish stable JSON snapshot
- move Evidence tab and Live Topology Evidence lens to the common result
- preserve Runtime and CAN Visibility independence
- update current UI/runtime rules for the approved behavior

Checkpoint: zero cross-surface disagreement for the same evaluation ID.

### Slice 5: Fault Finder Integration

- remove per-device truth reinterpretation from Fault Finder
- remove parsing of passive presentation strings
- consume structured Evidence facts and add only location inference

Checkpoint: Fault Finder affected-device set exactly matches authoritative Evidence fault states.

### Slice 6: Hardware Calibration

- run the complete connected scenario matrix
- tune source and device-class policies from labeled results
- measure false green, false red, detection latency, and recovery latency
- verify fair service across large device counts

Checkpoint: acceptance criteria pass on real roboRIO hardware.

### Slice 7: Authoritative Rollout

- switch from shadow comparison to authoritative Evidence fusion
- retain decision-diff diagnostics for one release cycle
- document policy version and migration behavior
- remove obsolete post-hoc fusion paths only after stable field validation

Checkpoint: no fallback path silently produces a different Evidence truth.

## Test Strategy

Purpose: prove correctness at rule, engine, surface, and hardware levels.

### Unit Tests

Required coverage:

- production `EvidenceBlock` envelope validation, deduplication, and routing
- every source adapter
- every device-class claim limit
- freshness decay boundaries and monotonicity
- hard expiry
- source-unavailable silence handling
- correlation saturation
- conflict detection
- semantic gates
- indirect corroboration requirement
- confidence calculation
- color mapping
- profile, topology, runtime, and source-session invalidation

### Property Tests

Required invariants:

- increasing age never increases influence
- expired evidence has zero current influence
- adding duplicate correlated evidence cannot exceed its group cap
- configuration alone never changes existence to present
- unavailable-source silence never changes existence to absent
- one indirect observation never creates red
- adding strong fresh direct counterevidence cannot reduce support for its asserted hypothesis
- rendering and parsing are not part of fusion
- device iteration order does not affect results
- source input order does not affect results

### Replay Tests

Every replay test runs offline through the production `submitEvidenceBlock()` path with an explicit virtual clock. No replay test may depend on a robot connection, CAN interface, REST endpoint, Tk UI, or elapsed wall-clock time.

Required scenarios:

- healthy fully powered system
- downstream CAN power removed while robot controller remains powered
- one motor disconnected
- CANcoder disconnected
- PDP or PDH disconnected
- passive observer disconnected
- REST/runtime disconnected
- runtime deactivated
- full probe not run
- one device omitted from a probe run
- stale positive probe versus fresh targeted console failure
- stale manual pass versus current failure
- fresh positive passive traffic versus stale console failure
- exact targeted console fault versus broad system fault
- wrong CAN ID
- wrong model
- duplicate CAN ID
- high utilization
- bus-off or TX-full event
- console encoding damage
- profile change
- topology change
- source restart
- more than 20 devices
- recovery after each applicable failure

### Cross-Surface Tests

For one evaluation ID, assert exact agreement among:

- Evidence tab row
- Evidence topology node
- Evidence inspector
- Live Topology Evidence lens
- exported Evidence JSON
- textual Evidence report
- Fault Finder starting per-device state

Runtime and CAN Visibility are excluded because they intentionally present source-specific interpretations.

### Connected Hardware Tests

Required roboRIO scenarios:

1. Power all devices and establish baseline.
2. Remove downstream CAN power while keeping the robot controller powered.
3. Restore downstream CAN power and measure recovery.
4. Disconnect each supported CAN device class individually.
5. Reconnect each device and measure recovery.
6. Disconnect CANable while robot runtime remains connected.
7. Disconnect robot REST/runtime while CANable remains connected.
8. Run Full Probe with all devices.
9. Verify an intentionally omitted or unsupported probe target remains unknown rather than failed.
10. Run manual and DSL functional tests and verify dimension-specific evidence.
11. Generate high utilization or an error storm safely without host UI failure.
12. Validate round-robin service and maximum lag with a large configured device set.

All motor-motion tests require normal operator safety controls and explicit commands.

## Acceptance Criteria

The first authoritative release must satisfy all of the following:

- the Evidence conclusion is reproducible from its observation trace
- source and device iteration order do not affect the result
- every current observation has provenance and freshness influence
- expired evidence contributes zero current-state influence
- passive controller-emitted traffic cannot prove target-device existence
- cumulative packet counts cannot prove current presence
- passive silence is negative only when observer health and observation duration justify it
- robot-controller health does not rescue unpowered downstream CAN devices
- one broad system fault does not make unrelated devices red
- indirect evidence requires independent corroboration before red
- conflicts render yellow
- probable or inferred degradation renders orange
- red is reserved for current high-confidence failure or absence
- gray represents insufficient current evidence
- functional proof and current communication are represented separately
- Fault Finder does not disagree with authoritative Evidence per-device truth
- Runtime and CAN Visibility remain independent lenses
- no Evidence consumer reparses rendered text
- UI remains responsive during an unpowered CAN bus error storm
- more than 20 devices receive bounded fair service
- powered baseline, CAN-power-off, selective disconnect, and recovery hardware scenarios pass
- deterministic replay passes for the complete scenario corpus
- cross-surface disagreement count is zero
- replay nondeterminism count is zero
- every fixed fusion bug has a narrow regression test

## Reliability Release Gates

Purpose: prevent premature promotion from shadow mode.

The new engine must remain in shadow mode until:

- every required replay scenario has labeled expected results
- every red conclusion has a trace showing direct proof or independent corroboration
- no known false green remains in the CAN-power-off scenario
- no known false red remains in the fully powered baseline
- selective disconnect identifies the intended device without staining unrelated devices
- recovery behavior is repeatable
- cross-surface agreement is exact
- large-device fairness metrics stay within configured policy
- all relevant local regressions pass
- connected non-motion robot regression passes
- motion-dependent hardware tests pass under explicit operator control

## Definition Of Done

This feature is complete when:

- one shared Evidence engine owns final fused device truth
- all relevant current sources are normalized and available to the engine
- all current influence decays with age according to explicit policy
- historical observations remain visible but cannot remain current truth
- four separate device dimensions and system-level state are published
- every decision is explainable and replayable
- raw Runtime and CAN Visibility lenses retain their own meanings
- Evidence UI, Live Topology Evidence, reports, JSON, and Fault Finder agree
- current order-sensitive and text-parsing fusion paths are retired
- hardware and replay release gates pass
- operator documentation explains colors, confidence, conflict, and history

## Tradeoffs

- A structured observation ledger and dimension-specific fusion model are more complex than a rule cascade, but they make decisions reproducible and testable.
- Conservative unknown and caution states may initially appear less decisive, but they are more trustworthy than unsupported green or red conclusions.
- Continuous decay requires source-specific policy and calibration, but it avoids stale binary truth.
- Correlation tracking reduces apparent corroboration from repeated errors, but prevents one root event from creating false certainty.
- Keeping raw lenses independent permits visible disagreement, but that disagreement is diagnostically useful and the Evidence lens explains the combined conclusion.
- Hardware calibration takes time, but confidence labels are not credible without it.

## Future Extensions

- calibrated probabilistic models after a sufficiently large labeled corpus exists
- multiple passive observers with attachment-point-aware inference
- explicit power-domain sensors and switch-state evidence
- automated evidence-request recommendations
- richer operator clue workflows
- evidence timelines and state-transition playback
- per-mechanism conclusions above individual devices
- camera and vision-processor source adapters
- automatic policy tuning proposals reviewed by humans
- AI-generated diagnostic summaries constrained to the authoritative Evidence snapshot

## Related Documents

- `Current UI And Runtime Rules - V2.md`
- `docs/FEATURE_SPEC_CAN_DEVICE_EVIDENCE_SOURCE_CONTRACTS.md`
- `docs/FEATURE_SPEC_CAN_EVIDENCE_UI.md`
- `docs/FEATURE_SPEC_CONSOLE_EVIDENCE_PRIMARY_FAULT_SOURCE.md`
- `docs/FEATURE_SPEC_ACTIVE_DEVICE_PRESENCE_CONFIDENCE.md`
- `docs/FEATURE_SPEC_PIT_ROBOT_DIAGNOSIS_FIRST_PASS.md`
- `docs/FEATURE_SPEC_MULTI_OBSERVER_CAN_FAULT_LOCALIZATION.md`
- `docs/SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md`
- `docs/SPEC_OPERATOR_CLUES_MODEL.md`
- `docs/SPEC_BREAK_AND_ERROR_OPERATOR_SURFACES.md`
- `docs/AI_DIAGNOSIS.md`
