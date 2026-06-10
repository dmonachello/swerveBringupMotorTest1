# Audit: Shared Contract Drift - 2026-06-10

## Purpose

Inventory the current repo areas where the stated "shared/common code owns the contract" rule is drifting in practice.

This report focuses on artifacts and flows that are exposed through multiple surfaces:

- CLI
- Bringup Control UI
- topology editor
- robot runtime / Java command server
- config download / export / save paths

This is not a full architecture review of every module. It is a targeted drift audit for multi-surface contract ownership.

## Scope

Included:

- `bringup_system.json` and `bridgeConfig`
- DSL test selection, storage, and enable-state semantics
- selected-test state and selected-test actions
- runtime-state JSON and host-side consumers
- topology/config validation and topology projections

Not included:

- passive CAN reverse-engineering outputs in depth
- every single command parser alias
- Java-only internal runtime code that has no cross-surface contract

## Method

The audit used:

- architecture and layering docs
- direct code search for builders, serializers, normalizers, and validators
- recent bug-fix traces around selected-test drift, DSL enabled-state drift, and `bridgeConfig.generatedAt`

Primary principle used for evaluation:

- If two or more surfaces build, serialize, or interpret the same artifact/contract independently, drift risk exists unless one shared/common path is clearly authoritative.

## Executive Summary

The concern is valid. Drift does not stop with `bridgeConfig`.

The repo shows a repeated pattern:

- one artifact is shared across surfaces
- multiple surfaces still contain local construction or persistence logic
- common/shared ownership exists partially, but not completely
- drift becomes visible only during manual round-trip or cross-surface tests

The highest-risk drift areas are:

1. unified config and `bridgeConfig` write preparation
2. DSL test storage and per-profile test-set semantics across Python and Java
3. selected-test state across UI local state, robot state, and test action commands
4. topology/config validation and topology projection logic across editor, CLI, and schema/store layers

There are also positive examples where shared ownership has started to work:

- device-definition required-field validation was recently centralized into shared Python common code and reused by CLI/editor/validator

That pattern should be expanded.

## Findings

## Finding 1: Unified Config And `bridgeConfig` Writing Still Has Multiple Authorities

### Risk

High

### Why

The same config artifact is written or prepared in multiple host-side surfaces with local logic:

- CLI unified config save
- CLI bridge-config-only save
- CLI profile export
- topology editor save/write path
- runtime bridge-config export path
- robot-side current-config persistence/apply path

This is the exact class of drift that surfaced in the `generatedAt` issue.

### Evidence

- CLI has local bridge-config ordering/stamping logic in [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py:17460)
- CLI writes unified config through multiple save/build paths:
  - [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py:15688)
  - [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py:17572)
  - [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py:17650)
- topology editor writes `bringup_system.json` with its own root-extras/bridgeConfig handling in [tools/can_topology/can_top_editor.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/can_top_editor.py:2114)
- runtime bridge-config export has a separate builder in [tools/can_nt/bridge_ops.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_ops.py:2113)
- robot-side config apply/persist has its own authority in:
  - [src/main/java/frc/robot/BringupUtil.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupUtil.java:1887)
  - [src/main/java/frc/robot/BringupUtil.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupUtil.java:2462)

### Drift Symptoms Already Observed

- `bridgeConfig.generatedAt` was `null` in some host-written files and stamped in other flows
- downloaded current config and local config differed in shape and optional fields
- `enabled` for DSL tests appeared on robot-persisted config before host-local baseline had the same shape

### Desired Authority

One shared Python common-code write-prep path for host-side unified config and `bridgeConfig` serialization.

Robot-side apply/persist can remain separate, but it should consume the same artifact contract and normalization rules as the host-side serializer.

### Recommended Consolidation

Create one shared module under `tools/common/` for:

- `bridgeConfig` normalization
- `bridgeConfig` metadata stamping
- unified-config write preparation
- optional-field policy
- key ordering policy

Then route:

- `bridge_cli`
- `can_top_editor`
- host-side export helpers

through that one shared serializer/preparer.

## Finding 2: DSL Test Storage And Per-Profile Test-Set Semantics Are Split Across Python And Java

### Risk

High

### Why

Per-profile DSL test resolution and storage semantics exist in both shared Python host code and separate Java robot-side loaders.

That is expected at some level because host and robot are in different languages, but the semantic ownership is not clearly centralized enough. Behavior changed recently around enabled state because the Python and Java representations had drifted.

### Evidence

Python shared test-set resolution:

- [tools/common/robot_test_dsl/service.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/common/robot_test_dsl/service.py:225)
- [tools/common/config_lifecycle/query_service.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/common/config_lifecycle/query_service.py:72)

UI/CLI consumers:

- [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:930)
- [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:1008)
- [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py:6843)

Robot-side test loading and set selection:

- [src/main/java/frc/robot/tests/BringupTestRegistry.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/BringupTestRegistry.java:40)
- [src/main/java/frc/robot/tests/BringupTestRegistry.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/BringupTestRegistry.java:155)
- [src/main/java/frc/robot/BringupUtil.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupUtil.java:542)

Recent enabled-state addition required changes in Java-only DSL models and persistence:

- [src/main/java/frc/robot/tests/dsl/DslModels.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/dsl/DslModels.java:26)
- [src/main/java/frc/robot/tests/dsl/DslBringupTest.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/dsl/DslBringupTest.java:77)
- [src/main/java/frc/robot/tests/BringupTestRegistry.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/tests/BringupTestRegistry.java:78)

### Drift Symptoms Already Observed

- `toggleTest` previously ACKed success but did nothing for DSL tests
- host-side tests and robot-side persisted config diverged in `enabled` shape
- selected-test actions were working against stale robot-side selected test state

### Desired Authority

The DSL storage schema and per-profile test-set semantics need an explicit shared contract doc plus generated or shared fixtures that both Python and Java tests must validate against.

### Recommended Consolidation

- Treat Python `tools/common/robot_test_dsl/` as the semantic source for host-side authoring and validation
- Add contract fixtures for robot-side loading behavior
- Add a robot/host cross-surface regression that round-trips:
  - selected test set
  - enabled flags
  - stored source
  - test names

## Finding 3: Selected-Test State Is Still A Multi-Layer Coordination Problem

### Risk

High

### Why

The "selected test" concept spans:

- local UI dropdown state
- robot-side selected test index/name
- robot-side tests table NT state
- report commands such as `printSelectedTestSource`
- action commands such as `runTest` and `toggleTest`

This is one logical state, but it is split across multiple mechanisms.

### Evidence

UI local selection / sync logic:

- [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:4935)
- [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:4997)
- [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:6780)

Robot-side selected-test state:

- [src/main/java/frc/robot/BringupCore.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupCore.java:1098)
- [src/main/java/frc/robot/BringupCore.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupCore.java:1153)
- [src/main/java/frc/robot/BringupCore.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BringupCore.java:1858)

Robot-side command plumbing:

- [src/main/java/frc/robot/BridgeUiTestCommands.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiTestCommands.java:120)
- [src/main/java/frc/robot/BridgeUiCommandHandler.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java:4155)

### Drift Symptoms Already Observed

- UI dropdown showed a selected test not in the current profile
- `printSelectedTestSource` printed the stale robot-side selection instead of the visible profile-scoped UI selection
- disabled selected tests had to be handled carefully to avoid selected-name disappearing

### Desired Authority

One explicit selected-test synchronization contract:

- source of truth
- when local UI may show staged selection
- when robot selection must be synchronized before action
- how disabled selected tests are represented

### Recommended Consolidation

- document selected-test lifecycle as a contract
- centralize host-side sync workflow into a dedicated shared service instead of keeping it embedded in UI event code
- add one end-to-end test bundle for:
  - profile switch
  - selected-test switch
  - print source
  - toggle enabled
  - run selected

## Finding 4: Runtime-State JSON Has One Main Builder, But Multiple Host-Side Interpreters

### Risk

Medium

### Why

This area is healthier than `bridgeConfig`, because the robot-side JSON builder is relatively centralized. The drift risk is now mostly in host-side interpretation and secondary projections.

### Evidence

Robot-side main builder:

- [src/main/java/frc/robot/BridgeUiCommandHandler.java](/c:/Users/dmona/swerveBringupMotorTest1-main/src/main/java/frc/robot/BridgeUiCommandHandler.java:3217)

Host-side consumers and projections:

- UI applies payload in [tools/can_nt/bringup_ui.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bringup_ui.py:6282)
- CLI fetches and indexes payload in [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py:11719)
- runtime query wrapper in [tools/can_nt/runtime_query_service.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/runtime_query_service.py:83)
- specialized normalizers:
  - [tools/can_nt/motor_diag_normalize.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/motor_diag_normalize.py:1)
  - [tools/can_nt/power_diag_normalize.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/power_diag_normalize.py:1)

### Drift Symptoms Already Observed

- manual testing often requires checking whether output differences are contract differences or just host-side interpretation differences
- the UI and CLI each contain nontrivial runtime-state shaping logic

### Desired Authority

The robot-side runtime-state JSON builder should remain the authoritative producer.

Host-side interpretation should be pushed behind shared query/normalization services so UI and CLI consume the same normalized runtime-state model.

### Recommended Consolidation

- strengthen `runtime_query_service.py`
- add shared runtime-state normalization objects under `tools/common/` or a clearer host query layer
- reduce UI-embedded and CLI-embedded payload interpretation logic

