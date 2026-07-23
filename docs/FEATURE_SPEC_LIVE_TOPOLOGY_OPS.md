SPEC_STATUS: PARTIALLY_IMPLEMENTED

Live Topology Ops Feature Spec

Purpose: Capture the initial plan to combine topology visualization with live operations.

Summary
Purpose: Describe the feature in one paragraph.
Create a live "topology ops" surface that overlays real-time device state on the topology diagram and enables safe, targeted actions (select device, run tests, group actions). The feature builds on existing REST/TCP bringup control/state paths plus host-side diagnostics models and aims to deliver a high "wow factor" while preserving safety and clear ownership of config data.

Goals
Purpose: Define the desired outcomes.
- Use the topology diagram as a live status dashboard.
- Enable safe, intentional device/group operations from the diagram.
- Share command and session layers with existing CLI/GUI.
- Keep config editing separate from runtime actions.

Non-Goals
Purpose: Clarify what is out of scope for the first iterations.
- Replace the existing CLI or Bringup Control UI.
- Direct freeform duty control without safety gating.
- Real-time layout editing during live ops (config edits remain in edit mode).

Operator Surfaces Impact
Purpose: Define how this affects existing surfaces.
- Bringup Control UI gains a Live Ops view.
- Topology Editor remains edit-only.
- CLI remains supported and unchanged.

Live Ops Capabilities (Candidate)
Purpose: List potential operations by risk tier.

Tier 1: Read-Only (low risk)
- Presence (present/missing/stale)
- Basic telemetry (current, duty, temp, faults)
- Last seen timestamp
- Selected device indicator

Tier 2: Targeted Actions (medium risk)
- Select device (selected-device)
- Toggle selected-mode on/off
- Run test (device or group)

Tier 3: Live Control (high risk)
- Enable/disable group
- Live binding edits
- Direct duty control

Safety and UX Principles
Purpose: Define guardrails to prevent unintended actions.
- Default to read-only; explicit "Armed" toggle for actions.
- Clear visual "live" state and action confirmations.
- Respect robot enabled/disabled state and safety interlocks.
- Keep config edits separate from runtime operations.

Data Sources
Purpose: Identify the live data sources to render overlays.
- host-side visibility and evidence providers.
- REST runtime state: groups, selected-device, runtime status.
- Local config: label -> device identity mapping.

Mapping/Identity
Purpose: Ensure device labels link across systems.
- Device labels are authoritative and shared via bringup_system.json.
- Topology nodes map to labels; runtime state keys must align to labels.

Phased Delivery
Purpose: Break the feature into safe increments.

Phase 1: Live Overlay (Read-Only)
- Live status overlays on topology nodes inside the Bringup Control UI.
- No commands issued to robot.
- Tooltips/side panel show telemetry and status.
- Data source is REST runtime-state plus host-side diagnostics models.
- Offline test path uses a runtime-state JSON file (manual reload in UI).
- Update cadence is configurable; default 2 Hz.
- Routine UI polling should prefer a light snapshot path over a full diagnostic snapshot path.
- Light polling should prefer cheaper telemetry fields and avoid optional noisy reads when possible.
- Presence uses presenceConfidence (0.0-1.0) plus lastSeen timestamp.
- Faults are deferred to Phase 2 (explicit requirement).
- Group overlays (bridgeConfig.byProfile) can be toggled on/off in the live view.
- Color legend: green=present/fresh, orange=stale/weak, gray=absent/low.

Phase 2: Selected-Device + Tests
- Click node -> selected-device (with confirm).
- Button to toggle selected-mode.
- Run device test or group test.

Phase 3: Group Ops
- Enable/disable group.
- View and invoke group bindings.

Phase 4: Live Control
- Live binding edits.
- Direct output control with safety gating.

Dependencies
Purpose: List prerequisites and shared components.
- BridgeSession for TCP UI commands.
- bridge_ops for command wrappers.
- bringup_system.json for label mapping.
- shared host-side visibility/evidence state for live overlays.

Success Criteria
Purpose: Define how to know Phase 1 is complete.
- Topology nodes show live presence/health state without a robot crash.
- Overlay updates smoothly (no UI blocking).
- Labels match CLI/GUI device names.

Tradeoffs
Purpose: Record known tradeoffs.
- Live overlay requires consistent label mapping; incorrect labels reduce accuracy.
- Read-only first reduces risk but delays "wow" operations.
- Lighter polling reduces console noise and runtime overhead, but it may omit some deep diagnostic fields from the routine overlay path.

Future Extensions
Purpose: Track safe next steps.
- Click-to-select with confirmation.
- Inline group controls on group boxes.
- Operator audit log for actions.

