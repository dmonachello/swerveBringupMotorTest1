SPEC_STATUS: PARTIALLY_IMPLEMENTED

# Feature spec: REST typed UI state migration

## Purpose

Define a staged refactor of the Python UI so REST payload fetch/parsing happens in one place, payloads are converted immediately into typed shared state objects, tabs consume those typed objects directly, and the temporary `_RestValueAdapter` / `_RestTableAdapter` compatibility layer is removed.

## Implementation Status

Purpose: Record the completed code migration separately from robot-connected operator acceptance.

- Implementation is complete on `feature/rest-typed-ui-state-migration`.
- Production Python code has no references to `_RestValueAdapter`, `_RestTableAdapter`, `_ui_table`, or `_tests_table`.
- REST payload normalization and typed snapshot construction are owned by `rest_ui_snapshot_service.py` and `rest_ui_state_models.py`.
- Shared UI state and migrated tab consumers read those typed snapshots rather than table-shaped compatibility wrappers.
- Automated acceptance passed on 2026-09-09; robot-connected manual acceptance remains required before this specification can be marked `IMPLEMENTED`.

## Problem

The current UI still carries a transitional compatibility layer in `tools/can_nt/bringup_ui.py` through:

- `_RestValueAdapter`
- `_RestTableAdapter`

Those adapters let table-shaped UI code keep running after the move away from NetworkTables-backed flows. They were useful as a migration bridge, but they now create structural problems:

- raw REST parsing is not fully centralized
- UI code still thinks in table-entry access patterns instead of typed state
- multiple code paths can interpret the same payload shape differently
- tab code remains more tightly coupled to transport details than it should be
- bugs become harder to trace because a REST bug can appear as a fake table-read bug

The adapters also work against the repo’s stated direction:

- one shared-state rule
- no cached-truth rule
- common code must own shared contracts across surfaces

## Goal

Refactor the UI so that:

- raw REST fetch/parsing happens in one authoritative place
- REST JSON is normalized immediately into typed/shared state objects
- all operator-facing tabs consume shared typed state, not fake table wrappers
- transport and payload-shape details stop leaking into tab logic
- adapter usage shrinks to zero and the adapters are deleted

## Non-goals

This spec does not:

- redesign the UI visually
- replace Tkinter
- change the supported REST contract by itself
- require an all-at-once rewrite of `bringup_ui.py`
- change the existing operator-facing rules unless a later implementation slice explicitly does so

## Current state

The current structure is roughly:

- [bringup_ui.py](../tools/can_nt/bringup_ui.py)
  - owns polling, widgets, handlers, local state, and refresh flow
- [host_ui_state_service.py](../tools/can_nt/host_ui_state_service.py)
  - already contains shared typed decision/state objects and pure resolution logic
- [live_topology_view.py](../tools/can_topology/live_topology_view.py)
  - renders topology scenes
- service modules such as:
  - [command_workflow_service.py](../tools/can_nt/command_workflow_service.py)
  - [passive_discovery_integration_service.py](../tools/can_nt/passive_discovery_integration_service.py)
  - [can_fault_inference.py](../tools/can_nt/can_fault_inference.py)

The active transitional seam is in [bringup_ui.py](../tools/can_nt/bringup_ui.py), where REST snapshots are wrapped by `_RestTableAdapter.from_runtime_state(...)` and `_RestTableAdapter.from_tests_state(...)` so legacy table-style code can continue to call:

- `getEntry(...)`
- `getSubTable(...)`
- NT-shaped getters like `getString`, `getBoolean`, `getDouble`

That means the UI is partially REST-native in transport, but still partially table-native in data access.

## Why this refactor is worth doing

### Correctness

A typed state layer reduces ambiguity. A field like `selected_test_name` or `runtime_active` should have one normalized representation, not multiple ad hoc getter paths.

### Shared behavior

When multiple tabs need the same meaning, they should consume one shared typed state record rather than re-reading transport-shaped data.

