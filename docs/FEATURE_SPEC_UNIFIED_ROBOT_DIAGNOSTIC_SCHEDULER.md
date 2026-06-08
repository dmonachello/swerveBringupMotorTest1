# Feature Spec: Unified Robot Diagnostic Scheduler

## Purpose

Define a future robot-side scheduler for diagnostics and support work so the system can scale to larger device counts without overrunning the WPILib `20 ms` control loop.

## Status

This spec is for future consideration.

It does not describe current behavior.

Current pragmatic direction is to keep `activePresenceProbe` as an explicit one-shot operator action and avoid periodic robot-side probe execution until this scheduler is designed and instrumented well enough to trust.

## Problem

The current robot runtime performs diagnostics and support work inside the normal robot loop.

That work has grown to include:

- sampled telemetry
- lifecycle refresh
- runtime snapshot gathering
- active presence probe support
- evidence/cache maintenance

This model does not scale well as device count grows.

A configuration with only a few devices already shows loop pressure. A future configuration may include up to roughly `20` motors plus supporting devices.

The real problem is peak per-loop cost, not just average cost over time.

Even if a full probe sweep happens only once every few seconds, one expensive probe slice can still overrun the single `20 ms` loop in which it runs.

## Goals

- Prevent control-loop overruns caused by diagnostics/support work.
- Preserve useful UI and diagnostic freshness.
- Scale to large device counts.
- Keep the scheduling model understandable to operators and developers.
- Make diagnostic work fail soft when budget is exhausted or scheduler work misbehaves.

## Non-Goals

- This scheduler does not own actuation or control logic.
- This scheduler does not replace WPILib mode methods such as `teleopPeriodic()`.
- This scheduler does not define the separate `usable/degraded/failed` model.
- This scheduler does not change the meaning of explicit operator tests.

## Scope

This is a unified robot-side scheduler for diagnostics and support work only.

It is intended to govern total robot-side diagnostics/support execution, not just a narrow telemetry helper.

In scope:

- sampled telemetry
- lifecycle-support snapshot work
- active-probe refresh eligibility
- evidence aggregation and cache update
- any other robot-side diagnostic/support work that would otherwise execute directly in the loop

Out of scope:

- none explicitly

SID_COMMENT: Current implementation still mixes unscheduled diagnostic work into normal loop paths. This spec is intended to replace that with one authoritative scheduler.

## Core Principles

- The scheduler uses a strict robot-side time budget.
- The scheduler is device-based.
- Each device visit may contain several ordered stages.
- Devices under active observation or active test work get serviced more often than idle devices.
- Devices not being observed should not be serviced.
- Unfinished work resumes later rather than bursting through the loop budget.
- If budget is exhausted, remaining work is deferred in round-robin order.
- If scheduler work fails in a loop, diagnostics/support work for that loop is skipped and the robot stays alive.

## Hard Budget

- Loop period: `20 ms`
- Initial scheduler budget: `2 ms` per loop
- Budget type: fixed milliseconds

Rationale:

- Loop overruns are the show-stopper.
- A fixed-millisecond budget is easier to reason about and debug than a percentage-only rule.

## Scheduling Model

### Unit of Scheduling

The scheduler operates per device.

Each visit to a device may include several ordered stages.

### Ordered Device Visit Stages

Each device visit uses this stage order:

1. lifecycle-support snapshot
2. sampled telemetry
3. active-probe refresh eligibility
4. evidence aggregation and cache update

### Resumable Visits

If a device visit cannot finish all stages within the available budget, unfinished work resumes on the next visit to that device.

The scheduler must maintain a per-device stage cursor.

### Failure During a Visit

If a stage is blocked or too expensive to complete in the current visit, that device visit fails for now and the scheduler moves on to the next eligible device.

The scheduler must not try to continue later stages for that device during the same visit after a blocking stage fails.

## Observation Tiers

The scheduler classifies devices into observation tiers.

### Hot Devices

A device is hot when any of these are true:

- selected in the UI
- member of the currently selected group
- under active manual test
- part of a running DSL test
- recently had a lifecycle transition
- recently had an error, reset, or stale event

### Warm Devices

A device is warm when:

- it is a member of `active-group` and `active-group` is not the currently selected group

Future work may add more warm triggers.

### Cold Devices

Cold devices receive no service.

A device is cold when it is not actively being observed or run.

## Budget Split

Use a fixed budget split:

- `80%` hot
- `20%` warm

This is intended to protect warm devices from starvation while still prioritizing actively observed devices.

## Fairness and Starvation

### Round Robin

