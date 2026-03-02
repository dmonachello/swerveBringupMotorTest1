# FRC Bringup Diagnostics System (Java roboRIO + Python CANable tool)

This repo is one system with two cooperating parts:
- Robot-side WPILib Java bringup harness that actively runs motors/sensors on the roboRIO.
- PC-side Python tool that passively listens to the robot CAN bus via CANable (slcan over COM port) and publishes diagnostics to NetworkTables for the robot code and dashboards.

Hard rules
- The Python side must be read-only on CAN. Never transmit CAN frames.
- Keep a strict separation between local robot data (read directly on the roboRIO) and CAN-bus data coming from the PC tool via NetworkTables. Do not mix or conflate the two in logging, diagnostics, or APIs.
- Do not assume how the Java code uses NetworkTables. Before changing any NT keys, first inventory current usage in Java and Python and produce a short report.
- NetworkTables paths are an API contract. If any key path changes, update both sides in the same change and keep backward compatibility for at least one iteration.
- Windows is the primary host for the Python tool (Driver Station laptop). Avoid Linux-only assumptions (SocketCAN, can0, etc) unless explicitly requested.
- Prefer small, reversible diffs. No sweeping refactors unless asked.
- Keep hardware configuration easy to customize: adding a team's device list/profile should be data-driven and clearly documented, not code surgery.
- The JSON report exposes telemetry under `devices[].attachments` (e.g., `type=revMotor` / `ctreMotor`) with fields such as `cmdDuty`, `appliedDuty`, and `motorCurrentA`.
- AI diagnosis guidance lives in `AI_DIAGNOSIS.md`.
- Documentation rules:
  - Use short headings and clear section hierarchy.
  - Prefer short paragraphs and bullet lists.
  - Start layer sections with a one-line Purpose.
  - Include concrete Examples where appropriate.
  - Keep output schema and contracts stable and explicitly listed.
  - Include Tradeoffs and Future Extensions sections in architecture docs.
  - Printed docs rule: if a section or subsection would fit on one page, do not allow it to split across pages (keep heading and content together).

What to do first for any task that touches the Java-Python interface
1) Inventory NetworkTables usage:
   - List every path written and read on the Java side.
   - List every path published by the Python tool.
   - Identify overlaps, mismatches, and dead keys.
   Do not edit code in this step.

2) Propose the contract:
   - Which side owns which keys.
   - Update cadence expectations (publish period).
   - Behavior when the Python tool is absent (Java must fail soft).
   Do not edit code in this step.

3) Implement changes:
   - Keep behavior stable unless the task explicitly asks for behavior change.
   - If renaming keys is necessary, mirror old keys for compatibility.

Definition of done
- Java code still builds and deploys via the normal GradleRIO workflow for this repo.
- Python tool still runs on Windows with CANable slcan COM port and FRC bitrate 1,000,000.
- Python tool still publishes bringup/diag keys without breaking existing dashboards/prints.
- PCAP/PCAPNG output (if enabled) still opens in Wireshark.

Where things live
- Java bringup code: src/main/java/... (look for RobotV2 and BringupUtil)
- Python CAN tool: tools/ (entrypoint can_nt_bridge.py)

Reverse engineering features to implement in tools/ (new work)

New CLI capabilities (additive)
- --pcap <path> already exists: keep it working.
- Add a capture session concept:
  - --session <name> to tag outputs (pcap + json) with a common name.
  - --session-dir <dir> default tools/logs or tools/captures.
- Add inventory output:
  - --dump-api-inventory <path> writes JSON inventory:
    per device key (mfg,type,id) -> list of (apiClass, apiIndex) with counts and rates.
- Add diff capability:
  - --diff-inventory <a.json> <b.json> prints a short delta:
    new pairs, missing pairs, biggest rate changes.
- Add byte fingerprinting:
  - For each (mfg,type,id,apiClass,apiIndex):
    track which byte positions change and a simple entropy/variation score.

Data products
- PCAPNG capture: full fidelity frames.
- inventory JSON: stable schema for comparison between runs.
- optional "analysis JSON": top talkers, candidate command frames, byte fingerprints.

Implementation constraints
- Keep the core loop simple. Do analysis in lightweight accumulators.
- No heavy dependencies beyond what we already use.
- Analysis code must work both live and for offline replay if we add replay later.
- All reverse engineering outputs must tolerate unknown devices and unknown message types.

NetworkTables publishing (additive)
- Add new keys under bringup/diag/can/...
  Suggested keys:
  - can/apiInventory/json  (compact JSON string)
  - can/topTalkers/json
  - can/candidates/json (suspected command-like frames + fingerprints)
- Do not change existing bringup/diag/dev/... keys.

CAN reverse engineering roadmap (new work)

Goal
- Build an evidence-based map of CAN traffic meaning, not just device presence.
- Output should be useful for humans (Wireshark + summaries) and for code (decoder registry).
- Treat all decoded meanings as hypotheses until verified by controlled experiments.

Hard rules
- Do not transmit CAN frames from the PC tool. Reverse engineering is passive capture + analysis only.
- Do not assume vendor message layouts. Derive from observed arbitration IDs + controlled robot actions + diffs.
- Prefer additive outputs: never remove existing logging/publishing; add new summaries and new keys.

Method (stage gates)
Stage 1: Inventory
- For each device (mfg, type, deviceId), list all observed (apiClass, apiIndex) pairs.
- Track per-pair rate (frames/sec) and first/last seen.
- Persist this inventory to JSON for later comparison.

Stage 2: Controlled experiments
- Use robot-side bringup actions as the stimulus (enable one device, set a constant output, stop, reverse).
- For each experiment, produce a PCAPNG capture and a JSON inventory snapshot.
- Store captures with consistent names so they can be diffed.

Stage 3: Diff and classify
- Compare inventories between experiments to detect:
  - command-like frames (appear/change rate when setpoint changes)
  - status frames (always periodic)
- For each candidate frame type, compute "byte change fingerprints" (which bytes change, how often).

Stage 4: Hypothesis decoders
- Maintain a decoder registry keyed by (manufacturer, deviceType, apiClass, apiIndex).
- Each decoder can emit named fields with scaling guesses, but must mark confidence.
- Unknown frames must still be surfaced with raw bytes, rate, and change fingerprints.

Stage 5: Publish insights
- Publish the inventory and key findings to NetworkTables under bringup/diag/can/... without breaking existing keys.
- Java consumption is optional and must fail soft if the publisher is absent.

