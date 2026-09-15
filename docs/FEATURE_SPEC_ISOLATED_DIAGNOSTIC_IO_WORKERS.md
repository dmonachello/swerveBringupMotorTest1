SPEC_STATUS: PROPOSED

# Feature spec: isolated diagnostic I/O workers

## Purpose

Move potentially blocking, non-control vendor and HAL diagnostic reads out of the roboRIO's 20 ms periodic thread while keeping device-state reporting accurate, bounded, and recoverable.

This feature is a companion to [the central work-slice manager](FEATURE_SPEC_CENTRAL_WORK_SLICE_MANAGER.md). The manager decides when diagnostic work may be submitted. This feature defines how risky hardware reads execute after submission.

## Problem

CAN devices that are unpowered, disconnected, misconfigured, or overloaded can cause CTRE, REV, and WPILib/HAL read calls to wait for a timeout. The vendor library may also print an error for each failure.

If these reads occur in `robotPeriodic()`, they can overrun the 20 ms control deadline. Repeating the reads can amplify the failure through CAN traffic, error printing, report work, and REST state requests.

The robot must remain responsive when all CAN devices lose power, when one device disappears, or when a device returns after a failure.

## Goals

- Keep motor control, safety handling, and Driver Station mode processing on the robot periodic thread.
- Execute risky diagnostic reads outside that thread.
- Isolate one vendor family or API failure from other diagnostic work.
- Bound every queue, worker count, retry rate, and retained result set.
- Treat a completed read result as an observation with a timestamp, not timeless cached truth.
- Stop normal diagnostic polling promptly when fresh passive evidence shows the CAN bus is unavailable.
- Recover gradually when passive CAN traffic returns.
- Preserve raw failure information for evidence, UI, CLI, and CAN Fault Finder without requiring console spam.
- Make overload, rejected work, stuck workers, cooldowns, and stale observations visible.

## Non-goals

- Moving actuator writes, test outputs, safety stops, or command-scheduler work off the robot thread.
- Creating one thread per device.
- Assuming a worker can interrupt or cancel a native/HAL call already in progress.
- Treating the last successful read as proof that a device is currently present.
- Increasing diagnostic CAN traffic merely to obtain faster status updates.
- Hiding vendor-library failures from diagnosis.

## Design Principles

### Control Thread Ownership

The 20 ms robot thread owns control outputs, safety state, Driver Station state, test progression, and submission of non-critical diagnostic work. It must never wait for a diagnostic worker result.

### Worker Ownership

A worker owns only diagnostic reads for its assigned API family. It returns immutable observation results through a bounded completion channel. It must not issue motor commands or modify lifecycle ownership.

### One Shared Admission Gate

Workers must not accept independent unlimited work. The central work-slice manager is the only normal producer of diagnostic-read requests. REST, reports, probes, and UI state builders request work through the same admission path.

### Freshness Is Data

Every result includes observation time, completion time, source, result status, and expiry policy. A previous successful read becomes stale as its age grows. Stale data may provide history but cannot override fresh negative passive or runtime evidence.

### Fail Quietly, Report Deliberately

The system captures failures as structured observations and emits rate-limited summaries through the shared report runner. It does not create direct print bursts from periodic code.

## Worker Families

The initial worker count must remain small. Workers are per I/O family, not per device.

| Worker | Owned reads | Notes |
| --- | --- | --- |
| WPILib power worker | `PowerDistribution` PDP and PDH snapshot reads | Isolates blocking HAL power-distribution reads. |
| CTRE status worker | Talon FX, CANcoder, Pigeon, and CTRE status-signal refreshes | Serializes CTRE diagnostic refreshes. |
| REV status worker | SparkMax/Flex diagnostic reads | Serializes REV diagnostic reads. |
| NI/local input worker | DIO, roboRIO, and other local non-CAN reads if they prove expensive | May remain synchronous if measurements show it is safe. |

No worker is added merely because a device type exists. A new worker requires a measured blocking or isolation need.

## Request Contract

Each diagnostic read request contains:

- `requestId`: unique identifier for accounting and correlation.
- `deviceKey`: configured label plus canonical vendor, type, interface, bus, and address when available.
- `workerFamily`: the required worker family.
- `readKind`: light snapshot, full snapshot, health check, or recovery probe.
- `requestedAtMonotonicMs`: submission time.
- `deadlineMonotonicMs`: latest useful completion time.
- `priority`: maintenance, operator request, or explicit recovery probe.
- `coalesceKey`: stable key used to combine duplicate pending work.
- `reason`: lifecycle refresh, REST request, active probe, DSL support, or recovery.

