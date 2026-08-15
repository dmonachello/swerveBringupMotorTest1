SPEC_STATUS: PROPOSED

# Feature Spec: Topology Editor Device Management And Deletion

## Purpose

Define a clear topology-editor device-management model for removing a device from the current profile versus deleting a device from shared config, with explicit cleanup rules for `bringup_system.json`.

This spec is intentionally focused on delete and cleanup behavior. It does not redesign topology authoring, bindings, or runtime behavior.

## Summary

The topology editor should expose two distinct device-management actions:

- remove from profile
- delete from app entirely

These actions must have different scope, different confirmation text, and different cleanup behavior.

The core rule is:

- removing a node from the canvas must not silently mean global deletion
- global deletion must perform full config cleanup across shared inventory, profile memberships, saved topology metadata, and label-based editor-owned references

## Background

Today the topology editor already behaves as both:

- a profile-local topology canvas
- a shared-config authoring surface

That creates an important device-ownership distinction:

- some actions should only affect the active profile being edited
- some actions should remove the device definition everywhere

That distinction exists in code today, but it is not yet a clearly specified product feature. Operators can reasonably ask whether deleting a node also cleans up the config properly, which means the behavior boundary is not explicit enough.

## Problem Statement

The product currently risks operator confusion in three ways:

- canvas deletion looks like device deletion, even when it is only profile-local removal
- inventory deletion is stronger, but the UI contract is not clearly documented as a separate feature
- cleanup expectations are high because shared labels are referenced by multiple config surfaces

If the editor does not make delete scope explicit, users can either:

- accidentally remove only the active-profile node when they intended global cleanup
- or fear global damage when they only wanted to remove a node from one profile

## Goals

- Define explicit user-facing delete scopes in the topology editor.
- Preserve the distinction between profile membership and shared device definition.
- Guarantee that global device deletion performs consistent config cleanup.
- Keep label-based cleanup rules stable across topology editor, saved config, and related editor-owned metadata.
- Preserve cross-profile safety by never silently deleting references outside the requested scope.
- Preserve CLI parity for the resulting config model.

## Non-Goals

- Redesigning runtime group semantics.
- Changing robot-side behavior.
- Editing `bringup_bindings.json`.
- Editing Java bringup code.
- Replacing label-based identity in this feature.
- General refactoring of topology storage.

## Current Model

Purpose: Describe the config ownership boundary that this feature must respect.

The editor currently manages at least these layers of meaning:

- shared device inventory under `devices[]`
- active-profile membership under `profiles.<name>.devices[]`
- per-profile saved topology snapshots under `topology.profiles.<name>`
- per-profile editor metadata under `bridgeConfig.byProfile.<name>`

Those layers are related but not identical.

One shared device can:

- exist in the shared inventory
- be referenced by one or more profiles
- have a visible node in one saved topology profile
- be absent from another profile’s topology snapshot

This spec keeps that model.

## Proposed Actions

### Remove From Profile

Purpose: Remove a device from the active profile being edited without deleting the shared device definition.

This action should be available when the selected object represents a device that is present in the active profile.

Effects:

- remove the device’s profile membership from the active profile
- remove its topology node from the active profile canvas
- remove active-profile saved topology references for that device
- prune active-profile `bridgeConfig.byProfile.<activeProfile>` label references owned by the editor
- prune active-profile attachment, power, DIO, and related topology-local links

This action must not:

- delete the device from `devices[]`
- remove it from any other profile
- prune other profiles’ `bridgeConfig` entries
- silently convert into global deletion

### Delete From App Entirely

Purpose: Delete a device definition everywhere in the app's persisted config.

This action should be available when the selected object represents a shared-config device definition, including inventory-only devices.

Effects:

- remove the device from `devices[]`
- remove it from every `profiles.<name>.devices[]` membership list
- remove matching device nodes from every saved topology profile snapshot
- remove topology edges and callouts that point to removed topology nodes
- prune `bridgeConfig.byProfile.*` label references across all profiles
- prune editor-owned test references stored under `bridgeConfig.byProfile.*.tests`

This action must require confirmation.

If the device is referenced by one or more profiles, the confirmation must explicitly say that deletion removes the device from every referencing profile.

## Cleanup Contract

Purpose: Define what “clean up the config properly” means for this feature.

Global deletion is complete only if all of the following are true after save:

- the label is gone from `devices[]`
- the label is gone from every `profiles.<name>.devices[]`
- any saved topology node whose `deviceRef` matches the deleted label is removed
- any saved callout whose `targetNodeKey` points to a removed device node is removed
- any saved topology edge whose endpoint points to a removed device node is removed
- any `bridgeConfig.byProfile.*.groups[].members[]` entry referencing the label is removed
- any `bridgeConfig.byProfile.*.selectedDevice.device` value referencing the label is cleared and disabled
- any editor-owned test reference under `bridgeConfig.byProfile.*.tests` that targets the label is pruned

