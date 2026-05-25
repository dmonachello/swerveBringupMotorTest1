SPEC_STATUS: PROPOSED

# Feature Spec: GUI Interaction and Viewport Stability

## Purpose

Define the non-negotiable interaction contract for all GUI surfaces in this repo so that screen behavior is stable, predictable, and professional under real operator use.

This spec exists because poor screen behavior can make a good system feel broken:

- plain clicks are causing diagram jumps
- drag start is causing layout churn
- zoom is rebasing around the wrong point
- panel changes are disturbing the main workspace
- redraw behavior is happening too often and at the wrong times

This spec is intended to become the governing contract for GUI work moving forward.

## Scope

This spec applies to all GUI surfaces in this repo.

Current in-scope surfaces:

- topology editor
- bringup UI

Future GUI surfaces must follow this spec unless an explicit exception is documented.

## Summary

The core rule is simple:

- if the user did not ask to move the view, the view must not move

Corollaries:

- a no-op click must be a true no-op for viewport state
- selection changes must not disturb pan, zoom, or scroll position
- drag must not begin until pointer motion crosses a real threshold
- panel updates must not cause diagram jump behavior
- style-only changes must not trigger full-scene redraw
- zoom must anchor on a deliberate reference point

## Problem Statement

The current GUI interaction behavior has shown several classes of failure:

- clicking can move the viewport
- drag start can cause a left jump
- wheel zoom can move the scene unexpectedly
- redraw and layout changes are happening when no meaningful user-visible change should occur
- changes in one pane can disturb another pane’s workspace

These failures are not acceptable because GUI quality is part of the product, not a cosmetic extra.

## Goals

- Make no-op interactions true no-ops.
- Keep viewport position stable during ordinary interaction.
- Prevent panel updates from disturbing the diagram workspace.
- Eliminate unnecessary redraw operations.
- Make drag start reliable and threshold-based.
- Make zoom behavior deterministic and anchored correctly.
- Define measurable automated and manual acceptance criteria.
- Require instrumentation hooks so future regressions can be diagnosed quickly.

## Non-Goals

- Defining visual style such as colors, typography, or branding.
- Replacing the current GUI toolkit.
- Redesigning all editor/UI layouts from scratch.
- Preventing legitimate movement when the user explicitly pans, zooms, drags, resizes, or fits the view.

## Hard Interaction Rule

Purpose: State the primary invariant.

If the user did not ask to move the viewport, the viewport must not move.

This includes:

- canvas left/top position
- zoom level
- scroll position
- visible scene origin

The only allowed viewport movement is movement directly caused by an explicit user intent such as:

- pan
- zoom
- fit-to-window
- explicit splitter drag
- explicit open/close of a major UI section

## Core Invariants

Purpose: Define measurable before/after rules.

### 1. No-Op Click Invariant

A click with no meaningful model or layout change must be a true no-op for screen behavior.

Examples:

- empty click when nothing is selected
- click on an already selected object without movement
- mouse down and mouse up on the same object without crossing drag threshold
- focus change caused by click without content change

Required outcomes:

- no viewport move
- no zoom change
- no pan change
- no pane resize
- no full-scene redraw

### 2. Selection Change Invariant

Selection changes may update visible selection styling and details content, but must not disturb workspace geometry.

Examples:

- selecting a node
- clearing a selection
- selecting from the left panel
- selecting in the diagram

Required outcomes:

- selection styling may change
- details content may update in place
- viewport must remain stable
- pane geometry must remain stable
- style-only selection change must not force full-scene redraw

### 3. Cross-Pane Isolation Invariant

Interaction in one pane must not disturb another pane’s workspace.

Examples:

- scrolling the left panel must not move the diagram
- selecting in the node list must not move the diagram
- changing details text must not shift the canvas

Required outcomes:

- left-panel interaction never changes diagram pan/zoom/scroll state
- diagram interaction never causes unrelated pane jump behavior

### 4. Drag Commitment Invariant

