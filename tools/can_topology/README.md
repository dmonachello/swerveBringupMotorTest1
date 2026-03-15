# CAN Topology Editor

## Purpose
Create a bringup profile JSON by sketching CAN nodes on a shared bus line.

## What It Does
Purpose: Turn a diagram into a `bringup_profiles.json` file.
- Add nodes (motors, sensors, PDH, etc.).
- Edit labels, CAN IDs, and optional fields.
- Export a single profile JSON ready for deploy.

## How To Run
Purpose: Launch the editor without extra dependencies.
```cmd
python tools\\can_topology\\can_top_editor.py
```

## Profile Validation
Purpose: Validate `bringup_profiles.json` for compatibility.
```cmd
python tools\\can_topology\\validate_profiles.py
python tools\\can_topology\\validate_profiles.py --path src\\main\\deploy\\bringup_profiles.json
python tools\\can_topology\\validate_profiles.py --strict
python tools\\can_topology\\validate_profiles.py --verbose
```
Checks:
- JSON parses and contains a `profiles` object.
- Allowed categories only (buckets, singletons, `devices`).
- Each entry has integer `id` in range -1 or 0-62.
- `devices` entries include `vendor` and `type`.
- `limits` entries use integer `fwdDio`/`revDio` and boolean `invert`.
- Duplicate CAN IDs are reported per profile.

## Workflow
Purpose: Describe the shortest path from sketch to JSON.
1. Click `Add` and enter device details.
2. Drag boxes to arrange them on the bus line.
3. Set the profile name (dropdown lists profiles from the loaded file).
4. File -> Save Profile As...
5. Or use File -> `Save to Deploy` to append/replace directly in `src/main/deploy/bringup_profiles.json`.
6. Use `Set As Default` to update `default_profile` on save.
7. Use File -> `Export PDF...` to write a printable PDF (requires `reportlab`).

## Details Panel
Purpose: Show fields not displayed on the boxes.
- Select any node to view full metadata (motor, limits, terminator, vendor/type).
- Diagram boxes show `label (id X)` only; type remains in the left list.

## Auto-Load
Purpose: Start with your existing profile if present.
- On startup, the editor reads `src/main/deploy/bringup_profiles.json` and loads
  its `default_profile` automatically.
- Use File -> Open Profile... to pick a different profile.

## Legacy File
Purpose: Keep the previous editor available for reference without accidental use.
- The old script has been moved to `tools/can_topology/legacy/can_topology_editor_OLD.py`.
- The active editor is `tools/can_topology/can_top_editor.py`.

## Notes
Purpose: Document limitations up front.
- Diagram positions are saved under `diagram.profiles.<profileName>` only.
- Nodes snap to the nearest bus segment and appear above or below the bus line (row 0/1).
- The canvas supports horizontal and vertical scrolling for large layouts.
- Box width shrinks when space is tight to reduce overlap.
- Drag empty space to move the bus line and connected nodes up or down.
- Use `Add Bus` and then click on the canvas to place a new bus segment (it will not shift existing buses).
- Drag either curved end of a bus segment to resize it; connected segments stay aligned.
- File -> `Undo` restores the last change (nodes, buses, callouts, and drag moves).
- Drag a node near a bus segment to move it to that bus (nearest bus wins).
- Drag a bus line to move it; connected nodes move with it.
- Hold `Ctrl` and use the mouse wheel to zoom in/out (View menu also works).
- Keyboard shortcuts:
  - `Ctrl+A`: select all nodes (devices + callouts).
  - `Ctrl+C`: copy selection.
  - `Ctrl+D`: duplicate selection.
  - `Ctrl+V`: paste.
  - `Delete` / `Backspace`: remove selected nodes/callouts.
  - `Ctrl+Z`: undo.
  - `Ctrl+L`: tidy selection (layout within bus bounds).
  - `Ctrl+Shift+L`: reset layout (reassigns rows/buses).
  - `Layout -> Tidy All`: align all buses into shared columns.
  - `Ctrl+0`: reset zoom.
  - `Ctrl++` / `Ctrl+=`: zoom in.
  - `Ctrl+-` / `Ctrl+_`: zoom out.
  - `Ctrl+G`: toggle snap-to-grid.
  - `Ctrl+Shift+G`: toggle smart guides.
  - `Ctrl+S`: save to deploy.
- Diagram layout metadata is saved under `diagram.profiles.<profileName>` and
  ignored by the robot and PC tools.
- Use `Add Callout` to create a text label with a leader line to a bus or node.
- Callouts are stored as nodes and follow the same drag/selection rules as devices.
- Select a node and use the Scale controls to resize that node's box; scale is saved
  in the diagram metadata.
- Select a callout and use the Callout Scale controls to resize it; scale is saved.
- Singletons (`pdh`, `pdp`, `pigeon`, `roborio`) allow only one node each.
- `devices` entries require `vendor` and `type`.
- `terminator` is an optional per-node flag (true/false) to mark a bus end.
- Vendor and device type fields use dropdowns populated from `src/main/deploy/can_mappings.json`
  (you can also type a custom value).

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

