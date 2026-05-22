SPEC_STATUS: RESEARCH_ONLY

# Feature Spec: Operator Visibility and Failure Explanations

## Summary

Purpose: Make configuration, runtime control, and failure causes visible enough that operators can understand what is active, what is saved, what is blocked, and what to do next.

This spec defines a usability-first hardening pass for operator surfaces, starting with the CLI as the canonical lowest-level surface. The immediate goal is not broad new functionality. The goal is to remove invisible state, ambiguous ownership, silent failure, and hard-to-trace blocked behavior.

## Problem Statement

Purpose: Describe the current operator pain clearly.

Real robot testing exposed several usability and safety gaps:

- local config edits are easy to lose because saved versus in-memory state is unclear
- config push behavior is not obvious or staged clearly
- bind behavior is difficult to verify and difficult to explain when inactive
- joystick and command ownership conflicts are mostly invisible
- group and device enable state is hard to reason about
- instantiated versus configured versus active devices are not shown clearly
- `add next` is deterministic but opaque
- DSL tests are powerful but awkward to inspect and edit from the CLI
- some failures are silent, generic, or require code knowledge to explain

The result is that operators cannot reliably answer these questions:

- What is loaded locally?
- What is dirty and unsaved?
- What config is active on the robot?
- Which devices are instantiated and eligible?
- Which bindings are active right now?
- Who owns a physical control?
- Why did a command or test not run?

## Goals

Purpose: Define the outcomes this pass must deliver.

- Make hidden state visible before changing semantics.
- Make failures explicit, staged, and actionable.
- Keep the CLI as the complete lowest-level control surface.
- Expose enough runtime and config state that operators do not need code knowledge to debug bringup failures.
- Preserve current safety direction, especially test-owned actuation and Driver Station emergency behavior.
- Keep changes additive and reversible.

## Non-Goals

Purpose: Bound this pass so it stays focused.

- broad new product features
- disabling or bypassing Driver Station emergency behavior
- replacing the CLI with a new UI
- changing passive CAN tool rules
- sweeping architecture rewrites

## Design Principles

Purpose: State the rules that govern usability changes.

- No invisible mutation: commands that change state must make the new state visible.
- No silent blocking: blocked actions must report the blocking reason.
- No false confidence: when runtime data is unavailable, surfaces must say it is unavailable.
- One question, one command: common operator questions should have direct inspection commands.
- Host and robot context must remain distinct and explicitly labeled.
- Shared contracts must be owned centrally when multiple surfaces present the same state.

## Scope

Purpose: Define the intended change area.

Primary scope:

- Bridge CLI behavior and help
- robot show/status surfaces that support CLI inspection
- shared host-side workflow and save/push behavior
- documentation for operator workflows and failure interpretation
- regression coverage for a minimum bringup path

Secondary scope:

- button-driven or mouse-driven surfaces may adopt the same visibility contract later
- robot-side runtime state may need additive fields so CLI inspection can explain blocked or inactive behavior

## Terminology

Purpose: Keep the spec precise.

- Host context: local CLI editing state and local loaded files.
- Robot context: runtime state on the roboRIO reached through TCP commands.
- Dirty state: local in-memory changes not yet persisted to disk.
- Binding: an explicit mapping from one input signal to one output target signal.
- Control owner: the active command path that currently consumes a physical control.
- Observer: a path that may inspect a control or signal without consuming it.
- Instantiated device: a configured device that has been created in the runtime vendor/device layer.
- Enabled device: a device that is permitted to participate in output-producing flows.
- Active binding: a binding that fully resolves and is currently allowed to drive its target.

## Core Questions

Purpose: Define the operator questions the system must answer directly.

The operator surface must answer:

- What files and profiles are loaded locally?
- What has changed and not been saved?
- What was last saved locally?
- What was last pushed to the robot?
- Which config or profile is active on the robot?
- What is active right now at runtime?
- Which devices are configured, instantiated, enabled, and blocked?
- Which groups are enabled and which members are skipped?
- Which signals are present and what values are they carrying?
- Which bindings resolve, and why are others inactive?
- Which control currently owns `controller.axis` or `controller.button`?
- Why did a test, bind, push, or run request fail?

## Functional Requirements

### 1. Dirty Config Tracking

Purpose: Make unsaved local state obvious and recoverable.

Requirements:

- Any command that mutates local config must mark the affected workspace state dirty.
- The CLI prompt must visibly indicate dirty state.
  - Example: `bridge*#`
- Add `show dirty`.
- `show dirty` must report:
  - which sections are dirty
  - what source file each section maps to
  - a short summary of unsaved changes when available
- Add `save` as an obvious default persistence command for current workspace sources.
- Bare `save` must succeed only when every dirty section already has a known source path.
- If any dirty section lacks a known source path, `save` must fail with direct fix text identifying the missing destination.
- Add `revert` to discard unsaved in-memory changes and restore the last loaded or saved disk state.
- On `exit`, the CLI must warn when dirty state exists.
- All config writes must be atomic.
- Save must create a timestamped backup before replacement.
- `push config` must refuse when relevant local config is dirty by default.
- The normal operator path is save to disk first, then push.
- An explicit override may exist for advanced use, but it must be visibly exceptional.
  - Example: `--force-dirty`

### 2. Clear Config Push Workflow

Purpose: Make robot config application staged and inspectable.

Requirements:

- Provide one obvious command path for applying local config to the robot:
  - `push config`
- The push workflow must report each stage explicitly:
  - local config source resolved
  - schema validation passed or failed
  - semantic validation passed or failed
  - config sent to robot
  - robot accepted or rejected config
  - post-apply hash, CRC, or version check passed or failed
  - active robot profile or config identity
- Failure at any stage must stop the workflow and report the failed stage.
- Text and JSON output must expose the same stage model.
- No stage may silently fail and still report overall success.
- The operator must be able to inspect:
  - last local save identity
  - last robot push identity
  - whether current local state matches the last pushed robot-applied state

### 2A. Save and Push Provenance

Purpose: Make saved and pushed state traceable across local and robot contexts.

Requirements:

- The operator surface must expose provenance for local save state and robot push state.
- Add or extend inspection output so the operator can see:
  - last modified timestamp for current in-memory local state
  - last saved path
  - last saved timestamp
  - last saved hash or version identity
  - last pushed path or logical source
  - last pushed timestamp
  - last pushed hash or version identity
  - last robot-accepted hash, CRC, or version identity when available
  - whether current local state matches last saved state
  - whether current local state matches last pushed state
  - whether robot active state matches last pushed state
- `show workspace` should include a compact provenance summary.
- A dedicated detailed command may also be provided.
  - Example: `show provenance`
- If the system cannot prove equivalence, it must report `unknown` rather than implying a match.
- `last modified` must remain distinct from `last saved` and `last pushed`.
- `push config` should only proceed normally from a saved-on-disk source, so the pushed artifact is explicit and inspectable.

### 3. Binding Observability Before Semantic Changes

Purpose: Make current bind state visible before changing bind behavior.

Requirements:

- Add direct inspection commands:
  - `show bindings`
  - `bind list`
  - `bind explain <binding>`
- Optional:
  - `bind test <binding>`
- Each binding report must include:
  - input device
  - input signal
  - output device or group
  - output signal
  - whether the input device resolves
  - whether the output target resolves
  - whether the input signal exists
  - whether the output signal exists
  - whether the output target is enabled
  - whether the binding is active, blocked, unresolved, or disabled
  - last input value if available
  - last output value if available
  - inactive reason when not active
- If runtime values are not currently available, the surface must report that explicitly.

### 3A. Active Runtime View

Purpose: Provide one direct answer to â€œwhat is active right now?â€

Requirements:

