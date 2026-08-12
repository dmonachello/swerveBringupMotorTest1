# Status Review - August 3, 2026

## Purpose

Purpose: capture a grounded status review of the repo based on the current workspace, recent commits, and current architecture/readiness docs.

## Executive Summary

The project is in a late buildout and pre-1.0 hardening phase.

Core bringup and diagnostics functionality exists across both sides of the system:

- roboRIO-side Java bringup/runtime code
- Windows-first Python host tools
- passive CAN observation
- CLI and UI operator surfaces
- DSL authoring/validation on host and DSL execution on robot

The main gap is no longer basic architecture or whether the system can perform bringup at all. The main remaining gap is productization and consolidation on the host side:

- clearer supported workflows
- stronger workflow/application-service ownership
- better failure/recovery behavior
- stronger cross-boundary verification
- thinner Python presentation layers

## Current System State

Purpose: summarize what the system already does today.

This repo contains a combined FRC bringup and diagnostics system with two cooperating parts:

- robot-side WPILib Java bringup/runtime code on the roboRIO
- host-side Python tools for passive CAN observation, diagnostics, CLI/UI control, and evidence workflows

Supported bringup direction is no longer centered on NetworkTables. The current baseline is REST-driven or host-local diagnostics flows, while preserving strict separation between:

- robot-local telemetry gathered directly on the roboRIO
- CAN-bus-derived host diagnostics gathered on the PC

The Python side remains read-only on CAN for supported workflows.

## Recent Completed Work

Purpose: record the latest visible completed milestones from git history.

Recent commits indicate the following near-term progress:

- `893e436` on August 1, 2026: `Finish CANCoder and Pigeon 2 bringup support`
- `33165d3` on August 3, 2026: `Checkpoint UI runtime and DSL docs updates`

This suggests the repo is still actively evolving, but the work is now more focused on runtime/UI behavior, documentation, and supported-path hardening rather than foundational system creation.

## Active Work Signals

Purpose: describe the most visible in-progress themes from the current workspace state.

The current workspace and recently changed files point to three active themes:

- UI/runtime behavior and scope-control work in the host UI
- DSL runtime documentation and clarification work
- docs graph, glossary, and MOC cleanup

Representative files:

- [tools/can_nt/bringup_ui.py](../tools/can_nt/bringup_ui.py)
- [tools/can_nt/tests/test_bringup_ui_actions.py](../tools/can_nt/tests/test_bringup_ui_actions.py)
- [docs/DSL_INTERPRETER_RUNTIME.md](./DSL_INTERPRETER_RUNTIME.md)
- [docs/GLOSSARY.md](./GLOSSARY.md)
- [docs/DOCS_GRAPH_SUGGESTIONS.md](./DOCS_GRAPH_SUGGESTIONS.md)

## Architecture Status

Purpose: summarize the repo's current architecture direction and unfinished gap.

The layered architecture direction is partially implemented.

The repo's own architecture/spec material indicates that:

- the Java command/runtime path has already seen meaningful architecture progress
- the primary remaining architecture frontier is now the Python/host side
- workflow/application services are still weaker than they should be
- shared config/profile lifecycle and diagnostics normalization need stronger ownership
- Python presentation layers, especially the host UI, still carry too much behavior

This means the most valuable engineering work is likely to be selective host-side extraction and consolidation rather than a sweeping rewrite.

## What Looks Done Enough

Purpose: identify the major capability areas that already exist and are usable.

These areas appear established enough to count as core project capabilities:

- robot-side bringup harness
- host-side passive CAN diagnostics
- REST-backed command/control path
- CLI surface
- GUI surface
- DSL host-authoring and robot-execution pipeline
- profile/config-driven workflows

This does not imply perfect polish or final maturity. It means these are no longer speculative foundations.

## What Is Not Finished

Purpose: identify the major remaining gaps before the project can feel complete.

Based on the current readiness and architecture docs, the main unfinished areas are:

- one clearly blessed operator workflow
- stronger setup and environment verification
- stronger recovery and failure-mode guidance
- clearer feature maturity boundaries
- stronger verification across Java, Python, config, and transport contracts
- additional host-side workflow/service extraction

The project is therefore not feature-frozen. It is better described as selectively expanding, consolidating, and hardening.

## Constraints That Matter

Purpose: capture the repo rules that most directly shape future work.

Important constraints from repo instructions and current docs:

- Python tools must remain read-only on CAN.
- Supported flows must not reintroduce a required NetworkTables bridge.
- Robot-local telemetry and PC-observed CAN diagnostics must remain separate.
- UI/runtime behavior changes must be checked against `Current UI And Runtime Rules - V2.md` before changing operator-visible behavior.
- Real bug fixes should add the narrowest meaningful regression test unless automation is not practical.

These constraints materially narrow what counts as acceptable future functionality work.

## Assessment

Purpose: provide a concise project-level judgment.

The project appears to be past the question of whether it can basically perform bringup and diagnostics. It is now in the phase where the most important work is:

- consolidating host-side behavior into clearer ownership layers
- tightening supported workflows
- improving operator trust through better verification and failure handling
- continuing targeted functionality only where it directly strengthens the supported bringup path

In short:

- core capability: present
- product maturity: incomplete
- architecture cleanup: still needed
- targeted future functionality: still justified

## Suggested Next Engineering Focus

Purpose: identify the highest-leverage next coding direction implied by current state.

The strongest next engineering target is host-side runtime/scope workflow extraction from the UI layer into a shared workflow/service module.

Why this is the best next step:

- it matches the repo's own architecture priorities
- it reduces behavior drift risk across UI/CLI surfaces
- it strengthens the Python side where the docs say the biggest gap remains
- it improves maintainability without requiring a sweeping redesign

## Source Basis

Purpose: record the main sources used for this review.

This review is grounded primarily in:

- `git log` and current workspace state as of August 3, 2026
- [docs/ARCHITECTURE.md](./ARCHITECTURE.md)
- [docs/SPEC_LAYERED_ARCHITECTURE_REFACTOR.md](./SPEC_LAYERED_ARCHITECTURE_REFACTOR.md)
- [docs/RELEASE_1_0_READINESS.md](./RELEASE_1_0_READINESS.md)
- [docs/TEST_PLAN_TODAY.md](./TEST_PLAN_TODAY.md)
