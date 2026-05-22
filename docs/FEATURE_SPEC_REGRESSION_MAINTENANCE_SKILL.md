SPEC_STATUS: IMPLEMENTED

# Feature Spec: Regression Maintenance and Skill Runner

## Purpose

Purpose: define a maintained regression-testing workflow for this repo that is
updated regularly, run on a predictable cadence, and callable on demand through
a Codex skill.

This spec complements, rather than replaces:

- [FEATURE_SPEC_REGRESSION_AUTOMATION.md](./FEATURE_SPEC_REGRESSION_AUTOMATION.md)

That earlier spec describes the regression framework direction. This spec
describes how the regression surface should be kept current in practice and how
it should be exposed as a repeatable skill.

## Status

Draft V1.

No implementation changes are approved by this spec alone.

## Problem

The repo has useful regression tests, but there is still a gap between:

- having scripts that can be run manually
- having a maintained regression inventory
- having a repeatable habit for updating tests when features change
- having a one-command or one-skill way to run the right checks at any time

Without that operational layer:

- new features can land without matching regression coverage
- stale regressions can give a false sense of safety
- developers may run different test subsets inconsistently
- review quality depends too much on memory instead of an explicit checklist

## Goals

- Define regression tests as a maintained product surface, not ad hoc scripts.
- Require regression updates when contract-sensitive features change.
- Define a small, repeatable cadence for running regressions.
- Provide a Codex skill that can run the relevant regression set at any time.
- Keep local-only checks separate from robot-connected checks.
- Make output actionable enough for day-to-day engineering use.

## Non-Goals

- This spec does not require full CI integration in V1.
- This spec does not require every test in the repo to be migrated at once.
- This spec does not replace human review.
- This spec does not authorize motion automation on connected hardware.
- This spec does not define the full fixture schema again.

## Scope

In scope:

- regression inventory and ownership expectations
- update policy when features change
- regular run cadence
- skill contract and invocation model
- output expectations for the skill
- minimum required suite categories

Out of scope:

- the complete internal implementation of the regression runner
- visual UI snapshot testing
- performance benchmarking
- autonomous robot-motion validation

## Principles

- Contract-first: regressions protect operator-visible and machine-visible
  behavior.
- Negative-path by design: regressions must intentionally try malformed input,
  unsupported input, missing prerequisites, and other user mistakes for
  user-facing surfaces.
- Small and frequent: update regressions as part of feature work, not later.
- Deterministic by default: local regressions must remain the primary fast gate.
- Explicit hardware separation: robot-connected regressions are opt-in and must
  stay non-motion unless separately approved.
- Runnable anytime: the same regression surface must be callable manually and
  through a skill.
- Recovery-oriented errors: tests should verify that failures produce useful
  corrective guidance, not just a hard failure code, when the surface is meant
  for students or non-expert operators.

## Required Regression Categories

V1 requires these maintained categories:

### 1. Local deterministic regressions

Purpose: protect parsing, config, status, CLI, and non-hardware workflows.

Examples:

- Python DSL compile and validate tests
- CLI local command-path regressions
- config round-trip and schema checks
- status-code behavior checks

### 2. Java unit regressions

Purpose: protect robot-side runtime behavior that can be tested offline.

Examples:

- DSL runtime semantics
- device-signal mapping behavior
- fallback behavior
- deadband or transform behavior

### 3. Robot-connected non-motion regressions

Purpose: protect connected command paths without commanding motion.

Examples:

- show/validate/config flows
- TCP/UI reachability checks
- connected runtime state fetches

### 4. Feature-specific regression additions

Purpose: require targeted coverage for new contract-sensitive features.

Examples:

- new DSL syntax
- new device type in config/runtime
- new normalized JSON fields
- new warning/failure behavior

## Regression Update Policy

Whenever a feature changes any of the following, regression updates are
required in the same change:

- parser or grammar behavior
- normalized payload shape
- status codes or status-code meaning
- config schema or required fields
- operator-visible CLI behavior
- robot-side runtime semantics
- documented examples that act as supported workflows

Required rule:

- if behavior changes, at least one regression must be added or updated to
  prove the intended outcome
- if the behavior is user-facing, at least one regression must exercise an
  invalid, malformed, or missing-input path and verify that the error handling
  is safe and helpful

Preferred rule:

- each feature spec should name the expected regression category and runner
  target

Additional rule for this project:

- because this project is intended to be used by students and non-computer
  skilled operators, user-facing features should be assumed to receive
  unexpected input and misuse during normal operation
- regressions should therefore include "try to break it" cases for parser,
  CLI, config, workflow, and connected command surfaces whenever practical

## Maintenance Cadence

V1 cadence:

### Per change

Run the smallest relevant regression set before finishing feature work.

Examples:

- Python-only DSL changes:
  - targeted Python unit tests
- Java DSL runtime changes:
  - targeted Java tests
