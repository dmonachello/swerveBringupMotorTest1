# Alpha Release Readiness

## Purpose

Define the required features, bug fixes, and verification steps to reach an "alpha"
release of this repo (robot Java + PC Python tool).

## Scope

- Robot-side: WPILib Java bringup harness (roboRIO).
- PC-side: Windows-first Python CANable sniffer + optional UI/CLI/topology
  tooling.
- Interfaces: REST/TCP for supported bringup control/state workflows and
  host-local diagnostics models.

## Definition Of "Alpha"

Purpose: Set the quality bar for an early release that a team can use repeatedly.

- Intended users: internal team members (pit + dev laptop) with basic FRC tooling.
- Primary goal: predictable bringup and diagnostics workflows with evidence capture.
- Acceptable: rough edges in UI polish and incomplete reverse-engineering features.
- Not acceptable: crashes on first run, broken docs, or unsafe defaults.

## Top Priorities (Alpha)

Purpose: Focus effort on the two areas that most affect day-to-day usability.

1. Device config + bringup test authoring must be fast, repeatable, and hard to
   mess up.
1. PC tool first-run reliability on Windows must be “it just works” (no
   crashes, clear errors).

## Alpha Exit Criteria

Purpose: Concrete pass/fail gates for declaring alpha.

1. Fresh clone on Windows can run the PC tool without code edits.
1. Robot project builds and deploys via the normal GradleRIO workflow.
1. Supported REST/TCP and host-local bringup contracts are explicitly documented and stable.
1. Hardware profiles/tests are data-driven, validated, and syncable to deploy.
1. Safety rules hold:

    - PC tool is CAN read-only by default.
    - Robot fails soft when the PC tool is absent.

## Blocker Bug Fixes (Do First)

Purpose: These must be fixed before any alpha tag is meaningful.

1. Make device config + bringup test creation easy and reliable:

    - One “happy path” workflow exists and is documented end-to-end.
    - Creating a new profile does not require code edits or manual JSON surgery.
    - Creating a matching bringup tests file is data-driven and validated.
    - Validators emit actionable, specific error messages (duplicate labels,
      missing fields, bad references).
    - Round-trip guarantees:
      - Topology editor save -> validate -> sync-to-deploy -> robot load.
      - Test wizard/template -> validate -> robot load.
    - Provide a single validate+sync gate command that teams run every time after
      edits:
      - Validates `src/main/deploy/bringup_system.json` (schema + semantic
        references).
      - Stamps `data_version`/`data_hash` when needed.
      - Rewrites the deploy-owned `src/main/deploy/bringup_system.json`.

1. Fix PC tool startup crash (done):

    - Regenerate/align CLI constants so
      `python -m tools.can_nt.can_nt_bridge --version` runs without crashing.

1. Remove or replace non-portable hardcoded scripts/paths:

    - `cli.bat` hardcodes a user-specific Python path.
    - Alpha requires one blessed entrypoint that works across machines.

1. Align Windows install script with actual tool needs:

    - `install_windows.ps1` should install dependencies that the docs and CLI
      expect (notably `prompt_toolkit`). (done)

1. Replace placeholder contract/setup docs:

    - `docs/NT_CONTRACT.md` is a TODO stub. (done)
    - `docs/SETUP.md` is a TODO stub. (done)

1. Fix confusing first-run warnings:

    - `tools/can_topology/validate_profiles.py` emits a SyntaxWarning due to
      invalid escape sequences in the module docstring. (done)

## Required Alpha Features

Purpose: Minimum product behavior for a usable alpha.

### Windows Entrypoints

Purpose: Avoid fragile invocation patterns.

- Provide and document one primary way to run the PC tool on Windows.
- Prefer module invocation:
  - Example: `python -m tools.can_nt.can_nt_bridge ...`
- If shipping `.cmd` wrappers, ensure they do not embed user-specific paths and
  work with standard Python installs.

### Historical NetworkTables Contract (Retired)

Purpose: Record the retired contract so older docs are not mistaken for the current architecture.

- Supported bringup control and diagnostics workflows no longer depend on NetworkTables.
- Historical references should point readers to `docs/NT_CONTRACT.md`.
- New alpha work must not reintroduce NT as an active bringup transport.

### Profiles And Deploy Sync

Purpose: Ensure hardware configuration is easy, safe, and repeatable.

- `src/main/deploy/bringup_system.json` is the single config file.
- Deploy copy (`src/main/deploy/bringup_system.json`) must be kept in sync using
  `python -m tools.validate_sync` (recommended).
