# Project Master System Review

## 1. Purpose

Purpose: provide a candid first-pass master document for the full project,
covering history, architecture, implementation reality, mistakes, unresolved
issues, testing, and future direction.

This document is intentionally internal-first and blunt. It is meant to help
shape the next-level documentation tree, not to serve as a polished external
overview.

This first pass is one large document with internal sectioning. Later work can
split it into focused documents once the structure and priorities are stable.

## 2. Scope

Purpose: define what this document covers and what it does not.

In scope:

- full-system story from the start of the project through current direction
- both robot-side Java and host-side Python surfaces
- architecture, implementation, contracts, workflows, and operator surfaces
- known mistakes, dead ends, reversals, and technical debt
- current state versus partial state versus spec/research-only state
- testing history, regression strategy, and remaining gaps
- future direction, including committed, likely, and speculative work
- document-map references to existing repo docs

Out of scope:

- exhaustive line-by-line code inventory
- full reproduction of all existing specs
- pretending the current codebase is cleaner or more settled than it is

## 3. Reading Guide

Purpose: clarify how to interpret statements in this document.

Status labels used here:

- Implemented now: present in current repo behavior or structure
- Partial / inconsistent: present in some code or docs, but not fully coherent
- Spec / research only: direction or design intent, not solid implementation

Tone rules:

- this document names weak abstractions and failed directions directly
- disagreements between docs, code, and current intent are called out
- future direction is split by confidence, not presented as all equally real

## 4. Project Map

Purpose: give an early bullet-list map of the major features, issues, and
directions, with pointers to the detailed chapters below.

### 4.1 Project shape

- The repo is one system with two cooperating halves: roboRIO bringup runtime
  and PC-side passive CAN diagnostics.
  See Section 6 and Section 7.
- The actual value of the project is not just "CAN visibility"; it is
  evidence-based bringup with both local robot truth and passive bus truth.
  See Section 5, Section 6, Section 7, and Section 11.
- The system has expanded from a bringup harness into a multi-surface product:
  CLI, TCP UI, topology editor, diagnostics, DSL, testing workflows, and
  future pit diagnosis.
  See Section 10, Section 11, Section 12, Section 13, and Section 15.

### 4.2 Core constraints

- The Java side runs inside a 20 ms WPILib loop, which means report printing
  and command handling must never behave like a normal desktop app.
  See Section 6 and Section 16.
- The Python CAN tool must remain read-only on the CAN bus.
  See Section 7 and Section 16.
- Windows is the primary host environment for the PC tool and workflows.
  See Section 7 and Section 16.
- NetworkTables paths are a contract, not casual implementation detail.
  See Section 8 and Section 14.

### 4.3 What the project got right early

- Separating robot-local data from passive CAN observations was the right call.
  See Section 5 and Section 8.
- Data-driven profiles were the right long-term direction even though the path
  there has been messy.
  See Section 8 and Section 9.
- The emphasis on operator workflows and repeatable testing is one of the
  project's strongest qualities.
  See Section 10, Section 11, and Section 13.

### 4.4 What became more complicated than expected

- Unified config and schema evolution.
  See Section 9.
- CLI design, grammar, and status-code stability.
  See Section 10.
- Topology modeling, especially the shift from neighbor-shaped metadata to an
  actual graph.
  See Section 12.
- Test authoring and the evolution from hard-coded tests to data-driven and
  DSL-driven tests.
  See Section 13.
- Maintaining coherence between specs, code, and current intent.
  See Section 17 and Appendix B.

### 4.5 Things that were weaker than they should have been

- Too much duplicated truth across docs, config representations, and surfaces.
  See Section 17.
- Too much semantic logic historically lived in ad hoc JSON walking.
  See Section 9, Section 10, and Section 12.
- Some major features grew faster than the shared architecture underneath them.
  See Section 7, Section 10, Section 12, and Section 17.
- Documentation sprawled into many useful but overlapping specs without one
  honest master narrative.
  See Section 18 and Appendix B.

### 4.6 Current strong directions

- Push more host-side semantics into shared services and normalized models.
  See Section 7, Section 9, Section 10, and Section 12.
- Keep the CLI/operator contract stable while refactoring underneath it.
  See Section 10 and Section 14.
