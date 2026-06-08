#robotics #bringup 

Added a manual override to try to allow a device test even if it doesn't pass our existence testing

The key design rule is:

- `present` still means evidence-backed present
- override does **not** fake true presence
- override creates provisional states that allow instantiation and then controlled testing

## Revised Device State Table

| Current State | Event | Next State | Meaning |
|---|---|---|---|
| `unknown` | `define` | `defined` | Device exists in config |
| `unknown` | `discover` | `discovered` | Device seen on bus, but not defined |
| `discovered` | `define` | `defined-present` | Seen and now matched to config |
| `discovered` | `lost-presence` | `discovered-stale` | Was seen, not currently present |
| `discovered-stale` | `discover` | `discovered` | Seen again |
| `defined` | `discover` | `defined-present` | Configured device is currently present |
| `defined` | `enter-scope` | `in-scope` | Needed by active profile/test |
| `defined-present` | `lost-presence` | `defined-discovered` | Was seen before, not present now |
| `defined-present` | `enter-scope` | `in-scope-present` | Needed and currently present |
| `defined-discovered` | `discover` | `defined-present` | Present again |
| `defined-discovered` | `enter-scope` | `in-scope-discovered` | Needed, seen before, not currently present |
| `in-scope` | `discover` | `in-scope-present` | Needed and currently present |
| `in-scope` | `instantiate` | `instantiated-not-present` | Runtime object created, but device absent |
| `in-scope` | `manual-override-instantiate` | `override-instantiation-pending` | Operator explicitly authorizes instantiation attempt despite low score |
| `in-scope` | `exit-scope` | `defined` | No longer needed |
| `in-scope-present` | `lost-presence` | `in-scope-discovered` | Needed, but presence lost |
| `in-scope-present` | `instantiate` | `instantiated-present` | Runtime object created and working |
| `in-scope-present` | `exit-scope` | `defined-present` | No longer needed, still present |
| `in-scope-discovered` | `discover` | `in-scope-present` | Present again |
| `in-scope-discovered` | `instantiate` | `instantiated-not-present` | Runtime object created, but absent |
| `in-scope-discovered` | `manual-override-instantiate` | `override-instantiation-pending` | Operator explicitly authorizes instantiation attempt despite low score |
| `in-scope-discovered` | `exit-scope` | `defined-discovered` | No longer needed, still historically seen |
| `override-instantiation-pending` | `instantiate` | `instantiated-not-present-override` | Runtime object created under override, but no presence evidence yet |
| `override-instantiation-pending` | `discover` | `in-scope-present` | Presence recovered before instantiation completed |
| `override-instantiation-pending` | `instantiate-and-discover` | `instantiated-present-override` | Runtime object created under override and evidence now says device is present |
| `override-instantiation-pending` | `instantiate-failed` | `in-scope-discovered` | Override instantiation attempt failed |
| `override-instantiation-pending` | `manual-override-clear` | `in-scope-discovered` | Operator cancels override before instantiation succeeds |
| `override-instantiation-pending` | `exit-scope` | `defined-discovered` | No longer needed |
| `instantiated-present` | `lost-presence` | `instantiated-not-present` | Runtime object exists, device stopped responding |
| `instantiated-present` | `exit-scope` | `defined-present` | Runtime released, still present |
| `instantiated-not-present` | `discover` | `instantiated-present` | Device came back |
| `instantiated-not-present` | `exit-scope` | `defined-discovered` | Runtime released, still historically seen |
| `instantiated-not-present-override` | `discover` | `instantiated-present-override` | Device came back after override path |
| `instantiated-not-present-override` | `manual-override-clear` | `instantiated-not-present` | Remove override status; runtime object still exists but device not present |
| `instantiated-not-present-override` | `exit-scope` | `defined-discovered` | Runtime released, still historically seen |
| `instantiated-present-override` | `lost-presence` | `instantiated-not-present-override` | Runtime object exists, presence lost after override path |
| `instantiated-present-override` | `confidence-stable` | `instantiated-present` | Enough normal evidence accumulated; override no longer matters |
| `instantiated-present-override` | `exit-scope` | `defined-present` | Runtime released, still present |

## Revised State Meanings

| State                               | Meaning                                                                                     |
| ----------------------------------- | ------------------------------------------------------------------------------------------- |
| `unknown`                           | No config, no evidence                                                                      |
| `discovered`                        | Device currently seen, but not defined                                                      |
| `discovered-stale`                  | Unknown device was seen before, not present now                                             |
| `defined`                           | Defined in the config, config says it should exist, but never seen                          |
| `defined-present`                   | Defined and currently present                                                               |
| `defined-discovered`                | Defined, seen before, not present now                                                       |
| `in-scope`                          | Defined, needed now, never seen                                                             |
| `in-scope-present`                  | Defined, needed now, currently present                                                      |
| `in-scope-discovered`               | Defined, needed now, seen before, not present now                                           |
| `override-instantiation-pending`    | In scope, low-score or not present, but operator explicitly forced an instantiation attempt |
| `instantiated-present`              | Runtime object exists and device is present                                                 |
| `instantiated-not-present`          | Runtime object exists, but device is not present                                            |
| `instantiated-not-present-override` | Runtime object exists due to manual override, but device still lacks presence evidence      |
| `instantiated-present-override`     | Runtime object exists from override path and device is now evidence-backed present          |

## Events

| Event | Generated when |
|---|---|
| `define` | Config contains device |
| `discover` | Existence probability crosses the enter-present threshold upward |
| `lost-presence` | Existence probability crosses the exit-present threshold downward |
| `enter-scope` | Active profile/test requires this device |
| `exit-scope` | Active profile/test no longer requires this device |
| `instantiate` | Runtime wrapper/object is created |
| `instantiate-and-discover` | Instantiation succeeds and presence evidence is immediately available in the same bringup step |
| `instantiate-failed` | Runtime wrapper/object creation attempt fails |
| `manual-override-instantiate` | Operator explicitly forces a low-score device to be eligible for instantiation attempt |
| `manual-override-clear` | Operator clears the override state |
| `confidence-stable` | Sufficient normal evidence has accumulated so override provenance no longer matters |

## Operational Rules

- `manual-override-instantiate` is only valid from:
  - `in-scope`
  - `in-scope-discovered`
- Override never changes a device directly into a true `*-present` state.
- Override only opens the gate for instantiation attempt.
- Right-click/manual motor test should be allowed from:
  - `instantiated-present`
  - `instantiated-present-override`
- If you want a more aggressive last-resort mode, you could also allow testing from:
  - `instantiated-not-present-override`
  But that should be an explicit safety decision.

## Why this version is better

- It preserves the truth of `present`.
- It supports operator-forced bringup of weak-evidence devices.
- It keeps override visible in the state model.
- It gives you a clean path to normalize back to ordinary states once evidence improves.

The next useful step is to split this into:
- `Lifecycle FSM`
- `Usability FSM`

This table handles lifecycle and override well, but `usable / degraded / failed` should still be a second state machine layered on top.

