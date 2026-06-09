SPEC_STATUS: PROPOSED

# Spec: Host Layering And Shared Services Refactor

## Purpose

Define a concrete refactor plan for improving layering and shared-code usage across the host-side Python tools.

This spec focuses on the Driver Station / PC-side code:

- `tools/can_nt/`
- `tools/common/`
- `tools/can_topology/` where it intersects shared host-side semantics

The goal is to reduce cross-surface drift, move reusable behavior out of the CLI and UI entrypoints, and make the intended layered architecture more real in code.

## Scope

Purpose: define what this spec covers and what it does not.

This spec covers:

- host-side layering improvements
- shared workflow/service extraction
- shared config, DSL, runtime-state, and test-execution semantics
- reducing duplicated or surface-specific orchestration in CLI and UI

This spec does not require:

- a rewrite of the robot-side Java architecture
- a redesign of the REST command protocol
- a redesign of the NetworkTables contract
- a full UI rewrite
- a full CLI rewrite

## Context

Purpose: describe the current host-side state that motivates this refactor.

The host code already has meaningful shared pieces:

- `BridgeSession` provides shared REST transport and session behavior
- `bridge_ops.py` provides shared robot-facing operations
- `tools/common/config_lifecycle/` provides shared config lifecycle semantics
- `tools/common/workflows/workflow01_service.py` provides a first workflow service
- `tools/common/robot_test_dsl/` provides a real DSL compiler/validator domain layer
- `tools/common/` already contains shared topology, test, and utility modules

However, the host presentation layers still own too much product meaning:

- `bridge_cli.py` is both a presentation layer and a major workflow/orchestration layer
- `bringup_ui.py` is both a presentation layer and a local workflow/orchestration layer
- some shared code exists, but it stops too low in the stack
- some important shared behavior is still implemented through surface-specific paths

## Main Current-State Findings

Purpose: record the main architecture issues this spec is intended to address.

### 1. UI Reuses CLI Internals Instead Of Shared DSL Services

Current problem:

- the UI creates a `BridgeCli`
- mutates private CLI state
- calls private CLI DSL methods
- persists the mutated payload back out

Implication:

- the CLI is acting as an accidental DSL service
- UI DSL behavior depends on private CLI implementation details
- DSL workflows are not owned by a dedicated shared service layer

### 2. Local Profile/Test Discovery Policy Is Split Across Surfaces

Current problem:

- profile and test discovery rules live partly in UI helpers
- CLI has its own local config and test-selection logic
- source precedence and default-set rules can drift

Implication:

- CLI and UI can diverge in what they think is available
- local config semantics are not owned by a shared query/repository layer

### 3. Shared Transport Exists, But Shared Command Workflow Policy Is Incomplete

Current problem:

- `BridgeSession` is shared
- higher-level command workflow policy is not
- handshake, pending-command gating, retry behavior, and command tracking still live largely in surfaces

Implication:

- the wire protocol is shared
- the operator-level command lifecycle is still partly surface-specific

### 4. `bridge_ops.py` Mixes Multiple Concerns

Current problem:

- `bridge_ops.py` contains wrappers, workflow logic, validation logic, payload shaping, and file-related behaviors

Implication:

- it is useful shared code, but not a clean ownership boundary
- surfaces either depend on a broad god-module or bypass it

### 5. Runtime-State And Test-Execution Semantics Are Not Shared Enough

Current problem:

- runtime-state fetch/parse/cache behavior is not clearly owned by one shared host-side layer
- test select/run/wait/result sequencing is not owned end-to-end by one shared workflow layer

Implication:

- CLI and UI can evolve different runtime/test behavior over time

### 6. Topology And Visibility Have Shared Pieces, But Shared Composition Can Improve

Current problem:

- shared topology parsing/rendering exists
- read-only runtime overlays and authoring/editor flows still have separate composition logic

Implication:

- the repo has shared primitives
- it can still gain from a stronger shared topology/runtime composition layer

## Desired Layering Model

Purpose: define the target host-side architectural layering for this refactor.

The intended host-side layering model is:

1. Transport and Integration Layer
2. Shared Domain and Service Layer
3. Workflow and Application Service Layer
4. Presentation Layer

### 1. Transport And Integration Layer

Responsibilities:

- REST transport
- CAN and NT integration
- file IO boundaries
- path resolution helpers
- capture/logging adapters

Examples:

- `BridgeSession`
- CANable/CAN/NT modules
- JSON IO helpers

### 2. Shared Domain And Service Layer

Responsibilities:

- shared config lifecycle semantics
- shared test and DSL semantics
- shared topology parsing/rendering
- shared visibility semantics
- shared normalized result objects

Examples:

- `tools/common/config_lifecycle/`
- `tools/common/tests_domain/`
- `tools/common/robot_test_dsl/`
- topology helpers

### 3. Workflow And Application Service Layer

Responsibilities:

