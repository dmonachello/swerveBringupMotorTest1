## What this is
A combined FRC bringup and diagnostics system: a WPILib Java bringup harness that runs on the roboRIO to exercise motors/sensors, plus a Windows-focused Python host toolset that passively listens to the robot CAN bus (CANable / slcan over a COM port), builds topology/evidence, and exposes local and REST-driven diagnostics surfaces for operator workflows and automated tests.

### Stack
- **Language(s):** Python (host tools, CLI, UI) and Java (robot WPILib bringup); small amounts of docs/others (TS, Lua, PowerShell) for tooling.
- **Framework / runtime:** WPILib Java (FRC robot runtime) for the robot-side bringup; Python 3 for the host-side CLI/UI and services (Windows-first).
- **Notable libraries / tools:** WPILib + Gradle for robot build/deploy, Python 3 runtime, pyserial / slcan usage pattern for CAN over serial (CANable), a lightweight HTTP/REST service pattern (runtime_query_service.py / can_bus_report_service.py), and a Tkinter-style host UI (bringup_ui.py). (See docs/INSTALL_WINDOWS.md and tools/can_nt/ for install/run helpers.)

## How it's organized
Top-level important entries (annotated):
```
src/                       Java WPILib robot code (frc.robot package)
  main/
    java/frc/robot/        Bringup code: BringupCore.java, BringupRuntime.java, BringupPrinter.java, BridgeUi* classes, Robot/RobotV2, Main.java
tools/                     Host-side tools and scripts
  can_nt/                  Python CAN tools, CLI, UI, services and profiles
    bridge_cli.py
    bringup_ui.py
    can_nt_bridge.py
    passive_discovery_integration_service.py
    runtime_query_service.py
    can_profiles.py
    install_deps.bat / run_can_nt.cmd
docs/                      Extensive design, feature specs, user guides, test plans, workflows, and API/contract docs
build.gradle / gradlew     Java build (Gradle) and WPILib integration
tests/                     Test harnesses and/ or test data
vendordeps/                (vendored dependencies / generated artifacts)
```

How it fits together:
- The robot Java code (src/main/java/frc/robot) runs under WPILib in the roboRIO 20ms control loop; bringup/diagnostics/reporting functions are implemented across BringupCore.java, BringupRuntime.java, BringupPrinter.java and the BridgeUi* classes. The code intentionally throttles console/report output to avoid overrunning the 20ms loop.
- The host-side Python tools (tools/can_nt/) attach to a CANable (slcan serial device) in read-only mode, parse CAN frames, run passive device discovery and fault inference, and provide CLI and GUI surfaces plus REST endpoints (runtime_query_service.py, can_bus_report_service.py) so operators and automation can consume device topology and diagnostics.
- Docs in docs/ define the architecture, CLI grammars, operator workflows, and strict rules (e.g., Python tools must be read-only on CAN and NetworkTables is deprecated for supported flows).

## How to run it
Shortest steps (Windows host + robot build hints):

1. Host (PC) -- prepare and run the Python CAN toolset (Windows-first):
   - Install Python 3 and required deps (see tools/can_nt/install_deps.bat and docs/INSTALL_WINDOWS.md).
   - Configure the serial/CAN source in tools/can_nt/source_config.py (set the COM port for your CANable).
   - Start the host UI or CLI:
     - GUI: python tools/can_nt/bringup_ui.py
     - CLI: python tools/can_nt/bridge_cli.py
   - Or use the shipped scripts: run tools/can_nt/run_can_nt.cmd or run_can_robot.bat to start a typical session.

2. Robot (roboRIO) -- build the Java WPILib bringup:
   - From repository root, build with Gradle:
     - On Windows: gradlew.bat build
     - On Unix: ./gradlew build
   - Deploy per your WPILib workflow (see build.gradle and WPILib docs). The project contains the standard WPILib entry points (Main.java, Robot.java / RobotV2.java) and bringup modules (BringupCore.java, BringupRuntime.java).

Notes / required configuration:
- The host expects a COM/serial slcan device (CANable) and is designed not to transmit CAN frames; double-check source_config.py and the UI/CLI launch parameters for the selected serial port.
- See docs/INSTALL_WINDOWS.md, docs/USER_GUIDE.md, and tools/can_nt/README_CAN_NT.md for detailed, step-by-step setup and safety checks before running on live hardware.
- If you plan to change any remaining NetworkTables references, follow the repository's "Hard rules" and inventory JS/Python/Java usage first (docs/SPEC_REMOVE_NETWORKTABLES_COMPLETE.md).

