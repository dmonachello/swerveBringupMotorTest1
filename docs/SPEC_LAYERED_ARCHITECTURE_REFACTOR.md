SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Spec: Incremental Refactor Toward Layered Architecture

## Purpose

Define a practical, incremental refactor plan for moving the project toward the system-wide layered architecture described in `docs/ARCHITECTURE.md`.

This spec is intended for Codex. It should guide real implementation work without forcing a risky full rewrite.

## Context

The project already has meaningful structure and should **not** be rewritten from scratch. The goal is to refactor toward clearer layer ownership over multiple passes.

The system-wide layering model is:
1. Hardware and Transport Layer
2. Adapter and Protocol Layer
3. Domain Logic Layer
4. Workflow and Application Service Layer
5. Presentation and Operator Surface Layer
6. Contract and Specification Layer

This spec focuses on making the code follow those layers more consistently.

## Important Current-State Note

This spec has **not** yet been executed as a full layered-architecture refactor plan.

However, the repo is also **not** at a blank starting point. Before this spec is applied, the codebase already includes meaningful architecture progress, especially in the Java command path:
- `BridgeUiIngressPolicy`
- `BridgeUiCommandExecutor`
- `BridgeUiCommandDispatcher`
- Java command-family extraction
- Java command-path tests
- Python-side facade and transport-boundary improvements

Therefore, this spec must be executed from the **current repo baseline**, not from an assumed pre-refactor state.

Implications:
- The Java/roboRIO side is already partially advanced in layering for the UI command path.
- The biggest remaining architectural value is now on the Driver Station PC / Python side.
- Workflow/Application Service Layer work is now the highest-priority architectural gap.
- Java work under this spec should be treated primarily as cleanup, hardening, ownership tightening, and selective layering improvements where they clearly pay off.
- Python/PC work under this spec should be treated as the primary frontier for layered-architecture progress.

## Key Principle

Do **not** reorganize the project just to make folders match the layer names.

Instead:
- move behavior to the correct ownership layer
- reduce cross-layer leakage
- centralize shared semantics
- introduce workflow/application services where the product currently relies on docs and operator habits
- keep externally visible behavior stable unless a bug requires correction

## Big Goals

The refactor should improve these architectural properties:
- Presentation layers become thinner.
- Domain logic becomes more explicit and reusable.
- Workflow logic becomes first-class in code, not only in docs.
- Shared config/test/diagnostic semantics are centralized.
- Cross-language and cross-surface contracts are easier to reason about.
- Operator workflows become easier to support consistently.

## Priority Guidance From Current Baseline

When tradeoffs are required, prioritize the refactor work in this order:

1. Shared config/profile lifecycle semantics.
2. Workflow/Application Service Layer for primary workflows, especially `WORKFLOW_01_NEW_ROBOT_BRINGUP`.
3. Shared test-domain semantics.
4. Shared diagnostics normalization semantics.
5. Thinning Python presentation layers (`bridge_cli.py`, `bringup_ui.py`, related host-side surfaces).
6. Java-side cleanup/hardening/ownership tightening where it clearly improves layering.
7. Cosmetic file/package moves.

Interpretation rule:
- If a Java-side layered split is already materially present, do not redo it just because the spec mentions that architectural direction.
- Prefer to spend effort where the architecture is still weak in practice, which is now primarily the PC/Python and workflow/application layers.

## Non-Goals

Do not do these as part of this effort unless specifically required:
- redesign the TCP UI protocol
- redesign the NT contract
- rewrite working robot runtime code for style only
- force identical Java/Python implementations
- aggressively move files just to look cleaner
- create a giant generic "core" library with vague ownership

## Current Architectural Observations

The project already has strong pieces in place:
- Hardware/transport access exists on both robot and PC sides.
- Adapter/protocol code exists for device wrappers, TCP session, profile loading, visibility, and ingress policy.
- Domain logic exists for bring-up, tests, groups, session commands, profile commands, reports, and runtime actions.
- Presentation layers exist for CLI, UI, and topology editor.
- Contract/spec docs already exist for TCP, command handler architecture, workflow, and readiness.

