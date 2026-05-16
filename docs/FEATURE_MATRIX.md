# Feature Matrix

## Purpose

Provide a quick lookup table for which surface exposes which feature and what the feature depends on.

## Legend

- **UI**: Bringup Control UI
- **CLI**: Bridge CLI
- **Robot**: roboRIO runtime / bringup core
- **Topo**: topology editor
- **CAN Tool**: passive PC CAN tool
- **Yes / No / Partial**: availability or dependency

## Matrix

| Feature | UI | CLI | Robot | Topo | CAN Tool | Needs Robot | Needs CANable | Writes Config | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Select profile | Yes | Yes | Yes | Yes | Partial | Partial | No | Yes | UI/CLI can activate; editor loads/saves profile data |
| Toggle to next profile | Yes | Partial | Yes | No | No | Yes | No | No | UI `Toggle Profile`; runtime profile cycling |
| Add next motor | Yes | Yes | Yes | No | No | Yes | No | No | staged instantiation |
| Add all motors | Yes | Yes | Yes | No | No | Yes | No | No | bulk instantiation |
| Show status | Partial | Yes | Yes | No | No | Yes | No | No | UI has report button; CLI has direct command |
| Show devices | No | Yes | Yes | Partial | No | Partial | No | No | editor has node list, CLI has textual/JSON show |
| Run selected test | Yes | Yes | Yes | No | No | Yes | No | No | one test at a time |
| Run all enabled tests | Yes | Yes | Yes | No | No | Yes | No | No | scripted bulk test run |
| Toggle test enabled | Yes | Yes | Yes | No | No | Yes | No | No | affects run-all membership |
| DSL test execution | Partial | Partial | Yes | No | No | Yes | No | No | runtime consumes compiled `dslTests` |
| DSL test authoring | No | Yes | No | Partial | No | No | No | Yes | CLI authoring plus config edits |
| Group create/delete | Partial | Yes | Yes | Yes | No | Partial | No | Yes | profile-scoped groups |
| Group member enable/disable | No | Yes | Yes | Partial | No | Yes | No | Yes | key for staged joystick bringup |
| Group analog binding | No | Yes | Yes | No | No | Yes | No | Yes | live manual control path |
| Group hold/toggle/jog binding | No | Yes | Yes | No | No | Yes | No | Yes | button-style group control |
| Active-group operations | No | Yes | Yes | No | No | Yes | No | No | transient runtime-only |
| Selected-device mode | No | Yes | Yes | No | No | Yes | No | Yes | excludes one device from group output |
| Print state report | Yes | Partial | Yes | No | No | Yes | No | No | UI button plus CLI/status path |
| Print health report | Yes | No | Yes | No | No | Yes | No | No | local vendor API health |
| Print CAN bus report | Yes | No | Yes | No | No | Yes | No | No | robot-local CAN view |
| Print NT diagnostics | Yes | No | Yes | No | Yes | Partial | Yes | No | depends on CAN tool publishing |
| Print inputs report | Yes | No | Yes | No | No | Yes | No | No | controller state and bindings |
| Print bindings report | Yes | Yes | Yes | No | No | Partial | No | No | local/robot binding visibility |
| Print CANcoder report | Yes | No | Yes | No | No | Yes | No | No | encoder report surface |
| Dump full report | Yes | No | Yes | No | No | Yes | No | No | larger streamed report |
| Live topology display | Yes | No | Partial | Partial | No | No | No | No | shared renderer with editor base scene |
| Visibility table | Yes | No | Partial | No | Yes | Partial | Partial | No | source-based passive visibility |
| Live topology zoom/pan/fit | Yes | No | No | No | No | No | No | No | read-only camera controls |
| Show group overlays in live view | Yes | No | No | Yes | No | No | No | No | shared by profile groups |
| Topology node editing | No | No | No | Yes | No | No | No | Yes | device/layout authoring |
| Topology callouts | No | No | No | Yes | No | No | No | Yes | diagram annotation |
| CANnect/inject modeling | No | No | No | Yes | Partial | No | No | Yes | authored in editor, shown in live view |
| Connection filters | Partial | No | No | Yes | No | No | No | No | live and editor display filters |
| Group authoring from selection | No | No | No | Yes | No | No | No | Yes | writes `bridgeConfig` groups |
| Save canonical config | No | Yes | No | Yes | No | No | No | Yes | canonical root file |
| Sync deploy config | No | Partial | No | Partial | No | No | No | Yes | `validate_sync` and editor save flows |
| Config push to robot | No | Yes | Yes | No | No | Yes | No | No | in-memory robot apply over TCP |
| Passive CAN sniffing | No | No | No | No | Yes | No | Yes | No | read-only only |
| Publish NT diagnostics | Partial | No | Partial | No | Yes | Partial | Yes | No | consumed by robot/UI |
| PCAP capture | No | No | No | No | Yes | No | Yes | No | Wireshark-friendly capture |
| API inventory / diff | No | No | No | No | Yes | No | Yes | No | reverse-engineering support |
| Validate profiles | No | Partial | No | Partial | No | No | No | No | script plus save-time editor validation |
| Validate/sync full config | No | No | No | No | No | No | No | No | host tooling only |
| Topology regression suite | No | No | No | No | No | No | No | No | host regression bundle |
| Cross-surface regression suite | No | No | No | No | No | No | No | No | host regression bundle |

## Fast Answers

### If the goal is “make a motor move now”

Prefer:

- `add next`
- group bindings
- member enable / disable

Do not start with DSL tests unless the procedure must be scripted.

### If the goal is “run a repeatable checked procedure”

Prefer:

- selected DSL test
- run-all only after the individual cases are trusted

### If the goal is “edit the robot config”

Prefer:

- topology editor for devices/topology/groups
- CLI for text-oriented config and test authoring
- `python -m tools.validate_sync --warnings` before handoff or deploy

### If the goal is “see bus activity without commanding hardware”

Prefer:

- passive CAN tool
- NT diagnostics
- visibility view

## Maintenance Rule

When a feature is added, removed, or moved across surfaces, update this matrix in the same change.
