# Command Handler Architecture

Purpose: define the command parsing, validation, transport, execution, and output boundaries for the Python Bridge CLI and the Java robot-side UI handler.

## Why This Document Exists
Purpose: explain the refactor that split monolithic command handling into smaller boundaries while preserving scriptability and runtime behavior.

This system has two command surfaces that must stay aligned:
- Python Bridge CLI on the PC side.
- Java UI/TCP command handler on the robot side.

Both surfaces need to preserve these properties:
- Parsing stays separate from business logic.
- Safety and ingress policy stay explicit.
- Transport details stay isolated from command intent.
- Output formatting/publication stays separate from execution.
- Batch scripts and regression tests continue to exercise the same command path as interactive use.

## Design Goals
Purpose: state the intended outcomes of the split.

- Keep grammar and token handling out of domain execution.
- Keep robot transport concerns out of CLI orchestration.
- Keep UI ingress policy out of command switch logic.
- Preserve existing command semantics and status codes.
- Preserve scriptability for batch files and regression scripts.
- Create seams that can be tested directly with focused unit tests.

## High-Level Split
Purpose: show the common conceptual pipeline used on both Python and Java sides.

```text
raw command/input
  -> parse / normalize
  -> validate ingress or parsed payload
  -> transport facade or executor boundary
  -> command/domain switch logic
  -> result model
  -> output/presentation publication
```

The exact implementation differs by language, but the architecture is the same:
- A narrow input contract enters the pipeline.
- Validation happens before business execution.
- Execution returns a structured result model.
- Output formatting/publication consumes that result model.

## Python Bridge CLI Architecture
Purpose: describe the PC-side command stack used by `tools/can_nt/bridge_cli.py`.

### Main Files
- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/bridge_cli_facades.py`
- `tools/can_nt/bridge_robot_control_facade.py`
- `tools/can_nt/bridge_cli_parser.py`
- `tools/can_nt/bridge_cli_ast.py`
- `tools/can_nt/bridge_ops.py`

### Shared Host Services

- `tools/common/config_lifecycle/service.py`
- `tools/common/workflows/workflow01_service.py`
- `tools/common/tests_domain/semantics.py`
- `tools/common/diagnostics/normalize.py`

Purpose:

- keep config/profile lifecycle semantics centralized and reusable across CLI/UI/tooling
- keep workflow guidance out of parser/transport code paths
- keep test-domain and diagnostics-normalization logic out of presentation-heavy modules

### Responsibilities by Layer
Purpose: make each Python boundary explicit.

#### 1) Grammar + AST
Files:
- `bridge_cli_parser.py`
- `bridge_cli_ast.py`

Responsibilities:
- Parse raw CLI text.
- Produce tokens and AST payloads.
- Keep grammar-specific behavior isolated from downstream execution.

Non-responsibilities:
- Robot TCP send/wait behavior.
- Status printing.
- Command side effects.

#### 2) Parse Context Contract
File:
- `bridge_cli_facades.py`

Type:
- `BridgeCliParseContext`

Purpose:
- Narrow the parse facade dependency surface to only the operations needed for parsing and parse-fallback behavior.
- Avoid reaching directly into the full `BridgeCli` object from the parse facade.

Current contract fields include:
- `parse_line`
- `split_command`
- `maybe_print_failure_hint`
- `alias_replacement`
- `print_alias_removed`
- `normalize_tokens`
- `fallback_device_set`
- `config_command`
- `coerce_status`
- `mode_name`

#### 3) Parse Facade
File:
- `bridge_cli_facades.py`

Type:
- `BridgeCliParseFacade`

Responsibilities:
- Turn one raw line into a `ParsedLineResult`.
- Detect `--pretty --json` intent at parse time.
- Handle parser exceptions in one place.
- Preserve alias-removal and fallback-device-set behavior.

Return model:
- `ParsedLineResult(tokens, ast, status, line_pretty)`

#### 4) Validation Facade
File:
- `bridge_cli_facades.py`

Type:
- `BridgeCliValidateFacade`

Responsibilities:
- Validate the parsed payload before command dispatch.
- Treat empty-token lines as no-op success.
- Return an early `StatusResult` when execution should not continue.

This is intentionally small today; it is the first stop for pre-dispatch validation and can grow as more parsed-line rules are centralized.

#### 5) Robot Control Transport Contract
File:
- `bridge_robot_control_facade.py`

Type:
- `BridgeRobotControlTransport`

Purpose:
- Provide a narrow robot-command transport contract independent of the full CLI object.
- Separate robot send/wait/failure mechanics from command orchestration.

Current contract fields include:
- `send_command`
- `mark_command_sent`
- `wait_for_seq`
- `event_failed`
- `handle_add_device_conflict`

#### 6) Robot Control Facade
File:
- `bridge_robot_control_facade.py`

Type:
- `BridgeRobotControlFacade`

Responsibilities:
- Send a bridge command through the transport contract.
- Wait for ACK/OUT completion via transport callbacks.
- Map send and event failures to stable status codes.
- Preserve special handling for `groupAddDevice` conflict detection.

This isolates transport policy from `BridgeCli` command dispatch and keeps script-visible behavior unchanged.

#### 7) Output Facade
File:
- `bridge_cli_facades.py`

Type:
- `BridgeCliOutputFacade`

Responsibilities:
- Render `StatusResult` to console output.
- Centralize raw-code vs detail-message printing.
- Keep status formatting separate from business execution.

### BridgeCli Orchestration Role
Purpose: define what `BridgeCli` still owns after the split.

`BridgeCli` remains the orchestrator for:
- interactive prompt loop
- batch/script execution
- parser mode tracking
- command family dispatch
- local config state
- command tracker/protocol accounting

But `BridgeCli` now wires through narrower boundaries:
- `BridgeCliParseContext`
- `BridgeCliParseFacade`
- `BridgeCliValidateFacade`
- `BridgeCliExecuteFacade`
- `BridgeCliOutputFacade`
- `BridgeRobotControlTransport`

This preserves scriptability because batch scripts and interactive commands still travel through the same parse/validate/execute path.

### Python Command Flow
Purpose: show the operational path for one CLI command.

```text
raw CLI line
  -> BridgeCliParseFacade.parse_line(parse_context, line)
  -> BridgeCliValidateFacade.validate_parsed_line(parsed)
  -> BridgeCli command dispatch / AST execution
  -> BridgeCliExecuteFacade.execute_command(transport, command)
  -> BridgeRobotControlFacade.execute_command(...)
  -> StatusResult
  -> BridgeCliOutputFacade.emit_status(...)