- Add a runtime-focused inspection command.
  - Preferred: `show active`
- `show active` must report, when available:
  - whether a test is currently running
  - active test name
  - active profile
  - active selected device or selected target mode
  - active bindings currently effective
  - active control owners
  - outputs currently being commanded
  - stop latch or safety block state
  - blocked or degraded runtime paths
- If no runtime publisher or robot connection is present, the command must say which data is unavailable.
- `show active` is not a replacement for detailed commands; it is the summary view that links operators to deeper inspection.

### 3B. Signal Inspection

Purpose: Make input and output signal state observable without guessing from behavior.

Requirements:

- Add direct signal inspection commands.
  - Preferred minimum:
    - `show signals`
    - `signal watch <signal>`
- `show signals` must list known relevant runtime signals with availability state.
- `signal watch <signal>` must show live or recent values when the runtime path supports it.
- Signal inspection must distinguish:
  - signal known but unavailable
  - signal unknown
  - signal available with current value
- Binding and test explanation surfaces should refer to the same signal names and availability rules.

### 4. Physical Control Ownership

Purpose: Prevent unsafe or ambiguous reuse of one physical control.

Requirements:

- Define and expose a control lease model.
- A physical control may have exactly one active command consumer.
- Controls may be observed by multiple diagnostic paths, but not consumed by multiple command paths.
- A command path must claim a control before using it for actuation or test-driving behavior.
- Binding or test activation must fail when the control is already claimed.
- Only safety stop or disable may silently preempt existing ownership.
- All other takeovers must be explicit.
  - Example: `--take-control`
- Add inspection and recovery commands:
  - `control show`
  - `control release <control>`
  - `control release --owner <owner>`
- Conflict output must identify:
  - current owner
  - requested owner
  - required next step
- Ownership information must be reused consistently in:
  - `control show`
  - `bind explain`
  - test preflight output
  - test start failure output
  - active runtime summary

### 5. Bind Semantics Clarification

Purpose: Remove ambiguity around what `bind` means.

Normative direction for this pass:

- `bind` creates an explicit binding entry.
- `bind` is persistent config, not an invisible runtime-only side effect.
- `bind` does not silently instantiate devices.
- `bind` does not silently enable devices or groups.
- `bind` does not silently override control ownership.
- `bind` must be visible through `show bindings`.
- `bind explain` must state why a binding is inactive.

The documentation must answer:

- whether `bind` requires `save`
- whether `bind` requires `push config`
- whether `bind` claims control ownership
- whether `bind` continuously maps input to output
- whether scaling and deadband apply
- whether the mapping runs on host or robot
- whether DSL tests may override it
- what happens if the target device or group is disabled

### 6. Device and Group Visibility

Purpose: Make configured, instantiated, enabled, and active state easy to inspect.

Requirements:

- Add or strengthen inspection commands:
  - `show devices`
  - `show devices active`
  - `show devices enabled`
  - `show instantiated`
  - `show device <name>`
  - `show groups`
  - `show group <name>`
- Each device report must include:
  - configured yes or no
  - instantiated yes or no
  - enabled yes or no
  - group membership
  - active in current test yes or no
  - blocked or unavailable reason when applicable
- `show device <name>` must explicitly display instantiation state in normal CLI output.
- `show instantiated` must provide a CLI-visible view focused on per-device instantiation status rather than only aggregate counts.
- Group reports must show:
  - group enabled state
  - member enabled state
  - skipped or blocked members
  - binding count and effective active binding count when available

### 6A. Test Preflight Visibility

Purpose: Make test setup decisions visible before motion or runtime evaluation begins.

Requirements:

- Before a test starts, the system must print or expose a preflight summary.
- The preflight summary must include:
  - requested test name
  - requested targets
  - resolved targets
  - skipped targets
  - blocked targets
  - unresolved dependencies
  - control ownership conflicts
  - disabled device or group conflicts
  - instantiation requirements or missing instantiated devices
