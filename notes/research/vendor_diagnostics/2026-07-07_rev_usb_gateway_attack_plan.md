# REV USB Gateway Diagnostics Attack Plan

## Purpose

Purpose: define a staged investigation plan for discovering what diagnostic data REV Hardware Client can obtain through its USB-connected device/gateway path.

This plan is discovery work. It does not approve adding REV USB automation to the bringup tool yet.

The first job is to understand the transport, safety properties, data fields, and device coverage.

## Big Picture

CTRE gave us a network diagnostic path through Phoenix Tuner and the roboRIO-hosted Diagnostic Server.

REV appears to use a different pattern:

- PC runs REV Hardware Client.
- PC connects by USB to one REV device.
- The directly connected REV device can expose information about other REV devices on the robot.

That USB connection is the primary feed for this investigation.

Passive CAN capture is only a comparison tool in this plan. It helps determine whether REV's USB gateway activity causes CAN-side traffic, but it is not the REV diagnostic feed being designed here.

That means REV may provide a useful vendor diagnostic backchannel, but it must be treated as its own transport and safety case.

The goal is to turn the REV path into an observed inventory:

- what devices can be discovered
- what fields can be read
- what commands/actions exist
- what is read-only
- what is mutating
- whether the gateway transmits on CAN
- which fields map cleanly into the canonical troubleshooting evidence model

## Hard Safety Rules

- Do not add REV USB support to the bringup tool until the transport is understood.
- Do not automate any REV action until it has a safety class.
- Do not assume a Hardware Client query is passive on the robot CAN bus.
- Treat the USB connection as the authoritative acquisition path for REV vendor diagnostics during this research.
- Preserve raw captures and raw field names before mapping to canonical diagnostics.
- Treat vendor firmware and Hardware Client version as part of the inventory.
- If a REV workflow writes configuration, changes ID, updates firmware, runs a motor, or clears sticky faults, classify it as mutating or visible-side-effect.

## Core Questions

The investigation must answer these before implementation:

- What USB class is used by the connected REV device?
- Is the protocol serial-like, HID, vendor-specific USB, or mediated by a local service?
- Does REV Hardware Client enumerate downstream REV devices through the USB-connected device?
- Does downstream enumeration cause CAN transmissions?
- What inventory, version, fault, warning, and live signal data is exposed?
- Can the data be requested read-only?
- Are response schemas stable enough to inventory and diff?
- Can the same workflow cover Spark MAX, Spark Flex, PDH, PH, and other REV devices?

## Required Tools

- REV Hardware Client installed on the Windows PC.
- Wireshark with USBPcap installed.
- Device Manager.
- PowerShell.
- Optional serial monitor if the device enumerates as a COM port.
- Optional passive CANable capture running at the same time to detect whether USB actions cause CAN traffic changes.

## Stage 0: Setup Snapshot

Purpose: record the exact environment before captures.

Record:

- REV Hardware Client version.
- Windows version.
- Connected REV device model.
- Connected REV device firmware version.
- Robot power state.
- Whether the connected REV device is also attached to the robot CAN bus.
- Which other REV devices are expected on the robot.
- Whether CANable passive capture is running.

Output artifact:

- `notes/research/vendor_diagnostics/<date>_rev_setup_snapshot.md`

Minimum content:

- device list expected from robot profile
- physical USB attachment point
- REV Hardware Client version screenshot or text
- Device Manager device name and USB class impression

## Stage 1: Transport Identification

Purpose: determine what communication path REV Hardware Client uses.

Steps:

1. Plug in one REV device over USB.
2. Open Device Manager.
3. Record whether the device appears under:
   - `Ports (COM & LPT)`
   - `Human Interface Devices`
   - `Universal Serial Bus devices`
   - `libusb` or vendor-specific device classes
4. Start REV Hardware Client.
5. Check whether any local helper process or localhost service appears.

PowerShell checks:

```powershell
Get-PnpDevice | Where-Object { $_.FriendlyName -match 'REV|SPARK|USB|Serial|COM' }
Get-NetTCPConnection | Where-Object { $_.OwningProcess -ne 0 } | Sort-Object LocalPort
Get-Process | Where-Object { $_.ProcessName -match 'REV|Hardware|Client' }
```

Expected result:

- one transport classification from this set: `usb_serial`, `usb_hid`, `usb_vendor_specific`, `localhost_service`, `unknown`

Output artifact:

- add transport findings to setup snapshot

## Stage 2: Minimal Enumeration Capture

