# DSL Interpreter Runtime

## Purpose

Purpose: explain how a Robot Test DSL program becomes a robot-side test and how that test advances inside the 20 ms robot loop.

This document is written for students and mentors who want to understand what the DSL runner is doing, not just how to write DSL syntax.

## Short Version

The DSL is not a normal script that runs top-to-bottom once.

It is compiled on the host into a normalized JSON test model. The robot loads that model and runs it as a small state machine.

During teleop, the robot normally gets one turn about every 20 ms. On each turn, the active DSL test:

1. writes commanded outputs from `set`
2. samples sensor/controller signals
3. evaluates conditions
4. updates latched proof from `require`
5. decides whether the test should pass, fail, or keep running

The runner never sleeps, waits in a loop, or blocks until a condition becomes true. Time passes because WPILib calls the robot periodic loop again and again.

## Two Sides

Purpose: separate what happens on the Driver Station computer from what happens on the roboRIO.

The DSL system has two main sides:

- Host side: the Python UI/CLI edits, imports, compiles, validates, and stores DSL tests.
- Robot side: the Java runtime loads normalized tests and executes them against real devices.

The raw source is the text students write:

```text
test "pigeon2_yaw_static_sanity"

device "pigeon 2"

init:
    clear "pigeon 2".faults

main:
    until timer.elapsed >= 8.0
    require "pigeon 2".yaw_delta_max_abs > 5.0
    require "pigeon 2".angular_velocity_z < 2.0
    require "pigeon 2".accel_z > 0.7
    require "pigeon 2".supply_voltage > 10.0
    require "pigeon 2".faults == false
```

The robot does not run that text directly. The host compiles it into normalized JSON with explicit phases, statements, references, literals, IDs, and condition types.

## Compile Time

Purpose: explain what the host compiler does before the robot ever runs a test.

Compilation happens on the host computer, not in the 20 ms robot loop.

At compile time, the host DSL compiler:

1. removes comments and blank logical lines
2. parses `test`, `device`, `init`, `main`, and `close`
3. converts statements into structured records
4. gives statements stable IDs such as `require_1` and `until_1`
5. turns references like `"FALCON 9".position_delta` into `{device, signal, text}`
6. turns literals like `8.0` and `false` into typed values
7. stores the original source, a source hash, and the normalized payload together

The stored config has this shape:

```text
dslTests
  testsByName
    <testName>
      source
      sourceHash
      runnable
      normalized
  testSets
  defaultSet
```

The important rule is:

- Source is what people edit.
- Normalized JSON is what the robot executes.
- Validation checks that the two match.

## Robot Load Time

Purpose: explain how the robot gets from config JSON to executable tests.

When the robot loads the active profile, the Java test registry reads the `dslTests` section from `bringup_system.json`.

For each runnable test in the selected test set, the robot creates a `DslBringupTest` from the normalized payload.

The robot does not recompile the DSL source at this point. It already has the structured model it needs.

Implementation pointers:

- `src/main/java/frc/robot/tests/BringupTestRegistry.java`
- `src/main/java/frc/robot/tests/dsl/DslModels.java`
- `src/main/java/frc/robot/tests/dsl/DslBringupTest.java`

## Start Time

Purpose: explain what happens once when the operator starts a test.

When the operator clicks `Run Selected` or sends `runTest`, the selected test is started once.

At start time, the DSL runner:

1. clears old run state from the previous run
2. resolves each declared `device` by label
3. checks whether each device is allowed to be used by the lifecycle/runtime state
4. creates the device if creation is allowed and needed
5. captures starting position values for position delta signals
6. captures starting IMU yaw, pitch, and roll for IMU delta signals
7. applies safe values before test-owned outputs begin
8. runs `init:` `clear` statements
9. runs `init:` `set` statements
10. initializes all `require` conditions as not-yet-satisfied
11. marks the test as `RUNNING`

This is why signals such as `position_delta`, `position_delta_max_abs`, `yaw_delta`, and `yaw_delta_max_abs` are run-scoped. Their zero point is captured at test start.

## 20 ms Turn

Purpose: explain what the interpreter does during each robot-loop turn.

WPILib calls `teleopPeriodic()` on the robot about every 20 ms. The robot code uses that call to advance reports, bindings, and active tests.

For the active DSL test, one turn looks like this:

```text
if test is running:
    apply main set statements
    sample condition signals
    evaluate raw condition truth
    update stable filters
    latch require conditions
    check abort
    check success
    check until
    if terminal:
        stop test
```