```

### Python Scriptability Guarantees
Purpose: document why batch and regression paths remain stable.

- Interactive and batch modes share the same parser and command path.
- Transport failure mapping is centralized in one facade.
- Parse error handling is deterministic and unit-testable.
- Console status output formatting is centralized.
- Regression scripts continue to exercise the same command orchestration path used by operators.

## Java Robot UI Command Architecture
Purpose: describe the robot-side command ingress and execution split used by `BridgeUiCommandHandler`.

### Main Files
- `src/main/java/frc/robot/BridgeUiCommandHandler.java`
- `src/main/java/frc/robot/BridgeUiCommandExecutor.java`
- `src/main/java/frc/robot/BridgeUiIngressPolicy.java`
- `src/main/java/frc/robot/BridgeUiCommandResult.java`
- `src/main/java/frc/robot/BridgeUiOutputFacade.java`

### Responsibilities by Layer
Purpose: make each Java boundary explicit.

#### 1) Handler / Orchestrator
File:
- `BridgeUiCommandHandler.java`

Responsibilities:
- Receive NT and TCP UI command requests.
- Build ingress policy dependencies.
- Construct the executor and output facade.
- Route raw command input into the executor.
- Publish ACK/OUT/TCP monitor output using the output facade.
- Maintain runtime-owned state that the policy/executor depend on.

Non-responsibilities:
- Detailed ingress validation logic.
- Raw output publication details.
- Shared result data model definition.

#### 2) Ingress Policy
File:
- `BridgeUiIngressPolicy.java`

Purpose:
- Centralize parse/validate/pre-execution policy for UI command ingress.

Key types:
- `Dependencies`
- `Ingress`
- `ValidationFailure`

Responsibilities:
- Parse raw ingress into an `Ingress` model.
- Validate UI handshake and client lock rules.
- Enforce stop-latch gating for TCP start commands.
- Enforce disabled/E-stop command rules.
- Apply pre-execution side effects such as TCP stop-latch behavior.

Important design choice:
- Policy logic depends on a narrow `Dependencies` interface rather than directly owning robot state.
- This keeps ingress rules testable and separate from the giant command switch.

#### 3) Command Executor
File:
- `BridgeUiCommandExecutor.java`

Purpose:
- Own the high-level execution pipeline from raw request to command result.

Responsibilities:
- Parse ingress through `BridgeUiIngressPolicy`.
- Validate ingress before switch execution.
- Convert validation failures into `BridgeUiCommandResult`.
- Apply pre-execution policy hooks.
- Delegate command-specific execution through a switch callback.

Key design choice:
- The executor owns the common pipeline, while the command handler provides the switch-domain callback.
- This isolates the reusable execution flow from command-family implementation details.

#### 4) Command Result Model
File:
- `BridgeUiCommandResult.java`

Purpose:
- Provide a shared result payload for UI command execution.

Fields:
- `ok`
- `code`
- `message`
- `outText`
- `outJson`

This result model is the stable handoff between:
- ingress validation
- command execution
- TCP response construction
- NT ACK/OUT publication

#### 5) Output Facade
File:
- `BridgeUiOutputFacade.java`

Responsibilities:
- Historical note: older revisions published ACK/OUT fields through a UI NetworkTable.
- Supported bringup command handling now uses the REST/TCP path rather than a required UI NetworkTable bridge.
- Publish protocol monitor fields to the UI TCP monitor table.
- Publish lightweight state metadata like last ACK timestamp and session metadata.

Important design choice:
- Output/publication logic is separate from command execution and separate from ingress policy.
- This keeps the UI contract centralized and easier to audit.

### Java Command Flow
Purpose: show the operational path for historical NT ingress and the supported TCP ingress.

#### NetworkTables path (historical / retired)
```text
NT cmd entries
  -> BridgeUiCommandHandler.handleUiCommands()
  -> BridgeUiCommandExecutor.executeRaw(..., isTcp=false)
  -> BridgeUiIngressPolicy.parseIngress(...)
  -> BridgeUiIngressPolicy.validateIngress(...)
  -> handler switch callback executes command logic
  -> BridgeUiCommandResult
  -> BridgeUiOutputFacade.publishUiAck(...)
  -> BridgeUiOutputFacade.publishUiOut(...)
