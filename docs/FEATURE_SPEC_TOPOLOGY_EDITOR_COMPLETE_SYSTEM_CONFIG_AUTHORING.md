SPEC_STATUS: PROPOSED

# Feature Spec: Topology Editor Complete System Config Authoring

## Purpose

Define the topology editor as a full `bringup_system.json` authoring surface for robot/system definition data, while explicitly excluding test authoring and preserving full CLI parity.

This spec exists to answer a practical workflow problem:

- the topology editor already authors much of the system config
- some remaining robot-definition data still lives outside the editor
- operators want to define a whole robot in one place
- the CLI must still remain able to do everything

## Summary

The topology editor should be able to author a complete robot/system definition in `bringup_system.json`, including:

- device registry entries
- profile membership
- topology graph and layout
- infrastructure nodes
- DIO attachments and related topology wiring
- non-topology devices such as USB controllers
- per-profile topology-oriented grouping metadata

The topology editor should not become the authoring surface for:

- global bindings in `bringup_bindings.json`
- DSL tests
- bridge/local test authoring content

Those remain valid CLI/UI workflows.

The CLI parity rule is hard and never changes:

- any config capability available in the editor must remain available in the CLI
- the editor may add convenience, but must not become the only path for a capability

## Problem Statement

Today, the topology editor sits awkwardly between two roles:

- topology/layout editor
- partial system-config authoring tool

It already creates or mutates many robot-definition fields, but not all of them. That creates friction:

- operators can define most of a robot visually, but still need to drop into other surfaces for remaining non-test config
- some devices belong in the system config but have no meaningful topology placement
- the product boundary is unclear: is the editor only for topology, or for system definition more broadly?

The core issue is not tests or bindings. The core issue is that `bringup_system.json` contains more than only diagrammed nodes.

## Goals

- Allow the topology editor to author a complete `bringup_system.json` robot/system definition.
- Preserve topology-first workflows for diagrammed hardware.
- Allow non-topology devices to exist in the editor without forcing fake topology connections.
- Treat infrastructure nodes as first-class authorable objects.
- Use a shared object identity model with at least:
  - `label`
  - `objectType`
- Preserve full CLI parity for every editor-exposed capability.
- Keep tests, bindings, and DSL authoring out of scope for this editor feature.

## Non-Goals

- Replacing the CLI as an authoring surface.
- Moving bindings authoring into the topology editor.
- Moving DSL test authoring into the topology editor.
- Requiring every system-config object to have a topology node.
- Adding mandatory Driver Station or network modeling in the first implementation pass.
- Redesigning robot runtime semantics.

## Hard Rule: CLI Parity

Purpose: Record the non-negotiable interface rule.

The CLI must remain able to do everything.

Consequences:

- any new editor capability must correspond to an existing CLI capability or a CLI capability added in the same feature set
- editor-owned data must still be inspectable and editable through CLI workflows
- no system-config field may become editor-only

SID_COMMENT:
This is a product rule, not a temporary rollout note.

## Conceptual Model

Purpose: Define the editor’s role after this change.

The topology editor is not only a topology-canvas tool.

It is a:

- system-config authoring tool

with:

- a topology canvas for topology-participating objects
- additional editor surfaces for system-config objects that do not participate in topology

This means an object may be:

- part of the system config
- part of one or more profiles
- visible on the topology canvas
- or not visible on the topology canvas

Those are separate decisions.

## In-Scope Data

Purpose: Define what the editor must own in the first phase.

### 1. Shared Device Inventory

The editor must be able to create, edit, and delete entries in:

- `devices[]`

This includes:

- CAN devices
- DIO devices
- USB devices such as Xbox controllers
- internal/core devices when applicable

### 2. Profile Membership

The editor must be able to control:

- `profiles.<name>.devices[]`

This includes adding or removing devices from the active profile even if they do not appear as topology nodes.

### 3. Topology Graph

The editor must continue to own:

- topology nodes
- topology edges
- topology layout/view metadata
- infrastructure nodes and their relationships

### 4. Related Robot-Definition Metadata

The editor must continue to own robot-definition metadata that is structurally tied to device/topology authoring, such as:

- DIO attachments
- DIO-to-roboRIO wiring relationships
- topology-oriented group overlays stored in `bridgeConfig`

## Explicitly Out of Scope

Purpose: Define what stays outside this feature.

The topology editor should not become the primary authoring surface for:

- `bringup_bindings.json`
- global bindings
- DSL tests
- bridge/local test definitions
- runtime binding behavior

CLI and other UI surfaces remain valid for those workflows.

## Object Model

Purpose: Define the common model that allows devices and infrastructure to be treated consistently.

All authorable objects relevant to the editor should share a common identity header.

Minimum required common fields:

- `label`
- `objectType`

Examples:

```json
{
  "label": "frontLeft Drive Motor",
  "objectType": "device"
}
```

```json
{
  "label": "cannect 3",
  "objectType": "junction"
}
```

Current compatibility expectation:

- `nodeType` may continue to exist as a mirrored compatibility field where topology/diagram payloads still use it
- `objectType` is the canonical shared term when the concept is broader than topology

## Object Categories

Purpose: Clarify what kinds of objects may exist in the editor.

### Topology-Participating Objects

Examples:

- motors
- encoders
- roboRIO
- PDH
- limit switches
- SWYFT CANnect Direct
- SWYFT inject

These may appear as nodes on the canvas.

### Non-Topology Objects

Examples:

- USB Xbox controllers
- other future system-config objects with no meaningful physical topology relationship

These are still valid system-config objects and profile members, but they do not require topology placement.

## Current Phase

Purpose: Define the first implementation target.

### Editor Behavior

The first implementation phase should:

- allow editing of all device definitions needed for the robot/system config
- allow non-topology devices to be created and edited in the editor
- allow non-topology devices to be included in or excluded from profiles
- avoid forcing non-topology devices onto the topology canvas

### Recommended UI Direction

For the first phase, non-topology devices should be managed in list/panel form rather than as required canvas nodes.

Examples:

- device inventory panel
- profile membership panel
- object details panel

This is the smallest design that satisfies the “complete system definition” goal without over-expanding topology semantics.

### Rationale

This solves the immediate authoring gap while preserving the current meaning of the topology canvas:

- canvas is for meaningful topology relationships
- editor overall is for complete system-config authoring

## Future Phase

Purpose: Define the broader possible system-model expansion without forcing it into the first pass.

A future phase may expand the canvas to model broader control/system relationships such as:

- Driver Station
- network links
- controllers connected through Driver Station or host-side infrastructure

This would let USB controllers participate in a larger system diagram rather than existing only as non-topology config objects.

Possible future concepts:

- Driver Station node
- network node or network-link semantics
- control-path relationships
- external-system or host-side infrastructure objects

SID_COMMENT:
This is intentionally future work. It is not required to satisfy the first-pass “complete system definition” goal.

## Why Future Phase Is Separate

Purpose: Explain why Driver Station/network modeling should not be in the current implementation by default.

Adding Driver Station and network semantics is a broader architectural change because it introduces:

- new node types
- new edge semantics
- new validation rules
- a more ambiguous boundary between physical wiring and logical/control-path relationships

That is a valid direction, but it is larger than the current problem.

The current problem is solved by allowing non-topology devices in the editor without requiring fake topology.

## Data Ownership

Purpose: Define what data the topology editor owns versus what it must leave alone.

The topology editor should own the portions of `bringup_system.json` related to:

- device inventory
- profile membership
- topology
- topology-related overlays/groups

The topology editor should not silently rewrite unrelated test/bindings payloads.

If those sections are present:

- preserve them unless the editor is explicitly editing them

## Save/Load Rules

Purpose: Define expected persistence behavior.

### Save

When the editor saves:

- robot-definition changes must persist back into `bringup_system.json`
- non-topology devices must be preserved even if they do not appear on the canvas
- topology-less devices must not be dropped from profiles or `devices[]`
- mirrored compatibility fields such as `nodeType` may be rewritten from canonical `objectType` where applicable

### Load

When the editor loads:

- topology objects should populate the canvas
- non-topology devices should still appear in editor-managed inventory/profile surfaces
- absence from the canvas must not imply removal from the system config

## Validation Rules

Purpose: Keep system-config authoring consistent.

The editor must validate:

- all required device-definition fields by interface
- profile membership references
- topology references
- infrastructure-node labeling/identity

The editor must not require:

- a topology node for every device

Specifically:

- USB controllers may be valid profile devices without topology nodes

## CLI and Editor Compatibility

Purpose: Keep multi-surface behavior aligned.

The CLI and topology editor must operate on the same underlying config concepts:

- same device registry
- same profile membership
- same topology graph

If the editor introduces a new authoring capability for robot/system definition, the CLI must be able to:

- inspect it
- modify it
- persist it

## Migration and Rollout

Purpose: Keep the transition safe.

The first rollout should be additive at the workflow level:

- existing CLI workflows remain supported
- existing topology workflows remain supported
- editor gains broader authoring capability without invalidating old files

No breaking removal of CLI capability is allowed as part of this feature.

## Risks

Purpose: Make likely failure modes explicit.

- The editor may accidentally conflate “in config” with “on topology.”
- Non-topology devices may be dropped during save if inventory/profile logic is still canvas-derived.
- Future DS/network modeling could blur physical topology and logical control semantics if added too early.
- CLI/editor drift is a real risk if new editor-owned fields are not backed by shared model code.

## Test Requirements

Purpose: Define minimum verification expectations.

Implementation work for this spec must include:

- save/load coverage for non-topology devices
- validation coverage showing profile devices may exist without topology nodes
- editor coverage for adding/removing non-topology devices from profiles
- regression coverage ensuring topology save does not drop non-topology devices
- CLI verification showing the same resulting config remains inspectable and editable there

Manual verification should include:

- create a robot with CAN, DIO, and USB devices
- include USB controllers in the profile without placing them on the canvas
- save and reload without losing those devices
- confirm CLI can still inspect and modify the same resulting config

## Acceptance Criteria

This spec is satisfied when:

- the topology editor can author a complete `bringup_system.json` robot/system definition except tests and bindings
- non-topology devices such as USB controllers can be created, edited, and assigned to profiles in the editor
- non-topology devices are not forced into fake topology connections
- topology-participating objects still work as before
- CLI parity remains intact for all editor-exposed capabilities
- save/load/validation flows preserve both topology and non-topology parts of the system config
