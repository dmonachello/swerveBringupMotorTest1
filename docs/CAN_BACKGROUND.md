# CAN Bus Background (FRC)

This document is a practical, field-focused overview of CAN on FRC robots. It is structured as both a reference and a living discovery guide.

## Scope
- Explain how CAN works in the FRC context.
- Document known addressing and packet structure details.
- Provide a repeatable process for discovering and documenting unknown traffic.
- Offer troubleshooting guidance for common failures.

## How CAN Works (FRC)
CAN is a multi-drop, differential serial bus. Every device shares two wires (CANH/CANL) and takes turns transmitting short frames. Arbitration happens by ID: lower numeric IDs win priority and transmit first; losing devices back off automatically.

Key properties:
- Multi-drop: one bus, many devices.
- Differential signaling: noise-resistant when wiring is correct.
- Priority by ID: lower IDs win arbitration.
- Short frames: small payloads sent frequently.

In practice:
- Devices publish status frames at fixed rates.
- Controllers receive command frames from the roboRIO.
- The bus is healthy only if every device can transmit and receive without errors.

## CAN Addressing (FRC)
FRC uses extended 29-bit CAN IDs with a standardized layout. The arbitration ID is split into these fields:
- Device Type (5 bits)
- Manufacturer (8 bits)
- API Identifier (10 bits), broken into:
- API Class (6 bits)
- API Index (4 bits)
- Device Number (6 bits), often called the "CAN ID" set in vendor tools

Bit widths and ranges:
- Device Number is 6 bits (0-63).
- Manufacturer is 8 bits.
- Device Type is 5 bits.
- API ID is 10 bits total (API Class 6 bits, API Index 4 bits).

These fields define the full CAN address used for arbitration and message routing. The API Class/Index describe the kind of message (command, status, configuration, etc.).

Source: WPILib FRC CAN Device Specifications and WPILib CAN Java API.

### Packet Structure (FRC Specific)
- Arbitration ID: 29-bit extended ID using the field layout above.
- Payload: 0 to 8 data bytes (classic CAN).
- Priority: lower IDs win arbitration on the bus.

Source: WPILib FRC CAN Device Specifications and general CAN frame references.

### Device Number (CAN ID)
- Device Number is a 6-bit value used to distinguish multiple devices of the same type.
- Devices should default to ID 0; ID 0x3F may be reserved for device-specific broadcast.

Source: WPILib FRC CAN Device Specifications.

### Broadcast and Heartbeat
- Broadcast messages set Device Type = 0 and Manufacturer = 0. Broadcast API Class is 0.
- Defined broadcast messages include Disable, System Halt, System Reset, Device Assign, Device Query, Heartbeat, Sync, Update, Firmware Version, Enumerate, and System Resume.
- The roboRIO provides a universal CAN heartbeat every 20 ms. The spec defines its CAN ID (0x01011840) and payload layout, including match state and enable/disable fields.

Source: WPILib FRC CAN Device Specifications.

## Discovery Process (How We Learn More)
This project treats CAN reverse engineering as a structured process. The goal is to improve documentation over time without breaking the tool.

### Step 1: Inventory
- Capture a baseline of all (manufacturer, device type, device id, api class, api index).
- Record counts and rates per pair.

### Step 2: Controlled Experiments
- Change one variable at a time (enable one motor, apply constant duty, stop, reverse).
- Capture a new inventory and PCAP for each experiment.

### Step 3: Diff
- Compare inventories to identify frames that appear or change rate.
- Mark likely command frames vs periodic status frames.

### Step 4: Fingerprints
- Track which bytes change and how often.
- Store fingerprints for future decoding and cross-checking.

### Step 5: Document
- Update this file with confirmed field meanings.
- Label hypotheses explicitly until verified.

## Troubleshooting Workflow
### 1) Check bus health (roboRIO)
- Look at bus utilization, RX/TX errors, and bus-off count.
- Any rising error counts = wiring or termination first.

### 2) Check device health (local API)
- If a device is present locally, CAN wiring is likely OK for that device.
- If a device reports resets or sticky faults, check power and wiring.

### 3) Check PC sniffer (optional)
- If the sniffer sees traffic but the robot does not, check software/profile instantiation.
- If the sniffer sees nothing, check wiring and sniffer tap points.

