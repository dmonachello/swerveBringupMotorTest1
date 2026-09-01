SPEC_STATUS: PROPOSED

# Feature spec: central work-slice manager

## Purpose

Define one robot-side scheduler that owns non-critical background work inside the 20 ms control loop budget.

The current system has several independent bounded or semi-bounded work paths:

- queued report printing
- active presence probe stepping
- lifecycle refresh
- sampled telemetry collection
- future evidence and diagnosis work

Those local fixes reduce individual spikes, but they do not give the robot one authoritative place that decides:

- how much background work may run this cycle
- which work runs first
- what gets deferred
- what gets dropped
- how queue pressure is reported

This spec defines that central mechanism.

## Problem

The current system can still become unstable when several expensive conditions happen together, especially during fault states:

- multiple CAN devices unpowered or disconnected
- repeated vendor API timeouts
- console and diagnosis work both active
- active probe or other operator-triggered work running at the same time

The issue is not only one bad command. The issue is that multiple components can each do "a small amount" of work without one shared arbiter enforcing a total cycle budget.

That leads to:

- loop overruns
- REST instability
- blank or frozen host UI surfaces
- delayed or stale diagnosis updates
- hard-to-reason-about starvation between subsystems

## Goal

Create a single central work-slice manager that:

- enforces a shared per-cycle background-work budget
- runs only bounded work units
- uses bounded queues
- makes enqueue rejection explicit
- supports fair progress over time
- allows degraded operation under heavy fault load
- exposes clear stats so overload is visible

## Non-goals

This spec does not:

- change motor control or command scheduler semantics
- move critical control logic into queued background work
- allow unlimited buffering
- guarantee that all work is accepted
- hide overload by silently dropping work with no accounting

## Scope

This spec applies to robot-side non-critical work executed from the periodic loop, including:

- report generation and streaming
- active presence probe steps
- sampled telemetry collection beyond mandatory real-time data
- periodic lifecycle refresh
- diagnosis/evidence maintenance
- source-health or maintenance passes added later

This spec does not apply to:

- direct actuator updates needed for safe control
- WPILib command scheduler core behavior
- emergency stop handling
- required safety interlocks

## Current state

Today the system already has partial slicing in several places:

- `BringupPrinter` batches output
- `BringupCore.updateReports()` advances report jobs incrementally
- active presence probe now runs across multiple cycles
- lifecycle refresh uses a bounded periodic snapshot budget
- sampled telemetry was being moved toward bounded reads

These are useful tactical fixes.

They are not enough because there is still no central authority that says:

- reports get at most N work units after probe and safety maintenance
- telemetry must stop early if probe already consumed the budget
- a noisy fault condition cannot flood the system with accepted work

## Design principles

### One budget owner

All background work in the robot loop must run through one manager that owns the cycle budget.

### Bounded queues only

Every queue must have a fixed capacity.

No producer may assume enqueue succeeds.

### Explicit enqueue result

Every submitter must receive a structured result such as:

- `ACCEPTED`
- `ACCEPTED_COALESCED`
- `REJECTED_QUEUE_FULL`
- `REJECTED_DUPLICATE`
- `REJECTED_DISABLED`
- `REJECTED_INVALID`

### Degrade instead of block

When overloaded, the system must defer or reject background work rather than blocking the loop.

### Fairness with priorities

Urgent maintenance work should run before low-priority convenience work, but lower priorities must still make progress when the system is healthy enough.

### Observable overload

Queue depth, age, drops, coalescing, skips, and budget exhaustion must be visible in reports and host surfaces.

### Common contract

All participating subsystems must use the same queue, task, rejection, and accounting contract rather than inventing local variants.

## Core model

### Work classes

Background work is divided into classes:

- `MAINTENANCE`
- `DIAGNOSTIC`
- `REPORT`
- `OPERATOR_REQUEST`
- `HOUSEKEEPING`

Examples:

- lifecycle refresh: `MAINTENANCE`
- evidence aging tick: `MAINTENANCE`
- sampled telemetry pass: `DIAGNOSTIC`
- active presence probe: `OPERATOR_REQUEST`
- report chunk emission: `REPORT`
- cleanup of expired state: `HOUSEKEEPING`

### Priority bands

Each task also has a priority band:

- `HIGH`
- `MEDIUM`
- `LOW`

Priority affects scheduling order, not queue ownership. Queue ownership is by class.

### Work unit

A work unit must be small enough to complete within a tight bounded slice.

Examples:

- process one report chunk
- sample one device or one small signal batch
- execute one active-presence-probe target step
- age one bounded evidence batch

