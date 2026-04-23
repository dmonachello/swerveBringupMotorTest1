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
- Presentation layers still know too much in places.
- Shared config lifecycle semantics are still spread across tools.
- Shared diagnostics/test semantics are not centralized enough.
- Some orchestration classes still contain family-specific helper leakage.

## Required Refactor Strategy

Implement this as a sequence of **incremental architecture passes**, not one giant change.

Each pass should:
- produce a measurable ownership improvement
- preserve behavior
- include tests where appropriate
- leave the repo buildable/runnable

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
3. centralize test-domain semantics
4. centralize diagnostics semantics
5. introduce workflow/application services for Workflow 01 and validate/sync
6. refactor CLI/UI to consume those services
7. trim orchestration/helper leakage
8. align docs and tests

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

## Implementation Note For Codex

Treat this as an incremental architecture refactor, not a rewrite.

The main architectural gap to close is the weak Workflow/Application Service Layer.

If tradeoffs are required, prioritize in this order:
1. shared config/profile lifecycle semantics
2. workflow/application services for Workflow 01
3. thinner presentation layers
4. diagnostics/test domain centralization
5. cosmetic package/file moves

At the end, report:
- modules/services added or expanded
- responsibilities moved between layers
- surfaces made thinner
- docs updated
- remaining gaps that should be deferred to later passes
