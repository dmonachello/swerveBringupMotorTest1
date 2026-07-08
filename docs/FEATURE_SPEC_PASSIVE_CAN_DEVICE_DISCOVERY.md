# Feature Spec Passive CAN Device Discovery

## Purpose

Define a vendor-agnostic passive discovery scheme that infers device presence from recurring CAN traffic without transmitting any CAN frames.

## Status

`RESEARCH_ONLY`

## Problem

The current passive discovery idea has a critical flaw: a packet that references a device ID is not automatically proof that the device is present on the bus.

Examples:

- A roboRIO or vendor client can emit command packets targeted at a device.
- A bridge or client can emit poll packets about a device.
- Shared bus-control traffic can mention no specific device or can use a generic device ID.

Those packets do not prove that the device itself is powered, alive, or transmitting.

Passive discovery therefore needs a stricter rule:

- Only packet families that are strongly believed to be emitted by the device itself may count as passive presence evidence.

## Scope

This spec covers:

- passive discovery from direct CAN sniffer captures
- passive discovery from REV USB bridge traffic after conversion into CAN frames
- family-level classification of recurring traffic
- device presence confidence derived from passive evidence

This spec does not cover:

- active vendor polling
- CTRE HTTP query flows
- commands transmitted onto the CAN bus by this project
- full semantic decoding of every payload byte

## Hard Rules

- The production discovery path must remain passive on CAN.
- A frame family must not count as passive presence evidence unless it is classified as likely device-emitted traffic.
- Command-like traffic must never be used as passive proof of device presence.
- Shared bus-control traffic must never be used as proof of a specific device presence.
- The same passive scheme must work on:
  - direct CAN sniffer captures
  - REV USB bridge captures converted into CAN frames

## Observer Inputs

## Purpose

Normalize all passive inputs into a shared frame record before classification.

Supported inputs:

- direct CAN sniffer frames
- REV USB bridge captures converted to SocketCAN `pcapng`

Normalized record fields:

- `timestamp`
- `canId`
- `dlc`
- `data`
- decoded FRC extended-ID fields when applicable:
  - `manufacturer`
  - `deviceType`
  - `apiClass`
  - `apiIndex`
  - `deviceId`
- `observerSource`

## Core Concept

## Purpose

Discover devices from recurring frame families, not from single packets.

A `frame family` is keyed by:

- `manufacturer`
- `deviceType`
- `deviceId`
- `apiClass`
- `apiIndex`

Passive presence is inferred from the behavior of a frame family over time.

The key question is not:

- "Does this frame mention device ID N?"

The key question is:

- "Is this family likely emitted by device N itself, and does it recur as expected?"

## Packet Purpose Classes

## Purpose

Classify families by likely purpose before using them for presence.

### `DEVICE_EMITTED_PRIMARY_STATUS`

High-rate per-device recurring traffic.

Typical characteristics:

- roughly `40-120 Hz`
- present during idle steady state
- device-specific
- persists across multiple seconds
- often changes payload values continuously or stepwise

Use:

- valid passive presence evidence
- strong passive presence evidence

### `DEVICE_EMITTED_SECONDARY_STATUS`

Lower-rate per-device recurring traffic.

Typical characteristics:

- roughly `3-20 Hz`
- present during idle steady state
- device-specific

Use:

- valid passive presence evidence
- companion evidence that raises confidence

### `DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING`

Very stable, recurring per-device traffic.

Typical characteristics:

- often low-rate
- payload may stay constant for long periods
- still repeats steadily while the device is present

Use:

- valid passive presence evidence
- especially useful when richer status families are absent

### `CONTROLLER_EMITTED_COMMAND`

Traffic likely sent by a controller or client to drive device behavior.

Typical characteristics:

- changes with operator command changes
- lower-rate than primary status
- tied to control mode or setpoint changes

Use:

- not valid passive presence evidence

### `CONTROLLER_EMITTED_POLL`

Traffic likely sent by a controller or client to request information.

Typical characteristics:

- often shared or low-rate
- may precede state replies
- may exist even if the device does not respond

Use:

- not valid passive presence evidence

### `SHARED_BUS_CONTROL`

Traffic not attributable to a specific device presence.

Typical characteristics:

- may use generic or shared device IDs such as `deviceId=0`
- tied to refresh, discovery, or bus-level coordination