## What "Bus Off" Means
Bus-off is a safety shutdown by the CAN controller after too many errors. It is almost always a wiring or termination failure. Stop debugging devices until this is fixed.

## How Utilization Matters
High utilization means the bus is near capacity. Symptoms include:
- rising TX full counts
- delayed or missing frames
- devices that appear intermittently

If utilization is high, reduce status frame rates or disconnect unused devices.

## CAN Best Practices (FRC)
- Keep CANH/CANL twisted the entire length.
- Use secure connectors; avoid loose or single-strand terminals.
- Check power wiring separately from CAN.
- Use a consistent device labeling scheme in profiles.

## Swyft Devices (Ethernet-Style Cabling)
Some devices use Ethernet-style cabling (RJ45) to carry CAN signals. These are still CAN devices, but the physical connectors are different.

What to know:
- The cable looks like Ethernet, but the signal is still CAN (not TCP/IP).
- Miswired pinouts or non-standard patch cables can break the bus.
- Long or low-quality cables increase susceptibility to noise.

Practical tips:
- Use the vendor-recommended pinout and cables only.
- Avoid mixing generic Ethernet patch cables unless explicitly supported.
- Confirm the device's CANH/CANL mapping before troubleshooting the rest of the bus.

## FRC Constants (Manufacturer, Device Type, API)
FRC assigns constants for the fields inside the 29-bit arbitration ID.

### Manufacturer IDs (assigned values)
- 0: Broadcast
- 1: NI
- 2: Luminary Micro
- 3: DEKA
- 4: CTR Electronics
- 5: REV Robotics
- 6: Grapple
- 7: MindSensors
- 8: Team Use
- 9: Kauai Labs
- 10: Copperforge
- 11: Playing With Fusion
- 12: Studica
- 13: The Thrifty Bot
- 14: Redux Robotics
- 15: AndyMark
- 16: Vivid Hosting
- 17: Vertos Robotics
- 18: SWYFT Robotics
- 19: Lumyn Labs
- 20: Brushland Labs
- 21-255: Reserved

Source: WPILib FRC CAN Device Specifications.

### Device Types (assigned values)
- 0: Broadcast Messages
- 1: Robot Controller
- 2: Motor Controller
- 3: Relay Controller
- 4: Gyro Sensor
- 5: Accelerometer
- 6: Distance Sensor
- 7: Encoder
- 8: Power Distribution Module
- 9: Pneumatics Controller
- 10: Miscellaneous
- 11: IO Breakout
- 12: Servo Controller
- 13: Color Sensor
- 14-30: Reserved
- 31: Firmware Update

Source: WPILib FRC CAN Device Specifications.

### API Class and API Index (from spec examples)
The FRC spec provides example API Class and Index tables for a CAN motor controller.
- API Class examples: Voltage Control (0), Speed Control (1), Voltage Compensation (2), Position Control (3), Current Control (4), Status (5), Periodic Status (6), Configuration (7), Ack (8).
- API Index examples: Enable (0), Disable (1), Set Setpoint (2), P (3), I (4), D (5), Set Reference (6), Trusted Enable (7), Trusted Set No Ack (8), Trusted Set Setpoint No Ack (10), Set Setpoint No Ack (11).

Source: WPILib FRC CAN Device Specifications.

## Quick Checklist
- [ ] Two terminations only.
- [ ] CANH and CANL not swapped.
- [ ] No duplicate IDs.
- [ ] Devices powered and not brown-out resetting.
- [ ] Utilization below saturation.
- [ ] Sniffer sees traffic (if used).

## Related Docs
- `README.md` for the bringup workflow and button bindings.
- `AI_DIAGNOSIS.md` for interpreting `bringup_report.json`.
- `ARCHITECTURE.md` for layered design details.

## API Class/Index Examples (Unverified)
These are additional hypotheses collected from field observations. They are not guaranteed across vendors.
They are intentionally retained to guide future experiments, but they should not be treated as canonical.

### API Class (example for motor controllers)
- 0: Voltage Control Mode
- 1: Speed Control Mode
- 2: Voltage Compensation Mode
- 3: Position Control Mode
- 4: Current Control Mode
- 5: Status
- 6: Periodic Status
- 7: Configuration
- 8: Ack

### API Index (example within a control class)
- 0: Enable Control
- 1: Disable Control
- 2: Set Setpoint
- 3: P Constant
- 4: I Constant
- 5: D Constant
- 6: Set Reference
- 7: Trusted Enable
- 8: Trusted Set No Ack
- 10: Trusted Set Setpoint No Ack
- 11: Set Setpoint No Ack

