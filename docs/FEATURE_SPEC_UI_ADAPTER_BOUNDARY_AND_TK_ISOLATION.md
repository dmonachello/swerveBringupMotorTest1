# UI Adapter Boundary And Tk Isolation

## Purpose

Define a future refactor that isolates Tk-specific user interface code behind a narrow adapter boundary so the system can switch UI packages later without rewriting shared behavior, host policies, or workflow semantics.

## Problem

The current host-side UI stack mixes several concerns in the same files:

- shared behavior and action policy
- surface orchestration
- Tk widget construction
- direct widget mutation
- canvas/layout rendering details

This coupling creates three costs:

1. changing UI behavior often requires editing Tk-heavy files instead of shared services
2. CLI, Bringup UI, and topology surfaces can drift in meaning when each path interprets state separately
3. replacing Tk later would require both a rendering rewrite and a behavior rewrite

Recent work on shared host-side state and action contracts reduced the first two problems, but Tk-specific rendering and event code is still deeply mixed with surface orchestration.

## Goals

- isolate Tk-specific code behind a clear adapter boundary
- keep shared state, action gating, and workflow semantics outside Tk files
- make a future UI-package replacement primarily a presentation rewrite
- increase code sharing across Bringup UI, CLI, and topology/editor surfaces
- preserve current operator workflows and command semantics during the refactor

## Non-Goals

- replacing Tk in this phase
- redesigning the visual layout or operator workflow
- changing robot-side command behavior
- introducing a web UI or other new UI stack in the same change
- rewriting all surfaces at once

## Guiding Principle

If two surfaces show or interpret the same meaning, common code must own that meaning completely.

UI files should primarily:

- bind events
- request shared state
- render view models
- dispatch user intents

UI files should not own:

- activation policy
- scope/edit ownership meaning
- manual-duty availability meaning
- runtime readiness interpretation
- topology semantic composition rules that are not inherently renderer-specific

## Current State

### Shared Progress

Purpose: describe what is already moving in the correct direction.

- `tools/can_nt/host_ui_state_service.py` now owns a growing portion of shared host-side meaning
- action gating has started moving out of `bringup_ui.py` and into shared contracts
- CLI and topology/editor paths already consume some of the same host-side state/action results
- regression coverage exists for some cross-surface agreement rules

### Remaining Coupling

Purpose: identify what still makes UI replacement expensive.

The highest remaining coupling is in files such as:

- `tools/can_nt/bringup_ui.py`
- `tools/can_topology/live_topology_view.py`

These files still combine:

- domain-aware event handling
- surface-specific orchestration
- direct Tk widget state mutation
- Tk layout/container decisions
- Tk canvas drawing behavior

The topology canvas path is the strongest Tk lock-in point because scene meaning and canvas rendering are still close together.

## Target Architecture

### Overview

Purpose: define the desired boundary between shared behavior and Tk-specific presentation.

The target host-side structure is:

1. domain and workflow services
2. shared host state and action contracts
3. surface-neutral view-model builders
4. surface controllers that translate user intents into shared operations
5. Tk adapter/rendering layer

Only layer 5 should depend directly on Tk.

### Layer Responsibilities

#### 1. Domain And Workflow Services

Purpose: own business behavior independent of any surface package.

This layer includes:

- group/test/profile semantics
- runtime ownership rules
- lifecycle command semantics
- workflow sequencing
- compatibility rules across host surfaces

This layer must not import Tk.

#### 2. Shared Host State And Action Contracts

Purpose: expose stable answers about what the host currently means.

Examples:

- scope control state
- manual-duty access state
- active-group edit action state
- override action state
- future selected-test activation state

This layer must remain surface-neutral and reusable by:

- Bringup UI
- CLI
- topology/editor surfaces
- future replacement UI packages

#### 3. Surface-Neutral View Models

Purpose: describe what a surface should show without deciding how Tk renders it.

Examples:

- action button states and status text
- topology scene graph or node/edge view-models
- active-group membership view-models
- selected-test panel state
- operator warning and waiting-state banners

These objects should be plain dataclasses, typed dicts, or equivalent neutral structures.

#### 4. Surface Controllers

Purpose: translate user intents into shared operations without containing renderer logic.

Examples:

- activate selected scope
- deactivate selected scope
- toggle active-group membership
- request manual-duty popup open
- apply override action

Controllers may coordinate:

- refresh-before-action
- dispatch
- result handling
- follow-up refresh policy

Controllers should not directly mutate Tk widgets.

#### 5. Tk Adapter And Rendering Layer

Purpose: contain all Tk-specific construction, bindings, layout, and drawing behavior.

This layer includes:

- widget creation
- layout containers
- `StringVar` or similar Tk state holders when unavoidable
- widget enable/disable calls
- canvas drawing primitives
- Tk event binding and focus behavior

This layer consumes shared view-models and controller outputs.

## Required Boundaries

### Boundary A: No Tk Imports Below The Adapter Layer

Purpose: prevent accidental backsliding.

Files that provide shared host meaning must not import:

- `tkinter`
- `ttk`
- Tk variable wrappers
- canvas-specific helpers unless those helpers live entirely in the adapter layer

### Boundary B: No Shared Policy Hidden In Widget Callbacks

Purpose: keep policy reusable across surfaces.

A widget callback may decide:

- which controller intent to send
- which selected item was clicked

A widget callback must not decide:

- whether an action is allowed
- whether runtime state is trustworthy
- whether a topology node is editable
- whether a status banner should mean blocked, waiting, or stale when shared state already owns that answer

### Boundary C: Topology Meaning Must Be Renderer-Neutral

Purpose: prevent canvas code from becoming the semantic source of truth.

Topology scene composition should be owned by one shared path that produces renderer-neutral scene data.

Tk canvas code may decide:

- coordinates
- visual grouping
- drawing order
- hit boxes

Tk canvas code must not independently recompute:

- active/inactive semantic membership
- evidence meaning
- edit ownership meaning
- compatibility between topology/editor and live runtime views

SID_QUESTION: Should the future shared topology scene contract be one canonical scene model consumed by both editor and live topology, or a canonical semantic model plus two explicit compatibility adapters?

## Proposed Phases

### Phase 1: Finish Shared Action And State Extraction

Purpose: move remaining policy out of Tk-heavy files.

Scope:

- continue moving action gating and blocked-state meaning into shared host services
- remove sticky surface-local enable/disable rules
- ensure CLI, Bringup UI, and topology/editor consume the same action contracts where behavior should match

Success criteria:

- action availability is derived state, not sticky widget state
- cross-surface regressions cover the shared policy rules

### Phase 2: Introduce Surface-Neutral View Models

Purpose: stop passing raw runtime and UI-local fragments directly into Tk render code.

Scope:

- define view-model builders for selected-test controls, active-group controls, and topology summaries
- make Tk code consume those view-models rather than recomputing meaning

Success criteria:

- major UI sections render from one plain-data model
- tests can validate meaning without creating Tk widgets

### Phase 3: Split Controllers From Rendering

Purpose: separate event orchestration from widget manipulation.

Scope:

- extract controller objects or modules for major action families
- reduce direct command/session orchestration inside Tk widget classes
- keep refresh and post-command behavior in controller paths

Success criteria:

- event handlers become thin adapters
- controller tests run without Tk

### Phase 4: Isolate Topology Canvas Rendering

Purpose: make the hardest renderer-specific area swappable.

Scope:

- separate topology semantic scene composition from Tk canvas drawing
- define a neutral scene contract for nodes, links, states, and interaction targets
- keep hit testing and geometry in a renderer adapter layer where practical

Success criteria:

- topology meaning can be tested without canvas creation
- a future non-Tk renderer could consume the same scene contract

### Phase 5: Evaluate Replacement UI Packages

Purpose: defer framework choice until the codebase is ready.

Candidate evaluation may compare:

- Tk retention with thinner adapters
- Qt or PySide
- web-hosted UI
- embedded browser shell

This decision should happen only after phases 1 through 4 are substantially complete.

## Expected Reliability Benefits

This refactor should improve reliability in addition to portability.

Reasons:

- shared policy reduces path-specific disagreement bugs
- renderer code becomes less likely to hide workflow semantics
- more behavior becomes testable without GUI setup
- state transitions become easier to validate across CLI, UI, and topology surfaces

The reliability gain is not from changing widget packages.

The reliability gain comes from moving meaning out of renderer code and into shared contracts.

## Test Strategy

### Unit Coverage

Purpose: maximize non-GUI verification.

Add or expand tests for:

- shared action-access contracts
- view-model builders
- controller refresh/dispatch sequencing
- topology semantic scene composition

### Cross-Surface Agreement Coverage

Purpose: keep one-shared-state behavior honest.

Add regressions that prove:

- CLI and UI show the same blocked reason for the same action
- topology and control surfaces agree on editable versus locked state
- repeated activation and ownership transitions remain aligned across surfaces

### Minimal Tk Smoke Coverage

Purpose: retain confidence that the adapter layer still renders and binds correctly.

Keep Tk-specific tests narrow:

- widget creation smoke tests
- event-to-controller binding tests
- canvas adapter smoke tests

Do not rely on Tk tests for business-rule coverage when shared non-Tk tests can cover the same behavior.

## Migration Strategy

Purpose: keep the refactor incremental and reversible.

- preserve current UI package and operator workflows while extracting boundaries
- move one surface slice at a time
- keep old and new paths behaviorally aligned through regressions
- avoid a flag day rewrite

The recommended slice order is:

1. action/state policy
2. selected-test and active-group control panels
3. override/manual control flows
4. topology scene composition
5. deeper Tk adapter cleanup

## Risks

- temporary duplication while shared models are introduced
- overly abstract view-model layers that add ceremony without reducing coupling
- accidental leakage of Tk assumptions back into shared services
- topology adapter work becoming larger than expected

## Tradeoffs

Purpose: acknowledge costs explicitly.

- this adds architectural layers and naming overhead in the short term
- some files may become smaller but more numerous
- a full payoff requires sustained follow-through; partial extraction alone does not make framework replacement cheap
- topology rendering may still keep some renderer-specific complexity even after semantic isolation

## Future Extensions

Purpose: identify useful follow-on work once the boundary exists.

- build a headless host-surface test harness that exercises controllers and view-models without Tk
- support multiple UI front ends over the same shared host contracts
- generate richer machine-readable scene snapshots for diagnostics and regression artifacts
- evaluate a web or Qt front end using the same controller and view-model layers