The manager never accepts "run the entire report" or "probe all devices" as one unit.

### Queue lanes

Each work class has a bounded queue lane.

Minimum required lanes:

- maintenance lane
- diagnostic lane
- report lane
- operator-request lane
- housekeeping lane

Each lane has:

- fixed capacity
- priority policy
- duplicate/coalescing policy
- per-cycle service quota hint

## Scheduling model

### Cycle budget

Each robot cycle reserves a fixed background-work budget smaller than the full 20 ms loop.

This spec does not lock the numeric value yet. It must be centrally configurable and measurable.

The manager should support both:

- maximum work items per cycle
- optional soft time budget based on monotonic timestamps

The manager must stop dispatching background work when either budget is exhausted.

### Dispatch order

Default dispatch policy:

1. `MAINTENANCE/HIGH`
2. `OPERATOR_REQUEST/HIGH`
3. `DIAGNOSTIC/MEDIUM`
4. `REPORT/MEDIUM`
5. `HOUSEKEEPING/LOW`

This is a policy default, not a hardcoded forever rule.

### Fairness

The manager must prevent starvation.

Required behavior:

- per-lane round-robin within equal priority
- age-aware boost for old queued items
- no lane may be skipped forever while the system is otherwise healthy

### Re-queue model

Long-running activities are represented as repeated bounded work items, not one monolithic job.

Examples:

- active presence probe submits or resubmits one next-step item until complete
- report generation resubmits next chunk
- telemetry sampling resubmits next device batch

The manager must not require callers to busy-loop inside one dispatch.

## Queue contract

### Required queue properties

Each queue must be:

- bounded
- non-blocking for submitters
- safe for repeated periodic use
- instrumented

### Submit result

All queue submissions must return a structured result containing at least:

- status code
- lane name
- queue depth after attempt
- whether the request was coalesced
- optional rejection reason

### Producer responsibilities

Every producer must explicitly handle rejection.

Allowed producer behaviors on rejection:

- drop and count
- coalesce into an existing pending item
- mark internal dirty state and retry on a later tick
- surface a warning
- downgrade output detail

Forbidden producer behavior:

- assume acceptance and lose state silently
- block waiting for queue space
- recursively retry until accepted

### Coalescing

Coalescing is required for naturally replaceable work.

Examples:

- "refresh lifecycle snapshot" should collapse to one pending refresh
- "sample telemetry for this device family" may collapse to one dirty marker
- "update report progress" may not need multiple duplicate pending items

Examples that should not blindly coalesce:

- distinct operator-request probe steps for different devices when the step ordering matters

## Task interface

Each background task type must expose a common interface conceptually equivalent to:

- task identity
- work class
- priority
- maximum expected cost category
- coalescing key if any
- `runOneSlice(...)`

`runOneSlice(...)` must return a structured completion result such as:

- `COMPLETE`
- `PARTIAL_REQUEUE`
- `FAILED`
- `SKIPPED_SOURCE_UNAVAILABLE`
- `SKIPPED_PRECONDITION`

The result must also report:

- work units consumed
- optional follow-up task request
- warning/error note if relevant

## Source and dependency awareness

Some background tasks depend on external availability:

- CAN device power
- REST server availability
- vendor API responsiveness
- passive observer freshness

The scheduler itself should not interpret those domains deeply, but tasks must be able to return:

- source unavailable
- stale prerequisite
- retry later

The manager must account for these outcomes without treating them as crashes.

## Backpressure and overload behavior

### Required overload responses

When queue pressure rises or loop time is threatened, the system must prefer these responses in order:

1. coalesce replaceable work
2. skip low-priority work this cycle
3. reject new low-priority submissions
4. downgrade detail level for verbose producers
5. surface overload status

### Required stats

The manager must keep counters for at least:

- accepted submissions
- coalesced submissions
- rejected full
- rejected duplicate
- rejected disabled
- tasks run
- tasks completed
- tasks requeued
- tasks failed
- tasks skipped
- cycles budget-exhausted
- max queue depth per lane
- oldest pending age per lane

### Operator visibility

At minimum, overload state must be visible in:

- robot-side report/status text
- host diagnostics surfaces that already expose runtime/app status

## Integration plan

### Phase 1: install manager without changing behavior ownership

Introduce the central manager and migrate selected existing bounded jobs behind it while preserving current behavior as closely as possible.

First migrations:

- report chunk emission
- active presence probe step execution
- lifecycle refresh maintenance

### Phase 2: migrate telemetry sampling

