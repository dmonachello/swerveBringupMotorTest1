# Topology Editor Manual Retest Checklist

Purpose: Provide a targeted manual retest pass after topology editor changes and after reviewing the `can-topology-editor-20260515` branch.

## Test Setup

- Launch:
  - `python -m tools.can_topology.can_top_editor`
- Primary profile:
  - `robot_2026_swerve`
- Suggested screen coverage:
  - normal desktop width
  - maximized on a wide monitor
- Record for each step:
  - pass/fail
  - notes
  - screenshot path if a visual problem appears

## 1. Load / Save / Restart

- [ ] Launch the editor.
- [ ] Load `robot_2026_swerve`.
- [ ] Verify the expected large profile appears:
  - 8 motors
  - 4 CANnect nodes
  - roboRIO
  - PDH
  - expected callouts and links
- [ ] Save the profile.
- [ ] Quit the editor.
- [ ] Relaunch the editor.
- [ ] Reload `robot_2026_swerve`.
- [ ] Verify nothing disappeared.
- [ ] Verify there is no exception on load.

Notes:

____________________________________________________________________________

## 2. Fit / Zoom / Pan Stability

- [ ] Use `Fit to Window`.
- [ ] Verify the diagram is framed sensibly.
- [ ] Verify the left edge of the diagram is visible and not clipped.
- [ ] Click empty canvas.
- [ ] Verify the viewport does not jump.
- [ ] Click a node without dragging it.
- [ ] Verify the viewport does not jump.
- [ ] Zoom in with the scroll wheel.
- [ ] Click empty canvas.
- [ ] Verify zoom/view is preserved.
- [ ] Zoom out with the scroll wheel.
- [ ] Click empty canvas.
- [ ] Verify the zoomed-out view is preserved.
- [ ] Pan with the middle mouse button.
- [ ] Click empty canvas.
- [ ] Verify the pan is preserved.

Notes:

____________________________________________________________________________

## 3. Selection Behavior

- [ ] Select one node.
- [ ] Verify a single click is enough to select it.
- [ ] Click empty canvas.
- [ ] Verify selection clears.
- [ ] Shift-select multiple nodes.
- [ ] Click empty canvas.
- [ ] Verify all selected nodes clear.
- [ ] Select a bus segment.
- [ ] Click empty canvas.
- [ ] Verify bus selection clears.

Notes:

____________________________________________________________________________

## 3A. Drag Stability

- [ ] Start from a sensible centered view.
- [ ] Select `pdh`.
- [ ] Drag `pdh` from the left side of the diagram toward the right.
- [ ] Verify only `pdh` moves.
- [ ] Verify the whole diagram does not jump left at drag start.
- [ ] Use `Fit to Window`, then zoom out.
- [ ] Drag `pdh` again.
- [ ] Verify the zoomed-out view does not collapse or snap left on first drag.

Notes:

____________________________________________________________________________

## 4. Wide-Screen Layout

- [ ] Maximize on a wide display.
- [ ] Use `Fit to Window`.
- [ ] Verify the diagram is reasonably centered.
- [ ] Verify the content is not shoved hard left with excessive blank space to the right.
- [ ] Verify important devices are not off-screen by default.

Notes:

____________________________________________________________________________

## 5. Bus Resize Behavior

- [ ] Resize a bus segment to the left.
- [ ] Resize the same segment to the right.
- [ ] Verify attached normal devices follow the segment bounds.
- [ ] Verify CANnect Direct nodes follow the segment bounds.
- [ ] Verify CANnect Inject nodes follow the segment bounds.
- [ ] Verify linked device connectors still line up.
- [ ] Save.
- [ ] Quit and relaunch.
- [ ] Reload the same profile.
- [ ] Verify the resized geometry is retained.

Notes:

____________________________________________________________________________

## 6. CANnect / Inject Behavior

- [ ] Add one CANnect Direct node.
- [ ] Add one CANnect Inject node.
- [ ] Link a device to a CANnect node.
- [ ] Add CAN bus links for the CANnect node.
- [ ] Set a CANnect port.
- [ ] Verify the assigned port renders correctly.
- [ ] Save, quit, reload.
- [ ] Verify the CANnect nodes, bus links, device links, and port assignment are retained.

Notes:

____________________________________________________________________________

## 7. Connection Filters

- [ ] Click `None` in the Connections filter.
- [ ] Verify all connection types disappear.
- [ ] Specifically verify the blue virtual/ethernet links disappear.
- [ ] Re-enable `CAN`.
- [ ] Re-enable `Power`.
- [ ] Re-enable `DIO`.
- [ ] Re-enable `PWM`.
- [ ] Re-enable `Analog`.
- [ ] Re-enable `Virtual`.
- [ ] Verify each category displays only its expected links.

Notes:

____________________________________________________________________________

## 8. Component Editing and Retention

- [ ] Edit one CAN motor device.
- [ ] Edit one encoder device.
- [ ] Edit the PDH device.
- [ ] Edit one DIO device.
- [ ] For at least one edited device, change:
  - label
  - CAN ID or DIO
  - vendor
  - device type
  - model
  - tags
- [ ] Save.
- [ ] Quit and relaunch.
- [ ] Reload the same profile.
- [ ] Verify the edited values are retained exactly.

Notes:

____________________________________________________________________________

## 9. Validation Messaging

- [ ] Create or edit a generic device so vendor and device type are missing.
- [ ] Trigger save or validation.
- [ ] Verify the error message names the exact device label.
- [ ] If practical, also test one invalid DIO device.
- [ ] Verify validation failures identify the offending configured entity clearly.

Notes:

____________________________________________________________________________

## 10. Callouts

- [ ] Add or edit a callout.
- [ ] Point one callout at a device.
- [ ] If supported, point one callout at a bus.
- [ ] Save.
- [ ] Quit and relaunch.
- [ ] Reload the same profile.
- [ ] Verify callout text, target, and placement are retained.

Notes:

____________________________________________________________________________

## 11. Basic Edit Operations

- [ ] Add a node.
- [ ] Edit that node.
- [ ] Remove that node.
- [ ] If undo/redo is available, verify it works for at least one edit.
- [ ] Save and reload.
- [ ] Verify no exception occurs.

Notes:

____________________________________________________________________________

## Highest-Priority Quick Pass

If time is limited, run these first:

- [ ] Load / save / quit / reload `robot_2026_swerve`
- [ ] `Fit to Window` then click empty canvas
- [ ] `Fit to Window`, zoom out, then drag `pdh`
- [ ] Middle-mouse pan then click empty canvas
- [ ] Resize a bus with CANnect/inject nodes present
- [ ] Use `None` filter and verify blue virtual links disappear
- [ ] Trigger invalid generic-device validation and verify the label appears in the error