```

#### TCP path
```text
TCP UiCommand
  -> BridgeUiCommandHandler.handleTcpUiCommand(...)
  -> queued to main robot loop
  -> BridgeUiCommandExecutor.executeRaw(..., isTcp=true)
  -> BridgeUiIngressPolicy parse/validate/pre-exec
  -> handler switch callback executes command logic
  -> BridgeUiCommandResult
  -> TCP response built from result
  -> optional BridgeUiOutputFacade.publishUiTcpMonitor(...)
```

## Shared Architectural Rules
Purpose: capture the cross-language invariants that both implementations follow.

### 1) Parse/ingress validation happens before execution
- Python validates parsed lines before dispatch.
- Java validates ingress before running command switch logic.

### 2) Transport details are isolated
- Python robot command send/wait behavior is hidden behind `BridgeRobotControlTransport` and `BridgeRobotControlFacade`.
- Java command ingress policy reads robot state through `BridgeUiIngressPolicy.Dependencies`.

### 3) Output formatting/publication is isolated
- Python status rendering lives in `BridgeCliOutputFacade`.
- Java ACK/OUT/TCP monitor publication lives in `BridgeUiOutputFacade`.

### 4) Structured result models cross boundaries
- Python uses `StatusResult` and parsed-line result objects.
- Java uses `BridgeUiCommandResult`.

### 5) Scriptability is preserved
- Python batch and interactive commands share one parser and execution path.
- Robot-side command handling still routes NT and TCP requests through a shared executor pipeline.

## Testing and Regression Strategy
Purpose: describe how the split is kept safe.

### Python focused tests
File:
- `tools/can_nt/tests/test_bridge_cli_facades.py`

Current coverage includes:
- Empty-token validation returns normal status.
- Alias replacement parse failures map to unknown-command status.
- Robot transport send failures map to network send-failed status.

### Existing regression coverage
Examples:
- `tools/can_nt/scripts/bridge_cli_v1_group_targeting_regression.py`
- `tools/can_nt/scripts/bridge_cli_group_targeting_4m2g3t_regression.py`

Purpose:
- Confirm facade splitting preserved externally visible CLI behavior.
- Guard scriptability and command semantics during refactors.

### Java verification
Purpose:
- Compile validation confirms the new top-level Java split remains integrated with the robot project.

## Tradeoffs
Purpose: document the intentional tradeoffs of this architecture.

- The Python CLI is still an orchestrator with significant state; the split narrows boundaries without fully replacing the CLI core.
- The Java command switch still lives in the handler; the executor isolates the common pipeline first, with command-family extraction left as future work.
- Some facades are intentionally thin because the immediate goal is stable boundaries and behavior preservation, not wholesale redesign.
- Narrow context/dependency interfaces reduce coupling, but they add adapter/wiring code in the orchestrator classes.

## Future Directions
Purpose: capture the next safe steps after this split.

- Extract command-family handlers from `BridgeCli` by domain (profiles, groups, tests, diagnostics, runtime).
- Extract command-family handlers from the Java switch path where that improves clarity.
- Add more focused tests for parse context behavior, transport success/failure paths, and Java ingress policy behavior.
- Standardize result-model conventions further across Python and Java command paths.
- Keep `docs/TCP_UI_PROTOCOL.md` and this document aligned when protocol fields or gating rules change.

## File Map Summary
Purpose: provide a quick lookup table.

### Python
- `tools/can_nt/bridge_cli.py` - CLI orchestrator
- `tools/can_nt/bridge_cli_facades.py` - parse/validate/output facades and parse context
- `tools/can_nt/bridge_robot_control_facade.py` - robot command transport facade
- `tools/can_nt/tests/test_bridge_cli_facades.py` - focused facade tests

### Java
- `src/main/java/frc/robot/BridgeUiCommandHandler.java` - handler/orchestrator
- `src/main/java/frc/robot/BridgeUiCommandExecutor.java` - shared execution pipeline
- `src/main/java/frc/robot/BridgeUiIngressPolicy.java` - ingress parse/validate/pre-exec policy
- `src/main/java/frc/robot/BridgeUiCommandResult.java` - shared result model
- `src/main/java/frc/robot/BridgeUiOutputFacade.java` - ACK/OUT/TCP monitor publication facade