Use:

- not valid passive presence evidence

### `UNKNOWN`

Traffic not yet classified confidently.

Use:

- must not count as presence evidence until promoted by stronger observations

## Family Metrics

## Purpose

Use repeatable measurements to classify frame families.

For every frame family, compute:

- `count`
- `rateHz`
- `interarrivalMeanSec`
- `interarrivalStdDevSec`
- `uniquePayloadCount`
- `payloadTransitionCount`
- `firstSeen`
- `lastSeen`

Derived helper signals:

- `isRecurring`
- `isStableCadence`
- `isHighRate`
- `isLowRate`
- `isMostlyConstantPayload`
- `isDeviceSpecific`
- `isSharedBusScoped`

## Classification Heuristics

## Purpose

Provide a first-pass behavior-based classifier before vendor-specific seed rules are applied.

Promote a family toward `DEVICE_EMITTED_PRIMARY_STATUS` when:

- it is device-specific
- it recurs across most of the capture window
- its cadence is stable
- its rate is roughly `40-120 Hz`
- it is present even in idle non-commanded captures

Promote a family toward `DEVICE_EMITTED_SECONDARY_STATUS` when:

- it is device-specific
- it recurs steadily
- its rate is roughly `3-20 Hz`
- it appears during idle non-commanded captures

Promote a family toward `DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING` when:

- it is device-specific
- it recurs steadily
- its payload is constant or near-constant for long periods

Promote a family toward `CONTROLLER_EMITTED_COMMAND` when:

- it appears only for selected devices or active control scenarios
- it changes with control type or setpoint changes
- it carries values that match operator-entered commands

Promote a family toward `SHARED_BUS_CONTROL` when:

- it is shared across devices
- it uses a generic device scope such as `deviceId=0`
- it appears tied to client refresh or bus-level activity

## Presence Evidence Rules

## Purpose

Define which families may count toward passive device presence.

A frame family may count toward passive presence only if it is classified as one of:

- `DEVICE_EMITTED_PRIMARY_STATUS`
- `DEVICE_EMITTED_SECONDARY_STATUS`
- `DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING`

A frame family must not count toward passive presence if it is classified as one of:

- `CONTROLLER_EMITTED_COMMAND`
- `CONTROLLER_EMITTED_POLL`
- `SHARED_BUS_CONTROL`
- `UNKNOWN`

## Presence Confidence

## Purpose

Produce a stable confidence score from passive evidence only.

### `HIGH`

Observed recently:

- at least one `DEVICE_EMITTED_PRIMARY_STATUS` family
- and at least one companion `DEVICE_EMITTED_SECONDARY_STATUS` or `DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING` family

### `MEDIUM`

Observed recently:

- one strong recurring device-emitted family

### `LOW`

Observed recently:

- weak or incomplete device-emitted evidence only

### `NONE`

Observed recently:

- no qualifying device-emitted families

## Seed Observations From 2026-07-07

## Purpose

Record the current high-value observations that seed the first-pass classifier.

These are research observations, not final wire contracts.

### REV Motor Controller Device 25

Observed likely `CONTROLLER_EMITTED_COMMAND` families:

- `0x2050099`
  - `apiClass=0`, `apiIndex=2`
  - duty-cycle command family
  - payload bytes `0..3` match commanded duty-cycle float32
- `0x2050159`
  - `apiClass=0`, `apiIndex=5`
  - voltage command family
  - payload bytes `0..3` match commanded voltage float32
- `0x2050199`
  - `apiClass=0`, `apiIndex=6`
  - current command family
  - payload bytes `0..3` match commanded current float32

Observed likely `DEVICE_EMITTED_PRIMARY_STATUS` families:

- `0x205b819`
- `0x205b899`
- `0x205b8d9`
- `0x205b919`
- `0x205b959`
- `0x205b999`

Observed likely `DEVICE_EMITTED_SECONDARY_STATUS` family:

- `0x205b859`

Observed likely `DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING` family:

- `0x205bc19`

Observed likely `SHARED_BUS_CONTROL` families:

- `0x502c0`
- `0x2052c80`

### REV Motor Controller Device 7

In an idle non-commanded two-device capture, device `7` showed replicated per-device families:

- `0x205b807`
- `0x205b887`
- `0x205b847`
- `0x205bc07`