- Treat topology as canonical graph truth, not neighbor tables.
  See Section 12.
- Keep testing and regression automation as first-class architecture, not
  afterthought.
  See Section 15.

### 4.7 Current unresolved tensions

- Practical existing boundaries versus ideal layered architecture.
  See Section 17.
- Refactor freedom versus compatibility for operators and scripts.
  See Section 10, Section 14, and Section 17.
- How broad the topology model should become before implementation catches up.
  See Section 12 and Section 19.
- How much of pit diagnosis is product direction versus research speculation.
  See Section 19.

## 5. History Overview

Purpose: summarize the major eras of the project without turning this document
into a long chronological narrative.

### 5.1 Phase 1: robot bringup harness

- The project started as a robot-side bringup harness focused on actuating
  hardware, reading device health, and supporting controlled manual bringup.
- The early center of gravity was Java, vendor APIs, device wrappers, and
  report-style output from the robot.
- The key insight was that bringup is not the same as final robot behavior and
  needs its own harness and safety model.

### 5.2 Phase 2: passive CAN visibility from the PC

- The system expanded by adding a PC-side Python tool that listens to CAN via a
  CANable and publishes diagnostics through NetworkTables.
- This created the dual-source model: robot-local truth and passive bus truth.
- This was a major project-defining improvement because it allowed detection of
  missing traffic and bus-level symptoms that robot-local wrappers alone cannot
  show.

### 5.3 Phase 3: profile-driven workflows

- Configuration moved toward profile-driven, data-driven hardware definition.
- This was necessary for repeatability and multi-robot adaptability.
- It also created schema, migration, and ownership complexity that is still not
  fully settled.

### 5.4 Phase 4: operator surface expansion

- The project gained more user-facing surfaces: CLI, Bringup Control UI, TCP UI
  protocol, topology editor, and richer reports.
- This improved usability and reach, but also increased the number of
  contracts that need to remain stable.

### 5.5 Phase 5: tests, DSL, and authoring

- The system moved from fixed bringup actions toward test authoring, reusable
  test sets, and a Robot Test DSL.
- This improved expressiveness and reusability, but it also expanded the
  semantic model significantly.

### 5.6 Phase 6: topology and diagnosis push

- Topology moved from lightweight diagram metadata toward a graph-model
  ambition.
- Pit diagnosis and multi-observer fault localization emerged as important
  future directions.
- This is where current ambition is highest and implementation coherence is
  still catching up.

## 6. Robot Runtime

Purpose: describe the robot-side Java runtime, what it does well, and where
its architectural and implementation pressure points are.

Current state:

- Implemented now: the roboRIO side owns actuation, local device instantiation,
  health snapshots, report output, and safety-critical control decisions.
- Implemented now: the robot is the server in the client/server model.
- Implemented now: report output is throttled through a shared runner because
  the 20 ms loop cannot tolerate bursty console printing.
- Partial / inconsistent: internal layering exists in docs and to some extent
  in code, but large coordinator-style classes and practical shortcuts still
  exist.

What the Java side is fundamentally responsible for:

- device creation and vendor SDK interaction
- test execution and actuation safety
- report generation
- TCP command handling and runtime state
- soft consumption of PC-published diagnostics

What was right:

- Robot-side ownership of actuation was non-negotiable and correct.
- Keeping Xbox/local safety priority above network clients was correct.
- Treating report throttling as a core architectural rule instead of a style
  preference was correct.

What is weaker than it should be:

- There is still too much large-class coordination logic in some paths.
- Some architectural aspirations were documented before code structure was
  ready to support them cleanly.
- Java-side boundaries are better than an ad hoc prototype, but not yet clean
  enough to claim a finished architecture.

Relevant docs:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [COMMAND_HANDLER_ARCHITECTURE.md](COMMAND_HANDLER_ARCHITECTURE.md)
- [SPEC_PHASE_2_JAVA_UI_COMMAND_REFACTOR.md](SPEC_PHASE_2_JAVA_UI_COMMAND_REFACTOR.md)
- [SPEC_PHASE_2_HARDENING_PASS.md](SPEC_PHASE_2_HARDENING_PASS.md)

## 7. Host-Side Python Architecture

Purpose: describe the Python side as it exists now, including where it is the
main frontier of architectural change.

