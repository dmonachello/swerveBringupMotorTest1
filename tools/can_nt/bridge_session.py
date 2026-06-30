from __future__ import annotations

"""
NAME
    bridge_session.py - Shared REST bridge session for GUI and CLI.

SYNOPSIS
    from tools.can_nt.bridge_session import BridgeSession

DESCRIPTION
    Centralizes REST session connect/send/poll behavior and exposes a
    compatibility event stream so existing CLI/UI code can share one command
    transport layer without reimplementing command lifecycle handling in each
    surface.
"""

import datetime
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional


@dataclass
class BridgeEvent:
    """
    NAME
        BridgeEvent - Parsed ACK/OUT event from the bridge transport.

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
HANDSHAKE_TIMEOUT_SEC_DEFAULT = 3.5
TRACE_CMD_UI_PING = "uiPing"
TRACE_CMD_UI_POLL_LOG = "uiPollLog"
HTTP_METHOD_GET = "GET"
HTTP_METHOD_POST = "POST"
HTTP_CONTENT_TYPE = "application/json"
HTTP_HEADER_CONTENT_TYPE = "Content-Type"
HTTP_HEADER_ACCEPT = "Accept"
HTTP_ACCEPT_JSON = "application/json"
REST_PATH_HEALTH = "/health"
REST_PATH_SESSION = "/session"
REST_PATH_SESSION_CONNECT = "/session/connect"
REST_PATH_SESSION_DISCONNECT = "/session/disconnect"
REST_PATH_SESSION_RESET = "/session/reset"
REST_PATH_SESSION_PING = "/session/ping"
REST_PATH_COMMANDS = "/commands"
REST_PATH_LOGS = "/logs"
REST_PATH_MONITOR_ENABLE = "/monitor/enable"
REST_PATH_MONITOR_DISABLE = "/monitor/disable"
REST_PATH_PROTOCOL_MONITOR = "/ui/protocol-monitor"
REST_PATH_RUNTIME_STATE = "/runtime/state"
REST_PATH_TESTS_STATE = "/tests/state"
REST_PATH_CONFIG_CURRENT = "/config/current"
REST_QUERY_AFTER = "after"
REST_QUERY_CLIENT_ID = "clientId"
REST_JSON_CLIENT_ID = "clientId"
REST_JSON_REQUEST_ID = "requestId"
REST_JSON_NAME = "name"
REST_JSON_ARGS = "args"
REST_JSON_COMMAND_ID = "commandId"
REST_JSON_STATUS = "status"
REST_JSON_MESSAGE = "message"
REST_JSON_SESSION_ID = "sessionId"
REST_JSON_NEXT_SEQUENCE = "nextSequence"
REST_JSON_CHUNKS = "chunks"
REST_JSON_TEXT = "text"
REST_JSON_LOGS = "logs"
REST_JSON_SEQUENCE = "sequence"
REST_JSON_CONNECTED = "connected"
REST_STATUS_FINISHED = "FINISHED"
REST_STATUS_FAILED = "FAILED"
REST_STATUS_STOPPED = "STOPPED"
REST_STATUS_REJECTED = "REJECTED"
REST_STATUS_UNKNOWN = "UNKNOWN"
REST_STATUS_RUNNING = "RUNNING"
REST_STATUS_ACCEPTED = "ACCEPTED"
EVENT_TYPE_ACK = "ack"
EVENT_TYPE_OUT = "out"
EVENT_STATUS_OK = "ok"
EVENT_STATUS_ERROR = "error"
COMMAND_UI_HANDSHAKE = "uiHandshake"
COMMAND_UI_DISCONNECT = "uiDisconnect"
COMMAND_UI_PING = "uiPing"
COMMAND_UI_POLL_LOG = "uiPollLog"
COMMAND_UI_MONITOR_ENABLE = "uiMonitorEnable"
COMMAND_UI_MONITOR_DISABLE = "uiMonitorDisable"
COMMAND_STOP = "stopCommand"
SESSION_COMMANDS = {
    COMMAND_UI_HANDSHAKE,
    COMMAND_UI_DISCONNECT,
    COMMAND_UI_PING,
    COMMAND_UI_POLL_LOG,
    COMMAND_UI_MONITOR_ENABLE,
    COMMAND_UI_MONITOR_DISABLE,
}
REST_PORT_DEFAULT = 5805
REST_TIMEOUT_CONNECT_SEC = 0.5
REST_TIMEOUT_COMMAND_SEC = 3.5
LOG_TIMEOUT_SEC = 2.0
EMPTY_STRING = ""
VALUE_ZERO = 0
VALUE_ONE = 1
JSON_INDENT_NONE = None
TRACE_PREFIX_SEND = "REST SEND "
TRACE_PREFIX_RECV = "REST RECV "
TRACE_PREFIX_FAIL = "REST FAIL "
MESSAGE_CONNECT_FAILED = "REST connect failed."
MESSAGE_HANDSHAKE_FAILED = "REST session connect failed."
MESSAGE_OWNER_REQUIRED = "Owning control client required."
MESSAGE_METHOD_NOT_ALLOWED = "Method not allowed."


def _local_timezone_args() -> Dict[str, Any]:
    """
    NAME
        _local_timezone_args - Build timezone args for session connect metadata.
    """
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    offset = now.utcoffset()
    offset_min = VALUE_ZERO
    if offset is not None:
        offset_min = int(offset.total_seconds() / SECONDS_PER_MINUTE)
    tzinfo = now.tzinfo
    tz_id = EMPTY_STRING
    if tzinfo is not None:
        tz_id = getattr(tzinfo, "key", EMPTY_STRING) or getattr(tzinfo, "zone", EMPTY_STRING) or EMPTY_STRING
    args = {TIMEZONE_ARG_OFFSET_MIN: offset_min}
    if tz_id:
        args[TIMEZONE_ARG_ID] = tz_id
    return args


def _trace_should_log_name(name: str) -> bool:
    """
    NAME
        _trace_should_log_name - Suppress noisy keepalive command names from raw traces.
    """
    value = (name or EMPTY_STRING).strip()
    return value not in (TRACE_CMD_UI_PING, TRACE_CMD_UI_POLL_LOG)


class RestHttpClient:
    """
    NAME
        RestHttpClient - Minimal JSON HTTP client for robot REST endpoints.
    """

    def __init__(self, host: str, port: int) -> None:
        self._base_url = f"http://{host}:{port}"
        self._trace_logger: Optional[callable] = None

    def set_trace_logger(self, logger: Optional[callable]) -> None:
        self._trace_logger = logger

    def _trace(self, message: str) -> None:
        logger = self._trace_logger
        if not callable(logger):
            return
        try:
            logger(message)
        except Exception:
            return

    def request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = REST_TIMEOUT_COMMAND_SEC,
        query: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = self._base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data: Optional[bytes] = None
        if payload is not None:
            body = json.dumps(payload)
            data = body.encode("utf-8")
            self._trace(TRACE_PREFIX_SEND + method + " " + url + " " + body)
        else:
            self._trace(TRACE_PREFIX_SEND + method + " " + url)
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header(HTTP_HEADER_ACCEPT, HTTP_ACCEPT_JSON)
        if payload is not None:
            request.add_header(HTTP_HEADER_CONTENT_TYPE, HTTP_CONTENT_TYPE)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8")
                self._trace(TRACE_PREFIX_RECV + str(response.status) + " " + text)
                parsed = json.loads(text) if text else {}
                if not isinstance(parsed, dict):
                    parsed = {}
                parsed["_http_status"] = int(response.status)
                return parsed
        except urllib.error.HTTPError as ex:
            text = ex.read().decode("utf-8")
            self._trace(TRACE_PREFIX_FAIL + str(ex.code) + " " + text)
            try:
                parsed = json.loads(text) if text else {}
            except Exception:
                parsed = {}
            if not isinstance(parsed, dict):
                parsed = {}
            parsed["_http_status"] = int(ex.code)
            return parsed
        except Exception as ex:
            self._trace(TRACE_PREFIX_FAIL + repr(ex))
            return {"_http_status": VALUE_ZERO, REST_JSON_MESSAGE: str(ex), "ok": False}


@dataclass
class PendingCommand:
    """
    NAME
        PendingCommand - In-flight REST command awaiting terminal output.
    """

    seq: int
    name: str
    command_id: int


class BridgeSession:
    """
    NAME
        BridgeSession - Shared REST session for bridge commands.

    DESCRIPTION
        Owns robot REST session establishment, command submission, command
        status/output polling, and a compatibility ACK/OUT event stream used by
        existing CLI/UI callers.
    """

    def __init__(
        self,
        rio_host: str,
        rest_port: int,
        auto_handshake: bool = True,
    ) -> None:
        self._rio_host = rio_host
        self._rest_port = int(rest_port) if int(rest_port) > VALUE_ZERO else REST_PORT_DEFAULT
        self._http = RestHttpClient(rio_host, self._rest_port)
        self._client_id = str(uuid.uuid4())
        self._seq = VALUE_ZERO
        self._handshake_done = False
        self._last_handshake_error = EMPTY_STRING
        self._session_id = EMPTY_STRING
        self._last_state: Dict[str, Any] = {}
        self._auto_handshake = auto_handshake
        self._connected = False
        self._event_queue: Deque[BridgeEvent] = deque()
        self._last_log_sequence = VALUE_ZERO
        self._pending_by_seq: Dict[int, PendingCommand] = {}
        self._last_runtime_state: Dict[str, Any] = {}
        self._last_tests_state: Dict[str, Any] = {}
        self._last_protocol_monitor: Dict[str, Any] = {}

    def is_connected(self) -> bool:
        """
        NAME
            is_connected - Return REST server reachability status.
        """
        return self._connected

    def handshake_done(self) -> bool:
        return self._handshake_done

    def last_handshake_error(self) -> str:
        return self._last_handshake_error

    def session_id(self) -> str:
        return self._session_id

    def set_trace_logger(self, logger: Optional[callable]) -> None:
        self._http.set_trace_logger(logger)

    def connect(self) -> bool:
        """
        NAME
            connect - Probe REST health endpoint.
        """
        response = self._http.request(HTTP_METHOD_GET, REST_PATH_HEALTH, timeout=REST_TIMEOUT_CONNECT_SEC)
        self._connected = response.get("_http_status") == 200
        return self._connected

    def disconnect(self) -> None:
        """
        NAME
            disconnect - Release the REST control session if owned.
        """
        if self._handshake_done:
            self._http.request(
                HTTP_METHOD_POST,
                REST_PATH_SESSION_DISCONNECT,
                payload={REST_JSON_CLIENT_ID: self._client_id},
                timeout=REST_TIMEOUT_CONNECT_SEC,
            )
        self._connected = False
        self.reset_handshake()

    def reset_handshake(self) -> None:
        self._handshake_done = False
        self._last_handshake_error = EMPTY_STRING
        self._session_id = EMPTY_STRING
        self._pending_by_seq.clear()

    def mark_handshake_done(
        self,
        session_id: Optional[str] = None,
        min_next_seq: Optional[int] = None,
    ) -> None:
        self._handshake_done = True
        if session_id:
            self._session_id = session_id
        if isinstance(min_next_seq, int) and min_next_seq > VALUE_ZERO:
            self._seq = max(self._seq, min_next_seq - VALUE_ONE)

    def set_client_id(self, client_id: str) -> None:
        cid = (client_id or EMPTY_STRING).strip()
        if cid:
            self._client_id = cid

    def ensure_handshake(
        self,
        reset: bool = False,
        timeout_sec: float = HANDSHAKE_TIMEOUT_SEC_DEFAULT,
    ) -> bool:
        """
        NAME
            ensure_handshake - Acquire the REST control session.
        """
        if self._handshake_done and not reset:
            self._last_handshake_error = EMPTY_STRING
            return True
        if not self.connect():
            self._last_handshake_error = MESSAGE_CONNECT_FAILED
            return False
        if reset:
            self._http.request(
                HTTP_METHOD_POST,
                REST_PATH_SESSION_RESET,
                payload={},
                timeout=timeout_sec,
            )
        payload: Dict[str, Any] = {REST_JSON_CLIENT_ID: self._client_id}
        payload.update(_local_timezone_args())
        response = self._http.request(
            HTTP_METHOD_POST,
            REST_PATH_SESSION_CONNECT,
            payload=payload,
            timeout=timeout_sec,
        )
        if response.get("_http_status") != 200 or not bool(response.get("ok")):
            self._last_handshake_error = str(response.get(REST_JSON_MESSAGE, MESSAGE_HANDSHAKE_FAILED))
            self._connected = False
            return False
        self._connected = True
        self._handshake_done = True
        self._last_handshake_error = EMPTY_STRING
        self._session_id = str(response.get(REST_JSON_SESSION_ID, EMPTY_STRING))
        return True

    def send_command(self, name: str, args: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        NAME
            send_command - Submit a REST command and enqueue compatibility events.
        """
        command_name = str(name or EMPTY_STRING).strip()
        command_args = dict(args or {})
        if self._auto_handshake and command_name not in (COMMAND_UI_HANDSHAKE, COMMAND_UI_DISCONNECT):
            if not self.ensure_handshake():
                return None
        seq = self._next_seq()
        if command_name == COMMAND_UI_HANDSHAKE:
            self._handle_handshake_command(seq, command_args)
            return seq
        if command_name == COMMAND_UI_DISCONNECT:
            self._handle_disconnect_command(seq)
            return seq
        if command_name == COMMAND_UI_PING:
            self._handle_ping_command(seq)
            return seq
        if command_name == COMMAND_UI_POLL_LOG:
            self._handle_poll_log_command(seq)
            return seq
        if command_name == COMMAND_UI_MONITOR_ENABLE:
            self._handle_monitor_command(seq, True)
            return seq
        if command_name == COMMAND_UI_MONITOR_DISABLE:
            self._handle_monitor_command(seq, False)
            return seq
        self._handle_robot_command(seq, command_name, command_args)
        return seq

    def poll_events(self) -> List[BridgeEvent]:
        """
        NAME
            poll_events - Drain queued compatibility events and poll pending commands.
        """
        self._poll_pending_commands()
        events = list(self._event_queue)
        self._event_queue.clear()
        return events

    def get_state_snapshot(self) -> Dict[str, Any]:
        state = dict(self._last_state or {})
        state.update(self._flatten_runtime_state(self._last_runtime_state))
        return state

    def fetch_protocol_monitor(self) -> Dict[str, Any]:
        response = self._http.request(
            HTTP_METHOD_GET,
            REST_PATH_PROTOCOL_MONITOR,
            timeout=REST_TIMEOUT_COMMAND_SEC,
        )
        if response.get("_http_status") == 200 and bool(response.get("ok")):
            self._last_protocol_monitor = dict(response)
        return dict(self._last_protocol_monitor)

    def fetch_runtime_state(self) -> Dict[str, Any]:
        response = self._http.request(
            HTTP_METHOD_GET,
            REST_PATH_RUNTIME_STATE,
            timeout=REST_TIMEOUT_COMMAND_SEC,
        )
        payload = response.get("runtime")
        if response.get("_http_status") == 200 and isinstance(payload, dict):
            self._last_runtime_state = dict(payload)
            self._last_state.update(self._flatten_runtime_state(self._last_runtime_state))
        return dict(self._last_runtime_state)

    def fetch_tests_state(self) -> Dict[str, Any]:
        response = self._http.request(
            HTTP_METHOD_GET,
            REST_PATH_TESTS_STATE,
            timeout=REST_TIMEOUT_COMMAND_SEC,
        )
        payload = response.get("tests")
        if response.get("_http_status") == 200 and isinstance(payload, dict):
            self._last_tests_state = dict(payload)
        return dict(self._last_tests_state)

    def fetch_session_snapshot(self) -> Dict[str, Any]:
        response = self._http.request(
            HTTP_METHOD_GET,
            REST_PATH_SESSION,
            timeout=REST_TIMEOUT_CONNECT_SEC,
        )
        if response.get("_http_status") == 200 and bool(response.get("ok")):
            self._last_state = {
                "sessionId": str(response.get(REST_JSON_SESSION_ID, EMPTY_STRING)),
                "connected": bool(response.get(REST_JSON_CONNECTED, False)),
                "ownerClientId": str(response.get("ownerClientId", EMPTY_STRING)),
                "monitorEnabled": bool(response.get("monitorEnabled", False)),
                "lastActivityMs": response.get("lastActivityMs", VALUE_ZERO),
            }
        return dict(self._last_state)

    def _next_seq(self) -> int:
        self._seq += VALUE_ONE
        return self._seq

    def _handle_handshake_command(self, seq: int, args: Dict[str, Any]) -> None:
        reset = bool(args.get("reset", False))
        ok = self.ensure_handshake(reset=reset)
        status = EVENT_STATUS_OK if ok else EVENT_STATUS_ERROR
        message = "UI handshake OK." if ok else (self._last_handshake_error or MESSAGE_HANDSHAKE_FAILED)
        self._enqueue_ack(seq, COMMAND_UI_HANDSHAKE, status, message)
        payload = {
            REST_JSON_SESSION_ID: self._session_id,
            "minNextSeq": self._seq + VALUE_ONE,
            "protocolVersion": VALUE_ONE,
        }
        self._enqueue_out(seq, COMMAND_UI_HANDSHAKE, status, message, EMPTY_STRING, json.dumps(payload))

    def _handle_disconnect_command(self, seq: int) -> None:
        response = self._http.request(
            HTTP_METHOD_POST,
            REST_PATH_SESSION_DISCONNECT,
            payload={REST_JSON_CLIENT_ID: self._client_id},
            timeout=REST_TIMEOUT_CONNECT_SEC,
        )
        ok = response.get("_http_status") == 200 and bool(response.get("ok"))
        status = EVENT_STATUS_OK if ok else EVENT_STATUS_ERROR
        message = str(response.get(REST_JSON_MESSAGE, EMPTY_STRING))
        self._enqueue_ack(seq, COMMAND_UI_DISCONNECT, status, message)
        self._enqueue_out(seq, COMMAND_UI_DISCONNECT, status, message, message, EMPTY_STRING)
        self._connected = False
        self.reset_handshake()

    def _handle_ping_command(self, seq: int) -> None:
        response = self._http.request(
            HTTP_METHOD_POST,
            REST_PATH_SESSION_PING,
            payload={REST_JSON_CLIENT_ID: self._client_id},
            timeout=REST_TIMEOUT_CONNECT_SEC,
        )
        ok = response.get("_http_status") == 200 and bool(response.get("ok"))
        status = EVENT_STATUS_OK if ok else EVENT_STATUS_ERROR
        message = str(response.get(REST_JSON_MESSAGE, EMPTY_STRING))
        self._enqueue_ack(seq, COMMAND_UI_PING, status, message)
        self._enqueue_out(seq, COMMAND_UI_PING, status, message, message, EMPTY_STRING)

    def _handle_poll_log_command(self, seq: int) -> None:
        response = self._http.request(
            HTTP_METHOD_GET,
            REST_PATH_LOGS,
            timeout=LOG_TIMEOUT_SEC,
            query={REST_QUERY_AFTER: self._last_log_sequence},
        )
        ok = response.get("_http_status") == 200 and bool(response.get("ok"))
        status = EVENT_STATUS_OK if ok else EVENT_STATUS_ERROR
        message = str(response.get(REST_JSON_MESSAGE, EMPTY_STRING))
        self._enqueue_ack(seq, COMMAND_UI_POLL_LOG, status, message)
        lines: List[str] = []
        if ok:
            logs = response.get(REST_JSON_LOGS)
            if isinstance(logs, list):
                for row in logs:
                    if isinstance(row, dict):
                        text = str(row.get(REST_JSON_TEXT, EMPTY_STRING))
                        if text:
                            lines.append(text)
            next_sequence = response.get(REST_JSON_NEXT_SEQUENCE)
            if isinstance(next_sequence, int):
                self._last_log_sequence = next_sequence
        self._enqueue_out(seq, COMMAND_UI_POLL_LOG, status, message, "\n".join(lines), EMPTY_STRING)

    def _handle_monitor_command(self, seq: int, enabled: bool) -> None:
        path = REST_PATH_MONITOR_ENABLE if enabled else REST_PATH_MONITOR_DISABLE
        name = COMMAND_UI_MONITOR_ENABLE if enabled else COMMAND_UI_MONITOR_DISABLE
        response = self._http.request(
            HTTP_METHOD_POST,
            path,
            payload={REST_JSON_CLIENT_ID: self._client_id},
            timeout=REST_TIMEOUT_COMMAND_SEC,
        )
        ok = response.get("_http_status") == 200 and bool(response.get("ok"))
        status = EVENT_STATUS_OK if ok else EVENT_STATUS_ERROR
        message = str(response.get(REST_JSON_MESSAGE, EMPTY_STRING))
        self._enqueue_ack(seq, name, status, message)
        self._enqueue_out(seq, name, status, message, message, EMPTY_STRING)

    def fetch_current_config(self) -> Optional[Dict[str, Any]]:
        """
        NAME
            fetch_current_config - Fetch the robot's current bringup_system.json payload.
        """
        if self._auto_handshake and not self.ensure_handshake():
            return None
        response = self._http.request(
            HTTP_METHOD_GET,
            REST_PATH_CONFIG_CURRENT,
            timeout=REST_TIMEOUT_COMMAND_SEC,
            query={REST_QUERY_CLIENT_ID: self._client_id},
        )
        if response.get("_http_status") != 200 or not bool(response.get("ok")):
            return None
        payload = response.get("config")
        return payload if isinstance(payload, dict) else None

    def _handle_robot_command(self, seq: int, name: str, args: Dict[str, Any]) -> None:
        request_id = f"{self._client_id}-{seq}"
        payload = {
            REST_JSON_CLIENT_ID: self._client_id,
            REST_JSON_REQUEST_ID: request_id,
            REST_JSON_NAME: name,
            REST_JSON_ARGS: args,
        }
        response = self._http.request(
            HTTP_METHOD_POST,
            REST_PATH_COMMANDS,
            payload=payload,
            timeout=REST_TIMEOUT_COMMAND_SEC,
        )
        http_status = int(response.get("_http_status", VALUE_ZERO))
        ok = http_status in (200, 202) and bool(response.get("ok"))
        ack_status = EVENT_STATUS_OK if ok else EVENT_STATUS_ERROR
        message = str(response.get(REST_JSON_MESSAGE, EMPTY_STRING))
        self._enqueue_ack(seq, name, ack_status, message)
        command_id = response.get(REST_JSON_COMMAND_ID)
        if not isinstance(command_id, int):
            self._enqueue_out(seq, name, ack_status, message, message, EMPTY_STRING)
            return
        command_status = str(response.get(REST_JSON_STATUS, EMPTY_STRING)).upper()
        if command_status in (REST_STATUS_FINISHED, REST_STATUS_FAILED, REST_STATUS_STOPPED, REST_STATUS_REJECTED, REST_STATUS_UNKNOWN):
            self._enqueue_terminal_command_output(seq, name, command_id, ack_status, message)
            return
        self._pending_by_seq[seq] = PendingCommand(seq=seq, name=name, command_id=command_id)

    def _poll_pending_commands(self) -> None:
        for seq, pending in list(self._pending_by_seq.items()):
            response = self._http.request(
                HTTP_METHOD_GET,
                f"{REST_PATH_COMMANDS}/{pending.command_id}",
                timeout=REST_TIMEOUT_COMMAND_SEC,
                query={REST_QUERY_CLIENT_ID: self._client_id},
            )
            http_status = int(response.get("_http_status", VALUE_ZERO))
            if http_status == VALUE_ZERO:
                continue
            command_status = str(response.get(REST_JSON_STATUS, EMPTY_STRING)).upper()
            if command_status not in (
                REST_STATUS_FINISHED,
                REST_STATUS_FAILED,
                REST_STATUS_STOPPED,
                REST_STATUS_REJECTED,
                REST_STATUS_UNKNOWN,
            ):
                continue
            ack_status = EVENT_STATUS_OK if command_status == REST_STATUS_FINISHED else EVENT_STATUS_ERROR
            message = str(response.get(REST_JSON_MESSAGE, EMPTY_STRING))
            self._enqueue_terminal_command_output(seq, pending.name, pending.command_id, ack_status, message)
            self._pending_by_seq.pop(seq, None)

    def _enqueue_terminal_command_output(
        self,
        seq: int,
        name: str,
        command_id: int,
        status: str,
        message: str,
    ) -> None:
        output = self._http.request(
            HTTP_METHOD_GET,
            f"{REST_PATH_COMMANDS}/{command_id}/output",
            timeout=REST_TIMEOUT_COMMAND_SEC,
            query={REST_QUERY_CLIENT_ID: self._client_id},
        )
        text, json_text = self._extract_output_payload(output)
        if not text and not json_text:
            text = message
        self._enqueue_out(seq, name, status, message, text, json_text)

    def _extract_output_payload(self, output: Dict[str, Any]) -> tuple[str, str]:
        chunks = output.get(REST_JSON_CHUNKS)
        if not isinstance(chunks, list) or not chunks:
            return EMPTY_STRING, EMPTY_STRING
        texts: List[str] = []
        json_text = EMPTY_STRING
        for row in chunks:
            if not isinstance(row, dict):
                continue
            chunk_text = str(row.get(REST_JSON_TEXT, EMPTY_STRING))
            if not chunk_text:
                continue
            parsed = _parse_json_text(chunk_text)
            if parsed is not None and json_text == EMPTY_STRING:
                json_text = chunk_text
            else:
                texts.append(chunk_text)
        return "\n".join(texts), json_text

    def _enqueue_ack(self, seq: int, name: str, status: str, message: str) -> None:
        self._event_queue.append(
            BridgeEvent(
                type=EVENT_TYPE_ACK,
                seq=seq,
                name=name,
                status=status,
                message=message,
                text=EMPTY_STRING,
                json_text=EMPTY_STRING,
                ts=time.time(),
                session_id=self._session_id,
                state=self.get_state_snapshot(),
                raw={REST_JSON_STATUS: status, REST_JSON_MESSAGE: message},
            )
        )

    def _enqueue_out(
        self,
        seq: int,
        name: str,
        status: str,
        message: str,
        text: str,
        json_text: str,
    ) -> None:
        self._event_queue.append(
            BridgeEvent(
                type=EVENT_TYPE_OUT,
                seq=seq,
                name=name,
                status=status,
                message=message,
                text=text,
                json_text=json_text,
                ts=time.time(),
                session_id=self._session_id,
                state=self.get_state_snapshot(),
                raw={REST_JSON_STATUS: status, REST_JSON_MESSAGE: message},
            )
        )

    def _flatten_runtime_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        flattened: Dict[str, Any] = {}
        if not isinstance(payload, dict):
            return flattened
        for key in (
            "enabled",
            "estopped",
            "mode",
            "selectedProfile",
            "activeRuntimeProfile",
            "runtimeActive",
            "controlledLifecycleActive",
        ):
            if key in payload:
                flattened[key] = payload.get(key)
        return flattened


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
