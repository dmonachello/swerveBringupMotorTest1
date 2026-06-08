SPEC_STATUS: DRAFT

# Feature Spec: UI2 Task Mode Reorganization

## Purpose

Define the next major organization model for the Bringup Control UI, currently called `UI2`.

UI2 is a task-centered reorganization of the existing UI. It must preserve current functionality and low-level diagnostic detail while making the common operator workflows easier to understand and execute.

## Status

This is a design-start spec, not an implementation request.

The goal of this draft is to make the intended direction concrete enough for critique. Open decisions are marked with `SID_QUESTION:` and should be resolved before a large UI implementation begins.

## Problem

The current UI exposes many useful capabilities, but the layout is organized around accumulated tools and tabs rather than the operator's current task.

Current pain points include:

- bringup actions, runtime controls, topology display, evidence, visibility, active group state, and raw decode data are spread across surfaces
- the topology diagram is useful in several workflows, but the UI still behaves as if topology management is a mode inside the bringup program
- incremental bringup and whole-robot diagnosis need different runtime activation behavior
- low-level detail is available, but its relationship to task-level conclusions is not always clear
- users can see a lot of data, but the UI does not consistently guide them toward the next useful action

The UI should make the selected task obvious without removing expert drill-down capability.

## Core Principle

UI2 must not remove diagnostic depth.

The default layout may hide advanced details, but every existing useful counter, raw value, evidence source, report, decode panel, and command output must remain available through drill-down or advanced panels.

## Goals

- Organize the UI around the operator's selected task.
- Support two primary task modes:
  - `Bringup`
  - `Diagnose`
- Treat topology as read-only inside this app.
- Keep the topology diagram as a shared visual work surface in both modes.
- Preserve all current lower-level data and diagnostic tools.
- Make runtime activation semantics match the selected task mode.
- Make active-group membership and scope visible and editable where appropriate.
- Make selected device and selected group status understandable without requiring the user to switch tabs.
- Keep expert-level raw data available for difficult failures and pit-side troubleshooting.

## Non-Goals

- Do not add topology editing to this UI.
- Do not remove the separate topology editor.
- Do not remove current evidence, visibility, raw decode, command output, or DSL capabilities.
- Do not treat UI2 as a cosmetic-only redesign.
- Do not implement broad behavior changes until the mode model and runtime activation contract are agreed.

## User Modes

UI2 has two primary modes.

## Bringup Mode

Purpose: validate newly connected hardware in an orderly, incremental way.

Bringup mode is for a robot or subsystem that may not be fully wired yet. The profile may define the full intended topology, but only a subset of devices should be active, instantiated, probed, or judged during the current bringup step.

Primary questions:

- Which device or small group am I bringing online now?
- Is it connected?
- Is it the expected device?
- For a motor, does it move when commanded?
- Are the basic signals sane enough to continue?
- What is the next device to add?

Expected default surfaces:

- read-only topology diagram showing all defined devices
- active-group or selected-scope panel
- eligible-device list with membership controls
- selected device or selected group inspector
- basic evidence summary
- manual right-click motion test controls
- stop and safety controls

Bringup mode should make out-of-scope devices visibly defined but not failed merely because they are not currently connected or instantiated.

SID_QUESTION: Should Bringup mode support multiple named bringup scopes directly, or should `active-group` remain the primary incremental workflow with named groups available only as an activation-scope selector?

## Diagnose Mode

Purpose: troubleshoot a robot that is expected to be functional.

Diagnose mode is for pit-side or bench-side failure analysis. The robot is assumed to be mostly or fully wired, but one or more devices, branches, tests, or CAN paths may be failing.

Primary questions:

- What is broken or suspicious?
- Which devices are missing, stale, degraded, or conflicting?
- Where should the user start looking physically?
- Is the failure likely a device issue, wiring issue, bus issue, power issue, or mapping issue?
- What raw evidence supports that conclusion?

Expected default surfaces:

- read-only topology diagram showing all defined devices
- whole-robot health summary
- CAN break or suspicious-region hints
- selected device or selected group inspector
- evidence summary and conflicts
- DSL/pre-written test launcher and results
- raw visibility and decode drill-down
- console evidence and command output

Diagnose mode should treat missing or stale profile devices as meaningful evidence unless explicitly filtered or marked out of scope.

SID_QUESTION: Should Diagnose mode have an explicit "known disconnected" override for intentional omissions, or should that be handled only through activation scope and profile selection?

## Topology Role

Purpose: use topology as the shared context without making this app a topology editor.