The biggest current layering gaps are:
- Workflow/Application Service Layer is weak in code.
- Presentation layers still know too much in places, especially on the PC/Python side.
- Shared config lifecycle semantics are still spread across tools.
- Shared diagnostics/test semantics are not centralized enough.
- Some orchestration classes still contain family-specific helper leakage.

Important interpretation:
- The orchestration/leakage point still applies to both sides, but it is now more urgent on the host-side Python surfaces than on the already-improved Java command path.

## Required Refactor Strategy

Implement this as a sequence of **incremental architecture passes**, not one giant change.

Each pass should:
- produce a measurable ownership improvement
- preserve behavior
- include tests where appropriate
- leave the repo buildable/runnable

## Execution Cadence and Quality Gates

Treat this refactor as a sequence of small, mergeable milestones.

Each milestone should be scoped to one clear ownership move (for example, one service extraction or one surface-thinning update).

For each milestone:

- run targeted tests for the changed area before and after the refactor
- run a broader compile/test pass before merging
- keep protocol/contract behavior stable unless a correctness bug is fixed
- avoid bundling unrelated cleanup in the same milestone

Recommended weighting for implementation effort:

- 40% high-value ownership changes (shared config/workflow services)
- 40% boundary and regression test coverage
- 20% docs/alignment and cleanup

## Pass 1: Establish Shared Layer Ownership Rules

### Objective
Make the layer boundaries explicit in code organization and design decisions before moving more logic.

### Required work
1. Read and follow:
   - `docs/ARCHITECTURE.md`
   - `docs/COMMAND_HANDLER_ARCHITECTURE.md`
   - `docs/WORKFLOW_01_NEW_ROBOT_BRINGUP.md`
   - `docs/RELEASE_1_0_READINESS.md`
2. Audit major modules and classify them by layer.
3. Add or update package/module comments where useful so ownership is explicit.
4. Do not make large behavior changes in this pass.

### Deliverable
A lightweight ownership cleanup that makes it easier to implement the later passes consistently.

## Pass 2: Strengthen the Domain Logic Layer

### Objective
Centralize domain semantics that are currently spread across surfaces or helper code.

### Current-state interpretation
- On the Java side, this pass is partly advanced already in the UI command path. Treat further Java work here as selective cleanup and hardening, not wholesale restructuring.
- On the Python side, this pass is still a major architectural task and should receive most of the implementation effort.

### Required targets

## A. Config/Profile Lifecycle Domain
Create or strengthen a shared config lifecycle domain module on the Python side.

### New or expanded module area
Use a coherent module area under `tools/common/` or similar, for example:
- `tools/common/profiles/`
- `tools/common/config_lifecycle/`

### Responsibilities
Centralize logic for:
- canonical config path ownership
- deploy copy path ownership
- config loading
- config validation entrypoints
- sync/deploy copy generation semantics
- profile lookup and resolution
- device lookup by label
- tests lookup by profile
- source reporting (`canonical`, `deploy`, `runtime`, `local`)
- host-vs-robot context semantics where feasible

### Rules
- remove duplicated path/source-of-truth semantics from individual surfaces where practical
- keep the canonical/deploy/runtime model explicit
- preserve current behavior

## B. Test Authoring and Validation Domain
Strengthen the host-side test domain as a first-class layer.

### New or expanded module area
Use or extend a coherent area such as:
- `tools/common/tests/`
- or expand existing test authoring modules into a clearer domain package

### Responsibilities
Centralize:
- test models
- test validation
- device-to-test reference validation
- test generation defaults/templates
- test set selection semantics
- per-profile test lookup semantics

### Goal
The robot should consume a validated clean representation; host-side authoring/generation/validation should own more of the complexity.

## C. Diagnostics Domain Normalization
Create or strengthen a shared diagnostics domain layer on the Python side.

### New or expanded module area
Suggested:
- `tools/common/diagnostics/`

