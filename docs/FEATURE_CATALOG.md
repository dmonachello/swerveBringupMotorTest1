SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Feature Catalog

## Purpose

Provide one operator/developer-facing inventory of the user-visible features in this repo.

This document is organized by feature family and workflow, not by source file.

See also:

- [ROBOT_BASE_FUNCTIONALITY.md](./ROBOT_BASE_FUNCTIONALITY.md) for the robot-side execution engine that remains in code after config-driven cleanup.

## Surfaces

- **Robot runtime**: roboRIO-side bringup execution, tests, groups, device creation, reporting.
- **Bringup UI**: desktop Tk control surface for profile selection, reports, tests, live topology, and visibility.
- **Bridge CLI**: Cisco-style TCP CLI for robot control and local config authoring.
- **Topology editor**: Tk editor for `bringup_system.json` devices, topology, groups, and profile metadata.
- **CAN tool**: passive PC-side CANable listener and NetworkTables publisher.
- **Regression / validation tools**: host-side checks for config, topology, CLI, and cross-surface compatibility.

## How To Read This Catalog

Each feature entry includes:

- **Purpose**
- **Surface**
- **How to access**
- **When to use it**
- **Do not confuse with**
- **Dependencies**
- **Current limitations**

## Testing Features

### Staged Device Instantiation

- **Purpose:** create bringup devices incrementally instead of activating everything at once.
- **Surface:** robot runtime, Bringup UI, Bridge CLI.
- **How to access:**
  - UI: `Add Motor`
  - CLI: `instantiate next motor`
- **When to use it:** first hardware verification, one-motor-at-a-time bringup, partial robot wiring.
- **Do not confuse with:** `Add All Motors` / `instantiate all devices`.
- **Dependencies:** active profile selected on the robot.
- **Current limitations:** this path is motor-oriented, not a fully general â€œany device type one at a timeâ€ mechanism.

### Bulk Device Instantiation

- **Purpose:** instantiate the full active-profile device set quickly.
- **Surface:** robot runtime, Bringup UI, Bridge CLI.
- **How to access:**
  - UI: `Add All Motors`
  - CLI: `instantiate all devices`
- **When to use it:** after staged verification, when the hardware is already trusted.
- **Do not confuse with:** staged `instantiate next motor`.
- **Dependencies:** active profile selected on the robot.
- **Current limitations:** higher risk during early bringup because many devices become active at once.

### Selected Test Execution

- **Purpose:** run the currently selected scripted bringup test once.
- **Surface:** robot runtime, Bringup UI, Bridge CLI.
- **How to access:**
  - UI: test dropdown + `Run Selected`
  - CLI: `tests select "<name>"`, then `tests run`
- **When to use it:** repeatable scripted procedures, encoder checks, device actions, joystick-driven scripted tests.
- **Do not confuse with:** group bindings, which are live/manual and not scripted.
- **Dependencies:** robot connected, selected test loaded from config.
- **Current limitations:** only one active bringup test runs at a time.

### Run All Enabled Tests

- **Purpose:** execute the enabled test list in order.
- **Surface:** robot runtime, Bringup UI, Bridge CLI.
- **How to access:**
  - UI: `Run All`
  - CLI: `tests run-all`
- **When to use it:** repeatable smoke passes after the individual devices are already known-good.
- **Do not confuse with:** ad hoc manual control.
- **Dependencies:** enabled tests must exist and their required devices must be instantiated.
- **Current limitations:** not appropriate for early uncertain hardware bringup.

### Test Enable / Disable

- **Purpose:** include or exclude a test from run-all.
- **Surface:** robot runtime, Bringup UI, Bridge CLI.
- **How to access:**
  - UI: `Toggle Enabled`
  - CLI: `tests toggle`
- **When to use it:** keep a curated test subset active for the current robot state.
- **Do not confuse with:** group member enable/disable, which affects live manual group outputs.
- **Dependencies:** a selected test must exist.

### DSL Tests

