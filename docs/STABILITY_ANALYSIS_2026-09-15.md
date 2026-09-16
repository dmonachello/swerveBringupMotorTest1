# Stability analysis

## Scope and evidence

This report examines the Python host applications, Java robot application, REST interface, full command-line interface, DSL, device lifecycle, CAN discovery, topology, configuration, user interfaces, robot communication, safety, shutdown, and regression tests.

Source code and executable tests are the primary evidence. Documents are not used as proof of runtime behavior. This was a read-only static analysis. No hardware or performance tests were run.

The source does not name separate applications UI1 and UI2. The two concrete Tk applications are [`BringupControlUI`](../tools/can_nt/bringup_ui.py#L2541) and [`TopologyEditor`](../tools/can_topology/can_top_editor.py#L796). This report treats them as the runtime UI and authoring UI.

## Overall assessment

The project has sound safety intent and substantial unit coverage, but it is not yet structurally resistant to regressions.

The strongest parts are:

- Robot disable transitions stop outputs and deactivate runtime state.
- Tests suppress group bindings while a DSL test is running.
- Manual control uses shared actionability gates.
- Configuration and topology have useful cross-surface regression coverage.
- Periodic telemetry limits the number of device reads per cycle.

The largest weaknesses are at subsystem boundaries:

1. REST lifecycle state can disagree with the robot command executor.
2. REST requests mutate robot state from HTTP worker threads while the robot loop accesses the same state.
3. DSL initialization can fail after applying an output without running cleanup.
4. Config push and config apply are not transactional.
5. UI polling and CAN processing have no time or backlog budgets suitable for a slower laptop.
6. Several objects represent "active," "instantiated," "present," and "in scope."

## A. System stability map

| Subsystem | Authoritative state | Duplicate or cache | Main vulnerability |
| --- | --- | --- | --- |
| Robot configuration | Static `BringupUtil` registry and profile state | Persisted JSON, selected profile, active profile, runtime catalog | Apply and persistence are non-atomic |
| Robot execution | `BringupCore` and `RobotLocalCommandExecutor` | REST command record and UI tracker | REST stop state does not stop execution |
| Device lifecycle | `ActivationManager` active session and live devices | `DeviceLifecycleRegistry`, `DeviceUnit.isCreated`, profile-active state | Several meanings of active and instantiated require reconciliation |
| DSL | Host compiler produces normalized payload; robot executes normalized payload | DSL source and `sourceHash` | Robot trusts normalized content without checking its source or schema |
| REST | `BringupRestServer` owns client and REST command records | Robot executor independently owns the running command | Session and execution lifecycles can diverge |
| Command-line interface | `BridgeCli` owns the host editing workspace; the robot owns runtime truth | Local payloads, schema store, models, dirty flags, profile fields, session caches, and provenance fields | Interactive timeouts can be accepted as success, and staged operations can leave host and robot state split |
| CAN observation | Passive discovery classifier and visibility provider | UI device snapshots and profile identity mapping | Unbounded frame queue and inferred identities |
| Topology | Saved topology and diagram data | Editor nodes, registry map and list, link arrays, root extras | Many mirrored mutable representations |
| Bringup Control | Current REST snapshots and local config session | Pending and last-known state fields | Blocking HTTP and command waits on the Tk thread |
| Control ownership | Running test, manual selection, enabled group bindings | Per-group activity flags and diagnostic watches | Overlapping groups can write the same device |
| Regression runner | Manifest-selected subprocess result | Stored baselines and history | No subprocess timeout or hung-child cleanup |

## B. State ownership map

### Defined, seen, required, and active

- **Defined** means that the loaded `BringupUtil` configuration contains a device definition and profile membership.
- **Seen** means that robot-local snapshots or host-side passive CAN traffic observed a device. These are independent observations.
- **Required** means that `DslNormalizedTest.devices` lists the device.
- **Instantiated** can mean `DeviceUnit.isCreated()`, `DeviceRuntimeState.isInstantiated()`, or a published lifecycle string that starts with `instantiated`.
- **Active** can mean that a profile, controlled lifecycle, device, group, test, or REST command is active.

The reconciliation code treats any of three sources as evidence that a device is instantiated: [`BringupRuntime.isLifecycleDeviceEffectivelyInstantiated`](../src/main/java/frc/robot/BringupRuntime.java#L1658). When the controlled lifecycle is active, its per-device state determines scope: [`BringupRuntime.resolveLifecycleDeviceInScope`](../src/main/java/frc/robot/BringupRuntime.java#L1695).

A failure between a controlled lifecycle update and a published lifecycle refresh can give different consumers different answers.

### Configuration

The robot's operational authority is the in-memory static state in `BringupUtil`. Disk is the restart authority. The host file is the authoring authority. Runtime groups are recreated after registry upload.

REST `/config/current` reconstructs selected robot fields instead of returning the original file. The reconstruction includes devices, profiles, DSL, and bridge configuration. It omits topology and diagram metadata: [`BringupUtil.buildCurrentProfilesJson`](../src/main/java/frc/robot/BringupUtil.java#L907). The host download function writes that reconstruction directly to disk: [`download_current_config`](../tools/can_nt/config_transfer_service.py#L292).

### REST commands

`BringupRestServer` owns client identity, REST command IDs, output chunks, and REST terminal status. `RobotLocalCommandExecutor` independently owns the actual active robot command in its `active` field: [`RobotLocalCommandExecutor`](../src/main/java/frc/robot/commands/local/RobotLocalCommandExecutor.java#L17).

`BridgeSession` owns the host's pending-request tracking and cached snapshots: [`BridgeSession.__init__`](../tools/can_nt/bridge_session.py#L270). A REST record that says `STOPPED` does not prove that robot execution stopped.

### Topology

Persisted JSON is the durable authority. The editor also holds `_nodes`, `_device_registry`, `_device_registry_list`, separate link arrays, `_root_extras`, pending deletions, and dirty flags: [`TopologyEditor.__init__`](../tools/can_topology/can_top_editor.py#L849).

Save reconciles the nodes into the registry immediately before serialization: [`TopologyEditor._save_loaded_profile`](../tools/can_topology/can_top_editor.py#L2165). Tests cover restart round trips, deletion, rename, cross-profile references, and group membership. The remaining concern is structural complexity, not one confirmed current deletion bug.

### Command-line interface

The CLI is both a local configuration editor and a robot-control client. Those roles have different authorities. The host workspace is authoritative for unsaved authoring changes. Files are the durable host authority. The robot is authoritative for selected profile, lifecycle, test execution, groups, and outputs after a command is acknowledged. `BridgeCli` holds all three views in one object: [`BridgeCli.__init__`](../tools/can_nt/bridge_cli.py#L2288).

| Review question | Source-first finding |
| --- | --- |
| 1. What owns authoritative state? | `BridgeCli` owns local editing state. `BridgeSession` owns host transport state. The robot owns runtime state. The CLI does not have one authority that covers both editing and execution: [`BridgeCli.__init__`](../tools/can_nt/bridge_cli.py#L2288), [`BridgeSession`](../tools/can_nt/bridge_session.py#L247). |
| 2. What is duplicated or cached? | The CLI keeps `_local_root_payload`, `_local_config`, `ConfigSchemaStore`, `TestAuthoringModel`, bindings, CAN mappings, five dirty flags, host and robot profile names, active-group members, last test ID, and save/push provenance: [`BridgeCli.__init__`](../tools/can_nt/bridge_cli.py#L2343). `BridgeSession` separately caches connection, handshake, pending commands, runtime, tests, protocol, and general state: [`BridgeSession.__init__`](../tools/can_nt/bridge_session.py#L258). |
| 3. What crosses subsystem boundaries? | Commands assume EBNF validation, parser normalization, AST dispatch, REST command names, JSON payload shapes, terminal `OUT` events, robot status text, and profile names all agree. The parser does load and validate against the EBNF: [`BridgeCliParser.__init__`](../tools/can_nt/bridge_cli_parser.py#L219), [`BridgeCliParser.parse`](../tools/can_nt/bridge_cli_parser.py#L394). However, `_execute_line` handles question, active, test-run, targeting, and reset commands before the normal parse facade: [`BridgeCli._execute_line`](../tools/can_nt/bridge_cli.py#L5194). |
| 4. What happens after partial failure? | Config replacement can clear robot groups, install local state, then send plan commands one at a time: [`BridgeCli._apply_config_plan`](../tools/can_nt/bridge_cli.py#L10403). Group deletion discards each wait result and returns success after the loop: [`BridgeCli._clear_existing_groups`](../tools/can_nt/bridge_cli.py#L11170). A failed later command leaves a prefix applied, with no rollback. |
| 5. What happens when communication is interrupted? | `_wait_for_seq` returns `None` on timeout. `_event_failed` treats that as failure only in batch mode; interactive mode returns `False`: [`BridgeCli._wait_for_seq`](../tools/can_nt/bridge_cli.py#L11269), [`BridgeCli._event_failed`](../tools/can_nt/bridge_cli.py#L11302). A ping failure queues error events but does not clear `_connected`: [`BridgeSession._handle_ping_command`](../tools/can_nt/bridge_session.py#L522). The CLI can therefore retain stale connected state. |
| 6. What lacks regression protection? | The tests cover a broad command surface, profile synchronization, lifecycle payloads, DSL authoring, topology, and output verbosity. They do not directly cover `run_batch`, interactive timeout-as-success behavior, active-command error propagation, keepalive and foreground concurrency, stale connection state after ping failure, or staged config interruption. The timeout test asserts only whether a warning is printed: [`BridgeCliTimeoutOutputTests`](../tools/can_nt/tests/test_bridge_cli_timeout_output.py#L47). |
| 7. What depends on ordering or timing? | Batch stops at the first failed `StatusResult`: [`BridgeCli.run_batch`](../tools/can_nt/bridge_cli.py#L2596). Command completion polls on a wall-clock deadline: [`wait_for_command_event`](../tools/can_nt/command_workflow_service.py#L103). Test waiting adds nested command polls and sleeps: [`BridgeCli._wait_for_test_run_completion`](../tools/can_nt/bridge_cli.py#L5504). Connect-time profile discovery also uses bounded retries: [`BridgeCli._query_robot_selected_profile_after_connect`](../tools/can_nt/bridge_cli.py#L12804). |
| 8. Which invariants matter? | A successful status must mean a terminal robot result was received. Local profile and push provenance must change only after confirmed robot success. Dirty flags must match the payload. One sequence must map to one request. Shutdown must release the control session. The first two are not enforced on interactive timeout: [`BridgeCli._event_failed`](../tools/can_nt/bridge_cli.py#L11302), [`BridgeCli._profiles_push`](../tools/can_nt/bridge_cli.py#L10858). |
| 9. Where can components disagree? | `_set_active_profile` writes both `_robot_selected_profile` and `_groups_profile` after a timeout is treated as non-failure: [`BridgeCli._set_active_profile`](../tools/can_nt/bridge_cli.py#L3296). The provenance payload reports `robot-vs-pushed=YES` whenever any last-pushed hash exists; it does not compare a robot hash: [`BridgeCli._build_provenance_payload`](../tools/can_nt/bridge_cli.py#L2881). Host, displayed provenance, and robot can disagree. |
| 10. What is assumed but not enforced? | Interactive and batch execution assume different timeout meanings. The `active add`, `active next`, and `active show` shortcuts ignore the returned event and always return normal status: [`BridgeCli._handle_active_command`](../tools/can_nt/bridge_cli.py#L5715). Startup assumes the canonical config and default bindings are appropriate and loads them automatically in both modes: [`BridgeCli.run_interactive`](../tools/can_nt/bridge_cli.py#L2433), [`BridgeCli.run_batch`](../tools/can_nt/bridge_cli.py#L2596). |

Verified CLI strengths include EBNF-backed parsing, fail-fast batch execution, dirty-state blocking before config push, explicit session disconnect in both interactive and batch `finally` paths, validation before saves, and atomic temp-and-backup writes for standalone bridge config: [`BridgeCli._shutdown_session`](../tools/can_nt/bridge_cli.py#L2629), [`BridgeCli._atomic_write_json`](../tools/can_nt/bridge_cli.py#L10668).

## C. Important system invariants

1. A REST command marked stopped must not own robot execution or outputs. The code does not enforce this invariant.
2. Only one writer may control a motor during a cycle. Tests and manual ownership are gated, but overlapping enabled groups can violate this invariant.
3. Leaving Disabled must stop outputs and require explicit reactivation. [`Robot.disabledInit`](../src/main/java/frc/robot/Robot.java#L166) enforces this invariant.
4. Group bindings must not overwrite an active test. [`BridgeGroupManager.applyBindings`](../src/main/java/frc/robot/BridgeGroupManager.java#L585) exits while a test is running.
5. A DSL test that fails to start must leave writable signals safe. Partial initialization does not guarantee this invariant.
6. DSL source, normalized payload, `sourceHash`, and schema version must describe the same program. The host validator checks source equivalence and the hash: [`validate_entry`](../tools/common/robot_test_dsl/validator.py#L111). The robot loader does not.
7. A successful configuration response must mean that memory, disk, selected profile, and runtime groups agree. Current operations can commit only a prefix of these changes.
8. A failed lifecycle close must not strand the state machine in `DEACTIVATING` or `FAILED`. Current cleanup lacks `finally` protection.
9. A ready candidate must be present and actionable. Active-group candidate selection currently checks only that a lifecycle record exists: [`isDeviceEligibleForActiveGroup`](../src/main/java/frc/robot/BridgeUiCommandHandler.java#L2334).
10. UI and CAN loops need bounded work per iteration. Neither the Tk REST polling path nor CAN backlog drain has a time budget.
11. Host-observed CAN identity must not become robot-local proof of operability.
12. A downloaded config must preserve every field required for a host round trip. `/config/current` violates this invariant for topology and diagram data.
13. CLI success must require a terminal success response, independent of interactive or batch mode. Current timeout handling violates this invariant.
14. CLI provenance must compare observed robot state with the pushed artifact before claiming a match. Current provenance derives that claim only from the existence of a prior push hash.

## D. Failure boundaries

### REST stop and communication loss

**Risk: Critical**

Disconnect, explicit stop, reset, and session timeout only mutate the REST `CommandRecord` and clear `activeCommand`: [`handleCommandStop`](../src/main/java/frc/robot/rest/BringupRestServer.java#L748), [`stopActiveCommandLocked`](../src/main/java/frc/robot/rest/BringupRestServer.java#L1001), and [`expireSessionIfNeeded`](../src/main/java/frc/robot/rest/BringupRestServer.java#L1053).

The callback interface provides execution and status queries, but no cancel callback. `Robot` forwards only those operations: [`Robot.RestCallbacksImpl`](../src/main/java/frc/robot/Robot.java#L590).

Verified result: REST can report that a running command stopped while the robot executor remains active.

Hypothesis: Whether physical output persists depends on the command and later robot-loop behavior.

### REST and robot-loop concurrency

**Risk: Critical**

The REST server uses a fixed HTTP thread pool: [`BringupRestServer.start`](../src/main/java/frc/robot/rest/BringupRestServer.java#L242). It invokes robot callbacks on those threads: [`runImmediateCommandLocked`](../src/main/java/frc/robot/rest/BringupRestServer.java#L960).

`RobotLocalCommandExecutor.submit`, `step`, and the `active` field are not synchronized: [`RobotLocalCommandExecutor.submit`](../src/main/java/frc/robot/commands/local/RobotLocalCommandExecutor.java#L24), [`RobotLocalCommandExecutor.step`](../src/main/java/frc/robot/commands/local/RobotLocalCommandExecutor.java#L73).

The 20 ms thread steps commands, advances tests, and applies bindings: [`Robot.teleopPeriodic`](../src/main/java/frc/robot/Robot.java#L213). REST runtime reads also build snapshots from live state and hardware: [`BridgeUiCommandHandler.buildRuntimeStateJson`](../src/main/java/frc/robot/BridgeUiCommandHandler.java#L3647).

Verified result: HTTP and robot threads can access robot state and vendor devices without one serialization boundary.

### REST safety-latch mismatch

**Risk: Critical**

`executeRestCommand` passes `false` as the legacy transport flag: [`BridgeUiCommandHandler.executeRestCommand`](../src/main/java/frc/robot/BridgeUiCommandHandler.java#L1770). The stop-latch check and pre-execution stop behavior run only when that flag is true: [`BridgeUiIngressPolicy.validateIngress`](../src/main/java/frc/robot/BridgeUiIngressPolicy.java#L142), [`BridgeUiIngressPolicy.applyPreExecution`](../src/main/java/frc/robot/BridgeUiIngressPolicy.java#L177).

Verified result: REST start commands do not receive the stop-latch protection applied to the legacy transport path.

### DSL partial initialization

**Risk: Critical**

DSL startup applies safe values, performs init clears, and executes init sets in sequence. If a later operation fails, `start` returns without calling `stop`: [`DslBringupTest.start`](../src/main/java/frc/robot/tests/dsl/DslBringupTest.java#L125), [`DslBringupTest.applySets`](../src/main/java/frc/robot/tests/dsl/DslBringupTest.java#L381).

`BringupCore` treats `start == false` as blocked and does not finalize the DSL test: [`BringupCore.runSelectedBringupTest`](../src/main/java/frc/robot/BringupCore.java#L834). Runtime exceptions also skip the global stop for DSL tests.

Verified result: An earlier successful init write can remain active after a later initialization failure.

### Robot configuration apply

**Risk: Critical**

`applyRegistryPayload` replaces profiles, device registry, tests, bridge configuration, DSL, instance state, and generation before optional activation: [`BringupUtil.applyRegistryPayload`](../src/main/java/frc/robot/BringupUtil.java#L2538).

Post-apply verification and persistence happen later with no rollback: [`BringupUtil.verifyRegistryApply`](../src/main/java/frc/robot/BringupUtil.java#L2585). Persistence writes directly to the target file: [`BringupUtil.persistRegistryJson`](../src/main/java/frc/robot/BringupUtil.java#L2626).

Verified result: The robot can return a failure response after its runtime state has changed.

### Host configuration push

**Risk: Critical**

Host push applies the registry, selects the profile, deletes all robot groups, computes the import plan, and imports commands one at a time: [`push_config`](../tools/can_nt/config_transfer_service.py#L196).

A plan-generation failure occurs after group deletion. A network failure during import leaves a prefix of groups installed. The operation has no rollback or final reconciliation.

### CLI timeout and status handling

**Risk: High**

The shared wait returns no event when the terminal response does not arrive. In batch mode, `_event_failed(None, ...)` reports failure. In interactive mode, it reports success: [`BridgeCli._event_failed`](../tools/can_nt/bridge_cli.py#L11302).

This result feeds profile selection, runtime activation, lifecycle changes, test execution, config push, and general robot commands. For example, profile selection updates both the cached robot profile and host editing profile after the wait: [`BridgeCli._set_active_profile`](../tools/can_nt/bridge_cli.py#L3312). Registry push records local state and last-push provenance after the same check: [`BridgeCli._profiles_push`](../tools/can_nt/bridge_cli.py#L10910).

Verified result: an interactive terminal-response timeout can be returned as normal and can advance local state as if the robot confirmed the operation.

### CLI command-path status bypass

**Risk: High**

`active show`, `active add`, and `active next` send a command, wait, discard the event, and always return normal status: [`BridgeCli._handle_active_command`](../tools/can_nt/bridge_cli.py#L5715). This bypass is stronger than the general interactive timeout rule because it also masks an explicit error event and applies in batch mode.

Verified result: these active-group shortcuts can produce a zero exit status after send failure, timeout, or robot rejection.

### CLI session liveness and concurrency

**Risk: Medium, partly hypothetical**

The foreground command path and the keepalive thread share one `BridgeSession`. The keepalive sends synchronous ping requests: [`BridgeCli._keepalive_loop`](../tools/can_nt/bridge_cli.py#L2548). `BridgeSession` mutates its sequence, event queue, pending-command map, connection fields, and caches without locks: [`BridgeSession._next_seq`](../tools/can_nt/bridge_session.py#L490), [`BridgeSession.poll_events`](../tools/can_nt/bridge_session.py#L422).

A failed ping does not mark the session disconnected. Shutdown gives the keepalive thread a bounded join and proceeds to disconnect even if the thread is still alive: [`BridgeCli._stop_keepalive`](../tools/can_nt/bridge_cli.py#L2535), [`BridgeCli._shutdown_session`](../tools/can_nt/bridge_cli.py#L2629).

The command wait checks its deadline before calling `poll_events`, but that call can perform a 3.5-second HTTP request for every pending command: [`wait_for_command_event`](../tools/can_nt/command_workflow_service.py#L121), [`BridgeSession._poll_pending_commands`](../tools/can_nt/bridge_session.py#L622). The configured wait is therefore not a hard elapsed-time bound. CLI mode can also run the CAN sniffer in another daemon thread: [`run_bridge`](../tools/can_nt/can_nt_bridge.py#L1675).

Verified result: liveness is a cached flag rather than a current reachability guarantee, shared session mutation has no explicit serialization, and a slow REST request can overrun the CLI's nominal command deadline.

Hypothesis: on a slow laptop or delayed network, CAN processing, keepalive, and foreground HTTP calls can compete, reorder compatibility events, or race with disconnect. A concurrency stress test is required to establish whether this causes user-visible failures under CPython.

### CLI startup and recovery state

**Risk: Medium**

Interactive and batch modes automatically load the canonical profiles, bindings, and mappings before executing user commands: [`BridgeCli._auto_merge_default_profiles`](../tools/can_nt/bridge_cli.py#L2907), [`BridgeCli._auto_load_default_sources`](../tools/can_nt/bridge_cli.py#L2932). Invalid or partial profile data is sanitized and installed into the workspace, then recovery and dirty state are set: [`BridgeCli._load_profiles_from_path`](../tools/can_nt/bridge_cli.py#L2944).

Verified result: a batch script's initial state depends on files at canonical paths, and a damaged file can become a salvaged in-memory workspace rather than causing startup to stop. Batch remains fail-fast for command results, but startup loading is not represented as a batch command result.

### Lifecycle cleanup

**Risk: High**

Activation rollback and normal deactivation call `LiveDevice.close()` without individual exception handling or a `finally` cleanup path: [`ActivationManager.performDeactivate`](../src/main/java/frc/robot/diag/lifecycle/activation/ActivationManager.java#L236), [`ActivationManager.rollback`](../src/main/java/frc/robot/diag/lifecycle/activation/ActivationManager.java#L263).

A close exception can leave some devices closed and others live. It can also strand the session, device maps, lifecycle state, and per-device runtime state.

### Active-scope replacement

**Risk: High**

Selected-test activation deactivates the current session before it validates new test membership: [`BringupRuntime.activateSelectedTestDevices`](../src/main/java/frc/robot/BringupRuntime.java#L295). If selection or activation fails, the previous scope is gone.

Profile activation has a similar boundary. Profile activation can succeed before controlled active-group activation fails: [`BridgeUiProfileCommands.executeProfileActivate`](../src/main/java/frc/robot/BridgeUiProfileCommands.java#L224).

### Active-next transition

**Risk: High**

`activeNext` stops, deactivates, and removes the current primary device before it finds or adds a replacement: [`BridgeUiCommandHandler.applyActiveNext`](../src/main/java/frc/robot/BridgeUiCommandHandler.java#L2202).

If no candidate exists or the add fails, the previous membership is not restored. Candidate eligibility requires only a lifecycle row, not current presence or actionability.

### Control ownership across groups

**Risk: High**

`addMember` accepts `forceMove` but does not use it or remove the device from other groups: [`BridgeGroupManager.addMember`](../src/main/java/frc/robot/BridgeGroupManager.java#L404).

`applyBindings` iterates every enabled group and writes every enabled member: [`BridgeGroupManager.applyBindings`](../src/main/java/frc/robot/BridgeGroupManager.java#L594).

Verified result: Two enabled binding groups can write the same device in group iteration order. The later write wins. No explicit ownership rule chooses between binding groups.

### Manual group partial success

**Risk: High**

Manual group duty skips unknown or ineligible members and returns success if at least one member accepts the write: [`applyManualGroupDuty`](../src/main/java/frc/robot/BridgeUiCommandHandler.java#L3021).

The caller reports `Manual group duty applied` without listing skipped members: [`BridgeUiGroupCommands`](../src/main/java/frc/robot/BridgeUiGroupCommands.java#L433).

Verified result: The host and robot can disagree about whether the whole group received the requested command.

### File persistence

**Risk: High**

Shared JSON writes overwrite the destination directly: [`write_json`](../tools/common/json_io.py#L28). When canonical and deploy paths differ, the service writes them in sequence: [`ConfigLifecycleService.sync_profiles_payload`](../tools/common/config_lifecycle/service.py#L101).

A crash, power loss, full disk, or second-write failure can leave truncated or divergent files.

### Robot configuration download

**Risk: High**

The robot current-config builder omits topology and diagram fields. Download overwrites the requested host path with this reduced representation. Runtime data survives, but host topology-authoring state can be lost.

### Bringup Control on a slow laptop

**Risk: High**

The Tk poll callback performs a connection probe, session fetch, runtime fetch, and test-state fetch in sequence on the UI thread: [`BringupControlUI._poll_runtime_ui_state`](../tools/can_nt/bringup_ui.py#L15409).

Runtime and test calls each allow a 3.5-second timeout: [`BridgeSession.fetch_runtime_state`](../tools/can_nt/bridge_session.py#L448). The UI schedules the next callback only after the current poll finishes: [`BringupControlUI._poll_runtime_ui_state`](../tools/can_nt/bringup_ui.py#L15720).

`_send_and_wait` also sleeps on the UI thread while it processes only idle redraw tasks: [`BringupControlUI._send_and_wait`](../tools/can_nt/bringup_ui.py#L4917).

A partially reachable robot can freeze the UI for several seconds. A slower laptop increases the risk of stale state and repeated operator actions.

### Passive CAN backlog

**Risk: High**

Every source reader appends to an unbounded `queue.Queue`: [`run_bridge`](../tools/can_nt/can_nt_bridge.py#L961), [`_source_reader`](../tools/can_nt/can_nt_bridge.py#L977).

The consumer drains until the queue is empty before it ticks visibility or publishes updates: [`_run_sniffer`](../tools/can_nt/can_nt_bridge.py#L1491).

If processing falls behind, memory can grow without limit. Visibility and UI publication can also starve while the consumer drains old frames.

### Robot 20 ms timing

**Risk: High, partly hypothetical**

The periodic path limits reads by count, not elapsed time. Every 250 ms while enabled, it can perform a full device snapshot in the robot thread: [`BringupRuntime.sampleTelemetry`](../src/main/java/frc/robot/BringupRuntime.java#L735), [`BringupRuntime.refreshDeviceLifecycleInternal`](../src/main/java/frc/robot/BringupRuntime.java#L1522).

Verified result: Vendor reads occur in the robot thread and only a count budget exists.

Hypothesis: One slow vendor call can overrun the 20 ms loop. Runtime measurement is required.

### Regression-runner cleanup

**Risk: Medium**

The regression runner starts subprocesses without a timeout in verbose and captured modes: [`execute_command`](../tools/can_nt/scripts/lib/regression_framework.py#L274).

A hung Gradle test, UI test, serial operation, or connected regression can block the sequential suite. The runner has no child-process-tree cleanup policy.

## E. Regression-test coverage gaps

The local manifest covers Java, DSL, CLI, topology, cross-surface behavior, and policy guards: [`local` suite](../tests/regression/fixtures/regression_runner_manifest.json#L197). Connected robot validation is a separate non-motion suite: [`robot-non-motion` suite](../tests/regression/fixtures/regression_runner_manifest.json#L209).

The following boundaries lack direct regression protection:

1. REST disconnect, timeout, reset, and `/stop` cancellation of the actual robot command.
2. Concurrent REST activity and 20 ms command-executor steps.
3. REST start behavior while the safety latch is active.
4. DSL initialization where one write succeeds and a later write fails.
5. `LiveDevice.close()` throwing during rollback or deactivation.
6. Robot config failure after in-memory mutation, post-apply verification failure, or persistence failure.
7. Host push interruption after each stage. The current config-transfer test covers the successful sequence: [`ConfigTransferServiceTests`](../tools/can_nt/tests/test_config_transfer_service.py#L117).
8. `/config/current` round trips that preserve topology, diagram, and unknown root fields.
9. Two enabled binding groups that command the same device.
10. Manual group control with both successful and failed members.
11. CAN producer throughput above consumer capacity.
12. Tk responsiveness under slow and partially failing REST requests.
13. Robot-loop deadlines under slow vendor reads. Current tests check round-robin count selection, not elapsed time: [`BringupRuntimeLifecycleSelectionTest`](../src/test/java/frc/robot/BringupRuntimeLifecycleSelectionTest.java#L550).
14. Regression subprocess timeout and descendant cleanup.
15. Cross-language DSL rejection of future schema versions or mismatched source and normalized data. Java registry tests currently cover profile-name selection: [`BringupTestRegistryTest`](../src/test/java/frc/robot/tests/BringupTestRegistryTest.java#L7).
16. Interactive and batch equivalence for missing terminal `OUT` events.
17. Error and timeout propagation for `active show`, `active add`, and `active next`.
18. `run_batch` behavior with startup salvage, automatic source loading, early command failure, and guaranteed disconnect.
19. Keepalive overlap with foreground command sends, event polling, reconnect, and disconnect.
20. Stale `BridgeSession.is_connected()` after ping and command transport failures.
21. CLI config replacement interrupted during each group deletion and each plan command.
22. Provenance output against a robot whose config changed after the last push.
23. CLI command latency and timeout overrun while the CAN sniffer is saturated on the older laptop.

## F. Sources of nondeterministic behavior

Verified sources include:

- HTTP worker threads and the robot periodic thread access shared robot state independently.
- CAN source scheduling determines queue order between sources.
- CAN visibility depends on arrival timestamps and stale windows.
- Lifecycle snapshots rotate through eligible devices, so freshness depends on round-robin position.
- UI behavior depends on the duration and order of synchronous REST calls.
- CLI outcome depends on interactive versus batch mode when a terminal response is missing.
- CLI keepalive timing can overlap foreground HTTP requests through one unsynchronized session object.
- CLI waits use wall-clock time, so system-clock adjustment can lengthen or shorten deadlines.
- Overlapping group outputs depend on group iteration order.
- Active-group candidate selection depends on a mutable cursor and profile ordering.
- Source shutdown uses two-second joins but does not verify that each daemon thread stopped: [`_stop_source_threads`](../tools/can_nt/can_nt_bridge.py#L1112).

The following hypotheses need runtime evidence:

- Vendor API calls sometimes overrun the robot loop.
- CAN backlog grows during full-rate capture on the older laptop.
- Tk freezes lead operators to repeat actions because state appears stale.
- Unknown-manufacturer traffic produces false identities in field captures.

## G. Cross-subsystem failure propagation

| Origin | Propagation | Result |
| --- | --- | --- |
| Laptop or network pause | UI blocks, REST session expires, REST record stops only | UI reports disconnection while robot execution can remain active |
| Config push interruption | Registry applies, profile selects, groups delete, import fails | Host file, robot registry, and runtime groups describe different systems |
| CLI terminal-response loss | Interactive wait returns no event, failure check accepts it | Local profile, provenance, or command status can advance without robot confirmation |
| CLI active shortcut failure | Send, timeout, or robot error is discarded | Batch can continue or exit successfully after an active-group operation failed |
| CLI keepalive overlap | Background ping and foreground command share mutable session state | Liveness, sequence, events, and disconnect order can become timing-dependent |
| Robot persistence failure | In-memory registry changes, disk write fails | Current process uses new state; reboot loads old or damaged state |
| DSL init failure | Earlier motor set succeeds, later init operation fails, no finalization runs | Test reports blocked while an output can remain applied |
| Lifecycle close exception | Deactivation aborts during cleanup | Some devices close, others remain live, and the session state is stranded |
| Overlapping groups | Two controller bindings target one device | Output depends on group ordering instead of ownership |
| Slow host | CAN queue grows and UI REST calls block | Visibility becomes stale and memory use grows |
| REST worker concurrency | HTTP command or read overlaps robot periodic work | Commands, groups, lifecycle, snapshots, or vendor calls can race |
| Config download | Robot reconstruction omits topology and overwrites a host file | Runtime data survives but topology-authoring state is lost |
| False CAN identity | Non-CTRE or non-REV canonical identity is accepted as definite | An unexpected device can influence host visibility and operator decisions |

The last row separates fact from hypothesis. The classifier requires defining traffic for CTRE and REV, but it accepts another manufacturer when canonical identity decoding succeeds: [`classify_observed_traffic`](../tools/passive_discovery_poc/traffic_classification.py#L531). The available real-capture assertion covers one capture with expected Spark and Falcon devices: [`PassiveDiscoveryAnalysisTests`](../tools/passive_discovery_poc/tests/test_analysis.py#L51). The false-positive rate in field traffic is unknown.

## H. Ranked stability risks

### Critical

- REST stop, disconnect, and timeout do not cancel robot execution.
- REST HTTP workers access robot runtime concurrently with the 20 ms loop.
- REST commands bypass stop-latch start gating.
- DSL startup can leave an earlier output active after partial initialization failure.
- Robot registry apply can fail after it commits in-memory changes.
- Host config push is a non-transactional distributed update.

### High

- Lifecycle close exceptions can strand sessions and hardware state.
- Selected-test and profile activation replace state without rollback.
- `activeNext` destroys current membership before it proves a replacement.
- Multiple binding groups can write the same device without arbitration.
- Manual group commands report success after partial application.
- Config files are overwritten non-atomically.
- `/config/current` drops topology and diagram metadata.
- Bringup Control performs blocking REST work on the Tk thread.
- Passive CAN uses an unbounded queue and unbounded drain pass.
- Robot telemetry has count budgets but no time budget.
- Robot execution does not check DSL schema or source-hash consistency.
- Interactive CLI timeouts can be accepted as successful robot operations.
- Active-group CLI shortcuts discard transport and robot failures.

### Medium

- Lifecycle truth is distributed across profile state, controlled session state, device wrappers, snapshots, and a derived registry.
- Topology Editor maintains many mutable copies of the same configuration.
- Active-group ready selection proves only that a lifecycle record exists.
- Regression subprocesses have no timeout or cleanup policy.
- CLI keepalive and foreground commands mutate one session without an explicit lock.
- CLI connection state can remain true after a failed keepalive request.
- CLI startup salvage and automatic source loading affect batch initial state outside the batch result stream.
- Reload deactivates and clears current runtime state before it proves that replacement configuration can load: [`BringupUtil.reloadProfilesFromJson`](../src/main/java/frc/robot/BringupUtil.java#L1779).
- Invalid startup configuration stops robot initialization instead of leaving a reduced diagnostic mode: [`BringupUtil.loadProfilesFromJson`](../src/main/java/frc/robot/BringupUtil.java#L1711).

### Low

- Normal cache-staleness windows in host display models.
- Session IDs, timestamps, and diagnostic ordering differences.
- Best-effort daemon-thread shutdown when the CAN driver returns promptly.
- Historical naming drift that does not affect executable behavior.

## Verified findings and hypotheses

The source verifies these findings:

- REST cancellation does not reach the executor.
- REST and robot periodic work run on different threads.
- REST bypasses the stop-latch condition.
- DSL partial-init cleanup is absent.
- Configuration operations lack rollback.
- File writes are non-atomic.
- Group overlap permits multiple writers.
- UI HTTP calls are synchronous.
- CAN queues and drains are unbounded.
- The robot does not check DSL schema and hash consistency.
- Robot config download omits topology.
- The listed regression gaps exist.
- Interactive and batch CLI timeout semantics differ.
- Active-group CLI shortcuts always return normal after waiting.
- CLI provenance can claim a robot match without reading a robot hash.

These hypotheses still need runtime evidence:

- A motor has remained active after REST loss or DSL partial startup.
- Vendor reads cause measured 20 ms robot-loop overruns.
- CAN backlog grows on the older laptop at expected bus load.
- Bringup Control misses its UI update target on the older laptop.
- Field traffic produces false-positive CAN identities.
- Concurrent REST and robot-loop access has caused a concrete state exception.

## First investigations

Investigate these problems first:

1. REST stop, disconnect, and timeout behavior against actual executor and motor state.
2. REST HTTP-thread access to robot runtime and vendor devices.
3. REST stop-latch bypass.
4. DSL partial-initialization cleanup.
5. Interactive CLI timeout handling for profile, lifecycle, test, and config commands.
6. CLI active-group shortcut error and exit-status propagation.
7. Robot registry rollback and interrupted host config push after each stage.
8. CLI keepalive, reconnect, foreground command, and shutdown concurrency on the older laptop.
9. Bringup Control responsiveness and CAN queue latency on the older laptop.
10. Robot-loop duration during full snapshots and vendor reads.

These problems have the clearest paths to unsafe output, loss of operator trust, host and robot disagreement, or failures that appear only on slower hardware.