### Simpler debugging

A bad diagnosis should be traceable as:

1. REST payload received
2. normalized typed snapshot built
3. shared state/decision resolved
4. tab rendered

The fake table layer obscures that chain.

### Better testability

Typed state objects can be created directly in unit tests without building fake nested entry tables.

### Cleaner retirement of historical assumptions

The adapters preserve old NetworkTables-like thinking. Removing them helps complete the architectural shift to supported REST-driven bringup flows.

## Design principles

### One ingestion path

Every REST poll should feed one authoritative ingestion path that:

- receives raw payloads
- validates shape
- normalizes defaults
- records fetch metadata
- emits typed shared state objects

No tab should parse raw REST payloads independently.

### Typed immediately

Raw JSON should exist only at the boundary.

After fetch/parsing, the system should work with typed records, not unstructured dictionaries and not table adapters.

### Shared state before shared decisions

The first layer is typed snapshots of what was received.

The second layer is shared decision logic that derives operator-facing meaning from those snapshots.

Do not mix the two layers.

### Preserve behavior first

Migration should initially preserve current visible behavior, including current quirks that are intentionally relied on, unless an approved slice explicitly changes operator-facing behavior.

### Narrow reversible slices

Each migration slice should remove one adapter dependency cluster at a time and add regressions before deleting old access paths.

## Target architecture

## Layer 1: transport fetch

Purpose: Talk to the REST session and obtain raw JSON payloads.

Owner:

- `bridge_session.py`
- thin fetch helpers in `bringup_ui.py` or a new dedicated REST UI data-source module

Responsibilities:

- connect / handshake state
- fetch `session snapshot`
- fetch `runtime state`
- fetch `tests state`
- fetch other REST-backed snapshots as needed
- timestamp arrival
- report fetch failures

Output:

- raw Python dictionaries exactly reflecting REST payloads
- fetch metadata such as:
  - received time
  - source name
  - request kind
  - failure state

This layer must not expose fake NT/table wrappers.

## Layer 2: REST normalization

Purpose: Convert raw JSON into typed shared snapshot objects.

Recommended new module:

- `tools/can_nt/rest_ui_snapshot_service.py`

Recommended record families:

- `SessionSnapshot`
- `RuntimeSnapshot`
- `TestsSnapshot`
- `PassiveVisibilitySnapshot`
- `EvidenceSnapshot`
- `FaultFinderSnapshot`

Each snapshot should contain:

- normalized scalar fields
- normalized row collections
- explicit optionality
- explicit timestamps/freshness metadata
- raw source revision metadata when useful

Examples:

- `RuntimeSnapshot.runtime_active: bool`
- `RuntimeSnapshot.controlled_lifecycle_active: bool`
- `RuntimeSnapshot.devices_by_label: dict[str, RuntimeDeviceSnapshot]`
- `TestsSnapshot.selected_name: str`
- `TestsSnapshot.rows_by_name: dict[str, TestRowSnapshot]`
- `SessionSnapshot.session_id: str`

This layer should also:

- normalize missing values
- normalize profile/test “none” handling consistently
- normalize label casing rules once
- isolate schema drift handling

## Layer 3: shared UI domain state

Purpose: Hold the current authoritative host-side view of robot/UI state.

Recommended new record:

- `UiSharedState`

It should aggregate the latest normalized snapshots plus host-local context:

- selected local profile
- selected local test
- pending transitions
- tracker pending state
- transport status
- active source status
- cached local config session metadata

This is the state object consumed by shared decision logic.

This layer should be transport-aware only through normalized status fields, not through raw REST dictionaries.

## Layer 4: shared decision services

Purpose: Derive operator-facing meaning from shared typed state.

Primary home:

- [host_ui_state_service.py](../tools/can_nt/host_ui_state_service.py)

This layer already exists in partial form and should be expanded, not replaced.

It should consume typed snapshot/domain objects and compute:

- context sync state
- runnable state
- selected-test scope state
- active-group summaries
- topology scene state
- action gating state
- warning/notice state

## Layer 5: tab/view consumers

Purpose: Render widgets from shared typed state and shared decision outputs.

Each tab should read:

- typed shared state
- shared decision results

Each tab should not read:

- raw REST dictionaries
- `_RestTableAdapter`
- `_RestValueAdapter`
- nested `getEntry(...).getString(...)` style access

## Typed objects to introduce

These names are illustrative, not mandatory. The important part is the contract.

### Session

- `SessionSnapshot`
  - `session_id`
  - `generated_at_ms`
  - `last_activity_ms`
  - `handshake_ready`
  - `owner_known`

### Runtime

- `RuntimeSnapshot`
  - `generated_at_ms`
  - `selected_profile`
  - `active_runtime_profile`
  - `runtime_active`
  - `controlled_lifecycle_active`
  - `robot_enabled`
  - `robot_estopped`
  - `robot_mode`
  - `groups`
  - `devices_by_label`

- `RuntimeDeviceSnapshot`
  - `label`
  - `enabled`
  - `present`
  - `instantiated`
  - `scope_active`
  - `testable`
  - `manual_operable`
  - `test_operable`
  - `lifecycle_state`
  - `active_group_label`
  - `identity`
  - `telemetry`

- `RuntimeGroupSnapshot`
  - `name`
  - `enabled`
  - `primary_label`
  - `members`
  - `binding_active`

### Tests

- `TestsSnapshot`
  - `generated_at_ms`
  - `selected_name`
  - `active_name`
  - `active_status`
  - `run_all_active`
  - `rows_by_name`
  - `ordered_names`

- `TestRowSnapshot`
  - `name`
  - `selected`
  - `enabled`
  - `status`
  - `required_devices`
  - `exists_locally`
  - `runnable_known`

### Optional later snapshots

- `VisibilitySnapshot`
- `EvidenceSnapshot`
- `FaultDiagnosisSnapshot`

The first implementation slices do not need to type every surface at once, but the architecture should reserve room for them.

## Before and after examples

These examples are tied to the current `tools/can_nt/bringup_ui.py` methods that still depend on `_RestTableAdapter` and `_RestValueAdapter`.

## Example 1: `_poll_runtime_ui_state()` building fake tables

### From

Current poll-time boundary logic:

```python
session_snapshot = self._session.fetch_session_snapshot()
runtime_snapshot = self._session.fetch_runtime_state()
tests_snapshot = self._session.fetch_tests_state()

if runtime_table_payload:
    self._ui_table = _RestTableAdapter.from_runtime_state(
        session_snapshot,
        runtime_table_payload,
        fetched_at_ms=fetched_at_ms,
    )
self._tests_table = _RestTableAdapter.from_tests_state(tests_snapshot)
```

Problems:

- raw REST fetch and table-shape translation happen in the UI class
- the transport boundary is hidden inside `_poll_runtime_ui_state()`
- every downstream consumer inherits fake table semantics

### To

Target poll-time boundary:

```python
raw_session = self._session.fetch_session_snapshot()
raw_runtime = self._session.fetch_runtime_state()
raw_tests = self._session.fetch_tests_state()

normalized = build_rest_ui_snapshots(
    raw_session=raw_session,
    raw_runtime=raw_runtime,
    raw_tests=raw_tests,
    received_at_ms=now_ms,
)

self._latest_session_snapshot = normalized.session
self._latest_runtime_snapshot = normalized.runtime
self._latest_tests_snapshot = normalized.tests
self._ui_shared_state = build_ui_shared_state(
    local_ui_state=self._local_ui_state,
    normalized_snapshots=normalized,
)
```

Benefits:

- one explicit REST ingestion boundary
- one explicit normalization step
- no fake tables stored as shared state

## Example 2: `_poll_runtime_ui_state()` reading runtime fields

### From

Current adapter-based field reads:

```python
session_id = self._ui_table.getEntry("state/sessionId").getString("")
enabled = self._ui_table.getEntry("state/enabled").getBoolean(True)
estopped = self._ui_table.getEntry("state/estopped").getBoolean(False)
mode = self._ui_table.getEntry("state/mode").getString("disabled")
last_ack_ms = self._ui_table.getEntry("state/lastAckMs").getDouble(0.0)
self._robot_selected_profile = _normalize_profile_name(
    self._ui_table.getEntry(NT_UI_STATE_SELECTED_PROFILE).getString(PROFILE_NONE)
)
self._robot_active_runtime_profile = _normalize_profile_name(
    self._ui_table.getEntry(NT_UI_STATE_ACTIVE_RUNTIME_PROFILE).getString(PROFILE_NONE)
)
```

Problems:

- typed meaning is reconstructed at each read site
- default values are embedded in widget/update logic
- field-path knowledge leaks out of normalization

### To

Typed runtime snapshot access:

```python
runtime_snapshot = self._latest_runtime_snapshot
session_snapshot = self._latest_session_snapshot

session_id = session_snapshot.session_id
enabled = runtime_snapshot.robot_enabled
estopped = runtime_snapshot.robot_estopped
mode = runtime_snapshot.robot_mode
last_ack_ms = runtime_snapshot.last_ack_ms
self._robot_selected_profile = runtime_snapshot.selected_profile
self._robot_active_runtime_profile = runtime_snapshot.active_runtime_profile
```

Benefits:

- one canonical field contract
- defaults and profile normalization happen once
- callers read domain state instead of encoded paths

## Example 3: `_resolve_selected_from_rows()` removal

### From

Current helper:

```python
if self._tests_table is None:
    return ""
total = int(self._tests_table.getEntry("totalCount").getDouble(0.0))
rows = self._tests_table.getSubTable("rows")
if total <= 0:
    return ""
for i in range(total):
    row = rows.getSubTable(str(i))
    if row.getEntry("selected").getBoolean(False):
        return row.getEntry("name").getString("")
return ""
```

Problems:

- test selection fallback depends on synthetic `totalCount` and string-index rows
- selected-row detection is reimplemented in a UI helper
- this helper exists only because normalization stopped too early

### To

Selection resolved by normalization:

```python
tests_snapshot = self._latest_tests_snapshot
selected_name = tests_snapshot.selected_name
```

Benefits:

- one authoritative selected-test value
- no row scanning helper in the UI layer
- easier regression testing around selection drift

## Example 4: `_resolve_test_names_from_rows()` and `_sync_test_dropdown_values()`

### From

Current row scan:

```python
if self._tests_table is None:
    return []
total = int(self._tests_table.getEntry("totalCount").getDouble(0.0))
rows = self._tests_table.getSubTable("rows")
if total <= 0:
    return []
names: List[str] = []
for i in range(total):
    row = rows.getSubTable(str(i))
    name = str(row.getEntry("name").getString("") or "").strip()
    if name and name not in names:
        names.append(name)
return names
```

Then in `_poll_runtime_ui_state()`:

```python
test_names = self._resolve_test_names_from_rows()
if selected_name and selected_name != PROFILE_NONE and selected_name not in test_names:
    test_names = test_names + [selected_name]
self._sync_test_dropdown_values(test_names)
```

### To

Current robot-known names are part of the typed snapshot:

```python
tests_snapshot = self._latest_tests_snapshot
test_names = list(tests_snapshot.ordered_names)
if tests_snapshot.selected_name and tests_snapshot.selected_name not in test_names:
    test_names.append(tests_snapshot.selected_name)
self._sync_test_dropdown_values(test_names)
```

Or, after a fuller migration:

```python
self._sync_test_dropdown_values_from_snapshot(self._latest_tests_snapshot)
```

Benefits:

- row ordering and uniqueness are centralized
- `_sync_test_dropdown_values()` stops caring about table row shape
- robot-known test inventory becomes testable as a single snapshot contract