- Each skipped or blocked item must include a concise reason.
- If preflight fails, the failure output must reference the same target-level reasons rather than replacing them with a generic error.

### 7. `add next` Visibility

Purpose: Make deterministic progression commands explain themselves.

Requirements:

- Document exactly what list and cursor `add next` uses.
- Before or during mutation, print enough information to explain the selection:
  - exact device added
  - source list name
  - previous cursor position or item
  - new cursor position or item
- If `add next` wraps, say so explicitly.
- If retained, `add next` must explain why the chosen device was next.
- If later replaced, the replacement command must preserve explicit preview and result reporting.

### 8. Enable and Disable Semantics

Purpose: Make effective eligibility deterministic and visible.

Rules:

- Device disabled always wins.
- A disabled device must never receive output commands.
- A disabled group cannot be selected by group-based tests unless explicitly overridden.
- If group enabled but device disabled, the device remains blocked.
- If device enabled but group disabled, group-based tests must skip or block that device.
- Skipped or blocked devices must be reported during test setup and bind explanation.

### 9. DSL Test Authoring Usability

Purpose: Reduce friction for common test authoring tasks.

Requirements:

- Add or strengthen commands:
  - `test list`
  - `test show <name>`
  - `test new <name> --template <template>`
  - `test edit <name>`
  - `test validate <name>`
  - `test run <name>`
  - `test clone <existing> <new>`
- `test edit` should open the configured external editor when possible.
- If no editor is configured, the CLI must print a direct fix or fallback path.
- Validation and run output must identify blocked dependencies such as:
  - missing devices
  - missing control ownership
  - disabled targets
  - unresolved signals

### 10. DSL `wait` and `timeout` Semantics

Purpose: Remove ambiguity in DSL timing behavior.

Normative direction:

- `wait 5s` means pause or hold execution for 5 seconds.
- `wait` does not terminate a test by itself.
- Test termination uses `until`, `abort`, `success`, or explicit `timeout`.
- If a forced maximum runtime is needed, it must be represented explicitly as `timeout`.

### 10A. Trace Mode

Purpose: Allow selected commands and tests to emit progress and status details when operators need deeper runtime visibility.

Requirements:

- The system must provide settable trace levels for commands and tests that benefit from progress visibility.
- Trace mode must be opt-in.
- Trace mode must be controllable at runtime.
  - Examples:
    - `trace basic`
    - `trace verbose`
    - `trace off`
    - `trace status`
    - command-scoped flags such as `--trace basic`
- Trace output must be clearly distinguishable from normal operator output.
- Trace mode must not replace final success, failure, blocked, or result summaries.

Required levels:

- `off`
  - no extra trace output beyond normal summaries
- `basic`
  - stage transitions
  - target object
  - progress milestones
  - waiting states
  - completion or abort reason
- `verbose`
  - everything in `basic`
  - retries or backoff
  - detailed resolution and eligibility checks
  - ownership claim or release details
  - target-by-target preflight detail
  - additional low-level execution progress useful for debugging

Use cases:

- long-running config push workflows
- test preflight and test execution progress
- binding activation and resolution debugging
- control ownership claim and release debugging
- staged validation or recovery workflows

Trace content should include, when relevant:

- current stage name
- current target object
- progress transitions
- waiting states
- retries or backoff states
- blocked or skipped reasons discovered during execution
- completion or abort reason

Behavior rules:

- Trace mode should be independently settable from TIU mode.
- TIU mode may display summarized trace events, but TIU and trace are not the same feature.
- Trace mode should support both:
  - global session-level enable or disable
  - per-command or per-test opt-in override
- Per-command or per-test trace level overrides should be able to raise or lower detail relative to the session default.
- Batch or regression usage must have a stable way to enable or disable trace output.
- Batch or regression usage must have a stable way to select the trace level.
- Trace mode should be rate-limited or event-driven so it does not flood output unnecessarily.
- When trace mode is `off`, commands must still emit normal high-signal summaries.
- Commands and tests should default to `basic`-appropriate milestone events rather than verbose step spam unless `verbose` is explicitly requested.

