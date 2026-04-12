from __future__ import annotations

"""
NAME
    bridge_session.py - Shared TCP bridge session for GUI and CLI.

SYNOPSIS
    from tools.can_nt.bridge_session import BridgeSession

DESCRIPTION
    Centralizes TCP connect/send/receive, ACK/OUT parsing, and runtime state
    snapshots for the bridge UI and CLI front ends.
"""

import datetime
import json
import queue
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from tools.common.runtime_constants import THREAD_NAME_TCP_READER

@dataclass
class BridgeEvent:
    """
    NAME
        BridgeEvent - Parsed ACK/OUT event from the TCP bridge.

    DESCRIPTION
        Carries a parsed payload plus the raw data for callers that need it.
    """

    type: str
    seq: int
    name: str
    status: str
    message: str
    text: str
    json_text: str
    ts: float
    session_id: str
    state: Dict[str, Any]
    raw: Dict[str, Any]


TIMEZONE_ARG_ID = "timezoneId"
TIMEZONE_ARG_OFFSET_MIN = "timezoneOffsetMin"
SECONDS_PER_MINUTE = 60


def _local_timezone_args() -> Dict[str, Any]:
    """
    NAME
        _local_timezone_args - Build timezone args for uiHandshake.
    """
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    offset = now.utcoffset()
    offset_min = 0
    if offset is not None:
        offset_min = int(offset.total_seconds() / SECONDS_PER_MINUTE)
    tzinfo = now.tzinfo
    tz_id = ""
    if tzinfo is not None:
        tz_id = getattr(tzinfo, "key", "") or getattr(tzinfo, "zone", "") or ""
    args = {TIMEZONE_ARG_OFFSET_MIN: offset_min}
    if tz_id:
        args[TIMEZONE_ARG_ID] = tz_id
    return args


