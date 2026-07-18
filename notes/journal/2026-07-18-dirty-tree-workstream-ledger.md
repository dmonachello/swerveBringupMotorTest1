# Dirty Tree Workstream Ledger

## Purpose

Classify the current dirty tree into recoverable workstreams so the repo can be returned to a known engineering state without depending on lost chat context.

This ledger is based on the recovery snapshot at:

- `notes/recovery/2026-07-18_162335/`

## Summary

The current dirty tree is not one mixed blob. It separates into at least four meaningful workstreams:

1. centralized-control / shared UI state refactor
2. Obsidian documentation-maintenance pipeline
3. Java / robot-side and passive-diagnostics hardening work
4. recovery artifacts added during reconstruction

These workstreams are adjacent, but not identical. They should not be treated as one commit by default.

## Workstream 1: Centralized Control Refactor

### Intent

Move shared UI meaning out of scattered view-local logic and into common host-side state services.

Primary spec:

- `docs/FEATURE_SPEC_SHARED_UI_CONTEXT_AND_CENTRALIZED_CONTROL.md`

Primary files:

- `tools/can_nt/host_ui_state_service.py`
- `tools/can_nt/tests/test_host_ui_state_service.py`
- `tools/can_nt/bringup_ui.py`
- `tools/can_topology/live_topology_view.py`
- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/tests/test_bringup_ui_actions.py`
- `tools/can_topology/tests/test_live_topology_view.py`

Secondary related files:

- `docs/FEATURE_SPEC_SHARED_UI_CONTEXT_AND_CENTRALIZED_CONTROL.md`

### Recovered status

- real implementation exists in the dirty tree
- the work is cross-surface, not just a local UI tweak
- the shared-state service is new and tested

### Evidence

- `tools/can_nt/host_ui_state_service.py` is new and contains shared state contracts and resolvers
- `tools/can_nt/tests/test_host_ui_state_service.py` exists and passes
- `bringup_ui.py` and `live_topology_view.py` now consume shared profile/runnable/active-group logic

### Validation already observed

- `python -m pytest tools/can_nt/tests/test_host_ui_state_service.py`
- `python -m pytest tools/can_topology/tests/test_live_topology_view.py -q`

Both passed during recovery on July 18, 2026.

### Recommended commit boundary

This workstream is a strong candidate for its own checkpoint commit once reviewed for spillover.

## Workstream 2: Obsidian Documentation Maintenance Pipeline

### Intent

Build a repo-local documentation-maintenance pipeline for Obsidian knowledge graph upkeep, MOCs, glossary, health reporting, and related analysis.

Primary files:

- `tools/docs_maintenance/__init__.py`
- `tools/docs_maintenance/inventory.py`
- `tools/docs_maintenance/pipeline.py`
- `tools/docs_maintenance/artifacts.py`
- `tools/docs_maintenance/main.py`
- `tools/docs_maintenance/README.md`
- `tools/docs_maintenance/run_docs_maintenance.ps1`
- `tools/docs_maintenance/register_scheduled_task.ps1`
- `tools/docs_maintenance/tests/test_pipeline.py`
- `tools/docs_maintenance/reports/*.json`
- `docs/mocs/*.md`

Likely related docs:

- `README.md`
- `docs/ADD_A_NEW_DEVICE.md`

### Recovered status

- this is not speculative; it is implemented enough to have a pipeline, artifact writer, tests, reports, and generated MOCs
- the project appears to be in active local development and local execution state

### Evidence

- `tools/docs_maintenance/README.md` describes the pipeline
- `main.py` supports writing docs artifacts
- `artifacts.py` materializes MOCs and glossary/index content
- `pipeline.py` includes orphan detection, glossary entries, proposed MOCs, related-topic suggestions, and rename/terminology analysis
- `docs/mocs/` exists with generated or maintained hub pages:
  - `architecture.md`
  - `can_diagnostics.md`
  - `dsl.md`
  - `rest_api.md`
  - `robot_bringup.md`
  - `testing.md`
  - `topology.md`
  - `ui.md`
- `tools/docs_maintenance/reports/` contains run outputs dated July 18, 2026

### Scheduled-task finding

- the docs-maintenance project includes `register_scheduled_task.ps1`
- however, the earlier machine check did not find a currently registered scheduled task matching the expected tool names

Interpretation:

- the code supports scheduling
- the repo evidence does not show that the scheduled task is currently installed from this session's checks

### Recommended commit boundary

This should be split from the centralized-control refactor.

It is a separate product/workflow with its own scripts, tests, outputs, and generated docs.

## Workstream 3: Java / Diagnostics Hardening Slice

### Intent

This slice appears related to Java-side command/runtime behavior plus passive-diagnostics / evidence / fault-inference hardening.

Primary modified files:

- `src/main/java/frc/robot/BridgeUiCommandHandler.java`
- `src/main/java/frc/robot/BridgeUiGroupCommands.java`
- `src/main/java/frc/robot/BridgeUiProfileCommands.java`
- `src/main/java/frc/robot/BuildInfo.java`
- `src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java`
- `src/main/java/frc/robot/manufacturers/ctre/util/PdpStatusReader.java`
- `src/main/java/frc/robot/tests/dsl/DslBringupTest.java`
- `src/test/java/frc/robot/BridgeUiGroupCommandsTest.java`
- `src/test/java/frc/robot/BridgeUiProfileCommandsTest.java`
- `src/test/java/frc/robot/DslBringupTestTest.java`
- `src/test/java/frc/robot/manufacturers/...` (new untracked subtree)
- `tools/can_nt/can_fault_inference.py`
- `tools/can_nt/passive_discovery_integration_service.py`
- `tools/can_nt/tests/test_passive_discovery_integration_service.py`
- `tools/can_nt/tests/test_bridge_cli_visibility.py`
- `tools/can_nt/generated/robot_local_commands_generated.py`
- `tools/common/build_info.py`
- `Feature Spec - CAN Bus Debug Final Push.md`

### Recovered status

- this slice is real, but its exact boundary is less cleanly recoverable than Workstreams 1 and 2
- it likely combines robot-side behavior changes with evidence/fault-diagnostics iteration

### Caution

This workstream may itself need splitting into:

- Java command/runtime/test changes
- passive-discovery / fault-inference changes
- generated build or command metadata changes

### Recommended action

Do not checkpoint this slice blindly with Workstream 1 or 2.

It needs one more pass of classification before commit planning.

## Workstream 4: Recovery Artifacts

### Intent

Preserve the current state and reconstruction trail after the chat-loss incident.

Files:

- `notes/journal/2026-07-18-centralized-control-refactor-recovery.md`
- `notes/recovery/2026-07-18_162335/*`
- this ledger file

### Recommended commit boundary

Either:

- keep these local until the source work is stabilized

or:

- commit them in a dedicated recovery/admin commit that is clearly separate from product code changes

## Files Most Strongly Associated With Each Workstream

### Centralized control

- `tools/can_nt/host_ui_state_service.py`
- `tools/can_nt/tests/test_host_ui_state_service.py`
- `tools/can_nt/bringup_ui.py`
- `tools/can_topology/live_topology_view.py`
- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/tests/test_bringup_ui_actions.py`
- `tools/can_topology/tests/test_live_topology_view.py`

### Docs maintenance

- `tools/docs_maintenance/*`
- `docs/mocs/*`

### Diagnostics / Java hardening

- `src/main/java/frc/robot/*`
- `src/test/java/frc/robot/*`
- `tools/can_nt/can_fault_inference.py`
- `tools/can_nt/passive_discovery_integration_service.py`
- related tests and generated metadata

### Recovery-only

- `notes/recovery/*`
- `notes/journal/2026-07-18-centralized-control-refactor-recovery.md`
- `notes/journal/2026-07-18-dirty-tree-workstream-ledger.md`

## Recommended Next Recovery Steps

1. Keep Workstream 1 and Workstream 2 mentally separate from this point forward.

2. Review Workstream 3 specifically for whether it hides multiple unrelated code changes.

3. Decide whether to:

- checkpoint Workstream 1 first
- checkpoint Workstream 2 first
- or create two separate recovery branches from the same frozen state

4. Avoid one giant catch-all commit.

That would recreate the ambiguity this ledger is meant to remove.
