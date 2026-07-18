# Workstream 3 Split

## Purpose

Refine the previously ambiguous Java / diagnostics hardening slice into smaller, commit-sized sub-workstreams.

This note continues the recovery trail from:

- `notes/journal/2026-07-18-dirty-tree-workstream-ledger.md`

## Summary

The previously ambiguous slice is not one change. It separates into at least three smaller sub-workstreams:

1. scope/lifecycle terminology alignment
2. PDP reader hardening and DSL signal-behavior tests
3. shared evidence-to-fault snapshot integration

These should be reviewed independently.

## Sub-workstream A: Scope Terminology Alignment

### Intent

Align user-facing language away from older "controlled lifecycle" phrasing toward "scope" / "scope membership" phrasing.

### Files

- `src/main/java/frc/robot/BridgeUiGroupCommands.java`
- `src/main/java/frc/robot/BridgeUiProfileCommands.java`
- `src/main/java/frc/robot/commands/local/RobotLocalCommandRegistry.java`
- `tools/can_nt/bridge_cli.py`

### Recovered change shape

- message text changed from `controlled lifecycle scope` to `active scope membership`
- `Deactivate lifecycle` wording changed to `Deactivate scope`
- `Show Lifecycle State` wording changed to `Show Scope State`

### Interpretation

This is a coherent terminology/UX alignment slice.

It is small and should not be mixed with device-reader hardening or passive-diagnostics logic if avoidable.

## Sub-workstream B: PDP Reader Hardening And DSL Signal Semantics

### Intent

Harden PDP reads against repeated failures and extend DSL test behavior around signal disappearance and latching.

### Files

- `src/main/java/frc/robot/manufacturers/ctre/util/PdpStatusReader.java`
- `src/test/java/frc/robot/manufacturers/ctre/util/PdpStatusReaderTest.java`
- `src/main/java/frc/robot/tests/dsl/DslBringupTest.java`
- `src/test/java/frc/robot/DslBringupTestTest.java`

### Recovered change shape

`PdpStatusReader.java`:

- introduces `PowerDistributionAccess` abstraction
- injects `LongSupplier` clock
- adds cached read-failure cooldown behavior
- throws a cached `IllegalStateException` during cooldown instead of hammering repeated read failures

`PdpStatusReaderTest.java`:

- new untracked test file covering reader behavior

`DslBringupTestTest.java`:

- adds tests for power-distribution signal loss after initial success
- adds tests for motor require-latching behavior when a signal later disappears
- broadens signal-recording device helpers to support custom labels/device types and signal removal

### Interpretation

This is a coherent runtime/test-behavior hardening slice centered on:

- PDP probe/read resilience
- DSL signal semantics under disappearing telemetry

It appears materially separate from the centralized-control UI state refactor.

## Sub-workstream C: Shared Evidence Fault Snapshot Integration

### Intent

Move fault-finder derivation closer to the shared interpreted evidence layer so multiple consumers can use one frozen snapshot.

### Files

- `tools/can_nt/passive_discovery_integration_service.py`
- `tools/can_nt/can_fault_inference.py`
- `tools/can_nt/tests/test_passive_discovery_integration_service.py`
- `tools/can_nt/tests/test_bridge_cli_visibility.py`

Likely adjacent consumers:

- `tools/can_nt/bringup_ui.py`

### Recovered change shape

`passive_discovery_integration_service.py`:

- now imports `build_fault_diagnosis` and `render_fault_diagnosis`
- adds `build_evidence_fault_snapshot(...)`
- adds explicit snapshot keys:
  - `rows`
  - `result`
  - `renderedText`
  - `candidateCount`
  - `ranAt`
- adds clearer note constants for:
  - infrastructure passive presence
  - limited infrastructure corroboration
  - device-targeted stale/timeout console evidence
  - conflicts between console faults and stale positive evidence
  - infrastructure missing inference from fresh console timeout evidence

`can_fault_inference.py`:

- removes one branch that generated infrastructure-only fault candidates when no affected non-infrastructure rows existed
- now evaluates affected/degraded rows from the full row set instead of a prefiltered non-infrastructure subset

### Interpretation

This is a coherent passive-diagnostics / fault-finder integration slice.

It is adjacent to the centralized-control work because `bringup_ui.py` consumes the new shared snapshot, but the underlying ownership is diagnostics/evidence logic, not UI-state centralization.

## Sub-workstream D: Generated Metadata / Build Metadata Touches

### Files

- `tools/can_nt/generated/robot_local_commands_generated.py`
- `tools/common/build_info.py`
- `src/main/java/frc/robot/BuildInfo.java`

### Interpretation

These look like support or regeneration fallout, not clearly primary feature work on their own.

They should be reviewed to determine whether they belong with:

- terminology alignment
- diagnostics snapshot work
- or a separate generated-artifact refresh commit

## Recommended Commit Planning

Best current split:

1. centralized-control/shared UI state refactor
2. docs-maintenance pipeline
3. scope terminology alignment
4. PDP reader hardening + DSL signal semantics
5. passive-discovery evidence snapshot integration
6. recovery/admin notes

If fewer commits are desired, the safest merges are:

- merge 3 into 1 only if the terminology is intentionally part of the same operator-surface contract change
- merge 5 into 1 only if the goal is explicitly "shared UI meaning + shared evidence meaning" in one milestone

The least safe merge is:

- mixing 2, 3, 4, and 5 into one catch-all recovery commit

## Current Best Reading

The repository is recoverable to a known state because the dirty tree is no longer opaque:

- the centralized-control slice is identifiable
- the docs-maintenance slice is identifiable
- the remaining modified files can now be grouped into smaller coherent buckets

That is enough structure to start making intentional checkpoints instead of guessing.
