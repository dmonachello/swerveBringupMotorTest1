# Restoration Summary

- Topic: activation hardening, stabilization planning, and CTRE passive identity decode investigation.
- Hard limit: this bundle cannot restore hidden server-side chat state; it only preserves visible local context, repo state, git state, and this written summary.
- Current state:
  - Repo is on `main` at `33165d3` with local uncommitted work.
  - Added status review doc: `docs/STATUS_REVIEW_2026-08-03.md`.
  - Added activation hardening plan: `docs/TEST_PLAN_ACTIVATION_HARDENING_2026-08-03.md`.
  - Added 12 targeted activation regression tests in `tools/can_nt/tests/test_bringup_ui_actions.py`.
  - The 12 new activation tests pass when run directly.
  - The full `test_bringup_ui_actions` suite still has pre-existing failures in the current workspace.
  - Hermes path drift caused `ui.bat` to launch the wrong Python; user PATH was corrected so `python` now resolves to Python 3.13 again.
  - Passive CAN / CTRE investigation found a real tool bug in profile dump identity collection.
- CTRE decode finding:
  - `can_nt_bridge.py` collects `seen_can_keys` from raw `_decode_device_key(arb_id)` instead of normalized passive identities.
  - This bypasses CTRE passive normalization in `tools/passive_discovery_poc/metadata.py`.
  - Likely effects observed:
    - CANcoder passive raw type `5` should normalize to canonical type `7` but is dumped as `Unknown 4-5-18`.
    - Pigeon passive raw type `21` should normalize to canonical type `4` but is dumped as `Unknown 4-21-19`.
    - Broadcast/control-like CTRE traffic such as `Unknown 4-0-63` is being incorrectly treated as a device.
- Real hardware truth gathered during thread:
  - User confirmed one extra undefined REV Spark MAX / NEO at CAN ID 7.
  - Phoenix Tuner X reported CTRE devices on rio bus:
    - Talon FX ID 9
    - CANcoder ID 18
    - PDP ID 20
    - Pigeon 2 ID 19
  - Generated sniffer profile should not be copied directly into real config because CTRE identities are polluted by the decode bug.
- Unresolved questions:
  - Whether to patch `ui.bat` to use `py` for future interpreter stability.
  - Whether to implement the CTRE dump normalization fix immediately or park it for the stabilization phase.
  - Which workflow should be declared as the single blessed supported bringup path before pause.
- Safest next steps:
  1. Commit or checkpoint the current untracked docs and test additions if they should be preserved in git.
  2. Implement the CTRE identity fix in `tools/can_nt/can_nt_bridge.py` by using normalized frame identities and filtering non-device CTRE control/broadcast traffic.
  3. Add regression tests for CTRE CANcoder/Pigeon passive normalization and fake identity suppression.
  4. Keep real robot profile edits grounded in Phoenix/manual truth until the passive dump fix is verified.
  5. Continue stabilization-only work; avoid adding broad new features.