- Legacy sync tool: `python tools/sync_profiles.py`.
- Provide a documented validation workflow:

  - Validate schema, required fields by interface, duplicate labels, and hash
    correctness.

### Bringup Tests Authoring

Purpose: Make it easy to create tests that match the devices table and fail
clearly when misconfigured.

- A “create tests for this profile” workflow exists and is documented.
- Tooling is available and works on Windows:
  - Bringup test wizard (`tools/bringup_test_wizard/...`) and/or template wizard
    (`tools/test_template_wizard/...`).
- Validation exists and is easy to run:
  - Unknown device label references are rejected with specific messages.
  - Required fields per test type are enforced.
  - The robot reports file/path errors and schema errors clearly when loading tests.

### End-to-End Diagnostics Surfaces

Purpose: The core workflows must work without surprises.

- Robot:
  - Controlled bringup actions (motors/sensors).
  - Throttled console reports (shared report runner).
  - JSON report output (`bringup_report.json`).
- PC tool:
  - CAN presence/age/count publishing to NT under `bringup/diag/...`.
  - CAN summary publishing and optional console monitor keys.

### Reverse-Engineering Basics (As Advertised)

Purpose: Keep implemented features aligned with repo claims.

- Inventory dump:
  - `--dump-api-inventory <path>` produces stable JSON.
- Diff:
  - `--diff-inventory <a.json> <b.json>` prints short, scannable deltas.
- Documentation includes examples and expected output shape.

## Reliability And Safety Must-Haves

Purpose: Reduce pit-time surprises and enforce safety constraints.

1. Robust Windows-first error handling:
   - COM port detection (`--list-ports`, auto-detect, `--no-prompt` behavior).
   - Clear failure messages when CANable/slcan cannot open.
1. Enforce "read-only by default" on PC tool:
   - Any CAN transmit capability must remain isolated under `tools/can_tx_poc/`
     and require explicit per-invocation authorization (for example,
     `--tx-allow`).
   - Docs must clearly mark transmit as non-default and risky.
1. Robot "PC tool absent" behavior:
   - No tight-loop error spam when NT keys are missing.
   - Reports remain useful using robot-local data alone.

## Verification Required For Alpha

Purpose: Define the minimum tests that make alpha credible.

### Windows Offline Smoke Checks

Purpose: Validate core tooling without requiring robot hardware.

- Python module import sanity:
  - Ensure the PC tool starts and `--version` works.
- CLI self-inventory:
  - `--list-ports` works.
  - `--list-keys` works.
  - `--dump-nt <path>` writes JSON.
- Profile validation:
  - Validate `src/main/deploy/bringup_system.json`.
  - Validate deploy copy `src/main/deploy/bringup_system.json`.
- Authoring workflows (offline):
  - Create a new minimal profile via the intended tool path and validate it.
  - Create a minimal bringup tests file for that profile via the intended tool
    path and validate it.

### Robot Build/Deploy Check

Purpose: Ensure the primary robot workflow is intact.

- Document the required JDK/WPILib setup and provide a one-command build check.
- Confirm GradleRIO build succeeds with the supported toolchain.

### Repo Hygiene

Purpose: Keep the repo usable across machines and CI.

- No unowned/unexplained files in the root.
- Any “local notes” files should be ignored via `.gitignore` or moved under a
  clear `notes/` area.

## Suggested Implementation Order

Purpose: Preserve momentum by unblocking first-run paths early.

1. Lock down the device config + tests authoring “happy path” (tools +
   validation + docs).
1. Fix the PC tool crash and confirm `--version` works.
1. Lock down Windows entrypoints (module invocation + optional wrapper).
1. Replace `docs/SETUP.md` and `docs/NT_CONTRACT.md` stubs with real content.
1. Add/refresh smoke checks and document exact pass/fail steps.
1. Tighten safety interlocks and "no PC tool" soft-fail behavior.

## Tradeoffs

Purpose: Make the constraints explicit.

- Being Windows-first limits reliance on Linux-only CAN tooling.
- Keeping NT keys stable slows refactors but prevents dashboard breakage.
- Adding analysis features increases CPU load on the PC; keep per-frame work
  O(1).

## Future Extensions (Post-Alpha)

Purpose: Capture what’s valuable but not required for alpha.

- Capture sessions (`--session`, `--session-dir`) for reproducible comparisons.
- Byte fingerprinting and candidate classification outputs published under
  `bringup/diag/can/...`.
- CI checks:
  - Python lint/type checks.
  - Headless “build robot code” validation with pinned toolchains.
