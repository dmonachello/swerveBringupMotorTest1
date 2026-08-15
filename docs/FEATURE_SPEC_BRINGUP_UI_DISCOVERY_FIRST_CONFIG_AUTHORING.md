SPEC_STATUS: PROPOSED

# Feature Spec: Bringup UI Discovery-First Config Authoring

## Purpose

Define a first-class discovery-first authoring workflow in Bringup Control so operators can bootstrap a valid `bringup_system.json` from the UI without requiring topology editor as the mandatory first step.

This spec also defines the compatibility expectations when a discovery-created config is later opened in topology editor.

## Summary

Bringup Control should support two explicit config-bootstrap paths:

- `File -> New Blank Config...`
- discovery-driven authoring from `Unrecognized Nodes`

The resulting workflow must allow an operator to:

- start with no config or a blank config
- auto-create a default profile when needed
- promote discovered nodes into shared device definitions
- add those devices to the shared inventory and the default profile
- save the config in memory or to disk
- later open the same config in topology editor and place auto-created device icons on the CAN bus diagram

Topology editor remains the surface for topology/layout authoring, but it is no longer the only valid place to start a config.

## Problem Statement

The product now has two different ways a config can start:

- topology-first
- discovery-first

Today the discovery-first path is incomplete.

The UI can already identify undefined nodes and offer `Create Device Definition...`, but that leaves practical gaps:

- there is no explicit blank-config workflow in the UI
- discovery-created sessions can feel like side effects instead of a supported authoring mode
- profile/default-profile behavior is not fully defined
- unsaved local discovery work does not yet have a clear dirty-document contract
- topology editor follow-on behavior is underspecified when a config has devices but no topology placement yet

The result is product ambiguity:

- users may assume topology editor must always create the config first
- users may discover devices in Bringup UI and then be unsure whether they are in a supported workflow
- cross-surface ownership becomes unclear

## Goals

- Make discovery-first config authoring a supported Bringup Control workflow.
- Add an explicit `New Blank Config...` entry path in Bringup Control.
- Allow `New Blank Config...` to start either:
  - as an in-memory unsaved session
  - as an immediately file-backed session
- Auto-create and set a default profile when discovery-first authoring needs one.
- Add newly discovered devices to:
  - shared config inventory
  - the default profile
- Define a normal dirty-session prompt for unsaved discovery-created work.
- Preserve one shared `bringup_system.json` contract across Bringup UI, CLI, and topology editor.
- Define topology-editor behavior for configs that have devices/profile membership but no persisted topology placement yet.

## Non-Goals

- Moving topology/layout authoring into Bringup Control.
- Replacing topology editor as the topology-editing surface.
- Adding bindings authoring to Bringup Control as part of this feature.
- Adding DSL test authoring to Bringup Control as part of this feature.
- Automatically inferring final topology positions from passive discovery evidence.
- Automatically pushing newly created config to the robot without explicit user action.

## Product Position

Discovery-first authoring is a supported bootstrap workflow.

Topology editor is still the topology/layout authoring surface, but it is no longer the required first surface for config creation.

The product should support both of these legitimate starts:

- start in topology editor and author visually first
- start in Bringup Control, discover devices, save config, then open topology editor later for layout

## Hard Rules

- Bringup Control must never create device definitions implicitly; the operator must still confirm `Create Device Definition...`.
- Discovery-created devices must be added to the canonical shared config model, not to a UI-only shadow structure.
- Discovery-created devices must be added to both:
  - `devices[]`
  - the active default profile membership list
- If no default profile exists when discovery authoring needs one, Bringup Control must create one automatically.
- Bringup Control must support both:
  - an unsaved blank config session
  - an immediately file-backed blank config session
- Unsaved discovery-created work must use a save/discard/cancel prompt before destructive context changes such as open/close.
- Topology editor must not reject a valid discovery-created config just because topology placement has not been persisted yet.
- Topology editor auto-generated placement for discovery-created devices must begin in memory and must persist only when the user saves.
- No surface may create a config representation that only that surface understands.

## User Outcomes

An operator should be able to:

1. launch Bringup Control with no preexisting config workflow in progress
2. choose `New Blank Config...` or open an existing config
3. discover undefined nodes in the UI
4. turn one or more discovered nodes into real device definitions
5. have those devices land in a valid default profile automatically
6. save that work to disk when ready
7. open the same file in topology editor
8. see all devices appear on the CAN bus diagram as positionable icons

## Surfaces

## Bringup Control

Purpose: Own bootstrap config creation, discovery promotion, and local dirty-session handling.

Bringup Control owns:

- blank-config creation
- local config session selection
- default-profile bootstrap for discovery-first flows
- discovered-node promotion into shared config device definitions
- unsaved-change prompting for local UI config edits

Bringup Control does not become the topology-layout editor.

## Topology Editor

Purpose: Own topology/layout authoring for a discovery-created config after bootstrap.

Topology editor owns:

- visual node placement
- topology graph persistence
- later layout refinement
- save-time persistence of in-memory auto-generated topology placement

Topology editor must accept a discovery-created config as valid even when no topology metadata has been saved yet.

## Shared Contract

Purpose: Keep the same config meaning across surfaces.

Bringup UI, topology editor, and CLI must all operate on the same `bringup_system.json` concepts:

- shared device inventory
- profile membership
- default profile
- topology metadata when present

Discovery-first bootstrap may produce a config that has:

- valid `devices[]`
- valid `profiles`
- a valid `default_profile`
- little or no persisted topology/diagram metadata yet

That state is supported and must not be treated as malformed solely because layout work has not happened yet.

## New Blank Config

## Action

Bringup Control should expose:

- `File -> New Blank Config...`

## Modes

The action should support two starts:

### 1. In-Memory Blank Session

The UI creates a new local config session in memory without immediately writing a file.

Use case:

- the operator wants to start discovering and defining devices before deciding where to save

### 2. File-Backed Blank Session

The UI prompts for a path up front and creates a new blank config session anchored to that file path.

Use case:

- the operator already knows where the config should live

## Minimal Blank Config Shape

The blank config should be valid for subsequent UI authoring.

Minimum required starting concepts:

- top-level config object
- `devices[]`
- `profiles`
- `default_profile` once the first profile is created/set

The blank config does not need persisted topology graph content on creation.

## Default Profile Bootstrap

## Rule

If discovery authoring requires a profile and none exists yet, Bringup Control must auto-create one and set it as the default profile.

This applies both when:

- starting from a blank config
- opening a config that has inventory but no usable default profile for the current workflow

## Intent

The operator should not have to stop and manually create a profile just to promote a discovered device.

## Naming

The first-pass auto-created profile name is:

- `default`

Rationale:

- it is the least surprising bootstrap name
- it reads correctly in both topology-first and discovery-first flows
- it avoids implying that the profile is temporary or second-class

## Discovery Promotion Workflow

## Source

The source list remains:

- `Unrecognized Nodes`

## Promotion Action

Right-clicking an unrecognized row and choosing `Create Device Definition...` remains an explicit user-confirmed action.

## Result

When confirmed, Bringup Control must:

1. ensure a default profile exists
2. create or update the shared device definition in `devices[]`
3. add that device label to the default profile membership
4. refresh the current UI session immediately
5. keep the change local/in-memory until explicit save

## Discovery-Created Config Meaning

A discovery-created config is a normal config, not a temporary import artifact.

The UI must not rely on:

- hidden discovery-only tombstones
- host-only caches as the authoritative device list
- unsaved guessed-node state as the long-term source of truth

Once confirmed, the device definition belongs to the same config contract used everywhere else.

## Duplicate And Conflict Handling

## Conflict Trigger

If discovery promotion encounters a label conflict, the UI must not silently overwrite the existing definition.

## Required Behavior

The UI must present a conflict-resolution choice.

At minimum, the operator must be able to understand that:

- a device with that label already exists
- continuing may mean reusing or renaming rather than blindly creating a duplicate

## First-Pass Constraint

The first-pass label-conflict dialog should offer:

- `Use Existing`
- `Rename New`
- `Cancel`

Rationale:

- `Use Existing` supports the common case where passive discovery found a device already represented in config
- `Rename New` supports intentionally distinct devices that would otherwise collide by label
- `Cancel` is required so the user is not forced into a destructive or incorrect guess while resolving identity

## Dirty Session Behavior

## Triggers

Bringup Control must treat discovery-created local config edits as unsaved work.

Examples:

- blank config started in memory
- discovered devices added but not saved
- profile/default-profile created locally but not saved

## Prompt

If the user attempts a context-breaking action such as:

- `Open Config...`
- `New Blank Config...`
- closing the app

the UI must remind the user that discovered/config edits are unsaved and offer:

- save
- discard
- cancel

## Intent

This should behave like a normal dirty-document editor flow rather than silently dropping local discovery work.

## Save Semantics

Choosing save should persist the current local config session to:

- the current anchored path when file-backed
- a chosen file path when the session is still in-memory only

## Topology Editor Compatibility

## Open Behavior

When topology editor opens a valid discovery-created config that has devices/profile membership but no saved layout yet, it should open normally.

It must not reject the file solely because topology nodes have not been persisted yet.

