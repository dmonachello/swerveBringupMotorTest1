SPEC_STATUS: PROPOSED

# Active Group Driven DSL Test Activation V2

**Purpose**

Supersede the earlier scope-centered design with a simpler operator model based on one dynamic group, `active-group`, shared between DSL and non-DSL workflows.

## Supersedes

**Purpose**

Identify the older spec that this document replaces for implementation direction.

- This document supersedes [FEATURE_SPEC_DSL_SELECTED_TEST_DEVICE_ACTIVATION.md](FEATURE_SPEC_DSL_SELECTED_TEST_DEVICE_ACTIVATION.md).
- The older document may remain for history and comparison.
- New implementation work should follow this V2 document.

## Goal

**Purpose**

Reduce operator confusion by making `active-group` the one dynamic group the user needs to understand.

- The user should not need to understand or track a separate `scope` concept.
- Static groups remain unchanged.
- `active-group` is the only dynamic group the user works with directly.
- In the `Tests` tab, the selected DSL test defines `active-group`.
- In non-Tests tabs, the Active Group panel defines `active-group`.
- Activation and deactivation are explicit user actions.
- Tab changes between `Tests` and non-Tests always deactivate the active group.

## Non-Goals

**Purpose**

Clarify what this version does not change.

- Do not change static group behavior.
- Do not add a second user-facing dynamic group.
- Do not expose `scope` as an operator concept.
- Do not auto-run a DSL test when a group is activated.
- Do not allow group membership edits while the group is active.
- Do not silently keep hardware active when crossing the `Tests` / non-Tests boundary.

## Core User Model

**Purpose**

Define the one concept the operator should carry.

- `active-group` is the current working set.
- The system may fill `active-group` from different sources depending on context:
  - selected DSL test in `Tests`
  - manual selection in non-Tests tabs
- The group can be inactive or active.
- The group membership and the instantiated state are different things.
- The UI must make it clear when `active-group` is loaded but not instantiated.

## Group Sources

**Purpose**

Define who owns `active-group` in each UI context.

### Tests Tab

**Purpose**

Describe how DSL uses `active-group`.

- The selected DSL test owns `active-group` membership while the `Tests` tab is selected.
- Selecting a test in the dropdown or list populates `active-group` from that test's required devices.
- The Active Group panel in `Tests` is read-only.
- The user cannot directly edit `active-group` in `Tests`.
- The only way to change `active-group` membership in `Tests` is to:
  - select a different DSL test
  - or change the DSL test definition itself

### Non-Tests Tabs

**Purpose**

Describe how manual workflows use `active-group`.

- Non-Tests tabs own `active-group` through the Active Group panel.
- The last manual `active-group` membership must be remembered.
- Leaving `Tests` restores the remembered manual `active-group` membership automatically.
- Switching among non-Tests tabs does not deactivate or rebuild the group.

## Group Activation Buttons

**Purpose**

Define the operator-facing controls.

- The top shared buttons should use group language:
  - `Activate Group`
  - `Deactivate Group`
- Do not use `Scope` in user-facing button labels.
- In `Tests`, `Activate Group` activates the currently displayed test-driven `active-group`.
- In non-Tests tabs, `Activate Group` activates the currently displayed manual `active-group`.
- `Deactivate Group` tears down the current active group.

## Tests To Non-Tests Boundary Rule

**Purpose**

Define the mandatory behavior when crossing between DSL and non-DSL contexts.

- Crossing from `Tests` to any non-Tests tab always deactivates the active group.
- Crossing from any non-Tests tab into `Tests` always deactivates the active group.
- Crossing the boundary also clears the currently displayed `active-group` contents for the old context.
- After entering `Tests`, the newly selected DSL test may repopulate `active-group`.
- After leaving `Tests`, the remembered manual `active-group` membership is restored automatically.
- There are no exceptions for matching membership.
- After a boundary-crossing deactivation, the user must explicitly activate again.

## Within Tests Behavior

**Purpose**

Define what happens when the selected DSL test changes while staying in the `Tests` tab.

- If the selected test changes and its required membership differs from the currently displayed `active-group`:
  - deactivate if active
  - repopulate `active-group`
  - leave the group inactive
- If the selected test changes but the required membership is identical:
  - no deactivate/rebuild is required
  - no hardware change is required
- No confirmation dialog is required for this rebuild.

## Group Membership Editing Rules

**Purpose**

Prevent ambiguous runtime state.

- In non-Tests tabs, the user must not be allowed to edit group membership while `active-group` is active.
- In `Tests`, the Active Group panel is always read-only.
- Group membership changes are allowed only while inactive in non-Tests tabs.
- If the user attempts to deactivate when the group is already inactive, return a harmless reminder that nothing changed.

## Display Rules For Active Group

**Purpose**

Define how the Active Group panel should behave across contexts.

- The same Active Group panel should be reused in `Tests` and non-Tests tabs.
- In `Tests`, it should show the DSL-derived `active-group` members.
- In `Tests`, it must clearly show that the displayed devices are not instantiated until activation occurs.
- If no test is selected, the panel should keep showing the previous displayed test-driven rows unless a tab change occurs.
- When leaving `Tests`, the panel switches back to the restored manual `active-group`.

## Support Devices And Singletons

**Purpose**

Define which devices may appear in the group and how they are treated.

- DSL-required support devices such as `controller0` and `lmtSw0` should appear in `active-group` when required by the selected test.
- Singleton/support devices must appear as locked rows in the Active Group panel.
- The user must not be allowed to toggle singleton/support rows directly in `Tests`.
- The current required singleton/support set is:
  - `controller0`
  - `roborio`
  - `pdp`