Current state:

- Implemented now: passive CAN listener, NetworkTables publishing, CLI,
  topology editor, config tooling, and various shared host-side libraries.
- Implemented now: Windows-first workflows and slcan/CANable assumptions.
- Partial / inconsistent: the host side contains both layered architecture
  direction and legacy direct-surface logic.
- Spec / research only in places: richer topology semantics and future
  diagnosis models.

What the Python side currently does:

- observes CAN traffic passively
- classifies and publishes bus diagnostics
- provides CLI and editing surfaces
- owns much of the offline configuration lifecycle
- increasingly acts as the place where shared semantic models should live

What is strong:

- The host side is where data-driven and shared-service patterns make the most
  sense.
- It is much easier to evolve and test than robot-side code.
- It is the right place for normalization layers, config lifecycle helpers,
  topology semantics, and regression tooling.

What is weak:

- The host side grew by accretion across many tools and specs.
- Too much semantic logic historically lived directly in CLI/editor code.
- Several features started as tactical additions and only later received an
  architectural model.

Relevant docs:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [BRIDGE_RUNTIME_ARCH.md](BRIDGE_RUNTIME_ARCH.md)
- [shared_code_libs.md](shared_code_libs.md)
- [FEATURE_SPEC_SIMPLIFY_AND_UNIFY.md](FEATURE_SPEC_SIMPLIFY_AND_UNIFY.md)

## 8. Data and Contract Model

Purpose: describe the major contracts that keep the system coherent, and where
contract discipline has mattered most.

Major contracts:

- NetworkTables diagnostics contract
- unified config JSON contract
- CLI grammar and status-code contract
- TCP UI protocol contract
- generated artifact sync contract

What was right:

- Treating NT keys as a real API contract is correct.
- Separating command transport from diagnostics transport is correct.
- Status codes matter because text alone is not enough for stable automation.

What has been difficult:

- Contract changes often touched multiple surfaces at once.
- Some doc sets describe intent more cleanly than current implementation.
- Contract drift is one of the project's recurring failure modes.

Known anti-patterns:

- changing key names casually
- relying on user-facing text where machine-readable codes should exist
- allowing generated artifacts to drift from source definitions
- duplicating semantic truth across parallel data shapes

Relevant docs:

- [NT_CONTRACT.md](NT_CONTRACT.md)
- [TCP_UI_PROTOCOL.md](TCP_UI_PROTOCOL.md)
- [CLI_GRAMMAR_UNIFICATION_SPEC.md](CLI_GRAMMAR_UNIFICATION_SPEC.md)
- [FEATURE_SPEC_UNIFIED_STATUS_CODES_PY_JAVA.md](FEATURE_SPEC_UNIFIED_STATUS_CODES_PY_JAVA.md)
- [GENERATED_ARTIFACTS_POLICY.md](GENERATED_ARTIFACTS_POLICY.md)

## 9. Unified Config and Schema Evolution

Purpose: describe the shift to a unified config model and the problems it
solved and created.

Current state:

- Implemented now: `bringup_system.json` is the main source of shared
  configuration truth.
- Implemented now: devices table, profile membership, tests, bridge config,
  topology, and related sections live together.
- Partial / inconsistent: migration paths, schema enforcement, and older mental
  models still leak through.

What this solved:

- one place for shared bringup configuration
- data-driven hardware definitions
- consistent cross-surface references by label
- better authoring workflows than code edits

What this complicated:

- schema versioning
- migration from older shapes
- ownership boundaries inside one big JSON file
- duplication hazards between profile-local and global structures

What should be considered a hard lesson:

- schema growth without a strong normalized semantic layer creates chaos
- JSON is easy to edit but easy to misuse
- once multiple surfaces write the same file, discipline matters more than
  convenience

Relevant docs:

- [bringup_profiles_schema.md](bringup_profiles_schema.md)
- [bringup_profiles_schema_erd.md](bringup_profiles_schema_erd.md)
- [PROFILE_SCHEMA_REFACTOR.md](PROFILE_SCHEMA_REFACTOR.md)
- [FEATURE_SPEC_CONFIG_STORE.md](FEATURE_SPEC_CONFIG_STORE.md)
- [FEATURE_SPEC_CONFIG_RECOVERY_UNIFIED.md](FEATURE_SPEC_CONFIG_RECOVERY_UNIFIED.md)

