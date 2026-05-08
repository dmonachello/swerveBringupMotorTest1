---
name: regression-runner
description: >-
  Run the repo's maintained regression bundles through the unified wrapper.
  Use when the user asks to run regressions, check whether recent changes
  broke existing behavior, exercise a targeted suite such as dsl/cli/java,
  or run the connected non-motion robot regression against a specific
  roboRIO.
---

# Regression Runner

Use the unified runner at:

```text
python tools/can_nt/scripts/run_regressions.py
```

## Commands

Run the default local bundle:

```text
python tools/can_nt/scripts/run_regressions.py --suite local
```

Run a targeted suite:

```text
python tools/can_nt/scripts/run_regressions.py --suite dsl
python tools/can_nt/scripts/run_regressions.py --suite cli
python tools/can_nt/scripts/run_regressions.py --suite java
```

Run the connected non-motion robot suite:

```text
python tools/can_nt/scripts/run_regressions.py --suite robot-non-motion \
  --rio 172.22.11.2
```

Run all local suites and include the robot suite:

```text
python tools/can_nt/scripts/run_regressions.py --suite all --include-robot \
  --rio 172.22.11.2
```

Refresh the expected baseline for one suite:

```text
python tools/can_nt/scripts/run_regressions.py --suite local --refresh-expected
```

Write a machine-readable report:

```text
python tools/can_nt/scripts/run_regressions.py --suite local --json-out \
  tests/regression/local_report.json
```

## Rules

- Run from the repo root.
- Prefer the unified runner over invoking multiple regression commands manually.
- Use `--suite dsl`, `cli`, or `java` when the user asks for a targeted pass.
- Use `--suite local` for the normal pre-push or maintenance pass.
- Use `robot-non-motion` only when the user asks for connected validation
  or the change touches robot TCP/UI behavior.
- Use `--refresh-expected` only after confirming that the new behavior is
  intended.
- Use `--json-out` when the user wants a machine-readable artifact or when
  another tool will consume the result.
- Report which suite ran, which commands failed, and whether the failure
  looks like a new break or an existing red regression.

## Notes

- The V1 runner is a wrapper over existing canonical commands.
- `--refresh-expected` writes suite baselines under
  `tests/regression/expected/runner_baselines/`.
- The runner normalizes `JAVA_HOME` for Gradle if the shell points it at
  the JDK `bin` directory instead of the JDK root.
