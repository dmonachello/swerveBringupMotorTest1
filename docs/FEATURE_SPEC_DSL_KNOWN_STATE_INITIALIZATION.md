SPEC_STATUS: PROPOSED

# DSL Known-State Initialization

## Purpose

Extend the Robot Diagnostic Test DSL so an initialization phase can safely span multiple robot loop ticks before the main phase begins. This supports tests that must move hardware to a known state, such as driving an arm to a limit switch or encoder position, without blocking the 20 ms robot loop.

All phase declarations use explicit `phase <name>:` syntax. The first implementation supports only the reserved phase names `init`, `main`, and `close`.

This document is a proposal only. It does not change the current DSL contract or [Current UI And Runtime Rules - V2.md](../Current%20UI%20And%20Runtime%20Rules%20-%20V2.md).

## Problem

The current runner executes `init` once during test startup, then immediately starts `main`. A test cannot currently command an actuator to a known position and wait for evidence that it arrived before the live test rules begin.

Blocking inside startup is not acceptable. A wait loop would consume the robot's 20 ms control budget and degrade control responsiveness.

## Goals

- Allow explicit multi-tick initialization without blocking.
- Reuse the existing DSL condition syntax and 20 ms evaluation model.
- Define `success` as successful completion of the current phase, not always the entire test.
- Preserve all existing one-pass `init` tests unchanged.
- Keep hardware safe when initialization completes, fails, or is interrupted.
- Expose the active phase and phase-completion reason in existing test status/detail surfaces.

## Non-Goals

- Do not add loops, branches, variables, callbacks, or arbitrary sequencing.
- Do not add a blocking `wait` operation.
- Do not change `close`; it remains one-pass cleanup.
- Do not create a separate robot scheduler outside the existing test update path.
- Do not alter active-group, selected-test, or runtime activation rules.

## Examples

### Arm To Limit

The arm moves during `init` until its limit switch is pressed. `main` starts only after that condition is true.

```text
test "arm_known_position_check"

device "arm motor"
device armLimit

phase init:
    set "arm motor".output_percent_cmd = -0.15
    abort timer.elapsed >= 5.0
    until armLimit.pressed

phase main:
    require armLimit.pressed
    success timer.elapsed >= 5.5
```

### One-Pass Setup Remains One Pass

This continues to behave exactly as it does today.

```text
phase init:
    clear "FALCON 9".faults

phase main:
    until timer.elapsed >= 2.0
```

## Phase Model

The test state machine becomes:

```text
START -> INIT -> MAIN -> CLOSE -> TERMINAL
```

`INIT` is entered only when a `phase init:` block exists. A phase may complete in one tick or over many ticks.

- A phase without `until` or `success` completes after its first evaluation tick.
- A phase with an unsatisfied `until` or `success` remains active and is revisited once per robot test update.
- The runner never sleeps, waits internally, or executes an unbounded loop in a single update.
- Statement order inside a phase does not define execution order.

## Statement Semantics

### `set`

`set` statements in an active multi-tick `init` phase are applied once per tick, just like `main` `set` statements. This is required to maintain a commanded arm or other actuator while its initialization condition is pending.

When `init` completes, any output written by `init` and not also written by `main` is returned to its DSL-defined safe value before `main` begins. This prevents an initialization-only command from continuing unintentionally.

### `clear`

`init` `clear` statements run once when entering `INIT`, not once per tick. Repeating a destructive clear could erase useful fault evidence or create unnecessary bus traffic.

### `abort`

`abort` is terminal for the whole test in every phase where it is allowed. It performs normal `close` processing and final safe-state application.

Example:

```text
abort "arm motor".current_actual > 30
```

### `success`

`success` means successful completion of the current phase.

- In `init`, it completes initialization and transitions to `main`.
- In `main`, it completes the test successfully.

`success` is immediate completion. It does not require phase `require` statements to have latched.

### `until`

`until` means normal completion of the current phase.

- In `init`, it transitions to `main` only if all `init` `require` statements have latched.
- In `main`, it completes the test only if all `main` `require` statements have latched.
- If the `until` condition becomes true before the phase requirements are satisfied, the test fails with `FAIL_REQUIRE_NOT_MET`.

This preserves the current purpose of `until`: stop normally only after required evidence has been proven.

### `require`

`require` is allowed in `init` and `main`. It latches successful proof for the active phase. `init` requirements are distinct from `main` requirements and do not carry into `main`.

SID_QUESTION: Confirm whether `require` should be allowed in `init` for the first implementation. The recommended answer is yes because it makes phase behavior symmetric and can prove that a known-state sensor was observed.

## Condition Priority

Each active `INIT` or `MAIN` tick uses this fixed order:

1. Apply the active phase's `set` statements.
2. Sample signals and evaluate conditions.
3. Update stable-condition filters and latch active-phase `require` statements.
4. Evaluate `abort` conditions.
5. Evaluate `success` conditions.
6. Evaluate `until` conditions.

The first terminal condition in that priority order wins. Source line order does not affect it.

## Time And Boundedness

`timer.elapsed` remains the run-wide timer and starts at test start. The first implementation does not add `phase.elapsed`.