## 10. CLI and Operator Workflows

Purpose: describe the CLI as both one of the project's best operator ideas and
one of its biggest contract burdens.

Current state:

- Implemented now: Bridge CLI is a major operator and editing surface.
- Implemented now: CLI grammar, help, contexts, status surfaces, and local vs
  robot context concepts.
- Partial / inconsistent: some behaviors are cleaner in spec than in code.
- Implemented now: CLI is deeply tied to config editing, testing, and robot
  interactions.

Why the CLI matters:

- It gives expert users a precise and scriptable surface.
- It becomes a forcing function for domain clarity.
- It exposes semantic inconsistency quickly.

What went right:

- novice/operator usability was taken seriously
- context distinction between host-local and robot-runtime state is important
- canonical command/stability thinking is good and necessary

What went wrong or remains risky:

- CLI scope became huge
- parser/grammar/help/completion consistency is hard to maintain
- command stability constrains refactors underneath
- some commands grew before the shared domain model beneath them was stable

Relevant docs:

- [BRIDGE_CLI_FULL_SPEC.md](BRIDGE_CLI_FULL_SPEC.md)
- [BRIDGE_CLI_DESIGN.md](BRIDGE_CLI_DESIGN.md)
- [CLI_REFERENCE_MANUAL.md](CLI_REFERENCE_MANUAL.md)
- [CLI_USER_MANUAL.md](CLI_USER_MANUAL.md)
- [CLI_GRAMMAR_UNIFICATION_SPEC.md](CLI_GRAMMAR_UNIFICATION_SPEC.md)

## 11. Diagnostics and Reporting

Purpose: cover the system's reporting, diagnostics, evidence products, and the
reason the project is more than a simple bringup harness.

Current state:

- Implemented now: local device reports, CAN diagnostics, JSON report output,
  PCAP/PCAPNG capture, and AI-assisted triage inputs.
- Implemented now: a strong emphasis on evidence collection.
- Partial / inconsistent: some diagnosis ambitions are still ahead of
  implementation.

What the project does well here:

- combines local and passive evidence
- produces machine- and human-readable outputs
- treats reports as workflow tools, not decoration

What remains difficult:

- diagnosis quality is only as good as contract discipline and profile accuracy
- too much ambition in diagnosis can tempt overclaiming
- passive evidence must be presented carefully to avoid false certainty

Relevant docs:

- [AI_DIAGNOSIS.md](AI_DIAGNOSIS.md)
- [MOTOR_DIAGNOSIS_SPEC.md](MOTOR_DIAGNOSIS_SPEC.md)
- [CAN Bus DIagnostic Feature Specification.md](CAN%20Bus%20DIagnostic%20Feature%20Specification.md)
- [SPEC_BREAK_AND_ERROR_OPERATOR_SURFACES.md](SPEC_BREAK_AND_ERROR_OPERATOR_SURFACES.md)

## 12. Topology, Editor, and Live View

Purpose: cover one of the most ambitious and least-settled parts of the
project.

Current state:

- Partial / inconsistent: topology currently sits between implemented graph
  behavior and older neighbor/diagram mental models.
- Implemented now: topology editor, stored topology section, and read/report
  surfaces.
- Spec / research only in places: full normalized graph semantics, richer
  traversal, and future diagnosis use.

Why topology matters:

- it is the only route to serious topology-aware diagnostics
- it connects physical layout, operator understanding, and inference
- it becomes a shared semantic model across CLI, editor, and diagnosis

What was weak:

- neighbor-based thinking stayed around too long
- diagram metadata and semantic truth were too intertwined
- the feature surface grew before the graph model became authoritative

Current best direction:

- canonical graph truth
- edges and ports as first-class semantics
- neighbors as derived views only
- no raw JSON walking for topology semantics

Relevant docs:

- [FEATURE_SPEC_TOPOLOGY_UPGRADE.md](FEATURE_SPEC_TOPOLOGY_UPGRADE.md)
- [FEATURE_SPEC_LIVE_TOPOLOGY_OPS.md](FEATURE_SPEC_LIVE_TOPOLOGY_OPS.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)

## 13. Test Authoring and Robot Test DSL

