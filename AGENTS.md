# FRC Bringup Diagnostics System (Java roboRIO + Python CANable tool)

This repo is one system with two cooperating parts:
- Robot-side WPILib Java bringup harness that actively runs motors/sensors on the roboRIO.
- PC-side Python tool that passively listens to the robot CAN bus via CANable (slcan over COM port) and publishes diagnostics to NetworkTables for the robot code and dashboards.

Real-time structure (20ms loop + scheduler)
Purpose: Explain why console output is throttled and how long reports are produced safely.
- WPILib runs robot code on a 20ms periodic loop (teleop/disabled/auto).
- The command scheduler and motor control live inside that 20ms budget.
- Loop overruns degrade control responsiveness and can cause missed behaviors.
- Console printing is slow and blocking; large dumps can easily exceed 20ms.
- Therefore, all report-like output is routed through a shared report runner:
  - Reports are queued and printed incrementally across multiple cycles.
  - The runner limits work per cycle (batch size) and chunk size per print.
  - This keeps output readable without stalling robot control loops.
- Any new report must use the shared report runner (no direct print bursts).

Hard rules
- The Python side must be read-only on CAN. Never transmit CAN frames.
- Keep a strict separation between local robot data (read directly on the roboRIO) and CAN-bus data coming from the PC tool via NetworkTables. Do not mix or conflate the two in logging, diagnostics, or APIs.
- Do not assume how the Java code uses NetworkTables. Before changing any NT keys, first inventory current usage in Java and Python and produce a short report.
- NetworkTables paths are an API contract. If any key path changes, update both sides in the same change and keep backward compatibility for at least one iteration.
- Windows is the primary host for the Python tool (Driver Station Windows PC). Avoid Linux-only assumptions (SocketCAN, can0, etc) unless explicitly requested.
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

Documentation Rules (Code)
Purpose: Keep man-page style documentation consistent in Java and Python sources.
- Use concise man-page style documentation blocks for important code elements.
- Document these:
  - Java: all classes, all public methods, and private methods with non-trivial logic.
  - Python: all modules, all top-level functions, and complex helper functions.
- Do NOT document trivial code such as:
  - getters/setters
  - simple pass-through wrappers
  - obvious one-line helpers
- Documentation sections should include when relevant:
  - NAME
  - SYNOPSIS
  - DESCRIPTION
  - PARAMETERS
  - RETURNS
  - SIDE EFFECTS
  - ERRORS
  - NOTES
  - EXAMPLE (optional)
- Guidelines:
  - Documentation must add information that the code does not already express.
  - Avoid repeating the function signature in prose.
  - Prefer concise technical language.
  - When modifying a function, update the documentation if behavior changes.
  - If an undocumented file is modified and contains meaningful logic, add documentation.
- Never change program behavior when enforcing documentation rules.

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
- Python CAN tool: tools/can_nt/ (entrypoint can_nt_bridge.py)

Shuffleboard layouts (profile-specific)
Purpose: Provide a default dashboard layout that includes per-device presenceConfidence tiles and a scrolling bringup tree.
- Layout files are profile-specific because device CAN IDs differ by configuration.
- Save layouts under src/main/deploy/ with a profile-specific name:
  - Example: bringup_shuffleboard_home_030226.json
- Workflow for a new profile:
  - Open Shuffleboard and arrange tiles (presenceConfidence + bringup tree).
  - File -> Save Layout As... to src/main/deploy/bringup_shuffleboard_<profile>.json
  - Load with File -> Open when using that profile.

Data-driven CAN profile mapping (Python tool)
Purpose: Add new manufacturers/devices by editing rule tables instead of code logic.
- File: tools/can_nt/can_nt_bridge.py
- Tables:
  - STATUS_RULES / CONTROL_RULES for frame classification
  - PROFILE_MAP_RULES for --dump-profile mapping
- To add a new device mapping, append a rule to PROFILE_MAP_RULES:
  - bucket: list-based devices (e.g., "neos", "krakens", "cancoders")
  - singleton: single-ID devices (e.g., "pdh", "pdp", "pigeon", "roborio")
  - note: optional assumption string included in generated profile notes

Reverse engineering features to implement in tools/ (new work)

New CLI capabilities (additive)
- --pcap <path> already exists: keep it working.
- Add a capture session concept:
  - --session <name> to tag outputs (pcap + json) with a common name.
  - --session-dir <dir> default tools/can_nt/logs or tools/captures.
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

