SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Feature Spec: Vendor-Agnostic Traffic Classification And Device Identity

## Purpose

Purpose: define a vendor-agnostic classification layer that separates physical device identity from other observed CAN traffic families, while preserving all observed traffic for diagnostics and reverse-engineering.

This spec is motivated by a current CTRE-specific failure mode, but the design target is system-wide and vendor-agnostic.

## Current Status

Purpose: record the implementation status as of August 12, 2026.

Implemented and validated:

- shared traffic classification now separates `definite`, `supporting`, and `nonDevice` evidence roles
- `--dump-profile` and `--dump-api-inventory` now preserve retained non-device traffic under `nonDeviceTrafficFamilies[]`
- live device visibility no longer promotes the investigated fake CTRE rows into physical device identities
- verified CTRE passive sensor signatures for CANcoder and Pigeon now promote to canonical physical device identities

Still partial:

- this spec's general vendor-agnostic model is broader than the currently validated CTRE-first implementation
- non-device traffic is preserved in machine-readable outputs, but operator-facing surfacing of those families is still less complete than the final design target

## Problem

The current host-side observation path can turn some real CAN traffic into fake physical device identities.

This happens when the system:

- decodes raw extended-ID fields from a frame
- extracts a raw `(manufacturer, deviceType, deviceId)` tuple
- treats that tuple as if it were already a canonical physical device identity
- stores it as an observed device
- exposes it through UI, profile dump, and inventory outputs

The subtle bug is that a decoded tuple is often a useful observation, but it is not always a valid canonical device identity and it is not always valid evidence that a distinct physical device should be created in inventory.

In other words, the system is currently too close to this mental model:

```text
Frame
  ->
decoded tuple
  ->
device row
```

That shortcut is unsafe.

The safer model is:

```text
Frame
  ->
observation
  ->
traffic-family classification
  ->
identity contribution decision
  ->
physical device row or non-device traffic family
```

This distinction matters because not all observed traffic families should create device rows.

Examples:

- passive vendor traffic may use raw device-type aliases that should normalize to a canonical type before any device identity is emitted
- controller-emitted or gateway-emitted traffic may mention a device-oriented tuple without proving that a distinct physical device should be created in inventory
- shared-bus or broadcast-like traffic may be real and important evidence but not attributable to a single physical device

The system must therefore distinguish:

- traffic that contributes to canonical physical device identity
- traffic that is real but should be represented as another traffic kind

## Scope

This spec applies to all affected host-side surfaces that currently consume observed CAN traffic identity:

- live visibility and unprofiled device rows
- host evidence views
- `--dump-profile`
- `--dump-api-inventory`
- later diff and reverse-engineering consumers that build on the same shared observation path

This spec defines:

- the shared traffic classification model
- the shared identity-contribution rules
- the output contracts for physical devices and non-device traffic families
- the first concrete CTRE implementation direction

This spec does not define:

- full semantic decoding of every vendor payload byte
- changes to robot-side actuation behavior
- any active CAN transmission behavior

## Goals

- Preserve all observed traffic.
- Stop inventing fake physical device identities from non-device traffic.
- Canonicalize vendor-specific passive aliases before device identity is emitted.
- Provide one shared classification pipeline for all host-side consumers.
- Add a stable JSON contract for non-device traffic families.
- Keep the design vendor-agnostic while allowing CTRE-specific first-pass rules.

## Non-Goals

- Do not discard or hide real traffic just because it does not map to a device.
- Do not require a full payload-semantic decode before classification can work.
- Do not claim model-exact identity when only family-level evidence exists.
- Do not redesign unrelated UI workflows as part of this change.

## Current Failure Mode

## Purpose

Purpose: document the concrete bug class that motivates this work.

The current host-side path already produces normalized frames for passive discovery, including vendor-specific device-type normalization where known.

However, some higher-level consumers still collect observed device identities from raw decoded arbitration-ID tuples instead of the normalized and classified identity path.

This creates two concrete problems:

- passive aliases can appear as separate fake devices
- non-device traffic families can appear as fake physical device rows

