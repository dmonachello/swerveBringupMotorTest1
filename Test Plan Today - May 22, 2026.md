# Test Plan (May 22, 2026)

  

## Purpose

  

Validate the full change window from May 15, 2026 through May 22, 2026, with emphasis on the last major checkins:

  

- config ownership cutover to `src/main/deploy/`

- topology upgrade and cross-surface compatibility

- CLI visibility, TIU, and bindings diagnostics

- robot-local command modularization and generated host UI metadata

- DSL signal-provider modularization and controller/device signal behavior

  

## Scope

  

This plan replaces the older storage-layer-only pass.

  

This pass is intended to answer:

  

- Does the repo still pass its maintained local regression surface?

- Do topology editor, shared parsers, schema store, CLI readers, and exports still agree on one topology/config contract?

- Do deploy-owned config paths behave correctly after removal of runtime fallbacks and legacy `data/` ownership?

- Do robot-local commands still behave the same after the Java registry/executor refactor?

- Do DSL tests still resolve controller/device signals correctly after provider-based modularization?

  

## Change Window Under Test

  

Commits in scope for this plan:

  

- `05b0481` `Unify topology rendering across editor and UI`

- `f1559c0` `Add swerve club test config and feature docs`

- `a1fe22c` `Align topology PDF export with editor scene`

- `1548a4f` `Add CLI visibility, TIU, and bindings diagnostics`

- `92d7b9f` `Remove runtime config fallbacks and document robot base`

- `5d7e439` `Cut over config tooling to deploy-owned files`

- `b1f4db7` `Remove legacy data directory files`

- `5df0dcf` `Merge branch 'topology_upgrade'`

- `8f6dabf` `Modularize robot local commands and DSL signal providers`

  

## Test Objectives By Risk Area

  

### 1. Config Ownership And Path Cutover

  

Purpose: verify host-side tools now consistently use deploy-owned files and fail safely without legacy runtime fallbacks.

  

Primary risks:

  

- stale references to deleted `data/` config files

- schema store and CLI reading different sources

- host context and robot context becoming ambiguous

- missing bindings/controller data breaking validation paths

  

### 2. Topology Upgrade And Cross-Surface Compatibility

  

Purpose: verify the root topology graph, editor, shared parsers, validation, CLI readers, live view behavior, and PDF/export paths still agree.

  

Primary risks:

  

- editor save/load drift from canonical graph shape

- infrastructure nodes leaking into runtime device registries

- scene/render mismatch between editor and exported outputs

- cross-surface regressions between editor save, schema store, and CLI consumers

  

### 3. CLI Visibility, TIU, And Bindings Diagnostics

  

Purpose: verify new visibility/bindings diagnostics did not break canonical CLI behavior or config workflows.

  

Primary risks:

  

- parser/help/spec drift

- new diagnostics surfacing wrong host-vs-robot context

- visibility output breaking regression assumptions

  

### 4. Robot-Local Command Modularization

  

Purpose: verify the new canonical Java command registry/executor preserved behavior across controller and host-UI command paths.

  

Primary risks:

  

- controller-triggered and UI-triggered commands diverging

- command metadata generation drifting from Java registry truth

- queue/interrupt/single-active behavior regressing

- compatibility adapter paths masking missing commands

  

### 5. DSL Signal Provider Modularization

  

Purpose: verify device-owned signal providers and controller signal expansion preserved runtime semantics.

  

Primary risks:

  

- signal read/write/clear semantics changing silently

- unsupported clear targets no longer failing clearly

- Xbox/controller signal names resolving inconsistently between host and robot

- non-motor devices such as DIO-backed limit switches failing DSL validation or runtime

  

## Preconditions

  

- Repo root: `C:\Users\dmona\swerveBringupMotorTest1-main`

- Windows shell with `python` on `PATH`

- Java available for `.\gradlew.bat test`

- If Java tests are run with `JAVA_HOME` set, it must point at the JDK root, not `bin`

- For local-only CLI checks, use `--no-can --no-nt`

- For connected robot checks, roboRIO must be reachable and the TCP UI endpoint available

  

## Execution Order

  

Run the pass in this order:

  

1. Automated local regression gates

2. Targeted config and CLI checks

3. Topology editor and cross-surface manual checks

4. Java and robot-local-command focused checks

5. Connected non-motion robot checks

6. Optional live CAN/NT checks if the task being verified touched runtime diagnostics

  

## A) Automated Local Regression Gates

  

Purpose: confirm the maintained local baseline is still green before targeted manual work.

  

Run:

  

```text

python tools/can_nt/scripts/run_regressions.py --suite local

python tools/can_nt/scripts/run_regressions.py --suite dsl

python tools/can_nt/scripts/run_regressions.py --suite topology

python tools/can_nt/scripts/run_regressions.py --suite cross-surface

python tools/can_nt/scripts/run_regressions.py --suite cli

python tools/can_nt/scripts/run_regressions.py --suite java

python tools/can_nt/scripts/run_regressions.py --suite changelog

```

  

