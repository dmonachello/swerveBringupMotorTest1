SPEC_STATUS: PROPOSED

# Feature spec: central work-slice manager

## Purpose

Give the roboRIO one owner for non-critical work that runs around the 20 ms control loop.

The system already limits reports, probes, lifecycle refreshes, and some telemetry reads in separate places. That helped, but each component still decides for itself how much work is safe. This manager decides it once for the whole robot.

## Problem

The bad case is not one slow task. It is several modest tasks arriving together while CAN hardware is missing or noisy:

- devices are unpowered or disconnected;
- vendor APIs are timing out;
- console capture and diagnosis work are active;
- an operator starts a presence probe; and
- REST requests continue asking for state.

Each component may be locally bounded and still collectively exceed the available time. The results have been familiar: loop overruns, stale diagnosis, REST disconnects, and UI windows that stop updating.

The robot needs one place that decides what runs now, what waits, and what is rejected.

## Goals

- Keep the 20 ms control loop responsive during fault conditions.
- Run only small, bounded units of non-critical work.
- Bound every queue and make rejected work visible.
- Give urgent maintenance work priority without starving lower-priority work forever.
- Preserve enough accounting to find the producer or task that is creating pressure.
- Keep the design compatible with incremental evidence and diagnosis work.

## Non-goals

- Moving motor control, safety stops, or the WPILib command scheduler into a queue.
- Promising that every background request will be accepted.
- Buffering unlimited work until the robot recovers.
- Hiding drops or overload behind a normal-looking status screen.

## Scope

The manager owns non-critical robot-side work normally initiated from periodic code:

- report generation and chunked output;
- active presence-probe steps;
- optional sampled telemetry;
- periodic lifecycle refresh;
- evidence and diagnosis maintenance; and
- future source-health maintenance.

It does not own direct actuator writes, safety interlocks, emergency-stop handling, or required WPILib scheduler behavior.

## Current state

Several existing paths already slice their work:

- `BringupPrinter` batches output;
- `BringupCore.updateReports()` advances report jobs incrementally;
- active presence probes advance across cycles;
- lifecycle refresh has a snapshot budget; and
- sampled telemetry has per-pass limits.

Those controls are useful, but they do not share a total budget. A probe can consume time that telemetry also assumes is available. A noisy source can continue submitting work while the report path is trying to catch up.

## Core rules

### One budget owner

All background periodic work goes through one manager. Individual tasks may retain small internal bounds, but they do not independently decide how much total periodic time they may consume.

### Bounded queues

Every lane has a fixed capacity. Producers must expect rejection and must not block or retry in a loop while waiting for space.

### Explicit outcomes

Every submission returns a structured result:

- `ACCEPTED`
- `ACCEPTED_COALESCED`
- `REJECTED_QUEUE_FULL`
- `REJECTED_DUPLICATE`
- `REJECTED_DISABLED`
- `REJECTED_INVALID`

### Defer before blocking

When the system is overloaded, defer, coalesce, reduce detail, or reject work. Never wait for a queue or allow a report/probe task to monopolize the robot loop.

### Shared contract

Reports, probes, telemetry, lifecycle maintenance, and later evidence work use the same task, queue, result, and accounting model. Local variants are a source of drift and should be avoided.

## Work model

### Work classes

The initial classes are:

- `MAINTENANCE`
- `DIAGNOSTIC`
- `REPORT`
- `OPERATOR_REQUEST`
- `HOUSEKEEPING`

Examples:

- lifecycle refresh and evidence aging are `MAINTENANCE`;
- sampled telemetry is `DIAGNOSTIC`;
- an active presence probe is an `OPERATOR_REQUEST`;
- report chunks are `REPORT`; and
- expired-state cleanup is `HOUSEKEEPING`.

### Priority

Tasks use `HIGH`, `MEDIUM`, or `LOW` priority. Priority affects dispatch order. Queue ownership remains with the work class.

### Work units

A work unit must finish within a tight, known bound. It can process one report chunk, one device snapshot, one probe step, or a small evidence-aging batch. It may not mean "run the complete report" or "probe every device."

### Lanes

The first version has one bounded lane for each work class. Each lane defines its capacity, duplicate/coalescing rule, priority treatment, and normal service share.

## Scheduling

### Cycle budget

Every robot cycle reserves only part of its 20 ms window for background work. The manager supports a maximum number of work items and, if enabled, a soft monotonic-time limit. It stops dispatching when either limit is reached.

The values must be centrally configured, measured, and conservative by default.

### Default order

The initial policy is:

1. `MAINTENANCE/HIGH`
2. `OPERATOR_REQUEST/HIGH`
3. `DIAGNOSTIC/MEDIUM`
4. `REPORT/MEDIUM`
5. `HOUSEKEEPING/LOW`

This is a default, not a permanent priority claim. It must remain configurable and observable.

### Fairness

Within an equal-priority lane, tasks run round-robin. Old pending work receives an age-based boost. When the system is healthy, no lane may remain unserved indefinitely.

### Requeueing

Long activities are a sequence of small tasks. A presence probe submits its next device step. A report submits its next chunk. Telemetry submits its next device batch. Callers never spin inside one dispatch waiting to finish the larger job.

## Queue contract

Every queue is bounded, non-blocking for producers, safe for repeated periodic use, and instrumented.

A submission result includes at least:

- status code;
- lane name;
- queue depth after the attempt;
- whether the request was coalesced; and
- a rejection reason when applicable.

On rejection, a producer may drop and count the request, merge it into an existing pending task, mark itself dirty for a later retry, show a warning, or reduce output detail. It may not assume acceptance, wait for room, or recursively retry.

