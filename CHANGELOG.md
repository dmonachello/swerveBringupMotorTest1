# Changelog

All notable user-facing changes are documented in this file.

## 2026-05-18

### Improved - 2026-05-18

- Fixed the V1 group-targeting regression normalization so saved
  `bridgeConfig.byProfile` comparisons stay stable when the active profile name
  comes from the loaded bringup config instead of a synthetic placeholder.
- Fixed schema-store test validation to fail soft when controller bindings are
  absent during topology-editor round-trip validation, preserving cross-surface
  compatibility for standalone bringup-system saves.
- Moved the `robot_2026_swerve` topology-editor and cross-surface regression
  paths onto regression-owned config fixtures so those tests no longer depend
  on the active local install copies under `data/` or `src/main/deploy/`.
- Cut host-side config ownership over to `src/main/deploy/` for
  `bringup_system.json` and `bringup_bindings.json`, removing the active
  dependency on `data/` paths in shared path resolution and default tool
  workflows.

## 2026-05-09

### Added - 2026-05-09

- Added a canonical root-level topology graph model under
  `topology.profiles.<profile>.nodes/edges`.
- Added topology node and edge validation for device references, endpoints,
  duplicate ports, and edge identity.
- Added topology regression coverage for malformed graph inputs and live
  topology filter behavior.

### Improved - 2026-05-09

- Upgraded the topology editor and live topology view to load the new graph
  model directly instead of relying on `diagram` neighbor metadata as the main
  truth.
- Added connection-type filters to the topology editor and live topology UI,
  including persisted filter state in topology view metadata.
- Updated CLI topology inspection to derive neighbor views from graph edges.
- Restored the checked-in bringup config to the root-level topology graph
  model and removed the regressed `diagram`-style topology persistence from the
  active config copies.
- Tightened profile/config validation around edge-based topology data and
  aligned the local CLI/config save paths to preserve the canonical topology
  graph shape.
- Fixed robot-side registry profile apply so pushed profile device labels are
  resolved consistently during activation.

## 2026-05-10

### Added - 2026-05-10

- Added standalone DIO limit switch runtime support so a DIO-backed limit
  switch can be instantiated as a real bringup device and referenced directly
  by DSL tests.

### Improved - 2026-05-10

- Generalized DSL test required-device handling away from motor-only
  assumptions so controller, sensor, and other non-motor dependencies are
  validated through the same device-instantiation gate.
- Updated robot-side test and UI reporting surfaces to use generic
  required-device semantics instead of special motor lists.

## 2026-05-12

### Added - 2026-05-12

- Added a new `robot_2026_swerve` profile with the 2026 swerve module device
  inventory for real-robot data gathering.
- Added a DSL device signal interface spec describing the direction toward a
  device-owned read/write signal contract and away from snapshot-backed DSL
  execution.
- Added a component model unification spec defining a shared canonical
  component/topology interpretation model for device versus infrastructure
  handling.

### Improved - 2026-05-12

- Fixed topology editor save/load persistence for CANnect Ethernet links, CAN
  bus links, and CANnect device links.
- Preserved CANnect node kind across save/reload so direct and inject nodes are
  restored as topology infrastructure rather than generic nodes.
- Fixed topology editor and shared topology parsing so infrastructure nodes stay
  out of runtime device registries while remaining visible in topology and live
  views.
- Fixed CANnect topology interpretation so Ethernet links remain between
  CANnect nodes and only the inject node retains a CAN backbone trunk link.
- Fixed topology power-link validation to allow PDH/PDP power links to motors
  and other non-DIO consumers while keeping CANnect Direct limited to low-power
  devices.
- Fixed topology editor profile load behavior to restore the last saved view
  without forcing an automatic fit-to-window reset.
- Fixed CAN device registry round-trip updates in the topology editor so power
  devices such as PDH keep their typed fields instead of degrading back to
  generic device entries.

## 2026-05-13

### Added - 2026-05-13

- Added an automated `cross-surface` regression suite that round-trips
  topology-editor output through shared profile validation, schema-store load,
  and CLI bringup-system consumers.

### Improved - 2026-05-13

- Fixed topology editor blank-space clicks to clear selection without undoing
  fit-to-window or shifting the current canvas view.
- Expanded topology regression coverage for viewport preservation, blank-space
  deselection, and fit-to-window interaction behavior.
- Made regression command baseline comparison treat `gradlew.bat` paths as
  checkout-local so Java regression runs do not drift across machines.

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