## Try asking
- Which Java classes implement the throttled report runner and where is console-print batching enforced? (hint: check BringupPrinter.java, BringupRuntime.java, BringupCore.java)
- How do I point the Python tool at a live CANable on COM3 and start the GUI for passive discovery? (check tools/can_nt/source_config.py, install_deps.bat, then bringup_ui.py / run_can_nt.cmd)
- Where are device profiles and the steps to add support for a new controller (e.g., a new REV or CTRE device)? (see docs/ADD_A_NEW_DEVICE.md and tools/can_nt/can_profiles.py)

If you want, I can:
- Show the specific lines in BringupPrinter.java and BringupRuntime.java that implement incremental printing and batch limits.
- Walk you through running the host tool against a recorded CAN pcap or a live CANable (with exact command lines).


---

Direct summary — DSL focus

- The project implements a domain-specific language (DSL) for robot bringup/diagnostics whose semantic unit is an “experiment” (a test). The DSL is authored on the host, compiled/validated into normalized JSON, and executed on the roboRIO by a small, safe, non‑procedural runtime. The host owns authoring/validation; the robot owns execution, device actuation, and safety.

What I inspected and how I looked
- I searched the repo for DSL material and opened the key robot runtime classes and host helpers. Principal artifacts I examined:
  - Robot runtime: src/main/java/frc/robot/tests/dsl/DslBringupTest.java and src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java and src/main/java/frc/robot/tests/dsl/DslModels.java
  - Host/UI helpers and reference: tools/can_nt/dsl_reference.py, tools/can_nt/host_ui_actions.py
  - Docs: docs/DSL_INTERPRETER_RUNTIME.md, docs/DSL_LANGUAGE_PACK_FOR_AI.md, docs/SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md, docs/FEATURE_SPEC_DSL_CONDITION_STABILITY_AND_RANGE_OPERATORS.md and multiple DSL-related spec/user-guide docs under docs/
  - Generated contract artifact (referenced): tools/common/generated/robot_test_dsl_signals.json

Core architecture (two-sided)
- Host side
  - Authoring: authors write text .dsl files (example syntax shown in docs).
  - Compile/normalize: host compiler/validator parses DSL source, removes comments, assigns stable IDs, converts references/literals into typed JSON, and stores normalized tests under bringup_system.json (dslTests.testsByName.normalized). Validation happens here (host UI exposes Import DSL Test and Validate DSL Tests).
  - UI/CLI surfaces: Bringup Control UI exposes import/validate/run flows; CLI commands include `test import`, `test validate`, `show test ... normalized`, `tests run` / `tests run --wait`.
  - Generated host artifacts (JSON + Python helpers) reflect the canonical signal registry and are used for UI and validation.
- Robot side
  - Robot reads the normalized JSON only (it does not reparse DSL source).
  - For each runnable test the robot creates a DslBringupTest from the normalized model and runs it inside the WPILib periodic loop (~20 ms turns).
  - Devices own read/write/clear hooks — the runtime calls device.readDslSignal, device.writeDslSignal, device.clearDslSignal. The DslSignalRegistry defines canonical signals and device-type aliases.

Language semantics and constructs
- Phases: init, main, close (host compiler normalizes into explicit phases).
- Statements:
  - set <target> = <literal | source> [deadband <n>] [scaled <n>] [default <n>]
  - clear <target>
  - abort <condition>
  - until <condition>
  - require <condition> (latched evidence)
  - success <condition>
  - unsafe-exit entries to exclude certain signals from final safe resets
- Condition forms:
  - Bare boolean: device.signal (for boolean signals)
  - Comparison: device.signal > 5, etc. (>, >=, <, <=, ==, !=)
  - Range: between and outside (e.g., require encoder.position between 100 120)
  - Stability suffix: stable <seconds> — condition is true only if raw condition has been continuously true for the given duration (not a blocking wait; modifies truth evaluation).
- Built-in timer: timer.elapsed returns seconds since test start (readable only, not a configured device).
- Non-procedural design: the runtime is a live rule evaluator, not a blocking script. No general expression language (no and/or/not, no abs(), no nested expressions) — docs and specs explicitly forbid adding these unless intentionally extended.

