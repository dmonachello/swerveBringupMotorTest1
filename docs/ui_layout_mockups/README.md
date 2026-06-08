# UI Layout Mockups

Purpose: Compare candidate Bringup Control UI organizations before changing the application layout.

These SVGs are deterministic wireframe images. They are meant to support discussion of task flow, panel priority, and information hierarchy. They do not describe final visual styling.

## Options

- [Option 1: Two-Mode Cockpit](option-1-two-mode-cockpit.svg)
- [Option 2: Workflow Stepper](option-2-workflow-stepper.svg)
- [Option 3: Topology Workbench](option-3-topology-workbench.svg)
- [Option 4: Mission Control](option-4-mission-control.svg)
- [Option 5: Queue And Evidence Board](option-5-queue-evidence-board.svg)

## Evaluation Criteria

- Supports incremental bringup without distracting the operator with full-robot failures.
- Supports diagnose mode by surfacing whole-robot clues and likely CAN break regions.
- Keeps topology read-only while using it as the spatial reference.
- Keeps actions scoped to the selected task mode.
- Preserves current capabilities without making all of them visible at once.

