# Device FSM State Table (Superseded)

This note preserves the terminology and intent of the former root-level
`Device FSM state table.md`. The current contract is the Device Lifecycle FSM
in
`docs/FEATURE_SPEC_SCOPE_AWARE_RUNTIME_ACTIVATION_AND_INCREMENTAL_INSTANTIATION.md`.

## Preserved intent

The earlier table introduced a manual override for devices that did not pass
presence checks. Its central rules were:

- `present` remained evidence-backed; override did not fake presence.
- override opened a controlled instantiation attempt.
- override provenance stayed visible in states such as
  `override-instantiation-pending`, `instantiated-not-present-override`, and
  `instantiated-present-override`.
- testing was normally allowed only after instantiation and presence evidence.

## Superseded names

The earlier table used `discovered`, `discovered-stale`,
`defined-discovered`, and `in-scope-discovered`. The current FSM uses the more
explicit `unknown-present`, `unknown-stale`, `defined-stale`, and
`in-scope-stale` names and adds a latched `override-instantiation-failed`
state. Use the current FSM for implementation and operator behavior.
