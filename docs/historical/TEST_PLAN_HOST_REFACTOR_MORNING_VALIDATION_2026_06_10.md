# Test Plan: Host Refactor Morning Validation 2026-06-10

## Purpose

Define the complete validation plan for the morning test pass on Wednesday, June 10, 2026 after the host-side layering and shared-services refactor landed on Tuesday, June 9, 2026.

This plan is focused on proving two things:

- the host refactor did not break operator-visible behavior in the Bringup Control UI or Bridge CLI
- the newly shared host-side layers behave the same as the older surface-local paths they replaced

## Scope

Purpose: define what this morning pass covers and what it does not.

This plan covers:

- Bringup Control UI startup and session behavior
- Bridge CLI startup and core robot-facing command behavior
- shared config API and repository-owned `bringup_system.json` access behavior
- UI DSL import and validate actions
- UI test selection and execution controls
- UI config push and current-config download
- shared command lifecycle behavior:
  - connect
  - handshake
  - reconnect
  - pending-command gating
  - runtime-state refresh
- CLI show/runtime/test flows that now depend on the refactored shared layers

This plan does not require:

- validating every CLI command in the system
- validating topology editor authoring behavior
- validating passive CAN reverse-engineering outputs
- validating robot-side Java feature changes unrelated to the host refactor

## Refactor Areas Under Test

Purpose: name the code paths this morning pass is intended to validate.

Primary changed areas:

- [tools/common/config_api/repository.py](/abs/path/tools/common/config_api/repository.py)
- [tools/common/config_api/session.py](/abs/path/tools/common/config_api/session.py)
- [tools/common/config_api/snapshot.py](/abs/path/tools/common/config_api/snapshot.py)
- [tools/can_nt/bringup_ui.py](/abs/path/tools/can_nt/bringup_ui.py)
- [tools/can_nt/bridge_cli.py](/abs/path/tools/can_nt/bridge_cli.py)
- [tools/can_nt/bridge_ops.py](/abs/path/tools/can_nt/bridge_ops.py)
- [tools/can_nt/command_catalog_service.py](/abs/path/tools/can_nt/command_catalog_service.py)
- [tools/can_nt/command_workflow_service.py](/abs/path/tools/can_nt/command_workflow_service.py)
- [tools/can_nt/runtime_query_service.py](/abs/path/tools/can_nt/runtime_query_service.py)
- [tools/can_nt/test_execution_service.py](/abs/path/tools/can_nt/test_execution_service.py)
- [tools/can_nt/config_transfer_service.py](/abs/path/tools/can_nt/config_transfer_service.py)
- [tools/common/config_lifecycle/query_service.py](/abs/path/tools/common/config_lifecycle/query_service.py)
- [tools/common/robot_test_dsl/service.py](/abs/path/tools/common/robot_test_dsl/service.py)
- [tools/can_nt/scripts/config_api_guard.py](/abs/path/tools/can_nt/scripts/config_api_guard.py)

Main risks:

- UI actions appear enabled but do nothing
- canonical/deploy config load/save/sync behavior drifts after the repository cutover
- one surface sees different profiles/tests than another because a shared config query path regressed
- config push/download still works but local file persistence path is wrong or stale
- pending-command gating blocks valid actions or allows overlapping actions
- reconnect / handshake state gets stuck
- runtime-state refresh regresses after command completion
- DSL import or validate works in tests but fails in the real UI flow
- config push/download regresses because workflow ownership moved out of `bridge_ops.py`
- CLI show/test paths regress because wait/poll behavior changed

## Test Strategy

Purpose: explain the test order and why it is structured this way.

Run the morning pass in four stages:

1. Local non-robot sanity checks
2. UI session and host-local workflow checks
3. Robot-connected UI runtime workflow checks
4. Robot-connected CLI compatibility checks

This order is intentional:

- fail fast on local startup/import issues before touching hardware
- verify the UI-first flows the repo now prefers
- then verify CLI compatibility after the UI paths are known-good

This document now defines three reusable validation tiers:

- `Full Milestone Pass`
  - the complete morning validation after a large refactor milestone
- `Short Smoke Retest`
  - a fast cross-surface confidence pass after later smaller changes
- `Targeted Retest Matrix`
  - additional focused retests chosen by which host layer changed

## Test Tiers