## Auto-Population

Topology editor should create in-memory device icons for all profile devices on the CAN bus diagram when topology placement is missing.

Expected first-pass behavior:

- place icons onto the CAN bus diagram
- allow the user to move them
- do not persist those generated positions until the user saves

## Persistence Boundary

Auto-generated topology placement should remain an editor-memory construct until save.

This preserves two useful properties:

- discovery-first configs remain lightweight before topology work
- topology editor still owns the decision to persist layout metadata

## Save Result

Once the user saves from topology editor, the generated/adjusted diagram state should persist as normal topology metadata in `bringup_system.json`.

## Data Ownership

## Bringup Control Owns

- local bootstrap config session state
- blank-config creation flow
- default-profile auto-creation
- discovery-device promotion into shared inventory/profile membership
- dirty-session prompting for unsaved config edits

## Topology Editor Owns

- topology node placement
- diagram save semantics
- in-memory auto-generation of missing device icons for visual placement

## Shared Config Owns

- durable device inventory
- durable profile membership
- durable default-profile selection
- durable topology metadata after topology editor save

## Failure Modes

## No Config Yet

If the UI starts without a loaded config, `New Blank Config...` should establish one explicitly instead of relying on an implicit hidden fallback.

## No Profile Yet

If discovery promotion needs a profile and none exists, the UI should auto-create one rather than blocking the workflow.

## Save Needed Before Push

If local discovery-created edits exist only in memory, `Push Config` should launch a save-path prompt first instead of being silently disabled.

Expected first-pass behavior:

- if the local session is file-backed, `Push Config` uses the current saved path as normal
- if the local session is in-memory only, `Push Config` first prompts the user to save the config to disk
- if the user cancels the save-path prompt, `Push Config` does not continue

Rationale:

- the user already expressed intent to keep moving forward
- forcing the operator to discover why `Push Config` is disabled is unnecessary friction
- save-first keeps the pushed artifact explicit and inspectable without losing momentum

## Conflict During Discovery

If the operator hits a label conflict, the UI should stop and require explicit resolution instead of silently inventing a second meaning for the same label.

## Cross-Surface Examples

## Example A: Blank In Memory, Discover, Save Later

1. Launch Bringup Control.
2. Choose `File -> New Blank Config...`.
3. Select in-memory mode.
4. Discover unrecognized nodes.
5. Promote one device through `Create Device Definition...`.
6. UI auto-creates and sets a default profile.
7. Device lands in:
   - `devices[]`
   - default profile membership
8. User later chooses `Save Config As...`.

## Example B: Blank File First, Discover, Then Open Topology Editor

1. Launch Bringup Control.
2. Choose `File -> New Blank Config...`.
3. Select file-backed mode and choose a path.
4. Discover and promote several devices.
5. Save.
6. Open the same file in topology editor.
7. Topology editor auto-places device icons on the CAN bus diagram in memory.
8. User drags them into better positions.
9. User saves to persist topology metadata.

## Example C: Unsaved Discovery Work Then Open Another File

1. User has a blank in-memory session with several newly promoted devices.
2. User chooses `Open Config...`.
3. UI warns about unsaved discovered/config edits.
4. User chooses one of:
   - save
   - discard
   - cancel

## Regression Expectations

- Bringup UI supports `New Blank Config...` in both in-memory and file-backed modes.
- Discovery promotion auto-creates a default profile when needed.
- Discovery promotion adds devices to both shared inventory and default-profile membership.
- Unsaved discovery-created edits trigger save/discard/cancel prompts on open/new/close.
- `Save Config` and `Save Config As...` preserve discovery-created content.
- Topology editor opens discovery-created configs without requiring preexisting layout metadata.
- Topology editor auto-populates movable device icons for missing topology placement and persists them only on save.
- CLI can still inspect and edit the resulting config without any UI-only compatibility layer.

## Tradeoffs

- Supporting both topology-first and discovery-first bootstrap increases product surface area, but it removes a real usability dead end.
- Auto-creating a default profile reduces friction, but it means the product must standardize expectations around a first profile existing earlier.
- In-memory topology auto-population keeps ownership clean, but it requires topology editor to tolerate partially authored configs without treating them as broken.
- Dirty-session prompts add friction at open/close time, but silent loss of discovery-created work is worse.

## Future Extensions

- explicit profile-creation/rename UX during discovery-first bootstrap
- richer duplicate-resolution flows beyond label conflict
- optional guided import of discovery-created devices into topology-group workflows
- smarter first-pass auto-layout for topology editor icon placement
- a formal zero-config wizard that chains blank-config creation, discovery, save, topology placement, and robot push