## Finding 5: Topology Validation And Projection Logic Is Spread Across Editor, CLI, And Store Layers

### Risk

High

### Why

Topology data is shared across:

- topology editor authoring
- CLI `show topology`
- standalone topology validation
- config/schema store validation and sanitization
- cross-surface regression consumers

The repo already has cross-surface tests here because drift risk is known and real.

### Evidence

Topology editor write path:

- [tools/can_topology/can_top_editor.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/can_top_editor.py:2114)

Standalone topology validation:

- [tools/can_topology/validate_profiles.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/validate_profiles.py:186)
- [tools/can_topology/validate_profiles.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/validate_profiles.py:395)

Schema/store validation and sanitization:

- [tools/config/schema_store.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/config/schema_store.py:1555)
- [tools/config/schema_store.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/config/schema_store.py:2148)

CLI topology projections and commands:

- [tools/can_nt/tests/test_bridge_cli_topology_show.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/tests/test_bridge_cli_topology_show.py:245)
- [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py:14928)

Cross-surface regression already exists because this area drifts:

- [tools/can_nt/tests/test_cross_surface_regression.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/tests/test_cross_surface_regression.py:55)

### Drift Symptoms Already Observed

- separate validation logic in editor/validator/store can diverge
- topology round-trips require dedicated cross-surface regression tests
- CLI topology rendering and editor save semantics have needed explicit compatibility work

### Desired Authority

One shared topology domain model and one shared validation/sanitization layer used by:

- editor
- CLI topology views
- standalone validators
- config store

### Recommended Consolidation

- continue moving topology parsing/rendering/validation into `tools/common/topology_*`
- reduce direct topology interpretation inside CLI/editor
- make standalone validator and schema-store validator consume the same validation core where feasible

## Finding 6: There Are Positive Examples Where Shared Ownership Is Improving

### Risk

Low

### Why It Matters

The repo is not uniformly drifting. Some recent work shows the right direction and should be used as the template for broader consolidation.

### Evidence

Device-definition required-field validation now uses shared common Python rules:

- shared helper: [tools/common/device_definition_rules.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/common/device_definition_rules.py:1)
- CLI consumer: [tools/can_nt/bridge_cli.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_nt/bridge_cli.py:15541)
- topology editor consumer: [tools/can_topology/can_top_editor.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/can_top_editor.py:3364)
- validator consumer: [tools/can_topology/validate_profiles.py](/c:/Users/dmona/swerveBringupMotorTest1-main/tools/can_topology/validate_profiles.py:310)

This is exactly the pattern the repo wants:

- one shared rule set
- multiple surfaces consume it
- tests validate the shared rule set once

## Risk Ranking

### Highest Priority

1. unified config / `bridgeConfig` serializer ownership
2. DSL test storage and per-profile test-set contract ownership
3. selected-test synchronization contract

### Next Priority

4. topology validation/projection ownership
5. runtime-state host-side normalization

### Lower Priority

6. presentation-only formatting differences where one authoritative data model already exists

## Recommended Plan

## Phase 1: Stop The Current Drift

- create one shared host-side serializer/preparer for unified config and `bridgeConfig`
- route CLI save/export and topology-editor save through it
- add explicit round-trip regression checks for:
  - save unified config
  - save bridge config
  - push config
  - download current config

## Phase 2: Make DSL Test Contract Explicit

- write one contract note for:
  - `dslTests.testsByName`
  - `testSets`
  - `dslTestSet`
  - `enabled`
- add cross-language regression fixtures for host and robot consumers

## Phase 3: Extract Selected-Test Sync Service

- create one host-side shared selected-test sync service
- remove action-specific sync logic from UI event handlers where practical
- test profile switch + test source + toggle + run flows together

## Phase 4: Consolidate Topology Validation Core

- identify overlap between:
  - `tools/can_topology/validate_profiles.py`
  - `tools/config/schema_store.py`
  - CLI topology projection logic
- extract one shared validation core and keep shell/wrapper layers thin

## Open Questions

- Should the shared serializer own both host-local save semantics and robot-download normalization expectations, or should robot-side download be allowed a separate stable normalization policy?
- Should Java-side DSL model/schema fixtures be generated from the Python-side contract, or only regression-tested against shared fixture files?
- Should `bridgeConfig` remain a separate host-local concern inside unified config, or be promoted to a more formal shared config domain model under `tools/common/`?

## Conclusion

The current issue set is not a random cluster of bugs. It is evidence of incomplete consolidation around multi-surface contract ownership.

The repo already states the right rule:

- shared behavior exposed through multiple surfaces should be owned by common code

The audit result is:

- that rule is only partially true in the current implementation
- the biggest drift is around shared artifact writing and multi-surface state semantics
- the repo should treat this as an architectural cleanup track, not only as isolated bug fixes