class TcpCommandClient:
    """
    NAME
        TcpCommandClient - Line-delimited JSON TCP client for UI commands.
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._sock: Optional[socket.socket] = None
        self._reader: Optional[threading.Thread] = None
        self._queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._connected = False
        self._lock = threading.Lock()

    def is_connected(self) -> bool:
        """
        NAME
            is_connected - Return whether the TCP socket is connected.
        """
        return self._connected

    def connect(self, timeout: float = 0.5) -> bool:
        """
        NAME
            connect - Attempt to connect to the TCP server.
        """
        if self._connected:
            return True
        try:
            sock = socket.create_connection((self._host, self._port), timeout=timeout)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(None)
            self._sock = sock
            self._connected = True
            self._reader = threading.Thread(
                target=self._read_loop,
                name=THREAD_NAME_TCP_READER,
                daemon=True,
            )
            self._reader.start()
            return True
        except Exception:
            self._connected = False
            self._sock = None
            return False

    def close(self) -> None:
        """
        NAME
            close - Close the TCP connection.
        """
        with self._lock:
            if self._sock is not None:
                try:
                    self._sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self._sock.close()
                except Exception:
                    pass
            self._sock = None
            self._connected = False

    def send(self, payload: Dict[str, Any]) -> bool:
        """
        NAME
            send - Send a JSON command payload to the server.
        """
        if not self._connected or self._sock is None:
            return False
        data = (json.dumps(payload) + "\n").encode("utf-8")
        with self._lock:
            try:
                self._sock.sendall(data)
                return True
            except Exception:
                self._connected = False
                return False

    def poll(self) -> List[Dict[str, Any]]:
        """
        NAME
            poll - Drain queued responses.
        """
        items: List[Dict[str, Any]] = []
        while True:
            try:
                items.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return items

    def _read_loop(self) -> None:
        """
        NAME
            _read_loop - Background reader for JSON lines.
        """
        sock = self._sock
        if sock is None:
            return
        try:
            with sock.makefile("r", encoding="utf-8") as reader:
                for line in reader:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                        if isinstance(payload, dict):
                            self._queue.put(payload)
                    except Exception:
                        continue
        except Exception:
            pass
        finally:
            self._connected = False
            with self._lock:
                if self._sock is sock:
                    try:
                        self._sock.close()
                    except Exception:
                        pass
                    self._sock = None


class BridgeSession:
    """
    NAME
        BridgeSession - Shared TCP session for bridge commands.

    DESCRIPTION
        Owns TCP connect/send/receive and maintains a merged runtime state
        snapshot from TCP responses and optional NT state.
    """

    def __init__(
        self,
        rio_host: str,
        tcp_port: int,
        nt_state_reader: Optional[callable] = None,
        auto_handshake: bool = True,
    ) -> None:
        self._rio_host = rio_host
        self._tcp_port = tcp_port
        self._tcp = TcpCommandClient(rio_host, tcp_port)
        self._client_id = str(uuid.uuid4())
        self._seq = 0
        self._handshake_done = False
        self._session_id = ""
        self._last_state: Dict[str, Any] = {}
        self._nt_state_reader = nt_state_reader
        self._last_connect_attempt = 0.0
        self._auto_handshake = auto_handshake

    def is_connected(self) -> bool:
        """
        NAME
            is_connected - Return TCP connection status.
        """
        return self._tcp.is_connected()

    def handshake_done(self) -> bool:
        """
        NAME
            handshake_done - Return whether uiHandshake completed.
        """
        return self._handshake_done

    def session_id(self) -> str:
        """
        NAME
            session_id - Return the current UI session ID.
        """
        return self._session_id

    def connect(self) -> bool:
        """
        NAME
            connect - Connect to the TCP UI server.
        """
        now = time.time()
        if not self._tcp.is_connected() and (now - self._last_connect_attempt) > 0.5:
            self._last_connect_attempt = now
            self._tcp.connect()
        return self._tcp.is_connected()

    def disconnect(self) -> None:
        """
        NAME
            disconnect - Close the TCP connection.
        """
        self._tcp.close()
        self.reset_handshake()

    def reset_handshake(self) -> None:
        """
        NAME
            reset_handshake - Clear the stored handshake state.
        """
        self._handshake_done = False
        self._session_id = ""

    def mark_handshake_done(
        self,
        session_id: Optional[str] = None,
        min_next_seq: Optional[int] = None,
    ) -> None:
        """
        NAME
            mark_handshake_done - Record a successful handshake.
        """
        self._handshake_done = True
        if session_id:
            self._session_id = session_id
        if isinstance(min_next_seq, int) and min_next_seq > 0:
            self._seq = max(self._seq, min_next_seq - 1)

    def set_client_id(self, client_id: str) -> None:
        """
        NAME
            set_client_id - Override the clientId used in commands.
        """
        cid = (client_id or "").strip()
        if cid:
            self._client_id = cid

    def ensure_handshake(self, reset: bool = False, timeout_sec: float = 1.5) -> bool:
        """
        NAME
            ensure_handshake - Send uiHandshake if required and wait for ACK/OUT.
        """
        if self._handshake_done and not reset:
            return True
        if not self.connect():
            return False
        seq = self._next_seq()
        args = {"reset": bool(reset)}
        args.update(_local_timezone_args())
        payload = {
            "type": "cmd",
            "seq": seq,
            "name": "uiHandshake",
            "args": args,
            "ts": time.time(),
            "clientId": self._client_id,
        }
        if not self._tcp.send(payload):
            return False
        deadline = time.time() + timeout_sec
        seen_ack = False
        while time.time() < deadline:
            for event in self._drain_events():
                if event.seq != seq:
                    continue
                if event.type == "ack":
                    seen_ack = True
                if event.type == "out":
                    self._handshake_done = True
                    self._session_id = event.session_id or self._session_id
                    payload_json = _parse_json_text(event.json_text)
                    min_next = None
                    if isinstance(payload_json, dict):
                        min_next = payload_json.get("minNextSeq")
                    if isinstance(min_next, int) and min_next > 0:
                        self._seq = max(self._seq, min_next - 1)
                    return True
            if seen_ack:
                time.sleep(0.01)
            else:
                time.sleep(0.02)
        return False

    def send_command(self, name: str, args: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        NAME
            send_command - Send a command after ensuring handshake.
        """
        cmd_name = str(name)
        if self._auto_handshake and cmd_name not in ("uiHandshake", "uiDisconnect"):
            if not self.ensure_handshake():
                return None
        seq = self._next_seq()
        payload = {
            "type": "cmd",
            "seq": seq,
            "name": cmd_name,
            "args": args or {},
            "ts": time.time(),
            "clientId": self._client_id,
        }
        if not self._tcp.send(payload):
            return None
        return seq

    def poll_events(self) -> List[BridgeEvent]:
        """
        NAME
            poll_events - Drain and parse inbound TCP events.
        """
        return self._drain_events()

    def get_state_snapshot(self) -> Dict[str, Any]:
        """
        NAME
            get_state_snapshot - Return merged TCP + NT state.
        """
        state = dict(self._last_state or {})
        if self._nt_state_reader is not None:
            try:
                nt_state = self._nt_state_reader()
                if isinstance(nt_state, dict):
                    state.update(nt_state)
            except Exception:
                pass
        return state

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _drain_events(self) -> List[BridgeEvent]:
        events: List[BridgeEvent] = []
        for payload in self._tcp.poll():
            event = _parse_event(payload)
            if event is None:
                continue
            if event.state:
                self._last_state = dict(event.state)
            events.append(event)
        return events


def _parse_json_text(text: str) -> Optional[Any]:
    """
    NAME
        _parse_json_text - Parse a JSON string to Python objects.
    """
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _parse_event(payload: Dict[str, Any]) -> Optional[BridgeEvent]:
    """
    NAME
        _parse_event - Convert a raw payload into a BridgeEvent.
    """
    etype = str(payload.get("type", "")).lower()
    if etype not in ("ack", "out"):
        return None
    seq = int(payload.get("seq", -1))
    name = str(payload.get("name", ""))
    status = str(payload.get("status", ""))
    message = str(payload.get("message", ""))
    text = str(payload.get("text", ""))
    json_text = str(payload.get("json", ""))
    ts = float(payload.get("ts", 0.0))
    session_id = str(payload.get("sessionId", ""))
    state = payload.get("state")
    state_dict = state if isinstance(state, dict) else {}
    return BridgeEvent(
        type=etype,
        seq=seq,
        name=name,
        status=status,
        message=message,
        text=text,
        json_text=json_text,
        ts=ts,
        session_id=session_id,
        state=state_dict,
        raw=payload,
    )
