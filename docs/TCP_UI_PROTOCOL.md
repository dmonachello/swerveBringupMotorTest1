# TCP UI Protocol (CLI/GUI Middle Layer)

Purpose: Define the exact message layer between the TCP stream and CLI command text.

## Scope

Purpose: State what this document covers and what it does not.

- Covers the robot TCP UI command channel used by both GUI and CLI.
- Covers framing, request/response schemas, state and session rules, and error behavior.
- Covers real exchange transcripts based on the current implementation.
- Does not redefine CLI grammar; CLI text-to-command mapping remains in `docs/BRIDGE_CLI_DESIGN.md`.
- For copy/paste operational examples, see `docs/TCP_UI_PROTOCOL_QUICK_REF.md`.
## Layer Model


Purpose: Clarify the stack from bytes on the socket to operator commands.

- Bottom layer: plain TCP byte stream.
- Middle layer: UTF-8, line-delimited JSON messages (one JSON object per line).
- Top layer: CLI text commands mapped to robot command names and argument objects.

## Wire Framing

Purpose: Define message boundaries and parse behavior on both ends.

- Client send framing: JSON payload plus trailing newline (`\n`).
- Server receive framing: `readLine()` per inbound command line.
- Server send framing: each ACK and OUT is emitted as its own line.
- Empty lines are ignored.
- A malformed inbound JSON line yields a single error line:
  - `{"type":"error","message":"Malformed command"}`

Implementation anchors:

- Server framing/parsing: `src/main/java/frc/robot/ui/TcpUiServer.java`.
- Client framing/parsing: `tools/can_nt/bridge_session.py`.

## Message Types

Purpose: Define the JSON envelope types used on this channel.

- `cmd`: client-to-robot command envelope.
- `ack`: robot-to-client acknowledgement envelope.
- `out`: robot-to-client command output envelope.
- `error`: transport/parser error envelope from `TcpUiServer` (malformed line, etc.).

Notes:

- The robot parser does not require a `type` field in inbound requests; it reads `seq`, `name`, `args`, `ts`, `clientId`.
- The Python `BridgeSession` currently parses and returns only `ack` and `out` events.

## Request Schema (`cmd`)

Purpose: Document accepted inbound fields and defaults.

Inbound request object fields as parsed by `TcpUiServer.parseCommand`:

- `seq` (number, optional): sequence number, default `-1` when missing.
- `name` (string, optional): robot command name, default empty string.
- `args` (object, optional): command args object, serialized and forwarded as JSON text.
- `ts` (number, optional): caller timestamp, default `0.0`.
- `clientId` (string, optional): logical client identity for lock and dedupe.

Canonical request shape used by shared client:

```json
{"type":"cmd","seq":12,"name":"showStatus","args":{},"ts":1713555001.2,"clientId":"cli-abc"}
```

## Response Schema (`ack` / `out`)

Purpose: Define stable response fields returned for each accepted command.

ACK fields:

- `type`: always `"ack"`.
- `seq`: echoes request sequence.
- `name`: echoes request command name.
- `status`: `"ok"` or `"error"`.
- `message`: short status/error text.
- `ts`: echoes request timestamp.
- `sessionId`: current UI session id.
- `state`: object with robot mode snapshot:
  - `enabled` (boolean)
  - `estopped` (boolean)
  - `mode` (`"auto" | "teleop" | "test" | "disabled"`)

OUT fields:

- `type`: always `"out"`.
- `seq`: echoes request sequence.
- `name`: echoes request command name.
- `text`: human-readable command output.
- `ts`: echoes request timestamp.
- `sessionId`: current UI session id.
- `json` (optional string): command-specific JSON payload encoded as a JSON string.
- `state`: same object schema as ACK.

Important detail:

- `out.json` is a JSON-encoded string field, not a nested object. Clients that need structure must parse it.

## Session, Lock, and Handshake Contract

Purpose: Define required ordering and ownership semantics for clients.

- `uiHandshake` is required before most commands.
- `uiHandshake`, `uiDisconnect`, and `uiPing` are allowed without prior handshake.
- A non-empty `clientId` is required; otherwise command fails with `Missing clientId.`.
- Lock ownership is single-client by `clientId`.
- If another client holds lock, command fails with:
  - `UI locked by another client. Disconnect or reboot to switch.`
- `uiDisconnect` by lock owner releases the lock.

Handshake OUT `json` payload fields:

- `sessionId` (string)
- `lastAckSeq` (number)
- `minNextSeq` (number)
- `protocolVersion` (number, currently `1`)

## Sequencing and Duplicate Handling

Purpose: Describe server behavior when requests are retransmitted.

- Duplicate handling is per `clientId`.
- If a command arrives with `seq <=` last seen seq for that client:
  - If same as cached last response seq, server returns cached ACK/OUT.
  - Otherwise duplicate is dropped.
- Handshake response may include `minNextSeq` so clients can jump ahead safely.

## Disabled and Safety Gating

Purpose: Clarify command acceptance under disabled/E-Stop and stop-latch conditions.

