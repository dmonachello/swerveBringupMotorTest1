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
HOST_ACTION_DSL_TEST_IMPORT = "hostDslTestImport"
HOST_ACTION_DSL_TEST_VALIDATE = "hostDslTestValidate"
HOST_UI_RECONNECT_LABEL = "Reconnect UI Session"
HOST_UI_RECONNECT_DESCRIPTION = (
    "Reconnect the PC UI session and perform a fresh UI handshake."
)
DSL_SECTION_TITLE = "DSL"
HOST_UI_DSL_IMPORT_LABEL = "Import DSL Test"
HOST_UI_DSL_IMPORT_DESCRIPTION = (
    "Import a .dsl file into local bringup_system.json for the selected profile."
)
HOST_UI_DSL_VALIDATE_LABEL = "Validate DSL Tests"
HOST_UI_DSL_VALIDATE_DESCRIPTION = (
    "Validate local DSL tests for the selected profile and print compiler/validator output."
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
    },
    {
        "name": HOST_ACTION_DSL_TEST_IMPORT,
        "showInHostUi": True,
        "uiSection": DSL_SECTION_TITLE,
        "uiLabel": HOST_UI_DSL_IMPORT_LABEL,
        "uiDescription": HOST_UI_DSL_IMPORT_DESCRIPTION,
        "actionKind": ACTION_KIND_HOST_LOCAL,
        "source": ACTION_SOURCE_HOST,
        "uiArgsJson": "",
    },
    {
        "name": HOST_ACTION_DSL_TEST_VALIDATE,
        "showInHostUi": True,
        "uiSection": DSL_SECTION_TITLE,
        "uiLabel": HOST_UI_DSL_VALIDATE_LABEL,
        "uiDescription": HOST_UI_DSL_VALIDATE_DESCRIPTION,
        "actionKind": ACTION_KIND_HOST_LOCAL,
        "source": ACTION_SOURCE_HOST,
        "uiArgsJson": "",
    },
]
