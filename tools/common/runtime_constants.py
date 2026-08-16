from __future__ import annotations

"""
NAME
    runtime_constants.py - Shared runtime snapshot constants.

SYNOPSIS
    from tools.common.runtime_constants import RUNTIME_KEY_THREADS

DESCRIPTION
    Defines keys and status strings for runtime thread/component reporting.
"""

RUNTIME_KEY_THREADS = "threads"
RUNTIME_KEY_COMPONENTS = "components"
RUNTIME_KEY_NAME = "name"
RUNTIME_KEY_STATUS = "status"
RUNTIME_KEY_DETAIL = "detail"
RUNTIME_KEY_IDENT = "ident"
RUNTIME_KEY_DAEMON = "daemon"
RUNTIME_KEY_ALIVE = "alive"

RUNTIME_COMPONENT_CLI = "cli"
RUNTIME_COMPONENT_SNIFFER = "sniffer"
RUNTIME_COMPONENT_SESSION = "session"
RUNTIME_COMPONENT_VISIBILITY = "visibility"
RUNTIME_COMPONENT_PCAP = "pcap"
RUNTIME_COMPONENT_CONSOLE = "console-monitor"
RUNTIME_COMPONENT_SOURCES = "sources"
RUNTIME_COMPONENT_SOURCE_PREFIX = "source:"

RUNTIME_STATUS_RUNNING = "running"
RUNTIME_STATUS_STOPPED = "stopped"
RUNTIME_STATUS_ENABLED = "enabled"
RUNTIME_STATUS_DISABLED = "disabled"
RUNTIME_STATUS_CONNECTED = "connected"
RUNTIME_STATUS_DISCONNECTED = "disconnected"
RUNTIME_STATUS_AVAILABLE = "available"
RUNTIME_STATUS_UNAVAILABLE = "unavailable"

RUNTIME_DETAIL_SEPARATOR = " "
RUNTIME_DETAIL_HANDSHAKE_DONE = "handshake=done"
RUNTIME_DETAIL_HANDSHAKE_PENDING = "handshake=pending"
RUNTIME_DETAIL_SESSION_PREFIX = "session="
RUNTIME_DETAIL_COUNT_PREFIX = "count="
RUNTIME_DETAIL_AVAILABLE_PREFIX = "available="
RUNTIME_DETAIL_ENABLED = "enabled"
RUNTIME_DETAIL_DISABLED = "disabled"

THREAD_NAME_TCP_READER = "tcp-reader"
