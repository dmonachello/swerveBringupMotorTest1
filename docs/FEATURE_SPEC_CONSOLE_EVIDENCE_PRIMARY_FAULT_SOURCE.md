# Feature Spec: Console Evidence As Primary Fault Source

## Purpose

Define how robot and host console messages become a first-class, high-trust evidence source for CAN and device-presence diagnosis.

## Status

`IMPLEMENTATION_READY`

## Problem

The current system already captures some console-derived information, but it does not treat device-targeted console faults as one of the strongest sources of diagnostic truth.

This causes real misses in hardware fault cases such as:

- a motor is physically disconnected
- vendor/runtime code emits repeated stale or timeout warnings for the exact device
- stale runtime snapshots or weak passive observations still keep the device row too healthy
- `CAN Fault Finder` under-ranks or misses the fault entirely

In practice, the console often reports failures earlier and more explicitly than the higher-level runtime APIs.

Examples:

- exact vendor family
- exact device type
- exact CAN ID
- explicit stale/timeout/unreachable wording

Those messages should not remain only as UI text.

They should materially drive device interpretation and fault ranking.

## Goal

Treat fresh, device-targeted console faults as one of the most trusted negative evidence sources in the system.

In particular:

- console messages must be normalized into structured fault evidence
- structured console faults must be attached to the matching device row
- fresh targeted console faults must outrank stale or weak positive evidence
- `CAN Fault Finder` must consider a device affected even if weak stale positive evidence still says `present`

## Non-Goals

This feature does not:

- remove passive CAN, runtime, probe, or manual sources
- make all console text equally authoritative
- replace vendor tools
- claim exact electrical root cause from console text alone
- collapse system-level bus warnings and device-targeted warnings into one undifferentiated stream

## Core Principle

Fresh device-targeted console fault evidence is stronger than stale or weak positive presence evidence.

For disconnect and stale-communication diagnosis, the system should assume vendor-targeted console faults are authoritative unless contradicted by stronger fresh direct evidence.

## Scope

This feature applies to:

- `Evidence` device interpretation
- shared interpreted device rows
- `CAN Fault Finder`
- dirty-device reevaluation triggers
- console-derived freshness/conflict logic

It applies first to the current known fault families already seen in the system, especially CTRE stale and timeout style messages.

## Terminology

### Device-Targeted Console Fault

A console event that can be mapped to a specific expected or observed device, usually using:

- vendor name
- device type
- CAN ID
- known label mapping

Example:

- `talon fx 9 ... CAN message is stale`

### System-Level Console Fault

A console event that describes bus-wide or controller-wide health rather than a single device.

Examples:

- bus off
- tx full
- error spike
- high utilization
- loop overrun

### Structured Console Fault

A normalized record derived from raw console text with fields the evidence engine can reason about directly.

## Structured Console Fault Model

Each normalized console record should include:

- `sourceLens`
  - `console`
- `origin`
  - `robot`
  - `host`
- `timestamp`
- `ageSec`
- `freshness`
  - `fresh`
  - `aging`
  - `stale`
- `severity`
  - `info`
  - `warn`
  - `error`
- `scope`
  - `device`
  - `system`
- `vendor`
  - for example `ctre`, `rev`, `wpilib`
- `deviceType`
  - for example `talon fx`, `spark max`, `pdh`, `pdp`
- `canId`
  - integer when available
- `matchedLabel`
  - selected profile device label when resolved
- `faultFamily`
  - normalized symbolic family
- `rawText`

## Initial Fault Families

Minimum initial `faultFamily` values:

- `ctre_stale_status_signal`
- `ctre_timeout`
- `ctre_device_unreachable`
- `rev_timeout`
- `device_signal_stale`
- `bus_off`
- `tx_full`
- `error_spike`
- `high_util`
- `loop_overrun`
- `controller_side_comm_loss`
- `unknown_device_fault`
- `unknown_system_fault`

## Source Classification Rules

### Device-Targeted Classification

A message is device-targeted when it includes enough information to resolve a specific device or likely device identity.

Minimum acceptable mapping inputs:

- vendor + device type + CAN ID

or:

- exact known label

### System-Level Classification