Within each tier, device visits are handled in round-robin order.

### Warm Starvation Protection

Warm devices must also have a max allowed service age so they cannot be skipped forever.

This means the scheduler uses both:

- round-robin ordering
- starvation max-age enforcement

## Stage Freshness Targets

Each device stage must have a freshness target.

Examples:

- sampled telemetry target age
- lifecycle-support snapshot target age
- active-probe cache target age
- evidence/cache update target age

Exact first-pass values are not yet locked in this spec.

SID_QUESTION: What should the default freshness targets be for each stage in first implementation?

## Configuration and Rollout

### Ownership

Scheduler policy should be configurable from UI preferences.

SID_COMMENT: The actual persistence backing for those preferences may later live in a profile, settings file, or robot-side config layer, but the operator-facing source of control should be UI preferences.

### First-Pass Configurables

At minimum, first pass should allow configuring:

- total scheduler budget in milliseconds
- hot/warm split percentage
- per-stage freshness targets
- warm-device starvation max age
- tier transition ages for “recent lifecycle transition” and “recent error/reset/stale event”

### Mode Switching

The scheduler should be switchable for rollout.

Required modes:

- legacy full-scan behavior
- scheduled behavior

SID_QUESTION: What exact operator-facing mode names should be used in the UI?

## Failure Handling

### Budget Exhaustion

When the scheduler budget is exhausted in a loop:

- remaining items are deferred
- work resumes later in round-robin order

### Scheduler Failure

If the scheduler itself fails or misbehaves during a loop:

- diagnostics/support work for that loop is skipped
- the robot remains alive
- control/actuation paths are unaffected

### Invalid Internal Behavior

The scheduler must never be allowed to crash the robot because a support task exceeded budget or hit an exception.

## Observability

The scheduler must have visible debugging and operator-facing status.

### Required Surfaces

Surface scheduler information in:

- UI
- CLI
- NT/status
- console warnings

### Required Debug Data

Useful debugging stats must be shown.

At minimum, expose:

- total budget
- budget used in the last loop
- hot device count
- warm device count
- deferred visit count
- skipped visit count
- overload count
- per-device last service age
- per-device current stage cursor
- per-device tier

SID_QUESTION: Which of these should be shown in normal UI versus a dedicated debug panel?

### Repeated Overload Signaling

When overload happens repeatedly, show it in:

- console
- NT/status
- UI banner

## UI Presentation

### Not Observed Devices

Devices that are intentionally not being serviced must be visibly marked as “not being observed.”

Acceptable approaches include:

- different color
- an asterisk marker
- other explicit visual indicator

The goal is to make it clear that stale or frozen data can be intentional, not necessarily a fault.

### Freshness and Service Age

UI should surface enough freshness information that users understand:

- whether data is live
- whether data is cached
- whether a device is intentionally cold

## Interaction With Active Presence Probe

This spec exists largely because periodic robot-side active-probe work may be too expensive to run opportunistically inside the control loop without a proper scheduler.

Current short-term recommendation:

- keep `activePresenceProbe` as a manual one-shot operator action
- display probe age prominently
- decrease the importance of probe evidence as it ages
- rely on live telemetry and lifecycle state for ongoing status

Future scheduled model:

- active-probe refresh becomes just one stage in a budgeted device visit
- it is eligible only when the device is hot or warm
- it must obey the same strict budget and defer rules as other diagnostic work

## Why This Exists

This discussion was triggered by loop overruns and audible Falcon restart chirps during bringup.

The most likely immediate trigger was increased robot-side probe work, but the broader architectural issue is that diagnostics/support work is not yet governed by a single hard-budget scheduler.

This spec records the future direction without forcing an immediate implementation.

## Tradeoffs

### Advantages

- Predictable loop cost
- Better scaling to large device counts
- Understandable prioritization model
- Easier debugging of overload behavior

### Costs

- More scheduler state to maintain
- More explicit freshness handling in UI
- More complexity than immediate full-scan reads
- Potentially older data for warm and cold devices

## Future Extensions

- Per-device timing instrumentation and histograms
- Dynamic cost estimation per stage
- Device-class-specific stage sets
- Smarter hot/warm promotion and decay rules
- A richer scheduler debug panel
- Automatic probe cadence tuning based on measured cost

## Open Questions

SID_QUESTION: What should the default freshness targets be for each stage in first implementation?

SID_QUESTION: What exact operator-facing mode names should be used in the UI?

SID_QUESTION: Which scheduler debug fields should appear in the normal operator UI versus a dedicated debug panel?

