# Spec: Phase 2 Java UI Command Refactor

## Purpose

Define the required Phase 2 refactor work for the Java robot-side UI command path so Codex can implement it from the current Phase 1.5 state to Phase 2 completion.

This spec focuses on structural decomposition of the Java command path. The goal is to preserve existing behavior while moving command-family business logic out of `BridgeUiCommandHandler` and into dedicated domain executors.

## Scope

In scope:
- Java robot-side UI command path
- `BridgeUiCommandHandler`
- `BridgeUiCommandExecutor`
- `BridgeUiIngressPolicy`
- `BridgeUiCommandResult`
- `BridgeUiOutputFacade`
- new dispatcher and domain command-family classes
- new Java tests for ingress, executor, and extracted families

Out of scope:
- TCP protocol redesign
- NT contract redesign
- Python CLI/UI refactors
- changes to externally visible command semantics unless required for correctness
- unrelated robot bringup/test/report behavior changes

## Current State

The project already has these boundaries in place:
- `BridgeUiIngressPolicy`
- `BridgeUiCommandExecutor`
- `BridgeUiCommandResult`
- `BridgeUiOutputFacade`
- `BridgeUiCommandHandler`

The current architecture is materially improved from the prior monolithic state, but still incomplete because:
- `BridgeUiCommandHandler` still owns the large command switch / command-family logic
- command execution is not yet split by domain
- Java-side tests for ingress/executor/family boundaries are still limited

## Problem Statement

The current Java command path still concentrates too much command-specific business logic inside `BridgeUiCommandHandler`.

That causes these risks:
- handler remains too large and hard to reason about
- command families are not clearly owned by domain
- future command additions will continue growing one file
- testability is weaker than necessary
- command-family drift risk remains higher than desired

## Phase 2 Objective

Move from the current shared pipeline:
- ingress policy
- executor
- shared result model
- output facade
- one large handler-owned command switch

to a domain-dispatched execution architecture where:
- `BridgeUiCommandHandler` is mostly orchestration and wiring
- `BridgeUiCommandExecutor` owns the common execution pipeline
- a dispatcher routes commands to domain family executors
- domain family executors own command-specific business logic
- tests cover ingress, executor, and at least the first extracted families

## Required End State

At the end of Phase 2:

### `BridgeUiCommandHandler` must mainly do:
- receive NT commands
- receive TCP commands
- queue/drain TCP commands on the robot loop
- wire dependencies into policy, dispatcher, and executor
- publish ACK/OUT/TCP monitor via `BridgeUiOutputFacade`

### `BridgeUiCommandHandler` must not remain the primary owner of:
- the large command-family switch
- large command-specific result-building branches
- session/protocol command business logic
- profile command business logic
- test command business logic
- report command business logic

### `BridgeUiCommandExecutor` must:
- parse ingress through `BridgeUiIngressPolicy`
- validate ingress
- apply pre-execution side effects
- delegate to a dispatcher/family executor
- return a `BridgeUiCommandResult`

### Domain command-family executors must own:
- UI/session protocol commands
- profile/config commands
- test commands
- group/selection commands
- report/diagnostic commands
- optional small runtime/system commands if needed

## Architectural Rules

### 1. Preserve the current shared pipeline
The following remain valid and must stay in place:
- `BridgeUiIngressPolicy` owns ingress parsing, validation, and pre-execution policy
- `BridgeUiCommandExecutor` owns the shared execution pipeline
- `BridgeUiCommandResult` remains the shared result model
- `BridgeUiOutputFacade` remains the single owner of output publication

### 2. Do not pass the full handler into family executors
Bad:
```java
new BridgeUiProfileCommands(this)
```

Good:
```java
new BridgeUiProfileCommands(new BridgeUiProfileCommands.Dependencies() { ... })
```

### 3. Do not recreate the monolith in a new file
Avoid:
- one giant dispatcher switch replacing the old giant handler switch
- one giant `RuntimeCommands` dumping ground
- one generic abstraction layer that hides real domain ownership

### 4. Preserve behavior
This refactor is structural. It must preserve:
- command names
- current ACK/OUT behavior
- current NT/TCP shared execution path
- handshake/lock semantics
- stop-latch semantics
- disabled/E-stop gating
- current JSON payload shapes where already established
- current status/message behavior unless a bug requires correction

## Required New Abstractions

## A. Dispatcher layer

### New file
- `src/main/java/frc/robot/BridgeUiCommandDispatcher.java`

### Responsibility
Route validated commands to domain family executors.

### Acceptable patterns
Either of these is acceptable:

#### Pattern 1: family interface with `supports()`
```java
interface BridgeUiCommandFamily {
  boolean supports(String commandName);

  BridgeUiCommandResult execute(
      BridgeUiIngressPolicy.Ingress ingress,
      double cmdTs,
      boolean isTcp);
}
```

#### Pattern 2: dispatcher owns explicit routing
```java
final class BridgeUiCommandDispatcher {
  BridgeUiCommandResult dispatch(
      BridgeUiIngressPolicy.Ingress ingress,
      double cmdTs,
      boolean isTcp);
}
```

