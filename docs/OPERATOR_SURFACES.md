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
- Local view: Reads per-profile bridge metadata plus profiles-derived devices for inspection and editing.

Bringup Control UI (GUI)
Purpose: Provide button-driven control and status output.
- Owns: UI layout, output panel, status indicators, and retry/timeout UI cues.
- Uses: BridgeSession + bridge_ops for all command sends.
- Local view: UI does not edit config; it is a runtime control surface.
- Live Ops: hosts the read-only live topology overlay (Phase 1).
- Live view can render per-profile group boxes and labels (toggle in the UI).

Topology Editor
Purpose: Define and visualize device topology and layout.
- Owns: Diagram layout, device placement, profile edits, and group overlays.
- Uses: bringup_system.json (profiles + optional bridgeConfig.byProfile).
- Does not: send commands or modify runtime state.
- Interaction rule: ordinary clicks, selection changes, and side-panel actions must not move the diagram viewport.

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
- Group membership is label-based over the shared object set, not device-only.

Data Ownership
Purpose: Specify who owns which data.
- devices table + profiles + diagram: owned by topology editor or manual JSON edits.
- Per-profile bridge metadata (groups, bindings, selected device): shared between topology editor, CLI, and runtime tools.
- Runtime state: owned by robot (TCP UI) and published to NT for dashboards.

Host vs Robot Context
Purpose: Prevent "active profile" confusion across surfaces.
- Host context: local editing/inspection state (which profile the CLI/topology editor is operating on).
- Robot context: runtime state on the roboRIO (which profile is active and which test is selected/running).
- Rule: host context MUST NOT change robot context unless an explicit TCP robot command is executed (e.g., `profiles activate`, `tests select/run`).
- Show commands support `[robot|local|both]` for many targets; `show workspace` is host-only.

File Map (By Surface)
Purpose: Clarify which files each surface reads/writes and how often they change.

Bridge CLI
- src/main/deploy/bringup_system.json: primary local config (profiles + devices table + groups). Change likelihood: high. Read: default.
- Loaded system config test section: tests edited by CLI. Change likelihood: high. Read: from the loaded system config.
- src/main/deploy/bringup_bindings.json: controller names/ports for inputSource validation. Change likelihood: low-medium. Read: default.
- src/main/deploy/can_mappings.json: CAN manufacturer/device-type names. Change likelihood: low. Read: default.
- .bridge_cli_settings.json: CLI preferences (message level). Change likelihood: low. Read: default.

Bringup Control UI
- src/main/deploy/bringup_system.json: profile list + labels for dropdowns/live view. Change likelihood: high. Read: default.
- Loaded system config test section: tests list for UI. Change likelihood: high. Read: from the loaded system config.
- src/main/deploy/bringup_bindings.json: controller labels. Change likelihood: low-medium. Read: default.
- src/main/deploy/can_mappings.json: CAN vendor/type names. Change likelihood: low. Read: default.

Topology Editor
- src/main/deploy/bringup_system.json: profiles + diagram + bridgeConfig.byProfile. Change likelihood: high. Read: default.
- src/main/deploy/can_mappings.json: vendor/type dropdowns. Change likelihood: low. Read: default.
- can_table.txt: import input only. Change likelihood: medium. Read: explicit (import command).
- profile.json: single-profile import/export. Change likelihood: medium. Read: explicit (load/save).

Live Topology View
- src/main/deploy/bringup_system.json: diagram + profiles for overlays. Change likelihood: high. Read: default.

Data Flow
Purpose: Explain how data moves between surfaces.
- Topology editor writes profiles/diagram to bringup_system.json.
- CLI loads bringup_system.json, edits groups and bindings, and writes per-profile bridge metadata back.
- CLI can write unified bringup_system.json (profiles + per-profile bridge metadata) for a single source.
- GUI reads runtime state; it does not edit config files.

Examples
Purpose: Show common workflows.

Example: Topology -> CLI
- Edit devices and layout in topology editor.
- Save to src/main/deploy/bringup_system.json.
- CLI: merge config src/main/deploy/bringup_system.json, assign or edit groups, then save config.

Example: CLI-only
- CLI: create devices/groups, then save config src/main/deploy/bringup_system.json.
- Optional: open topology editor and load the active deploy file for layout.

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
- bringup_system.json schema_version 5.
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
- Add a UI-only indicator when per-profile group metadata is missing from the active deploy file.