The underlying architectural mistake is confusion between:

- message-oriented observation
- canonical physical device identity

The decoded tuple belongs first to the observation layer.

It should only become a physical device row after:

- vendor-specific normalization when required
- traffic-family classification
- an explicit decision that this traffic kind contributes to device identity

Observed CTRE examples from current investigation:

- raw passive `deviceType=5` should normalize to canonical CANcoder `deviceType=7`
- raw passive `deviceType=21` should normalize to canonical Pigeon `deviceType=4`
- broadcast or control-like CTRE traffic can currently appear as a fake identity such as `Unknown 4-0-63`

These examples show why a raw decoded tuple is not enough by itself to populate physical inventory:

- some tuples are aliases that need canonicalization
- some tuples belong to real traffic families that are not physical devices

The bug is therefore not that decoded tuples are meaningless.

The bug is that the current path promotes them too early and with too little interpretation.

## Design Summary

Purpose: state the intended design in one short view.

Every observed frame should produce two separate interpretations:

1. a traffic-family classification
2. an optional physical device identity contribution

Not every traffic family contributes to physical device identity.

Consumers must use:

- `devices[]` for physical device identities
- `nonDeviceTrafficFamilies[]` for real observed traffic that does not represent a physical device row

Both outputs come from one shared classification pipeline.

The next refinement is that classifiable traffic must be separated into three evidence roles:

- definite device-defining traffic
- supporting or reference-only traffic
- non-device or unknown traffic

Only the first role is allowed to create a physical device row by itself.

## Shared Classification Pipeline

## Purpose

Purpose: define the single shared ownership path for all affected consumers.

All host-side consumers should derive device identity and non-device traffic from one shared pipeline:

1. Observe raw frame.
2. Build normalized frame.
3. Classify traffic family.
4. Decide whether the family contributes to physical device identity.
5. If yes:
   - emit canonical device identity contribution.
6. If no:
   - emit non-device traffic family contribution.
7. Fan out the shared result to:
   - live visibility
   - evidence/debug surfaces
   - profile dump
   - inventory dump

No consumer should recompute identity contribution rules independently.

This follows the repo's shared-state and no-cached-truth direction.

## Classification Outputs

## Purpose

Purpose: define the two top-level outputs produced by the shared pipeline.

Each observed frame family must produce:

- `trafficKind`
- `contributesToDeviceIdentity`
- `identityDisposition`
- optional `canonicalDeviceIdentity`
- optional `trafficFamilyKey`
- supporting observed metrics

Rules:

- `canonicalDeviceIdentity` is present only when the family contributes to a physical device identity
- `identityDisposition` must be one of:
  - `definite`
  - `supporting`
  - `nonDevice`
- `trafficFamilyKey` is always present for classifiable traffic
- non-device traffic must never be dropped simply because it does not contribute to identity

Interpretation:

- `definite` means the family can create or reinforce a physical device row
- `supporting` means the family may reinforce an already-known device identity but must not create a new device row by itself
- `nonDevice` means the family is retained for diagnostics and reverse engineering but must not create a device row

## Traffic Kinds

## Purpose

Purpose: define the stable first-pass classification vocabulary.

Initial vendor-agnostic `trafficKind` values:

- `device_primary_status`
- `device_secondary_status`
- `device_sensor_status`
- `device_heartbeat_housekeeping`
- `supporting_reference`
- `controller_emitted_command`
- `controller_emitted_poll`
- `shared_bus_control`
- `broadcast_system`
- `unknown_family`

Interpretation rules:

- `device_*` kinds may contribute to physical device identity if canonical identity can be resolved
- `supporting_reference` must never create a physical device identity by itself
- `controller_emitted_command` must never create a physical device identity by itself
- `controller_emitted_poll` must never create a physical device identity by itself
- `shared_bus_control` must never create a physical device identity by itself
- `broadcast_system` must never create a physical device identity by itself
- `unknown_family` defaults to no identity contribution unless later promoted by explicit rules

## Canonical Device Identity