### Responsibilities
Normalize and centralize semantics for:
- local health vs CAN visibility vs console-derived warnings
- visible vs missing vs stale vs unknown
- evidence snapshot shape
- normalized diagnostics results consumed by CLI/UI/reporting

### Rule
Multiple presentation surfaces should consume shared diagnostic meaning, not invent their own interpretation.

## Pass 3: Introduce Workflow and Application Service Layer

### Objective
Make the product workflows explicit in code, not just in docs.

This is the most important architectural gap.

### Current-state interpretation
This pass is now the highest-value unfinished architectural work in the repo.
It should be treated as the center of gravity of this spec.

## A. Workflow 01 service: New robot bring-up
Create a first-class workflow/application service for the incremental new-robot bring-up flow.

### New module area
Suggested:
- `tools/can_nt/workflows/new_robot_bringup.py`
- or a shared `tools/workflows/` package if that fits better

### Responsibilities
Coordinate the primary workflow:
- add one component
- create or select focused test(s)
- validate config and tests
- sync deploy copy
- deploy/apply guidance state
- run focused verification step(s)
- report next expected action
- collect evidence guidance

### Important note
This does **not** need to perform all deployment itself. It can orchestrate workflow semantics and expose reusable steps/services used by CLI/UI/docs.

## B. Validate/Sync workflow service
Create a reusable application service for:
- validate canonical config
- validate tests
- stamp version/hash if needed
- write deploy copy
- report source/state clearly

### Goal
Make validate+sync behavior more unified across tools and docs.

## C. Focused component verification workflow service
If the previous services do not cover it naturally, introduce an application service that represents:
- one device/component under test
- expected verification steps
- expected evidence
- outcome classification (`pass`, `fail`, `ambiguous`)

### Goal
Reduce the amount of workflow meaning scattered across CLI/UI/docs.

## Pass 4: Thin the Presentation Layers

### Objective
Make presentation layers ask for outcomes instead of re-owning meaning-heavy logic.

### Current-state interpretation
This pass now applies most strongly to the host-side Python surfaces.
For Java, most presentation-layer work under this spec should be interpreted as cleanup of residual orchestration/helper leakage, not major new decomposition unless clearly justified.

## A. Bridge CLI
Refactor `tools/can_nt/bridge_cli.py` further so it becomes more clearly:
- parser/orchestrator/presenter

and less a large owner of business logic.

### Required direction
- move domain logic into services/facades where practical
- keep parser/AST behavior separate
- keep transport/session behavior behind facade/transport layers
- keep output formatting in presentation-focused code

### Preferred decomposition
The CLI should rely more on:
- profile/config service
- tests service
- diagnostics service
- robot control service
- workflow services

## B. Bringup Control UI
Refactor `tools/can_nt/bringup_ui.py` further so it becomes more clearly:
- widget/layout/state presentation
- runtime command invoker via shared services
- status/result renderer

### Required direction
- do not let UI code own profile/test/diagnostic semantics that can live below
- keep command behavior shared with CLI through services/facades where possible

## C. Topology editor
Do not force topology-editor behavior into runtime layers, but do reduce duplicated config lifecycle semantics where possible.

### Required direction
- topology editor remains an authoring surface
- shared config lifecycle rules should be pulled from shared modules where practical
- editor-only layout semantics remain local to the editor

## Pass 5: Continue Shrinking Orchestration Classes

### Objective
Reduce residual helper leakage in orchestration classes that still carry too much lower-layer behavior.

### Current-state interpretation
- `BridgeUiCommandHandler.java` is now primarily a cleanup/hardening target under this spec.
- `tools/can_nt/bridge_cli.py` and related Python host-side surfaces remain major architectural targets under this pass.

## Targets
- `BridgeUiCommandHandler.java`
- `tools/can_nt/bridge_cli.py`
- any other large classes still mixing orchestration with family/domain behavior

### Required direction
- move family-specific helpers/constants into domain-family owners where practical
- keep orchestration classes focused on wiring, sequencing, and lifecycle
- narrow dependency adapters/interfaces

### Important note
Do this incrementally. Do not churn stable code unless ownership is clearly wrong.

## Pass 6: Strengthen the Contract and Specification Layer

### Objective
Make shared contracts easier to maintain and align with code.

### Required direction
Create or strengthen a clearer ownership area for cross-surface contracts.

### Suggested contract areas
- TCP UI protocol
- NT contract
- config/profile schema
- status/result semantics
- diagnostics semantics
- host-vs-robot context semantics

### Acceptable implementation forms
- stronger doc cross-references
- centralized contract helper modules on Python side
- clearer Java status/contract ownership
- explicit schema/contract helper packages

### Rule
Do not just add docs; also align code ownership where contract logic is currently diffuse.

## Required Directory/Module Direction

The exact final file layout may vary, but the following ownership direction is required.

## Python
Move toward something conceptually like this:

```text
tools/
  common/
    profiles/
      models.py
      lifecycle.py
      validation.py
      sources.py
    tests/
      models.py
      validation.py
      generation.py
    diagnostics/
      models.py
      normalize.py
    contracts/
      tcp_ui.py
      nt_contract.py
      status_codes.py

  can_nt/
    bridge_cli.py
    bringup_ui.py
    bridge_session.py
    bridge_robot_control_facade.py
    services/
      profiles_service.py
      tests_service.py
      diagnostics_service.py
      runtime_service.py
      groups_service.py
    workflows/
      new_robot_bringup.py
      validate_sync_workflow.py
```
```

This is a direction, not a mandatory exact tree.

## Java
Move toward something conceptually like this where practical:

```text
src/main/java/frc/robot/
  ui/
    ingress/
    execution/
    output/
    model/
  profiles/
    runtime/
  tests/
    runtime/
    model/
  diagnostics/
    reporting/
    model/
  status/
```
```

Do not force risky package moves if the benefit is low. Prioritize ownership correctness over cosmetic movement.

Current-state note:
- Because the Java command path has already been materially improved, package reshaping on the Java side is now optional and lower priority than host-side service/workflow layering.
- Prefer Java ownership cleanup, dependency narrowing, and hardening over broad package churn.

## Layer Ownership Rules

Codex must follow these rules during the refactor:

### Hardware and Transport Layer
Owns:
- vendor APIs
- sockets
- serial/slcan
- NetworkTables client/server transport
- filesystem I/O primitives

Should not own:
- workflow semantics
- business rules
- operator messaging beyond low-level transport errors

### Adapter and Protocol Layer
Owns:
- parsing raw payloads
- vendor/wire adaptation
- session parsing
- config file parsing/loading
- normalization from raw transport to internal models

Should not own:
- product workflow decisions
- presentation behavior

### Domain Logic Layer
Owns:
- profile semantics
- test semantics
- command-family semantics
- diagnostics meaning
- group semantics
- stop-latch and safety semantics
- result/status semantics

Should not be duplicated across multiple surfaces.

### Workflow and Application Service Layer
Owns:
- multi-step user-success flows
- sequencing of domain actions
- canonical workflow behavior
- next-step guidance

Should not become a UI layer.

### Presentation Layer
Owns:
- text/UI rendering
- input gathering
- table/JSON/pretty output
- widgets/menus/command entry

Should not own:
- config lifecycle semantics
- business rule duplication
- protocol semantics
- workflow meaning where a service can own it

### Contract Layer
Owns:
- stable shared expectations
- schemas/protocols/status catalogs/docs alignment

Should constrain both Java and Python implementation.

## Deliverables

This refactor effort should produce:

### Important delivery rule
Do not treat the deliverables as requiring equal effort on both sides.
From the current baseline:
- Java deliverables are mainly selective ownership cleanup, hardening, and tests where useful.
- Python/PC deliverables are the primary implementation focus for the layered refactor.

### Production code changes
- new or expanded shared config/profile lifecycle modules
- new or expanded tests domain modules
- new or expanded diagnostics normalization modules
- new workflow/application service modules
- thinner CLI/UI/orchestration code with logic moved downward where appropriate
- reduced residual helper leakage in orchestration classes

### Tests
Add or expand tests for newly introduced shared services/workflow services and any moved domain logic.

At minimum:
- tests for shared config lifecycle semantics
- tests for test validation/generation semantics if modified
- tests for workflow service behavior if introduced
- keep existing regression coverage passing

### Documentation alignment
Update docs if code ownership changes materially:
- `docs/ARCHITECTURE.md`
- `docs/COMMAND_HANDLER_ARCHITECTURE.md`
- `docs/WORKFLOW_01_NEW_ROBOT_BRINGUP.md`
- any workflow or contract docs directly affected

## Implementation Order

Use this order unless a strong code reason requires a different one:

1. establish ownership comments and module intent
2. centralize config/profile lifecycle semantics
3. introduce workflow/application services for Workflow 01 and validate/sync
4. centralize test-domain semantics
5. centralize diagnostics semantics
6. refactor CLI/UI to consume those services
7. trim orchestration/helper leakage
8. align docs and tests

Implementation note from current baseline:
- Steps 2, 3, 4, 5, and 6 should be understood as primarily PC/Python-side work unless a Java-side ownership problem clearly blocks them.
- Java-side work under step 7 should be incremental and justified by clear ownership leakage, not by architectural purity alone.

## Verification Cadence

Use this test cadence throughout implementation:

1. after each pass, run targeted tests for that pass
2. after each phase boundary, run full Java compile/tests and relevant Python regressions
3. after any contract-sensitive change, rerun protocol/regression checks immediately
4. before finalizing, run full compile/tests/regressions end-to-end

Minimum commands per phase boundary should include project compile/tests and the current CLI regression suite used by the team.

The refactor is not considered complete for a pass until its tests are green.

## Constraints

- Do not rewrite the whole project.
- Do not change external behavior unless needed for correctness.
- Prefer incremental passes that preserve a working system.
- Prefer explicit domain ownership over generic abstractions.
- Do not create a vague mega-core shared library.
- Keep Java/Python implementations language-appropriate while sharing semantics.
- Prioritize shared semantics and workflow ownership over cosmetic file moves.

## Success Criteria

This layered-architecture refactor is successful when:
- workflow/application services exist for the primary product workflows
- config/profile lifecycle semantics are more centralized
- test semantics are more centralized
- diagnostics semantics are more centralized
- presentation layers are thinner and rely more on services/facades
- orchestration classes contain less family/domain helper leakage
- cross-surface behavior is more consistent
- docs and code ownership align more clearly with the layered model
- builds/tests/regressions still pass

From the current repo baseline, the strongest evidence of success should come from:
- new shared host-side services and workflow modules
- thinner Python presentation surfaces
- clearer central ownership of config/test/diagnostics semantics
- Java-side cleanup/hardening that improves ownership without unnecessary churn
- each pass has explicit test evidence (targeted + boundary/full-suite where applicable)

## Implementation Note For Codex

Treat this as an incremental architecture refactor, not a rewrite.

The main architectural gap to close is the weak Workflow/Application Service Layer.

Important current-state reminder:
- This spec has not yet been executed as a whole.
- However, the current repo already includes meaningful Java-side command-path layering progress.
- Therefore, do not spend equal effort on both sides by default.

Default interpretation for implementation:
- Java/roboRIO side: selective cleanup, hardening, ownership tightening, and test improvements where useful.
- Driver Station PC / Python side: primary implementation focus for layered-architecture progress.

If tradeoffs are required, prioritize in this order:
1. shared config/profile lifecycle semantics
2. workflow/application services for Workflow 01
3. shared test-domain semantics
4. shared diagnostics normalization
5. thinner Python presentation layers
6. Java-side cleanup/hardening where ownership is still weak
7. cosmetic package/file moves

At the end, report:
- modules/services added or expanded
- responsibilities moved between layers
- surfaces made thinner
- docs updated
- remaining gaps that should be deferred to later passes
- which work was primarily Java-side vs PC/Python-side