Topology in UI2 is read-only.

The topology diagram should:

- show all defined devices from the selected profile
- show logical groups and active scope
- show which devices are instantiated for the current runtime session
- show which devices are present or visible
- show selected device or selected group context
- show diagnostic status without conflating defined, scoped, instantiated, and present states

The topology diagram should not:

- create devices
- delete devices
- move devices
- edit topology links
- replace the topology editor

SID_QUESTION: What is the exact visual encoding for `defined`, `in scope`, `instantiated`, `present`, `failed`, and `not connected yet` so users do not confuse bringup omissions with diagnose failures?

## Runtime Activation

Purpose: make runtime behavior match the selected UI mode.

Runtime activation cannot mean the same thing in both modes.

In Bringup mode, runtime activation should activate only the intended scope plus required infrastructure. This avoids console spam and questionable code paths for devices that are defined but not wired yet.

In Diagnose mode, runtime activation should activate the whole selected profile unless the user explicitly chooses a narrower diagnostic scope.

The detailed activation contract is covered by `docs/FEATURE_SPEC_SCOPE_AWARE_RUNTIME_ACTIVATION_AND_INCREMENTAL_INSTANTIATION.md`.

UI2 must present this contract clearly:

- the activation scope selector belongs next to `Runtime Activate`
- the UI owns the requested activation scope
- the robot runtime must synchronize to the requested scope or report an error
- empty scopes are no-ops with clear operator feedback
- deactivation always deactivates the active runtime

SID_QUESTION: Should the mode selector automatically set the default activation scope, with `Bringup` defaulting to `Group: active-group` and `Diagnose` defaulting to `All`?

## Required Infrastructure

Purpose: separate always-needed infrastructure from devices being incrementally brought online.

Some devices should be available regardless of selected bringup scope.

Initial required infrastructure:

- `roborio`
- `pdp/pdh`

Possible required or semi-required devices:

- CAN analyzer / observer
- driver controller
- limit switches attached to the active motor or subsystem

SID_QUESTION: Which non-motor devices are always-required infrastructure, and which are scope-controlled bringup devices?

## Data Preservation

Purpose: make sure UI2 reorganizes data instead of deleting it.

UI2 must preserve access to:

- passive CAN visibility
- unknown and unprofiled node visibility
- packet counts and rates
- CTRE raw decode data
- raw frame-derived counters
- active presence probe score
- active probe failed checks, warnings, and errors
- console evidence
- manual test evidence
- passive evidence
- final evidence interpretation
- current, voltage, duty, velocity, position, and position delta
- runtime JSON and dump reports
- DSL test definitions, execution, and results
- command log and ACK/OUT detail
- NetworkTables and bridge diagnostics

Default panels should summarize these data. Advanced panels should expose the full detail.

SID_QUESTION: Which current panels become always-visible, which become drill-down drawers, and which become advanced-only?

## Current Capability Mapping

Purpose: preserve existing functionality while relocating it into task-centered surfaces.

Proposed mapping:

- `Live Topology` becomes the shared read-only topology work surface.
- `Evidence` becomes a primary Diagnose surface and a Bringup drill-down.
- `Visibility` becomes a Diagnose advanced surface and a Bringup advanced drill-down.
- active-group controls become primary Bringup controls.
- active-group status and membership become a right-side Bringup panel.
- right-click device motor test remains available in both modes.
- right-click group motor test remains available in both modes where safe.
- DSL tests become primary Diagnose actions and advanced Bringup actions.
- console output and command ACK/OUT detail move to an always-available log drawer.
- reports remain available, but their location should follow task relevance.
- raw decode panels remain available in advanced Diagnose detail.

SID_QUESTION: Should the old tab names remain available during transition as a `Legacy` or `Advanced` area, or should UI2 immediately replace the tab structure once implemented?

## Bringup Layout Direction

Purpose: make the incremental workflow obvious.

Bringup mode should prioritize:

- current activation scope
- active-group membership
- eligible next devices
- primary member
- selected device details
- manual motion response
- basic evidence verdict
- stop and safety controls

Likely layout:

- top: global connection, profile, mode, activation scope, runtime controls, robot state, clock
- left: task actions for bringup only
- center: read-only topology diagram
- right: active scope and selected-device/group inspector
- bottom: compact evidence/test timeline or log strip
- drawer: advanced raw details

SID_COMMENT: The best current direction appears to be a hybrid of the previous mockups: a two-mode shell, topology-centered work surface, and a right-side task inspector.

## Diagnose Layout Direction