- multi-step operator workflows
- command gating policy
- runtime/test execution sequencing
- config import/save/push flows
- profile activation workflows

Examples to add or expand:

- shared DSL workflow service
- local config repository/query service
- command workflow service
- runtime-state service
- test-execution workflow service

### 4. Presentation Layer

Responsibilities:

- CLI input and output behavior
- UI controls, dialogs, and view state
- topology editor interaction behavior

Rules:

- surfaces should invoke shared behavior
- surfaces should not own reusable semantics when those semantics are shared across multiple surfaces

## Refactor Goals

Purpose: state the desired outcomes of this refactor.

This refactor should:

- reduce direct CLI/UI ownership of shared product meaning
- remove cross-surface drift in config, DSL, runtime, and test semantics
- make shared workflows callable without depending on CLI or UI private methods
- make new host-side features easier to add once, then reuse across surfaces
- keep externally visible behavior stable unless a bug fix requires a correction

## Proposed Shared Modules And Responsibilities

Purpose: define the specific shared ownership areas to add or strengthen.

## A. Shared Local Config Repository And Query Service

### Goal

Create a shared host-side repository/query layer for `bringup_system.json` and related local config state.

### Responsibilities

- load canonical and deploy config copies
- expose profile inventory
- expose per-profile test inventory
- expose DSL store and test-set selection semantics
- persist config with shared sync rules
- report local dirty state and source metadata

### Desired outcomes

- UI and CLI stop implementing their own profile/test discovery logic
- local config read/write semantics are centralized

### Suggested module area

- `tools/common/config_lifecycle/` expansion
- or new coherent modules under `tools/common/profiles/` and `tools/common/tests_domain/`

## B. Shared DSL Workflow Service

### Goal

Replace the current pattern where the UI instantiates `BridgeCli` and calls private CLI DSL helpers.

### Responsibilities

- import DSL source into local config
- validate local DSL tests
- list DSL tests for a profile
- expose normalized DSL output
- own profile-aware DSL import/validate workflow semantics

### Desired outcomes

- CLI calls the DSL service
- UI calls the DSL service
- no host surface depends on CLI private DSL methods

### Suggested module area

- `tools/common/robot_test_dsl/` remains the domain engine
- add a higher-level host-side workflow/service module, for example:
  - `tools/common/robot_test_dsl/service.py`
  - or `tools/common/workflows/dsl_workflow_service.py`

## C. Shared Command Workflow And Session-State Service

### Goal

Move operator-level command lifecycle policy above `BridgeSession` into shared code.

### Responsibilities

- handshake policy
- pending-command gating
- retry or no-retry rules
- session ownership state
- connected/disconnected/handshaken/stale state interpretation
- command tracker semantics

### Desired outcomes

- CLI and UI stop each owning their own command lifecycle policy
- `BridgeSession` stays transport-focused

### Suggested module area

- `tools/can_nt/command_workflow_service.py`
- or a shared workflow/service area under `tools/common/workflows/`

## D. Shared Runtime-State Service

### Goal

Centralize runtime-state fetch, parse, normalize, and cache behavior.

### Responsibilities

- request runtime JSON
- parse and validate runtime payloads
- normalize common runtime views
- cache runtime state when appropriate
- expose a shared machine-readable result object

### Desired outcomes

- runtime-state behavior becomes consistent across CLI and UI
- later features can reuse one runtime-state path

## E. Shared Test-Execution Workflow Service

### Goal

Own the shared semantics for test select/run/wait/result behavior.

### Responsibilities

- selected-test workflow
- run-selected workflow
- run-all workflow where applicable
- wait/result polling semantics
- normalized test result interpretation

### Desired outcomes

- CLI and UI stop encoding test-execution sequencing independently

## F. Shared Profile Activation Workflow Service

### Goal

Own the shared semantics for push/select/activate/deactivate behavior.

### Responsibilities

- config push workflow
- profile selection workflow
- runtime activation/deactivation workflow
- shared gating rules and failure interpretation

### Desired outcomes

- profile/runtime workflow behavior is shared and explicit

## G. Shared Command Catalog Service

### Goal

Centralize generated command inventory loading and host-action merging.

### Responsibilities

- load generated command metadata
- merge host-local actions with robot-backed actions
- present a normalized command catalog to surfaces

### Desired outcomes

- UI-specific command catalog loading becomes shared
- future surfaces can reuse the same command inventory behavior

## H. Shared Output And Result Models

### Goal

Move from surface-specific text-first behavior toward shared result models.

### Responsibilities

- structured validation result objects
- structured workflow result objects
- structured command outcome objects
- structured runtime/test/DSL result summaries

### Desired outcomes

- surfaces format results differently if needed
- underlying meaning remains shared and machine-readable

## I. Shared Topology And Runtime Composition Service

### Goal

Centralize the composition of:

- config topology
- runtime overlays
- visibility overlays
- group overlays

into a shared host-side model before rendering.

### Responsibilities

