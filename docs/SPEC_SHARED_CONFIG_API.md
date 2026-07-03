# Spec: Shared Config API

## Purpose

Define the single required host-side API for working with `bringup_system.json`.

The goal is:

- every host application uses the same config interface
- no application reads or writes `bringup_system.json` directly
- path resolution, file IO, stamping, query semantics, mutation semantics, and save/sync behavior are owned by one shared layer

## Problem

Purpose: state the design problem this API is solving.

Today, config access is split across:

- CLI code
- Bringup Control UI code
- topology/editor tooling
- helper scripts and wizards
- lower-level shared helpers

The current codebase already has useful shared pieces:

- `ConfigLifecycleService`
- `LocalConfigQueryService`
- schema/store helpers
- DSL workflow helpers

But access is still too open:

- some code still reads raw JSON directly
- some code still writes raw JSON directly
- some code still chooses its own config path rules
- some code still mutates root payload dictionaries directly
- some tools still implement partial save/sync behavior themselves

That means:

- drift in semantics
- duplicated logic
- inconsistent dirty-state behavior
- inconsistent query precedence
- too many ways to accidentally bypass shared rules

## Hard Rule

Purpose: make the intended enforcement rule explicit.

For `bringup_system.json`, all host applications must use the shared config API.

Disallowed outside the shared config API implementation:

- direct `read_json(...)` on `bringup_system.json`
- direct `write_json(...)` on `bringup_system.json`
- direct path resolution for canonical/deploy config copies
- direct mutation of the root config dictionary as an application workflow
- surface-local query precedence for profiles/tests/DSL/config state

Allowed:

- small scripts whose sole purpose is migration, repair, or one-shot maintenance may use a lower-level compatibility adapter, but that adapter must still be owned by the shared config API package
- tests may construct in-memory payload fixtures
- tests that persist a valid temporary `bringup_system.json` file must do so through the shared config API, not direct JSON file writes

Explicitly not allowed:

- Bringup Control UI
- Bridge CLI
- CAN Topology Editor
- shared support code that exists primarily to serve those applications

## Scope

Purpose: define what this API covers.

This API covers:

- local config path resolution
- opening/loading config
- querying config
- editing config
- dirty tracking
- validation and stamping
- saving and syncing canonical/deploy copies
- shared sub-APIs for profile/device/group/test/DSL access

This API does not directly cover:

- robot REST push/download transport
- NetworkTables publishing
- bindings in `bringup_bindings.json`

Those may call this API, but they are not the API itself.

This API effort also does not require an on-disk schema redesign for `bringup_system.json`.

The intent is:

- stabilize and centralize access to the current schema
- hide raw structure behind a shared API
- preserve current on-disk behavior unless a separate schema migration is explicitly planned

## Exception Boundary

Purpose: make the temporary exception narrow and explicit.

The direct-access exception exists only for small migration/repair utility programs.

Allowed exception class:

- short-lived migration scripts
- repair scripts
- cleanup scripts
- one-shot maintenance utilities

Examples of the intended exception class:

- migrate schema/key format
- clean up stale config content
- move old persisted data into a new representation

This exception is not for major operator surfaces.

Explicitly disallowed from bypassing the shared config API:

- Bridge CLI
- Bringup Control UI
- CAN Topology Editor

Also disallowed:

- long-lived shared libraries used by those applications
- convenience helpers written for those applications
- new feature scripts that are effectively mini-apps

Rule of thumb:

- if the code is part of daily operator workflow, it must use the shared config API
- if the code is a temporary migration or repair utility, a compatibility adapter is acceptable during transition

Important limit:

- the exception is temporary
- those utilities must also be migrated to shared-config-API-only usage over time

## Design Principles

Purpose: define the rules that shape the API.

### 1. One entrypoint

Every app should obtain config access through one top-level shared object family.

### 2. No raw root-dict ownership in surfaces

CLI, UI, editor, and wizards should not own root-payload mutation logic.

### 3. Read paths and write paths must share semantics

The same layer that answers:

- what profiles exist
- what tests exist
- which DSL tests belong to a profile

must also own the mutation rules that affect those answers.

### 4. Explicit save boundary

Mutation in memory and persistence to disk must be separate, explicit operations.

### 5. Dirty state is shared

Unsaved-change semantics must come from the shared config API, not per-surface booleans.

### 6. Snapshots first, formatting second

Applications should consume structured objects and results, then format them for CLI/UI.

### 7. Compatibility adapters are allowed

The API can expose raw-payload views for legacy code during migration, but those adapters must still be owned by the shared config layer.

### 8. Access refactor first, schema redesign later if ever needed

The shared config API should be built around the current schema first.

Reason:

- the main problem being solved here is access discipline and ownership
- changing schema at the same time would increase migration risk and test scope
- the API boundary should reduce the need for future schema-aware code in major apps

If a schema redesign is ever needed, it should be a separate planned effort after the shared API boundary exists.

## Proposed Module Area

Purpose: define where this API should live.

Recommended location:

- `tools/common/config_api/`

If keeping work near current code is preferred, an acceptable alternative is:

- expand `tools/common/config_lifecycle/` into a fuller config API package

Preferred package split:

- `tools/common/config_api/repository.py`
- `tools/common/config_api/session.py`
- `tools/common/config_api/models.py`
- `tools/common/config_api/results.py`
- `tools/common/config_api/query_api.py`
- `tools/common/config_api/edit_api.py`
- `tools/common/config_api/validation_api.py`
- `tools/common/config_api/compat.py`

## Top-Level API Shape

Purpose: define the top-level objects applications are allowed to use.

Recommended top-level types:

- `ConfigRepository`
- `ConfigSnapshot`
- `ConfigEditSession`
- `ConfigSaveResult`
- `ConfigValidationResult`

### 1. `ConfigRepository`

Purpose: own file/path/source access and create snapshots or edit sessions.

Primary responsibilities:

- resolve canonical and deploy config paths
- open config from canonical source
- open config from explicit path
- create read-only snapshots
- create mutable edit sessions
- save/sync through shared semantics

Suggested methods:

```python
class ConfigRepository:
    def canonical_path(self) -> Path: ...
    def deploy_path(self) -> Path: ...
    def load_canonical(self) -> ConfigSnapshot: ...
    def load_path(self, path: Path) -> ConfigSnapshot: ...
    def begin_canonical_edit(self) -> ConfigEditSession: ...
    def begin_path_edit(self, path: Path) -> ConfigEditSession: ...
    def save(self, session: ConfigEditSession, target: str = "canonical") -> ConfigSaveResult: ...
    def sync(self, session: ConfigEditSession) -> ConfigSaveResult: ...
```

### 2. `ConfigSnapshot`

Purpose: provide a structured read-only view of config state.

Primary responsibilities:

- expose query APIs
- expose metadata about source/path/version/hash
- expose raw payload only through an explicit compatibility method

Suggested methods/properties:

```python
class ConfigSnapshot:
    @property
    def source_path(self) -> Path: ...
    @property
    def schema_version(self) -> int: ...
    @property
    def data_version(self) -> str: ...
    @property
    def data_hash(self) -> str: ...
    def profiles(self) -> ProfilesQueryApi: ...
    def devices(self) -> DevicesQueryApi: ...
    def groups(self) -> GroupsQueryApi: ...
    def dsl_tests(self) -> DslTestsQueryApi: ...
    def bridge(self) -> BridgeQueryApi: ...
    def to_payload(self) -> dict: ...  # compatibility only
```

### 3. `ConfigEditSession`

Purpose: provide the only allowed mutation surface for applications.

Primary responsibilities:

- own mutable working state
- track dirty state
- expose sub-APIs for safe edits
- validate before save

Suggested methods/properties:

```python
class ConfigEditSession:
    @property
    def source_path(self) -> Path: ...
    @property
    def dirty(self) -> bool: ...
    def profiles(self) -> ProfilesEditApi: ...
    def devices(self) -> DevicesEditApi: ...
    def groups(self) -> GroupsEditApi: ...
    def dsl_tests(self) -> DslTestsEditApi: ...
    def bridge(self) -> BridgeEditApi: ...
    def validate(self) -> ConfigValidationResult: ...
    def discard(self) -> None: ...
    def snapshot(self) -> ConfigSnapshot: ...
    def to_payload(self) -> dict: ...  # compatibility only
```

## Query APIs

Purpose: define the read-only operations applications should use.

### `ProfilesQueryApi`

Suggested methods:

```python
list_names() -> list[str]
default_profile() -> str | None
exists(profile_name: str) -> bool
get(profile_name: str) -> ProfileView | None
selectable_names(none_label: str = "(none)") -> list[str]
```

### `DevicesQueryApi`

Suggested methods:

```python
list_all() -> list[DeviceView]
by_label(label: str) -> DeviceView | None
labels_for_profile(profile_name: str) -> list[str]
devices_for_profile(profile_name: str) -> list[DeviceView]
```

### `DslTestsQueryApi`

Suggested methods:

```python
list_test_names(profile_name: str) -> list[str]
get_entry(test_name: str) -> DslTestEntryView | None
default_set() -> str | None
set_for_profile(profile_name: str) -> str | None
normalized_payload(test_name: str) -> dict | None
```

Important rule:

- the query API owns the precedence rules for profile test discovery
- surfaces may not reproduce those rules themselves

### `GroupsQueryApi`

Suggested methods:

```python
list_groups(profile_name: str) -> list[GroupView]
get_group(profile_name: str, group_name: str) -> GroupView | None
```

## Edit APIs

Purpose: define the allowed mutation operations.

### `ProfilesEditApi`

Suggested methods:

```python
set_default(profile_name: str) -> None
create(profile_name: str) -> None
rename(old_name: str, new_name: str) -> None
delete(profile_name: str) -> None
assign_devices(profile_name: str, device_labels: list[str]) -> None
set_dsl_test_set(profile_name: str, set_name: str | None) -> None
```

### `DevicesEditApi`

Suggested methods:

```python
add(device_payload: DeviceCreateRequest) -> None
update(label: str, changes: DeviceUpdateRequest) -> None
rename(label: str, new_label: str) -> None
delete(label: str) -> None
```

### `GroupsEditApi`

Suggested methods:

```python
create(profile_name: str, group_name: str) -> None
delete(profile_name: str, group_name: str) -> None
add_member(profile_name: str, group_name: str, device_label: str, enabled: bool = True) -> None
remove_member(profile_name: str, group_name: str, device_label: str) -> None
set_binding_list(profile_name: str, group_name: str, bindings: list[dict]) -> None
```

### `DslTestsEditApi`

Suggested methods:

```python
import_file(profile_name: str, test_name: str, source_path: Path, set_name: str | None = None) -> DslImportResult
validate_profile(profile_name: str) -> ConfigValidationResult
delete(test_name: str) -> None
cleanup_stale(profile_name: str) -> list[str]
set_default_set(set_name: str) -> None
assign_test_to_set(test_name: str, set_name: str) -> None
remove_test_from_set(test_name: str, set_name: str) -> None
```

## Validation API

Purpose: define how validation should work.

Validation must exist at two levels:

- targeted subsystem validation
- full config validation

Suggested methods:

```python
session.validate() -> ConfigValidationResult
session.dsl_tests().validate_profile(profile_name) -> ConfigValidationResult
repository.validate_snapshot(snapshot) -> ConfigValidationResult
```

Validation result must be structured, not text-only.

Suggested shape:

```python
class ConfigValidationResult:
    ok: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    area: str
```

Applications may format the result, but may not invent their own validation semantics.

## Save And Sync API

Purpose: define persistence semantics.

Saving must be explicit.

Recommended operations:

```python
repository.save(session, target="canonical")
repository.save(session, target="explicit", path=Path(...))
repository.sync(session)
```

Rules:

- `save(..., target="canonical")` writes only canonical unless policy says otherwise
- `sync(...)` applies canonical/deploy shared sync semantics
- stamping of schema/version/hash happens inside the repository
- surfaces must not stamp payloads themselves

## Dirty-State Model

Purpose: define how unsaved changes should be tracked.

Dirty state must be owned centrally.

Recommended model:

```python
class ConfigDirtyState:
    any_dirty: bool
    profiles_dirty: bool
    devices_dirty: bool
    groups_dirty: bool
    dsl_tests_dirty: bool
    metadata_dirty: bool
```

Suggested methods:

```python
session.dirty
session.dirty_state()
session.last_saved_hash()
session.last_loaded_hash()
```

UI and CLI should consume this state, not maintain parallel booleans as the source of truth.

## Raw Payload Compatibility

Purpose: allow migration without keeping raw access as the primary model.

The shared config API may expose:

- `snapshot.to_payload()`
- `session.to_payload()`

But these are compatibility escapes, not the primary application API.

Rules:

- new application code should not mutate the returned dict directly
- old code using raw dict access should be migrated behind typed or named edit/query calls

## Path And Source Model

Purpose: define how config sources should be represented.

Suggested source kinds:

- `canonical`
- `deploy`
- `explicit_path`
- `downloaded_robot_copy`
- `temporary_copy`

Suggested model:

```python
class ConfigSource:
    kind: str
    path: Path
    exists: bool
    writable: bool
```

Applications should not guess whether a file is canonical or deploy by comparing strings themselves.

## Application Usage Rules

Purpose: state how each host surface should use the API.

### CLI

The CLI may:

- load a snapshot
- open an edit session
- call query/edit APIs
- save or sync through the repository

The CLI may not:

- directly read or write `bringup_system.json`
- own its own dirty-state truth

### Bringup Control UI

The UI may:

- load snapshots for profile/test visibility
- open edit sessions for narrow host-local actions such as DSL import/validate
- call repository save/sync methods

The UI may not:

- mutate raw root payloads
- define profile/test precedence locally
- read or write `bringup_system.json` directly

### Topology Editor

The editor may:

- open an edit session
- perform device/profile/topology mutations through the edit APIs
- save via the repository

The editor may not:

- bypass the repository for direct writes
- directly read or write `bringup_system.json`

### Wizards And Helper Scripts

Wizards may:

- open an edit session
- apply structured mutations
- save/sync via the repository

They may not:

- open and rewrite `bringup_system.json` directly

## Migration Rules

Purpose: define how to migrate existing code toward the API.

Migration should happen in phases.

### Phase 1: ban new direct access

Immediately stop adding new direct `read_json` / `write_json` access to `bringup_system.json`.

This applies immediately to:

- CLI
- UI
- topology editor
- shared app-support modules used by those surfaces

Temporary exception:

- only small migration/repair utilities may continue using a compatibility adapter until migrated

### Phase 2: move read paths

Move all profile/test/device discovery into query APIs.

### Phase 3: move write paths

Move DSL import, profile edits, device edits, group edits, and editor writes into edit-session APIs.

### Phase 4: shrink compatibility escapes

Reduce raw-payload adapters after surfaces no longer depend on them.

### Phase 5: migrate the temporary utility exception set

Move the remaining small migration/repair utilities onto the shared config API as well.

Goal:

- no direct `bringup_system.json` access remains outside the shared config API package

Expected end state:

- utility scripts may still be separate programs
- but they must consume `ConfigRepository`, `ConfigSnapshot`, `ConfigEditSession`, or a narrow utility-facing adapter built on top of them
- they may not read or write `bringup_system.json` directly

Recommended order:

1. migrate read-only utilities first
2. migrate repair/cleanup utilities next
3. migrate schema/key migration utilities last if they need lower-level adapters during the transition

Temporary compatibility policy:

- compatibility adapters may continue to exist for a while
- but they must be owned by the shared config API package
- they must be treated as transitional, not permanent public interfaces

## Enforcement

Purpose: define how the rule should be checked.

Recommended enforcement:

- add a lint/check script that flags direct `read_json` / `write_json` usage against `bringup_system.json`
- add a check for direct use of `profiles_canonical_path()` and `profiles_deploy_path()` outside the shared config API package
- add tests that prove CLI and UI use the shared query/edit flows

Priority enforcement targets:

- `tools/can_nt/bridge_cli.py`
- `tools/can_nt/bringup_ui.py`
- `tools/can_topology/can_top_editor.py`
- shared modules that those applications depend on for config access

Secondary enforcement target:

- after the major apps are migrated, begin removing direct-access usage from the temporary migration/repair utility set

Suggested search-based guards:

- `read_json(` near `bringup_system.json`
- `write_json(` near `bringup_system.json`
- `profiles_canonical_path(` outside config API implementation
- `profiles_deploy_path(` outside config API implementation

## Suggested First Concrete API Cut

Purpose: define the smallest useful implementation slice.

First implementation milestone:

1. create `ConfigRepository`
2. create `ConfigSnapshot`
3. create `ConfigEditSession`
4. move current `ConfigLifecycleService` under the repository implementation
5. move current `LocalConfigQueryService` under the snapshot/query implementation
6. move current shared DSL service to depend on `ConfigEditSession` instead of free payload dict mutation

That first cut is enough to start enforcing:

- no direct path resolution
- no direct read/write
- no direct root-payload ownership in UI/CLI for common flows

## Utility Migration Plan

Purpose: define how the temporary utility exception should be retired.

The small utility scripts should not remain permanently outside the shared config API.

They should be migrated in this order:

### Step 1: classify the utility set

Split utilities into:

- read-only inspection utilities
- repair/cleanup utilities
- schema/key migration utilities

### Step 2: add utility-facing adapters on top of the shared API

If a utility needs a simpler entrypoint than a full edit session, add a thin shared adapter such as:

```python
load_config_snapshot(path: Path) -> ConfigSnapshot
begin_config_edit(path: Path) -> ConfigEditSession
save_config_edit(session: ConfigEditSession, target: str = "explicit") -> ConfigSaveResult
```

These adapters should still be implemented inside the shared config API package.

### Step 3: migrate read-only utilities first

Reason:

- lowest risk
- easiest to prove
- removes direct-read duplication early

### Step 4: migrate cleanup/repair utilities next

Reason:

- they usually mutate a narrow part of the config
- they benefit from shared save/stamp/validation semantics

### Step 5: migrate schema/key migration utilities last

Reason:

- these may need temporary lower-level compatibility hooks
- they can be the final consumers of compatibility adapters before those adapters are retired

### Step 6: remove the exception

Once all utility scripts use the shared config API:

- remove the temporary exception language
- keep only tests as the remaining in-memory-fixture allowance

## Non-Goals

Purpose: explicitly state what this spec is not trying to do.

This spec is not trying to:

- redesign the on-disk `bringup_system.json` schema
- migrate the robot-side Java loader to a new config format
- change persisted field names just because a shared API is being added
- combine this effort with a broad schema cleanup initiative

If any of those become necessary later, they should be handled as separate follow-on specs.

## Tradeoffs

Purpose: record the main costs of this design.

- The API is more structured than direct dict access, so some scripts will need refactoring.
- Migration will take time because the codebase already has many helpers and legacy paths.
- Compatibility adapters are necessary for a while, which means the system will not become perfectly strict immediately.

## Future Extensions

Purpose: describe likely next steps after the first implementation.

- add robot-config import/export adapters that consume `ConfigSnapshot` / `ConfigEditSession`
- add typed result objects for save, sync, and push preflight
- add a shared bindings API for `bringup_bindings.json`
- add a shared runtime-state-to-config comparison service
- add structured audit/history metadata for config edits

## Bottom Line

Purpose: provide one short summary to carry forward.

The correct design is to treat `bringup_system.json` as a repository-owned artifact, not a file that each application is free to read, mutate, and rewrite on its own. All host applications should go through one shared config API that owns path resolution, loading, query semantics, mutation semantics, dirty tracking, validation, and save/sync behavior.