Runtime behavior (DslBringupTest important points)
- Execution loop (per WPILib periodic turn):
  1. resolve and write set statements (continuous ownership of set targets)
  2. sample signals (samples cached per tick)
  3. evaluate conditions (raw → stable filter → effective)
  4. update latched requires (require is latched evidence)
  5. decide pass/fail or continue (abort/until/success semantics)
- Safety:
  - The runtime applies safe values at start and final safe-values on close; device-level stop() is used for motor outputs when safe stop is required.
  - Host tools are read-only on CAN by default; host must not transmit CAN by default (safety guard).
- Device signal handling:
  - DslSignalRegistry provider model defines signal surfaces per semantic device type (motor, encoderExternal, imu, xboxController, PDH/PDP, test timer, etc.).
  - Registry provides canonical device type aliases (e.g., CANCoder → encoderExternal, Pigeon → imu).
  - DslBringupTest treats position/imu signals as deltas relative to captured baselines (start positions), and supports aggregate max values (e.g., velocity_actual_max_abs).
  - Devices decide how to map DSL read/write/clear to actual hardware; runtime validates writable ranges via device.isDslWritableValueInRange.

Host tooling, validation, and workflows
- Import/validate: UI exposes Import DSL Test and Validate DSL Tests (host-local actions); CLI supports test import/validate/show/normalized.
- Normalized JSON is authoritative for robot execution; the host validator ensures normalized and source align and tests are valid for the active profile.
- Typical operator flow: import .dsl → validate → import into profile → select test in UI → Run Selected (UI-first model is recommended).
- CLI fallback exists for scripted batch runs (tests run, tests run-all, tests wait).
- There are tests and pipelines for host & robot validation; docs list commands to run them.

Language features called out in docs/specs
- stable suffix (stable <seconds>) — for debounce/stability filtering
- between / outside range operators — inclusive bounds for range checks
- safe default patterns and recommended snippets (docs/DSL_LANGUAGE_PACK_FOR_AI.md gives authoring best-practices and examples)
- explicit “what it is not” (no procedural constructs, no compound boolean expressions, no arithmetic functions like abs() unless intentionally added)

Key files and places to inspect (paths)
- Robot runtime and models:
  - src/main/java/frc/robot/tests/dsl/DslBringupTest.java (runtime engine)
  - src/main/java/frc/robot/tests/dsl/DslSignalRegistry.java (canonical signal registry)
  - src/main/java/frc/robot/tests/dsl/DslModels.java (normalized JSON model classes)
  - src/main/java/frc/robot/tests/BringupTestRegistry.java (load-time registry — referenced in docs)
- Host/UI & helpers:
  - tools/can_nt/dsl_reference.py (renders generated reference tree in UI)
  - tools/can_nt/host_ui_actions.py (host UI actions: import/validate)
  - tools/common/generated/robot_test_dsl_signals.json (generated machine-readable signal catalog referenced by host)
- Docs with authoritative rules:
  - docs/DSL_INTERPRETER_RUNTIME.md (runtime/apparatus summary)
  - docs/ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md (runtime truth: referenced by DSL_LANGUAGE_PACK_FOR_AI)
  - docs/DSL_LANGUAGE_PACK_FOR_AI.md (authoring patterns, examples, AI handoff guidance)
  - docs/FEATURE_SPEC_DSL_CONDITION_STABILITY_AND_RANGE_OPERATORS.md (stable/between/outside syntax and semantics)
  - docs/SPEC_DSL_DEVICE_SIGNAL_INTERFACE.md (device/registry contract)

Notable design decisions and constraints (quick list)
- Host compiles/normalizes; robot executes normalized JSON only.
- Device-owned signal API: devices own read/write/clear semantics; runtime validates and calls device hooks.
- Non-procedural, tick-driven runtime (no blocking waits).
- Stable and range operators added to make tests robust against noise — these modify condition truth, not execution ordering.
- Timer is host/robot built-in and returns seconds since start.
- Safety-first defaults: host tools are read-only on CAN by default; the runtime applies safe-values and supports unsafe-exit exceptions.

Next steps I can take for you
- Show the host-side DSL compiler/validator code (I can search under tools/ for the parser/grammar and open that file).
- Show an example normalized JSON for a .dsl test (either by opening a normalized test from src/main/deploy/bringup_system.json or by compiling an example).
- Walk through a specific runtime path in DslBringupTest (e.g., how stable is implemented, how set fallbacks work) with exact line references.
- Show the generated robot_test_dsl_signals.json content so you can see the exact signal catalog the host uses.