- **Purpose:** define scripted, normalized bringup tests with commands, conditions, aborts, and explicit stop logic.
- **Surface:** robot runtime, Bridge CLI authoring, config files.
- **How to access:**
  - top-level `dslTests` in `bringup_system.json`
  - CLI `test` authoring/import/export/validate commands
- **When to use it:** automated or repeatable diagnostics, encoder-confirmed motions, button-gated procedures, safety-checked test flows.
- **Do not confuse with:** simple group analog bindings.
- **Dependencies:** required devices must be defined in the active profile and available at runtime.
- **Current limitations:** authoring and host-side discovery still split across embedded per-profile test sections and top-level `dslTests`.

### Joystick Test Type

- **Purpose:** simple authoring model for one input source driving a device list.
- **Surface:** config authoring, robot runtime.
- **How to access:** `type: joystick` entries in the authoring test model.
- **When to use it:** simple same-input same-device-class tests.
- **Do not confuse with:** composite DSL tests, which support explicit multi-device command scripting.
- **Dependencies:** controller input source and device list.
- **Current limitations:** too limited for split-stick multi-group control; use DSL composite or group bindings for that.

### Device Action Tests

- **Purpose:** run non-motor actions such as LED actions where supported.
- **Surface:** config authoring, robot runtime.
- **How to access:** `deviceAction` tests.
- **When to use it:** verify non-motor devices with command-like actions.
- **Do not confuse with:** motor output tests.

### Deadband Sweep Tests

- **Purpose:** characterize motion thresholds and deadband response.
- **Surface:** config authoring, robot runtime.
- **How to access:** `deadbandSweep` tests.
- **When to use it:** tuning motor thresholds or confirming encoder-based motion onset.
- **Do not confuse with:** manual joystick bringup.

## Manual Control Features

### Group Analog Bindings

- **Purpose:** connect one input to a whole device group for live manual control.
- **Surface:** robot runtime, Bridge CLI, config.
- **How to access:**
  - CLI config mode:
    - `group <name>`
    - `bind <input> analog`
- **When to use it:** staged motor bringup, joystick-driven vendor groups, quick ad hoc control.
- **Do not confuse with:** DSL joystick tests.
- **Dependencies:** robot connected; group members configured.
- **Current limitations:** disabled while a bringup test is running.

### Group Hold / Toggle / Jog Bindings

- **Purpose:** map button-like inputs to fixed-value outputs.
- **Surface:** robot runtime, Bridge CLI, config.
- **How to access:** `bind <input> <hold|toggle|jog-forward|jog-reverse> <value>`
- **When to use it:** temporary buttons, fixed-speed checks, simple manual actions.
- **Do not confuse with:** persistent controller axis bindings in `bringup_bindings.json`.

### Group Member Enable / Disable

- **Purpose:** control which devices inside a group actually respond.
- **Surface:** robot runtime, Bridge CLI, config.
- **How to access:** `member enable "<label>"`, `member disable "<label>"`, `member toggle "<label>"`
- **When to use it:** staged one-motor-at-a-time bringup while keeping the broader group binding intact.
- **Do not confuse with:** test enable/disable.
- **Dependencies:** device must already be a member of the group.

### Group Enable / Disable

- **Purpose:** turn an entire manual-control group on or off.
- **Surface:** robot runtime, Bridge CLI, config.
- **How to access:** `enable` / `disable` while inside `group <name>`
- **When to use it:** emergency stop of a manual-control path, fast suspend/resume of a vendor group.
- **Do not confuse with:** removing members or clearing bindings.

### Active Group

- **Purpose:** build a transient runtime-only selection of devices without editing permanent groups.
- **Surface:** robot runtime, Bridge CLI.
- **How to access:** `active add`, `active next`, `active show`
- **When to use it:** ad hoc runtime selection experiments.
- **Do not confuse with:** persistent profile groups in `bridgeConfig`.
- **Dependencies:** robot connected.
- **Current limitations:** active-group behavior is runtime/transient and not the same as profile-defined groups.

### Selected Device Mode

