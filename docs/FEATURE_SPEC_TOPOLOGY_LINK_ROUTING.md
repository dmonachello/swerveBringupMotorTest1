SPEC_STATUS: NOT_IMPLEMENTED

# Feature Spec: Topology Link Routing

Purpose: define a routed-link feature for the CAN topology editor so connection lines avoid drawing straight through nodes.

## 1. Summary

Purpose: describe the user-visible change in one paragraph.

The topology editor currently draws most non-bus connections as straight point-to-point lines. On dense diagrams this causes power, virtual, CANnect, and other link lines to run directly through device boxes, making the diagram harder to read and causing ambiguity about what is connected to what. This feature adds obstacle-aware routed links so eligible connections are rendered as segmented paths that route around nodes while remaining deterministic and stable across redraws.

## 2. Goals

Purpose: define the outcomes the feature must produce.

- Improve readability of dense topologies.
- Prevent routed links from crossing through node boxes.
- Keep routing deterministic for the same topology state.
- Preserve existing saved topology data contracts.
- Allow staged rollout by connection type instead of requiring an all-at-once rewrite.

## 3. Non-Goals

Purpose: prevent scope creep.

- Do not change bus segment rendering in the first phase.
- Do not introduce spline or curved freeform routers in the first phase.
- Do not attempt full global crossing minimization in the first phase.
- Do not change how topology links are saved in `bringup_system.json`.
- Do not add new CLI or Java behavior in the first phase.

## 4. Problem Statement

Purpose: make the current failure mode explicit.

Current connection rendering has these limitations:

- straight lines can pass through device boxes
- multiple unrelated links can stack on top of each other
- dense CANnect clusters become difficult to interpret
- manual node movement can make the diagram temporarily unreadable even when the underlying topology is valid

The editor needs a rendering layer that treats nodes as obstacles and routes eligible links through legal corridors around those obstacles.

## 5. Definitions

Purpose: standardize terms used by the spec.

- `routed link`: a connection rendered as multiple orthogonal segments
- `obstacle`: a node rectangle expanded by a routing margin
- `corridor`: a legal horizontal or vertical path between obstacles
- `port anchor`: the start or end point for a routed connection
- `orthogonal routing`: horizontal and vertical segments with 90-degree bends only
- `routing stability`: small redraws should not completely reshuffle paths unless topology geometry actually changed

## 6. Scope

Purpose: define which connection classes are in scope for each stage.

### Phase 1

Purpose: deliver a useful first version with limited risk.

Phase 1 must support routed rendering for:

- power links
- virtual links
- CANnect device links
- CANnect ethernet-style links

Phase 1 must not route:

- main CAN bus segments
- bus connector curves between segments
- DIO rail lines unless implementation cost stays low

### Phase 2

Purpose: define the next expansion point without requiring it now.

Phase 2 may add routed rendering for:

- DIO links
- attachment links
- selected CAN trunk paths where useful

## 7. Functional Requirements

Purpose: specify required behavior.

### 7.1 Obstacle Avoidance

Purpose: prevent lines from crossing nodes.

- Routed links must not pass through any node box other than their source or destination node.
- Obstacles must use an expanded margin around each node, not the raw exact box edge.
- Source and destination ports remain valid entry and exit points.

### 7.2 Orthogonal Paths

Purpose: keep first-phase routing simple and readable.

- Routed links must be horizontal/vertical segmented polylines.
- Each bend must be a 90-degree turn.
- The implementation should prefer fewer bends when multiple valid paths exist.

### 7.3 Determinism

Purpose: avoid redraw jitter.

- The same topology geometry must produce the same routed path on repeated redraws.
- Path selection order must be stable and not depend on hash iteration order.

### 7.4 Port Anchoring

Purpose: preserve the meaning of connection endpoints.

- A routed link must begin at the same semantic port anchor currently used by the straight-line renderer.
- A routed link must end at the corresponding destination anchor.
- Port-aware node types such as CANnect nodes must continue to use explicit port anchors instead of node-center anchors.

### 7.5 Fallback Behavior

Purpose: keep the editor usable when no route is found.

- If the router cannot find a legal path, the editor must fail soft.
- Phase 1 fallback behavior should render the original direct line or a minimally processed direct line.
- Failure to route one link must not break drawing of the rest of the diagram.

### 7.6 User Control

Purpose: support safe rollout and comparison.

- The editor must provide a view toggle for routed links.
- The default may remain off in early integration, then turn on after stabilization.
- The toggle state does not need to be persisted in Phase 1 unless there is already an established view-state persistence pattern.

SID_QUESTION: Should routed-link mode become the default immediately after implementation, or ship first behind an opt-in `View -> Routed Links` toggle?

## 8. Routing Model

Purpose: define the preferred technical approach without locking every implementation detail.

### 8.1 Recommended Phase 1 Router