The order is fixed. Source line order inside `main:` does not control this order.

So these two source files mean the same thing:

```text
main:
    set "FALCON 9".output = 0.25
    until timer.elapsed >= 2.0
    require "FALCON 9".position_delta > 10.0
```

```text
main:
    require "FALCON 9".position_delta > 10.0
    until timer.elapsed >= 2.0
    set "FALCON 9".output = 0.25
```

The interpreter treats `main:` as a rule set, not as a sequential script.

## Set Statements

Purpose: explain how outputs are commanded safely and repeatedly.

A `main:` `set` statement is applied every turn while the test is running.

Example:

```text
main:
    set "FALCON 9".output = 0.333
```

That does not write once. It means the test owns that output and keeps commanding it each turn until the test ends or another rule stops it.

Signal-driven sets are also resolved each turn:

```text
set "SPARKMAX/NEO 25".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0
```

Each turn, the runner:

1. reads `controller0.leftY`
2. applies deadband
3. multiplies by the scale
4. checks whether the target value is in range
5. writes the target output

If the source signal is unavailable during `main:`, the default value is used. If a default fallback is still active when an `until` condition ends the test, the test fails with fallback-active status.

## Signal Sampling

Purpose: explain what values the interpreter reads each turn.

The runner samples the signals used by conditions in:

- `abort`
- `success`
- `until`
- `require`

It also reads source signals needed by signal-driven `set` statements.

Signals come from device wrappers through `readDslSignal()`. Different device types expose different signals:

- motors expose output, current, velocity, position, temperature, and fault-like signals
- external encoders expose absolute position and delta signals
- IMUs expose yaw, pitch, roll, angular velocity, acceleration, voltage, and faults
- controllers expose button and axis signals
- the built-in timer exposes `timer.elapsed`

Computed signals are handled by the interpreter:

- `timer.elapsed` is current FPGA timestamp minus test start timestamp
- `position_delta` is current position minus start position
- `yaw_delta` is current yaw minus start yaw
- `*_max_abs` keeps the largest absolute value observed during the run

## Conditions

Purpose: explain how `abort`, `success`, `until`, and `require` are evaluated.

Every condition first becomes a raw true-or-false value.

Examples:

```text
"FALCON 9".current > 40.0
"pigeon 2".faults == false
lmtSw0.pressed
encoder1.position between 100 120
```

If a condition uses `stable`, the raw value must stay true continuously for the requested time before the effective condition becomes true.

Example:

```text
require "FALCON 9".velocity > 1000 stable 0.25
```

That does not block for 0.25 seconds. It checks on each turn whether the raw condition is still true and accumulates stable time across turns.

## Require Latching

Purpose: explain why `require` means evidence, not constant truth.

`require` is latched proof.

Once a `require` condition becomes true, it is recorded as satisfied. It does not need to remain true until the end of the test.

Example:

```text
main:
    set "FALCON 9".output = 0.25
    until timer.elapsed >= 2.0
    require "FALCON 9".velocity > 1000
```

This means:

- run the motor for up to 2 seconds
- pass only if velocity exceeded 1000 at least once before the `until` ended the test

It does not mean:

- velocity must still be above 1000 at exactly 2 seconds

This distinction matters for mechanical tests because a sensor can prove motion briefly and then slow down before the stop boundary.

## Terminal Priority

Purpose: explain how the interpreter decides the final result.

After `require` latching, the runner checks terminal conditions in this order:

```text
abort > success > until
```

`abort` wins because it represents a forbidden or unsafe condition.

`success` comes next because it represents enough proof to finish immediately.

`until` is the normal stop boundary. When an `until` condition becomes true, the test stops and checks whether all `require` conditions were satisfied.

Result behavior:

- `abort` true means fail now.
- `success` true means pass now.
- `until` true and all requirements satisfied means pass.
- `until` true and any requirement missing means fail.
- `until` true while signal-set fallback is active means fail.

## Stop Time

Purpose: explain cleanup and output safety.

When a DSL test ends, the runner calls `stop()` once.

Stop time does this:

1. marks a still-running test as interrupted if it was stopped externally
2. runs `close:` `clear` statements
3. runs `close:` `set` statements
4. applies safe values to writable signals
5. marks the run finalized so cleanup is not repeated

