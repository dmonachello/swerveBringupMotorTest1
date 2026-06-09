# Host Software Architecture

## Purpose

Explain the structure of the PC-side software in this repo so a developer can quickly answer two questions:

- what are the big host-side chunks of functionality
- how those chunks work together at runtime

This document is intentionally host-focused. It describes the Python tooling that runs on the Driver Station or development PC, not the roboRIO internals.

## Scope

Purpose: define what this document covers.

This document covers:

- the host-side CLI
- the Bringup Control UI
- the passive CAN and NetworkTables bridge
- shared Python service/domain modules
- topology and visibility support
- test authoring and DSL support

This document does not try to fully document:

- the robot-side Java architecture
- every individual command or parser rule
- every JSON field in every config file

## Big Picture

Purpose: describe the major host-side subsystems in one place.

The host software is not one single app. It is a set of cooperating Python surfaces and shared modules:

1. `tools/can_nt/can_nt_bridge.py`
   The runtime host process. It can listen to CAN through CANable, publish diagnostics to NetworkTables, capture PCAP/PCAPNG, monitor console output, and optionally host the CLI or launch the UI workflow around the robot connection.
2. `tools/can_nt/bridge_cli.py`
   The main command-line operator surface. It owns the Cisco-style CLI experience, command parsing, local config editing, config validation, and many host-side workflows.
3. `tools/can_nt/bringup_ui.py`
   The main desktop operator surface. It provides Tk-based controls for runtime activation, test execution, log viewing, topology viewing, and a small number of host-local actions such as DSL import and validation.
4. `tools/can_nt/bridge_session.py`
   The shared robot transport layer. It owns the REST session, handshake, command send/poll lifecycle, and log polling used by both CLI and UI.
5. `tools/can_nt/bridge_ops.py`
   The shared host operation layer for common robot-backed actions and local config helpers. CLI and UI are supposed to call this instead of each inventing their own command payloads.
6. `tools/common/`
   Shared host-side domain and service modules. This is where the newer layering work lives: config lifecycle semantics, workflow services, test-domain helpers, DSL compiler/validator logic, topology parsing/render helpers, and shared utilities.
7. `tools/can_nt/visibility_provider.py`
   The in-process visibility model. It turns observed CAN traffic from one or more sources into a host-side visibility snapshot used by UI and CLI surfaces.

### How The Host Apps Are Launched

Purpose: tie the big chunks above to the actual command-line entrypoints.

There are three practical host app entrypoints a developer usually runs:

1. Bridge CLI
   This is not a separate executable. It is a mode of the CAN/NT host app.

   Common launch commands:

   ```cmd
   tools\can_nt\run_can_nt.cmd --cli
   python tools\can_nt\can_nt_bridge.py --cli --rio 172.22.11.2
   python -m tools.can_nt.can_nt_bridge --cli --rio 172.22.11.2
   ```

   Relationship to the big picture:

   - launches the `can_nt_bridge.py` host process
   - exposes the `bridge_cli.py` operator surface
   - uses `bridge_session.py` and `bridge_ops.py` for robot-facing actions
   - may also run the passive CAN/NT bridge functions unless launched with flags that narrow scope

2. Bringup Control UI
   This is also a mode of the CAN/NT host app, not a separate standalone launcher in normal use.

   Common launch commands:

   ```cmd
   tools\can_nt\run_can_nt.cmd --ui
   python tools\can_nt\can_nt_bridge.py --ui --rio 172.22.11.2
   python -m tools.can_nt.can_nt_bridge --ui --rio 172.22.11.2
   ```

   Relationship to the big picture:

   - launches the `can_nt_bridge.py` host process
   - opens the `bringup_ui.py` desktop surface
   - uses the same shared `bridge_session.py` transport and `bridge_ops.py` operations as the CLI
   - embeds the Live Topology read-only view rather than launching topology as a separate runtime app