These strongly support the hypothesis that:

- `b8xx` families are per-device periodic status
- `b84x` families are slower per-device status
- `bc0x` families are very slow per-device housekeeping or heartbeat

### CTRE Talon FX Device 9

Observed likely `DEVICE_EMITTED_PRIMARY_STATUS` families:

- `0x2042c49` at roughly `100 Hz`
- `0x2042dc9` at roughly `50 Hz`

Observed likely `DEVICE_EMITTED_SECONDARY_STATUS` or `HEARTBEAT_HOUSEKEEPING` families:

- `0x2042d49`
- `0x2042d89`
- `0x2042e09`
- `0x2042e49`
- `0x2042e89`
- `0x2042ec9`
- `0x2043049`
- `0x2044749`
- `0x2046bc9`

### CTRE Pigeon 2 Device 19

Observed likely `DEVICE_EMITTED_PRIMARY_STATUS` families:

- `0x15042d13` at roughly `100 Hz`
- `0x150430d3` at roughly `50 Hz`

Observed likely `DEVICE_EMITTED_SECONDARY_STATUS` families:

- `0x15043113`
- `0x150431d3`
- `0x15043213`

Observed likely `DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING` families:

- `0x15043193`
- `0x15043353`
- `0x15044753`
- `0x15046bd3`

### CTRE PDP Device 20

Observed likely `DEVICE_EMITTED_PRIMARY_STATUS` families:

- `0x8041754`
- `0x8041414`
- `0x8041454`
- `0x8041494`
- `0x8041654`

## Discovery Algorithm

## Purpose

Describe the first-pass passive discovery pipeline.

1. Normalize all observed frames into the common record format.
2. Decode FRC extended-ID fields where applicable.
3. Group frames by family:
   - `(manufacturer, deviceType, deviceId, apiClass, apiIndex)`
4. Compute family metrics.
5. Apply behavior-based classification heuristics.
6. Apply vendor-specific seed rules where confidence is already strong.
7. Aggregate device-emitted families by:
   - `(manufacturer, deviceType, deviceId)`
8. Produce passive presence confidence from valid device-emitted families only.

## Output Schema

## Purpose

Keep discovery outputs machine-readable and source-agnostic.

Example:

```json
{
  "deviceKey": {
    "manufacturer": 5,
    "deviceType": 2,
    "deviceId": 25
  },
  "observerSource": "can_sniffer",
  "presenceConfidence": "high",
  "families": [
    {
      "apiClass": 46,
      "apiIndex": 0,
      "role": "device_emitted_primary_status",
      "rateHz": 50.1,
      "recent": true
    },
    {
      "apiClass": 46,
      "apiIndex": 1,
      "role": "device_emitted_secondary_status",
      "rateHz": 4.1,
      "recent": true
    }
  ],
  "notes": [
    "No active polling used.",
    "Presence based only on likely device-emitted families."
  ]
}
```

## Validation Plan

## Purpose

Promote candidate families from plausible to trusted passive presence evidence.

Required experiments:

1. Idle steady-state capture with devices powered and present.
2. Single-device removal capture:
   - power off or unplug one target device only
   - confirm candidate per-device families disappear
3. Single-device return capture:
   - restore that device
   - confirm the same families reappear
4. Multi-device same-vendor capture:
   - confirm family replication by device ID
5. Commanded versus non-commanded capture:
   - separate command families from device-emitted status families

Promotion rule:

- A family may be promoted to trusted passive presence evidence only after disappearance and reappearance behavior is observed for the corresponding physical device.

## Tradeoffs

## Purpose

Capture the main limits of passive discovery.

- Passive discovery can infer presence, but not exact electrical root cause.
- Stable recurring traffic is stronger than single packets, but it still depends on enough observation time.
- Some richer telemetry families may depend on vendor-client interaction history.
- REV USB bridge captures are useful research inputs, but production logic should operate on normalized CAN frames rather than on USB transport details.

## Future Extensions

## Purpose

List next steps after the first-pass classifier exists.

- add family-purpose confidence scores
- learn richer payload semantics for trusted device-emitted families
- combine passive presence with CTRE active diagnostic confirmation when available
- surface family disappearance and cadence degradation as health clues
- update the Wireshark dissector conservatively with confirmed command-family and family-role hints