Notes about my search
- I pulled together the above from the runtime code and many docs. My code search was limited to the top matching DSL-related files; there are more DSL-related docs and scripts in docs/ and tools/ that I can open on request (e.g., the host parser/grammar files, UI code paths, and generated artifacts).

Which of the next steps do you want me to do now? (I can open the host parser/validator, show an example normalized test JSON, or walk a particular runtime flow line‑by‑line.)


---

Below is a focused, source‑backed breakdown of the host compiler/validator, a real normalized test JSON example pulled from the repo, a line‑referenced walk through the DslBringupTest runtime paths you asked about, and where to find the generated signal catalog.

1) Host-side DSL compiler — key behavior and locations
- File: tools/common/robot_test_dsl/compiler.py
  - Entry point: compile_source(name, source) — parses logical lines and builds the normalized RobotTestDslNormalized model (see function header and main loop) (compiler.py:92–226).
  - Set parsing:
    - Detects set statements with RE_SET (compiler.py:56, lines 148–183).
    - Handles two RHS forms:
      - Source-driven sets with deadband/scale/default (RE_SET_SIGNAL; compiler.py:57–60, handling lines 153–172).
      - Literal sets (lines 174–180).
  - Condition parsing:
    - Keyword statements (abort/success/until/require) handled via RE_KEYWORD_EXPR (compiler.py:62, lines 197–216).
    - Stable suffix parsed with RE_STABLE_SUFFIX and _parse_stable_seconds (compiler.py:63 & _parse_stable_seconds:565–573).
    - Range expressions (between/outside) parsed with RE_RANGE_EXPR (compiler.py:64–67 and _parse_condition:522–536).
  - Robust compilation helpers:
    - collect_compile_errors() gathers multiple per-line compile problems (compiler.py:229–306).
    - compile_source_best_effort() compiles while collecting and returning per-line errors (compiler.py:308–458).

(See tools/common/robot_test_dsl/compiler.py for the full implementation and regular expressions.)

2) Host-side DSL validator — key behavior and rules
- File: tools/common/robot_test_dsl/validator.py
  - Top-level validation calls:
    - validate_store() validates the whole store (validator.py:59–82).
    - validate_entry() validates a single entry and ensures source/normalized sync (validator.py:85–97).
  - Source vs normalized check:
    - The validator attempts to recompile the source (compile_source) and compares regenerated normalized payload with the stored normalized JSON; mismatch => error "Source and normalized payload are out of sync." (validator.py:110–136).
  - Semantic checks (sample highlights):
    - Ensures declared devices exist in device catalog (validator.py:144–156).
    - Validates set statements: target must exist, be writable, numeric targets only, deadband/scale/default constraints, and target safe-value availability (validator.py:218–296).
    - Validates condition shapes: numeric ranges only for numeric signals; stable seconds must be > 0 (validator.py:311–336; stable check validator.py:317–320).
    - Rejects bare (uncomparative) conditions on non-boolean signals (validator.py:213–216).
  - Signal metadata lookups use the generated signal catalog (signal_catalog) read by the host service (service.py uses tools/common/generated/robot_test_dsl_signals.json; see service.py and _signal_meta usage in validator.py:384–401).

(See tools/common/robot_test_dsl/validator.py for full validation rules and error/warning production.)