Move sampled telemetry reads to manager-owned bounded work units with round-robin fairness.

This is important because telemetry scales with device count and can become expensive during CAN-fault conditions.

### Phase 3: migrate evidence and diagnosis maintenance

Move future robot-side evidence maintenance or diagnosis passes to the manager.

### Phase 4: unify budgeting policy

Remove remaining ad-hoc per-component periodic budgets where the central manager now owns equivalent behavior.

Local micro-bounds inside a task may remain, but they become implementation details rather than the primary scheduling policy.

## Interaction with evidence fusion

The evidence-fusion design already assumes:

- bounded work
- incremental processing
- explicit queue lanes
- replayability

The robot-side work-slice manager is the runtime execution counterpart to that model.

Shared design requirements:

- bounded ingestion
- bounded evaluation
- freshness-aware degradation
- drop accounting
- explicit source-health reporting

This spec does not force the evidence engine itself onto the robot. It defines how any robot-side evidence-related work must be scheduled if present.

## Failure modes to handle

### Queue full

Expected under fault storms or operator misuse.

Required behavior:

- reject explicitly
- increment counters
- allow producer-specific fallback

### Persistent source timeout

Expected when CAN devices are unpowered or disconnected.

Required behavior:

- tasks remain bounded
- failing tasks do not monopolize the budget
- repeated retries are throttled or age-managed

### Producer bug

If a producer repeatedly submits non-coalescing work every cycle, bounded queues must cap damage and stats must expose it.

### Task bug

If a task overruns its expected slice, the manager must at least:

- record slow-task stats
- surface the offending task identity

Future enforcement may add per-task quarantine, but this spec only requires reporting in the first implementation stage.

## Required diagnostics

The manager must surface a concise health view including:

- total pending work
- per-lane queue depth
- oldest age per lane
- recent rejections
- recent budget exhaustion
- top submitters by rejected count
- top task types by runtime when available

Recommended output locations:

- robot-side health/state report
- runtime/app status snapshot
- host UI inspector or diagnostics panel

## Configuration

The following must be centrally configurable:

- per-cycle max work items
- optional soft time budget
- lane capacities
- per-lane service hints
- coalescing policy toggles where needed for testing
- diagnostics verbosity

Configuration must default conservatively.

## Testing

### Unit tests

Required unit coverage:

- queue full rejection
- duplicate/coalesced submission
- round-robin fairness
- priority ordering
- age-based anti-starvation behavior
- task requeue progression across cycles
- skipped-source outcomes
- budget exhaustion stopping further dispatch

### Fault-state regression

Required targeted robot-side regressions:

- all CAN devices powered
- one CAN device disconnected
- multiple CAN devices disconnected
- CAN bus unpowered while roboRIO still powered
- active presence probe during missing-device condition

Expected result:

- no monolithic freeze
- bounded queue growth
- visible rejection/overload accounting
- host surfaces remain responsive enough to recover

### Load regression

Add synthetic tests that submit work faster than it can be processed.

Expected result:

- bounded memory use
- explicit rejection counts
- no blocking submitter behavior

## Migration rules

During migration:

- do not remove existing safety behavior
- keep diffs small and reversible
- add narrow regression tests per migrated component
- preserve current operator-facing workflows unless separately approved

If any migrated path destabilizes the robot loop, it must be easy to revert that slice independently.

## Open decisions

SID_QUESTION: Should the first implementation use only max-work-items per cycle, or also a soft monotonic time budget in the same slice?

SID_QUESTION: Should operator-request work always outrank maintenance work, or should maintenance retain first priority to protect freshness of core state?

SID_QUESTION: Which existing sampled telemetry reads are truly mandatory every loop and therefore must stay outside this manager?

## Recommended first implementation

The first implementation should:

- add the manager with bounded lanes
- migrate report chunks
- migrate active presence probe stepping
- migrate lifecycle refresh
- keep queue stats visible
- require explicit rejection handling in all migrated producers

Then test under:

- normal healthy bus
- one missing device
- no CAN bus power

Only after that should sampled telemetry move under the manager.

## Tradeoffs

- A central manager adds structural complexity, but it replaces multiple inconsistent local throttles.
- Bounded queues may reject work that would previously have been attempted, but rejection is safer than hidden overload.
- Incremental work means some views converge over several cycles, but the system remains responsive and truthful about freshness.

## Future extensions

- per-task runtime timing histograms
- temporary suppression or quarantine of chronically slow tasks
- dynamic budget tuning based on robot mode
- host-visible live scheduler inspector
- shared scheduling abstractions for host-side background work where useful
