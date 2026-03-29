Operator Surfaces Architecture

Purpose: Define how the CLI, GUI, and topology editor share layers, data, and responsibilities.

Overview
Purpose: Summarize the operator surfaces and the shared layers.
- Surfaces: Bridge CLI, Bringup Control UI (GUI), Topology Editor, Dashboards.
- Shared layers: BridgeSession, bridge_ops, unified config schema (bringup_system.json).
- Goals: Single source of truth for config data, consistent command behavior, and stable contracts.

Operator Surfaces
Purpose: List each surface and what it owns.

Bridge CLI
Purpose: Provide a Cisco-style operator console.
- Owns: Prompt modes, command parsing, batch execution.
- Uses: BridgeSession + bridge_ops for all command sends.
- Local view: Reads bridgeConfig.byProfile + profiles-derived devices for inspection and editing.

Bringup Control UI (GUI)
Purpose: Provide button-driven control and status output.
- Owns: UI layout, output panel, status indicators, and retry/timeout UI cues.
- Uses: BridgeSession + bridge_ops for all command sends.
- Local view: UI does not edit config; it is a runtime control surface.
- Live Ops: hosts the read-only live topology overlay (Phase 1).
- Live view can render bridgeConfig.byProfile group boxes/labels (toggle in the UI).

Topology Editor
Purpose: Define and visualize device topology and layout.
- Owns: Diagram layout, device placement, profile edits, and group overlays.
- Uses: bringup_system.json (profiles + optional bridgeConfig.byProfile).
- Does not: send commands or modify runtime state.

Dashboards (Shuffleboard/Glass)
Purpose: Visualize runtime status and diagnostics.
- Owns: Layout and visualization only.
- Uses: NetworkTables data published by robot and PC tools.

Shared Layers
Purpose: Define the shared modules used by multiple surfaces.

BridgeSession
Purpose: Centralize TCP connection, ACK/OUT parsing, and runtime state snapshot.
- Used by: CLI and GUI.

bridge_ops
Purpose: Centralize command wrappers and local config logic.
- Used by: CLI and GUI for all command sends.
- Contains: show/group/binding/selected-device operations and local config helpers.

Unified Config (bringup_system.json)
Purpose: Store profiles, diagram, and bridgeConfig.byProfile in one file.
- Used by: CLI and topology editor.
- Contract: bridgeConfig is optional; profiles + diagram are authoritative for device lists.

Data Ownership
Purpose: Specify who owns which data.
- Device registry + profiles + diagram: owned by topology editor or manual JSON edits.
- bridgeConfig.byProfile (groups, bindings, selectedDevice): owned by CLI and runtime tools.
- Runtime state: owned by robot (TCP UI) and published to NT for dashboards.

Data Flow
Purpose: Explain how data moves between surfaces.
- Topology editor writes profiles/diagram to bringup_system.json.
- CLI loads bringup_system.json, edits groups/bindings, and writes bridgeConfig.byProfile back.
- CLI can write unified bringup_system.json (profiles + bridgeConfig.byProfile) for a single source.
- GUI reads runtime state; it does not edit config files.

Examples
Purpose: Show common workflows.

Example: Topology -> CLI
- Edit devices and layout in topology editor.
- Save to data/bringup_system.json.
- CLI: merge config data/bringup_system.json, add groups, then save unified-config.

Example: CLI-only
- CLI: create devices/groups, then save unified-config data/bringup_system.json.
- Optional: open topology editor and load canonical file for layout.

Example: Sniffer bootstrap
- Run sniffer --dump-profile to create a profile.
- Rename labels, open topology editor, then use CLI to add groups.

Failure/Absence Behavior
Purpose: Define behavior when components are missing.
- Robot disconnected: CLI edits are local only; GUI shows disconnected status.
- PC tool absent: robot continues; Java code must fail soft.
- Missing bridgeConfig: CLI groups start empty; profiles still load.

Output and Contracts
Purpose: List stable contracts and keys.
- bringup_system.json schema_version 4.
- bridgeConfig schemaVersion 2.
- NetworkTables keys remain under bringup/diag/...

Tradeoffs
Purpose: Document known design tradeoffs.
- Centralizing command sends in bridge_ops reduces drift but adds indirection.
- Keeping profiles and bridgeConfig.byProfile in one file simplifies sharing but requires strict ordering and clear ownership.
- UI retry logic is shared to align behavior but still visualized differently per surface.

Future Extensions
Purpose: Track safe next steps.
- Add a small operator-surface "status" panel that shows which file is loaded and last saved.
- Add a spec-to-code checklist test to guard shared-layer usage.
- Add a UI-only indicator when bridgeConfig.byProfile groups are missing from the canonical file.
