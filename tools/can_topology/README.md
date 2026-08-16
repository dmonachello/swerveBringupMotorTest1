# CAN Topology Editor

## Purpose
Create a bringup profile JSON by sketching CAN nodes on a shared bus line.

## What It Does
Purpose: Turn a diagram into a `bringup_system.json` file.
- Add device nodes (motors, sensors, PDH, etc.).
- Add infrastructure nodes such as SWYFT CANnect Direct and Inject.
- Edit labels, CAN IDs, and optional fields.
- Maintain topology, diagram layout, and per-profile group overlays.
- Export a single profile JSON ready for deploy.
- Edit-only: live overlays are shown in the Bringup Control UI.
- Group overlays are shared with the UI live view.

## How To Run
Purpose: Launch the editor without extra dependencies.
```cmd
python tools\\can_topology\\can_top_editor.py
```

Version:
```cmd
python tools\\can_topology\\can_top_editor.py --version
```

## Profile Validation
Purpose: Validate `bringup_system.json` for compatibility.
```cmd
python tools\\can_topology\\validate_profiles.py
python tools\\can_topology\\validate_profiles.py --path src\\main\\deploy\\bringup_system.json
python tools\\can_topology\\validate_profiles.py --strict
python tools\\can_topology\\validate_profiles.py --verbose
```
Checks:
- JSON parses and contains `profiles` plus a devices table.
- Root `schema_version` matches the expected value (5).
- Root `data_version` is present and non-empty.
- Root `data_hash` is present and matches the computed value.
- devices table labels are unique.
- Profiles reference known device labels only and may not repeat labels.
- Device entries include required fields per interface (CAN, DIO, PWM, ANALOG).
- Attachment references must point at known device labels.

## Workflow

Purpose: Describe the shortest path from sketch to JSON.

1. Click `Add` and enter device details.
2. Drag boxes to arrange them on the bus line.
3. Set the profile name (dropdown lists profiles from the loaded file).
4. File -> `Save Config` writes the full current multi-profile config back to the path it was loaded from.
5. File -> `Save Config As...` writes the full current multi-profile config to a new path and keeps that path as the active source.
6. File -> `Save Profile As...` exports a standalone one-profile config JSON.
7. File -> `Save Selection As...` writes only selected nodes/callouts.
8. File -> `Save to Deploy` writes the current config state into `src/main/deploy/bringup_system.json`.
9. Save Selection As... never overwrites an existing file; it auto-suffixes `_1`, `_2`, etc.
10. File -> `Reload Canonical` reloads `src/main/deploy/bringup_system.json` into the editor.
11. Profiles menu: Import Profile... (external file -> canonical, with diagram metadata if present).
12. Profiles menu: Export Profile... (single profile to external file).
13. Profiles menu: Rename Profile... (default-profile designation follows the renamed profile).
14. Profiles menu: Delete Profile... (non-default only; last profile protected).
15. Destructive profile actions write a timestamped backup alongside the active file.
16. Use `Set As Default` to update `default_profile` on save.
17. Use File -> `Export PDF...` to write a printable PDF (requires `reportlab`).
18. Use File -> `Print Diagram...` to print without a manual export step.

Optional: Apply the updated devices/profiles tables payload without redeploy using the Bridge CLI `profiles push <path>`.

## Details Panel
Purpose: Show fields not displayed on the boxes.
- Select any node to view full metadata (interface, CAN identity, limits, terminator).
- Diagram boxes show the label with a separate `ID` line; type remains in the left list.
- Tags appear in the details panel for quick reference.
- Callout selections show a callout details panel (including target debug fields).
- The details dock is hidden by default and can be shown with View -> `Show Details Dock`.