Purpose: define how this plan should be reused after future refactor changes.

### Full Milestone Pass

Use this when:

- a major host refactor milestone lands
- shared command/session/runtime/config behavior changed in multiple places
- you need a high-confidence end-to-end validation checkpoint

What it includes:

- all stages in this document
- UI startup/session
- UI DSL workflow
- UI runtime/test workflow
- UI config transfer workflow
- UI command gating/recovery
- CLI compatibility workflow
- optional focused automated regressions

Expected duration:

- longest pass
- use this when validating a milestone boundary, not after every small edit

### Short Smoke Retest

Use this when:

- additional refactor work lands after a known-good milestone
- you need a quick confidence pass before deciding whether a full retest is necessary

Minimum smoke checks:

1. UI launch
2. UI connect and handshake
3. `Reconnect UI Session`
4. local profile list matches expected canonical config
5. one `Import DSL Test`
6. one `Validate DSL Tests`
7. one runtime activate
8. one selected-test dropdown change
9. one `Run Selected`
10. one `Show Runtime State`
11. one `Download Current Config` or `Push Config`, depending on what changed
12. CLI launch
13. `show runtime --json --pretty`

Pass rule:

- if all smoke checks pass and the later change was narrow, do not immediately rerun the whole milestone pass
- if any smoke check fails, stop and debug before broader retesting

### Targeted Retest Matrix

Use this when:

- the changed code is mostly contained to one host layer
- you want to rerun only the tests most likely to expose regressions in that layer

Rule:

- always run the `Short Smoke Retest`
- then add the targeted retests from the matrix below for the changed area

## Targeted Retest Matrix

Purpose: map refactor areas to the smallest additional manual retest set that should follow the smoke pass.

### Session-State And Command-Gating Changes

Examples:

- handshake logic
- owner-required recovery
- pending-command tracking
- reconnect behavior
- shared command workflow helpers

Run after smoke:

- `Reconnect UI Session`
- busy-gating test
- disconnect/reconnect recovery test
- owner-required path if reproducible
- CLI one-command send/wait path:
  - `show runtime --json --pretty`
  - `show tests --json --pretty`

### Runtime-State Fetch Or Interpretation Changes

Examples:

- runtime JSON fetch/query logic
- runtime-state parsing
- live overlay refresh rules
- runtime stale-state behavior

Run after smoke:

- `Show Runtime State`
- runtime activate
- runtime deactivate
- selected-test run followed by runtime-state observation
- confirm no stale pending state after runtime refresh

### DSL Workflow Changes

Examples:

- DSL import
- DSL validate
- DSL store resolution
- test dropdown population from DSL state

Run after smoke:

- `Import DSL Test`
- `Validate DSL Tests`
- re-import after source edit
- test dropdown selection for the imported test
- CLI fallback:
  - `show test <knownTestName> normalized --json --pretty`

### Local Config Repository Or Query Changes

Examples:

- profile discovery
- test inventory discovery
- canonical/deploy local config load or sync rules
- local root payload ownership

Run after smoke:

- profile list visibility in the UI
- selecting the intended profile
- test dropdown population for that profile
- `Import DSL Test`
- `Validate DSL Tests`
- `Download Current Config`
- `Push Config` if write semantics changed

### Shared Config API Or Storage-Layer Changes

Examples:

- `ConfigRepository`
- `ConfigSnapshot`
- `ConfigEditSession`
- canonical/deploy sync rules
- config API guard enforcement

Run after smoke:

- UI profile list check against canonical local config
- CLI `show profiles`
- one local config mutation through the UI:
  - `Import DSL Test`
  - `Validate DSL Tests`
- one persistence path check:
  - `Download Current Config`
  - `Push Config`
- one guard check:
  - `python tools/can_nt/scripts/config_api_guard.py`

### Config Transfer Workflow Changes

Examples:

- push config
- download current config
- robot apply/select/group replay sequencing

Run after smoke:

- `Download Current Config`
- `Push Config`
- runtime activate after push
- `Show Runtime State` after push
- one selected test run after push if the push touched test-related config

### Test-Execution Workflow Changes

Examples:

- select test
- run selected
- run all
- toggle enabled
- shared test execution service

Run after smoke:

- dropdown selection change
- `Run Selected`
- `Toggle Enabled`
- `Run All` if safe
- CLI:
  - `tests select <knownTestName>`
  - `tests run --wait`

