SPEC_STATUS: RESEARCH_ONLY

# Robot Diagnostic Architecture v0.5

Version: 0.5 Draft

Status: Proposed

Supersedes:

- Everything Is DSL v0.1
- Hardware Execution Via DSL, Information Access Via REST v0.2
- Robot Diagnostic API Architecture v0.3
- Robot Diagnostic Architecture v0.4 Draft

## 1. Purpose

Purpose: define the target top-level architecture for the Robot Diagnostic System.

This architecture separates:

- execution
- information access
- transport

The primary goals are:

- one execution model
- one safety model
- one ownership model
- one consistent user experience across CLI, UI, automation, and future tools

Primary mental model:

- the robot acts as the DSL execution VM
- normalized DSL is the VM program format
- the host is the authoring and compilation environment

## 2. Core Principle

All hardware-affecting behavior executes through the DSL runtime.

All information access occurs through REST.

Transport mechanisms are implementation details below the device/provider layer and are invisible to the DSL runtime.

Important clarification:

- the robot does not need to compile DSL source
- the robot only needs to execute normalized DSL payloads
- host-side tools may still own source authoring, source preview, source compilation, and group expansion

Equivalent VM statement:

- the robot does not need to compile source code for the VM
- the robot only needs to execute normalized programs

## 3. Architectural Planes

The system consists of two primary planes:

```text
Execution Plane
Information Plane
```

In VM terms:

- the Execution Plane is the VM runtime
- the Information Plane is the VM inspection and management surface

### 3.1 Execution Plane

Implemented by:

```text
DSL Runtime
Execution Manager
Runtime Gate
```

Responsible for:

- commanding hardware
- executing tests
- enforcing ownership
- enforcing safety
- determining `PASS`
- determining `FAIL`
- determining `INTERRUPTED`
- determining `CANCELLED`

All hardware-affecting behavior executes through the DSL runtime.

No alternate actuation path should survive as a first-class architecture concept.

In VM terms, this plane is the robot-side program execution subsystem.

### 3.2 Information Plane

Implemented by:

```text
REST API
Reports
Inspection Surfaces
```

Responsible for:

- status inspection
- reporting
- execution management
- configuration access
- topology access
- historical data access
- signal inspection

The REST API never directly commands hardware.

REST manages DSL execution and runtime lifecycle, but does not replace DSL execution.

## 4. Two Gates

The target architecture has two distinct gates:

1. runtime gate
2. execution gate

In VM terms:

- the runtime gate controls whether the VM is loaded and ready
- the execution gate controls whether the VM is currently running a program

### 4.1 Runtime Gate

The runtime gate is controlled by:

```text
Runtime Activate
Runtime Deactivate
```

When runtime is active:

- devices may be instantiated
- devices may be read
- reports and live telemetry may be available
- no writable ownership exists unless an execution is running

VM interpretation:

- the VM is loaded and ready
- local devices/providers are bound
- no program currently owns writable behavior

When runtime is inactive:

- no execution may run
- no hardware-affecting behavior may occur

VM interpretation:

- the VM is unavailable for program execution

### 4.2 Execution Gate

The execution gate is controlled by the execution manager.

When no execution is running:

- runtime may still be active
- telemetry/read access may still be available
- no actuation owner exists

VM interpretation:

- the VM is idle

When an execution is running:

- exactly one execution owns hardware-affecting behavior
- all writable behavior is mediated by the DSL runtime

VM interpretation:

- one normalized program is in execution

## 5. Lifecycle States

The target state model is:

### 5.1 Runtime Inactive, No Execution

- no actuation
- no active hardware owner
- runtime-owned resources are not active

### 5.2 Runtime Active, No Execution

- devices instantiated and readable
- inspection available
- no writable ownership
- any jog/manual/run action must start a DSL execution

### 5.3 Runtime Active, Execution Running

- exactly one execution owns writable behavior
- all motor/jog/test actions are part of that execution

### 5.4 Disable / E-Stop / Cancel

