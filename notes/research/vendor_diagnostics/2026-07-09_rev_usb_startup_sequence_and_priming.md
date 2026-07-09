# REV USB Startup Sequence And Priming

## Purpose

Purpose: record the first clear evidence that REV Hardware Client actively sends USB serial traffic which appears to prime a USB-connected Spark MAX into a useful gateway/relay state.

This note also defines the next isolation steps needed to determine the minimum startup sequence required for the passive-discovery PoC to work cold after power-up.

## Source Artifacts

- Capture:
  - `tools/vendor_diag/revStart1.pcapng`
- Controlled behavioral observations:
  - cold power-up plus two passive runs produced no devices/families
  - opening and closing REV Hardware Client caused the same passive run to begin producing device/family evidence
- Related notes:
  - `notes/research/vendor_diagnostics/2026-07-07_rev_usb_gateway_attack_plan.md`
  - `notes/research/vendor_diagnostics/2026-07-08_rev_passive_can_findings.md`

## Controlled Behavior Conclusion

Current strongest conclusion:

- On this setup, REV Hardware Client priming appears required after cold power-up.
- The most likely explanation is that the client sends one or more host-to-device USB messages which cause the Spark MAX USB interface to begin relaying or exposing traffic that our passive serial reader can consume.

This is no longer a weak guess. It is supported by:

- two cold passive runs after power-cycle with no data
- one run immediately after opening and closing REV Hardware Client with useful data
- USBPcap evidence showing explicit host-to-device traffic to the Spark-adjacent USB serial device

## Relevant USB Device

From `revStart1.pcapng`:

- `usb.device_address == 16`
- `idVendor = 0x0483`
- `idProduct = 0xa30e`

This matches the generic Windows serial device identity previously observed for the Spark MAX USB connection.

## Startup Transition Point

The key transition begins at about `7.176 s` in the capture.

Observed serial-port style setup traffic:

- `SET CONTROL LINE STATE`
- repeated `GET LINE CODING`
- `SET LINE CODING`

Observed line-coding payload:

```text
80250000000008
```

Interpreted as little-endian baud-rate setup:

- `0x2580 = 9600`

This means the host is not just reading from the device. It is opening/configuring the serial interface first.

## First Observed Host-To-Device Burst

Immediately after the line-state and line-coding setup, the host begins sending bulk `OUT` traffic to the device.

The first observed ASCII payloads include:

```text
T08041754814000000000000f76
T15042d138feffffafff048001
T150430d38f1df03c0fe030005
S8
T0205b819800007c0600188000
O
T02042c4980000006000000000
T0205b81980000010000188000
```

## Interpretation

These observations strongly support all of the following:

1. REV Hardware Client is not operating as a passive monitor.
2. It actively writes USB serial traffic to the directly connected Spark MAX.
3. The startup path is a sequence, not a single obvious packet.
4. The sequence includes both:
   - short command-like tokens such as `S8` and `O`
   - longer `T...` ASCII records that look CAN-frame-like
5. The currently working passive `--live-rev-serial` mode is probably benefitting from device state established by that sequence.

## Current Best Hypotheses

Most likely possibilities:

- `S8` selects or configures a serial/CAN mode.
- `O` opens or enables streaming.
- one or more `T...` messages request, trigger, or maintain relay behavior.
- the full sequence, not one isolated token, may be required.

Less likely now:

- firmware-version mismatch
- wrong COM port
- random timing
- spontaneous downstream relay enablement with no host-side cause

## What This Means For The PoC

Current implication for `--live-rev-serial`:

- the source is not yet a reliable cold-start discovery mode
- the USB-connected Spark appears to need a host-side initialization/query sequence first
- the current passive serial reader is only seeing the post-primed steady state

That means the next useful implementation target is not more COM-port work. It is:

- isolating the minimal host-to-device startup sequence
- then deciding whether to implement that as a dedicated REV USB enrichment/query plugin

## Minimum Sequence Isolation Plan

## Goal

Goal: determine the smallest host-to-device sequence that makes the Spark MAX begin exposing useful downstream traffic after cold power-up.

## Baseline

For every experiment:

- power cycle the directly USB-connected Spark MAX
- keep the downstream CAN bus intact
- do not open REV Hardware Client unless the step explicitly requires it
- run the passive PoC after each attempt:

```text
python tools/passive_discovery_poc/passive_discovery.py --live-rev-serial --duration 15.0 --full-dump
```

Success condition:

- the passive run shows at least:
  - Spark `25`
  - Spark `7`
  - and some downstream CTRE family evidence

Failure condition:

- the passive run shows no devices/families

## Experiment Order

### Experiment 1: Port Open Only

Objective:

- determine whether merely opening and configuring the serial port is enough

Action:

- reproduce only:
  - control line state setup
  - line coding setup
- do not send `S8`
- do not send `O`
- do not send any `T...` payloads

Interpretation:

- if this works, priming is mostly a serial-port state transition
- if not, at least one later command is required

### Experiment 2: `S8` Only

Objective:

- determine whether `S8` alone enables the useful state

Action:

- open/configure serial
- send only `S8`

Interpretation:

- if this works, `S8` is the leading trigger candidate

### Experiment 3: `O` Only

Objective:

- determine whether `O` alone enables the useful state

Action:

- open/configure serial
- send only `O`

Interpretation:

- if this works, `O` is the leading trigger candidate

### Experiment 4: `S8` Then `O`

Objective:

- test whether the short command pair is sufficient without the `T...` traffic

Action:

- open/configure serial
- send `S8`
- send `O`

Interpretation:

- if this works, the longer `T...` traffic may be optional or only used later

### Experiment 5: First `T...` Message Only

Objective:

- determine whether a CAN-like request is the true trigger

Action:

- open/configure serial
- send only the first observed `T...` payload

Interpretation:

- if this works, the key trigger is likely a protocol-level query rather than a generic open token

### Experiment 6: `S8`, `O`, And First `T...` Request

Objective:

- test the smallest plausible mixed sequence

Action:

- open/configure serial
- send `S8`
- send `O`
- send the first relevant `T...` request

Interpretation:

- if this works while the simpler cases do not, the minimal sequence is likely a combination of mode-open plus request traffic

### Experiment 7: Replay Full Early Burst

Objective:

- prove the captured startup burst is causally sufficient

Action:

- replay the earliest host-to-device burst exactly as captured

Interpretation:

- if this works reliably, we have a high-confidence bridge from passive observation to active reproduction

## Immediate Engineering Recommendations

1. Add source diagnostics to the REV serial path:
   - resolved port
   - raw bytes received
   - parsed record count
   - normalized frame count
2. Preserve the exact first-burst payload list in code comments or a fixture when building the eventual probe.
3. Implement the first reproducer as a separate research tool, not inside the main passive PoC path.

Suggested first tool:

- `tools/vendor_diag/rev_usb_prime_probe.py`

## Current Confidence

High confidence:

- REV Hardware Client sends USB host-to-device setup and command traffic
- cold-start passive success is state-dependent on this setup
- the startup path includes both serial-port configuration and explicit payload writes

Moderate confidence:

- one of `S8`, `O`, or the first `T...` request is part of the enabling trigger

Not yet proven:

- the true minimum required sequence
- whether the primed state persists until power loss, USB disconnect, or some timeout
- whether all Spark MAX / Spark Flex firmware combinations behave the same way
