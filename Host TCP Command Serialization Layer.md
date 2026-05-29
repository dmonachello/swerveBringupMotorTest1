

  

SPEC_STATUS: PROPOSED

  

## Purpose

  

Define one mandatory host-side communication layer above the robot TCP UI command channel so all host apps serialize normal commands and use the same recovery/session behavior.

  

## Goal

  

Any host app in this repo that talks to the robot over the TCP UI command channel must use one shared command layer instead of sending raw commands directly through the TCP session object.

  

The layer exists to prevent these failures:

  

- host sends a second command while the first is still active

- scripts become timing-sensitive and brittle

- different host apps implement different retry or blocking behavior

- session recovery depends on ad hoc workarounds

  

## Scope

  

This spec applies only to host-to-robot command traffic over the TCP UI command channel.

  

This spec does not cover:

  

- NetworkTables reads/writes

- passive CAN capture

- non-TCP robot communication paths

- robot-internal command scheduling beyond the behavior visible through the TCP protocol

  

## In-Scope Host Apps

  

Any host app in this repo that talks to the robot over the TCP UI command channel must use this layer.

  

Examples:

  

- Bringup CLI

- Bringup Control UI

- topology/live topology surfaces when they send robot commands

- regression scripts

- direct Python automation helpers

- future host utilities that send robot TCP UI commands

  

## Required Architecture

  

There must be one common host-side command layer above the raw TCP session.

  

The raw TCP session remains responsible for:

  

- connect/disconnect

- wire framing

- seq/client/session transport details

- raw send/receive primitives

  

The new shared layer becomes responsible for:

  

- command classification

- one-in-flight serialization for normal commands

- waiting for terminal completion before sending the next normal command

- bypass handling for priority recovery/session commands

- non-blocking handling for passive/session utility commands

- consistent timeout handling

- consistent busy/failure handling

- shared observability for all host surfaces

  

Per-surface implementations must not reimplement these rules independently.

  

## Command Classes

  

### Serialized Normal Commands

  

These commands must use one-in-flight serialization.

  

Rules:

  

- only one serialized normal command may be in flight at a time per robot session

- the next serialized normal command must not be sent until the prior serialized normal command reaches terminal completion

- no host surface may bypass this rule

  

Included commands:

  

- `profilesApply`

- `profilesReload`

- `profileActivate`

- `selectProfile`

- all `show*` commands

- group/config commands

- device selection commands

- test commands

- manual device duty commands

  

SID_COMMENT: If future command inventory grows, default new host-visible commands into the serialized-normal class unless they are explicitly classified otherwise.

  

### Priority Recovery/Session Commands

  

These commands may bypass the serialized normal queue.

  

Rules:

  

- these commands may be issued even when a serialized normal command is active

- these commands exist to recover or establish the session

- they must not depend on the normal serialized queue being idle

  

Included commands:

  

- `stopCommand`

- `uiHandshake`

- `uiDisconnect`

  

### Passive/Session Utility Commands

  

These commands must not consume the serialized normal command slot.

  

Rules:

  

- these commands may run while no normal command is active

- they must not block later serialized normal commands from starting

- they must not be treated as active robot work

  

Included commands:

  

- `uiPing`

- `uiPollLog`

- `uiMonitorEnable`

- `uiMonitorDisable`

  

## Host Layer Behavioral Contract

  

### Serialized Submission

  

When a host app submits a serialized normal command:

  

1. The layer must wait until no other serialized normal command is in flight.

2. The layer must send the command.

3. The layer must wait for terminal completion.

4. Only after terminal completion may the next serialized normal command be sent.

  

### Terminal Completion

  

For this layer, a terminal completion is the point where the command is definitively done for host sequencing purposes.

  

Terminal outcomes include:

  

- success

- failure

- interrupted

- rejected

- timeout

  

If a command reaches any terminal outcome, the serialized slot is released.

  

## No Automatic Optimistic Concurrency

  

The host layer must not use busy errors as normal flow control.

  

Specifically:

  