A message is system-level when it does not cleanly map to one device and instead represents bus-wide or runtime-wide health.

### Unknown Classification

If a message cannot be confidently mapped to either a device or a system-level family, it may still be stored, but it must not receive the same weight as normalized targeted evidence.

## Trust and Precedence Rules

### Device-Targeted Fresh Faults

Fresh device-targeted console faults are high-trust negative evidence.

They must:

- strongly downgrade `operability`
- reduce confidence in stale positive presence
- mark the device dirty for immediate reevaluation
- be visible in the device evidence inspector

### System-Level Fresh Faults

Fresh system-level console faults are high-trust global evidence.

They must:

- contribute to bus-wide pressure or controller-side candidates
- reduce confidence in broad runtime-derived conclusions when appropriate
- not be attached to one specific device unless additional mapping exists

### Stale Positive Evidence

The following must not overrule fresh targeted console faults by themselves:

- old manual motion results
- stale runtime `present`
- passive visibility with zero or near-zero current traffic rate
- stale probe success

### Stronger Fresh Positive Contradiction

A fresh targeted console fault may be outweighed only by stronger fresh direct evidence such as:

- fresh active probe success on the same device
- fresh runtime evidence clearly proving continued healthy use
- other equivalent high-trust direct evidence

When this happens, the row should usually become `conflict` or strong `degraded`, not silently healthy.

## Per-Device Interpretation Changes

The shared interpreted device row must consume structured console faults as one of its main inputs.

### Required Effects

If a fresh device-targeted console fault exists for the device:

- `operability` should move toward `FAILED` or strong `DEGRADED`
- `confidence` should not remain `HIGH` unless contradicted by stronger fresh direct evidence
- `state` should become:
  - `failed`
  - `degraded`
  - or `conflict`
- `notesText` should explicitly mention the targeted console fault family

### Presence Semantics

Fresh device-targeted console faults may leave `existence = PRESENT` if direct evidence still shows the device exists on the bus, but the row must still count as affected when:

- `operability` is strongly degraded or failed
- stale/weak positive evidence is the only support
- console fault evidence is fresh and repeated

This is important because disconnect-like cases may briefly retain partial visibility while the device is effectively unusable.

## Affected Device Rules For Fault Finder

The fault finder must broaden what counts as an affected device.

In addition to missing or absent devices, a device must count as affected when:

- it has fresh device-targeted console fault evidence
- and the interpreted row is:
  - `FAILED`
  - `DEGRADED` with low confidence
  - or `CONFLICT`

This prevents `candidates=none` results when the console is clearly reporting an exact device failure.

## Dirty Reevaluation Triggers

Any newly observed device-targeted console fault must:

- immediately mark the matched device dirty
- assign high dirty priority
- move reevaluation ahead of ordinary cursor progression

Any newly observed system-level console fault must:

- trigger fault-finder freshness re-evaluation
- update the system bus-health summary

## Freshness Rules

Console fault records must age explicitly.

Minimum buckets:

- `fresh`
- `aging`
- `stale`

Suggested initial policy:

- `fresh` for recent events in the active observation window
- `aging` after the first short decay threshold
- `stale` after the longer threshold where the event should no longer dominate device interpretation

Exact numbers may be constants in code, but they must be symbolic constants, not inline literals.

## UI Changes

### Evidence Tab

`Console Evidence (Robot/Host)` must show normalized device-targeted faults clearly, including:

- fault family
- severity
- freshness
- vendor/device identity match

The Evidence tab must expose two layers of console reporting:

- generalized console stats
- device-specific console stats for the selected device

### Generalized Console Stats

The system must report generalized console statistics for the active observation window.

Minimum generalized fields:

- total event count
- device-targeted event count
- system-level event count
- unclassified event count
- warn/error/fatal totals
- top fault families
- top vendors seen
- fresh/aging/stale totals when available
- first seen / last seen when available

These stats may appear in the existing system console area or in a dedicated structured subsection, but they must be available as structured evidence and not only inferred from free-form text.

### Device-Specific Console Stats

For the selected device, `Console Evidence (Robot/Host)` must show device-specific console statistics.

Minimum device-specific fields:

- matched label
- vendor
- device type
- CAN ID when known
- matched event count
- warn/error/fatal totals
- repeat rate or burst count
- first seen / last seen when available
- top fault family
- parser confidence
- normalization status
  - `structured`
  - `partial_match`
  - `unclassified`
- representative raw examples

The device-specific section should also present a short verdict such as:

- `strong targeted negative evidence`
- `weak targeted evidence`
- `unclassified console evidence`

### CAN Bus Health Section

The system bus-health text must stop implying that there are no warnings anywhere when only the system-level bus categories are clear.

The wording must make explicit that this section is:

- system-level bus health
- not all device-targeted warnings

### CAN Fault Finder

Candidate explanations must cite structured console evidence in:

- `supportingEvidence`
- `conflictingEvidence`
- or both

### Provenance

Console-derived evidence must remain visibly labeled as `console`.

## Implementation Plan

### Step 1: Structured Console Normalization

Extend console snapshot building to produce structured records with:

- scope
- vendor
- device type
- can id
- matched label
- fault family
- severity
- freshness

Also extend the snapshot to produce:

- generalized console stats
- per-device console stats
- representative raw examples per device

Likely code areas:

- `tools/can_nt/bringup_ui.py`
- shared console snapshot helpers already used by the evidence path

### Step 2: Evidence Combiner Precedence

Update per-device interpretation so fresh targeted console faults:

- strongly downgrade operability
- weaken stale positive rescue paths
- produce clearer notes and source scores

Primary code area:

- `tools/can_nt/passive_discovery_integration_service.py`

### Step 3: Dirty Priority Integration

When structured console faults change:

- mark matching devices dirty
- reevaluate them before ordinary cursor continuation

Primary code area:

- `tools/can_nt/bringup_ui.py`

### Step 4: Fault Finder Affected-Device Logic

Update affected-device selection so strong console-targeted failures count even when `existence` is still `PRESENT`.

Primary code area:

- `tools/can_nt/can_fault_inference.py`

### Step 5: UI Wording Cleanup

Clarify that the bus-health section is system-only and does not replace device-targeted console evidence.

Primary code area:

- `tools/can_nt/bringup_ui.py`

## Acceptance Criteria

The feature is complete when:

- a fresh `talon fx <id>` stale or timeout warning is normalized into a device-targeted structured fault
- the matching expected device row is marked affected even if weak stale positive evidence still exists
- `CAN Fault Finder` no longer returns `candidates=none` for a real targeted disconnect case that is clearly present in fresh console evidence
- stale manual motion evidence cannot rescue a device against fresh targeted console failure evidence
- weak passive visibility with zero-rate traffic cannot rescue a device against fresh targeted console failure evidence
- system bus-health wording no longer implies there are no warnings when only per-device console faults are present
- the Evidence tab console subpanel shows structured generalized and device-specific stats rather than only raw message text
- unit tests cover:
  - targeted CTRE stale warning
  - targeted timeout warning
  - system-level bus fault
  - fresh targeted console fault versus stale runtime/manual/passive positives
  - fault-finder affected-device promotion from console evidence
  - generalized console stat aggregation
  - device-specific console stat aggregation and example rendering

## Test Cases

Minimum required tests:

- disconnect `FALCON 9` and verify repeated CTRE stale warnings become a targeted structured fault
- verify the `FALCON 9` row becomes affected
- verify `CAN Fault Finder` produces a candidate instead of `no_fault_detected`
- verify system bus-health text can still say bus-wide health is okay while per-device console evidence shows a device-targeted fault
- verify a bus-wide warning case still produces the right system-level candidate

## Tradeoffs

Promoting console evidence increases diagnostic sensitivity, but it also requires careful parsing and freshness handling.

This is acceptable because:

- targeted vendor console faults are often more trustworthy in failure cases than stale runtime API snapshots
- the system already labels evidence provenance
- conflicts can be surfaced honestly instead of hidden

## Future Extensions

Future work can add:

- richer vendor-specific fault normalization
- repeated-event clustering
- confidence calibration from repeated identical warnings
- explicit correlation between console faults and baseline-compare deviations
- console replay fixtures from captured real sessions
