SPEC_STATUS: PROPOSED

# Feature Spec: Topology Editor Xbox Controller Authoring

## Purpose

Define a first-pass topology-editor feature for creating and managing Xbox controllers as non-topology devices in `bringup_system.json`.

This spec is intentionally narrow:

- Xbox controllers only
- topology editor only
- `bringup_system.json` only
- no bindings work
- no Driver Station or network modeling

## Summary

The topology editor should provide an `Add Xbox Controller...` action that:

- creates one or more Xbox controller device records
- assigns them to the active profile being edited
- shows them in the existing left-side list
- allows them to be edited and deleted through normal editor workflows
- does not place them on the topology canvas

## Background

The topology editor already authors much of `bringup_system.json`, but controllers are still awkward because they are valid system-config devices without meaningful CAN/DIO topology placement.

Operators need to finish robot config in the editor without inventing fake diagram nodes or wiring.

## Goals

- Allow Xbox controllers to be created directly from the topology editor.
- Treat Xbox controllers as normal shared-config devices and active-profile members.
- Keep controllers visible and editable in the existing left-side list.
- Keep controllers off the topology canvas in the first pass.
- Keep `bringup_bindings.json` completely out of scope.
- Preserve CLI parity for the same resulting config.

## Non-Goals

- General USB-device authoring in this first pass.
- Editing `bringup_bindings.json`.
- Automatic binding creation or update.
- Driver Station modeling.
- Network-path modeling.
- Putting Xbox controllers on the topology canvas.

## Scope Boundary

This feature is part of topology-editor system-config authoring, not topology-diagram expansion.

The editor is allowed to manage devices that do not participate in diagram topology.

## Hard Rules

- The feature must modify only `bringup_system.json`.
- The feature must not modify `bringup_bindings.json`.
- Added controllers must appear in the left-side list.
- Added controllers must not appear on the topology canvas.
- Controllers must be added to the currently active profile being edited.
- Duplicate controller label creation must be rejected.
- Duplicate controller USB port creation must be rejected.

## Supported Device Type

First-pass support is limited to:

- Xbox controller

Expected config shape is consistent with the existing device model used elsewhere in the repo for controller devices.

Example:

```json
{
  "label": "controller0",
  "type": "xboxController",
  "deviceInterface": "USB",
  "id": 0,
  "model": "Xbox Controller"
}
```

## User Workflow

### Add

The topology editor should expose:

- `Add Xbox Controller...`

This opens a dialog with at least:

- count
- starting port

Behavior:

- creates the requested number of Xbox controller records
- assigns sequential ports starting from the provided starting port
- adds each created controller to the active profile
- inserts each created controller into the shared device inventory
- refreshes the left-side list immediately
- does not create any topology node or canvas item

## List Behavior

Controllers should appear directly in the existing left-side list.

They should not require:

- a separate panel
- a separate section
- a special non-topology list

They are part of the same system-config inventory, even though they are not diagram nodes.

## Edit Behavior

Controllers should be editable through the normal editor edit/details flow.

Expected editable fields:

- label
- port/id
- model
- tags

The editor should preserve the same validation rules used for other shared-config devices where applicable.

## Delete Behavior

Deleting a controller from the topology editor means deleting it entirely from the system config.

That includes:

- removing it from the shared device inventory
- removing it from the active profile
- removing it from any other profile that references it if the user confirms the deletion

If the controller is referenced by one or more profiles, the editor must:

- warn the user
- explain that deletion removes the controller from every referencing profile
- require confirmation before continuing

## Duplicate Handling

The add flow must reject:

- duplicate labels
- duplicate USB ports

This applies against the current shared device inventory and the active profile result being created.

If any requested controller in the batch would conflict, the editor should fail the add operation with a clear error instead of partially creating the batch.

## Default Naming

Controllers need a deterministic label strategy for batch creation.

Default generated labels are:

- `controller<port>`

Examples:

- port `0` -> `controller0`
- port `1` -> `controller1`

## Persistence Rules

### Save

When the editor saves:

- controllers must remain in `devices[]`
- controllers must remain in the active profile membership list
- controllers must not be synthesized into topology or diagram node lists

### Load

When the editor loads:

- controllers must appear in the left-side list
- controllers must be editable
- controllers must not be treated as missing merely because they have no topology node

## Validation Rules

The topology editor must accept Xbox controllers as valid non-topology profile devices.

The editor must not require:

- a topology node
- a bus
- a topology edge
- a diagram placement

The editor must still validate:

- unique label
- unique controller port according to this feature’s rule
- valid required fields for the device type

## CLI Compatibility

The CLI parity rule still applies.

This feature does not require new CLI authoring syntax by itself, but the resulting config must remain:

- inspectable by CLI
- editable by CLI
- saveable by CLI

The topology editor must not create a controller representation that only the editor understands.

## Failure Behavior

The editor should fail fast and clearly when:

- the requested controller label already exists
- the requested controller port already exists
- the active profile is missing
- save/load would drop controller records

The failure message should name the conflicting label or port explicitly.

## Test Requirements

Implementation work for this feature must include:

- add-one-controller editor test
- add-multiple-controllers editor test
- duplicate label rejection test
- duplicate port rejection test
- load/save round-trip test proving controllers remain off-canvas but in-list
- delete-with-warning test when a controller is referenced by one or more profiles
- regression proving topology save does not drop non-topology Xbox controllers

Manual verification should include:

1. open the topology editor
2. load a profile
3. use `Add Xbox Controller...`
4. create multiple controllers from a starting port
5. verify they appear in the left list
6. verify they do not appear on the canvas
7. save and reload
8. verify they remain in the list and in the profile
9. attempt a duplicate add and verify clear rejection
10. delete a referenced controller and verify warning plus confirmation behavior

## Acceptance Criteria

This feature is complete when:

- the topology editor has an `Add Xbox Controller...` action
- the dialog accepts count and starting port
- added controllers are created in shared config and active profile membership
- added controllers appear in the left-side list
- added controllers do not appear on the topology canvas
- duplicate label and duplicate port creation are rejected with clear errors
- deleting a controller removes it entirely after warning/confirmation when referenced
- save/load preserves controllers correctly
- bindings remain untouched