Purpose: make whole-robot troubleshooting faster under pressure.

Diagnose mode should prioritize:

- whole-robot health summary
- missing/stale/degraded devices
- CAN bus health
- suspected physical regions or branches
- selected device or selected group evidence
- quick manual tests
- pre-written DSL tests
- raw visibility and decode drill-down

Likely layout:

- top: global connection, profile, mode, runtime controls, robot state, clock
- left: diagnose actions and test launcher
- center: read-only topology diagram with diagnostic overlays
- right: selected device/group inspector plus fault clues
- bottom: evidence timeline, command output, or test results
- drawer: raw visibility, decode, counters, and full reports

SID_QUESTION: Should Diagnose mode initially show a clue-first panel before the topology, or should topology remain the center of the screen at all times?

## Selection Model

Purpose: avoid ambiguity between selected device, selected group, and active scope.

UI2 should distinguish:

- selected device
- selected group
- active runtime scope
- active-group membership
- current primary active-group member
- currently running manual or scripted test

The right-side inspector should change title and content based on what is selected:

- device selected: show device telemetry and evidence
- group selected: show group members, per-member telemetry, and group verdict
- active-group selected: show editable active-group membership and primary member
- no selection: show mode summary and next action guidance

SID_QUESTION: Should clicking the active-group outline select `active-group`, while clicking inside overlapping named groups selects the smallest containing group, or should group labels be the only group-selection target?

## Expert Drill-Down

Purpose: keep the tool useful for knowledgeable users and hard failures.

UI2 should support an advanced detail drawer or panel available from both modes.

Advanced detail should include:

- raw CAN visibility tables
- CTRE raw decode tables
- full active probe details
- full manual test data
- raw runtime JSON
- command log with ACK/OUT blocks
- NetworkTables bridge diagnostics
- report output

The advanced area should be resizable and scrollable.

SID_QUESTION: Should advanced detail be a bottom drawer, right drawer, separate tab within each mode, or detachable window?

## Safety

Purpose: keep motion controls explicit and constrained.

UI2 must preserve existing motion safety principles:

- right-click motor and group tests must use drag-only speed controls
- clicking the slider track must not jump to a high value
- stop controls must remain visible
- runtime inactive state must be obvious
- ownership errors must be shown as blocking errors
- group runs must show all commanded members and per-member response

Bringup mode should make scoped activation and small group tests the default. Diagnose mode may allow whole-robot activation, but manual motion still needs explicit operator action.

## Migration Plan

Purpose: reduce risk by moving from the current UI to UI2 in reversible steps.

Recommended phases:

1. Add a mode shell with `Bringup` and `Diagnose` while preserving existing tabs.
2. Move active-group and scoped activation controls into the Bringup task panel.
3. Add mode-aware right-side inspectors for device, group, and active-group selection.
4. Move whole-robot evidence, visibility, and DSL test workflows into Diagnose.
5. Add an advanced drawer that contains the old raw/detail surfaces.
6. Implement mode-specific runtime activation semantics.
7. Remove or rename legacy tab structure only after UI2 proves usable.

SID_QUESTION: Should UI2 be introduced as a separate launch command first, or should it replace the current UI behind a feature flag/preference?

## Acceptance Criteria

UI2 is acceptable only if:

- a new user can tell whether they are in Bringup or Diagnose mode
- Bringup mode supports one-device-at-a-time incremental workflow
- Diagnose mode supports whole-robot troubleshooting
- topology remains read-only
- all defined devices remain visible in topology
- out-of-scope bringup devices are not presented as failures
- missing diagnose devices are presented as evidence
- selected device, selected group, and active scope are not ambiguous
- expert raw details remain available
- runtime activation scope is visible before activation
- robot runtime state mismatch is surfaced as an error

## Open Questions

Purpose: collect unresolved questions that affect implementation size or operator behavior.

- SID_QUESTION: What exact UI control switches between `Bringup` and `Diagnose`?
- SID_QUESTION: Should the mode selection persist between launches?
- SID_QUESTION: Should a user be able to run DSL tests in Bringup mode, or should that require Diagnose mode?
- SID_QUESTION: Should active-group membership be editable only in Bringup mode, or also in Diagnose mode?
- SID_QUESTION: What is the minimum set of data that must stay visible without opening advanced drill-down?
- SID_QUESTION: Should UI2 keep a single command log shared by both modes?
- SID_QUESTION: Should status coloring have separate palettes for Bringup and Diagnose to avoid confusing `not wired yet` with `failed`?