- active execution is stopped
- runtime safing runs
- runtime is forced inactive

## 6. Ownership Model

The robot owns:

```text
Device Registry
Signal Registry
Proxy Device Providers
DSL Runtime
Execution Manager
REST API
Execution Records
Stored Tests
```

In VM terms, the robot owns the execution runtime and the local device/signal world visible to programs.

The host owns:

```text
Topology
Groups
Selections
Labels
Diagrams
Editors
UI State
Source Authoring
Source Compilation
Preview UX
```

In VM terms, the host owns the toolchain around the VM, not the execution engine itself.

Host-side concepts are never required by the robot runtime.

## 7. Device Model

The Device Registry is the single source of truth for all DSL-visible devices at runtime.

All signal sources visible to DSL are represented as devices.

The DSL runtime does not distinguish between:

- physical devices
- proxy devices
- other virtual devices

Examples:

```text
device "FLDrive"
device "controller0"
device "JogSlider"
device "RunButton"
```

All are treated as devices by the DSL runtime.

VM interpretation:

- devices are the VM's external interface surface
- the VM does not care whether a device is physical or proxy-backed

## 8. Physical Devices

Examples:

```text
SparkMax
TalonFX
CANcoder
LimitSwitch
XboxController
```

These devices obtain data from robot hardware or robot-local input systems.

## 9. Proxy And Virtual Devices

Examples:

```text
JogSlider
RunButton
HostJoystick
```

These devices obtain data from software providers, but they must still appear as robot-local devices to the DSL runtime.

Rules:

- proxy devices must be declared in DSL like any other device
- proxy devices are backed by robot-local provider code
- transport messages update provider state
- the DSL runtime reads only local device/provider state

The runtime must not directly consume host transport messages as execution inputs.

VM interpretation:

- transport updates local VM inputs through providers
- programs execute only against local device/provider state

## 10. Device Abstraction Rule

Upper layers must not care how device data is obtained.

Examples of hidden acquisition mechanisms:

```text
CAN
DIO
PWM
REST
WebSocket
UDP
NetworkTables
Shared Memory
Local Variables
```

These are implementation details below the device/provider abstraction.

The Device Registry presents a uniform device abstraction to:

```text
DSL Runtime
REST API
Reports
```

## 11. Group Expansion Rule

Groups are host-side concepts.

Example:

```text
DriveMotors
    FLDrive
    FRDrive
    BLDrive
    BRDrive
```

Before execution, a host-side tool must expand group references into explicit device declarations.

Example:

```text
device "FLDrive"
device "FRDrive"
device "BLDrive"
device "BRDrive"
```

The robot never evaluates host group definitions.

The robot executes explicit normalized DSL only.

VM interpretation:

- the robot executes explicit normalized programs only

This prevents disagreement between host and robot about group membership.

## 12. Execution Model

Every hardware-affecting user action becomes a DSL execution.

Examples:

```text
Run Motor
Run Group
Run Selection
Smoke Test
Subsystem Test
Jog Motor
```

Flow:

```text
User Action
    ↓
Generate DSL Source or Normalized DSL on Host
    ↓
Submit Normalized Execution Envelope to Robot
    ↓
Execute Through DSL Runtime
```

The generated DSL should remain viewable and inspectable even when one-click execution is allowed.

VM interpretation:

- every hardware-affecting user action is program generation plus program submission to the VM

## 13. Execution Envelope

Ad hoc execution requests use a dedicated execution envelope.

The robot accepts normalized DSL, not raw source compilation requests.

VM interpretation:

- this envelope is the VM program submission format

The envelope contains:

- normalized DSL test body
- execution metadata
- optional original source text for traceability

Suggested fields:

```text
executionName
normalizedTest
sourceText
sourceHash
generatedBy
generatedAt
requestedBy
```

Notes:

- `normalizedTest` reuses the existing normalized DSL test shape
- the envelope is an execution API contract, not a storage-shape alias
- host-side source text remains useful for inspection and history, but is not required for execution