Expected:

  

- all suites pass

- no baseline drift unless an intentional behavior change was made and expected outputs were refreshed in the same change

- no command path points at deleted `data/` config files

  

SID_COMMENT:

- Record each suite result here with pass/fail and any unexpected baseline drift.

  

## B) Config Ownership And Source-Of-Truth Checks

  

Purpose: verify deploy-owned config files are now the host-side default and legacy fallback assumptions are gone.

  

### B1. Verify Checked-In Config Locations

  

Check:

  

- `src/main/deploy/bringup_system.json` exists

- `src/main/deploy/bringup_bindings.json` exists

- legacy `data/bringup_system.json` and `data/motor_specs.json` are absent

  

Expected:

  

- host tools rely on deploy-owned config

- no user-facing docs or errors still direct users to the removed `data/` copies

  

### B2. Local CLI Validation Pass

  

Run:

  

```text

python tools/can_nt/can_nt_bridge.py --cli --no-can --no-nt

configure terminal

validate config

bindings validate

can-mappings validate

show config dirty

show tests

show can-mappings

end

```

  

Expected:

  

- config validation succeeds or points at the exact invalid entity

- bindings validation fails soft if optional controller bindings are absent

- dirty-state output is stable and source-aware

- show commands report the correct local source context

  

### B3. Host Context Versus Robot Context

  

Check:

  

- editing local config does not implicitly change robot active profile

- any profile-selection output clearly distinguishes host-local state from robot runtime state

  

Expected:

  

- no command or message implies that local editing alone activates a robot profile

  

SID_COMMENT:

- Capture any message that still confuses host-selected profile with robot-active profile.

  

## C) CLI Visibility, TIU, And Diagnostics Checks

  

Purpose: validate the CLI changes added in the last week without relying only on unit tests.

  

### C1. CLI Unit Surface

  

Run:

  

```text

python -m unittest tools.can_nt.tests.test_bridge_cli_visibility

python -m unittest tools.can_nt.tests.test_bridge_cli_robot_test_dsl_cli

python -m unittest tools.can_nt.tests.test_bridge_cli_facades

```

  

Expected:

  

- visibility output tests pass

- DSL CLI authoring tests pass

- facade tests pass with no help/grammar drift

  

### C2. Manual CLI Smoke For Diagnostics

  

Run:

  

```text

python tools/can_nt/can_nt_bridge.py --cli --no-can --no-nt

show tests

show topology

show topology json

show config dirty

help

```

  

Expected:

  

- canonical command forms work

- help text matches current command vocabulary

- topology show output renders from the current shared topology interpretation

- visibility/diagnostic output is readable and not duplicated

  

SID_COMMENT:

- Note any parser/help/spec mismatch here. If syntax drift is found, update the grammar and generated artifacts in the same fix.

  

## D) Topology Upgrade And Cross-Surface Checks

  

Purpose: validate the largest behavior change in the week: canonical topology graph ownership and unified rendering/composition paths.

  

### D1. Automated Cross-Surface Coverage

  

Run:

  

```text

python tools/can_nt/scripts/topology_editor_regression.py

python tools/can_nt/scripts/cross_surface_regression.py

python -m unittest tools.can_topology.tests.test_can_top_editor_profile_load

python -m unittest tools.can_topology.tests.test_live_topology_view

python -m unittest tools.can_topology.tests.test_validate_profiles_topology

```

  

Expected:

  

- topology editor fixture regression passes

- cross-surface round-trip passes

- profile-load, live-view, and validation tests all pass

  

### D2. Manual Editor Retest

  

Run the focused checklist in [docs/TOPOLOGY_EDITOR_MANUAL_RETEST_CHECKLIST.md](/c:/Users/dmona/swerveBringupMotorTest1-main/docs/TOPOLOGY_EDITOR_MANUAL_RETEST_CHECKLIST.md:1).

  

Minimum required items for this pass:

  

- load/save/quit/reload `robot_2026_swerve`

- fit-to-window, zoom, pan, and blank-space deselection stability

- bus resize behavior with CANnect direct and inject nodes

- connection filter behavior, including `None`

- component edit retention after save/reload

- invalid-device validation messaging includes exact labels

- callout retention

  

### D3. Shared Rendering And Export Checks

  

Purpose: verify the rendering unification and PDF/export alignment changes.

  

Run:

  

- open the topology editor on `robot_2026_swerve`

- compare on-screen scene composition to:

  - CLI topology views where applicable

  - generated export/PDF output if `reportlab` is available

  

Expected:

  

- device placement and connection interpretation match the shared scene model

- exported output does not use an older independent composition path

  

SID_COMMENT:

- Attach screenshots or export paths if any editor-versus-export mismatch appears.

  

## E) Robot-Local Command Modularization Checks

  

