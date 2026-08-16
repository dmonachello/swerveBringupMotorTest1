# Release Stabilization Review

Date: 2026-08-16

Status: Not ready for release

P0 status: Resolved in the current working tree; P1 stabilization remains.

## Purpose

Assess whether the current repository is ready to release based on the implemented
code, documentation, tests, configuration, and integration boundaries.

This review does not propose redesigning working components. It identifies the
smallest set of changes required to produce a release candidate.

## Release Decision

The project is not ready for release.

The intended architecture is coherent: the roboRIO owns actuation and safety
behind REST, while the Windows host provides passive CAN observation plus UI and
CLI configuration. Three concrete P0 defects prevent release, and the current
release gate is red.

## Intended Architecture

Purpose: Record the architecture reconstructed from the current implementation
and governing documentation.

- `RobotV2` owns robot lifecycle, actuation, safety, DSL execution, and the REST
  server.
- The host tool reads CAN passively through CANable and must never transmit.
- The UI and CLI use shared host services and current robot REST state.
- `src/main/deploy/bringup_system.json` is the canonical shared configuration.
- The topology editor authors that configuration and its topology graph.
- NetworkTables is retired from supported workflows.
- Robot-local telemetry and host-observed CAN evidence remain separate.

## P0 - Cannot Release

### Host CAN Transmission Path

Resolution: The supported bridge no longer exposes or imports transmission code.
Experimental replay is isolated under `tools/can_tx_poc/`, remains disabled by
default, and requires `--tx-allow` for each invocation.

The host includes a live CAN transmission path despite the passive-only system
contract.

Evidence:

- `AGENTS.md:24` says the Python host must never transmit CAN frames.
- `docs/ARCHITECTURE.md:109`, `:367`, and `:455` repeat the passive-only rule.
- `tools/can_nt/can_cli.py:344-351` exposes `--tx-seq` and `--tx-allow`.
- `tools/can_nt/can_nt_bridge.py:762-764` permits transmission behind a safety
  gate.
- `tools/can_nt/can_nt_bridge.py:1192-1194` starts requested transmission.
- `tools/can_nt/can_tx.py:129-136` constructs a CAN message and calls
  `bus.send()`.

A safety flag does not satisfy the passive-only architecture. This path must not
ship. PCAP-only marker injection is distinct from live bus transmission and is
not included in this finding.

### Invalid Canonical Configuration

Resolution: The analyzer node key is repaired, shared schema validation now
rejects duplicate node keys and missing edge endpoints, and canonical metadata is
regenerated through `tools.validate_sync`.

The tracked canonical configuration contains invalid topology, while the primary
validator reports success.

Evidence:

- `src/main/deploy/bringup_system.json:4151` begins the
  `test_minimal_25_9` profile.
- The profile contains node key `12` but no node key `11`.
- Edges at `src/main/deploy/bringup_system.json:4287-4300` reference node key
  `11`.
- `python -m tools.can_topology.validate_profiles --path
  src/main/deploy/bringup_system.json` reports two missing endpoints.
- `python -m tools.validate_sync --no-write --warnings` reports successful
  validation.
- `tools/config/schema_store.py:2148-2194` validates topology device references
  but not edge endpoints.

The tracked release input is malformed, and the documented validation gate does
not detect it.

### Topology Round-Trip Corruption

Resolution: Unmatched-key allocation now applies only to registry-backed profile
devices. Infrastructure keys remain stable, with focused round-trip and
cross-surface regression coverage.

A no-op topology-editor save can corrupt valid topology.

Evidence:

- The maintained topology-editor and cross-surface regression bundles fail.
- `tools/can_topology/tests/test_can_top_editor_profile_load.py:648-690`
  defines an explicit save-and-restart round-trip equality requirement.
- `tools/can_nt/tests/test_cross_surface_regression.py:137-181` requires editor
  output to remain readable by validators, the shared store, and the CLI.
- `tools/can_topology/can_top_editor.py:5590-5679` restores device and
  infrastructure keys.
- `tools/can_topology/can_top_editor.py:5681-5688` subsequently renumbers
  unmatched nodes.
- `_device_nodes()` at `tools/can_topology/can_top_editor.py:8916-8921`
  includes every non-callout node, including infrastructure nodes.
- Existing edges retain their previous endpoint keys.

The observed regression changes a CANnect node key and leaves nine dangling
edges. This is a normal operator save path, so it is release-blocking.

## P1 - Fix Before Release

### Supported Test Surface Is Red

The maintained local suite passed seven of ten bundles. The topology-editor,
cross-surface, and changelog-guard bundles failed. A full source test run produced
854 passes and 21 failures.

Evidence:

- UI tests in `tools/can_nt/tests/test_bringup_ui_actions.py:1766-1794` and
  `:3297-3302` expect the former `Activate Group` behavior.
- `Current UI And Runtime Rules - V2.md:296-410` specifies `Runtime Activate`.
- Several UI tests instantiate incomplete objects through `__new__` and recurse
  instead of exercising supported initialization.
- Discovery and passive-analysis fixtures also contain stale expectations.

