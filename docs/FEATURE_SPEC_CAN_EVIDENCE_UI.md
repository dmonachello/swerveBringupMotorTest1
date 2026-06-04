SPEC_STATUS: PROPOSED

# Feature Spec: CAN Evidence UI

## Purpose

Purpose: define the user-facing UI for the new CAN device evidence feature without disrupting the current raw visibility and reverse-engineering workflow.

This spec defines a new `Evidence` tab in the Bringup Control UI.

It does **not** replace the existing `Visibility` tab.

## Problem Statement

The project is adding a richer CAN device evidence system that combines:

- passive visibility
- console diagnostics
- active vendor probing
- manual stimulus-response results

The user needs a surface that can answer:

- is the device present
- is it operable
- is it the correct mapped device
- why does the system think that

However, the existing `Visibility` tab already serves an important and different role:

- raw passive observation
- low-level traffic inspection
- unrecognized node viewing
- reverse engineering of unknown CAN messages

The new evidence UI must therefore be additive and must not damage the current raw visibility workflow.

## Goal

Add a new `Evidence` tab that:

- keeps the CAN topology/diagram as the primary visual surface
- shows interpreted per-device evidence results
- preserves a smaller summary table for all devices
- provides a selected-device inspector with per-source evidence details
- leaves the current `Visibility` tab intact as the raw/reverse-engineering surface

## Non-Goals

This spec does not:

- redesign the current `Visibility` tab into the evidence surface
- remove low-level passive visibility details
- define the final evidence fusion algorithm
- replace existing topology rendering with a new separate graph system

## Tab Model

## Existing `Visibility` Tab

Purpose: remain the raw passive and reverse-engineering surface.

The current `Visibility` tab should remain responsible for:

- defined node visibility
- unrecognized nodes
- packet counts and rates
- raw traffic-oriented visibility inspection
- reverse-engineering support for unknown CAN bus activity

This tab should stay intact except for additive improvements that do not change its core role.

## New `Evidence` Tab

Purpose: present interpreted per-device evidence state.

This tab should answer:

- what the system thinks about each expected device
- what sources support that conclusion
- what conflicts or uncertainty remain

## Layout Direction

The `Evidence` tab should be topology-first, not table-first.

### Primary Layout

Three major regions:

1. center-left main topology canvas
2. right-side selected-device inspector
3. bottom secondary summary table

Optional fourth region:

4. bottom-most notes/conflicts strip

## 1. Topology Canvas

Purpose: preserve system context and make evidence spatially meaningful.

The topology/diagram should remain the main surface in the tab.

Requirements:

- reuse the existing topology/canvas model rather than introducing a separate shadow graph
- show expected devices in their normal topology positions
- color nodes by interpreted evidence result
- allow selection by clicking a node
- keep enough of the existing topology readability that branch and mapping issues remain understandable

### Node Color Semantics

Recommended first-pass semantics:

- green:
  - strong present and operable
- yellow:
  - degraded, conflicted, or caution state
- red:
  - absent or failed
- orange:
  - wrong device response or wrong branch/mapping issue
- gray:
  - unknown / insufficient evidence

These colors should come from interpreted evidence results, not passive visibility alone.

### Selection Behavior

When a node is selected:

- the right-side inspector updates
- the bottom summary table highlights the same row if present

## 2. Selected-Device Inspector

Purpose: provide evidence drill-down for one selected device.

This should be a right-side vertical panel.

### Top Summary Card

The top of the panel should show:

- device label
- existence result
- operability result
- identity/mapping result
- confidence band

Example fields:

- `Existence: ABSENT`
- `Operability: FAILED`
- `Identity: UNKNOWN`
- `Confidence: HIGH`

### Per-Source Sections

Below the summary card, show separate sections for:

- Passive Evidence
- Console Evidence
- Active Probe
- Manual Test

Each section should remain source-distinct.

The panel must not flatten all source rows into one undifferentiated list.