3. CAN Topology Editor
   This is a separate host app under `tools/can_topology/`.

   Common launch commands:

   ```cmd
   python tools\can_topology\can_top_editor.py
   python -m tools.can_topology.can_top_editor
   ```

   Relationship to the big picture:

   - launches the topology editor app, not the CAN/NT bridge host process
   - is used for offline config and topology authoring
   - shares topology/config concepts with the UI, but it is a separate edit-oriented surface
   - the Bringup Control UI Live Topology tab reuses read-only topology view logic, while the full editor lives in `tools/can_topology/can_top_editor.py`

Important distinction:

- the Bringup Control UI and Bridge CLI are two surfaces on top of the `can_nt_bridge.py` host process
- the topology editor is a separate app focused on offline authoring
- the UI Live Topology tab is not the topology editor; it is a read-only runtime-facing view embedded in the UI

## Mental Model

Purpose: give the shortest useful model for how the host side actually works.

The host side has three jobs:

- talk to the robot safely
- manage and inspect local config and test definitions
- observe the system from the outside through CAN, NetworkTables, logs, and runtime snapshots

Those jobs are split into two kinds of code:

- presentation surfaces: CLI and UI
- shared service/domain code: REST session, shared operations, config lifecycle, workflow guidance, test semantics, DSL compiler/validator, visibility, topology helpers

The current codebase is partially layered, not fully layered.

That means:

- some important semantics already live in shared modules
- the CLI and UI still contain a lot of orchestration and product logic themselves
- the host architecture direction is to keep moving shared meaning out of the surfaces and into reusable services

## Main Chunks

### 1. Runtime Host Process

Purpose: own the long-running PC-side process that connects external data sources to the rest of the system.

Primary file:

- [tools/can_nt/can_nt_bridge.py](/abs/path/tools/can_nt/can_nt_bridge.py)

What it does:

- opens the CANable SLCAN connection
- reads CAN traffic passively
- classifies and summarizes observed traffic
- publishes diagnostics to NetworkTables under `bringup/diag/...`
- optionally writes PCAP or PCAPNG capture output
- optionally runs console monitoring
- can expose the CLI workflow in the same host process

Important supporting modules:

- [tools/can_nt/can_analyzer.py](/abs/path/tools/can_nt/can_analyzer.py)
- [tools/can_nt/can_nt_publish.py](/abs/path/tools/can_nt/can_nt_publish.py)
- [tools/can_nt/can_nt_client.py](/abs/path/tools/can_nt/can_nt_client.py)
- [tools/can_nt/can_reporting.py](/abs/path/tools/can_nt/can_reporting.py)
- [tools/can_nt/can_pcap.py](/abs/path/tools/can_nt/can_pcap.py)
- [tools/can_nt/can_console_monitor.py](/abs/path/tools/can_nt/can_console_monitor.py)
- [tools/can_nt/can_profiles.py](/abs/path/tools/can_nt/can_profiles.py)

Key architectural point:

This process is the host-side observer and publisher. It is the place where passive CAN evidence becomes host-visible diagnostics, summaries, and capture artifacts.

### 2. Robot Command Transport

Purpose: provide one shared way for host surfaces to talk to the robot runtime.

Primary file:

- [tools/can_nt/bridge_session.py](/abs/path/tools/can_nt/bridge_session.py)

What it does:

- connects to the robot REST command server
- owns client/session identity
- performs handshake and reconnect behavior
- sends commands
- polls command status and output
- polls logs
- emits parsed ACK/OUT-style events for callers

Why it matters:

- CLI and UI share the same robot transport contract
- session ownership and half-duplex behavior live here instead of being reimplemented everywhere
- the host side can change presentation behavior without changing the transport contract

Key architectural point:

`BridgeSession` is the boundary between host operator tools and robot runtime command execution.

### 3. Shared Robot-Facing Operations

Purpose: centralize common host operations that sit above transport and below presentation.

Primary file:

- [tools/can_nt/bridge_ops.py](/abs/path/tools/can_nt/bridge_ops.py)

What it does:

- wraps common robot-backed commands such as connect, push, runtime activate, test selection, and command send
- performs some local config validation and local payload shaping
- provides shared helpers that both CLI and UI can call

Why it exists:

- the CLI and UI need many of the same actions
- command construction and response handling should not be duplicated blindly in each surface

Key architectural point:

This layer is the shared host-side action library, but it is not yet the complete product workflow layer. Some workflow meaning still lives higher up in `bridge_cli.py` and `bringup_ui.py`.

### 4. Command-Line Surface

Purpose: provide the most complete host-side operator and editing surface.

Primary file:

- [tools/can_nt/bridge_cli.py](/abs/path/tools/can_nt/bridge_cli.py)

What it owns in practice:

- interactive and batch command execution
- command parsing and AST execution
- local config editing workflows
- test and DSL-oriented local authoring workflows
- config validation and save/load flows
- some runtime workflows through the shared session and ops layers

Related parser/grammar files:

- [tools/can_nt/bridge_cli_parser.py](/abs/path/tools/can_nt/bridge_cli_parser.py)
- [tools/can_nt/bridge_cli_ast.py](/abs/path/tools/can_nt/bridge_cli_ast.py)
- [tools/can_nt/bridge_cli_ebnf.txt](/abs/path/tools/can_nt/bridge_cli_ebnf.txt)

Key architectural point:

The CLI is both a presentation layer and a large orchestration layer. It is currently one of the biggest host-side architectural centers of gravity.

### 5. Desktop UI Surface

Purpose: provide a Windows-friendly operator surface for runtime control and observation.

Primary file:

- [tools/can_nt/bringup_ui.py](/abs/path/tools/can_nt/bringup_ui.py)

What it owns in practice:

- connection controls and session state display
- runtime activate/deactivate controls
- push/download config actions
- test selection and execution controls
- output/log panes
- live topology and live runtime overlays
- visibility views
- a few host-local workflow actions such as `Import DSL Test` and `Validate DSL Tests`

Supporting files:

- [tools/can_nt/host_ui_actions.py](/abs/path/tools/can_nt/host_ui_actions.py)
- [tools/can_nt/bridge_cmd_tracker.py](/abs/path/tools/can_nt/bridge_cmd_tracker.py)

Key architectural point:

The UI is mainly a runtime interaction and observation surface. It is not a general config editor. Its host-local write behavior is narrow and intentional.

Launch relationship:

- normally started through `can_nt_bridge.py --ui`
- commonly launched via `tools\can_nt\run_can_nt.cmd --ui`
- contains the embedded Live Topology view, not the separate topology editor

### 6. Shared Config Lifecycle Services

Purpose: own host-side meaning about where config lives and how shared config copies are managed.

Primary files:

- [tools/common/config_lifecycle/service.py](/abs/path/tools/common/config_lifecycle/service.py)
- [tools/common/paths.py](/abs/path/tools/common/paths.py)

What this layer does:

- resolves canonical and deploy config paths
- reports config source entries for display
- loads profile payloads
- stamps schema/version/hash fields
- synchronizes canonical and deploy copies with shared semantics

Key architectural point:

This is one of the clearer examples of the host-side layering direction: shared config lifecycle policy should live here, not be redefined differently by each surface.

### 7. Shared Workflow Services

Purpose: turn operator intent into explicit host-side readiness and sequencing rules.

Primary file:

- [tools/common/workflows/workflow01_service.py](/abs/path/tools/common/workflows/workflow01_service.py)

What it does:

- evaluates whether Workflow 01 style bring-up is blocked or ready
- explains blocking reasons
- proposes next steps

Key architectural point:

This is not a command runner. It is workflow policy. It exists so workflow guidance becomes code-owned instead of only living in docs or operator habit.

### 8. Shared Test and DSL Domain

Purpose: own host-side semantics for test discovery, authoring, compilation, and validation.

Primary areas:

- [tools/common/tests_domain/semantics.py](/abs/path/tools/common/tests_domain/semantics.py)
- [tools/common/test_authoring/__init__.py](/abs/path/tools/common/test_authoring/__init__.py)
- [tools/common/robot_test_dsl/__init__.py](/abs/path/tools/common/robot_test_dsl/__init__.py)

What lives here:

- test inventory and selection semantics
- shared in-memory test authoring models
- serializer and validator logic for authored tests
- line-oriented DSL parser/compiler
- normalized DSL store serialization
- DSL validation against profile devices and supported signals

Key architectural point:

The host side does not treat DSL as only a UI or CLI feature. DSL is a shared domain with compiler and validator code that presentation surfaces call into.

### 9. Topology and Visibility Support

Purpose: provide shared host-side models for read-only structural and live-observation views.

Primary files:

- [tools/can_nt/visibility_provider.py](/abs/path/tools/can_nt/visibility_provider.py)
- [tools/common/topology_parse.py](/abs/path/tools/common/topology_parse.py)
- [tools/common/topology_draw.py](/abs/path/tools/common/topology_draw.py)
- [tools/common/topology_render.py](/abs/path/tools/common/topology_render.py)

What this layer does:

- tracks per-source and per-device visibility state
- merges expected devices with observed devices
- computes host-side visibility snapshots for UI and CLI use
- parses topology/config payloads
- draws shared topology shapes and overlays

Key architectural point:

This layer is read-oriented. It helps the host explain what the system looks like and what is visible, but it is not the general config-authoring layer.

Launch relationship:

- the read-only live topology view is embedded inside the Bringup Control UI
- the separate editable topology app is launched via `python tools\can_topology\can_top_editor.py`

## Host Data Flow

### Local Config Flow

Purpose: show how config moves on the host side before the robot uses it.

Typical flow:

1. A host surface loads or edits local config.
2. Shared config lifecycle code resolves canonical and deploy file paths.
3. Shared validators or test/DSL modules inspect the local payload.
4. The host saves or syncs the updated payload.
5. A later push action sends config to the robot runtime.

Important distinction:

- local host config is not the same thing as active robot runtime state
- selecting a profile locally is not the same thing as activating that profile on the robot

### Runtime Command Flow

Purpose: show how a button click or CLI command reaches the robot.

Typical flow:

1. UI or CLI decides to run an action.
2. The surface calls shared ops or session code.
3. `BridgeSession` sends REST commands to the robot.
4. The robot accepts, rejects, or finishes the command.
5. The host surface renders ACK/OUT text, runtime state, or follow-up results.

This is the control path.

### Observation Flow

Purpose: show how host-side evidence becomes visible to operators.

There are several observation inputs:

- passive CAN from CANable
- NetworkTables state and diagnostics
- robot REST runtime state snapshots
- robot console/log output
- local config/topology files

These inputs feed:

- CLI reports
- UI output panes
- live topology overlays
- visibility views
- capture artifacts such as PCAP and inventory JSON

This is the evidence path.

## What Is Shared vs Surface-Specific

Purpose: make the current architectural shape explicit.

Shared today:

- REST command transport
- common robot-backed operations
- config lifecycle semantics
- workflow readiness service
- test-domain selection semantics
- DSL compiler/validator
- topology parsing and rendering helpers
- visibility provider

Still surface-heavy today:

- a lot of CLI orchestration and command semantics
- a lot of UI orchestration and view-state management
- some config/test workflow sequencing
- some output formatting and interaction policy

Practical takeaway:

The codebase is already moving toward layered host-side ownership, but the CLI and UI are still larger and more responsible than the long-term target.

## Typical Workflows

### Runtime Bringup

Purpose: show the main host-side runtime workflow.

- load or select local config
- connect to the robot
- complete UI or CLI session handshake
- activate runtime on the selected profile
- run a focused test
- observe logs, runtime state, and topology overlays
- capture extra evidence if results are ambiguous

### Local DSL Authoring

Purpose: show the main host-side DSL workflow.