## Interaction Rules
Purpose: Document the viewport and drag behavior the editor must preserve.
- Plain click is a no-op for viewport position and zoom.
- Clicking empty canvas may clear selection, but must not move the diagram.
- Drag does not begin until pointer motion crosses a real threshold.
- A real drag may move the selected object, bus, or connector, but must not shift the whole viewport.
- `Fit to Window` centers the diagram in the viewport and scales it without flashing through a wrong view.
- `Ctrl+MouseWheel` zoom anchors on the mouse position.
- Menu and keyboard zoom actions anchor on viewport center.

## Auto-Load
Purpose: Start with your existing profile if present.
- On startup, the editor reads `src/main/deploy/bringup_system.json` and loads its
  `default_profile` automatically.
- Use File -> Open Config... to load a different `bringup_system.json`, then pick a profile from that config.
- If `data_hash` is missing or mismatched, the editor can still open the file for repair.


## Legacy File
Purpose: Keep the previous editor available for reference without accidental use.
- The old script has been moved to `tools/can_topology/legacy/can_topology_editor_OLD.py`.
- The active editor is `tools/can_topology/can_top_editor.py`.

## Notes
Purpose: Document limitations up front.
- Topology-editor-written config files now include canonical root `topology.profiles.<profileName>` data for UI/editor interoperability.
- Nodes snap to the nearest bus segment and appear above or below the bus line (row 0/1).
- The canvas supports horizontal and vertical scrolling for large layouts.
- Box width shrinks when space is tight to reduce overlap.
- Drag empty space to move the bus line and connected nodes up or down.
- Use `Add Bus` and then click on the canvas to place a new bus segment (it will not shift existing buses).
- Drag either curved end of a bus segment to resize it; connected segments stay aligned.
- Drag the square bus-wrap handle to move the join side between connected bus segments.
- File -> `Undo` restores the last change (nodes, buses, callouts, and drag moves).
- Drag a node near a bus segment to move it to that bus (nearest bus wins).
- Drag a bus line to move it; connected nodes move with it.
- Drag a device onto a CANnect node (or use Edit -> `Link Device to CANnect`) to attach it.
- `Edit -> Fix CANnect Conflicts` removes CAN trunk links from Ethernet-linked CANnect nodes.
- Hold `Ctrl` and use the mouse wheel to zoom in/out (View menu also works).
- Zoom range is 10% to 200%.
- View -> `Show Warnings/Errors` toggles duplicate-ID badges.
- Paste drops selection near the current viewport (not original coordinates).
- Left list and right canvas are separated by a draggable splitter.
- Help -> Help... provides a topic list (overview, layout tips, profiles, shortcuts).
- Tags are freeform labels saved on device entries and diagram metadata.
- Exported files currently keep legacy `diagram.profiles.<profileName>` data alongside canonical root `topology.profiles.<profileName>` for compatibility during transition.
- Use `Add Callout` to create a text label with a leader line to a bus or node.
- Callouts are stored as nodes and follow the same drag/selection rules as devices.
- Select a node and use the Scale controls to resize that node's box; scale is saved
  in the diagram metadata.
- Select a callout and use the Callout Scale controls to resize it; scale is saved.
- devices table labels must be unique.
- `terminator` is an optional per-node flag (true/false) to mark a bus end.
- Vendor and device type fields use dropdowns populated from `src/main/deploy/can_mappings.json`
  (you can also type a custom value).
- Group overlays (from bridgeConfig.byProfile) can be toggled via View -> Show Group Overlays.
- Group overlays are rendered as solid colored outline boxes with separate labels.

## Groups (BridgeConfig)
Purpose: Use the topology editor to create and visualize groups.
- Multi-select device and infrastructure nodes, then use Groups -> Create Group from Selection...
- Groups are saved as per-profile group metadata in `bringup_system.json`.
- Group members are label-based and may include devices or infrastructure nodes.
- The editor draws solid colored group outline boxes (toggle in View menu).
- Runtime actions still depend on the member object type and supported function.
- Groups are optional and ignored by the robot code unless CLI/runtime workflows use them.
- The Bringup Control UI live view can also show these groups (Show Groups toggle).