- config/CLI contract changes:
  - targeted CLI regressions

### Daily or before push

Run the standard local regression bundle:

- targeted Python unit tests
- Java unit tests
- canonical local CLI regression scripts or unified runner equivalent

### Before merge or release candidate

Run the broader regression bundle:

- full local deterministic regression set
- Java tests
- any required generated-artifact checks
- robot-connected non-motion checks when the changed surface affects them

## Skill Requirement

V1 must define a Codex skill for regression execution.

Suggested skill name:

- `regression-runner`

Suggested skill location:

- `.codex/skills/regression-runner/`

Required skill artifacts:

- `SKILL.md`
- optional helper scripts under `scripts/`

## Skill Contract

Purpose: give engineers one reliable way to run the right regressions at any
time.

The skill must support these user intents:

- run the default local regression set
- run a targeted regression subset for a specific feature area
- run robot-connected non-motion regressions when explicitly requested
- summarize failures with concrete commands and files
- optionally suggest which baselines or tests likely need updates

### Minimum supported skill modes

#### Local default mode

Runs the standard offline checks for this repo.

Expected coverage:

- Python unit tests relevant to tooling and DSL
- Java unit tests
- current canonical local regression scripts or the unified runner equivalent

#### Targeted mode

Runs only the checks relevant to a requested surface.

Examples:

- `dsl`
- `cli`
- `java`
- `config`
- `status`

#### Connected non-motion mode

Runs robot-connected checks only when the user explicitly supplies the robot
target and acknowledges connected execution.

## Skill Invocation Examples

Examples of expected user requests:

```text
[$regression-runner]
Run the default local regression set for this repo.
```

```text
[$regression-runner]
Run targeted DSL regressions only.
```

```text
[$regression-runner]
Run robot non-motion regressions against 172.22.11.2.
```

## Skill Output Requirements

The skill output must include:

- which suite or subset was run
- exact commands executed
- pass/fail summary
- failing file or test names
- whether failures are likely caused by:
  - behavior regressions
  - stale expected outputs
  - missing regression updates
  - environment prerequisites

Preferred output shape:

1. summary
2. failures
3. skipped checks and why
4. next actions

## Default Command Surface

V1 should use existing commands where possible.

Current expected local commands include:

- `python -m unittest tools.can_nt.tests.test_robot_test_dsl tools.can_nt.tests.test_bridge_cli_robot_test_dsl_cli`
- `.\gradlew.bat test`
- `python tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py`
- `python tools/can_nt/scripts/bridge_cli_group_targeting_4m2g3t_regression.py`

Current expected connected command includes:

- `python tools/can_nt/scripts/bridge_cli_robot_non_motion_regression.py --rio <ip>`

This list may be centralized later in the unified runner, but the skill must
not invent a different contract from the repoâ€™s canonical commands.

## Ownership Model

Regression upkeep must have explicit ownership.

V1 rules:

- feature author updates the nearest relevant regression
- reviewer checks that a contract-sensitive feature has matching coverage
- release owner runs the broader pre-release regression bundle

If no reasonable regression can be added yet, the change must explicitly note:

- why coverage is missing
- what follow-up regression is required

## Gating Rules

V1 gating expectations:

- no contract-sensitive feature should merge with zero regression impact
- stale or failing local deterministic regressions block feature completion
- connected non-motion regressions are required when connected behavior changes
- robot-connected regressions remain advisory only when the environment is
  unavailable, but that must be stated explicitly

## Documentation Requirements

When this feature is implemented, update:

- repo-facing regression workflow docs
- any developer quick-start documentation that lists the standard test gates
- skill documentation for installation and usage

The docs must clearly say:

- what the default regression bundle is
- when to run targeted vs full checks
- how to invoke the skill
- how to refresh or update regressions after intended behavior changes

## Definition of Done

This feature is done when:

- the repo has a defined default regression bundle
- the repo has a defined targeted regression model
- the required update policy is documented
- a Codex skill is defined for running regressions at any time
- the skill can run local checks and report useful failures
- connected non-motion regression invocation is defined and opt-in
- documentation names the regular run cadence

## Risks

- too-large default bundles may discourage routine use
- weak ownership rules may still allow stale regressions
- skill output may become noisy if it does not separate environment failures
  from product regressions

## Mitigations

- keep the default bundle small and deterministic
- keep targeted mode first-class
- require exact commands in output
- separate local and connected results clearly

## Tradeoffs

- a maintained regression workflow adds process overhead, but it is cheaper
  than rediscovering behavior drift later
- a skill adds another maintained interface, but it makes good habits easier to
  repeat
- targeted modes reduce latency, but full bundles are still needed before
  broader integration points

## Future Extensions

- CI entrypoints that mirror the same local and targeted bundles
- automated suite selection from changed files
- baseline refresh helpers with explicit review prompts
- machine-readable regression inventory files
- richer skill modes for generated-artifact checks and release-readiness runs

