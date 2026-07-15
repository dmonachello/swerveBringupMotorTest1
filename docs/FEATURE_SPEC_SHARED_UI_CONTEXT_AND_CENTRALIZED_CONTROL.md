# Shared UI Context And Centralized Control

## Purpose

Define a refactor that moves shared UI meaning out of scattered tab/panel logic and into common host-side state services.

This spec is about architecture, not a one-off fix for the current profile-selection bug.

## Problem

The app currently has too much similar decision logic spread across:

- profile selection handling
- live topology
- evidence topology
- active-group panels
- runnable-state panels
- activation button enablement
- selected-test scope behavior

This causes several recurring problems:

- multiple surfaces can disagree about the same underlying state
- small behavior changes require touching many files
- regressions are easy to introduce because each surface recomputes meaning
- fixes become patch-shaped instead of contract-shaped
- profile/context/runnability bugs expose architectural drift rather than isolated mistakes

Recent examples include:

- profile dropdown showing `"(none)"` while topology still rendered a real profile
- active-group content implying profile-backed candidates before local profile selection
- stale evidence continuing to support device health after stronger console fault evidence appeared

These are symptoms of the same root issue:

- not enough common code
- not enough centralized control
- too many surfaces owning their own interpretation logic

## Goal

Create a shared host-side state model so that common meaning is computed once and consumed everywhere.

The central rule is:

- if multiple surfaces are supposed to represent the same state, one common service must own that state contract

## Non-Goals

- redesigning the whole app UI
- rewriting robot-side lifecycle behavior unless required by the shared host contract
- replacing all existing services at once
- changing operator workflows beyond what is necessary to align surfaces to one shared meaning

## Core Principle

The UI should not decide meaning independently in many places.

Instead:

- one shared state layer computes the meaning
- views render it
- actions consult it

This must apply to:

- what profile context is active
- whether profile-backed surfaces should be blank
- whether manual/selected-test activation is allowed
- what runnable-state message should be shown
- what active-group state means
- how stale/invalidated device evidence is interpreted

## Architectural Direction

Introduce shared host-side state objects/services that own the full contract for:

1. UI context
2. diagnostic profile context
3. runnable scope / activation state
4. topology scene state
5. interpreted evidence state

Views should become consumers of these states rather than independent decision-makers.

## Proposed Shared State Model

### 1. `UiContextState`

Purpose: Own session-level UI context.

Fields should include:

- `localSelectedProfile`
- `robotSelectedProfile`
- `robotActiveRuntimeProfile`
- `selectedTestName`
- `scopeKind`
  - `manual`
  - `selected_test`
- `hasLocalProfileSelection`
- `hasRobotRuntimeState`
- `transportConnected`
- `handshakeReady`

### 2. `DiagnosticProfileState`

Purpose: Decide whether profile-backed diagnostics should render and which profile they should use.

Fields should include:

- `effectiveProfile`
- `showBlankProfileState`
- `blankReason`
- `localProfileRequired`
- `robotProfileAvailable`
- `profileContextSource`
  - `blank`
  - `local`
  - `robot_selected`
  - `robot_active_runtime`

Rules:

- if local UI selection is `"(none)"`, profile-backed diagnostic surfaces should be blank
- robot-selected/default-profile fallback must not silently populate profile-backed surfaces when local selection is `"(none)"`
- if a real local profile is selected, then robot-active/robot-selected profile context may refine the effective diagnostic profile according to the shared contract

### 3. `RunnableScopeState`

Purpose: Own whether manual or selected-test actions are allowed and why.

Fields should include:

- `scopeKind`
- `activationAllowed`
- `deactivationAllowed`
- `runSelectedAllowed`
- `statusHeadline`
- `statusDetail`
- `statusLevel`
- `blockedReason`

This state must centralize logic that is currently spread across:

- button enablement
- runnable-state panels
- runtime notice logic
- scope activation prompts

### 4. `TopologySceneState`

Purpose: Own whether a topology scene exists and what should be rendered.

Fields should include:

- `profileName`
- `isBlank`
- `blankReason`
- `nodes`
- `edges`
- `groups`
- `activeGroupState`

Important rule:

- scene existence must be decided centrally before rendering

The view should not infer:

- whether it should blank
- whether to fall back to default profile
- whether active-group content is meaningful

### 5. `InterpretedDeviceState`

Purpose: Own final device evidence meaning across Evidence, Topology, and Fault Finder.

This should continue consolidating:

- runtime presence
- passive CAN visibility
- console evidence
- full probe
- manual observations
- enrichment

But the contract must explicitly include invalidation rules, not just additive notes.

New required semantics:

- stronger fresh device-targeted fault evidence can invalidate weaker stale support evidence
- invalidated probe/manual evidence must be surfaced as invalidated, not quietly left as historical support
- all surfaces that show device evidence must consume the same interpreted row model