Purpose: capture the smallest workflow that enumerates devices.

Primary feed:

- REV USB connection between the PC and the directly connected REV device

Capture setup:

- Start USBPcap capture before launching or refreshing REV Hardware Client.
- If possible, keep only one REV USB device attached.
- Start a simultaneous passive CAN capture if CANable is available.
- Start screen recording or take notes with timestamps for each UI action.

Workflow:

1. Start capture.
2. Launch REV Hardware Client.
3. Let the device list populate.
4. Select the USB-connected REV device.
5. Stop capture.

Artifacts:

- USB capture: `notes/research/vendor_diagnostics/captures/<date>_rev_minimal_enumeration_usb.pcapng`
- Optional CAN capture: `notes/research/vendor_diagnostics/captures/<date>_rev_minimal_enumeration_can.pcapng`
- Notes: `notes/research/vendor_diagnostics/<date>_rev_minimal_enumeration_notes.md`

Questions to answer:

- What packets appear when the device list populates?
- Is the payload text-like or binary?
- Are downstream devices visible?
- Did passive CAN traffic change during enumeration?

## Stage 3: Downstream Device Discovery

Purpose: prove whether the USB-connected REV device acts as a gateway to other REV devices.

Primary feed:

- REV USB traffic captured while Hardware Client enumerates downstream devices through the directly connected REV device

Workflow:

1. Connect the USB cable to one known REV device.
2. Keep at least one other REV CAN device connected on the robot.
3. Capture REV Hardware Client refresh/discovery.
4. Record the visible device list.
5. Disconnect one downstream REV device from CAN or power only if the robot is safe and disabled.
6. Refresh discovery again.
7. Reconnect and refresh.

Evidence to collect:

- before/after visible device list
- USB capture
- optional passive CAN capture
- operator notes on physical state

Pass condition:

- the visible list changes in a way that matches the downstream physical change

Fail condition:

- Hardware Client only reports the directly USB-connected device

Important interpretation:

- If discovery changes passive CAN traffic, the gateway path is not passive.
- If discovery does not change passive CAN traffic, it still may use existing device status traffic or vendor-private behavior; do not assume passivity without more evidence.

## Stage 4: Device Detail Capture

Purpose: discover per-device identity, faults, warnings, and live status fields.

Primary feed:

- REV USB traffic captured while Hardware Client opens each device detail surface

Run one capture per device family.

Target families:

- Spark MAX
- Spark Flex
- PDH
- PH
- any other REV device currently available on the robot

Workflow for each device:

1. Start USBPcap capture.
2. Select exactly one device in REV Hardware Client.
3. Open its main detail page.
4. Open faults/warnings/status sections.
5. Open firmware/version page.
6. Stop capture.

Record:

- UI page names visited
- visible fields and values
- whether fields are static or live-updating
- whether any field has units
- whether faults and sticky faults are separate

Output artifact:

- one notes file per device family
- examples: `<date>_rev_spark_max_detail_inventory.md`, `<date>_rev_spark_flex_detail_inventory.md`, `<date>_rev_pdh_detail_inventory.md`, `<date>_rev_ph_detail_inventory.md`

## Stage 5: Live Signal Behavior

Purpose: determine whether REV exposes live status useful for troubleshooting.

Candidate fields:

- supply voltage
- output duty cycle
- applied output
- motor current
- temperature
- encoder position
- encoder velocity
- fault bits
- warning bits
- sticky fault bits
- firmware version
- device ID
- device name
- CAN status or heartbeat status

Workflow:

1. Capture an idle live status page for 10 seconds.
2. If safe, use robot-owned bringup controls to command a small motor output.
3. Capture live status while output changes.
4. Stop the robot-owned command.
5. Capture the return to idle.

Safety rule:

- REV Hardware Client must not be used to command motor output during this investigation unless explicitly approved.

Expected result:

- identify which fields update live
- determine whether live fields can distinguish powered-but-disabled, enabled-and-commanded, CAN-missing, faulted, and stale/no-update states

## Stage 6: Mutation Boundary Capture

Purpose: classify which workflows are unsafe or mutating without executing dangerous changes.

Do not perform the mutating action unless it is harmless and explicitly approved.

Inspect or capture navigation to screens for:

- change CAN ID
- set device name
- burn/save configuration
- restore defaults
- clear sticky faults
- firmware update
- motor test/run

Classify each discovered action:

- `read_only`
- `read_like_but_stateful`
- `visible_side_effect`
- `configuration_mutating`
- `motion_mutating`
- `firmware_mutating`
- `unsafe_unknown`

