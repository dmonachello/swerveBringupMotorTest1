SPEC_STATUS: IMPLEMENTED

# Feature spec: Local regression report

## Purpose

Purpose: define a local regression-analysis command that runs the maintained
test set, asks a local Ollama model to analyze the results, and writes a
Codex-ready evidence report without giving the model write or command access.

## Status

Version 1 is implemented by `tools/local-regression-report.ps1`.

## Problem

The unified regression runner can execute the repository's maintained tests,
but a failed run still requires a person or Codex to gather the useful parts:

- the exact failed commands
- the first useful errors
- affected tests and source files
- recent changes near the failures
- likely failure categories
- a concise investigation handoff

Repeating that collection work consumes Codex time without requiring Codex to
edit or design the system. A local model can do this analysis if the wrapper,
not the model, owns all commands and writes.

## Goals

- Run every maintained regression that does not require a connected robot.
- Support connected non-motion regressions only through an explicit option.
- Analyze passing and failing runs with local Ollama.
- Preserve enough evidence to audit every conclusion.
- Produce a Markdown report that a human can read and Codex can use directly.
- Keep Qwen unable to modify source, tests, configuration, specifications, or
  Git state.
- Keep the existing regression runner as the only test-suite definition.

## Non-goals

- The tool does not fix code or tests.
- The tool does not generate patches.
- The tool does not refresh expected regression baselines.
- The tool does not choose arbitrary commands.
- The tool does not provide Qwen with shell, Git, or file-writing tools.
- The tool does not run robot-connected tests by default.
- The tool does not replace human or Codex judgment about intended behavior.
- Version 1 does not select targeted suites from changed files.

## Command

Purpose: define the operator-facing command.

The entry point is:

```powershell
.\tools\local-regression-report.ps1
```

The default command runs:

```text
python tools/can_nt/scripts/run_regressions.py --suite all --json-out <temporary-path>
```

The existing `all` suite excludes the connected robot suite by default.

### Parameters

Version 1 supports these parameters:

| Parameter | Default | Meaning |
| --- | --- | --- |
| `-Model` | `qwen3-coder:30b` | Ollama model used for analysis |
| `-OllamaUrl` | `http://localhost:11434/api/chat` | Local Ollama chat endpoint |
| `-TimeoutMinutes` | `30` | Maximum regression-runner duration |
| `-IncludeRobot` | off | Adds the connected non-motion suite |
| `-Rio` | none | roboRIO host or IP address |
| `-UiRestPort` | runner default | Optional REST port for connected tests |
| `-OutputRoot` | `.local-ai/regression-reports` | Final report root relative to the repository |

`-IncludeRobot` requires `-Rio`. `-Rio` without `-IncludeRobot` is an error.

Connected execution uses the unified runner:

```text
python tools/can_nt/scripts/run_regressions.py --suite all --include-robot --rio <host-or-ip> --json-out <temporary-path>
```

The wrapper passes `--ui-rest-port` only when the operator supplies
`-UiRestPort`.

Version 1 must not expose `--refresh-expected`.

## Existing runner relationship

Purpose: keep one owner for suite membership and regression behavior.

`tools/can_nt/scripts/run_regressions.py` remains authoritative for:

- suite membership
- command order
- baseline comparison
- local failure history
- changelog-guard behavior
- connected non-motion safety rules

`local-regression-report.ps1` wraps that command. It must not copy the suite
manifest or maintain a second command list.

The wrapped runner may perform its existing maintenance writes:

- update `.codex/logs/regressions/`
- seed `CHANGELOG.md` when the changelog guard requires an entry
- create normal ignored build and test output

The report wrapper must not make those writes itself.

## Run sequence

Purpose: define the required order and the point at which artifacts become
visible.

The command runs these steps in order:

1. Resolve the repository root from the script location.
2. Validate the command parameters.
3. Capture the initial repository snapshot.
4. Verify the Ollama endpoint and requested model.
5. Create a private working directory under the operating-system temporary
   directory.
6. Run the unified regression runner against the current working tree.
7. Capture stdout, stderr, duration, exit code, and runner JSON.
8. Capture the final repository snapshot.
9. Validate every repository change against the allowed-write policy.
10. Build a bounded analysis request from deterministic evidence.
11. Ask Ollama for JSON that matches the analysis schema.
12. Validate the model response.
13. Render the Markdown report and manifest.
14. Move the complete bundle into the Git-ignored report root.
15. Remove the temporary working directory.
16. Return the exit code defined by this specification.

The wrapper must run the regression runner once. It must not stop after the
first failed test. The unified runner must continue through every selected
command and include all results in its JSON output.

## Current working tree

Purpose: define which repository state the report analyzes.

The command analyzes the current working tree, including:

- the checked-in `HEAD`
- staged changes
- unstaged changes
- untracked files reported by Git