### Preferred direction
Prefer a design that supports clean future family additions without another giant switch file.

## B. Optional request wrapper

### Optional new file
- `src/main/java/frc/robot/BridgeUiCommandRequest.java`

### Purpose
Wrap execution inputs if this simplifies signatures.

### Example
```java
final class BridgeUiCommandRequest {
  final BridgeUiIngressPolicy.Ingress ingress;
  final double cmdTs;
  final boolean isTcp;
}
```

This is optional, not required.

## Required Domain Families

## 1. `BridgeUiSessionCommands`

### New file
- `src/main/java/frc/robot/BridgeUiSessionCommands.java`

### This should be the first extraction.

### It should own commands like:
- `uiPing`
- `uiHandshake`
- `uiDisconnect`
- monitor enable/disable commands if those are command-driven
- other pure session/protocol commands

### Responsibilities
- UI session establishment
- lock ownership changes
- session reset behavior
- handshake response JSON creation
- disconnect behavior specific to command semantics

### It must not own
- raw ingress validation
- output publication
- TCP queue orchestration

## 2. `BridgeUiProfileCommands`

### New file
- `src/main/java/frc/robot/BridgeUiProfileCommands.java`

### It should own commands like:
- `profileActivate`
- `profilesReload`
- `profilesApply`
- other runtime profile/config apply or activation commands

### Responsibilities
- activate runtime profile
- reload profile/config data
- apply pushed profile/config payloads
- build profile-related `BridgeUiCommandResult` payloads and messages

## 3. `BridgeUiTestCommands`

### New file
- `src/main/java/frc/robot/BridgeUiTestCommands.java`

### It should own commands like:
- select test
- toggle test
- run test
- run all tests
- tests overview/info execution

### Responsibilities
- test selection changes
- test enabled/disabled changes
- run / run-all behavior
- tests-related command results and JSON payloads

## 4. `BridgeUiGroupCommands`

### New file
- `src/main/java/frc/robot/BridgeUiGroupCommands.java`

### It should own commands like:
- `activeAdd`
- `activeNext`
- selected-device commands
- group-targeting related runtime actions
- active-group / selected-device command behavior

### Responsibilities
- active-group cursor logic
- selected device resolution
- group command result text
- group-targeting behavior within already-validated execution context

## 5. `BridgeUiReportCommands`

### New file
- `src/main/java/frc/robot/BridgeUiReportCommands.java`

### It should own commands like:
- state/status reports
- summary/health/bindings/sources report commands
- diagnostics-style report command execution
- report commands whose main effect is building text/JSON output

### Responsibilities
- invoke report-producing robot logic
- build report command `BridgeUiCommandResult`
- keep report commands separate from state-mutation commands

## 6. Optional `BridgeUiRuntimeCommands`

### Optional file
- `src/main/java/frc/robot/BridgeUiRuntimeCommands.java`

Only add this if there are truly leftover commands that do not fit elsewhere.

If added:
- keep it intentionally small
- do not let it become a dumping ground

## Narrow Dependency Interfaces

Each family must expose a narrow dependency interface containing only what it needs.

### Example: session commands
```java
interface Dependencies {
  String getActiveUiClientId();
  void setActiveUiClientId(String clientId);
  String getUiSessionId();
  void resetUiSession();
  ZoneId resolveRemoteCommandZone(JsonObject args);
  void setRemoteCommandZone(ZoneId zone);
  boolean isUiProtocolMonitorEnabled();
  void setUiProtocolMonitorEnabled(boolean enabled);
  NetworkTable getUiTcpTable();
  long getLastUiAckSeq();
}
```

### Example: profile commands
```java
interface Dependencies {
  boolean activateProfile(String name);
  boolean reloadProfiles();
  BridgeUiCommandResult applyProfiles(JsonObject args, boolean isTcp);
  String getActiveProfileName();
}
```

### Example: test commands
```java
interface Dependencies {
  BringupTestRegistry getTestRegistry();
  BringupCore getCore();
  BridgeUiCommandResult runSelectedTest();
  BridgeUiCommandResult runAllTests();
}
```

The actual methods may differ, but the design rule is mandatory:
- narrow dependency interface per family
- no full handler injection

## Executor Refactor Requirements

Modify `BridgeUiCommandExecutor` so that after:
- parse ingress
- validate ingress
- apply pre-execution

…it delegates to the dispatcher instead of directly depending on handler-owned switch logic.

### Target shape
```java
BridgeUiCommandResult executeRaw(...) {
  Ingress ingress = ingressPolicy.parseIngress(...);
  ValidationFailure failure = ingressPolicy.validateIngress(...);
  if (failure != null) { ... }
  ingressPolicy.applyPreExecution(...);
  return dispatcher.dispatch(ingress, cmdTs, isTcp);
}
```

If a callback/delegate is retained temporarily, it must be thin and must not simply recreate the old monolith.