An initialization phase that commands motion should include an `abort timer.elapsed >= <limit>` safety bound. Host validation should emit a warning when an `init` phase has a multi-tick terminator and writable output but no timer-based abort.

SID_QUESTION: Decide whether this should be a warning only or a validation error. Recommendation: warning initially, because the DSL already allows intentionally operator-ended tests.

## Grammar Changes

The proposed grammar makes phase declaration explicit:

```text
phase_body = [ init_phase ] main_phase [ close_phase ] ;

init_phase  = "phase" "init" ":" { init_stmt } ;
main_phase  = "phase" "main" ":" { main_stmt } ;
close_phase = "phase" "close" ":" { close_stmt } ;

init_stmt   = set_stmt
            | clear_stmt
            | abort_stmt
            | until_stmt
            | success_stmt
            | require_stmt ;

main_stmt   = set_stmt
            | abort_stmt
            | until_stmt
            | success_stmt
            | require_stmt ;
```

`close_stmt` remains:

```text
close_stmt = set_stmt | clear_stmt ;
```

Rules:

- `phase main:` is required.
- `phase init:` and `phase close:` are optional.
- A phase may appear at most once.
- The only accepted order is `init`, then `main`, then `close`.
- Bare `init:`, `main:`, and `close:` are invalid after implementation.
- User-defined phase names are reserved for a later feature and are invalid in the first implementation.

## Normalized Model

The normalized JSON phase structure already has `sets`, `clears`, `aborts`, `successes`, `untils`, and `requires`. No schema expansion is required for `init` conditions.

The robot runtime must add transient run state that is not persisted in the normalized test:

- active phase: `INIT`, `MAIN`, `CLOSE`, or terminal
- per-phase latched requirements
- active-phase start timestamp for diagnostics
- initialization completion reason
- initialization-owned output targets

## Runtime Safety Rules

- Device lifecycle admission still occurs before entering `INIT`.
- Baselines for delta signals are captured once at test start, before `INIT` starts.
- Final safe-state application runs after every terminal result, including init abort, init requirement failure, external interruption, and communication failure.
- `close` runs once after a terminal result using current cleanup semantics.
- If a signal-driven `init` set source is unavailable, the test fails rather than applying a fallback. This preserves current startup behavior.
- If an `init` phase completes, its initialization-only outputs are safely released before the first `MAIN` tick.

## Operator Visibility

The test status/details payload should identify:

- current phase (`Initializing`, `Running`, `Closing`, or terminal)
- active phase elapsed time
- phase-completion reason, such as `until armLimit.pressed`
- any latched init requirements and their sample values

The UI may show `INITIALIZING` as a detail within the existing test state area. It must not report the test as successfully runnable or passed merely because `init` is active.

## Migration

No source-syntax backward compatibility is required.

- All repository DSL tests, examples, generated help, user guides, and fixtures must be converted from bare phase declarations to `phase <name>:`.
- The compiler rejects bare `init:`, `main:`, and `close:` after implementation.
- Existing one-pass initialization behavior remains available through `phase init:` containing only `set` and `clear` statements.
- Existing normalized test data must be regenerated from migrated source before deployment.
- New DSL source using multi-tick init conditions is rejected by older robot builds and accepted only after this feature is deployed.

## Implementation Plan

1. Update host parser, normalized-model validation, help, EBNF, and DSL reference generation for explicit phase syntax and allowed init conditions.
2. Add robot-side phase state and make `DslBringupTest.update()` advance `INIT` across normal 20 ms ticks.
3. Add safe transition handling from `INIT` to `MAIN`.
4. Extend result details and REST/UI presentation with current phase and phase evidence.
5. Convert every repository DSL source, example, fixture, and generated reference to explicit phase syntax.
6. Add parser, runtime, and connected robot regressions.
7. Update the current runtime rules and matching workflow document only after explicit approval to change the DSL behavior contract.

## Required Tests

- Bare phase syntax is rejected with a migration-oriented validation error.
- Explicit `phase init:` one-pass initialization executes exactly once.
- Init `until` remains in `INIT` across multiple updates, then enters `MAIN`.
- Init `success` enters `MAIN` and does not finish the whole test.
- Init `abort` fails the test and applies safe outputs.
- Init `until` with unmet init requirement fails with the expected result.
- Init output is reapplied while waiting and returned to safe value at the transition.
- Signal-driven init source loss fails startup as it does today.
- Main behavior remains unchanged after a one-pass or multi-tick init.
- No single update performs a loop over time or exceeds the established test-update work budget.

## Tradeoffs

- Reusing the phase condition model keeps the language small and predictable, but phase-aware state increases interpreter complexity.
- Reapplying init output each tick makes motion reliable, but requires explicit safe release at the phase transition.
- Allowing init requirements is more expressive, but authors must understand that init and main proof are separate.

## Future Extensions

- Add `phase.elapsed` if authors need per-phase timing without manually accounting for prior phases.
- Add a phase-specific status panel only if the existing test detail presentation becomes insufficient.
- Consider a reusable `known-state` shorthand only after ordinary phase conditions have proven adequate.