- edit a `.dsl` source file outside the UI
- import the DSL into local config through CLI or the narrow UI host action
- validate the local DSL store
- inspect normalized output when needed
- push config and run the test through robot-facing runtime controls

### Passive CAN Observation

Purpose: show the main host-side passive diagnostics workflow.

- open CANable
- observe frames passively
- classify device visibility and frame activity
- publish NT diagnostics
- optionally write PCAP or inventory outputs
- optionally feed visibility and live operator surfaces

## Why The Code Feels Large

Purpose: explain the practical reason the host side can feel harder to read than the robot side.

The host layer is doing several jobs at once:

- operator presentation
- local editing and validation
- remote robot control
- passive observation and capture
- compatibility across CLI, UI, JSON reports, and generated artifacts

That creates large files in a few places, especially:

- [tools/can_nt/bridge_cli.py](/abs/path/tools/can_nt/bridge_cli.py)
- [tools/can_nt/bringup_ui.py](/abs/path/tools/can_nt/bringup_ui.py)
- [tools/can_nt/can_nt_bridge.py](/abs/path/tools/can_nt/can_nt_bridge.py)

The important thing is not to think of those files as one feature each. They are umbrella entrypoints that sit on top of smaller shared layers.

## Recommended Reading Order

Purpose: give a practical path for understanding the host side without reading everything at once.

Read in this order:

1. [docs/ARCHITECTURE.md](/abs/path/docs/ARCHITECTURE.md)
2. [docs/HOST_SOFTWARE_ARCHITECTURE.md](/abs/path/docs/HOST_SOFTWARE_ARCHITECTURE.md)
3. [tools/can_nt/bridge_session.py](/abs/path/tools/can_nt/bridge_session.py)
4. [tools/can_nt/bridge_ops.py](/abs/path/tools/can_nt/bridge_ops.py)
5. [tools/common/config_lifecycle/service.py](/abs/path/tools/common/config_lifecycle/service.py)
6. [tools/common/workflows/workflow01_service.py](/abs/path/tools/common/workflows/workflow01_service.py)
7. [tools/common/robot_test_dsl/__init__.py](/abs/path/tools/common/robot_test_dsl/__init__.py)
8. [tools/can_nt/visibility_provider.py](/abs/path/tools/can_nt/visibility_provider.py)
9. [tools/can_nt/bridge_cli.py](/abs/path/tools/can_nt/bridge_cli.py)
10. [tools/can_nt/bringup_ui.py](/abs/path/tools/can_nt/bringup_ui.py)
11. [tools/can_nt/can_nt_bridge.py](/abs/path/tools/can_nt/can_nt_bridge.py)

This order goes from stable shared contracts toward the larger surface entrypoints.

## Tradeoffs

Purpose: acknowledge the current host-side design costs.

- The host side has better shared transport and domain code than it used to, but major surfaces are still large.
- The CLI is still both a presentation layer and a substantial orchestration layer.
- The UI is mainly runtime-focused and intentionally not a full config editor, which keeps scope down but means some workflows remain split.
- Shared services exist for config lifecycle, workflow readiness, and DSL/test semantics, but not every operator workflow is owned end-to-end by shared application services yet.

## Future Extensions

Purpose: note the likely architectural direction without changing current behavior.

- keep moving workflow semantics out of CLI/UI and into shared application services
- keep narrowing direct command construction inside presentation layers
- keep shared topology and visibility composition paths common across surfaces
- expand host-side docs with deeper follow-on guides for config lifecycle, runtime command flow, and DSL internals

## Layered Architecture Approach

Purpose: explain the intended host-side layering model and how to think about new code placement.

The host software is easiest to reason about when viewed as a layered system rather than a collection of large entrypoint files.

The practical layered model is:

1. transport and integration layer
2. shared domain and service layer
3. workflow or application layer
4. presentation layer

### 1. Transport And Integration Layer

Purpose: isolate external protocols, file IO boundaries, and raw integrations.

Examples in this repo:

- `bridge_session.py` for REST command transport
- CANable and CAN parsing modules under `tools/can_nt/`
- NetworkTables publishing/client code
- JSON file IO and path resolution helpers
- capture/logging adapters such as PCAP output and console monitoring

What belongs here:

- protocol details
- retry and timeout mechanics
- raw payload fetch/publish logic
- file read/write boundaries

What should not belong here:

- operator workflow decisions
- test semantics
- config policy beyond basic transport or IO needs

### 2. Shared Domain And Service Layer

Purpose: own reusable product meaning that should be shared across CLI, UI, and other host surfaces.

Examples in this repo:

- config lifecycle services in `tools/common/config_lifecycle/`
- workflow readiness service in `tools/common/workflows/`
- test-domain semantics in `tools/common/tests_domain/`
- DSL compiler/validator in `tools/common/robot_test_dsl/`
- shared topology parsing/render helpers in `tools/common/`
- shared visibility model in `visibility_provider.py`

What belongs here:

- config lifecycle rules
- test and DSL semantics
- topology interpretation rules
- reusable validation logic
- reusable normalized models

What should not belong here:

- Tk widget behavior
- CLI prompt behavior
- one-off button wiring
- view-specific formatting where no shared contract exists

### 3. Workflow Or Application Layer

Purpose: coordinate domain actions into supported operator workflows.

This is the layer that answers questions like:

- what has to happen before a runtime test can run
- what order should config validation, save, push, activate, and execute follow
- what should be blocked, warned, or suggested next

Examples in this repo today:

- `Workflow01Service` is a real start in this direction
- parts of `bridge_ops.py` also act like shared application actions

But this layer is still incomplete.

A lot of workflow meaning still lives inside:

- `bridge_cli.py`
- `bringup_ui.py`

That is one of the main reasons those files still feel large.

### 4. Presentation Layer

Purpose: provide operator-facing surfaces without owning the deeper shared meaning.

Examples in this repo:

- `bridge_cli.py`
- `bringup_ui.py`
- the topology editor app under `tools/can_topology/`

What belongs here:

- command entry and display
- button wiring
- dialogs
- text formatting for a specific surface
- surface-specific selection state

What should not dominate here:

- duplicate config lifecycle rules
- duplicate test/DSL semantics
- duplicate robot command construction
- workflow policy that should be shared across surfaces

### Design Intent

Purpose: state the architectural direction plainly.

The design intent is:

- integrations should be swappable without rewriting product meaning
- product meaning should be shared across surfaces
- workflows should be code-owned, not only doc-owned
- UI and CLI should become thinner over time

That means when adding new behavior, the preferred question is not:

- which big file should I put this in

The preferred questions are:

- is this transport logic
- is this shared domain meaning
- is this workflow sequencing
- is this only presentation behavior

### Current Reality

Purpose: describe where the codebase is relative to the target layering model.

The host side is not fully cleanly layered yet.

Current reality:

- the transport layer is reasonably explicit
- the shared domain/service layer is real and growing
- the workflow layer exists in a limited form
- the presentation layers still carry too much orchestration

So the right mental model is:

- treat the layered architecture as the design direction
- treat the existing large entrypoint files as partially layered implementations still being thinned over time

### Practical Rule For Future Changes

Purpose: give a concrete placement rule for new host-side work.

When adding or changing host-side behavior:

- put protocol and IO details in transport/integration modules
- put reusable semantics in `tools/common` or another clearly shared service module
- put multi-step operator flow rules in workflow or application services
- keep CLI and UI focused on invoking shared behavior and presenting results

If the same meaning would have to be implemented twice for CLI and UI, it probably belongs below the presentation layer.

## Bottom Line

Purpose: give one short summary to carry forward.

The host software has five practical centers of gravity:

- the passive CAN and diagnostics process
- the shared robot REST session
- the shared host operation helpers
- the two operator surfaces: CLI and UI
- the shared `tools/common` domain and service modules

If you understand those chunks and the difference between control paths and observation paths, the rest of the host code becomes much easier to place.
