SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Feature Spec: Passive CAN Device Discovery PoC

## Purpose

Define the first proof-of-concept implementation for passive CAN device discovery, health inference, and reverse-engineering evidence extraction.

This PoC is the first executable target derived from [FEATURE_SPEC_PASSIVE_CAN_DEVICE_DISCOVERY.md](/c:/Users/dmona/swerve3/docs/FEATURE_SPEC_PASSIVE_CAN_DEVICE_DISCOVERY.md). It is intentionally separate from production code, but it must be structured so it can be integrated back into the existing host-side Python stack with minimal rework.

## Status

`PARTIALLY_IMPLEMENTED`

## Goal

The PoC should answer three questions from passive evidence:

1. What devices appear to be present on the CAN bus?
2. How much health/confidence evidence do we have for each device?
3. What frame-family evidence and byte-level fingerprints help further reverse engineering?

The immediate user is a developer running the tool at the terminal.

The longer-term goal is to feed the larger troubleshooting system with:

- reliable device inventory
- passive health evidence
- machine-consumable reverse-engineering artifacts

## Relationship to Broader Work

This PoC sits between:

- raw passive captures and ad hoc manual analysis
- future production integration into the host-side diagnostics stack

It is not yet:

- the final integrated troubleshooting engine
- a dashboard surface
- a complete vendor protocol decoder

## Hard Requirements

- The PoC must remain read-only on CAN.
- The PoC must not use NetworkTables.
- The PoC must support both REV and CTRE from day one.
- The PoC must work on offline capture files first.
- Before the PoC is considered complete, it must also support live sources.
- Unknown traffic must be preserved, not discarded.
- Expected-but-missing devices must be surfaced by default when a bringup profile is provided.
- Unexpected observed devices must be surfaced by default.
- CTRE HTTP enrichment is optional, but when available it is trusted more than passive CAN for CTRE-specific conflicts.

## Scope

The PoC covers:

- offline analysis of passive CAN captures
- live passive acquisition from supported sources
- passive device inventory
- passive presence confidence
- bounded health classification with explicit evidence gaps
- frame-family classification
- byte-level variation and fingerprint evidence
- optional CTRE HTTP enrichment
- optional comparison against bringup profile JSON

The PoC does not cover:

- UI work beyond minimal terminal verification output
- NetworkTables publishing
- Java-side consumption
- active CAN polling or CAN transmission
- automatic fault localization from topology
- automated repair advice

## Non-Goals

- polished presentation
- final production schema stability across all future phases
- complete semantic decoding of all vendor payloads
- direct integration into the existing CLI/UI during the PoC

## Repository Placement

The PoC should live in a separate directory:

- `tools/passive_discovery_poc/`

It should still be designed for later extraction or reintegration by:

- reusing existing acquisition/parsing code where practical
- keeping domain logic separate from CLI glue
- keeping schemas and contracts explicit

## Implementation Shape

Preferred internal split:

- acquisition adapters
- normalized frame model
- family metrics and classification
- device inference and scoring
- enrichment adapters
- output/rendering layer
- thin CLI entrypoint

The expected top-level entrypoint is:

- `tools/passive_discovery_poc/passive_discovery.py`

## Input Priority

Implement acquisition in this order:

1. offline `pcapng`
2. offline candump/text
3. live CANable/slcan serial
4. live REV USB bridge capture
5. CTRE HTTP endpoint query

The PoC may stop before implementing all live modes, but it is not complete until live support exists.

## Multi-Source Fusion

The PoC may use multiple sources in one run when doing so improves accuracy.

Examples:

- passive CAN plus CTRE HTTP enrichment
- passive CAN plus bringup profile comparison
- passive CAN plus topology/profile naming metadata

Source precedence rule:

- for CTRE device existence and richer CTRE metadata, trust CTRE HTTP more than passive CAN when the two conflict
- preserve both sources and record the conflict explicitly

## Supported Run Modes

The PoC should use one command with options rather than multiple unrelated entrypoints.

First-pass expected modes:

- analyze offline capture
- observe live traffic
- enable CTRE enrichment
- enable profile comparison
- request full evidence dump

## Primary Inputs

### Passive Capture Inputs

- `pcapng`
- candump/text
- live CANable/slcan serial stream
- live REV USB bridge stream or directly parsed REV USB bridge traffic

### Optional Enrichment Inputs

- CTRE diagnostic HTTP endpoint
- bringup profile JSON

## Bringup Profile Use

When present, the bringup profile should provide:

- expected device inventory
- profile node metadata
- naming/role context when available

The PoC should fail the run if profile parsing is requested and the profile is missing or malformed.

## Canonical Identity

The canonical passive identity key is:

- `(manufacturer, deviceType, deviceId)`

When available, augment with:

- bus name
- profile node
- inferred model
- human-readable role/name from profile

## Output Contract