## Handler Refactor Requirements

By the end of Phase 2, `BridgeUiCommandHandler` should mainly own:
- runtime state fields
- dependency wiring
- TCP queueing / response coordination
- invocation of executor
- output facade calls
- small helper adapters for dependency interfaces if needed

It should not contain the primary command-family switch anymore.

## Testing Requirements

Phase 2 is not complete without focused Java-side tests.

### Required new tests

## A. `BridgeUiIngressPolicyTest`
Add tests covering:
- missing command name
- missing clientId
- handshake required before normal command
- lock conflict with different clientId
- TCP start command blocked by stop latch
- disabled robot blocked for non-allowlisted command
- disabled robot allowed for allowlisted command
- pre-execution stop command triggers stop latch / safety stop

## B. `BridgeUiCommandExecutorTest`
Add tests covering:
- validation failure returns error result
- successful validated ingress dispatches to dispatcher/family
- pre-execution policy happens before dispatch
- dispatcher result is returned unchanged on success path

## C. `BridgeUiSessionCommandsTest`
Add tests covering at minimum:
- `uiHandshake` claims lock when not already locked
- `uiDisconnect` releases lock when same client owns it
- `uiDisconnect` fails when wrong client tries to release
- `uiPing` returns expected success result
- session reset behavior if supported by handshake args

## D. At least one additional family test
Prefer one of:
- `BridgeUiProfileCommandsTest`
- `BridgeUiTestCommandsTest`

Choose whichever family is extracted second.

## Extraction Order

Implement in this order unless a strong code constraint requires another sequence.

## Phase 2A
1. Add dispatcher abstraction
2. Extract `BridgeUiSessionCommands`
3. Add tests for:
   - ingress policy
   - executor
   - session commands

## Phase 2B
4. Extract `BridgeUiProfileCommands`
5. Extract `BridgeUiTestCommands`
6. Add tests for at least one of those families

## Phase 2C
7. Extract `BridgeUiGroupCommands`
8. Extract `BridgeUiReportCommands`
9. Add small `BridgeUiRuntimeCommands` only if still needed
10. Remove handler leftovers and dead code

## Cleanup Requirements

At the end of the refactor:
- remove dead handler methods that existed only for the old switch path
- remove old constants no longer owned by handler
- move family-specific constants/messages into the owning family where appropriate
- keep shared result model and shared output facade
- keep ingress policy as the only owner of ingress gating/pre-exec policy
- avoid duplicating validation rules inside families

## Code Quality Requirements

### Design requirements
- top-level classes, not giant nested classes
- narrow dependency interfaces per family
- no full-handler injection into family executors
- no new mega-dispatcher monolith
- avoid moving the old switch wholesale into one new giant file

### Readability requirements
- each family file should have a clear purpose comment/docstring
- each family should group related commands cohesively
- helper methods should remain local to their family where possible

## Deliverables

### New production classes
Required:
- `BridgeUiCommandDispatcher.java`
- `BridgeUiSessionCommands.java`
- `BridgeUiProfileCommands.java`
- `BridgeUiTestCommands.java`
- `BridgeUiGroupCommands.java`
- `BridgeUiReportCommands.java`

Optional:
- `BridgeUiRuntimeCommands.java`
- `BridgeUiCommandRequest.java`

### Refactored production classes
- `BridgeUiCommandHandler.java`
- `BridgeUiCommandExecutor.java`

### New tests
- `BridgeUiIngressPolicyTest.java`
- `BridgeUiCommandExecutorTest.java`
- `BridgeUiSessionCommandsTest.java`
- at least one additional family test

## Success Criteria

Phase 2 is complete only when all of these are true:
- `BridgeUiCommandHandler` no longer owns the large command-family switch
- command execution is split into domain family classes
- `BridgeUiCommandExecutor` delegates through dispatcher/family boundaries
- NT and TCP still use the same shared execution path
- `BridgeUiIngressPolicy` remains the single ingress/policy boundary
- `BridgeUiOutputFacade` remains the single output/publication boundary
- Java tests exist for ingress policy and executor behavior
- Java tests exist for at least the extracted session family
- at least one more extracted family has direct tests
- dead code and old switch leftovers are removed
- compile and tests pass with the supported toolchain

## Constraints

- Do not change externally visible behavior unless necessary for correctness.
- Do not merge unrelated protocol redesigns into this work.
- Do not introduce generic abstractions that hide real domain responsibilities.
- Prefer explicit domain ownership over clever indirection.
- Keep any runtime/system leftovers intentionally small.

## Implementation Note For Codex

Please implement Phase 2 completely, not partially:
- add dispatcher
- remove command-family switch ownership from handler
- extract domain-family executors
- add tests
- clean dead code
- keep behavior stable
- ensure compile/tests pass

If incremental delivery is needed, use this sequence:
1. dispatcher
2. session commands
3. ingress/executor/session tests
4. profile + test commands
5. group + report commands
6. final cleanup and test pass
