# FRC Bringup Diagnostics System (Java roboRIO + Python CANable tool)

This repo is one system with two cooperating parts:

- Robot-side WPILib Java bringup harness that actively runs motors/sensors on the roboRIO.
- PC-side Python tool that passively listens to the robot CAN bus via CANable (slcan over COM port) and publishes diagnostics to NetworkTables for the robot code and dashboards.
- Shared docs/specs that define CLI behavior, layered architecture, operator workflows, and pit-side diagnosis direction.

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
- For behavior exposed through multiple surfaces (for example editor, live UI, CLI, reports), common code must own the full shared contract, not just helper primitives. If two surfaces are supposed to show or interpret the same topology/config state, they must share the same scene/model-building path or an explicitly documented compatibility adapter. Do not add or preserve independent render/composition pipelines for the same artifact unless the difference is intentional and documented.
- When CLI syntax changes, update the formal grammar in `tools/can_nt/bridge_cli_ebnf.txt` in the same change (and keep generated grammar artifacts in sync).
- When status definitions or generated command/status artifacts change, update all generated outputs in the same change. See `docs/GENERATED_ARTIFACTS_POLICY.md`.
- Keep hardware configuration easy to customize: adding a team's device list/profile should be data-driven and clearly documented, not code surgery.
- The JSON report exposes telemetry under `devices[].attachments` (e.g., `type=revMotor` / `ctreMotor`) with fields such as `cmdDuty`, `appliedDuty`, and `motorCurrentA`.
- AI diagnosis guidance lives in `docs/AI_DIAGNOSIS.md`.
- Enforce no string or numeric literals in executable code paths. All literals must be defined in a dedicated constants section/file and referenced symbolically. (Documentation and constant definitions are exempt.)
- Debuggability is a project-wide design goal. Add explicit invariant checks at parser/dispatcher boundaries, shared-contract adapters, cross-surface state sync points, and other glue layers where architectural drift tends to hide.
- When an internal invariant fails, do not misreport it as user syntax or configuration error. Surface it as a loud internal bug with enough context to localize the fault quickly (for example mode, command, handler, profile, or contract path).
- Use `assert` for developer/test-only impossible states where crashing is acceptable. In operator-facing tools, prefer nonfatal but prominent bug reports plus explicit internal-error status codes so the session remains debuggable.
- Treat parsed-but-unrouted commands, unexpected shared-model gaps, and cross-surface contract mismatches as architecture bugs. Report them immediately and loudly rather than silently recovering or downgrading them to generic failures.
- Documentation rules:
  - Use short headings and clear section hierarchy.
  - Prefer short paragraphs and bullet lists.
  - Start layer sections with a one-line Purpose.
  - Include concrete Examples where appropriate.
  - Keep output schema and contracts stable and explicitly listed.
  - Include Tradeoffs and Future Extensions sections in architecture docs.
  - Printed docs rule: if a section or subsection would fit on one page, do not allow it to split across pages (keep heading and content together).
  - Markdown linting (prevent MD022): Headings must be surrounded by blank lines (one empty line before and one empty line after).
    - Also keep lists surrounded by blank lines when adjacent to headings/paragraphs to avoid MD032.
  - Any modified Markdown file must pass markdownlint spacing rules (at minimum MD022 and MD032) before finalizing changes.

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

Spec Editing Notes
Purpose: Keep spec reviews actionable with consistent inline markers.

- Use `SID_QUESTION:` for open questions that must be answered before changing behavior.
- Use `SID_COMMENT:` for non-blocking notes or rationale.
- Place markers inline near the relevant section (not at the end).
- Remove `SID_QUESTION` lines once resolved in a follow-up edit.

Testing Notes Workflow (Global)
Purpose: Keep multiple test passes clean while preserving prior results.