- **Purpose:** exclude one chosen device from group outputs.
- **Surface:** robot runtime, Bridge CLI, config/runtime state.
- **How to access:** `selected-device <label>`, `selected-mode on|off`
- **When to use it:** isolate one device from otherwise broad manual group control.
- **Do not confuse with:** disabling the device inside the group itself.

## Profile And Config Features

### Canonical Unified Config

- **Purpose:** store profiles, device registry, bridge config, topology, and DSL tests in one file.
- **Surface:** topology editor, CLI, robot runtime, validation tools.
- **How to access:** `src/main/deploy/bringup_system.json`.
- **When to use it:** nearly all configuration work.
- **Do not confuse with:** derived deploy copy.
- **Current limitations:** checked-in deploy copies may still be edited directly during active development, but canonical schema and shared-object rules still apply.

### Derived Deploy Config

- **Purpose:** provide the robot-side deploy copy of the unified config.
- **Surface:** robot runtime, validation/sync workflow.
- **How to access:** `src/main/deploy/bringup_system.json`
- **When to use it:** robot deploy/runtime consumption.
- **Do not confuse with:** canonical root copy for authoring.

### Profile Selection

- **Purpose:** switch the active robot configuration.
- **Surface:** robot runtime, Bringup UI, Bridge CLI, topology editor.
- **How to access:**
  - UI: profile dropdown, `Toggle Profile`
  - CLI: `profiles activate <name>` or profile commands
  - topology editor: load profile UI
- **When to use it:** swap robot hardware definitions without code surgery.

### Config Push

- **Purpose:** apply a local config to the robot over TCP without redeploying code.
- **Surface:** Bridge CLI.
- **How to access:** `profiles push <path> [--activate <profile>]`, `config push <path> [--activate <profile>]`
- **When to use it:** quick on-robot config iteration.
- **Do not confuse with:** saving local files only.
- **Dependencies:** robot TCP UI connection.
- **Current limitations:** applies in memory on the robot; not a disk persistence mechanism.

### Validation And Sync

- **Purpose:** validate canonical config and keep deploy artifacts in sync.
- **Surface:** host tooling.
- **How to access:** `python -m tools.validate_sync --warnings`
- **When to use it:** after any config, topology, test, or profile change.

## Group And Binding Features

### Persistent Profile Groups

- **Purpose:** store named device collections under each profile.
- **Surface:** topology editor, CLI, robot runtime, live topology.
- **How to access:** per-profile group metadata in `bringup_system.json`
- **When to use it:** recurring logical sets such as `krakens`, `neos`, `driveTrain`.
- **Current limitations:** members are label-based shared objects; runtime actions apply only to members whose object type supports the requested function.

### Show Groups

- **Purpose:** inspect groups, members, enabled state, and bindings.
- **Surface:** Bringup UI, Bridge CLI, live topology overlay.
- **How to access:** `show groups`, `show group <name>`, UI `Show Groups` overlay toggle.
- **When to use it:** verify manual-control setup and profile structure.

### Controller Axis Bindings

- **Purpose:** define named input aliases like `leftDrive` and `rightDrive`.
- **Surface:** robot runtime, CLI local binding tools, reports.
- **How to access:** `bringup_bindings.json`, CLI `bindings` commands, `printBindings`.
- **When to use it:** map physical controller inputs to named commands.
- **Do not confuse with:** group bindings, which consume these named inputs.

## Reporting And Diagnostics Features

### State Report

- **Purpose:** print current runtime state, active profile, device list, and selected test.
- **Surface:** robot runtime, Bringup UI, Bridge CLI.
- **How to access:** UI `State`, CLI `show status` and related report paths.

### Health Report

- **Purpose:** print local vendor API health, faults, temperatures, and current data.
- **Surface:** robot runtime, Bringup UI.
- **How to access:** UI `Health`
- **When to use it:** on-robot device health checks.
- **Do not confuse with:** PC CAN sniffer visibility.

### CAN Bus Report