## Centralization Requirements

### Requirement 1: One Decision Path For Profile-Backed Blank State

The following must come from one shared decision:

- profile dropdown implications
- live topology blank vs populated
- evidence topology blank vs populated
- active-group panel candidate visibility
- manual activation availability

No individual surface may define its own blank-state fallback rules.

### Requirement 2: One Decision Path For Runnable Messaging

The following must come from one shared state object:

- runnable headline
- runnable detail
- warning/error/info level
- action enablement

No separate copies of “why can’t I run?” logic should remain in different panels.

### Requirement 3: One Decision Path For Evidence Invalidation

The following must come from one shared interpreter:

- stale probe handling
- stale manual handling
- console fault precedence
- final source scores
- conflict state

No panel should locally reinterpret these after the interpreted row is built.

### Requirement 4: Views Render, Services Decide

UI classes should primarily:

- request shared state
- bind widgets to that state
- dispatch actions

They should not be the main owners of multi-source business rules.

## Current Anti-Patterns To Remove

The refactor should eliminate or reduce:

- multiple methods independently checking `PROFILE_NONE`
- per-surface fallback to robot/default profile
- renderer-local scene fallback decisions
- separate activation-allowed logic and runnable-notice logic
- separate active-group readiness logic in multiple surfaces
- evidence invalidation being represented only as notes instead of as shared state

## Refactor Plan

### Phase 1: Define Shared State Contracts

Add common host-side data structures/services for:

- `UiContextState`
- `DiagnosticProfileState`
- `RunnableScopeState`
- `TopologySceneState`

This phase is contract-first.

No broad UI rewrite yet.

### Phase 2: Centralize Profile Context And Blank-State Control

Move profile-backed blank/populated decisions into one shared service.

Consumers:

- live topology
- evidence topology
- active-group side panel
- activation button enablement

Expected result:

- local profile `"(none)"` produces one consistent blank-state outcome everywhere

### Phase 3: Centralize Runnable Scope State

Move scope/runnability logic into one shared service.

Consumers:

- runnable-state panel
- live runtime notice
- activate/deactivate buttons
- selected-test readiness messaging

### Phase 4: Centralize Active-Group View Model

Create a shared active-group view model.

Consumers:

- live topology side panel
- tests-tab active-group panel
- any activation/selection status panels

### Phase 5: Tighten Interpreted Evidence Ownership

Continue moving evidence precedence and invalidation into the shared interpreted row/state layer so:

- topology coloring
- evidence table
- device inspector
- fault finder

all consume the same meaning without local reinterpretation.

## Implementation Constraints

- prefer small, reversible steps
- keep behavior stable except where the centralized contract intentionally changes it
- add focused regression tests for each newly centralized contract
- do not reintroduce local fallbacks once a shared service owns the rule
- preserve existing UI look/feel where possible while moving meaning into common code

## Regression Requirements

Add scenario-style regressions for:

1. No local profile selected:

- profile dropdown shows `"(none)"`
- topology is blank
- evidence topology is blank
- active-group candidate panel is empty or explicitly unavailable
- manual activation is disabled
- runnable message explains that profile selection is required

2. Local profile selected:

- topology/evidence/active-group all use the same effective profile context

3. Fresh targeted console fault against stale support evidence:

- stale probe/manual support is invalidated in the shared interpreted row
- all consuming surfaces reflect that same invalidation

4. Active-group/runnable state:

- button enablement and runnable-status panels stay aligned under the same state transition

## Acceptance Criteria

This feature is complete when:

- there is one shared decision path for blank vs populated profile-backed diagnostics
- there is one shared decision path for runnable/activation messaging
- there is one shared decision path for evidence invalidation
- startup and reconnect behavior no longer depend on per-view fallback rules
- changing one central contract no longer requires patching several tabs/panels separately

## Tradeoffs

Benefits:

- less code churn
- fewer drift bugs
- easier reasoning about state
- better regression coverage at the scenario level

Costs:

- some existing UI methods will need to become thinner and defer to services
- early refactor phases may temporarily add adapter code before legacy branches are removed

## Open Questions

SID_QUESTION: Should `DiagnosticProfileState` live inside `bringup_ui.py` first as an internal shared service, or should it be introduced immediately under a reusable `tools/common` or `tools/can_nt` service module?

SID_QUESTION: Should the active-group view model be a child of `RunnableScopeState`, or a separate shared state object consumed by both topology and tests surfaces?

SID_QUESTION: Should the first implementation slice centralize profile/runnable state together, or land profile blank-state centralization first and then runnable-state centralization second?

## Summary

The heart of this refactor is not “fix profile none.”

It is:

- move shared UI meaning into common code
- centralize control of state contracts
- make views render shared state instead of inventing their own similar logic

That is the architectural problem this spec is intended to solve.