## Purpose

Purpose: define the only identity shape that may flow into `devices[]`.

Canonical physical device identity is:

- `manufacturer`
- `deviceType`
- `deviceId`

This identity must represent a physical device-family identity after any vendor-specific passive normalization is applied.

Examples:

- CTRE passive CANcoder alias type `5` becomes canonical type `7`
- CTRE passive Pigeon alias type `21` becomes canonical type `4`

Only canonical identities may:

- become observed device rows
- become structured passive-identity label candidates such as `REV_MOTORCONTROLLER_07`
- enter `--dump-profile` `devices[]`
- enter `--dump-api-inventory` `devices[]`

## Non-Device Traffic Families

## Purpose

Purpose: define the new stable JSON contract for real traffic that should not become physical device rows.

Introduce a new top-level output section:

```json
nonDeviceTrafficFamilies: []
```

This section is required for:

- inventory outputs
- profile-dump metadata
- any future evidence/debug surfaces that use the shared contract

Suggested stable object shape:

```json
{
  "familyKey": "ctre.shared_bus_control.pf_ef",
  "manufacturer": 4,
  "trafficKind": "shared_bus_control",
  "rawIdentityHints": [
    {
      "manufacturer": 4,
      "deviceType": 0,
      "deviceId": 63
    }
  ],
  "frameFamilies": [
    {
      "apiClass": 0,
      "apiIndex": 0
    }
  ],
  "metrics": {
    "count": 1234,
    "rateHz": 50.0,
    "lastSeenMs": 123456789
  },
  "notes": [
    "Observed traffic family retained for diagnostics but not promoted to a physical device identity."
  ]
}
```

Contract rules:

- `familyKey` must be stable for the same family within a capture and across repeated dumps when possible
- `rawIdentityHints` preserve the original observed raw tuple information
- `trafficKind` is required
- `identityDisposition` is required
- `metrics` are required
- these rows must never be copied into `devices[]`

## Output Contracts By Surface

## Purpose

Purpose: define how each affected surface should consume the shared result.

### Live Visibility And Unprofiled Rows

- show canonical physical device identities in the device list
- show non-device traffic in a separate traffic-family section or drilldown
- do not create structured passive-identity device rows from non-device traffic families

### `--dump-profile`

- `devices[]` must contain only canonical physical device identities
- `profiles.<name>.devices[]` must reference only those canonical device labels
- non-device traffic must be preserved under metadata, not mixed into `devices[]`

Suggested metadata field:

```json
trafficMetadata: {
  nonDeviceTrafficFamilies: []
}
```

### `--dump-api-inventory`

- `devices[]` must contain only canonical physical device identities
- `nonDeviceTrafficFamilies[]` must contain the retained non-device traffic records

### Reverse-Engineering Consumers

- may consume both physical identities and non-device traffic families
- must not collapse non-device traffic back into fake physical device identities

## Shared Ownership

## Purpose

Purpose: define where the authoritative classification decisions must live.

The authoritative classification and identity-contribution decisions must live in one shared host-side module area.

Recommended ownership:

- a shared passive discovery or common CAN classification module

Not allowed:

- separate UI-only classification rules
- separate dump-only identity rules
- ad hoc recomputation in multiple surfaces

## CTRE First-Pass Implementation

## Purpose

Purpose: define the first concrete vendor implementation without making the design CTRE-specific overall.

The first pass should add explicit CTRE handling for:

- motor-controller primary and secondary status families
- passive CANcoder alias families
- passive Pigeon alias families
- shared-bus or control/gateway CTRE traffic
- CTRE supporting/reference-only families that should reinforce but not define devices

First-pass expectations:

- CTRE passive alias families normalize to canonical device type before device identity is emitted
- CTRE passive alias families may still be classified as supporting/reference-only if they do not independently prove a distinct physical device
- selected verified CTRE passive sensor signatures may be promoted to `definite` when they are known to be device-defining for a canonical device identity
- CTRE control or broadcast-like traffic is retained as non-device traffic
- CTRE reference/supporting families are retained as supporting evidence and do not create new physical device rows by themselves
- CTRE non-device traffic no longer creates fake profile-dump device rows