- **Purpose:** print robot-local CAN/vendor API view.
- **Surface:** robot runtime, Bringup UI.
- **How to access:** UI `CAN Bus`
- **When to use it:** compare robot-local visibility to the passive sniffer view.

### NT Diagnostics Report

- **Purpose:** print PC-side CAN tool diagnostics published via NetworkTables.
- **Surface:** robot runtime, Bringup UI.
- **How to access:** UI `NT Diagnostics`
- **When to use it:** passive bus presence and age/count diagnostics.
- **Dependencies:** PC CAN tool running and connected.

### Inputs Report

- **Purpose:** show controller state and input binding interpretation.
- **Surface:** robot runtime, Bringup UI.
- **How to access:** UI `Inputs`
- **When to use it:** confirm joystick/button mappings and axis direction.

### Dump Report

- **Purpose:** print a broad full bringup report.
- **Surface:** robot runtime, Bringup UI.
- **How to access:** UI `Dump`
- **When to use it:** wide diagnostic snapshot.

### CANcoder Report

- **Purpose:** show encoder presence and readings for configured encoders.
- **Surface:** robot runtime, Bringup UI.
- **How to access:** UI `CANcoder`

### Bindings Report

- **Purpose:** print controller bindings and axis mappings.
- **Surface:** robot runtime, Bringup UI, Bridge CLI.
- **How to access:** UI `Bindings`, CLI `show bindings`

## Live Topology And Visibility Features

### Live Topology View

- **Purpose:** read-only runtime view of the active topology.
- **Surface:** Bringup UI.
- **How to access:** `Live Topology` tab.
- **When to use it:** compare authored topology to live presence, layout, and group overlays.

### Visibility View

- **Purpose:** show topology plus a visibility table by source/device.
- **Surface:** Bringup UI.
- **How to access:** `Visibility` tab.
- **When to use it:** inspect passive evidence by source.
- **Current limitations:** disconnected-source summary semantics still need cleanup in some cases.

### Read-Only Camera Controls In Live UI

- **Purpose:** zoom and pan in the UI without allowing edits.
- **Surface:** Bringup UI live topology views.
- **How to access:** zoom buttons, `Fit to Window`, middle-mouse pan.
- **Do not confuse with:** topology editor, which can move nodes.

### Group Overlays In Live UI

- **Purpose:** visualize `bridgeConfig` groups as solid outline boxes and labels.
- **Surface:** Bringup UI live topology views.
- **How to access:** `Show Groups` toggle.

## Topology Editor Features

### Profile Load / Save / Export

- **Purpose:** edit and persist topology-aware profile config.
- **Surface:** topology editor.
- **How to access:** file/profile menu and save commands.

### Device Registry Editing

- **Purpose:** add/edit/remove device definitions and profile membership.
- **Surface:** topology editor.
- **How to access:** node dialogs, details panel, list view, bulk edit.

### Topology Layout Editing

- **Purpose:** position devices, buses, CANnect nodes, and callouts.
- **Surface:** topology editor.
- **How to access:** drag nodes, resize bus segments, tidy/layout commands.

### CANnect / Inject Modeling

- **Purpose:** model CANnect Direct / Inject nodes, device links, Ethernet-style links, and port roles.
- **Surface:** topology editor, live topology view.
- **How to access:** edit menu actions and node dialogs.

### Callouts

- **Purpose:** attach explanatory labels to nodes or buses.
- **Surface:** topology editor.
- **How to access:** `Add Callout`, edit/remove callout actions.

### Group Authoring In Topology Editor

- **Purpose:** create and visualize CLI/runtime groups from the diagram.
- **Surface:** topology editor.
- **How to access:** `Groups` menu, group overlay interactions.
- **Current limitations:** group membership is label-based and may include devices plus infrastructure nodes.

### Viewport Controls

- **Purpose:** inspect large diagrams comfortably.
- **Surface:** topology editor.
- **How to access:** fit-to-window, scroll-wheel zoom, middle-mouse pan, zoom reset.
- **Current limitations:** plain click must not move viewport state; zoom and fit behavior are governed by the GUI interaction stability contract.