- the layer must not intentionally send serialized normal command B while serialized normal command A is still in flight

- scripts must not have to guess timing gaps between commands

- operator apps must not depend on retry-after-failure timing hacks

  

## Busy Response Handling

  

If the robot still returns a busy-style failure such as:

  

- `Another command is already active.`

  

then the shared host layer must treat that as an exceptional mismatch between host and robot state.

  

Required behavior:

  

- mark the submitted command as failed for that attempt

- surface the failure clearly to the caller

- do not silently resend the command automatically in the same path unless the spec for that caller explicitly requests bounded retry

  

SID_COMMENT: The main design goal is to prevent busy rejections by host-side serialization, not to normalize them away with hidden retries.

  

## Command Result Model

  

The common layer must expose a shared result contract to all host apps.

  

At minimum it must provide:

  

- command name

- seq

- client id

- command class

- sent timestamp

- completion timestamp

- terminal status

- robot message text

- machine-readable code when available

- raw JSON/text payloads when available

  

This result contract must be common code, not per-surface reconstruction.

  

## Queue Model

  

For serialized normal commands, the host layer must provide an internal queue or equivalent waiting mechanism.

  

Requirements:

  

- preserve submission order

- allow multiple callers to wait safely

- guarantee that only one serialized normal command is sent at a time

- release the slot on terminal completion

  

This queue is host-side only.

  

It does not imply that the robot must queue commands.

  

## Priority Command Behavior

  

### `stopCommand`

  

`stopCommand` is a recovery interrupt command.

  

Required behavior:

  

- may bypass the serialized normal queue

- may be sent while a serialized normal command is in flight

- should be used by host recovery paths when the robot-side active command must be interrupted

  

### `uiHandshake`

  

`uiHandshake` is a session-establishment command.

  

Required behavior:

  

- may bypass the serialized normal queue

- must remain available even if robot-side active command state is confused

- is not considered the active serialized normal command

  

### `uiDisconnect`

  

`uiDisconnect` is a session-release command.

  

Required behavior:

  

- may bypass the serialized normal queue

- must remain available during recovery

  

## Passive Utility Command Behavior

  

### `uiPing`

  

- may be sent without taking the serialized normal slot

- must not block later serialized normal commands

  

### `uiPollLog`

  

- may be sent without taking the serialized normal slot

- must not cause a later serialized normal command to be rejected as busy

  

### `uiMonitorEnable` / `uiMonitorDisable`

  

- must not consume the serialized normal slot

  

## App Integration Requirements

  

### Bringup CLI

  

Purpose: Ensure batch and interactive CLI commands follow the same safe sequencing rules.

  

Requirements:

  

- all robot TCP command sends must go through the shared layer

- batch mode must not send the next serialized normal command until the previous one reaches terminal completion

- interactive mode must use the same path as batch mode

- `config push`, `profilesApply`, `show*`, group commands, and test commands must all use the shared serialized path

- recovery actions must use the priority path

  

### Bringup Control UI

  

Purpose: Keep operator actions and background session activity from colliding.

  

Requirements:

  

- all robot command actions must go through the shared layer

- button presses for serialized normal commands must enqueue/wait instead of issuing raw sends

- background session activity such as `uiPing` and `uiPollLog` must use the passive utility classification

- emergency/recovery actions must use the priority path

  

### Live Topology / Manual Motor Control

  

Purpose: Prevent continuous manual control commands from corrupting later config or inspection operations.

  

Requirements:

  

- manual device duty commands must be classified as serialized normal commands

- left-click stop or clear operations that intentionally interrupt manual control may use priority recovery behavior only if explicitly routed through `stopCommand`; otherwise they remain normal serialized commands

- any robot-side command path triggered from topology/live views must use the shared layer

  

SID_COMMENT: The exact UI interaction remains separate from this transport spec. The transport rule is mandatory regardless of popup/slider behavior.

  

### Topology Editor

  

Purpose: Keep future robot-facing topology/config actions aligned with CLI and UI semantics.

  

Requirements:

  

