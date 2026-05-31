"""
NAME
    host_ui_actions.py - Host-side Bringup UI action metadata.

SYNOPSIS
    from tools.can_nt.host_ui_actions import HOST_UI_ACTIONS

DESCRIPTION
    Defines host-local UI actions that are rendered alongside robot-backed
    commands in the Bringup Control UI. These actions are desktop workflow
    operations rather than robot registry commands and therefore are owned by
    the Python host layer.
"""

from typing import Any, Dict, List

SESSION_SECTION_TITLE = "Session"
ACTION_KIND_HOST_LOCAL = "hostLocal"
ACTION_SOURCE_HOST = "host"

HOST_ACTION_RECONNECT_UI_SESSION = "hostReconnectUiSession"
HOST_UI_RECONNECT_LABEL = "Reconnect UI Session"
HOST_UI_RECONNECT_DESCRIPTION = (
    "Reconnect the PC UI session and perform a fresh UI handshake."
)

HOST_UI_ACTIONS: List[Dict[str, Any]] = [
    {
        "name": HOST_ACTION_RECONNECT_UI_SESSION,
        "showInHostUi": True,
        "uiSection": SESSION_SECTION_TITLE,
        "uiLabel": HOST_UI_RECONNECT_LABEL,
        "uiDescription": HOST_UI_RECONNECT_DESCRIPTION,
        "actionKind": ACTION_KIND_HOST_LOCAL,
        "source": ACTION_SOURCE_HOST,
        "uiArgsJson": "",
    }
]
