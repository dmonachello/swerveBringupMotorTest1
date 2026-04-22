# Feature Spec: Regression Automation Framework (V1)

## Purpose

Define a data-driven regression framework for the bringup CLI and robot-connected command path, using fixture configs and expected results as stable comparison artifacts.

## Status

Draft V1 (planning only).

No implementation changes are approved by this spec alone.

## Problem Statement

Current regression coverage is useful but script-specific and partially stateful.

Gaps:

- test inputs are embedded in scripts instead of reusable fixture files
- expected outcomes are asserted ad hoc instead of baseline-managed artifacts
- no unified runner for local-only and robot-connected suites
- limited change-control workflow for intentional behavior updates

Result: behavior drift is harder to detect and review at scale.

## Goals

- Create a reusable fixture + expected-results model for regression tests.
- Keep local suites deterministic and fully automatable.
- Support connected-robot suites with non-motion safety constraints.
- Make expected behavior reviewable in versioned files (golden baselines).
- Enable a single command to run selected suites and return CI-friendly status.

## Non-Goals

- No motion-command automation in V1.
- No CAN transmit behavior from PC tooling.
- No replacement of existing scripts on day one.
- No mandatory CI integration in V1 (but design for easy CI adoption).

## Principles

- Deterministic first: local tests must not depend on external hardware.
- Additive rollout: existing regression scripts remain valid during migration.
- Baseline clarity: expected behavior must be explicit and diffable.
- Safety first: robot-connected suites must stay non-motion by default.
- Small reversible changes: convert suites incrementally.

## Scope

In scope (V1):

- fixture file format for command sequences and optional preconditions
- expected-results format for status/output assertions
- unified regression runner with suite selection flags
- baseline refresh mode for intentional behavior changes
- local and robot-non-motion suite separation

Out of scope (V1):

- autonomous motion validation
- performance benchmarking framework
- property/fuzz testing
- coverage instrumentation

## Proposed Repository Layout

Purpose: define stable locations for regression assets.

- `tests/regression/fixtures/`
- `tests/regression/expected/`
- `tools/can_nt/scripts/run_regressions.py`
- `tools/can_nt/scripts/lib/regression_framework.py`

Examples:

- `tests/regression/fixtures/group_targeting_local_v1.json`
- `tests/regression/fixtures/robot_non_motion_v1.json`
- `tests/regression/expected/group_targeting_local_v1.expected.json`
- `tests/regression/expected/robot_non_motion_v1.expected.json`

## Test Data Model

Purpose: separate test inputs from test logic.

Fixture file (conceptual):

- metadata: suite name, mode (`local` or `robot_non_motion`)
- environment assumptions (optional)
- command steps in order
- optional setup/teardown commands

Expected-results file (conceptual):

- per-step expected status code set
- required output fragments
- optional forbidden output fragments
- optional structured JSON assertions when command supports JSON output

## Assertion Strategy

Purpose: maximize signal while minimizing brittle tests.

Priority order:

1. Status code assertions (primary contract)
2. Structured JSON assertions (`--json --pretty`)
3. Targeted text fragment assertions (fallback)

Avoid full raw-output equality except when explicitly justified.

## Suite Types

### Local Deterministic Suite

Purpose: run on any developer machine without robot/CAN/NT.

Characteristics:

- no hardware dependency
- reproducible outcomes
- safe as default pre-commit gate

### Robot Non-Motion Suite

Purpose: validate connected-path behavior without commanding motion.

Characteristics:

- requires TCP connectivity to roboRIO
- uses only non-motion commands (`show`, `validate`, mode transitions, connect/disconnect)
- fails fast if robot unavailable

## Topology Editor and UI Addendum

Purpose: define how regression automation extends beyond CLI-only coverage.

### Topology Editor Scope

V1 target: prioritize model/data regressions over visual automation.

Candidate checks:

- load fixture JSON and validate parse + schema acceptance
- round-trip save and compare normalized JSON content
- profile import/export consistency
- label rename propagation to known references
- reference integrity checks (no dangling labels after edits)

Preferred assertion style:

- structured JSON comparison after canonical normalization
- explicit status/result codes from editor-side validation helpers
- targeted text assertions for warnings/errors when needed

### Bringup UI Scope

V1 target: non-motion workflow regressions using command/state paths.

Candidate checks:

- connect/disconnect behavior and failure handling
- state-refresh behavior for runtime status panes
- non-motion command routes (`show`, `validate`, profile/group navigation)
- source-mode visibility checks (`local`, `robot`, `both`) where applicable

Out of scope in V1:

- pixel-accurate screenshot comparisons
- full visual diffing across layout/theme changes
- motion command automation

### Phased Rollout

Phase 1:

- shared fixture and expected framework for CLI/local and robot non-motion scripts

Phase 2:

- migrate topology editor data-transform checks into the same fixture/expected model

Phase 3:

- add targeted UI workflow regression checks backed by stable state assertions

SID_QUESTION: Should topology editor regressions run in the same runner process, or as a dedicated sub-runner invoked by the main runner?

SID_QUESTION: For UI regressions, should V1 require a mock session playback mode to reduce dependence on live robot availability?

## Runner Behavior

Purpose: standardize invocation and exit semantics.

Proposed CLI:

- `python tools/can_nt/scripts/run_regressions.py --suite local`
- `python tools/can_nt/scripts/run_regressions.py --suite robot-non-motion --rio 172.22.11.2`
- `python tools/can_nt/scripts/run_regressions.py --suite all --include-robot --rio 172.22.11.2`
- `python tools/can_nt/scripts/run_regressions.py --refresh-expected --suite local`

Exit code contract:

- `0` all selected checks pass
- non-zero any check fails or required environment missing

## Baseline Update Workflow

Purpose: control intentional behavior changes.

Flow:

1. run suites in compare mode
2. inspect failures and confirm intended vs unintended deltas
3. run refresh mode only for intended deltas
4. review baseline diffs in PR
5. merge only with explicit reviewer acknowledgment

## Safety Rules

- Robot-connected suite must remain non-motion unless explicitly expanded in a future spec.
- No CAN transmit behavior is added to regression tooling.
- No hidden baseline refresh in normal compare mode.
- Runner must clearly print which suite type is active.

## Definition of Done (V1)

- Fixture and expected schemas documented and versioned.
- Unified runner executes at least one migrated local suite.
- Unified runner executes at least one migrated robot non-motion suite.
- Existing local regression script can be run through runner (directly or wrapped).
- Failure output identifies suite, step index, command, and assertion that failed.

## Risks

- Overly strict output matching can cause noisy failures.
- Hidden shared state can reduce determinism.
- Robot environment variability may cause flaky connected tests.

## Mitigations

- Prefer status/JSON assertions over full text matching.
- Enforce per-suite setup/reset commands.
- Keep robot suites small, non-motion, and explicit about prerequisites.

## Open Questions

SID_QUESTION: Should expected files support regex matchers, or stay exact-fragment only in V1?

SID_QUESTION: Should local suite runner auto-bootstrap a temporary workspace copy for isolation?

SID_QUESTION: Should robot suite require explicit `--ack-non-motion` flag as an extra safety gate?

## Tradeoffs

- More fixtures and expected files increase repo size, but improve reviewability.
- Baseline refresh workflow adds process overhead, but prevents silent behavior drift.
- Unified runner centralizes logic, but introduces framework maintenance cost.

## Future Extensions

- Motion-safe simulated suite with robot-side mock hooks.
- Trend reporting across runs (pass/fail history and flaky detection).
- Schema validation for fixture/expected files.
- CI matrix split (`local`, `robot-non-motion`) with artifact upload.