- Additional devices may be added later as needed.

## Activation Set

**Purpose**

Define exactly what `Activate Group` uses.

- `Activate Group` uses exactly the currently displayed `active-group` rows.
- No hidden extra non-singleton devices may be added at activation time.
- Required singleton/support devices may also be active according to policy.
- In `Tests`, this means the activation set is exactly the displayed DSL-driven group plus required singleton/support devices.
- In non-Tests tabs, this means the activation set is exactly the displayed manual group plus required singleton/support devices.

## DSL Test Readiness

**Purpose**

Define when `Run Selected` may be allowed.

- `Run Selected` must remain blocked until the test-driven `active-group` is activated.
- There are no exceptions after a `Tests` / non-Tests tab crossing.
- If a selected test change does not change membership and the group is still active from the same `Tests` context, no extra activation is required.
- `Run Selected` must block if required singleton/support devices are unavailable.
- `Run Selected` must block if the selected test references devices not valid for the current profile.

## Status Messages

**Purpose**

Make the active/inactive meaning explicit.

Suggested required texts:

- In `Tests` after loading from the selected test but before activation:
  - `active-group loaded from selected test - not activated`
- In non-Tests after restoring the remembered manual group but before activation:
  - `manual active-group restored - not activated`
- On already-inactive deactivation:
  - reminder that nothing happened

The exact wording may vary slightly, but the meaning must remain explicit.

## Validation And Error Display

**Purpose**

Define where invalid test-to-profile mismatches must appear.

- If a selected DSL test references a device not present in the current profile:
  - report it in Validate Status
  - also visibly indicate the problem in the Active Group panel
- The invalid device does not need to be silently omitted from reasoning.
- The UI should make it obvious that the group is loaded but not valid to activate/run.

## Remembered Manual Group

**Purpose**

Define what is preserved when DSL temporarily owns `active-group`.

- The last manual `active-group` membership must be remembered when entering `Tests`.
- That remembered manual membership is not editable while the `Tests` tab owns the displayed group.
- Leaving `Tests` restores the remembered manual membership automatically.
- Restoration on leaving `Tests` does not activate the group.

## CLI Behavior

**Purpose**

Keep CLI and UI aligned with the simpler group model.

- Existing `active-group` lifecycle activation/deactivation remains valid.
- CLI behavior should align with the same group-first model used by the UI.
- The implementation may still use internal lifecycle/session machinery, but CLI/operator language should stay centered on groups.
- Future CLI additions should prefer group-centered naming over scope-centered naming.

## Examples

**Purpose**

Show the intended workflow without introducing extra concepts.

### Example 1: Enter Tests

1. User starts in a non-Tests tab with a manual `active-group`.
2. User switches to `Tests`.
3. The system deactivates the current active group.
4. The old displayed group is cleared.
5. The selected DSL test populates `active-group`.
6. The panel shows the loaded devices as not instantiated.
7. User must press `Activate Group` before `Run Selected`.

### Example 2: Change Test In Tests

1. User is in `Tests`.
2. Selected test changes from `falcon9_move_150_rotations` to `falcon9_to_limit`.
3. If membership changed:
   - deactivate if active
   - repopulate `active-group`
   - leave inactive
4. If membership did not change:
   - leave the group and hardware state alone

### Example 3: Leave Tests

1. User is in `Tests` with a DSL-driven `active-group`.
2. User switches to `Live Topology`.
3. The system deactivates the active group.
4. The DSL-driven displayed group is cleared.
5. The remembered manual `active-group` membership is restored.
6. The restored manual group remains inactive until explicitly activated.

### Example 4: Locked Devices

Selected DSL test requires:

- `FALCON 9`
- `lmtSw0`
- `controller0`

Active Group panel in `Tests` shows:

- `FALCON 9`
- `lmtSw0` as locked
- `controller0` as locked

The user may not directly edit these rows in `Tests`.

## Acceptance Criteria

**Purpose**

Define when this V2 behavior is complete enough to accept.

- The user does not need to understand a separate `scope` concept.
- The UI uses group-oriented language for the main activation buttons.
- `active-group` is the only user-facing dynamic group.
- Selecting a DSL test repopulates `active-group` in `Tests`.
- Crossing the `Tests` / non-Tests boundary always deactivates the active group.
- Leaving `Tests` restores the remembered manual `active-group` membership automatically and inactive.
- In `Tests`, the Active Group panel is read-only.
- In non-Tests tabs, group membership cannot be edited while active.
- In `Tests`, support devices and singletons required by the test are shown as locked rows.
- `Activate Group` activates exactly the displayed group plus required singleton/support devices.
- `Run Selected` stays blocked until the group is activated.
- Invalid test/profile device mismatches are visible in both Validate Status and the Active Group panel.

## Tradeoffs

**Purpose**

Record the main consequences of this simpler model.

- This model is easier for operators to understand because everything revolves around one dynamic group.
- It makes tab changes more destructive because they always deactivate on the `Tests` / non-Tests boundary.
- It intentionally favors predictability over reuse of still-compatible active hardware across contexts.
- It keeps implementation flexibility internally while constraining the user-facing contract to groups.

## Future Extensions

**Purpose**

List additive work that can follow without changing the core V2 model.

- Add more locked singleton/support device categories as needed.
- Improve visual styling for invalid or inactive group rows.
- Add clearer per-row reason badges in the Active Group panel.
- Add CLI help/manpage updates that explain the group-only operator model.
