# Spec: Phase 2 Hardening Pass

## Purpose

Define the required hardening work after the Java UI command-path Phase 2 baseline refactor.

Phase 2 established the new architecture:
- ingress policy
- shared executor pipeline
- shared result model
- output facade
- dispatcher
- domain command families

This hardening pass finishes the work needed to make that architecture more robust, better tested, and less dependent on residual helper leakage in `BridgeUiCommandHandler`.

## Scope

In scope:
- Java robot-side UI command path
- test expansion for ingress, executor, and command families
- narrowing dependency adapters and reducing handler helper leakage
- moving family-specific constants/helpers out of `BridgeUiCommandHandler` where practical
- preserving current external behavior while improving confidence and maintainability

Out of scope:
- protocol redesign
- NT contract redesign
- unrelated robot behavior changes
- Python refactors
- broad product/workflow changes outside the Java UI command path

## Current State Summary

The project now has:
- `BridgeUiIngressPolicy`
- `BridgeUiCommandExecutor`
- `BridgeUiCommandDispatcher`
- `BridgeUiCommandResult`
- `BridgeUiOutputFacade`
- `BridgeUiSessionCommands`
- `BridgeUiProfileCommands`
- `BridgeUiTestCommands`
- `BridgeUiGroupCommands`
- `BridgeUiReportCommands`
- `BridgeUiRuntimeCommands`

Baseline tests exist for:
- ingress policy
- executor
- session commands
- profile commands

This is a good Phase 2 baseline.

However, the baseline still shows these gaps:
- `BridgeUiCommandHandler` remains large and still owns many family-specific helpers/constants
- ingress/executor tests are incomplete relative to the intended boundary behavior
- family-level tests do not yet cover Group/Report/Runtime families
- some dependency adapters may still be broader or noisier than necessary

## Hardening Objectives

Complete the next-quality step after Phase 2 baseline by doing four things:

1. Expand boundary tests so the new architecture is meaningfully protected.
2. Add direct tests for the still-untested command families.
3. Reduce helper leakage and family-specific constant ownership in `BridgeUiCommandHandler`.
4. Keep behavior stable while improving internal modularity and confidence.

## Required Work

## 1. Expand Ingress Policy Test Coverage

### File
- `src/test/java/frc/robot/BridgeUiIngressPolicyTest.java`

### Current gap
Current tests only cover a small subset of ingress behavior.

### Required additions
Add tests for all of the following:
- missing command name
- missing clientId
- handshake required before normal command
- lock conflict with different clientId
- TCP start command blocked by stop latch
- disabled robot blocks non-allowlisted command
- disabled robot allows allowlisted command
- TCP stop command triggers pre-execution side effects:
  - `setStopLatch(...)`
  - `applySafetyStop(...)`

### Requirements
- tests should assert the exact or intended stable failure message where already part of behavior
- tests should use narrow fake dependency objects, not the real handler
- no dependence on unrelated robot runtime state

## 2. Expand Executor Test Coverage

### File
- `src/test/java/frc/robot/BridgeUiCommandExecutorTest.java`

### Current gap
Current executor tests validate only a failure path and one success dispatch path.

### Required additions
Add tests for:
- validation failure returns error result and does not dispatch
- validated ingress dispatches to dispatcher correctly
- pre-execution policy is applied before dispatch
- dispatcher result is returned unchanged on success path
- unknown command behavior is stable through the dispatcher/executor path

### Recommended approach
Use stub dispatcher and stub ingress policy dependencies where needed so sequencing can be asserted cleanly.

## 3. Add Direct Family Tests For Untested Families

### Required new test files
Add:
- `src/test/java/frc/robot/BridgeUiGroupCommandsTest.java`
- `src/test/java/frc/robot/BridgeUiReportCommandsTest.java`
- `src/test/java/frc/robot/BridgeUiRuntimeCommandsTest.java`

### A. `BridgeUiGroupCommandsTest`
Add tests covering at minimum:
- `showGroup` requires `args.name`
- `showGroup` returns not-found error when group missing
- `groupCreate` creates a missing group
- `groupCreate` rejects duplicate group name
- `groupDelete` requires `confirm=true`
- `showDevice` requires `args.name`
- `showDevice` returns not-found error when device missing
- one show command verifies JSON/text output routing through `applyShowResult(...)`

### B. `BridgeUiReportCommandsTest`
Add tests covering at minimum:
- diagnostics unavailable blocks summary/NT/CAN dump paths appropriately
- `showStatus` routes through show-result application
- `showVersion` routes through show-result application
- `dumpReport` writes success path message correctly
- `dumpReport` failure-to-write path message correctly

### C. `BridgeUiRuntimeCommandsTest`
Add tests covering at minimum:
- `addMotor` rejects inactive profile when activation still fails
- `addMotor` or `addAll` activates profile when possible and succeeds
- `clearStopLatch` returns cleared/not-active message correctly
- fixed speed commands toggle/set expected speed and message behavior