### Passive Evidence Section

Typical fields:

- last seen
- packet count
- packet rate
- stale/missing state

### Console Evidence Section

Typical fields:

- active message family names
- latest age
- severity
- short message example or summary

### Active Probe Section

Typical fields:

- bucket
- score
- major evidence items
- warnings/failures

### Manual Test Section

Typical fields:

- latest outcome code
- target label
- observed label if wrong device responded
- observed branch if wrong branch responded
- command kind
- command timing window
- short operator note

If no manual test exists yet:

- explicitly show `Not run`

## 3. Device Summary Table

Purpose: provide a compact sortable overview of all devices.

This table must be present, but secondary.

It should not dominate the tab or replace the topology canvas.

Recommended placement:

- bottom panel below the topology canvas and inspector

### Required Columns

First-pass recommended columns:

- `Device`
- `Existence`
- `Operability`
- `Identity`
- `Confidence`
- `Latest Test`

Optional later columns:

- `Passive`
- `Console`
- `Probe`
- `Manual`

if the summary table needs more direct source columns after first-pass usability feedback.

### Table Behavior

Requirements:

- sortable by result columns
- filterable
- selecting a row selects the device in the topology canvas and inspector

### Filters

First-pass recommended filters:

- `All`
- `Missing`
- `Degraded`
- `Conflicted`

Possible later filters:

- `Manual Test Missing`
- `Wrong Mapping`
- `Unknown`

## 4. Conflicts / Notes Strip

Purpose: surface important interpretation caveats without overwhelming the inspector.

This should be a compact strip or panel near the bottom.

Typical content:

- broad communication isolation warnings
- source conflict notes
- reminders that a result is conservative or incomplete

Example:

- `Console and probe agree that Spark 25 is unreachable.`
- `Broad bus isolation may explain multiple downstream timeouts.`

## User Workflow

First-pass intended workflow:

1. user opens `Evidence`
2. user sees topology-wide color state
3. user scans bottom summary table for missing/degraded/conflicted devices
4. user selects a device in the topology or table
5. user inspects per-source evidence in the right panel
6. user runs manual tests when needed
7. manual test results appear in the same device inspector and summary state

## Data Source Expectations

The UI should consume canonical normalized evidence results and attachments.

It should not become the place where source interpretation logic lives.

The UI should read from:

- normalized source results
- runtime/device snapshot attachments
- canonical report/runtime data structures

It should not independently re-derive core evidence semantics from raw source fields where avoidable.

## Relationship To Other Surfaces

## `Visibility`

- remains raw passive/reverse-engineering surface
- unchanged in role

## `Live Topology`

- may continue to emphasize runtime/passive state
- the new `Evidence` tab is the interpreted evidence view

## Reports / Output

- should present the same evidence distinctions textually
- should not diverge semantically from the new tab

## Tradeoffs

- Keeping `Visibility` intact plus adding `Evidence` increases surface count, but preserves a valuable raw diagnostic workflow.
- A topology-first layout is more spatially meaningful than a table-first layout, but requires careful panel sizing to avoid crowding.
- A smaller summary table is less exhaustive on first glance, but avoids turning the UI into a spreadsheet and preserves the diagram as primary context.

## Definition Of Done

This UI feature is done for its first pass when:

- a new `Evidence` tab exists
- the `Visibility` tab remains intact in role
- the topology canvas is the primary visual surface in `Evidence`
- the right-side selected-device inspector shows final interpreted fields plus per-source sections
- a smaller secondary summary table exists
- device selection stays synchronized between topology, summary table, and inspector
- node colors reflect interpreted evidence states rather than passive visibility alone
- manual test results, when available, appear in the selected-device inspector

## Future Extensions

- expandable evidence timeline view
- explicit conflict badges on nodes
- manual-test history per device
- grouped subsystem summary rows
- topology overlays for wrong-branch or wrong-device response patterns
- richer filter presets for field troubleshooting
