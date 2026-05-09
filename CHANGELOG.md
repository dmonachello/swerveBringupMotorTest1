# Changelog

All notable user-facing changes are documented in this file.

## 2026-05-08

### Added - 2026-05-08

- Added a unified regression runner with named suites for local, DSL, CLI,
  Java, topology, changelog, and connected non-motion checks.
- Added topology editor regressions to the default local regression bundle.
- Added a changelog publication guard that requires `CHANGELOG.md` updates for
  major user-visible worktree changes.
- Added machine-readable regression reports and refreshable suite baselines for
  the unified runner.
- Added local regression failure history tracking that records first-failure,
  changed-failure, and recovery transitions without storing full green-run
  history.

### Improved - 2026-05-08

- Updated local regression output to print the specific feature coverage for
  each regression command as it runs.
- Updated stale group-targeting regression scripts to the current DSL and
  config save paths.
- Tightened DSL host validation so malformed numeric `set` syntax is rejected
  before runtime.
- Synced the checked-in bringup config copies to include controller-aware DSL
  test content and richer topology data for the demo profile.

## 2026-05-06

### Added - 2026-05-06

- Added Robot Test DSL signal-set deadband support for signal-driven writes
  such as `controller0.leftY deadband 0.08 scaled 0.25 default 0.0`.

### Notes

- This feature implementation was done with pi.

## 2026-04-22

### Added - 2026-04-22

- Added a robot non-motion regression suite for connected TCP-path
  validation.
- Added a group/targeting regression script to improve automated CLI
  behavior checks.
- Added and expanded TCP UI protocol documentation and quick reference docs.
- Added a regression automation feature spec plus related test plans and
  procedures.

### Improved - 2026-04-22

- Expanded local regression assertions for better command targeting and
  validation coverage.
- Aligned CLI and documentation terminology around the devices table for
  consistency.
- Updated CLI grammar artifacts and parser/AST support files to match
  current behavior.
- Normalized Bridge CLI to canonical command forms for novice-first
  consistency.
- Refined architecture, setup, operator, NT contract, and testing docs
  for clearer workflows.

### Notable

- Significant update to `tools/can_nt/bridge_cli.py` and related CLI
  support files.
- Removed legacy CLI aliases (`ls`, `cfg`, `prof`, `val`, `show session`)
  with immediate hard errors and canonical replacement guidance.
- Removed duplicate or legacy `bringup_system.json` locations from `data/`
  and `src/main/deploy/` in this change set.
