# Usability Stabilization Review

Date: 2026-08-17

Status: Not ready for release

## Purpose

Assess the current repository from an operator-usability perspective, with
priority on proper functionality, deterministic state sync, and removal of
workflow hacks such as toggling profile or file selection to force the UI to
catch up.

## Review Standard

- One visible action should produce one complete state transition.
- Host and robot profile context should converge automatically when policy
  allows.
- No supported workflow should require reselecting a profile, switching away
  and back, or pressing an extra refresh just to make already-completed work
  appear.
- When evidence is ambiguous, the product should say ambiguous rather than show
  contradictory labels, guesses, or scope state.

## Top 10 Usability Issues

### 1. Host/Robot Profile Context Does Not Always Converge Automatically

Priority: `P0`

- Symptom: after connect, the host can keep or appear to keep the wrong profile
  context until the operator reselects a profile or refreshes.
- Main code: `tools/can_nt/bridge_cli.py:12725`, `tools/can_nt/bringup_ui.py:4963`,
  `tools/common/profile_session.py:52`
- Desired behavior: one connect action should leave CLI and UI anchored to one
  clear profile context without extra user intervention.

### 2. Passive Deep Dive Can Contradict The Selected Device

Priority: `P0`

- Symptom: a row selected as `roborio` can still guess `Xbox Controller`.
- Main code: `tools/can_nt/passive_discovery_integration_service.py:3399`,
  `tools/can_nt/passive_discovery_integration_service.py:3464`
- Desired behavior: defined-device deep-dive output must not present
  contradictory identity guesses.

### 3. Passive Discovery Classification Drift On Known Capture

Priority: `P0`

- Symptom: the same reviewed capture now produces a different expected-vs-
  unexpected classification.
- Main code: `tools/passive_discovery_poc/tests/test_analysis.py:56`
- Desired behavior: known capture classifications must remain stable unless the
  change is deliberate and re-baselined with rationale.

### 4. Profile Selection Does Not Guarantee Full Multi-Panel Refresh

Priority: `P1`

- Symptom: changing the selected profile can update some panels while others
  lag until another action occurs.
- Main code: `tools/can_nt/bringup_ui.py:5078`, `:5470`, `:9745`, `:11777`
- Desired behavior: one profile change updates tests, devices, evidence,
  topology, and scope state together.

### 5. Save/Open/Refresh Paths Can Leave Surfaces Out Of Sync

Priority: `P1`

- Symptom: after save, open, download, or refresh, different parts of the UI
  can still reflect different config sessions.
- Main code: `tools/can_nt/bringup_ui.py:9691`, `:12103`
- Desired behavior: file/session changes should propagate to all dependent
  surfaces from one action.

### 6. Manual Refresh Is Still Too Central To Normal Operation

Priority: `P1`

- Symptom: some runtime-owned actions and views still rely on explicit refresh
  to become trustworthy or editable.
- Main code: `tools/can_nt/bringup_ui.py:733`, `:11206`,
  `tools/can_nt/host_ui_state_service.py:394`
- Desired behavior: `Refresh` should remain a recovery tool, not a normal-step
  workaround.

### 7. Evidence And Visibility Context Can Drift From Main UI Context

Priority: `P1`

- Symptom: diagnostics can appear to follow a different profile context than the
  rest of the UI.
- Main code: `tools/can_nt/bringup_ui.py:4963`, `:4988`, `:8028`
- Desired behavior: profile context rules must be consistent and obvious across
  tabs.

### 8. Topology Deletion Semantics Are Still Easy To Misread

Priority: `P1`

- Symptom: users can reasonably confuse profile-local removal with shared/global
  deletion.
- Main references:
  `docs/FEATURE_SPEC_TOPOLOGY_EDITOR_DEVICE_MANAGEMENT_AND_DELETION.md:220`,
  `notes/journal/2026-08-12-topology-device-delete-follow-up.md`
- Desired behavior: delete scope should be obvious before the operator commits
  the action.

### 9. Topology Neighbor Metadata Can Be Saved In A Known-Stale State

Priority: `P1`

- Symptom: the editor can preserve known stale neighbor-derived metadata.
- Main code: `tools/can_topology/can_top_editor.py:138`, `:1820`
- Desired behavior: save should either rebuild, clearly degrade, or explicitly
  block stale neighbor persistence.

### 10. The Maintained Release Gate Still Misses Some UX Contract Drift

Priority: `P1`

- Symptom: the main local suite is healthier, but it still permits missing
  baselines and dirty-tree churn.
- Main references:
  `tests/regression/expected/runner_baselines/local.expected.json`,
  `build.gradle:86`
- Desired behavior: the supported local gate should be green, fully baselined,
  and clean-tree-safe.

## Recommended Order

1. Fix profile-context convergence on connect.
2. Fix passive deep-dive identity contradictions.
3. Resolve passive discovery fixture drift.
4. Audit profile/load/save/refresh paths for stale subpanels.
5. Tighten deletion semantics and stale-topology persistence behavior.

## Verification Approach

- Add one narrow regression for each real bug.
- Verify with one operator-style repro checklist per fix:
  - connect
  - select profile
  - save/open config
  - inspect tests, evidence, topology, and visibility
  - confirm no second-click workaround is needed