3) Example normalized JSON for a .dsl test
- File: src/main/deploy/bringup_system.json includes compiled/normalized tests under "dslTests.testsByName".
- Example: the normalized entry for "Swerve Krakens Left Joystick" (excerpt, taken from bringup_system.json):

  - Location in file: src/main/deploy/bringup_system.json — the dslTests block starts at ~line 844; the "Swerve Krakens Left Joystick" normalized entry begins at ~line 885.

  Excerpt (abridged for clarity — exact JSON in file):

  {
    "name": "Swerve Krakens Left Joystick",
    "devices": [
      { "name": "frontLeft Drive Motor" },
      { "name": "frontRight Drive Motor" },
      { "name": "backLeft Drive Motor" },
      { "name": "backRight Drive Motor" },
      { "name": "controller0" }
    ],
    "unsafeExit": [],
    "init": { "sets": [], "clears": [], "aborts": [], "successes": [], "untils": [], "requires": [] },
    "main": {
      "sets": [
        {
          "id": "",
          "text": "set \"frontLeft Drive Motor\".output_percent_cmd = controller0.leftY deadband 0.12 scaled 0.20 default 0.0",
          "target": { "device": "frontLeft Drive Motor", "signal": "output_percent_cmd", "text": "frontLeft Drive Motor.output_percent_cmd" },
          "source": { "device": "controller0", "signal": "leftY", "text": "controller0.leftY" },
          "deadband": 0.12,
          "scale": 0.2
        },
        ... (same for other three drive motors)
      ],
      "clears": [],
      "aborts": [
        {
          "id": "",
          "kind": "abort",
          "text": "abort controller0.B",
          "reference": { "device": "controller0", "signal": "B", "text": "controller0.B" },
          "mode": "bare"
        }
      ],
      "successes": [],
      "untils": [],
      "requires": []
    },
    "close": { "sets": [], "clears": [], "aborts": [], "successes": [], "untils": [], "requires": [] }
  }

- The full normalized JSON for each test (and the entire dslTests store) is available in src/main/deploy/bringup_system.json under dslTests.testsByName — the file contains many test entries and full normalized payloads.

4) DslBringupTest runtime path — line‑referenced walkthrough (robot-side)
- File: src/main/java/frc/robot/tests/dsl/DslBringupTest.java
  - Test lifecycle:
    - start(...) sets up devices, captures start baselines, applies safe values, applies init clears/sets, initializes require latch map, sets result RUNNING, and enqueues start message (DslBringupTest.start: lines 125–201; device lookup and baseline capture around lines 151–184; applySafeValues and init apply lines 185–191).
  - Per-turn update loop:
    - update(context, nowSec) is the periodic tick entry (DslBringupTest.update: lines 204–266).
    - Steps executed each tick (in order):
      1. applySets for main phase writes commanded outputs (applySets and resolveSetValue) — see applySets (381–398) which iterates sets and calls resolveSetValue (472–507).
      2. sampleAll collects all referenced signals once per tick (sampleAll: 645–656).
      3. evaluateAllConditions evaluates raw → stable → effective for all conditions (evaluateAllConditions: 667–676; evaluateCondition: 679–686).
      4. update latched requires: requires are latched when their effective condition transitions true (lines 215–226 show require latch logic in update).
      5. termination checks: aborts (227–234), successes (235–242), untils (243–265) — until checks whether all requires latched; supports fallback detection (if fallbackActiveThisTick not empty then FAIL_SET_FALLBACK_ACTIVE).
  - Stable condition implementation:
    - Raw evaluation performed by evaluateRawCondition (688–726). It handles:
      - bare boolean references (returns Boolean.TRUE.equals(left)) (690–693).
      - range (between/outside) via evaluateRangeCondition (694–696 and evaluateRangeCondition: 741–754).
      - comparisons (>, >=, <, <=, ==, !=) when both left/right numeric or boolean or string fallback (lines 697–725).
    - Stable filter applied by updateStableFilter(condition, rawValue, nowSec) (756–775):
      - If condition.stableSeconds is null → return rawValue immediately (756–759).
      - If rawValue is false → reset stable start, elapsed = 0, stableSatisfied=false and return false (760–765).
      - If rawValue is true:
        - previousRaw and previousStart are consulted to compute stableStart (766–769).
        - stableElapsed = nowSec - stableStart (769).
        - stableSatisfied = stableElapsed >= condition.stableSeconds (770).
        - store stableStart/elapsed/satisfied in maps and return stableSatisfied (771–774).
    - Diagnostics recorded: conditionRawValues, conditionStableElapsedSec, conditionStableSatisfied, conditionEffectiveValues (these are used in buildConditionDetails: 329–349 and in buildRequireDetails: 302–327).
  - Set fallback / default behavior:
    - resolveSetValue implements:
      - literal sets: validate numeric literal and range checks (lines 477–489).
      - source-driven sets: read source via readSignalValue(...); if source unavailable, fallback logic invoked (lines 490–507).
    - When source not numeric/unavailable:
      - handleUnavailableSource(...) distinguishes phases:
        - in init -> fail (lines 514–518).
        - in close -> skip (lines 519–521).
        - in main -> attempt resolveSignalSetDefaultValue (lines 522–537).
      - Default fallback value is either provided defaultLiteral or DEFAULT_SIGNAL_SET_FALLBACK (compiler/model) (resolveSignalSetDefaultValue: 539–547).
      - When fallback used, lastResolvedSetValues updated and markFallbackWarning(statement, fallback, nowSec) is called (lines 534–537).
    - markFallbackWarning sets fallbackActiveThisTick (610–612), records fallbackActiveBySetId (612) and calls logWarningThrottled to enqueue a warning (613–622).
    - If fallbacks are active during an until termination, the test will fail with FAIL_SET_FALLBACK_ACTIVE (update: lines 252–261).
  - Safe-value and safe-stop semantics:
    - applySafeValues iterates writable signals from DslSignalRegistry and either writes the safe value or invokes device.stop() for safe stop output (applySafeValues: 425–454).
    - shouldApplySafeStop returns true for SIGNAL_OUTPUT safe-value STOP (456–459).
  - Built-in timer:
    - readSignalValue returns timer.elapsed computed as nowSec - startSec (lines 777–780).
  - Other notes:
    - device read/write/clear are delegated to DeviceUnit implementations: device.readDslSignal, device.writeDslSignal, device.clearDslSignal (readDeviceSignalValue and writeTargetSignal use these calls at 830–854 and 572–589 respectively).
    - The runtime computes deltas for position/IMU signals by comparing to captured start baselines (readDeviceSignalValue: lines 835–854; captureImuBaseline: 916–924).
    - Require revocation for latched requires when source device becomes unavailable applies to certain power devices (shouldRevokeLatchedRequire: lines 856–869).

