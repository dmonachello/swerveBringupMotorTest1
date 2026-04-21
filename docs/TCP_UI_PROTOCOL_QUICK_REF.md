# TCP UI Protocol Quick Reference

Purpose: Provide a copy/paste operator guide for the TCP JSON line protocol used by CLI/GUI.

## Defaults

Purpose: Capture the common connection and framing defaults.

- Host: roboRIO address (example `172.22.11.2`).
- Port: `5809` unless overridden by robot config.
- Encoding: UTF-8.
- Framing: one JSON object per line, newline-delimited (`\n`).
- Response pattern: usually two lines per command (`ack`, then `out`).

## Minimal Envelope Shapes

Purpose: Show the exact fields expected on the wire.

Command (`cmd`):

```json
{"type":"cmd","seq":1,"name":"uiHandshake","args":{"reset":false},"ts":1713555000.123,"clientId":"cli-abc"}
```

Ack (`ack`):

```json
{"type":"ack","seq":1,"name":"uiHandshake","status":"ok","message":"UI handshake OK.","ts":1713555000.123,"sessionId":"...","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
```

Output (`out`):

```json
{"type":"out","seq":1,"name":"uiHandshake","text":"OK","ts":1713555000.123,"sessionId":"...","json":"{\"sessionId\":\"...\",\"minNextSeq\":1,\"protocolVersion\":1}","state":{"enabled":false,"estopped":false,"mode":"disabled"}}
```

## Required Flow

Purpose: Keep command order valid for lock/session behavior.

1. Connect TCP.
2. Send `uiHandshake` with non-empty `clientId`.
3. Read `ack` and `out`.
4. Send regular commands (for example `showStatus`, `showGroups`).
5. When done, send `uiDisconnect` to release lock.

## Copy/Paste Exchanges

Purpose: Provide direct test payloads for manual probing.

Handshake:

```text
{"type":"cmd","seq":1,"name":"uiHandshake","args":{"reset":false},"ts":1713555000.123,"clientId":"cli-abc"}
```

Status query:

```text
{"type":"cmd","seq":2,"name":"showStatus","args":{},"ts":1713555001.123,"clientId":"cli-abc"}
```

Lock release:

```text
{"type":"cmd","seq":3,"name":"uiDisconnect","args":{},"ts":1713555002.123,"clientId":"cli-abc"}
```

## Netcat / Ncat Examples

Purpose: Enable fast manual interaction from terminals.

Windows with Ncat (`nmap` package):

```powershell
ncat 172.22.11.2 5809
```

Linux/macOS with `nc`:

```bash
nc 172.22.11.2 5809
```

After connecting, paste one JSON line at a time from the previous section and press Enter.

## Python Probe Script (Copy/Paste)

Purpose: Provide a minimal reproducible client for handshake + one command + disconnect.

```python
import json
import socket
import time

HOST = "172.22.11.2"
PORT = 5809
CLIENT_ID = "cli-quickref"


def send_cmd(sock, seq, name, args):
    payload = {
        "type": "cmd",
        "seq": seq,
        "name": name,
        "args": args,
        "ts": time.time(),
        "clientId": CLIENT_ID,
    }
    wire = json.dumps(payload) + "\n"
    sock.sendall(wire.encode("utf-8"))
    ack = sock_file.readline().strip()
    out = sock_file.readline().strip()
    print("ACK", ack)
    print("OUT", out)


with socket.create_connection((HOST, PORT), timeout=2.0) as sock:
    sock_file = sock.makefile("r", encoding="utf-8")
    send_cmd(sock, 1, "uiHandshake", {"reset": False})
    send_cmd(sock, 2, "showStatus", {})
    send_cmd(sock, 3, "uiDisconnect", {})
```

## Common Errors

Purpose: Speed up diagnosis of first-connection issues.

- `Missing clientId.`: include non-empty `clientId` in every command.
- `UI handshake required before commands.`: send `uiHandshake` first.
- `UI locked by another client...`: another `clientId` currently owns the lock.
- `Robot disabled.` / `Robot disabled (E-Stop).`: command blocked by DS state.
- `{"type":"error","message":"Malformed command"}`: invalid JSON line or truncated payload.

## Reference

Purpose: Point to the complete specification and implementation anchors.

- Full spec: `docs/TCP_UI_PROTOCOL.md`.
- CLI mapping: `docs/BRIDGE_CLI_DESIGN.md`.
- Server implementation: `src/main/java/frc/robot/ui/TcpUiServer.java`.
- Command handler implementation: `src/main/java/frc/robot/BridgeUiCommandHandler.java`.
