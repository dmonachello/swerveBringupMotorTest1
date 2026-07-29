# Regression Runner User Guide

## 1. Purpose

Purpose: explain how to run the maintained regression bundles for this repo,
both from Codex and directly from the command line.

This guide is for:

- developers changing Java, Python, CLI, DSL, topology, or config behavior
- operators who want a repeatable local verification pass
- reviewers who need to understand what each suite covers

This guide covers:

- what the regression runner is
- how the Codex skill maps to the runner
- how to run suites directly from the shell
- what files are produced
- how baselines and failure history work
- how to refresh expected outputs safely

## 2. What This Feature Is

The regression runner is the unified entrypoint for the repo's maintained
regression bundles.

Use this command:

```text
python tools/can_nt/scripts/run_regressions.py
```

The runner replaces ad hoc use of several individual scripts with one command
surface that:

- selects a named suite
- runs the canonical commands for that suite
- compares results to checked-in baselines
- prints feature coverage while running
- updates local failure-oriented history

## 3. What the Codex Skill Is

The Codex skill `regression-runner` is a thin wrapper over the same unified
runner.

That means:

- the skill does not use a separate test engine
- the skill does not have separate hidden suites
- the skill and shell command should give the same result for the same suite

Skill file:

- [.codex/skills/regression-runner/SKILL.md](../.codex/skills/regression-runner/SKILL.md)

## 4. When to Use It

Use the regression runner when you need to:

- check whether recent changes broke existing behavior
- run the normal local pre-push verification pass
- run a narrower targeted suite such as `dsl`, `cli`, or `java`
- run the connected non-motion robot path against a real roboRIO
- refresh checked-in baselines after an intentional behavior change

This project also has an explicit regression rule:

- do not test only the happy path
- for user-facing features, also test malformed input, missing input,
  unsupported input, and common operator mistakes
- for this project, success includes rejecting bad input safely and giving the
  user useful help in fixing the problem

## 5. Prerequisites

### 5.1 Local Suites

For normal local suites, you need:

- the repo checked out locally
- Python available on the machine
- Windows-friendly local environment
- Java / Gradle environment for Java tests

If Java tests are run on Windows, `JAVA_HOME` should point at the JDK root,
not the `bin` directory.

Example:

```text
C:\Users\Public\wpilib\2024\jdk
```

The runner also normalizes `JAVA_HOME` automatically if the shell points it at
`...\jdk\bin`.

### 5.2 Connected Robot Suite

For `robot-non-motion`, you also need:

- a reachable roboRIO
- the REST command endpoint available
- the roboRIO host or IP address

Example:

```text
--rio 172.22.11.2
```

## 6. Suites

The current maintained suites are:

- `local`
- `dsl`
- `cli`
- `java`
- `topology`
- `changelog`
- `robot-non-motion`
- `all`

### 6.1 `local`

Purpose: normal default local verification bundle.

Current coverage:

- DSL compiler / validator / signal-driven set / deadband
- DSL CLI import / validate / show
- controller device config
- connected command dispatch
- Java unit surface
- group-targeting regressions
- topology editor regressions
- changelog publication guard
- UI runtime workflow lockstep guard

### 6.2 `dsl`

Purpose: narrow pass for Robot Test DSL work.

Current coverage:

- Python DSL unit tests
- Java `DslBringupTest` runtime tests

### 6.3 `cli`

Purpose: narrow pass for CLI and config workflows.

Current coverage:

- DSL CLI tests
- group-targeting regressions
- config save path checks

### 6.4 `java`

Purpose: run the Java unit test surface.

### 6.5 `topology`

Purpose: run topology editor and topology metadata regressions.

### 6.6 `changelog`

Purpose: enforce the major-change changelog update policy.

Current coverage:

- changelog publication guard
- shared config API policy guard
- UI runtime workflow lockstep guard

### 6.7 `robot-non-motion`

Purpose: run the connected robot REST/UI regression without commanding motion.

### 6.8 `all`

Purpose: run all local suites.

By default, `all` does not include the connected robot suite.

To include the robot suite, you must also pass:

```text
--include-robot --rio <host-or-ip>
```

## UI Runtime Workflow Lockstep

Purpose: keep [CURRENT_UI_RUNTIME_RULES.md](./CURRENT_UI_RUNTIME_RULES.md) `Common Workflows` in lockstep with maintained regression coverage guidance.

This section must mirror the workflow headings in:

- [CURRENT_UI_RUNTIME_RULES.md](./CURRENT_UI_RUNTIME_RULES.md)

The automated guard compares the workflow subsection headings in both places.
If one list changes without the other, the regression fails.

### Manual Scope Activation While Inactive

Regression coverage:

- shared host-side scope-control tests
- selected/manual button-state tests where applicable

### Manual Membership Change While Scope Is Active

Regression coverage:

- shared scope-control gating tests
- active-group lock/editability tests