- if the topology editor talks to the robot over TCP, it must use the shared layer

- profile/config apply actions must use serialized normal submission

- session/recovery actions must use the priority path

  

### Regression Scripts And Automation

  

Purpose: Make scripts deterministic and remove timing guesses.

  

Requirements:

  

- scripts must use the shared layer instead of raw `BridgeSession.send_command(...)` for robot commands

- scripts must not need ad hoc `sleep(...)` gaps between serialized normal commands

- scripts may still choose to inspect failure and retry intentionally, but the base send path must already serialize correctly

  

## Surface API Shape

  

The shared host layer must expose a common API used by all apps.

  

Exact names may vary, but functionality must include:

  

- submit serialized normal command and wait for terminal completion

- submit priority command

- submit passive utility command

- inspect current in-flight serialized normal command

- inspect queue depth

- register completion/error callbacks or await results

  

Example conceptual API:

  

```text

submit_serialized(name, args) -> CommandResult

submit_priority(name, args) -> CommandResult

submit_passive(name, args) -> CommandResult

get_inflight_command() -> CommandSummary | null

get_queue_depth() -> int

```

  

SID_COMMENT: This example is conceptual. Final implementation naming should align with existing Python shared-service conventions.

  

## Error Handling

  

Required host-side handling:

  

- timeout must complete the command as terminal failure and release the serialized slot

- disconnect must fail any in-flight serialized normal command and clear queued waiting state appropriately

- malformed response must fail the affected command cleanly

- busy rejection must be surfaced as a host/robot state mismatch, not silently hidden

  

## Observability

  

The shared host layer must provide consistent observability for all host surfaces.

  

At minimum:

  

- current in-flight serialized normal command

- queue depth

- last completed command

- last failed command

- timeout count

- busy rejection count

- disconnect count while command in flight

  

This must be available for debugging and regression work.

  

## Testing Requirements

  

Automated tests must cover:

  

- second serialized normal command is not sent until the first completes

- passive utility commands do not block serialized normal commands

- priority commands can be sent while a serialized normal command is active

- disconnect/timeout release the serialized slot

- CLI batch sequencing uses the shared layer

- UI background polling does not block config/apply or show commands

  

Manual tests must cover:

  

- interactive CLI back-to-back `show*` then `config push`

- Bringup UI connected while CLI performs serialized normal commands

- manual motor control followed by recovery and config apply

- session recovery with `stopCommand` and `uiHandshake`

  

## Rollout Requirements

  

Implementation must proceed by moving existing host surfaces onto the shared layer, not by leaving parallel send paths in place.

  

Required rollout order:

  

1. common layer implementation

2. CLI adoption

3. Bringup Control UI adoption

4. regression/automation adoption

5. any remaining host robot clients

  

During rollout:

  

- old direct-send paths must be removed or explicitly blocked once migration is complete

- docs and examples must stop recommending raw direct command sends for normal host usage

  

## Non-Goals

  

- changing NetworkTables ownership

- redesigning robot-local command taxonomy beyond what is needed for the transport contract

- adding robot-side multi-command queueing

- changing topology editor non-robot workflows

  

## Tradeoffs

  

- serialization may slightly reduce peak command throughput

- operator feedback may need clearer “waiting” state in UI surfaces

- some formerly optimistic flows will become explicitly ordered

  

These tradeoffs are acceptable because deterministic behavior is more important than speculative concurrency for robot bringup and scripting.

  

## Definition Of Done

  

- all host TCP robot command surfaces use one shared command layer

- normal commands are not sent concurrently from host apps

- `Another command is already active.` is no longer a normal operator or script experience for back-to-back safe commands

- recovery/session commands remain available even when robot-side active command state is confused

- regression scripts no longer need timing sleeps between normal TCP commands

- docs for CLI/UI/automation are updated to describe the shared layer behavior

  

## Future Extensions

  

- explicit host-visible busy state with active command name

- bounded optional retry policy for narrow safe cases

- richer queue inspection in operator UIs

- robot-side active command introspection for display and diagnostics