### Command Catalog Or Host-Action Changes

Examples:

- generated command inventory loading
- host-local action merge rules
- action section composition

Run after smoke:

- command catalog presence check
- verify:
  - `Reconnect UI Session`
  - `Import DSL Test`
  - `Validate DSL Tests`
  - `Run Selected`
- confirm no expected action disappears from the UI

### CLI-Only Presentation Or Output Changes

Examples:

- CLI pretty-printing
- CLI wait/output formatting
- CLI parser-adjacent wiring to shared services

Run after smoke:

- CLI launch
- `show runtime --json --pretty`
- `show tests --json --pretty`
- one selected-test run
- one CLI-only DSL normalized inspection command

## Preconditions

Purpose: list the setup that must exist before starting the plan.

Required environment:

- Windows host machine
- repo workspace at the expected branch / working tree for the June 9, 2026 refactor
- Python environment that can run `tools/can_nt/can_nt_bridge.py`
- roboRIO reachable at the intended IP
- robot-side REST command server reachable on port `5805` unless overridden
- the local `bringup_system.json` and any DSL test files needed for validation

Recommended hardware/software readiness:

- one operator available to observe the UI and robot behavior
- one test profile already known to activate successfully on the robot
- at least one imported DSL test that is already expected to pass
- at least one DSL source file available for re-import
- NT available if the UI is being used in its normal connected mode

Suggested exact launch commands:

```cmd
python tools\can_nt\can_nt_bridge.py --ui --rio 172.22.11.2
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
```

Optional wrapper forms:

```cmd
tools\can_nt\run_can_nt.cmd --ui
tools\can_nt\run_can_nt.cmd --cli
```

If an offline sanity check is needed first:

```cmd
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

## Evidence To Capture

Purpose: define what evidence should be retained from the morning pass.

Capture these artifacts:

- pass/fail notes per test case
- screenshots of any UI failures or stuck states
- copied CLI output for any failing command
- the exact launch command used
- the selected profile name
- the selected test name when a test-related failure occurs
- whether the robot was enabled, disabled, estopped, or runtime-inactive when the failure happened

If a failure occurs during DSL import/validate:

- record the `.dsl` filename
- record the profile name
- save the exact validation output

If a failure occurs during push/download:

- record the file path used
- record whether the file was canonical local config or a separate exported copy

## Pass/Fail Rules

Purpose: define what counts as success for the morning pass.

A test case passes when:

- the operator action completes
- the expected UI/CLI output appears
- the system does not get stuck in an incorrect pending state
- no unexpected exception dialog, traceback, or silent no-op occurs

The morning pass is considered successful overall when:

- all critical tests pass
- no blocker-level regression is found in UI connect/handshake, DSL import/validate, test execution, or config push/download
- CLI compatibility checks complete without refactor-caused failures

The morning pass is considered blocked when:

- the UI cannot connect reliably
- handshake/reconnect gets stuck
- imported DSL tests cannot be validated or selected
- test execution commands stop working in the UI
- config push/download fails due to refactor-caused workflow breakage

## Severity Rules

Purpose: classify failures consistently during the morning pass.

Use these severities:

- `Blocker`
  - prevents continued UI or CLI use
  - examples:
    - UI cannot connect
    - commands never clear pending
    - push config always fails after the refactor
- `High`
  - major intended workflow broken but testing can continue in another path
  - examples:
    - DSL import broken but validate still works
    - Run Selected broken but CLI run still works
- `Medium`
  - behavior works with a workaround or incorrect UX/state reporting appears
  - examples:
    - wrong button enabled state
    - stale status label
    - duplicate log lines
- `Low`
  - cosmetic or minor logging issue with no workflow impact

## Test Matrix

Purpose: define the concrete test groups for the morning run.

Critical groups:

1. UI startup and session lifecycle
2. UI host-local DSL workflow
3. UI robot-backed test workflow
4. UI config transfer workflow
5. UI command gating and recovery behavior
6. CLI compatibility workflow

Secondary groups:

7. UI command catalog presence and action layout
8. Runtime-state refresh and observation behavior

## Stage 1: Local Non-Robot Sanity

Purpose: verify startup and obvious local regressions before relying on robot hardware.

### Test 1.1: UI launches cleanly

Steps:

1. Start the UI:

```cmd
python tools\can_nt\can_nt_bridge.py --ui --rio 172.22.11.2
```

2. Confirm the main window opens.
3. Confirm no startup traceback appears in the console.
4. Confirm the main action sections render.

Expected:

- UI opens successfully
- no startup exception
- action buttons and tabs appear

### Test 1.2: Command catalog contains expected host-local actions

Steps:

1. Inspect the UI action area.
2. Confirm these actions are present:
   - `Reconnect UI Session`
   - `Import DSL Test`
   - `Validate DSL Tests`
3. Confirm `Run Selected` is still present in the expected robot-backed action area.

Expected:

- host-local actions are visible
- robot-backed actions are still visible
- no action section is unexpectedly empty

### Test 1.3: Offline CLI starts cleanly

Steps:

1. Start offline CLI:

```cmd
python tools\can_nt\can_nt_bridge.py --cli --no-can --no-nt
```

2. Confirm CLI prompt appears.
3. Run a simple local command such as:

```text
show profiles
```

Expected:

- CLI starts without traceback
- local command path still works

### Test 1.4: Local config visibility is consistent across surfaces

Purpose: verify the shared config API did not split UI and CLI visibility of the same local config.

Steps:

1. In the UI, note the visible profile list.
2. In offline CLI, run:

```text
show profiles
```

3. Compare the visible profile names between UI and CLI.
4. Confirm the expected default/current profile is present.

Expected:

- UI and CLI show the same local profile inventory
- no profile is missing from one surface only
- no obvious stale canonical/deploy mismatch appears at startup

## Stage 2: UI Session And Host-Local Workflow Validation

Purpose: validate the UI paths most affected by the host refactor before deeper robot flows.

### Test 2.1: UI connect and initial handshake

Steps:

1. Launch the UI in connected mode.
2. Wait for REST connection to establish.
3. Watch status and pending labels during initial handshake.

Expected:

- UI reaches connected state
- handshake completes automatically
- pending state clears
- no repeated handshake loop

Failure clues:

- pending label never clears
- connection oscillates without stabilizing
- repeated handshake messages without successful ready state

### Test 2.2: Reconnect UI Session

Steps:

1. While connected and idle, click `Reconnect UI Session`.
2. Watch output and state labels.
3. Confirm the UI regains a good ready state.

Expected:

- reconnect action runs
- pending state clears after completion
- UI remains usable

### Test 2.3: Import DSL Test

Steps:

1. Select the intended profile in the UI.
2. Click `Import DSL Test`.
3. Choose a known-good `.dsl` file.
4. Accept or enter the intended test name.
5. Accept or enter the intended set name.

Expected:

- import completes without exception
- UI shows validation or success text
- imported test appears in the test dropdown after refresh
- no CLI dependency is required for the import itself

Capture:

- selected DSL file
- test name
- set name
- output text shown by the UI

### Test 2.4: Validate DSL Tests

Steps:

1. With the same profile selected, click `Validate DSL Tests`.
2. Review the output pane.

Expected:

- validation runs
- output is human-readable and complete
- known-good tests report success
- UI remains responsive after validation

### Test 2.5: Re-import after source edit

Purpose: specifically check the workflow concern discussed during the design pass.

Steps:

1. Make a small harmless edit to a test `.dsl` file outside the UI.
2. Use `Import DSL Test` again for the same test.
3. Run `Validate DSL Tests`.

Expected:

- re-import updates local config cleanly
- validate reflects the latest imported source
- no stale-content behavior appears

## Stage 3: UI Robot-Backed Runtime Workflow Validation

Purpose: verify that the refactored shared command/runtime layers still behave correctly in the main UI-first operator flow.

### Test 3.1: Profile selection and runtime activate

Steps:

1. Select the intended profile in the UI.
2. Click `Runtime Activate`.
3. Observe output, pending label, and any runtime-related status.

Expected:

- command sends successfully
- pending clears
- runtime becomes active
- no stuck handshake or stale owner state

### Test 3.2: Show Runtime State

Steps:

1. Click `Show Runtime State`.
2. Review the output.

Expected:

- runtime-state command completes
- output appears
- no pending-state deadlock occurs afterward

### Test 3.3: Test dropdown selection

Steps:

1. Choose an imported test from the dropdown.
2. Watch the output.

Expected:

- `selectTestByName` behavior still works
- selected test remains consistent
- pending clears after selection

### Test 3.4: Run Selected

Steps:

1. With one known-good test selected, click `Run Selected`.
2. Observe robot behavior and UI output.
3. Confirm the selected test result updates.

Expected:

- command sends
- test runs once
- UI remains responsive
- selected-test status/result updates

### Test 3.5: Toggle Enabled

Steps:

1. Select a known test.
2. Click `Toggle Enabled`.
3. Confirm enabled state changes.
4. Toggle it back.

Expected:

- enabled state changes correctly
- no stale selection or broken test table behavior

### Test 3.6: Run All

Steps:

1. Ensure the enabled set is known and safe.
2. Click `Run All`.
3. Observe sequencing and output.

Expected:

- batch execution starts
- UI does not enter an invalid command state
- active/running indication updates

### Test 3.7: Runtime deactivate

Steps:

1. When testing is idle, click `Runtime Deactivate`.

Expected:

- command completes
- runtime leaves active state
- UI returns to a clean idle connected state

## Stage 4: UI Config Transfer Workflow Validation

Purpose: specifically validate the config push/download flow now that ownership moved into a narrower shared transfer service.

This stage also validates the new repository-owned local config storage boundary.

### Test 4.1: Download Current Config

Steps:

1. Click `Download Current Config`.
2. Save to a new filename.
3. Confirm file is written.
4. Open the file and confirm it is valid JSON.

Expected:

- download succeeds
- file exists
- file is readable JSON

### Test 4.2: Push Config

Steps:

1. Click `Push Config`.
2. Select the intended `bringup_system.json`.
3. Use a known-good profile.
4. Observe output through completion.

Expected:

- push completes successfully
- profile apply/select/group import flow still works
- UI does not get stuck in pending state afterward

### Test 4.3: Push Config then Runtime Activate

Steps:

1. Immediately after a successful push, activate runtime again.
2. Run `Show Runtime State`.

Expected:

- no broken state transition after push
- runtime still activates successfully

### Test 4.4: Local DSL import persists into the canonical config view

Purpose: prove a local config mutation written through the shared config API is visible on the next read.

Steps:

1. Import one known-good DSL test from the UI.
2. Validate DSL tests from the UI.
3. In CLI, run:

```text
show tests --json --pretty
```

4. Confirm the imported test appears in the local test inventory.

Expected:

- imported DSL content persists
- a follow-up local read sees the same test inventory
- UI and CLI remain aligned on the stored local config state

### Test 4.5: Canonical local config path remains the active source of truth

Purpose: confirm the major surfaces still point at the same canonical config after the repository migration.

Steps:

1. In CLI, run:

```text
show sources --json --pretty
```

2. Record the reported local config source path.
3. In the UI, use profile refresh / local config-backed actions normally.
4. Confirm behavior matches the same expected local config file.

Expected:

- the CLI reports the expected canonical local config path
- the UI behaves as though it is reading the same local source
- no sign appears that one surface is reading a different local copy

## Stage 5: UI Command Gating And Recovery Validation

Purpose: verify the refactored shared command tracking still protects the UI correctly.

### Test 5.1: Busy gating

Steps:

1. Start a command that takes visible time.
2. While it is pending, attempt another action.

Expected:

- second action is blocked
- UI shows a busy/pending message
- no overlapping command corruption occurs

### Test 5.2: Disconnect / reconnect recovery

Steps:

1. Interrupt robot connectivity or restart the robot command endpoint if practical.
2. Observe UI recovery.
3. Reclaim the session with `Reconnect UI Session` if needed.

Expected:

- UI reports loss of connection or ownership clearly
- UI can recover cleanly
- no permanent broken pending state remains

### Test 5.3: Owner-required path

Steps:

1. If another client can take ownership, trigger that condition.
2. Observe the UI response.
3. Use `Reconnect UI Session`.

Expected:

- UI surfaces owner-required state clearly
- reconnect path restores control

## Stage 6: CLI Compatibility Validation

Purpose: confirm the CLI still behaves correctly on the refactored shared layers.

### Test 6.1: CLI connect and show runtime

Steps:

1. Start connected CLI:

```cmd
python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
```

2. Run:

```text
show runtime --json --pretty
```

Expected:

- command sends successfully
- CLI prints ACK/OUT flow correctly
- runtime JSON returns normally

### Test 6.2: CLI show tests

Steps:

1. Run:

```text
show tests --json --pretty
```

Expected:

- tests overview command still works
- output is unchanged or acceptably equivalent

### Test 6.3: CLI selected-test execution path

Steps:

1. Run:

```text
tests select <knownTestName>
tests run --wait
```

Expected:

- selected-test path still works
- run completes
- no refactor-caused wait/poll regression appears

### Test 6.4: CLI DSL inspection fallback

Purpose: verify the remaining CLI-only DSL inspection path still works alongside the new UI-first flow.

Steps:

1. Run:

```text
show test <knownTestName> normalized --json --pretty
```

Expected:

- normalized DSL output is still available

## Stage 7: Optional Focused Regression Commands

Purpose: run the already maintained automated checks if morning time allows.

Recommended commands:

```cmd
python -m unittest tools.common.tests.test_config_api_repository -q
python -m unittest tools.common.tests.test_local_config_query_service -q
python -m unittest tools.can_nt.tests.test_command_workflow_service -q
python -m unittest tools.can_nt.tests.test_bringup_ui_actions -q
python -m unittest tools.can_nt.tests.test_bridge_cli_robot_test_dsl_cli -q
python -m unittest tools.common.tests.test_robot_test_dsl_service -q
python tools/can_nt/scripts/config_api_guard.py
```

Optional broader regression:

```cmd
python tools/can_nt/scripts/run_regressions.py --suite dsl
python tools/can_nt/scripts/run_regressions.py --suite local
```

## Failure Triage Guide

Purpose: speed up diagnosis during the morning pass.

If the UI does not connect:

- check roboRIO reachability
- check REST port
- check whether the failure is network or handshake specific

If the UI is connected but commands never clear pending:

- note the last command name
- capture UI output
- try `Reconnect UI Session`
- compare with CLI behavior for the same command

If DSL import/validate fails:

- confirm selected profile
- confirm `.dsl` file path
- capture the exact output text
- verify whether CLI normalized inspection still works

If push/download fails:

- record the selected file path
- record whether the failure happened before send, during apply, or during post-apply profile/group steps

If CLI show/test commands fail while UI works:

- record the exact command
- capture ACK/OUT output
- treat it as a likely shared wait/workflow or CLI surface compatibility issue

## Stop Criteria

Purpose: define when to stop the morning pass and switch to debugging.

Stop immediately and switch to focused debugging if any of these occur:

- UI cannot reach a stable connected/handshaken state
- `Import DSL Test` fails for a known-good file
- `Validate DSL Tests` fails unexpectedly for a known-good local config
- `Run Selected` fails on a previously known-good test
- `Push Config` fails in a way that appears refactor-related
- CLI `show runtime --json --pretty` fails after the refactor

Continue the broader plan only after the blocker is understood.

## Suggested Morning Run Order

Purpose: provide one concise execution order.

Run in this exact order:

1. UI launch
2. command catalog presence check
3. UI connect and handshake
4. Reconnect UI Session
5. UI/CLI profile list consistency check
6. Import DSL Test
7. Validate DSL Tests
8. runtime activate
9. select test
10. Run Selected
11. Toggle Enabled
12. Run All if safe
13. Show Runtime State
14. Download Current Config
15. Push Config
16. runtime activate again
17. CLI launch
18. `show runtime --json --pretty`
19. `show tests --json --pretty`
20. `show sources --json --pretty`
21. `tests select ...`
22. `tests run --wait`
23. `python tools/can_nt/scripts/config_api_guard.py`
24. optional automated regressions

## Recording Template

Purpose: provide a simple format for real-time note taking.

Use this template during the pass:

```text
Test Case:
Time:
Operator:
Launch Command:
Profile:
Selected Test:
Result: PASS / FAIL / BLOCKED
Observed Output:
Observed Robot Behavior:
Severity:
Notes:
```

## Bottom Line

Purpose: summarize the intent of the morning pass in one paragraph.

The morning validation should prove that the host refactor preserved the UI-first operator workflow, preserved CLI compatibility, and did not break shared command/session/runtime/config behavior after those responsibilities were moved into shared host-side services.