Purpose: verify the Java registry/executor refactor preserved command behavior and the generated Python UI metadata stayed aligned.

  

### E1. Java Unit Surface

  

Run:

  

```text

.\gradlew.bat test --tests frc.robot.RobotLocalCommandRegistryTest

.\gradlew.bat test --tests frc.robot.DslBringupTestTest

.\gradlew.bat test --tests frc.robot.BridgeUiCommandExecutorTest

.\gradlew.bat test --tests frc.robot.BridgeUiRuntimeCommandsTest

.\gradlew.bat test --tests frc.robot.BridgeUiSessionCommandsTest

```

  

Expected:

  

- registry tests pass

- DSL runtime tests pass

- bridge command execution/session tests pass

  

### E2. Generated Artifact Alignment

  

Run:

  

```text

python tools/can_nt/scripts/generate_robot_local_command_artifacts.py

```

  

Expected:

  

- the generator runs successfully

- no unexpected diff appears in `tools/can_nt/generated/robot_local_commands_generated.py` unless the registry changed intentionally

- generated Python metadata still matches the active Java registry

  

### E3. Manual Host UI Surface Check

  

Run:

  

- start the Python bringup UI

- inspect the action/button surface built from generated metadata

- verify per-command visibility preferences still load and save

  

Expected:

  

- no hardcoded legacy-only button sections appear where generated metadata should drive the UI

- command labels, sections, descriptions, and default args match the Java-owned inventory

  

SID_COMMENT:

- Record any missing command, duplicated command, wrong section, or wrong default arg.

  

## F) DSL Signal Provider And Device-Signal Checks

  

Purpose: verify the provider-based DSL signal registry and device-owned signal hooks preserved authoring and runtime behavior.

  

### F1. Python DSL And CLI Tests

  

Run:

  

```text

python -m unittest tools.can_nt.tests.test_robot_test_dsl

python -m unittest tools.common.tests.test_device_catalog

python -m unittest tools.common.tests.test_schema_store_profiles

```

  

Expected:

  

- DSL parser/validator tests pass

- device catalog tests pass

- schema-store profile tests pass with current profile-owned controller semantics

  

### F2. Java DSL Runtime Tests

  

Run:

  

```text

.\gradlew.bat test --tests frc.robot.DslBringupTestTest

```

  

Expected:

  

- signal-driven set behavior still works

- deadband behavior still works

- unsupported clear targets fail explicitly

- non-motor device requirements validate correctly

  

### F3. Manual CLI Authoring Smoke

  

Run:

  

```text

python tools/can_nt/can_nt_bridge.py --cli --no-can --no-nt

configure terminal

test set default

test create MySignalTest

type joystick

device add "SPARKMAX/NEO 25"

inputSource controller0.leftY

deadband 0.12

show

end

```

  

Expected:

  

- no parse errors

- test mode prompt transitions correctly

- `show` reflects joystick type, controller signal source, device membership, and deadband

  

SID_COMMENT:

- If controller naming now depends on `xboxController` devices in the profile, note whether the compatibility fallback was needed.

  

## G) Connected Non-Motion Robot Pass

  

Purpose: verify the robot/host boundary after the refactors without commanding motion-dependent workflows.

  

Run:

  

```text

python tools/can_nt/scripts/bridge_cli_robot_non_motion_regression.py --rio 172.22.11.2

```

  

Expected:

  

- handshake succeeds

- session/keepalive behavior is stable

- status and command routing work without motion

- stop-latch and disconnect handling remain safe

  

If time permits, also run:

  

```text

python tools/can_nt/scripts/run_regressions.py --suite robot-non-motion --rio 172.22.11.2

```

  

SID_COMMENT:

- Archive robot IP, robot image/build under test, and any handshake or lock-conflict anomalies.

  

## H) Optional Live Bringup Checks

  

Purpose: add a hardware pass when the task being validated touched controller bindings, tests, or runtime diagnostics.

  

Check:

  

- profile select versus activate behavior

- `addAll` on the selected profile

- `printState`, `printTestsOverview`, and profile-device reports

- hold-to-run and run-all behavior for enabled tests

- disable/enable safety behavior

- TCP stop latch and clear behavior

  

Expected:

  

- behavior matches pre-refactor operator semantics

- controller path and host-UI path reach the same underlying command behavior

  

## Exit Criteria

  

This pass is complete when:

  

- all required automated suites in sections A, C, D, E, and F pass

- no stale `data/` config references remain in active workflows

- topology editor round-trip and cross-surface checks pass

- generated robot-local command artifacts match the Java registry

- connected non-motion robot regression passes, or its hardware dependency is explicitly called out

- any failures are written up with exact command, observed output, and owning subsystem

  

## Results

  

TESTING_RESULTS:

- Date:

- Tester:

- Branch / commit:

- Local regression summary:

- Targeted manual summary:

- Connected robot summary:

- Open failures: