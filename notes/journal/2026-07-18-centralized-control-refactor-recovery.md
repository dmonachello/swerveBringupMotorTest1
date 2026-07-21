# Centralized Control Refactor Recovery

## Purpose

Record the recoverable status of the shared UI context / centralized control refactor after the original working chat became unavailable.

This note is intended to separate:

- confirmed repo facts
- confirmed in-progress dirty-tree work
- unknown intent that may have existed only in the lost chat

## Date Boundary

This recovery note was written on July 18, 2026.

The key dates in the recovered trail are:

- June 9-10, 2026: host shared-services refactor milestone and validation artifacts
- June 24-26, 2026: scope-state and controlled-bringup lifecycle milestones
- July 11, 2026: CAN fault finder pickup plan note
- July 15, 2026: explicit checkpoint before centralized control refactor
- July 18, 2026: reconstruction from repo state

## Confirmed Baseline

The last committed checkpoint on `main` is:

- commit `361fb2e`
- date: July 15, 2026
- message: `Checkpoint current CAN diagnostics and UI state before centralized control refactor`

Interpretation:

- the centralized control refactor was not yet committed at that checkpoint
- anything implementing that refactor after this point is currently recoverable only from the working tree, not from committed history

## Confirmed Earlier Architectural Progress

The repo does contain earlier committed refactor progress that predates the centralized-control slice.

Examples:

- host shared-services work had already landed by the June 10, 2026 validation plan
- commit `59c52e9` on June 24, 2026: `Define scope state contract and active-group scrolling`
- commit `db9b000` on June 25, 2026: `Implement DSL test active-group V2 flow`
- commit `fda59e4` on June 26, 2026: `Polish DSL test activation V2 and probe UX`
- commit `769e2f2` on June 27, 2026: `Tighten bringup readiness and shared group state`

This means the centralized-control work is not starting from scratch. It is building on prior host-side layering and scope-state groundwork that is already in git.

## Dirty-Tree Refactor Evidence

As of July 18, 2026, the centralized-control work is present in the working tree and is not fully committed.

Strong signals:

- untracked `tools/can_nt/host_ui_state_service.py`
- untracked `tools/can_nt/tests/test_host_ui_state_service.py`
- large in-progress edits in `tools/can_nt/bringup_ui.py`
- large in-progress edits in `tools/can_topology/live_topology_view.py`
- smaller related edits in `tools/can_nt/bridge_cli.py`

Interpretation:

- the current true refactor state lives partly outside git history
- the repo contains real implementation progress, not just a spec
- the lost chat may have explained sequencing and intent, but the code still preserves a substantial portion of the actual work

## Recovered Working-Tree Scope

### 1. Shared host-side state module exists

`tools/can_nt/host_ui_state_service.py` is a new shared service module.

Confirmed shared state/data structures present there:

- `DiagnosticProfileState`
- `RunnableScopeState`
- `SelectedTestScopeState`
- `ActiveGroupSummaryState`
- `ActiveScopeMembershipState`
- `SelectedTestPanelState`
- `ActiveGroupMemberRowState`
- `RuntimeStateFetchState`
- `ManualDutyScopeState`

Confirmed shared resolvers/helpers present there:

- `resolve_diagnostic_profile_state(...)`
- `resolve_runnable_scope_state(...)`
- `resolve_selected_test_scope_state(...)`
- `resolve_selected_test_panel_state(...)`
- `resolve_active_group_summary_state(...)`
- `resolve_active_scope_membership_state(...)`
- `resolve_runtime_state_fetch_state(...)`
- `resolve_manual_duty_scope_state(...)`
- `should_clear_runtime_event_notice(...)`

Interpretation:

- the implementation went beyond the spec's initial minimum
- the dirty tree already contains a real shared-state layer, not just placeholders

### 2. `bringup_ui.py` has been moved toward consuming shared state

Recovered changes show `bringup_ui.py` now imports and uses the shared host UI state service for:

- diagnostic profile resolution
- runnable scope state resolution
- selected-test scope/status text
- active-group member row state
- runtime-state fetch gating
- runtime notice clearing behavior
- manual-duty scope gating

Recovered direction:

- many local string/status constants were replaced by shared constants
- local rule methods were thinned and redirected to shared resolvers
- activation gating started using shared runnable-scope state instead of local ad hoc checks

Interpretation:

- this is clearly Phase 2 and Phase 3 refactor work from the centralized-control spec
- `bringup_ui.py` is in the middle of being converted from rule owner to shared-state consumer

### 3. `live_topology_view.py` has also been moved toward consuming shared state

Recovered changes show `live_topology_view.py` now imports and uses the shared host UI state service for:

- diagnostic profile application
- runnable scope notice/state
- active-group summary state
- active-scope membership state

Recovered direction:

- live topology notice logic is being centralized
- active-group status and editability are being computed by shared code
- topology profile reload is being driven by a shared diagnostic profile state object

Interpretation:

- this is direct evidence that the refactor was intentionally cross-surface
- the work is not isolated to one file or one bug fix

### 4. Test coverage was started for the shared-state contract

`tools/can_nt/tests/test_host_ui_state_service.py` exists in the working tree.

Recovered tested areas:

- profile blank-state requirement
- robot-active-profile precedence
- runnable-state waiting behavior
- manual-scope block when no local profile is selected
- ready-state when scope is active
- runtime-state fetch gating
- runtime notice clearing behavior
- active-scope membership sorting and locked state
- manual-duty gating relative to active controlled scope

Interpretation:

- the refactor was being implemented with at least some deliberate contract-level tests
- this is a strong sign that the lost chat likely had progressed beyond brainstorming and into concrete execution

## Recovery Mapping Against The Spec

The main spec in play appears to be `docs/FEATURE_SPEC_SHARED_UI_CONTEXT_AND_CENTRALIZED_CONTROL.md`.

### Phase 1: Define shared state contracts

Recovered status:

- substantially in progress in the dirty tree

Reason:

- multiple shared state classes and resolver functions now exist in one module

Caution:

- the spec called out `UiContextState` and `TopologySceneState` explicitly
- those exact named types do not appear to be fully established yet in the recovered working tree

### Phase 2: Centralize profile context and blank-state control

Recovered status:

- in progress and materially implemented in the dirty tree

Reason:

- `DiagnosticProfileState`
- `resolve_diagnostic_profile_state(...)`
- shared profile application paths in `bringup_ui.py` and `live_topology_view.py`

Best current reading:

- this phase appears started and likely partly working
- it is not proven complete from repo state alone

### Phase 3: Centralize runnable scope state

Recovered status:

- strongly in progress and likely the most advanced current slice

Reason:

- `RunnableScopeState`
- `resolve_runnable_scope_state(...)`
- shared runtime notice handling
- shared activation gating
- shared selected-test status helpers

Best current reading:

- this appears to be the main center of gravity of the current dirty-tree refactor

### Phase 4: Centralize active-group view model

Recovered status:

- started in the dirty tree

Reason:

- `ActiveGroupSummaryState`
- `ActiveScopeMembershipState`
- shared active-group/member-row resolvers
- topology consumer changes

Best current reading:

- active-group state centralization was underway, not just planned

### Phase 5: Tighten interpreted evidence ownership

Recovered status:

- not safely recoverable as complete from the current evidence

Reason:

- the dirty tree still includes changes around CAN fault/evidence files
- however, the clearest recovered centralized-control work is around profile context, runnable state, and active-group state
- repo evidence alone does not prove that evidence invalidation ownership was already fully migrated into one shared interpreted-device contract

Best current reading:

- likely not complete
- may have been queued as a later or adjacent slice

## Confirmed Unknowns

These items remain unknown because the lost chat may have contained them, but the repo does not prove them:

- the exact next stage that was intended after the current dirty-tree edits
- whether the plan was to commit profile centralization first and runnable centralization second, or land them together
- whether `UiContextState` was intentionally deferred
- whether `TopologySceneState` was intentionally deferred
- whether evidence invalidation was meant to be part of this same commit series or a later pass
- whether any manual validation had already been run against the current dirty tree but not recorded

## Safest Engineering Interpretation

The safest interpretation as of July 18, 2026 is:

- the repo is not at pre-refactor status
- the repo is not at completed centralized-control status
- the repo is in a genuine in-progress implementation state for the centralized-control refactor
- the most recoverable implemented slices are shared profile context, runnable state, and active-group state
- the exact finish line and intended next commit boundaries are not fully recoverable from chat history

## Recommended Next Steps

1. Do not discard the current dirty tree.

2. Treat commit `361fb2e` as the last safe committed baseline before this refactor slice.

3. Preserve the current dirty tree immediately in one of these ways:

- make a dedicated checkpoint commit
- or save a patch/export outside chat state

4. Before further feature work, run focused tests around:

- `tools/can_nt/tests/test_host_ui_state_service.py`
- `tools/can_nt/tests/test_bringup_ui_actions.py`
- `tools/can_topology/tests/test_live_topology_view.py`

5. Decide the next commit boundary explicitly.

Recommended boundary:

- one commit for shared profile/runnable/active-group state centralization
- separate later commit for interpreted evidence ownership tightening

6. After that checkpoint, update the spec or add a follow-up note marking:

- what phases are now committed
- what is still intentionally deferred

## Why This Note Exists

This note exists because git preserved the code state, but not enough of the conversational execution context.

The repo needed one written artifact that states:

- where the last safe checkpoint is
- where the in-progress centralized-control work actually lives
- which parts are confirmed
- which parts are still uncertain

That artifact now exists here.
