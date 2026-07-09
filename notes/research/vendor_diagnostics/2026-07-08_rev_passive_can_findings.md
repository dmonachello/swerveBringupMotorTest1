# REV Passive CAN Findings

## Purpose

Purpose: record the current REV findings from USBPcap and converted SocketCAN captures, with emphasis on passive CAN presence evidence and USB-to-CAN bridge behavior.

This note is a discovery artifact, not a complete protocol specification.

## Scope

This note covers:

- REV USB bridge observations from Hardware Client captures
- observed REV CAN frame families
- likely command families
- likely passive per-device status families
- current confidence and unresolved questions

This note does not cover:

- automating REV Hardware Client
- proving full USB transport semantics
- adding REV support to production tooling

## Cold-Start Limitation

`TESTING_RESULTS:` On the current setup, cold power-up alone did not reliably produce useful USB-relayed passive traffic from the directly connected Spark MAX.

`TESTING_RESULTS:` After opening and then closing REV Hardware Client, the same passive serial capture path began producing recurring per-device families.

`TESTING_RESULTS:` This strongly suggests the USB-connected Spark MAX enters a useful relay/streaming state only after a host-side startup/query sequence has been sent over USB.

## Source Artifacts

Primary captures discussed in this pass:

- `usbCap2_can.pcapng`
- `usbCap3_can.pcapng`
- `usbCap4_can.pcapng`
- `usbCap8_can.pcapng`
- converted SocketCAN outputs derived from the USB captures

Observed REV devices in the captures:

- `Spark MAX` CAN ID `25`
- `Spark MAX` CAN ID `7`

## High-Level Conclusions

1. REV Hardware Client sends explicit CAN-formatted traffic through the USB-connected REV device.
2. The USB-connected REV device behaves like a USB-to-CAN bridge or gateway.
3. Some observed REV CAN families are clearly controller-emitted commands or shared bus-control traffic.
4. Separate recurring per-device families appear to be device-emitted status traffic and are the best passive presence candidates.
5. We do not yet have proof of a dedicated CAN-level one-request/one-reply diagnostic family.
6. A request may still influence the next scheduled periodic status frame rather than producing a unique one-off reply.

## Confirmed USB Bridge Behavior

Observed USB `OUT` payloads include ASCII CAN records such as:

```text
T02052c8080000000000000000
T000502c0101
T020501998d578a04100008000
```

Interpretation:

- the host sends CAN-formatted messages over USB
- the directly connected REV device forwards or mediates those messages onto the CAN side
- this is an active gateway path, not a passive mirror

Observed pattern in `usbCap8`:

- a recurring host-originated 3-frame burst about every `30.95 ms`
- shared bus-control style traffic
- plus a selected-device command frame

## Confirmed REV Command Families

For `Spark MAX` device `25`, the following families are strongly supported as controller-emitted command traffic:

### `0x2050099`

- `manufacturer=5`
- REV motor-controller family
- `api_class=0`
- `api_index=2`
- likely duty-cycle command
- payload `word0` matched UI setpoint `0.148`

### `0x2050159`

- `api_class=0`
- `api_index=5`
- likely voltage command
- payload `word0` matched UI setpoints such as `6.139` and `-6.139`

### `0x2050199`

- `api_class=0`
- `api_index=6`
- likely current command
- payload `word0` matched UI setpoint `20.059`

Interpretation:

- these families are not valid passive presence evidence
- they are controller-emitted traffic sent toward a device

## Shared REV Bus-Control Families

In the two-Spark idle capture `usbCap8`, the following shared families were observed:

- `0x000502c0`
- `0x02052c80`

Observed properties:

- shared scope rather than a concrete device ID
- repeated regularly during idle Hardware Client activity
- visible as host-originated USB `OUT` traffic

Interpretation:

- likely shared poll, keepalive, bridge-control, or discovery-control traffic
- not valid passive presence evidence for a specific Spark MAX

## Per-Device REV Status Families

## Single Powered Spark MAX Isolation

`TESTING_RESULTS:` Additional isolation runs were performed with only one Spark MAX powered via the USB cable and no other REV device powered.

`TESTING_RESULTS:` Under that condition, the recurring per-device families below are much stronger evidence of device-emitted traffic rather than false positives from another active Spark talking to the target CAN ID.

## Spark MAX CAN ID 25

Recurring per-device families observed for device `25`:

- `0x205b819` about `50 Hz`
- `0x205b859` about `4 Hz`
- `0x205bc19` about `1 Hz`

