from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ConsoleRule:
    name: str
    regex: Any
    severity: str
    scope: str
    event_type: str
    device_id_group: Optional[int] = None


@dataclass
class ConsoleEntry:
    key: str
    event_type: str
    device_id: Optional[int]
    severity: str
    active: bool
    count: int
    first_seen: float
    last_seen: float
    last_message: str
    rule_name: str


class ConsoleMonitor:
    def __init__(
        self,
        rules_path: str,
        inactivity_timeout: float,
        publish_rate_hz: float,
        debug_log_path: str,
        debug_log_max_mb: int,
        debug_log_max_files: int,
        transport: str,
        host: str,
        port: int,
    ) -> None:
        self._rules_path = rules_path
        self._rules: List[ConsoleRule] = []
        self._entries: Dict[str, ConsoleEntry] = {}
        self._lock = threading.Lock()
        self._timeout_s = max(0.1, inactivity_timeout)
        self._publish_period = 0.5 if publish_rate_hz <= 0 else 1.0 / publish_rate_hz
        self._last_publish = 0.0
        self._lines_received = 0
        self._lines_matched = 0
        self._packets_received = 0
        self._last_addr: Optional[str] = None
        self._logger: Optional[logging.Logger] = None
        self._transport = transport.lower()
        self._host = host
        self._port = port
        self._udp_sock = None
        self._tcp_sock = None
        self._tcp_buf = bytearray()
        self._last_connect_attempt = 0.0
        self._recent_timeouts: Dict[int, float] = {}
        self._bus_fault_window_s = 5.0
        self._bus_fault_min_devices = 2
        self._published_keys: set[Tuple[Optional[int], str]] = set()
        self._reset_requested = False
        self._init_logger(debug_log_path, debug_log_max_mb, debug_log_max_files)
        self._load_rules()
        self._init_sockets()

    def _init_logger(self, path: str, max_mb: int, max_files: int) -> None:
        if not path:
            return
        try:
            Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            print(f"WARNING: Failed to create console log directory for '{path}': {exc}")
            return
        logger = logging.getLogger("console_monitor")
        logger.setLevel(logging.INFO)
        try:
            handler = RotatingFileHandler(
                path,
                maxBytes=max(1, max_mb) * 1024 * 1024,
                backupCount=max(1, max_files),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"WARNING: Failed to open console debug log '{path}': {exc}")
            return
        formatter = logging.Formatter("%(asctime)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
        self._logger = logger

    def _load_rules(self) -> None:
        self._rules.clear()
        try:
            raw = Path(self._rules_path).read_text(encoding="utf-8")
            payload = json.loads(raw)
        except Exception as exc:
            print(f"WARNING: Failed to load console rules '{self._rules_path}': {exc}")
            return
        rules = payload.get("rules", []) if isinstance(payload, dict) else []
        import re
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            name = str(rule.get("name", "")).strip()
            regex_text = rule.get("regex")
            if not name or not regex_text:
                continue
            try:
                flags = re.IGNORECASE if rule.get("ignore_case", True) else 0
                compiled = re.compile(regex_text, flags)
            except Exception as exc:
                print(f"WARNING: Invalid console regex '{name}': {exc}")
                continue
            severity = str(rule.get("severity", "INFO")).upper()
            scope = str(rule.get("scope", "system")).lower()
            event_type = str(rule.get("event_type", name)).strip()
            device_group = rule.get("device_id_group")
            if isinstance(device_group, int):
                group = device_group
            else:
                group = None
            self._rules.append(
                ConsoleRule(
                    name=name,
                    regex=compiled,
                    severity=severity,
                    scope=scope,
                    event_type=event_type,
                    device_id_group=group,
                )
            )

    def stop(self) -> None:
        if self._udp_sock is not None:
            try:
                self._udp_sock.close()
            except Exception:
                pass
            self._udp_sock = None
        if self._tcp_sock is not None:
            try:
                self._tcp_sock.close()
            except Exception:
                pass
            self._tcp_sock = None

    def _init_sockets(self) -> None:
        import socket
        if self._transport == "udp":
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.bind(("0.0.0.0", self._port))
                sock.setblocking(False)
                self._udp_sock = sock
            except Exception as exc:
                print(f"WARNING: Failed to bind NetConsole UDP {self._port}: {exc}")
                try:
                    sock.close()
                except Exception:
                    pass
                self._udp_sock = None

    def poll(self, now: float) -> None:
        if self._transport == "udp":
            self._poll_udp(now)
        else:
            self._poll_tcp(now)

    def request_reset(self) -> None:
        self._reset_requested = True

    def _poll_udp(self, now: float) -> None:
        import socket
        if self._udp_sock is None:
            return
        while True:
            try:
                data, addr = self._udp_sock.recvfrom(65535)
            except BlockingIOError:
                break
            except socket.error:
                break
            if not data:
                continue
            self._packets_received += 1
            try:
                self._last_addr = f"{addr[0]}:{addr[1]}"
            except Exception:
                self._last_addr = None
            self._handle_payload(data, now)

    def _poll_tcp(self, now: float) -> None:
        import socket
        if self._tcp_sock is None:
            if (now - self._last_connect_attempt) < 1.0:
                return
            self._last_connect_attempt = now
            try:
                sock = socket.create_connection((self._host, self._port), timeout=0.5)
                sock.setblocking(False)
                self._tcp_sock = sock
                self._last_addr = f"{self._host}:{self._port}"
            except Exception:
                self._tcp_sock = None
                return
        while True:
            try:
                data = self._tcp_sock.recv(65535)
            except BlockingIOError:
                break
            except Exception:
                try:
                    self._tcp_sock.close()
                except Exception:
                    pass
                self._tcp_sock = None
                self._tcp_buf.clear()
                break
            if not data:
                try:
                    self._tcp_sock.close()
                except Exception:
                    pass
                self._tcp_sock = None
                self._tcp_buf.clear()
                break
            self._packets_received += 1
            self._tcp_buf.extend(data)
            self._drain_tcp_buffer(now)

    def _drain_tcp_buffer(self, now: float) -> None:
        # NetConsole TCP frames are 2-byte big-endian length-prefixed records.
        # Payloads contain binary metadata plus the printable log text.
        while len(self._tcp_buf) >= 2:
            length = int.from_bytes(self._tcp_buf[:2], "big")
            if length <= 0:
                del self._tcp_buf[:2]
                continue
            if len(self._tcp_buf) < 2 + length:
                break
            payload = bytes(self._tcp_buf[2 : 2 + length])
            del self._tcp_buf[: 2 + length]
            self._handle_payload(payload, now)

    def _handle_payload(self, payload: bytes, ts: float) -> None:
        try:
            text = payload.decode("utf-8", errors="ignore")
        except Exception:
            return
        lines = text.splitlines() or [text]
        for line in lines:
            if not line:
                continue
            self._lines_received += 1
            if self._logger is not None:
                self._logger.info(line.rstrip())
            if self._process_line(line, ts):
                self._lines_matched += 1

    def _process_line(self, line: str, ts: float) -> bool:
        for rule in self._rules:
            match = rule.regex.search(line)
            if not match:
                continue
            device_id = None
            if rule.scope == "device" and rule.device_id_group is not None:
                try:
                    device_id = int(match.group(rule.device_id_group))
                except Exception:
                    device_id = None
            if rule.scope == "device" and device_id is not None:
                key = f"device:{rule.event_type}:{device_id}"
            else:
                key = f"system:{rule.event_type}"
            with self._lock:
                entry = self._entries.get(key)
                if entry is None:
                    self._entries[key] = ConsoleEntry(
                        key=key,
                        event_type=rule.event_type,
                        device_id=device_id,
                        severity=rule.severity,
                        active=True,
                        count=1,
                        first_seen=ts,
                        last_seen=ts,
                        last_message=line.strip(),
                        rule_name=rule.name,
                    )
                else:
                    entry.count += 1
                    entry.last_seen = ts
                    entry.last_message = line.strip()
                    entry.active = True
            if rule.scope == "device" and device_id is not None:
                if rule.event_type in {"SPARK_STATUS_TIMEOUT", "CAN_TIMEOUT"}:
                    self._note_timeout(device_id, ts)
            break
        else:
            return False
        return True

    def _note_timeout(self, device_id: int, ts: float) -> None:
        cutoff = ts - self._bus_fault_window_s
        self._recent_timeouts[device_id] = ts
        stale = [key for key, last in self._recent_timeouts.items() if last < cutoff]
        for key in stale:
            self._recent_timeouts.pop(key, None)
        if len(self._recent_timeouts) < self._bus_fault_min_devices:
            return
        self._set_derived_bus_fault(ts, len(self._recent_timeouts))

    def _set_derived_bus_fault(self, ts: float, devices: int) -> None:
        key = "system:BUS_FAULT_SUSPECTED"
        message = f"DERIVED: {devices} devices timed out within {self._bus_fault_window_s:.0f}s"
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._entries[key] = ConsoleEntry(
                    key=key,
                    event_type="BUS_FAULT_SUSPECTED",
                    device_id=None,
                    severity="WARN",
                    active=True,
                    count=1,
                    first_seen=ts,
                    last_seen=ts,
                    last_message=message,
                    rule_name="DERIVED_BUS_FAULT_SUSPECTED",
                )
                return
            if not entry.active:
                entry.count += 1
            entry.last_seen = ts
            entry.last_message = message
            entry.active = True

    def publish(self, table, now: float) -> None:
        if (now - self._last_publish) < self._publish_period:
            return
        self._last_publish = now
        if table is None:
            return
        with self._lock:
            entries = list(self._entries.values())
        for entry in entries:
            if entry.active and (now - entry.last_seen) > self._timeout_s:
                entry.active = False
        console_table = table.getSubTable("console")
        console_table.getEntry("reset").setBoolean(False)
        reset_entry = console_table.getEntry("reset")
        if reset_entry.getBoolean(False) or self._reset_requested:
            self._reset_requested = False
            self._reset_console_state(console_table)
            reset_entry.setBoolean(False)
        active_count = sum(1 for e in entries if e.active)
        console_table.getEntry("lastPublish").setDouble(float(now))
        console_table.getEntry("activeCount").setDouble(float(active_count))
        console_table.getEntry("totalCount").setDouble(float(len(entries)))
        console_table.getEntry("rulesLoaded").setDouble(float(len(self._rules)))
        console_table.getEntry("linesReceived").setDouble(float(self._lines_received))
        console_table.getEntry("linesMatched").setDouble(float(self._lines_matched))
        console_table.getEntry("packetsReceived").setDouble(float(self._packets_received))
        console_table.getEntry("lastSource").setString(self._last_addr or "")
        for entry in entries:
            if entry.device_id is not None:
                base = console_table.getSubTable("devices").getSubTable(str(entry.device_id)).getSubTable(entry.event_type)
            else:
                base = console_table.getSubTable("system").getSubTable(entry.event_type)
            base.getEntry("Active").setBoolean(entry.active)
            base.getEntry("Count").setDouble(float(entry.count))
            base.getEntry("LastSeen").setDouble(float(entry.last_seen))
            base.getEntry("Message").setString(entry.last_message)
            base.getEntry("Severity").setString(entry.severity)
            self._published_keys.add((entry.device_id, entry.event_type))

    def _reset_console_state(self, console_table) -> None:
        with self._lock:
            self._entries.clear()
        for device_id, event_type in list(self._published_keys):
            if device_id is not None:
                base = console_table.getSubTable("devices").getSubTable(str(device_id)).getSubTable(event_type)
            else:
                base = console_table.getSubTable("system").getSubTable(event_type)
            base.getEntry("Active").setBoolean(False)
            base.getEntry("Count").setDouble(0.0)
            base.getEntry("LastSeen").setDouble(0.0)
            base.getEntry("Message").setString("")
            base.getEntry("Severity").setString("")
        self._published_keys.clear()
        self._lines_received = 0
        self._lines_matched = 0
        self._packets_received = 0
        self._last_addr = None
        self._recent_timeouts.clear()
