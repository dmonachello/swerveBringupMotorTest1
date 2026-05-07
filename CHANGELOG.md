# Changelog

All notable user-facing changes are documented in this file.

## 2026-05-06

### Added

- Added Robot Test DSL signal-set deadband support for signal-driven writes such as `controller0.leftY deadband 0.08 scaled 0.25 default 0.0`.

### Notes

- This feature implementation was done with pi.

## 2026-04-22

### Added

- Added a robot non-motion regression suite for connected TCP-path validation.
- Added a group/targeting regression script to improve automated CLI behavior checks.
- Added and expanded TCP UI protocol documentation and quick reference docs.
- Added a regression automation feature spec plus related test plans and procedures.

### Improved

- Expanded local regression assertions for better command targeting and validation coverage.
- Aligned CLI and documentation terminology around the devices table for consistency.
- Updated CLI grammar artifacts and parser/AST support files to match current behavior.
- Normalized Bridge CLI to canonical command forms for novice-first consistency.
- Refined architecture, setup, operator, NT contract, and testing docs for clearer workflows.

### Notable

- Significant update to `tools/can_nt/bridge_cli.py` and related CLI support files.
- Removed legacy CLI aliases (`ls`, `cfg`, `prof`, `val`, `show session`) with immediate hard errors and canonical replacement guidance.
- Removed duplicate or legacy `bringup_system.json` locations from `data/` and `src/main/deploy/` in this change set.