Pointer jitter is not drag.

Drag begins only after pointer motion crosses a pixel threshold.

Before threshold:

- no model mutation
- no geometry change
- no drag-specific redraw behavior
- no panel hide/show behavior

After threshold:

- drag is considered real
- movement may proceed continuously unless snap-to-grid is enabled

## Panel Geometry Rules

Purpose: Prevent layout churn from disturbing the main workspace.

### 1. Ordinary Interaction Must Not Resize Panes

Ordinary interaction includes:

- click
- selection
- drag start
- mouse-up after click
- focus changes
- side-panel scrolling

These interactions must not resize panes.

### 2. Panel Content Must Update In Place

Details panels and similar side panels must update content in place whenever possible.

Examples:

- selected object details
- status text
- warnings
- metadata text

Packing and unpacking panels during ordinary interaction is disallowed if it changes workspace geometry.

### 3. Major Layout Changes Must Be Explicit

Pane geometry change is allowed only for explicit actions such as:

- user drags a splitter
- user opens a major section
- user closes a major section
- user invokes fit-to-window
- window resize from the OS

Even when allowed, these changes must not flash through incorrect intermediate viewport states.

## Redraw Rules

Purpose: Stop unnecessary canvas rebuilds.

### 1. Full-Scene Redraw Is Restricted

Full-scene redraw is allowed only for:

- true geometry change
- scene membership change
- explicit view transform change

Examples:

- node moved
- bus resized
- object added or removed
- filter changed and visible content membership changed
- zoom changed
- window size changed
- profile loaded

### 2. Style-Only Changes Must Update In Place

Style-only changes must not trigger full-scene rebuild.

Examples:

- selection highlight
- deselection highlight removal
- hover/focus affordance
- warning badge style change without geometry change

Required approach:

- update existing rendered items in place

### 3. No Hidden Redraw Chains

A no-op interaction must not cause:

- redraw on mouse down
- redraw on mouse up
- delayed redraw from configure side effects
- panel hide/show redraw cycle
- move-then-restore viewport behavior

SID_COMMENT:
This rule exists specifically to forbid “jump then restore” implementations that appear stable only after a correction pass.

## Zoom and Pan Contract

Purpose: Define deterministic viewport movement.

### 1. Wheel Zoom

Wheel zoom must anchor on the mouse pointer.

Required behavior:

- the world point under the pointer before zoom remains under the pointer after zoom

### 2. Keyboard/Menu Zoom

Keyboard or menu zoom actions must anchor on viewport center.

Required behavior:

- the world point under viewport center before zoom remains under viewport center after zoom

### 3. Fit to Window

Fit-to-window must:

1. determine the diagram bounds
2. center the diagram in the viewport
3. scale to fit

It must not visibly jump through incorrect intermediate positions.

### 4. Pan

Pan is the only interaction whose direct purpose is viewport movement.

Required behavior:

- viewport movement must follow user input directly
- selection, panel, or redraw side effects must not add extra motion

## Click and Drag Rules

Purpose: Define exact behavior for the most common operator interactions.

### 1. Empty Click

If nothing is selected:

- empty click must be a true no-op

If something is selected:

- empty click may clear selection
- viewport and pane geometry must remain stable

### 2. Click on Object

If the object is not selected:

- selection may change
- style and details content may update
- viewport must remain stable

If the object is already the only selected object:

- do not re-run unnecessary selection work
- do not redraw the whole scene
- do not change panel geometry

### 3. Drag Start

Before drag threshold is crossed:

- this is still a click
- no drag-specific panel or layout behavior may occur

After drag threshold is crossed:

- drag becomes real
- object may move continuously unless snap-to-grid is enabled

### 4. Drag End

Mouse-up after a non-drag click must not trigger drag cleanup redraw.

Mouse-up after a real drag may finalize geometry and redraw as needed.

## Implementation Requirements

Purpose: Turn behavior rules into coding constraints.