Submission returns one explicit result:

- `ACCEPTED`
- `COALESCED`
- `REJECTED_QUEUE_FULL`
- `REJECTED_DUPLICATE`
- `REJECTED_BUS_UNAVAILABLE`
- `REJECTED_COOLDOWN`
- `REJECTED_INVALID`

Callers must handle rejection without retrying in a tight loop.

## Queue Rules

Each worker has one bounded request queue and one bounded completion queue.

- Pending requests with the same `coalesceKey` are merged rather than duplicated.
- A full queue rejects low-priority work first; it does not evict an in-flight request.
- Expired queued requests are discarded before execution and counted as expired.
- Completion queues retain only the latest result per device/read-kind plus bounded diagnostic history.
- Queue depth, coalesced count, rejection count, expiry count, and oldest-request age are published in runtime diagnostics.

## Global CAN Admission Gate

### Bus-Unavailable Entry

The passive CAN observer may declare the configured CAN bus unavailable when fresh observations show a broad absence pattern, such as:

- configured CAN devices have no recent device-emitted traffic;
- `Exist Pkts` are zero or no longer increasing for the affected devices; and
- the observer itself remains healthy enough to make that conclusion.

This is a bus-level observation, not proof of a specific electrical cause.

On entry:

- normal CTRE, REV, and WPILib-power polling stops;
- queued normal CAN diagnostic reads are expired or coalesced away;
- no new normal requests are accepted;
- a currently in-flight native call is allowed to finish or time out naturally;
- each affected device receives a fresh bus-unavailable evidence observation;
- local roboRIO, DIO, USB, and Driver Station observations continue normally.

### Recovery Entry

New passive CAN traffic and increasing device-emitted `Exist Pkts` clear the bus-unavailable gate. Recovery does not immediately poll every configured device.

The scheduler submits bounded round-robin recovery probes:

- one device family or device at a time;
- lower rate than normal lifecycle polling until a healthy result is observed;
- no parallel burst across workers when CAN health remains degraded.

A direct successful read clears the cooldown for that device. Failed devices remain in cooldown and are retried at their scheduled recovery time.

## Cooldown Policy

Cooldown is generic device-read state, keyed by canonical device identity and read kind.

After a read fails:

- record the failure timestamp, failure class, and message fingerprint;
- return a structured failed observation;
- reject or defer duplicate reads until that device's next eligible time;
- increase the retry interval for repeated same-class failures, up to a configured maximum;
- reset or reduce the interval after a direct successful read or a credible passive recovery observation.

The initial PDP-specific cooldown is a predecessor, not the final shared mechanism. The new shared cooldown contract must replace per-device ad hoc policies only after regression coverage proves equivalent or safer behavior.

Cooldown reduces retry load. It does not mark the device present, absent, or healthy by itself.

## Completion Contract

Workers emit immutable diagnostic observations. Each includes:

- target identity and configured-label match confidence;
- source family and worker identity;
- observation and completion monotonic timestamps;
- result: `SUCCESS`, `TIMEOUT`, `UNAVAILABLE`, `FAILED`, or `EXPIRED`;
- snapshot payload when successful;
- normalized failure class and a bounded message summary when unsuccessful;
- elapsed read time;
- cooldown state after completion;
- correlation ID linking request and completion.

The evidence-fusion service consumes these observations using the normal evidence-block API. Device views consume the fused state and preserve observation freshness.

## Thread Safety and Ordering

- No vendor device may have simultaneous diagnostic reads from two worker families.
- Diagnostic reads for a worker family are serial.
- Actuator writes remain on the robot thread.
- Before implementation, each vendor API used by a worker must be reviewed for concurrent read/write guarantees.
- If a vendor API is not proven safe for concurrent read and write, its diagnostic requests must be scheduled only during a safe ownership window or use a robot-thread bounded alternative.
- A REST request never performs a direct hardware read. It requests an observation and returns the latest completed observation with freshness metadata.

## Timing and Overload

The central work-slice manager controls submission rate. Workers isolate latency but do not create extra CAN capacity.