The intended behavior must be confirmed against the approved rules before any UI
behavior changes. Stale tests and fixtures should then be aligned with that
behavior, and the maintained runner should cover the full supported source test
surface.

### Verification Mutates Tracked Files

The regression and build gate mutates tracked generated metadata and can trigger
its own changelog guard.

Evidence:

- `build.gradle:86-89` defines the build-info update task.
- `build.gradle:114-116` makes Java compilation depend on that task.
- `tools/update_build_info.py:301` and later code write tracked Java and Python
  build-info files.
- During this review, the Java test step changed `BuildInfo.java` and
  `build_info.py`; the later changelog guard treated generated changes as major
  source changes.

Release verification must be deterministic and leave a clean worktree.

### Transport Documentation Contradicts Runtime

Operator-facing transport documentation does not consistently describe the
implemented REST architecture.

Evidence:

- `src/main/java/frc/robot/RobotV2.java:75-78` and `:121-122` start the REST
  server.
- `docs/NT_CONTRACT.md:4-10` says NetworkTables is retired.
- `docs/TCP_UI_PROTOCOL.md:1`, `:9`, `:36`, and `:46` present the removed TCP UI
  server as active.
- `docs/FEATURE_MATRIX.md:42`, `:60`, and `:100` claim NetworkTables diagnostics
  publishing and consumption.
- `docs/BRIDGE_RUNTIME_ARCH.md:42`, `:55`, `:59`, and `:92` describe a TCP
  reader.
- `install_windows.ps1:45-54` installs `pyntcore` and `pynetworktables`.

Historical documents must be labeled clearly, and supported installation and
operator documentation must describe the current REST and host-local flow.

### Windows Setup Is Not Reproducible

The supported Windows setup and launcher path is neither pinned nor portable.

Evidence:

- `install_windows.ps1:45-54` installs unpinned latest packages.
- `docs/INSTALL_WINDOWS.md:20-24` lists fewer dependencies than the installer.
- `cli.bat:2` and `CLI2.BAT:2` hard-code a user-specific Python 3.13 path.
- Root launchers hard-code the roboRIO address.
- `uiNoCan.bat` does not forward additional arguments.

The release needs a single reproducible dependency set and launch path with
overrideable Python and roboRIO settings.

### Release Identity Is Inconsistent

The repository does not present a consistent release version or release history.

Evidence:

- `README.md:9-17` describes the project as internal alpha and unfinished 1.0.
- `tools/can_nt/VERSION`, `tools/common/app_versions.py`, and
  `src/main/java/frc/robot/AppVersion.java` report `1.0.0`.
- `CHANGELOG.md` has no entries after 2026-07-08 despite later user-facing work.
- `docs/RELEASE_1_0_READINESS.md:252-308` has no completed checklist items.

Use an RC identity until all mandatory release gates pass, then set the final
version and release history deliberately.

### Documentation Entry Path Is Stale

The primary documentation path contains broken, machine-specific, and obsolete
content.

Evidence:

- `README.md` contains machine-specific `/abs/path/c:/...` links.
- `docs/USER_GUIDE.md:223-237` contains unresolved citation placeholders and
  references retired NetworkTables tools.
- `docs/DOCS_HEALTH_REPORT.md:5-9` records nine broken links, 137 orphan pages,
  and 14 duplicate-title families.
- `docs/FEATURE_MATRIX.md` contains stale NetworkTables claims and malformed
  characters.

The release does not require cleaning every orphaned document, but its supported
entry path, installation guide, user guide, and feature matrix must be reliable.

### Hardware Integration Evidence Is Missing

The Java unit suite passes, but release-critical behavior has not been verified
against a connected roboRIO during this review.

Evidence:

- In-process REST endpoint and session tests pass.
- The connected non-motion regression was not run because no target was
  authorized or confirmed.
- `docs/RELEASE_1_0_READINESS.md:274-294` leaves disconnect handling, session
  locking, stop latching, disabled and E-stop behavior, protocol behavior, and
  end-to-end tests unchecked.

Before RC, run the connected non-motion suite and document Driver Station
disable, E-stop, disconnect, and stop-latch results.

### Persistence Failures Can Be Hidden

The topology editor can report a successful save while suppressing backup or
synchronization failures.

Evidence:

- `tools/can_topology/can_top_editor.py:2066-2078` swallows backup failures.
- `tools/can_topology/can_top_editor.py:3281-3298` suppresses synchronization
  errors.

Save completion must distinguish successful canonical persistence from degraded
backup or synchronization behavior.

### Profile Dropdown Uses The Wrong Config Source

The topology editor's lower `Profiles` dropdown can list profiles from the
canonical deploy config instead of the config currently opened by the operator.
Its `Load` action can consequently load a profile from the wrong file.

Evidence:

- `tools/can_topology/can_top_editor.py:2726-2727` stores the opened path in
  `_profile_source_path` and updates the upper profile-name choices from that
  file.
- `_read_profile_index()` at
  `tools/can_topology/can_top_editor.py:2907-2929` always reads
  `_default_profiles_path()` rather than the active source path.