- If robot is disabled and command is not allow-listed, command fails with:
  - `Robot disabled.` or `Robot disabled (E-Stop).`
- If stop latch is active and command is a start/enabling command, command fails with:
  - `Stop latch active ... Clear from Xbox or UI to resume.`
- A substantial read/config subset is allowed while disabled (for example `showStatus`, group config commands, profile activate/reload/apply, `uiPollLog`, `uiPing`).

## Actual Exchange Transcripts

Purpose: Provide realistic on-wire examples matching current robot/client behavior.

### 1) Successful handshake

```text
C->R {"type":"cmd","seq":1,"name":"uiHandshake","args":{"reset":false},"ts":1713555000.123,"clientId":"cli-abc"}

R->C {"type":"ack","seq":1,"name":"uiHandshake","status":"ok","message":"UI handshake OK.","ts":1713555000.123,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
R->C {"type":"out","seq":1,"name":"uiHandshake","text":"OK","ts":1713555000.123,"sessionId":"9d6f...","json":"{\"sessionId\":\"9d6f...\",\"lastAckSeq\":0,\"minNextSeq\":1,\"protocolVersion\":1}","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
```

### 2) Normal command after handshake

```text
C->R {"type":"cmd","seq":2,"name":"showStatus","args":{},"ts":1713555001.200,"clientId":"cli-abc"}

R->C {"type":"ack","seq":2,"name":"showStatus","status":"ok","message":"OK","ts":1713555001.200,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
R->C {"type":"out","seq":2,"name":"showStatus","text":"...status text...","ts":1713555001.200,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
```

### 3) Missing `clientId`

```text
C->R {"type":"cmd","seq":3,"name":"showGroups","args":{},"ts":1713555002.000}

R->C {"type":"ack","seq":3,"name":"showGroups","status":"error","message":"Missing clientId.","ts":1713555002.000,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
R->C {"type":"out","seq":3,"name":"showGroups","text":"Missing clientId.","ts":1713555002.000,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
```

### 4) Handshake required

```text
C->R {"type":"cmd","seq":4,"name":"addMotor","args":{},"ts":1713555003.000,"clientId":"cli-abc"}

R->C {"type":"ack","seq":4,"name":"addMotor","status":"error","message":"UI handshake required before commands.","ts":1713555003.000,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
R->C {"type":"out","seq":4,"name":"addMotor","text":"UI handshake required before commands.","ts":1713555003.000,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
```

### 5) Lock conflict

```text
C2->R {"type":"cmd","seq":1,"name":"showStatus","args":{},"ts":1713555004.000,"clientId":"cli-other"}

R->C2 {"type":"ack","seq":1,"name":"showStatus","status":"error","message":"UI locked by another client. Disconnect or reboot to switch.","ts":1713555004.000,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
R->C2 {"type":"out","seq":1,"name":"showStatus","text":"UI locked by another client. Disconnect or reboot to switch.","ts":1713555004.000,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
```

### 6) Malformed JSON line

```text
C->R {"type":"cmd","seq":5,"name":"showStatus"   <- truncated line

R->C {"type":"error","message":"Malformed command"}
```

### 7) Lock release

```text
C->R {"type":"cmd","seq":6,"name":"uiDisconnect","args":{},"ts":1713555005.000,"clientId":"cli-abc"}

R->C {"type":"ack","seq":6,"name":"uiDisconnect","status":"ok","message":"UI lock released.","ts":1713555005.000,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
R->C {"type":"out","seq":6,"name":"uiDisconnect","text":"OK","ts":1713555005.000,"sessionId":"9d6f...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
```

## CLI Mapping Note

Purpose: Link top-layer CLI text to middle-layer command names.

- CLI command text is parsed locally, then mapped to `cmd.name` + `cmd.args`.
- Mapping examples are defined in `docs/BRIDGE_CLI_DESIGN.md` under "Command Mapping (Robot TCP)".

## Tradeoffs

Purpose: Record protocol design tradeoffs relevant to operations and tooling.

- Line-delimited JSON is easy to debug and script, but carries no binary framing checksums.
- `out.json` as a string preserves backward compatibility, but requires second-stage parse.
- Dual `ack` + `out` lines keep command lifecycle explicit, but double message count.
- `clientId` lock ownership is simple and robust, but prevents concurrent control clients.

## Future Extensions

Purpose: List additive-compatible protocol improvements.

- Add explicit `protocolVersion` field to ACK/OUT top-level envelope.
- Add structured transport error schema beyond `{"type":"error","message":...}`.
- Add optional capability discovery command for supported command names/args.
- Add optional keepalive timeout advisory in handshake JSON payload.

## Normative References

Purpose: Point to implementation and design sources that define current behavior.

- `src/main/java/frc/robot/ui/TcpUiServer.java`
- `src/main/java/frc/robot/BridgeUiCommandHandler.java`
- `tools/can_nt/bridge_session.py`
- `docs/BRIDGE_CLI_DESIGN.md`
- `docs/BRIDGE_CLI_FULL_SPEC.md`