Purpose: describe the evolution from manual bringup actions to data-driven and
DSL-driven test authoring.

Current state:

- Implemented now: data-driven tests and test sets
- Implemented now: CLI authoring surfaces
- Implemented now: Robot Test DSL with growing runtime support
- Partial / inconsistent: the full semantic surface is still expanding and not
  every concept is equally mature

Why this matters:

- repeated bringup actions should not require code changes
- tests turn operator knowledge into reusable artifacts
- DSL work is one of the main ways the project becomes more than a one-off tool

What has gone well:

- device labels as references enable reuse
- CLI authoring reduces JSON pain
- the DSL creates a path toward richer repeatable diagnostics

What has been costly:

- semantic growth creates validation pressure
- runtime support must stay aligned with compiler/serializer/docs
- authoring usability and strict semantic correctness pull in different
  directions

Relevant docs:

- [USER_GUIDE_ROBOT_TEST_DSL.md](USER_GUIDE_ROBOT_TEST_DSL.md)
- [FEATURE_SPEC_ROBOT_TEST_DSL_CLI.md](FEATURE_SPEC_ROBOT_TEST_DSL_CLI.md)
- [FEATURE_SPEC_TEST_AUTHORING.md](FEATURE_SPEC_TEST_AUTHORING.md)
- [CLI_TEST_AUTHORING_USER_GUIDE.md](CLI_TEST_AUTHORING_USER_GUIDE.md)

## 14. User and Operator Surfaces

Purpose: describe how the project exposes itself to users and why surface
coherence matters.

Major surfaces:

- Xbox/local robot controls
- console reports
- Bringup Control UI
- Bridge CLI
- TCP UI protocol
- topology editor
- Shuffleboard/dashboard-related views

What matters:

- every surface has a different user and failure mode
- local safety and remote control must never be confused
- operator-facing consistency matters more than implementation neatness

What remains a challenge:

- too many surfaces can drift in semantics or wording
- some surfaces are product-like, others are still engineering-heavy
- the project needs a more deliberate map of which surface is for which user

Relevant docs:

- [OPERATOR_SURFACES.md](OPERATOR_SURFACES.md)
- [TCP_UI_PROTOCOL.md](TCP_UI_PROTOCOL.md)
- [USER_GUIDE.md](USER_GUIDE.md)

## 15. Testing, Regression, and Verification History

Purpose: treat testing as a core part of the system design rather than a final
checklist.

Current state:

- Implemented now: multiple documented test procedures
- Implemented now: maintained regression runner and suites
- Implemented now: both local-only and connected validation paths
- Still true: some areas remain harder to validate than others, especially rich
  UI/editor behavior and hardware-specific interactions

Why testing became central:

- the project has many contracts and surfaces
- regressions are easy when semantics are spread across code and docs
- hardware workflows are expensive to rediscover under pressure

What was learned:

- local/offline regression matters because hardware access is limited
- connected non-motion regression is valuable because robot integration matters
- topology and CLI changes need dedicated regression coverage

What still needs honesty:

- not all implemented features are equally well tested
- some historical testing lived in manual plans longer than ideal
- the repo has many test docs because the problem space is genuinely varied, not
  because a single clean test story already exists

Relevant docs:

- [TESTING.md](TESTING.md)
- [TESTING_WINDOWS_OFFLINE.md](TESTING_WINDOWS_OFFLINE.md)
- [USER_GUIDE_REGRESSION_RUNNER.md](USER_GUIDE_REGRESSION_RUNNER.md)
- [TEST_PROCEDURE_ZERO_CONFIG.md](TEST_PROCEDURE_ZERO_CONFIG.md)
- [WORKFLOW_01_NEW_ROBOT_BRINGUP.md](WORKFLOW_01_NEW_ROBOT_BRINGUP.md)

## 16. Cross-Cutting Constraints and Hard Rules

Purpose: gather the rules that repeatedly shape implementation choices.

Hard constraints:

- 20 ms robot loop budget
- report printing must be throttled
- PC CAN tool is read-only
- Windows-first host workflows
- Java/Python NT contract stability
- generated artifacts must stay synchronized
- hardware configuration should remain data-driven
- executable code should avoid stray literals in favor of constants

These are not cosmetic rules. They are the difference between a usable system
and a fragile one.