Expected corrected outcomes for the investigated robot:

- real devices such as Talon FX, CANcoder, Pigeon, PDP remain visible as physical devices
- bogus rows such as `Unknown 4-0-63` no longer appear as physical devices
- non-device CTRE traffic remains visible in `nonDeviceTrafficFamilies[]`

## Controlled Trace Rules

## Purpose

Purpose: record the classification rules derived from August 12, 2026 connect/disconnect traces.

Device-defining signatures:

- CTRE Talon FX/Falcon motor controllers use canonical `4:2:<canId>` with `apiClass/apiIndex` `11/1` and `11/7`.
- CTRE CANcoder uses raw passive `4:5:<canId>` normalized to canonical `4:7:<canId>` with `apiClass/apiIndex` `11/3`.
- CTRE Pigeon 2 uses raw passive `4:21:<canId>` normalized to canonical `4:4:<canId>` with `apiClass/apiIndex` `11/4`.
- CTRE PDP uses canonical `4:8:<canId>` with `apiClass/apiIndex` `5/0`, `5/1`, `5/2`, `5/9`, and `5/13`.
- REV Spark MAX uses canonical `5:2:<canId>` with `apiClass/apiIndex` `46/0`, `46/1`, `46/2`, and `47/0`.

Supporting-only or non-device signatures:

- CTRE `apiClass 62` is diagnostic/enumeration traffic and must not create physical device rows.
- CTRE diagnostic pair rows observed in traces include `4:2:6` for Falcon `4:2:9`, `4:7:7` for CANcoder `4:7:18`, `4:4:9` for Pigeon `4:4:19`, and `4:8:8` for PDP `4:8:20`.
- CTRE broadcast/shared traffic such as `4:0:63` remains non-device shared-bus traffic.
- CTRE motor-controller reference traffic such as `apiClass/apiIndex` `7/3` remains supporting-only, even when the tuple's CAN ID matches a real motor.
- REV command/control traffic is not sufficient by itself to create a Spark MAX device row; observed REV status/heartbeat pages above are the device-defining evidence.

Interpretation limit:

- These rules classify identity contribution only; exact vendor payload field meanings remain hypotheses unless independently decoded and validated.

## Data Model Decisions

## Purpose

Purpose: record the design decisions chosen for this spec.

Chosen decisions:

- one shared classification pipeline owns both device and non-device outputs
- non-device traffic gets a stable top-level JSON contract
- `devices[]` is reserved strictly for physical canonical device identities
- `nonDeviceTrafficFamilies[]` is the stable top-level container for retained non-device traffic
- the design is vendor-agnostic, with CTRE as the first concrete implementation

## Failure Modes And Recovery

## Purpose

Purpose: define how the system should behave when classification is incomplete or ambiguous.

If traffic cannot yet be classified confidently:

- preserve it under `nonDeviceTrafficFamilies[]`
- mark `trafficKind = unknown_family`
- mark `identityDisposition = nonDevice`
- do not promote it into `devices[]`

If canonical device identity cannot be resolved:

- preserve raw hints
- keep the family visible for later inspection
- do not invent a fake physical device identity

This ensures the system is conservative:

- all traffic preserved
- uncertain traffic not discarded
- uncertain traffic not overclaimed as a device

## Backward Compatibility

## Purpose

Purpose: define how existing consumers should evolve safely.

Compatibility rules:

- existing physical-device outputs should remain additive where possible
- new `nonDeviceTrafficFamilies[]` is additive for machine consumers
- profile-dump `devices[]` becomes stricter, not broader
- if any consumer previously depended on fake device rows, that behavior is considered a bug, not a compatibility requirement

## Testing Strategy

## Purpose

Purpose: define the required automated and manual verification for this change.

Required automated tests:

- CTRE passive CANcoder raw alias normalizes to canonical type and contributes to device identity
- CTRE passive Pigeon raw alias normalizes to canonical type and contributes to device identity
- CTRE motor-controller traffic remains canonical motor identity
- CTRE shared-bus or broadcast-like traffic is retained but not promoted to device identity
- CTRE supporting/reference families are retained as supporting evidence and do not create new device identities by themselves
- profile dump excludes fake identities such as `Unknown 4-0-63`
- inventory dump includes `nonDeviceTrafficFamilies[]`
- REV behavior remains unchanged

Required fixture coverage:

- a mixed real-world bus containing:
  - REV Spark MAX traffic
  - CTRE Talon FX traffic
  - CTRE CANcoder traffic
  - CTRE Pigeon traffic
  - CTRE PDP traffic
  - CTRE non-device traffic that previously produced fake identities

Manual verification:

- compare corrected passive outputs against Phoenix Tuner X for CTRE devices
- verify the live UI shows real CTRE devices as device rows
- verify retained CTRE non-device traffic appears in the non-device traffic section rather than as fake devices

### TESTING_RESULTS:

August 12, 2026 validation completed against a real mixed REV + CTRE robot CAN bus and Phoenix Tuner X CTRE ground truth.

Automated verification that passed:

- `python -m unittest tools.passive_discovery_poc.tests.test_traffic_classification tools.can_nt.tests.test_can_dump_outputs tools.can_nt.tests.test_can_nt_bridge_device_maps tools.can_nt.tests.test_visibility_provider`
- `python -m py_compile tools/passive_discovery_poc/traffic_classification.py tools/passive_discovery_poc/tests/test_traffic_classification.py tools/can_nt/can_nt_bridge.py tools/can_nt/visibility_provider.py`

Live dump validation that passed:

- `py -m tools.can_nt.can_nt_bridge --dump-profile tools\can_nt\profile_check_2026-08-12.json --dump-profile-after 5 --dump-profile-include-unknown`
- `py -m tools.can_nt.can_nt_bridge --dump-api-inventory tools\can_nt\inventory_check_2026-08-12.json --dump-api-inventory-after 5`

Observed validated outcomes:

- canonical CTRE device identities were emitted correctly:
  - `4:2:9`
  - `4:4:19`
  - `4:7:18`
  - `4:8:20`
- the known extra REV Spark MAX remained visible as `5:2:7`
- previously observed fake CTRE device rows no longer appeared in `devices[]`, including:
  - `Unknown 4-0-63`
  - `KRAKEN 8`
  - `Pigeon 9`
  - `CANCoder 7`
  - `PDP 6`
- broadcast, control, and supporting/reference CTRE traffic was retained separately under `nonDeviceTrafficFamilies[]`
- live UI screenshots from August 12, 2026 showed the expected defined nodes only, with no fake CTRE unrecognized rows

## Rollout Plan

## Purpose

Purpose: define a safe incremental implementation order.

Recommended implementation order:

1. Introduce shared traffic-kind and identity-contribution model.
2. Route `can_nt_bridge` identity collection through normalized frame identity.
3. Add non-device traffic-family accumulation and stable JSON output.
4. Update profile dump and inventory dump to consume the shared model.
5. Update live visibility consumers.
6. Add regression fixtures and tests.
7. Revalidate against real CTRE hardware and Phoenix Tuner X.

## Tradeoffs

## Purpose

Purpose: make the design costs explicit.

Tradeoffs:

- keeping all traffic increases output complexity
- adding `nonDeviceTrafficFamilies[]` introduces a new machine-readable contract to maintain
- some existing debug habits that relied on fake device rows will need to shift to the new traffic-family view

These tradeoffs are acceptable because they avoid the worse failure mode:

- silently inventing fake physical device identities

## Future Extensions

## Purpose

Purpose: capture how this work can generalize later.

Future extensions:

- richer family signatures beyond raw `(apiClass, apiIndex)` pairs
- byte-fingerprint attachment to `nonDeviceTrafficFamilies[]`
- more vendor-specific canonicalization rules
- explicit confidence scoring for traffic-family classification
- UI drilldowns for non-device traffic families
