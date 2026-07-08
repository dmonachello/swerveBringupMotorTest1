# NetworkTables Contract

## Purpose
Record that the old bringup NetworkTables contract has been retired.

## Current State
- Supported bringup control, UI, CLI, and reporting workflows are REST-driven or host-local.
- The Python host bridge no longer publishes `bringup/diag/...` keys.
- The robot no longer depends on host-published NT diagnostics for supported workflows.
- Legacy `bringup/tests/...` publish tables are also removed from the supported host/UI path.

## Historical Note
- Earlier versions used NetworkTables as a bridge between:
  - the Windows CANable host tool
  - the roboRIO bringup harness
  - optional dashboards and compatibility readers
- That contract was removed in phase 2 of NT removal.

## Replacement Contracts
- Robot command/control:
  - REST via `tools/can_nt/bridge_session.py`
- Robot runtime/tests state:
  - REST `/runtime/state`
  - REST `/tests/state`
- Host CAN visibility:
  - in-process `VisibilityProvider`
- Host console diagnostics:
  - in-process `ConsoleMonitor`

## Rules
- Do not add new bringup functionality on top of NetworkTables.
- If a new host/robot contract is needed, define it explicitly as REST, generated artifacts, or host-local shared state.
- If NetworkTables appears in new bringup code, treat it as an architectural regression unless the change is explicitly justified and documented.
