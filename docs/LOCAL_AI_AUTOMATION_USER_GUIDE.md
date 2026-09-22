# Local AI automation user guide

## Purpose

Purpose: run the repository's local AI check-in and regression tools without
using Codex for routine analysis.

Run all commands from the repository root in Windows PowerShell:

```powershell
cd <repo-root>
```

## Current commands

| Task | Command | Changes state |
| --- | --- | --- |
| Preview a check-in | `.\tools\local-checkin.ps1 -DryRun` | no |
| Commit, tag, and push | `.\tools\local-checkin.ps1` | yes |
| Reject a mixed check-in | `.\tools\local-checkin.ps1 -AbortOnMixed` | yes, unless mixed |
| Run regressions and create an AI report | `.\tools\local-regression-report.ps1` | yes, maintained test outputs and history |
| Include connected non-motion tests | `.\tools\local-regression-report.ps1 -IncludeRobot -Rio <address>` | yes, maintained test outputs and history |
| Check test registration | `python tools/can_nt/scripts/regression_coverage_guard.py` | no |
| Test the check-in script | `.\tools\local-checkin.ps1 -SelfTest` | no |
| Test the regression-report script | `.\tools\local-regression-report.ps1 -SelfTest` | no |

## Prepare Ollama

Both PowerShell tools use the local Ollama server by default. The regression
report rejects a non-local endpoint. The check-in script sends repository
context to its configured `-OllamaUrl`, so keep that URL local.

Install the default model once:

```powershell
ollama pull qwen3-coder:30b
```

If Ollama does not start with Windows, start it in a separate terminal:

```powershell
ollama serve
```

Check the server and installed models:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags
```

Each AI-dependent script runs this check itself. The regression-report script
also tests schema-constrained output before it starts the test suite.

## Run the normal local workflow

### 1. Run the regression report

Run all maintained non-robot tests:

```powershell
.\tools\local-regression-report.ps1
```

The command prints the final report path. Completed bundles are stored under:

```text
.local-ai\regression-reports\<timestamp>-<run-id>\
```

Review `report.md` first. Use `regression-result.json`, the raw logs, and the
analysis files when you need the supporting evidence.

### 2. Preview the check-in

Run the check-in tool in read-only mode:

```powershell
.\tools\local-checkin.ps1 -DryRun
```

Review these fields:

- branch and upstream
- proposed commit header
- version bump and tag
- mixed-change decision
- files reviewed
- affected applications
- summary

The dry run does not stage, commit, tag, or push.

### 3. Apply the check-in

Warning: the default command stages, commits, tags, and pushes without a
second confirmation prompt.

After you approve the dry-run proposal, run:

```powershell
.\tools\local-checkin.ps1
```

The script uses the current branch and its configured upstream. It aborts when
the branch has no upstream or when the upstream contains work that is not in
the local branch.

The push is atomic. Git updates the branch and the tag together, or neither
remote reference changes.

## Control mixed check-ins

Mixed concerns are allowed by default. The script lists each detected concern
and uses the deterministic mixed-change commit header.

To reject mixed work before Git mutation, run:

```powershell
.\tools\local-checkin.ps1 -AbortOnMixed
```

Use `-AbortOnMixed` when you want to split documentation, robot runtime, host
diagnostics, or other concerns into separate commits.

Repository-specific ownership rules live in:

```text
tools\local-checkin-ownership.map
```

The check-in script can run in another repository without that file. It uses
generic ownership defaults in that case.

## Understand tag selection

The validated proposal chooses one of these tag forms:

- `vX.Y.Z` for a `patch`, `minor`, or `major` version bump
- `checkpoint-<timestamp>-<scope>` when the version bump is `none`

Documentation and local automation concerns do not force a release bump. The
script checks existing local and remote tags before it creates the new tag.

## Run connected regressions

The default regression report never connects to a robot.

To add the connected non-motion suite, supply the roboRIO address:

```powershell
.\tools\local-regression-report.ps1 `
    -IncludeRobot `
    -Rio 172.22.11.2
```

If the REST server uses another port, add `-UiRestPort`:

```powershell
.\tools\local-regression-report.ps1 `
    -IncludeRobot `
    -Rio 172.22.11.2 `
    -UiRestPort 5809
```

`-IncludeRobot` requires `-Rio`. Supplying `-Rio` without `-IncludeRobot` is
an error.

## Add a new test