## 17. Architectural Tensions, Mistakes, and Debt

Purpose: state the uncomfortable truths directly.

Major tensions:

- ideal layering versus practical existing code shape
- operator stability versus refactor freedom
- one big unified config versus increasing semantic complexity
- topology ambition versus implementation maturity
- spec volume versus implementation coherence

Named anti-patterns that have shown up:

- duplicated truth
- raw JSON walking for semantic decisions
- neighbor-as-truth
- giant handler/coordinator files
- surface-specific logic that should have been shared-service logic
- spec-first expansion without enough normalization underneath

Things we thought were core but are no longer core:

- neighbor tables as long-term topology truth
- diagram metadata as enough topology semantics
- relying on ad hoc command growth without a stronger semantic core

Technical debt that still matters:

- too many overlapping docs with mixed freshness
- some features are broader in spec than in implementation
- some implementation paths still encode older mental models

## 18. Documentation State and Needed Split

Purpose: explain the current documentation problem and where this new master
document fits.

Current reality:

- the repo has many useful documents
- the documents are not well enough unified by one candid master narrative
- some docs are stable references, some are directional specs, some are test
  runbooks, and some are effectively historical artifacts

Why this new doc exists:

- to become the blunt, high-level project map
- to expose contradictions and stale mental models
- to seed later split docs at multiple levels

Suggested later split direction:

- project overview and positioning
- architecture and runtime contracts
- config/data model
- CLI/operator surfaces
- topology and diagnosis
- test authoring and DSL
- testing/regression strategy
- historical reversals and architectural lessons

## 19. Future Direction

Purpose: separate committed, likely, and speculative direction.

### 19.1 Near-term committed direction

- strengthen shared host-side semantic layers
- finish topology graph normalization and edge-native truth
- keep CLI/operator contracts stable during refactors
- continue investing in regression automation
- keep dual-source diagnostics as a foundational principle

### 19.2 Medium-term probable direction

- split large master docs into clearer families
- tighten config lifecycle and migration behavior
- improve topology/editor/live-view coherence
- continue moving reusable semantics into shared services
- improve test authoring ergonomics without weakening correctness

### 19.3 Speculative or research direction

- multi-observer topology-aware pit diagnosis
- richer inferred topology and fault-localization overlays
- stronger reverse-engineering of CAN traffic semantics
- more automated explanation and guided diagnosis

### 19.4 What the project is not

- not a vendor-tool replacement in every dimension
- not a generic robotics architecture framework
- not a CAN traffic transmitter or active bus manipulator on the PC side
- not a finished diagnosis oracle
- not a substitute for disciplined hardware workflow

## 20. Glossary and Terminology Cleanup

Purpose: stabilize overloaded terms that have been used inconsistently.

Terms that need disciplined use:

- profile: host configuration membership and related per-profile data
- active profile: must distinguish host-local editing context from robot runtime
  context
- topology: semantic graph truth, not merely diagram layout
- diagram: rendering/editor metadata, not automatically the topology truth
- neighbor: derived view, not canonical record type
- bridge: can mean CAN/NT bridge, TCP bridge CLI context, or future network
  bridging; use precisely
- report: robot-side throttled output, not every summary blob in the repo
- test: data-driven bringup test, DSL test, or broader regression test; say
  which one
- observed versus inferred: passive evidence versus diagnosis conclusion

## Appendix A. Repo Structure Map

Purpose: point to the main code locations at a useful level.

- Java robot bringup code: `src/main/java/...`
- Deploy/runtime config artifacts: `src/main/deploy/`
- Canonical config and shared data: `data/`
- Python CAN/NT tooling: `tools/can_nt/`
- Python topology tooling: `tools/can_topology/`
- Shared Python libraries: `tools/common/`
- Tests and regressions: `tests/`, plus tool-specific test modules

## Appendix B. Document Map / Bibliography

Purpose: group major existing docs by topic and note their role in the current
documentation landscape.

### B.1 High-level system docs

- [README.md](../README.md): current high-level project entry point
- [ARCHITECTURE.md](ARCHITECTURE.md): strongest current architecture anchor
- [USER_GUIDE.md](USER_GUIDE.md): broad user-facing system guide

### B.2 Contracts and protocols