## Example 5: active test/run state inside `_poll_runtime_ui_state()`

### From

Current adapter reads:

```python
active_name = self._tests_table.getEntry("activeName").getString("")
active_status = self._tests_table.getEntry("activeStatus").getString("")
run_all = self._tests_table.getEntry("runAllActive").getBoolean(False)
running = "(none)"
if active_name:
    running = active_name
    if active_status:
        running += f" ({active_status})"
    if run_all:
        running += " [run all]"
```

### To

Typed tests snapshot:

```python
tests_snapshot = self._latest_tests_snapshot
running = format_running_label(
    active_name=tests_snapshot.active_name,
    active_status=tests_snapshot.active_status,
    run_all_active=tests_snapshot.run_all_active,
)
```

Benefits:

- tests-run state has a typed contract
- string formatting can move into common code
- `run` payload interpretation is not spread across the UI

## Example 6: `_runtime_device_confirms_scope_member()` raw dict reads

### From

Current code reads `_latest_runtime_devices` as untyped dicts:

```python
runtime_device = runtime_devices.get(label_key)
if not isinstance(runtime_device, dict):
    return False
if str(runtime_device.get("lifecycleState", NT_VALUE_EMPTY)).strip().lower() == "controlled-active":
    return True
if bool(runtime_device.get("manualOperable", False)):
    return True
if bool(runtime_device.get("testOperable", False)):
    return True
if bool(runtime_device.get("testable", False)):
    return True
active_group_label = str(runtime_device.get("activeGroupLabel", NT_VALUE_EMPTY)).strip().lower()
return active_group_label == GROUP_ACTIVE_NAME
```

### To

Typed runtime-device lookup:

```python
runtime_device = self._latest_runtime_snapshot.devices_by_label.get(label_key)
if runtime_device is None:
    return False
if runtime_device.lifecycle_state == LIFECYCLE_STATE_CONTROLLED_ACTIVE:
    return True
if runtime_device.manual_operable or runtime_device.test_operable or runtime_device.testable:
    return True
return runtime_device.active_group_label_normalized == GROUP_ACTIVE_NAME
```

Benefits:

- scope-membership rules stop depending on raw JSON keys
- device-row shape is explicit and shared
- this closes one more gap between adapter-backed and dict-backed consumers

## Example 7: `_fetch_runtime_state_snapshot()` and `_poll_runtime_ui_state()` convergence

### From

`_fetch_runtime_state_snapshot()` already fetches raw REST and applies runtime payload directly:

```python
runtime_snapshot = self._session.fetch_runtime_state()
if not isinstance(runtime_snapshot, dict) or not runtime_snapshot:
    ...
self._apply_runtime_state_payload(runtime_snapshot)
```

But `_poll_runtime_ui_state()` separately fetches session/runtime/tests, caches raw dicts, and rebuilds adapters. That means there are two partially overlapping runtime ingestion paths.

### To

Both methods should converge on one shared normalization entry point:

```python
normalized = self._rest_ui_snapshot_service.fetch_and_normalize(
    include_session=True,
    include_runtime=True,
    include_tests=include_tests,
    received_at_ms=now_ms,
)
self._apply_normalized_ui_state(normalized)
```

Benefits:

- one runtime ingestion contract
- fewer chances for poll path and manual refresh path to diverge
- easier instrumentation when debugging stale or partial state

## Example 8: tests no longer build fake table fixtures

### From

Today, UI tests can end up depending on synthetic table state:

```python
ui._tests_table = _SubTableStub(
    entries={"selectedName": "mtrs_limit", "totalCount": 2},
    subtables={
        "rows": _SubTableStub(
            subtables={
                "0": _SubTableStub(entries={"name": "mtrs_limit", "selected": True}),
                "1": _SubTableStub(entries={"name": "newTests_123", "selected": False}),
            }
        )
    },
)
```

### To

Tests should inject typed snapshots:

```python
ui._latest_tests_snapshot = TestsSnapshot(
    generated_at_ms=1000.0,
    selected_name="mtrs_limit",
    active_name="",
    active_status="",
    run_all_active=False,
    ordered_names=("mtrs_limit", "newTests_123"),
    rows_by_name={
        "mtrs_limit": TestRowSnapshot(name="mtrs_limit", selected=True),
        "newTests_123": TestRowSnapshot(name="newTests_123", selected=False),
    },
)
```

Benefits:

- tests state their intent directly
- no fake `getEntry()` / `getSubTable()` scaffolding
- normalization tests and UI consumer tests can be separated cleanly
- fixtures become smaller and clearer
- less fake infrastructure is required just to validate UI logic

## Migration plan

### Slice 1: inventory and boundary lock

Purpose: Make the current adapter surface explicit before changing behavior.

Tasks:

- enumerate every `_ui_table` and `_tests_table` consumer in `bringup_ui.py`
- classify each use as:
  - runtime state read
  - tests state read
  - selection sync
  - action gating
  - topology rendering support
  - status text support
- document which call sites still rely on:
  - `getEntry`
  - `getSubTable`
  - `totalCount`
  - `rows`

Deliverable:

- adapter dependency inventory in this spec or a companion tracking document

Exit condition:

- no hidden adapter consumers remain

### Slice 2: typed runtime/tests snapshots

Purpose: Introduce typed REST snapshots without deleting old paths yet.

Tasks:

- add typed snapshot classes
- add one normalizer service for runtime/tests/session payloads
- build snapshots inside the poll path immediately after fetch
- store the latest typed snapshots on the UI controller
- add tests for normalization edge cases

Rules:

- old adapter-based consumers may continue temporarily
- typed snapshots must be authoritative for all new code

Exit condition:

- poll path always produces typed runtime/tests/session snapshots

### Slice 3: move shared decision logic to typed inputs

Purpose: Stop shared decision services from depending on fake table reads or raw dictionaries.

Tasks:

- update `host_ui_state_service.py` call sites to accept typed values/records
- add adapters only at service boundaries if necessary during transition
- convert context sync, runnable state, selected-test state, and scope control logic first

Exit condition:

- shared decision layer consumes typed snapshots, not `_RestTableAdapter`

### Slice 4: convert Tests-tab consumers

Purpose: Remove adapter usage from the highest-friction state machine first.

Reason:

- Tests tab currently has the most selection/sync complexity
- many recent bugs involved selected test, robot selected test, and scope activation

Tasks:

- replace `_tests_table` reads with `TestsSnapshot`
- replace helper methods that scan fake table rows
- keep one shared selected-test contract between:
  - current test label
  - selected test devices
  - readiness/runnable panels
  - run/activate/deactivate buttons

Exit condition:

- Tests tab no longer needs `_RestTableAdapter.from_tests_state(...)`

### Slice 5: convert top bar and runtime-gating consumers

Purpose: Move global action and status logic to typed state.

Tasks:

- convert runtime activation/deactivation gating
- convert context-sync banner/prompt state
- convert transport/runtime status reads
- remove NT-shaped getter patterns from top-level action code

Exit condition:

- global action/state logic no longer depends on fake table objects

### Slice 6: convert remaining surfaces

Purpose: Finish tab consumers incrementally.

Expected areas:

- Live Topology selection panel support
- Output / status detail helpers
- Evidence panel support where it still reads runtime/tests state
- any remaining diagnostics surfaces using `_ui_table` / `_tests_table`

Exit condition:

- no production code path reads `_RestValueAdapter` / `_RestTableAdapter`

### Slice 7: delete adapters

Purpose: Remove the compatibility layer entirely.

Tasks:

- delete `_RestValueAdapter`
- delete `_RestTableAdapter`
- delete dead compatibility helpers
- delete tests that only validate fake-table behavior
- keep tests that validate behavior contracts through typed state

Exit condition:

- adapters removed
- all tests green

## Required contracts