## Keyboard Shortcuts
Purpose: Keep shortcuts documented in one place.
- `Ctrl+A`: select all nodes (devices + callouts).
- `Shift+Click`: multi-select nodes or buses (drag for marquee).
- `Ctrl+C`: copy selection.
- `Ctrl+D`: duplicate selection.
- `Ctrl+V`: paste.
- `Delete` / `Backspace`: remove selected devices/callouts from the current profile.
- `Ctrl+Z`: undo.
- `Ctrl+L`: tidy selection within bus bounds.
- `Ctrl+Shift+L`: reset layout (per-bus even spacing, preserves bus/row).
- `Ctrl+0`: reset zoom.
- `Ctrl++` / `Ctrl+=`: zoom in.
- `Ctrl+-` / `Ctrl+_`: zoom out.
- `Ctrl+MouseWheel`: zoom.
- `Ctrl+G`: toggle snap-to-grid.
- `Ctrl+Shift+G`: toggle smart guides.
- `Ctrl+S`: save to deploy.
- `Arrow keys`: nudge selected nodes (`Shift` = faster).
- `F2` or double-click: edit the selected cell in the node list.

## Layout Actions
Purpose: Define what layout operations do.
- `Tidy Selection`: align selected nodes into shared columns across buses.
- `Tidy All`: align all device nodes into shared columns across buses.
- `Reset Layout`: evenly spreads nodes per bus segment (no bus/row reassignment).
- `Align` / `Distribute`: horizontal alignment tools for selected nodes.
- `Auto Layout (Readable)`: groups nodes per bus and keeps CANnect clusters readable.

## Tags
Purpose: Group and sort nodes with freeform labels.
- Tags are comma-separated strings (e.g., `swerve`, `front-left`).
- Tags are stored on device entries in `bringup_system.json`.
- Use `Tags` menu actions to select, filter, tidy, or sort by tag.
- Use `Apply Tag to Selection` / `Remove Tag from Selection` to bulk edit tags.
- Tag filters accept expressions with `AND`/`OR`, `&&`/`||`, commas, or implicit OR (parentheses supported).
- `Select Filtered Nodes` converts the active filter into a selection.
- Filter dialog supports OR/AND append toggles and a scrollable tag list.

## Node List Editing
Purpose: Edit displayed fields directly in the left list.
- Double-click (or press `F2`) to edit `CAN ID`, `Type`, `Label`, or `Tags`.
- Multi-select rows, then edit a cell to apply that value to all selected rows.
- Validation runs on commit (Enter or click away).
- `Type` uses a dropdown (still accepts custom text).

## Bulk Edit
Purpose: Apply changes across many nodes at once.
- Edit -> Bulk Edit... applies changes to all selected nodes/callouts.
- Use Apply checkboxes to control which fields are updated.
- Label supports replace/prefix/suffix; tags support replace/add/remove.

## Help Menu
Purpose: Show where to find built-in help.
- Help -> Help... shows topic-based guidance.
- Help -> Keyboard Shortcuts... shows the shortcut list.
- Help -> About... shows the app version.

## Architecture
Purpose: Explain the post-refactor code layout and responsibilities.
- `tools/can_topology/can_top_editor.py`: Entry point and UI controller (TopologyEditor).
- `tools/can_topology/can_top_models.py`: Data model + constants (Node, category lists).
- `tools/can_topology/can_top_dialogs.py`: Modal dialogs for adding/editing nodes/callouts.

Data flow
- User action -> TopologyEditor handler
- Dialog returns values -> TopologyEditor updates Node data
- Editor redraws + serializes layout metadata

Tradeoffs
- The split keeps behavior stable but still leaves rendering, IO, and event logic
  in the main editor for now.

Future Extensions
- Move file IO and export helpers into a dedicated module.
- Extract canvas rendering and hit-testing into a drawing helper module.
- Add automated sanity checks for profiles before save.

