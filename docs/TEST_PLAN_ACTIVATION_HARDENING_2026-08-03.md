# Activation Hardening Test Plan - August 3, 2026

## Purpose

Purpose: define the automated and manual test work needed to harden activation and deactivation behavior across the host UI, shared host-side state decisions, and robot runtime confirmation flow.

## Scope

This plan targets the activation portion of the system, especially:

- top-bar `Runtime Activate` and `Runtime Deactivate`
- selected-test scope activation and deactivation
- manual active-group scope activation and deactivation
- transition-pending and runtime-confirmation logic
- action gating and runnable-state consistency

This plan does not change the intended operator workflow by itself. It is a hardening and verification plan for the current behavior baseline.

## Risk Areas

Purpose: capture the failure modes most likely to cause intermittent or contradictory activation behavior.

Primary risk areas:

- selected-test scope versus manual scope ownership
- superset membership versus exact-match membership
- command ACK accepted before runtime snapshot fully confirms state
- pending transition cleared too early or too late
- button enabled-state not matching the actual command path
- stale runtime state, reconnect, or ownership churn during activation
- tab or context changes while activation is pending

## Goals

Purpose: define what "bulletproof" means for this area.

Activation is considered hardened when:

- enabled buttons never immediately fail for reasons already knowable from current state
- activation and deactivation decisions are deterministic for the same input state
- selected-test membership compatibility is evaluated consistently
- pending transitions clear only from matching runtime confirmation or explicit timeout
- stale or partial runtime payloads do not silently produce contradictory scope state
- connected manual validation matches the same workflows exercised by automated tests

## Automated Coverage Matrix

Purpose: define the desired automated regression surface for activation behavior.

### Layer 1: Shared Decision Tests

Target:

- host-side activation and scope decision helpers

Coverage:

- manual activation allowed when profile is selected, runtime state is live, and active group is not empty
- manual activation blocked when no profile is selected
- manual activation blocked when active group is empty
- selected-test activation allowed when current active scope exactly matches required membership
- selected-test activation allowed when current active scope is a superset of required membership
- selected-test activation blocked when a required device is missing from the current active scope
- selected-test scope-swap requirement only when desired membership is not a subset of current scope
- selected-test required-membership-loaded decision uses subset/superset logic consistently
- deactivation gating remains consistent with the active runtime/lifecycle state

### Layer 2: Transition Latch Tests

Target:

- pending activation/deactivation confirmation logic

Coverage:

- activation ACK starts transition-pending state
- deactivation ACK starts transition-pending state
- pending transition stays active while only partial confirmation is available
- pending transition clears when runtime flags and membership confirmation match
- pending transition does not clear from unrelated runtime payload changes
- pending transition times out cleanly and resets internal pending fields
- current-scope fallback clearing behavior is explicitly tested so future changes cannot accidentally widen it

### Layer 3: Command-Path Tests

Target:

- top-level host UI activation command routing

Coverage:

- top-bar runtime activation uses the runtime command path
- selected-test activation preloads required membership when needed
- selected-test activation does not send a command when scope swap is required
- selected-test activation does not send a command when required membership still cannot be loaded
- manual scope activation path remains distinct from selected-test preparation logic
- top-bar deactivation uses the current deactivation command path

### Layer 4: UI Gating Consistency Tests

Target:

- host UI action enable/disable state versus runnable and runtime state

Coverage:

- no-profile-selected disables manual activation
- selected-test scope can stay activatable while current scope already covers the needed devices
- selected-test scope disables activation and leaves deactivation available when scope swap is required
- transition-pending disables activation and deactivation
- run-selected gating remains tied to robot-reported readiness

## Automated Tests Implemented In This Change

Purpose: record the automated activation coverage added immediately as part of this hardening pass.

The current implementation work adds automated tests for:

- selected-test superset membership does not require scope swap
- selected-test missing required member does require scope swap
- selected-test required-membership-loaded returns true for supersets
- selected-test required-membership-loaded returns false when a required device is missing
- selected-test required-membership-loaded returns `None` when disconnected
- runtime-activate ACK starts pending runtime confirmation
- runtime-deactivate ACK starts pending runtime confirmation
- lifecycle-activate ACK starts pending controlled-lifecycle and membership confirmation
- lifecycle-deactivate ACK starts pending deactivation confirmation
- selected-test deactivate ACK starts pending deactivation confirmation
- transition latch does not clear from runtimeActive alone when membership confirmation is still missing
- transition latch clears once runtimeActive and membership confirmation both arrive