(See src/main/java/frc/robot/tests/dsl/DslBringupTest.java for exact code and the line ranges referenced above.)

5) Generated signal catalog (host artifact)
- Generated artifact path: tools/common/generated/robot_test_dsl_signals.json
  - This JSON is emitted from the robot-side DslSignalRegistry (frc.robot.tests.dsl.DslSignalRegistry) and contains the authoritative mapping of deviceTypes → signals → metadata (valueType, readable, writable, clearable, safeValue, safeProvider, unsafeExitAllowed).
  - Example signal set is derived from DslSignalRegistry.java (robot-side registry). DslSignalRegistry defines signal names such as:
    - Motor signals: output, output_percent_cmd, output_percent_applied, current, current_actual, temperature, velocity, position, position_delta, faults, etc. (DslSignalRegistry: lines 41–56 and provider registration lines 106–114).
    - Controller signals: A, B, X, Y, LB, RB, leftX, leftY, rightX, rightY, leftTrigger, rightTrigger (DslSignalRegistry: lines 85–104).
    - Timer: SIGNAL_ELAPSED ("elapsed") (DslSignalRegistry: line 77).
  - The generated JSON file is the machine-readable catalog used by host validator and UI. Full contents are at tools/common/generated/robot_test_dsl_signals.json in the repo.

6) Quick pointers to the exact files (so you can open lines referenced)
- Host compiler: tools/common/robot_test_dsl/compiler.py
- Host validator: tools/common/robot_test_dsl/validator.py
- Host DSL service + serializer: tools/common/robot_test_dsl/service.py and serializer.py
- Generated signal catalog: tools/common/generated/robot_test_dsl_signals.json
- Normalized tests store: src/main/deploy/bringup_system.json (dslTests.testsByName)
- Robot runtime: src/main/java/frc/robot/tests/dsl/DslBringupTest.java and DslSignalRegistry.java

If you want additional verbatim excerpts (for example, the full compile_source function, the validator checks for set defaults/ranges, or the entire normalized JSON for a given test name), I can paste those exact blocks from the files shown above.

---

Short answer — make the troubleshooter more effective by (1) collecting richer, correlated CAN evidence, (2) adding automated inference rules and guided remediation steps, (3) improving visualizations/UX for faster diagnosis, and (4) adding safe active diagnostics and repeatable regression tests. Below I give a prioritized set of concrete changes you can implement, with file-level places in this repo to touch and example metrics/endpoints/DSL extensions to add.

Priority 1 — Quick wins (fast to add, high value)
- Add last-seen / per-ID summary and error counts (host)
  - What: for every observed CAN ID show lastSeen, frameCount, errorFrameCount, avgInterArrivalMs.
  - Why: immediately surfaces dead devices, flaky links, noisy IDs.
  - Where: extend passive_discovery_integration_service.py and runtime_query_service.py to compute and return these fields; also add them to the UI table in bringup_ui.py and CLI show commands.