Replaceable work must coalesce. For example, multiple pending lifecycle refreshes collapse into one request. Ordered probe steps for different devices must not be merged when that would change their meaning.

## Task interface

Each task exposes a common contract:

- task identity;
- work class;
- priority;
- expected cost category;
- optional coalescing key; and
- `runOneSlice(...)`.

`runOneSlice(...)` returns one of:

- `COMPLETE`
- `PARTIAL_REQUEUE`
- `FAILED`
- `SKIPPED_SOURCE_UNAVAILABLE`
- `SKIPPED_PRECONDITION`

The result also records work units consumed, an optional follow-up task, and a bounded warning or error note.

## Dependencies and failures

Tasks may depend on CAN power, passive-observer freshness, REST availability, or vendor API responsiveness. The scheduler does not diagnose those domains itself. A task reports that its source is unavailable or stale and asks to retry later.

The manager accounts for that result. It does not treat it as a crash, and it does not allow it to consume the whole cycle repeatedly.

## Overload behavior

When pressure rises or the loop is close to its budget, the manager responds in this order:

1. Coalesce replaceable work.
2. Skip low-priority work for the current cycle.
3. Reject new low-priority submissions.
4. Ask verbose producers to reduce detail.
5. Publish the overload state.

It maintains counters for accepted, coalesced, rejected-full, rejected-duplicate, rejected-disabled, run, completed, requeued, failed, skipped, and budget-exhausted work. It also tracks maximum queue depth and oldest pending age for every lane.

At minimum, those facts appear in robot status text and the host diagnostics state already used by the UI.

## Integration

### Phase 1: establish the manager

Add the manager and migrate work that already has a bounded unit:

- report chunk emission;
- active presence-probe steps; and
- lifecycle-refresh maintenance.

Preserve current operator behavior as closely as possible.

### Phase 2: telemetry

Move optional sampled telemetry to manager-owned round-robin work. This matters at larger device counts and during CAN faults.

### Phase 3: evidence and diagnosis

Route robot-side evidence maintenance and diagnosis passes through the manager.

### Phase 4: remove duplicate budgets

Remove ad hoc component-level schedules where the manager owns the same decision. A task may keep a local micro-bound, but the central manager remains the authority for total periodic background work.

## Evidence fusion relationship

Evidence fusion expects bounded ingestion, bounded evaluation, freshness-aware degradation, drop accounting, and source-health reporting. The work-slice manager is the robot-side execution mechanism for any evidence-related task that runs there.

This does not require the evidence engine itself to run on the roboRIO.

## Failure cases

### Full queue

Full queues are expected during an error storm or a poor producer. The request is rejected explicitly, counters rise, and the producer chooses a defined fallback.

### Persistent source timeout

Missing or unpowered CAN devices are expected. Their tasks stay bounded and cannot monopolize the budget. Retry policy is throttled or age-managed.

### Producer defect

A producer that submits unique non-coalescing work every cycle can fill its lane, but it cannot grow memory without limit. Its rejection counters identify it.

### Slow task

The first version records task identity and slow-task timing. A later version may quarantine a task, but this feature does not depend on that policy.

## Diagnostics

The manager publishes:

- total pending work;
- queue depth and oldest age by lane;
- recent rejections;
- recent budget exhaustion;
- top rejected submitters; and
- slow task types and runtimes when timing is available.

Recommended surfaces are robot health/status output, the runtime status snapshot, and a host UI inspector.

## Configuration

Central configuration covers:

- maximum work items per cycle;
- optional soft time budget;
- lane capacities;
- normal service shares;
- test-only coalescing controls; and
- diagnostics verbosity.

Defaults must favor control responsiveness over background completeness.

## Testing

### Unit tests

Cover queue-full rejection, coalescing, round-robin behavior, priority ordering, age-based fairness, requeue progression, source-unavailable results, and dispatch stopping at the cycle budget.

### Fault-state regression

Run robot-side checks with healthy hardware, one disconnected CAN device, several disconnected devices, no CAN-bus power with the roboRIO still powered, and an active presence probe during a missing-device condition.

Expected results:

- no single-cycle freeze;
- bounded queue growth;
- visible overload and rejection accounting; and
- host surfaces remain responsive enough to recover.

### Load regression

Use synthetic producers that submit work faster than it can run. Confirm bounded memory, explicit rejections, and no producer blocking.

## Migration rules

- Preserve safety behavior.
- Keep changes small and independently reversible.
- Add a narrow regression test for every migrated producer.
- Preserve existing operator workflows unless a separate behavior change is approved.

If a migrated path destabilizes the robot loop, it must be possible to revert that migration without removing the manager or other completed migrations.

## Open decisions

SID_QUESTION: Should the first implementation use only a maximum item count, or also a soft monotonic-time limit?

SID_QUESTION: Should operator-request work outrank maintenance, or should maintenance remain first to protect core-state freshness?

SID_QUESTION: Which sampled telemetry reads are mandatory every loop and must stay outside the manager?

## Recommended first implementation

Start with bounded lanes, report chunks, presence-probe steps, lifecycle refresh, queue statistics, and explicit rejection handling. Test healthy CAN, one missing device, and no CAN power before moving telemetry under the manager.

## Tradeoffs

A central manager adds structure, but it replaces a collection of unrelated local throttles. Some views will converge over several cycles instead of immediately. That is acceptable if freshness is explicit and the robot remains responsive. A rejected request is safer than hidden overload.

## Future extensions

- Per-task runtime histograms.
- Temporary suppression or quarantine for repeatedly slow tasks.
- Budget tuning by robot mode.
- A live host-side scheduler inspector.
- A compatible scheduler abstraction for host-side work where it earns its complexity.