### GUI Interaction Stability Contract

- **Purpose:** keep click, drag, zoom, pan, redraw, and pane layout behavior stable and predictable.
- **Surface:** topology editor, Bringup UI.
- **How to access:** implemented as the governing behavior contract in `FEATURE_SPEC_GUI_INTERACTION_AND_VIEWPORT_STABILITY.md`.
- **When to use it:** any time GUI work changes viewport, selection, drag, splitter, redraw, or panel layout behavior.
- **Do not confuse with:** visual styling guidance; this is a screen-behavior contract.
- **Dependencies:** automated viewport/redraw checks plus manual GUI retest.

### Connection Filters

- **Purpose:** show/hide CAN, power, DIO, PWM, analog, and virtual links.
- **Surface:** topology editor, live topology view.
- **How to access:** connection filter controls.

### Validation Messaging

- **Purpose:** catch missing fields, invalid device definitions, topology issues, and stale metadata.
- **Surface:** topology editor, validation scripts.
- **How to access:** save-time validation, `validate_profiles.py`.

## Passive CAN Tool Features

### Read-Only CAN Sniffing

- **Purpose:** listen to CAN traffic via CANable without transmitting.
- **Surface:** PC CAN tool.
- **How to access:** `python -m tools.can_nt.can_nt_bridge ...`
- **Hard rule:** passive only; never transmits CAN.

### NetworkTables Publishing

- **Purpose:** publish passive diagnostics for robot/UI consumption.
- **Surface:** PC CAN tool.
- **How to access:** run `can_nt_bridge.py` with robot connectivity.

### Unknown Device Publishing

- **Purpose:** surface CAN traffic from devices not in the active profile.
- **Surface:** PC CAN tool.
- **How to access:** `--publish-unknown`

### Capture / PCAP / Wireshark Support

- **Purpose:** record CAN traffic for offline analysis.
- **Surface:** PC CAN tool.
- **How to access:** `--pcap`, `--pcap-pipe`

### Inventory / Diff Outputs

- **Purpose:** inventory API traffic and compare captures.
- **Surface:** PC CAN tool.
- **How to access:** inventory and diff command-line options.

## Validation And Regression Features

### Topology Regression Suite

- **Purpose:** keep topology editor, live topology, and profile contract behavior stable.
- **Surface:** host tooling.
- **How to access:** `python tools/can_nt/scripts/run_regressions.py --suite topology`

### Cross-Surface Regression Suite

- **Purpose:** prove topology-editor-produced config still works for other consumers.
- **Surface:** host tooling.
- **How to access:** `python tools/can_nt/scripts/run_regressions.py --suite cross-surface`

### Local Regression Bundle

- **Purpose:** run the common local checks across subsystems.
- **Surface:** host tooling.
- **How to access:** `python tools/can_nt/scripts/run_regressions.py --suite local`

### Schema / Sync Validation

- **Purpose:** validate config shape and keep derived artifacts updated.
- **Surface:** host tooling.
- **How to access:** `python -m tools.validate_sync --warnings`

## Common Confusions

### Group Binding vs DSL Test

- **Group binding:** live manual control path
- **DSL test:** scripted test program

### `instantiate next motor` vs group enable

- `instantiate next motor` creates devices in profile order
- group member `enable` decides which created devices respond
- enabled group members can force creation, so staged bringup requires disabling not-yet-approved members

### Single Config File

- shared host and roboRIO config file: `src/main/deploy/bringup_system.json`
- the current workflow uses one repo-owned config file rather than separate authoring and deploy copies

## Future Maintenance Rule

Any new user-visible capability should update:

- this catalog
- `docs/FEATURE_MATRIX.md`
- `docs/WORKFLOWS.md` when the capability changes how a task is performed
- `docs/FEATURE_SPEC_GUI_INTERACTION_AND_VIEWPORT_STABILITY.md` when the capability changes GUI screen behavior