For motor outputs, the safe value is normally zero. The DSL runtime applies that final safety behavior itself, so the higher-level test runner does not need to apply an extra global stop for DSL tests.

`unsafe-exit` is an explicit exception for a writable signal. Use it carefully because it means final safing skips that signal.

## Timing

Purpose: explain what "20 ms" means in practice.

The robot targets a 20 ms periodic loop, but a turn can run late if code takes too long.

The DSL interpreter is designed to do bounded work each turn:

- no sleeps
- no busy waits
- no long loops waiting for hardware
- no large console print bursts
- no parsing DSL source during the loop

Reports are printed through a shared report runner so long text output is broken into chunks over multiple cycles.

If the Driver Station reports a loop overrun, it means the robot loop took longer than the 20 ms budget. The DSL runner should stay small enough that it is not the normal cause of overruns.

## REST Output Timing

Purpose: explain why command output can appear one tick ahead of samples.

The REST `runTest` command starts the test immediately and returns a run snapshot.

That first response can show:

```text
state = running
lastSamples = {}
```

That is normal. The test has started, but the next periodic turn may not have sampled conditions yet.

After the next `teleopPeriodic()` update, `lastSamples`, aggregate signals, and condition details are refreshed.

## Example Walkthrough

Purpose: show a complete simple test as a timeline.

Example source:

```text
test "falcon9_move_150_rotations"

device "FALCON 9"

main:
    set "FALCON 9".output = 0.333
    until "FALCON 9".position_delta > 150.0
    require "FALCON 9".position_delta > 10.0
```

At compile time:

- the host creates normalized records for one device, one set, one until, and one require
- the normalized payload is saved with the source

At start time:

- the robot finds `FALCON 9`
- the robot creates or reuses the device wrapper
- the robot captures the starting position
- the test starts running

On early turns:

- output is set to `0.333`
- current position is sampled
- `position_delta` is computed from the start position
- `require position_delta > 10.0` is still false
- `until position_delta > 150.0` is still false

Once the Falcon moves more than 10 rotations:

- the `require` latches true
- the test keeps running because `until` is still false

Once the Falcon moves more than 150 rotations:

- the `until` becomes true
- all `require` conditions are satisfied
- the test result becomes pass
- final safe output is applied

## Common Misunderstandings

Purpose: avoid mistakes when explaining or authoring tests.

- `main:` is not line-by-line script execution.
- `set` in `main:` means continuously command every turn.
- `require` means "this evidence happened at least once."
- `until` means "normal stop boundary."
- `stable` does not pause the robot code.
- `timer.elapsed` is computed from timestamps; it does not sleep.
- Raw source is not parsed on the robot during each loop.
- The first `runTest` response may be before the first sample update.

## Implementation Pointers

Purpose: map the explanation to code for students who want to inspect the implementation.

Host compiler and storage:

- `tools/common/robot_test_dsl/compiler.py`
- `tools/common/robot_test_dsl/serializer.py`
- `tools/common/robot_test_dsl/validator.py`

Robot model and registry:

- `src/main/java/frc/robot/tests/dsl/DslModels.java`
- `src/main/java/frc/robot/tests/BringupTestRegistry.java`

Robot runtime:

- `src/main/java/frc/robot/RobotV2.java`
- `src/main/java/frc/robot/BringupRuntime.java`
- `src/main/java/frc/robot/BringupCore.java`
- `src/main/java/frc/robot/tests/dsl/DslBringupTest.java`
- `src/main/java/frc/robot/tests/BringupTestContext.java`

Device signal hooks:

- `src/main/java/frc/robot/devices/DeviceUnit.java`
- `src/main/java/frc/robot/devices/DeviceDslSupport.java`
- `src/main/java/frc/robot/tests/dsl/signals/`

## Tradeoffs

Purpose: explain why the system is designed this way.

Compiling on the host keeps parsing and validation out of the robot control loop.

Executing normalized JSON keeps the robot runtime simple and predictable.

Evaluating a rule set every turn fits the WPILib periodic model better than trying to run a blocking script.

The tradeoff is that students must think of DSL tests as state machines, not as normal programs that execute line by line.

## Future Extensions

Purpose: list improvements that could make the runtime easier to teach and debug.

- Add a UI view that shows the normalized form beside the source.
- Add a live "current tick" debug panel showing sampled values and condition truth.
- Add a timeline view for when each `require` latched.
- Add a diagram showing source, normalized JSON, robot registry, and 20 ms update flow.