The command runs tests directly in that working tree. It does not create a
copy, clone, stash, or temporary worktree.

The report records the branch, `HEAD`, configured upstream when present, dirty
state, and changed paths captured before the run. A missing upstream does not
block local regression analysis.

## Ollama preflight

Purpose: fail before expensive work when local analysis cannot run.

Every repository script that depends on Ollama must run the same minimum
preflight at startup. The script must call `GET /api/tags`, confirm that the
requested model is installed, and stop with recovery guidance on failure. This
check must occur before tests, Git mutations, or other expensive work.

Scripts that require structured model output must also send and validate a
small schema-constrained probe. A successful `/api/tags` response alone does
not prove that structured inference works.

Before starting regressions, the wrapper must:

- call `GET /api/tags` on the server derived from `-OllamaUrl`
- confirm that `-Model` appears in the returned model list
- send a small schema-constrained probe
- validate the probe response

If any preflight check fails, the command returns nonzero. It must not run the
regression suite or create a report bundle.

A successful preflight does not excuse a later Ollama failure. If final
analysis fails or returns invalid JSON, the command returns nonzero and
publishes no report bundle. Existing regression history or an allowed
`CHANGELOG.md` seed from the completed test run may remain.

## Runtime and timeout

Purpose: stop a hung regression run without losing control of the wrapper.

The default timeout is 30 minutes for the complete unified runner process.

When the timeout expires, the wrapper must:

1. terminate the runner process tree
2. record the timeout in the evidence package
3. continue with repository-state validation
4. request the full Qwen analysis
5. publish the report if analysis and validation succeed
6. return the regression-failure exit code

`-TimeoutMinutes` accepts a positive integer. The implementation must enforce
a documented upper bound.

## Allowed commands

Purpose: make model-driven command execution structurally impossible.

PowerShell may execute only fixed operations required by this specification:

- read-only Git queries for branch, upstream, status, diff, log, and tags
- the unified regression runner with validated arguments
- local HTTP requests to the configured Ollama endpoint
- deterministic reads of files named by collected evidence

Qwen receives no tools. Qwen cannot request another command, select a path to
write, or extend the allowlist.

The wrapper must reject command text returned by the model. Model output is
data only.

## Evidence collection

Purpose: give Qwen enough context without sending the entire repository.

The deterministic wrapper owns evidence selection. The analysis request may
contain:

- repository snapshot metadata
- changed path names
- staged and unstaged diff summaries
- recent commit subjects
- regression-runner JSON
- captured stdout and stderr
- failing test identifiers
- stack-trace paths and symbols
- bounded source excerpts around referenced symbols
- existing baseline comparison statuses

The implementation must define constants for all size limits. At minimum, it
must limit:

- total prompt characters
- raw output characters per failed command
- number of source files
- characters per source excerpt
- recent commit count

If required evidence exceeds a limit, the wrapper records the truncation in
the request and report. It must not silently omit evidence.

Repository text is untrusted data. The system prompt must tell Qwen to ignore
instructions found in diffs, logs, source, tests, and documentation.

## Analysis schema

Purpose: make the local model response machine-checkable.

Ollama must return JSON with these top-level fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | Analysis schema version |
| `overall_status` | enum | `pass`, `fail`, `timeout`, or `infrastructure_error` |
| `summary` | string | Short statement of the run result |
| `findings` | array | Evidence-backed findings |
| `healthy_signals` | array | Passing evidence that narrows the investigation |
| `uncertainties` | array | Questions the evidence cannot answer |
| `recommended_investigation` | array | Ordered read-only investigation steps |
| `codex_handoff` | object | Ready-to-use Codex investigation request |

Each finding contains:

| Field | Type | Meaning |
| --- | --- | --- |
| `title` | string | Concise finding name |
| `classification` | enum | Failure category |
| `confidence` | enum | `low`, `medium`, or `high` |
| `observed_behavior` | string | What the evidence proves happened |
| `suspected_cause` | string | Hypothesis, or empty when no hypothesis is supported |
| `evidence` | array | References to tests, commands, logs, or source excerpts |
| `relevant_files` | array | Existing repository-relative paths from the evidence package |
| `next_checks` | array | Ordered investigation steps |

Allowed finding classifications are:

- `product_regression`
- `test_regression`
- `baseline_drift`
- `environment`
- `test_infrastructure`
- `known_failure`
- `unclear`

The validator must reject:

- missing fields
- unknown enum values
- duplicate findings
- paths not present in the evidence package
- evidence references that do not exist
- empty summaries
- commands or patch content in fields that do not permit them

The wrapper may retry invalid model output a fixed number of times. All retry
counts belong in the constants section.

## Codex handoff

Purpose: let Codex start with evidence instead of repeating repository
discovery.

