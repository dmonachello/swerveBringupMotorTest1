# Test Plan: Shared Contract Cleanup 2026-06-13

## Purpose

Verify the remaining audit cleanup for shared topology validation/projection and shared host-side runtime-state normalization.

This plan covers:

- shared topology validation authority across validator, schema store, CLI, and topology editor
- shared topology query/projection behavior for CLI topology lookups
- shared runtime-state attachment and field lookup behavior across Bringup Control UI and Live Topology
- regression safety for the broader host/robot workflow surfaces

## Scope

In scope:

- `tools/common/topology_validate.py`
- `tools/common/topology_query.py`
- `tools/common/runtime_state.py`
- `tools/can_topology/validate_profiles.py`
- `tools/config/schema_store.py`
- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/bringup_ui.py`
- `tools/can_topology/live_topology_view.py`

Out of scope:

- new robot-side runtime-state schema changes
- CAN protocol behavior changes
- new topology editor features unrelated to shared-contract ownership

## Automated Verification

Purpose: Prove the shared-core refactor did not break the maintained local contract suite.

Completed checks:

1. Focused unit and integration checks

```powershell
python -m unittest `
  tools.common.tests.test_topology_shared_contract `
  tools.common.tests.test_runtime_state_shared_contract `
  tools.common.tests.test_schema_store_profiles `
  tools.can_topology.tests.test_validate_profiles_topology `
  tools.can_nt.tests.test_bridge_cli_topology_show `
  tools.can_nt.tests.test_bridge_cli_visibility `
  tools.can_nt.tests.test_bringup_ui_actions `
  tools.can_topology.tests.test_live_topology_view
```

Expected result:

- all tests pass

2. Maintained local regression bundle

```powershell
python tools/can_nt/scripts/run_regressions.py --suite local
```

Expected result:

- `passed=9 failed=0`

3. Topology regression wrapper

```powershell
python tools/can_nt/scripts/topology_editor_regression.py
```

Expected result:

- `passed=2 failed=0`

## Manual Verification

Purpose: Verify the surface-level behavior that is still best checked by an operator across CLI and UI.

### Setup

1. Start the CLI against the robot or in the normal local host workflow you use for testing.
2. Start Bringup Control UI against the same profile/config world.
3. Use a profile with known topology data and runtime-state output.
4. If using a robot, keep tests non-motion unless a step explicitly requires safe motion.

### Section 1: CLI Topology Views

Purpose: Verify CLI topology show/lookups still reflect the shared topology query layer.

1. Run:

```text
show topology
show topology local --json --pretty
show topology neighbors local
show topology node "<known device label>"
show neighbors "<known device label>"
```

Expected:

- commands succeed
- known devices show stable `label`, `key`, `objectType`, `nodeClass`, `bus`, and neighbor data
- neighbor data is consistent across `show topology node ...` and `show neighbors ...`
- infrastructure nodes such as analyzers/junctions still display as non-device topology nodes when present

### Section 2: CLI Topology Validation

Purpose: Verify CLI validation uses the shared topology validation authority.

1. Run:

```text
validate topology
validate topology --verbose
```

Expected:

- valid configs print `OK: topology is valid.`
- verbose mode still prints the broader config validation passes and finishes with topology-valid output

Optional negative check:

1. Create or load a temporary config with:
   - duplicate topology node key
   - missing `deviceRef`
   - edge pointing to a missing node
2. Run `validate topology`.

Expected:

- each invalid condition is reported
- duplicate node key and missing edge endpoint are caught through the same rule set as standalone topology validation

### Section 3: Topology Editor Cross-Surface Contract

Purpose: Verify editor save/load still round-trips through the shared topology validation contract.

1. Open the topology editor.
2. Load the active profile.
3. Save the profile/config.
4. From CLI, run:

```text
validate topology
show topology local
show topology node "<known device label>"
```

Expected:

- save succeeds
- CLI can read the saved topology without compatibility fixes or missing-node issues
- known topology nodes still resolve correctly after save

### Section 4: Bringup Control UI Runtime-State Surfaces

Purpose: Verify Bringup Control UI and Live Topology still interpret runtime-state payloads consistently through shared runtime helpers.

1. Open Bringup Control UI on a profile with runtime devices present.
2. Click `Show Runtime State`.
3. Inspect:
   - `Output`
   - `Live Topology`
   - `Evidence`
   - `Visibility`

Expected:

- runtime-state fetch succeeds
- no Python exceptions
- device values such as duty, current, position, and presence still populate
- active probe and presence-check age displays look reasonable
- no surface shows obviously contradictory per-device runtime values when looking at the same device

### Section 5: Selected Device / Topology Cross-Check

Purpose: Verify topology metadata and runtime overlays still line up for the same device.

1. Pick one known motor device visible in both CLI and UI.
2. In CLI, run:

```text
show topology node "<device>"
show runtime-state robot
```

3. In UI, inspect the same device in `Live Topology` and `Evidence`.

Expected:

- same device label resolves in all surfaces
- topology identity is stable
- runtime overlay values such as presence, current, and command/applied values match the same underlying robot snapshot within normal timing differences

### Section 6: Non-Robot Local Runtime Path

Purpose: Verify the local/offline runtime-state path still works after shared runtime normalization changes.

1. Start the CLI in a local-only workflow where robot runtime is unavailable.
2. Run:

```text
show runtime-state --json --pretty
```

Expected:

- command succeeds
- JSON prints without crash
- output still includes a generated timestamp and local-mode runtime skeleton

## Pass Criteria

The cleanup passes when:

- all automated checks pass
- CLI topology queries and validation behave normally
- topology editor save/load remains readable by CLI and validator
- Bringup Control UI and Live Topology show stable runtime-state values without exceptions
- no cross-surface contradictions are observed for the same topology/runtime data

## Failure Notes

Record any failure with:

- command or UI action used
- active profile
- whether robot or local mode was active
- exact output or screenshot
- whether the mismatch was topology validation, topology projection, or runtime-state interpretation
