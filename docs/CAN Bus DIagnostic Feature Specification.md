CAN Bus DIagnostic Feature Specification (No Additional Low-Level Hardware)
Purpose
This specification defines the feature set for a CAN-based diagnostic system that operates without additional electrical-layer hardware. It relies entirely on CAN traffic observation, controlled stimulus, and topology-aware inference.
Scope
Uses existing CAN interfaces (CANable, PiCAN, etc.)
No custom transceiver-level or electrical measurement hardware
Focus on protocol-level and behavioral inference
---
System Overview
The system consists of:
Controlled stimulus generation (robot side)
Passive CAN observation (one or more observers)
Topology model (expected system layout)
Inference engine (compares expected vs observed)
---
1. Observation Layer
Inputs
CAN frames (ID, data, timestamp)
Observer location (logical position in topology)
Authoritative decoding references
- `tools/can_nt/can_frc_defs.py` (FRC arbitration ID decode + frame classification)
- `tools/can_nt/can_nt_publish.py` `decode_frc_ext_id()` (manufacturer/deviceType/deviceId extraction)
- `tools/can_nt/wireshark/frc_can_dissector.lua` (Wireshark decode reference)
Notes
- Device identity is derived from the FRC extended arbitration ID fields as implemented in the references above.
- The dissector and Python decode functions are the source of truth for ID layout and field meanings.
Capabilities
Detect presence/absence of traffic
Measure frame rates
Detect changes in traffic after stimulus
Compare observations across multiple observers
Derived Signals
traffic_present (bool)
traffic_rate (frames/sec)
observer_visibility (per node, per observer)
traffic_change_after_stimulus (bool/degree)
---
2. Stimulus Layer
Inputs
Controlled robot actions (motor commands, subsystem activation, etc.)
Capabilities
Generate known CAN traffic patterns indirectly
Associate expected nodes with each stimulus
Outputs
stimulus_id
expected_nodes
expected_behavior (qualitative)
---
3. Topology Model
Represents:
Expected nodes
Logical ordering or grouping
Observer locations
Used for:
Predicting which observers should see which traffic
Identifying inconsistencies between expected and observed
Neighbor Ports Model
Purpose: Define directed, port-based adjacency for precise neighbor relationships.
Rules
Neighbors are not inferred from x/y coordinates.
Each node exposes a finite set of named ports based on node type.
Links connect a specific port on one node to a specific port on another.
This supports linear nodes (2 ports) and branch nodes (>2 ports) without ambiguity.
Port rules
Linear devices: ports left, right.
End devices: port next only.
Branch nodes: ports left, right, branch1, branch2 (extendable).
Analyzer nodes: ports left, right by default unless configured as branch taps.
Schema (diagram metadata)
{
  "neighborPorts": [
    { "node": 12, "port": "left", "neighbor": 10, "neighborPort": "right" },
    { "node": 12, "port": "right", "neighbor": 14, "neighborPort": "left" },
    { "node": 12, "port": "branch1", "neighbor": 30, "neighborPort": "next" }
  ]
}
Compatibility
neighborLinks is deprecated for topology-aware inference.
If both are present, neighborPorts takes precedence.
---
4. Inference Layer
Core Function
Compare expected topology + stimulus with observed CAN behavior
Key Questions Answered
Which nodes are present?
Which nodes are missing or silent?
Which nodes respond to stimulus?
Are observations consistent across observers?
Derived States (per node)
present
missing
responding
not_responding
ambiguous
Derived Conditions (system-level)
possible_break_between_segments
inconsistent_visibility
unexpected_node_or_id
---
5. Multi-Observer Correlation
Capabilities
Compare traffic visibility across observers
Examples
Seen at observer A but not B → possible break between A and B
Seen at all observers → node likely present
Seen at none → node missing or inactive
---
6. Output Model
System outputs structured diagnostic results.
Example
Expected nodes: 12
Confirmed present: 9
Missing: 2
Ambiguous: 1
Likely break: between observer_mid and observer_end
Node-level output
node_id
presence_state
response_state
visibility_map
confidence_score
---
7. Constraints
No electrical-layer measurements
No direct CAN protocol modification
No new CAN messages introduced
Vendor-specific behavior handled indirectly via observation
---
8. Success Criteria
The system is successful if it can:
Identify missing nodes reliably
Distinguish between "not present" and "not responding"
Narrow down likely fault regions using multiple observers
Improve over manual LED/console debugging workflow
---
9. Limitations
Cannot directly detect electrical faults
Cannot distinguish root cause when multiple failures overlap
Relies on observable traffic patterns
---
Summary
This system performs topology-aware, stimulus-driven inference using only CAN traffic observation. It replaces manual debugging heuristics with structured reasoning, without requiring additional hardware beyond existing CAN interfaces.