- `_refresh_profile_choices()` at
  `tools/can_topology/can_top_editor.py:2932-2956` populates the lower dropdown
  from that canonical index.
- `_on_load_selected_profile()` at
  `tools/can_topology/can_top_editor.py:2968-2987` also loads from
  `_default_profiles_path()` instead of `_profile_source_path`.
- `Current UI And Runtime Rules - V2.md:232-238` requires `Open Config...` to
  make the selected file the active source for profile browsing and later
  saves.

Make both profile controls and the lower `Load` action use the active loaded
config source. Add a source-switching regression proving that canonical profile
names do not leak into another opened config.

### Discovery-First Status Is Unclear

Discovery-first configuration is presented as supported while the underlying
specification and validation remain partial.

Evidence:

- `docs/APP_NOTE_DISCOVERY_FIRST_CONFIG_BOOTSTRAP.md` presents the bootstrap
  path as supported.
- `docs/FEATURE_SPEC_BRINGUP_UI_DISCOVERY_FIRST_CONFIG_AUTHORING.md:1` is
  `PROPOSED`.
- `docs/FEATURE_SPEC_PASSIVE_CAN_DEVICE_DISCOVERY_POC.md:1` is
  `PARTIALLY_IMPLEMENTED` and requires live validation.
- Discovery-related tests fail in the full source test run.

Either stabilize and validate the core workflow or label it experimental for the
release candidate.

## P2 - Acceptable Known Limitations

Purpose: Record limitations that do not require release-time redesign.

- Host layering remains incomplete, with large UI and CLI modules. The current
  boundaries are documented and do not justify a stabilization-time refactor.
- Legacy flags and compatibility adapters may remain when clearly labeled and
  covered by tests.
- Topology deletion semantics retain open specification questions. Document the
  limitation rather than expanding the feature during stabilization.
- The broad orphan-document backlog and repository-root clutter may remain after
  the supported documentation path is curated.
- CI is absent. A deterministic and mandatory local release gate is acceptable
  for this release candidate.

## Later

Purpose: Exclude enhancements that are not required for this release.

- Byte fingerprinting.
- CLI configuration wizards.
- Message compiler generation.
- Multi-analyzer workflows.
- Topology link routing.
- Unified Python and Java status codes.
- Test-owned actuation extensions.
- SSH CLI support.
- Broader host-service extraction.
- Topology deletion dry-run previews.
- Comprehensive documentation reorganization.

## Verification Results

Purpose: Record the evidence produced during this review.

Post-P0-fix verification:

- Topology editor maintained regression: two passed, zero failed.
- Cross-surface maintained regression: one passed, zero failed.
- Focused schema, topology, cross-surface, parser, and PoC tests: 102 passed.
- Canonical topology validation: passed.
- Primary no-write synchronization validation: passed.
- Full Python source suite: 19 failures remain, all in previously identified P1
  UI, CLI, and discovery expectations; no P0 regression remains.

- Maintained local regression command:
  `python tools/can_nt/scripts/run_regressions.py --suite local --no-history`.
- Maintained result: 7 passed and 3 failed.
- Full source command: `python -m pytest tools -q -p no:cacheprovider`.
- Full source result: 854 passed, 21 failed, one warning, and 24 subtests passed.
- Java unit tests passed through the maintained regression runner.
- Repository-wide collection found duplicate ignored recovery test modules that
  cause two import-file-mismatch collection errors.
- The connected roboRIO regression was not run.
- The specialized topology validator found two missing edge endpoints in the
  canonical configuration.
- The primary no-write synchronization validator reported success for the same
  malformed configuration.

## Smallest Path To RC

Purpose: Define the minimum ordered stabilization plan.

1. Freeze the release support envelope around REST robot control, UI and CLI,
   topology editing, and passive CAN reception. Remove live host CAN transmission
   from the release surface.
2. Repair `test_minimal_25_9`, converge topology validation, and make the primary
   validator reject dangling edge endpoints. Add the narrow regression.
3. Fix topology-editor key preservation and pass topology plus cross-surface
   round-trip regressions.
4. Reconcile UI and discovery tests with the approved runtime rules. De-scope
   discovery-first as experimental if it cannot be validated without expanding
   the stabilization scope.
5. Make verification clean-tree-safe, include the complete supported Python and
   Java test surface, and require a fully green local suite.
6. Run the connected non-motion suite and manually verify disconnect, session
   locking, stop latch, disabled behavior, and E-stop behavior.
7. Correct supported transport documentation, Windows installation, launchers,
   release notes, and version identity.
8. Create the release-candidate tag only from a clean tree with every mandatory
   gate green.

## Tradeoffs

The plan deliberately avoids architectural cleanup that is not needed to make the
existing product reliable. It prioritizes safety-contract compliance, canonical
data integrity, operator save behavior, deterministic validation, and release
documentation.

Discovery-first behavior should remain in scope only if its current contract can
be validated with narrow fixes. Otherwise, labeling it experimental is safer than
expanding the release stabilization effort.

## Future Extensions

After release, the project can resume the proposed reverse-engineering features,
host service extraction, richer topology editing, CI automation, and broad
documentation consolidation listed in the Later section.