Output surfaces:

- Normal CLI mode:
  - trace lines may stream into CLI output
- TIU mode:
  - trace summaries may appear in the recent-events or output area
  - detailed trace output may flow into the CLI output pane

Safety rules:

- Trace mode must not change command or test behavior.
- Trace mode must not introduce large blocking print bursts in robot-side real-time loops.
- Any robot-side report-like trace output must respect the shared report runner and existing loop-budget protections.

### 11. Driver Station Emergency Behavior Preservation

Purpose: Keep emergency stop behavior intact while improving operator usability.

Requirements:

- Do not disable or bypass Driver Station stop behavior.
- Do not rely on trapped keyboard keys for live enabled robot actuation control.
- CLI may remain the setup, inspect, save, push, and arm surface.
- Live robot actuation should move toward joystick ownership or button-driven UI surfaces rather than keyboard traps.

### 12. Minimum Bringup Path Regression

Purpose: Provide one repeatable bringup path that does not depend on ad hoc expert guidance.

Add one documented and testable minimum bringup path covering:

- load config
- show configured devices
- create or select steering group
- create or select motion group
- save config
- push config
- show active, instantiated, and enabled devices
- bind one joystick axis to one safe target
- show bindings
- run a simple test
- stop safely
- show result or log

This flow must become a maintained regression and a documented operator procedure.

### 13. Live Operation Surface Direction

Purpose: Record the usability direction for enabled robot operation without weakening emergency behavior.

Requirements:

- The system must not require trapped keyboard keys for enabled robot operation.
- Live operation workflows should prefer:
  - joystick-owned controls
  - button-driven UI controls
  - mouse-driven controls
- CLI should remain the setup, inspect, save, push, arm, and diagnose surface.
- Future UI or wizard work should reuse the same visibility and failure explanation contract defined here.

### 14. TIU Mode

Purpose: Provide a switchable high-visibility mode that keeps the most important operator state on screen continuously.

Definition:

- TIU mode is a CLI mode that can be switched on or off.
- TIU means a dense operator visibility mode, not a separate control surface and not a separate command model.
- TIU mode must reuse the same host state, robot state, and explanation contracts defined elsewhere in this spec.

Requirements:

- TIU mode must be explicitly switchable on and off.
  - Commands:
    - `tiu on`
    - `tiu off`
- When enabled, TIU mode should keep as much high-value state visible on screen at once as practical without requiring repeated `show` commands.
- TIU mode is read-mostly.
- TIU mode must still allow normal CLI command entry.
- TIU mode must not change command semantics, control ownership semantics, save semantics, or push semantics.
- TIU mode must not introduce keyboard-trapped enabled-operation control behavior.

Minimum content:

- host state:
  - loaded source paths
  - active profile
  - dirty state
- save and push provenance:
  - last modified identity or timestamp
  - last saved identity
  - last pushed identity
  - local versus pushed versus robot match state
- robot state:
  - connected or disconnected
  - enabled
  - estopped
  - active robot profile
- active runtime state:
  - running test or idle state
  - selected target or mode when relevant
  - safety latch or stop latch state
- summarized devices state:
  - configured count
  - instantiated count
  - enabled count
  - blocked count
- TIU mode must display instantiation state in its devices section.
- TIU should provide both:
  - aggregate instantiation counts
  - enough per-device detail to identify which configured devices are not instantiated
- summarized groups state:
  - enabled groups
  - blocked or skipped members count
- summarized bindings state:
  - active count
  - unresolved count
  - blocked count
- control ownership summary:
  - currently claimed controls
  - current owners
- recent actionable events:
  - recent warnings
  - recent blocked actions
  - recent failures

Interaction model:

- TIU mode may refresh continuously while data sources are available.
- TIU mode may also refresh on command completion when continuous refresh is not practical.
- TIU mode must preserve normal CLI command entry and execution while active.
- The operator must be able to run normal CLI commands without leaving TIU mode.
- TIU mode must allow operators to return to normal CLI presentation without losing underlying session state.
- `tiu on` and `tiu off` are presentation commands only.
- Switching TIU on or off must not reset:
  - connection state
  - active CLI context
  - loaded workspace state
  - trace level
  - command history
- TIU mode should provide a visible section-selector area with checkbox-style toggles for which summary sections are shown.
- The operator should be able to hide unused sections while TIU mode remains active.
- Hidden sections must free space for the normal CLI scrolling area rather than leaving blank dashboard space.
- Detailed inspection commands remain authoritative.
  - Examples:
    - `show active`
    - `show dirty`
    - `show signals`
    - `bind explain <binding>`
    - `control show`

Layout behavior:

- TIU mode should prefer a fixed non-scrolling status area with a bounded recent-events area rather than allowing the main operator summary to scroll away.
- The TIU layout should include:
  - a fixed status area
  - a section-selector area with checkbox-style toggles
  - a normal CLI scrolling area
  - a command entry line
- If section toggles reduce the height of the fixed status area, the reclaimed space should be given to the CLI scrolling area.
- The layout should avoid leaving large unused dashboard gaps when only a few sections are enabled.
- If the terminal is too small to show all enabled sections, lower-priority sections may collapse behind an explicit hidden-sections indicator rather than forcing the command line off screen.

Example layout:

```text
+----------------------------------------------------------------------------------+
| bridge(tiu)*#                                                   12:41:08        |
+----------------------------------------------------------------------------------+
| [x] Host  [x] Save/Push  [x] Robot  [ ] Groups  [x] Bindings  [ ] Signals       |
| [x] Devices  [x] Control  [x] Events                                             |
+----------------------------------------------------------------------------------+
| HOST                     | SAVE / PUSH                  | ROBOT                   |
| Profile: home_050126    | Last modified: 12:41:22     | Connected: yes          |
| Dirty: yes              | Last save:     12:35:44     | Enabled:   false        |
| Sources: loaded         | Last push:     12:36:10     | EStopped:  false        |
|                         | Match: local!=saved          | Active: home_050126     |
+----------------------------------------------------------------------------------+
| DEVICES                  | BINDINGS                     | CONTROL                  |
| Configured:   14         | Active:     1               | xbox0.leftY -> manual    |
| Instantiated: 6          | Blocked:    2               | xbox0.rightY -> dsl:t1   |
| Enabled:      5          | Unresolved: 1               | xbox0.A -> none          |
| Blocked:      1          |                              |                          |
| Not inst: SPARKMAX 25    |                              |                          |
+----------------------------------------------------------------------------------+
| RECENT EVENTS                                                                     |
| 12:40:51 BLOCKED bind activate: xbox0.rightY owned by dsl:t1                      |
| 12:40:12 WARNING push config refused: local config dirty                          |
+----------------------------------------------------------------------------------+
| CLI OUTPUT                                                                         |
| show bindings                                                                      |
| Binding: xbox0.leftY -> motion.output                                              |
|   status: ACTIVE                                                                   |
|   last input value: -0.42                                                          |
|   last output value: -0.42                                                         |
| ...                                                                                |
+----------------------------------------------------------------------------------+
| bridge(tiu)*#                                                                      |
+----------------------------------------------------------------------------------+
```

Resize behavior example:

- If `Groups` and `Signals` are toggled on, the fixed status area grows and the CLI output area shrinks.
- If `Bindings` and `Control` are toggled off, the fixed status area shrinks and the CLI output area grows.
- If only `Host`, `Save/Push`, and `Robot` are enabled, TIU should compress to a small header-like dashboard and give most rows back to CLI output.

Failure behavior:

- If some runtime inputs are unavailable, TIU mode must identify those sections as unavailable rather than showing stale or implied values.
- If robot state is disconnected, TIU mode must continue showing host-local state and clearly mark robot-dependent sections as unavailable.

Tradeoffs:

- TIU mode increases screen density and refresh complexity, but reduces operator guesswork during bringup.
- TIU mode is a visibility layer only; it must not become a hidden alternate state machine.

## Failure Explanation Contract

Purpose: Define how failures should be presented across commands.

Any operator-facing command that fails, blocks, skips, or degrades must report:

- operation name
- target object when relevant
- failure class
  - invalid
  - unresolved
  - blocked
  - disabled
  - conflict
  - unavailable
- concise reason
- direct next step when known

Examples:

- `blocked`: `xbox0.leftY is owned by DSL test drive_test_01`
- `disabled`: `motor1 is configured but disabled`
- `unresolved`: `binding target group drive_left does not exist`
- `unavailable`: `last input value unavailable; runtime publisher absent`

## Output Surfaces

Purpose: State where this contract must appear first.

Phase 1 required surfaces:

- CLI text output
- CLI JSON output where applicable
- robot-side show or status outputs that feed CLI inspection

Phase 2 candidates:

- Bringup Control UI panels
- topology live overlay
- dashboard-facing summaries

## Documentation Requirements

Purpose: Keep operator docs aligned with the intended usability contract.

Update or add documentation for:

- dirty versus saved versus pushed state
- provenance of last save and last push
- control ownership and conflict resolution
- bind semantics and inactive reasons
- active runtime summary and signal inspection
- device and group effective eligibility
- `add next` source list and cursor semantics
- test preflight summaries
- minimum bringup path
- failure message interpretation

Relevant docs likely include:

- `docs/FEATURE_SPEC_CLI_USABILITY.md`
- `docs/CLI_REFERENCE_MANUAL.md`
- `docs/CLI_USER_MANUAL.md`
- `docs/TEST_PROCEDURE_ZERO_CONFIG.md`
- `docs/TESTING_REAL_ROBOT_BRINGUP.md`

## Acceptance Criteria

Purpose: Provide a go or no-go bar for this pass.

- Operators can determine dirty versus saved state without reading code.
- Operators can determine last saved versus last pushed versus current local state without reading code.
- Operators can determine what is active right now from one summary command.
- Operators can inspect signal availability and current values where supported.
- Operators can explain why a binding is inactive from CLI output alone.
- Operators can identify which device or group state blocked a test or command.
- Operators can see which targets were skipped or blocked before a test starts.
- Config push reports stage-by-stage success or failure with no silent failure path.
- A control ownership conflict reports the current owner and the required next step.
- `add next` reports what it selected and why.
- The minimum bringup path is documented and regression tested.

## Tradeoffs

Purpose: Record likely implementation tradeoffs.

- Richer inspection output may require additive robot runtime state fields.
- A stronger control lease model may surface conflicts that were previously hidden.
- Better explanations may temporarily expose inconsistencies between local and robot state that were previously masked.
- Some commands may become more verbose, but the gain in traceability is the point of this pass.

## Future Extensions

Purpose: Keep later work out of the critical path.

- add UI-specific panels for control ownership and active bindings
- add failure summaries grouped by workspace, runtime, and control domains
- add machine-readable operator logs for post-test analysis
- add guided wizards built on the same visibility contract

## Resolved Decisions

Purpose: Record decisions resolved during spec review.

- `push config` must refuse dirty local config by default.
- The standard path is save to disk first, then push from a saved artifact.
- An advanced explicit override may exist, but it must be clearly exceptional.
- Bare `save` works only when every dirty section already has a known source path.
- If any dirty section lacks a known path, the command must fail with a direct fix.

SID_COMMENT: This pass should prefer exposing current runtime truth and blocked reasons before changing bind, group, or test semantics.

