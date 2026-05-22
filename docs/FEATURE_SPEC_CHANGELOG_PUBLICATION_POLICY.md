SPEC_STATUS: IMPLEMENTED

# Feature Spec: Changelog Publication Policy

## Purpose

Define when `CHANGELOG.md` must be updated and how that requirement is enforced
during local regression runs and major pushes.

## Status

Implemented V1.

## Problem

The repo has user-facing behavior changes, but changelog updates can be missed
unless they are enforced explicitly.

That causes two problems:

- important user-visible changes are easy to overlook at push time
- release notes become incomplete and need reconstruction later

## Goals

- require `CHANGELOG.md` updates for major user-visible changes
- keep the rule deterministic enough for a local pre-push gate
- make the check runnable through the unified regression runner

## Non-Goals

- automatic changelog text generation in the gate itself
- release-note quality review by script alone
- perfect semantic classification of every possible file change

## Major Change Definition

V1 treats a change as major when the worktree includes changes in one or more
of these product surfaces:

- robot-side runtime code under `src/main/java/`
- CLI or connected command behavior under `tools/can_nt/`
- shared DSL compiler/validator behavior under `tools/common/robot_test_dsl/`
- topology editor or topology validation behavior under `tools/can_topology/`
- shipped deploy config under `src/main/deploy/`
- supported workflow examples under `docs/examples/`

V1 intentionally does not require a changelog update for:

- pure test-only changes
- regression fixture-only changes
- baseline refresh-only changes
- local-only config changes under `data/`

## Rule

If a major change is present in the worktree, `CHANGELOG.md` must also be
modified in the same worktree before the local regression bundle is considered
green.

## Enforcement

V1 enforcement is a local deterministic guard script:

- `python tools/can_nt/scripts/changelog_guard.py`

The script:

- inspects tracked modified files relative to `HEAD`
- includes untracked files
- checks whether any changed path matches the major-change surface
- fails if a major change exists and `CHANGELOG.md` is unchanged

## Unified Runner Integration

The guard is part of the local unified regression bundle.

That means:

- targeted invocation is supported through the runner manifest
- default local regression runs enforce the changelog rule

## Operator Workflow

When the guard fails:

1. decide whether the changed files represent a real user-facing change
2. if yes, update `CHANGELOG.md`
3. if no, narrow the guard surface or move the file out of the major-change set

## Tradeoffs

- path-based enforcement is simple and reliable, but conservative
- some internal changes may require a human to decide whether the changelog
  entry should be short or extensive

## Future Extensions

- commit-range mode for CI
- staged-only mode for pre-commit hooks
- changelog section validation
- optional integration with the changelog generator skill

