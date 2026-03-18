# DUT Command UI Review (Updated)

Date: 2026-03-18

## Summary
The UI path remains sound (Tk UI -> NT commands -> robot handler), and the protocol is now more robust with session handshakes, state heartbeat keys, and explicit timeout handling. The changes address the main failure modes: UI restart, stale/out-of-sequence commands, and loss of visibility into command lifecycle.

## Current Command Path (Updated)

PC side:
- `tools/can_nt/bringup_ui.py`
- `tools/can_nt/can_nt_bridge.py`

Robot side:
- `src/main/java/frc/robot/RobotV2.java`
- `src/main/java/frc/robot/ui/TcpUiServer.java`

## Protocol (Updated)

Commands use TCP (line-delimited JSON) on port 5809 by default.
Protocol monitor keys (optional) publish under `bringup/ui_tcp/...` when enabled.

Command payload (PC -> roboRIO):
- `type = "cmd"`
- `seq` (monotonic int)
- `name`
- `args` (object, optional)
- `ts`
- `clientId` (required; unique per UI instance)

Ack payload (roboRIO -> PC):
- `type = "ack"`
- `seq`
- `name`
- `status`
- `message`
- `ts`
- `sessionId`
- `state` (enabled/estopped/mode)

Out payload (roboRIO -> PC):
- `type = "out"`
- `seq`
- `name`
- `text`
- `ts`
- `json` (optional structured payload)
- `sessionId`
- `state` (enabled/estopped/mode)

State/heartbeat (still via NT):
- `bringup/ui/state/enabled`
- `bringup/ui/state/estopped`
- `bringup/ui/state/mode`
- `bringup/ui/state/lastAckMs`

## Handshake + Reset

New command:
- `cmd/name = uiHandshake`
- `cmd/args/json = {"clientId": "<uuid>", "reset": false}`

Robot response:
- `out/json = {"sessionId": "...", "lastAckSeq": N, "minNextSeq": N+1, "protocolVersion": 1}`

Reset behavior:
- UI can send `uiHandshake` with `reset: true` to resync when the UI restarts or a command stalls.
- Robot returns a new `sessionId` and the authoritative `minNextSeq` to use next.

## Single-Client Lock

- The roboRIO accepts commands only from the active `clientId`.
- To switch PCs, the active UI must send `uiDisconnect` or the robot must reboot.
- `uiDisconnect` releases the lock only for the active client.

## UI Reliability Behavior (Updated)

- Strict one-command-at-a-time gating remains.
- UI seeds the command sequence from `state/lastAckSeq` (and ack/out) on connect.
- UI enforces a tight timeout and retries the last command once after recovery.
- UI auto-handshakes on connect and after session changes.
- UI marks the robot state as stale if `state/lastAckMs` stops updating.

## What This Fixes

- UI restart no longer causes permanent "seq stuck" behavior.
- Operator has a clean reset path without rebooting the robot.
- Responses can be correlated to requests via `name/ts` and optional json.
- Session state is visible and debuggable through NT.

## Remaining Gaps (Optional Future Work)

- Add direct `selectProfileByName` command instead of only toggle.
- Add structured result payloads for richer UI display.
- Add device-scoped commands (`clearFaultsDevice`, `setOutputDevice`).
- Add `cmd/nonce` echo if tighter correlation is desired after reconnect.

## Bottom Line

The NT protocol is now robust enough for field use without a TCP transport. The handshake + heartbeat keys close the biggest reliability gaps (stale commands and UI restarts), while preserving the simplicity of NetworkTables.