Output artifact:

- add action safety classification to the REV inventory JSON

## Stage 7: Protocol Extraction

Purpose: turn captures into a first-pass protocol inventory.

For USB serial:

- record baud rate if discoverable
- record request/response frame boundaries
- record text commands if visible
- record checksums/framing if binary

For HID or vendor-specific USB:

- record endpoint numbers
- record transfer directions
- group transfers by UI action timestamp
- identify repeated polling patterns
- identify stable request and response sizes

For localhost service:

- capture HTTP/WebSocket/local TCP traffic separately
- inventory endpoints like the CTRE work

Output artifact:

- `notes/research/vendor_diagnostics/<date>_rev_usb_gateway_first_pass_inventory.json`
- `notes/research/vendor_diagnostics/<date>_rev_usb_gateway_first_pass_inventory.md`

## Stage 8: Raw Field Inventory

Purpose: create the REV equivalent of the CTRE field catalog.

Required JSON shape:

```json
{
  "vendor": "REV",
  "transport": "usb_gateway",
  "hardware_client_version": "",
  "capture_date": "",
  "source_artifacts": [],
  "observed_device_families": [],
  "observed_actions": [],
  "observed_fields": [],
  "known_gaps": []
}
```

Each observed field should include:

- `deviceFamily`
- `fieldName`
- `fieldPath`
- `fieldType`
- `units`
- `exampleValue`
- `observedEnumValues`
- `sourceScreen`
- `updateBehavior`
- `candidateCanonicalField`
- `confidence`

## Stage 9: Canonical Mapping

Purpose: map stable REV fields into the troubleshooting evidence model only after raw inventory exists.

High-priority mappings:

- firmware and identity to `device.identity.*`
- visible/present state to `device.presence.*`
- voltage/current to `device.power.*` and electrical evidence
- fault and warning bits to `device.runtime.faulted` and `device.runtime.warnings`
- CAN status fields, if present, to `device.can.*`
- LED or indicator-equivalent fields to `device.indicator.*`

Mapping rule:

- every mapped field must retain raw source path and capture provenance

## Stage 10: Integration Decision Gate

Purpose: decide whether REV USB should become part of the tool, remain a manual research workflow, or be deferred.

Proceed to implementation only if:

- transport is understood enough to parse repeatably
- read-only status can be separated from mutating actions
- useful fields are exposed for REV motor controllers
- behavior is stable across at least two capture sessions
- safety implications of gateway CAN traffic are known

Do not implement if:

- the protocol cannot be parsed without fragile timing assumptions
- read-only and mutating actions cannot be separated
- the Hardware Client path requires privileged driver behavior that cannot be packaged cleanly
- useful status is already better obtained through robot-side REVLib APIs

## Preferred First Implementation Shape

If REV USB integration passes the gate, the first implementation should be a standalone probe, not UI integration.

Suggested path:

- `tools/vendor_diag/rev_usb_probe.py`

Initial behavior:

- enumerate devices
- print raw JSON-like inventory if available
- write inventory artifact to disk
- no config writes
- no firmware actions
- no motor control

Only after that should the shared troubleshooting evidence layer consume selected fields.

## Parallel Robot-Side Fallback

Purpose: avoid betting everything on USB protocol discovery.

In parallel, inventory what robot-side REVLib already exposes:

- faults
- sticky faults
- warnings
- supply voltage
- applied output
- motor current
- temperature
- encoder position and velocity

If robot-side REVLib gives enough stable data, it may be the safer first integration path for REV live status.

The USB gateway path can still remain valuable for:

- bench diagnosis
- firmware/version inventory
- cross-checking device identity
- cases where robot code is not deployed or not healthy

## Success Criteria

The REV research pass is useful when it produces:

- a transport classification
- at least one clean minimal enumeration capture
- a first-pass REV action/field inventory
- safety classification for discovered workflows
- a list of stable fields worth mapping into CAN troubleshooting
- a clear decision about whether first integration should use USB gateway, robot-side REVLib, or both

## Immediate Checklist

1. Record setup snapshot.
2. Identify USB class and any local helper services.
3. Capture minimal device enumeration.
4. Capture downstream-device discovery if available.
5. Capture Spark MAX detail/status pages.
6. Capture Spark Flex detail/status pages if hardware is available.
7. Compare passive CAN traffic during REV discovery.
8. Build first-pass raw REV inventory markdown and JSON.
9. Decide integration path.