The `codex_handoff` object contains:

- the investigation objective
- the observed failures
- the strongest evidence
- relevant repository paths
- unresolved questions
- ordered checks
- the report-bundle paths
- explicit constraints

The constraints must state:

- inspect before editing
- distinguish verified findings from hypotheses
- do not change tests only to make them pass
- confirm intended behavior before changing a contract
- add the narrowest useful regression for each confirmed bug

The Markdown report ends with a fenced, ready-to-paste Codex prompt generated
from the validated object.

## Report bundle

Purpose: preserve the human report and the evidence needed to audit it.

Completed bundles live under:

```text
.local-ai/regression-reports/<timestamp>-<run-id>/
```

The implementation must add this root to `.gitignore`.

Each completed bundle contains:

```text
report.md
manifest.json
regression-result.json
analysis-request.json
analysis-response.json
runner.stdout.log
runner.stderr.log
```

Connected runs also record the supplied roboRIO target and REST port in
`manifest.json`. The report must not print credentials or unrelated environment
variables.

The wrapper builds the bundle outside the repository. It publishes the bundle
only after every required file validates. A failed run must not leave a partial
bundle under `.local-ai/regression-reports/`.

## Markdown report

Purpose: provide one readable investigation record.

`report.md` uses this section order:

1. Run summary
2. Repository state
3. Regression results
4. Failed commands and tests
5. Findings
6. Healthy signals
7. Uncertainties
8. Recommended investigation
9. Repository changes made by the regression runner
10. Evidence inventory
11. Codex handoff prompt

The report must separate deterministic facts from Qwen hypotheses. Each Qwen
hypothesis includes its confidence value and evidence references.

An all-green run still receives the full report. Qwen must explain what passed,
identify any skipped or missing coverage, and avoid inventing failures.

## Repository-state validation

Purpose: detect writes outside the approved regression behavior.

The initial and final snapshots include:

- `HEAD`
- current branch
- configured upstream
- index diff
- tracked working-tree diff
- untracked path list
- SHA-256 hashes for pre-existing untracked regular files
- local tag list

The run must fail integrity validation if:

- `HEAD` changes
- the branch changes
- the configured upstream changes
- the index changes
- a tag is added, removed, or changed
- a pre-existing tracked change is overwritten or removed
- a pre-existing untracked file changes or disappears
- a tracked file other than `CHANGELOG.md` changes
- `CHANGELOG.md` changes without a matching changelog-guard result
- an unexpected untracked source, test, configuration, specification, or
  documentation file appears

Allowed changes include:

- local history under `.codex/logs/regressions/`
- ignored build and test outputs produced by the maintained runner
- a changelog entry seeded by the maintained changelog guard
- the completed report bundle

The report lists every allowed change made during the run. Integrity failure
prevents bundle publication because the report cannot claim a safe run.

The wrapper must not attempt to restore unexpected changes automatically. It
must print the changed paths and stop so a human can inspect them.

## Exit codes

Purpose: make the command useful from PowerShell and automation.

| Code | Meaning | Report published |
| --- | --- | --- |
| `0` | Every selected regression passed and analysis completed | yes |
| `1` | One or more regressions failed or timed out | yes |
| `2` | Parameters, repository state, or prerequisites were invalid | no |
| `3` | Ollama preflight or final analysis failed | no |
| `4` | Repository integrity validation failed | no |
| `5` | A complete report bundle could not be validated or published | no |

The command prints the final report path before returning `0` or `1`.

## Failure handling

Purpose: define what remains after each failure boundary.

### Preflight failure

The command runs no regressions and publishes no bundle.

### Regression failure

The command completes analysis, publishes the bundle, and returns `1`.

### Regression timeout

The command terminates the runner, completes analysis, publishes the bundle,
and returns `1`.

### Ollama analysis failure

The command publishes no bundle and returns `3`. The command deletes temporary
logs and model request files. Existing regression history and an allowed
changelog seed may remain.

### Integrity failure

The command publishes no bundle and returns `4`. It leaves unexpected changes
untouched for human inspection.

### Report publication failure

The command returns `5` and removes any incomplete final directory when safe.

## Security and safety rules

- Bind Ollama requests to the configured local endpoint only.
- Do not send repository data to a remote API.
- Treat diffs, logs, source, tests, and documentation as untrusted text.
- Never execute model output.
- Never accept a model-provided path outside the evidence package.
- Never expose arbitrary PowerShell through configuration.
- Never run baseline refresh from this command.
- Never run connected tests without `-IncludeRobot` and `-Rio`.
- Preserve the supported PC-side rule that diagnostics do not transmit CAN.
- Do not add robot motion tests through this feature.

## Configuration ownership

Purpose: keep stable behavior in code and project policy in data.

The PowerShell script owns:

- command sequencing
- validation
- artifact transactions
- exit codes
- Ollama request and response handling
- repository integrity checks

The existing regression runner owns suite commands and baselines.

Version 1 keeps model, endpoint, timeout, and output-root defaults in the
PowerShell constants section. A later version may move reusable defaults into a
validated adjacent configuration file.

## Logging

Purpose: retain useful evidence without leaking unrelated machine state.

Raw logs contain only stdout and stderr from the unified runner. The wrapper
must not dump the full process environment.

The manifest records:

- tool schema version
- start and finish timestamps
- duration
- branch, `HEAD`, and upstream
- dirty state and changed paths
- selected runner arguments
- model and endpoint host
- connected target when supplied
- regression and wrapper exit codes
- artifact hashes
- truncation notices

## Verification plan

Purpose: prove the safety and report contracts before enabling normal use.

### Unit tests

Add focused tests for:

- CLI parameter validation
- exit-code mapping
- report-path generation
- artifact manifest hashing
- Qwen schema validation
- evidence-reference validation
- prompt-size truncation notices
- before-and-after repository comparison
- allowed changelog seeding
- rejection of every other tracked-file change

### Ollama contract tests

Use a local fake HTTP endpoint to prove:

- unavailable endpoint fails before regression execution
- missing model fails before regression execution
- invalid probe JSON fails before regression execution
- invalid final JSON retries only to the fixed limit
- exhausted retries publish no bundle

### Runner integration tests

Use a temporary Git repository and a fake regression runner to prove:

- all-green execution publishes a full bundle and returns `0`
- test failure publishes a full bundle and returns `1`
- timeout terminates the process tree, publishes a bundle, and returns `1`
- runner history writes are allowed
- an attributable `CHANGELOG.md` seed is allowed
- an unexpected tracked edit blocks publication and returns `4`
- a partial final directory is never visible

### Live verification

Before version 1 is complete:

1. Run the real non-robot `all` suite.
2. Confirm that the Markdown report matches the runner JSON.
3. Confirm that each evidence reference resolves.
4. Confirm that Qwen modified no repository file.
5. Confirm that an all-green run still contains the complete report sections.
6. Run an explicitly approved connected non-motion pass against a reachable
   roboRIO.

## Implementation sequence

Purpose: keep each implementation step independently testable.

1. Add parameter validation, repository discovery, and Ollama preflight.
2. Add the temporary artifact directory and final publication transaction.
3. Wrap the unified runner with timeout and process-tree termination.
4. Add repository snapshots and allowed-write validation.
5. Add bounded evidence collection.
6. Add the Qwen schema, prompt, retries, and response validator.
7. Add Markdown rendering and the Codex handoff block.
8. Add connected option handling.
9. Add `.gitignore` coverage for the final report root.
10. Run the live non-robot and connected verification passes.

No step may grant Qwen command or write access.

## Definition of done

Version 1 is complete when:

- the default command runs the unified `all` suite without connected tests
- the connected suite requires explicit options
- Ollama failure before the run starts creates no report or test side effects
- every successful analysis publishes all required artifacts
- all-green and failed runs both receive full Qwen analysis
- regression failures return nonzero after publishing the report
- invalid Qwen output cannot create a report
- unexpected repository writes block publication
- existing history and attributable changelog writes remain supported
- Qwen has no command, Git, or file-writing tools
- unit and integration tests cover each failure boundary
- the user guide documents invocation, artifacts, and exit codes

## Tradeoffs

- Running tests in the current working tree preserves the exact developer state,
  but test processes can write there. Snapshot validation detects unexpected
  tracked changes after they happen; it does not prevent them.
- Requiring Ollama for green runs costs local GPU time, but every report has one
  consistent format and analysis contract.
- Deleting artifacts after an Ollama failure keeps incomplete reports out of
  the repository, but the test run may need to be repeated after Ollama is
  fixed.
- Keeping suite ownership in the existing runner avoids drift, but report
  generation depends on the runner's JSON remaining complete and stable.

## Future extensions

- Targeted suite reports selected by an explicit operator option.
- Comparison with the last green report.
- Flaky-test detection across local history.
- Optional performance summaries from test duration history.
- A local review report that analyzes a diff without running regressions.
- A documentation-drift report that identifies likely stale documents without
  editing them.
- A reusable repository-neutral configuration file for model and evidence
  limits.

## Related documents

- [Regression Runner User Guide](./USER_GUIDE_REGRESSION_RUNNER.md)
- [Regression Automation Framework](./FEATURE_SPEC_REGRESSION_AUTOMATION.md)
- [Regression Maintenance and Skill Runner](./FEATURE_SPEC_REGRESSION_MAINTENANCE_SKILL.md)
- [AI Diagnosis Using `bringup_report.json`](./AI_DIAGNOSIS.md)