### 1. No Restore-Wrapping as Primary Strategy

Viewport preserve/restore wrappers may exist as defensive helpers, but they must not be the main mechanism used to hide bad interaction behavior.

The primary strategy must be:

- do not perform unnecessary redraw or layout mutation in the first place

### 2. Stable Geometry During Ordinary Interaction

Ordinary interaction paths must not:

- pack/unpack panels in ways that change workspace size
- trigger configure loops that shift the main canvas
- reset scrollregion or xview/yview unless required by explicit view movement

### 3. Minimal Update Paths

GUI code must prefer:

- in-place item updates for style changes
- targeted geometry updates for moved items
- full-scene redraw only for true scene or geometry changes

### 4. Shared Contract Across Surfaces

If multiple GUI surfaces show the same conceptual scene behavior, they must follow the same interaction rules.

Examples:

- viewport stability
- zoom anchor behavior
- no-op click semantics
- drag commitment semantics

## Observability and Instrumentation

Purpose: Make future GUI regressions diagnosable.

GUI code must support temporary or permanent debug instrumentation for:

- canvas left/top position
- zoom level
- redraw count
- layout/configure event count
- selection state changes
- drag state transitions

Preferred usage:

- enable during focused regression diagnosis
- compare before/after state for a single interaction sequence

## Required Automated Tests

Purpose: Define the minimum regression gate.

Automated tests must cover at minimum:

- no-op empty click does not change viewport
- click-to-select does not change viewport
- click-to-clear-selection does not change viewport
- clicking an already singly-selected object does not force reselect churn
- mouse-up after plain click does not trigger drag cleanup redraw
- drag does not start below threshold
- drag does start above threshold
- drag start does not resize/hide panels
- wheel zoom anchors at pointer
- keyboard/menu zoom anchors at viewport center
- fit-to-window produces deterministic centered result
- left-panel interaction does not change diagram viewport

Where exact GUI assertions are difficult in headless mode, tests must still validate:

- redraw call count
- layout mutation count
- viewport state helper inputs/outputs

## Required Manual Tests

Purpose: Define the minimum human retest pass.

Every GUI interaction change must include a manual retest checklist that covers at minimum:

- launch the surface
- scroll horizontally, then click empty space
- scroll vertically, then click empty space
- click an object without dragging
- click an already-selected object
- clear selection by empty click
- start a drag and confirm no jump occurs at threshold crossing
- wheel zoom over a specific object
- keyboard/menu zoom
- fit-to-window
- left-panel scroll and selection while observing the diagram
- splitter drag and major section open/close where applicable

Manual pass expectations:

- no visible jump
- no visible flash through a wrong viewport state
- no accidental recentering
- no cross-pane disturbance

## Failure Conditions

Purpose: Make rejection criteria explicit.

A GUI change fails this spec if any of the following occur:

- plain click moves the viewport
- drag start causes visible jump
- wheel zoom rebases around the wrong point
- panel content updates resize panes during ordinary interaction
- style-only change forces full-scene redraw
- one pane’s interaction disturbs another pane’s workspace
- viewport visibly jumps and then gets restored

## Acceptance Criteria

This spec is satisfied when:

- no-op interactions are true no-ops for screen behavior
- selection changes do not disturb viewport or pane geometry
- drag start is threshold-based and visually stable
- zoom behavior is explicitly anchored and stable
- full-scene redraw is limited to legitimate geometry or scene changes
- left-panel interactions do not disturb the main diagram
- automated regressions cover the required cases
- manual retest confirms no visible jump or flash behavior

## Future AGENTS Follow-Up

Purpose: Record the intended next step without changing `AGENTS.md` yet.

After this spec is reviewed, a distilled GUI rule set should be added to `AGENTS.md` for any task that touches GUI behavior.

That distilled rule set should include at minimum:

- no-op click is a true no-op
- no full redraw for style-only changes
- no interaction-driven pane resize
- anchored zoom rules
- required automated/manual GUI interaction verification