Purpose: define the practical first implementation.

Phase 1 should use an orthogonal visibility-graph or corridor-graph router:

- collect obstacle rectangles from current node bounds
- expand each obstacle by a configurable margin
- derive candidate X and Y guide lines from:
  - source/destination port coordinates
  - obstacle edges plus margin
  - bus Y coordinates where helpful
- build legal horizontal/vertical graph segments between visible guide intersections
- use Dijkstra or A* to choose a path

### 8.2 Routing Cost Heuristic

Purpose: keep paths visually sane.

The path score should prefer:

1. valid routes that do not intersect obstacles
2. fewer bends
3. shorter total path length
4. stable corridor reuse over arbitrary alternates

Phase 1 may ignore global crossing optimization if local readability is improved.

### 8.3 Link Ordering

Purpose: reduce nondeterministic path selection.

Eligible links should be routed in a stable order, for example:

- by connection type
- then by source key
- then by destination key

This gives repeatable path allocation when route occupation or tie-breaking matters.

## 9. Rendering Rules

Purpose: specify how routed paths appear.

- Routed links remain color-coded by connection type.
- Existing line style cues such as dash patterns should remain when possible.
- Routed links may share segments visually in Phase 1 if that is the simplest output.
- Phase 1 does not require bundled-lane separation for overlapping routed paths.

## 10. Data Contract Impact

Purpose: state what changes in saved data and what does not.

Phase 1 must be rendering-only.

- No changes to saved topology schema are required.
- No new route points should be persisted in `bringup_system.json`.
- Existing `canLinks`, `deviceLinks`, `ethernetLinks`, `powerLinks`, and related topology metadata remain authoritative.

If later work introduces manual route pinning or saved bend points, that must be a separate feature.

## 11. Performance Requirements

Purpose: define acceptable runtime behavior.

- Redraw remains interactive on normal editor-sized topologies.
- The routing pass must be fast enough not to make dragging feel broken.
- If full reroute during drag is too expensive, Phase 1 may:
  - route on drag release
  - or route only selected link classes during drag

SID_QUESTION: During node drag, should routing recompute continuously, or should Phase 1 recompute only after drag release for stability and performance?

## 12. UI Requirements

Purpose: define the operator-facing controls.

- Add `View -> Routed Links` toggle.
- Optional status text or tooltip may describe routed links as obstacle-aware connection rendering.
- No new modal dialogs are required for Phase 1.

## 13. Testing Requirements

Purpose: define objective acceptance checks.

### 13.1 Headless Geometry Tests

Purpose: validate routing math without real UI interaction.

Add regression tests for:

- routed path does not intersect unrelated node rectangles
- routed path begins and ends at expected anchors
- stable topology fixture yields deterministic route segments
- fallback behavior occurs when no route is available

### 13.2 Fixture Coverage

Purpose: exercise dense and sparse layouts.

At minimum include:

- simple two-node power link
- CANnect cluster with linked devices
- dense `robot_2026_swerve`-style layout
- one intentionally constrained layout where no legal path exists

### 13.3 Manual Verification

Purpose: confirm visual quality that headless tests cannot fully judge.

Manual checks must include:

- routes visibly avoid nodes
- labels remain readable
- no major redraw jitter during common edit operations
- routed-link toggle behaves predictably

## 14. Rollout Plan

Purpose: reduce integration risk.

### Stage 1

Purpose: land reusable routing helpers without turning them on broadly.

- build obstacle collection
- build orthogonal pathfinder
- add geometry tests

### Stage 2

Purpose: enable one or two link classes first.

- route power links
- route CANnect virtual/device links
- expose `View -> Routed Links`

### Stage 3

Purpose: expand usage after stabilization.

- add more connection classes
- tune corridor heuristics
- reduce ugly overlaps where practical

## 15. Definition Of Done

Purpose: define when this feature is complete for Phase 1.

- Routed links are available in the topology editor behind a stable toggle or enabled default.
- Phase 1 link classes route around node obstacles.
- No schema changes are required to save or reload existing profiles.
- Topology regression suite covers routing geometry and fallback behavior.
- Manual verification confirms improved readability on dense topologies.

## 16. Tradeoffs

Purpose: make the costs explicit.

- Orthogonal routing is easier to reason about than spline routing, but can still look mechanical.
- Phase 1 obstacle avoidance improves readability without solving all line crossings.
- Rendering-only routing is safer than persisted manual routes, but users cannot hand-author custom bend points.
- Stable deterministic routing may sometimes choose a slightly longer path in exchange for reduced jitter.

## 17. Future Extensions

Purpose: capture likely follow-on work without coupling it to Phase 1.

- route additional connection classes
- lane separation for overlapping paths
- route bundling near shared trunks
- manual bend-point or route-pin editing
- saved preferred routes
- path smoothing after orthogonal route generation
- localized reroute around selected nodes only

