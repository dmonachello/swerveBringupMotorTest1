# Development And Feature Roadmap

## Purpose
Provide a single, stable plan for what to build next, why it matters, and how to verify progress.

## Scope
- This roadmap covers both robot-side Java and PC-side Python.
- Time is not the driver; progress is feature-complete and verified.
- Items are ordered by dependency and value, not by date.

## Current State (Baseline)
Purpose: Anchor the roadmap against what already exists.
- Robot bringup harness runs motors/sensors and prints health reports.
- PC tool passively listens on CAN (slcan) and publishes diagnostics to NetworkTables.
- PCAP/PCAPNG capture is supported.
- Data-driven hardware profiles and bringup tests are in place.

## Track A (Main): CAN Bus Debugging Features
Purpose: Make diagnosing CAN bus faults fast, reliable, and repeatable.
- Add a one-line CAN health summary (utilization, errors, TX full, bus-off).
- Add trend detection for error spikes and utilization surges.
- Add a wiring/termination hint when bus-off or TX full rises.
- Add a “bus quiet” detector with guidance (sniffer not seeing frames).
Example:
- “BUS ALERT: util 78% (rising), tx_full +3, bus_off +1.”

## Track B: Core Reliability And Usability
Purpose: Make core workflows predictable and easy to use.
- Harden error handling and logging for CANable + COM port detection.
- Confirm “no PC tool” behavior is soft-fail on the robot.
- Add short “first-run” checklist and troubleshooting quick-start.
- Validate documentation parity between Java and Python reports.
Example:
- Run with PC tool off, then on, and confirm the D-pad Down table updates without errors.

## Track B: Capture Sessions
Purpose: Make CAN captures reproducible and easy to compare.
- Add `--session <name>` and `--session-dir <dir>` in PC tool.
- Tag PCAP and JSON outputs with session name and profile.
- Keep default paths Windows-friendly (`tools/can_nt/logs` or `tools/captures`).
Example:
- `--session drivetrain_forward` writes:
  - `drivetrain_forward.pcapng`
  - `drivetrain_forward_inventory.json`

## Track C: Reverse Engineering - Inventory Output (Stage 1)
Purpose: Persist what the CAN bus is doing in a stable, comparable schema.
- Implement `--dump-api-inventory <path>` JSON output.
- Track per (mfg,type,id,apiClass,apiIndex):
  - frame count
  - firstSeen, lastSeen
  - rate (fps)
- Publish compact inventory to `bringup/diag/can/apiInventory/json`.
Example:
- Compare two JSONs from different sessions and see changed pairs.

## Track C: Reverse Engineering - Inventory Diff
Purpose: Quickly spot differences between experiments.
- Implement `--diff-inventory <a.json> <b.json>`:
  - new pairs
  - missing pairs
  - biggest rate changes
- Keep output short and human-scannable.
Example:
- “NEW: CTRE/TalonFX/11 apiClass=2 apiIndex=1 rate +50.0 fps”

## Track C: Reverse Engineering - Byte Fingerprinting
Purpose: Identify candidate command-like frames without vendor assumptions.
- Track byte-change positions for each (mfg,type,id,apiClass,apiIndex).
- Add a simple variation score and percent-changed per byte.
- Publish candidates to `bringup/diag/can/candidates/json`.
Example:
- Byte 2 changes 95% of frames when duty changes.

## Track C: Reverse Engineering - Candidate Classification
Purpose: Classify frames as “likely status” or “likely command.”
- Compare fingerprints and rate deltas between controlled experiments.
- Flag frames that appear only when outputs change.
- Keep raw evidence visible even when labeled.

## Track C: Reverse Engineering - Hypothesis Decoders
Purpose: Start a decoder registry with confidence labels.
- Registry keyed by (mfg, type, apiClass, apiIndex).
- Each decoder emits fields + scaling guesses + confidence.
- Unknown frames remain raw with fingerprints.
Example:
- `motorCurrentA` (low confidence) inferred from byte changes and rate patterns.

## Track B (Optional): Dashboard Migration
Purpose: Move off Shuffleboard with no key changes.
- Port layout to Elastic dashboard.
- Keep NT keys stable; update layout files only.

## Track B (Optional): CAN Bus Topology Viewer (PC)
Purpose: Provide a simple visual map of the CAN bus node list.
- Build a small PC program that renders nodes as boxes on a single shared bus line.
- Each node shows label, CAN ID, manufacturer, and device type.
- Data source: existing profiles + live PC tool observations (if available).
- Start with a static layout; no auto-routing or clustering required.
Example:
- “PDH (id 1)”, “NEO 10”, “KRAKEN 11” displayed as boxes on a horizontal bus line.

## Verification Checklist
Purpose: Define “done” for each phase.
- All phases:
  - No CAN transmit from PC tool.
  - Robot still deploys via GradleRIO.
  - Windows PC tool works with slcan COM port at 1,000,000 bitrate.
- Phase 2:
  - Session outputs are created with correct names and locations.
- Phase 3:
  - Inventory JSON validates against a stable schema.
- Phase 4:
  - Diff output shows meaningful deltas between two runs.
- Phase 5:
  - Fingerprints are stable across repeated identical tests.

## Risks And Tradeoffs
Purpose: Make the design constraints explicit.
- More analysis increases CPU cost on the PC; keep per-frame work O(1).
- “Best-effort” inference risks false positives; always preserve raw evidence.
- Keeping backward-compatible NT keys limits refactor speed but prevents dashboard breakage.

## Future Extensions
Purpose: Capture ideas that are valuable but not required now.
- Offline replay mode for PCAP-based analysis.
- Auto-generated experiment scripts from bringup tests.
- Small web UI for live inventory and diffs.
- Export to CSV for quick spreadsheet analysis.