- Persist full frame logs and offer PCAP/JSON export
  - What: write a rolling frame log (timestamp, id, dlc, payload hex, flags, raw) and add an endpoint / action to export it (pcap-ng or JSON).
  - Why: offline analysis, replay, regression baselines, sharing with team.
  - Where: tools/can_nt/* bridge code that currently parses slcan frames — add a logger and an export command; add "Export CAN capture" host UI button (host_ui_actions.py).
- Error-frame detection and simple heuristics
  - What: count CAN error frames, ACK failures, bus-off events and mark bus health (OK/WARNING/CRITICAL).
  - Why: error frames are the earliest indicator of wiring/termination issues.
  - Where: add analysis in a new module tools/can_nt/can_analysis.py and surface metrics through runtime_query_service.py.

Priority 2 — Better inference + guided workflows
- Topology heartbeats and “expected vs observed” check
  - What: build expected ID list from bringup_system.json profile and compare against observed IDs. Report missing, unexpected, duplicate IDs.
  - Why: quickly tells you if a device is not present or misconfigured ID.
  - Where: tools/common/config_api and tools/can_nt/service integration; show in UI topology view and dedicated “CAN health” panel.
- Per-device fingerprinting and protocol templates
  - What: for known device types, capture typical frame IDs/payload patterns (periodic status frames, extended IDs) and detect deviations (missing frames, truncated payloads).
  - Why: distinguishes a healthy device (sends regular telemetry) from one that is physically present but misconfigured.
  - Where: add device profile signatures from tools/common/generated/robot_test_dsl_signals.json or new generated artifact; implement matching in can_analysis.py.
- Detect likely termination issues and wiring faults
  - Heuristics: very high error-frame rate, long inter-frame collisions, many retransmits, no ACKs — these point to termination/resistor/wiring problems.
  - Provide suggested fixes: check terminators, wiring harness, power, remove single device to isolate.
  - Where: detection in can_analysis.py + UI "Troubleshoot" suggestions shown in bringup_ui.py.

Priority 3 — Visualizations and UX
- Time-series timeline with scrubber & per-ID filtering
  - What: interactive timeline of frames, errors, and selected ID events with zoom and histogram of inter-frame times.
  - Why: helps find bursts, transient outages, and collisions.
  - Where: enhance bringup_ui.py (or the web REST UI) to show a timeline view; provide ability to highlight frame payloads and link to run logs.
- Heatmap / frame-rate chart and bus utilization gauge
  - What: heatmap of IDs by frame-rate; bus utilization percent (bits/sec vs bus speed).
  - Why: shows bus saturation and which IDs dominate.
  - Where: can_analysis.py + bringup_ui.py + runtime_query_service.py endpoints.
- Guided troubleshooting wizard
  - What: UI step-by-step flow that runs checks in order (collect capture → check errors/terminators → compare expected IDs → ask operator to swap cable / power cycle → re-run checks).
  - Why: reduces time-to-fix for inexperienced operators; produces structured artifact for later review.
  - Where: new host action (host_ui_actions.py) and a new workflow module tools/can_nt/dsl_troubleshoot_wizard.py.

Priority 4 — Safer active diagnostics and automation
- Add operator-confirmed active probes (send-only when operator consents)
  - What: ability to request a device respond (e.g., request periodic status) or send a diagnostic ping. Keep default read-only.
  - Safety: require explicit UI prompt and "I acknowledge" and limit to short bursts.
  - Where: extend runtime_query_service.py and bridge CLI to add a host action that calls a small robot-side command; implement send code paths in tools/can_nt but gated by explicit flags.
- DSL-driven CAN health tests
  - What: create DSL tests that check bus health and per-device presence (e.g., require can_id_X.lastSeen > 0 within 2s).
  - Why: allows running reproducible regression checks as part of CI or operator flow.
  - Where: add host-side signal_catalog entries for CAN presence and add sample .dsl tests to tools/test_templates or src/main/deploy bringup_system.json tests set.
- Fault injection test harness (lab-only)
  - What: simulate missing termination, open bus, and device resets using a test bench CAN transceiver or a CAN interface that supports fault injection in a lab.
  - Why: validate detection rules and regression tests.
  - Where: new scripts under tools/can_nt/scripts/injection (requires lab hardware).

Priority 5 — Long-term / advanced features
- Correlate CAN evidence with robot runtime DSL results
  - What: when a DSL run fails (DslBringupTest result), cross-link the failure time to CAN capture segments, show frames around the failure.
  - Where: robot-side code enqueues timestamps; host runtime_query_service pulls robot-run timestamps and slices capture logs.
- Machine-learning anomaly detection / baseline comparisons
  - What: compare current capture to a baseline “known-good” capture and surface anomalous IDs/payloads/temporal patterns.
  - Where: research component, add tool under tools/can_nt/analysis_ml/.
- Protocol decoders (J1939/CANopen/custom)
  - What: for higher-level diagnostics decode payloads into fields for devices that support such protocols.
  - Where: can_analysis.py with optional decoders; integrate with UI.

Concrete implementation suggestions (code/file pointers)
- New modules:
  - tools/can_nt/can_analysis.py — compute per-ID stats, error metrics, utilization, termination heuristics, produce a structured JSON summary.
  - tools/can_nt/can_capture.py — add rolling frame log and export to pcap/json.
  - tools/can_nt/dsl_troubleshoot_wizard.py — guided UI flow.
- Integrations / edits:
  - passive_discovery_integration_service.py — add hooks to feed captured frames into can_analysis and persist logs.
  - runtime_query_service.py — add endpoints:
    - GET /can/frames?start=&end=&id=
    - GET /can/metrics
    - POST /can/export?format=pcap
    - GET /can/topology_diff
  - bringup_ui.py — add panels: CAN Metrics, Timeline, Export capture, Troubleshoot Wizard.
  - host_ui_actions.py — add host actions for Export CAN capture and Run CAN Troubleshoot Wizard.
- Validator/DSL:
  - Add new DSL observable signals (host/robot) in tools/common/generated/robot_test_dsl_signals.json and DslSignalRegistry:
    - can_bus.utilization, can_bus.error_rate, <device>.can_last_seen, <device>.can_frame_count
  - Add validator support so .dsl tests can use these signals.
- Tests/regressions:
  - Add unit tests under tools/can_nt/tests for can_analysis heuristics and CLI regression scripts (tools/can_nt/scripts).
  - Add a dsl regression that ensures a known-good baseline build passes (as in CHANGELOG/regression guidelines).

Example metrics to compute (for each reporting window)
- per-id:
  - lastSeenTimestamp
  - frameCount
  - avgInterArrivalMs, medianInterArrivalMs, stdev
  - errorFrameCount (if observed)
  - percentCorrupted (if parsing errors)
- bus-wide:
  - errorFrameRate (errors/sec)
  - retransmitRate
  - busUtilizationPercent (bits on bus / link_speed_bits)
  - busiestIDs list (top N by frames)
  - terminationHealthScore (heuristic from errorFrameRate and ack-failures)
- derived alerts:
  - MissingExpectedIDs = expectedIDs - observedIDs
  - CollidingIDs = IDs with interleaved payloads or many error frames
  - PossibleTerminationIssue = errorFrameRate > threshold and busUtilization < low threshold>

Safety and policy notes (must keep!)
- Keep host tools read-only by default. Any active transmit feature must be operator-confirmed and time-limited in UI and CLI (and have visible safety text).
- Fail-safe: if analysis suggests dangerous conditions (e.g., transient high-power load), do not auto-send commands.
- Logging/privacy: ensure export commands are explicit.

Quick implementation roadmap (4 sprints)
1. Sprint 1 (1–2 weeks): per-ID last-seen, frame counts, error counters; persistence of raw capture and a JSON export endpoint; CLI show commands to display summary.
2. Sprint 2 (2 weeks): add can_analysis.py with heuristics (missing IDs, error detection, termination heuristics) and surface in UI timeline and metrics gauge.
3. Sprint 3 (2–3 weeks): guided troubleshooting wizard, DSL signals for CAN presence, add DSL test examples and CI regression.
4. Sprint 4 (3+ weeks): active diagnostics (operator-gated), ML baseline comparisons, protocol decoders.

Offer
- I can:
  - produce a starter implementation for tools/can_nt/can_analysis.py (signature + basic heuristics + unit tests).
  - add runtime_query_service.py endpoints and a minimal bringup_ui.py panel to display per-ID summary.
  - create a first DSL test example that asserts presence of key CAN IDs and registers new DSL signals (and show the small registry changes required).
Which of those would you like me to implement or prototype first?
