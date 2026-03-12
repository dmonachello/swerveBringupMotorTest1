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
python -m tools.can_topology.can_topology_editor
```

## Workflow
Purpose: Describe the shortest path from sketch to JSON.
1. Click `Add` and enter device details.
2. Drag boxes to arrange them on the bus line.
3. Set the profile name.
4. File -> Save Profile As...
5. Or use File -> `Save to Deploy` to append/replace directly in `src/main/deploy/bringup_profiles.json`.
6. Use `Set As Default` to update `default_profile` on save.

## Details Panel
Purpose: Show fields not displayed on the boxes.
- Select any node to view full metadata (motor, limits, terminator, vendor/type).

## Auto-Load
Purpose: Start with your existing profile if present.
- On startup, the editor reads `src/main/deploy/bringup_profiles.json` and loads
  its `default_profile` automatically.
- Use File -> Open Profile... to pick a different profile.

## Notes
Purpose: Document limitations up front.
- Positions are for display only and are not saved in JSON.
- Nodes can be placed above or below the bus line; layout alternates rows.
- The canvas supports horizontal and vertical scrolling for large layouts.
- Box width shrinks when space is tight to reduce overlap.
- Drag empty space to move the bus line and connected nodes up or down.
- Use `Add Bus` to create another parallel bus segment connected by a bridge.
- Drag a node near a bus segment to move it to that bus (nearest bus wins).
- Hold `Ctrl` and use the mouse wheel to zoom in/out (View menu also works).
- Diagram layout metadata is saved under `diagram.profiles.<profileName>` and
  ignored by the robot and PC tools.
- Use `Add Callout` to create a text label with a leader line to a bus or node.
- Singletons (`pdh`, `pdp`, `pigeon`, `roborio`) allow only one node each.
- `devices` entries require `vendor` and `type`.
- `terminator` is an optional per-node flag (true/false) to mark a bus end.
- Vendor and device type fields use dropdowns populated from `src/main/deploy/can_mappings.json`
  (you can also type a custom value).