These tests live in:

- [tools/can_nt/tests/test_bringup_ui_actions.py](../tools/can_nt/tests/test_bringup_ui_actions.py)

## Automated Commands

Purpose: provide the exact local commands for the activation-focused automated pass.

From repo root:

```powershell
python -m unittest tools.can_nt.tests.test_bringup_ui_actions
python tools/can_nt/scripts/run_regressions.py --suite local
```

If a narrower activation-only pass is needed during active development:

```powershell
python -m unittest tools.can_nt.tests.test_bringup_ui_actions.BringupUiActionMetadataTests
```

## Manual Connected Test Procedure

Purpose: define the explicit robot-connected checks that are still valuable beyond unit automation.

Prerequisites:

- reachable roboRIO REST command endpoint
- Windows host with the normal UI workflow available
- active profile with at least one valid manual active-group member
- at least one selected test whose required devices are known

### Procedure 1: Manual Scope Activation While Inactive

1. Start the host UI and connect to the robot.
2. Select a valid profile.
3. Go to the manual or Live Topology context.
4. Confirm the active group is non-empty.
5. Press `Runtime Activate`.
6. Wait for runtime state refresh to settle.
7. Press `Runtime Deactivate`.
8. Wait for runtime state refresh to settle.

Expected:

- activation succeeds without duplicate-command behavior
- the UI enters a temporary waiting or resync state while confirmation is pending
- the scope returns to inactive after deactivation
- no contradictory "ready" and "inactive" messages appear during the same settled state

### Procedure 2: Selected-Test Activation When Scope Is Already Compatible

1. Connect the UI to the robot.
2. Select a profile and a known selected test.
3. Arrange current active-group membership so it already contains all required test devices.
4. Enter the Tests context.
5. Press `Runtime Activate`.
6. Observe the selected-test status and output pane.

Expected:

- activation is allowed
- no scope-swap-required message appears
- extra active-group members do not block activation if required members are already present

### Procedure 3: Selected-Test Activation When Scope Swap Is Required

1. Keep the robot connected and a controlled scope active.
2. Select a test whose required device set is not fully contained in the current active-group membership.
3. Enter the Tests context.
4. Press `Runtime Activate`.

Expected:

- the UI does not send a hidden alternate activation path
- the operator is told to deactivate and reactivate to switch scope
- activation does not silently proceed with the wrong membership

### Procedure 4: Selected-Test Membership Preload Path

1. Start with no controlled scope active.
2. Select a test whose required membership is not yet loaded into the robot active group.
3. Press `Runtime Activate`.
4. Observe the output pane and final scope state.

Expected:

- the UI loads selected-test membership before activation
- activation proceeds only if the required membership becomes available
- if the membership still cannot be loaded, the UI stops with a clear reason instead of leaving ambiguous pending state

### Procedure 5: Activation Under Runtime Refresh Delay

1. Connect to the robot under conditions where runtime updates are slightly delayed.
2. Press `Runtime Activate`.
3. Observe the UI before the confirming runtime payload arrives.
4. Wait for the runtime payload to arrive and settle.

Expected:

- the UI remains in an explicit waiting or resync state
- activation is not treated as fully complete before confirmation arrives
- once confirmation arrives, pending state clears cleanly

### Procedure 6: Deactivation While Scope Is Active

1. Activate a scope successfully.
2. Press `Runtime Deactivate`.
3. Observe output, button states, and settled final state.

Expected:

- deactivation is available only when it is truly valid
- the UI enters pending confirmation while deactivation is being confirmed
- the settled state clearly returns to inactive

## Manual Failure Checklist

Purpose: provide a tight checklist for what to record when a manual activation problem is observed.

If any manual step fails, record:

- exact profile name
- exact selected test name, if any
- current tab or context
- whether scope owner was manual or selected test
- current active-group members
- expected required members
- output-pane lines around the action
- whether the button was enabled before the failure
- whether the robot runtime payload eventually matched the expected transition

## Exit Criteria

Purpose: define when this activation hardening effort is strong enough to trust.

Exit criteria:

- automated activation-focused tests pass locally
- broader local regression suite still passes
- manual connected procedures pass on a real robot
- no known button-state versus command-path contradiction remains
- no known transition-pending latch clears early without matching confirmation
