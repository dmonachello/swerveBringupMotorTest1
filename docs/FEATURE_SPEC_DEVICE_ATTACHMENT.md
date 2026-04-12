# Device Attachment UX Improvements

## Purpose
Define a consistent, low-friction workflow for DIO attachments and visual links in the topology editor and CLI.

## Background
Current attachment behavior spans logical ownership (host → attachment) and physical wiring (DIO → roboRIO). DIO devices are not CAN devices, yet they appear in the topology view and require clear, stable linking and persistence rules.

## Goals
- Make DIO attachment and wiring explicit and understandable.
- Allow unattached DIO devices without invalidating configs.
- Render attachment and wiring links consistently before and after restart.
- Ensure label rename updates references and informs the user.

## Non-Goals
- Changing robot-side behavior or CAN bus semantics.
- Introducing new schemas outside existing `bringup_system.json`.
- Removing existing attachment or wiring concepts.

## Definitions
- **Attachment link**: logical link from a host device to an attachment (e.g., motor → limit switch).
- **DIO wire**: physical wiring link from DIO device to roboRIO.
- **DIO rail**: visual offset used to render DIO devices off the CAN bus.

## UX Requirements (Topology Editor)
### DIO Creation
Purpose: Ensure DIO nodes are defined correctly.
- DIO devices must specify `Interface=DIO`, `Type=limitSwitch|encoderExternal`, and a DIO channel.
- Missing host attachment or wiring should warn on save, not block.

### Attachments
Purpose: Make logical ownership visible and stable.
- `Edit -> Attach Device (Logical)` creates an attachment link between a host and a DIO device.
- Attachment links are drawn between host and attachment (non-roboRIO hosts only).
- Attachment links should anchor to the center of the device shapes (visual stability).

### Wiring
Purpose: Show physical DIO wiring to roboRIO.
- `Edit -> Wire DIO to roboRIO` draws a dashed DIO wire.
- DIO wires should originate from the **top-center** of the roboRIO shape.
- DIO wires should terminate at the **top-center** of the DIO device shape.

### Legend
Purpose: Explain link semantics by color/line style.
- Include legend entries for:
  - Attachment (logical) — dashed brown line
  - DIO wire (roboRIO) — dashed blue line
  - CAN bus (physical) — solid black line

### DIO Placement (Persistence)
Purpose: Keep DIO placement stable across restarts.
- DIO free-Y values must be stored relative to the DIO rail (no double-offset).
- Diagram metadata must record the free-Y mode for DIO nodes.
- Legacy diagrams should be migrated on load (one-time offset correction).

### DIO Dragging
Purpose: Ensure drag behavior matches the cursor and stays stable.
- DIO nodes should not jump when drag starts.
- DIO nodes should not jump when drag ends (release).

### Rename Behavior (Topology Editor)
Purpose: Prevent broken references after label changes.
- On label edit, prompt to confirm rename and reference updates.
- If confirmed, update:
  - `bridgeConfig.byProfile.<profile>.groups[].members[].device`
  - `bridgeConfig.byProfile.<profile>.selectedDevice.device`
  - callout target labels
  - registry label mapping

## CLI Requirements
### Rename Device
Purpose: Keep references consistent across configuration data.
- `rename device <old> <new>` must update all references automatically.
- Emit an INFO summary listing updated reference categories and counts.

Reference categories:
- `profiles.devices`
- `devices.attachments`
- `bridgeConfig.groups`
- `bridgeConfig.selectedDevice`
- `diagram.nodes`
- `tests.devices`
- `tests.limitSwitch.id`
- `tests.rotation.encoderKey`
- `tests.deadbandSweep.encoderKey`

## Data & Schema Rules
Purpose: Keep schema stable and explicit.
- No schema removals; all changes are additive.
- Add a diagram metadata field for DIO free-Y mode:
  - `diagram.profiles.<profile>.dioFreeYMode = "rail"`

## Examples
### Example: DIO Warning (Save)
```
DIO devices are not fully attached/wired:
Not attached to host: lmt2
Not wired to roboRIO: lmt2

Continue saving?
```

### Example: Rename Summary (CLI)
```
INFO: Updated references for old_label -> new_label: profiles.devices(1), devices.attachments(2), tests.devices(1)
```

## Tradeoffs
- Warning-only validation allows incomplete DIO setups to persist, which may hide misconfigurations.
- Extra diagram metadata increases file size slightly, but avoids layout drift.

## Future Extensions
- Optional per-device “requires host attachment” flag for stricter validation.
- Distinct line styles for DIO attachment vs DIO wiring.
- Attachment direction arrows for clarity.