### Selected-Test Activation When Scope Is Inactive

Regression coverage:

- selected-test activate button-state tests
- selected-test runtime activation command-path tests

### Selected-Test Activation When The Active Scope Has The Wrong Membership

Regression coverage:

- shared selected-test activate gating tests
- UI auto-deactivate/scope-swap/runtime-activate workflow tests

### Selected-Test Run After Ready

Regression coverage:

- shared selected-test readiness tests
- `Run Selected` enablement synchronization tests

### Leaving The Tests Tab

Regression coverage:

- tests-boundary transition ownership tests
- manual owner-mode restoration tests

### Manual Right-Click Or Group Duty While Scope Is Active

Regression coverage:

- manual duty access-state tests
- controlled-scope manual target eligibility tests

### Singleton Devices Across Repeated Workflows

Regression coverage:

- shared selected-test/member-row singleton state tests
- group contract singleton lock-state tests

## 7. Running from the Command Line

### 7.1 Default Local Bundle

```text
python tools/can_nt/scripts/run_regressions.py --suite local
```

### 7.2 Targeted Suite

```text
python tools/can_nt/scripts/run_regressions.py --suite dsl
python tools/can_nt/scripts/run_regressions.py --suite cli
python tools/can_nt/scripts/run_regressions.py --suite java
python tools/can_nt/scripts/run_regressions.py --suite topology
python tools/can_nt/scripts/run_regressions.py --suite changelog
```

### 7.3 Connected Non-Motion Robot Suite

```text
python tools/can_nt/scripts/run_regressions.py --suite robot-non-motion \
  --rio 172.22.11.2
```

### 7.4 All Local Suites and Include Robot

```text
python tools/can_nt/scripts/run_regressions.py --suite all --include-robot \
  --rio 172.22.11.2
```

## 8. Running Through Codex

Use the `regression-runner` skill in the Codex chat.

Examples:

```text
[$regression-runner] Run the default local regression set.
[$regression-runner] Run the dsl suite.
[$regression-runner] Run the topology suite.
[$regression-runner] Run the robot-non-motion suite against 172.22.11.2.
[$regression-runner] Run local and write JSON output to tests/regression/local_run.json.
```

The skill should be treated as a request router to the same runner command,
not a separate implementation.

## 9. Command-Line Options

### 9.1 `--suite`

Selects the suite.

Examples:

```text
--suite local
--suite dsl
--suite robot-non-motion
```

### 9.2 `--include-robot`

Only meaningful when used with:

```text
--suite all
```

It adds the connected non-motion robot suite to the all-up run.

### 9.3 `--rio`

Required for:

```text
--suite robot-non-motion
```

and for:

```text
--suite all --include-robot
```

### 9.4 `--ui-rest-port`

Optional connected-suite override for the robot REST command port.

### 9.5 `--verbose`

Prints stdout and stderr even for passing commands.

Use this when:

- debugging a regression script
- reviewing exact command output
- investigating intermittent behavior

### 9.6 `--refresh-expected`

Refreshes the checked-in expected baseline for the selected suite.

Example:

```text
python tools/can_nt/scripts/run_regressions.py --suite local --refresh-expected
```

Use this only after confirming that the changed behavior is intentional.

### 9.7 `--json-out`

Writes a machine-readable JSON report to the given path.

Example:

```text
python tools/can_nt/scripts/run_regressions.py --suite local --json-out tests/regression/local_run.json
```

### 9.8 `--no-history`

Skips local regression history updates for the current run.

Example:

```text
python tools/can_nt/scripts/run_regressions.py --suite dsl --no-history
```

Use this when:

- you are doing a disposable local experiment
- you do not want a dirty-worktree failure recorded in local history

## 10. What the Output Means

Each command prints:

- pass/fail
- command label
- exit code
- mode
- duration
- the exact command
- feature coverage labels
- baseline comparison status

Example shape:

```text
[PASS] dsl-unit: exit=0 mode=local dur=0.19s
COMMAND: ...python.exe -m unittest tools.can_nt.tests.test_robot_test_dsl
FEATURES: dsl compiler, dsl validator, signal-driven set, deadband
STATUS: match
```

Summary line:

```text
SUMMARY: suite=local passed=7 failed=0 total=7
```

## 11. Comparison Status Values

Common status values:

- `match`
  - actual result matches the checked-in baseline
- `regression`
  - previously green behavior is now failing
- `known_failure`
  - baseline already expected failure for this command
- `fixed_since_baseline`
  - baseline expected failure, but current run passed
- `missing_baseline`
  - no checked-in baseline exists for this suite/command
- `command_drift`
  - the command definition changed relative to the stored baseline

## 12. Baselines

Checked-in baselines live here:

- [tests/regression/expected/runner_baselines](../tests/regression/expected/runner_baselines)

Examples:

- [local.expected.json](../tests/regression/expected/runner_baselines/local.expected.json)
- [dsl.expected.json](../tests/regression/expected/runner_baselines/dsl.expected.json)
- [topology.expected.json](../tests/regression/expected/runner_baselines/topology.expected.json)

Baselines are shared project artifacts and should be checked in when
intentionally refreshed.

## 13. Local Failure History

Purpose: keep useful regression history without logging every green run forever.

The runner now keeps local history under:

- `.codex/logs/regressions/`

This directory is local-only and ignored by git.

### 13.1 What Is Always Written

For every normal run, the runner updates:

- `latest/<suite>.latest.json`

For passing runs, the runner also updates:

- `latest/<suite>.last_green.json`

### 13.2 What Is Logged as an Event

The runner creates event records only for transitions:

- first failure
- changed failure
- recovery after failure

These event files live under:

- `.codex/logs/regressions/events/<suite>/`

### 13.3 Why This Design Exists

Most regression runs should be green.

Saving a full permanent record for every green run creates noise.

What matters more is:

- when a suite first went red
- what commit/worktree state was active
- what the last green state was before that

### 13.4 Metadata Stored in History

History records include:

- timestamp
- suite
- git commit
- branch
- dirty/clean worktree state
- changed file list

## 14. JSON Reports

If you pass `--json-out`, the runner writes a machine-readable report for that
specific invocation.

The report includes:

- suite
- summary
- baseline path
- per-command result
- comparison status
- metadata

This is useful for:

- external tooling
- CI-like wrappers
- manual archival of a specific run

## 15. Typical Workflows

### 15.1 Before a Push

Run:

```text
python tools/can_nt/scripts/run_regressions.py --suite local
```

If local changes touched a major user-visible surface, the `changelog-guard`
step will require `CHANGELOG.md` to be updated.

### 15.2 While Working on DSL Code

Run:

```text
python tools/can_nt/scripts/run_regressions.py --suite dsl
```

This is faster and more focused than `local`.

### 15.3 While Working on Topology

Run:

```text
python tools/can_nt/scripts/run_regressions.py --suite topology
```

### 15.4 While Working on Changelog / Release Process

Run:

```text
python tools/can_nt/scripts/run_regressions.py --suite changelog
```

### 15.5 After an Intentional Behavior Change

First compare:

```text
python tools/can_nt/scripts/run_regressions.py --suite local
```

Then, only if the behavior change is intended, refresh the baseline:

```text
python tools/can_nt/scripts/run_regressions.py --suite local --refresh-expected
```

Review the baseline diff before committing it.

### 15.6 When Adding a User-Facing Feature

Do not stop after adding only a happy-path regression.

Also add at least one negative-path regression when practical:

- malformed syntax
- unknown names or references
- missing required arguments
- invalid value ranges
- unavailable connected prerequisites

For this project, the negative-path regression should check two things:

- the program fails safely
- the message gives useful direction to a student or non-expert operator

## 16. When Not to Refresh Baselines

Do not use `--refresh-expected` when:

- you are unsure why a failure happened
- the change may be a bug
- the output changed only because of a broken command path
- a connected robot suite failed due to environment issues

Refreshing the baseline is not a substitute for understanding a failure.

## 17. Troubleshooting

### 17.1 `robot-non-motion` Fails Immediately

Check:

- the roboRIO host/IP is correct
- the robot is reachable
- the REST command path is available

### 17.2 Java Tests Fail Due to Environment

Check:

- Java is installed
- `JAVA_HOME` points to the JDK root

Example valid value:

```text
C:\Users\Public\wpilib\2024\jdk
```

### 17.3 A Suite Shows `command_drift`

That means the command definition no longer matches the checked-in baseline.

Usually this means:

- suite command wiring changed
- manifest command arguments changed
- the suite needs an intentional baseline refresh

### 17.4 You Want to Avoid Writing Local History

Use:

```text
--no-history
```

## 18. Related Files

Runner:

- [tools/can_nt/scripts/run_regressions.py](../tools/can_nt/scripts/run_regressions.py)
- [tools/can_nt/scripts/lib/regression_framework.py](../tools/can_nt/scripts/lib/regression_framework.py)

Manifest:

- [tests/regression/fixtures/regression_runner_manifest.json](../tests/regression/fixtures/regression_runner_manifest.json)

Skill:

- [.codex/skills/regression-runner/SKILL.md](../.codex/skills/regression-runner/SKILL.md)

Spec:

- [FEATURE_SPEC_REGRESSION_AUTOMATION.md](./FEATURE_SPEC_REGRESSION_AUTOMATION.md)

## 19. Summary

Use the regression runner as the single maintained entrypoint for regression
verification.

Remember these rules:

- use `local` for the normal default pass
- use targeted suites for faster development checks
- use `robot-non-motion` only for connected validation
- refresh baselines only for intentional behavior changes
- rely on local history for failure transitions, not full green-run archives
