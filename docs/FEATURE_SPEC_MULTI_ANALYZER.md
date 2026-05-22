SPEC_STATUS: NOT_IMPLEMENTED

Multi-Analyzer Fault Inference Feature Spec

Purpose: Define topology-aware multi-analyzer visibility and fault inference in the PC bridge app.

Summary
Purpose: Describe the feature in one paragraph.
Add topology-aware fault inference to the PC bridge app by combining analyzer placement, device placement, and per-analyzer visibility. The system infers likely fault regions from visibility boundaries along an ordered bus while flagging non-contiguous patterns as anomalous. Outputs are CLI reports only and must avoid claiming exact fault locations or electrical causes.

Goals
Purpose: Define the desired outcomes.
- Place analyzers as first-class nodes in the topology model.
- Build per-analyzer visibility and message-rate tables.
- Infer likely fault regions using topology order and visibility divergence.
- Report likely fault location at multiple granularities (between nodes, at device, at connector) with confidence.
- Report likely electrical fault categories with confidence.
- Provide human-readable CLI reports with confidence and evidence.

Non-Goals
Purpose: Clarify what is out of scope.
- Electrical-level diagnosis or precise fault point claims.
- Topology discovery from traffic.
- Robot-side inference or UI changes.

Requirements
Purpose: Capture functional requirements.
- CAN analyzers must be placeable in the topology model as first-class nodes.
- Devices must have defined placement in topology order.
- Diagnostics must combine analyzer placement, device placement, and per-analyzer visibility.
- Inference must identify boundaries, contiguous blocks, and anomalies.
- Output must include fault region, affected devices, analyzer boundary, confidence, and evidence.

Constraints
Purpose: Define hard limits.
- Inference must be topology-aware, not topology-discovering.
- Non-linear or non-contiguous visibility patterns must be labeled anomalous and low-confidence.

Inputs
Purpose: List required inputs and their owners.
- Topology order: diagram node positions in `bringup_system.json` (owned by topology editor).
- Analyzer nodes: new node type with labels and placement (owned by topology editor).
- Per-analyzer visibility: seen/missing, last seen, fps, msg counts (owned by PC bridge).

Outputs
Purpose: Define CLI report content and contracts.
- Likely fault region (as a span of device labels or indices).
- Likely fault location (between nodes, at device, or connector) with confidence.
- Likely electrical fault category with confidence.
- Affected devices (ordered list).
- Analyzer boundary involved (which analyzers diverge and where).
- Confidence (High, Medium, Low).
- Evidence (counts, fps deltas, visibility ranges).

Data Tables
Purpose: Define the per-analyzer table schema used for inference.
- `seen` (bool)
- `lastSeenSec` (float)
- `ageSec` (float)
- `fps` (float)
- `msgCount` (int)

Inference Rules (High-Level)
Purpose: Describe the logic without implementation details.
- Build ordered device list from topology placement.
- Compare visibility vectors across analyzers.
- Detect visibility boundaries where seen->missing transitions occur.
- Prefer single contiguous missing blocks as valid regions.
- Mark non-contiguous patterns as anomalous and low-confidence.
- Use analyzer agreement and contiguity to raise confidence.
- Emit location and electrical hypotheses with confidence only (no certainty claims).

Debugging Procedure (Value Test)
Purpose: Validate that inference produces actionable, correct hints.

Run 1: Baseline (No Faults)
Purpose: Verify a healthy bus yields no fault region.
1. Run two analyzers at different positions on the same bus.
2. Record per-analyzer visibility tables.
3. Expected: All devices visible on both; no fault region; confidence High.

Run 2: Single Segment Break
Purpose: Verify boundary detection.
1. Open a CAN segment between two known devices.
2. Run the PC bridge with both analyzers.
3. Expected: One boundary; contiguous affected block; confidence High.

Run 3: Single Missing Device
Purpose: Verify anomaly labeling.
1. Power off or unplug one mid-bus device.
2. Run the PC bridge.
3. Expected: No boundary; anomaly flagged; confidence Low.

Run 4: Non-Contiguous Loss
Purpose: Verify anomaly labeling on scattered losses.
1. Unplug two devices in different bus regions.
2. Run the PC bridge.
3. Expected: Non-contiguous missing; anomaly flagged; confidence Low.

Run 5: Rate-Only Degradation
Purpose: Verify rate-only issues do not become false regions.
1. Increase bus load without removing devices.
2. Run the PC bridge.
3. Expected: Rate anomaly reported; no fault region.

Tradeoffs
Purpose: Document known tradeoffs.
- Requires accurate topology placement; incorrect order reduces inference quality.
- Multiple analyzers add setup complexity but improve localization.
- Conservative anomaly labeling may reduce false positives at the cost of sensitivity.

Future Extensions
Purpose: List safe next steps.
- Visual overlay in the topology UI.
- Export inference snapshots to JSON for postmortem.
- Replay PCAPs through multi-analyzer inference.