The robot should not need a second source compiler in order to behave like the VM.

## 14. Execution Record

Every DSL execution produces an Execution Record.

Suggested fields:

```text
executionId
startTime
endTime
status
normalizedTest
sourceText
sourceHash
result
terminationReason
generatedBy
requestedBy
```

Status values:

```text
PENDING
RUNNING
PASS
FAIL
INTERRUPTED
CANCELLED
```

Only one execution may be active at a time.

If an execution request arrives while another execution is active:

- the new request is rejected
- the current execution is not replaced

VM interpretation:

- the VM is single-program-at-a-time

## 15. Runtime And Execution Interaction

The runtime gate and execution gate interact as follows:

- execution start requires runtime active
- runtime deactivate cancels active execution first
- Driver Station disable cancels active execution and forces runtime inactive
- E-stop cancels active execution and forces runtime inactive
- no execution may outlive the runtime gate

VM interpretation:

- a program cannot survive VM teardown

## 16. REST API

Base path:

```text
/api/v1
```

REST provides:

- inspection
- reporting
- runtime lifecycle management
- execution lifecycle management
- configuration access

REST does not directly command hardware.

## 17. Runtime Resources

### 17.1 Activate Runtime

```text
POST /api/v1/runtime/activate
```

Behavior:

- instantiate and prepare runtime-owned hardware/resources
- allow read/inspection access
- do not start execution ownership

VM interpretation:

- load and bind the VM runtime without starting a program

### 17.2 Deactivate Runtime

```text
POST /api/v1/runtime/deactivate
```

Behavior:

- cancel active execution if present
- safe outputs
- release runtime-owned resources

VM interpretation:

- stop the active program, then unload the VM runtime

### 17.3 Runtime State

```text
GET /api/v1/runtime/state
```

Returns:

- runtime active/inactive
- current mode constraints
- active execution id, if any
- readiness and ownership state

## 18. DSL Execution Resources

### 18.1 Start Execution

```text
POST /api/v1/dsl/executions
```

Input:

- execution request envelope

Behavior:

- validate normalized payload shape
- allocate execution id
- verify runtime is active
- reject if another execution is already running
- acquire execution ownership
- start execution

VM interpretation:

- submit one normalized program to the VM and start it

### 18.2 Active Execution

```text
GET /api/v1/dsl/executions/active
```

Returns:

- execution state
- status
- ownership information

### 18.3 Cancel Execution

```text
DELETE /api/v1/dsl/executions/active
```

Behavior:

- stop execution
- perform runtime safing
- release execution ownership

Result:

```text
CANCELLED
```

This is the standard remote abort mechanism.

### 18.4 Execution History

```text
GET /api/v1/dsl/executions/history
```

### 18.5 Execution Result

```text
GET /api/v1/dsl/executions/{id}/result
```

Returns:

- result
- timing
- evidence
- failures
- execution metadata

## 19. Stored Tests

Stored tests are executable normalized DSL artifacts with optional source text for authoring traceability.

VM interpretation:

- stored tests are saved programs for the VM

Stored tests are not:

```text
Groups
Topology Objects
UI Artifacts
Selections
```

### 19.1 List Tests

```text
GET /api/v1/stored-tests
```

### 19.2 Retrieve Test

```text
GET /api/v1/stored-tests/{name}
```

Returns:

- normalized test
- optional source text
- optional metadata

### 19.3 Execute Test

```text
POST /api/v1/stored-tests/{name}
```

Behavior:

- load stored normalized DSL
- create an execution request
- execute through the same execution path as ad hoc runs

### 19.4 Delete Test

```text
DELETE /api/v1/stored-tests/{name}
```

Optional.

## 20. Proxy Input Staleness Rule

Proxy device staleness may force-cancel an execution.

This is in addition to authored DSL conditions such as:

```text
abort JogSlider.stale
```

The runtime should infer proxy dependencies from the normalized test body.

Recommended rule:

- if a proxy device is referenced by the execution, it is execution-critical
- if the runtime determines that provider is stale beyond policy, the execution may be force-cancelled

This avoids silent continuation under dead host input state.

## 21. Proxy Input Transport

Proxy device values may arrive through:

```text
REST
WebSocket
UDP
NetworkTables
```

These are implementation details.

The execution path is always:

```text
Transport
    ↓
Provider
    ↓
Device Registry
    ↓
DSL Runtime
```

Equivalent VM path:

```text
Transport
    ↓
Provider
    ↓
Local VM Input Device
    ↓
Program Execution
```

## 22. Interactive Jog Example

Generated DSL:

```text
test "temp_jog"

device "ArmMotor"
device "JogSlider"

main:
    set "ArmMotor".output = JogSlider.value scaled 1.0 default 0.0

    abort JogSlider.stale

    until JogSlider.released
    until timer.elapsed >= 10.0
```

Host updates:

```text
JogSlider.value
JogSlider.released
JogSlider.stale
```

through the provider layer.

The UI may still allow one-click run, but that run must still become a DSL execution internally.

## 23. Reports

Reports belong entirely to the Information Plane.

Reports are not DSL.

Reports may consume:

```text
Signal Values
Execution Results
Topology
Configuration
Logs
History
```

Examples:

```text
Motor Summary
CAN Health
Power Health
Execution History
Device Inventory
```

Reports never command hardware.

## 24. UI Rule

Any UI action that affects hardware must generate or submit DSL execution content.

Examples:

```text
Run Motor
Run Group
Run Selection
Smoke Test
Subsystem Test
Jog Motor
```

One-click execution is allowed.

Mandatory preview is not required.

But the generated DSL or normalized execution content should remain inspectable for:

- transparency
- debugging
- DSL education
- reproducibility

VM interpretation:

- one-click run does not eliminate the underlying program artifact

## 25. Safety Rule

The DSL runtime is the sole authority for:

```text
Execution Ownership
Startup Safing
Shutdown Safing
Abort Handling
Pass/Fail Determination
Cancel Handling
```

The runtime gate is the sole authority for:

```text
Runtime Activation
Runtime Deactivation
Resource Availability
```

No REST endpoint should directly set motor outputs.

No alternate execution path should bypass DSL runtime safety behavior.

VM interpretation:

- the VM is the sole hardware-affecting execution authority

## 26. Legacy Compatibility Direction

The current system still contains non-DSL execution-era concepts such as:

- direct manual motor duty paths
- non-DSL jog behavior
- command-specific execution logic outside the DSL runtime

Under this target architecture, those are transitional legacy paths.

The migration goal is:

- preserve operator capabilities
- re-route them internally through normalized DSL execution
- remove hardware-affecting special paths over time

Equivalent VM goal:

- preserve workflows
- collapse actuation into one VM program model

## 27. Tradeoffs

Benefits:

- one execution engine
- one ownership model
- one safety model
- one actuation mental model
- clearer separation between host authoring and robot execution

Costs:

- host-generated actions must produce normalized DSL envelopes
- proxy providers need explicit robot-local provider infrastructure
- some current convenience paths become migration work instead of stable APIs

## 28. Future Extensions

Possible extensions:

- stronger typed execution envelope schema
- richer execution dependency metadata
- saved ad hoc execution replay
- execution templates for UI actions
- optional source-presence requirements for audit-heavy environments

## 29. Long-Term Vision

The robot ultimately exposes two major subsystems:

```text
Execution Plane
    DSL Runtime
    Execution Manager
    Runtime Gate

Information Plane
    REST API
    Reports
```

All hardware-affecting behavior flows through normalized DSL execution.

All inspection, reporting, configuration access, and execution management flow through REST.

The Device Registry provides a unified abstraction layer that hides the source of signal data and presents physical and proxy devices identically to the execution and information planes.

Concise long-term phrasing:

- the host compiles, previews, and submits programs
- the robot acts as the DSL execution VM
- the VM runs one normalized diagnostic program at a time against a local device/signal world