- [NT_CONTRACT.md](NT_CONTRACT.md)
- [TCP_UI_PROTOCOL.md](TCP_UI_PROTOCOL.md)
- [TCP_UI_PROTOCOL_QUICK_REF.md](TCP_UI_PROTOCOL_QUICK_REF.md)
- [FEATURE_SPEC_UNIFIED_STATUS_CODES_PY_JAVA.md](FEATURE_SPEC_UNIFIED_STATUS_CODES_PY_JAVA.md)
- [GENERATED_ARTIFACTS_POLICY.md](GENERATED_ARTIFACTS_POLICY.md)

### B.3 CLI and operator surfaces

- [BRIDGE_CLI_FULL_SPEC.md](BRIDGE_CLI_FULL_SPEC.md)
- [BRIDGE_CLI_DESIGN.md](BRIDGE_CLI_DESIGN.md)
- [CLI_REFERENCE_MANUAL.md](CLI_REFERENCE_MANUAL.md)
- [CLI_USER_MANUAL.md](CLI_USER_MANUAL.md)
- [OPERATOR_SURFACES.md](OPERATOR_SURFACES.md)

### B.4 Config and schema

- [bringup_profiles_schema.md](bringup_profiles_schema.md)
- [bringup_profiles_schema_erd.md](bringup_profiles_schema_erd.md)
- [PROFILE_SCHEMA_REFACTOR.md](PROFILE_SCHEMA_REFACTOR.md)
- [FEATURE_SPEC_CONFIG_STORE.md](FEATURE_SPEC_CONFIG_STORE.md)
- [FEATURE_SPEC_CONFIG_RECOVERY_UNIFIED.md](FEATURE_SPEC_CONFIG_RECOVERY_UNIFIED.md)

### B.5 Topology and diagnosis

- [FEATURE_SPEC_TOPOLOGY_UPGRADE.md](FEATURE_SPEC_TOPOLOGY_UPGRADE.md)
- [FEATURE_SPEC_LIVE_TOPOLOGY_OPS.md](FEATURE_SPEC_LIVE_TOPOLOGY_OPS.md)
- [SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md](SPEC_TOPOLOGY_FAULT_INFERENCE_MODEL.md)
- [FEATURE_SPEC_MULTI_OBSERVER_CAN_FAULT_LOCALIZATION.md](FEATURE_SPEC_MULTI_OBSERVER_CAN_FAULT_LOCALIZATION.md)
- [FEATURE_SPEC_PIT_ROBOT_DIAGNOSIS_FIRST_PASS.md](FEATURE_SPEC_PIT_ROBOT_DIAGNOSIS_FIRST_PASS.md)
- [AI_DIAGNOSIS.md](AI_DIAGNOSIS.md)

### B.6 Test authoring and DSL

- [USER_GUIDE_ROBOT_TEST_DSL.md](USER_GUIDE_ROBOT_TEST_DSL.md)
- [FEATURE_SPEC_ROBOT_TEST_DSL_CLI.md](FEATURE_SPEC_ROBOT_TEST_DSL_CLI.md)
- [FEATURE_SPEC_TEST_AUTHORING.md](FEATURE_SPEC_TEST_AUTHORING.md)
- [CLI_TEST_AUTHORING_USER_GUIDE.md](CLI_TEST_AUTHORING_USER_GUIDE.md)

### B.7 Testing and workflows

- [TESTING.md](TESTING.md)
- [TESTING_WINDOWS_OFFLINE.md](TESTING_WINDOWS_OFFLINE.md)
- [USER_GUIDE_REGRESSION_RUNNER.md](USER_GUIDE_REGRESSION_RUNNER.md)
- [WORKFLOW_01_NEW_ROBOT_BRINGUP.md](WORKFLOW_01_NEW_ROBOT_BRINGUP.md)
- [TEST_PROCEDURE_ZERO_CONFIG.md](TEST_PROCEDURE_ZERO_CONFIG.md)

### B.8 Historical / directional / likely-overlapping specs

- numerous `FEATURE_SPEC_*` and `SPEC_*` documents remain valuable as detailed
  topic references, but not all should be assumed equally current
- future cleanup should explicitly classify docs as:
  - current reference
  - active direction
  - partial implementation note
  - historical/superseded