## Sources and Further Reading
These are the primary references used for the verified sections above. Additional vendor docs and field captures should be added here as they are verified.
- WPILib FRC CAN Device Specifications (addressing, device types, manufacturer IDs, broadcast messages, heartbeat layout): https://docs.wpilib.org/en/stable/docs/software/can-devices/can-specification.html
- WPILib CAN Java API (field bit widths and API ID size): https://github.wpilib.org/allwpilib/docs/release/java/edu/wpi/first/wpilibj/CAN.html
- General CAN frame references (payload size and frame layout): https://www.autopi.io/blog/can-bus-explained/
- WPILib Third-Party CAN Devices overview: https://docs.wpilib.org/en/stable/docs/software/can-devices/third-party-can-devices.html
- REV Hardware Client: https://docs.revrobotics.com/rev-hardware-client
- CTRE Tuner X: https://store.ctr-electronics.com/software/

## Dissector-Driven Inferences (New)
These are practical inferences we can make directly from the Wireshark dissector fields and tags:
- Broadcast vs device-specific frames: Broadcast messages apply to all devices; device-specific frames target a single CAN ID.
- RoboRIO heartbeat presence: Heartbeat frames confirm the roboRIO is transmitting and the bus is alive. Missing heartbeat points to a bus-level issue.
- Misaddressed devices: Unexpected manufacturer/device-type combinations often indicate a misconfigured ID or an unknown device on the bus.
- Priority hotspots: Arbitration ID trends can show which device IDs and API classes dominate traffic bursts.

## Appendix: Spec Notes (Paraphrased, Complete)
These are paraphrased notes extracted from the FRC CAN specifications. They are intentionally verbose so we do not lose any detail that has been captured so far.

### Protected Frames
- Actuator-control CAN nodes (motor controllers, relays, pneumatics controllers, etc.) must verify the robot is enabled and commands originate from the roboRIO.

### Broadcast Messages (by API Index)
- Disable (0)
- System Halt (1)
- System Reset (2)
- Device Assign (3)
- Device Query (4)
- Heartbeat (5)
- Sync (6)
- Update (7)
- Firmware Version (8)
- Enumerate (9)
- System Resume (10)
- Devices should disable immediately when receiving Disable (arbID 0). Other broadcast messages are optional.

### Requirements for FRC CAN Nodes
- Use arbitration IDs that match the prescribed FRC format:
  - Valid, issued CAN Device Type.
  - Valid, issued Manufacturer ID.
  - API Class(es) and Index(s) assigned and documented by the device manufacturer.
  - User-selectable device number if multiple units of the same type may coexist.
- Support minimum broadcast requirements.
- If controlling actuators, confirm the robot is issuing commands, is enabled, and is still present.
- Provide software library support for LabVIEW, C++, and Java (or coordinate with FIRST/control system partners).

### Universal Heartbeat (RoboRIO)
- The roboRIO sends a universal CAN heartbeat every 20 ms.
- Full CAN ID: `0x01011840` (NI manufacturer, Robot Controller type, Device ID 0, API ID `0x061`).
- 8-byte payload with a packed bitfield layout. Fields and widths:
  - Match time (seconds): byte 8, 8 bits.
  - Match number: bytes 6-7, 10 bits.
  - Replay number: byte 6, 6 bits.
  - Red alliance: byte 5, 1 bit.
  - Enabled: byte 5, 1 bit.
  - Autonomous mode: byte 5, 1 bit.
  - Test mode: byte 5, 1 bit.
  - System watchdog: byte 5, 1 bit.
  - Tournament type: byte 5, 3 bits.
  - Time of day (year): byte 4, 6 bits.
  - Time of day (month): bytes 3-4, 4 bits.
  - Time of day (day): byte 3, 5 bits.
  - Time of day (seconds): bytes 2-3, 6 bits.
  - Time of day (minutes): bytes 1-2, 6 bits.
  - Time of day (hours): byte 1, 5 bits.
- If the System watchdog flag is set, motor controllers are enabled.
- If 100 ms has passed since this packet was received, devices should assume the robot program is hung and act as disabled.
- Fields other than Enabled, Autonomous, Test, and System watchdog are invalid until some time after the Driver Station connects.