### Single authoritative selected-test contract

Selected test must exist in one normalized host-side field and one robot-side field. All tabs and actions must consume that shared meaning.

No tab may infer selected test from row iteration if a normalized selected-test field already exists.

### Single authoritative runtime device map

Runtime device state by label must be normalized once and shared everywhere.

No surface should rebuild device maps independently from raw payload dictionaries.

### Explicit freshness

Typed snapshots must carry freshness metadata. Later logic must not guess freshness from arbitrary timestamps or side caches.

### Deterministic PROFILE_NONE normalization

Profile/test none-state handling must be centralized. The refactor must reduce, not increase, stringly-typed none/empty drift.

## Testing strategy

### Unit tests

Add narrow tests for:

- payload normalization
- missing field defaults
- malformed field handling
- selected test normalization
- runtime device map normalization
- profile/test none handling

### UI logic regression tests

Preserve and expand current tests around:

- context sync
- selected test preservation
- runtime activate/deactivate gating
- tab-specific selected-test behavior

Those tests should gradually shift from fake table stubs toward typed snapshot fixtures.

### Replay / fixture tests

Store representative REST payload fixtures for:

- disconnected state
- runtime inactive
- runtime active manual scope
- runtime active selected-test scope
- profile mismatch
- test mismatch
- stale runtime state

Use those fixtures to verify typed normalization and downstream decisions.

## Testing Results

Purpose: Preserve automated acceptance evidence for the completed migration.

TESTING_RESULTS: 2026-09-09 automated acceptance passed.

- `python -m pytest tools\\can_nt\\tests tools\\common\\tests -q`: 849 passed.
- `python tools\\can_nt\\scripts\\run_regressions.py --suite local`: 10 of 10 bundles passed, including the Java unit suite.
- A production-code search found no references to `_RestValueAdapter`, `_RestTableAdapter`, `_ui_table`, or `_tests_table`.

Remaining manual acceptance is limited to robot-connected workflow verification described below.

### Manual verification

Check at minimum:

1. profile select and push flow
2. manual active-group flow
3. selected-test activation/deactivation flow
4. runtime activate from Tests tab
5. runtime activate from Live Topology
6. mismatch LED/prompt behavior
7. reconnect/restart behavior

## Risks

### Hidden adapter consumers

Risk:

- a tab or helper still depends on table semantics after most code is migrated

Mitigation:

- explicit inventory first
- delete by slice
- grep-based gate before final removal

### Behavior drift during cleanup

Risk:

- migration unintentionally changes selected-test or scope semantics

Mitigation:

- keep behavior-preservation regressions
- make behavior changes only in explicit approved slices

### Two truths during transition

Risk:

- typed state and adapter-backed state diverge

Mitigation:

- typed snapshots become authoritative as soon as introduced
- old reads become compatibility-only
- remove parallel ownership quickly

### Large-file gravity

Risk:

- `bringup_ui.py` stays large even after adapters are removed

Mitigation:

- this spec focuses on transport/data-shape cleanup first
- later specs may split controller/view responsibilities further

## Tradeoffs

- Short term, this adds types and normalization code before deleting old code.
- That is extra complexity during migration, but it reduces long-term ambiguity.
- A staged migration is slower than a rewrite, but far safer for this repo’s current bug-fix-heavy state.

## Future extensions

- move more host-local state into typed controller state objects
- create typed fixture generators for UI regression tests
- unify evidence/runtime/tests snapshots under a broader host shared-state model
- shrink `bringup_ui.py` further by moving tab-specific presenters out after adapter removal

## Definition of done

This refactor is done when:

- REST fetch/parsing happens in one authoritative path
- runtime/tests/session snapshots are normalized immediately into typed objects
- shared decision services consume typed state
- tabs no longer read fake table adapters
- `_RestValueAdapter` and `_RestTableAdapter` are deleted
- existing UI behavior regressions still pass
- manual validation confirms no operator workflow regressions in the affected tabs