Each run should produce one canonical JSON artifact by default.

That artifact should contain:

- run metadata
- source metadata
- discovered devices
- expected-but-missing devices
- unexpected observed devices
- frame-family inventory
- evidence summaries
- unknown/raw traffic summaries
- optional CTRE enrichment
- optional profile comparison results

An additional full-dump mode may emit richer artifacts, but the default should still be one main JSON file per run.

## Human Verification Output

Default terminal output should show:

- concise device table
- supporting evidence families for each device

Full dumps should appear only when explicitly requested.

## Device-Level Output Expectations

Each device row should support at least:

- canonical identity
- inferred vendor/device classification
- expected/unexpected/missing status
- `presenceConfidence`
- `healthConfidence`
- `inventoryConfidence`
- `evidenceSources`
- bounded health enum
- supporting family references
- evidence gaps

## Health Classification

Use this bounded first-pass enum:

- `unknown`
- `limited`
- `good_evidence`
- `degraded`
- `fault_indicated`

Health must be accompanied by explicit evidence gaps.

Examples:

- present, but no fault/status surface decoded
- passive evidence only, no richer CTRE corroboration
- device expected in profile but not currently observed

## Frame-Family Expectations

The PoC should preserve and analyze frame families using the broader passive discovery model:

- likely device-emitted primary status
- likely device-emitted secondary status
- likely device-emitted heartbeat/housekeeping
- likely controller-emitted command
- likely controller-emitted poll
- likely shared bus control
- unknown

The PoC should go as deep as practical on:

- cadence
- payload variation
- byte-position change fingerprints
- cross-capture recurrence

## Unknown Traffic Handling

If a frame cannot be decoded into known FRC fields or a known family role:

- retain it as raw unknown traffic
- include it in the canonical JSON artifact
- surface it in full-dump/evidence mode

Unknown traffic must not be silently dropped.

## Failure Handling

### Live Source Failure

- fail hard if a live primary acquisition source drops mid-run

### CTRE HTTP Failure

- degrade to passive-only with a warning
- if CTRE is the only requested source, the run may still complete with a clearly degraded result when possible

### Profile Failure

- fail the run if profile use was requested and the profile is missing or malformed

### Weak Evidence

- emit an uncertain device row when evidence is too weak for a stronger conclusion

## Testing Strategy

Automated tests should cover:

- known devices detected correctly
- shared `deviceId=0` traffic excluded from presence
- known command families excluded from presence
- unknown raw traffic preserved
- expected/missing device handling
- unexpected device handling
- evidence-family reporting
- canonical JSON semantics

Test style:

- semantic assertions
- plus a small set of golden JSON fixtures for representative runs

## Required Initial Fixtures

Initial required regression fixtures:

- `usbCap2_can.pcapng`
- `usbCap3_can.pcapng`
- `usbCap4_can.pcapng`
- `usbCap8_can.pcapng`

The fixture set must be extensible so additional captures can be added later.

## Required Live Validation

Before the PoC is considered complete, validate all of:

- live CANable/slcan observation
- live REV USB bridge observation
- live CTRE HTTP enrichment against a reachable roboRIO

## Evidence Goals

The PoC succeeds only if all three become useful:

1. reliable device inventory
2. useful health assessment
3. useful reverse-engineering evidence

## Milestones

### Milestone 1

- scaffold PoC directory
- implement offline `pcapng` ingestion
- normalize frames
- group frame families
- emit canonical JSON
- render default device/evidence table

### Milestone 2

- add candump/text ingestion
- add family metrics
- add first-pass classification and confidence scoring
- add expected/missing/unexpected profile comparison

### Milestone 3

- add deeper evidence and fingerprint output
- add richer REV/CTRE seed rules
- add CTRE HTTP enrichment

### Milestone 4

- add live CANable/slcan support
- add live REV USB bridge support
- validate all required live modes

## Integration-Back Plan

The PoC should be structured so later integration can move:

- reusable domain logic into shared host-side Python code
- reusable acquisition adapters into existing capture/input layers
- stable JSON contracts into higher-level CLI/UI/report consumers

Code that should stay PoC-local as long as possible:

- experimental heuristics
- unstable CLI flags
- ad hoc reverse-engineering printouts

## Definition of Done

The PoC is done when:

- it runs offline on the required fixture captures
- it detects the known CTRE and REV devices with useful evidence
- it excludes known command/shared families from presence
- it preserves unknown traffic
- it compares against bringup profile JSON
- it performs optional CTRE enrichment
- it supports all required live modes
- it emits one canonical machine-consumable JSON artifact per run
- it provides enough default terminal output for manual verification
- it demonstrates useful inventory, health, and reverse-engineering value

## Documentation Requirement

The PoC directory should include a short README describing:

- supported inputs
- command usage
- output artifact shape
- known limitations
- how the PoC is intended to integrate back into the main project later