Single-powered interpretation for device `25`:

- `(5,2,25,46,0)` likely primary per-device status
- `(5,2,25,46,1)` likely secondary per-device status
- `(5,2,25,47,0)` likely heartbeat or housekeeping

## Spark MAX CAN ID 7

Recurring per-device families observed for device `7` in `usbCap8`:

- `0x205b807`
- `0x205b887`
- `0x205b847`
- `0x205bc07`

Additional single-powered observation for device `7`:

- `(5,2,7,46,0)` about `51 Hz`
- `(5,2,7,46,1)` about `4.1 Hz`
- `(5,2,7,46,2)` about `51 Hz`
- `(5,2,7,47,0)` about `1.0 Hz`

Single-powered interpretation for device `7`:

- `(5,2,7,46,0)` likely primary per-device status
- `(5,2,7,46,1)` likely secondary per-device status
- `(5,2,7,46,2)` likely additional high-rate per-device status
- `(5,2,7,47,0)` likely heartbeat or housekeeping

Observed pairing by device ID:

- device `25`
  - `0x205b819`
  - `0x205b899`
  - `0x205b859`
  - `0x205bc19`
- device `7`
  - `0x205b807`
  - `0x205b887`
  - `0x205b847`
  - `0x205bc07`

Interpretation:

- these replicated families are strong evidence of per-device recurring status traffic
- they are much better passive presence candidates than command or shared bus-control frames

## Current Role Classification

Best current first-pass classification:

- `b8xx` families
  - likely `primary per-device periodic status`
- `b84x` families
  - likely `secondary slower per-device status`
- `bc0x` families
  - likely `very-low-rate heartbeat or housekeeping`

More explicit API-family interpretation from the single-powered Spark runs:

- `api_class=46, api_index=0`
  - strong candidate for primary per-device status
- `api_class=46, api_index=1`
  - strong candidate for secondary per-device status
- `api_class=46, api_index=2`
  - likely additional primary or high-rate per-device status
- `api_class=47, api_index=0`
  - strongest current heartbeat or housekeeping candidate

For current passive presence purposes, the minimum useful set appears to be:

- one `b8xx` family for the device
- plus either:
  - one `b84x` family
  - or one `bc0x` family

## What the Second Spark MAX Experiment Proved

The second Spark MAX on CAN ID `7` was useful because it showed:

- per-device families replicate when a second device is present
- the low device-ID bits change with the physical device ID
- shared `device_id=0` traffic remains separate from per-device traffic

Most important result:

- this experiment did not reveal an obvious one-shot "announcement packet"
- it did strengthen the case that recurring per-device status traffic is the passive presence surface we actually want

Single-powered follow-up result:

- the same conclusion held even when only one Spark MAX was powered from USB
- that substantially reduces the risk that these recurring families are false positives caused by another active Spark talking to the target CAN ID

## Command-Followed-by-Status-Change Observations

Observed behavior in command captures:

- command family changes first
- then existing periodic `b8xx` status families change payload values shortly after
- the status family already existed before the command and continued after the command

Interpretation:

- these are not currently proven to be dedicated one-off replies
- they are better described as periodic status surfaces that reflect changed device state

Important caveat:

- a request may still be answered through the next scheduled status emission
- periodic status traffic can still be the practical response surface even without a unique reply family

## What We Do Not Yet Know

- the exact semantic meaning of most payload bytes in `b8xx`, `b84x`, and `bc0x`
- whether richer `b8xx` families appear only after deeper client interaction
- whether there exists any dedicated REV CAN reply family separate from the periodic status families
- whether other REV device classes such as `Spark Flex`, `PDH`, or `PH` use the same family structure

## Current Safe Judgment

What is currently strong:

- host-originated REV command families are identifiable
- shared REV bus-control families are identifiable
- recurring per-device REV status families are identifiable
- passive Spark MAX presence can likely be inferred from recurring per-device `b8xx/b84x/bc0x` traffic

What is currently still inference:

- exact byte-level field meanings
- exact request/response semantics for richer diagnostic interaction
- whether all richer periodic status families are always-on

## Recommended Next Steps

1. Run single-device disappearance and reappearance tests to promote candidate status families from likely to validated device-emitted evidence.
2. Capture additional idle sessions with multiple REV devices and no active motor commands.
3. Compare selected versus unselected device behavior in Hardware Client.
4. Add other REV device classes when available to test whether the same family structure generalizes.
5. Preserve representative raw USB and SocketCAN fixtures for future family-level regression analysis.