- The robot periodic thread uses a fixed submission budget per cycle.
- Workers use a global CAN diagnostic in-flight policy, normally allowing one risky CAN transaction at a time while bus health is degraded.
- Worker execution duration is measured and published.
- A worker considered stuck remains occupied; the system does not create replacement threads.
- Repeated worker stalls surface a source-health degradation and operator-visible warning.

## Operator Surfaces

The UI, CLI, and diagnostics reports share one runtime state contract containing:

- bus-admission state: normal, degraded, or unavailable;
- per-worker queue depth, in-flight request, last completion age, and rejection counters;
- per-device latest read result, observation age, cooldown remaining, and failure summary;
- whether a shown value is direct/current, fresh completed, stale historical, or unavailable;
- whether the system is recovering through bounded round-robin probes.

The CAN Fault Finder may use these observations as evidence, but it must state when a conclusion is based on broad bus unavailability rather than a device-local direct failure.

## Failure Scenarios

### One disconnected SparkMax

- Passive CAN indicates the configured SparkMax has no recent device-emitted traffic while other devices remain visible.
- The REV worker may attempt one scheduled diagnostic read.
- A timeout starts that device's cooldown.
- Other REV devices and other worker families remain eligible within global CAN limits.
- The device becomes increasingly stale if no recovery evidence arrives.

### All CAN devices unpowered

- Passive observer publishes broad bus-unavailable evidence.
- Normal CTRE, REV, and PDP/PDH requests stop.
- In-flight calls may finish with timeouts, but no replacement requests accumulate.
- The robot remains responsive for local, Driver Station, and UI command handling.

### CAN power returns

- Passive traffic clears the admission gate.
- The scheduler issues bounded round-robin recovery probes.
- Successful direct reads clear device cooldowns.
- Remaining failed devices are isolated and retried sparsely.

### REST polling is frequent

- REST reads completed runtime state only.
- It cannot cause a synchronous full profile snapshot or add unbounded hardware-read work.
- Its request is coalesced with an already pending lifecycle or probe request for the same device/read-kind.

## Testing

### Unit Tests

- queue capacity, rejection, coalescing, expiry, and counters;
- cooldown growth, reset, and freshness behavior;
- bus-unavailable entry and recovery admission behavior;
- one-worker-per-family serialization;
- global degraded-bus in-flight cap;
- evidence blocks emitted for success, timeout, unavailable, and expired results.

### Simulation Tests

- fake workers with controllable completion delays;
- a permanently blocked worker with no replacement-thread creation;
- all-CAN-unpowered scenario with bounded queue depth and continued periodic progress;
- one-missing-device scenario with continued healthy-device service;
- recovery with round-robin, no-burst scheduling.

### Robot Validation

- measure periodic loop duration with all hardware healthy;
- remove one CAN device and confirm no recurring 20 ms overrun caused by diagnostic retries;
- remove CAN power and confirm REST/UI remain responsive and queues remain bounded;
- restore CAN power and confirm device status transitions from unavailable or stale through recovery to fresh direct evidence;
- verify motor control and safety stop behavior remain robot-thread owned.

## Rollout

1. Add worker interfaces, fake workers, queue accounting, and tests with no production read migration.
2. Route REST runtime-state reads through completed observations only.
3. Migrate PDP/PDH reads, preserving the existing cooldown behavior as a compatibility baseline.
4. Migrate CTRE status reads, then REV status reads after vendor thread-safety review.
5. Enable the global CAN admission gate and recovery scheduler behind a runtime diagnostic flag.
6. Compare loop timing, error volume, evidence quality, and recovery behavior against the current implementation before making the new path default.

## Tradeoffs

- Read results may arrive later than a synchronous snapshot, but they no longer jeopardize the control deadline.
- A single blocked worker can delay its family, which is preferable to stalling the whole robot.
- Strict degraded-bus admission can make direct state less immediately available, but avoids a self-amplifying timeout storm.
- More threads add synchronization requirements; bounded ownership and immutable completions keep that complexity contained.

## Future Extensions

- Per-vendor measured timeout and latency profiles.
- Adaptive worker rates based on CAN utilization and error rates.
- Explicit vendor API capability declarations for read/write concurrency safety.
- Persisted fault timelines built from worker completion observations.
- SystemCore-specific local I/O worker family if its APIs have different blocking behavior.
