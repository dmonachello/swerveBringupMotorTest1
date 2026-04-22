# Feature Spec: CLI Canonical Command Normalization (Novice-First)

## Summary

This spec defines a strict normalization pass for the Bridge CLI command surface so each action has one canonical command form. The objective is to reduce operator confusion, improve discoverability, and enforce consistent grammar across parser, implementation, help text, and manuals.

This change is novice-first and strict:

- Novice users are the optimization target.
- Removed aliases hard-error immediately.
- Canonical forms are enforced now, not phased in.

## Problem Statement

The current CLI includes multiple synonyms and duplicate grammar paths for the same intent (for example `show`/`ls`, `profile`/`prof`, and duplicate `save` entries). This increases cognitive load for new operators, complicates help output, and creates drift between grammar, implementation, and documentation.

## Goals

- Enforce one canonical command form per action family.
- Make top workflows predictable for novice users.
- Ensure `?` help and `help` text teach only canonical forms.
- Keep parser grammar, command dispatch, and docs fully synchronized.
- Keep beginner messaging as the default operator guidance level.

## Non-Goals

- Adding unrelated new CLI features.
- Changing robot-side control behavior.
- Preserving backward compatibility for removed aliases.
- Modifying NetworkTables key contracts.

## Scope

In scope files:

- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/bridge_cli_ebnf.txt`
- `tools/can_nt/bridge_cli_parser.py`
- `tools/can_nt/bridge_cli_ast.py`
- `tools/can_nt/bridge_cli_grammar_gen.py`
- `tools/can_nt/bridge_cli_constants_gen.py`
- `docs/CLI_USER_MANUAL.md`
- `docs/CLI_REFERENCE_MANUAL.md`

Out of scope:

- Java robot code changes.
- CAN bridge data publishing changes.
- Dashboard layout changes.

## Locked Product Decisions

- Persona priority: novice operators first.
- Grammar policy: strict canonical normalization now.
- Alias policy: removed aliases hard-error immediately.
- Context policy: retain context-based mode workflow (`exec`, `config`, `group`, `device`, `test`) as-is; only command naming/syntax is normalized.

## Canonical Command Principles

- Use one verb-object pattern per intent.
- Prefer explicit terms over abbreviations.
- Keep argument ordering stable across command families.
- Use one canonical output flag pattern (`--json`, `--pretty`) for show/read commands.
- Use one save/validate/run style consistently across local and robot-aware flows.

## Canonical Surface (Target)

The following canonical forms are normative examples for normalization:

- Use `show ...` as canonical inspection verb (remove `ls` alias).
- Use `profile ...` as canonical profile verb (remove `prof` alias).
- Use `configure terminal` as canonical config entry (remove `cfg` alias).
- Keep `show workspace` as canonical session view (remove alternate command names if any).
- Keep one canonical `save` form per destination and remove duplicate productions.

Final canonical matrix must be generated from implementation inventory and recorded in `docs/CLI_REFERENCE_MANUAL.md`.

## Functional Requirements

## 1) Alias Removal and Hard Errors

- All removed aliases must fail with an immediate CLI error.
- Error text must include the canonical replacement command.
- No compatibility shim or fallback execution is allowed.

Example:

```text
ERROR: Unknown command 'prof'. Use 'profile'.
```

## 2) Grammar and Parser Synchronization

- Remove alias productions from `tools/can_nt/bridge_cli_ebnf.txt`.
- Regenerate parser and grammar-derived artifacts in the same change.
- Keep parser and runtime dispatch behavior consistent with grammar.

## 3) Help and Discoverability

- `?` completion must present canonical forms only.
- `help` and command help text must show canonical examples only.
- `show commands` output must match canonical command matrix exactly.

## 4) Novice-First Message Level

- Beginner messaging remains the default user-facing guidance mode.
- `messages <beginner|medium|expert>` remains supported as the control surface.
- `--cli-messages beginner` remains the startup override.
- Persisted message level behavior via `.bridge_cli_settings.json` remains intact.

## 5) Documentation Contract

- `docs/CLI_USER_MANUAL.md` must teach canonical commands only.
- `docs/CLI_REFERENCE_MANUAL.md` must enumerate only canonical grammar.
- Any examples using removed aliases must be replaced.

## Error Handling Requirements

- Removed alias invocation returns deterministic CLI error status.
- Error text must be short, actionable, and canonical-replacement specific.
- Parse/dispatch errors must not terminate the interactive session.
- Batch mode behavior remains non-interactive.

## Acceptance Criteria

- Alias commands fail immediately with replacement guidance.
- Canonical commands succeed for all currently supported workflows.
- EBNF, parser artifacts, and runtime command dispatch are in sync.
- `?`, `help`, and manuals show only canonical forms.
- Beginner message-level flow remains functional and default.
- Existing regression suites pass for normalized command surface.

## Test Plan

- Add or update parser tests for removed aliases to assert hard errors.
- Add or update command-dispatch tests for canonical-only acceptance.
- Run CLI regression scripts for:

  - local group/targeting workflow
  - robot non-motion workflow

- Verify help output snapshots contain no removed aliases.
- Verify docs command examples match runtime behavior.

## Rollout

- Land grammar + dispatch + help + docs in one change set.
- Add a changelog entry summarizing canonical-only enforcement.
- No grace period for alias compatibility.

## Tradeoffs

- Pro: lower long-term confusion and support burden for new users.
- Pro: tighter guarantees for parser/docs/runtime consistency.
- Con: immediate breakage for users relying on old aliases.
- Con: short-term support overhead to update scripts and habits.

## Future Extensions

- Add an optional command-lint mode for batch scripts before execution.
- Add a machine-readable command inventory export for docs/tests sync.
- Add targeted onboarding tips keyed by novice workflow milestones.