### Requirements
- tests should use narrow fake dependency implementations
- tests should cover both happy path and at least one negative path per family
- tests should assert stable externally visible messages where those messages are part of user behavior

## 4. Tighten Dispatcher Testability

### Optional but recommended
Add:
- `src/test/java/frc/robot/BridgeUiCommandDispatcherTest.java`

### Suggested coverage
- first matching family handles command
- unknown command returns expected error result
- null/blank command behavior is sensible and stable

This is not strictly mandatory if equivalent behavior is fully covered through executor tests, but it is recommended.

## 5. Reduce Handler Helper Leakage

### File
- `src/main/java/frc/robot/BridgeUiCommandHandler.java`

### Current gap
The handler still contains significant family-specific helpers and constants, especially around:
- active-group behavior
- report building helpers
- runtime command support helpers
- family-specific text/constants

### Required review
Review each helper still in the handler and classify it as one of:
- orchestration-owned and should stay in handler
- family-specific and should move into a family or family dependency adapter
- shared utility and should move to a small helper class if reused by multiple families
- dead/obsolete and should be removed

### High-priority leakage targets
The following areas should be specifically reviewed:
- active-group helper methods and constants used only by `BridgeUiGroupCommands`
- report-related helper methods/constants used only by `BridgeUiReportCommands`
- runtime-only helper methods/constants used only by `BridgeUiRuntimeCommands`
- family-specific message strings still stored in handler

### Important constraint
Do not over-extract pure handler-owned robot state or queue orchestration. The goal is to move family-specific ownership, not to hollow out the handler artificially.

## 6. Narrow Dependency Adapters Where Possible

### Current gap
The handler currently wires many family dependencies inline, which is expected, but some adapters may still expose more than the family truly needs.

### Required review
For each family dependency interface:
- verify every method is actually used
- remove unused dependency methods
- reduce accidental exposure of handler internals
- rename overly generic dependency methods if clearer domain names help

### Focus areas
Prioritize review of:
- `BridgeUiGroupCommands.Dependencies`
- `BridgeUiReportCommands.Dependencies`
- `BridgeUiRuntimeCommands.Dependencies`

These are likely the broadest and most complex.

## 7. Move Family-Specific Constants Out Of Handler Where Reasonable

### Purpose
Improve ownership clarity and reduce the appearance that the handler still owns family behavior.

### Required action
Where a constant/message is used by only one family:
- move it into that family class
- or keep it inside a family-specific dependency adapter if that is the true owner

### Do not move
Do not move constants that are truly handler-owned, such as:
- queue timing constants
- TCP lease/timeout orchestration constants
- handler-local state bookkeeping constants
- output facade ownership constants already moved elsewhere

## 8. Keep Behavior Stable

This hardening pass is still primarily structural/test-oriented.

Must preserve:
- command names
- ACK/OUT behavior
- NT/TCP shared execution path
- ingress policy semantics
- current status/message behavior unless correcting a clear bug
- current protocol field behavior

## Success Criteria

The hardening pass is complete when all of these are true:
- ingress policy tests cover the intended boundary cases
- executor tests cover validation, dispatch, ordering, and unknown-command behavior
- direct tests exist for Group, Report, and Runtime command families
- family tests cover both success and failure behavior
- `BridgeUiCommandHandler` has measurably less family-specific helper leakage
- obviously family-specific constants/helpers have moved out of handler where practical
- broad dependency interfaces have been trimmed where possible
- compile and tests pass with supported toolchain

## Deliverables

### New tests
Required:
- `BridgeUiGroupCommandsTest.java`
- `BridgeUiReportCommandsTest.java`
- `BridgeUiRuntimeCommandsTest.java`

Recommended:
- `BridgeUiCommandDispatcherTest.java`

### Updated tests
- `BridgeUiIngressPolicyTest.java`
- `BridgeUiCommandExecutorTest.java`

### Refined production files
- `BridgeUiCommandHandler.java`
- possibly one or more family classes if helpers/constants move
- possibly dependency interfaces if narrowed

## Implementation Order

Use this order:
1. expand ingress policy tests
2. expand executor tests
3. add Group family tests
4. add Report family tests
5. add Runtime family tests
6. trim dependency interfaces
7. move family-specific constants/helpers out of handler where practical
8. final compile/test pass

## Constraints

- Do not redesign the command protocol.
- Do not change behavior just to simplify tests.
- Prefer narrow explicit fake dependencies in tests.
- Avoid introducing a new generic utility layer unless reuse is clearly justified.
- Keep the hardening pass focused on test depth and ownership cleanup.

## Implementation Note For Codex

Please treat this as a focused hardening pass, not a new redesign.

Priority order:
- first improve test depth around the new architecture
- then reduce obvious handler helper leakage
- then trim dependency interfaces

At the end, report:
- tests added/expanded
- helpers/constants moved out of handler
- dependency interfaces narrowed
- any remaining handler leakage or follow-up opportunities