- combine static topology with runtime and visibility state
- provide a shared composed view model
- support both read-only UI views and other reporting surfaces

### Desired outcomes

- topology-related surfaces share more than primitives
- composition drift between views is reduced

## J. Shared Dirty-State Service

### Goal

Centralize host-side unsaved-change semantics.

### Responsibilities

- track config dirty state
- track bindings/mappings/test/DSL dirty state
- expose shared “unsaved changes” semantics
- support workflow blocking and warnings consistently

### Desired outcomes

- UI and CLI stop interpreting unsaved local state differently

## Refactor Plan

Purpose: define an incremental execution order.

## Phase 1: Extract High-Value Shared Services

### Required work

1. Extract the shared DSL workflow service.
2. Extract the shared local config repository/query service.
3. Move UI DSL import/validate off CLI internals.
4. Update CLI to call the same shared DSL service.

### Success criteria

- UI no longer instantiates `BridgeCli` for DSL workflows
- CLI and UI use the same DSL service entrypoints
- profile/test discovery rules are no longer UI-local

## Phase 2: Introduce Shared Command Workflow Ownership

### Required work

1. Add a shared command workflow/session-state service.
2. Move handshake/pending/gating policy out of UI and CLI where practical.
3. Keep `BridgeSession` focused on transport mechanics.

### Success criteria

- session-state interpretation is shared
- command gating rules are shared
- CLI and UI use the same higher-level command lifecycle semantics

## Phase 3: Split `bridge_ops.py` By Concern

### Required work

Refactor `bridge_ops.py` into narrower ownership areas, for example:

- transport command wrappers
- config push/download workflows
- import/export planning helpers
- runtime/test workflow helpers

### Success criteria

- `bridge_ops.py` stops acting as a mixed-concern god-module
- surfaces can depend on smaller workflow/service modules

## Phase 4: Add Shared Runtime And Test Workflow Services

### Required work

1. Add shared runtime-state service.
2. Add shared test-execution workflow service.
3. Add shared profile activation workflow service.

### Success criteria

- runtime/test/profile workflow semantics are shared across surfaces
- CLI and UI no longer each own those flows independently

## Phase 5: Strengthen Shared Composition And Result Models

### Required work

1. Add shared output/result model structures where missing.
2. Add shared topology/runtime composition service.
3. Add shared dirty-state semantics.
4. Add shared command-catalog loading if still surface-specific.

### Success criteria

- surfaces consume more shared composed models
- text formatting becomes thinner and more surface-specific only

## Design Rules

Purpose: give implementation rules for future host-side changes.

When adding host-side behavior:

- put protocol and IO mechanics in transport/integration modules
- put reusable semantics in shared domain/service modules
- put multi-step operator flows in workflow/application services
- keep CLI and UI focused on presentation and surface-specific state

If the same meaning would otherwise be implemented twice for CLI and UI, it should usually be moved below the presentation layer.

## Non-Goals

Purpose: prevent this spec from expanding into a rewrite.

This refactor should not:

- rewrite host tooling from scratch
- force immediate movement of all code into new packages
- break CLI or UI operator behavior without cause
- replace stable transport contracts just to look cleaner
- move code only for cosmetic folder symmetry

## Testing Requirements

Purpose: ensure refactor work is verified with behavior-preserving checks.

Each milestone under this spec should:

- add or update unit tests for newly extracted services
- preserve current CLI and UI behavior where expected
- preserve DSL import/validate behavior across both surfaces
- preserve runtime/test command behavior across both surfaces
- preserve topology/visibility behavior unless the change explicitly targets those semantics

Recommended focus:

- service-level tests first
- cross-surface regression tests second
- broad regression bundles after milestone completion

## Documentation Requirements

Purpose: keep architecture and operator docs aligned with the new ownership model.

When this spec is executed:

- update `docs/HOST_SOFTWARE_ARCHITECTURE.md`
- update `docs/ARCHITECTURE.md` where layer ownership changes materially
- update any CLI/UI workflow docs affected by new shared service ownership
- keep wording clear that the UI is mainly runtime-facing unless a refactor intentionally changes that scope

## Acceptance Criteria

Purpose: define when this refactor direction is materially successful.

This spec is considered successfully implemented when:

- the UI no longer depends on CLI private internals for DSL workflows
- profile/test discovery semantics are shared across CLI and UI
- session-state and command lifecycle semantics are substantially shared above transport
- `bridge_ops.py` has clearer ownership boundaries
- runtime-state and test-execution workflows have shared service ownership
- shared topology/runtime composition is stronger where cross-surface drift previously existed
- CLI and UI entrypoints are thinner and more presentation-focused than the current baseline

## Bottom Line

Purpose: summarize the main architectural change this spec is asking for.

The host code already has shared transport and some shared domain modules.

The next architectural step is to add more shared workflow and service ownership above those layers, so CLI and UI stop being the place where reusable host-side product meaning lives.