Profile-local removal is complete only if all of the following are true after save:

- the label is gone from the active profile’s membership list
- the active profile saved topology no longer contains the removed device node
- the active profile’s topology-local links no longer target the removed node
- the active profile’s `bridgeConfig.byProfile.<activeProfile>` label references are pruned
- other profiles remain unchanged

## Shared Contract Rule

Purpose: Keep editor behavior aligned with the repo’s shared-contract direction.

All surfaces that represent device membership or deletion scope must derive from the same underlying config meaning:

- shared device definition
- profile membership
- saved topology presence

The editor must not invent a separate delete model that only exists in canvas state.

## User Workflows

### Workflow 1: Remove A Device From One Profile

The operator:

- selects a device node on the canvas
- chooses a remove action
- confirms removal from the current profile if prompted

Expected result:

- the device disappears from the active profile canvas
- the device no longer belongs to the active profile
- the device still exists in shared inventory
- the device remains available to other profiles

### Workflow 2: Delete A Device From The App Entirely

The operator:

- selects a device in the inventory or another shared-config device-management surface
- chooses delete from app entirely
- reviews any cross-profile warning
- confirms deletion

Expected result:

- the device disappears from shared inventory
- the device is removed from all profiles
- saved topology and editor-owned metadata no longer contain stale references

## UI Requirements

Purpose: Make delete scope obvious before the user commits.

The topology editor should use scope-specific labels such as:

- `Remove From Profile`
- `Delete From App Entirely`

The editor should not use a single ambiguous `Delete` label for both behaviors unless the surrounding context makes scope explicit.

Confirmation text must include scope language:

- current profile only
- all profiles
- shared config

## Persistence Rules

### Save

On save, the editor must persist the requested scope exactly.

For profile-local removal:

- only the active profile and its saved topology snapshot change

For global deletion:

- all affected profile memberships and all affected saved topology profiles are pruned before write

### Load

On load, the editor must not reconstruct deleted device nodes from stale topology metadata.

If a saved topology entry still refers to a deleted label because of a legacy or externally edited file, load/repair behavior should prune or repair those stale references rather than treat them as valid live nodes.

## Validation Rules

The editor must preserve these invariants:

- no saved topology profile may contain a device node whose `deviceRef` is absent from `devices[]`
- no profile membership list may contain a label absent from `devices[]`
- no group member label may persist after confirmed global deletion
- no selected-device reference may persist after confirmed global deletion

Profile-local removal must preserve these invariants:

- removing a device from one profile must not mutate other profiles
- removing a device from one profile must not delete the shared device definition unless the user explicitly requested global deletion

## CLI Compatibility

Purpose: Keep the feature aligned with the repo’s authoring-surface rules.

This feature does not require new CLI syntax by itself, but the resulting persisted config must remain:

- readable by CLI
- editable by CLI
- valid for existing CLI workflows

The topology editor must not create a deletion tombstone or intermediate representation that only the editor understands.

## Regression Coverage

Purpose: Define the narrowest meaningful automated checks for this feature.

Required regression coverage includes:

- removing a selected node prunes only the current profile’s `bridgeConfig` references
- global inventory deletion removes the device from shared inventory
- global inventory deletion removes the device from every profile membership list on save
- global inventory deletion prunes saved topology device nodes, dependent callouts, and dependent edges
- global inventory deletion prunes `bridgeConfig` group members, selected-device refs, and editor-owned test refs
- profile-local removal leaves unrelated profiles unchanged

## Tradeoffs

Purpose: Make the chosen model explicit.

- Keeping profile-local removal and global deletion separate is slightly more UI surface, but it prevents dangerous ambiguity.
- Continuing to use label-based cleanup is practical and consistent with the current config contract, but it makes rename and delete correctness important.
- Full cleanup during global deletion increases save-time pruning work, but it is the right place to guarantee config consistency.

## Future Extensions

- add a dedicated device-management panel with explicit scope actions
- add dry-run delete previews listing every reference that will be removed
- add shared validation tooling that reports dangling topology and bridgeConfig references in externally edited files
- add a CLI explain command for device-reference ownership and delete impact

## Open Questions

SID_QUESTION: Should a canvas-selected device offer both actions directly in the same context menu, or should global deletion remain inventory-only in the first pass to reduce accidental damage?

SID_QUESTION: Should global deletion also prune non-editor-owned future metadata sections by shared label, or should that remain explicitly scoped to known editor-owned contracts only?