Add a Java test under `src/test/java`. Gradle discovers it automatically.

Add a Python file named `test_*.py` under one of these directories:

- `tools/can_nt/tests`
- `tools/common/tests`
- `tools/can_topology/tests`
- `tools/docs_maintenance/tests`
- `tools/can_tx_poc/tests`

The local suite discovers the new file automatically.

If you create another test directory, the regression coverage guard fails.
Add a discovery command to
`tests/regression/fixtures/regression_runner_manifest.json`, or add a justified
exclusion to
`tests/regression/fixtures/regression_coverage_exclusions.json`.

Register a new standalone `_regression.py` script in the runner manifest and
assign its command to a suite. The guard rejects unassigned commands.

Run the guard directly when you change test layout:

```powershell
python tools/can_nt/scripts/regression_coverage_guard.py
```

## Check-in parameters

| Parameter | Default | Use |
| --- | --- | --- |
| `-Model` | `qwen3-coder:30b` | Select another installed Ollama model |
| `-OllamaUrl` | `http://localhost:11434/api/chat` | Select another local Ollama endpoint |
| `-ContextLength` | `65536` | Set the model context window |
| `-TimeoutSeconds` | `300` | Set the Ollama request timeout |
| `-DryRun` | off | Display the proposal without changing Git |
| `-AbortOnMixed` | off | Reject a mixed-concern proposal |
| `-SelfTest` | off | Run script contract tests |

## Regression-report parameters

| Parameter | Default | Use |
| --- | --- | --- |
| `-Model` | `qwen3-coder:30b` | Select another installed Ollama model |
| `-OllamaUrl` | `http://localhost:11434/api/chat` | Select another local Ollama endpoint |
| `-TimeoutMinutes` | `30` | Limit the complete regression runner |
| `-IncludeRobot` | off | Add connected non-motion tests |
| `-Rio` | none | Set the connected roboRIO address |
| `-UiRestPort` | runner default | Override the robot REST port |
| `-OutputRoot` | `.local-ai/regression-reports` | Set the ignored report directory |
| `-SelfTest` | off | Run script contract tests |

## Regression-report exit codes

| Code | Meaning | Report published |
| --- | --- | --- |
| `0` | Every selected regression passed | yes |
| `1` | A regression failed or timed out | yes |
| `2` | Parameters or prerequisites were invalid | no |
| `3` | Ollama preflight or analysis failed | no |
| `4` | The runner changed an unexpected repository file | no |
| `5` | Report validation or publication failed | no |

Check the last exit code in PowerShell:

```powershell
$LASTEXITCODE
```

## Recover from common failures

### Ollama is unavailable

Start Ollama, then check the tags endpoint:

```powershell
ollama serve
Invoke-RestMethod http://localhost:11434/api/tags
```

### The model is missing

Install the configured model:

```powershell
ollama pull qwen3-coder:30b
```

### The branch has no upstream

Configure the upstream before you run the check-in tool:

```powershell
git push --set-upstream origin <branch-name>
```

### The check-in is mixed

Run a dry run and inspect the listed concerns:

```powershell
.\tools\local-checkin.ps1 -DryRun
```

Either accept the mixed check-in or split the files into separate commits. Use
`-AbortOnMixed` to make mixed work a hard failure.

### The atomic push fails

The local commit and tag remain available for recovery. Read the failure
message before you retry. Do not create another commit until you inspect the
current `HEAD`, the tag, and the configured upstream.

### The regression report rejects repository changes

Inspect the paths printed by the integrity failure. The script does not revert
them. The maintained runner may update generated build information, local
regression history, and an attributable changelog seed. Any other tracked
write blocks publication.

## Keep this guide current

Add every new local operator command to the **Current commands** table. Include
its default behavior, mutation behavior, options, output location, and failure
recovery steps.

Update this guide in the same change when you add or rename:

- a `tools/local-*.ps1` entry point
- a local AI model prerequisite
- a report artifact
- a test discovery root
- a check-in or regression safety rule

## Related documents

- [Regression runner user guide](./USER_GUIDE_REGRESSION_RUNNER.md)
- [Local regression report specification](./FEATURE_SPEC_LOCAL_REGRESSION_REPORT.md)
- [Regression automation specification](./FEATURE_SPEC_REGRESSION_AUTOMATION.md)
- [Generated artifacts policy](./GENERATED_ARTIFACTS_POLICY.md)