- Add new notes under `SID_COMMENT:` during a fresh pass.
- After each pass, replace `SID_COMMENT:` with `TESTING_RESULTS:` to archive the run.
- Leave `TESTING_RESULTS:` blocks in place; only `SID_COMMENT:` should be reused for the next pass.

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
- Relevant CLI regression scripts pass, or any hardware/network dependency is explicitly called out.
- If Java tests are run on Windows, `JAVA_HOME` must point at the JDK root (for example `C:\Users\Public\wpilib\2024\jdk`), not the `bin` directory.

Where things live

- Java bringup code: src/main/java/... (look for RobotV2 and BringupUtil)
- Python CAN tool: tools/can_nt/ (entrypoint can_nt_bridge.py)
- Shared Python domain/service code: tools/common/
- Regression fixtures/expected outputs: tests/regression/

Current regression commands

Purpose: Keep local behavior checked with the same gates used by recent work.

- Local group/targeting regression:
  - `python tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py`
- Expanded local group/test regression:
  - `python tools/can_nt/scripts/bridge_cli_group_targeting_4m2g3t_regression.py`
- Connected non-motion robot regression (requires reachable roboRIO TCP UI endpoint):
  - `python tools/can_nt/scripts/bridge_cli_robot_non_motion_regression.py --rio 172.22.11.2`
- Java unit tests:
  - `.\gradlew.bat test`
- Robot-connected tests are optional unless the task explicitly touches robot TCP/UI behavior or the user asks for connected validation.

Layered architecture direction

Purpose: Keep new work aligned with the current architecture docs without forcing a sweeping rewrite.

- The practical target is the layered model described in `docs/ARCHITECTURE.md` and `docs/SPEC_LAYERED_ARCHITECTURE_REFACTOR.md`.
- Python/PC-side services are the current main frontier for layered progress:
  - shared config lifecycle
  - workflow services
  - test/profile/group domain semantics
  - status and command handling
- Prefer moving reusable host-side behavior into shared services instead of duplicating it inside CLI/UI surfaces.
- Do not redo Java-side architecture just because a spec mentions a split; preserve existing working boundaries unless the task requires a change.
- Preserve command semantics, status codes, batch behavior, and regression script compatibility during refactors.

CLI and status contract

Purpose: Keep operator-facing commands and machine-readable outcomes stable.

- Prefer canonical command forms documented in the CLI specs and manuals.
- Keep parser, help text, docs, grammar, and regression fixtures aligned when command syntax changes.
- Status-code behavior is part of the API contract. Do not replace code-based outcomes with text-only checks.
- Existing batch scripts and regression scripts must keep exercising the same command path as interactive use.

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

Pit robot diagnosis direction

Purpose: Capture the current spec/research direction for pit-side fault localization.

- Current pit-diagnosis work is still spec/research unless a task explicitly asks for implementation.
- Relevant specs:
  - `docs/FEATURE_SPEC_MULTI_OBSERVER_CAN_FAULT_LOCALIZATION.md`
  - `docs/SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md`
  - `docs/SPEC_OPERATOR_CLUES_MODEL.md`
  - `docs/SPEC_BREAK_AND_ERROR_OPERATOR_SURFACES.md`
  - `docs/SPEC_BREAK_ERROR_IMPLEMENTATION_TRACE.md`
  - `docs/FEATURE_SPEC_PIT_ROBOT_DIAGNOSIS_FIRST_PASS.md` when present
- Treat the product concept as multi-observer, topology-aware CAN fault localization with operator-supplied field clues.
- Use `neighborPorts` as the preferred semantic topology graph for inference. Treat `neighborLinks` as a lower-fidelity compatibility/fallback source.
- Output candidate fault regions and evidence provenance; do not overclaim exact electrical causes from passive evidence alone.
- Operator clues are weighted evidence, not truth. Preserve passive evidence and surface conflicts when clues disagree with telemetry.
- New pit-diagnosis outputs should be additive and should not break existing bringup, dashboard, CLI, or JSON report behavior.

