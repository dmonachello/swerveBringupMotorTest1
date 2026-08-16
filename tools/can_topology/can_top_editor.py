#!/usr/bin/env python3
"""
NAME
    can_top_editor.py - Simple CAN bus topology editor (diagram -> profile).

SYNOPSIS
    python -m tools.can_topology.can_top_editor

DESCRIPTION
    Opens a small GUI that lets you place CAN nodes on a shared bus line and
    export a bringup profile JSON. This tool is Windows-friendly and relies
    only on the Python standard library (tkinter).

SIDE EFFECTS
    Opens a GUI window and reads/writes JSON files.

ERRORS
    Shows dialog errors for invalid data and file I/O failures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox, simpledialog

from tools.common.profile_session import SESSION_STATUS_LOCAL_ONLY

SCRIPT_PACKAGE_NAME = "tools.can_topology"
SCRIPT_REPO_ROOT_PARENT_INDEX = 2

if __package__ in (None, ""):
    repo_root_path = Path(__file__).resolve().parents[SCRIPT_REPO_ROOT_PARENT_INDEX]
    repo_root_text = str(repo_root_path)
    if repo_root_text not in sys.path:
        sys.path.insert(0, repo_root_text)
    __package__ = SCRIPT_PACKAGE_NAME

ENABLE_CANNECT_BUS_LINKS = True
ENABLE_CANNECT_FREE_FLOAT = True
ENABLE_CANNECT_CLUSTER_DRAG = True
TEXT_EMPTY = ""
EMPTY_STRING = TEXT_EMPTY
NODE_TYPE_DEVICE = "device"
NODE_TYPE_CALLOUT = "callout"
MENU_LABEL_ADD_ANALYZER = "Add Analyzer"
MENU_LABEL_ADD_DEVICE = "Add Node..."
MENU_LABEL_ADD_DIO_DEVICE = "Add DIO Device..."
MENU_LABEL_ADD_XBOX_CONTROLLER = "Add Xbox Controller..."
MENU_LABEL_SET_CANNECT_PORT = "Set CANnect Port..."
MENU_LABEL_POPULATE_NEIGHBORS = "Populate Neighbors from Layout"
MENU_LABEL_OPEN_CONFIG = "Open Config..."
MENU_LABEL_RELOAD_CANONICAL = "Reload Canonical"
MENU_LABEL_SAVE_CONFIG = "Save Config"
MENU_LABEL_SAVE_CONFIG_AS = "Save Config As..."
MENU_LABEL_SAVE_PROFILE_AS = "Save Profile As..."
MENU_LABEL_SAVE_SELECTION_AS = "Save Selection As..."
MENU_LABEL_SAVE_TO_DEPLOY = "Save to Deploy"
MENU_LABEL_WRITE_MINIMAL_DIAGRAM = "Write Minimal Diagram Metadata..."
DIALOG_TITLE_ADD_DIO = "Add DIO Device"
DIALOG_TITLE_ADD_XBOX_CONTROLLER = "Add Xbox Controller"
DIALOG_TITLE_EDIT_XBOX_CONTROLLER = "Edit Xbox Controller"
DIALOG_TITLE_REPLACE = "Replace"
ANALYZER_LABEL_PREFIX = "Analyzer"
ANALYZER_DEFAULT_CAN_ID = -1
ANALYZER_NODE_TYPE = "diagram"
ANALYZER_TAGS = ["analyzer"]
ANALYZER_LABEL_START = 1
ANALYZER_LABEL_STEP = 1
ANALYZER_ROW_MOD = 2
ANALYZER_SCALE = 1.0
LAYOUT_PAD_X = 200
BUS_INDEX_FLOOR = 1
CANNECT_PORT_MIN = 1
CANNECT_PORT_STEP = 1
CANNECT_PORT_ZERO = 0
CANNECT_PORT_COUNT_DEFAULT = 0
CAN_ID_DIAGRAM_DEFAULT = -1
DIAGRAM_VENDOR_SWYFT = "SWYFT"
DIAGRAM_VENDOR_ANALYZER = "ANALYZER"
DIAGRAM_DEVICE_WIRING = "Wiring"
DIAGRAM_DEVICE_ANALYZER = "Analyzer"
CATEGORY_ROBORIO = "roborio"
TAG_SWYFT = "swyft"
TAG_CANNECT = "cannect"
TAG_INJECT = "inject"
TAG_DIRECT = "direct"
TAG_ANALYZER = "analyzer"
MSG_CAN_BUS_LINK_TITLE = "Add CAN Bus Link"
MSG_CAN_BUS_LINK_SELECT_NODE = "Select exactly one CANnect node."
MSG_CAN_BUS_LINK_SELECT_BUS = "Select exactly one bus segment."
MSG_CAN_BUS_LINK_NODE_INVALID = "Selected node is not a CANnect node."
MSG_CAN_BUS_LINK_FULL = "{} already has {} CAN bus links."
MSG_CAN_BUS_LINK_DUP = "A CAN bus link to this segment already exists."
MSG_ADD_BUS_TITLE = "Add Bus"
MSG_ADD_BUS_PROMPT = "Click on the canvas where you want the new bus."
MSG_ADD_BUS_CONN_DUP = "A CAN bus link to this segment already exists."
MSG_ADD_BUS_CONN_INVALID = "Selected node is not a CANnect Direct node."
MSG_ADD_BUS_CONN_FULL = "{} already has {} CAN bus links."
MSG_SET_PORT_TITLE = "Set CANnect Port"
MSG_SET_PORT_SELECT = "Select one device linked to a CANnect node."
MSG_SET_PORT_NO_LINK = "Selected device is not linked to a CANnect node."
MSG_SET_PORT_INVALID = "Invalid port number."
MSG_SET_PORT_BUSY = "Port {} is already used by another device."
PROMPT_PORT = "Port (1-{}):"
BUS_CONNECT_DEFAULT = True
BUS_CONNECT_DISABLED = False
BUS_CONNECT_SIDE_LEFT = "left"
BUS_CONNECT_SIDE_RIGHT = "right"
PROMPT_BUS_INDEX = "Bus index (0-{}):"
PROMPT_BUS_TITLE = "Select Bus Segment"
PROMPT_CANNECT_TITLE = "Select CANnect Node"
PROMPT_CANNECT_LABEL = "CANnect label:\n{}"
ERR_CANNECT_NOT_FOUND = "CANnect label not found."
ERR_CANNECT_NONE = "No CANnect nodes exist in this diagram."
MSG_FIX_CANNECT_TITLE = "Fix CANnect Conflicts"
MSG_FIX_CANNECT_NONE = "No Ethernet-linked CANnect Inject nodes found."
MSG_FIX_CANNECT_REMOVED = "Removed {} CAN trunk link(s) from Ethernet-linked CANnect Inject nodes."
MSG_FIX_CANNECT_NO_REMOVE = "No CAN trunk links needed removal."
TITLE_POPULATE_NEIGHBORS = "Populate Neighbors"
MSG_POPULATE_NEIGHBORS_EMPTY = "No CAN nodes are available to populate neighbors."
MSG_POPULATE_NEIGHBORS_DONE = (
    "Populated {} neighbor link(s) and {} neighbor port link(s)."
)
TITLE_NEIGHBORS_STALE = "Neighbor Metadata Stale"
MSG_NEIGHBORS_STALE_SAVE = (
    "Neighbor metadata was generated before the latest layout change.\n\n"
    "Choose Yes to rebuild neighbors from the current layout before saving.\n"
    "Choose No to save the existing stale neighbor metadata.\n"
    "Choose Cancel to stop the save."
)
ERR_NO_SOURCE_CONFIG_TITLE = "No Source Config"
ERR_NO_SOURCE_CONFIG_TEXT = "Open a config first or use Save Config As..."
TITLE_SAVE_BRINGUP_CONFIG = "Save Bringup Config"
MSG_SAVED_CONFIG_FMT = "Updated {path} with profile '{profile}'."
MSG_SAVED_DEPLOY_FMT = "Updated deploy config from profile '{profile}'."
NEIGHBOR_STATUS_NOT_POPULATED = "Neighbors: not populated"
NEIGHBOR_STATUS_CURRENT = "Neighbors: current"
NEIGHBOR_STATUS_STALE = "Neighbors: stale"
LEFT_BOTTOM_SCROLL_HEIGHT = 300
LEFT_BOTTOM_SCROLL_BORDER = 0
LEFT_BOTTOM_WINDOW_ORIGIN = (0, 0)
LEFT_BOTTOM_PACK_PAD_Y = (6, 0)
LEFT_BOTTOM_SCROLL_DELTA = -1
LEFT_BOTTOM_MOUSEWHEEL_UNIT = "units"
LEFT_BOTTOM_MOUSEWHEEL_DIVISOR = 120
PROFILE_SCHEMA_VERSION_FALLBACK = 5
PROFILE_SCHEMA_COMPATIBILITY_VERSIONS = (2, 3, 4)
TK_EVENT_CONFIGURE = "<Configure>"
TK_EVENT_MOUSEWHEEL = "<MouseWheel>"
TK_EVENT_CONTROL_MOUSEWHEEL = "<Control-MouseWheel>"
TK_EVENT_BUTTON_4 = "<Button-4>"
TK_EVENT_BUTTON_5 = "<Button-5>"
TK_EVENT_MIDDLE_BUTTON_PRESS = "<ButtonPress-2>"
TK_EVENT_MIDDLE_BUTTON_DRAG = "<B2-Motion>"
TK_EVENT_MIDDLE_BUTTON_RELEASE = "<ButtonRelease-2>"
TK_BBOX_ALL = "all"
CLICK_DRAG_THRESHOLD_PX = 6.0
GUI_INTERACTION_DEBUG_ENV = "SID_GUI_INTERACTION_DEBUG"
GUI_INTERACTION_DEBUG_LOGDIR = "logs"
GUI_INTERACTION_DEBUG_LOG = "gui_interaction_debug.log"
MOUSEWHEEL_UP_NUM = 4
MOUSEWHEEL_DOWN_NUM = 5
ZOOM_WHEEL_STEP = 0.1
PAN_SCROLLREGION_PAD_VIEWPORTS = 1.0
SCROLLREGION_FIELD_COUNT = 4
SCROLLREGION_MIN_INDEX = 0
SCROLLREGION_MAX_INDEX = 2
SCROLLREGION_MIN_SPAN = 1.0
INVENTORY_ROW_PREFIX = "inventory:"
CONTROLLER_LABEL_PREFIX = "controller"
CONTROLLER_MODEL_DEFAULT = "Xbox Controller"
CONTROLLER_FIELD_LABEL = "Label"
CONTROLLER_FIELD_PORT = "USB Port"
CONTROLLER_FIELD_MODEL = "Model"
CONTROLLER_FIELD_TAGS = "Tags"
CONTROLLER_FIELD_COUNT = "Count"
CONTROLLER_FIELD_START_PORT = "Starting Port"
CONTROLLER_DIALOG_WIDTH = 320
CONTROLLER_DIALOG_PAD = 10
CONTROLLER_DIALOG_ROW_PAD = 6
CONTROLLER_COUNT_DEFAULT = 1
CONTROLLER_PORT_DEFAULT = 0
CONTROLLER_MANUFACTURER_DEFAULT = 1
CONTROLLER_DEVICE_TYPE_DEFAULT = 1
LIST_SCOPE_PROFILE = "Current Profile"
LIST_SCOPE_FULL = "Full Config"
MSG_CONTROLLER_DUPLICATE_LABEL = "Controller label '{}' already exists."
MSG_CONTROLLER_LABEL_REQUIRED = "Controller label is required."
MSG_CONTROLLER_DUPLICATE_PORT = "Xbox controller USB port {} already exists."
MSG_CONTROLLER_ALREADY_IN_PROFILE = "Xbox controller '{}' is already in the current profile."
MSG_CONTROLLER_INVALID_COUNT = "Controller count must be at least 1."
MSG_CONTROLLER_INVALID_PORT = "USB port must be 0 or greater."
MSG_CONTROLLER_SELECTION_REQUIRED = "Select an Xbox controller in the list."
MSG_INVENTORY_DROP_UNSUPPORTED = "This device cannot be placed on the topology canvas."
MSG_INVENTORY_EDIT_UNSUPPORTED = "Drag CAN or DIO inventory devices onto the canvas to add them to the current profile."
MSG_CONTROLLER_DELETE_CONFIRM = "Delete Xbox controller '{}' from the system config?"
MSG_CONTROLLER_DELETE_REFERENCED = (
    "Xbox controller '{label}' is referenced by other profiles:\n\n"
    "{profiles}\n\n"
    "Delete it from the entire system config anyway?"
)
MSG_INVENTORY_DELETE_CONFIRM = "Delete '{}' from the system config?"
MSG_INVENTORY_DELETE_REFERENCED = (
    "Device '{label}' is referenced by profiles:\n\n"
    "{profiles}\n\n"
    "Delete it from the entire system config anyway?"
)
BUTTON_REMOVE_FROM_PROFILE = "Remove From Profile"
BUTTON_DELETE_FROM_APP = "Delete From App Entirely"
TITLE_REMOVE_FROM_PROFILE = "Remove From Profile"
TITLE_DELETE_FROM_APP = "Delete From App Entirely"
MSG_REMOVE_NODE_SELECT = "Select a node to remove from the current profile."
MSG_REMOVE_SELECTION_SELECT = "Select devices or callouts to remove from the current profile."
MSG_REMOVE_SELECTION_CONFIRM = "Remove selected devices/callouts from the current profile?"
MSG_REMOVE_PROFILE_NOT_PRESENT = "'{}' is not in the current profile."
MSG_REMOVE_PROFILE_CONFIRM = "Remove '{}' from the current profile?"
MSG_DELETE_APP_SELECT_SINGLE = "Select a single device definition to delete from the app entirely."
MSG_DELETE_APP_UNSUPPORTED = "Only shared device definitions can be deleted from the app entirely."
MSG_CONTROLLER_ADD_NONE = "No Xbox controllers were added."
DETAIL_INTERFACE_USB = "USB"
MSG_INVALID_DIO_CHANNEL = "Invalid DIO channel for {}."
MSG_GENERIC_DEVICE_VENDOR_TYPE_REQUIRED = (
    "Generic device '{}' requires vendor and device type."
)
MSG_DEVICE_CAN_FIELDS_REQUIRED = "Device '{}' missing CAN fields: id/manufacturer/deviceType."
MSG_MISSING_DIO_TYPE = "Missing DIO device type for {}."
MSG_INVALID_DIO_TYPE = "Invalid DIO device type for {}."
MSG_ATTACH_SELECT = "Select exactly two nodes (one DIO device and one host device)."
MSG_ATTACH_INVALID = "Attachment requires one DIO device and one non-DIO device."
MSG_ATTACH_DUP = "Attachment already exists."
MSG_ATTACH_NONE = "No attachment links were removed."
MSG_ATTACH_REMOVE_SELECT = "Select one or more nodes to remove attachment links."
MSG_WIRE_SELECT = "Select a DIO device to wire to roboRIO."
MSG_WIRE_NO_ROBORIO = "No roboRIO node found in the diagram."
MSG_WIRE_DUP = "DIO wiring link already exists."
MSG_WIRE_NONE = "No DIO wiring links were removed."
MSG_WIRE_REMOVE_SELECT = "Select one or more nodes to remove DIO wiring links."
MSG_POWER_SELECT = "Select exactly two non-DIO nodes, with at least one power node."
MSG_POWER_INVALID = "Power links require two non-DIO nodes and at least one power node."
MSG_POWER_DUP = "Power link already exists."
MSG_POWER_NONE = "No power links were removed."
MSG_POWER_REMOVE_SELECT = "Select one or more nodes to remove power links."
MSG_DIO_ATTACH_REQUIRED = "DIO device {} must be attached to a host device."
MSG_DIO_WIRE_REQUIRED = "DIO device {} must be wired to roboRIO."
MSG_DIO_NO_ROBORIO = "DIO devices require a roboRIO node."
TITLE_ATTACH_DEVICE = "Attach Device"
TITLE_REMOVE_ATTACHMENT = "Remove Attachment"
TITLE_WIRE_DIO = "Wire DIO"
TITLE_REMOVE_DIO_WIRE = "Remove DIO Wire"
TITLE_POWER_LINK = "Power Link"
TITLE_REMOVE_POWER_LINK = "Remove Power Link"
KEY_ATTACHMENT_LINKS = "attachmentLinks"
KEY_DIO_LINKS = "dioLinks"
KEY_POWER_LINKS = "powerLinks"
KEY_DIAGRAM_NEIGHBOR_LINKS = "neighborLinks"
KEY_DIAGRAM_NEIGHBOR_PORTS = "neighborPorts"
KEY_TOPOLOGY = "topology"
KEY_TOPOLOGY_PROFILES = "profiles"
KEY_TOPOLOGY_NODES = "nodes"
KEY_TOPOLOGY_EDGES = "edges"
KEY_TOPOLOGY_VERSION = "version"
KEY_TOPOLOGY_SOURCE = "source"
KEY_TOPOLOGY_LAYOUT = "layout"
KEY_TOPOLOGY_OBJECT_TYPE = "objectType"
KEY_TOPOLOGY_NODE_TYPE = "nodeType"
KEY_TOPOLOGY_NODE_CLASS = "nodeClass"
KEY_TOPOLOGY_DEVICE_REF = "deviceRef"
KEY_TOPOLOGY_EDGE_ID = "id"
KEY_TOPOLOGY_EDGE_TYPE = "edgeType"
KEY_TOPOLOGY_FROM_NODE = "fromNode"
KEY_TOPOLOGY_FROM_PORT = "fromPort"
KEY_TOPOLOGY_TO_NODE = "toNode"
KEY_TOPOLOGY_TO_PORT = "toPort"
KEY_TOPOLOGY_VIEW = "view"
KEY_TOPOLOGY_FILTERS = "connectionFilters"
KEY_TOPOLOGY_BUS = "bus"
KEY_TOPOLOGY_ROW = "row"
KEY_TOPOLOGY_X = "x"
KEY_TOPOLOGY_Y = "y"
KEY_TOPOLOGY_Y_RELATIVE = "yRelative"
KEY_DIO = "dio"
KEY_POWER = "power"
KEY_NODE_KEY = "key"
KEY_ID = "id"
KEY_CATEGORY = "category"
KEY_DEVICE_TYPE = "deviceType"
TOPOLOGY_VERSION = 1
TOPOLOGY_SOURCE_LOCAL = "local"
TOPOLOGY_NODE_DEVICE = "device"
TOPOLOGY_NODE_JUNCTION = "junction"
TOPOLOGY_NODE_ANALYZER = "analyzer"
TOPOLOGY_NODE_POWER = "power"
TOPOLOGY_NODE_VIRTUAL = "virtual"
TOPOLOGY_NODE_CLASS_DEVICE = "device"
TOPOLOGY_NODE_CLASS_INFRASTRUCTURE = "infrastructure"
TOPOLOGY_EDGE_CAN_TRUNK = "can_trunk"
TOPOLOGY_EDGE_CAN_DROP = "can_drop"
TOPOLOGY_EDGE_CAN_TAP = "can_tap"
TOPOLOGY_EDGE_DIO = "dio"
TOPOLOGY_EDGE_POWER = "power"
TOPOLOGY_EDGE_VIRTUAL = "virtual"
TOPOLOGY_FILTER_CAN = "can"
TOPOLOGY_FILTER_POWER = "power"
TOPOLOGY_FILTER_DIO = "dio"
TOPOLOGY_FILTER_PWM = "pwm"
TOPOLOGY_FILTER_ANALOG = "analog"
TOPOLOGY_FILTER_VIRTUAL = "virtual"
TOPOLOGY_FILTERS_ORDER = (
    TOPOLOGY_FILTER_CAN,
    TOPOLOGY_FILTER_POWER,
    TOPOLOGY_FILTER_DIO,
    TOPOLOGY_FILTER_PWM,
    TOPOLOGY_FILTER_ANALOG,
    TOPOLOGY_FILTER_VIRTUAL,
)
TOPOLOGY_FILTER_LABELS = {
    TOPOLOGY_FILTER_CAN: "CAN",
    TOPOLOGY_FILTER_POWER: "Power",
    TOPOLOGY_FILTER_DIO: "DIO",
    TOPOLOGY_FILTER_PWM: "PWM",
    TOPOLOGY_FILTER_ANALOG: "Analog",
    TOPOLOGY_FILTER_VIRTUAL: "Virtual",
}
KEY_LINK_DEVICE = "device"
KEY_LINK_ATTACHMENT = "attachment"
KEY_LINK_ROBORIO = "roborio"
KEY_LINK_A = "a"
KEY_LINK_B = "b"
KEY_LINK_NODE = "node"
KEY_LINK_PORT = "port"
KEY_LINK_NEIGHBOR = "neighbor"
KEY_LINK_NEIGHBOR_PORT = "neighborPort"
KEY_ATTACHMENTS = "attachments"
NEIGHBOR_PORT_LEFT = "left"
PDF_FILE_EXTENSION = ".pdf"
TEMP_PRINT_DIAGRAM_PREFIX = "can_topology_"
TEMP_PRINT_NODE_LIST_PREFIX = "can_topology_nodes_"
TEMP_PRINT_CLEANUP_DELAY_MS = 30000
WINDOWS_NO_ASSOCIATION_ERROR = 1155
WINDOWS_REGKEY_CURRENT_USER_USERCHOICE = (
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice"
)
WINDOWS_REGKEY_CLASSES_ROOT_PDF = r".pdf"
WINDOWS_REGKEY_SHELL_PRINT_SUFFIX = r"\shell\print\command"
WINDOWS_REGVALUE_PROGID = "ProgId"
MSG_PRINT_OPENED_MANUAL = (
    "No default PDF print handler is available for the current .pdf association.\n\n"
    "Opened the PDF so you can print manually."
)
MSG_PRINT_NO_HANDLER = (
    "Saved PDF, but the current .pdf association does not expose a print action.\n\n"
    "Opened the PDF so you can print manually."
)
MSG_PRINTED_DIAGRAM = "Queued PDF for printing: {}"
MSG_PRINTED_NODE_LIST = "Queued node list for printing: {}"
NEIGHBOR_PORT_RIGHT = "right"
KEY_UNDO_INTERFACE = "interface"
KEY_UNDO_DIO = "dio"
KEY_UNDO_INVERT = "invert"
KEY_UNDO_ATTACHMENT_LINKS = "attachment_links"
KEY_UNDO_DIO_LINKS = "dio_links"
KEY_UNDO_POWER_LINKS = "power_links"
KEY_UNDO_NEIGHBOR_LINKS = "neighbor_links"
KEY_UNDO_NEIGHBOR_PORTS = "neighbor_ports"
ATTACH_LINE_COLOR = "#7a5d00"
WIRE_LINE_COLOR = "#1f6feb"
POWER_LINE_COLOR = "#c05000"
LINK_LINE_WIDTH = 2
ATTACH_LINK_DASH = (10, 4)
DIO_WIRE_DASH = (2, 3)
ETHERNET_BACKBONE_DASH = (8, 4)
ETHERNET_DEVICE_DASH = (6, 2, 1, 2)
DIO_RAIL_OFFSET = 120.0
COUNT_ZERO = 0
COUNT_ONE = 1
SEP_COMMA_SPACE = ", "
NEWLINE = "\n"
TITLE_RENAME_LABEL = "Rename Label"
MSG_RENAME_LABEL_CONFIRM = (
    "Rename '{old}' to '{new}'?\n"
    "This will update label references in this profile.\n"
    "Continue?"
)
TITLE_DIO_WARN = "DIO Warning"
MSG_DIO_WARN_HEADER = "DIO devices are not fully attached/wired:"
MSG_DIO_WARN_ATTACH = "Not attached to host: {labels}"
MSG_DIO_WARN_WIRE = "Not wired to roboRIO: {labels}"
MSG_DIO_WARN_NO_ROBORIO = "No roboRIO node present for DIO wiring."
MSG_DIO_WARN_PROMPT = "Continue saving?"
KEY_DIO_FREEY_MODE = "dioFreeYMode"
DIO_FREEY_MODE_RAIL = "rail"
KEY_DIAGRAM_BUS_COUNT = "busCount"
KEY_DIAGRAM_BUS_SPACING = "busSpacing"
KEY_DIAGRAM_BUS_OFFSETS = "busOffsets"
KEY_DIAGRAM_BUS_LEFTS = "busLefts"
KEY_DIAGRAM_BUS_RIGHTS = "busRights"
KEY_DIAGRAM_BUS_CONNECTORS = "busConnectors"
KEY_DIAGRAM_BUS_CONNECTOR_SIDES = "busConnectorSides"
KEY_DIAGRAM_NODES = "nodes"
KEY_DIAGRAM_CALLOUTS = "callouts"
KEY_DIAGRAM_ETHERNET_LINKS = "ethernetLinks"
KEY_DIAGRAM_CAN_LINKS = "canLinks"
KEY_DIAGRAM_DEVICE_LINKS = "deviceLinks"
DIAGRAM_CONTENT_LIST_KEYS = (
    KEY_DIAGRAM_BUS_OFFSETS,
    KEY_DIAGRAM_BUS_LEFTS,
    KEY_DIAGRAM_BUS_RIGHTS,
    KEY_DIAGRAM_BUS_CONNECTORS,
    KEY_DIAGRAM_BUS_CONNECTOR_SIDES,
    KEY_DIAGRAM_NODES,
    KEY_DIAGRAM_CALLOUTS,
    KEY_DIAGRAM_ETHERNET_LINKS,
    KEY_DIAGRAM_CAN_LINKS,
    KEY_DIAGRAM_DEVICE_LINKS,
    KEY_ATTACHMENT_LINKS,
    KEY_DIO_LINKS,
    KEY_DIAGRAM_NEIGHBOR_LINKS,
    KEY_DIAGRAM_NEIGHBOR_PORTS,
)
DIAGRAM_CONTENT_SCALAR_KEYS = (
    KEY_DIAGRAM_BUS_COUNT,
    KEY_DIAGRAM_BUS_SPACING,
)
TOPOLOGY_CONTENT_LIST_KEYS = (
    KEY_TOPOLOGY_NODES,
    KEY_TOPOLOGY_EDGES,
)
BUS_LINE_COLOR = "#444444"
MFG_NI = 1
MFG_CTRE = 4
MFG_REV = 5
DEVTYPE_ROBORIO = 1
DEVTYPE_GYRO = 4
DEVTYPE_MOTOR = 2
DEVTYPE_ENCODER = 7
DEVTYPE_POWER = 8
DEVTYPE_MISC = 10
MODEL_NEO_550 = "NEO 550"
MODEL_FLEX = "VORTEX"
MODEL_KRAKEN = "KRAKEN"
MODEL_FALCON = "FALCON"
HELP_DIO_TITLE = "DIO Devices"
HELP_DIO_BODY = (
    "Purpose: Model DIO devices like limit switches and external encoders.\n"
    "\n"
    "- Use Edit -> Add DIO Device... to create a DIO node.\n"
    "- Set Interface=DIO, Type=limitSwitch or encoderExternal, and DIO channel.\n"
    "- Attach to a host device (Edit -> Attach Device) when you want ownership/reference.\n"
    "- Wire to roboRIO (Edit -> Wire DIO to roboRIO) when you want physical wiring shown.\n"
    "- Missing attachment/wiring is allowed but will warn on save.\n"
)
ARG_VERSION = "--version"
ARG_VERSION_ATTR = "version"
ACTION_STORE_TRUE = "store_true"
HELP_VERSION = "Print version and exit."
ABOUT_TITLE = "About CAN Topology Editor"
ABOUT_NAME = "CAN Topology Editor"
ABOUT_DESCRIPTION = "GUI for editing CAN topology profiles."
ABOUT_LAUNCH = "Launch via python -m tools.can_topology.can_top_editor"
ABOUT_SEPARATOR = "\n"
BUILD_TITLE = "Build"

try:
    from tools.common.json_io import read_json
    from tools.common.topology_render import (
        device_type_key_for_category,
        fill_color_for_vendor,
        outline_color_for_vendor,
        shape_kind_for_category,
        text_color_for_fill,
        vendor_key_for_category,
    )
    from tools.common.topology_layout import (
        bus_ys as bus_ys_for_offsets,
        node_box_dims,
        node_box_y,
        node_center_y_unscaled,
    )
    from tools.common.topology_text import (
        fit_font_size as fit_font_size_shared,
        truncate_to_width as truncate_to_width_shared,
        wrap_label_lines as wrap_label_lines_shared,
    )
    from tools.common.topology_draw import draw_group_overlays, render_topology_canvas_common
except ImportError:  # Allow running as a script from this folder.
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[1]))
    from common.json_io import read_json  # type: ignore
    from common.topology_render import (  # type: ignore
        device_type_key_for_category,
        fill_color_for_vendor,
        outline_color_for_vendor,
        shape_kind_for_category,
        text_color_for_fill,
        vendor_key_for_category,
    )
    from common.topology_layout import (  # type: ignore
        bus_ys as bus_ys_for_offsets,
        node_box_dims,
        node_box_y,
        node_center_y_unscaled,
    )
    from common.topology_text import (  # type: ignore
        fit_font_size as fit_font_size_shared,
        truncate_to_width as truncate_to_width_shared,
        wrap_label_lines as wrap_label_lines_shared,
    )
    from common.topology_draw import draw_group_overlays, render_topology_canvas_common  # type: ignore
try:
    from tools.common.paths import profiles_canonical_path, profiles_deploy_path, repo_root
    from tools.common.config_api import (
        blank_profile_payload,
        ConfigRepository,
        create_blank_profile,
        delete_profile,
        rename_profile,
        replace_profile_devices,
        replace_profile_topology_entry,
        upsert_profile,
    )
    from tools.common.profile_io import compute_profiles_hash
except ImportError:
    try:
        from common.paths import profiles_canonical_path, profiles_deploy_path, repo_root  # type: ignore
        from common.config_api import (  # type: ignore
            blank_profile_payload,
            ConfigRepository,
            create_blank_profile,
            delete_profile,
            rename_profile,
            replace_profile_devices,
            replace_profile_topology_entry,
            upsert_profile,
        )
        from common.profile_io import compute_profiles_hash  # type: ignore
    except ImportError:
        profiles_canonical_path = None
        profiles_deploy_path = None
        repo_root = None
        blank_profile_payload = None
        ConfigRepository = None
        create_blank_profile = None
        delete_profile = None
        rename_profile = None
        replace_profile_devices = None
        replace_profile_topology_entry = None
        upsert_profile = None
        compute_profiles_hash = None

try:
    from tools.common import profile_constants as profile_consts
except ImportError:
    profile_consts = None

BRIDGE_CONFIG_SCHEMA_VERSION_FALLBACK = 1
KEY_BRIDGE_CONFIG = (
    profile_consts.KEY_BRIDGE_CONFIG if profile_consts is not None else "bridgeConfig"
)
KEY_BRIDGE_SCHEMA_VERSION = (
    profile_consts.KEY_BRIDGE_SCHEMA_VERSION
    if profile_consts is not None
    else "bridgeSchemaVersion"
)
KEY_BRIDGE_GENERATED_AT = (
    profile_consts.KEY_BRIDGE_GENERATED_AT
    if profile_consts is not None
    else "generatedAt"
)
KEY_BRIDGE_BY_PROFILE = (
    profile_consts.KEY_BRIDGE_BY_PROFILE if profile_consts is not None else "byProfile"
)
KEY_BRIDGE_GROUPS = (
    profile_consts.KEY_BRIDGE_GROUPS if profile_consts is not None else "groups"
)
KEY_BRIDGE_TESTS = (
    profile_consts.KEY_BRIDGE_TESTS if profile_consts is not None else "tests"
)
KEY_DEVICES = profile_consts.KEY_DEVICES if profile_consts is not None else "devices"
KEY_PROFILES = profile_consts.KEY_PROFILES if profile_consts is not None else "profiles"
KEY_BRIDGE_SELECTED_DEVICE = (
    profile_consts.KEY_BRIDGE_SELECTED_DEVICE
    if profile_consts is not None
    else "selectedDevice"
)
KEY_DEVICE = profile_consts.KEY_DEVICE if profile_consts is not None else "device"
KEY_LABEL = profile_consts.KEY_LABEL if profile_consts is not None else "label"
KEY_OBJECT_TYPE = (
    profile_consts.KEY_OBJECT_TYPE if profile_consts is not None else "objectType"
)
KEY_NODE_CLASS = (
    profile_consts.KEY_NODE_CLASS if profile_consts is not None else "nodeClass"
)
KEY_TYPE = profile_consts.KEY_TYPE if profile_consts is not None else "type"
KEY_TAGS = profile_consts.KEY_TAGS if profile_consts is not None else "tags"
KEY_MANUFACTURER = (
    profile_consts.KEY_MANUFACTURER if profile_consts is not None else "manufacturer"
)
KEY_INVERT = profile_consts.KEY_INVERT if profile_consts is not None else "invert"
KEY_VENDOR = profile_consts.KEY_VENDOR if profile_consts is not None else "vendor"
KEY_MODEL = profile_consts.KEY_MODEL if profile_consts is not None else "model"
TYPE_XBOX_CONTROLLER = (
    profile_consts.TYPE_XBOX_CONTROLLER if profile_consts is not None else "xboxController"
)
KEY_INTERFACE = (
    profile_consts.KEY_INTERFACE if profile_consts is not None else "interface"
)
KEY_INTERFACE_LEGACY = (
    profile_consts.KEY_INTERFACE_LEGACY if profile_consts is not None else "interface"
)
KEY_BRIDGE_GROUP_MEMBERS = "members"
KEY_SELECTED_ENABLED = "enabled"
KEY_TEST_DEFAULT_SET = "default_test_set"
KEY_TEST_SETS = "test_sets"
KEY_TEST_MOTOR_LABELS = "motorLabels"
KEY_TEST_ROTATION = "rotation"
KEY_TEST_ENCODER_KEY = "encoderKey"
KEY_TEST_DEADBAND_SWEEP = "deadbandSweep"
KEY_TEST_LIMIT_SWITCH = "limitSwitch"
KEY_TEST_LIMIT_SWITCH_ID = "id"
ENCODER_KEY_INTERNAL = "internal"


def bridge_group_member_label(member: Dict[str, object]) -> str:
    """
    NAME
        bridge_group_member_label - Read one bridge group member label.
    """
    if profile_consts is not None and hasattr(profile_consts, "get_group_member_label"):
        return str(profile_consts.get_group_member_label(member)).strip()
    value = member.get(KEY_LABEL)
    if isinstance(value, str) and value.strip():
        return value.strip()
    legacy = member.get(KEY_DEVICE)
    if isinstance(legacy, str) and legacy.strip():
        return legacy.strip()
    return TEXT_EMPTY


def topology_node_class_from_entry(entry: Dict[str, object]) -> str:
    """
    NAME
        topology_node_class_from_entry - Resolve nodeClass with shared compatibility fallback.
    """
    if profile_consts is not None and hasattr(profile_consts, "get_node_class"):
        return str(profile_consts.get_node_class(entry)).strip()
    value = entry.get(KEY_NODE_CLASS)
    if isinstance(value, str) and value.strip():
        return value.strip()
    object_type = str(entry.get(KEY_OBJECT_TYPE) or entry.get(KEY_TOPOLOGY_NODE_TYPE) or TEXT_EMPTY).strip()
    return TOPOLOGY_NODE_CLASS_DEVICE if object_type == TOPOLOGY_NODE_DEVICE else TOPOLOGY_NODE_CLASS_INFRASTRUCTURE


def make_bridge_group_member(label: str, enabled: bool = True) -> Dict[str, object]:
    """
    NAME
        make_bridge_group_member - Build a canonical bridge group member entry.
    """
    if profile_consts is not None and hasattr(profile_consts, "make_group_member"):
        return dict(profile_consts.make_group_member(label, enabled))
    return {
        KEY_LABEL: str(label).strip(),
        KEY_SELECTED_ENABLED: bool(enabled),
    }

try:
    from tools.config.schema_store import ConfigSchemaStore
except ImportError:
    ConfigSchemaStore = None

try:
    from .can_top_models import (
        BUCKET_CATEGORIES,
        DIAGRAM_CATEGORIES,
        DIAGRAM_CATEGORY_ANALYZER,
        DIAGRAM_CATEGORY_CANNECT_DIRECT,
        DIAGRAM_CATEGORY_CANNECT_INJECT,
        DIO_DEVICE_TYPES,
        INTERFACE_CAN,
        INTERFACE_DIO,
        GENERIC_CATEGORY,
        SINGLETON_CATEGORIES,
        SUPPORTED_DEVICE_TYPES,
        SUPPORTED_MANUFACTURERS,
        Node,
    )
    from .can_top_dialogs import CalloutDialog, NodeDialog
    from .can_top_layout import (
        align_selected,
        distribute_selected_horizontally,
        effective_bus_bounds,
        node_half_width,
        reset_layout_per_bus,
        snap_value,
        tidy_selection,
    )
    from .can_top_selection import (
        collect_tags,
        compile_tag_filter,
        match_tag,
        normalize_tag,
        normalize_tags,
        sort_nodes,
        tags_to_string,
    )
except ImportError:  # Allow running as a script from this folder.
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[1]))
    from can_topology.can_top_models import (  # type: ignore
        BUCKET_CATEGORIES,
        DIAGRAM_CATEGORIES,
        DIAGRAM_CATEGORY_ANALYZER,
        DIAGRAM_CATEGORY_CANNECT_DIRECT,
        DIAGRAM_CATEGORY_CANNECT_INJECT,
        DIO_DEVICE_TYPES,
        INTERFACE_CAN,
        INTERFACE_DIO,
        GENERIC_CATEGORY,
        SINGLETON_CATEGORIES,
        SUPPORTED_DEVICE_TYPES,
        SUPPORTED_MANUFACTURERS,
        Node,
    )
    from can_topology.can_top_dialogs import CalloutDialog, NodeDialog  # type: ignore
    from can_topology.can_top_layout import (  # type: ignore
        align_selected,
        distribute_selected_horizontally,
        effective_bus_bounds,
        node_half_width,
        reset_layout_per_bus,
        snap_value,
        tidy_selection,
    )
    from can_topology.can_top_selection import (  # type: ignore
        collect_tags,
        compile_tag_filter,
        match_tag,
        normalize_tag,
        normalize_tags,
        sort_nodes,
        tags_to_string,
    )

INFRASTRUCTURE_NODE_CATEGORIES = (
    DIAGRAM_CATEGORY_CANNECT_INJECT,
    DIAGRAM_CATEGORY_CANNECT_DIRECT,
    DIAGRAM_CATEGORY_ANALYZER,
)
INFRASTRUCTURE_MODEL_WIRING = DIAGRAM_DEVICE_WIRING.lower()
INFRASTRUCTURE_LABEL_ANALYZER = ANALYZER_LABEL_PREFIX.lower()

try:
    from tools.common.time_utils import timestamp_version
except ImportError:  # Allow running as a script from this folder.
    from common.time_utils import timestamp_version  # type: ignore

try:
    from tools.common.app_versions import (
        APP_CAN_TOPOLOGY_NAME,
        VERSIONS,
        VERSION_HEADER,
        format_version_line,
    )
    from tools.common.build_info import build_lines
except ImportError:  # Allow running as a script from this folder.
    from common.app_versions import (  # type: ignore
        APP_CAN_TOPOLOGY_NAME,
        VERSIONS,
        VERSION_HEADER,
        format_version_line,
    )
    from common.build_info import build_lines  # type: ignore

VERSION_APP_NAME = APP_CAN_TOPOLOGY_NAME
VERSION_TITLE = VERSION_HEADER


class TopologyEditor(tk.Tk):
    """
    NAME
        TopologyEditor - Main window for the CAN topology editor.

    DESCRIPTION
        Manages the node list, canvas rendering, and file export of a bringup
        system JSON.
    """

    @staticmethod
    def _config_repository() -> Optional["ConfigRepository"]:
        """
        NAME
            _config_repository - Return the shared config repository when available.
        """
        if ConfigRepository is None:
            return None
        return ConfigRepository()

    def _load_config_payload(self, path: Path) -> Dict[str, object]:
        """
        NAME
            _load_config_payload - Load a bringup_system.json-compatible payload through the shared repository.
        """
        repository = self._config_repository()
        if repository is not None:
            return repository.load_path(path).to_payload()
        return read_json(path)

    def _save_config_payload(self, path: Path, data: Dict[str, object]) -> Dict[str, object]:
        """
        NAME
            _save_config_payload - Save a bringup_system.json-compatible payload through the shared repository.
        """
        repository = self._config_repository()
        if repository is not None:
            session = repository.session_for_payload(path, data)
            target = path.resolve()
            canonical = repository.canonical_path().resolve()
            deploy = repository.deploy_path().resolve()
            if target == canonical or target == deploy:
                repository.sync(session)
            else:
                repository.save(session, path=path)
            return session.to_payload()
        data["schema_version"] = self._expected_schema_version()
        data["data_version"] = timestamp_version()
        data["data_hash"] = self._compute_data_hash(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return data

    def __init__(self) -> None:
        super().__init__()
        self.title("CAN Topology Editor")
        self.geometry("980x600")
        self.minsize(760, 480)
        self._nodes: List[Node] = []
        self._next_key = 1
        self._device_registry: Dict[str, Dict[str, object]] = {}
        self._device_registry_list: List[Dict[str, object]] = []
        self._non_topology_profile_labels: List[str] = []
        self._pending_global_device_deletions: set[str] = set()
        self._selected_inventory_label: Optional[str] = None
        self._list_drag_item: Optional[str] = None
        self._list_drag_start: Optional[Tuple[int, int]] = None
        self._list_dragging = False
        self._selected_key: Optional[int] = None
        self._drag_state: Optional[Tuple[int, float, float]] = None
        self._drag_free_y: Dict[int, float] = {}
        self._group_overlay_regions: List[Dict[str, object]] = []
        self._bus_connector_regions: List[Dict[str, object]] = []
        self._ethernet_links: List[Tuple[int, int]] = []
        self._can_bus_links: List[Dict[str, int]] = []
        self._cannect_device_links: List[Dict[str, int]] = []
        self._attachment_links: List[Dict[str, int]] = []
        self._dio_wiring_links: List[Dict[str, int]] = []
        self._power_links: List[Dict[str, int]] = []
        self._neighbor_links: List[Dict[str, int]] = []
        self._neighbor_ports: List[Dict[str, object]] = []
        self._neighbors_dirty = False
        self._profile_name = "drawn_profile"
        self._default_profile_name: Optional[str] = None
        self._profile_source_path: Optional[str] = None
        self._suppress_profile_select = False
        self._profile_names: List[str] = []
        self._profile_pick_var = tk.StringVar(value="")
        self._callout_scale_var = tk.StringVar(value="1.00")
        self._callout_debug_vars = {
            "target_type": tk.StringVar(value="--"),
            "target_key": tk.StringVar(value="--"),
            "target_label": tk.StringVar(value="--"),
            "target_category": tk.StringVar(value="--"),
            "target_id": tk.StringVar(value="--"),
            "target_bus": tk.StringVar(value="--"),
            "target_exists": tk.StringVar(value="--"),
        }
        self._layout_width = 0.0
        self._box_w = 140
        self._box_h = 60
        self._pan_y = 0.0
        self._pan_drag: Optional[Tuple[float, float]] = None
        self._bus_offsets: List[float] = [0.0]
        self._bus_lefts: List[float] = []
        self._bus_rights: List[float] = []
        self._bus_spacing = 160.0
        self._add_bus_mode = False
        self._pending_bus_after: Optional[int] = None
        self._pending_cannect_direct: Optional[int] = None
        self._pending_bus_island: bool = False
        self._bus_connectors: List[bool] = []
        self._bus_connector_sides: List[str] = []
        self._bus_drag: Optional[Tuple[int, float, float, float, float]] = None
        self._bus_resize: Optional[Tuple[int, str, float, float, float]] = None
        self._bus_connector_drag: Optional[Tuple[int, str]] = None
        self._undo_stack: List[Dict[str, object]] = []
        self._undo_limit = 20
        self._drag_undo_pending = False
        self._dirty = False
        self._zoom_label_var = tk.StringVar(value="Zoom: 100%")
        self._neighbor_status_var = tk.StringVar(value=NEIGHBOR_STATUS_NOT_POPULATED)
        self._neighbor_status_label: Optional[ttk.Label] = None
        self._profile_session_status_var = tk.StringVar(value=SESSION_STATUS_LOCAL_ONLY)
        self._selected_nodes: set[int] = set()
        self._selected_buses: set[int] = set()
        self._selection_rect: Optional[int] = None
        self._selection_start: Optional[Tuple[float, float]] = None
        self._selection_overlay_ids: List[int] = []
        self._node_bounds: Dict[int, Tuple[float, float, float, float]] = {}
        self._bus_ys: List[float] = []
        self._dragging_active = False
        self._redraw_pending = False
        self._clipboard: Optional[Dict[str, object]] = None
        self._multi_drag: Optional[Dict[str, object]] = None
        self._last_base_y: Optional[float] = None
        self._details_layout_shift = False
        self._last_canvas_height: Optional[int] = None
        self._pending_fit_to_window = False
        self._preserve_left_after_configure: Optional[float] = None
        self._preserve_top_after_configure: Optional[float] = None
        self._view_scrollregion_x_override: Optional[Tuple[float, float]] = None
        self._suppress_list_select = False
        self._syncing_selection = False
        self._zoom = 1.0
        self._debug_redraw_count = 0
        self._draw_state = {"bus_ys": [], "y_shift": 0.0, "scale": 1.0}
        self._snap_to_grid_var = tk.BooleanVar(value=False)
        self._smart_guides_var = tk.BooleanVar(value=False)
        self._grid_size_var = tk.IntVar(value=20)
        self._guide_x: Optional[float] = None
        self._guide_bus: Optional[int] = None
        self._guide_snap_px = 6.0
        self._tag_filter: Optional[str] = None
        self._tag_filter_fn: Optional[object] = None
        self._tag_filter_var = tk.StringVar(value="Filter: All")
        self._tag_filter_button: Optional[ttk.Button] = None
        self._list_scope_var = tk.StringVar(value=LIST_SCOPE_PROFILE)
        self._connection_filter_vars = {
            key: tk.BooleanVar(value=True) for key in TOPOLOGY_FILTERS_ORDER
        }
        self._list_sort_var = tk.StringVar(value="can_id")
        self._root_extras: Dict[str, object] = {}
        self._show_group_overlays_var = tk.BooleanVar(value=True)
        self._inline_editor: Optional[tk.Widget] = None
        self._inline_edit_info: Optional[Dict[str, object]] = None
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self._load_default_profile_if_present()
        self._refresh_profile_choices()
        self._redraw_canvas()

    def _build_ui(self) -> None:
        """
        NAME
            _build_ui - Construct menus and main layout.
        """
        self._build_menu()
        container = ttk.Frame(self, padding=8)
        container.pack(fill="both", expand=True)

        splitter = ttk.Panedwindow(container, orient="horizontal")
        splitter.pack(fill="both", expand=True)

        left = ttk.Frame(splitter)
        right = ttk.Frame(splitter)
        splitter.add(left, weight=1)
        splitter.add(right, weight=4)

        ttk.Label(left, text="Nodes").pack(anchor="w")
        list_scope_row = ttk.Frame(left)
        list_scope_row.pack(fill="x", pady=(2, 2))
        ttk.Label(list_scope_row, text="List Scope").pack(side="left")
        self._list_scope_combo = ttk.Combobox(
            list_scope_row,
            textvariable=self._list_scope_var,
            values=(LIST_SCOPE_PROFILE, LIST_SCOPE_FULL),
            state="readonly",
            width=16,
        )
        self._list_scope_combo.pack(side="right")
        self._list_scope_combo.bind("<<ComboboxSelected>>", self._on_list_scope_changed)
        tag_filter = ttk.Frame(left)
        tag_filter.pack(fill="x", pady=(2, 4))
        ttk.Label(tag_filter, textvariable=self._tag_filter_var).pack(side="left", anchor="w")
        self._tag_filter_button = ttk.Button(
            tag_filter, text="Clear", command=self._clear_tag_filter
        )
        self._tag_filter_button.pack(side="right")
        connection_filter = ttk.LabelFrame(left, text="Connections")
        connection_filter.pack(fill="x", pady=(0, 6))
        button_row = ttk.Frame(connection_filter)
        button_row.pack(fill="x", padx=4, pady=(2, 4))
        ttk.Button(button_row, text="All", command=self._enable_all_connection_filters).pack(side="left")
        ttk.Button(button_row, text="None", command=self._disable_all_connection_filters).pack(side="left", padx=(4, 0))
        filter_grid = ttk.Frame(connection_filter)
        filter_grid.pack(fill="x", padx=4, pady=(0, 4))
        for index, filter_key in enumerate(TOPOLOGY_FILTERS_ORDER):
            ttk.Checkbutton(
                filter_grid,
                text=TOPOLOGY_FILTER_LABELS[filter_key],
                variable=self._connection_filter_vars[filter_key],
                command=self._on_connection_filters_changed,
            ).grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 10), pady=1)
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True, pady=(4, 6))
        self.node_list = ttk.Treeview(
            list_frame,
            columns=("can_id", "type", "label", "group", "tags", "profiles"),
            show="headings",
            height=12,
            selectmode="extended",
        )
        self.node_list.heading("can_id", text="CAN ID")
        self.node_list.heading("type", text="Category")
        self.node_list.heading("label", text="Label")
        self.node_list.heading("group", text="Group")
        self.node_list.heading("tags", text="Tags")
        self.node_list.heading("profiles", text="Profiles")
        self.node_list.column("can_id", width=60, anchor="center")
        self.node_list.column("type", width=80, anchor="w")
        self.node_list.column("label", width=150, anchor="w")
        self.node_list.column("group", width=120, anchor="w")
        self.node_list.column("tags", width=100, anchor="w")
        self.node_list.column("profiles", width=160, anchor="w")
        self.node_list.pack(side="left", fill="both", expand=True)
        node_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.node_list.yview)
        node_scroll.pack(side="right", fill="y")
        self.node_list.configure(yscrollcommand=node_scroll.set)
        self.node_list.bind("<<TreeviewSelect>>", self._on_list_select)
        self.node_list.bind("<Double-1>", self._on_list_edit_start)
        self.node_list.bind("<F2>", self._on_list_edit_start)
        self.node_list.bind("<ButtonPress-1>", self._on_list_press, add="+")
        self.node_list.bind("<B1-Motion>", self._on_list_drag, add="+")
        self.bind_all("<ButtonRelease-1>", self._on_global_left_release, add="+")

        bottom_shell = ttk.Frame(left)
        bottom_shell.pack(fill=tk.X, side=tk.BOTTOM, pady=LEFT_BOTTOM_PACK_PAD_Y)
        bottom_canvas = tk.Canvas(
            bottom_shell,
            borderwidth=LEFT_BOTTOM_SCROLL_BORDER,
            highlightthickness=LEFT_BOTTOM_SCROLL_BORDER,
            height=LEFT_BOTTOM_SCROLL_HEIGHT,
        )
        bottom_scroll = ttk.Scrollbar(
            bottom_shell, orient=tk.VERTICAL, command=bottom_canvas.yview
        )
        bottom = ttk.Frame(bottom_canvas)
        bottom_window = bottom_canvas.create_window(
            LEFT_BOTTOM_WINDOW_ORIGIN, window=bottom, anchor=tk.NW
        )
        bottom_canvas.configure(yscrollcommand=bottom_scroll.set)
        bottom_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        bottom_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def _sync_bottom_scroll_region(_event: tk.Event) -> None:
            bottom_canvas.configure(scrollregion=bottom_canvas.bbox(TK_BBOX_ALL))

        def _sync_bottom_width(event: tk.Event) -> None:
            bottom_canvas.itemconfigure(bottom_window, width=event.width)

        def _on_bottom_mousewheel(event: tk.Event) -> None:
            bottom_canvas.yview_scroll(
                int(
                    LEFT_BOTTOM_SCROLL_DELTA
                    * (event.delta / LEFT_BOTTOM_MOUSEWHEEL_DIVISOR)
                ),
                LEFT_BOTTOM_MOUSEWHEEL_UNIT,
            )

        bottom.bind(TK_EVENT_CONFIGURE, _sync_bottom_scroll_region)
        bottom_canvas.bind(TK_EVENT_CONFIGURE, _sync_bottom_width)
        bottom_canvas.bind(TK_EVENT_MOUSEWHEEL, _on_bottom_mousewheel)

        ttk.Separator(bottom, orient="horizontal").pack(fill="x", pady=(0, 6))
        ttk.Label(bottom, text="Profile Name").pack(anchor="w")
        self.entry_profile = ttk.Combobox(bottom, values=self._profile_names, state="normal")
        self.entry_profile.set(self._profile_name)
        self.entry_profile.pack(fill="x", pady=(2, 0))
        self.entry_profile.bind("<<ComboboxSelected>>", self._on_profile_select)
        ttk.Label(bottom, text="Profiles").pack(anchor="w", pady=(6, 0))
        profile_row = ttk.Frame(bottom)
        profile_row.pack(fill="x", pady=(2, 0))
        self.profile_combo = ttk.Combobox(
            profile_row,
            textvariable=self._profile_pick_var,
            values=[],
            state="readonly",
        )
        self.profile_combo.pack(side="left", fill="x", expand=True)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_pick)
        ttk.Button(profile_row, text="Load", command=self._on_load_selected_profile).pack(
            side="left", padx=(6, 0)
        )
        self.var_set_default = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="Set As Default", variable=self.var_set_default).pack(
            anchor="w", pady=(4, 8)
        )
        self._refresh_default_checkbox()
        ttk.Label(bottom, textvariable=self._profile_session_status_var).pack(anchor="w", pady=(0, 4))
        ttk.Label(bottom, textvariable=self._zoom_label_var).pack(anchor="w", pady=(2, 2))
        self._neighbor_status_label = ttk.Label(bottom, textvariable=self._neighbor_status_var)
        self._neighbor_status_label.pack(anchor="w", pady=(0, 6))

        button_row = ttk.Frame(bottom)
        button_row.pack(fill="x")
        ttk.Button(button_row, text="Add", command=self._on_add).pack(fill="x", pady=2)
        ttk.Button(button_row, text="Edit Selected", command=self._on_edit_selected).pack(
            fill="x", pady=2
        )
        ttk.Button(button_row, text=BUTTON_REMOVE_FROM_PROFILE, command=self._on_remove_selected).pack(
            fill="x", pady=2
        )
        ttk.Button(button_row, text=BUTTON_DELETE_FROM_APP, command=self._on_delete_from_app_selected).pack(
            fill="x", pady=2
        )
        ttk.Button(button_row, text="Tidy All", command=self._tidy_all).pack(fill="x", pady=2)
        ttk.Button(button_row, text="Add Bus", command=self._on_add_bus).pack(fill="x", pady=2)
        ttk.Button(button_row, text="Add Callout", command=self._on_add_callout).pack(
            fill="x", pady=2
        )

        canvas_wrap = ttk.Frame(right)
        canvas_wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_wrap, background="#ffffff")
        self.canvas.pack(fill="both", expand=True, side="top")
        self.h_scroll = ttk.Scrollbar(right, orient="horizontal", command=self.canvas.xview)
        self.h_scroll.pack(fill="x", side="bottom")
        self.v_scroll = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview)
        self.v_scroll.pack(fill="y", side="right")
        self.canvas.configure(xscrollcommand=self.h_scroll.set)
        self.canvas.configure(yscrollcommand=self.v_scroll.set)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind(TK_EVENT_MIDDLE_BUTTON_PRESS, self._on_canvas_pan_press)
        self.canvas.bind(TK_EVENT_MIDDLE_BUTTON_DRAG, self._on_canvas_pan_drag)
        self.canvas.bind(TK_EVENT_MIDDLE_BUTTON_RELEASE, self._on_canvas_pan_release)
        self.canvas.bind("<Control-c>", lambda _e: self._on_copy())
        self.canvas.bind("<Control-v>", lambda _e: self._on_paste())
        self.bind_all("<Control-z>", lambda _e: self._undo_last())
        self.bind_all("<Control-Z>", lambda _e: self._undo_last())
        self.bind_all("<Control-a>", lambda _e: self._select_all_nodes())
        self.bind_all("<Control-A>", lambda _e: self._select_all_nodes())
        self.bind_all("<Control-plus>", lambda _e: self._zoom_step(0.1))
        self.bind_all("<Control-minus>", lambda _e: self._zoom_step(-0.1))
        self.bind_all("<Control-underscore>", lambda _e: self._zoom_step(-0.1))
        self.bind_all("<Control-equal>", lambda _e: self._zoom_step(0.1))
        self.bind_all("<Control-0>", lambda _e: self._zoom_reset())
        self.bind_all("<Control-Shift-L>", lambda _e: self._layout_even())
        self.bind_all("<Control-Shift-l>", lambda _e: self._layout_even())
        self.bind_all("<Control-l>", lambda _e: self._tidy_selection())
        self.bind_all("<Control-L>", lambda _e: self._tidy_selection())
        self.bind_all("<Control-d>", lambda _e: self._duplicate_selection())
        self.bind_all("<Control-D>", lambda _e: self._duplicate_selection())
        self.bind_all("<Control-g>", lambda _e: self._toggle_snap_to_grid())
        self.bind_all("<Control-G>", lambda _e: self._toggle_snap_to_grid())
        self.bind_all("<Control-Shift-G>", lambda _e: self._toggle_smart_guides())
        self.bind_all("<Control-Shift-g>", lambda _e: self._toggle_smart_guides())
        self.bind_all("<Control-s>", lambda _e: self._save_shortcut())
        self.bind_all("<Control-S>", lambda _e: self._save_shortcut())
        self.bind_all("<Control-p>", lambda _e: self._print_pdf_shortcut())
        self.bind_all("<Control-P>", lambda _e: self._print_pdf_shortcut())
        self.bind_all("<Delete>", self._on_delete_key)
        self.bind_all("<BackSpace>", self._on_delete_key)
        self.canvas.bind(TK_EVENT_CONFIGURE, self._on_canvas_configure)
        self.canvas.bind(TK_EVENT_MOUSEWHEEL, self._on_zoom_wheel)
        self.canvas.bind(TK_EVENT_CONTROL_MOUSEWHEEL, self._on_zoom_wheel)
        self.canvas.bind(TK_EVENT_BUTTON_4, self._on_zoom_wheel)
        self.canvas.bind(TK_EVENT_BUTTON_5, self._on_zoom_wheel)
        self.canvas.bind("<Left>", lambda e: self._nudge_selection("left", e))
        self.canvas.bind("<Right>", lambda e: self._nudge_selection("right", e))
        self.canvas.bind("<Up>", lambda e: self._nudge_selection("up", e))
        self.canvas.bind("<Down>", lambda e: self._nudge_selection("down", e))

        self._build_details_panel(right)
        self._set_details_dock_visible(bool(self._show_details_dock_var.get()))
        self._set_tag_filter(self._tag_filter)

    def _build_menu(self) -> None:
        """
        NAME
            _build_menu - Configure top-level menus.
        """
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New", command=self._new_diagram)
        file_menu.add_command(label=MENU_LABEL_OPEN_CONFIG, command=self._open_profile)
        file_menu.add_command(label=MENU_LABEL_RELOAD_CANONICAL, command=self._reload_canonical_profile)
        file_menu.add_command(label=MENU_LABEL_SAVE_CONFIG, command=self._save_config)
        file_menu.add_command(label=MENU_LABEL_SAVE_CONFIG_AS, command=self._save_config_as)
        file_menu.add_command(label=MENU_LABEL_SAVE_PROFILE_AS, command=self._save_profile_as)
        file_menu.add_command(label=MENU_LABEL_SAVE_SELECTION_AS, command=self._save_selection_as)
        file_menu.add_command(label=MENU_LABEL_SAVE_TO_DEPLOY, command=self._on_save_to_deploy)
        file_menu.add_command(
            label=MENU_LABEL_WRITE_MINIMAL_DIAGRAM,
            command=self._write_minimal_diagram_metadata,
        )
        file_menu.add_command(label="Export PDF...", command=self._on_export_pdf)
        file_menu.add_command(label="Print Diagram...", command=self._print_pdf_shortcut)
        file_menu.add_command(label="Print Node List...", command=self._print_node_list)
        file_menu.add_command(label="Export Java Constants...", command=self._on_export_java_constants)
        file_menu.add_command(label="Undo", command=self._undo_last)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menu.add_cascade(label="File", menu=file_menu)

        profiles_menu = tk.Menu(menu, tearoff=False)
        profiles_menu.add_command(label="New Blank Profile...", command=self._new_blank_profile)
        profiles_menu.add_command(label="Import Profile...", command=self._import_profile)
        profiles_menu.add_command(label="Export Profile...", command=self._export_profile)
        profiles_menu.add_separator()
        profiles_menu.add_command(label="Rename Profile...", command=self._rename_profile)
        profiles_menu.add_command(label="Delete Profile...", command=self._delete_profile)
        menu.add_cascade(label="Profiles", menu=profiles_menu)
        edit_menu = tk.Menu(menu, tearoff=False)
        edit_menu.add_command(label="Copy", command=self._on_copy)
        edit_menu.add_command(label="Paste", command=self._on_paste)
        edit_menu.add_command(label="Bulk Edit...", command=self._bulk_edit_selection)
        edit_menu.add_separator()
        edit_menu.add_command(label=MENU_LABEL_ADD_DEVICE, command=self._on_add)
        edit_menu.add_command(label=MENU_LABEL_ADD_DIO_DEVICE, command=self._on_add_dio_device)
        edit_menu.add_command(
            label=MENU_LABEL_ADD_XBOX_CONTROLLER,
            command=self._on_add_xbox_controller,
        )
        edit_menu.add_command(label="Add CANnect Inject", command=self._add_cannect_inject)
        edit_menu.add_command(label="Add CANnect Direct", command=self._add_cannect_direct)
        edit_menu.add_command(label=MENU_LABEL_ADD_ANALYZER, command=self._add_analyzer_node)
        edit_menu.add_command(label="Add Bus Segment", command=self._on_add_bus)
        edit_menu.add_command(label="Add Ethernet Link", command=self._add_ethernet_link)
        edit_menu.add_command(label="Remove Ethernet Link", command=self._remove_ethernet_link)
        edit_menu.add_separator()
        edit_menu.add_command(label="Link Device to CANnect", command=self._link_selected_devices_to_cannect)
        edit_menu.add_command(label=MENU_LABEL_SET_CANNECT_PORT, command=self._set_cannect_port)
        edit_menu.add_command(
            label="Fix CANnect Conflicts", command=lambda: self._fix_cannect_conflicts(notify=True)
        )
        if ENABLE_CANNECT_BUS_LINKS:
            edit_menu.add_separator()
            edit_menu.add_command(label="Add CAN Bus Link", command=self._add_can_bus_link)
            edit_menu.add_command(label="Remove CAN Bus Link", command=self._remove_can_bus_link)
            edit_menu.add_separator()
        edit_menu.add_command(label="Remove CANnect Device Link", command=self._remove_cannect_device_link)
        edit_menu.add_separator()
        edit_menu.add_command(label="Attach Device (Logical)", command=self._attach_device_link)
        edit_menu.add_command(label="Remove Attachment Link", command=self._remove_attachment_link)
        edit_menu.add_command(label="Add Power Link", command=self._add_power_link)
        edit_menu.add_command(label="Remove Power Link", command=self._remove_power_link)
        edit_menu.add_command(label="Wire DIO to roboRIO", command=self._wire_dio_to_roborio)
        edit_menu.add_command(label="Remove DIO Wire", command=self._remove_dio_wire)
        edit_menu.add_separator()
        edit_menu.add_command(
            label=MENU_LABEL_POPULATE_NEIGHBORS,
            command=self._populate_neighbors_from_layout,
        )
        menu.add_cascade(label="Edit", menu=edit_menu)
        tags_menu = tk.Menu(menu, tearoff=False)
        tags_menu.add_command(label="Select by Tag...", command=self._select_by_tag)
        tags_menu.add_command(label="Filter List by Tag...", command=self._filter_list_by_tag)
        tags_menu.add_command(label="Select Filtered Nodes", command=self._select_filtered_nodes)
        tags_menu.add_command(label="Clear Tag Filter", command=self._clear_tag_filter)
        tags_menu.add_separator()
        tags_menu.add_command(label="Apply Tag to Selection...", command=self._apply_tag_to_selection)
        tags_menu.add_command(
            label="Remove Tag from Selection...", command=self._remove_tag_from_selection
        )
        tags_menu.add_separator()
        tags_menu.add_command(label="Tidy by Tag...", command=self._tidy_by_tag)
        tags_menu.add_separator()
        tags_menu.add_radiobutton(
            label="Sort List by CAN ID",
            variable=self._list_sort_var,
            value="can_id",
            command=self._refresh_list,
        )
        tags_menu.add_radiobutton(
            label="Sort List by Tag",
            variable=self._list_sort_var,
            value="tag",
            command=self._refresh_list,
        )
        menu.add_cascade(label="Tags", menu=tags_menu)

        groups_menu = tk.Menu(menu, tearoff=False)
        groups_menu.add_command(
            label="Create Group from Selection...",
            command=self._create_group_from_selection,
        )
        groups_menu.add_command(
            label="Remove Group...",
            command=self._remove_bridge_group,
        )
        menu.add_cascade(label="Groups", menu=groups_menu)

        layout_menu = tk.Menu(menu, tearoff=False)
        layout_menu.add_command(label="Align Left", command=lambda: self._align_selected("left"))
        layout_menu.add_command(label="Align Center", command=lambda: self._align_selected("center"))
        layout_menu.add_command(label="Align Right", command=lambda: self._align_selected("right"))
        layout_menu.add_separator()
        layout_menu.add_command(
            label="Distribute Horizontally", command=self._distribute_selected_horizontally
        )
        layout_menu.add_separator()
        layout_menu.add_command(label="Tidy All", command=self._tidy_all)
        layout_menu.add_command(label="Tidy Selection", command=self._tidy_selection)
        layout_menu.add_separator()
        layout_menu.add_command(label="Reset Layout", command=self._layout_even)
        layout_menu.add_command(label="Single Bus Layout", command=self._layout_single_bus)
        layout_menu.add_separator()
        layout_menu.add_command(label="Auto Layout (Readable)", command=self._auto_layout_readable)
        menu.add_cascade(label="Layout", menu=layout_menu)
        view_menu = tk.Menu(menu, tearoff=False)
        view_menu.add_command(label="Zoom In", command=lambda: self._zoom_step(0.1))
        view_menu.add_command(label="Zoom Out", command=lambda: self._zoom_step(-0.1))
        view_menu.add_command(label="Zoom Reset", command=self._zoom_reset)
        view_menu.add_command(label="Fit to Window", command=self._fit_to_window)
        view_menu.add_separator()
        self._show_warn_badges_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(
            label="Show Warnings/Errors",
            variable=self._show_warn_badges_var,
            command=self._redraw_canvas,
        )
        view_menu.add_checkbutton(
            label="Show Group Overlays",
            variable=self._show_group_overlays_var,
            command=self._redraw_canvas,
        )
        self._show_details_dock_var = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(
            label="Show Details Dock",
            variable=self._show_details_dock_var,
            command=lambda: self._set_details_dock_visible(bool(self._show_details_dock_var.get())),
        )
        view_menu.add_checkbutton(label="Snap to Grid", variable=self._snap_to_grid_var)
        view_menu.add_checkbutton(label="Smart Guides", variable=self._smart_guides_var)
        grid_menu = tk.Menu(view_menu, tearoff=False)
        for size in (10, 20, 40):
            grid_menu.add_radiobutton(
                label=f"{size}px", value=size, variable=self._grid_size_var
            )
        view_menu.add_cascade(label="Grid Size", menu=grid_menu)
        view_menu.add_command(label="Legend...", command=self._show_legend_dialog)
        menu.add_cascade(label="View", menu=view_menu)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="Help...", command=self._show_help_dialog)
        help_menu.add_command(label="Keyboard Shortcuts...", command=self._show_shortcuts_dialog)
        help_menu.add_separator()
        help_menu.add_command(label="About...", command=self._show_about_dialog)
        menu.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menu)

    def _build_details_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_details_panel - Create the selected-node details area.
        """
        self._details_dock_container = ttk.Frame(parent)
        panel = ttk.LabelFrame(self._details_dock_container, text="Node Details", padding=8)
        self._node_details_panel = panel

        self.detail_vars = {
            "category": tk.StringVar(value="--"),
            "label": tk.StringVar(value="--"),
            "can_id": tk.StringVar(value="--"),
            "interface": tk.StringVar(value="--"),
            "dio": tk.StringVar(value="--"),
            "invert": tk.StringVar(value="--"),
            "vendor": tk.StringVar(value="--"),
            "type": tk.StringVar(value="--"),
            "motor": tk.StringVar(value="--"),
            "limits": tk.StringVar(value="--"),
            "terminator": tk.StringVar(value="--"),
            "scale": tk.StringVar(value="1.00"),
            "tags": tk.StringVar(value="--"),
        }
        self._terminator_status_var = tk.StringVar(value="???")


        rows = [
            ("Category", "category"),
            ("Label", "label"),
            ("CAN ID", "can_id"),
            ("Interface", "interface"),
            ("DIO", "dio"),
            ("Invert", "invert"),
            ("Vendor", "vendor"),
            ("CAN Device Type", "type"),
            ("Motor", "motor"),
            ("Limits", "limits"),
            ("Terminator", "terminator"),
            ("Tags", "tags"),
            ("Scale", "scale"),
        ]
        for idx, (title, key) in enumerate(rows):
            ttk.Label(panel, text=f"{title}:").grid(row=idx, column=0, sticky="w", padx=(0, 6))
            ttk.Label(panel, textvariable=self.detail_vars[key]).grid(
                row=idx, column=1, sticky="w"
            )
        scale_row = len(rows)
        scale_controls = ttk.Frame(panel)
        scale_controls.grid(row=scale_row, column=1, sticky="w", pady=(4, 0))
        ttk.Button(scale_controls, text="-", width=3, command=lambda: self._nudge_scale(-0.1)).pack(
            side="left"
        )
        ttk.Button(scale_controls, text="+", width=3, command=lambda: self._nudge_scale(0.1)).pack(
            side="left", padx=(4, 0)
        )
        status_row = scale_row + 1
        self._terminator_status_label = ttk.Label(
            panel, textvariable=self._terminator_status_var
        )
        self._terminator_status_label.grid(
            row=status_row, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        callout_panel = ttk.LabelFrame(self._details_dock_container, text="Callout Details", padding=8)
        self._callout_details_panel = callout_panel
        ttk.Label(callout_panel, text="Scale:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Label(callout_panel, textvariable=self._callout_scale_var).grid(
            row=0, column=1, sticky="w"
        )
        callout_controls = ttk.Frame(callout_panel)
        callout_controls.grid(row=1, column=1, sticky="w", pady=(4, 0))
        ttk.Button(
            callout_controls, text="-", width=3, command=lambda: self._nudge_callout_scale(-0.1)
        ).pack(side="left")
        ttk.Button(
            callout_controls, text="+", width=3, command=lambda: self._nudge_callout_scale(0.1)
        ).pack(side="left", padx=(4, 0))
        debug_rows = [
            ("Target Type", "target_type"),
            ("Target Key", "target_key"),
            ("Target Label", "target_label"),
            ("Target Category", "target_category"),
            ("Target ID", "target_id"),
            ("Target Bus", "target_bus"),
            ("Target Exists", "target_exists"),
        ]
        for idx, (title, key) in enumerate(debug_rows, start=2):
            ttk.Label(callout_panel, text=f"{title}:").grid(
                row=idx, column=0, sticky="w", padx=(0, 6)
            )
            ttk.Label(callout_panel, textvariable=self._callout_debug_vars[key]).grid(
                row=idx, column=1, sticky="w"
            )
        self._node_details_panel.pack(fill="x", pady=(8, 0))
        self._callout_details_panel.pack(fill="x", pady=(8, 0))

    def _set_details_dock_visible(self, visible: bool) -> None:
        """
        NAME
            _set_details_dock_visible - Show or hide the explicit details dock.
        """
        container = getattr(self, "_details_dock_container", None)
        if container is None:
            return
        try:
            mapped = bool(container.winfo_manager())
        except Exception:
            mapped = False
        if visible and not mapped:
            container.pack(fill="x", side="bottom")
        elif not visible and mapped:
            container.pack_forget()

    def _update_details_panel(self, node: Optional[Node]) -> None:
        """
        NAME
            _update_details_panel - Refresh the details panel fields.
        """
        self._refresh_terminator_status()
        if node is None:
            self._clear_node_details_fields()
            self._clear_callout_details_fields()
            return
        if node.node_type == "callout":
            return
        if node.node_type == "callout":
            return

        limits_text = "--"
        if node.limits:
            fwd = node.limits.get("fwdDio", "--")
            rev = node.limits.get("revDio", "--")
            inv = node.limits.get("invert", False)
            limits_text = f"fwd={fwd}, rev={rev}, invert={inv}"

        term_text = "--" if node.terminator is None else ("on" if node.terminator else "off")

        self.detail_vars["category"].set(node.category)
        self.detail_vars["label"].set(node.label)
        if isinstance(node.can_id, int) and node.can_id >= 0:
            self.detail_vars["can_id"].set(str(node.can_id))
        else:
            self.detail_vars["can_id"].set("--")
        self.detail_vars["interface"].set(node.interface or "--")
        if node.interface == INTERFACE_DIO:
            dio_text = "--" if node.dio is None else str(node.dio)
            invert_text = "--" if node.invert is None else ("on" if node.invert else "off")
        else:
            dio_text = "--"
            invert_text = "--"
        self.detail_vars["dio"].set(dio_text)
        self.detail_vars["invert"].set(invert_text)
        self.detail_vars["vendor"].set(node.vendor or "--")
        self.detail_vars["type"].set(node.device_type or "--")
        self.detail_vars["motor"].set(node.motor or "--")
        self.detail_vars["limits"].set(limits_text)
        self.detail_vars["terminator"].set(term_text)
        self.detail_vars["scale"].set(f"{node.scale:.2f}")
        self.detail_vars["tags"].set(self._tags_to_string(node.tags) or "--")

    def _inventory_entry_for_label(self, label: str) -> Optional[Dict[str, object]]:
        """
        NAME
            _inventory_entry_for_label - Look up one device registry entry by label.
        """
        label_text = str(label).strip()
        if not label_text:
            return None
        entry = self._device_registry.get(label_text)
        if isinstance(entry, dict):
            return entry
        return None

    def _active_profile_labels(self) -> set[str]:
        """
        NAME
            _active_profile_labels - Return all labels currently in the active profile.
        """
        labels = {
            (node.label or TEXT_EMPTY).strip()
            for node in self._device_nodes()
            if (node.label or TEXT_EMPTY).strip()
        }
        labels.update(
            label
            for label in list(self.__dict__.get("_non_topology_profile_labels", []) or [])
            if str(label).strip()
        )
        return labels

    def _inventory_row_id(self, label: str) -> str:
        """
        NAME
            _inventory_row_id - Build the Treeview row id for an inventory label.
        """
        return f"{INVENTORY_ROW_PREFIX}{label}"

    def _inventory_label_from_row_id(self, row_id: str) -> str:
        """
        NAME
            _inventory_label_from_row_id - Extract the inventory label from a Treeview row id.
        """
        if not row_id.startswith(INVENTORY_ROW_PREFIX):
            return TEXT_EMPTY
        return row_id[len(INVENTORY_ROW_PREFIX):]

    def _is_xbox_controller_entry(self, entry: Dict[str, object]) -> bool:
        """
        NAME
            _is_xbox_controller_entry - Return true for USB xbox controller entries.
        """
        interface = str(entry.get(KEY_INTERFACE) or entry.get(KEY_INTERFACE_LEGACY) or TEXT_EMPTY).strip()
        controller_type = str(entry.get(KEY_TYPE, TEXT_EMPTY)).strip()
        return interface.upper() == DETAIL_INTERFACE_USB and controller_type == profile_consts.TYPE_XBOX_CONTROLLER

    def _is_topology_capable_inventory_entry(self, entry: Dict[str, object]) -> bool:
        """
        NAME
            _is_topology_capable_inventory_entry - Return true for CAN/DIO entries that can appear on the canvas.
        """
        return self._is_can_device_entry(entry) or self._is_dio_device_entry(entry)

    def _inventory_details_node(self, label: str) -> Optional[Node]:
        """
        NAME
            _inventory_details_node - Build a details-only Node view for one inventory label.
        """
        entry = self._inventory_entry_for_label(label)
        if not isinstance(entry, dict):
            return None
        interface = str(entry.get(KEY_INTERFACE) or entry.get(KEY_INTERFACE_LEGACY) or TEXT_EMPTY).strip()
        device_type = str(entry.get(KEY_TYPE, TEXT_EMPTY)).strip()
        model = str(entry.get(KEY_MODEL, TEXT_EMPTY)).strip()
        dio_value = entry.get(KEY_ID)
        node_interface = interface or INTERFACE_CAN
        node_can_id = CAN_ID_DIAGRAM_DEFAULT
        node_dio = None
        if node_interface.upper() == INTERFACE_DIO:
            node_interface = INTERFACE_DIO
            node_dio = int(dio_value) if isinstance(dio_value, int) else None
        elif node_interface.upper() == DETAIL_INTERFACE_USB:
            node_interface = DETAIL_INTERFACE_USB
        else:
            node_interface = INTERFACE_CAN
            node_can_id = int(dio_value) if isinstance(dio_value, int) else CAN_ID_DIAGRAM_DEFAULT
        return Node(
            key=CAN_ID_DIAGRAM_DEFAULT,
            category=GENERIC_CATEGORY,
            label=str(entry.get(KEY_LABEL, TEXT_EMPTY)).strip(),
            can_id=node_can_id,
            interface=node_interface,
            vendor=TEXT_EMPTY,
            device_type=device_type,
            motor=model,
            dio=node_dio,
            invert=bool(entry.get(KEY_INVERT)) if isinstance(entry.get(KEY_INVERT), bool) else None,
            scale=1.0,
            tags=self._normalize_tags(entry.get(KEY_TAGS, [])),
        )

    def _clear_node_details_fields(self) -> None:
        """
        NAME
            _clear_node_details_fields - Reset node detail values in place.
        """
        for key in self.detail_vars:
            self.detail_vars[key].set("--")

    def _clear_callout_details_fields(self) -> None:
        """
        NAME
            _clear_callout_details_fields - Reset callout detail values in place.
        """
        self._callout_scale_var.set("--")
        for key in self._callout_debug_vars:
            self._callout_debug_vars[key].set("--")

    def _update_callout_details(self, callout: Node) -> None:
        """
        NAME
            _update_callout_details - Refresh callout debug fields.
        """
        self._callout_scale_var.set(f"{callout.scale:.2f}")
        self._callout_debug_vars["target_type"].set(callout.callout_target_type or "--")
        self._callout_debug_vars["target_key"].set(
            "--" if callout.callout_target_node_key is None else str(callout.callout_target_node_key)
        )
        self._callout_debug_vars["target_label"].set(callout.callout_target_label or "--")
        self._callout_debug_vars["target_category"].set(callout.callout_target_category or "--")
        self._callout_debug_vars["target_id"].set(
            "--" if callout.callout_target_id is None else str(callout.callout_target_id)
        )
        self._callout_debug_vars["target_bus"].set(str(callout.callout_target_bus))
        exists = False
        if callout.callout_target_type == "node" and callout.callout_target_node_key is not None:
            exists = any(
                n.key == callout.callout_target_node_key for n in self._device_nodes()
            )
        self._callout_debug_vars["target_exists"].set("yes" if exists else "no")

    def _terminator_count(self, nodes: Optional[List[Node]] = None) -> int:
        """
        NAME
            _terminator_count - Count nodes marked as CAN bus terminators.
        """
        targets = nodes if nodes is not None else self._profile_device_nodes()
        return sum(1 for n in targets if n.terminator is True)

    def _refresh_terminator_status(self) -> None:
        """
        NAME
            _refresh_terminator_status - Update the terminator count warning text.
        """
        count = self._terminator_count()
        if count == 2:
            text = "Terminator nodes: 2 (ok)"
            color = "#1a7f37"
        else:
            text = f"Terminator nodes: {count} (expected 2)"
            color = "#b42318"
        self._terminator_status_var.set(text)
        if hasattr(self, "_terminator_status_label"):
            try:
                self._terminator_status_label.configure(foreground=color)
            except tk.TclError:
                pass

    def _confirm_terminators(self, nodes: Optional[List[Node]] = None) -> bool:
        """
        NAME
            _confirm_terminators - Warn when terminator count is not two.
        """
        count = self._terminator_count(nodes)
        if count == 2:
            return True
        return messagebox.askyesno(
            "Terminator Warning",
            f"Terminator nodes: {count} (expected 2).\n\nSave anyway?",
        )

    def _nudge_scale(self, delta: float) -> None:
        """
        NAME
            _nudge_scale - Adjust the selected node scale.
        """
        node = self._get_selected_node()
        if node is None:
            return
        node.scale = max(0.6, min(2.0, node.scale + delta))
        self._update_details_panel(node)
        self._redraw_canvas()

    def _preserve_canvas_view(self, action) -> None:
        """
        NAME
            _preserve_canvas_view - Run an action without shifting canvas view.
        """
        try:
            left = float(self.canvas.canvasx(0))
        except Exception:
            left = None
        try:
            top = float(self.canvas.canvasy(0))
        except Exception:
            top = None
        action()
        try:
            self.update_idletasks()
        except Exception:
            pass
        self._preserve_left_after_configure = left
        self._preserve_top_after_configure = top
        if left is not None:
            self._set_canvas_xview_left(left)
        if top is not None:
            self._set_canvas_yview_top(top)

    def _gui_debug_enabled(self) -> bool:
        """
        NAME
            _gui_debug_enabled - Return True when GUI interaction logging is enabled.
        """
        raw = str(os.environ.get(GUI_INTERACTION_DEBUG_ENV, TEXT_EMPTY)).strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _gui_debug_log(self, event_name: str, **fields: object) -> None:
        """
        NAME
            _gui_debug_log - Append one GUI interaction trace line.
        """
        if not self._gui_debug_enabled():
            return
        try:
            left = float(self.canvas.canvasx(0))
        except Exception:
            left = float("nan")
        try:
            top = float(self.canvas.canvasy(0))
        except Exception:
            top = float("nan")
        try:
            xview = tuple(self.canvas.xview())
        except Exception:
            xview = ()
        try:
            yview = tuple(self.canvas.yview())
        except Exception:
            yview = ()
        try:
            scrollregion = str(self.canvas.cget("scrollregion"))
        except Exception:
            scrollregion = TEXT_EMPTY
        parts = [
            f"event={event_name}",
            f"redraw={self._debug_redraw_count}",
            f"left={left:.3f}",
            f"top={top:.3f}",
            f"xview={xview}",
            f"yview={yview}",
            f"scrollregion={scrollregion!r}",
            f"canvas_w={self.canvas.winfo_width()}",
            f"canvas_h={self.canvas.winfo_height()}",
        ]
        for key, value in fields.items():
            parts.append(f"{key}={value!r}")
        log_dir = Path(__file__).resolve().parent / GUI_INTERACTION_DEBUG_LOGDIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / GUI_INTERACTION_DEBUG_LOG
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(" ".join(parts) + "\n")

    def _has_neighbor_metadata(self) -> bool:
        """
        NAME
            _has_neighbor_metadata - Return True when saved neighbor data exists.
        """
        return bool(self._neighbor_links or self._neighbor_ports)

    def _refresh_neighbor_status(self) -> None:
        """
        NAME
            _refresh_neighbor_status - Update neighbor freshness indicator.
        """
        if not self._has_neighbor_metadata():
            status = NEIGHBOR_STATUS_NOT_POPULATED
        elif self._neighbors_dirty:
            status = NEIGHBOR_STATUS_STALE
        else:
            status = NEIGHBOR_STATUS_CURRENT
        self._neighbor_status_var.set(status)

    def _mark_neighbors_stale(self) -> None:
        """
        NAME
            _mark_neighbors_stale - Mark generated neighbor metadata as stale.
        """
        if self._has_neighbor_metadata():
            self._neighbors_dirty = True
        self._refresh_neighbor_status()

    def _mark_neighbors_current(self) -> None:
        """
        NAME
            _mark_neighbors_current - Mark neighbor metadata as matching layout.
        """
        self._neighbors_dirty = False
        self._refresh_neighbor_status()

    def _nudge_callout_scale(self, delta: float) -> None:
        """
        NAME
            _nudge_callout_scale - Adjust the selected callout scale.
        """
        node = self._get_selected_node()
        if node is None or node.node_type != "callout":
            return
        node.scale = max(0.6, min(2.0, node.scale + delta))
        self._dirty = True
        self._callout_scale_var.set(f"{node.scale:.2f}")
        self._redraw_canvas()

    def _push_undo(self) -> None:
        """
        NAME
            _push_undo - Save a snapshot for undo.
        """
        self._dirty = True
        snapshot = {
            "nodes": [
                {
                    "key": n.key,
                    "node_type": n.node_type,
                    "category": n.category,
                    "label": n.label,
                    "can_id": n.can_id,
                    KEY_UNDO_INTERFACE: n.interface,
                    "vendor": n.vendor,
                    "device_type": n.device_type,
                    "motor": n.motor,
                    "limits": n.limits,
                    KEY_UNDO_DIO: n.dio,
                    KEY_UNDO_INVERT: n.invert,
                    "terminator": n.terminator,
                    "x": n.x,
                    "row": n.row,
                    "bus_index": n.bus_index,
                    "scale": n.scale,
                    "callout_text": n.callout_text,
                    "callout_target_type": n.callout_target_type,
                    "callout_target_bus": n.callout_target_bus,
                    "callout_target_node_key": n.callout_target_node_key,
                    "callout_y": self._node_center_y_unscaled(n)
                    if n.node_type == "callout"
                    else n.callout_y,
                    "free_y": n.free_y,
                    "profile_visible": getattr(n, "profile_visible", True),
                }
                for n in self._nodes
            ],
            "ethernet_links": list(self._ethernet_links),
            "can_bus_links": list(self._can_bus_links),
            "cannect_device_links": list(self._cannect_device_links),
            KEY_UNDO_ATTACHMENT_LINKS: list(self._attachment_links),
            KEY_UNDO_DIO_LINKS: list(self._dio_wiring_links),
            KEY_UNDO_POWER_LINKS: list(self._power_links),
            KEY_UNDO_NEIGHBOR_LINKS: list(self._neighbor_links),
            KEY_UNDO_NEIGHBOR_PORTS: list(self._neighbor_ports),
            "neighbors_dirty": self._neighbors_dirty,
            "bus_offsets": list(self._bus_offsets),
            "bus_lefts": list(self._bus_lefts),
            "bus_rights": list(self._bus_rights),
            "layout_width": self._layout_width,
            "pan_y": self._pan_y,
            "zoom": self._zoom,
            "next_key": self._next_key,
        }
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._undo_limit:
            self._undo_stack.pop(0)

    def _undo_last(self) -> None:
        """
        NAME
            _undo_last - Restore the last snapshot.
        """
        if not self._undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        snap = self._undo_stack.pop()
        self._nodes = [
            Node(
                key=n["key"],
                category=n["category"],
                label=n["label"],
                can_id=n["can_id"],
                node_type=n.get("node_type", "device"),
                interface=n.get(KEY_UNDO_INTERFACE, INTERFACE_CAN),
                vendor=n.get("vendor", ""),
                device_type=n.get("device_type", ""),
                motor=n.get("motor", ""),
                limits=n.get("limits"),
                dio=n.get(KEY_UNDO_DIO),
                invert=n.get(KEY_UNDO_INVERT),
                terminator=n.get("terminator"),
                x=n.get("x", 0.0),
                row=n.get("row", 0),
                bus_index=n.get("bus_index", 0),
                scale=n.get("scale", 1.0),
                callout_text=n.get("callout_text", ""),
                callout_target_type=n.get("callout_target_type", "node"),
                callout_target_bus=n.get("callout_target_bus", 0),
                callout_target_node_key=n.get("callout_target_node_key"),
                callout_y=n.get("callout_y", 0.0),
                free_y=n.get("free_y"),
                profile_visible=bool(n.get("profile_visible", True)),
            )
            for n in snap["nodes"]
        ]
        self._ethernet_links = [
            (int(a), int(b))
            for a, b in snap.get("ethernet_links", [])
            if isinstance(a, int) and isinstance(b, int)
        ]
        if ENABLE_CANNECT_BUS_LINKS:
            self._can_bus_links = [
                {"node": int(link.get("node")), "bus": int(link.get("bus")), "port": int(link.get("port", 1))}
                for link in snap.get("can_bus_links", [])
                if isinstance(link, dict)
                and isinstance(link.get("node"), int)
                and isinstance(link.get("bus"), int)
            ]
        else:
            self._can_bus_links = []
        self._cannect_device_links = [
            {
                "node": int(link.get("node")),
                "device": int(link.get("device")),
                "port": int(link.get("port", 1)),
            }
            for link in snap.get("cannect_device_links", [])
            if isinstance(link, dict)
            and isinstance(link.get("node"), int)
            and isinstance(link.get("device"), int)
        ]
        self._attachment_links = [
            {
                KEY_LINK_DEVICE: int(link.get(KEY_LINK_DEVICE)),
                KEY_LINK_ATTACHMENT: int(link.get(KEY_LINK_ATTACHMENT)),
            }
            for link in snap.get(KEY_UNDO_ATTACHMENT_LINKS, [])
            if isinstance(link, dict)
            and isinstance(link.get(KEY_LINK_DEVICE), int)
            and isinstance(link.get(KEY_LINK_ATTACHMENT), int)
        ]
        self._dio_wiring_links = [
            {
                KEY_LINK_ROBORIO: int(link.get(KEY_LINK_ROBORIO)),
                KEY_LINK_DEVICE: int(link.get(KEY_LINK_DEVICE)),
            }
            for link in snap.get(KEY_UNDO_DIO_LINKS, [])
            if isinstance(link, dict)
            and isinstance(link.get(KEY_LINK_ROBORIO), int)
            and isinstance(link.get(KEY_LINK_DEVICE), int)
        ]
        self._power_links = [
            {
                KEY_LINK_A: int(link.get(KEY_LINK_A)),
                KEY_LINK_B: int(link.get(KEY_LINK_B)),
            }
            for link in snap.get(KEY_UNDO_POWER_LINKS, [])
            if isinstance(link, dict)
            and isinstance(link.get(KEY_LINK_A), int)
            and isinstance(link.get(KEY_LINK_B), int)
        ]
        self._neighbor_links = self._normalize_neighbor_links(snap.get(KEY_UNDO_NEIGHBOR_LINKS, []))
        self._neighbor_ports = self._normalize_neighbor_ports(snap.get(KEY_UNDO_NEIGHBOR_PORTS, []))
        self._neighbors_dirty = bool(snap.get("neighbors_dirty", False))
        self._bus_offsets = snap["bus_offsets"]
        self._bus_lefts = snap.get("bus_lefts", [])
        self._bus_rights = snap.get("bus_rights", [])
        self._layout_width = snap["layout_width"]
        self._pan_y = snap["pan_y"]
        self._zoom = snap["zoom"]
        self._next_key = snap["next_key"]
        
        self._refresh_list()
        self._update_details_panel(None)
        self._redraw_canvas()
        self._refresh_neighbor_status()

    def _new_diagram(self) -> None:
        """
        NAME
            _new_diagram - Reset the editor to a blank diagram.
        """
        if not self._confirm_discard():
            return
        self._nodes.clear()
        self._ethernet_links = []
        self._can_bus_links = []
        self._cannect_device_links = []
        self._attachment_links = []
        self._dio_wiring_links = []
        self._power_links = []
        self._neighbor_links = []
        self._neighbor_ports = []
        self._neighbors_dirty = False
        self._next_key = 1
        self._selected_key = None
        self._clear_node_details_fields()
        self._clear_callout_details_fields()
        self._layout_width = 0.0
        self._pan_y = 0.0
        self._zoom = 1.0
        self._zoom_label_var.set("Zoom: 100%")
        self._bus_offsets = [0.0]
        self._bus_lefts = []
        self._bus_rights = []
        self._bus_connectors = []
        self._last_base_y = None
        self._details_layout_shift = False
        self._dirty = False
        self._root_extras = {}
        self._refresh_neighbor_status()
        self._refresh_list()
        self._update_details_panel(None)
        self._redraw_canvas()

    def _open_profile(self) -> None:
        """
        NAME
            _open_profile - Load nodes from an existing bringup profile file.
        """
        path = filedialog.askopenfilename(
            title="Open Bringup Profiles JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._load_profile_from_path(path, ask_profile=True, confirm_discard=True)

    def _backup_profiles_file(self, path: Path) -> None:
        """
        NAME
            _backup_profiles_file - Write a timestamped backup copy.
        """
        if not path.exists():
            return
        stamp = timestamp_version()
        backup = path.with_name(f"{path.stem}.bak_{stamp}{path.suffix}")
        try:
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            return

    def _load_profiles_payload(self, path: Path) -> Optional[Dict[str, object]]:
        """
        NAME
            _load_profiles_payload - Load bringup_system.json with repair prompts.
        """
        store_payload = None
        if ConfigSchemaStore is not None and repo_root is not None:
            default_path = self._default_profiles_path()
            if path == default_path:
                store = ConfigSchemaStore()
                try:
                    store.load(repo_root())
                    store_payload = store.root_payload()
                except Exception:
                    store_payload = None
        if store_payload is not None:
            data = store_payload
            # ConfigSchemaStore may still synthesize an empty profiles payload from a
            # legacy canonical path that is absent in this repo layout. If that
            # happens, fall back to the actual requested file instead of prompting
            # for repair on valid deploy-backed configs.
            data_version = data.get("data_version")
            default_profile = data.get("default_profile")
            if (
                path.exists()
                and (
                    not isinstance(data_version, str)
                    or not data_version.strip()
                    or not isinstance(default_profile, str)
                    or not default_profile.strip()
                )
            ):
                try:
                    data = self._load_config_payload(path)
                except Exception as exc:
                    messagebox.showerror("Error", f"Failed to open file: {exc}")
                    return None
        else:
            try:
                data = self._load_config_payload(path)
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to open file: {exc}")
                return None
        if not isinstance(data, dict):
            messagebox.showerror("Error", "Profiles JSON root must be an object.")
            return None
        schema_version = data.get("schema_version")
        if schema_version is not None and schema_version not in self._accepted_schema_versions():
            proceed = messagebox.askyesno(
                "Schema Mismatch",
                "Profile schema_version mismatch. Open anyway to repair?",
            )
            if not proceed:
                return None
        data_version = data.get("data_version")
        if not isinstance(data_version, str) or not data_version.strip():
            proceed = messagebox.askyesno(
                "Version Missing",
                "Profile data_version missing or empty. Open anyway to repair?",
            )
            if not proceed:
                return None
        data_hash = data.get("data_hash")
        if not isinstance(data_hash, str) or not data_hash.strip():
            proceed = messagebox.askyesno(
                "Hash Missing",
                "Profile data_hash missing or empty. Open anyway to repair?",
            )
            if not proceed:
                return None
        else:
            computed_hash = self._compute_data_hash(data)
            if data_hash != computed_hash:
                proceed = messagebox.askyesno(
                    "Hash Mismatch",
                    "Profile data_hash mismatch. Open anyway to repair?",
                )
                if not proceed:
                    return None
        self._stash_root_extras(data)
        self._load_device_registry(data)
        return data

    def _write_profiles_payload(
        self,
        path: Path,
        data: Dict[str, object],
        include_extras: bool = True,
    ) -> bool:
        """
        NAME
            _write_profiles_payload - Write bringup_system.json with fresh hash.
        """
        if include_extras:
            for key, value in self._root_extras.items():
                if key == "bridgeConfig":
                    # Always persist the latest bridgeConfig (per-profile groups/selectedDevice).
                    data[key] = value
                    continue
                if key not in data:
                    data[key] = value
        self._apply_node_updates_to_registry()
        if self._device_registry_list:
            data["devices"] = self._device_registry_list
        try:
            if ConfigRepository is not None:
                repository = ConfigRepository()
                session = repository.session_for_payload(path, data)
                target = path.resolve()
                canonical = repository.canonical_path().resolve()
                deploy = repository.deploy_path().resolve()
                if target == canonical or target == deploy:
                    repository.sync(session)
                    data.clear()
                    data.update(session.to_payload())
                else:
                    repository.save(session, path=path)
                    data.clear()
                    data.update(session.to_payload())
            else:
                data["schema_version"] = self._expected_schema_version()
                data["data_version"] = timestamp_version()
                data["data_hash"] = self._compute_data_hash(data)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to write {path}: {exc}")
            return False
        return True

    def _import_profile(self) -> None:
        """
        NAME
            _import_profile - Import a profile from an external JSON file.
        """
        src = filedialog.askopenfilename(
            title="Import Bringup Profile",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not src:
            return
        src_path = Path(src)
        incoming = self._load_profiles_payload(src_path)
        if incoming is None:
            return
        incoming_profiles = incoming.get("profiles")
        if not isinstance(incoming_profiles, dict) or not incoming_profiles:
            messagebox.showerror("Error", "No profiles found in import file.")
            return
        names = sorted(incoming_profiles.keys())
        name = self._choose_profile_name(names, incoming.get("default_profile"))
        if not name:
            return
        profile = incoming_profiles.get(name)
        if not isinstance(profile, dict):
            messagebox.showerror("Error", "Selected profile is not an object.")
            return
        incoming_diagram = None
        incoming_topology = None
        diagram = incoming.get("diagram")
        if isinstance(diagram, dict):
            diagram_profiles = diagram.get("profiles")
            if isinstance(diagram_profiles, dict):
                incoming_diagram = diagram_profiles.get(name)
        topology = incoming.get(KEY_TOPOLOGY)
        if isinstance(topology, dict):
            topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
            if isinstance(topology_profiles, dict):
                incoming_topology = topology_profiles.get(name)

        dest_path = self._canonical_profiles_path()
        dest = self._load_profiles_payload(dest_path) if dest_path.exists() else {
            "default_profile": name,
            "profiles": {},
            KEY_TOPOLOGY: {
                KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {},
            },
        }
        if dest is None:
            return
        profiles = dest.get("profiles")
        if not isinstance(profiles, dict):
            profiles = {}

        target_name = name
        if target_name in profiles:
            choice = messagebox.askyesnocancel(
                "Profile Exists",
                f"Profile '{target_name}' exists. Replace it?",
            )
            if choice is None:
                return
            if choice is False:
                new_name = simpledialog.askstring("Rename", "New profile name:")
                if not new_name:
                    return
                if new_name in profiles:
                    messagebox.showerror("Error", "That profile name already exists.")
                    return
                target_name = new_name

        topology_entry = None
        if incoming_topology is not None:
            topology_entry = incoming_topology
        elif incoming_diagram is not None:
            topology_entry = self._topology_entry_from_legacy_diagram(incoming_diagram)

        self._backup_profiles_file(dest_path)
        if upsert_profile is not None:
            upsert_profile(
                dest,
                target_name,
                profile,
                topology_entry=topology_entry,
                diagram_entry=incoming_diagram if isinstance(incoming_diagram, dict) else None,
                set_default_if_missing=True,
            )
        else:
            dest["profiles"] = profiles
            profiles[target_name] = profile
            topology = dest.get(KEY_TOPOLOGY)
            if not isinstance(topology, dict):
                topology = {
                    KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                    KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                    KEY_TOPOLOGY_PROFILES: {},
                }
            topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
            if not isinstance(topology_profiles, dict):
                topology_profiles = {}
            if topology_entry is not None:
                topology_profiles[target_name] = topology_entry
            dest[KEY_TOPOLOGY] = {
                KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: topology_profiles,
            }
            if dest.get("default_profile") is None:
                dest["default_profile"] = target_name
        if not self._write_profiles_payload(dest_path, dest, include_extras=True):
            return
        self._refresh_profile_choices(keep_selection=False)
        if messagebox.askyesno("Imported", "Import complete. Load the imported profile now?"):
            self._load_profile_from_path(str(dest_path), ask_profile=False, confirm_discard=True, selected_name=target_name)

    def _export_profile(self) -> None:
        """
        NAME
            _export_profile - Export a single profile to an external JSON file.
        """
        src_path = self._canonical_profiles_path()
        src = self._load_profiles_payload(src_path)
        if src is None:
            return
        profiles = src.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            messagebox.showerror("Error", "No profiles found to export.")
            return
        names = sorted(profiles.keys())
        name = self._choose_profile_name(names, src.get("default_profile"))
        if not name:
            return
        profile = profiles.get(name)
        if not isinstance(profile, dict):
            messagebox.showerror("Error", "Selected profile is not an object.")
            return
        diag = None
        topology_entry = None
        diagram = src.get("diagram")
        if isinstance(diagram, dict):
            diagram_profiles = diagram.get("profiles")
            if isinstance(diagram_profiles, dict):
                diag = diagram_profiles.get(name)
        topology = src.get(KEY_TOPOLOGY)
        if isinstance(topology, dict):
            topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
            if isinstance(topology_profiles, dict):
                topology_entry = topology_profiles.get(name)

        path = filedialog.asksaveasfilename(
            title="Export Profile",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        payload: Dict[str, object] = {
            "default_profile": name,
            "profiles": {name: profile},
        }
        if topology_entry is not None:
            payload[KEY_TOPOLOGY] = {
                KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {name: topology_entry},
            }
        elif diag is not None:
            payload[KEY_TOPOLOGY] = {
                KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {name: self._topology_entry_from_legacy_diagram(diag)},
            }
        if not self._write_profiles_payload(Path(path), payload, include_extras=False):
            return
        messagebox.showinfo("Exported", f"Wrote {path}")

    def _rename_profile(self) -> None:
        """
        NAME
            _rename_profile - Rename one profile in the canonical file.
        """
        path = self._canonical_profiles_path()
        data = self._load_profiles_payload(path)
        if data is None:
            return
        profiles = data.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            messagebox.showerror("Error", "No profiles available to rename.")
            return
        default_name = data.get("default_profile")
        names = sorted(profiles.keys())
        old_name = self._choose_profile_name(names, default_name if isinstance(default_name, str) else None)
        if not old_name:
            return
        new_name = simpledialog.askstring("Rename Profile", "New profile name:")
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name:
            messagebox.showerror("Error", "Profile name is required.")
            return
        if new_name in profiles:
            messagebox.showerror("Error", "That profile name already exists.")
            return
        self._backup_profiles_file(path)
        if rename_profile is not None:
            rename_profile(data, old_name, new_name)
        else:
            profiles[new_name] = profiles.pop(old_name)
            diagram = data.get("diagram")
            if isinstance(diagram, dict):
                diagram_profiles = diagram.get("profiles")
                if isinstance(diagram_profiles, dict) and old_name in diagram_profiles:
                    diagram_profiles[new_name] = diagram_profiles.pop(old_name)
                    data["diagram"] = {"profiles": diagram_profiles}
            topology = data.get(KEY_TOPOLOGY)
            if isinstance(topology, dict):
                topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
                if isinstance(topology_profiles, dict) and old_name in topology_profiles:
                    topology_profiles[new_name] = topology_profiles.pop(old_name)
                    data[KEY_TOPOLOGY] = topology
            data["profiles"] = profiles
        if not self._write_profiles_payload(path, data, include_extras=True):
            return
        if self._profile_name == old_name:
            self._profile_name = new_name
            self.entry_profile.set(new_name)
        self._refresh_profile_choices(keep_selection=False)
        messagebox.showinfo("Renamed", f"Renamed '{old_name}' to '{new_name}'.")

    def _delete_profile(self) -> None:
        """
        NAME
            _delete_profile - Delete a non-default profile in the canonical file.
        """
        path = self._canonical_profiles_path()
        data = self._load_profiles_payload(path)
        if data is None:
            return
        profiles = data.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            messagebox.showerror("Error", "No profiles available to delete.")
            return
        default_name = data.get("default_profile")
        names = sorted(profiles.keys())
        if len(names) <= 1:
            messagebox.showerror("Error", "Cannot delete the last remaining profile.")
            return
        target = self._choose_profile_name(names, default_name if isinstance(default_name, str) else None)
        if not target:
            return
        if isinstance(default_name, str) and target == default_name:
            messagebox.showerror("Error", "Default profile cannot be deleted.")
            return
        if not messagebox.askyesno("Delete Profile", f"Delete profile '{target}'?"):
            return
        self._backup_profiles_file(path)
        if delete_profile is not None:
            delete_profile(data, target)
        else:
            profiles.pop(target, None)
            diagram = data.get("diagram")
            if isinstance(diagram, dict):
                diagram_profiles = diagram.get("profiles")
                if isinstance(diagram_profiles, dict):
                    diagram_profiles.pop(target, None)
                    data["diagram"] = {"profiles": diagram_profiles}
            topology = data.get(KEY_TOPOLOGY)
            if isinstance(topology, dict):
                topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
                if isinstance(topology_profiles, dict):
                    topology_profiles.pop(target, None)
                    data[KEY_TOPOLOGY] = topology
            data["profiles"] = profiles
        if not self._write_profiles_payload(path, data, include_extras=True):
            return
        if self._profile_name == target:
            new_active = default_name if isinstance(default_name, str) and default_name in profiles else names[0]
            self._load_profile_from_path(str(path), ask_profile=False, confirm_discard=True, selected_name=new_active)
        self._refresh_profile_choices(keep_selection=False)
        messagebox.showinfo("Deleted", f"Deleted profile '{target}'.")

    def _reload_canonical_profile(self) -> None:
        """
        NAME
            _reload_canonical_profile - Reload the canonical profiles file.
        """
        path = self._default_profiles_path()
        if not path.exists():
            messagebox.showerror("Missing", f"No profiles file found at {path}.")
            return
        self._load_profile_from_path(
            str(path),
            ask_profile=False,
            confirm_discard=True,
        )

    def _blank_profile_payload(self) -> Dict[str, object]:
        """
        NAME
            _blank_profile_payload - Build a blank profile object.
        """
        if blank_profile_payload is not None:
            return blank_profile_payload()
        return {KEY_DEVICES: []}

    def _blank_topology_entry(self) -> Dict[str, object]:
        """
        NAME
            _blank_topology_entry - Build a blank topology entry for a new profile.
        """
        return {
            KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
            KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
            KEY_TOPOLOGY_NODES: [],
            KEY_TOPOLOGY_EDGES: [],
            KEY_TOPOLOGY_VIEW: {
                "busOffsets": [0.0],
                "busCount": 1,
                "busSpacing": self._bus_spacing,
                "busLefts": [],
                "busRights": [],
                "busConnectors": [],
                KEY_DIAGRAM_BUS_CONNECTOR_SIDES: [],
                "panY": 0.0,
                "zoom": 1.0,
                KEY_DIAGRAM_ETHERNET_LINKS: [],
                "canLinks": [],
                "deviceLinks": [],
                KEY_TOPOLOGY_FILTERS: sorted(self._active_connection_filters()),
                "callouts": [],
            },
        }

    def _new_blank_profile(self) -> None:
        """
        NAME
            _new_blank_profile - Create a new blank profile in the current config file.
        """
        target_path = Path(self._profile_source_path) if self._profile_source_path else self._default_profiles_path()
        if not target_path.exists():
            messagebox.showerror("Missing", f"No profiles file found at {target_path}.")
            return
        new_name = simpledialog.askstring("New Blank Profile", "Profile name:")
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            messagebox.showerror("Error", "Profile name is required.")
            return
        data = self._load_profiles_payload(target_path)
        if data is None:
            return
        profiles = data.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            profiles = {}
        if new_name in profiles:
            messagebox.showerror("Error", "That profile name already exists.")
            return
        if not self._confirm_discard():
            return
        self._backup_profiles_file(target_path)
        if create_blank_profile is not None:
            create_blank_profile(
                data,
                new_name,
            )
        else:
            topology = data.get(KEY_TOPOLOGY)
            if not isinstance(topology, dict):
                topology = {
                    KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                    KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                    KEY_TOPOLOGY_PROFILES: {},
                }
            topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
            if not isinstance(topology_profiles, dict):
                topology_profiles = {}
            profiles[new_name] = self._blank_profile_payload()
            topology_profiles[new_name] = self._blank_topology_entry()
            data[KEY_PROFILES] = profiles
            data[KEY_TOPOLOGY] = {
                KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: topology_profiles,
            }
        if not self._write_profiles_payload(target_path, data, include_extras=True):
            return
        self._refresh_profile_choices(keep_selection=False)
        self._load_profile_from_path(
            str(target_path),
            ask_profile=False,
            confirm_discard=False,
            selected_name=new_name,
        )
        messagebox.showinfo("Created", f"Created blank profile '{new_name}'.")

    def _load_profile_from_path(
        self,
        path: str,
        ask_profile: bool,
        confirm_discard: bool,
        selected_name: Optional[str] = None,
    ) -> None:
        """
        NAME
            _load_profile_from_path - Load a profile JSON and populate nodes.

        PARAMETERS
            path: Path to bringup_system.json.
            ask_profile: Whether to prompt for which profile to load.
            confirm_discard: Whether to prompt before discarding current nodes.
            selected_name: Optional profile name to load.
        """
        try:
            data = self._load_config_payload(Path(path))
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open file: {exc}")
            return
        self._stash_root_extras(data)
        self._load_device_registry(data)
        profiles = data.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            messagebox.showerror("Error", "No profiles found in JSON.")
            return
        names = sorted(profiles.keys())
        default_name = data.get("default_profile")
        default_profile_name = default_name if isinstance(default_name, str) else None
        if selected_name:
            if selected_name not in profiles:
                messagebox.showerror("Error", f"Profile '{selected_name}' not found in JSON.")
                return
            name = selected_name
        elif ask_profile:
            name = self._choose_profile_name(names, default_profile_name)
            if not name:
                return
        else:
            name = default_profile_name if default_profile_name in profiles else names[0]
        profile = profiles.get(name)
        if not isinstance(profile, dict):
            messagebox.showerror("Error", "Profile data is not a JSON object.")
            return
        if confirm_discard and not self._confirm_discard():
            return
        self._nodes = self._nodes_from_profile(profile)
        self._sync_non_topology_profile_labels(profile)
        self._pending_global_device_deletions = set()
        self._selected_inventory_label = None
        self._next_callout = 1
        self._callout_scale_var.set("--")
        self._layout_width = 0.0
        self._pan_y = 0.0
        self._zoom = 1.0
        self._zoom_label_var.set("Zoom: 100%")
        self._bus_offsets = [0.0]
        self._bus_lefts = []
        self._bus_rights = []
        self._last_base_y = None
        self._details_layout_shift = False
        self._ethernet_links = []
        self._can_bus_links = []
        self._cannect_device_links = []
        self._attachment_links = []
        self._power_links = []
        self._neighbor_links = []
        self._neighbor_ports = []
        self._neighbors_dirty = False
        self._dio_wiring_links = []
        topology_applied = False
        diagram_profiles = {}
        topology_profiles = {}
        topology_root = data.get(KEY_TOPOLOGY)
        if isinstance(topology_root, dict):
            topology_profiles = topology_root.get(KEY_TOPOLOGY_PROFILES) or {}
        diagram = data.get("diagram")
        if isinstance(diagram, dict):
            diagram_profiles = diagram.get("profiles") or {}
        if isinstance(topology_profiles, dict):
            topology_entry = topology_profiles.get(name)
            if isinstance(topology_entry, dict) and self._topology_has_saved_content(topology_entry):
                self._apply_topology_snapshot(topology_entry)
                topology_applied = True
                self._zoom_label_var.set(f"Zoom: {int(self._zoom * 100)}%")
                if not self._profile_device_nodes():
                    self._nodes = self._nodes_from_profile(profile)
                    self._ethernet_links = []
                    self._can_bus_links = []
                    self._cannect_device_links = []
                    self._attachment_links = []
                    self._dio_wiring_links = []
                    self._power_links = []
                    topology_applied = False
        if not topology_applied and isinstance(diagram_profiles, dict):
            diag = diagram_profiles.get(name)
            if isinstance(diag, dict) and self._diagram_has_saved_content(diag):
                self._apply_diagram_snapshot(diag)
                topology_applied = True
                self._zoom_label_var.set(f"Zoom: {int(self._zoom * 100)}%")
                if not self._profile_device_nodes():
                    self._nodes = self._nodes_from_profile(profile)
                    self._ethernet_links = []
                    self._can_bus_links = []
                    self._cannect_device_links = []
                    self._attachment_links = []
                    self._dio_wiring_links = []
                    self._power_links = []
                    topology_applied = False
        if not topology_applied:
            self._rebuild_attachment_links_from_registry()
            self._ensure_dio_wiring_links()
        self._next_key = 1 + max([n.key for n in self._nodes], default=0)
        self._profile_name = name
        self._default_profile_name = default_profile_name
        self._profile_source_path = path
        self._set_profile_names(names)
        self._suppress_profile_select = True
        try:
            self.entry_profile.set(name)
        except tk.TclError:
            self.entry_profile.delete(0, tk.END)
            self.entry_profile.insert(0, name)
        self._suppress_profile_select = False
        if hasattr(self, "profile_combo"):
            try:
                values = self.profile_combo["values"]
            except tk.TclError:
                values = []
            if name in values:
                self._profile_pick_var.set(name)
        self._refresh_list()
        self._update_details_panel(None)
        if not topology_applied:
            self._layout_even()
        else:
            max_node_x = max((n.x for n in self._nodes), default=0.0)
            self._layout_width = max(self._layout_width, max_node_x + 200)
            self._redraw_canvas()
        try:
            self.state("zoomed")
        except tk.TclError:
            pass
        self.update_idletasks()
        self._pending_fit_to_window = False
        if topology_applied:
            self._zoom_label_var.set(f"Zoom: {int(self._zoom * 100)}%")
            self._redraw_canvas()
        else:
            self._zoom = 1.0
            self._pan_y = 0.0
            self._zoom_label_var.set("Zoom: 100%")
            self._redraw_canvas()
        self._dirty = False
        self._refresh_default_checkbox()
        self._refresh_neighbor_status()
        self.update_idletasks()
        self._view_scrollregion_x_override = None
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)

    def _load_default_profile_if_present(self) -> None:
        """
        NAME
            _load_default_profile_if_present - Auto-load default profile on startup.

        DESCRIPTION
            Reads the canonical bringup_system.json and loads its
            default_profile into the diagram when available.
        """
        try:
            path = self._default_profiles_path()
            if path.exists():
                self._load_profile_from_path(
                    str(path),
                    ask_profile=False,
                    confirm_discard=False,
                )
        except Exception:
            return

    @staticmethod
    def _expected_schema_version() -> int:
        if profile_consts is not None and hasattr(profile_consts, "PROFILE_SCHEMA_VERSION"):
            return int(profile_consts.PROFILE_SCHEMA_VERSION)
        return PROFILE_SCHEMA_VERSION_FALLBACK

    @classmethod
    def _accepted_schema_versions(cls) -> Tuple[int, ...]:
        versions = [cls._expected_schema_version()]
        for value in PROFILE_SCHEMA_COMPATIBILITY_VERSIONS:
            if value not in versions:
                versions.append(value)
        return tuple(versions)

    @staticmethod
    def _compute_data_hash(payload: Dict[str, object]) -> str:
        """
        NAME
            _compute_data_hash - Compute a stable hash for profile payloads.
        """
        if compute_profiles_hash is not None:
            return compute_profiles_hash(payload)
        normalized = dict(payload)
        normalized["data_hash"] = ""
        blob = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    @staticmethod
    def _root_known_keys() -> set[str]:
        return {
            "schema_version",
            "data_version",
            "data_hash",
            "default_profile",
            "profiles",
            "diagram",
            KEY_TOPOLOGY,
            "devices",
        }

    @staticmethod
    def _diagram_has_saved_content(diagram: Dict[str, object]) -> bool:
        """
        NAME
            _diagram_has_saved_content - Check whether a diagram snapshot has layout data.

        DESCRIPTION
            Empty per-profile diagram objects are placeholders, not layouts.
            Treating them as applied suppresses the normal profile-driven
            topology build and can leave the editor blank.
        """
        for key in DIAGRAM_CONTENT_LIST_KEYS:
            value = diagram.get(key)
            if isinstance(value, list) and value:
                return True
        for key in DIAGRAM_CONTENT_SCALAR_KEYS:
            if key in diagram:
                return True
        return False

    @staticmethod
    def _topology_has_saved_content(topology_profile: Dict[str, object]) -> bool:
        """
        NAME
            _topology_has_saved_content - Check whether a topology entry has graph data.
        """
        for key in TOPOLOGY_CONTENT_LIST_KEYS:
            value = topology_profile.get(key)
            if isinstance(value, list) and value:
                return True
        return False

    def _stash_root_extras(self, payload: Dict[str, object]) -> None:
        """
        NAME
            _stash_root_extras - Preserve non-profile root keys (e.g., bridgeConfig).
        """
        known = self._root_known_keys()
        self._root_extras = {key: value for key, value in payload.items() if key not in known}

    def _load_device_registry(self, payload: Dict[str, object]) -> None:
        """
        NAME
            _load_device_registry - Cache device definitions from bringup_system.json.
        """
        devices = payload.get("devices")
        if not isinstance(devices, list):
            self._device_registry_list = []
            self._device_registry = {}
            return
        registry_list: List[Dict[str, object]] = []
        registry_map: Dict[str, Dict[str, object]] = {}
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get("label", "")).strip()
            if not label:
                continue
            registry_list.append(entry)
            registry_map[label] = entry
        self._device_registry_list = registry_list
        self._device_registry = registry_map

    def _default_profiles_path(self) -> Path:
        canonical = self._canonical_profiles_path()
        if canonical.exists():
            return canonical
        # LEGACY (remove after v3 unified file adoption).
        legacy = Path(__file__).resolve().parents[2] / "data" / "bringup_profiles.json"
        if legacy.exists():
            return legacy
        return canonical

    @staticmethod
    def _canonical_profiles_path() -> Path:
        if ConfigRepository is not None:
            return ConfigRepository().canonical_path()
        return Path(__file__).resolve().parents[2] / "src" / "main" / "deploy" / "bringup_system.json"

    @staticmethod
    def _deploy_profiles_path() -> Path:
        if ConfigRepository is not None:
            return ConfigRepository().deploy_path()
        return Path(__file__).resolve().parents[2] / "src" / "main" / "deploy" / "bringup_system.json"

    def _read_profile_index(self) -> Tuple[List[str], Optional[str]]:
        try:
            path = self._default_profiles_path()
            if not path.exists():
                return [], None
            data = self._load_config_payload(path)
            profiles = data.get("profiles")
            if not isinstance(profiles, dict) or not profiles:
                return [], None
            names = sorted(profiles.keys())
            default_name = data.get("default_profile")
            return names, default_name if isinstance(default_name, str) else None
        except Exception:
            return [], None

    def _refresh_profile_choices(self, keep_selection: bool = True) -> None:
        names, default_name = self._read_profile_index()
        self._default_profile_name = default_name
        self.profile_combo["values"] = names
        if not names:
            self._profile_pick_var.set("")
            self._refresh_default_checkbox()
            return
        current = self._profile_pick_var.get()
        if keep_selection and current in names:
            self._refresh_default_checkbox()
            return
        if self._profile_name in names:
            self._profile_pick_var.set(self._profile_name)
            self._refresh_default_checkbox()
            return
        if default_name in names:
            self._profile_pick_var.set(default_name)
            self._refresh_default_checkbox()
            return
        self._profile_pick_var.set(names[0])
        self._refresh_default_checkbox()

    def _refresh_default_checkbox(self) -> None:
        """
        NAME
            _refresh_default_checkbox - Mirror the current profile default state.
        """
        if not hasattr(self, "var_set_default"):
            return
        self.var_set_default.set(
            bool(self._profile_name and self._profile_name == self._default_profile_name)
        )

    def _on_profile_pick(self, _event: tk.Event) -> None:
        name = self._profile_pick_var.get().strip()
        if name:
            self.entry_profile.delete(0, tk.END)
            self.entry_profile.insert(0, name)

    def _on_load_selected_profile(self) -> None:
        name = self._profile_pick_var.get().strip()
        if not name:
            messagebox.showerror("Invalid", "Select a profile first.")
            return
        path = self._default_profiles_path()
        if not path.exists():
            messagebox.showerror("Missing", f"No profiles file found at {path}.")
            return
        self._load_profile_from_path(
            str(path),
            ask_profile=False,
            confirm_discard=True,
            selected_name=name,
        )

    def _choose_profile_name(self, names: List[str], default_name: Optional[str]) -> Optional[str]:
        """
        NAME
            _choose_profile_name - Ask the user which profile to load.
        """
        dialog = tk.Toplevel(self)
        dialog.title("Select Profile")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Profile").pack(anchor="w", padx=10, pady=(10, 2))
        var = tk.StringVar(value=default_name or names[0])
        combo = ttk.Combobox(dialog, values=names, textvariable=var, state="readonly", width=30)
        combo.pack(padx=10, pady=4)

        result: List[Optional[str]] = [None]

        def _ok() -> None:
            result[0] = var.get()
            dialog.destroy()

        def _cancel() -> None:
            dialog.destroy()

        button_row = ttk.Frame(dialog)
        button_row.pack(padx=10, pady=(6, 10), anchor="e")
        ttk.Button(button_row, text="Cancel", command=_cancel).pack(side="left", padx=4)
        ttk.Button(button_row, text="OK", command=_ok).pack(side="left", padx=4)
        self.wait_window(dialog)
        return result[0]

    def _on_profile_select(self, _event: tk.Event) -> None:
        """
        NAME
            _on_profile_select - Load the selected profile from the dropdown.
        """
        if self._suppress_profile_select:
            return
        selected = self.entry_profile.get().strip()
        if not selected or selected == self._profile_name:
            return
        path = self._profile_source_path
        if not path:
            path = str(self._default_profiles_path())
        self._load_profile_from_path(path, ask_profile=False, confirm_discard=True, selected_name=selected)

    def _set_profile_names(self, names: List[str]) -> None:
        """
        NAME
            _set_profile_names - Update the profile dropdown values.
        """
        unique = sorted({name for name in names if name})
        self._profile_names = unique
        if hasattr(self, "entry_profile"):
            try:
                self.entry_profile.configure(values=self._profile_names)
            except tk.TclError:
                pass

    def _save_profile_as(self) -> None:
        """
        NAME
            _save_profile_as - Export the current diagram into a profile JSON.
        """
        profile_name = self.entry_profile.get().strip()
        if not profile_name:
            messagebox.showerror("Invalid", "Profile name is required.")
            return
        validation_error = self._validate_nodes()
        if validation_error:
            messagebox.showerror("Invalid", validation_error)
            return
        if not self._confirm_can_id_collisions():
            return
        if not self._confirm_terminators():
            return
        if not self._confirm_neighbors_current_for_save():
            return
        path = filedialog.asksaveasfilename(
            title="Save Bringup Profiles JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        data = {
            "default_profile": profile_name,
            "schema_version": self._expected_schema_version(),
            "data_version": timestamp_version(),
            "profiles": {
                profile_name: self._profile_from_nodes(),
            },
            KEY_TOPOLOGY: {
                KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {
                    profile_name: self._topology_snapshot(),
                },
            },
            "diagram": {
                "profiles": {
                    profile_name: self._diagram_snapshot(),
                }
            },
        }
        self._apply_node_updates_to_registry()
        if self._device_registry_list:
            data["devices"] = self._device_registry_list
        try:
            data = self._save_config_payload(Path(path), data)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to write file: {exc}")
            return
        self._dirty = False
        self._set_profile_names(self._profile_names + [profile_name])
        messagebox.showinfo("Saved", f"Wrote profile to {path}")

    def _save_selection_as(self) -> None:
        """
        NAME
            _save_selection_as - Export selected nodes into a profile JSON.
        """
        if not self._selected_nodes:
            messagebox.showinfo("Save Selection", "Select one or more nodes or callouts.")
            return
        profile_name = self.entry_profile.get().strip()
        if not profile_name:
            messagebox.showerror("Invalid", "Profile name is required.")
            return
        selected_nodes = [n for n in self._nodes if n.key in self._selected_nodes]
        selected_devices = [n for n in selected_nodes if n.node_type == "device"]
        if not selected_devices:
            messagebox.showinfo("Save Selection", "Selection contains no device nodes.")
            return
        validation_error = self._validate_nodes(nodes=selected_devices)
        if validation_error:
            messagebox.showerror("Invalid", validation_error)
            return
        if not self._confirm_can_id_collisions(nodes=selected_devices):
            return
        if not self._confirm_terminators(nodes=selected_devices):
            return
        if not self._confirm_neighbors_current_for_save():
            return
        path = filedialog.asksaveasfilename(
            title="Save Bringup Profiles JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        path_obj = Path(path)
        if path_obj.exists():
            base = path_obj.stem
            suffix = path_obj.suffix or ".json"
            parent = path_obj.parent
            index = 1
            while True:
                candidate = parent / f"{base}_{index}{suffix}"
                if not candidate.exists():
                    path_obj = candidate
                    break
                index += 1
            messagebox.showinfo(
                "Save Selection",
                f"File exists. Saving as {path_obj.name} instead.",
            )
        path = str(path_obj)
        data = {
            "default_profile": profile_name,
            "schema_version": self._expected_schema_version(),
            "data_version": timestamp_version(),
            "profiles": {
                profile_name: self._profile_from_nodes_list(selected_devices),
            },
            KEY_TOPOLOGY: {
                KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {
                    profile_name: self._topology_snapshot_from_nodes(selected_nodes),
                },
            },
            "diagram": {
                "profiles": {
                    profile_name: self._diagram_snapshot_from_nodes(selected_nodes),
                }
            },
        }
        self._apply_node_updates_to_registry()
        if self._device_registry_list:
            data["devices"] = self._device_registry_list
        data["data_hash"] = self._compute_data_hash(data)
        selected_keys = {n.key for n in selected_nodes}
        diag_profile = data["diagram"]["profiles"][profile_name]
        diag_profile["ethernetLinks"] = [
            {"a": a, "b": b}
            for a, b in self._ethernet_links
            if a in selected_keys and b in selected_keys
        ]
        diag_profile["canLinks"] = [
            {"node": link["node"], "bus": link["bus"], "port": link.get("port", 1)}
            for link in self._can_bus_links
            if link.get("node") in selected_keys
        ]
        diag_profile["deviceLinks"] = [
            {
                "node": link["node"],
                "device": link["device"],
                "port": link.get("port", 1),
            }
            for link in self._cannect_device_links
            if link.get("node") in selected_keys and link.get("device") in selected_keys
        ]
        diag_profile[KEY_ATTACHMENT_LINKS] = [
            {
                KEY_LINK_DEVICE: link.get(KEY_LINK_DEVICE),
                KEY_LINK_ATTACHMENT: link.get(KEY_LINK_ATTACHMENT),
            }
            for link in self._attachment_links
            if link.get(KEY_LINK_DEVICE) in selected_keys
            and link.get(KEY_LINK_ATTACHMENT) in selected_keys
        ]
        diag_profile[KEY_DIO_LINKS] = [
            {
                KEY_LINK_ROBORIO: link.get(KEY_LINK_ROBORIO),
                KEY_LINK_DEVICE: link.get(KEY_LINK_DEVICE),
            }
            for link in self._dio_wiring_links
            if link.get(KEY_LINK_DEVICE) in selected_keys
            and link.get(KEY_LINK_ROBORIO) in selected_keys
        ]
        diag_profile[KEY_POWER_LINKS] = [
            {
                KEY_LINK_A: link.get(KEY_LINK_A),
                KEY_LINK_B: link.get(KEY_LINK_B),
            }
            for link in self._power_links
            if link.get(KEY_LINK_A) in selected_keys and link.get(KEY_LINK_B) in selected_keys
        ]
        try:
            self._save_config_payload(Path(path), data)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to write file: {exc}")
            return
        self._dirty = False
        self._set_profile_names(self._profile_names + [profile_name])
        messagebox.showinfo("Saved", f"Wrote selection profile to {path}")

    def _save_config(self) -> None:
        """
        NAME
            _save_config - Write the full current config back to the loaded source path.
        """
        source_path = self._profile_source_path
        if not source_path:
            messagebox.showerror(ERR_NO_SOURCE_CONFIG_TITLE, ERR_NO_SOURCE_CONFIG_TEXT)
            return
        self._save_profile_to_path(
            Path(source_path),
            prompt_replace=False,
            update_source=True,
        )

    def _save_config_as(self) -> None:
        """
        NAME
            _save_config_as - Write the full current config to a new path and make it the active source.
        """
        path = filedialog.asksaveasfilename(
            title=TITLE_SAVE_BRINGUP_CONFIG,
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._save_profile_to_path(
            Path(path),
            prompt_replace=False,
            update_source=True,
            seed_path=Path(self._profile_source_path) if self._profile_source_path else None,
        )

    def _on_save_to_deploy(self) -> None:
        """
        NAME
            _on_save_to_deploy - Append or replace a profile in bringup_system.json.
        """
        canonical = self._canonical_profiles_path()
        deploy = self._deploy_profiles_path()
        self._save_profile_to_path(canonical, prompt_replace=True, update_source=True)
        self._sync_profiles_to_deploy(canonical, deploy)

    @staticmethod
    def _sync_profiles_to_deploy(source: Path, deploy: Path) -> None:
        """
        NAME
            _sync_profiles_to_deploy - Copy canonical profiles into deploy path.
        """
        try:
            if ConfigRepository is not None:
                repository = ConfigRepository()
                payload = repository.load_path(source).to_payload()
                session = repository.session_for_payload(deploy, payload)
                repository.save(session, path=deploy)
            else:
                deploy.parent.mkdir(parents=True, exist_ok=True)
                deploy.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            # Best-effort sync; report via UI only if needed.
            pass

    def _save_profile_to_path(
        self,
        path: Path,
        prompt_replace: bool,
        update_source: bool,
        seed_path: Optional[Path] = None,
    ) -> None:
        """
        NAME
            _save_profile_to_path - Write profile+diagram data into a JSON file.

        PARAMETERS
            path: Target JSON file path.
            prompt_replace: Whether to prompt before replacing an existing profile.
            update_source: Whether to update the current source path to this file.
            seed_path: Optional existing full-config source to clone when the target file does not exist yet.
        """
        profile_name = self.entry_profile.get().strip()
        if not profile_name:
            messagebox.showerror("Invalid", "Profile name is required.")
            return
        validation_error = self._validate_nodes()
        if validation_error:
            messagebox.showerror("Invalid", validation_error)
            return
        if not self._confirm_can_id_collisions():
            return
        if not self._confirm_terminators():
            return
        if not self._confirm_dio_warnings():
            return
        if not self._confirm_neighbors_current_for_save():
            return
        data = {}
        if path.exists():
            try:
                data = self._load_config_payload(path)
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to read {path}: {exc}")
                return
        elif isinstance(seed_path, Path) and seed_path.exists():
            try:
                data = self._load_config_payload(seed_path)
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to read {seed_path}: {exc}")
                return
        if not isinstance(data, dict):
            data = {}
        if data.get("schema_version") != self._expected_schema_version():
            data["schema_version"] = self._expected_schema_version()
        profiles = data.get("profiles")
        if not isinstance(profiles, dict):
            profiles = {}

        if prompt_replace and profile_name in profiles:
            replace = messagebox.askyesno(
                "Replace Profile",
                f"Profile '{profile_name}' exists. Replace it?",
            )
            if not replace:
                return

        if self._pending_global_device_deletions:
            pending = {
                label.strip()
                for label in self._pending_global_device_deletions
                if label.strip()
            }
            for entry_profile in profiles.values():
                if not isinstance(entry_profile, dict):
                    continue
                devices = entry_profile.get(KEY_DEVICES)
                if not isinstance(devices, list):
                    continue
                entry_profile[KEY_DEVICES] = [
                    label for label in devices if str(label).strip() not in pending
                ]
            topology = data.get(KEY_TOPOLOGY)
            topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES) if isinstance(topology, dict) else None
            if not isinstance(topology_profiles, dict):
                topology_profiles = {}
            for topology_entry in topology_profiles.values():
                if not isinstance(topology_entry, dict):
                    continue
                self._prune_topology_entry_device_refs(topology_entry, pending)

        saved_profile = self._merge_saved_profile_fields(
            profiles.get(profile_name),
            self._profile_from_nodes(),
        )
        if upsert_profile is not None:
            upsert_profile(
                data,
                profile_name,
                saved_profile,
                topology_entry=self._topology_snapshot(),
            )
        else:
            topology = data.get(KEY_TOPOLOGY)
            if not isinstance(topology, dict):
                topology = {
                    KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                    KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                    KEY_TOPOLOGY_PROFILES: {},
                }
            topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
            if not isinstance(topology_profiles, dict):
                topology_profiles = {}
            profiles[profile_name] = saved_profile
            data["profiles"] = profiles
            topology_profiles[profile_name] = self._topology_snapshot()
            data[KEY_TOPOLOGY] = {
                KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: topology_profiles,
            }
        if self.var_set_default.get() or "default_profile" not in data:
            data["default_profile"] = profile_name
        default_name = data.get("default_profile")
        self._default_profile_name = default_name if isinstance(default_name, str) else None
        if not self._write_profiles_payload(path, data, include_extras=True):
            return
        self._pending_global_device_deletions = set()
        self._dirty = False
        if update_source:
            self._profile_source_path = str(path)
        updated_profiles = data.get(KEY_PROFILES)
        self._set_profile_names(sorted(updated_profiles.keys()) if isinstance(updated_profiles, dict) else [])
        self._refresh_profile_choices(keep_selection=False)
        self._refresh_default_checkbox()
        message = MSG_SAVED_CONFIG_FMT.format(path=path, profile=profile_name)
        if path.resolve() == self._deploy_profiles_path().resolve():
            message = MSG_SAVED_DEPLOY_FMT.format(profile=profile_name)
        messagebox.showinfo("Saved", message)

    def _prune_topology_entry_device_refs(
        self,
        topology_entry: Dict[str, object],
        pending: set[str],
    ) -> None:
        """
        NAME
            _prune_topology_entry_device_refs - Remove deleted device refs from one saved topology profile.
        """
        nodes = topology_entry.get(KEY_TOPOLOGY_NODES)
        if not isinstance(nodes, list) or not pending:
            return
        pending_lower = {label.lower() for label in pending}
        removed_keys: set[int] = set()
        kept_nodes: List[Dict[str, object]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = str(node.get("nodeType", node.get("objectType", TEXT_EMPTY))).strip().lower()
            if node_type == NODE_TYPE_DEVICE:
                device_ref = str(node.get(KEY_TOPOLOGY_DEVICE_REF, TEXT_EMPTY)).strip()
                if device_ref.lower() in pending_lower:
                    node_key = node.get("key")
                    if isinstance(node_key, int):
                        removed_keys.add(node_key)
                    continue
            kept_nodes.append(node)
        if removed_keys:
            kept_nodes = [
                node
                for node in kept_nodes
                if not (
                    isinstance(node, dict)
                    and str(node.get("nodeType", TEXT_EMPTY)).strip().lower() == NODE_TYPE_CALLOUT
                    and node.get("targetNodeKey") in removed_keys
                )
            ]
        topology_entry[KEY_TOPOLOGY_NODES] = kept_nodes
        edges = topology_entry.get(KEY_TOPOLOGY_EDGES)
        if isinstance(edges, list) and removed_keys:
            topology_entry[KEY_TOPOLOGY_EDGES] = [
                edge
                for edge in edges
                if isinstance(edge, dict)
                and edge.get("fromNode") not in removed_keys
                and edge.get("toNode") not in removed_keys
            ]

    def _validate_nodes(self, nodes: Optional[List[Node]] = None) -> Optional[str]:
        """
        NAME
            _validate_nodes - Enforce category constraints before save.

        RETURNS
            Error message or None when valid.
        """
        seen_singletons = {}
        seen_strict: Dict[Tuple[str, str, int], Node] = {}
        nodes_to_check = nodes if nodes is not None else self._profile_device_nodes()
        for node in nodes_to_check:
            if node.category in SINGLETON_CATEGORIES:
                if node.category in seen_singletons:
                    return f"Only one {node.category} is allowed."
                seen_singletons[node.category] = node
            if node.interface != INTERFACE_DIO and node.category == GENERIC_CATEGORY:
                if not node.vendor or not node.device_type:
                    return MSG_GENERIC_DEVICE_VENDOR_TYPE_REQUIRED.format(node.label)
            if node.interface == INTERFACE_DIO:
                if node.dio is None or not isinstance(node.dio, int) or node.dio < 0:
                    return MSG_INVALID_DIO_CHANNEL.format(node.label)
                if not node.device_type:
                    return MSG_MISSING_DIO_TYPE.format(node.label)
                if node.device_type not in DIO_DEVICE_TYPES:
                    return MSG_INVALID_DIO_TYPE.format(node.label)
            else:
                if not self._is_valid_can_id(node.can_id):
                    return f"Invalid CAN ID {node.can_id} for {node.label}."
                generated_entry = self._device_entry_from_node(node)
                if "manufacturer" not in generated_entry or "deviceType" not in generated_entry:
                    return MSG_DEVICE_CAN_FIELDS_REQUIRED.format(node.label)
            strict_key = self._dup_key_for_node(node)
            if strict_key is not None:
                vendor, dev_type, can_id = strict_key
                strict_key = (vendor, dev_type, can_id)
                if strict_key in seen_strict:
                    other = seen_strict[strict_key]
                    return (
                        f"Duplicate CAN address (vendor/type/id) {can_id} "
                        f"({other.label}, {node.label})."
                    )
                seen_strict[strict_key] = node
            if node.limits is not None:
                try:
                    self._normalize_limits(node.limits)
                except ValueError as exc:
                    return f"Invalid limits for {node.label}: {exc}"
        return None

    def _profile_from_nodes(self) -> Dict[str, object]:
        """
        NAME
            _profile_from_nodes - Build a bringup profile object.

        RETURNS
            Dict compatible with bringup_system.json.
        """
        return self._profile_from_nodes_list(self._profile_device_nodes(), include_non_topology=True)

    def _profile_from_nodes_list(
        self,
        nodes: List[Node],
        include_non_topology: bool = False,
    ) -> Dict[str, object]:
        """
        NAME
            _profile_from_nodes_list - Build a bringup profile from a node list.
        """
        nodes = [n for n in nodes if self._is_registry_device_node(n)]
        labels = [n.label for n in nodes if n.node_type == NODE_TYPE_DEVICE]
        if include_non_topology:
            for label in list(self.__dict__.get("_non_topology_profile_labels", []) or []):
                if label and label not in labels:
                    labels.append(label)
        return {"devices": labels}

    def _merge_saved_profile_fields(
        self,
        existing_profile: object,
        updated_profile: Dict[str, object],
    ) -> Dict[str, object]:
        """
        NAME
            _merge_saved_profile_fields - Preserve non-topology profile metadata while rewriting devices.
        """
        devices = updated_profile.get(KEY_DEVICES, [])
        if replace_profile_devices is None:
            merged = dict(existing_profile) if isinstance(existing_profile, dict) else {}
            merged.update(updated_profile)
            return merged
        return replace_profile_devices(existing_profile, devices if isinstance(devices, list) else [])

    def _sync_non_topology_profile_labels(self, profile: Dict[str, object]) -> None:
        """
        NAME
            _sync_non_topology_profile_labels - Preserve active-profile labels without canvas nodes.
        """
        devices = profile.get(KEY_DEVICES)
        if not isinstance(devices, list):
            self._non_topology_profile_labels = []
            return
        node_labels = {
            (node.label or TEXT_EMPTY).strip()
            for node in self._nodes
            if node.node_type == NODE_TYPE_DEVICE and (node.label or TEXT_EMPTY).strip()
        }
        extras: List[str] = []
        seen: set[str] = set()
        for label in devices:
            label_text = str(label).strip()
            if not label_text or label_text in seen or label_text in node_labels:
                continue
            seen.add(label_text)
            extras.append(label_text)
        self._non_topology_profile_labels = extras

    def _node_to_entry(self, node: Node) -> Dict[str, object]:
        """
        NAME
            _node_to_entry - Convert a Node into a profile entry dict.
        """
        entry: Dict[str, object] = {"label": node.label, "id": node.can_id}
        if node.category == GENERIC_CATEGORY:
            entry["vendor"] = node.vendor
            entry["type"] = node.device_type
        if node.motor:
            entry["motor"] = node.motor
        if node.limits:
            entry["limits"] = self._normalize_limits(node.limits)
        if node.terminator is not None:
            entry["terminator"] = node.terminator
        if node.tags:
            entry["tags"] = list(node.tags)
        return entry

    @staticmethod
    def _is_valid_can_id(value: int) -> bool:
        """
        NAME
            _is_valid_can_id - Validate a CAN ID for compatibility.

        RETURNS
            True when the ID is -1 or in the 0-62 range.
        """
        return isinstance(value, int) and value >= -1 and value <= 62

    @staticmethod
    def _normalize_limits(limits: Dict[str, object]) -> Dict[str, object]:
        """
        NAME
            _normalize_limits - Normalize limit switch fields for JSON output.

        RETURNS
            Limits dict with integer DIO values and boolean invert.
        """
        if not isinstance(limits, dict):
            raise ValueError("limits must be an object")
        fwd = limits.get("fwdDio", -1)
        rev = limits.get("revDio", -1)
        invert = bool(limits.get("invert", False))

        def _coerce_dio(value: object, label: str) -> int:
            if value is None or value == "":
                return -1
            if isinstance(value, bool):
                raise ValueError(f"{label} must be an integer")
            if isinstance(value, (int,)):
                dio = int(value)
            elif isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
                dio = int(value.strip())
            else:
                raise ValueError(f"{label} must be an integer")
            if dio < -1:
                raise ValueError(f"{label} must be -1 or greater")
            return dio

        return {
            "fwdDio": _coerce_dio(fwd, "fwdDio"),
            "revDio": _coerce_dio(rev, "revDio"),
            "invert": invert,
        }

    def _nodes_from_profile(self, profile: Dict[str, object]) -> List[Node]:
        """
        NAME
            _nodes_from_profile - Convert a profile dict into Node objects.
        """
        nodes: List[Node] = []
        devices = profile.get("devices")
        if isinstance(devices, list):
            for label in devices:
                node = self._node_from_device_label(label)
                if node is not None:
                    nodes.append(node)
            return nodes

        def _append(category: str, entry: Dict[str, object]) -> None:
            label = str(entry.get("label", "")).strip()
            can_id = int(entry.get("id", 0))
            vendor = str(entry.get("vendor", "")).strip()
            dev_type = str(entry.get("type", "")).strip()
            motor = str(entry.get("motor", "")).strip()
            limits = entry.get("limits")
            if isinstance(limits, dict):
                limits = dict(limits)
            terminator = entry.get("terminator")
            tags = self._normalize_tags(entry.get("tags", []))
            node = Node(
                key=self._next_key,
                category=category,
                label=label or f"{category.upper()} {can_id}",
                can_id=can_id,
                vendor=vendor,
                device_type=dev_type,
                motor=motor,
                limits=limits if isinstance(limits, dict) else None,
                terminator=bool(terminator) if isinstance(terminator, bool) else None,
                x=0.0,
                row=0,
                scale=1.0,
                tags=tags,
            )
            self._next_key += 1
            nodes.append(node)

        for category in BUCKET_CATEGORIES:
            entries = profile.get(category, [])
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        _append(category, entry)
        for category in SINGLETON_CATEGORIES:
            entry = profile.get(category)
            if isinstance(entry, dict):
                _append(category, entry)
        entries = profile.get(GENERIC_CATEGORY, [])
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    _append(GENERIC_CATEGORY, entry)
        return nodes

    def _node_from_device_label(self, label: object) -> Optional[Node]:
        """
        NAME
            _node_from_device_label - Build a Node from a device registry label.
        """
        label_text = str(label).strip()
        if not label_text:
            return None
        entry = self._device_registry.get(label_text)
        if not isinstance(entry, dict):
            return None
        return self._node_from_device_def(entry)

    @staticmethod
    def _infrastructure_category_from_label(label: str) -> Optional[str]:
        """
        NAME
            _infrastructure_category_from_label - Infer infrastructure category from a label.
        """
        label_norm = label.strip().lower()
        if not label_norm:
            return None
        if TAG_INJECT in label_norm:
            return DIAGRAM_CATEGORY_CANNECT_INJECT
        if TAG_CANNECT in label_norm:
            return DIAGRAM_CATEGORY_CANNECT_DIRECT
        if INFRASTRUCTURE_LABEL_ANALYZER in label_norm:
            return DIAGRAM_CATEGORY_ANALYZER
        return None

    @staticmethod
    def _is_infrastructure_category(category: str) -> bool:
        """
        NAME
            _is_infrastructure_category - Return true for topology-only infrastructure categories.
        """
        return category.strip().lower() in INFRASTRUCTURE_NODE_CATEGORIES

    def _is_infrastructure_device_entry(self, entry: Dict[str, object]) -> bool:
        """
        NAME
            _is_infrastructure_device_entry - Detect leaked infrastructure pseudo-devices.
        """
        label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
        if self._infrastructure_category_from_label(label) is not None:
            return True
        tags = {
            str(tag).strip().lower()
            for tag in entry.get("tags", [])
            if isinstance(tag, str)
        }
        if tags.intersection({TAG_SWYFT, TAG_CANNECT, TAG_INJECT, TAG_DIRECT, TAG_ANALYZER}):
            return True
        model = str(entry.get(KEY_MODEL, entry.get("model", EMPTY_STRING))).strip().lower()
        return model == INFRASTRUCTURE_MODEL_WIRING

    def _node_from_infrastructure_entry(self, entry: Dict[str, object]) -> Optional[Node]:
        """
        NAME
            _node_from_infrastructure_entry - Convert a leaked infrastructure entry into a topology node.
        """
        label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
        category = self._infrastructure_category_from_label(label)
        if category is None:
            tags = {
                str(tag).strip().lower()
                for tag in entry.get("tags", [])
                if isinstance(tag, str)
            }
            if TAG_INJECT in tags:
                category = DIAGRAM_CATEGORY_CANNECT_INJECT
            elif TAG_ANALYZER in tags:
                category = DIAGRAM_CATEGORY_ANALYZER
            else:
                category = DIAGRAM_CATEGORY_CANNECT_DIRECT
        vendor = DIAGRAM_VENDOR_ANALYZER if category == DIAGRAM_CATEGORY_ANALYZER else DIAGRAM_VENDOR_SWYFT
        motor = DIAGRAM_DEVICE_ANALYZER if category == DIAGRAM_CATEGORY_ANALYZER else DIAGRAM_DEVICE_WIRING
        tags = self._normalize_tags(entry.get("tags", []))
        node = Node(
            key=self._next_key,
            category=category,
            label=label,
            can_id=CAN_ID_DIAGRAM_DEFAULT,
            node_type=ANALYZER_NODE_TYPE,
            interface=INTERFACE_CAN,
            vendor=vendor,
            device_type=TEXT_EMPTY,
            motor=motor,
            limits=None,
            terminator=None,
            x=0.0,
            row=0,
            scale=1.0,
            tags=tags,
            profile_visible=False,
        )
        self._next_key += 1
        return node

    def _node_from_device_def(self, entry: Dict[str, object]) -> Optional[Node]:
        """
        NAME
            _node_from_device_def - Build a Node from a device registry entry.
        """
        if self._is_dio_device_entry(entry):
            label = str(entry.get("label", "")).strip()
            device_type = str(entry.get("type", "")).strip()
            dio_value = entry.get(KEY_ID)
            if not isinstance(dio_value, int):
                dio_value = entry.get(KEY_DIO)
            invert = entry.get("invert")
            tags = self._normalize_tags(entry.get("tags", []))
            node = Node(
                key=self._next_key,
                category=GENERIC_CATEGORY,
                label=label,
                can_id=CAN_ID_DIAGRAM_DEFAULT,
                interface=INTERFACE_DIO,
                vendor="",
                device_type=device_type,
                motor="",
                limits=None,
                dio=int(dio_value) if isinstance(dio_value, int) else None,
                invert=bool(invert) if isinstance(invert, bool) else None,
                terminator=None,
                x=0.0,
                row=0,
                scale=1.0,
                tags=tags,
            )
            self._next_key += 1
            return node
        if not self._is_can_device_entry(entry):
            return None
        can_id = entry.get("id")
        if not isinstance(can_id, int):
            return None
        if self._is_infrastructure_device_entry(entry):
            return self._node_from_infrastructure_entry(entry)
        label = str(entry.get("label", "")).strip()
        category = self._category_for_device(entry)
        vendor = self._vendor_for_device(entry)
        device_type = self._device_type_for_device(entry)
        motor = str(entry.get("model", "")).strip()
        terminator = entry.get("terminator")
        tags = self._normalize_tags(entry.get("tags", []))
        node = Node(
            key=self._next_key,
            category=category,
            label=label,
            can_id=can_id,
            interface=INTERFACE_CAN,
            vendor=vendor,
            device_type=device_type,
            motor=motor,
            limits=None,
            terminator=bool(terminator) if isinstance(terminator, bool) else None,
            x=0.0,
            row=0,
            scale=1.0,
            tags=tags,
        )
        self._next_key += 1
        return node

    def _is_can_device_entry(self, entry: Dict[str, object]) -> bool:
        interface = str(entry.get(KEY_INTERFACE) or entry.get(KEY_INTERFACE_LEGACY) or "").strip()
        if profile_consts is not None:
            return interface.upper() == profile_consts.INTERFACE_CAN
        return interface.upper() == "CAN"

    def _is_dio_device_entry(self, entry: Dict[str, object]) -> bool:
        interface = str(entry.get(KEY_INTERFACE) or entry.get(KEY_INTERFACE_LEGACY) or "").strip()
        if profile_consts is not None:
            return interface.upper() == profile_consts.INTERFACE_DIO
        return interface.upper() == INTERFACE_DIO

    def _category_for_device(self, entry: Dict[str, object]) -> str:
        manufacturer = entry.get("manufacturer")
        device_type = entry.get("deviceType")
        model = str(entry.get("model", "")).upper()
        if device_type == DEVTYPE_MOTOR:
            if manufacturer == MFG_REV:
                if MODEL_NEO_550 in model:
                    return "neo550s"
                if MODEL_FLEX in model:
                    return "flexes"
                return "neos"
            if manufacturer == MFG_CTRE:
                if MODEL_FALCON in model:
                    return "falcons"
                return "krakens"
        if device_type == DEVTYPE_ENCODER:
            return "cancoders"
        if device_type == DEVTYPE_MISC:
            return "candles"
        if device_type == DEVTYPE_POWER:
            return "pdp" if manufacturer == MFG_CTRE else "pdh"
        if device_type == DEVTYPE_GYRO:
            return "pigeon"
        if device_type == DEVTYPE_ROBORIO:
            return "roborio"
        return GENERIC_CATEGORY

    def _vendor_for_device(self, entry: Dict[str, object]) -> str:
        manufacturer = entry.get("manufacturer")
        if manufacturer == MFG_NI:
            return "NI"
        if manufacturer == MFG_CTRE:
            return "CTRE"
        if manufacturer == MFG_REV:
            return "REV"
        return ""

    def _device_type_for_device(self, entry: Dict[str, object]) -> str:
        manufacturer = entry.get("manufacturer")
        device_type = entry.get("deviceType")
        model = str(entry.get("model", "")).upper()
        if device_type == DEVTYPE_MOTOR:
            if manufacturer == MFG_REV:
                if MODEL_NEO_550 in model:
                    return "NEO 550"
                if MODEL_FLEX in model:
                    return "FLEX"
                return "NEO"
            if manufacturer == MFG_CTRE:
                if MODEL_FALCON in model:
                    return "FALCON"
                return "KRAKEN"
        if device_type == DEVTYPE_ENCODER:
            return "CANCoder"
        if device_type == DEVTYPE_MISC:
            return "CANdle"
        if device_type == DEVTYPE_POWER:
            return "PowerDistributionModule"
        if device_type == DEVTYPE_GYRO:
            return "Pigeon"
        if device_type == DEVTYPE_ROBORIO:
            return "roboRIO"
        return ""

    def _apply_node_updates_to_registry(self) -> None:
        """
        NAME
            _apply_node_updates_to_registry - Update device registry entries from nodes.
        """
        if not isinstance(self._device_registry_list, list):
            self._device_registry_list = []
        if not isinstance(self._device_registry, dict):
            self._device_registry = {}
        self._prune_infrastructure_registry_entries()
        for node in self._device_nodes():
            if not self._is_registry_device_node(node):
                continue
            entry = self._device_registry.get(node.label)
            if isinstance(entry, dict):
                entry[KEY_LABEL] = node.label
                entry[KEY_INTERFACE] = (
                    profile_consts.INTERFACE_DIO if profile_consts is not None else INTERFACE_DIO
                ) if node.interface == INTERFACE_DIO else (
                    profile_consts.INTERFACE_CAN if profile_consts is not None else INTERFACE_CAN
                )
                entry.pop(KEY_INTERFACE_LEGACY, None)
                if node.interface == INTERFACE_DIO:
                    entry[KEY_ID] = node.dio
                    entry.pop(KEY_DIO, None)
                    entry["invert"] = bool(node.invert) if node.invert is not None else False
                    if node.device_type and node.device_type.strip():
                        entry["type"] = node.device_type
                    for key in ("manufacturer", "deviceType", "model", "terminator"):
                        entry.pop(key, None)
                else:
                    generated_entry = self._device_entry_from_node(node)
                    for key in ("manufacturer", "deviceType", "id", "model", "type"):
                        entry.pop(key, None)
                    for key, value in generated_entry.items():
                        if key in (KEY_LABEL, KEY_INTERFACE, KEY_INTERFACE_LEGACY, "tags", "terminator"):
                            continue
                        entry[key] = value
                if node.tags:
                    entry["tags"] = list(node.tags)
                elif "tags" in entry:
                    entry["tags"] = []
                if node.terminator is not None:
                    entry["terminator"] = node.terminator
                elif "terminator" in entry:
                    entry.pop("terminator", None)
                continue
            new_entry = self._device_entry_from_node(node)
            self._device_registry_list.append(new_entry)
            self._device_registry[node.label] = new_entry
        self._sync_attachment_links_to_registry()

    def _prune_infrastructure_registry_entries(self) -> None:
        """
        NAME
            _prune_infrastructure_registry_entries - Remove infrastructure nodes from devices[].
        """
        if not self._device_registry_list:
            return
        kept_entries: List[Dict[str, object]] = []
        kept_registry: Dict[str, Dict[str, object]] = {}
        for entry in self._device_registry_list:
            if not isinstance(entry, dict):
                continue
            if self._is_infrastructure_device_entry(entry):
                continue
            label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
            kept_entries.append(entry)
            if label:
                kept_registry[label] = entry
        self._device_registry_list[:] = kept_entries
        self._device_registry = kept_registry

    @staticmethod
    def _normalize_power_link(link: Dict[str, object]) -> Optional[Dict[str, int]]:
        """
        NAME
            _normalize_power_link - Normalize one power link into stable endpoint order.
        """
        if not isinstance(link, dict):
            return None
        a = link.get(KEY_LINK_A)
        b = link.get(KEY_LINK_B)
        if not isinstance(a, int) or not isinstance(b, int) or a == b:
            return None
        low = min(a, b)
        high = max(a, b)
        return {KEY_LINK_A: low, KEY_LINK_B: high}

    def _sync_attachment_links_to_registry(self) -> None:
        """
        NAME
            _sync_attachment_links_to_registry - Store attachment links in registry.
        """
        if not self._device_registry_list:
            return
        node_by_key = {n.key: n for n in self._device_nodes()}
        attachments_by_label: Dict[str, List[str]] = {}
        for link in self._attachment_links:
            host_key = link.get(KEY_LINK_DEVICE)
            attach_key = link.get(KEY_LINK_ATTACHMENT)
            if not isinstance(host_key, int) or not isinstance(attach_key, int):
                continue
            host = node_by_key.get(host_key)
            attach = node_by_key.get(attach_key)
            if host is None or attach is None:
                continue
            attachments_by_label.setdefault(host.label, []).append(attach.label)
        for entry in self._device_registry_list:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get("label", "")).strip()
            if not label:
                continue
            attachments = attachments_by_label.get(label)
            if attachments:
                entry[KEY_ATTACHMENTS] = sorted(set(attachments))
            elif KEY_ATTACHMENTS in entry:
                entry.pop(KEY_ATTACHMENTS, None)

    def _rebuild_attachment_links_from_registry(self) -> None:
        """
        NAME
            _rebuild_attachment_links_from_registry - Build attachment links from registry.
        """
        self._attachment_links = []
        if not self._device_registry_list:
            return
        node_by_label = {n.label: n for n in self._device_nodes()}
        for entry in self._device_registry_list:
            if not isinstance(entry, dict):
                continue
            host_label = str(entry.get("label", "")).strip()
            if not host_label:
                continue
            attachments = entry.get(KEY_ATTACHMENTS)
            if not isinstance(attachments, list):
                continue
            host_node = node_by_label.get(host_label)
            if host_node is None:
                continue
            for attach_label in attachments:
                if not isinstance(attach_label, str):
                    continue
                attach_node = node_by_label.get(attach_label.strip())
                if attach_node is None:
                    continue
                link = {KEY_LINK_DEVICE: host_node.key, KEY_LINK_ATTACHMENT: attach_node.key}
                if link not in self._attachment_links:
                    self._attachment_links.append(link)

    def _prune_attachment_links(self) -> bool:
        """
        NAME
            _prune_attachment_links - Drop invalid attachment links.

        RETURNS
            True when any links were removed.
        """
        node_by_key = {n.key: n for n in self._device_nodes()}
        before = len(self._attachment_links)
        self._attachment_links = [
            link
            for link in self._attachment_links
            if isinstance(link, dict)
            and link.get(KEY_LINK_DEVICE) in node_by_key
            and link.get(KEY_LINK_ATTACHMENT) in node_by_key
            and self._is_dio_node(node_by_key[link.get(KEY_LINK_ATTACHMENT)])
            and not self._is_dio_node(node_by_key[link.get(KEY_LINK_DEVICE)])
        ]
        return len(self._attachment_links) != before

    def _prune_power_links(self) -> bool:
        """
        NAME
            _prune_power_links - Drop invalid power links.

        RETURNS
            True when any links were removed.
        """
        node_by_key = {n.key: n for n in self._device_nodes()}
        before = len(self._power_links)
        normalized: List[Dict[str, int]] = []
        seen: set[Tuple[int, int]] = set()
        for entry in self._power_links:
            link = self._normalize_power_link(entry)
            if link is None:
                continue
            a = link[KEY_LINK_A]
            b = link[KEY_LINK_B]
            if a not in node_by_key or b not in node_by_key:
                continue
            if self._is_dio_node(node_by_key[a]) or self._is_dio_node(node_by_key[b]):
                continue
            key = (a, b)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(link)
        self._power_links = normalized
        return len(self._power_links) != before

    def _prune_dio_wiring_links(self) -> bool:
        """
        NAME
            _prune_dio_wiring_links - Drop invalid DIO wiring links.

        RETURNS
            True when any links were removed.
        """
        node_by_key = {n.key: n for n in self._device_nodes()}
        before = len(self._dio_wiring_links)
        self._dio_wiring_links = [
            link
            for link in self._dio_wiring_links
            if isinstance(link, dict)
            and link.get(KEY_LINK_DEVICE) in node_by_key
            and link.get(KEY_LINK_ROBORIO) in node_by_key
            and self._is_dio_node(node_by_key[link.get(KEY_LINK_DEVICE)])
            and node_by_key[link.get(KEY_LINK_ROBORIO)].category == CATEGORY_ROBORIO
        ]
        return len(self._dio_wiring_links) != before

    def _ensure_dio_wiring_links(self) -> bool:
        """
        NAME
            _ensure_dio_wiring_links - Ensure each DIO node is wired to roboRIO.

        RETURNS
            True when any links were added.
        """
        roborio = self._roborio_node()
        if roborio is None:
            return False
        existing = {link.get(KEY_LINK_DEVICE) for link in self._dio_wiring_links}
        added = False
        for node in self._device_nodes():
            if not self._is_dio_node(node):
                continue
            if node.key in existing:
                continue
            self._dio_wiring_links.append(
                {KEY_LINK_ROBORIO: roborio.key, KEY_LINK_DEVICE: node.key}
            )
            added = True
        return added

    def _device_entry_from_node(self, node: Node) -> Dict[str, object]:
        """
        NAME
            _device_entry_from_node - Build a device registry entry from a node.
        """
        if node.interface == INTERFACE_DIO:
            entry: Dict[str, object] = {
                KEY_LABEL: node.label,
                KEY_INTERFACE: profile_consts.INTERFACE_DIO if profile_consts is not None else INTERFACE_DIO,
                KEY_ID: node.dio,
                "invert": bool(node.invert) if node.invert is not None else False,
            }
            entry.pop(KEY_INTERFACE_LEGACY, None)
            if node.device_type and node.device_type.strip():
                entry["type"] = node.device_type
            if node.tags:
                entry["tags"] = list(node.tags)
            return entry
        manufacturer = self._manufacturer_id_from_vendor(node.vendor)
        device_type_name = str(node.device_type or TEXT_EMPTY).strip()
        device_type = self._device_type_id_from_name(device_type_name)
        entry = {
            KEY_LABEL: node.label,
            KEY_INTERFACE: profile_consts.INTERFACE_CAN if profile_consts is not None else INTERFACE_CAN,
            "id": node.can_id,
        }
        entry.pop(KEY_INTERFACE_LEGACY, None)
        if manufacturer is not None:
            entry["manufacturer"] = manufacturer
        if device_type is not None:
            entry["deviceType"] = device_type
        if node.motor:
            entry["model"] = node.motor
        if node.device_type and not node.motor:
            entry["model"] = node.device_type
        if device_type_name:
            entry["type"] = self._device_def_type_from_device_name(device_type_name)
        if node.tags:
            entry["tags"] = list(node.tags)
        if node.terminator is not None:
            entry["terminator"] = node.terminator
        return entry

    def _manufacturer_id_from_vendor(self, vendor: str) -> Optional[int]:
        vendor_norm = vendor.strip().upper()
        if vendor_norm == "NI":
            return MFG_NI
        if vendor_norm == "CTRE":
            return MFG_CTRE
        if vendor_norm == "REV":
            return MFG_REV
        return None

    def _confirm_dio_warnings(self) -> bool:
        """
        NAME
            _confirm_dio_warnings - Warn on unattached/unwired DIO devices.
        """
        nodes_to_check = self._profile_device_nodes()
        node_by_key = {n.key: n for n in self._device_nodes()}
        roborio_node = self._roborio_node()
        attachment_keys = {
            link.get(KEY_LINK_ATTACHMENT)
            for link in self._attachment_links
            if isinstance(link, dict)
            and link.get(KEY_LINK_DEVICE) in node_by_key
            and link.get(KEY_LINK_ATTACHMENT) in node_by_key
            and self._is_dio_node(node_by_key[link.get(KEY_LINK_ATTACHMENT)])
            and not self._is_dio_node(node_by_key[link.get(KEY_LINK_DEVICE)])
        }
        wiring_keys = {
            link.get(KEY_LINK_DEVICE)
            for link in self._dio_wiring_links
            if isinstance(link, dict)
            and link.get(KEY_LINK_DEVICE) in node_by_key
            and link.get(KEY_LINK_ROBORIO) in node_by_key
            and self._is_dio_node(node_by_key[link.get(KEY_LINK_DEVICE)])
            and node_by_key[link.get(KEY_LINK_ROBORIO)].category == CATEGORY_ROBORIO
        }
        dio_nodes = [n for n in nodes_to_check if n.interface == INTERFACE_DIO]
        if not dio_nodes:
            return True
        missing_attach = [n.label for n in dio_nodes if n.key not in attachment_keys]
        missing_wire = [n.label for n in dio_nodes if n.key not in wiring_keys]
        if not missing_attach and not missing_wire and roborio_node is not None:
            return True
        lines = [MSG_DIO_WARN_HEADER]
        if roborio_node is None:
            lines.append(MSG_DIO_WARN_NO_ROBORIO)
        if missing_attach:
            lines.append(MSG_DIO_WARN_ATTACH.format(labels=SEP_COMMA_SPACE.join(missing_attach)))
        if missing_wire:
            lines.append(MSG_DIO_WARN_WIRE.format(labels=SEP_COMMA_SPACE.join(missing_wire)))
        lines.append(TEXT_EMPTY)
        lines.append(MSG_DIO_WARN_PROMPT)
        return messagebox.askyesno(TITLE_DIO_WARN, NEWLINE.join(lines))

    def _device_type_id_from_name(self, name: str) -> Optional[int]:
        key = name.strip().upper()
        if not key:
            return None
        if "MOTORCONTROLLER" in key:
            return DEVTYPE_MOTOR
        if "ENCODER" == key or "ENCODEREXTERNAL" in key:
            return DEVTYPE_ENCODER
        if "GYROSENSOR" in key:
            return DEVTYPE_GYRO
        if "POWERDISTRIBUTIONMODULE" in key:
            return DEVTYPE_POWER
        if "MISCELLANEOUS" in key:
            return DEVTYPE_MISC
        if "NEO" in key or "FLEX" in key or "KRAKEN" in key or "FALCON" in key:
            return DEVTYPE_MOTOR
        if "CANCODER" in key or "ENCODER" in key:
            return DEVTYPE_ENCODER
        if "CANDLE" in key:
            return DEVTYPE_MISC
        if "PDH" in key or "PDP" in key or "POWERDISTRIBUTION" in key:
            return DEVTYPE_POWER
        if "PIGEON" in key or "IMU" in key or "GYRO" in key:
            return DEVTYPE_GYRO
        if "ROBORIO" in key or "ROBOTCONTROLLER" in key:
            return DEVTYPE_ROBORIO
        return None

    def _device_def_type_from_device_name(self, name: str) -> str:
        key = name.strip().upper()
        if not key:
            return ""
        if "MOTORCONTROLLER" in key:
            return profile_consts.TYPE_MOTOR if profile_consts is not None else "motor"
        if "ENCODER" == key or "ENCODEREXTERNAL" in key:
            return (
                profile_consts.TYPE_ENCODER_EXTERNAL
                if profile_consts is not None
                else "encoderExternal"
            )
        if "NEO" in key or "FLEX" in key or "KRAKEN" in key or "FALCON" in key:
            return profile_consts.TYPE_MOTOR if profile_consts is not None else "motor"
        if "CANCODER" in key or "ENCODER" in key:
            return profile_consts.TYPE_ENCODER_EXTERNAL if profile_consts is not None else "encoderExternal"
        return ""

    def _diagram_snapshot(self) -> Dict[str, object]:
        """
        NAME
            _diagram_snapshot - Capture editor layout metadata for persistence.

        RETURNS
            Diagram metadata dict stored under the profile name.
        """
        return self._diagram_snapshot_from_nodes(self._nodes)

    def _topology_snapshot(self) -> Dict[str, object]:
        """
        NAME
            _topology_snapshot - Capture the canonical topology graph for persistence.
        """
        return self._topology_snapshot_from_nodes(self._nodes)

    def _topology_snapshot_minimal(self) -> Dict[str, object]:
        """
        NAME
            _topology_snapshot_minimal - Capture a reduced canonical topology graph.
        """
        devices = [node for node in self._nodes if node.node_type != "callout"]
        return self._topology_snapshot_from_nodes(devices)

    def _topology_snapshot_from_nodes(self, nodes_list: List[Node]) -> Dict[str, object]:
        """
        NAME
            _topology_snapshot_from_nodes - Translate editor state into topology graph data.
        """
        topology_nodes: List[Dict[str, object]] = []
        node_by_key = {node.key: node for node in nodes_list if node.node_type != "callout"}
        for node in nodes_list:
            if node.node_type == "callout":
                continue
            layout = {
                KEY_TOPOLOGY_BUS: node.bus_index,
                KEY_TOPOLOGY_ROW: node.row,
                KEY_TOPOLOGY_X: float(node.x),
            }
            if isinstance(node.free_y, (int, float)):
                layout[KEY_TOPOLOGY_Y] = float(node.free_y)
                layout[KEY_TOPOLOGY_Y_RELATIVE] = bool(
                    getattr(node, "free_y_relative", True)
                )
            if self._is_registry_device_node(node):
                topology_nodes.append(
                    {
                        KEY_NODE_KEY: node.key,
                        KEY_TOPOLOGY_OBJECT_TYPE: TOPOLOGY_NODE_DEVICE,
                        KEY_TOPOLOGY_NODE_TYPE: TOPOLOGY_NODE_DEVICE,
                        KEY_TOPOLOGY_NODE_CLASS: TOPOLOGY_NODE_CLASS_DEVICE,
                        KEY_TOPOLOGY_DEVICE_REF: node.label,
                        KEY_TOPOLOGY_LAYOUT: layout,
                    }
                )
                continue
            object_type = self._topology_node_type_for_editor_node(node)
            topology_nodes.append(
                {
                    KEY_NODE_KEY: node.key,
                    KEY_LABEL: node.label,
                    KEY_CATEGORY: node.category,
                    KEY_TOPOLOGY_OBJECT_TYPE: object_type,
                    KEY_TOPOLOGY_NODE_TYPE: object_type,
                    KEY_TOPOLOGY_NODE_CLASS: TOPOLOGY_NODE_CLASS_INFRASTRUCTURE,
                    KEY_VENDOR: node.vendor,
                    KEY_MODEL: node.motor,
                    KEY_TOPOLOGY_LAYOUT: layout,
                }
            )
        edges = self._topology_edges_from_editor_state(node_by_key)
        callouts = [
            {
                "text": node.callout_text,
                "targetType": node.callout_target_type,
                "targetBus": node.callout_target_bus,
                "targetNodeKey": node.callout_target_node_key,
                "targetCategory": node.callout_target_category,
                "targetLabel": node.callout_target_label,
                "targetId": node.callout_target_id,
                "x": node.x,
                "y": node.callout_y,
                "freeY": node.free_y,
                "freeYRelative": node.free_y is not None,
                "bus": node.bus_index,
                "row": node.row,
                "scale": node.scale,
                "tags": list(node.tags or []),
            }
            for node in nodes_list
            if node.node_type == "callout"
        ]
        self._ensure_bus_connector_sides(len(self._bus_offsets))
        return {
            KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
            KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
            KEY_TOPOLOGY_NODES: topology_nodes,
            KEY_TOPOLOGY_EDGES: edges,
            KEY_TOPOLOGY_VIEW: {
                "busOffsets": list(self._bus_offsets),
                "busCount": len(self._bus_offsets),
                "busSpacing": self._bus_spacing,
                "busLefts": list(self._bus_lefts),
                "busRights": list(self._bus_rights),
                "busConnectors": list(self._bus_connectors),
                KEY_DIAGRAM_BUS_CONNECTOR_SIDES: list(self._bus_connector_sides),
                "panY": self._pan_y,
                "zoom": self._zoom,
                KEY_DIAGRAM_ETHERNET_LINKS: [{"a": a, "b": b} for a, b in self._ethernet_links],
                "canLinks": list(self._can_bus_links),
                "deviceLinks": list(self._cannect_device_links),
                KEY_TOPOLOGY_FILTERS: sorted(self._active_connection_filters()),
                "callouts": callouts,
            },
        }

    def _topology_node_type_for_editor_node(self, node: Node) -> str:
        """
        NAME
            _topology_node_type_for_editor_node - Map an editor node to a topology node type.
        """
        if node.category == DIAGRAM_CATEGORY_ANALYZER:
            return TOPOLOGY_NODE_ANALYZER
        if node.category in (DIAGRAM_CATEGORY_CANNECT_DIRECT, DIAGRAM_CATEGORY_CANNECT_INJECT):
            return TOPOLOGY_NODE_JUNCTION
        return TOPOLOGY_NODE_VIRTUAL

    def _topology_node_class_for_editor_node(self, node: Node) -> str:
        """
        NAME
            _topology_node_class_for_editor_node - Classify one editor node using the shared graph split.
        """
        if node.node_type == NODE_TYPE_CALLOUT:
            return "callout"
        return (
            TOPOLOGY_NODE_CLASS_INFRASTRUCTURE
            if self._is_infrastructure_category(node.category or EMPTY_STRING)
            else TOPOLOGY_NODE_CLASS_DEVICE
        )

    def _active_connection_filters(self) -> set[str]:
        """
        NAME
            _active_connection_filters - Return the enabled connection filter keys.
        """
        vars_map = getattr(self, "_connection_filter_vars", None)
        if not isinstance(vars_map, dict):
            return set(TOPOLOGY_FILTERS_ORDER)
        return {
            filter_key
            for filter_key, var in vars_map.items()
            if bool(var.get())
        }

    def _on_connection_filters_changed(self) -> None:
        """
        NAME
            _on_connection_filters_changed - Redraw after a filter toggle.
        """
        self._redraw_canvas()

    def _enable_all_connection_filters(self) -> None:
        """
        NAME
            _enable_all_connection_filters - Enable every connection filter.
        """
        for var in self._connection_filter_vars.values():
            var.set(True)
        self._redraw_canvas()

    def _disable_all_connection_filters(self) -> None:
        """
        NAME
            _disable_all_connection_filters - Disable every connection filter.
        """
        for var in self._connection_filter_vars.values():
            var.set(False)
        self._redraw_canvas()

    def _connection_filter_allows(self, filter_key: str) -> bool:
        """
        NAME
            _connection_filter_allows - Check whether one filter category is enabled.
        """
        var = self._connection_filter_vars.get(filter_key)
        return bool(var.get()) if var is not None else False

    def _topology_edges_from_editor_state(self, node_by_key: Dict[int, Node]) -> List[Dict[str, object]]:
        """
        NAME
            _topology_edges_from_editor_state - Build canonical edges from editor links.
        """
        edges: List[Dict[str, object]] = []
        seen: set[Tuple[int, str, int, str]] = set()
        edge_index = 1
        for entry in self._neighbor_ports:
            if not isinstance(entry, dict):
                continue
            from_node = entry.get(KEY_LINK_NODE)
            to_node = entry.get(KEY_LINK_NEIGHBOR)
            from_port = entry.get(KEY_LINK_PORT)
            to_port = entry.get(KEY_LINK_NEIGHBOR_PORT)
            if not isinstance(from_node, int) or not isinstance(to_node, int):
                continue
            if not isinstance(from_port, str) or not isinstance(to_port, str):
                continue
            reverse_key = (to_node, to_port, from_node, from_port)
            current_key = (from_node, from_port, to_node, to_port)
            if current_key in seen or reverse_key in seen:
                continue
            seen.add(current_key)
            edges.append(
                {
                    KEY_TOPOLOGY_EDGE_ID: f"edge_{edge_index}",
                    KEY_TOPOLOGY_FROM_NODE: from_node,
                    KEY_TOPOLOGY_FROM_PORT: from_port,
                    KEY_TOPOLOGY_TO_NODE: to_node,
                    KEY_TOPOLOGY_TO_PORT: to_port,
                    KEY_TOPOLOGY_EDGE_TYPE: self._topology_edge_type_for_ports(
                        node_by_key.get(from_node),
                        node_by_key.get(to_node),
                        from_port,
                        to_port,
                    ),
                }
            )
            edge_index += 1
        for entry in self._dio_wiring_links:
            if not isinstance(entry, dict):
                continue
            from_node = entry.get(KEY_LINK_ROBORIO)
            to_node = entry.get(KEY_LINK_DEVICE)
            if not isinstance(from_node, int) or not isinstance(to_node, int):
                continue
            edges.append(
                {
                    KEY_TOPOLOGY_EDGE_ID: f"edge_{edge_index}",
                    KEY_TOPOLOGY_FROM_NODE: from_node,
                    KEY_TOPOLOGY_FROM_PORT: KEY_DIO.lower(),
                    KEY_TOPOLOGY_TO_NODE: to_node,
                    KEY_TOPOLOGY_TO_PORT: KEY_DIO.lower(),
                    KEY_TOPOLOGY_EDGE_TYPE: TOPOLOGY_EDGE_DIO,
                }
            )
            edge_index += 1
        for entry in self._power_links:
            link = self._normalize_power_link(entry)
            if link is None:
                continue
            edges.append(
                {
                    KEY_TOPOLOGY_EDGE_ID: f"edge_{edge_index}",
                    KEY_TOPOLOGY_FROM_NODE: link[KEY_LINK_A],
                    KEY_TOPOLOGY_FROM_PORT: KEY_POWER,
                    KEY_TOPOLOGY_TO_NODE: link[KEY_LINK_B],
                    KEY_TOPOLOGY_TO_PORT: KEY_POWER,
                    KEY_TOPOLOGY_EDGE_TYPE: TOPOLOGY_EDGE_POWER,
                }
            )
            edge_index += 1
        for entry in self._attachment_links:
            if not isinstance(entry, dict):
                continue
            from_node = entry.get(KEY_LINK_DEVICE)
            to_node = entry.get(KEY_LINK_ATTACHMENT)
            if not isinstance(from_node, int) or not isinstance(to_node, int):
                continue
            edges.append(
                {
                    KEY_TOPOLOGY_EDGE_ID: f"edge_{edge_index}",
                    KEY_TOPOLOGY_FROM_NODE: from_node,
                    KEY_TOPOLOGY_FROM_PORT: KEY_LINK_ATTACHMENT,
                    KEY_TOPOLOGY_TO_NODE: to_node,
                    KEY_TOPOLOGY_TO_PORT: KEY_LINK_ATTACHMENT,
                    KEY_TOPOLOGY_EDGE_TYPE: TOPOLOGY_EDGE_VIRTUAL,
                }
            )
            edge_index += 1
        return edges

    def _topology_edge_type_for_ports(
        self,
        from_node: Optional[Node],
        to_node: Optional[Node],
        from_port: str,
        to_port: str,
    ) -> str:
        """
        NAME
            _topology_edge_type_for_ports - Infer canonical edge type from ports/nodes.
        """
        port_names = {from_port.lower(), to_port.lower()}
        if "tap" in port_names or (
            from_node is not None and from_node.category == DIAGRAM_CATEGORY_ANALYZER
        ) or (
            to_node is not None and to_node.category == DIAGRAM_CATEGORY_ANALYZER
        ):
            return TOPOLOGY_EDGE_CAN_TAP
        if any(name.startswith("drop") or name.startswith("branch") for name in port_names):
            return TOPOLOGY_EDGE_CAN_DROP
        return TOPOLOGY_EDGE_CAN_TRUNK

    def _topology_entry_from_legacy_diagram(self, diagram: object) -> Dict[str, object]:
        """
        NAME
            _topology_entry_from_legacy_diagram - Convert legacy diagram metadata to topology.
        """
        if not isinstance(diagram, dict):
            return {
                KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_NODES: [],
                KEY_TOPOLOGY_EDGES: [],
                KEY_TOPOLOGY_VIEW: {},
            }
        legacy_nodes = diagram.get(KEY_DIAGRAM_NODES)
        nodes: List[Node] = []
        if isinstance(legacy_nodes, list):
            for entry in legacy_nodes:
                if not isinstance(entry, dict):
                    continue
                node_type = str(
                    entry.get(KEY_TOPOLOGY_OBJECT_TYPE)
                    or entry.get(KEY_TOPOLOGY_NODE_TYPE)
                    or "device"
                ).strip()
                if node_type == "callout":
                    nodes.append(
                        Node(
                            key=int(entry.get(KEY_NODE_KEY, 0)),
                            category="callout",
                            label=str(entry.get("text", EMPTY_STRING)),
                            can_id=CAN_ID_DIAGRAM_DEFAULT,
                            node_type="callout",
                            x=float(entry.get(KEY_TOPOLOGY_X, 0.0)),
                            row=int(entry.get(KEY_TOPOLOGY_ROW, 0)),
                            bus_index=int(entry.get(KEY_TOPOLOGY_BUS, 0)),
                            scale=float(entry.get("scale", 1.0)),
                            callout_text=str(entry.get("text", EMPTY_STRING)),
                            callout_target_type=str(entry.get("targetType", "node")),
                            callout_target_bus=int(entry.get("targetBus", 0) or 0),
                            callout_target_node_key=entry.get("targetNodeKey"),
                            callout_target_category=str(entry.get("targetCategory", EMPTY_STRING)),
                            callout_target_label=str(entry.get("targetLabel", EMPTY_STRING)),
                            callout_target_id=entry.get("targetId"),
                            callout_y=float(entry.get(KEY_TOPOLOGY_Y, 0.0)),
                            free_y=float(entry.get("freeY"))
                            if isinstance(entry.get("freeY"), (int, float))
                            else None,
                        )
                    )
                    continue
                nodes.append(
                    Node(
                        key=int(entry.get(KEY_NODE_KEY, 0)),
                        category=str(entry.get("category", GENERIC_CATEGORY)),
                        label=str(entry.get(KEY_LABEL, EMPTY_STRING)),
                        can_id=int(entry.get(KEY_ID, CAN_ID_DIAGRAM_DEFAULT))
                        if str(entry.get(KEY_ID, EMPTY_STRING)).strip() != EMPTY_STRING
                        else CAN_ID_DIAGRAM_DEFAULT,
                        node_type="device",
                        vendor=str(entry.get(KEY_VENDOR, EMPTY_STRING)),
                        motor=str(entry.get(KEY_MODEL, EMPTY_STRING)),
                        x=float(entry.get(KEY_TOPOLOGY_X, 0.0)),
                        row=int(entry.get(KEY_TOPOLOGY_ROW, 0)),
                        bus_index=int(entry.get(KEY_TOPOLOGY_BUS, 0)),
                        scale=float(entry.get("scale", 1.0)),
                        free_y=float(entry.get("freeY"))
                        if isinstance(entry.get("freeY"), (int, float))
                        else None,
                        profile_visible=bool(entry.get("profileVisible", True)),
                    )
                )
        saved_neighbor_links = deepcopy(diagram.get(KEY_DIAGRAM_NEIGHBOR_LINKS, []))
        saved_neighbor_ports = deepcopy(diagram.get(KEY_DIAGRAM_NEIGHBOR_PORTS, []))
        saved_dio_links = deepcopy(diagram.get(KEY_DIO_LINKS, []))
        saved_ethernet_links = deepcopy(diagram.get(KEY_DIAGRAM_ETHERNET_LINKS, []))
        saved_can_links = deepcopy(diagram.get("canLinks", []))
        saved_device_links = deepcopy(diagram.get("deviceLinks", []))
        saved_attachment_links = deepcopy(diagram.get(KEY_ATTACHMENT_LINKS, []))
        saved_power_links = deepcopy(diagram.get(KEY_POWER_LINKS, []))
        original_neighbor_links = self._neighbor_links
        original_neighbor_ports = self._neighbor_ports
        original_dio_links = self._dio_wiring_links
        original_ethernet_links = self._ethernet_links
        original_can_links = self._can_bus_links
        original_device_links = self._cannect_device_links
        original_attachment_links = self._attachment_links
        original_power_links = self._power_links
        try:
            self._neighbor_links = saved_neighbor_links if isinstance(saved_neighbor_links, list) else []
            self._neighbor_ports = saved_neighbor_ports if isinstance(saved_neighbor_ports, list) else []
            self._dio_wiring_links = saved_dio_links if isinstance(saved_dio_links, list) else []
            self._ethernet_links = []
            if isinstance(saved_ethernet_links, list):
                for entry in saved_ethernet_links:
                    if isinstance(entry, dict):
                        a = entry.get("a")
                        b = entry.get("b")
                        if isinstance(a, int) and isinstance(b, int):
                            self._ethernet_links.append((a, b))
            self._can_bus_links = saved_can_links if isinstance(saved_can_links, list) else []
            self._cannect_device_links = (
                saved_device_links if isinstance(saved_device_links, list) else []
            )
            self._attachment_links = (
                saved_attachment_links if isinstance(saved_attachment_links, list) else []
            )
            self._power_links = saved_power_links if isinstance(saved_power_links, list) else []
            return self._topology_snapshot_from_nodes(nodes)
        finally:
            self._neighbor_links = original_neighbor_links
            self._neighbor_ports = original_neighbor_ports
            self._dio_wiring_links = original_dio_links
            self._ethernet_links = original_ethernet_links
            self._can_bus_links = original_can_links
            self._cannect_device_links = original_device_links
            self._attachment_links = original_attachment_links
            self._power_links = original_power_links

    def _diagram_snapshot_minimal(self) -> Dict[str, object]:
        """
        NAME
            _diagram_snapshot_minimal - Capture a minimal diagram snapshot.

        DESCRIPTION
            Emits just enough diagram metadata to keep node positions stable
            without baking in custom bus offsets or callouts.
        """
        devices = [n for n in self._nodes if n.node_type != "callout"]
        bus_count = max((n.bus_index for n in devices), default=0) + 1
        self._ensure_bus_connectors(max(1, bus_count))
        self._ensure_bus_connector_sides(max(1, bus_count))
        snapshot = {
            "busCount": max(1, bus_count),
            "busSpacing": float(self._bus_spacing),
            "panY": 0.0,
            "zoom": 1.0,
            "busConnectors": list(self._bus_connectors),
            KEY_DIAGRAM_BUS_CONNECTOR_SIDES: list(self._bus_connector_sides),
            KEY_DIO_FREEY_MODE: DIO_FREEY_MODE_RAIL,
            "nodes": [
                {
                    "objectType": n.node_type,
                    "nodeType": n.node_type,
                    "nodeClass": self._topology_node_class_for_editor_node(n),
                    "key": n.key,
                    "category": n.category,
                    "label": n.label,
                    "id": n.can_id,
                    "bus": n.bus_index,
                    "row": n.row,
                    "x": n.x,
                    "scale": n.scale,
                    "freeY": n.free_y,
                    "freeYRelative": n.free_y is not None,
                    "tags": list(n.tags) if n.tags else [],
                    "profileVisible": getattr(n, "profile_visible", True),
                }
                for n in devices
            ],
            "ethernetLinks": [{"a": a, "b": b} for a, b in self._ethernet_links],
            "canLinks": list(self._can_bus_links),
            KEY_ATTACHMENT_LINKS: list(self._attachment_links),
            KEY_DIO_LINKS: list(self._dio_wiring_links),
            KEY_POWER_LINKS: list(self._power_links),
            KEY_DIAGRAM_NEIGHBOR_LINKS: list(self._neighbor_links),
            KEY_DIAGRAM_NEIGHBOR_PORTS: list(self._neighbor_ports),
        }
        return snapshot

    def _write_minimal_diagram_metadata(self) -> None:
        """
        NAME
            _write_minimal_diagram_metadata - Save a minimal diagram snapshot.

        DESCRIPTION
            Writes diagram metadata for the current profile back into the
            loaded JSON file, leaving profile device data untouched.
        """
        profile_name = self.entry_profile.get().strip()
        if not profile_name:
            messagebox.showerror("Invalid", "Profile name is required.")
            return
        path = self._profile_source_path
        if not path:
            messagebox.showerror(
                "No Source File",
                "Open a bringup_system.json file first, then retry.",
            )
            return
        try:
            data = self._load_config_payload(path)
            schema_version = data.get("schema_version")
            if schema_version not in self._accepted_schema_versions():
                messagebox.showerror(
                    "Invalid",
                    "Profile schema_version mismatch "
                    f"(supported {self._accepted_schema_versions()}, got {schema_version}).",
                )
                return
            data_version = data.get("data_version")
            if not isinstance(data_version, str) or not data_version.strip():
                messagebox.showerror("Invalid", "Profile data_version missing or empty.")
                return
            data_hash = data.get("data_hash")
            if not isinstance(data_hash, str) or not data_hash.strip():
                proceed = messagebox.askyesno(
                    "Hash Missing",
                    "Profile data_hash is missing or empty. Open anyway to repair?",
                )
                if not proceed:
                    return
            else:
                computed_hash = self._compute_data_hash(data)
                if data_hash != computed_hash:
                    proceed = messagebox.askyesno(
                        "Hash Mismatch",
                        "Profile data_hash mismatch. Open anyway to repair?",
                    )
                    if not proceed:
                        return
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open file: {exc}")
            return
        profiles = data.get("profiles")
        if not isinstance(profiles, dict) or profile_name not in profiles:
            messagebox.showerror(
                "Missing Profile",
                f"Profile '{profile_name}' not found in the source file.",
            )
            return
        if not self._confirm_neighbors_current_for_save():
            return
        if replace_profile_topology_entry is not None:
            replace_profile_topology_entry(
                data,
                profile_name,
                self._topology_snapshot_minimal(),
            )
        else:
            topology = data.get(KEY_TOPOLOGY)
            if not isinstance(topology, dict):
                topology = {
                    KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                    KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                    KEY_TOPOLOGY_PROFILES: {},
                }
            topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
            if not isinstance(topology_profiles, dict):
                topology_profiles = {}
            topology_profiles[profile_name] = self._topology_snapshot_minimal()
            data[KEY_TOPOLOGY] = {
                KEY_TOPOLOGY_VERSION: TOPOLOGY_VERSION,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: topology_profiles,
            }
        try:
            self._save_config_payload(path, data)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save file: {exc}")
            return
        self._dirty = False
        self._load_profile_from_path(path, ask_profile=False, confirm_discard=False, selected_name=profile_name)
        messagebox.showinfo(
            "Diagram Metadata",
            f"Minimal diagram metadata written for '{profile_name}'.",
        )

    def _diagram_snapshot_from_nodes(self, nodes_list: List[Node]) -> Dict[str, object]:
        """
        NAME
            _diagram_snapshot_from_nodes - Capture diagram metadata for a node subset.
        """
        nodes: List[Dict[str, object]] = []
        for node in nodes_list:
            if node.node_type == "callout":
                nodes.append(
                    {
                        "objectType": "callout",
                        "nodeType": "callout",
                        "nodeClass": "callout",
                        "key": node.key,
                        "text": node.callout_text,
                        "targetType": node.callout_target_type,
                        "targetBus": node.callout_target_bus,
                        "targetNodeKey": node.callout_target_node_key,
                        "targetCategory": node.callout_target_category,
                        "targetLabel": node.callout_target_label,
                        "targetId": node.callout_target_id,
                        "x": node.x,
                        "y": self._node_center_y_unscaled(node),
                        "freeY": node.free_y,
                        "freeYRelative": node.free_y is not None,
                        "bus": node.bus_index,
                        "row": node.row,
                        "scale": node.scale,
                        "tags": list(node.tags or []),
                        "profileVisible": getattr(node, "profile_visible", True),
                    }
                )
            else:
                nodes.append(
                    {
                        "objectType": node.node_type,
                        "nodeType": node.node_type,
                        "nodeClass": self._topology_node_class_for_editor_node(node),
                        "key": node.key,
                        "category": node.category,
                        "label": node.label,
                        "id": node.can_id,
                        "bus": node.bus_index,
                        "row": node.row,
                        "x": node.x,
                        "freeY": node.free_y,
                        "freeYRelative": node.free_y is not None,
                        "scale": node.scale,
                        "tags": list(node.tags or []),
                        "profileVisible": getattr(node, "profile_visible", True),
                    }
                )
        self._ensure_bus_connector_sides(len(self._bus_offsets))
        return {
            "busOffsets": list(self._bus_offsets),
            "busCount": len(self._bus_offsets),
            "busSpacing": self._bus_spacing,
            "busLefts": list(self._bus_lefts),
            "busRights": list(self._bus_rights),
            "busConnectors": list(self._bus_connectors),
            KEY_DIAGRAM_BUS_CONNECTOR_SIDES: list(self._bus_connector_sides),
            "panY": self._pan_y,
            "zoom": self._zoom,
            KEY_DIO_FREEY_MODE: DIO_FREEY_MODE_RAIL,
            "nodes": nodes,
            "ethernetLinks": [{"a": a, "b": b} for a, b in self._ethernet_links],
            "canLinks": list(self._can_bus_links),
            "deviceLinks": list(self._cannect_device_links),
            KEY_ATTACHMENT_LINKS: list(self._attachment_links),
            KEY_DIO_LINKS: list(self._dio_wiring_links),
            KEY_POWER_LINKS: list(self._power_links),
            KEY_DIAGRAM_NEIGHBOR_LINKS: list(self._neighbor_links),
            KEY_DIAGRAM_NEIGHBOR_PORTS: list(self._neighbor_ports),
        }

    def _apply_diagram_snapshot(self, diagram: Dict[str, object]) -> None:
        """
        NAME
            _apply_diagram_snapshot - Restore editor layout metadata.
        """
        bus_offsets = diagram.get("busOffsets")
        if isinstance(bus_offsets, list) and bus_offsets:
            self._bus_offsets = [float(x) for x in bus_offsets if isinstance(x, (int, float))]
        else:
            bus_count = diagram.get("busCount")
            if isinstance(bus_count, int) and bus_count > 0:
                self._bus_offsets = [i * self._bus_spacing for i in range(bus_count)]
        spacing = diagram.get("busSpacing")
        if isinstance(spacing, (int, float)) and spacing > 0:
            self._bus_spacing = float(spacing)
            self._bus_offsets = [i * self._bus_spacing for i in range(len(self._bus_offsets))]
        bus_lefts = diagram.get("busLefts")
        bus_rights = diagram.get("busRights")
        if isinstance(bus_lefts, list):
            self._bus_lefts = [float(x) for x in bus_lefts if isinstance(x, (int, float))]
        if isinstance(bus_rights, list):
            self._bus_rights = [float(x) for x in bus_rights if isinstance(x, (int, float))]
        bus_connectors = diagram.get("busConnectors")
        if isinstance(bus_connectors, list):
            self._bus_connectors = [bool(x) for x in bus_connectors]
        else:
            self._bus_connectors = []
        self._ensure_bus_connectors(len(self._bus_offsets))
        bus_connector_sides = diagram.get(KEY_DIAGRAM_BUS_CONNECTOR_SIDES)
        if isinstance(bus_connector_sides, list):
            self._bus_connector_sides = list(bus_connector_sides)
        else:
            self._bus_connector_sides = []
        self._ensure_bus_connector_sides(len(self._bus_offsets))
        pan_y = diagram.get("panY")
        if isinstance(pan_y, (int, float)):
            self._pan_y = float(pan_y)
        zoom = diagram.get("zoom")
        if isinstance(zoom, (int, float)):
            self._zoom = max(0.1, min(2.0, float(zoom)))
        dio_free_y_mode = str(diagram.get(KEY_DIO_FREEY_MODE, "")).strip()
        dio_free_y_legacy = dio_free_y_mode != DIO_FREEY_MODE_RAIL

        # Drop existing callout/diagram-only nodes before applying snapshot data.
        self._nodes = [n for n in self._nodes if self._is_registry_device_node(n)]
        device_keys = {n.key for n in self._nodes}

        nodes = diagram.get("nodes")
        device_key_remap: Dict[int, int] = {}
        loaded_callouts = False
        pending_callout_resolve: List[Node] = []
        if isinstance(nodes, list):
            reserved_keys: set[int] = set()
            device_entries: List[Dict[str, object]] = []
            for entry in nodes:
                if not isinstance(entry, dict):
                    continue
                node_type = (
                    entry.get(KEY_OBJECT_TYPE)
                    or entry.get("nodeType")
                    or entry.get("node_type")
                    or "device"
                )
                if node_type == "callout" or ("text" in entry and "targetType" in entry):
                    key = entry.get("key")
                    if isinstance(key, int):
                        reserved_keys.add(key)
                    continue
                if node_type == "diagram" or entry.get("profileVisible", True) is False:
                    key = entry.get("key")
                    if isinstance(key, int):
                        reserved_keys.add(key)
                    continue
                device_entries.append(entry)
            device_by_tuple = {
                (n.category, n.label, n.can_id): n
                for n in self._device_nodes()
                if self._is_registry_device_node(n)
            }
            used_keys: set[int] = set()
            for entry in device_entries:
                key = entry.get("key")
                if not isinstance(key, int):
                    continue
                cat = entry.get("category")
                label = entry.get("label")
                node_id = entry.get("id")
                match = device_by_tuple.get((cat, label, node_id))
                if match is None:
                    continue
                if key not in reserved_keys and key not in used_keys:
                    match.key = key
                device_key_remap[key] = match.key
                used_keys.add(match.key)
            if self._nodes:
                self._next_key = max(self._next_key, max(n.key for n in self._nodes) + 1)
            device_keys = {n.key for n in self._nodes}
        if isinstance(nodes, list):
            for entry in nodes:
                if not isinstance(entry, dict):
                    continue
                node_type = (
                    entry.get(KEY_OBJECT_TYPE)
                    or entry.get("nodeType")
                    or entry.get("node_type")
                    or "device"
                )
                profile_visible = entry.get("profileVisible", True)
                if node_type == "callout" or ("text" in entry and "targetType" in entry):
                    callout_y = float(entry.get("y", entry.get("callout_y", 0.0)))
                    free_y = entry.get("freeY")
                    free_rel = entry.get("freeYRelative")
                    bus_index = entry.get("bus")
                    row = entry.get("row")
                    if not isinstance(bus_index, int) or not isinstance(row, int):
                        bus_index, row = self._nearest_bus_and_row_from_offset(callout_y)
                    free_val = None
                    if isinstance(free_y, (int, float)):
                        # TODO(major-refactor): Remove legacy freeY absolute->relative migration after re-saving profiles.
                        free_val = float(free_y)
                        if self._bus_offsets:
                            bus_offset = self._bus_offsets[min(max(int(bus_index), 0), len(self._bus_offsets) - 1)]
                            if free_rel is True:
                                free_val = float(free_y)
                            elif abs(free_val) > 200.0 or abs(free_val - callout_y) < 0.5:
                                free_val = free_val - bus_offset
                    callout = Node(
                        key=self._next_key,
                        category="callout",
                        label=str(entry.get("text", "")),
                        can_id=-1,
                        node_type="callout",
                        x=float(entry.get("x", 0.0)),
                        row=int(row),
                        bus_index=int(bus_index),
                        scale=float(entry.get("scale", 1.0)),
                        callout_text=str(entry.get("text", "")),
                        callout_target_type=str(entry.get("targetType", entry.get("callout_target_type", "node"))),
                        callout_target_bus=int(entry.get("targetBus", entry.get("callout_target_bus", 0)) or 0),
                        callout_target_node_key=entry.get("targetNodeKey", entry.get("callout_target_node_key")),
                        callout_target_category=str(entry.get("targetCategory", "")),
                        callout_target_label=str(entry.get("targetLabel", "")),
                        callout_target_id=entry.get("targetId"),
                        callout_y=callout_y,
                        free_y=free_val,
                        tags=self._normalize_tags(entry.get("tags", [])),
                    )
                    self._next_key = max(self._next_key, callout.key + 1)
                    self._nodes.append(callout)
                    pending_callout_resolve.append(callout)
                    loaded_callouts = True
                    continue
                if node_type == "diagram" or profile_visible is False:
                    bus = entry.get("bus")
                    row = entry.get("row")
                    x = entry.get("x")
                    scale = entry.get("scale")
                    free_y = entry.get("freeY")
                    free_rel = entry.get("freeYRelative")
                    key = entry.get("key")
                    if not isinstance(key, int):
                        key = self._next_key
                    node = Node(
                        key=key,
                        category=str(entry.get("category", "cannect_direct")),
                        label=str(entry.get("label", "CANnect Direct")),
                        can_id=int(entry.get("id", -1)) if str(entry.get("id", "")).strip() != "" else -1,
                        node_type="diagram",
                        vendor=str(entry.get("vendor", "SWYFT")),
                        device_type=str(entry.get("device_type", "")),
                        motor=str(entry.get("motor", "")),
                        limits=entry.get("limits") if isinstance(entry.get("limits"), dict) else None,
                        terminator=entry.get("terminator") if isinstance(entry.get("terminator"), bool) else None,
                        x=float(x) if isinstance(x, (int, float)) else 0.0,
                        row=int(row) if isinstance(row, int) else 0,
                        bus_index=int(bus) if isinstance(bus, int) else 0,
                        scale=max(0.6, min(2.0, float(scale)))
                        if isinstance(scale, (int, float))
                        else 1.0,
                        free_y=None,
                        tags=self._normalize_tags(entry.get("tags", [])),
                        profile_visible=False,
                    )
                    if isinstance(free_y, (int, float)):
                        free_val = float(free_y)
                        if self._bus_offsets:
                            bus_offset = self._bus_offsets[
                                min(max(node.bus_index, 0), len(self._bus_offsets) - 1)
                            ]
                            if free_rel is True:
                                free_val = float(free_y)
                            elif abs(free_val) > 200.0 or abs(free_val - bus_offset) < abs(free_val):
                                free_val = free_val - bus_offset
                        node.free_y = free_val
                    self._next_key = max(self._next_key, int(key) + 1)
                    self._nodes.append(node)
                    continue
                cat = entry.get("category")
                label = entry.get("label")
                node_id = entry.get("id")
                for node in self._device_nodes():
                    if not self._is_registry_device_node(node):
                        continue
                    if node.category == cat and node.label == label and node.can_id == node_id:
                        tags_raw = entry.get("tags", None)
                        tags = node.tags if tags_raw is None else self._normalize_tags(tags_raw)
                        bus = entry.get("bus")
                        row = entry.get("row")
                        x = entry.get("x")
                        if isinstance(bus, int):
                            node.bus_index = bus
                        if isinstance(row, int):
                            node.row = row
                        if isinstance(x, (int, float)):
                            node.x = float(x)
                        scale = entry.get("scale")
                        if isinstance(scale, (int, float)):
                            node.scale = max(0.6, min(2.0, float(scale)))
                        free_y = entry.get("freeY")
                        free_rel = entry.get("freeYRelative")
                        if isinstance(free_y, (int, float)):
                            # TODO(major-refactor): Remove legacy freeY absolute->relative migration after re-saving profiles.
                            free_val = float(free_y)
                            if self._bus_offsets:
                                bus_offset = self._bus_offsets[min(max(node.bus_index, 0), len(self._bus_offsets) - 1)]
                                if free_rel is True:
                                    free_val = float(free_y)
                                elif abs(free_val) > 200.0 or abs(free_val - bus_offset) < abs(free_val):
                                    free_val = free_val - bus_offset
                            if dio_free_y_legacy and self._is_dio_node(node):
                                free_val = free_val - DIO_RAIL_OFFSET
                            node.free_y = free_val
                        node.tags = tags
                        node.profile_visible = bool(entry.get("profileVisible", True))
                        key = entry.get("key")
                        if isinstance(key, int) and key in device_key_remap:
                            node.key = device_key_remap[key]
                        break

        # Legacy format: convert callouts list into callout nodes.
        callouts = diagram.get("callouts")
        if not loaded_callouts and isinstance(callouts, list):
            for entry in callouts:
                if not isinstance(entry, dict):
                    continue
                callout_y = float(entry.get("y", 0.0))
                free_y = entry.get("freeY")
                free_rel = entry.get("freeYRelative")
                bus_index = entry.get("bus")
                row = entry.get("row")
                if not isinstance(bus_index, int) or not isinstance(row, int):
                    bus_index, row = self._nearest_bus_and_row_from_offset(callout_y)
                free_val = None
                if isinstance(free_y, (int, float)):
                    # TODO(major-refactor): Remove legacy freeY absolute->relative migration after re-saving profiles.
                    free_val = float(free_y)
                    if self._bus_offsets:
                        bus_offset = self._bus_offsets[min(max(int(bus_index), 0), len(self._bus_offsets) - 1)]
                        if free_rel is True:
                            free_val = float(free_y)
                        elif abs(free_val) > 200.0 or abs(free_val - callout_y) < 0.5:
                            free_val = free_val - bus_offset
                callout = Node(
                    key=self._next_key,
                    category="callout",
                    label=str(entry.get("text", "")),
                    can_id=-1,
                    node_type="callout",
                    x=float(entry.get("x", 0.0)),
                    row=int(row),
                    bus_index=int(bus_index),
                    scale=float(entry.get("scale", 1.0)),
                    callout_text=str(entry.get("text", "")),
                    callout_target_type=str(entry.get("targetType", entry.get("target_type", "node"))),
                    callout_target_bus=int(entry.get("targetBus", entry.get("target_bus", 0)) or 0),
                    callout_target_node_key=entry.get("targetNodeKey", entry.get("target_node_key")),
                    callout_target_category=str(entry.get("targetCategory", "")),
                    callout_target_label=str(entry.get("targetLabel", "")),
                    callout_target_id=entry.get("targetId"),
                    callout_y=callout_y,
                    free_y=free_val,
                    tags=self._normalize_tags(entry.get("tags", [])),
                )
                self._next_key += 1
                self._nodes.append(callout)
                pending_callout_resolve.append(callout)

        if pending_callout_resolve:
            node_by_key = {n.key: n for n in self._device_nodes()}
            for callout in pending_callout_resolve:
                if callout.callout_target_type != "node":
                    continue
                target_key = callout.callout_target_node_key
                if isinstance(target_key, int) and target_key in device_key_remap:
                    target_key = device_key_remap[target_key]
                    callout.callout_target_node_key = target_key
                if isinstance(target_key, int) and target_key in node_by_key:
                    target = node_by_key[target_key]
                    callout.callout_target_category = target.category
                    callout.callout_target_label = target.label
                    callout.callout_target_id = target.can_id
                    continue
                resolved = None
                if callout.callout_target_category or callout.callout_target_label:
                    for node in self._device_nodes():
                        if callout.callout_target_category and node.category != callout.callout_target_category:
                            continue
                        if (
                            callout.callout_target_id is not None
                            and node.can_id != callout.callout_target_id
                        ):
                            continue
                        if callout.callout_target_label and node.label != callout.callout_target_label:
                            continue
                        resolved = node
                        break
                if resolved is None:
                    nearest = None
                    best = float("inf")
                    target_bus = int(callout.callout_target_bus or 0)
                    for node in self._device_nodes():
                        if node.bus_index != target_bus:
                            continue
                        dist = abs(node.x - callout.x)
                        if dist < best:
                            best = dist
                            nearest = node
                    if nearest is None:
                        for node in self._device_nodes():
                            dist = abs(node.x - callout.x)
                            if dist < best:
                                best = dist
                                nearest = node
                    resolved = nearest
                if resolved is not None:
                    callout.callout_target_type = "node"
                    callout.callout_target_node_key = resolved.key
                    callout.callout_target_category = resolved.category
                    callout.callout_target_label = resolved.label
                    callout.callout_target_id = resolved.can_id
                else:
                    callout.callout_target_type = "bus"
                    callout.callout_target_bus = int(callout.callout_target_bus or 0)
                    callout.callout_target_node_key = None
        links = diagram.get("ethernetLinks")
        self._ethernet_links = []
        if isinstance(links, list):
            node_keys = {n.key for n in self._nodes}
            for entry in links:
                if isinstance(entry, dict):
                    a = entry.get("a")
                    b = entry.get("b")
                elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                    a, b = entry
                else:
                    continue
                if not isinstance(a, int) or not isinstance(b, int):
                    continue
                if a == b:
                    continue
                if a not in node_keys or b not in node_keys:
                    continue
                link = (min(a, b), max(a, b))
                if link not in self._ethernet_links:
                    self._ethernet_links.append(link)

        self._can_bus_links = []
        if ENABLE_CANNECT_BUS_LINKS:
            can_links = diagram.get("canLinks")
            if isinstance(can_links, list):
                node_keys = {n.key for n in self._nodes}
                for entry in can_links:
                    if not isinstance(entry, dict):
                        continue
                    node_key = entry.get("node")
                    bus_index = entry.get("bus")
                    port = entry.get("port", 1)
                    if not isinstance(node_key, int) or not isinstance(bus_index, int):
                        continue
                    if node_key not in node_keys:
                        continue
                    if bus_index < 0 or bus_index >= len(self._bus_offsets):
                        continue
                    if not isinstance(port, int) or port < 1:
                        port = 1
                    self._can_bus_links.append(
                        {"node": int(node_key), "bus": int(bus_index), "port": int(port)}
                    )

        self._cannect_device_links = []
        device_links = diagram.get("deviceLinks")
        if isinstance(device_links, list):
            node_keys = {n.key for n in self._nodes}
            for entry in device_links:
                if not isinstance(entry, dict):
                    continue
                node_key = entry.get("node")
                device_key = entry.get("device")
                port = entry.get("port", 1)
                if not isinstance(node_key, int) or not isinstance(device_key, int):
                    continue
                if device_key not in node_keys and device_key in device_key_remap:
                    device_key = device_key_remap[device_key]
                if node_key not in node_keys or device_key not in node_keys:
                    continue
                if not isinstance(port, int) or port < 1:
                    port = 1
                self._cannect_device_links.append(
                    {"node": int(node_key), "device": int(device_key), "port": int(port)}
                )

        self._attachment_links = []
        attachment_from_diagram = KEY_ATTACHMENT_LINKS in diagram
        attachment_links = diagram.get(KEY_ATTACHMENT_LINKS)
        if isinstance(attachment_links, list):
            node_keys = {n.key for n in self._nodes}
            for entry in attachment_links:
                if not isinstance(entry, dict):
                    continue
                host_key = entry.get(KEY_LINK_DEVICE)
                attach_key = entry.get(KEY_LINK_ATTACHMENT)
                if not isinstance(host_key, int) or not isinstance(attach_key, int):
                    continue
                if host_key in device_key_remap:
                    host_key = device_key_remap[host_key]
                if attach_key in device_key_remap:
                    attach_key = device_key_remap[attach_key]
                if host_key not in node_keys or attach_key not in node_keys:
                    continue
                self._attachment_links.append(
                    {KEY_LINK_DEVICE: int(host_key), KEY_LINK_ATTACHMENT: int(attach_key)}
                )
        if not attachment_from_diagram:
            self._rebuild_attachment_links_from_registry()

        self._power_links = []
        power_links = diagram.get(KEY_POWER_LINKS)
        if isinstance(power_links, list):
            node_keys = {n.key for n in self._nodes}
            for entry in power_links:
                link = self._normalize_power_link(entry)
                if link is None:
                    continue
                a = link[KEY_LINK_A]
                b = link[KEY_LINK_B]
                if a in device_key_remap:
                    a = device_key_remap[a]
                if b in device_key_remap:
                    b = device_key_remap[b]
                if a not in node_keys or b not in node_keys:
                    continue
                normalized = self._normalize_power_link({KEY_LINK_A: a, KEY_LINK_B: b})
                if normalized is not None:
                    self._power_links.append(normalized)

        self._dio_wiring_links = []
        dio_links = diagram.get(KEY_DIO_LINKS)
        if isinstance(dio_links, list):
            node_keys = {n.key for n in self._nodes}
            for entry in dio_links:
                if not isinstance(entry, dict):
                    continue
                robo_key = entry.get(KEY_LINK_ROBORIO)
                dev_key = entry.get(KEY_LINK_DEVICE)
                if not isinstance(robo_key, int) or not isinstance(dev_key, int):
                    continue
                if robo_key in device_key_remap:
                    robo_key = device_key_remap[robo_key]
                if dev_key in device_key_remap:
                    dev_key = device_key_remap[dev_key]
                if robo_key not in node_keys or dev_key not in node_keys:
                    continue
                self._dio_wiring_links.append(
                    {KEY_LINK_ROBORIO: int(robo_key), KEY_LINK_DEVICE: int(dev_key)}
                )

        self._neighbor_links = self._normalize_neighbor_links(
            diagram.get(KEY_DIAGRAM_NEIGHBOR_LINKS), device_key_remap
        )
        self._neighbor_ports = self._normalize_neighbor_ports(
            diagram.get(KEY_DIAGRAM_NEIGHBOR_PORTS), device_key_remap
        )
        self._mark_neighbors_current()
        self._prune_attachment_links()
        self._prune_power_links()
        self._prune_power_links()
        self._prune_dio_wiring_links()
        self._ensure_dio_wiring_links()
        self._fix_cannect_conflicts(notify=False)
        self._apply_cannect_free_float()
        self._resolve_overlaps()

    def _apply_topology_snapshot(self, topology: Dict[str, object]) -> None:
        """
        NAME
            _apply_topology_snapshot - Restore editor layout from canonical topology data.
        """
        view = topology.get(KEY_TOPOLOGY_VIEW)
        view_dict = view if isinstance(view, dict) else {}
        bus_offsets = view_dict.get("busOffsets")
        if isinstance(bus_offsets, list) and bus_offsets:
            self._bus_offsets = [float(x) for x in bus_offsets if isinstance(x, (int, float))]
        else:
            self._bus_offsets = [0.0]
        spacing = view_dict.get("busSpacing")
        if isinstance(spacing, (int, float)) and spacing > 0:
            self._bus_spacing = float(spacing)
        bus_lefts = view_dict.get("busLefts")
        if isinstance(bus_lefts, list):
            self._bus_lefts = [float(x) for x in bus_lefts if isinstance(x, (int, float))]
        bus_rights = view_dict.get("busRights")
        if isinstance(bus_rights, list):
            self._bus_rights = [float(x) for x in bus_rights if isinstance(x, (int, float))]
        bus_connectors = view_dict.get("busConnectors")
        if isinstance(bus_connectors, list):
            self._bus_connectors = [bool(x) for x in bus_connectors]
        else:
            self._bus_connectors = []
        self._ensure_bus_connectors(len(self._bus_offsets))
        bus_connector_sides = view_dict.get(KEY_DIAGRAM_BUS_CONNECTOR_SIDES)
        if isinstance(bus_connector_sides, list):
            self._bus_connector_sides = list(bus_connector_sides)
        else:
            self._bus_connector_sides = []
        self._ensure_bus_connector_sides(len(self._bus_offsets))
        pan_y = view_dict.get("panY")
        if isinstance(pan_y, (int, float)):
            self._pan_y = float(pan_y)
        zoom = view_dict.get("zoom")
        if isinstance(zoom, (int, float)):
            self._zoom = max(0.1, min(2.0, float(zoom)))
        saved_filters = view_dict.get(KEY_TOPOLOGY_FILTERS)
        if isinstance(saved_filters, list):
            active = {str(entry).strip().lower() for entry in saved_filters if isinstance(entry, str)}
            for filter_key, var in self._connection_filter_vars.items():
                var.set(filter_key in active)

        self._nodes = [node for node in self._nodes if self._is_registry_device_node(node)]
        self._ethernet_links = []
        self._can_bus_links = []
        self._cannect_device_links = []
        self._attachment_links = []
        self._dio_wiring_links = []
        self._power_links = []
        self._neighbor_links = []
        self._neighbor_ports = []
        links = view_dict.get(KEY_DIAGRAM_ETHERNET_LINKS)
        if isinstance(links, list):
            for entry in links:
                if not isinstance(entry, dict):
                    continue
                a = entry.get("a")
                b = entry.get("b")
                if isinstance(a, int) and isinstance(b, int):
                    link = (min(a, b), max(a, b))
                    if link not in self._ethernet_links:
                        self._ethernet_links.append(link)
        can_links = view_dict.get("canLinks")
        if isinstance(can_links, list):
            for entry in can_links:
                if not isinstance(entry, dict):
                    continue
                node_key = entry.get("node")
                bus_index = entry.get("bus")
                port = entry.get("port", 1)
                if not isinstance(node_key, int) or not isinstance(bus_index, int):
                    continue
                if not isinstance(port, int) or port < 1:
                    port = 1
                self._can_bus_links.append(
                    {"node": int(node_key), "bus": int(bus_index), "port": int(port)}
                )
        device_links = view_dict.get("deviceLinks")
        if isinstance(device_links, list):
            for entry in device_links:
                if not isinstance(entry, dict):
                    continue
                node_key = entry.get("node")
                device_key = entry.get("device")
                port = entry.get("port", 1)
                if not isinstance(node_key, int) or not isinstance(device_key, int):
                    continue
                if not isinstance(port, int) or port < 1:
                    port = 1
                self._cannect_device_links.append(
                    {"node": int(node_key), "device": int(device_key), "port": int(port)}
                )

        device_by_label = {
            node.label.lower(): node
            for node in self._device_nodes()
            if self._is_registry_device_node(node)
        }
        reserved_keys: set[int] = set()
        matched_device_labels: set[str] = set()
        topology_nodes = topology.get(KEY_TOPOLOGY_NODES)
        if isinstance(topology_nodes, list):
            for entry in topology_nodes:
                if not isinstance(entry, dict):
                    continue
                key = entry.get(KEY_NODE_KEY)
                layout = entry.get(KEY_TOPOLOGY_LAYOUT)
                layout_dict = layout if isinstance(layout, dict) else {}
                if not isinstance(key, int):
                    continue
                node_type = str(
                    entry.get(KEY_TOPOLOGY_OBJECT_TYPE)
                    or entry.get(KEY_TOPOLOGY_NODE_TYPE)
                    or EMPTY_STRING
                ).strip()
                if node_type == TOPOLOGY_NODE_DEVICE:
                    device_ref_text = str(entry.get(KEY_TOPOLOGY_DEVICE_REF, EMPTY_STRING)).strip()
                    device_ref = device_ref_text.lower()
                    match = device_by_label.get(device_ref)
                    if match is None:
                        infrastructure_match = self._node_from_device_label(device_ref_text)
                        if infrastructure_match is None or not self._is_infrastructure_node(infrastructure_match):
                            continue
                        matched_device_labels.add(device_ref)
                        infrastructure_match.key = key
                        if isinstance(layout_dict.get(KEY_TOPOLOGY_BUS), int):
                            infrastructure_match.bus_index = int(layout_dict.get(KEY_TOPOLOGY_BUS))
                        if isinstance(layout_dict.get(KEY_TOPOLOGY_ROW), int):
                            infrastructure_match.row = int(layout_dict.get(KEY_TOPOLOGY_ROW))
                        if isinstance(layout_dict.get(KEY_TOPOLOGY_X), (int, float)):
                            infrastructure_match.x = float(layout_dict.get(KEY_TOPOLOGY_X))
                        if isinstance(layout_dict.get(KEY_TOPOLOGY_Y), (int, float)):
                            infrastructure_match.free_y = float(layout_dict.get(KEY_TOPOLOGY_Y))
                            infrastructure_match.free_y_relative = bool(
                                layout_dict.get(KEY_TOPOLOGY_Y_RELATIVE, True)
                            )
                            infrastructure_match.topology_y_relative_explicit = (
                                KEY_TOPOLOGY_Y_RELATIVE in layout_dict
                            )
                        self._nodes.append(infrastructure_match)
                        reserved_keys.add(key)
                        continue
                    matched_device_labels.add(device_ref)
                    reserved_keys.add(key)
                    match.key = key
                    if isinstance(layout_dict.get(KEY_TOPOLOGY_BUS), int):
                        match.bus_index = int(layout_dict.get(KEY_TOPOLOGY_BUS))
                    if isinstance(layout_dict.get(KEY_TOPOLOGY_ROW), int):
                        match.row = int(layout_dict.get(KEY_TOPOLOGY_ROW))
                    if isinstance(layout_dict.get(KEY_TOPOLOGY_X), (int, float)):
                        match.x = float(layout_dict.get(KEY_TOPOLOGY_X))
                    if isinstance(layout_dict.get(KEY_TOPOLOGY_Y), (int, float)):
                        match.free_y = float(layout_dict.get(KEY_TOPOLOGY_Y))
                        match.free_y_relative = bool(
                            layout_dict.get(KEY_TOPOLOGY_Y_RELATIVE, True)
                        )
                        match.topology_y_relative_explicit = (
                            KEY_TOPOLOGY_Y_RELATIVE in layout_dict
                        )
                    continue
                label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
                node = Node(
                    key=key,
                    category=self._editor_category_for_topology_node(entry),
                    label=label,
                    can_id=CAN_ID_DIAGRAM_DEFAULT,
                    node_type="diagram",
                    interface=INTERFACE_CAN,
                    vendor=str(entry.get(KEY_VENDOR, EMPTY_STRING)).strip(),
                    device_type=str(entry.get(KEY_DEVICE_TYPE, EMPTY_STRING)).strip(),
                    motor=str(entry.get(KEY_MODEL, EMPTY_STRING)).strip(),
                    x=float(layout_dict.get(KEY_TOPOLOGY_X, 0.0)),
                    row=int(layout_dict.get(KEY_TOPOLOGY_ROW, 0)),
                    bus_index=int(layout_dict.get(KEY_TOPOLOGY_BUS, 0)),
                    free_y=float(layout_dict.get(KEY_TOPOLOGY_Y))
                    if isinstance(layout_dict.get(KEY_TOPOLOGY_Y), (int, float))
                    else None,
                    profile_visible=False,
                )
                node.free_y_relative = bool(layout_dict.get(KEY_TOPOLOGY_Y_RELATIVE, True))
                self._nodes.append(node)
                node.topology_y_relative_explicit = KEY_TOPOLOGY_Y_RELATIVE in layout_dict
                reserved_keys.add(key)

        next_key = max([node.key for node in self._nodes], default=0) + 1
        for node in self._profile_device_nodes():
            label_key = str(node.label or TEXT_EMPTY).strip().lower()
            if not label_key or label_key in matched_device_labels:
                continue
            if node.key < next_key:
                node.key = next_key
                next_key += 1

        self._next_key = max([node.key for node in self._nodes], default=0) + 1

        topology_edges = topology.get(KEY_TOPOLOGY_EDGES)
        if isinstance(topology_edges, list):
            for entry in topology_edges:
                if not isinstance(entry, dict):
                    continue
                from_node = entry.get(KEY_TOPOLOGY_FROM_NODE)
                to_node = entry.get(KEY_TOPOLOGY_TO_NODE)
                from_port = entry.get(KEY_TOPOLOGY_FROM_PORT)
                to_port = entry.get(KEY_TOPOLOGY_TO_PORT)
                edge_type = str(entry.get(KEY_TOPOLOGY_EDGE_TYPE, EMPTY_STRING)).strip()
                if not isinstance(from_node, int) or not isinstance(to_node, int):
                    continue
                if edge_type == TOPOLOGY_EDGE_DIO:
                    self._dio_wiring_links.append(
                        {KEY_LINK_ROBORIO: from_node, KEY_LINK_DEVICE: to_node}
                    )
                    continue
                if edge_type == TOPOLOGY_EDGE_POWER:
                    link = self._normalize_power_link({KEY_LINK_A: from_node, KEY_LINK_B: to_node})
                    if link is not None:
                        self._power_links.append(link)
                    continue
                if edge_type == TOPOLOGY_EDGE_VIRTUAL:
                    self._attachment_links.append(
                        {KEY_LINK_DEVICE: from_node, KEY_LINK_ATTACHMENT: to_node}
                    )
                    continue
                self._neighbor_links.append(
                    {KEY_LINK_A: min(from_node, to_node), KEY_LINK_B: max(from_node, to_node)}
                )
                if isinstance(from_port, str) and isinstance(to_port, str):
                    self._neighbor_ports.append(
                        {
                            KEY_LINK_NODE: from_node,
                            KEY_LINK_PORT: from_port,
                            KEY_LINK_NEIGHBOR: to_node,
                            KEY_LINK_NEIGHBOR_PORT: to_port,
                        }
                    )
                    self._neighbor_ports.append(
                        {
                            KEY_LINK_NODE: to_node,
                            KEY_LINK_PORT: to_port,
                            KEY_LINK_NEIGHBOR: from_node,
                            KEY_LINK_NEIGHBOR_PORT: from_port,
                        }
                    )
        if not self._attachment_links:
            self._rebuild_attachment_links_from_registry()
        self._restore_missing_cannect_bus_links()

        callouts = view_dict.get("callouts")
        if isinstance(callouts, list):
            for entry in callouts:
                if not isinstance(entry, dict):
                    continue
                callout = Node(
                    key=self._next_key,
                    category="callout",
                    label=str(entry.get("text", EMPTY_STRING)),
                    can_id=CAN_ID_DIAGRAM_DEFAULT,
                    node_type="callout",
                    x=float(entry.get("x", 0.0)),
                    row=int(entry.get("row", 0)),
                    bus_index=int(entry.get("bus", 0)),
                    scale=float(entry.get("scale", 1.0)),
                    callout_text=str(entry.get("text", EMPTY_STRING)),
                    callout_target_type=str(entry.get("targetType", "node")),
                    callout_target_bus=int(entry.get("targetBus", 0) or 0),
                    callout_target_node_key=entry.get("targetNodeKey"),
                    callout_target_category=str(entry.get("targetCategory", EMPTY_STRING)),
                    callout_target_label=str(entry.get("targetLabel", EMPTY_STRING)),
                    callout_target_id=entry.get("targetId"),
                    callout_y=float(entry.get("y", 0.0)),
                    free_y=float(entry.get("freeY"))
                    if isinstance(entry.get("freeY"), (int, float))
                    else None,
                    tags=self._normalize_tags(entry.get("tags", [])),
                )
                self._next_key += 1
                self._nodes.append(callout)

        self._mark_neighbors_current()
        self._prune_attachment_links()
        self._prune_power_links()
        self._prune_power_links()
        self._prune_dio_wiring_links()
        self._ensure_dio_wiring_links()
        self._fix_cannect_conflicts(notify=False)
        self._restore_legacy_cannect_free_y_mode()
        self._apply_cannect_free_float()
        self._resolve_overlaps()

    def _editor_category_for_topology_node(self, entry: Dict[str, object]) -> str:
        """
        NAME
            _editor_category_for_topology_node - Map topology node types to editor categories.
        """
        category = str(entry.get(KEY_CATEGORY, EMPTY_STRING)).strip()
        if category:
            return category
        node_type = str(
            entry.get(KEY_TOPOLOGY_OBJECT_TYPE)
            or entry.get(KEY_TOPOLOGY_NODE_TYPE)
            or EMPTY_STRING
        ).strip()
        if node_type == TOPOLOGY_NODE_ANALYZER:
            return DIAGRAM_CATEGORY_ANALYZER
        if node_type == TOPOLOGY_NODE_JUNCTION:
            return DIAGRAM_CATEGORY_CANNECT_DIRECT
        return GENERIC_CATEGORY

    @staticmethod
    def _normalize_neighbor_links(
        entries: object,
        key_remap: Optional[Dict[int, int]] = None,
    ) -> List[Dict[str, int]]:
        """
        NAME
            _normalize_neighbor_links - Validate undirected neighbor links.
        """
        normalized: List[Dict[str, int]] = []
        seen: set[Tuple[int, int]] = set()
        if not isinstance(entries, list):
            return normalized
        key_remap = key_remap or {}
        for entry in entries:
            if isinstance(entry, dict):
                a = entry.get(KEY_LINK_A)
                b = entry.get(KEY_LINK_B)
            elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                a, b = entry
            else:
                continue
            if isinstance(a, int) and a in key_remap:
                a = key_remap[a]
            if isinstance(b, int) and b in key_remap:
                b = key_remap[b]
            if not isinstance(a, int) or not isinstance(b, int) or a == b:
                continue
            pair = (min(a, b), max(a, b))
            if pair in seen:
                continue
            seen.add(pair)
            normalized.append({KEY_LINK_A: pair[0], KEY_LINK_B: pair[1]})
        return normalized

    @staticmethod
    def _normalize_neighbor_ports(
        entries: object,
        key_remap: Optional[Dict[int, int]] = None,
    ) -> List[Dict[str, object]]:
        """
        NAME
            _normalize_neighbor_ports - Validate directed port neighbor links.
        """
        normalized: List[Dict[str, object]] = []
        seen: set[Tuple[str, str, str, str]] = set()
        if not isinstance(entries, list):
            return normalized
        key_remap = key_remap or {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            node = entry.get(KEY_LINK_NODE)
            port = entry.get(KEY_LINK_PORT)
            neighbor = entry.get(KEY_LINK_NEIGHBOR)
            neighbor_port = entry.get(KEY_LINK_NEIGHBOR_PORT)
            if isinstance(node, int) and node in key_remap:
                node = key_remap[node]
            if isinstance(neighbor, int) and neighbor in key_remap:
                neighbor = key_remap[neighbor]
            if not isinstance(node, (int, str)) or not isinstance(neighbor, (int, str)):
                continue
            if not isinstance(port, str) or not isinstance(neighbor_port, str):
                continue
            key = (str(node), port, str(neighbor), neighbor_port)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    KEY_LINK_NODE: node,
                    KEY_LINK_PORT: port,
                    KEY_LINK_NEIGHBOR: neighbor,
                    KEY_LINK_NEIGHBOR_PORT: neighbor_port,
                }
            )
        return normalized

    def _confirm_discard(self) -> bool:
        """
        NAME
            _confirm_discard - Ask before discarding current diagram.
        """
        if not self._dirty:
            return True
        return messagebox.askyesno("Discard Changes", "Discard the current diagram?")

    def _on_close(self) -> None:
        """
        NAME
            _on_close - Confirm before closing when there are unsaved changes.
        """
        if not self._confirm_discard():
            return
        self.destroy()

    def _on_add(self) -> None:
        """
        NAME
            _on_add - Add a new node to the diagram.
        """
        dialog = NodeDialog(self, "Add Node")
        self.wait_window(dialog)
        if not dialog.result:
            return
        self._push_undo()
        data = dialog.result
        category = str(data["category"])
        if category in SINGLETON_CATEGORIES:
            if any(n.category == category for n in self._nodes):
                replace = messagebox.askyesno(
                    DIALOG_TITLE_REPLACE,
                    f"{category} already exists. Replace it?",
                )
                if not replace:
                    return
                self._nodes = [n for n in self._nodes if n.category != category]
        is_diagram_category = category in DIAGRAM_CATEGORIES
        vendor_default, device_type_default, tag_defaults = (TEXT_EMPTY, TEXT_EMPTY, [])
        if is_diagram_category:
            vendor_default, device_type_default, tag_defaults = self._diagram_defaults(category)
        tags = self._normalize_tags(data.get("tags", []))
        if is_diagram_category:
            tags = self._normalize_tags(tags + tag_defaults)
        interface = str(data.get("interface", INTERFACE_CAN)).strip() or INTERFACE_CAN
        node = Node(
            key=self._next_key,
            category=category,
            label=str(data["label"]),
            can_id=CAN_ID_DIAGRAM_DEFAULT if is_diagram_category else int(data["can_id"]),
            node_type=ANALYZER_NODE_TYPE if is_diagram_category else NODE_TYPE_DEVICE,
            interface=interface if not is_diagram_category else INTERFACE_CAN,
            vendor=str(data.get("vendor", TEXT_EMPTY)) if not is_diagram_category else vendor_default,
            device_type=str(data.get("device_type", TEXT_EMPTY)) if not is_diagram_category else device_type_default,
            motor=str(data.get("motor", TEXT_EMPTY)) if not is_diagram_category else TEXT_EMPTY,
            limits=data.get("limits") if (not is_diagram_category and isinstance(data.get("limits"), dict)) else None,
            dio=data.get("dio") if (not is_diagram_category and interface == INTERFACE_DIO) else None,
            invert=data.get("dio_invert") if (not is_diagram_category and interface == INTERFACE_DIO) else None,
            terminator=bool(data.get("terminator")) if (not is_diagram_category and data.get("terminator") is not None) else None,
            x=self._next_x_position(),
            row=len(self._nodes) % 2,
            bus_index=len(self._nodes) % max(len(self._bus_offsets), 1),
            scale=1.0,
            tags=tags,
            profile_visible=bool(data.get("profile_visible", False if is_diagram_category else True)),
        )
        self._next_key += 1
        self._nodes.append(node)
        self._layout_width = max(self._layout_width, node.x + 200)
        self._prune_attachment_links()
        self._prune_power_links()
        self._prune_dio_wiring_links()
        self._ensure_dio_wiring_links()
        self._refresh_list()
        self._mark_neighbors_stale()
        self._redraw_canvas()
        self._select_node(node.key)

    def _add_cannect_inject(self) -> None:
        """
        NAME
            _add_cannect_inject - Add a CANnect Inject diagram node.
        """
        self._add_cannect_node(kind="inject")

    def _add_cannect_direct(self) -> None:
        """
        NAME
            _add_cannect_direct - Add a CANnect Direct diagram node.
        """
        self._add_cannect_node(kind="direct")

    def _add_cannect_node(self, kind: str) -> None:
        """
        NAME
            _add_cannect_node - Create a diagram-only SWYFT CANnect node.
        """
        label = "CANnect Inject" if kind == "inject" else "CANnect Direct"
        category = "cannect_inject" if kind == "inject" else "cannect_direct"
        self._push_undo()
        node = Node(
            key=self._next_key,
            category=category,
            label=label,
            can_id=-1,
            node_type="diagram",
            vendor="SWYFT",
            device_type="Wiring",
            x=self._next_x_position(),
            row=len(self._nodes) % 2,
            bus_index=len(self._nodes) % max(len(self._bus_offsets), 1),
            scale=1.0,
            tags=self._normalize_tags(["swyft", "cannect", kind]),
            profile_visible=False,
        )
        self._ensure_cannect_free_float(node)
        self._next_key += 1
        self._nodes.append(node)
        self._layout_width = max(self._layout_width, node.x + 200)
        self._refresh_list()
        self._mark_neighbors_stale()
        self._redraw_canvas()
        self._select_node(node.key)

    def _add_analyzer_node(self) -> None:
        """
        NAME
            _add_analyzer_node - Add a diagram-only CAN analyzer node.
        """
        self._push_undo()
        node = Node(
            key=self._next_key,
            category=DIAGRAM_CATEGORY_ANALYZER,
            label=self._next_analyzer_label(),
            can_id=ANALYZER_DEFAULT_CAN_ID,
            node_type=ANALYZER_NODE_TYPE,
            x=self._next_x_position(),
            row=len(self._nodes) % ANALYZER_ROW_MOD,
            bus_index=len(self._nodes) % max(len(self._bus_offsets), BUS_INDEX_FLOOR),
            scale=ANALYZER_SCALE,
            tags=self._normalize_tags(ANALYZER_TAGS),
            profile_visible=False,
        )
        self._next_key += 1
        self._nodes.append(node)
        self._layout_width = max(self._layout_width, node.x + LAYOUT_PAD_X)
        self._refresh_list()
        self._mark_neighbors_stale()
        self._redraw_canvas()
        self._select_node(node.key)

    def _on_add_dio_device(self) -> None:
        """
        NAME
            _on_add_dio_device - Add a DIO device node with DIO defaults.
        """
        initial = Node(
            key=self._next_key,
            category=GENERIC_CATEGORY,
            label=TEXT_EMPTY,
            can_id=CAN_ID_DIAGRAM_DEFAULT,
            node_type=NODE_TYPE_DEVICE,
            interface=INTERFACE_DIO,
            vendor=TEXT_EMPTY,
            device_type=DIO_DEVICE_TYPES[0] if DIO_DEVICE_TYPES else TEXT_EMPTY,
            motor=TEXT_EMPTY,
        )
        dialog = NodeDialog(self, DIALOG_TITLE_ADD_DIO, initial=initial)
        self.wait_window(dialog)
        if not dialog.result:
            return
        self._push_undo()
        data = dialog.result
        category = str(data["category"])
        if category in SINGLETON_CATEGORIES:
            if any(n.category == category for n in self._nodes):
                replace = messagebox.askyesno(
                    DIALOG_TITLE_REPLACE,
                    f"{category} already exists. Replace it?",
                )
                if not replace:
                    return
                self._nodes = [n for n in self._nodes if n.category != category]
        is_diagram_category = category in DIAGRAM_CATEGORIES
        vendor_default, device_type_default, tag_defaults = (TEXT_EMPTY, TEXT_EMPTY, [])
        if is_diagram_category:
            vendor_default, device_type_default, tag_defaults = self._diagram_defaults(category)
        tags = self._normalize_tags(data.get("tags", []))
        if is_diagram_category:
            tags = self._normalize_tags(tags + tag_defaults)
        interface = str(data.get("interface", INTERFACE_DIO)).strip() or INTERFACE_DIO
        node = Node(
            key=self._next_key,
            category=category,
            label=str(data["label"]),
            can_id=CAN_ID_DIAGRAM_DEFAULT if is_diagram_category else int(data["can_id"]),
            node_type=ANALYZER_NODE_TYPE if is_diagram_category else NODE_TYPE_DEVICE,
            interface=interface if not is_diagram_category else INTERFACE_CAN,
            vendor=str(data.get("vendor", TEXT_EMPTY)) if not is_diagram_category else vendor_default,
            device_type=str(data.get("device_type", TEXT_EMPTY)) if not is_diagram_category else device_type_default,
            motor=str(data.get("motor", TEXT_EMPTY)) if not is_diagram_category else TEXT_EMPTY,
            limits=data.get("limits") if (not is_diagram_category and isinstance(data.get("limits"), dict)) else None,
            dio=data.get("dio") if (not is_diagram_category and interface == INTERFACE_DIO) else None,
            invert=data.get("dio_invert") if (not is_diagram_category and interface == INTERFACE_DIO) else None,
            terminator=bool(data.get("terminator")) if (not is_diagram_category and data.get("terminator") is not None) else None,
            x=self._next_x_position(),
            row=len(self._nodes) % 2,
            bus_index=len(self._nodes) % max(len(self._bus_offsets), 1),
            scale=1.0,
            tags=tags,
            profile_visible=False if is_diagram_category else True,
        )
        self._next_key += 1
        self._nodes.append(node)
        self._layout_width = max(self._layout_width, node.x + 200)
        self._prune_attachment_links()
        self._prune_power_links()
        self._prune_dio_wiring_links()
        self._ensure_dio_wiring_links()
        self._refresh_list()
        self._mark_neighbors_stale()
        self._redraw_canvas()
        self._select_node(node.key)

    def _controller_label_for_port(self, port: int) -> str:
        """
        NAME
            _controller_label_for_port - Build the default controller label for a USB port.
        """
        return f"{CONTROLLER_LABEL_PREFIX}{port}"

    def _controller_port_in_use(self, port: int, exclude_label: str = TEXT_EMPTY) -> bool:
        """
        NAME
            _controller_port_in_use - Return true when a USB port is already claimed.
        """
        exclude_norm = exclude_label.strip().lower()
        for entry in self._device_registry_list:
            if not isinstance(entry, dict) or not self._is_xbox_controller_entry(entry):
                continue
            label = str(entry.get(KEY_LABEL, TEXT_EMPTY)).strip().lower()
            if exclude_norm and label == exclude_norm:
                continue
            if entry.get(KEY_ID) == port:
                return True
        return False

    def _matching_xbox_controller_entry(self, label: str, port: int) -> Optional[Dict[str, object]]:
        """
        NAME
            _matching_xbox_controller_entry - Find a registry Xbox controller with exact label and port.
        """
        entry = self._inventory_entry_for_label(label)
        if not isinstance(entry, dict) or not self._is_xbox_controller_entry(entry):
            return None
        if entry.get(KEY_ID) != port:
            return None
        return entry

    def _prompt_xbox_controller_dialog(
        self,
        title: str,
        count_default: int,
        start_port_default: int,
        label_default: str = TEXT_EMPTY,
        model_default: str = CONTROLLER_MODEL_DEFAULT,
        tags_default: str = TEXT_EMPTY,
        edit_mode: bool = False,
    ) -> Optional[Dict[str, object]]:
        """
        NAME
            _prompt_xbox_controller_dialog - Collect Xbox controller dialog fields.
        """
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        count_var = tk.StringVar(value=str(count_default))
        port_var = tk.StringVar(value=str(start_port_default))
        label_var = tk.StringVar(value=label_default)
        model_var = tk.StringVar(value=model_default)
        tags_var = tk.StringVar(value=tags_default)
        result: Dict[str, object] = {}

        frame = ttk.Frame(dialog, padding=CONTROLLER_DIALOG_PAD)
        frame.grid(row=0, column=0, sticky="nsew")
        row = 0
        if edit_mode:
            fields = [
                (CONTROLLER_FIELD_LABEL, label_var),
                (CONTROLLER_FIELD_PORT, port_var),
                (CONTROLLER_FIELD_MODEL, model_var),
                (CONTROLLER_FIELD_TAGS, tags_var),
            ]
        else:
            fields = [
                (CONTROLLER_FIELD_COUNT, count_var),
                (CONTROLLER_FIELD_START_PORT, port_var),
            ]
        for field_label, variable in fields:
            ttk.Label(frame, text=f"{field_label}:").grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, CONTROLLER_DIALOG_PAD),
                pady=(0, CONTROLLER_DIALOG_ROW_PAD),
            )
            entry = ttk.Entry(frame, textvariable=variable, width=CONTROLLER_DIALOG_WIDTH // 10)
            entry.grid(row=row, column=1, sticky="ew", pady=(0, CONTROLLER_DIALOG_ROW_PAD))
            if row == 0:
                entry.focus_set()
                entry.selection_range(0, "end")
            row += 1

        def _cancel() -> None:
            dialog.destroy()

        def _ok() -> None:
            if edit_mode:
                try:
                    port_value = int(port_var.get().strip())
                except ValueError:
                    messagebox.showerror(title, MSG_CONTROLLER_INVALID_PORT)
                    return
                if port_value < CONTROLLER_PORT_DEFAULT:
                    messagebox.showerror(title, MSG_CONTROLLER_INVALID_PORT)
                    return
                label_value = label_var.get().strip()
                if not label_value:
                    messagebox.showerror(title, MSG_CONTROLLER_LABEL_REQUIRED)
                    return
                result.update(
                    {
                        KEY_LABEL: label_value,
                        KEY_ID: port_value,
                        KEY_MODEL: model_var.get().strip() or CONTROLLER_MODEL_DEFAULT,
                        KEY_TAGS: self._normalize_tags(tags_var.get()),
                    }
                )
            else:
                try:
                    count_value = int(count_var.get().strip())
                except ValueError:
                    messagebox.showerror(title, MSG_CONTROLLER_INVALID_COUNT)
                    return
                try:
                    port_value = int(port_var.get().strip())
                except ValueError:
                    messagebox.showerror(title, MSG_CONTROLLER_INVALID_PORT)
                    return
                if count_value < CONTROLLER_COUNT_DEFAULT:
                    messagebox.showerror(title, MSG_CONTROLLER_INVALID_COUNT)
                    return
                if port_value < CONTROLLER_PORT_DEFAULT:
                    messagebox.showerror(title, MSG_CONTROLLER_INVALID_PORT)
                    return
                result.update(
                    {
                        CONTROLLER_FIELD_COUNT: count_value,
                        CONTROLLER_FIELD_START_PORT: port_value,
                    }
                )
            dialog.destroy()

        buttons = ttk.Frame(frame)
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(CONTROLLER_DIALOG_PAD, 0))
        ttk.Button(buttons, text="Cancel", command=_cancel).pack(side="right", padx=4)
        ttk.Button(buttons, text="OK", command=_ok).pack(side="right")

        self.wait_window(dialog)
        if not result:
            return None
        return result

    def _new_xbox_controller_entry(self, label: str, port: int) -> Dict[str, object]:
        """
        NAME
            _new_xbox_controller_entry - Build a canonical Xbox controller registry entry.
        """
        return {
            KEY_LABEL: label,
            KEY_INTERFACE: profile_consts.INTERFACE_USB if profile_consts is not None else DETAIL_INTERFACE_USB,
            KEY_ID: port,
            KEY_MANUFACTURER: CONTROLLER_MANUFACTURER_DEFAULT,
            KEY_DEVICE_TYPE: CONTROLLER_DEVICE_TYPE_DEFAULT,
            KEY_MODEL: CONTROLLER_MODEL_DEFAULT,
            KEY_TYPE: profile_consts.TYPE_XBOX_CONTROLLER if profile_consts is not None else TYPE_XBOX_CONTROLLER,
        }

    def _on_add_xbox_controller(self) -> None:
        """
        NAME
            _on_add_xbox_controller - Add one or more Xbox controllers to the active profile.
        """
        result = self._prompt_xbox_controller_dialog(
            DIALOG_TITLE_ADD_XBOX_CONTROLLER,
            CONTROLLER_COUNT_DEFAULT,
            CONTROLLER_PORT_DEFAULT,
            edit_mode=False,
        )
        if not isinstance(result, dict):
            return
        count = int(result.get(CONTROLLER_FIELD_COUNT, CONTROLLER_COUNT_DEFAULT))
        start_port = int(result.get(CONTROLLER_FIELD_START_PORT, CONTROLLER_PORT_DEFAULT))
        new_entries: List[Dict[str, object]] = []
        existing_labels_to_add: List[str] = []
        seen_labels: set[str] = set()
        seen_ports: set[int] = set()
        for offset in range(count):
            port = start_port + offset
            label = self._controller_label_for_port(port)
            exact_existing = self._matching_xbox_controller_entry(label, port)
            if exact_existing is not None:
                if label in self._non_topology_profile_labels:
                    messagebox.showinfo(
                        DIALOG_TITLE_ADD_XBOX_CONTROLLER,
                        MSG_CONTROLLER_ALREADY_IN_PROFILE.format(label),
                    )
                    return
                existing_labels_to_add.append(label)
                seen_labels.add(label)
                seen_ports.add(port)
                continue
            if label in self._device_registry or label in seen_labels:
                messagebox.showerror(DIALOG_TITLE_ADD_XBOX_CONTROLLER, MSG_CONTROLLER_DUPLICATE_LABEL.format(label))
                return
            if self._controller_port_in_use(port) or port in seen_ports:
                messagebox.showerror(DIALOG_TITLE_ADD_XBOX_CONTROLLER, MSG_CONTROLLER_DUPLICATE_PORT.format(port))
                return
            seen_labels.add(label)
            seen_ports.add(port)
            new_entries.append(self._new_xbox_controller_entry(label, port))
        if not new_entries and not existing_labels_to_add:
            messagebox.showinfo(DIALOG_TITLE_ADD_XBOX_CONTROLLER, MSG_CONTROLLER_ADD_NONE)
            return
        for label in existing_labels_to_add:
            if label not in self._non_topology_profile_labels:
                self._non_topology_profile_labels.append(label)
        for entry in new_entries:
            label = str(entry.get(KEY_LABEL, TEXT_EMPTY)).strip()
            self._device_registry_list.append(entry)
            self._device_registry[label] = entry
            if label not in self._non_topology_profile_labels:
                self._non_topology_profile_labels.append(label)
        self._dirty = True
        self._refresh_list()
        if new_entries:
            self._selected_inventory_label = str(new_entries[0].get(KEY_LABEL, TEXT_EMPTY)).strip()
        else:
            self._selected_inventory_label = existing_labels_to_add[0]
        self._selected_nodes = set()
        self._selected_buses = set()
        self._sync_selection_state()

    def _edit_selected_inventory_item(self) -> bool:
        """
        NAME
            _edit_selected_inventory_item - Edit the selected non-topology inventory item.
        """
        label = str(self._selected_inventory_label or TEXT_EMPTY).strip()
        entry = self._inventory_entry_for_label(label)
        if not isinstance(entry, dict) or not self._is_xbox_controller_entry(entry):
            return False
        result = self._prompt_xbox_controller_dialog(
            DIALOG_TITLE_EDIT_XBOX_CONTROLLER,
            CONTROLLER_COUNT_DEFAULT,
            int(entry.get(KEY_ID, CONTROLLER_PORT_DEFAULT))
            if isinstance(entry.get(KEY_ID), int)
            else CONTROLLER_PORT_DEFAULT,
            label_default=label,
            model_default=str(entry.get(KEY_MODEL, CONTROLLER_MODEL_DEFAULT)).strip() or CONTROLLER_MODEL_DEFAULT,
            tags_default=self._tags_to_string(self._normalize_tags(entry.get(KEY_TAGS, []))),
            edit_mode=True,
        )
        if not isinstance(result, dict):
            return True
        new_label = str(result.get(KEY_LABEL, TEXT_EMPTY)).strip()
        new_port = int(result.get(KEY_ID, CONTROLLER_PORT_DEFAULT))
        if new_label != label and new_label in self._device_registry:
            messagebox.showerror(DIALOG_TITLE_EDIT_XBOX_CONTROLLER, MSG_CONTROLLER_DUPLICATE_LABEL.format(new_label))
            return True
        if self._controller_port_in_use(new_port, exclude_label=label):
            messagebox.showerror(DIALOG_TITLE_EDIT_XBOX_CONTROLLER, MSG_CONTROLLER_DUPLICATE_PORT.format(new_port))
            return True
        if new_label != label:
            self._rename_registry_label(label, new_label)
            self._update_bridge_config_label_refs(label, new_label)
            self._non_topology_profile_labels = [
                new_label if existing == label else existing
                for existing in self._non_topology_profile_labels
            ]
            if label in self._pending_global_device_deletions:
                self._pending_global_device_deletions.discard(label)
                self._pending_global_device_deletions.add(new_label)
            entry = self._inventory_entry_for_label(new_label) or entry
        entry[KEY_LABEL] = new_label
        entry[KEY_ID] = new_port
        entry[KEY_MODEL] = str(result.get(KEY_MODEL, CONTROLLER_MODEL_DEFAULT)).strip() or CONTROLLER_MODEL_DEFAULT
        entry[KEY_TAGS] = list(result.get(KEY_TAGS, []))
        self._selected_inventory_label = new_label
        self._dirty = True
        self._refresh_list()
        self._sync_selection_state()
        return True

    def _profile_references_for_label(self, label: str) -> List[str]:
        """
        NAME
            _profile_references_for_label - Return profile names that reference a device label.
        """
        source_path = Path(self._profile_source_path) if self._profile_source_path else self._default_profiles_path()
        if not source_path.exists():
            return []
        try:
            data = self._load_config_payload(source_path)
        except Exception:
            return []
        profiles = data.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            return []
        label_text = str(label).strip()
        refs: List[str] = []
        for profile_name, profile in profiles.items():
            if not isinstance(profile, dict):
                continue
            devices = profile.get(KEY_DEVICES)
            if not isinstance(devices, list):
                continue
            if any(str(item).strip() == label_text for item in devices):
                refs.append(str(profile_name))
        return refs

    def _profiles_by_label(self) -> Dict[str, List[str]]:
        """
        NAME
            _profiles_by_label - Return profile memberships keyed by device label.
        """
        memberships: Dict[str, List[str]] = {}
        source_path = Path(self._profile_source_path) if self._profile_source_path else self._default_profiles_path()
        data: Dict[str, object] = {}
        if source_path.exists():
            try:
                loaded = self._load_config_payload(source_path)
                if isinstance(loaded, dict):
                    data = loaded
            except Exception:
                data = {}
        profiles = data.get(KEY_PROFILES)
        if isinstance(profiles, dict):
            for profile_name, profile in profiles.items():
                if not isinstance(profile, dict):
                    continue
                devices = profile.get(KEY_DEVICES)
                if not isinstance(devices, list):
                    continue
                clean_name = str(profile_name).strip()
                if not clean_name:
                    continue
                for label in devices:
                    label_text = str(label).strip()
                    if not label_text:
                        continue
                    memberships.setdefault(label_text, [])
                    if clean_name not in memberships[label_text]:
                        memberships[label_text].append(clean_name)
        topology_root = data.get(KEY_TOPOLOGY)
        if isinstance(topology_root, dict):
            topology_profiles = topology_root.get(KEY_TOPOLOGY_PROFILES)
            if isinstance(topology_profiles, dict):
                for profile_name, topology_entry in topology_profiles.items():
                    clean_name = str(profile_name).strip()
                    if not clean_name:
                        continue
                    for label_text, _entry in self._topology_inventory_entries(topology_entry).items():
                        memberships.setdefault(label_text, [])
                        if clean_name not in memberships[label_text]:
                            memberships[label_text].append(clean_name)
        current_profile = str(self._profile_name or TEXT_EMPTY).strip()
        if current_profile:
            current_labels = {
                (node.label or TEXT_EMPTY).strip()
                for node in self._profile_device_nodes()
                if (node.label or TEXT_EMPTY).strip()
            }
            current_labels.update(
                label.strip()
                for label in list(self.__dict__.get("_non_topology_profile_labels", []) or [])
                if str(label).strip()
            )
            for label_text, profile_names in memberships.items():
                if current_profile in profile_names and label_text not in current_labels:
                    memberships[label_text] = [
                        profile_name for profile_name in profile_names if profile_name != current_profile
                    ]
            for label_text in current_labels:
                memberships.setdefault(label_text, [])
                if current_profile not in memberships[label_text]:
                    memberships[label_text].append(current_profile)
        return {
            label: sorted(profile_names)
            for label, profile_names in memberships.items()
            if profile_names
        }

    def _topology_inventory_entries(self, topology_entry: object) -> Dict[str, Dict[str, object]]:
        """
        NAME
            _topology_inventory_entries - Extract label-keyed inventory metadata from one topology entry.
        """
        if not isinstance(topology_entry, dict):
            return {}
        topology_nodes = topology_entry.get(KEY_TOPOLOGY_NODES)
        if not isinstance(topology_nodes, list):
            return {}
        entries: Dict[str, Dict[str, object]] = {}
        for node in topology_nodes:
            if not isinstance(node, dict):
                continue
            node_type = str(
                node.get(KEY_TOPOLOGY_OBJECT_TYPE)
                or node.get(KEY_TOPOLOGY_NODE_TYPE)
                or EMPTY_STRING
            ).strip().lower()
            if node_type == NODE_TYPE_CALLOUT:
                continue
            label_text = str(
                node.get(KEY_TOPOLOGY_DEVICE_REF)
                or node.get(KEY_LABEL)
                or EMPTY_STRING
            ).strip()
            if not label_text:
                continue
            entry = entries.setdefault(label_text, {KEY_LABEL: label_text})
            category_text = str(node.get(KEY_CATEGORY, EMPTY_STRING)).strip()
            if not category_text:
                inferred = self._infrastructure_category_from_label(label_text)
                if inferred:
                    category_text = inferred
            if category_text and not str(entry.get(KEY_CATEGORY, EMPTY_STRING)).strip():
                entry[KEY_CATEGORY] = category_text
            node_id = node.get(KEY_ID)
            if isinstance(node_id, int) and node_id >= 0 and not isinstance(entry.get(KEY_ID), int):
                entry[KEY_ID] = node_id
            tags = self._normalize_tags(node.get(KEY_TAGS, []))
            if tags and not entry.get(KEY_TAGS):
                entry[KEY_TAGS] = tags
        return entries

    def _full_config_inventory_entries(self) -> Dict[str, Dict[str, object]]:
        """
        NAME
            _full_config_inventory_entries - Return all known config objects keyed by label.
        """
        entries: Dict[str, Dict[str, object]] = {}
        for label, entry in self._device_registry.items():
            label_text = str(label).strip()
            if not label_text or not isinstance(entry, dict):
                continue
            entries[label_text] = dict(entry)
        source_path = Path(self._profile_source_path) if self._profile_source_path else self._default_profiles_path()
        if not source_path.exists():
            return entries
        try:
            loaded = self._load_config_payload(source_path)
        except Exception:
            return entries
        if not isinstance(loaded, dict):
            return entries
        topology_root = loaded.get(KEY_TOPOLOGY)
        if not isinstance(topology_root, dict):
            return entries
        topology_profiles = topology_root.get(KEY_TOPOLOGY_PROFILES)
        if not isinstance(topology_profiles, dict):
            return entries
        for topology_entry in topology_profiles.values():
            for label_text, entry in self._topology_inventory_entries(topology_entry).items():
                existing = entries.get(label_text)
                if isinstance(existing, dict):
                    if (
                        not str(existing.get(KEY_CATEGORY, EMPTY_STRING)).strip()
                        and str(entry.get(KEY_CATEGORY, EMPTY_STRING)).strip()
                    ):
                        existing[KEY_CATEGORY] = entry.get(KEY_CATEGORY)
                    if not isinstance(existing.get(KEY_ID), int) and isinstance(entry.get(KEY_ID), int):
                        existing[KEY_ID] = entry.get(KEY_ID)
                    if not existing.get(KEY_TAGS) and entry.get(KEY_TAGS):
                        existing[KEY_TAGS] = entry.get(KEY_TAGS)
                    continue
                entries[label_text] = dict(entry)
        return entries

    def _remove_registry_entry_by_label(self, label: str) -> None:
        """
        NAME
            _remove_registry_entry_by_label - Remove one device registry entry by label.
        """
        label_text = str(label).strip()
        if not label_text:
            return
        self._device_registry.pop(label_text, None)
        self._device_registry_list = [
            entry
            for entry in self._device_registry_list
            if str(entry.get(KEY_LABEL, TEXT_EMPTY)).strip() != label_text
        ]

    def _remove_device_label_from_current_profile(self, label: str) -> bool:
        """
        NAME
            _remove_device_label_from_current_profile - Remove one shared device label from the active profile only.
        """
        label_text = str(label).strip()
        if not label_text:
            return False
        node_keys = {
            int(node.key)
            for node in self._profile_device_nodes()
            if str(node.label or TEXT_EMPTY).strip() == label_text
        }
        in_non_topology = label_text in self._non_topology_profile_labels
        if not node_keys and not in_non_topology:
            messagebox.showinfo(
                TITLE_REMOVE_FROM_PROFILE,
                MSG_REMOVE_PROFILE_NOT_PRESENT.format(label_text),
            )
            return True
        proceed = messagebox.askyesno(
            TITLE_REMOVE_FROM_PROFILE,
            MSG_REMOVE_PROFILE_CONFIRM.format(label_text),
        )
        if not proceed:
            return True
        self._push_undo()
        if node_keys:
            self._nodes = [node for node in self._nodes if int(node.key) not in node_keys]
        if in_non_topology:
            self._non_topology_profile_labels = [
                existing for existing in self._non_topology_profile_labels if existing != label_text
            ]
        self._selected_inventory_label = None
        if any(key in set(self._selected_nodes) for key in node_keys):
            self._clear_selection()
        self._prune_current_profile_bridge_config_label(label_text)
        self._prune_attachment_links()
        self._prune_power_links()
        self._prune_dio_wiring_links()
        self._dirty = True
        self._refresh_list()
        self._update_details_panel(None)
        self._update_selection_overlays()
        self._mark_neighbors_stale()
        self._redraw_canvas()
        return True

    def _remove_selected_inventory_item(self) -> bool:
        """
        NAME
            _remove_selected_inventory_item - Remove the selected inventory item from the active profile.
        """
        label = str(self._selected_inventory_label or TEXT_EMPTY).strip()
        entry = self._inventory_entry_for_label(label)
        if not isinstance(entry, dict):
            return False
        return self._remove_device_label_from_current_profile(label)

    def _delete_device_label_from_app(self, label: str) -> bool:
        """
        NAME
            _delete_device_label_from_app - Delete one shared device label from app-wide config and current editor state.
        """
        label_text = str(label).strip()
        if not label_text:
            return False
        refs = [name for name in self._profile_references_for_label(label_text) if str(name).strip()]
        if refs:
            proceed = messagebox.askyesno(
                TITLE_DELETE_FROM_APP,
                MSG_INVENTORY_DELETE_REFERENCED.format(
                    label=label_text,
                    profiles=NEWLINE.join(refs),
                ),
            )
        else:
            proceed = messagebox.askyesno(
                TITLE_DELETE_FROM_APP,
                MSG_INVENTORY_DELETE_CONFIRM.format(label_text),
            )
        if not proceed:
            return True
        self._push_undo()
        self._remove_registry_entry_by_label(label_text)
        self._pending_global_device_deletions.add(label_text)
        self._nodes = [
            node
            for node in self._nodes
            if not (
                self._is_registry_device_node(node)
                and str(node.label or TEXT_EMPTY).strip() == label_text
            )
        ]
        self._non_topology_profile_labels = [
            existing for existing in self._non_topology_profile_labels if existing != label_text
        ]
        self._prune_bridge_config_label(label_text)
        self._prune_attachment_links()
        self._prune_power_links()
        self._prune_dio_wiring_links()
        self._selected_inventory_label = None
        self._clear_selection()
        self._dirty = True
        self._refresh_list()
        self._update_details_panel(None)
        self._update_selection_overlays()
        self._mark_neighbors_stale()
        self._redraw_canvas()
        return True

    def _delete_inventory_entry_globally(self, label: str) -> bool:
        """
        NAME
            _delete_inventory_entry_globally - Delete one shared-config device definition from the app entirely.
        """
        return self._delete_device_label_from_app(label)

    def _next_analyzer_label(self) -> str:
        """
        NAME
            _next_analyzer_label - Build a unique analyzer label.
        """
        existing = {
            (n.label or "").strip()
            for n in self._nodes
            if (n.category or "").lower() == DIAGRAM_CATEGORY_ANALYZER
        }
        index = ANALYZER_LABEL_START
        while True:
            label = f"{ANALYZER_LABEL_PREFIX} {index}"
            if label not in existing:
                return label
            index += ANALYZER_LABEL_STEP

    def _diagram_defaults(self, category: str) -> Tuple[str, str, List[str]]:
        """
        NAME
            _diagram_defaults - Resolve vendor/type/tags for diagram categories.
        """
        cat = (category or "").lower()
        if cat == DIAGRAM_CATEGORY_CANNECT_INJECT:
            return (DIAGRAM_VENDOR_SWYFT, DIAGRAM_DEVICE_WIRING, [TAG_SWYFT, TAG_CANNECT, TAG_INJECT])
        if cat == DIAGRAM_CATEGORY_CANNECT_DIRECT:
            return (DIAGRAM_VENDOR_SWYFT, DIAGRAM_DEVICE_WIRING, [TAG_SWYFT, TAG_CANNECT, TAG_DIRECT])
        if cat == DIAGRAM_CATEGORY_ANALYZER:
            return (DIAGRAM_VENDOR_ANALYZER, DIAGRAM_DEVICE_ANALYZER, [TAG_ANALYZER])
        return (TEXT_EMPTY, TEXT_EMPTY, [])
    def _allow_multi_port_links(self, node: Node) -> bool:
        """
        NAME
            _allow_multi_port_links - Allow multiple links per CANnect port.
        """
        category = (node.category or "").lower()
        return category == DIAGRAM_CATEGORY_CANNECT_DIRECT

    def _cannect_port_counts(
        self,
        cannect: Node,
        links: List[Dict[str, int]],
        max_ports: int,
    ) -> Dict[int, int]:
        """
        NAME
            _cannect_port_counts - Count links per CANnect port.
        """
        counts = {port: CANNECT_PORT_COUNT_DEFAULT for port in range(CANNECT_PORT_MIN, max_ports + 1)}
        for link in links:
            if link.get("node") != cannect.key:
                continue
            port = int(link.get("port", CANNECT_PORT_ZERO))
            if port in counts:
                counts[port] += 1
        return counts

    @staticmethod
    def _select_least_loaded_port(counts: Dict[int, int]) -> int:
        """
        NAME
            _select_least_loaded_port - Pick the lowest-load CANnect port.
        """
        return min(counts.items(), key=lambda item: (item[1], item[0]))[0]

    @staticmethod
    def _max_cannect_ports(node: Node) -> int:
        """
        NAME
            _max_cannect_ports - Return CAN bus port count for a CANnect node.
        """
        category = (node.category or "").lower()
        if category == "cannect_inject":
            return 1
        if category == "cannect_direct":
            return 3
        return 0

    def _cannect_device_keys(self, cannect_key: int) -> set[int]:
        """
        NAME
            _cannect_device_keys - Return device keys linked to a CANnect node.
        """
        return {
            int(link.get("device"))
            for link in self._cannect_device_links
            if link.get("node") == cannect_key and isinstance(link.get("device"), int)
        }

    def _is_cannect_linked_device(self, node: Node) -> bool:
        """
        NAME
            _is_cannect_linked_device - Return True if a node is linked to a CANnect.
        """
        return any(
            link.get("device") == node.key for link in self._cannect_device_links if isinstance(node.key, int)
        )

    def _is_cannect_cluster_member(self, node: Node) -> bool:
        """
        NAME
            _is_cannect_cluster_member - Return True for CANnect nodes and linked devices.
        """
        return self._is_swyft_node(node) or self._is_cannect_linked_device(node)

    def _ensure_cannect_free_float(self, node: Node) -> None:
        """
        NAME
            _ensure_cannect_free_float - Mark CANnect cluster nodes as free-floating.
        """
        if not ENABLE_CANNECT_FREE_FLOAT:
            return
        if not self._is_cannect_cluster_member(node):
            return
        if getattr(node, "free_y_relative", True) is False and node.free_y is not None:
            return
        node.free_y = node_center_y_unscaled(node, self._bus_offsets, self._box_h)
        node.free_y_relative = False

    def _restore_legacy_cannect_free_y_mode(self) -> None:
        """
        NAME
            _restore_legacy_cannect_free_y_mode - Preserve old absolute CANnect Y values.

        DESCRIPTION
            Topology files written before yRelative existed stored CANnect cluster
            free-Y positions as absolute coordinates. Mark those as absolute before
            free-float normalization runs, otherwise reload adds the bus offset.
        """
        for node in self._nodes:
            if node.free_y is None:
                continue
            if getattr(node, "topology_y_relative_explicit", False):
                continue
            if self._is_cannect_cluster_member(node):
                node.free_y_relative = False

    def _apply_cannect_free_float(self) -> None:
        """
        NAME
            _apply_cannect_free_float - Apply free-float to CANnect nodes and linked devices.
        """
        if not ENABLE_CANNECT_FREE_FLOAT:
            return
        for node in self._nodes:
            if self._is_cannect_cluster_member(node):
                self._ensure_cannect_free_float(node)

    def _add_ethernet_link(self) -> None:
        """
        NAME
            _add_ethernet_link - Create an Ethernet link between SWYFT nodes.
        """
        selected = [n for n in self._device_nodes() if n.key in self._selected_nodes]
        swyft = [n for n in selected if self._is_swyft_node(n)]
        if len(swyft) != 2:
            messagebox.showinfo(
                "Add Ethernet Link",
                "Select exactly two CANnect nodes to link.",
            )
            return
        a, b = swyft[0].key, swyft[1].key
        link = (min(a, b), max(a, b))
        if link in self._ethernet_links:
            messagebox.showinfo(
                "Add Ethernet Link",
                "An Ethernet link already exists between the selected nodes.",
            )
            return
        self._push_undo()
        self._ethernet_links.append(link)
        before_can_links = len(self._can_bus_links)
        self._can_bus_links = [
            l for l in self._can_bus_links if l.get("node") not in (a, b)
        ]
        if len(self._can_bus_links) != before_can_links:
            self._dirty = True
        self._redraw_canvas()

    def _remove_ethernet_link(self) -> None:
        """
        NAME
            _remove_ethernet_link - Remove Ethernet links for selected SWYFT nodes.
        """
        selected_keys = {
            n.key
            for n in self._device_nodes()
            if n.key in self._selected_nodes and self._is_swyft_node(n)
        }
        if not selected_keys:
            messagebox.showinfo(
                "Remove Ethernet Link",
                "Select one or more CANnect nodes to remove links.",
            )
            return
        before = len(self._ethernet_links)
        self._push_undo()
        self._ethernet_links = [
            link for link in self._ethernet_links if link[0] not in selected_keys and link[1] not in selected_keys
        ]
        if len(self._ethernet_links) == before:
            messagebox.showinfo(
                "Remove Ethernet Link",
                "No Ethernet links were removed.",
            )
        self._redraw_canvas()

    def _add_can_bus_link(self) -> None:
        """
        NAME
            _add_can_bus_link - Link a CANnect node to a bus segment.

        NOTES
            Disabled when ENABLE_CANNECT_BUS_LINKS is False.
        """
        if not ENABLE_CANNECT_BUS_LINKS:
            return
        selected_nodes = [n for n in self._device_nodes() if n.key in self._selected_nodes]
        swyft = [n for n in selected_nodes if self._is_swyft_node(n)]
        cannect_nodes = [n for n in self._device_nodes() if self._is_swyft_node(n)]
        if not cannect_nodes:
            messagebox.showinfo(MSG_CAN_BUS_LINK_TITLE, ERR_CANNECT_NONE)
            return
        if len(swyft) == 1:
            node = swyft[0]
        elif len(cannect_nodes) == 1:
            node = cannect_nodes[0]
        else:
            labels = [n.label for n in cannect_nodes if n.label]
            if not labels:
                messagebox.showinfo(MSG_CAN_BUS_LINK_TITLE, MSG_CAN_BUS_LINK_SELECT_NODE)
                return
            prompt = PROMPT_CANNECT_LABEL.format("\n".join(labels))
            selection = simpledialog.askstring(PROMPT_CANNECT_TITLE, prompt)
            if selection is None:
                return
            selection = selection.strip()
            node = next((n for n in cannect_nodes if n.label == selection), None)
            if node is None:
                messagebox.showinfo(MSG_CAN_BUS_LINK_TITLE, ERR_CANNECT_NOT_FOUND)
                return
        if len(self._selected_buses) == 1:
            bus_index = list(self._selected_buses)[0]
        else:
            max_bus = max(len(self._bus_offsets) - 1, 0)
            if max_bus <= 0:
                bus_index = 0
            else:
                bus_index = simpledialog.askinteger(
                    PROMPT_BUS_TITLE,
                    PROMPT_BUS_INDEX.format(max_bus),
                    minvalue=0,
                    maxvalue=max_bus,
                )
                if bus_index is None:
                    return
        max_ports = self._max_cannect_ports(node)
        if max_ports <= 0:
            messagebox.showinfo(MSG_CAN_BUS_LINK_TITLE, MSG_CAN_BUS_LINK_NODE_INVALID)
            return
        allow_multi = self._allow_multi_port_links(node)
        existing_ports = [
            int(link["port"])
            for link in self._can_bus_links
            if link.get("node") == node.key
        ]
        if not allow_multi and len(existing_ports) >= max_ports:
            messagebox.showinfo(
                MSG_CAN_BUS_LINK_TITLE,
                MSG_CAN_BUS_LINK_FULL.format(node.label, max_ports),
            )
            return
        for link in self._can_bus_links:
            if link.get("node") == node.key and link.get("bus") == bus_index:
                messagebox.showinfo(MSG_CAN_BUS_LINK_TITLE, MSG_CAN_BUS_LINK_DUP)
                return
        if allow_multi:
            counts = self._cannect_port_counts(node, self._can_bus_links, max_ports)
            port = self._select_least_loaded_port(counts)
        else:
            port = next(
                (
                    p
                    for p in range(
                        CANNECT_PORT_MIN,
                        max_ports + BUS_INDEX_FLOOR,
                        CANNECT_PORT_STEP,
                    )
                    if p not in existing_ports
                ),
                CANNECT_PORT_MIN,
            )
        self._push_undo()
        self._can_bus_links.append({"node": node.key, "bus": bus_index, "port": port})
        self._redraw_canvas()

    def _link_selected_devices_to_cannect(self) -> None:
        """
        NAME
            _link_selected_devices_to_cannect - Link selected devices to one CANnect node.
        """
        selected_nodes = [n for n in self._device_nodes() if n.key in self._selected_nodes]
        swyft = [n for n in selected_nodes if self._is_swyft_node(n)]
        if len(swyft) != 1:
            messagebox.showinfo(
                "Link Device to CANnect",
                "Select exactly one CANnect node and one or more device nodes.",
            )
            return
        cannect = swyft[0]
        devices = [
            n
            for n in selected_nodes
            if n.key != cannect.key
            and n.node_type != "callout"
            and not self._is_swyft_node(n)
            and getattr(n, "profile_visible", True)
        ]
        if not devices:
            messagebox.showinfo(
                "Link Device to CANnect",
                "Select one or more device nodes to link.",
            )
            return
        max_ports = self._max_cannect_ports(cannect)
        if max_ports <= 0:
            messagebox.showinfo(
                "Link Device to CANnect",
                "Selected node is not a CANnect node.",
            )
            return
        allow_multi = self._allow_multi_port_links(cannect)
        used_ports = {
            int(link.get("port", CANNECT_PORT_ZERO))
            for link in self._cannect_device_links
            if link.get("node") == cannect.key
        }
        available_ports = [
            p
            for p in range(CANNECT_PORT_MIN, max_ports + 1, CANNECT_PORT_STEP)
            if p not in used_ports
        ]
        if not available_ports and not allow_multi:
            messagebox.showinfo(
                "Link Device to CANnect",
                f"{cannect.label} has no free device ports.",
            )
            return
        self._push_undo()
        device_keys = {n.key for n in devices}
        remaining_links = [
            link
            for link in self._cannect_device_links
            if link.get("device") not in device_keys
        ]
        self._cannect_device_links = remaining_links
        linked = 0
        port_counts = {}
        if allow_multi:
            port_counts = self._cannect_port_counts(cannect, remaining_links, max_ports)
        for device in devices:
            if allow_multi:
                port = self._select_least_loaded_port(port_counts)
                port_counts[port] = port_counts.get(port, CANNECT_PORT_COUNT_DEFAULT) + 1
            else:
                if not available_ports:
                    break
                port = available_ports.pop(0)
            self._cannect_device_links.append(
                {"node": cannect.key, "device": device.key, "port": port}
            )
            linked += 1
        self._dirty = True
        self._redraw_canvas()
        if not allow_multi and linked < len(devices):
            messagebox.showinfo(
                "Link Device to CANnect",
                f"Linked {linked} of {len(devices)} devices. {cannect.label} has only {max_ports} ports.",
            )

    def _remove_can_bus_link(self) -> None:
        """
        NAME
            _remove_can_bus_link - Remove CAN bus links for selected nodes/buses.

        NOTES
            Disabled when ENABLE_CANNECT_BUS_LINKS is False.
        """
        if not ENABLE_CANNECT_BUS_LINKS:
            return
        selected_nodes = {n.key for n in self._device_nodes() if n.key in self._selected_nodes}
        selected_buses = set(self._selected_buses)
        if not selected_nodes and not selected_buses:
            messagebox.showinfo(
                "Remove CAN Bus Link",
                "Select a CANnect node and/or a bus segment.",
            )
            return
        before = len(self._can_bus_links)
        self._push_undo()
        if selected_nodes and selected_buses:
            self._can_bus_links = [
                link
                for link in self._can_bus_links
                if not (link.get("node") in selected_nodes and link.get("bus") in selected_buses)
            ]
        elif selected_nodes:
            self._can_bus_links = [
                link for link in self._can_bus_links if link.get("node") not in selected_nodes
            ]
        else:
            self._can_bus_links = [
                link for link in self._can_bus_links if link.get("bus") not in selected_buses
            ]
        if len(self._can_bus_links) == before:
            messagebox.showinfo(
                "Remove CAN Bus Link",
                "No CAN bus links were removed.",
            )
        self._redraw_canvas()

    def _remove_cannect_device_link(self) -> None:
        """
        NAME
            _remove_cannect_device_link - Remove CANnect device links for selected nodes.
        """
        selected_nodes = {n.key for n in self._device_nodes() if n.key in self._selected_nodes}
        if not selected_nodes:
            messagebox.showinfo(
                "Remove CANnect Device Link",
                "Select one or more nodes to remove links.",
            )
            return
        before = len(self._cannect_device_links)
        self._push_undo()
        self._cannect_device_links = [
            link
            for link in self._cannect_device_links
            if link.get("node") not in selected_nodes and link.get("device") not in selected_nodes
        ]
        if len(self._cannect_device_links) == before:
            messagebox.showinfo(
                "Remove CANnect Device Link",
                "No CANnect links were removed.",
            )
        self._redraw_canvas()

    def _attach_device_link(self) -> None:
        """
        NAME
            _attach_device_link - Create a logical attachment link.
        """
        selected = [n for n in self._device_nodes() if n.key in self._selected_nodes]
        if len(selected) != 2:
            messagebox.showinfo(TITLE_ATTACH_DEVICE, MSG_ATTACH_SELECT)
            return
        dio_nodes = [n for n in selected if self._is_dio_node(n)]
        host_nodes = [n for n in selected if not self._is_dio_node(n)]
        if len(dio_nodes) != 1 or len(host_nodes) != 1:
            messagebox.showinfo(TITLE_ATTACH_DEVICE, MSG_ATTACH_INVALID)
            return
        attachment = dio_nodes[0]
        host = host_nodes[0]
        link = {KEY_LINK_DEVICE: host.key, KEY_LINK_ATTACHMENT: attachment.key}
        if link in self._attachment_links:
            messagebox.showinfo(TITLE_ATTACH_DEVICE, MSG_ATTACH_DUP)
            return
        self._push_undo()
        self._attachment_links.append(link)
        self._dirty = True
        self._redraw_canvas()

    def _remove_attachment_link(self) -> None:
        """
        NAME
            _remove_attachment_link - Remove attachment links for selected nodes.
        """
        selected_keys = {n.key for n in self._device_nodes() if n.key in self._selected_nodes}
        if not selected_keys:
            messagebox.showinfo(TITLE_REMOVE_ATTACHMENT, MSG_ATTACH_REMOVE_SELECT)
            return
        before = len(self._attachment_links)
        self._push_undo()
        self._attachment_links = [
            link
            for link in self._attachment_links
            if link.get(KEY_LINK_DEVICE) not in selected_keys
            and link.get(KEY_LINK_ATTACHMENT) not in selected_keys
        ]
        if len(self._attachment_links) == before:
            messagebox.showinfo(TITLE_REMOVE_ATTACHMENT, MSG_ATTACH_NONE)
        self._redraw_canvas()

    def _add_power_link(self) -> None:
        """
        NAME
            _add_power_link - Create a logical power link between two nodes.
        """
        selected = [n for n in self._device_nodes() if n.key in self._selected_nodes]
        if len(selected) != 2:
            messagebox.showinfo(TITLE_POWER_LINK, MSG_POWER_SELECT)
            return
        if any(self._is_dio_node(node) for node in selected):
            messagebox.showinfo(TITLE_POWER_LINK, MSG_POWER_INVALID)
            return
        if not self._is_valid_power_link_pair(selected[0], selected[1]):
            messagebox.showinfo(TITLE_POWER_LINK, MSG_POWER_INVALID)
            return
        link = self._normalize_power_link({KEY_LINK_A: selected[0].key, KEY_LINK_B: selected[1].key})
        if link is None:
            messagebox.showinfo(TITLE_POWER_LINK, MSG_POWER_INVALID)
            return
        if link in self._power_links:
            messagebox.showinfo(TITLE_POWER_LINK, MSG_POWER_DUP)
            return
        self._push_undo()
        self._power_links.append(link)
        self._dirty = True
        self._redraw_canvas()

    def _remove_power_link(self) -> None:
        """
        NAME
            _remove_power_link - Remove power links for selected nodes.
        """
        selected_keys = {n.key for n in self._device_nodes() if n.key in self._selected_nodes}
        if not selected_keys:
            messagebox.showinfo(TITLE_REMOVE_POWER_LINK, MSG_POWER_REMOVE_SELECT)
            return
        before = len(self._power_links)
        self._push_undo()
        self._power_links = [
            link
            for link in self._power_links
            if link.get(KEY_LINK_A) not in selected_keys and link.get(KEY_LINK_B) not in selected_keys
        ]
        if len(self._power_links) == before:
            messagebox.showinfo(TITLE_REMOVE_POWER_LINK, MSG_POWER_NONE)
        self._redraw_canvas()

    def _wire_dio_to_roborio(self) -> None:
        """
        NAME
            _wire_dio_to_roborio - Create a physical wiring link to roboRIO.
        """
        selected = [n for n in self._device_nodes() if n.key in self._selected_nodes]
        dio_nodes = [n for n in selected if self._is_dio_node(n)]
        if len(dio_nodes) != 1:
            messagebox.showinfo(TITLE_WIRE_DIO, MSG_WIRE_SELECT)
            return
        roborio = self._roborio_node()
        if roborio is None:
            messagebox.showinfo(TITLE_WIRE_DIO, MSG_WIRE_NO_ROBORIO)
            return
        dio_node = dio_nodes[0]
        link = {KEY_LINK_ROBORIO: roborio.key, KEY_LINK_DEVICE: dio_node.key}
        if link in self._dio_wiring_links:
            messagebox.showinfo(TITLE_WIRE_DIO, MSG_WIRE_DUP)
            return
        self._push_undo()
        self._dio_wiring_links = [
            l for l in self._dio_wiring_links if l.get(KEY_LINK_DEVICE) != dio_node.key
        ]
        self._dio_wiring_links.append(link)
        self._dirty = True
        self._redraw_canvas()

    def _remove_dio_wire(self) -> None:
        """
        NAME
            _remove_dio_wire - Remove DIO wiring links for selected nodes.
        """
        selected_keys = {n.key for n in self._device_nodes() if n.key in self._selected_nodes}
        if not selected_keys:
            messagebox.showinfo(TITLE_REMOVE_DIO_WIRE, MSG_WIRE_REMOVE_SELECT)
            return
        before = len(self._dio_wiring_links)
        self._push_undo()
        self._dio_wiring_links = [
            link
            for link in self._dio_wiring_links
            if link.get(KEY_LINK_DEVICE) not in selected_keys
            and link.get(KEY_LINK_ROBORIO) not in selected_keys
        ]
        if len(self._dio_wiring_links) == before:
            messagebox.showinfo(TITLE_REMOVE_DIO_WIRE, MSG_WIRE_NONE)
        self._redraw_canvas()

    def _populate_neighbors_from_layout(self) -> None:
        """
        NAME
            _populate_neighbors_from_layout - Create neighbor metadata from layout.

        DESCRIPTION
            Uses each CAN-capable node's bus index and x coordinate to build
            explicit left/right adjacency metadata for the current diagram.
        """
        self._rebuild_neighbors_from_layout(push_undo=True, notify=True)

    def _rebuild_neighbors_from_layout(self, push_undo: bool, notify: bool) -> bool:
        """
        NAME
            _rebuild_neighbors_from_layout - Refresh neighbor metadata cache.

        RETURNS
            True when neighbor data was rebuilt or cleared.
        """
        neighbor_links, neighbor_ports = self._build_layout_neighbor_metadata(self._nodes)
        if not neighbor_links:
            if notify:
                messagebox.showinfo(TITLE_POPULATE_NEIGHBORS, MSG_POPULATE_NEIGHBORS_EMPTY)
            if self._has_neighbor_metadata():
                if push_undo:
                    self._push_undo()
                self._neighbor_links = []
                self._neighbor_ports = []
                self._mark_neighbors_current()
            return False
        if push_undo:
            self._push_undo()
        self._neighbor_links = neighbor_links
        self._neighbor_ports = neighbor_ports
        self._mark_neighbors_current()
        if notify:
            messagebox.showinfo(
                TITLE_POPULATE_NEIGHBORS,
                MSG_POPULATE_NEIGHBORS_DONE.format(len(neighbor_links), len(neighbor_ports)),
            )
        return True

    def _confirm_neighbors_current_for_save(self) -> bool:
        """
        NAME
            _confirm_neighbors_current_for_save - Guard saves with stale neighbors.

        RETURNS
            True when the save should continue.
        """
        if not self._has_neighbor_metadata() or not self._neighbors_dirty:
            return True
        choice = messagebox.askyesnocancel(TITLE_NEIGHBORS_STALE, MSG_NEIGHBORS_STALE_SAVE)
        if choice is None:
            return False
        if choice:
            self._rebuild_neighbors_from_layout(push_undo=False, notify=False)
        return True

    @staticmethod
    def _build_layout_neighbor_metadata(
        nodes: List[Node],
    ) -> Tuple[List[Dict[str, int]], List[Dict[str, object]]]:
        """
        NAME
            _build_layout_neighbor_metadata - Infer adjacency from drawn order.

        DESCRIPTION
            Groups CAN-capable non-callout nodes by bus, sorts each group by
            x coordinate, and connects adjacent nodes with both undirected
            links and directed left/right port links.
        """
        grouped: Dict[int, List[Node]] = {}
        for node in nodes:
            if node.node_type == NODE_TYPE_CALLOUT:
                continue
            if getattr(node, "interface", INTERFACE_CAN) != INTERFACE_CAN:
                continue
            grouped.setdefault(int(node.bus_index), []).append(node)

        neighbor_links: List[Dict[str, int]] = []
        neighbor_ports: List[Dict[str, object]] = []
        for _bus, bus_nodes in sorted(grouped.items()):
            ordered = sorted(bus_nodes, key=lambda item: (float(item.x), int(item.key)))
            for left, right in zip(ordered, ordered[1:]):
                a = min(int(left.key), int(right.key))
                b = max(int(left.key), int(right.key))
                neighbor_links.append({KEY_LINK_A: a, KEY_LINK_B: b})
                neighbor_ports.append(
                    {
                        KEY_LINK_NODE: int(left.key),
                        KEY_LINK_PORT: NEIGHBOR_PORT_RIGHT,
                        KEY_LINK_NEIGHBOR: int(right.key),
                        KEY_LINK_NEIGHBOR_PORT: NEIGHBOR_PORT_LEFT,
                    }
                )
                neighbor_ports.append(
                    {
                        KEY_LINK_NODE: int(right.key),
                        KEY_LINK_PORT: NEIGHBOR_PORT_LEFT,
                        KEY_LINK_NEIGHBOR: int(left.key),
                        KEY_LINK_NEIGHBOR_PORT: NEIGHBOR_PORT_RIGHT,
                    }
                )
        return neighbor_links, neighbor_ports

    def _is_dio_node(self, node: Node) -> bool:
        """
        NAME
            _is_dio_node - Return True when a node is a DIO device.
        """
        return node.interface == INTERFACE_DIO

    def _is_power_node(self, node: Node) -> bool:
        """
        NAME
            _is_power_node - Return True when a node should participate in power links.
        """
        return node.category in {"pdh", "pdp"} or node.category == TOPOLOGY_NODE_POWER

    def _is_power_source_node(self, node: Node) -> bool:
        """
        NAME
            _is_power_source_node - Return True for nodes allowed to source power links.
        """
        return node.category in {"pdh", "pdp", DIAGRAM_CATEGORY_CANNECT_DIRECT} or (
            node.category == TOPOLOGY_NODE_POWER
        )

    def _is_primary_power_source_node(self, node: Node) -> bool:
        """
        NAME
            _is_primary_power_source_node - Return True for full-power sources like PDH/PDP.
        """
        return node.category in {"pdh", "pdp"} or node.category == TOPOLOGY_NODE_POWER

    def _is_low_power_device_node(self, node: Node) -> bool:
        """
        NAME
            _is_low_power_device_node - Return True for low-power CAN endpoints.
        """
        return node.category in {"cancoders", "candles", "pigeon"}

    def _is_power_consumer_node(self, node: Node) -> bool:
        """
        NAME
            _is_power_consumer_node - Return True for nodes allowed to receive power links.
        """
        if self._is_dio_node(node):
            return False
        if self._is_power_source_node(node):
            return False
        return node.node_type != NODE_TYPE_CALLOUT

    def _is_valid_power_link_pair(self, left: Node, right: Node) -> bool:
        """
        NAME
            _is_valid_power_link_pair - Validate one source/consumer power-link pair.
        """
        if self._is_primary_power_source_node(left) and self._is_power_consumer_node(right):
            return True
        if self._is_primary_power_source_node(right) and self._is_power_consumer_node(left):
            return True
        return (
            self._is_power_source_node(left) and self._is_low_power_device_node(right)
        ) or (
            self._is_power_source_node(right) and self._is_low_power_device_node(left)
        )

    def _roborio_node(self) -> Optional[Node]:
        """
        NAME
            _roborio_node - Return the roboRIO node if present.
        """
        return next((n for n in self._device_nodes() if n.category == CATEGORY_ROBORIO), None)

    def _set_cannect_port(self) -> None:
        """
        NAME
            _set_cannect_port - Reassign a device to a different CANnect port.
        """
        selected_nodes = [n for n in self._device_nodes() if n.key in self._selected_nodes]
        device_nodes = [n for n in selected_nodes if not self._is_swyft_node(n)]
        if len(device_nodes) != BUS_INDEX_FLOOR:
            messagebox.showinfo(MSG_SET_PORT_TITLE, MSG_SET_PORT_SELECT)
            return
        device = device_nodes[0]
        link = next(
            (l for l in self._cannect_device_links if l.get("device") == device.key),
            None,
        )
        if link is None:
            messagebox.showinfo(MSG_SET_PORT_TITLE, MSG_SET_PORT_NO_LINK)
            return
        cannect_key = link.get("node")
        cannect = next((n for n in self._device_nodes() if n.key == cannect_key), None)
        if cannect is None:
            messagebox.showinfo(MSG_SET_PORT_TITLE, MSG_SET_PORT_NO_LINK)
            return
        max_ports = self._max_cannect_ports(cannect)
        if max_ports <= CANNECT_PORT_ZERO:
            messagebox.showinfo(MSG_SET_PORT_TITLE, MSG_SET_PORT_INVALID)
            return
        port = simpledialog.askinteger(
            MSG_SET_PORT_TITLE,
            PROMPT_PORT.format(max_ports),
            minvalue=CANNECT_PORT_MIN,
            maxvalue=max_ports,
        )
        if port is None:
            return
        if not isinstance(port, int):
            messagebox.showinfo(MSG_SET_PORT_TITLE, MSG_SET_PORT_INVALID)
            return
        used_ports = {
            int(l.get("port", CANNECT_PORT_ZERO))
            for l in self._cannect_device_links
            if l.get("node") == cannect.key and l.get("device") != device.key
        }
        if port in used_ports and not self._allow_multi_port_links(cannect):
            messagebox.showinfo(MSG_SET_PORT_TITLE, MSG_SET_PORT_BUSY.format(port))
            return
        self._push_undo()
        link["port"] = int(port)
        self._sync_cannect_bus_index(cannect)
        self._ensure_cannect_free_float(cannect)
        self._ensure_cannect_free_float(device)
        self._redraw_canvas()

    def _fix_cannect_conflicts(self, notify: bool = False) -> bool:
        """
        NAME
            _fix_cannect_conflicts - Remove CAN trunk links from Ethernet-linked CANnect nodes.

        PARAMETERS
            notify: When true, show a summary dialog.

        RETURNS
            True when any links were removed, False otherwise.
        """
        ethernet_nodes: set[int] = set()
        for a, b in self._ethernet_links:
            ethernet_nodes.add(a)
            ethernet_nodes.add(b)
        if not ethernet_nodes:
            if notify:
                messagebox.showinfo(MSG_FIX_CANNECT_TITLE, MSG_FIX_CANNECT_NONE)
            return False
        inject_nodes = {
            n.key
            for n in self._device_nodes()
            if n.key in ethernet_nodes and n.category == DIAGRAM_CATEGORY_CANNECT_INJECT
        }
        if not inject_nodes:
            if notify:
                messagebox.showinfo(MSG_FIX_CANNECT_TITLE, MSG_FIX_CANNECT_NONE)
            return False
        before = len(self._can_bus_links)
        self._can_bus_links = [
            link for link in self._can_bus_links if link.get("node") not in inject_nodes
        ]
        removed = before - len(self._can_bus_links)
        if removed > 0:
            self._dirty = True
            self._redraw_canvas()
        if notify:
            if removed > 0:
                messagebox.showinfo(
                    MSG_FIX_CANNECT_TITLE,
                    MSG_FIX_CANNECT_REMOVED.format(removed),
                )
            else:
                messagebox.showinfo(MSG_FIX_CANNECT_TITLE, MSG_FIX_CANNECT_NO_REMOVE)
        return removed > 0

    def _maybe_link_dragged_device_to_cannect(self, dragged_key: int) -> None:
        """
        NAME
            _maybe_link_dragged_device_to_cannect - Link a dragged device to a CANnect node.
        """
        node = next((n for n in self._nodes if n.key == dragged_key), None)
        if node is None or not getattr(node, "profile_visible", True):
            return
        if node.node_type == "callout" or self._is_swyft_node(node):
            return
        bounds = self._node_bounds.get(node.key)
        if not bounds:
            return
        cx = (bounds[0] + bounds[2]) / 2.0
        cy = (bounds[1] + bounds[3]) / 2.0
        target = None
        for other in self._nodes:
            if not self._is_swyft_node(other):
                continue
            ob = self._node_bounds.get(other.key)
            if not ob:
                continue
            pad = 12.0 * max(self._zoom, 0.5)
            if (ob[0] - pad) <= cx <= (ob[2] + pad) and (ob[1] - pad) <= cy <= (ob[3] + pad):
                target = other
                break
        if target is None:
            return
        self._link_device_to_cannect(target, node)

    def _link_device_to_cannect(self, cannect: Node, device: Node) -> None:
        """
        NAME
            _link_device_to_cannect - Attach a device to a CANnect node.
        """
        if not self._is_swyft_node(cannect):
            return
        if not getattr(device, "profile_visible", True) or device.node_type == "callout":
            return
        max_ports = self._max_cannect_ports(cannect)
        if max_ports <= 0:
            return
        if any(
            link.get("node") == cannect.key and link.get("device") == device.key
            for link in self._cannect_device_links
        ):
            return
        allow_multi = self._allow_multi_port_links(cannect)
        used_ports = [
            int(link.get("port", CANNECT_PORT_ZERO))
            for link in self._cannect_device_links
            if link.get("node") == cannect.key
        ]
        if len(used_ports) >= max_ports and not allow_multi:
            return
        if allow_multi:
            counts = self._cannect_port_counts(cannect, self._cannect_device_links, max_ports)
            port = self._select_least_loaded_port(counts)
        else:
            port = next(
                (p for p in range(CANNECT_PORT_MIN, max_ports + 1, CANNECT_PORT_STEP) if p not in used_ports),
                CANNECT_PORT_MIN,
            )
        self._push_undo()
        self._cannect_device_links = [
            link for link in self._cannect_device_links if link.get("device") != device.key
        ]
        self._cannect_device_links.append(
            {"node": cannect.key, "device": device.key, "port": port}
        )
        self._sync_cannect_bus_index(cannect)
        self._ensure_cannect_free_float(cannect)
        self._ensure_cannect_free_float(device)
        self._redraw_canvas()

    def _link_bus_to_cannect(self, cannect: Node, bus_index: int) -> None:
        """
        NAME
            _link_bus_to_cannect - Create a CAN bus link for a CANnect node.

        NOTES
            Disabled when ENABLE_CANNECT_BUS_LINKS is False.
        """
        if not ENABLE_CANNECT_BUS_LINKS:
            return
        if not self._is_swyft_node(cannect):
            return
        max_ports = self._max_cannect_ports(cannect)
        if max_ports <= 0:
            return
        if bus_index < 0 or bus_index >= len(self._bus_offsets):
            return
        allow_multi = self._allow_multi_port_links(cannect)
        existing_ports = [
            int(link.get("port", CANNECT_PORT_ZERO))
            for link in self._can_bus_links
            if link.get("node") == cannect.key
        ]
        if len(existing_ports) >= max_ports and not allow_multi:
            return
        for link in self._can_bus_links:
            if link.get("node") == cannect.key and link.get("bus") == bus_index:
                return
        if allow_multi:
            counts = self._cannect_port_counts(cannect, self._can_bus_links, max_ports)
            port = self._select_least_loaded_port(counts)
        else:
            port = next(
                (p for p in range(CANNECT_PORT_MIN, max_ports + 1, CANNECT_PORT_STEP) if p not in existing_ports),
                CANNECT_PORT_MIN,
            )
        self._push_undo()
        self._can_bus_links.append({"node": cannect.key, "bus": bus_index, "port": port})
        self._sync_cannect_bus_index(cannect)
        self._redraw_canvas()
    def _on_edit(self) -> None:
        """
        NAME
            _on_edit - Edit the currently selected node.
        """
        node = self._get_selected_node()
        if node is None:
            messagebox.showinfo("Edit", "Select a node to edit.")
            return
        dialog = NodeDialog(self, "Edit Node", initial=node)
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        old_label = node.label
        new_label = str(data["label"]).strip()
        if old_label and new_label and old_label != new_label:
            if not self._confirm_label_rename(old_label, new_label):
                return
        self._push_undo()
        category = str(data["category"])
        if category in SINGLETON_CATEGORIES:
            if any(n.category == category and n.key != node.key for n in self._nodes):
                messagebox.showerror("Invalid", f"Only one {category} is allowed.")
                return
        node.category = category
        node.label = new_label or str(data["label"])
        node.can_id = int(data["can_id"])
        node.node_type = ANALYZER_NODE_TYPE if category in DIAGRAM_CATEGORIES else NODE_TYPE_DEVICE
        node.interface = str(data.get("interface", INTERFACE_CAN)).strip() or INTERFACE_CAN
        node.vendor = str(data.get("vendor", ""))
        node.device_type = str(data.get("device_type", ""))
        node.motor = str(data.get("motor", ""))
        node.limits = data.get("limits") if isinstance(data.get("limits"), dict) else None
        node.dio = data.get("dio") if node.interface == INTERFACE_DIO else None
        node.invert = data.get("dio_invert") if node.interface == INTERFACE_DIO else None
        node.terminator = (
            bool(data.get("terminator")) if data.get("terminator") is not None else None
        )
        node.bus_index = int(data.get("bus_index", node.bus_index))
        node.row = int(data.get("row", node.row))
        node.x = float(data.get("x", node.x))
        node.scale = max(0.6, min(2.0, float(data.get("scale", node.scale))))
        node.free_y = data.get("free_y") if isinstance(data.get("free_y"), (int, float)) else None
        node.profile_visible = bool(data.get("profile_visible"))
        node.tags = self._normalize_tags(data.get("tags", []))
        if old_label and new_label and old_label != new_label:
            self._apply_node_label_change(node, old_label, new_label)
        self._prune_attachment_links()
        self._prune_power_links()
        self._prune_dio_wiring_links()
        self._ensure_dio_wiring_links()
        self._refresh_list()
        self._redraw_canvas()
        self._select_node(node.key)

    def _edit_diagram_node(self, node: Node) -> None:
        """
        NAME
            _edit_diagram_node - Edit label/tags for a diagram-only node.
        """
        dialog = tk.Toplevel(self)
        dialog.title("Edit Diagram Node")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Label").grid(row=0, column=0, sticky="w")
        label_var = tk.StringVar(value=node.label)
        ttk.Entry(frame, textvariable=label_var, width=26).grid(row=0, column=1, sticky="w")

        ttk.Label(frame, text="Tags").grid(row=1, column=0, sticky="w")
        tags_var = tk.StringVar(value=", ".join(node.tags or []))
        ttk.Entry(frame, textvariable=tags_var, width=26).grid(row=1, column=1, sticky="w")

        result = {"ok": False}

        def _ok() -> None:
            if not label_var.get().strip():
                messagebox.showerror("Invalid", "Label is required.")
                return
            result["ok"] = True
            dialog.destroy()

        def _cancel() -> None:
            dialog.destroy()

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text="Cancel", command=_cancel).pack(side="right", padx=4)
        ttk.Button(buttons, text="OK", command=_ok).pack(side="right")

        self.wait_window(dialog)
        if not result["ok"]:
            return
        self._push_undo()
        node.label = label_var.get().strip()
        node.tags = self._normalize_tags(tags_var.get())
        self._refresh_list()
        self._redraw_canvas()

    def _on_remove(self) -> None:
        """
        NAME
            _on_remove - Remove the selected node from the current profile.
        """
        node = self._get_selected_node()
        if node is None:
            messagebox.showinfo(TITLE_REMOVE_FROM_PROFILE, MSG_REMOVE_NODE_SELECT)
            return
        removed_label = (node.label or TEXT_EMPTY).strip()
        self._push_undo()
        self._nodes = [n for n in self._nodes if n.key != node.key]
        self._selected_key = None
        if removed_label:
            self._prune_current_profile_bridge_config_label(removed_label)
        self._prune_attachment_links()
        self._prune_power_links()
        self._prune_dio_wiring_links()
        self._dirty = True
        self._refresh_list()
        self._update_details_panel(None)
        self._mark_neighbors_stale()
        self._redraw_canvas()

    def _on_edit_selected(self) -> None:
        """
        NAME
            _on_edit_selected - Edit the selected node or callout.
        """
        if self._selected_inventory_label and not self._selected_nodes and not self._selected_buses:
            if self._edit_selected_inventory_item():
                return
            messagebox.showinfo("Edit", MSG_INVENTORY_EDIT_UNSUPPORTED)
            return
        if self._selected_buses:
            messagebox.showinfo("Edit", "Bus segments are not editable.")
            return
        if len(self._selected_nodes) == 1:
            node = self._get_selected_node()
            if node is not None and node.node_type == "callout":
                self._on_edit_callout()
            else:
                self._on_edit()
            return
        messagebox.showinfo("Edit", "Select a single node or callout to edit.")

    def _on_remove_selected(self) -> None:
        """
        NAME
            _on_remove_selected - Remove selected nodes and callouts from the current profile.
        """
        if self._selected_inventory_label and not self._selected_nodes and not self._selected_buses:
            if self._remove_selected_inventory_item():
                return
            messagebox.showinfo(TITLE_REMOVE_FROM_PROFILE, MSG_INVENTORY_EDIT_UNSUPPORTED)
            return
        if self._selected_buses and not self._selected_nodes:
            if not self._remove_selected_buses():
                return
            self._refresh_list()
            self._update_details_panel(None)
            self._mark_neighbors_stale()
            self._redraw_canvas()
            return
        if not self._selected_nodes:
            messagebox.showinfo(TITLE_REMOVE_FROM_PROFILE, MSG_REMOVE_SELECTION_SELECT)
            return
        if not messagebox.askyesno(TITLE_REMOVE_FROM_PROFILE, MSG_REMOVE_SELECTION_CONFIRM):
            return
        removed_labels = [
            (n.label or TEXT_EMPTY).strip()
            for n in self._nodes
            if n.key in self._selected_nodes and (n.label or TEXT_EMPTY).strip()
        ]
        self._push_undo()
        self._nodes = [n for n in self._nodes if n.key not in self._selected_nodes]
        self._clear_selection()
        for label in removed_labels:
            self._prune_current_profile_bridge_config_label(label)
        self._prune_attachment_links()
        self._prune_power_links()
        self._prune_dio_wiring_links()
        self._dirty = True
        self._refresh_list()
        self._update_details_panel(None)
        self._mark_neighbors_stale()
        self._redraw_canvas()

    def _on_delete_from_app_selected(self) -> None:
        """
        NAME
            _on_delete_from_app_selected - Delete one selected shared device definition from the app entirely.
        """
        if self._selected_inventory_label and not self._selected_nodes and not self._selected_buses:
            if self._delete_inventory_entry_globally(self._selected_inventory_label):
                return
            messagebox.showinfo(TITLE_DELETE_FROM_APP, MSG_DELETE_APP_UNSUPPORTED)
            return
        if self._selected_buses or not self._selected_nodes or len(self._selected_nodes) != COUNT_ONE:
            messagebox.showinfo(TITLE_DELETE_FROM_APP, MSG_DELETE_APP_SELECT_SINGLE)
            return
        node = self._get_selected_node()
        if node is None or not self._is_registry_device_node(node):
            messagebox.showinfo(TITLE_DELETE_FROM_APP, MSG_DELETE_APP_UNSUPPORTED)
            return
        label = str(node.label or TEXT_EMPTY).strip()
        if not label:
            messagebox.showinfo(TITLE_DELETE_FROM_APP, MSG_DELETE_APP_UNSUPPORTED)
            return
        self._delete_device_label_from_app(label)

    def _remove_selected_buses(self) -> bool:
        """
        NAME
            _remove_selected_buses - Remove selected empty bus segments.

        RETURNS
            True when buses were removed, False when blocked.
        """
        indices = sorted(set(idx for idx in self._selected_buses if 0 <= idx < len(self._bus_offsets)))
        if not indices:
            messagebox.showinfo("Remove", "Select bus segments to remove.")
            return False
        if len(self._bus_offsets) - len(indices) < 1:
            messagebox.showinfo("Remove", "At least one bus segment is required.")
            return False
        device_nodes = self._device_nodes()
        callouts = self._callout_nodes()
        for idx in indices:
            blocking_nodes = [node for node in device_nodes if node.bus_index == idx]
            blocking_callouts = [
                callout
                for callout in callouts
                if callout.callout_target_type == "bus" and callout.callout_target_bus == idx
            ]
            if any(node.bus_index == idx for node in device_nodes):
                labels = [n.label for n in blocking_nodes if n.label]
                if not labels:
                    labels = [f"Node {n.key}" for n in blocking_nodes]
                messagebox.showinfo(
                    "Remove",
                    "Bus segment has nodes attached and cannot be removed.\n\n"
                    "Blocking nodes:\n- " + "\n- ".join(labels),
                )
                return False
            if blocking_callouts:
                labels = [c.callout_text or c.label for c in blocking_callouts]
                if not labels:
                    labels = [f"Callout {c.key}" for c in blocking_callouts]
                messagebox.showinfo(
                    "Remove",
                    "Bus segment has callouts attached and cannot be removed.\n\n"
                    "Blocking callouts:\n- " + "\n- ".join(labels),
                )
                return False
        if not messagebox.askyesno("Remove", "Remove selected empty bus segments?"):
            return False
        self._push_undo()
        for idx in reversed(indices):
            del self._bus_offsets[idx]
            if idx < len(self._bus_lefts):
                del self._bus_lefts[idx]
            if idx < len(self._bus_rights):
                del self._bus_rights[idx]
        if self._bus_connectors:
            surviving = [i for i in range(len(self._bus_offsets) + len(indices)) if i not in indices]
            index_map = {old: new for new, old in enumerate(surviving)}
            new_connectors: List[bool] = []
            new_connector_sides: List[str] = []
            for old_idx in range(len(self._bus_connectors)):
                a = old_idx
                b = old_idx + BUS_INDEX_FLOOR
                if a in index_map and b in index_map and index_map[b] == index_map[a] + BUS_INDEX_FLOOR:
                    new_connectors.append(self._bus_connectors[old_idx])
                    new_connector_sides.append(self._bus_connector_side(old_idx))
            self._bus_connectors = new_connectors
            self._bus_connector_sides = new_connector_sides
        self._ensure_bus_connectors(len(self._bus_offsets))
        self._ensure_bus_connector_sides(len(self._bus_offsets))
        def _shift_index(old: int) -> int:
            return old - sum(1 for removed in indices if removed < old)
        for node in device_nodes:
            if node.bus_index in indices:
                node.bus_index = 0
            else:
                node.bus_index = _shift_index(node.bus_index)
        for callout in callouts:
            if callout.callout_target_type != "bus":
                continue
            if callout.callout_target_bus in indices:
                callout.callout_target_bus = 0
            else:
                callout.callout_target_bus = _shift_index(callout.callout_target_bus)
        self._clear_selection()
        return True

    def _selected_cannect_direct_key(self) -> Optional[int]:
        """
        NAME
            _selected_cannect_direct_key - Return selected CANnect Direct key if singular.
        """
        selected_nodes = [n for n in self._device_nodes() if n.key in self._selected_nodes]
        direct_nodes = [
            n for n in selected_nodes if n.category == DIAGRAM_CATEGORY_CANNECT_DIRECT
        ]
        if len(direct_nodes) == BUS_INDEX_FLOOR:
            return direct_nodes[0].key
        return None

    def _maybe_link_new_bus_to_cannect_direct(self, node_key: int, bus_index: int) -> None:
        """
        NAME
            _maybe_link_new_bus_to_cannect_direct - Link new bus to selected CANnect Direct.
        """
        node = next((n for n in self._device_nodes() if n.key == node_key), None)
        if node is None or node.category != DIAGRAM_CATEGORY_CANNECT_DIRECT:
            messagebox.showinfo(MSG_CAN_BUS_LINK_TITLE, MSG_ADD_BUS_CONN_INVALID)
            return
        max_ports = self._max_cannect_ports(node)
        if max_ports <= CANNECT_PORT_ZERO:
            messagebox.showinfo(MSG_CAN_BUS_LINK_TITLE, MSG_CAN_BUS_LINK_NODE_INVALID)
            return
        for link in self._can_bus_links:
            if link.get("node") == node.key and link.get("bus") == bus_index:
                messagebox.showinfo(MSG_CAN_BUS_LINK_TITLE, MSG_ADD_BUS_CONN_DUP)
                return
        allow_multi = self._allow_multi_port_links(node)
        existing_ports = [
            int(link["port"])
            for link in self._can_bus_links
            if link.get("node") == node.key
        ]
        if not allow_multi and len(existing_ports) >= max_ports:
            messagebox.showinfo(
                MSG_CAN_BUS_LINK_TITLE,
                MSG_ADD_BUS_CONN_FULL.format(node.label, max_ports),
            )
            return
        if allow_multi:
            counts = self._cannect_port_counts(node, self._can_bus_links, max_ports)
            port = self._select_least_loaded_port(counts)
        else:
            port = next(
                (p for p in range(CANNECT_PORT_MIN, max_ports + 1, CANNECT_PORT_STEP) if p not in existing_ports),
                CANNECT_PORT_MIN,
            )
        self._can_bus_links.append({"node": node.key, "bus": bus_index, "port": port})
        self._sync_cannect_bus_index(node)

    def _restore_missing_cannect_bus_links(self) -> None:
        """
        NAME
            _restore_missing_cannect_bus_links - Rebuild only missing CANnect Inject trunk links.
        """
        linked_nodes = {
            int(link.get("node"))
            for link in self._can_bus_links
            if isinstance(link.get("node"), int)
        }
        max_bus_index = len(self._bus_offsets) - BUS_INDEX_FLOOR
        for node in self._device_nodes():
            if node.category != DIAGRAM_CATEGORY_CANNECT_INJECT:
                continue
            if node.key in linked_nodes:
                continue
            if not isinstance(node.bus_index, int) or node.bus_index < COUNT_ZERO or node.bus_index > max_bus_index:
                continue
            self._can_bus_links.append(
                {"node": int(node.key), "bus": int(node.bus_index), "port": CANNECT_PORT_MIN}
            )

    def _sync_cannect_bus_index(self, cannect: Node) -> None:
        """
        NAME
            _sync_cannect_bus_index - Anchor CANnect bus index to its trunk link.
        """
        if not self._is_swyft_node(cannect):
            return
        port_map: Dict[int, int] = {}
        for link in self._can_bus_links:
            if link.get("node") != cannect.key:
                continue
            bus_index = link.get("bus")
            port = link.get("port", CANNECT_PORT_MIN)
            if isinstance(bus_index, int) and isinstance(port, int):
                port_map[int(port)] = int(bus_index)
        if not port_map:
            return
        if CANNECT_PORT_MIN in port_map:
            cannect.bus_index = port_map[CANNECT_PORT_MIN]
        elif len(port_map) == BUS_INDEX_FLOOR:
            cannect.bus_index = next(iter(port_map.values()))

    def _refresh_list(self) -> None:
        """
        NAME
            _refresh_list - Update the listbox contents.
        """
        self._destroy_inline_editor()
        for item in self.node_list.get_children():
            self.node_list.delete(item)
        node_groups = self._node_groups_by_label()
        profiles_by_label = self._profiles_by_label() if self._list_scope_var.get() == LIST_SCOPE_FULL else {}
        nodes = list(self._device_nodes())
        if self._tag_filter_fn is not None:
            nodes = [n for n in nodes if self._tag_filter_fn(n)]
        nodes = sort_nodes(nodes, self._list_sort_var.get())
        node_labels = {
            (node.label or TEXT_EMPTY).strip()
            for node in nodes
            if (node.label or TEXT_EMPTY).strip()
        }
        for node in nodes:
            can_id = "" if not isinstance(node.can_id, int) or node.can_id < 0 else str(node.can_id)
            groups = SEP_COMMA_SPACE.join(node_groups.get(node.label, []))
            tags = self._tags_to_string(node.tags)
            profiles = SEP_COMMA_SPACE.join(profiles_by_label.get(node.label, []))
            self.node_list.insert(
                "",
                "end",
                iid=str(node.key),
                values=(can_id, node.category, node.label, groups, tags, profiles),
            )
        if self._list_scope_var.get() == LIST_SCOPE_FULL:
            full_inventory_entries = self._full_config_inventory_entries()
            registry_source = set(full_inventory_entries.keys())
        else:
            full_inventory_entries = {}
            registry_source = {
                str(label).strip()
                for label in list(self.__dict__.get("_non_topology_profile_labels", []) or [])
                if str(label).strip()
            }
        registry_labels = sorted(label for label in registry_source if label not in node_labels)
        for label in registry_labels:
            entry = (
                full_inventory_entries.get(label)
                if self._list_scope_var.get() == LIST_SCOPE_FULL
                else self._inventory_entry_for_label(label)
            )
            if isinstance(entry, dict):
                can_id = TEXT_EMPTY
                if self._is_can_device_entry(entry):
                    category = self._category_for_device(entry)
                    entry_id = entry.get("id")
                    if isinstance(entry_id, int) and entry_id >= 0:
                        can_id = str(entry_id)
                elif self._is_dio_device_entry(entry):
                    category = GENERIC_CATEGORY
                else:
                    category = (
                        str(entry.get(KEY_CATEGORY) or entry.get(KEY_TYPE) or GENERIC_CATEGORY).strip()
                        or GENERIC_CATEGORY
                    )
                tags = self._tags_to_string(self._normalize_tags(entry.get(KEY_TAGS, [])))
            else:
                can_id = TEXT_EMPTY
                category = GENERIC_CATEGORY
                tags = TEXT_EMPTY
            groups = SEP_COMMA_SPACE.join(node_groups.get(label, []))
            profiles = SEP_COMMA_SPACE.join(profiles_by_label.get(label, []))
            self.node_list.insert(
                TEXT_EMPTY,
                "end",
                iid=self._inventory_row_id(label),
                values=(can_id, category, label, groups, tags, profiles),
            )

    def _on_list_scope_changed(self, _event: tk.Event) -> None:
        """
        NAME
            _on_list_scope_changed - Refresh the left list when scope changes.
        """
        self._refresh_list()

    def _node_groups_by_label(self) -> Dict[str, List[str]]:
        """
        NAME
            _node_groups_by_label - Return bridge group names keyed by object label.
        """
        groups_by_label: Dict[str, List[str]] = {}
        for group in self._bridge_groups():
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name", TEXT_EMPTY)).strip()
            if not group_name:
                continue
            members = group.get(KEY_BRIDGE_GROUP_MEMBERS, []) or []
            if not isinstance(members, list):
                continue
            for member in members:
                label = TEXT_EMPTY
                if isinstance(member, dict):
                    label = bridge_group_member_label(member)
                elif isinstance(member, str):
                    label = member.strip()
                if not label:
                    continue
                names = groups_by_label.setdefault(label, [])
                if group_name not in names:
                    names.append(group_name)
        return groups_by_label

    def _on_list_edit_start(self, event: tk.Event) -> None:
        """
        NAME
            _on_list_edit_start - Begin inline editing in the node list.
        """
        if self._inline_editor is not None:
            self._destroy_inline_editor()
        region = self.node_list.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.node_list.identify_row(event.y)
        if not row_id:
            return
        column_id = self.node_list.identify_column(event.x)
        if not column_id:
            return
        try:
            col_index = int(column_id.lstrip("#")) - 1
        except ValueError:
            return
        columns = list(self.node_list["columns"])
        if col_index < 0 or col_index >= len(columns):
            return
        column_name = columns[col_index]
        if column_name not in ("can_id", "type", "label", "tags"):
            return
        node = next((n for n in self._nodes if str(n.key) == row_id), None)
        if node is None:
            return
        bbox = self.node_list.bbox(row_id, column=column_id)
        if not bbox:
            return
        x, y, w, h = bbox
        value = self.node_list.set(row_id, column_name)
        self._inline_edit_info = {
            "node": node,
            "column": column_name,
            "row_id": row_id,
        }

        if column_name == "type":
            categories = (
                BUCKET_CATEGORIES
                + SINGLETON_CATEGORIES
                + [GENERIC_CATEGORY]
                + list(DIAGRAM_CATEGORIES)
            )
            categories = list(dict.fromkeys(categories))
            editor: tk.Widget = ttk.Combobox(
                self.node_list, values=categories, state="normal"
            )
            if value in categories:
                editor.set(value)
            else:
                editor.set(node.category)
            editor.bind("<<ComboboxSelected>>", self._on_list_edit_commit)
        else:
            editor = ttk.Entry(self.node_list)
            editor.insert(0, value)
            editor.select_range(0, "end")
            editor.bind("<Return>", self._on_list_edit_commit)

        editor.bind("<Escape>", self._on_list_edit_cancel)
        editor.bind("<FocusOut>", self._on_list_edit_commit)
        editor.place(x=x, y=y, width=w, height=h)
        editor.focus_set()
        self._inline_editor = editor

    def _on_list_edit_cancel(self, _event: tk.Event) -> None:
        """
        NAME
            _on_list_edit_cancel - Cancel inline list editing.
        """
        self._destroy_inline_editor()

    def _on_delete_key(self, _event: tk.Event) -> None:
        """
        NAME
            _on_delete_key - Handle delete/backspace without breaking text edits.
        """
        widget = self.focus_get()
        if isinstance(widget, (tk.Entry, ttk.Entry, ttk.Combobox)):
            return
        self._on_remove_selected()

    def _on_list_edit_commit(self, _event: tk.Event) -> None:
        """
        NAME
            _on_list_edit_commit - Commit inline list edits to the node.
        """
        if self._inline_editor is None or self._inline_edit_info is None:
            return
        node = self._inline_edit_info.get("node")
        column = self._inline_edit_info.get("column")
        if not isinstance(node, Node) or not isinstance(column, str):
            self._destroy_inline_editor()
            return
        if isinstance(self._inline_editor, ttk.Combobox):
            new_value = self._inline_editor.get().strip()
        else:
            new_value = str(self._inline_editor.get()).strip()

        selected_items = list(self.node_list.selection())
        if selected_items:
            target_keys = []
            for item in selected_items:
                try:
                    target_keys.append(int(item))
                except ValueError:
                    continue
        else:
            target_keys = [node.key]
        targets = [n for n in self._nodes if n.key in target_keys]

        if column == "can_id":
            if new_value == "":
                can_id = -1
            else:
                try:
                    can_id = int(new_value)
                except ValueError:
                    self._reject_inline_edit(f"CAN ID must be an integer: '{new_value}'.")
                    return
            if not self._is_valid_can_id(can_id):
                self._reject_inline_edit(f"Invalid CAN ID {can_id}.")
                return
            for target in targets:
                target.can_id = can_id
        elif column == "type":
            category = new_value
            if not category:
                self._reject_inline_edit("Type is required.")
                return
            if category in SINGLETON_CATEGORIES:
                if len(targets) > 1:
                    self._reject_inline_edit(f"Only one {category} is allowed.")
                    return
                if any(n.category == category and n.key != targets[0].key for n in self._nodes):
                    self._reject_inline_edit(f"Only one {category} is allowed.")
                    return
            for target in targets:
                target.category = category
        elif column == "label":
            if not new_value:
                self._reject_inline_edit("Label is required.")
                return
            for target in targets:
                target.label = new_value
        elif column == "tags":
            tags = self._normalize_tags(new_value)
            for target in targets:
                target.tags = tags

        self._dirty = True
        self._destroy_inline_editor()
        self._refresh_list()
        self._redraw_canvas()

    def _destroy_inline_editor(self) -> None:
        """
        NAME
            _destroy_inline_editor - Tear down any active inline editor widget.
        """
        if self._inline_editor is not None:
            try:
                self._inline_editor.destroy()
            except tk.TclError:
                pass
        self._inline_editor = None
        self._inline_edit_info = None

    def _reject_inline_edit(self, message: str) -> None:
        """
        NAME
            _reject_inline_edit - Show validation error and keep editor active.
        """
        messagebox.showerror("Invalid", message)
        if self._inline_editor is None:
            return
        try:
            self._inline_editor.focus_set()
            if isinstance(self._inline_editor, ttk.Entry):
                self._inline_editor.select_range(0, "end")
            elif isinstance(self._inline_editor, ttk.Combobox):
                self._inline_editor.selection_range(0, "end")
        except tk.TclError:
            pass

    def _layout_even(self) -> None:
        """
        NAME
            _layout_even - Reset layout per bus without reassigning buses/rows.
        """
        if not self._nodes:
            self._redraw_canvas()
            return
        self._push_undo()
        eff_lefts, eff_rights = self._effective_bus_bounds()
        reset_layout_per_bus(
            self._device_nodes(),
            eff_lefts,
            eff_rights,
            self._box_w,
            bool(self._snap_to_grid_var.get()),
            int(self._grid_size_var.get() or 1),
        )
        max_x = max((n.x for n in self._nodes), default=0.0)
        self._layout_width = max(self._layout_width, max_x + 200)
        self._clear_guides()
        self._mark_neighbors_stale()
        self._redraw_canvas()

    def _layout_single_bus(self) -> None:
        """
        NAME
            _layout_single_bus - Arrange all device nodes on one bus segment.
        """
        if not self._nodes:
            self._redraw_canvas()
            return
        self._push_undo()
        self._bus_offsets = [0.0]
        self._bus_lefts = self._bus_lefts[:1] if self._bus_lefts else [40.0]
        self._bus_rights = self._bus_rights[:1] if self._bus_rights else []
        devices = self._device_nodes()
        for node in devices:
            node.bus_index = 0
            node.row = 0
            node.free_y = 0.0
        max_x = max((n.x for n in devices), default=0.0)
        if not self._bus_rights:
            self._bus_rights = [max_x + 400.0]
        eff_lefts, eff_rights = self._effective_bus_bounds()
        reset_layout_per_bus(
            devices,
            eff_lefts,
            eff_rights,
            self._box_w,
            bool(self._snap_to_grid_var.get()),
            int(self._grid_size_var.get() or 1),
        )
        max_x = max((n.x for n in self._nodes), default=0.0)
        self._layout_width = max(self._layout_width, max_x + 200)
        self._clear_guides()
        self._mark_neighbors_stale()
        self._redraw_canvas()

    def _selected_device_nodes(self) -> List[Node]:
        """
        NAME
            _selected_device_nodes - Return selected device nodes only.
        """
        return [n for n in self._device_nodes() if n.key in self._selected_nodes]

    def _effective_bus_bounds(self) -> Tuple[List[float], List[float]]:
        """
        NAME
            _effective_bus_bounds - Compute bus left/right bounds with connectors.

        RETURNS
            Tuple of (effective_lefts, effective_rights) per bus segment.
        """
        max_node_x = max((n.x for n in self._nodes), default=0.0)
        self._bus_lefts, self._bus_rights, eff_lefts, eff_rights = effective_bus_bounds(
            self._bus_offsets, self._bus_lefts, self._bus_rights, max_node_x
        )
        return eff_lefts, eff_rights

    def _node_half_width(self, node: Node) -> float:
        """
        NAME
            _node_half_width - Compute half the node width in diagram units.
        """
        return node_half_width(node, self._box_w)

    def _snap_value(self, value: float) -> float:
        """
        NAME
            _snap_value - Snap a value to the current grid size.
        """
        return snap_value(value, int(self._grid_size_var.get() or 1))

    def _nudge_step(self, event: tk.Event) -> float:
        """
        NAME
            _nudge_step - Determine nudge step size for keyboard moves.
        """
        if self._snap_to_grid_var.get():
            base = int(self._grid_size_var.get() or 1)
        else:
            base = 5
        if base < 1:
            base = 1
        if event.state & 0x0001:
            base *= 5
        return float(base)

    def _nudge_selection(self, direction: str, event: tk.Event) -> str:
        """
        NAME
            _nudge_selection - Nudge selected nodes with arrow keys.
        """
        if not self._selected_nodes:
            return "break"
        nodes = [n for n in self._nodes if n.key in self._selected_nodes]
        if not nodes:
            return "break"
        step = self._nudge_step(event)
        dx = 0.0
        dy = 0.0
        if direction == "left":
            dx = -step
        elif direction == "right":
            dx = step
        elif direction == "up":
            dy = -step
        elif direction == "down":
            dy = step
        if dx == 0.0 and dy == 0.0:
            return "break"
        self._push_undo()
        for node in nodes:
            if dx:
                node.x += dx
                if self._snap_to_grid_var.get():
                    node.x = self._snap_value(node.x)
            if dy:
                bus_index = min(
                    max(node.bus_index, 0), max(len(self._bus_offsets) - 1, 0)
                )
                bus_offset = self._bus_offsets[bus_index] if self._bus_offsets else 0.0
                if node.free_y is None:
                    node.free_y = self._node_center_y_unscaled(node) - bus_offset
                node.free_y = (node.free_y or 0.0) + dy
                if self._snap_to_grid_var.get():
                    node.free_y = self._snap_value(node.free_y)
        max_x = max((n.x for n in self._nodes), default=0.0)
        self._layout_width = max(self._layout_width, max_x + 200)
        self._dirty = True
        self._clear_guides()
        self._mark_neighbors_stale()
        self._redraw_canvas()
        return "break"

    def _clear_guides(self) -> None:
        """
        NAME
            _clear_guides - Clear any active smart guide lines.
        """
        self._guide_x = None
        self._guide_bus = None

    def _apply_smart_guides(
        self,
        node: Node,
        candidate_x: float,
        exclude_keys: set[int],
    ) -> Tuple[float, Optional[float]]:
        """
        NAME
            _apply_smart_guides - Snap to nearby node centers on the same bus.

        RETURNS
            Tuple of (new_x, guide_x or None).
        """
        if not self._smart_guides_var.get():
            return candidate_x, None
        scale = max(self._zoom, 0.01)
        threshold = self._guide_snap_px / scale
        nearest: Optional[float] = None
        nearest_score = float("inf")
        for other in self._device_nodes():
            if other.key in exclude_keys:
                continue
            dist = abs(other.x - candidate_x)
            if dist <= threshold:
                same_bus = 0.0 if other.bus_index == node.bus_index else 0.5
                score = dist + same_bus
                if score < nearest_score:
                    nearest = other.x
                    nearest_score = score
        if nearest is None:
            return candidate_x, None
        return nearest, nearest

    def _align_selected(self, mode: str) -> None:
        """
        NAME
            _align_selected - Align selected nodes horizontally.

        PARAMETERS
            mode - "left", "center", or "right".
        """
        nodes = self._selected_device_nodes()
        if not nodes:
            messagebox.showinfo("Align", "Select one or more device nodes to align.")
            return
        self._push_undo()
        eff_lefts, eff_rights = self._effective_bus_bounds()
        align_selected(
            nodes,
            self._selected_nodes,
            eff_lefts,
            eff_rights,
            mode,
            self._box_w,
            bool(self._snap_to_grid_var.get()),
            int(self._grid_size_var.get() or 1),
        )
        max_x = max((n.x for n in self._nodes), default=0.0)
        self._layout_width = max(self._layout_width, max_x + 200)
        self._clear_guides()
        self._mark_neighbors_stale()
        self._redraw_canvas()

    def _distribute_selected_horizontally(self) -> None:
        """
        NAME
            _distribute_selected_horizontally - Evenly space selected nodes.
        """
        nodes = self._selected_device_nodes()
        if len(nodes) < 3:
            messagebox.showinfo(
                "Distribute",
                "Select at least three device nodes to distribute.",
            )
            return
        self._push_undo()
        eff_lefts, eff_rights = self._effective_bus_bounds()
        distribute_selected_horizontally(
            nodes,
            self._selected_nodes,
            eff_lefts,
            eff_rights,
            self._box_w,
            bool(self._snap_to_grid_var.get()),
            int(self._grid_size_var.get() or 1),
        )
        max_x = max((n.x for n in self._nodes), default=0.0)
        self._layout_width = max(self._layout_width, max_x + 200)
        self._clear_guides()
        self._mark_neighbors_stale()
        self._redraw_canvas()

    def _tidy_selection(self) -> None:
        """
        NAME
            _tidy_selection - Tidy selected nodes within bus bounds.
        """
        nodes = self._selected_device_nodes()
        if not nodes:
            messagebox.showinfo("Tidy Selection", "Select one or more device nodes to tidy.")
            return
        eff_lefts, eff_rights = self._effective_bus_bounds()
        self._push_undo()
        tidy_selection(
            self._device_nodes(),
            self._selected_nodes,
            eff_lefts,
            eff_rights,
            self._box_w,
            bool(self._snap_to_grid_var.get()),
            int(self._grid_size_var.get() or 1),
        )
        max_x = max((n.x for n in self._nodes), default=0.0)
        self._layout_width = max(self._layout_width, max_x + 200)
        self._clear_guides()
        self._mark_neighbors_stale()
        self._redraw_canvas()

    def _tidy_all(self) -> None:
        """
        NAME
            _tidy_all - Tidy all device nodes while preserving bus assignments.
        """
        device_nodes = self._device_nodes()
        if not device_nodes:
            messagebox.showinfo("Tidy All", "No device nodes to tidy.")
            return
        prior_nodes = set(self._selected_nodes)
        prior_buses = set(self._selected_buses)
        try:
            self._selected_nodes = {n.key for n in device_nodes}
            self._selected_buses = set()
            self._tidy_selection()
        finally:
            self._selected_nodes = prior_nodes
            self._selected_buses = prior_buses
            self._sync_selection_state()

    def _next_x_position(self) -> float:
        """
        NAME
            _next_x_position - Pick a reasonable x position for a new node.
        """
        width = max(self.canvas.winfo_width(), 1)
        if not self._nodes:
            return width * 0.2
        max_x = max(node.x for node in self._nodes)
        return max_x + 180

    def _on_list_select(self, _event: tk.Event) -> None:
        """
        NAME
            _on_list_select - Sync selection from the listbox.
        """
        if self._suppress_list_select or self._syncing_selection:
            return
        selection = self.node_list.selection()
        if not selection:
            return
        inventory_labels = [
            item[len(INVENTORY_ROW_PREFIX):]
            for item in selection
            if item.startswith(INVENTORY_ROW_PREFIX)
        ]
        if inventory_labels:
            self._selected_inventory_label = inventory_labels[0]
            self._selected_nodes = set()
            self._selected_buses = set()
            self._selected_key = None
            self._clear_callout_details_fields()
            self._update_details_panel(
                self._inventory_details_node(self._selected_inventory_label)
            )
            self._update_selection_overlays()
            return
        selected_keys: set[int] = set()
        for item in selection:
            try:
                selected_keys.add(int(item))
            except ValueError:
                continue
        if not selected_keys:
            return
        self._selected_inventory_label = None
        self._selected_nodes = selected_keys
        self._selected_buses = set()
        self._sync_selection_state()

    def _on_list_press(self, event: tk.Event) -> None:
        """
        NAME
            _on_list_press - Record the pressed inventory row for a potential drag.
        """
        row_id = self.node_list.identify_row(event.y)
        self._list_drag_item = row_id if row_id.startswith(INVENTORY_ROW_PREFIX) else None
        self._list_drag_start = (int(event.x), int(event.y)) if self._list_drag_item else None
        self._list_dragging = False

    def _on_list_drag(self, event: tk.Event) -> None:
        """
        NAME
            _on_list_drag - Promote an inventory press into a drag once motion is clear.
        """
        if not self._list_drag_item or self._list_drag_start is None:
            return
        start_x, start_y = self._list_drag_start
        if self._drag_threshold_exceeded(float(event.x - start_x), float(event.y - start_y)):
            self._list_dragging = True

    def _on_global_left_release(self, _event: tk.Event) -> None:
        """
        NAME
            _on_global_left_release - Complete an inventory-to-canvas drag drop when active.
        """
        if not self._list_drag_item:
            return
        row_id = self._list_drag_item
        dragging = bool(self._list_dragging)
        self._list_drag_item = None
        self._list_drag_start = None
        self._list_dragging = False
        if not dragging:
            return
        label = self._inventory_label_from_row_id(row_id)
        if not label:
            return
        pointer_x = int(self.winfo_pointerx())
        pointer_y = int(self.winfo_pointery())
        canvas_left = int(self.canvas.winfo_rootx())
        canvas_top = int(self.canvas.winfo_rooty())
        canvas_right = canvas_left + int(self.canvas.winfo_width())
        canvas_bottom = canvas_top + int(self.canvas.winfo_height())
        if not (canvas_left <= pointer_x <= canvas_right and canvas_top <= pointer_y <= canvas_bottom):
            return
        local_x = pointer_x - canvas_left
        local_y = pointer_y - canvas_top
        canvas_x = float(self.canvas.canvasx(local_x))
        canvas_y = float(self.canvas.canvasy(local_y))
        self._add_inventory_label_to_canvas(label, canvas_x, canvas_y)

    def _add_inventory_label_to_canvas(self, label: str, cx: float, cy: float) -> None:
        """
        NAME
            _add_inventory_label_to_canvas - Add a registry device into the active profile at a canvas point.
        """
        entry = self._inventory_entry_for_label(label)
        if not isinstance(entry, dict):
            return
        if not self._is_topology_capable_inventory_entry(entry):
            messagebox.showinfo("Add to Profile", MSG_INVENTORY_DROP_UNSUPPORTED)
            return
        existing = next((node for node in self._device_nodes() if node.label == label), None)
        if existing is not None:
            self._select_node(existing.key)
            return
        node = self._node_from_device_def(entry)
        if node is None:
            messagebox.showinfo("Add to Profile", MSG_INVENTORY_DROP_UNSUPPORTED)
            return
        scale = max(self._zoom, 0.01)
        bus_index, row = self._nearest_bus_and_row(cy)
        node.x = max(float(cx) / scale, 0.0)
        node.bus_index = bus_index
        node.row = row
        node.scale = 1.0
        node.profile_visible = True
        self._push_undo()
        self._nodes.append(node)
        self._layout_width = max(self._layout_width, node.x + 200)
        self._non_topology_profile_labels = [
            existing_label
            for existing_label in self._non_topology_profile_labels
            if existing_label != label
        ]
        self._prune_attachment_links()
        self._prune_power_links()
        self._prune_dio_wiring_links()
        self._ensure_dio_wiring_links()
        self._refresh_list()
        self._mark_neighbors_stale()
        self._redraw_canvas()
        self._select_node(node.key)

    def _select_node(self, key: int) -> None:
        """
        NAME
            _select_node - Mark a node as selected and update styles.
        """
        self._set_single_node_selection(key)

    def _get_selected_node(self) -> Optional[Node]:
        """
        NAME
            _get_selected_node - Return the currently selected node.
        """
        if self._selected_key is None:
            return None
        for node in self._nodes:
            if node.key == self._selected_key:
                return node
        return None

    def _confirm_can_id_collisions(self, nodes: Optional[List[Node]] = None) -> bool:
        """
        NAME
            _confirm_can_id_collisions - Warn about duplicate CAN IDs.

        RETURNS
            True when ok to proceed, False to cancel save.
        """
        nodes = nodes if nodes is not None else self._profile_device_nodes()
        by_loose: Dict[int, List[Node]] = {}
        by_strict: Dict[Tuple[str, str, int], List[Node]] = {}
        for node in nodes:
            if not isinstance(node.can_id, int) or node.can_id < 0:
                continue
            can_id = int(node.can_id)
            by_loose.setdefault(can_id, []).append(node)
            vendor = self._vendor_key_for_node(node) or ""
            dev_type = self._device_type_key_for_node(node) or ""
            key = (vendor, dev_type, can_id)
            by_strict.setdefault(key, []).append(node)
        loose = {cid: items for cid, items in by_loose.items() if len(items) > 1}
        strict = {key: items for key, items in by_strict.items() if len(items) > 1}
        if not loose and not strict:
            return True
        lines = []
        if loose:
            lines.append("Loose collisions (same CAN ID, any device):")
            for cid, items in sorted(loose.items(), key=lambda item: item[0]):
                names = ", ".join(self._format_node_identity(n) for n in items)
                lines.append(f"  ID {cid}: {names}")
            lines.append("")
        if strict:
            lines.append("Strict collisions (same vendor + type + CAN ID):")
            for key, items in sorted(strict.items(), key=lambda item: item[0]):
                vendor, dev_type, cid = key
                details = f"{vendor}/{dev_type}"
                names = ", ".join(self._format_node_identity(n) for n in items)
                lines.append(f"  ID {cid} {details}: {names}")
            lines.append("")
        if loose and not strict:
            lines.append("Loose collisions may be intentional if vendor/type disambiguates IDs.")
        if strict:
            lines.append("Strict collisions indicate exact ID conflicts for the same device type.")
        lines.append("")
        lines.append("Save anyway?")
        return messagebox.askyesno("CAN ID Collision", "\n".join(lines))

    def _format_node_identity(self, node: Node) -> str:
        """
        NAME
            _format_node_identity - Build a short label for collision dialogs.
        """
        details = self._format_strict_descriptor(node)
        return f"{node.label} ({details})"

    def _format_strict_descriptor(self, node: Node) -> str:
        """
        NAME
            _format_strict_descriptor - Format category/vendor/type for strict collisions.
        """
        parts = [node.category]
        if node.vendor:
            parts.append(node.vendor)
        if node.device_type:
            parts.append(node.device_type)
        return "/".join(parts)

    def _device_nodes(self) -> List[Node]:
        """
        NAME
            _device_nodes - Return non-callout nodes.
        """
        return [n for n in self._nodes if n.node_type != "callout"]

    def _profile_device_nodes(self) -> List[Node]:
        """
        NAME
            _profile_device_nodes - Return nodes that belong in bringup profiles.
        """
        return [n for n in self._device_nodes() if self._is_registry_device_node(n)]

    def _callout_nodes(self) -> List[Node]:
        """
        NAME
            _callout_nodes - Return callout nodes only.
        """
        return [n for n in self._nodes if n.node_type == "callout"]

    def _node_box_dims(self, node: Node, scale: float) -> Tuple[float, float]:
        """
        NAME
            _node_box_dims - Return box width/height for a node at a scale.
        """
        return node_box_dims(node, self._box_w, self._box_h, scale)

    def _should_clamp_node_to_bus(self, node: Node) -> bool:
        """
        NAME
            _should_clamp_node_to_bus - Decide whether to clamp a node to bus bounds.
        """
        if node.node_type == "callout":
            return False
        if self._is_swyft_node(node):
            return True
        if node.node_type == "diagram" or not getattr(node, "profile_visible", True):
            return False
        return True

    def _clamp_nodes_to_bus_bounds(self, bus_indices: set[int]) -> None:
        """
        NAME
            _clamp_nodes_to_bus_bounds - Persist node positions inside resized bus spans.

        DESCRIPTION
            Redraw clamps visible node positions to the bus segment. When a bus
            endpoint is resized, persist the same clamp so diagram-only CANnect
            modules and their link ports follow the segment instead of snapping
            back on the next redraw or reload.
        """
        for node in self._device_nodes():
            if not self._should_clamp_node_to_bus(node):
                continue
            bus_index = min(max(node.bus_index, 0), max(len(self._bus_offsets) - 1, 0))
            if bus_index not in bus_indices:
                continue
            if bus_index >= len(self._bus_lefts) or bus_index >= len(self._bus_rights):
                continue
            seg_left = min(self._bus_lefts[bus_index], self._bus_rights[bus_index])
            seg_right = max(self._bus_lefts[bus_index], self._bus_rights[bus_index])
            min_x = min(seg_left + 20.0, seg_right - 20.0)
            max_x = max(seg_left + 20.0, seg_right - 20.0)
            node.x = min(max(node.x, min_x), max_x)

    def _clamp_node_x_to_current_bus_bounds(self, node: Node, candidate_x: float) -> float:
        """
        NAME
            _clamp_node_x_to_current_bus_bounds - Clamp a dragged node to the currently visible bus bounds.
        """

        if not self._should_clamp_node_to_bus(node):
            return candidate_x
        bus_index = min(max(node.bus_index, 0), max(len(self._bus_offsets) - 1, 0))
        draw_state = self.__dict__.get("_draw_state", {}) or {}
        bus_lefts = list(draw_state.get("bus_lefts", self._bus_lefts))
        bus_rights = list(draw_state.get("bus_rights", self._bus_rights))
        if bus_index >= len(bus_lefts) or bus_index >= len(bus_rights):
            eff_lefts, eff_rights = self._effective_bus_bounds()
            bus_lefts = list(eff_lefts)
            bus_rights = list(eff_rights)
        if bus_index >= len(bus_lefts) or bus_index >= len(bus_rights):
            return candidate_x
        seg_left = min(float(bus_lefts[bus_index]), float(bus_rights[bus_index]))
        seg_right = max(float(bus_lefts[bus_index]), float(bus_rights[bus_index]))
        node_scale = max(0.6, min(2.0, float(getattr(node, "scale", 1.0))))
        node_box_w, _node_box_h = self._node_box_dims(node, 1.0)
        half_w = (node_box_w * node_scale) / 2.0
        pad = max(20.0, half_w + 10.0)
        min_x = min(seg_left + pad, seg_right - pad)
        max_x = max(seg_left + pad, seg_right - pad)
        return min(max(candidate_x, min_x), max_x)

    def _node_box_y(self, node: Node, bus_y: float, box_h: float, scale: float) -> Tuple[float, float]:
        """
        NAME
            _node_box_y - Return top/bottom Y coordinates for a node box.
        """
        return node_box_y(node, bus_y, box_h, scale)

    def _node_bus_y(self, node: Node, bus_y: float, scale: float) -> float:
        """
        NAME
            _node_bus_y - Resolve the render rail for a node (CAN vs DIO).
        """
        if self._is_dio_node(node):
            return bus_y + DIO_RAIL_OFFSET * scale
        return bus_y

    def _confirm_label_rename(self, old: str, new: str) -> bool:
        """
        NAME
            _confirm_label_rename - Confirm label rename and reference updates.
        """
        return messagebox.askyesno(
            TITLE_RENAME_LABEL,
            MSG_RENAME_LABEL_CONFIRM.format(old=old, new=new),
        )

    def _rename_registry_label(self, old: str, new: str) -> None:
        """
        NAME
            _rename_registry_label - Update device registry label mappings.
        """
        if not self._device_registry_list or not self._device_registry:
            return
        old_key = old.strip().lower()
        entry = None
        for label, device in list(self._device_registry.items()):
            if label.strip().lower() == old_key:
                entry = device
                self._device_registry.pop(label, None)
                break
        if entry is None:
            return
        entry[KEY_LABEL] = new
        self._device_registry[new] = entry

    def _should_split_device_on_rename(self, node_key: int, old_label: str) -> bool:
        """
        NAME
            _should_split_device_on_rename - Treat a node rename as a new device when the old label is still in use.
        """

        old = str(old_label or TEXT_EMPTY).strip()
        if not old:
            return False
        old_lower = old.lower()
        if any(
            n.key != node_key
            and n.node_type == NODE_TYPE_DEVICE
            and str(n.label or TEXT_EMPTY).strip().lower() == old_lower
            for n in self._nodes
        ):
            return True
        if any(str(label).strip().lower() == old_lower for label in self._non_topology_profile_labels):
            return True
        references = [
            profile_name
            for profile_name in self._profile_references_for_label(old)
            if profile_name != self._profile_name
        ]
        return bool(references)

    def _apply_node_label_change(self, node: Node, old_label: str, new_label: str) -> None:
        """
        NAME
            _apply_node_label_change - Apply rename side effects for a node edit.
        """

        old = str(old_label or TEXT_EMPTY).strip()
        new = str(new_label or TEXT_EMPTY).strip()
        if not old or not new or old == new:
            return
        if self._should_split_device_on_rename(node.key, old):
            return
        self._rename_registry_label(old, new)
        self._update_bridge_config_label_refs(old, new)
        self._update_callout_target_labels(old, new)

    def _update_bridge_config_label_refs(self, old: str, new: str) -> int:
        """
        NAME
            _update_bridge_config_label_refs - Update bridgeConfig label references.
        """
        config = self._root_extras.get(KEY_BRIDGE_CONFIG)
        if not isinstance(config, dict):
            return COUNT_ZERO
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return COUNT_ZERO
        changed = COUNT_ZERO
        for entry in by_profile.values():
            if not isinstance(entry, dict):
                continue
            changed += self._update_bridge_config_entry_label_refs(entry, old, new)
        if changed > COUNT_ZERO:
            self._root_extras[KEY_BRIDGE_CONFIG] = config
        return changed

    def _update_bridge_config_entry_label_refs(self, entry: Dict[str, object], old: str, new: str) -> int:
        """
        NAME
            _update_bridge_config_entry_label_refs - Update label refs in one byProfile entry.
        """

        if not old or not new or old == new:
            return COUNT_ZERO
        changed = COUNT_ZERO
        old_lower = old.lower()
        for group in entry.get(KEY_BRIDGE_GROUPS, []) or []:
            if not isinstance(group, dict):
                continue
            members = group.get(KEY_BRIDGE_GROUP_MEMBERS, []) or []
            if not isinstance(members, list):
                continue
            for idx, member in enumerate(list(members)):
                if isinstance(member, dict):
                    name = bridge_group_member_label(member)
                    if name.lower() == old_lower:
                        member[KEY_LABEL] = new
                        member.pop(KEY_DEVICE, None)
                        changed += COUNT_ONE
                elif isinstance(member, str):
                    if member.strip().lower() == old_lower:
                        members[idx] = new
                        changed += COUNT_ONE
            group[KEY_BRIDGE_GROUP_MEMBERS] = members
        selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE)
        if isinstance(selected, dict):
            name = str(selected.get(KEY_DEVICE, TEXT_EMPTY)).strip()
            if name.lower() == old_lower:
                selected[KEY_DEVICE] = new
                changed += COUNT_ONE
        tests = entry.get(KEY_BRIDGE_TESTS)
        if isinstance(tests, dict):
            changed += self._update_tests_label_refs(tests, old, new)
        return changed

    def _update_tests_label_refs(self, tests: Dict[str, object], old: str, new: str) -> int:
        """
        NAME
            _update_tests_label_refs - Update test device references on rename.

        DESCRIPTION
            Updates known label-linked fields:
            - motorLabels[]
            - rotation.encoderKey
            - deadbandSweep.encoderKey (when present)
            - limitSwitch.id (when present)
        """

        changed = COUNT_ZERO
        old_lower = old.lower()
        test_sets = tests.get(KEY_TEST_SETS)
        if not isinstance(test_sets, dict):
            return COUNT_ZERO
        for set_name, entries in test_sets.items():
            _ = set_name
            if not isinstance(entries, list):
                continue
            for test in entries:
                if not isinstance(test, dict):
                    continue
                motor_labels = test.get(KEY_TEST_MOTOR_LABELS)
                if isinstance(motor_labels, list):
                    for idx, label in enumerate(list(motor_labels)):
                        if isinstance(label, str) and label.strip().lower() == old_lower:
                            motor_labels[idx] = new
                            changed += COUNT_ONE
                    test[KEY_TEST_MOTOR_LABELS] = motor_labels
                rotation = test.get(KEY_TEST_ROTATION)
                if isinstance(rotation, dict):
                    encoder_key = rotation.get(KEY_TEST_ENCODER_KEY)
                    if isinstance(encoder_key, str) and encoder_key.strip().lower() == old_lower:
                        rotation[KEY_TEST_ENCODER_KEY] = new
                        changed += COUNT_ONE
                sweep = test.get(KEY_TEST_DEADBAND_SWEEP)
                if isinstance(sweep, dict):
                    encoder_key = sweep.get(KEY_TEST_ENCODER_KEY)
                    if isinstance(encoder_key, str) and encoder_key.strip().lower() == old_lower:
                        sweep[KEY_TEST_ENCODER_KEY] = new
                        changed += COUNT_ONE
                limit_switch = test.get(KEY_TEST_LIMIT_SWITCH)
                if isinstance(limit_switch, dict):
                    ref = limit_switch.get(KEY_TEST_LIMIT_SWITCH_ID)
                    if isinstance(ref, str) and ref.strip().lower() == old_lower:
                        limit_switch[KEY_TEST_LIMIT_SWITCH_ID] = new
                        changed += COUNT_ONE
        return changed

    def _prune_bridge_config_label(self, label: str) -> int:
        """
        NAME
            _prune_bridge_config_label - Remove label references from bridgeConfig.

        DESCRIPTION
            Used when a device is deleted. Removes references from:
            - bridgeConfig.byProfile.*.groups members
            - bridgeConfig.byProfile.*.selectedDevice.device
            - bridgeConfig.byProfile.*.tests.test_sets entries (motorLabels, encoderKey, limitSwitch.id)
        """

        if not label:
            return COUNT_ZERO
        config = self._root_extras.get(KEY_BRIDGE_CONFIG)
        if not isinstance(config, dict):
            return COUNT_ZERO
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return COUNT_ZERO
        changed = COUNT_ZERO
        label_lower = label.lower()
        for entry in by_profile.values():
            if not isinstance(entry, dict):
                continue
            changed += self._prune_bridge_config_entry_label(entry, label, label_lower)
        if changed > COUNT_ZERO:
            self._root_extras[KEY_BRIDGE_CONFIG] = config
        return changed

    def _prune_current_profile_bridge_config_label(self, label: str) -> int:
        """
        NAME
            _prune_current_profile_bridge_config_label - Remove label refs from the active profile only.
        """

        if not label:
            return COUNT_ZERO
        config = self._root_extras.get(KEY_BRIDGE_CONFIG)
        if not isinstance(config, dict):
            return COUNT_ZERO
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return COUNT_ZERO
        profile_name = str(self._profile_name or TEXT_EMPTY).strip()
        entry = by_profile.get(profile_name)
        if not isinstance(entry, dict):
            return COUNT_ZERO
        changed = self._prune_bridge_config_entry_label(entry, label, label.lower())
        if changed > COUNT_ZERO:
            self._root_extras[KEY_BRIDGE_CONFIG] = config
        return changed

    def _prune_bridge_config_entry_label(
        self, entry: Dict[str, object], label: str, label_lower: str
    ) -> int:
        """
        NAME
            _prune_bridge_config_entry_label - Prune label refs in one byProfile entry.
        """

        changed = COUNT_ZERO
        groups = entry.get(KEY_BRIDGE_GROUPS)
        if isinstance(groups, list):
            for group in groups:
                if not isinstance(group, dict):
                    continue
                members = group.get(KEY_BRIDGE_GROUP_MEMBERS, []) or []
                if not isinstance(members, list):
                    continue
                before = len(members)
                members = [
                    member
                    for member in members
                    if not (
                        (isinstance(member, str) and member.strip().lower() == label_lower)
                        or (
                            isinstance(member, dict)
                            and bridge_group_member_label(member).lower() == label_lower
                        )
                    )
                ]
                if len(members) != before:
                    group[KEY_BRIDGE_GROUP_MEMBERS] = members
                    changed += before - len(members)
        selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE)
        if isinstance(selected, dict):
            name = str(selected.get(KEY_DEVICE, TEXT_EMPTY)).strip()
            if name.lower() == label_lower:
                selected[KEY_DEVICE] = TEXT_EMPTY
                selected[KEY_SELECTED_ENABLED] = False
                changed += COUNT_ONE

        tests = entry.get(KEY_BRIDGE_TESTS)
        if isinstance(tests, dict):
            changed += self._prune_tests_label_refs(tests, label, label_lower)
        return changed

    def _prune_tests_label_refs(self, tests: Dict[str, object], label: str, label_lower: str) -> int:
        """
        NAME
            _prune_tests_label_refs - Remove deleted device refs from tests payload.
        """

        changed = COUNT_ZERO
        test_sets = tests.get(KEY_TEST_SETS)
        if not isinstance(test_sets, dict):
            return COUNT_ZERO
        for set_name, entries in list(test_sets.items()):
            _ = set_name
            if not isinstance(entries, list):
                continue
            new_entries: List[object] = []
            for test in entries:
                if not isinstance(test, dict):
                    new_entries.append(test)
                    continue
                motor_labels = test.get(KEY_TEST_MOTOR_LABELS)
                if isinstance(motor_labels, list):
                    kept = [
                        v
                        for v in motor_labels
                        if not (isinstance(v, str) and v.strip().lower() == label_lower)
                    ]
                    if len(kept) != len(motor_labels):
                        changed += len(motor_labels) - len(kept)
                        test[KEY_TEST_MOTOR_LABELS] = kept
                    if not kept:
                        # Drop the test entirely if it no longer targets any devices.
                        changed += COUNT_ONE
                        continue
                rotation = test.get(KEY_TEST_ROTATION)
                if isinstance(rotation, dict):
                    encoder_key = rotation.get(KEY_TEST_ENCODER_KEY)
                    if isinstance(encoder_key, str) and encoder_key.strip().lower() == label_lower:
                        rotation[KEY_TEST_ENCODER_KEY] = ENCODER_KEY_INTERNAL
                        changed += COUNT_ONE
                sweep = test.get(KEY_TEST_DEADBAND_SWEEP)
                if isinstance(sweep, dict):
                    encoder_key = sweep.get(KEY_TEST_ENCODER_KEY)
                    if isinstance(encoder_key, str) and encoder_key.strip().lower() == label_lower:
                        sweep[KEY_TEST_ENCODER_KEY] = ENCODER_KEY_INTERNAL
                        changed += COUNT_ONE
                limit_switch = test.get(KEY_TEST_LIMIT_SWITCH)
                if isinstance(limit_switch, dict):
                    ref = limit_switch.get(KEY_TEST_LIMIT_SWITCH_ID)
                    if isinstance(ref, str) and ref.strip().lower() == label_lower:
                        limit_switch.pop(KEY_TEST_LIMIT_SWITCH_ID, None)
                        limit_switch[KEY_SELECTED_ENABLED] = False
                        changed += COUNT_ONE
                new_entries.append(test)
            test_sets[set_name] = new_entries
        tests[KEY_TEST_SETS] = test_sets
        return changed

    def _update_callout_target_labels(self, old: str, new: str) -> int:
        """
        NAME
            _update_callout_target_labels - Update callout target labels on rename.
        """
        changed = COUNT_ZERO
        for node in self._nodes:
            if node.node_type != NODE_TYPE_CALLOUT:
                continue
            label = str(node.callout_target_label or TEXT_EMPTY).strip()
            if label.lower() == old.lower():
                node.callout_target_label = new
                changed += COUNT_ONE
        return changed

    def _node_center_y_unscaled(self, node: Node) -> float:
        """
        NAME
            _node_center_y_unscaled - Compute unscaled center Y for a node.
        """
        if getattr(node, "free_y_relative", True) is False and node.free_y is not None:
            return float(node.free_y)
        return node_center_y_unscaled(node, self._bus_offsets, self._box_h)

    def _nearest_bus_and_row_from_offset(self, y_offset: float) -> Tuple[int, int]:
        """
        NAME
            _nearest_bus_and_row_from_offset - Pick nearest bus/row from an offset.
        """
        if not self._bus_offsets:
            return 0, 0
        nearest = 0
        best = float("inf")
        for idx, bus_offset in enumerate(self._bus_offsets):
            dist = abs(y_offset - bus_offset)
            if dist < best:
                best = dist
                nearest = idx
        row = 0 if y_offset < self._bus_offsets[nearest] else 1
        return nearest, row

    def _resolve_overlaps(self) -> None:
        """
        NAME
            _resolve_overlaps - Nudge overlapping nodes so they render distinctly.
        """
        if not self._nodes:
            return
        if len(self._bus_lefts) < len(self._bus_offsets):
            self._bus_lefts.extend([40.0] * (len(self._bus_offsets) - len(self._bus_lefts)))
        if len(self._bus_rights) < len(self._bus_offsets):
            max_node_x = max((n.x for n in self._nodes), default=0.0)
            self._bus_rights.extend(
                [max_node_x + 200.0] * (len(self._bus_offsets) - len(self._bus_rights))
            )
        min_gap = 10.0
        groups: Dict[Tuple[int, int], List[Node]] = {}
        for node in self._nodes:
            groups.setdefault((node.bus_index, node.row), []).append(node)
        for (bus_index, _row), nodes in groups.items():
            nodes.sort(key=lambda n: (n.x, n.key))
            placed: List[Tuple[float, float, float, float]] = []
            for node in nodes:
                node_scale = max(0.6, min(2.0, node.scale))
                base_w = 180.0 if node.node_type == "callout" else float(self._box_w)
                cur_w = base_w * node_scale
                cur_h = (50.0 if node.node_type == "callout" else float(self._box_h)) * node_scale
                center_y = self._node_center_y_unscaled(node)
                y0 = center_y - cur_h / 2.0
                y1 = center_y + cur_h / 2.0
                for other_x, other_half_w, other_y0, other_y1 in placed:
                    vertical_overlap = y0 < other_y1 + min_gap and y1 > other_y0 - min_gap
                    if not vertical_overlap:
                        continue
                    min_spacing = other_half_w + cur_w / 2.0 + min_gap
                    if node.x - other_x < min_spacing:
                        node.x = other_x + min_spacing
                placed.append((node.x, cur_w / 2.0, y0, y1))
            if 0 <= bus_index < len(self._bus_rights):
                max_x = max(n.x for n in nodes)
                self._bus_rights[bus_index] = max(self._bus_rights[bus_index], max_x + 120.0)

    def _set_single_node_selection(self, key: int) -> None:
        """
        NAME
            _set_single_node_selection - Select one node and clear other selections.
        """
        if self._selected_nodes == {key} and not self._selected_buses:
            return
        self._selected_inventory_label = None
        self._selected_nodes = {key}
        self._selected_buses = set()
        self._sync_selection_state()

    def _clear_selection(self) -> None:
        """
        NAME
            _clear_selection - Clear all current selections.
        """
        if not self._selected_nodes and not self._selected_buses and not self._selected_inventory_label:
            return
        self._selected_inventory_label = None
        self._selected_nodes = set()
        self._selected_buses = set()
        self._sync_selection_state()

    def _normalize_tag(self, value: str) -> str:
        """
        NAME
            _normalize_tag - Normalize a tag string for comparisons.
        """
        return normalize_tag(value)

    def _normalize_tags(self, value: object) -> List[str]:
        """
        NAME
            _normalize_tags - Normalize tags into a cleaned list.
        """
        return normalize_tags(value)

    def _tags_to_string(self, tags: List[str]) -> str:
        """
        NAME
            _tags_to_string - Format tag list for display.
        """
        return tags_to_string(tags)

    def _collect_tags(self) -> List[str]:
        """
        NAME
            _collect_tags - Gather all known tags for prompts.
        """
        return collect_tags(self._nodes)

    def _set_tag_filter(self, tag: Optional[str]) -> None:
        """
        NAME
            _set_tag_filter - Apply a tag filter to the node list.
        """
        expr = (tag or "").strip()
        if not expr:
            self._tag_filter = None
            self._tag_filter_fn = None
            self._tag_filter_var.set("Filter: All")
            if self._tag_filter_button is not None:
                self._tag_filter_button.configure(state="disabled")
            self._refresh_list()
            return
        try:
            fn = self._compile_tag_filter(expr)
        except ValueError as exc:
            messagebox.showerror("Invalid Filter", str(exc))
            return
        self._tag_filter = expr
        self._tag_filter_fn = fn
        label = f"Filter: {self._tag_filter}" if self._tag_filter else "Filter: All"
        self._tag_filter_var.set(label)
        if self._tag_filter_button is not None:
            state = "normal" if self._tag_filter else "disabled"
            self._tag_filter_button.configure(state=state)
        self._refresh_list()

    def _clear_tag_filter(self) -> None:
        """
        NAME
            _clear_tag_filter - Clear the active tag filter.
        """
        self._set_tag_filter(None)

    def _match_tag(self, node: Node, tag: str) -> bool:
        """
        NAME
            _match_tag - Return True if a node has the given tag.
        """
        return match_tag(node, tag)

    def _prompt_for_tag(self, title: str) -> Optional[str]:
        """
        NAME
            _prompt_for_tag - Prompt for a tag value.
        """
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Tag").pack(anchor="w", padx=10, pady=(10, 2))
        var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=var, width=30)
        entry.pack(padx=10, pady=4, fill="x")
        entry.focus_set()
        values = self._collect_tags()
        if values:
            ttk.Label(dialog, text="Existing Tags").pack(anchor="w", padx=10, pady=(6, 2))
            listbox = tk.Listbox(dialog, height=min(6, len(values)), exportselection=False)
            for item in values:
                listbox.insert("end", item)
            listbox.pack(padx=10, pady=(0, 6), fill="x")

            def _use_selected(_event: tk.Event) -> None:
                selection = listbox.curselection()
                if not selection:
                    return
                var.set(values[selection[0]])

            listbox.bind("<<ListboxSelect>>", _use_selected)

        result: List[Optional[str]] = [None]

        def _ok() -> None:
            result[0] = var.get()
            dialog.destroy()

        def _cancel() -> None:
            dialog.destroy()

        button_row = ttk.Frame(dialog)
        button_row.pack(padx=10, pady=(6, 10), anchor="e")
        ttk.Button(button_row, text="Cancel", command=_cancel).pack(side="left", padx=4)
        ttk.Button(button_row, text="OK", command=_ok).pack(side="left", padx=4)
        self.wait_window(dialog)
        return result[0]

    def _prompt_for_tag_filter(self, title: str) -> Optional[str]:
        """
        NAME
            _prompt_for_tag_filter - Prompt for a tag filter expression.
        """
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Filter Expression").pack(anchor="w", padx=10, pady=(10, 2))
        var = tk.StringVar(value=self._tag_filter or "")
        entry = ttk.Entry(dialog, textvariable=var, width=36)
        entry.pack(padx=10, pady=4, fill="x")
        entry.focus_set()

        ttk.Label(dialog, text="Use AND/OR, &&/||, or commas in filters.").pack(
            anchor="w", padx=10, pady=(0, 4)
        )

        values = self._collect_tags()
        if values:
            op_frame = ttk.Frame(dialog)
            op_frame.pack(anchor="w", padx=10, pady=(0, 4))
            ttk.Label(op_frame, text="Append with").pack(side="left")
            append_op = tk.StringVar(value="||")
            ttk.Radiobutton(op_frame, text="OR", variable=append_op, value="||").pack(
                side="left", padx=(6, 0)
            )
            ttk.Radiobutton(op_frame, text="AND", variable=append_op, value="&&").pack(
                side="left", padx=(6, 0)
            )
            ttk.Label(dialog, text="Existing Tags").pack(anchor="w", padx=10, pady=(6, 2))
            list_frame = ttk.Frame(dialog)
            list_frame.pack(padx=10, pady=(0, 6), fill="x")
            listbox = tk.Listbox(
                list_frame, height=min(8, len(values)), exportselection=False
            )
            for item in values:
                listbox.insert("end", item)
            listbox.pack(side="left", fill="x", expand=True)
            list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
            list_scroll.pack(side="right", fill="y")
            listbox.configure(yscrollcommand=list_scroll.set)

            def _use_selected(_event: tk.Event) -> None:
                selection = listbox.curselection()
                if not selection:
                    return
                tag = values[selection[0]]
                current = var.get().strip()
                if not current:
                    var.set(tag)
                else:
                    if " " in tag:
                        tag = f"({tag})"
                    var.set(f"{current} {append_op.get()} {tag}")

            listbox.bind("<<ListboxSelect>>", _use_selected)
            listbox.bind("<Double-Button-1>", _use_selected)

        result: List[Optional[str]] = [None]

        def _ok() -> None:
            result[0] = var.get()
            dialog.destroy()

        def _cancel() -> None:
            dialog.destroy()

        button_row = ttk.Frame(dialog)
        button_row.pack(padx=10, pady=(6, 10), anchor="e")
        ttk.Button(button_row, text="Cancel", command=_cancel).pack(side="left", padx=4)
        ttk.Button(button_row, text="OK", command=_ok).pack(side="left", padx=4)
        self.wait_window(dialog)
        return result[0]

    def _compile_tag_filter(self, expr: str):
        """
        NAME
            _compile_tag_filter - Compile a tag filter expression.
        """
        return compile_tag_filter(expr)

    def _select_by_tag(self) -> None:
        """
        NAME
            _select_by_tag - Select nodes and callouts matching a tag.
        """
        tag = self._prompt_for_tag("Select by Tag")
        if not tag:
            return
        normalized = self._normalize_tag(tag)
        matched = {n.key for n in self._nodes if self._match_tag(n, normalized)}
        if not matched:
            messagebox.showinfo("Select by Tag", f"No nodes matched tag '{normalized}'.")
            return
        self._selected_nodes = matched
        self._selected_buses = set()
        self._sync_selection_state()

    def _filter_list_by_tag(self) -> None:
        """
        NAME
            _filter_list_by_tag - Filter the node list by tag.
        """
        expr = self._prompt_for_tag_filter("Filter List by Tag")
        if expr is None:
            return
        expr = expr.strip()
        if not expr:
            return
        self._set_tag_filter(expr)

    def _select_filtered_nodes(self) -> None:
        """
        NAME
            _select_filtered_nodes - Select nodes matching the current filter.
        """
        if self._tag_filter_fn is None:
            messagebox.showinfo("Select Filtered", "No tag filter is active.")
            return
        matched = {n.key for n in self._device_nodes() if self._tag_filter_fn(n)}
        if not matched:
            messagebox.showinfo("Select Filtered", "No nodes match the current filter.")
            return
        self._selected_nodes = matched
        self._selected_buses = set()
        self._sync_selection_state()

    def _tidy_by_tag(self) -> None:
        """
        NAME
            _tidy_by_tag - Tidy nodes matching a specific tag.
        """
        tag = self._prompt_for_tag("Tidy by Tag")
        if not tag:
            return
        normalized = self._normalize_tag(tag)
        matches = [n for n in self._device_nodes() if self._match_tag(n, normalized)]
        if not matches:
            messagebox.showinfo("Tidy by Tag", f"No device nodes matched tag '{normalized}'.")
            return
        prior_nodes = set(self._selected_nodes)
        prior_buses = set(self._selected_buses)
        try:
            self._selected_nodes = {n.key for n in matches}
            self._selected_buses = set()
            self._tidy_selection()
        finally:
            self._selected_nodes = prior_nodes
            self._selected_buses = prior_buses
            self._sync_selection_state()

    def _apply_tag_to_selection(self) -> None:
        """
        NAME
            _apply_tag_to_selection - Add a tag to all selected nodes/callouts.
        """
        if not self._selected_nodes:
            messagebox.showinfo("Apply Tag", "Select one or more nodes or callouts.")
            return
        tag = self._prompt_for_tag("Apply Tag to Selection")
        if not tag:
            return
        normalized = self._normalize_tag(tag)
        if not normalized:
            return
        self._push_undo()
        for node in self._nodes:
            if node.key not in self._selected_nodes:
                continue
            tags = self._normalize_tags(node.tags)
            if normalized not in tags:
                tags.append(normalized)
            node.tags = tags
        self._refresh_list()
        self._redraw_canvas()

    def _remove_tag_from_selection(self) -> None:
        """
        NAME
            _remove_tag_from_selection - Remove a tag from selected nodes/callouts.
        """
        if not self._selected_nodes:
            messagebox.showinfo("Remove Tag", "Select one or more nodes or callouts.")
            return
        tag = self._prompt_for_tag("Remove Tag from Selection")
        if not tag:
            return
        normalized = self._normalize_tag(tag)
        if not normalized:
            return
        self._push_undo()
        for node in self._nodes:
            if node.key not in self._selected_nodes:
                continue
            tags = [t for t in self._normalize_tags(node.tags) if t != normalized]
            node.tags = tags
        self._refresh_list()
        self._redraw_canvas()

    def _ensure_bridge_config(self) -> Dict[str, object]:
        """
        NAME
            _ensure_bridge_config - Ensure bridgeConfig exists in the root payload.
        """
        existing = self._root_extras.get("bridgeConfig")
        if isinstance(existing, dict):
            config = existing
        else:
            config = {
                KEY_BRIDGE_SCHEMA_VERSION: (
                    profile_consts.BRIDGE_CONFIG_SCHEMA_VERSION
                    if profile_consts is not None
                    else BRIDGE_CONFIG_SCHEMA_VERSION_FALLBACK
                ),
                KEY_BRIDGE_GENERATED_AT: None,
                KEY_BRIDGE_BY_PROFILE: {},
            }
            self._root_extras["bridgeConfig"] = config
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            by_profile = {}
            config[KEY_BRIDGE_BY_PROFILE] = by_profile
        profile_name = self._profile_name or ""
        if profile_name:
            entry = by_profile.get(profile_name)
            if not isinstance(entry, dict):
                entry = {
                    KEY_BRIDGE_GROUPS: [],
                    KEY_BRIDGE_SELECTED_DEVICE: {
                        KEY_DEVICE: "",
                        KEY_SELECTED_ENABLED: False,
                    },
                }
                by_profile[profile_name] = entry
            if not isinstance(entry.get(KEY_BRIDGE_GROUPS), list):
                entry[KEY_BRIDGE_GROUPS] = []
        return config

    def _bridge_groups(self) -> List[Dict[str, object]]:
        """
        NAME
            _bridge_groups - Return the per-profile bridgeConfig groups list (may be empty).
        """
        config = self._root_extras.get("bridgeConfig")
        if not isinstance(config, dict):
            return []
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return []
        profile_name = self._profile_name or ""
        entry = by_profile.get(profile_name)
        if not isinstance(entry, dict):
            return []
        groups = entry.get(KEY_BRIDGE_GROUPS)
        return groups if isinstance(groups, list) else []

    def _create_group_from_selection(self) -> None:
        """
        NAME
            _create_group_from_selection - Create/update a group from selected nodes.
        """
        selected = [n for n in self._nodes if n.key in self._selected_nodes]
        if not selected:
            messagebox.showinfo("Create Group", "Select one or more nodes.")
            return
        name = simpledialog.askstring("Create Group", "Group name:")
        if not name:
            return
        name = name.strip()
        if not name:
            return
        self._ensure_bridge_config()
        groups = self._bridge_groups()
        existing = None
        for group in groups:
            if isinstance(group, dict) and str(group.get("name", "")).strip().lower() == name.lower():
                existing = group
                break
        if existing is not None:
            replace = messagebox.askyesno(
                "Group Exists",
                f"Group '{name}' exists. Replace its members with the current selection?",
            )
            if not replace:
                return
            target = existing
        else:
            target = {"name": name, "enabled": True, "members": [], "bindings": []}
            groups.append(target)
        members = [make_bridge_group_member(n.label, True) for n in selected]
        target["members"] = members
        if "bindings" not in target:
            target["bindings"] = []
        if "enabled" not in target:
            target["enabled"] = True
        self._dirty = True
        self._refresh_list()
        self._redraw_canvas()

    def _remove_bridge_group(self) -> None:
        """
        NAME
            _remove_bridge_group - Remove a group from bridgeConfig.
        """
        groups = [g for g in self._bridge_groups() if isinstance(g, dict) and g.get("name")]
        if not groups:
            messagebox.showinfo("Remove Group", "No groups found in bridgeConfig.")
            return
        names = [str(g.get("name")) for g in groups]
        prompt = "Group name to remove:\n" + ", ".join(names)
        name = simpledialog.askstring("Remove Group", prompt)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        config = self._ensure_bridge_config()
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            messagebox.showinfo("Remove Group", "No bridgeConfig profiles found.")
            return
        profile_name = self._profile_name or ""
        entry = by_profile.get(profile_name)
        if not isinstance(entry, dict):
            messagebox.showinfo("Remove Group", f"Profile '{profile_name}' not found.")
            return
        new_groups = []
        removed = False
        for group in entry.get(KEY_BRIDGE_GROUPS, []) or []:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name", "")).strip()
            if group_name.lower() == name.lower():
                removed = True
                continue
            new_groups.append(group)
        if not removed:
            messagebox.showinfo("Remove Group", f"Group '{name}' not found.")
            return
        entry[KEY_BRIDGE_GROUPS] = new_groups
        self._dirty = True
        self._refresh_list()
        self._redraw_canvas()

    def _auto_layout_readable(self) -> None:
        """
        NAME
            _auto_layout_readable - Auto-arrange nodes into readable rows.

        DESCRIPTION
            Groups nodes per bus, assigns rows by category, and spaces nodes
            into shared columns to reduce overlap and link crossings. Updates
            bus bounds to fit the new layout.
        """
        device_nodes = [n for n in self._nodes if n.node_type != "callout"]
        if not device_nodes:
            messagebox.showinfo("Auto Layout", "No device nodes to layout.")
            return

        self._push_undo()
        self._drag_undo_pending = False

        nodes_by_key: Dict[int, Node] = {n.key: n for n in self._nodes if isinstance(n.key, int)}
        # Resolve CANnect device buses from the specific CAN port -> bus mapping.
        cannect_bus_by_port: Dict[int, Dict[int, int]] = {}
        device_forced_bus: Dict[int, int] = {}
        if ENABLE_CANNECT_BUS_LINKS:
            for link in self._can_bus_links:
                node_key = link.get("node")
                bus_index = link.get("bus")
                port = link.get("port", 1)
                if isinstance(node_key, int) and isinstance(bus_index, int):
                    cannect_bus_by_port.setdefault(node_key, {})[int(port)] = bus_index
            # Anchor CANnect nodes to their port-1 bus (or the only bus link).
            for cannect_key, port_map in cannect_bus_by_port.items():
                cannect = nodes_by_key.get(cannect_key)
                if cannect is None:
                    continue
                if 1 in port_map:
                    cannect.bus_index = port_map[1]
                elif len(port_map) == 1:
                    cannect.bus_index = next(iter(port_map.values()))
            # Devices linked to CANnect must live on the bus segment for that port.
            # If the port-to-bus mapping is missing, fall back to the CANnect node bus
            # to avoid cross-bus link drawings.
            for link in self._cannect_device_links:
                cannect_key = link.get("node")
                device_key = link.get("device")
                port = int(link.get("port", 1))
                if not isinstance(cannect_key, int) or not isinstance(device_key, int):
                    continue
                device = nodes_by_key.get(device_key)
                if device is None:
                    continue
                port_map = cannect_bus_by_port.get(cannect_key, {})
                target_bus = port_map.get(port)
                if target_bus is None and len(port_map) == 1:
                    target_bus = next(iter(port_map.values()))
                if target_bus is None:
                    cannect = nodes_by_key.get(cannect_key)
                    if cannect is not None:
                        target_bus = cannect.bus_index
                if target_bus is not None:
                    device.bus_index = target_bus
                    device_forced_bus[device_key] = target_bus

        motor_cats = {"neos", "neo550s", "flexes", "krakens", "falcons"}
        sensor_cats = {"cancoders", "pigeon"}
        power_cats = {"pdh", "pdp"}
        controller_cats = {
            "roborio",
            DIAGRAM_CATEGORY_CANNECT_INJECT,
            DIAGRAM_CATEGORY_CANNECT_DIRECT,
            DIAGRAM_CATEGORY_ANALYZER,
        }

        def _category_group(node: Node) -> Tuple[int, str]:
            cat = (node.category or "").lower()
            if cat in controller_cats:
                return (0, cat)
            if cat in power_cats:
                return (1, cat)
            if cat in motor_cats:
                return (2, cat)
            if cat in sensor_cats:
                return (3, cat)
            return (4, cat)

        by_bus: Dict[int, List[Node]] = {}
        for node in device_nodes:
            if ENABLE_CANNECT_FREE_FLOAT and self._is_cannect_cluster_member(node):
                continue
            bus_index = max(0, int(node.bus_index))
            by_bus.setdefault(bus_index, []).append(node)

        # Group CANnect device links by bus segment.
        cannect_devices_by_bus: Dict[int, Dict[int, List[Node]]] = {}
        for link in self._cannect_device_links:
            cannect_key = link.get("node")
            device_key = link.get("device")
            port = int(link.get("port", 1))
            if not isinstance(cannect_key, int) or not isinstance(device_key, int):
                continue
            device = nodes_by_key.get(device_key)
            if device is None:
                continue
            target_bus = device_forced_bus.get(device_key)
            if target_bus is None:
                continue
            cannect_devices_by_bus.setdefault(target_bus, {}).setdefault(cannect_key, []).append(device)

        for bus_index, nodes in sorted(by_bus.items()):
            while len(self._bus_lefts) <= bus_index:
                self._bus_lefts.append(40.0)
            while len(self._bus_rights) <= bus_index:
                self._bus_rights.append(400.0)

            left_bound = self._bus_lefts[bus_index]
            right_bound = self._bus_rights[bus_index]
            usable_left = left_bound + 80.0
            usable_right = right_bound - 80.0
            if usable_right <= usable_left:
                usable_left = left_bound + 40.0
                usable_right = right_bound - 40.0

            # Assign rows.
            for node in nodes:
                cat = (node.category or "").lower()
                if cat in sensor_cats or cat in controller_cats:
                    node.row = 1
                else:
                    node.row = 0
                if ENABLE_CANNECT_FREE_FLOAT and self._is_cannect_cluster_member(node):
                    self._ensure_cannect_free_float(node)
                else:
                    node.free_y = None
                    node.free_y_relative = False
            used = set()
            cannect_nodes: List[Node] = []
            linked_group: Dict[int, List[Node]] = {}
            cluster_end = usable_left
            if ENABLE_CANNECT_BUS_LINKS:
                # Place CANnect nodes at the left edge of this bus.
                cannect_nodes = [
                    n for n in nodes if (n.category or "").lower() in {"cannect_inject", "cannect_direct"}
                ]
                cannect_nodes = sorted(cannect_nodes, key=lambda n: (n.label or "", n.can_id or 0))
                cannect_x = usable_left
                for idx, cannect in enumerate(cannect_nodes):
                    cannect.x = cannect_x
                    cannect.row = 1
                    if idx > 0:
                        cannect.x = cannect_x + idx * 20.0

                # Place CANnect-linked devices next to their CANnect in CAN ID order.
                linked_group = cannect_devices_by_bus.get(bus_index, {})
                cluster_end = cannect_x
                for cannect_key, devices in sorted(
                    linked_group.items(),
                    key=lambda item: (
                        nodes_by_key[item[0]].x if item[0] in nodes_by_key else cannect_x
                    ),
                ):
                    cannect_node = nodes_by_key.get(cannect_key)
                    cannect_row = cannect_node.row if cannect_node is not None else 1
                    devices_sorted = sorted(
                        devices,
                        key=lambda n: (
                            n.can_id if n.can_id is not None else 1_000_000,
                            n.label or "",
                        ),
                    )
                    start_x = (nodes_by_key[cannect_key].x if cannect_key in nodes_by_key else cannect_x) + 160.0
                    min_spacing = max(160.0, float(self._box_w) * 1.25)
                    needed_width = start_x + min_spacing * max(0, len(devices_sorted) - 1)
                    if needed_width > usable_right:
                        self._bus_rights[bus_index] = max(self._bus_rights[bus_index], needed_width + 120.0)
                        usable_right = self._bus_rights[bus_index] - 80.0
                    for idx, device in enumerate(devices_sorted):
                        device.x = start_x + idx * min_spacing
                        device.row = cannect_row
                        used.add(device.key)
                    if devices_sorted:
                        cluster_end = max(cluster_end, devices_sorted[-1].x)

            # Place remaining nodes across the rest of the span without condensing.
            remaining = [n for n in nodes if n.key not in used and n not in cannect_nodes]
            if remaining:
                remaining_sorted = sorted(
                    remaining,
                    key=lambda n: (_category_group(n), n.can_id or 0, n.label),
                )
                start_x = max(cluster_end + 140.0, usable_left)
                span = max(1.0, usable_right - start_x)
                min_spacing = max(140.0, float(self._box_w) * 1.2)
                spacing = max(min_spacing, span / max(len(remaining_sorted) - 1, 1))
                for idx, node in enumerate(remaining_sorted):
                    node.x = start_x + idx * spacing

            all_nodes = [n for n in nodes if isinstance(n.x, (int, float))]
            if all_nodes:
                min_x = min(n.x for n in all_nodes)
                max_x = max(n.x for n in all_nodes)
                existing_left = self._bus_lefts[bus_index]
                existing_right = self._bus_rights[bus_index]
                new_left = min_x - 80.0
                new_right = max_x + 120.0
                # Never shorten bus segments; only expand if needed.
                self._bus_lefts[bus_index] = min(existing_left, new_left)
                self._bus_rights[bus_index] = max(existing_right, new_right)

        self._redraw_canvas()
    def _bulk_edit_selection(self) -> None:
        """
        NAME
            _bulk_edit_selection - Apply edits across selected nodes/callouts.
        """
        if not self._selected_nodes:
            messagebox.showinfo("Bulk Edit", "Select one or more nodes or callouts.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Bulk Edit")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        container = ttk.Frame(dialog, padding=10)
        container.grid(row=0, column=0, sticky="nsew")

        def _row(label: str, row: int) -> ttk.Label:
            lbl = ttk.Label(container, text=label)
            lbl.grid(row=row, column=0, sticky="w", padx=(0, 6), pady=2)
            return lbl

        apply_label = ttk.Label(container, text="Apply")
        apply_label.grid(row=0, column=1, sticky="w")
        value_label = ttk.Label(container, text="Value")
        value_label.grid(row=0, column=2, sticky="w")

        row = 1

        var_apply_category = tk.BooleanVar(value=False)
        _row("Category", row)
        ttk.Checkbutton(container, variable=var_apply_category).grid(row=row, column=1, sticky="w")
        combo_category = ttk.Combobox(
            container,
            values=BUCKET_CATEGORIES + [GENERIC_CATEGORY] + SINGLETON_CATEGORIES,
            state="readonly",
            width=20,
        )
        combo_category.grid(row=row, column=2, sticky="w")
        row += 1

        var_apply_label = tk.BooleanVar(value=False)
        _row("Label", row)
        ttk.Checkbutton(container, variable=var_apply_label).grid(row=row, column=1, sticky="w")
        label_frame = ttk.Frame(container)
        label_frame.grid(row=row, column=2, sticky="w")
        combo_label_mode = ttk.Combobox(
            label_frame, values=["replace", "prefix", "suffix"], state="readonly", width=8
        )
        combo_label_mode.set("replace")
        combo_label_mode.pack(side="left")
        label_value = tk.StringVar()
        ttk.Entry(label_frame, textvariable=label_value, width=18).pack(side="left", padx=(6, 0))
        row += 1

        var_apply_vendor = tk.BooleanVar(value=False)
        _row("Vendor", row)
        ttk.Checkbutton(container, variable=var_apply_vendor).grid(row=row, column=1, sticky="w")
        vendor_value = tk.StringVar()
        vendor_combo = ttk.Combobox(
            container,
            values=SUPPORTED_MANUFACTURERS,
            textvariable=vendor_value,
            state="normal",
            width=24,
        )
        vendor_combo.grid(row=row, column=2, sticky="w")
        row += 1

        var_apply_type = tk.BooleanVar(value=False)
        _row("CAN Device Type", row)
        ttk.Checkbutton(container, variable=var_apply_type).grid(row=row, column=1, sticky="w")
        type_value = tk.StringVar()
        type_combo = ttk.Combobox(
            container,
            values=SUPPORTED_DEVICE_TYPES,
            textvariable=type_value,
            state="normal",
            width=24,
        )
        type_combo.grid(row=row, column=2, sticky="w")
        row += 1

        var_apply_motor = tk.BooleanVar(value=False)
        _row("Model", row)
        ttk.Checkbutton(container, variable=var_apply_motor).grid(row=row, column=1, sticky="w")
        motor_value = tk.StringVar()
        ttk.Entry(container, textvariable=motor_value, width=24).grid(row=row, column=2, sticky="w")
        row += 1

        var_apply_limits = tk.BooleanVar(value=False)
        _row("Limits", row)
        ttk.Checkbutton(container, variable=var_apply_limits).grid(row=row, column=1, sticky="w")
        limits_frame = ttk.Frame(container)
        limits_frame.grid(row=row, column=2, sticky="w")
        fwd_value = tk.StringVar()
        rev_value = tk.StringVar()
        invert_value = tk.BooleanVar(value=False)
        ttk.Label(limits_frame, text="Fwd").pack(side="left")
        ttk.Entry(limits_frame, textvariable=fwd_value, width=5).pack(side="left", padx=(2, 6))
        ttk.Label(limits_frame, text="Rev").pack(side="left")
        ttk.Entry(limits_frame, textvariable=rev_value, width=5).pack(side="left", padx=(2, 6))
        ttk.Checkbutton(limits_frame, text="Invert", variable=invert_value).pack(side="left")
        row += 1

        var_apply_term = tk.BooleanVar(value=False)
        _row("Terminator", row)
        ttk.Checkbutton(container, variable=var_apply_term).grid(row=row, column=1, sticky="w")
        term_combo = ttk.Combobox(
            container, values=["on", "off", "clear"], state="readonly", width=8
        )
        term_combo.set("off")
        term_combo.grid(row=row, column=2, sticky="w")
        row += 1

        var_apply_tags = tk.BooleanVar(value=False)
        _row("Tags", row)
        ttk.Checkbutton(container, variable=var_apply_tags).grid(row=row, column=1, sticky="w")
        tags_frame = ttk.Frame(container)
        tags_frame.grid(row=row, column=2, sticky="w")
        combo_tags_mode = ttk.Combobox(
            tags_frame, values=["replace", "add", "remove"], state="readonly", width=8
        )
        combo_tags_mode.set("replace")
        combo_tags_mode.pack(side="left")
        tags_value = tk.StringVar()
        ttk.Entry(tags_frame, textvariable=tags_value, width=18).pack(side="left", padx=(6, 0))
        row += 1

        result: Dict[str, object] = {}

        def _ok() -> None:
            result["apply_category"] = var_apply_category.get()
            result["category"] = combo_category.get().strip()
            result["apply_label"] = var_apply_label.get()
            result["label_mode"] = combo_label_mode.get().strip()
            result["label_value"] = label_value.get().strip()
            result["apply_vendor"] = var_apply_vendor.get()
            result["vendor"] = vendor_value.get().strip()
            result["apply_type"] = var_apply_type.get()
            result["device_type"] = type_value.get().strip()
            result["apply_motor"] = var_apply_motor.get()
            result["motor"] = motor_value.get().strip()
            result["apply_limits"] = var_apply_limits.get()
            result["limits_fwd"] = fwd_value.get().strip()
            result["limits_rev"] = rev_value.get().strip()
            result["limits_invert"] = invert_value.get()
            result["apply_term"] = var_apply_term.get()
            result["terminator"] = term_combo.get().strip()
            result["apply_tags"] = var_apply_tags.get()
            result["tags_mode"] = combo_tags_mode.get().strip()
            result["tags_value"] = tags_value.get().strip()
            dialog.destroy()

        def _cancel() -> None:
            dialog.destroy()

        button_row = ttk.Frame(container)
        button_row.grid(row=row, column=0, columnspan=3, sticky="e", pady=(8, 0))
        ttk.Button(button_row, text="Cancel", command=_cancel).pack(side="right", padx=4)
        ttk.Button(button_row, text="OK", command=_ok).pack(side="right")

        self.wait_window(dialog)
        if not result:
            return

        selected = [n for n in self._nodes if n.key in self._selected_nodes]
        if not selected:
            return

        apply_category = bool(result.get("apply_category"))
        new_category = str(result.get("category", "")).strip()

        if apply_category and new_category in SINGLETON_CATEGORIES:
            existing = [n for n in self._device_nodes() if n.category == new_category]
            target_nodes = [n for n in selected if n.node_type == "device"]
            if len(target_nodes) > 1:
                messagebox.showerror("Bulk Edit", f"Only one {new_category} is allowed.")
                return
            if existing and existing[0] not in target_nodes:
                messagebox.showerror("Bulk Edit", f"{new_category} already exists.")
                return

        self._push_undo()
        for node in selected:
            if node.node_type == "callout":
                if result.get("apply_label"):
                    mode = result.get("label_mode", "replace")
                    val = result.get("label_value", "")
                    if mode == "prefix":
                        node.label = f"{val}{node.label}"
                        node.callout_text = node.label
                    elif mode == "suffix":
                        node.label = f"{node.label}{val}"
                        node.callout_text = node.label
                    else:
                        node.label = val or node.label
                        node.callout_text = node.label
                if result.get("apply_tags"):
                    mode = result.get("tags_mode", "replace")
                    tags = self._normalize_tags(result.get("tags_value", ""))
                    if mode == "add":
                        current = self._normalize_tags(node.tags)
                        node.tags = sorted({*current, *tags})
                    elif mode == "remove":
                        current = self._normalize_tags(node.tags)
                        node.tags = [t for t in current if t not in set(tags)]
                    else:
                        node.tags = tags
                continue

            if apply_category and new_category:
                node.category = new_category
            if result.get("apply_label"):
                mode = result.get("label_mode", "replace")
                val = result.get("label_value", "")
                if mode == "prefix":
                    node.label = f"{val}{node.label}"
                elif mode == "suffix":
                    node.label = f"{node.label}{val}"
                else:
                    if val:
                        node.label = val
            if result.get("apply_vendor"):
                node.vendor = str(result.get("vendor", "")).strip()
            if result.get("apply_type"):
                node.device_type = str(result.get("device_type", "")).strip()
            if result.get("apply_motor"):
                node.motor = str(result.get("motor", "")).strip()
            if result.get("apply_limits"):
                limits = {
                    "fwdDio": result.get("limits_fwd", ""),
                    "revDio": result.get("limits_rev", ""),
                    "invert": bool(result.get("limits_invert")),
                }
                if not limits["fwdDio"] and not limits["revDio"] and not limits["invert"]:
                    node.limits = None
                else:
                    try:
                        node.limits = self._normalize_limits(limits)
                    except ValueError as exc:
                        messagebox.showerror("Bulk Edit", f"Invalid limits: {exc}")
                        return
            if result.get("apply_term"):
                term = result.get("terminator", "off")
                if term == "clear":
                    node.terminator = None
                elif term == "on":
                    node.terminator = True
                else:
                    node.terminator = False
            if result.get("apply_tags"):
                mode = result.get("tags_mode", "replace")
                tags = self._normalize_tags(result.get("tags_value", ""))
                if mode == "add":
                    current = self._normalize_tags(node.tags)
                    node.tags = sorted({*current, *tags})
                elif mode == "remove":
                    current = self._normalize_tags(node.tags)
                    node.tags = [t for t in current if t not in set(tags)]
                else:
                    node.tags = tags

            if node.category == GENERIC_CATEGORY:
                if not node.vendor or not node.device_type:
                    messagebox.showerror(
                        "Bulk Edit",
                        MSG_GENERIC_DEVICE_VENDOR_TYPE_REQUIRED.format(node.label),
                    )
                    return

        self._refresh_list()
        self._redraw_canvas()

    def _select_all_nodes(self) -> None:
        """
        NAME
            _select_all_nodes - Select all nodes (devices + callouts), no buses.
        """
        self._selected_inventory_label = None
        self._selected_nodes = {n.key for n in self._nodes}
        self._selected_buses = set()
        self._sync_selection_state()

    def _duplicate_selection(self) -> None:
        """
        NAME
            _duplicate_selection - Duplicate the current selection.
        """
        self._on_copy()
        self._on_paste()

    def _toggle_snap_to_grid(self) -> None:
        """
        NAME
            _toggle_snap_to_grid - Toggle snap-to-grid behavior.
        """
        current = bool(self._snap_to_grid_var.get())
        self._snap_to_grid_var.set(not current)

    def _toggle_smart_guides(self) -> None:
        """
        NAME
            _toggle_smart_guides - Toggle smart guide display.
        """
        current = bool(self._smart_guides_var.get())
        self._smart_guides_var.set(not current)
        if not self._smart_guides_var.get():
            self._clear_guides()
            self._redraw_canvas()

    def _on_canvas_configure(self, _event: tk.Event) -> None:
        """
        NAME
            _on_canvas_configure - Handle canvas resize events.
        """
        self._gui_debug_log("canvas_configure.before")
        self._redraw_canvas()
        if self._preserve_left_after_configure is not None:
            self._set_canvas_xview_left(self._preserve_left_after_configure)
            self._preserve_left_after_configure = None
        if self._preserve_top_after_configure is not None:
            self._set_canvas_yview_top(self._preserve_top_after_configure)
            self._preserve_top_after_configure = None
        if self._pending_fit_to_window:
            self._pending_fit_to_window = False
            self.after_idle(self._fit_to_window)
        self._gui_debug_log("canvas_configure.after")

    def _save_shortcut(self) -> None:
        """
        NAME
            _save_shortcut - Save using the default flow for the editor.
        """
        self._save_config()

    def _toggle_node_selection(self, key: int) -> None:
        """
        NAME
            _toggle_node_selection - Toggle a node in the multi-selection set.
        """
        self._selected_inventory_label = None
        if key in self._selected_nodes:
            self._selected_nodes.remove(key)
        else:
            self._selected_nodes.add(key)
        self._sync_selection_state()

    def _toggle_bus_selection(self, index: int) -> None:
        """
        NAME
            _toggle_bus_selection - Toggle a bus segment in the multi-selection set.
        """
        self._selected_inventory_label = None
        if index in self._selected_buses:
            self._selected_buses.remove(index)
        else:
            self._selected_buses.add(index)
        self._sync_selection_state()

    def _sync_selection_state(self) -> None:
        """
        NAME
            _sync_selection_state - Update selection-dependent UI and details panels.
        """
        if self._syncing_selection:
            return
        self._syncing_selection = True
        try:
            if self._selected_inventory_label and not self._selected_nodes and not self._selected_buses:
                self._selected_key = None
                row_id = f"{INVENTORY_ROW_PREFIX}{self._selected_inventory_label}"
                self._suppress_list_select = True
                try:
                    current = self.node_list.selection()
                    desired = (row_id,)
                    if current != desired:
                        for item in current:
                            self.node_list.selection_remove(item)
                        if self.node_list.exists(row_id):
                            self.node_list.selection_add(row_id)
                            self.node_list.see(row_id)
                finally:
                    self._suppress_list_select = False
                self._clear_callout_details_fields()
                self._update_details_panel(
                    self._inventory_details_node(self._selected_inventory_label)
                )
                self._update_selection_overlays()
                return
            selected_nodes = list(self._selected_nodes)
            if len(selected_nodes) == 1 and not self._selected_buses:
                self._selected_key = selected_nodes[0]
                self._suppress_list_select = True
                try:
                    current = self.node_list.selection()
                    desired = (str(self._selected_key),)
                    if current != desired:
                        for item in current:
                            self.node_list.selection_remove(item)
                        if self.node_list.exists(str(self._selected_key)):
                            self.node_list.selection_add(str(self._selected_key))
                            self.node_list.see(str(self._selected_key))
                finally:
                    self._suppress_list_select = False
                node = self._get_selected_node()
                if node is not None and node.node_type == "callout":
                    self._update_callout_details(node)
                    self._clear_node_details_fields()
                else:
                    self._clear_callout_details_fields()
                    self._update_details_panel(self._get_selected_node())
            else:
                self._selected_key = None
                self._suppress_list_select = True
                try:
                    current = set(self.node_list.selection())
                    desired = {str(k) for k in self._selected_nodes if self.node_list.exists(str(k))}
                    for item in current - desired:
                        self.node_list.selection_remove(item)
                    for item in desired - current:
                        self.node_list.selection_add(item)
                finally:
                    self._suppress_list_select = False
                self._update_details_panel(None)
            self._update_selection_overlays()
        finally:
            self._syncing_selection = False

    def _clear_selection_overlays(self) -> None:
        """
        NAME
            _clear_selection_overlays - Remove transient selection highlight items.
        """
        for item_id in list(self.__dict__.get("_selection_overlay_ids", []) or []):
            try:
                self.canvas.delete(item_id)
            except Exception:
                pass
        self._selection_overlay_ids = []

    def _update_selection_overlays(self) -> None:
        """
        NAME
            _update_selection_overlays - Draw selection highlights without rebuilding the scene.
        """
        self._clear_selection_overlays()
        overlay_ids: List[int] = []
        selection_color = "#1f6feb"
        for key in sorted(self._selected_nodes):
            bounds = self._node_bounds.get(key)
            if not bounds:
                continue
            x0, y0, x1, y1 = bounds
            overlay_ids.append(
                self.canvas.create_rectangle(
                    x0 - 4.0,
                    y0 - 4.0,
                    x1 + 4.0,
                    y1 + 4.0,
                    outline=selection_color,
                    width=2,
                )
            )
        draw_state = dict(self.__dict__.get("_draw_state", {}) or {})
        bus_ys = list(draw_state.get("bus_ys", []) or [])
        eff_lefts = list(draw_state.get("bus_lefts", []) or [])
        eff_rights = list(draw_state.get("bus_rights", []) or [])
        for idx in sorted(self._selected_buses):
            if idx < 0 or idx >= len(bus_ys):
                continue
            bus_y = float(bus_ys[idx])
            seg_left = (
                float(eff_lefts[idx]) * self._zoom
                if idx < len(eff_lefts)
                else 0.0
            )
            seg_right = (
                float(eff_rights[idx]) * self._zoom
                if idx < len(eff_rights)
                else seg_left
            )
            if idx % 2 == 0:
                start_x, end_x = seg_left, seg_right
            else:
                start_x, end_x = seg_right, seg_left
            overlay_ids.append(
                self.canvas.create_line(
                    start_x,
                    bus_y,
                    end_x,
                    bus_y,
                    width=5,
                    fill=selection_color,
                )
            )
        self._selection_overlay_ids = overlay_ids

    def _find_node_key_at(self, cx: float, cy: float) -> Optional[int]:
        """
        NAME
            _find_node_key_at - Resolve the topmost node key under a canvas point.
        """
        items = self.canvas.find_overlapping(cx, cy, cx, cy)
        if not items:
            return None
        for item in reversed(items):
            try:
                tags = self.canvas.gettags(item)
            except Exception:
                continue
            key = self._tag_to_key(tags)
            if key is not None:
                return key
        return None

    def _shift_held(self, event: tk.Event) -> bool:
        """
        NAME
            _shift_held - Return True when the shift key is pressed.
        """
        return bool(getattr(event, "state", 0) & 0x0001)

    def _apply_marquee_selection(
        self, x0: float, y0: float, x1: float, y1: float, additive: bool
    ) -> None:
        """
        NAME
            _apply_marquee_selection - Select nodes/callouts/buses within a rectangle.
        """
        if not additive:
            self._selected_nodes = set()
            self._selected_buses = set()
        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))
        for key, bounds in self._node_bounds.items():
            bx0, by0, bx1, by1 = bounds
            if not (bx1 < left or bx0 > right or by1 < top or by0 > bottom):
                self._selected_nodes.add(key)
        for idx, bus_y in enumerate(self._bus_ys):
            if top <= bus_y <= bottom:
                self._selected_buses.add(idx)
        self._sync_selection_state()

    def _start_multi_drag(self, cx: float, cy: float) -> None:
        """
        NAME
            _start_multi_drag - Begin dragging all selected nodes/callouts together.
        """
        node_start: Dict[int, Tuple[float, int, int, float, float]] = {}
        for node in self._nodes:
            if node.key in self._selected_nodes:
                start_center = self._node_center_y_unscaled(node)
                node_start[node.key] = (node.x, node.bus_index, node.row, node.scale, start_center)
        self._push_undo()
        self._drag_undo_pending = True
        self._multi_drag = {
            "start": (cx, cy),
            "nodes": node_start,
            "last": (cx, cy),
            "anchor": min(self._selected_nodes) if self._selected_nodes else None,
        }

    def _start_cannect_cluster_drag(self, cannect_key: int, cx: float, cy: float) -> None:
        """
        NAME
            _start_cannect_cluster_drag - Drag a CANnect node and its linked devices.
        """
        node_start: Dict[int, Tuple[float, int, int, float, float]] = {}
        linked = self._cannect_device_keys(cannect_key)
        for node in self._nodes:
            if node.key == cannect_key or node.key in linked:
                self._ensure_cannect_free_float(node)
                start_center = self._node_center_y_unscaled(node)
                node_start[node.key] = (node.x, node.bus_index, node.row, node.scale, start_center)
        self._multi_drag = {
            "start": (cx, cy),
            "nodes": node_start,
            "last": (cx, cy),
            "anchor": cannect_key,
        }
    def _redraw_canvas(self) -> None:
        """
        NAME
            _redraw_canvas - Repaint the bus line and node boxes.
        """
        self._debug_redraw_count = int(self.__dict__.get("_debug_redraw_count", 0)) + 1
        self._gui_debug_log("redraw.begin")
        self.canvas.delete("all")
        self._node_bounds = {}
        self._bus_ys = []
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        scale = self._zoom
        max_node_x = max((n.x for n in self._nodes), default=0.0)
        if len(self._bus_lefts) < len(self._bus_offsets):
            self._bus_lefts.extend([40.0] * (len(self._bus_offsets) - len(self._bus_lefts)))
        if len(self._bus_rights) < len(self._bus_offsets):
            self._bus_rights.extend([max_node_x + 200.0] * (len(self._bus_offsets) - len(self._bus_rights)))
        if len(self._bus_lefts) > len(self._bus_offsets):
            self._bus_lefts = self._bus_lefts[: len(self._bus_offsets)]
        if len(self._bus_rights) > len(self._bus_offsets):
            self._bus_rights = self._bus_rights[: len(self._bus_offsets)]
        eff_lefts = list(self._bus_lefts)
        eff_rights = list(self._bus_rights)
        for idx in range(len(eff_lefts) - 1):
            if idx % 2 == 0:
                shared = eff_rights[idx]
                eff_rights[idx + 1] = shared
            else:
                shared = eff_lefts[idx]
                eff_lefts[idx + 1] = shared
        min_left = min(eff_lefts, default=40.0)
        max_right = max(eff_rights, default=max_node_x + 200.0)
        x_shift = 0.0
        total_width = max(
            width,
            int((self._layout_width or max_right) * scale),
            int((max_right) * scale),
        )
        base_y = height * 0.5 + self._pan_y
        if (
            self._details_layout_shift
            and self._last_base_y is not None
            and (self._last_canvas_height is None or height != self._last_canvas_height)
        ):
            self._details_layout_shift = False
        self._last_base_y = base_y
        self._last_canvas_height = height
        bus_ys = bus_ys_for_offsets(base_y, self._bus_offsets, scale)
        box_w = self._box_w * scale
        box_h = self._box_h * scale
        span = box_h + 60 * scale
        min_y = min((y - span for y in bus_ys), default=0.0)
        max_y = max((y + span for y in bus_ys), default=height)
        for node in self._nodes:
            if not bus_ys:
                break
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys) - 1, 0))
            bus_y = bus_ys[bus_index]
            _, node_box_h = self._node_box_dims(node, scale)
            node_bus_y = self._node_bus_y(node, bus_y, scale)
            y0, y1 = self._node_box_y(node, node_bus_y, node_box_h, scale)
            min_y = min(min_y, y0)
            max_y = max(max_y, y1)
        margin = 20.0
        total_height = max(height, int(max_y - min_y + margin * 2))
        scrollregion_min_x = 0.0
        scrollregion_max_x = float(total_width)
        override = self.__dict__.get("_view_scrollregion_x_override")
        if (
            isinstance(override, tuple)
            and len(override) == SCROLLREGION_FIELD_COUNT - 2
        ):
            try:
                override_min_x = float(override[0])
                override_max_x = float(override[1])
            except (TypeError, ValueError):
                override_min_x = scrollregion_min_x
                override_max_x = scrollregion_max_x
            else:
                scrollregion_min_x = min(scrollregion_min_x, override_min_x)
                scrollregion_max_x = max(scrollregion_max_x, override_max_x)
        if bool(self.__dict__.get("_dragging_active", False)):
            try:
                raw_region = self.canvas.cget("scrollregion")
            except Exception:
                raw_region = TEXT_EMPTY
            parts = str(raw_region).split()
            if len(parts) == SCROLLREGION_FIELD_COUNT:
                try:
                    current_region = [float(part) for part in parts]
                except ValueError:
                    current_region = []
                if len(current_region) == SCROLLREGION_FIELD_COUNT:
                    scrollregion_min_x = min(scrollregion_min_x, current_region[SCROLLREGION_MIN_INDEX])
                    scrollregion_max_x = max(scrollregion_max_x, current_region[SCROLLREGION_MAX_INDEX])
        self.canvas.configure(
            scrollregion=(scrollregion_min_x, min_y - margin, scrollregion_max_x, max_y + margin)
        )
        self._draw_state = {
            "bus_ys": bus_ys,
            "scale": scale,
            "bus_lefts": eff_lefts,
            "bus_rights": eff_rights,
            KEY_DIAGRAM_BUS_CONNECTOR_SIDES: list(self.__dict__.get("_bus_connector_sides", []) or []),
        }
        show_can = self._connection_filter_allows(TOPOLOGY_FILTER_CAN)
        show_dio = self._connection_filter_allows(TOPOLOGY_FILTER_DIO)
        show_virtual = self._connection_filter_allows(TOPOLOGY_FILTER_VIRTUAL)
        x_left = (min_left - x_shift) * scale
        x_right = (max_right - x_shift) * scale
        turn_radius = max(8.0, 18 * scale)
        self._bus_ys = list(bus_ys)
        dup_keys: set[Tuple[str, str, int]] = set()
        key_counts: Dict[Tuple[str, str, int], int] = {}
        numeric_counts: Dict[int, int] = {}
        for node in self._device_nodes():
            key = self._dup_key_for_node(node)
            if key is None:
                continue
            key_counts[key] = key_counts.get(key, 0) + 1
            numeric_counts[key[2]] = numeric_counts.get(key[2], 0) + 1
        dup_keys = {key for key, count in key_counts.items() if count > 1}
        warn_ids = {can_id for can_id, count in numeric_counts.items() if count > 1}
        groups = self._bridge_groups() if "_root_extras" in self.__dict__ else []
        rendered = render_topology_canvas_common(
            canvas=self.canvas,
            nodes=self._nodes,
            bus_ys=bus_ys,
            base_y=base_y,
            scale=scale,
            x_shift=x_shift,
            eff_lefts=eff_lefts,
            eff_rights=eff_rights,
            show_can=show_can,
            show_dio=show_dio,
            show_virtual=show_virtual,
            show_power=self._connection_filter_allows(TOPOLOGY_FILTER_POWER),
            groups=groups,
            selected_node_keys=self._selected_nodes,
            selected_bus_indices=self._selected_buses,
            drag_free_y=self._drag_free_y,
            bus_connectors=self._bus_connectors,
            bus_connector_sides=list(self.__dict__.get("_bus_connector_sides", []) or []),
            bus_lefts=eff_lefts,
            bus_rights=eff_rights,
            min_x=min_left,
            max_x=max_right,
            bus_offsets=self._bus_offsets,
            box_w_base=self._box_w,
            box_h_base=self._box_h,
            linked_devices={link.get("device") for link in self._cannect_device_links},
            can_bus_links=self._can_bus_links if ENABLE_CANNECT_BUS_LINKS else [],
            device_links=self._cannect_device_links if show_can else [],
            power_links=[(link.get(KEY_LINK_A), link.get(KEY_LINK_B)) for link in self._power_links],
            attachment_links=[(link.get(KEY_LINK_DEVICE), link.get(KEY_LINK_ATTACHMENT)) for link in self._attachment_links],
            dio_links=[(link.get(KEY_LINK_ROBORIO), link.get(KEY_LINK_DEVICE)) for link in self._dio_wiring_links],
            ethernet_links=self._ethernet_links if show_virtual else [],
            show_groups=self._show_group_overlays_var.get(),
            node_box_dims_fn=self._node_box_dims,
            node_bus_y_fn=self._node_bus_y,
            node_box_y_fn=self._node_box_y,
            node_center_y_unscaled_fn=self._node_center_y_unscaled,
            should_clamp_node_to_bus_fn=self._should_clamp_node_to_bus,
            is_swyft_node_fn=self._is_swyft_node,
            is_dio_node_fn=self._is_dio_node,
            shape_kind_fn=self._shape_kind_for_node,
            fill_color_fn=self._fill_color_for_node,
            outline_color_fn=self._outline_color_for_node,
            text_color_fn=self._text_color_for_fill,
            label_text_fn=lambda node: node.display_text(),
            fit_font_size_fn=self._fit_font_size,
            wrap_label_lines_fn=self._wrap_label_lines,
            node_tag_name_fn=lambda key: f"node_{key}",
            is_callout_fn=lambda node: node.node_type == "callout",
        )
        self._node_bounds = rendered["node_bounds"]
        node_centers = rendered["node_centers"]
        self._group_overlay_regions = rendered["group_overlay_regions"]
        self._bus_connector_regions = rendered.get("bus_connector_regions", [])
        self._render_scene = rendered
        self._clear_selection_overlays()
        if self._show_warn_badges_var.get():
            for node in self._device_nodes():
                bounds = self._node_bounds.get(node.key)
                if bounds is None:
                    continue
                x0, y0, x1, _y1 = bounds
                dup_key = self._dup_key_for_node(node)
                if dup_key not in dup_keys and not (dup_key and dup_key[2] in warn_ids):
                    continue
                badge_x = min(x1 + 12, x_right - 8)
                badge_y = max(y0 - 12, min_y + 8)
                self.canvas.create_line(
                    x1,
                    y0,
                    badge_x - 6,
                    badge_y + 6,
                    width=1,
                    fill="#444444",
                )
                badge = self._draw_error_badge(badge_x, badge_y) if dup_key in dup_keys else self._draw_warning_badge(badge_x, badge_y)
                for badge_id in badge:
                    self.canvas.addtag_withtag(f"node_{node.key}", badge_id)
        for callout in self._callout_nodes():
            cx = (callout.x - x_shift) * scale
            bus_index = min(max(callout.bus_index, 0), max(len(bus_ys) - 1, 0))
            bus_y = bus_ys[bus_index] if bus_ys else base_y
            box_w, box_h = self._node_box_dims(callout, scale)
            if callout.key in self._drag_free_y:
                cy = base_y + self._drag_free_y[callout.key] * scale
                y0 = cy - box_h / 2
                y1 = cy + box_h / 2
            else:
                if callout.free_y is not None:
                    cy = base_y + self._node_center_y_unscaled(callout) * scale
                    y0 = cy - box_h / 2
                    y1 = cy + box_h / 2
                else:
                    y0, y1 = self._node_box_y(callout, bus_y, box_h, scale)
                    cy = (y0 + y1) / 2.0
            x0 = cx - box_w / 2
            x1 = cx + box_w / 2
            if callout.callout_target_type == "node":
                target_key = callout.callout_target_node_key
                if isinstance(target_key, str) and target_key.isdigit():
                    target_key = int(target_key)
                    callout.callout_target_node_key = target_key
                if target_key not in node_centers:
                    resolved = None
                    for node in self._device_nodes():
                        if callout.callout_target_category and node.category != callout.callout_target_category:
                            continue
                        if (
                            callout.callout_target_id is not None
                            and node.can_id != callout.callout_target_id
                        ):
                            continue
                        if callout.callout_target_label and node.label != callout.callout_target_label:
                            continue
                        resolved = node
                        break
                    if resolved is None and callout.callout_target_label:
                        label_matches = [
                            node
                            for node in self._device_nodes()
                            if node.label == callout.callout_target_label
                            and (
                                not callout.callout_target_category
                                or node.category == callout.callout_target_category
                            )
                        ]
                        if len(label_matches) == 1:
                            resolved = label_matches[0]
                        elif label_matches and callout.callout_target_id is not None:
                            for node in label_matches:
                                if node.can_id == callout.callout_target_id:
                                    resolved = node
                                    break
                    if resolved is not None:
                        callout.callout_target_node_key = resolved.key
                        callout.callout_target_category = resolved.category
                        callout.callout_target_label = resolved.label
                        callout.callout_target_id = resolved.can_id
                        target_key = resolved.key
                if target_key in node_centers:
                    tx, ty = node_centers[target_key]
                else:
                    bus_index = min(
                        max(callout.callout_target_bus, 0), max(len(bus_ys) - 1, 0)
                    )
                    ty = bus_ys[bus_index] if bus_ys else base_y
                    tx = cx
            else:
                bus_index = min(
                    max(callout.callout_target_bus, 0), max(len(bus_ys) - 1, 0)
                )
                ty = bus_ys[bus_index] if bus_ys else base_y
                tx = cx
            self.canvas.create_line(cx, cy, tx, ty, width=2, fill="#666666")
            outline = "#1f6feb" if callout.key in self._selected_nodes else "#666666"
            rect = self.canvas.create_rectangle(
                x0, y0, x1, y1, fill="#fffbe6", outline=outline, width=2
            )
            text_id = self.canvas.create_text(
                cx,
                cy,
                text=callout.callout_text,
                font=("Segoe UI", max(8, int(9 * scale * max(0.6, min(2.0, callout.scale))))),
                justify="center",
                width=max(60, int(box_w - 10)),
            )
            self._node_bounds[callout.key] = (x0, y0, x1, y1)
            self.canvas.addtag_withtag(f"node_{callout.key}", rect)
            self.canvas.addtag_withtag(f"node_{callout.key}", text_id)

        self._group_overlay_regions = []
        if self._show_group_overlays_var.get():
            self._draw_group_overlays()

        if self._guide_x is not None and self._smart_guides_var.get():
            guide_x = (self._guide_x - x_shift) * scale
            self.canvas.create_line(
                guide_x,
                min_y - margin,
                guide_x,
                max_y + margin,
                fill="#1f6feb",
                dash=(4, 4),
                width=1,
            )
        self._update_selection_overlays()
        self._gui_debug_log(
            "redraw.end",
            total_width=total_width,
            min_left=min_left,
            max_right=max_right,
            min_y=min_y,
            max_y=max_y,
        )

        # Legend is optional via View -> Legend.

    def _redraw_canvas_preserve_view(self) -> None:
        """
        NAME
            _redraw_canvas_preserve_view - Rebuild the scene without moving the viewport.
        """
        self._preserve_canvas_view(self._redraw_canvas)

    def _draw_group_overlays(self) -> None:
        """
        NAME
            _draw_group_overlays - Draw bounding boxes for bridgeConfig by-profile groups.
        """
        groups = self._bridge_groups()
        if not groups:
            return
        label_bounds: Dict[str, Tuple[float, float, float, float]] = {}
        for node in self._device_nodes():
            bounds = self._node_bounds.get(node.key)
            if bounds:
                label_bounds[node.label] = bounds
        self._group_overlay_regions = draw_group_overlays(
            self.canvas,
            label_bounds,
            groups,
            zoom=self._zoom,
        )

    def _group_member_keys_by_name(self, name: str) -> set[int]:
        """
        NAME
            _group_member_keys_by_name - Resolve a bridge group name to current node keys.
        """
        target = str(name or TEXT_EMPTY).strip().lower()
        if not target:
            return set()
        labels: set[str] = set()
        for group in self._bridge_groups():
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name", TEXT_EMPTY)).strip()
            if group_name.lower() != target:
                continue
            members = group.get(KEY_BRIDGE_GROUP_MEMBERS, []) or []
            if not isinstance(members, list):
                continue
            for member in members:
                label = TEXT_EMPTY
                if isinstance(member, dict):
                    label = bridge_group_member_label(member)
                elif isinstance(member, str):
                    label = member.strip()
                if label:
                    labels.add(label)
        if not labels:
            return set()
        return {node.key for node in self._nodes if node.label in labels}

    def _group_overlay_hit_test(self, cx: float, cy: float) -> Optional[str]:
        """
        NAME
            _group_overlay_hit_test - Return the group name when a group label/outline is clicked.
        """
        regions = list(self.__dict__.get("_group_overlay_regions", []) or [])
        if not regions:
            return None
        border_tol = 8.0
        for region in sorted(
            regions,
            key=lambda entry: (
                (entry.get("bounds", (0.0, 0.0, 0.0, 0.0))[2] - entry.get("bounds", (0.0, 0.0, 0.0, 0.0))[0])
                * (entry.get("bounds", (0.0, 0.0, 0.0, 0.0))[3] - entry.get("bounds", (0.0, 0.0, 0.0, 0.0))[1])
            ),
        ):
            bounds = region.get("bounds")
            label_bounds = region.get("label_bounds")
            if not isinstance(bounds, tuple) or len(bounds) != 4:
                continue
            x0, y0, x1, y1 = [float(value) for value in bounds]
            if isinstance(label_bounds, tuple) and len(label_bounds) == 4:
                lx0, ly0, lx1, ly1 = [float(value) for value in label_bounds]
                if lx0 <= cx <= lx1 and ly0 <= cy <= ly1:
                    return str(region.get("name", TEXT_EMPTY)).strip() or None
            on_left = abs(cx - x0) <= border_tol and y0 - border_tol <= cy <= y1 + border_tol
            on_right = abs(cx - x1) <= border_tol and y0 - border_tol <= cy <= y1 + border_tol
            on_top = abs(cy - y0) <= border_tol and x0 - border_tol <= cx <= x1 + border_tol
            on_bottom = abs(cy - y1) <= border_tol and x0 - border_tol <= cx <= x1 + border_tol
            if on_left or on_right or on_top or on_bottom:
                return str(region.get("name", TEXT_EMPTY)).strip() or None
        return None

    def _bus_connector_hit_test(self, cx: float, cy: float) -> Optional[int]:
        """
        NAME
            _bus_connector_hit_test - Return the connector index when a wrap connector is clicked.
        """
        regions = list(self.__dict__.get("_bus_connector_regions", []) or [])
        for region in regions:
            bounds = region.get("bounds")
            if not isinstance(bounds, tuple) or len(bounds) != 4:
                continue
            x0, y0, x1, y1 = [float(value) for value in bounds]
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                index = region.get("index")
                if isinstance(index, int):
                    return index
        return None

    def _shape_kind_for_node(self, node: Node) -> str:
        """
        NAME
            _shape_kind_for_node - Map node categories to a shape kind.
        """
        return shape_kind_for_category(node.category or "")

    @staticmethod
    def _is_swyft_node(node: Node) -> bool:
        """
        NAME
            _is_swyft_node - Identify CANnect diagram nodes.
        """
        category = (node.category or "").lower()
        if node.node_type == NODE_TYPE_CALLOUT:
            return False
        return category in (DIAGRAM_CATEGORY_CANNECT_INJECT, DIAGRAM_CATEGORY_CANNECT_DIRECT)

    def _is_infrastructure_node(self, node: Node) -> bool:
        """
        NAME
            _is_infrastructure_node - Identify topology-only infrastructure nodes.
        """
        return self._topology_node_class_for_editor_node(node) == TOPOLOGY_NODE_CLASS_INFRASTRUCTURE

    def _is_registry_device_node(self, node: Node) -> bool:
        """
        NAME
            _is_registry_device_node - Identify nodes that belong in devices[] and profile devices.
        """
        if node.node_type == NODE_TYPE_CALLOUT:
            return False
        if not getattr(node, "profile_visible", True):
            return False
        return not self._is_infrastructure_node(node)

    def _fill_color_for_node(self, node: Node) -> str:
        """
        NAME
            _fill_color_for_node - Resolve fill color based on manufacturer.
        """
        vendor = self._vendor_key_for_node(node)
        return fill_color_for_vendor(vendor)

    def _outline_color_for_node(self, node: Node) -> str:
        """
        NAME
            _outline_color_for_node - Resolve outline color by manufacturer.
        """
        vendor = self._vendor_key_for_node(node)
        return outline_color_for_vendor(vendor)

    def _vendor_key_for_node(self, node: Node) -> str:
        """
        NAME
            _vendor_key_for_node - Normalize vendor key for a node.
        """
        return vendor_key_for_category(node.category or "", node.vendor or "")

    def _device_type_key_for_node(self, node: Node) -> str:
        """
        NAME
            _device_type_key_for_node - Normalize device type key for a node.
        """
        return device_type_key_for_category(node.category or "", node.device_type or "")

    def _dup_key_for_node(self, node: Node) -> Optional[Tuple[str, str, int]]:
        """
        NAME
            _dup_key_for_node - Build a duplicate-detection key.
        """
        if node.interface != INTERFACE_CAN:
            return None
        if not isinstance(node.can_id, int) or node.can_id < 0:
            return None
        vendor = self._vendor_key_for_node(node) or "UNKNOWN"
        dev_type = self._device_type_key_for_node(node)
        return (vendor, dev_type, int(node.can_id))

    @staticmethod
    def _text_color_for_fill(fill: str) -> str:
        """
        NAME
            _text_color_for_fill - Choose readable text color for a fill.
        """
        return text_color_for_fill(fill)

    def _draw_legend(self, x: float, y: float) -> None:
        """
        NAME
            _draw_legend - Draw a shape/color legend in the top-left.
        """
        padding = 8
        line_h = 16
        link_line_h = 14
        shape_h = 14
        shape_w = 24
        text_x = x + padding + shape_w + 8
        legend_items = [
            ("Motors", "motor"),
            ("Sensors", "sensor"),
            ("Power", "power"),
            ("Controller", "controller"),
            ("Misc", "misc"),
        ]
        color_items = [
            ("CTRE", "CTRE"),
            ("REV", "REV"),
            ("KauaiLabs", "KAUAILABS"),
            ("PlayingWithFusion", "PLAYINGWITHFUSION"),
            ("AndyMark", "ANDYMARK"),
            ("NI", "NI"),
        ]
        link_items = [
            ("Attachment (logical)", ATTACH_LINE_COLOR, ATTACH_LINK_DASH),
            ("DIO wire (roboRIO)", WIRE_LINE_COLOR, DIO_WIRE_DASH),
            ("Ethernet device link", "#1c6ba8", ETHERNET_DEVICE_DASH),
            ("CAN bus (physical)", BUS_LINE_COLOR, None),
        ]
        height = (
            padding * 2
            + line_h * (len(legend_items) + len(color_items) + 2)
            + link_line_h * (len(link_items) + 1)
        )
        width = 240
        self.canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill="#ffffff",
            outline="#d0d0d0",
            width=1,
        )
        cy = y + padding
        self.canvas.create_text(
            x + padding,
            cy,
            text="Legend",
            anchor="nw",
            font=("Segoe UI", 9, "bold"),
            fill="#333333",
        )
        cy += line_h
        for label, kind in legend_items:
            sx0 = x + padding
            sy0 = cy + 2
            sx1 = sx0 + shape_w
            sy1 = sy0 + shape_h
            self._draw_device_shape(sx0, sy0, sx1, sy1, kind, "#f7f7f7", "#555555", 1)
            self.canvas.create_text(
                text_x,
                cy,
                text=label,
                anchor="nw",
                font=("Segoe UI", 9),
                fill="#333333",
            )
            cy += line_h
        cy += 4
        for label, vendor in color_items:
            sx0 = x + padding
            sy0 = cy + 2
            sx1 = sx0 + shape_w
            sy1 = sy0 + shape_h
            fill = self._fill_color_for_vendor(vendor)
            outline = self._outline_color_for_vendor(vendor)
            self.canvas.create_rectangle(
                sx0, sy0, sx1, sy1, fill=fill, outline=outline, width=1
            )
            self.canvas.create_text(
                text_x,
                cy,
                text=label,
                anchor="nw",
                font=("Segoe UI", 9),
                fill="#333333",
            )
            cy += line_h
        cy += 4
        for label, color, dash in link_items:
            lx0 = x + padding
            ly = cy + link_line_h // 2
            lx1 = lx0 + shape_w
            if dash:
                self.canvas.create_line(
                    lx0,
                    ly,
                    lx1,
                    ly,
                    width=LINK_LINE_WIDTH,
                    fill=color,
                    dash=dash,
                )
            else:
                self.canvas.create_line(
                    lx0,
                    ly,
                    lx1,
                    ly,
                    width=LINK_LINE_WIDTH,
                    fill=color,
                )
            self.canvas.create_text(
                text_x,
                cy,
                text=label,
                anchor="nw",
                font=("Segoe UI", 9),
                fill="#333333",
            )
            cy += link_line_h

    def _draw_error_badge(self, cx: float, cy: float) -> List[int]:
        """
        NAME
            _draw_error_badge - Draw a red exclamation badge.
        """
        r = 7
        badge = self.canvas.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            fill="#cc0000",
            outline="#aa0000",
            width=1,
        )
        text = self.canvas.create_text(
            cx,
            cy - 0.5,
            text="!",
            font=("Segoe UI", 9, "bold"),
            fill="#ffffff",
        )
        return [badge, text]

    def _draw_warning_badge(self, cx: float, cy: float) -> List[int]:
        """
        NAME
            _draw_warning_badge - Draw a yellow warning triangle badge.
        """
        r = 8
        points = [
            cx,
            cy - r,
            cx + r,
            cy + r,
            cx - r,
            cy + r,
        ]
        badge = self.canvas.create_polygon(
            points,
            fill="#f5c542",
            outline="#c28b00",
            width=1,
        )
        text = self.canvas.create_text(
            cx,
            cy + 1,
            text="!",
            font=("Segoe UI", 9, "bold"),
            fill="#5a3b00",
        )
        return [badge, text]

    def _show_legend_dialog(self) -> None:
        """
        NAME
            _show_legend_dialog - Show a legend popup dialog.
        """
        if getattr(self, "_legend_window", None):
            try:
                self._legend_window.lift()
                return
            except tk.TclError:
                self._legend_window = None
        dialog = tk.Toplevel(self)
        self._legend_window = dialog
        dialog.title("Legend")
        dialog.resizable(False, False)
        dialog.transient(self)

        canvas = tk.Canvas(dialog, width=260, height=320, background="#ffffff")
        canvas.pack(padx=8, pady=8)

        def _draw_on(canvas_obj: tk.Canvas) -> None:
            padding = 8
            line_h = 18
            link_line_h = 16
            shape_h = 14
            shape_w = 24
            text_x = padding + shape_w + 8
            legend_items = [
                ("Motors", "motor"),
                ("Sensors", "sensor"),
                ("Power", "power"),
                ("Controller", "controller"),
                ("Misc", "misc"),
            ]
            color_items = [
                ("CTRE", "CTRE"),
                ("REV", "REV"),
                ("KauaiLabs", "KAUAILABS"),
                ("PlayingWithFusion", "PLAYINGWITHFUSION"),
                ("AndyMark", "ANDYMARK"),
                ("NI", "NI"),
            ]
            cy = padding
            canvas_obj.create_text(
                padding,
                cy,
                text="Legend",
                anchor="nw",
                font=("Segoe UI", 10, "bold"),
                fill="#333333",
            )
            cy += line_h
            for label, kind in legend_items:
                sx0 = padding
                sy0 = cy + 2
                sx1 = sx0 + shape_w
                sy1 = sy0 + shape_h
                self._draw_device_shape_on(
                    canvas_obj, sx0, sy0, sx1, sy1, kind, "#f7f7f7", "#555555", 1
                )
                canvas_obj.create_text(
                    text_x,
                    cy,
                    text=label,
                    anchor="nw",
                    font=("Segoe UI", 9),
                    fill="#333333",
                )
                cy += line_h
            cy += 6
            for label, vendor in color_items:
                sx0 = padding
                sy0 = cy + 2
                sx1 = sx0 + shape_w
                sy1 = sy0 + shape_h
                fill = self._fill_color_for_vendor(vendor)
                outline = self._outline_color_for_vendor(vendor)
                canvas_obj.create_rectangle(
                    sx0, sy0, sx1, sy1, fill=fill, outline=outline, width=1
                )
                canvas_obj.create_text(
                    text_x,
                    cy,
                    text=label,
                    anchor="nw",
                    font=("Segoe UI", 9),
                    fill="#333333",
                )
                cy += line_h
            cy += 6
            link_items = [
                ("Attachment (logical)", ATTACH_LINE_COLOR, ATTACH_LINK_DASH),
                ("DIO wire (roboRIO)", WIRE_LINE_COLOR, DIO_WIRE_DASH),
                ("Ethernet device link", "#1c6ba8", ETHERNET_DEVICE_DASH),
                ("CAN bus (physical)", BUS_LINE_COLOR, None),
            ]
            for label, color, dash in link_items:
                lx0 = padding
                ly = cy + link_line_h // 2
                lx1 = lx0 + shape_w
                if dash:
                    canvas_obj.create_line(
                        lx0,
                        ly,
                        lx1,
                        ly,
                        width=LINK_LINE_WIDTH,
                        fill=color,
                        dash=dash,
                    )
                else:
                    canvas_obj.create_line(
                        lx0,
                        ly,
                        lx1,
                        ly,
                        width=LINK_LINE_WIDTH,
                        fill=color,
                    )
                canvas_obj.create_text(
                    text_x,
                    cy,
                    text=label,
                    anchor="nw",
                    font=("Segoe UI", 9),
                    fill="#333333",
                )
                cy += link_line_h

        _draw_on(canvas)

        button_row = ttk.Frame(dialog)
        button_row.pack(pady=(0, 8))
        ttk.Button(button_row, text="Close", command=dialog.destroy).pack()
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.bind(
            "<Destroy>",
            lambda _e: setattr(self, "_legend_window", None),
        )

    def _help_topics(self) -> Dict[str, str]:
        """
        NAME
            _help_topics - Build help topic text blocks.
        """
        return {
            "Overview": (
                "Purpose: Sketch CAN nodes on a shared bus and export a bringup profile.\n"
                "\n"
                "Quick steps:\n"
                "1) Add nodes and labels.\n"
                "2) Drag nodes onto bus segments.\n"
                "3) Drag devices onto CANnect nodes (or use Edit -> Link Device to CANnect).\n"
                "4) Save profile or export.\n"
            ),
            "Keyboard Shortcuts": (
                "Purpose: Speed up common actions.\n"
                "\n"
                "Selection:\n"
                "- Ctrl+A: Select all nodes (devices + callouts).\n"
                "- Shift+Click: Multi-select nodes or buses.\n"
                "\n"
                "Edit:\n"
                "- Ctrl+C: Copy selection.\n"
                "- Ctrl+D: Duplicate selection.\n"
                "- Ctrl+V: Paste.\n"
                "- Delete / Backspace: Remove selected devices/callouts from the current profile.\n"
                "- Ctrl+Z: Undo.\n"
                "\n"
                "Layout:\n"
                "- Ctrl+L: Tidy selection within bus bounds.\n"
                "- Ctrl+Shift+L: Reset layout (per-bus even spacing).\n"
                "- Layout -> Tidy All: Align all buses into shared columns.\n"
                "- Arrow keys: Nudge selected nodes (Shift = faster).\n"
                "\n"
                "View:\n"
                "- Ctrl+0: Reset zoom.\n"
                "- Ctrl++ / Ctrl+=: Zoom in.\n"
                "- Ctrl+- / Ctrl+_: Zoom out.\n"
                "- Ctrl+MouseWheel: Zoom.\n"
                "- Ctrl+G: Toggle snap-to-grid.\n"
                "- Ctrl+Shift+G: Toggle smart guides.\n"
                "\n"
                "Save:\n"
                "- Ctrl+S: Save Config to the currently loaded config path.\n"
            ),
            "Layout Tips": (
                "Purpose: Keep diagrams tidy and readable.\n"
                "\n"
                "- Use Snap to Grid for consistent spacing.\n"
                "- Use Smart Guides to align nodes on a bus segment.\n"
                "- Use arrow keys to nudge selections without re-dragging.\n"
                "- Tidy Selection aligns selected nodes into shared columns.\n"
                "- Reset Layout preserves bus/row and evens per-bus spacing.\n"
                "- Single Bus Layout puts all devices on one bus line.\n"
                "- Auto Layout (Readable) groups nodes by type and rows.\n"
                "- Align/Distribute tools are under the Layout menu.\n"
            ),
            "Tags": (
                "Purpose: Group and organize nodes with freeform tags.\n"
                "\n"
                "- Tags are comma-separated values on nodes and callouts.\n"
                "- Tags are saved into bringup_system.json for devices.\n"
                "- Use Tags -> Select by Tag to multi-select.\n"
                "- Use Tags -> Filter List by Tag to narrow the list.\n"
                "  Expression supports AND/OR, &&/||, commas, and implicit OR.\n"
                "- Use Tags -> Tidy by Tag to align a tag group.\n"
                "- Sort the list by tag from the Tags menu.\n"
            ),
            "Groups": (
                "Purpose: Store CLI groups and visualize them in the diagram.\n"
                "\n"
                "- Use Groups -> Create Group from Selection... after multi-selecting nodes.\n"
                "- Groups are stored under bridgeConfig.byProfile.<profile>.groups in bringup_system.json.\n"
                "- View -> Show Group Overlays toggles colored group outline boxes.\n"
            ),
            HELP_DIO_TITLE: HELP_DIO_BODY,
            "Bus Segments": (
                "Purpose: Understand bus segment editing.\n"
                "\n"
                "- Add Bus, then click to place a new segment.\n"
                "- Drag a bus line to move it; nodes follow.\n"
                "- Drag the curved end of a segment to resize it.\n"
            ),
            "Profiles & Export": (
                "Purpose: Save or export diagram data.\n"
                "\n"
                "- Save to Deploy writes to src/main/deploy/bringup_system.json.\n"
                "- Save Profile As... exports a single profile JSON.\n"
                "- Export PDF requires reportlab.\n"
            ),
        }

    def _show_help_dialog(self) -> None:
        """
        NAME
            _show_help_dialog - Show the help topics dialog.
        """
        if getattr(self, "_help_window", None):
            try:
                self._help_window.lift()
                return
            except tk.TclError:
                self._help_window = None
        dialog = tk.Toplevel(self)
        self._help_window = dialog
        dialog.title("Help")
        dialog.geometry("640x420")
        dialog.minsize(520, 320)
        dialog.transient(self)

        container = ttk.Frame(dialog, padding=8)
        container.pack(fill="both", expand=True)

        left = ttk.Frame(container)
        left.pack(side="left", fill="y")
        right = ttk.Frame(container)
        right.pack(side="right", fill="both", expand=True)

        ttk.Label(left, text="Topics").pack(anchor="w")
        topics = list(self._help_topics().keys())
        listbox = tk.Listbox(left, height=12, exportselection=False)
        for item in topics:
            listbox.insert("end", item)
        listbox.pack(fill="y", expand=True, pady=(4, 0))

        text = tk.Text(right, wrap="word", height=12)
        text.pack(fill="both", expand=True)
        text.configure(state="disabled")

        def _set_topic(name: str) -> None:
            content = self._help_topics().get(name, "")
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("1.0", content)
            text.configure(state="disabled")

        def _on_select(_event: tk.Event) -> None:
            selection = listbox.curselection()
            if not selection:
                return
            _set_topic(topics[selection[0]])

        listbox.bind("<<ListboxSelect>>", _on_select)
        if topics:
            listbox.selection_set(0)
            _set_topic(topics[0])

    def _show_shortcuts_dialog(self) -> None:
        """
        NAME
            _show_shortcuts_dialog - Show keyboard shortcuts only.
        """
        text = self._help_topics().get("Keyboard Shortcuts", "")
        messagebox.showinfo("Keyboard Shortcuts", text)

    def _show_about_dialog(self) -> None:
        """
        NAME
            _show_about_dialog - Show the about dialog.
        """
        version = VERSIONS.get(VERSION_APP_NAME, "")
        version_line = format_version_line(VERSION_APP_NAME, version) if version else ""
        lines = [ABOUT_NAME, version_line, BUILD_TITLE, *build_lines(), ABOUT_DESCRIPTION, ABOUT_LAUNCH]
        body = ABOUT_SEPARATOR.join([line for line in lines if line])
        messagebox.showinfo(ABOUT_TITLE, body)

    def _fill_color_for_vendor(self, vendor: str) -> str:
        """
        NAME
            _fill_color_for_vendor - Resolve fill color for a vendor key.
        """
        return fill_color_for_vendor(vendor)

    def _outline_color_for_vendor(self, vendor: str) -> str:
        """
        NAME
            _outline_color_for_vendor - Resolve outline color for a vendor key.
        """
        return outline_color_for_vendor(vendor)

    def _draw_device_shape_on(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        kind: str,
        fill: str,
        outline: str,
        width: int,
    ) -> List[int]:
        """
        NAME
            _draw_device_shape - Draw a device shape for the given kind.

        RETURNS
            List of canvas item ids.
        """
        if kind == "motor":
            return [self._draw_chamfer_rect(canvas, x0, y0, x1, y1, fill, outline, width)]
        if kind == "sensor":
            return [self._draw_hexagon(canvas, x0, y0, x1, y1, fill, outline, width)]
        if kind == "power":
            return [self._draw_diamond(canvas, x0, y0, x1, y1, fill, outline, width)]
        if kind == "controller":
            return [self._draw_tabbed_rect(canvas, x0, y0, x1, y1, fill, outline, width)]
        return [canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=width)]

    def _draw_chamfer_rect(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        fill: str,
        outline: str,
        width: int,
    ) -> int:
        """
        NAME
            _draw_chamfer_rect - Draw a rectangle with chamfered corners.
        """
        inset = max(6.0, min(14.0, (x1 - x0) * 0.08, (y1 - y0) * 0.25))
        points = [
            x0 + inset,
            y0,
            x1 - inset,
            y0,
            x1,
            y0 + inset,
            x1,
            y1 - inset,
            x1 - inset,
            y1,
            x0 + inset,
            y1,
            x0,
            y1 - inset,
            x0,
            y0 + inset,
        ]
        return canvas.create_polygon(
            points, fill=fill, outline=outline, width=width, joinstyle="round"
        )

    def _draw_hexagon(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        fill: str,
        outline: str,
        width: int,
    ) -> int:
        """
        NAME
            _draw_hexagon - Draw a horizontally stretched hexagon.
        """
        inset = max(8.0, min(18.0, (x1 - x0) * 0.18))
        yc = (y0 + y1) / 2.0
        points = [
            x0 + inset,
            y0,
            x1 - inset,
            y0,
            x1,
            yc,
            x1 - inset,
            y1,
            x0 + inset,
            y1,
            x0,
            yc,
        ]
        return canvas.create_polygon(
            points, fill=fill, outline=outline, width=width, joinstyle="round"
        )

    def _draw_diamond(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        fill: str,
        outline: str,
        width: int,
    ) -> int:
        """
        NAME
            _draw_diamond - Draw a diamond shape.
        """
        xc = (x0 + x1) / 2.0
        yc = (y0 + y1) / 2.0
        points = [xc, y0, x1, yc, xc, y1, x0, yc]
        return canvas.create_polygon(
            points, fill=fill, outline=outline, width=width, joinstyle="round"
        )

    def _draw_tabbed_rect(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        fill: str,
        outline: str,
        width: int,
    ) -> int:
        """
        NAME
            _draw_tabbed_rect - Draw a rectangle with a top-center tab.
        """
        tab_w = max(18.0, min(42.0, (x1 - x0) * 0.35))
        tab_h = max(10.0, min(18.0, (y1 - y0) * 0.25))
        xc = (x0 + x1) / 2.0
        points = [
            x0,
            y1,
            x1,
            y1,
            x1,
            y0 + tab_h,
            xc + tab_w / 2.0,
            y0 + tab_h,
            xc + tab_w / 2.0,
            y0,
            xc - tab_w / 2.0,
            y0,
            xc - tab_w / 2.0,
            y0 + tab_h,
            x0,
            y0 + tab_h,
        ]
        return canvas.create_polygon(
            points, fill=fill, outline=outline, width=width, joinstyle="round"
        )

    def _on_canvas_pan_press(self, event: tk.Event) -> str:
        """
        NAME
            _on_canvas_pan_press - Begin whole-diagram canvas panning.
        """
        self.canvas.focus_set()
        self._ensure_horizontal_pan_room()
        self.canvas.scan_mark(event.x, event.y)
        self._pan_drag = None
        self._drag_state = None
        self._multi_drag = None
        self._bus_drag = None
        self._bus_resize = None
        self._selection_start = None
        return "break"

    def _on_canvas_pan_drag(self, event: tk.Event) -> str:
        """
        NAME
            _on_canvas_pan_drag - Pan the canvas with the middle mouse button.
        """
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        return "break"

    def _on_canvas_pan_release(self, _event: tk.Event) -> str:
        """
        NAME
            _on_canvas_pan_release - Finish whole-diagram canvas panning.
        """
        return "break"

    def _ensure_horizontal_pan_room(self) -> None:
        """
        NAME
            _ensure_horizontal_pan_room - Expand scrollregion for middle-button pan.

        DESCRIPTION
            Fit-to-window can make the horizontal scrollregion no wider than
            the viewport. Tk canvas scanning cannot move horizontally in that
            state, so add temporary left/right blank space while preserving the
            current viewport origin.
        """
        try:
            raw_region = self.canvas.cget("scrollregion")
        except Exception:
            return
        parts = str(raw_region).split()
        if len(parts) != SCROLLREGION_FIELD_COUNT:
            return
        try:
            region = [float(part) for part in parts]
        except ValueError:
            return
        width = max(float(self.canvas.winfo_width()), SCROLLREGION_MIN_SPAN)
        current_left = float(self.canvas.canvasx(0))
        pad = width * PAN_SCROLLREGION_PAD_VIEWPORTS
        old_min_x = region[SCROLLREGION_MIN_INDEX]
        old_max_x = region[SCROLLREGION_MAX_INDEX]
        new_min_x = min(old_min_x, current_left - pad)
        new_max_x = max(old_max_x, current_left + width + pad)
        new_span = max(new_max_x - new_min_x, SCROLLREGION_MIN_SPAN)
        if new_min_x == old_min_x and new_max_x == old_max_x:
            return
        region[SCROLLREGION_MIN_INDEX] = new_min_x
        region[SCROLLREGION_MAX_INDEX] = new_max_x
        self._view_scrollregion_x_override = (new_min_x, new_max_x)
        self.canvas.configure(scrollregion=tuple(region))
        fraction = (current_left - new_min_x) / new_span
        self.canvas.xview_moveto(max(0.0, min(1.0, fraction)))

    def _set_canvas_xview_left(self, desired_left: float) -> None:
        """
        NAME
            _set_canvas_xview_left - Position the canvas viewport at an X coordinate.
        """
        try:
            raw_region = self.canvas.cget("scrollregion")
        except Exception:
            return
        parts = str(raw_region).split()
        if len(parts) != SCROLLREGION_FIELD_COUNT:
            return
        try:
            region = [float(part) for part in parts]
        except ValueError:
            return
        width = max(float(self.canvas.winfo_width()), SCROLLREGION_MIN_SPAN)
        old_min_x = region[SCROLLREGION_MIN_INDEX]
        old_max_x = region[SCROLLREGION_MAX_INDEX]
        new_min_x = min(old_min_x, desired_left)
        new_max_x = max(old_max_x, desired_left + width)
        new_span = max(new_max_x - new_min_x, SCROLLREGION_MIN_SPAN)
        if new_min_x != old_min_x or new_max_x != old_max_x:
            region[SCROLLREGION_MIN_INDEX] = new_min_x
            region[SCROLLREGION_MAX_INDEX] = new_max_x
            self._view_scrollregion_x_override = (new_min_x, new_max_x)
            self.canvas.configure(scrollregion=tuple(region))
        fraction = (desired_left - new_min_x) / new_span
        self.canvas.xview_moveto(max(0.0, min(1.0, fraction)))
        self._gui_debug_log(
            "set_xview_left",
            desired_left=desired_left,
            new_min_x=new_min_x,
            new_max_x=new_max_x,
            fraction=fraction,
        )

    def _set_canvas_yview_top(self, desired_top: float) -> None:
        """
        NAME
            _set_canvas_yview_top - Position the canvas viewport at a Y coordinate.
        """
        try:
            raw_region = self.canvas.cget("scrollregion")
        except Exception:
            return
        parts = str(raw_region).split()
        if len(parts) != SCROLLREGION_FIELD_COUNT:
            return
        try:
            region = [float(part) for part in parts]
        except ValueError:
            return
        height = max(float(self.canvas.winfo_height()), SCROLLREGION_MIN_SPAN)
        y_min_index = SCROLLREGION_MIN_INDEX + BUS_INDEX_FLOOR
        y_max_index = SCROLLREGION_MAX_INDEX + BUS_INDEX_FLOOR
        old_min_y = region[y_min_index]
        old_max_y = region[y_max_index]
        new_min_y = min(old_min_y, desired_top)
        new_max_y = max(old_max_y, desired_top + height)
        new_span = max(new_max_y - new_min_y, SCROLLREGION_MIN_SPAN)
        if new_min_y != old_min_y or new_max_y != old_max_y:
            region[y_min_index] = new_min_y
            region[y_max_index] = new_max_y
            self.canvas.configure(scrollregion=tuple(region))
        fraction = (desired_top - new_min_y) / new_span
        self.canvas.yview_moveto(max(0.0, min(1.0, fraction)))
        self._gui_debug_log(
            "set_yview_top",
            desired_top=desired_top,
            new_min_y=new_min_y,
            new_max_y=new_max_y,
            fraction=fraction,
        )

    def _drag_threshold_exceeded(self, dx: float, dy: float) -> bool:
        """
        NAME
            _drag_threshold_exceeded - Return True once pointer motion is clearly a drag.
        """
        return abs(dx) >= CLICK_DRAG_THRESHOLD_PX or abs(dy) >= CLICK_DRAG_THRESHOLD_PX

    def _on_canvas_press(self, event: tk.Event) -> None:
        """
        NAME
            _on_canvas_press - Begin dragging a node if clicked.
        """
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        self._gui_debug_log("press", event_x=event.x, event_y=event.y, cx=cx, cy=cy)
        self.canvas.focus_set()
        self._clear_guides()
        if self._selection_rect is not None:
            self.canvas.delete(self._selection_rect)
            self._selection_rect = None
            self._selection_start = None
        if self._add_bus_mode:
            self._add_bus_at(cy)
            self._add_bus_mode = False
            return
        connector_index = self._bus_connector_hit_test(cx, cy)
        if connector_index is not None and not self._shift_held(event):
            self._push_undo()
            self._drag_undo_pending = True
            self._bus_connector_drag = (connector_index, self._bus_connector_side(connector_index), cx)
            return
        group_name = self._group_overlay_hit_test(cx, cy)
        if group_name and not self._shift_held(event):
            member_keys = self._group_member_keys_by_name(group_name)
            if member_keys:
                self._selected_nodes = set(member_keys)
                self._selected_buses = set()
                self._sync_selection_state()
                self._start_multi_drag(cx, cy)
                return
        key = self._find_node_key_at(cx, cy)
        total_selected = len(self._selected_nodes)
        if self._shift_held(event):
            if key is not None:
                self._toggle_node_selection(key)
                return
            bus_index = self._bus_hit_test(cy)
            if bus_index is not None:
                self._toggle_bus_selection(bus_index)
                return
            self._selection_start = (cx, cy)
            self._selection_rect = self.canvas.create_rectangle(
                cx, cy, cx, cy, outline="#1f6feb", dash=(4, 2)
            )
            return
        if key is None:
            # Check if we clicked near a bus line to drag it.
            bus_index = self._bus_hit_test(cy)
            if bus_index is not None:
                end = self._bus_end_hit_test(bus_index, cx, cy)
                if end:
                    self._push_undo()
                    self._drag_undo_pending = True
                    self._bus_resize = (
                        bus_index,
                        end,
                        self._bus_lefts[bus_index],
                        self._bus_rights[bus_index],
                        cx,
                    )
                    return
                self._selected_buses = {bus_index}
                self._selected_inventory_label = None
                self._selected_nodes = set()
                self._sync_selection_state()
                self._push_undo()
                bus_ys = list(self._draw_state.get("bus_ys", []))
                bus_y = bus_ys[bus_index] if bus_ys else cy
                self._bus_drag = (bus_index, bus_y, self._bus_offsets[bus_index], cx, cy)
            else:
                if not self._selected_nodes and not self._selected_buses:
                    return
                self._clear_selection()
                return
            return
        if key in self._selected_nodes and total_selected > 1:
            self._start_multi_drag(cx, cy)
        else:
            already_single_selected = key in self._selected_nodes and total_selected == 1 and not self._selected_buses
            if not already_single_selected:
                self._set_single_node_selection(key)
            node = next((n for n in self._nodes if n.key == key), None)
            if ENABLE_CANNECT_CLUSTER_DRAG and node is not None and self._is_swyft_node(node):
                self._push_undo()
                self._drag_undo_pending = True
                self._start_cannect_cluster_drag(key, cx, cy)
                return
            self._push_undo()
            self._drag_undo_pending = True
            self._drag_state = (key, cx, cy)

    def _on_canvas_drag(self, event: tk.Event) -> None:
        """
        NAME
            _on_canvas_drag - Drag the selected node horizontally.
        """
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        self._gui_debug_log(
            "drag",
            event_x=event.x,
            event_y=event.y,
            cx=cx,
            cy=cy,
            drag_state=self._drag_state,
            multi_drag=bool(self._multi_drag),
            bus_drag=self._bus_drag,
            bus_resize=self._bus_resize,
            bus_connector_drag=self._bus_connector_drag,
        )
        if self._selection_start is not None and self._selection_rect is not None:
            x0, y0 = self._selection_start
            self.canvas.coords(self._selection_rect, x0, y0, cx, cy)
            return
        if self._multi_drag is not None:
            start_cx, start_cy = self._multi_drag.get("start", (cx, cy))
            dx = cx - start_cx
            dy = cy - start_cy
            if not self._dragging_active and not self._drag_threshold_exceeded(dx, dy):
                return
            if not self._dragging_active:
                self._dragging_active = True
            scale = max(self._zoom, 0.01)
            nodes_start = self._multi_drag.get("nodes", {})
            base_y = max(self.canvas.winfo_height(), 1) * 0.5 + self._pan_y
            dx_unscaled = dx / scale
            anchor_key = self._multi_drag.get("anchor")
            if anchor_key in nodes_start:
                anchor_start_x = nodes_start[anchor_key][0]
                if self._snap_to_grid_var.get():
                    dx_unscaled = self._snap_value(anchor_start_x + dx_unscaled) - anchor_start_x
                anchor_node = next((n for n in self._nodes if n.key == anchor_key), None)
                if anchor_node is not None:
                    candidate_x = anchor_start_x + dx_unscaled
                    candidate_x, guide_x = self._apply_smart_guides(
                        anchor_node, candidate_x, self._selected_nodes
                    )
                    candidate_x = self._clamp_node_x_to_current_bus_bounds(anchor_node, candidate_x)
                    dx_unscaled = candidate_x - anchor_start_x
                    self._guide_x = guide_x
                    self._guide_bus = anchor_node.bus_index if guide_x is not None else None
                else:
                    self._clear_guides()
            else:
                self._clear_guides()
            for node in self._nodes:
                if node.key not in nodes_start:
                    continue
                start_x, start_bus, start_row, start_scale, start_center = nodes_start[node.key]
                node.x = start_x + dx_unscaled
                free_y = start_center + dy / scale
                if self._is_dio_node(node):
                    free_y -= DIO_RAIL_OFFSET
                self._drag_free_y[node.key] = free_y
            self._redraw_canvas()
            return
        if self._pan_drag is not None:
            if not self._dragging_active:
                self._dragging_active = True
            start_y, start_pan = self._pan_drag
            dy = cy - start_y
            height = max(self.canvas.winfo_height(), 1)
            max_shift = height * 0.25
            self._pan_y = max(-max_shift, min(max_shift, start_pan + dy))
            self._dirty = True
            self._redraw_canvas()
            return
        if self._bus_drag is not None:
            bus_index, start_bus_y, start_offset, start_cx, start_cy = self._bus_drag
            if not self._dragging_active and not self._drag_threshold_exceeded(cx - start_cx, cy - start_cy):
                return
            if not self._dragging_active:
                self._dragging_active = True
            scale = max(self._zoom, 0.01)
            dy_canvas = cy - start_bus_y
            delta = dy_canvas / scale
            self._bus_offsets[bus_index] = start_offset + delta
            self._redraw_canvas()
            return
        if self._bus_connector_drag is not None:
            connector_index, start_side, start_cx = self._bus_connector_drag
            scale = max(self._zoom, 0.01)
            drag_dx = cx - start_cx
            if not self._dragging_active and abs(drag_dx) < CLICK_DRAG_THRESHOLD_PX:
                return
            if not self._dragging_active:
                self._dragging_active = True
            drag_threshold = max(18.0, 12.0 * scale)
            desired_side = start_side
            if drag_dx <= -drag_threshold:
                desired_side = BUS_CONNECT_SIDE_LEFT
            elif drag_dx >= drag_threshold:
                desired_side = BUS_CONNECT_SIDE_RIGHT
            if desired_side != self._bus_connector_side(connector_index):
                self._set_bus_connector_side(connector_index, desired_side)
                self._clamp_nodes_to_bus_bounds({connector_index, connector_index + 1})
                self._dirty = True
                self._redraw_canvas()
            return
        if self._bus_resize is not None:
            bus_index, end, start_left, start_right, start_cx = self._bus_resize
            if not self._dragging_active and abs(cx - start_cx) < CLICK_DRAG_THRESHOLD_PX:
                return
            if not self._dragging_active:
                self._dragging_active = True
            scale = max(self._zoom, 0.01)
            dx = (cx - start_cx) / scale
            left = start_left
            right = start_right
            min_len = 120.0

            connector_with_next = (
                bus_index < len(self._bus_connectors)
                and self._bus_connectors[bus_index]
                and end == self._bus_connector_side(bus_index)
            )
            connector_with_prev = (
                bus_index - BUS_INDEX_FLOOR >= 0
                and bus_index - BUS_INDEX_FLOOR < len(self._bus_connectors)
                and self._bus_connectors[bus_index - BUS_INDEX_FLOOR]
                and end == self._bus_connector_side(bus_index - BUS_INDEX_FLOOR)
            )

            new_pos = (start_left + dx) if end == "left" else (start_right + dx)
            min_allowed = float("-inf")
            max_allowed = float("inf")

            # Clamp for the current segment.
            if end == "left":
                max_allowed = min(max_allowed, right - min_len)
            else:
                min_allowed = max(min_allowed, left + min_len)

            # If we are dragging a connector, also clamp against the neighbor segment.
            if connector_with_next and bus_index + 1 < len(self._bus_offsets):
                next_left = self._bus_lefts[bus_index + 1]
                next_right = self._bus_rights[bus_index + 1]
                next_side = self._bus_connector_side(bus_index)
                if next_side == BUS_CONNECT_SIDE_RIGHT:
                    min_allowed = max(min_allowed, next_left + min_len)
                else:
                    max_allowed = min(max_allowed, next_right - min_len)
            if connector_with_prev and bus_index - 1 >= 0:
                prev_left = self._bus_lefts[bus_index - 1]
                prev_right = self._bus_rights[bus_index - 1]
                prev_side = self._bus_connector_side(bus_index - BUS_INDEX_FLOOR)
                if prev_side == BUS_CONNECT_SIDE_RIGHT:
                    min_allowed = max(min_allowed, prev_left + min_len)
                else:
                    max_allowed = min(max_allowed, prev_right - min_len)

            if min_allowed != float("-inf") or max_allowed != float("inf"):
                new_pos = max(min_allowed, min(max_allowed, new_pos))

            if end == "left":
                left = new_pos
            else:
                right = new_pos

            # Apply to neighbors when dragging a connector end.
            resized_bus_indices = {bus_index}
            if connector_with_next and bus_index + 1 < len(self._bus_offsets):
                resized_bus_indices.add(bus_index + 1)
                if self._bus_connector_side(bus_index) == BUS_CONNECT_SIDE_RIGHT:
                    self._bus_rights[bus_index + 1] = new_pos
                else:
                    self._bus_lefts[bus_index + 1] = new_pos
            if connector_with_prev and bus_index - 1 >= 0:
                resized_bus_indices.add(bus_index - 1)
                if self._bus_connector_side(bus_index - BUS_INDEX_FLOOR) == BUS_CONNECT_SIDE_RIGHT:
                    self._bus_rights[bus_index - 1] = new_pos
                else:
                    self._bus_lefts[bus_index - 1] = new_pos

            self._bus_lefts[bus_index] = left
            self._bus_rights[bus_index] = right
            self._clamp_nodes_to_bus_bounds(resized_bus_indices)
            self._layout_width = max(self._layout_width, right + 200)
            self._dirty = True
            self._redraw_canvas()
            return
        if not self._drag_state:
            return
        key, last_x, last_y = self._drag_state
        if not self._dragging_active and not self._drag_threshold_exceeded(cx - last_x, cy - last_y):
            return
        if not self._dragging_active:
            self._dragging_active = True
        node = next((n for n in self._nodes if n.key == key), None)
        if node is None:
            return
        dx = cx - last_x
        dy = cy - last_y
        scale = max(self._zoom, 0.01)
        candidate_x = node.x + dx / scale
        if self._snap_to_grid_var.get():
            candidate_x = self._snap_value(candidate_x)
        candidate_x, guide_x = self._apply_smart_guides(node, candidate_x, self._selected_nodes)
        candidate_x = self._clamp_node_x_to_current_bus_bounds(node, candidate_x)
        node.x = candidate_x
        self._guide_x = guide_x
        self._guide_bus = node.bus_index if guide_x is not None else None
        self._layout_width = max(self._layout_width, node.x + 200)
        base_y = max(self.canvas.winfo_height(), 1) * 0.5 + self._pan_y
        node = next((n for n in self._nodes if n.key == key), None)
        free_y = (cy - base_y) / scale
        if node is not None and self._is_dio_node(node):
            free_y -= DIO_RAIL_OFFSET
        self._drag_free_y[key] = free_y
        self._drag_state = (key, cx, cy)
        self._redraw_canvas()

    def _on_canvas_release(self, _event: tk.Event) -> None:
        """
        NAME
            _on_canvas_release - End drag operation.
        """
        self._gui_debug_log(
            "release.begin",
            drag_state=self._drag_state,
            multi_drag=bool(self._multi_drag),
            bus_drag=self._bus_drag,
            bus_resize=self._bus_resize,
            bus_connector_drag=self._bus_connector_drag,
            dragging_active=self._dragging_active,
        )
        if self._selection_rect is not None:
            x0, y0, x1, y1 = self.canvas.coords(self._selection_rect)
            self.canvas.delete(self._selection_rect)
            self._selection_rect = None
            self._selection_start = None
            self._apply_marquee_selection(x0, y0, x1, y1, additive=True)
            return
        layout_dragged = bool(
            self._dragging_active
            and (
                self._drag_state is not None
                or self._multi_drag is not None
                or self._bus_drag is not None
                or self._bus_resize is not None
                or self._bus_connector_drag is not None
            )
        )
        if self._bus_drag is not None:
            if not self._bus_connectors or all(self._bus_connectors):
                self._reorder_buses_by_y()
        if self._drag_free_y:
            for key, free_y in list(self._drag_free_y.items()):
                node = next((n for n in self._nodes if n.key == key), None)
                if node is None:
                    continue
                if ENABLE_CANNECT_FREE_FLOAT and self._is_cannect_cluster_member(node):
                    node.free_y = free_y
                    node.free_y_relative = False
                else:
                    free_y_for_bus = free_y
                    node.bus_index, node.row = self._nearest_bus_and_row_from_offset(free_y_for_bus)
                    if self._bus_offsets:
                        bus_offset = self._bus_offsets[min(max(node.bus_index, 0), len(self._bus_offsets) - 1)]
                        node.free_y = free_y_for_bus - bus_offset
                    else:
                        node.free_y = free_y_for_bus
            self._drag_free_y.clear()
        dragged_key = self._drag_state[0] if self._drag_state else None
        self._drag_state = None
        self._pan_drag = None
        self._bus_drag = None
        self._bus_resize = None
        self._bus_connector_drag = None
        self._multi_drag = None
        self._drag_undo_pending = False
        self._dragging_active = False
        self._clear_guides()
        if layout_dragged and self._selected_key is not None:
            self._update_details_panel(self._get_selected_node())
        if layout_dragged:
            self._mark_neighbors_stale()
            self._redraw_canvas()
        if dragged_key is not None:
            self._maybe_link_dragged_device_to_cannect(dragged_key)
        self._gui_debug_log("release.end", layout_dragged=layout_dragged, dragged_key=dragged_key)

    def _on_add_bus(self) -> None:
        """
        NAME
            _on_add_bus - Add a parallel bus segment connected to the first.
        """
        self._add_bus_mode = True
        self._pending_bus_after = (
            list(self._selected_buses)[0] if len(self._selected_buses) == BUS_INDEX_FLOOR else None
        )
        self._pending_cannect_direct = self._selected_cannect_direct_key()
        self._pending_bus_island = (
            self._pending_cannect_direct is not None and self._pending_bus_after is None
        )
        messagebox.showinfo(MSG_ADD_BUS_TITLE, MSG_ADD_BUS_PROMPT)

    def _add_bus_at(self, cy: float) -> None:
        """
        NAME
            _add_bus_at - Add a bus segment at a specific canvas Y position.
        """
        height = max(self.canvas.winfo_height(), 1)
        base_y = height * 0.5 + self._pan_y
        offset = cy - base_y
        self._push_undo()
        if not self._bus_offsets:
            self._bus_offsets = [0.0]
        old_bus_count = len(self._bus_offsets)
        if not self._bus_connectors and old_bus_count > BUS_INDEX_FLOOR:
            self._bus_connectors = [BUS_CONNECT_DEFAULT] * (old_bus_count - BUS_INDEX_FLOOR)
        self._ensure_bus_connector_sides(old_bus_count)
        # Preserve insertion order; do not sort so existing buses don't shift.
        if offset not in self._bus_offsets:
            insert_at = None
            if self._pending_bus_after is not None:
                insert_at = min(
                    max(self._pending_bus_after + BUS_INDEX_FLOOR, CANNECT_PORT_ZERO),
                    len(self._bus_offsets),
                )
            if insert_at is None:
                self._bus_offsets.append(offset)
                new_index = len(self._bus_offsets) - BUS_INDEX_FLOOR
                insert_at = new_index
            else:
                self._bus_offsets.insert(insert_at, offset)
                new_index = insert_at
            if old_bus_count > CANNECT_PORT_ZERO:
                if insert_at >= old_bus_count:
                    self._bus_connectors.append(BUS_CONNECT_DEFAULT)
                    self._bus_connector_sides.append(
                        self._default_bus_connector_side(len(self._bus_connectors) - BUS_INDEX_FLOOR)
                    )
                else:
                    self._bus_connectors.insert(insert_at, BUS_CONNECT_DEFAULT)
                    self._bus_connector_sides.insert(
                        insert_at,
                        self._default_bus_connector_side(insert_at),
                    )
            max_node_x = max((n.x for n in self._nodes), default=0.0)
            default_right = max(max_node_x + 200.0, 400.0)
            default_left = 40.0
            if new_index > CANNECT_PORT_ZERO and new_index - BUS_INDEX_FLOOR < len(self._bus_lefts):
                prev_index = new_index - BUS_INDEX_FLOOR
                if prev_index % 2 == 0:
                    connector_x = self._bus_rights[prev_index]
                else:
                    connector_x = self._bus_lefts[prev_index]
                if new_index % 2 == 0:
                    default_left = connector_x
                else:
                    default_right = connector_x
            self._bus_lefts.insert(new_index, default_left)
            self._bus_rights.insert(new_index, default_right)
            if self._pending_bus_after is not None:
                for node in self._nodes:
                    if node.bus_index >= new_index:
                        node.bus_index += BUS_INDEX_FLOOR
                for callout in self._callout_nodes():
                    if callout.callout_target_type == "bus" and callout.callout_target_bus >= new_index:
                        callout.callout_target_bus += BUS_INDEX_FLOOR
                for link in self._can_bus_links:
                    if link.get("bus") is not None and link["bus"] >= new_index:
                        link["bus"] += BUS_INDEX_FLOOR
            if self._pending_bus_island:
                if new_index > CANNECT_PORT_ZERO and new_index - BUS_INDEX_FLOOR < len(self._bus_connectors):
                    self._bus_connectors[new_index - BUS_INDEX_FLOOR] = BUS_CONNECT_DISABLED
                if new_index < len(self._bus_connectors):
                    self._bus_connectors[new_index] = BUS_CONNECT_DISABLED
            self._ensure_bus_connector_sides(len(self._bus_offsets))
            if old_bus_count > CANNECT_PORT_ZERO:
                pivot = max(min(new_index - BUS_INDEX_FLOOR, len(self._bus_connectors) - BUS_INDEX_FLOOR), 0)
                if 0 <= pivot < len(self._bus_connectors):
                    self._set_bus_connector_side(
                        pivot,
                        self._default_bus_connector_side(pivot),
                    )
            effective_cannect_direct = (
                self._pending_cannect_direct
                if self._pending_cannect_direct is not None
                else self._selected_cannect_direct_key()
            )
            if effective_cannect_direct is not None:
                self._maybe_link_new_bus_to_cannect_direct(effective_cannect_direct, new_index)
        self._pending_bus_after = None
        self._pending_cannect_direct = None
        self._pending_bus_island = False
        self._mark_neighbors_stale()
        self._redraw_canvas()

    def _on_add_callout(self) -> None:
        """
        NAME
            _on_add_callout - Add a callout label attached to a bus or node.
        """
        dialog = CalloutDialog(
            self,
            "Add Callout",
            nodes=self._device_nodes(),
            bus_count=len(self._bus_offsets),
        )
        self.wait_window(dialog)
        if not dialog.result:
            return
        self._push_undo()
        data = dialog.result
        bus_index = int(data.get("target_bus", 0))
        row = 1
        x_pos = self._next_x_position()
        if str(data.get("target_type")) == "node":
            target_key = data.get("target_node_key")
            target_node = next((n for n in self._nodes if n.key == target_key), None)
            if target_node is not None:
                bus_index = target_node.bus_index
                row = target_node.row
                x_pos = target_node.x
        node = Node(
            key=self._next_key,
            category="callout",
            label=str(data["text"]),
            can_id=-1,
            node_type="callout",
            x=x_pos,
            row=row,
            bus_index=bus_index,
            scale=1.0,
            callout_text=str(data["text"]),
            callout_target_type=str(data["target_type"]),
            callout_target_bus=int(data.get("target_bus", 0)),
            callout_target_node_key=data.get("target_node_key"),
            callout_target_category=str(data.get("target_node_category", "")),
            callout_target_label=str(data.get("target_node_label", "")),
            callout_target_id=data.get("target_node_id"),
            callout_y=0.0,
            tags=self._normalize_tags(data.get("tags", [])),
        )
        node.callout_y = self._node_center_y_unscaled(node)
        self._next_key += 1
        self._nodes.append(node)
        self._set_single_node_selection(node.key)
        self._redraw_canvas()

    def _on_edit_callout(self) -> None:
        """
        NAME
            _on_edit_callout - Edit the selected callout target/text.
        """
        node = self._get_selected_node()
        if node is None or node.node_type != "callout":
            messagebox.showinfo("Edit Callout", "Select a callout to edit.")
            return
        dialog = CalloutDialog(
            self,
            "Edit Callout",
            nodes=self._device_nodes(),
            bus_count=len(self._bus_offsets),
            initial=node,
        )
        self.wait_window(dialog)
        if not dialog.result:
            return
        self._push_undo()
        data = dialog.result
        node.callout_text = str(data["text"])
        node.label = node.callout_text
        node.callout_target_type = str(data["target_type"])
        node.callout_target_bus = int(data.get("target_bus", 0))
        node.callout_target_node_key = data.get("target_node_key")
        node.callout_target_category = str(data.get("target_node_category", ""))
        node.callout_target_label = str(data.get("target_node_label", ""))
        node.callout_target_id = data.get("target_node_id")
        node.tags = self._normalize_tags(data.get("tags", []))
        self._redraw_canvas()

    def _on_remove_callout(self) -> None:
        """
        NAME
            _on_remove_callout - Remove the selected callout.
        """
        node = self._get_selected_node()
        if node is None or node.node_type != "callout":
            messagebox.showinfo("Remove Callout", "Select a callout to remove.")
            return
        self._push_undo()
        self._nodes = [n for n in self._nodes if n.key != node.key]
        self._selected_key = None
        self._callout_scale_var.set("?")
        self._redraw_canvas()

    def _on_copy(self) -> None:
        """
        NAME
            _on_copy - Copy the current selection into an internal clipboard.
        """
        if not (self._selected_nodes or self._selected_buses):
            messagebox.showinfo("Copy", "Select nodes or buses to copy.")
            return
        nodes = [n for n in self._nodes if n.key in self._selected_nodes]
        buses = sorted(self._selected_buses)
        self._clipboard = {
            "nodes": [self._node_snapshot(n) for n in nodes],
            "buses": [(idx, self._bus_offsets[idx]) for idx in buses if idx < len(self._bus_offsets)],
        }

    def _on_paste(self) -> None:
        """
        NAME
            _on_paste - Paste items from the internal clipboard.
        """
        if not self._clipboard:
            messagebox.showinfo("Paste", "Clipboard is empty.")
            return
        clip_nodes = list(self._clipboard.get("nodes", []))
        clip_buses = list(self._clipboard.get("buses", []))
        if not (clip_nodes or clip_buses):
            return

        existing_ids = {(n.category, n.can_id) for n in self._profile_device_nodes()}
        pending_ids = {
            (n["category"], n["can_id"])
            for n in clip_nodes
            if n.get("node_type", "device") == "device"
        }
        if existing_ids.intersection(pending_ids):
            if not messagebox.askyesno(
                "CAN ID Conflict",
                "One or more pasted nodes share a category/CAN ID with existing nodes.\n\n"
                "Paste anyway?",
            ):
                return

        self._push_undo()
        delta_y = 40.0
        scale = max(self._zoom, 0.01)
        view_center_x = self.canvas.canvasx(max(self.canvas.winfo_width(), 1) / 2) / scale
        clip_xs = [float(n.get("x", 0.0)) for n in clip_nodes if isinstance(n, dict)]
        if clip_xs:
            clip_center_x = (min(clip_xs) + max(clip_xs)) / 2.0
            delta_x = view_center_x - clip_center_x
        else:
            delta_x = 40.0
        bus_map: Dict[int, int] = {}
        new_bus_indices: List[int] = []
        for old_index, offset in clip_buses:
            new_offset = offset + delta_y
            self._bus_offsets.append(new_offset)
            new_index = len(self._bus_offsets) - 1
            bus_map[old_index] = new_index
            new_bus_indices.append(new_index)

        new_nodes: List[int] = []
        node_map: Dict[int, int] = {}
        pending_callout_targets: List[Tuple[Node, Optional[int]]] = []
        for data in clip_nodes:
            new_key = self._next_key
            self._next_key += 1
            node_type = str(data.get("node_type", "device"))
            bus_index = int(data.get("bus_index", 0))
            if bus_index in bus_map:
                bus_index = bus_map[bus_index]
            node = Node(
                key=new_key,
                category=str(data.get("category", "callout")),
                label=str(data.get("label", "")),
                can_id=int(data.get("can_id", -1)),
                node_type=node_type,
                vendor=str(data.get("vendor", "")),
                device_type=str(data.get("device_type", "")),
                motor=str(data.get("motor", "")),
                limits=data.get("limits"),
                terminator=data.get("terminator"),
                x=float(data.get("x", 0.0)) + delta_x,
                row=int(data.get("row", 0)),
                bus_index=bus_index,
                scale=float(data.get("scale", 1.0)),
                callout_text=str(data.get("callout_text", "")),
                callout_target_type=str(data.get("callout_target_type", "node")),
                callout_target_bus=int(data.get("callout_target_bus", 0)),
                callout_target_node_key=data.get("callout_target_node_key"),
                callout_y=float(data.get("callout_y", 0.0)),
                free_y=data.get("free_y"),
                tags=self._normalize_tags(data.get("tags", [])),
            )
            if self._snap_to_grid_var.get():
                node.x = self._snap_value(node.x)
            if node.node_type == "callout":
                node.callout_y = self._node_center_y_unscaled(node)
                if node.callout_target_type == "bus" and node.callout_target_bus in bus_map:
                    node.callout_target_bus = bus_map[node.callout_target_bus]
                pending_callout_targets.append((node, node.callout_target_node_key))
            self._nodes.append(node)
            new_nodes.append(node.key)
            node_map[int(data.get("key", new_key))] = node.key

        for node, old_target in pending_callout_targets:
            if old_target in node_map:
                node.callout_target_node_key = node_map[old_target]

        if new_nodes:
            max_x = max((n.x for n in self._nodes if n.node_type == "device"), default=0.0)
            self._layout_width = max(self._layout_width, max_x + 200)

        self._selected_nodes = set(new_nodes)
        self._selected_buses = set(new_bus_indices)
        self._sync_selection_state()
        self._mark_neighbors_stale()
        self._redraw_canvas()

    def _node_snapshot(self, node: Node) -> Dict[str, object]:
        """
        NAME
            _node_snapshot - Capture node data for clipboard transfer.
        """
        return {
            "key": node.key,
            "node_type": node.node_type,
            "category": node.category,
            "label": node.label,
            "can_id": node.can_id,
            "vendor": node.vendor,
            "device_type": node.device_type,
            "motor": node.motor,
            "limits": node.limits,
            "terminator": node.terminator,
            "x": node.x,
            "row": node.row,
            "bus_index": node.bus_index,
            "scale": node.scale,
            "callout_text": node.callout_text,
            "callout_target_type": node.callout_target_type,
            "callout_target_bus": node.callout_target_bus,
            "callout_target_node_key": node.callout_target_node_key,
            "callout_target_category": node.callout_target_category,
            "callout_target_label": node.callout_target_label,
            "callout_target_id": node.callout_target_id,
            "callout_y": self._node_center_y_unscaled(node)
            if node.node_type == "callout"
            else node.callout_y,
            "free_y": self._node_center_y_unscaled(node),
            "tags": list(node.tags or []),
        }

    def _on_export_pdf(self) -> None:
        """
        NAME
            _on_export_pdf - Export the current diagram to a PDF file.
        """
        self._export_pdf(print_after=False, path_override=None)

    def _print_pdf_shortcut(self) -> None:
        """
        NAME
            _print_pdf_shortcut - Export and queue the diagram PDF for printing.
        """
        self._export_pdf(print_after=True, path_override="")

    def _windows_pdf_print_handler_available(self) -> bool:
        """
        NAME
            _windows_pdf_print_handler_available - Return whether Windows has a print verb for .pdf.

        RETURNS
            True when the current .pdf association exposes a shell print command.
        """
        if not sys.platform.startswith("win"):
            return False
        try:
            import winreg
        except Exception:
            return False

        prog_id = None
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_REGKEY_CURRENT_USER_USERCHOICE) as key:
                prog_id = winreg.QueryValueEx(key, WINDOWS_REGVALUE_PROGID)[0]
        except Exception:
            prog_id = None
        if not prog_id:
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, WINDOWS_REGKEY_CLASSES_ROOT_PDF) as key:
                    prog_id = winreg.QueryValue(key, EMPTY_STRING)
            except Exception:
                prog_id = None
        if not prog_id:
            return False
        try:
            with winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                prog_id + WINDOWS_REGKEY_SHELL_PRINT_SUFFIX,
            ):
                return True
        except Exception:
            return False

    def _print_or_open_pdf(self, path: str, printed_message: str) -> None:
        """
        NAME
            _print_or_open_pdf - Print a PDF when possible, otherwise open it for manual printing.

        PARAMETERS
            path: PDF file path.
            printed_message: Success message format string with one '{}' placeholder for the path.
        """
        import os

        if not self._windows_pdf_print_handler_available():
            os.startfile(path)
            messagebox.showinfo("Print", MSG_PRINT_NO_HANDLER)
            return
        try:
            os.startfile(path, "print")
            messagebox.showinfo("Printed", printed_message.format(path))
        except OSError as exc:
            if getattr(exc, "winerror", None) == WINDOWS_NO_ASSOCIATION_ERROR:
                try:
                    os.startfile(path)
                    messagebox.showinfo("Print", MSG_PRINT_OPENED_MANUAL)
                    return
                except Exception:
                    pass
            messagebox.showerror(
                "Print Failed",
                f"Saved PDF but failed to print:\n{exc}",
            )
        except Exception as exc:
            messagebox.showerror(
                "Print Failed",
                f"Saved PDF but failed to print:\n{exc}",
            )

    def _export_pdf(self, print_after: bool, path_override: Optional[str]) -> None:
        """
        NAME
            _export_pdf - Export the current diagram to a PDF file.

        PARAMETERS
            print_after: When true, queue the exported PDF for printing.
            path_override: If set, use this path. Empty string means temp file.
        """
        try:
            from reportlab.pdfgen import canvas as pdfcanvas  # type: ignore
            from reportlab.lib.colors import Color  # type: ignore
            from reportlab.pdfbase import pdfmetrics  # type: ignore
        except Exception:
            messagebox.showerror(
                "Missing Dependency",
                "PDF export requires the 'reportlab' package.\n\n"
                "Install with: pip install reportlab",
            )
            return
        path = None
        if path_override is None:
            path = filedialog.asksaveasfilename(
                title="Export PDF",
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf"), ("All files", "*.*")],
            )
        elif path_override == "":
            import tempfile

            fd, temp_path = tempfile.mkstemp(
                prefix=TEMP_PRINT_DIAGRAM_PREFIX,
                suffix=PDF_FILE_EXTENSION,
            )
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
            path = temp_path
        else:
            path = path_override
        if not path:
            return

        # Ensure draw state is up to date
        self._redraw_canvas()

        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        scale = self._zoom
        render_scene = self.__dict__.get("_render_scene", {})
        draw_state = self.__dict__.get("_draw_state", {})
        show_can = self._connection_filter_allows(TOPOLOGY_FILTER_CAN)
        show_dio = self._connection_filter_allows(TOPOLOGY_FILTER_DIO)
        show_virtual = self._connection_filter_allows(TOPOLOGY_FILTER_VIRTUAL)
        show_power = self._connection_filter_allows(TOPOLOGY_FILTER_POWER)
        show_groups = bool(self.__dict__.get("_show_group_overlays_var", None) and self._show_group_overlays_var.get())
        groups = self._bridge_groups() if "_root_extras" in self.__dict__ else []
        bus_ys = list(draw_state.get("bus_ys", []))
        eff_lefts = list(draw_state.get("bus_lefts", self._bus_lefts))
        eff_rights = list(draw_state.get("bus_rights", self._bus_rights))
        node_bounds = dict(render_scene.get("node_bounds", self._node_bounds))
        node_centers = dict(render_scene.get("node_centers", {}))
        ethernet_ports = dict(render_scene.get("ethernet_ports", {}))
        can_ports = dict(render_scene.get("can_ports", {}))
        max_node_x = max((n.x for n in self._nodes), default=0.0)
        min_left = min(eff_lefts, default=40.0)
        max_right = max(eff_rights, default=max_node_x + 200.0)
        total_width = max(
            width,
            int(max_right * scale),
            int(max((bounds[2] for bounds in node_bounds.values()), default=width)),
        )
        base_y = height * 0.5 + self._pan_y
        box_h = self._box_h * scale
        span = box_h + 60 * scale
        min_y = min((y - span for y in bus_ys), default=0.0)
        max_y = max((y + span for y in bus_ys), default=height)
        for bounds in node_bounds.values():
            min_y = min(min_y, bounds[1])
            max_y = max(max_y, bounds[3])
        for callout in self._callout_nodes():
            bus_index = min(max(callout.bus_index, 0), max(len(bus_ys) - 1, 0))
            bus_y = bus_ys[bus_index] if bus_ys else base_y
            box_w_callout, box_h_callout = self._node_box_dims(callout, scale)
            if callout.key in self._drag_free_y:
                cy = base_y + self._drag_free_y[callout.key] * scale
                y0 = cy - box_h_callout / 2
                y1 = cy + box_h_callout / 2
            elif callout.free_y is not None:
                cy = base_y + self._node_center_y_unscaled(callout) * scale
                y0 = cy - box_h_callout / 2
                y1 = cy + box_h_callout / 2
            else:
                y0, y1 = self._node_box_y(callout, bus_y, box_h_callout, scale)
            min_y = min(min_y, y0)
            max_y = max(max_y, y1)
        margin = 20.0
        min_y -= margin
        max_y += margin
        # Fit to 11x9 inch landscape page (in points)
        page_w = 11 * 72
        page_h = 9 * 72
        margin = 36.0
        content_w = max(total_width, 1)
        content_h = max(max_y - min_y, 1)
        fit_scale = min(
            (page_w - margin * 2) / content_w,
            (page_h - margin * 2) / content_h,
        )

        def _to_pdf(x: float, y: float) -> Tuple[float, float]:
            px = margin + (x - 0.0) * fit_scale
            py = margin + (y - min_y) * fit_scale
            return px, page_h - py

        def _wrap_pdf_lines(text: str, size: int, max_w: float) -> List[str]:
            if max_w <= 0:
                return [text]
            words = text.split()
            if not words:
                return [""]
            lines: List[str] = []
            current = words[0]
            for word in words[1:]:
                test = f"{current} {word}"
                if pdfmetrics.stringWidth(test, "Helvetica", size) <= max_w:
                    current = test
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
            final_lines: List[str] = []
            for line in lines:
                if pdfmetrics.stringWidth(line, "Helvetica", size) <= max_w:
                    final_lines.append(line)
                    continue
                chunk = ""
                for ch in line:
                    test = chunk + ch
                    if pdfmetrics.stringWidth(test, "Helvetica", size) <= max_w:
                        chunk = test
                    else:
                        if chunk:
                            final_lines.append(chunk)
                        chunk = ch
                if chunk:
                    final_lines.append(chunk)
            return final_lines

        def _fit_pdf_font(
            text: str, max_w: float, max_h: float, base_size: float
        ) -> Tuple[int, float, float, float, List[str]]:
            max_w = max_w * 0.88
            max_h = max_h * 0.82
            size = max(6, int(base_size))
            while size >= 6:
                ascent = pdfmetrics.getAscent("Helvetica") * size / 1000.0
                descent = abs(pdfmetrics.getDescent("Helvetica") * size / 1000.0)
                ascent_adj = ascent * 1.05
                descent_adj = descent * 1.2
                line_h = (ascent_adj + descent_adj) * 1.1
                lines = _wrap_pdf_lines(text, size, max_w)
                total_h = line_h * len(lines)
                if total_h > max_h:
                    size -= 1
                    continue
                if total_h <= max_h:
                    return size, line_h, ascent_adj, descent_adj, lines
                size -= 1
            ascent = pdfmetrics.getAscent("Helvetica") * 6 / 1000.0
            descent = abs(pdfmetrics.getDescent("Helvetica") * 6 / 1000.0)
            ascent_adj = ascent * 1.05
            descent_adj = descent * 1.2
            return 6, (ascent_adj + descent_adj) * 1.1, ascent_adj, descent_adj, _wrap_pdf_lines(
                text, 6, max_w
            )

        def _fit_lines_exact(
            text: str, max_w: float, max_h: float, base_size: float
        ) -> Tuple[int, float, float, List[str]]:
            """
            NAME
                _fit_lines_exact - Fit lines strictly within a height/width box.
            """
            size = max(6, int(base_size))
            while size >= 6:
                lines = _wrap_pdf_lines(text, size, max_w)
                ascent = pdfmetrics.getAscent("Helvetica") * size / 1000.0
                descent = abs(pdfmetrics.getDescent("Helvetica") * size / 1000.0)
                line_h = (ascent + descent) * 1.2
                if line_h * len(lines) <= max_h:
                    return size, line_h, ascent, lines
                size -= 1
            ascent = pdfmetrics.getAscent("Helvetica") * 6 / 1000.0
            descent = abs(pdfmetrics.getDescent("Helvetica") * 6 / 1000.0)
            return 6, (ascent + descent) * 1.2, ascent, _wrap_pdf_lines(text, 6, max_w)

        def _pdf_color(hex_color: str) -> Color:
            if not hex_color.startswith("#") or len(hex_color) != 7:
                return Color(0.0, 0.0, 0.0)
            try:
                r = int(hex_color[1:3], 16) / 255.0
                g = int(hex_color[3:5], 16) / 255.0
                b = int(hex_color[5:7], 16) / 255.0
            except ValueError:
                return Color(0.0, 0.0, 0.0)
            return Color(r, g, b)

        def _draw_pdf_polygon(points: List[Tuple[float, float]], fill: str, outline: str) -> None:
            path_obj = c.beginPath()
            px0, py0 = _to_pdf(points[0][0], points[0][1])
            path_obj.moveTo(px0, py0)
            for x, y in points[1:]:
                px, py = _to_pdf(x, y)
                path_obj.lineTo(px, py)
            path_obj.close()
            c.setFillColor(_pdf_color(fill))
            c.setStrokeColor(_pdf_color(outline))
            c.drawPath(path_obj, fill=1, stroke=1)

        def _draw_pdf_chamfer_rect(
            x0: float, y0: float, x1: float, y1: float, fill: str, outline: str
        ) -> None:
            chamfer = min(6.0, abs(x1 - x0) * 0.2, abs(y1 - y0) * 0.2)
            points = [
                (x0 + chamfer, y0),
                (x1 - chamfer, y0),
                (x1, y0 + chamfer),
                (x1, y1 - chamfer),
                (x1 - chamfer, y1),
                (x0 + chamfer, y1),
                (x0, y1 - chamfer),
                (x0, y0 + chamfer),
            ]
            _draw_pdf_polygon(points, fill, outline)

        def _draw_pdf_hexagon(
            x0: float, y0: float, x1: float, y1: float, fill: str, outline: str
        ) -> None:
            inset = min(10.0, abs(x1 - x0) * 0.25)
            points = [
                (x0 + inset, y0),
                (x1 - inset, y0),
                (x1, (y0 + y1) / 2),
                (x1 - inset, y1),
                (x0 + inset, y1),
                (x0, (y0 + y1) / 2),
            ]
            _draw_pdf_polygon(points, fill, outline)

        def _draw_pdf_diamond(
            x0: float, y0: float, x1: float, y1: float, fill: str, outline: str
        ) -> None:
            cx = (x0 + x1) / 2.0
            cy = (y0 + y1) / 2.0
            points = [
                (cx, y0),
                (x1, cy),
                (cx, y1),
                (x0, cy),
            ]
            _draw_pdf_polygon(points, fill, outline)

        def _draw_pdf_tabbed_rect(
            x0: float, y0: float, x1: float, y1: float, fill: str, outline: str
        ) -> None:
            tab_w = min(40.0, abs(x1 - x0) * 0.5)
            tab_h = min(10.0, abs(y1 - y0) * 0.2)
            cx = (x0 + x1) / 2.0
            points = [
                (x0, y0),
                (x1, y0),
                (x1, y1),
                (cx + tab_w / 2.0, y1),
                (cx + tab_w / 2.0, y1 + tab_h),
                (cx - tab_w / 2.0, y1 + tab_h),
                (cx - tab_w / 2.0, y1),
                (x0, y1),
            ]
            _draw_pdf_polygon(points, fill, outline)

        def _draw_pdf_device_shape(
            kind: str, x0: float, y0: float, x1: float, y1: float, fill: str, outline: str
        ) -> None:
            if kind == "motor":
                _draw_pdf_chamfer_rect(x0, y0, x1, y1, fill, outline)
            elif kind == "sensor":
                _draw_pdf_hexagon(x0, y0, x1, y1, fill, outline)
            elif kind == "power":
                _draw_pdf_diamond(x0, y0, x1, y1, fill, outline)
            elif kind == "controller":
                _draw_pdf_tabbed_rect(x0, y0, x1, y1, fill, outline)
            else:
                _draw_pdf_chamfer_rect(x0, y0, x1, y1, fill, outline)

        def _draw_pdf_error_badge(cx: float, cy: float) -> None:
            r = 7.0
            x0, y0 = _to_pdf(cx - r, cy - r)
            x1, y1 = _to_pdf(cx + r, cy + r)
            c.setFillColor(_pdf_color("#cc0000"))
            c.setStrokeColor(_pdf_color("#aa0000"))
            c.ellipse(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), fill=1, stroke=1)
            c.setFillColor(_pdf_color("#ffffff"))
            c.setFont("Helvetica-Bold", 9 * fit_scale)
            tx, ty = _to_pdf(cx, cy - 0.5)
            c.drawCentredString(tx, ty, "!")

        def _draw_pdf_warning_badge(cx: float, cy: float) -> None:
            r = 8.0
            points = [
                (cx, cy - r),
                (cx + r, cy + r),
                (cx - r, cy + r),
            ]
            _draw_pdf_polygon(points, "#f5c542", "#c28b00")
            c.setFillColor(_pdf_color("#5a3b00"))
            c.setFont("Helvetica-Bold", 9 * fit_scale)
            tx, ty = _to_pdf(cx, cy + 1)
            c.drawCentredString(tx, ty, "!")

        def _draw_pdf_group_overlays() -> None:
            if not show_groups or not groups:
                return
            palette = ["#1f6feb", "#f97316", "#16a34a", "#a855f7", "#0ea5e9", "#e11d48"]
            label_bounds: Dict[str, Tuple[float, float, float, float]] = {}
            for node in self._device_nodes():
                bounds = node_bounds.get(node.key)
                if bounds is not None:
                    label_bounds[node.label] = bounds
            if not label_bounds:
                return
            pad = 10.0
            for idx, group in enumerate(groups):
                if not isinstance(group, dict):
                    continue
                name = str(group.get("name", "")).strip()
                if not name:
                    continue
                members = group.get("members", []) or []
                bounds_list = []
                for member in members:
                    label = bridge_group_member_label(member) if isinstance(member, dict) else member
                    if not isinstance(label, str):
                        continue
                    bounds = label_bounds.get(label.strip())
                    if bounds:
                        bounds_list.append(bounds)
                if not bounds_list:
                    continue
                x0 = min(b[0] for b in bounds_list) - pad
                y0 = min(b[1] for b in bounds_list) - pad
                x1 = max(b[2] for b in bounds_list) + pad
                y1 = max(b[3] for b in bounds_list) + pad
                color = palette[idx % len(palette)]
                rx0, ry0 = _to_pdf(x0, y0)
                rx1, ry1 = _to_pdf(x1, y1)
                c.setStrokeColor(_pdf_color(color))
                c.setLineWidth(3 * fit_scale)
                c.rect(min(rx0, rx1), min(ry0, ry1), abs(rx1 - rx0), abs(ry1 - ry0), fill=0, stroke=1)
                label_font = max(10, int(12 * scale * fit_scale))
                label_pad_x = max(6.0, 6.0 * scale)
                label_h = max(18.0, 18.0 * scale)
                label_w = max(36.0, len(name) * max(7.5, 8.5 * scale))
                lx0 = x0 + 4.0
                ly1 = y0 - 4.0
                ly0 = ly1 - label_h
                lx1 = lx0 + label_w
                lrx0, lry0 = _to_pdf(lx0, ly0)
                lrx1, lry1 = _to_pdf(lx1, ly1)
                c.setFillColor(_pdf_color("#ffffff"))
                c.setStrokeColor(_pdf_color(color))
                c.setLineWidth(1 * fit_scale)
                c.rect(min(lrx0, lrx1), min(lry0, lry1), abs(lrx1 - lrx0), abs(lry1 - lry0), fill=1, stroke=1)
                c.setFillColor(_pdf_color(color))
                c.setFont("Helvetica", label_font)
                text_x, text_y = _to_pdf(lx0 + label_pad_x, ly0 + 4.0)
                c.drawString(text_x, text_y, name)

        c = pdfcanvas.Canvas(path, pagesize=(page_w, page_h))
        gray = Color(0.27, 0.27, 0.27)

        if show_can:
            turn_radius = max(8.0, 18 * scale)
            c.setStrokeColor(gray)
            c.setLineWidth(4 * fit_scale)
            for idx, bus_y in enumerate(bus_ys):
                seg_left = eff_lefts[idx] * scale
                seg_right = eff_rights[idx] * scale
                if idx % 2 == 0:
                    start_x, end_x = seg_left, seg_right
                else:
                    start_x, end_x = seg_right, seg_left
                x0, y0 = _to_pdf(start_x, bus_y)
                x1, y1 = _to_pdf(end_x, bus_y)
                c.line(x0, y0, x1, y1)
                if idx + 1 < len(bus_ys):
                    next_y = bus_ys[idx + 1]
                    side = self._bus_connector_side(idx)
                    connector_x = seg_right if side == BUS_CONNECT_SIDE_RIGHT else seg_left
                    offset = turn_radius if side == BUS_CONNECT_SIDE_RIGHT else -turn_radius
                    path_obj = c.beginPath()
                    p0 = _to_pdf(connector_x, bus_y)
                    p1 = _to_pdf(connector_x + offset, bus_y + turn_radius)
                    p2 = _to_pdf(connector_x + offset, next_y - turn_radius)
                    p3 = _to_pdf(connector_x, next_y)
                    path_obj.moveTo(p0[0], p0[1])
                    path_obj.curveTo(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1])
                    c.setLineWidth(5 * fit_scale)
                    c.drawPath(path_obj)
                    c.setLineWidth(4 * fit_scale)

        dup_keys: set[Tuple[str, str, int]] = set()
        key_counts: Dict[Tuple[str, str, int], int] = {}
        numeric_counts: Dict[int, int] = {}
        for node in self._device_nodes():
            key = self._dup_key_for_node(node)
            if key is None:
                continue
            key_counts[key] = key_counts.get(key, 0) + 1
            numeric_counts[key[2]] = numeric_counts.get(key[2], 0) + 1
        dup_keys = {key for key, count in key_counts.items() if count > 1}
        warn_ids = {can_id for can_id, count in numeric_counts.items() if count > 1}

        linked_devices = {link.get("device") for link in self._cannect_device_links}
        for node in self._device_nodes():
            bounds = node_bounds.get(node.key)
            center_entry = node_centers.get(node.key)
            if bounds is None or center_entry is None:
                continue
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys) - 1, 0))
            bus_y = bus_ys[bus_index] if bus_ys else base_y
            node_bus_y = center_entry[1]
            node_scale = max(0.6, min(2.0, node.scale))
            x0, y0, x1, y1 = bounds
            node_x = (x0 + x1) / 2.0
            node_box_w = x1 - x0
            allow_trunk = (not self._is_swyft_node(node)) or (node.category == "cannect_inject")
            if node.key not in linked_devices and allow_trunk and not self._is_dio_node(node):
                if node_bus_y >= bus_y:
                    x0l, y0l = _to_pdf(node_x, bus_y)
                    x1l, y1l = _to_pdf(node_x, y0)
                else:
                    x0l, y0l = _to_pdf(node_x, y1)
                    x1l, y1l = _to_pdf(node_x, bus_y)
                c.setLineWidth(2 * fit_scale)
                c.line(x0l, y0l, x1l, y1l)

            shape_kind = self._shape_kind_for_node(node)
            fill = self._fill_color_for_node(node)
            outline = self._outline_color_for_node(node)
            _draw_pdf_device_shape(shape_kind, x0, y0, x1, y1, fill, outline)

            text = node.display_text_pdf()
            rx0, ry0 = _to_pdf(x0, y0)
            rx1, ry1 = _to_pdf(x1, y1)
            left = min(rx0, rx1) + 3
            right = max(rx0, rx1) - 3
            top = max(ry0, ry1) - 3
            bottom = min(ry0, ry1) + 3
            avail_w = max(1.0, right - left)
            avail_h = max(1.0, top - bottom)
            pdf_font, line_h, ascent, lines = _fit_lines_exact(
                text, avail_w, avail_h, 9 * scale * node_scale * fit_scale
            )
            c.setFillColor(_pdf_color(self._text_color_for_fill(fill)))
            c.setFont("Helvetica", pdf_font)
            y = bottom + avail_h - ascent
            for line in lines:
                c.drawCentredString((left + right) / 2, y, line)
                y -= line_h

            if self._is_swyft_node(node):
                cy = (y0 + y1) / 2.0
                ports: Dict[str, Tuple[float, float]] = {}
                if node.category == "cannect_inject":
                    ports["out"] = (x1, cy)
                    ports["power_in"] = (node_x, y1)
                else:
                    ports["in"] = (x0, cy)
                    ports["out"] = (x1, cy)
                    ports["power_out"] = (node_x, y1)
                ports = ethernet_ports.get(node.key, ports)
                port_w = 6 * scale
                port_h = 10 * scale
                for port_name, (px, py) in ports.items():
                    if port_name.startswith("power_"):
                        continue
                    r0 = _to_pdf(px - port_w / 2, py - port_h / 2)
                    r1 = _to_pdf(px + port_w / 2, py + port_h / 2)
                    c.setFillColor(_pdf_color("#4aa3df"))
                    c.setStrokeColor(_pdf_color("#1c6ba8"))
                    c.rect(
                        min(r0[0], r1[0]),
                        min(r0[1], r1[1]),
                        abs(r1[0] - r0[0]),
                        abs(r1[1] - r0[1]),
                        fill=1,
                        stroke=1,
                    )
                port_map = can_ports.get(node.key, {})
                if port_map:
                    for port_idx, (px, _py) in sorted(port_map.items()):
                        p0 = _to_pdf(px - 3 * scale, y0)
                        p1 = _to_pdf(px - 3 * scale, y0 - 10 * scale)
                        p2 = _to_pdf(px + 3 * scale, y0)
                        p3 = _to_pdf(px + 3 * scale, y0 - 10 * scale)
                        c.setStrokeColor(_pdf_color("#2f7a2f"))
                        c.setLineWidth(2 * fit_scale)
                        c.line(p0[0], p0[1], p1[0], p1[1])
                        c.line(p2[0], p2[1], p3[0], p3[1])
                        c.setFillColor(_pdf_color("#2f7a2f"))
                        c.setFont("Helvetica", max(6, int(7 * scale * fit_scale)))
                        tpos = _to_pdf(px, y0 - 12 * scale)
                        c.drawCentredString(tpos[0], tpos[1], f"C{port_idx}")
                power_text = "Power In" if node.category == "cannect_inject" else "Power Out"
                power_key = "power_in" if node.category == "cannect_inject" else "power_out"
                power_pos = ports.get(power_key)
                if power_pos is not None:
                    c.setFillColor(_pdf_color("#555555"))
                    c.setFont("Helvetica", max(6, int(7 * scale * fit_scale)))
                    tpos = _to_pdf(power_pos[0], power_pos[1] + 10 * scale)
                    c.drawCentredString(tpos[0], tpos[1], power_text)

            dup_key = self._dup_key_for_node(node)
            if self._show_warn_badges_var.get() and (
                dup_key in dup_keys or (dup_key and dup_key[2] in warn_ids)
            ):
                badge_x = min(x1 + 12, max_right - 8)
                badge_y = max(y0 - 12, min_y + 8)
                p0 = _to_pdf(x1, y0)
                p1 = _to_pdf(badge_x - 6, badge_y + 6)
                c.setStrokeColor(_pdf_color("#444444"))
                c.setLineWidth(1 * fit_scale)
                c.line(p0[0], p0[1], p1[0], p1[1])
                if dup_key in dup_keys:
                    _draw_pdf_error_badge(badge_x, badge_y)
                else:
                    _draw_pdf_warning_badge(badge_x, badge_y)

        node_by_key = {node.key: node for node in self._device_nodes()}
        _draw_pdf_group_overlays()
        if show_can and ENABLE_CANNECT_BUS_LINKS:
            for link in self._can_bus_links:
                node_key = link.get("node")
                bus_index = link.get("bus")
                port = link.get("port", 1)
                if node_key not in can_ports:
                    continue
                if not isinstance(bus_index, int) or bus_index < 0 or bus_index >= len(bus_ys):
                    continue
                port_pos = can_ports[node_key].get(int(port))
                if not port_pos:
                    continue
                px, py = port_pos
                bus_y = bus_ys[bus_index]
                p0 = _to_pdf(px, py)
                p1 = _to_pdf(px, bus_y)
                c.setStrokeColor(_pdf_color("#2f7a2f"))
                c.setLineWidth(2 * fit_scale)
                c.line(p0[0], p0[1], p1[0], p1[1])

        if show_can:
            for link in self._cannect_device_links:
                node_key = link.get("node")
                device_key = link.get("device")
                port = link.get("port", 1)
                if node_key not in can_ports or device_key not in node_bounds:
                    continue
                port_pos = can_ports[node_key].get(int(port))
                if not port_pos:
                    continue
                px, py = port_pos
                dx0, dy0, dx1, dy1 = node_bounds[device_key]
                tx = (dx0 + dx1) / 2.0
                ty = dy0
                p0 = _to_pdf(px, py)
                p1 = _to_pdf(tx, ty)
                c.setStrokeColor(_pdf_color("#2f7a2f"))
                c.setLineWidth(LINK_LINE_WIDTH * fit_scale)
                c.line(p0[0], p0[1], p1[0], p1[1])

        if show_power:
            for link in self._power_links:
                a_key = link.get(KEY_LINK_A)
                b_key = link.get(KEY_LINK_B)
                if a_key not in node_centers or b_key not in node_centers:
                    continue
                a_bounds = node_bounds.get(a_key)
                b_bounds = node_bounds.get(b_key)
                if a_bounds:
                    ax = (a_bounds[0] + a_bounds[2]) / 2.0
                    ay = (a_bounds[1] + a_bounds[3]) / 2.0
                else:
                    ax, ay = node_centers[a_key]
                if b_bounds:
                    bx = (b_bounds[0] + b_bounds[2]) / 2.0
                    by = (b_bounds[1] + b_bounds[3]) / 2.0
                else:
                    bx, by = node_centers[b_key]
                p0 = _to_pdf(ax, ay)
                p1 = _to_pdf(bx, by)
                c.setStrokeColor(_pdf_color(POWER_LINE_COLOR))
                c.setLineWidth(LINK_LINE_WIDTH * fit_scale)
                c.line(p0[0], p0[1], p1[0], p1[1])

        if show_virtual:
            for link in self._attachment_links:
                host_key = link.get(KEY_LINK_DEVICE)
                attach_key = link.get(KEY_LINK_ATTACHMENT)
                if host_key not in node_centers or attach_key not in node_centers:
                    continue
                host_node = node_by_key.get(host_key)
                attach_node = node_by_key.get(attach_key)
                if host_node and self._is_dio_node(host_node):
                    continue
                if attach_node and self._is_dio_node(attach_node):
                    if host_node and host_node.category == CATEGORY_ROBORIO:
                        continue
                if attach_node and self._is_dio_node(attach_node) and host_node is None:
                    continue
                host_bounds = node_bounds.get(host_key)
                attach_bounds = node_bounds.get(attach_key)
                if host_bounds:
                    hx = (host_bounds[0] + host_bounds[2]) / 2.0
                    hy = (host_bounds[1] + host_bounds[3]) / 2.0
                else:
                    hx, hy = node_centers[host_key]
                if attach_bounds:
                    ax = (attach_bounds[0] + attach_bounds[2]) / 2.0
                    ay = (attach_bounds[1] + attach_bounds[3]) / 2.0
                else:
                    ax, ay = node_centers[attach_key]
                p0 = _to_pdf(hx, hy)
                p1 = _to_pdf(ax, ay)
                c.setStrokeColor(_pdf_color(ATTACH_LINE_COLOR))
                c.setLineWidth(LINK_LINE_WIDTH * fit_scale)
                try:
                    c.setDash(ATTACH_LINK_DASH[0] * fit_scale, ATTACH_LINK_DASH[1] * fit_scale)
                except Exception:
                    pass
                c.line(p0[0], p0[1], p1[0], p1[1])
                c.setDash()

        if show_dio:
            for link in self._dio_wiring_links:
                robo_key = link.get(KEY_LINK_ROBORIO)
                dev_key = link.get(KEY_LINK_DEVICE)
                if robo_key not in node_centers or dev_key not in node_centers:
                    continue
                robo_bounds = node_bounds.get(robo_key)
                if robo_bounds:
                    rx = (robo_bounds[0] + robo_bounds[2]) / 2.0
                    ry = robo_bounds[1]
                else:
                    rx, ry = node_centers[robo_key]
                dev_bounds = node_bounds.get(dev_key)
                if dev_bounds:
                    dx = (dev_bounds[0] + dev_bounds[2]) / 2.0
                    dy = dev_bounds[1]
                else:
                    dx, dy = node_centers[dev_key]
                p0 = _to_pdf(rx, ry)
                p1 = _to_pdf(dx, dy)
                c.setStrokeColor(_pdf_color(WIRE_LINE_COLOR))
                c.setLineWidth(LINK_LINE_WIDTH * fit_scale)
                try:
                    c.setDash(DIO_WIRE_DASH[0] * fit_scale, DIO_WIRE_DASH[1] * fit_scale)
                except Exception:
                    pass
                c.line(p0[0], p0[1], p1[0], p1[1])
                c.setDash()

        if show_virtual:
            for a, b in self._ethernet_links:
                if a not in ethernet_ports or b not in ethernet_ports:
                    continue
                if a not in node_centers or b not in node_centers:
                    continue
                ax, _ = node_centers[a]
                bx, _ = node_centers[b]
                ports_a = ethernet_ports[a]
                ports_b = ethernet_ports[b]
                if "in" in ports_a and "out" in ports_a:
                    pa = ports_a["in"] if bx < ax else ports_a["out"]
                else:
                    pa = ports_a.get("out") or ports_a.get("in")
                if "in" in ports_b and "out" in ports_b:
                    pb = ports_b["in"] if ax < bx else ports_b["out"]
                else:
                    pb = ports_b.get("out") or ports_b.get("in")
                if not pa or not pb:
                    continue
                p0 = _to_pdf(pa[0], pa[1])
                p1 = _to_pdf(pb[0], pb[1])
                c.setStrokeColor(_pdf_color("#1c6ba8"))
                c.setLineWidth(2 * fit_scale)
                try:
                    c.setDash(
                        ETHERNET_DEVICE_DASH[0] * fit_scale,
                        ETHERNET_DEVICE_DASH[1] * fit_scale,
                        ETHERNET_DEVICE_DASH[2] * fit_scale,
                        ETHERNET_DEVICE_DASH[3] * fit_scale,
                    )
                except Exception:
                    pass
                c.line(p0[0], p0[1], p1[0], p1[1])
                try:
                    c.setDash()
                except Exception:
                    pass

        for callout in self._callout_nodes():
            cx = callout.x * scale
            bus_index = min(max(callout.bus_index, 0), max(len(bus_ys) - 1, 0))
            bus_y = bus_ys[bus_index] if bus_ys else base_y
            box_w, box_h = self._node_box_dims(callout, scale)
            y0, y1 = self._node_box_y(callout, bus_y, box_h, scale)
            cy = (y0 + y1) / 2.0
            x0 = cx - box_w / 2
            x1 = cx + box_w / 2
            if (
                callout.callout_target_type == "node"
                and callout.callout_target_node_key in node_centers
            ):
                tx, ty = node_centers[callout.callout_target_node_key]
            else:
                bus_index = min(
                    max(callout.callout_target_bus, 0), max(len(bus_ys) - 1, 0)
                )
                ty = bus_ys[bus_index] if bus_ys else base_y
                tx = cx
            x0l, y0l = _to_pdf(cx, cy)
            x1l, y1l = _to_pdf(tx, ty)
            c.setStrokeColor(Color(0.4, 0.4, 0.4))
            c.setLineWidth(2 * fit_scale)
            c.line(x0l, y0l, x1l, y1l)
            rx0, ry0 = _to_pdf(x0, y0)
            rx1, ry1 = _to_pdf(x1, y1)
            c.setFillColor(_pdf_color("#fffbe6"))
            c.setStrokeColor(_pdf_color("#666666"))
            c.rect(min(rx0, rx1), min(ry0, ry1), abs(rx1 - rx0), abs(ry1 - ry0), fill=1)
            left = min(rx0, rx1) + 3
            right = max(rx0, rx1) - 3
            top = max(ry0, ry1) - 3
            bottom = min(ry0, ry1) + 3
            avail_w = max(1.0, right - left)
            avail_h = max(1.0, top - bottom)
            node_scale = max(0.6, min(2.0, callout.scale))
            pdf_font, line_h, ascent, lines = _fit_lines_exact(
                callout.callout_text, avail_w, avail_h, 9 * scale * node_scale * fit_scale
            )
            c.setFillColor(Color(0, 0, 0))
            c.setFont("Helvetica", pdf_font)
            y = bottom + avail_h - ascent
            for line in lines:
                c.drawCentredString((left + right) / 2, y, line)
                y -= line_h

        c.showPage()
        c.save()
        if print_after:
            self._print_or_open_pdf(path, MSG_PRINTED_DIAGRAM)

            def _cleanup() -> None:
                try:
                    Path(path).unlink()
                except Exception:
                    pass

            self.after(TEMP_PRINT_CLEANUP_DELAY_MS, _cleanup)
        else:
            messagebox.showinfo("Exported", f"Wrote PDF to {path}")

    def _print_node_list(self) -> None:
        """
        NAME
            _print_node_list - Print the node list as a PDF table.
        """
        self._export_node_list_pdf(print_after=True, path_override="")

    def _export_node_list_pdf(self, print_after: bool, path_override: Optional[str]) -> None:
        """
        NAME
            _export_node_list_pdf - Export the node list as a PDF table.

        PARAMETERS
            print_after: When true, queue the exported PDF for printing.
            path_override: If set, use this path. Empty string means temp file.
        """
        try:
            from reportlab.pdfgen import canvas as pdfcanvas  # type: ignore
            from reportlab.lib.colors import Color  # type: ignore
        except Exception:
            messagebox.showerror(
                "Missing Dependency",
                "PDF export requires the 'reportlab' package.\n\n"
                "Install with: pip install reportlab",
            )
            return

        path = None
        if path_override is None:
            path = filedialog.asksaveasfilename(
                title="Export Node List PDF",
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf"), ("All files", "*.*")],
            )
        elif path_override == "":
            import tempfile

            fd, temp_path = tempfile.mkstemp(
                prefix=TEMP_PRINT_NODE_LIST_PREFIX,
                suffix=PDF_FILE_EXTENSION,
            )
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
            path = temp_path
        else:
            path = path_override
        if not path:
            return

        nodes = list(self._device_nodes())
        if self._tag_filter_fn is not None:
            nodes = [n for n in nodes if self._tag_filter_fn(n)]
        nodes = sort_nodes(nodes, self._list_sort_var.get())

        key_counts: Dict[Tuple[str, str, int], int] = {}
        numeric_counts: Dict[int, int] = {}
        for node in nodes:
            key = self._dup_key_for_node(node)
            if key is None:
                continue
            key_counts[key] = key_counts.get(key, 0) + 1
            numeric_counts[key[2]] = numeric_counts.get(key[2], 0) + 1
        dup_keys = {key for key, count in key_counts.items() if count > 1}
        warn_ids = {can_id for can_id, count in numeric_counts.items() if count > 1}

        page_w = 11 * 72
        page_h = 8.5 * 72
        margin = 36
        c = pdfcanvas.Canvas(path, pagesize=(page_w, page_h))
        c.setTitle("CAN Topology Node List")

        header_font = "Helvetica-Bold"
        body_font = "Helvetica"
        font_size = 9
        row_h = 14
        table_top = page_h - margin - 20
        x = margin

        def _status(node: Node) -> str:
            key = self._dup_key_for_node(node)
            if key in dup_keys:
                return "ERROR"
            if key and key[2] in warn_ids:
                return "WARN"
            return ""

        def _status_cause(node: Node) -> str:
            key = self._dup_key_for_node(node)
            if key in dup_keys:
                return "Duplicate CAN ID (vendor+type)"
            if key and key[2] in warn_ids:
                return "Duplicate CAN ID (numeric)"
            return ""

        cols = [
            ("CAN ID", 50),
            ("Type", 90),
            ("Label", 210),
            ("Tags", 170),
            ("Status", 60),
            ("Cause", 170),
        ]

        def _draw_header(y: float) -> float:
            c.setFont(header_font, font_size)
            c.setFillColor(Color(0, 0, 0))
            col_x = x
            for title, width in cols:
                c.drawString(col_x, y, title)
                col_x += width
            y -= row_h
            c.setLineWidth(1)
            c.setStrokeColor(Color(0.2, 0.2, 0.2))
            c.line(x, y + row_h * 0.3, page_w - margin, y + row_h * 0.3)
            return y

        def _wrap(text: str, max_w: float) -> List[str]:
            if not text:
                return [""]
            words = text.split()
            lines: List[str] = []
            current = words[0]
            for word in words[1:]:
                test = f"{current} {word}"
                if c.stringWidth(test, body_font, font_size) <= max_w:
                    current = test
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
            return lines

        y = table_top
        y = _draw_header(y)
        c.setFont(body_font, font_size)

        for node in nodes:
            tags = self._tags_to_string(node.tags)
            values = [
                str(node.can_id),
                node.category,
                node.label,
                tags,
                _status(node),
                _status_cause(node),
            ]
            lines_per_row = 1
            wrapped: List[List[str]] = []
            col_x = x
            for (title, width), value in zip(cols, values):
                lines = _wrap(value, width - 4)
                wrapped.append(lines)
                lines_per_row = max(lines_per_row, len(lines))
                col_x += width
            needed_h = row_h * lines_per_row
            if y - needed_h < margin:
                c.showPage()
                y = table_top
                y = _draw_header(y)
                c.setFont(body_font, font_size)
            col_x = x
            for (title, width), lines in zip(cols, wrapped):
                line_y = y
                for line in lines:
                    c.drawString(col_x, line_y, line)
                    line_y -= row_h
                col_x += width
            y -= needed_h

        c.showPage()
        c.save()

        if print_after:
            self._print_or_open_pdf(path, MSG_PRINTED_NODE_LIST)

            def _cleanup() -> None:
                try:
                    Path(path).unlink()
                except Exception:
                    pass

            self.after(TEMP_PRINT_CLEANUP_DELAY_MS, _cleanup)
        else:
            messagebox.showinfo("Exported", f"Wrote PDF to {path}")

    def _on_export_java_constants(self) -> None:
        """
        NAME
            _on_export_java_constants - Export CAN IDs into a Java constants class.
        """
        profile_name = self.entry_profile.get().strip() or "Bringup"
        default_name = "BringupConstants.java"
        root = Path(__file__).resolve().parents[2]
        default_dir = root / "src" / "main" / "java"
        path = filedialog.asksaveasfilename(
            title="Export Java Constants",
            initialdir=str(default_dir) if default_dir.exists() else None,
            initialfile=default_name,
            defaultextension=".java",
            filetypes=[("Java", "*.java"), ("All files", "*.*")],
        )
        if not path:
            return
        class_name = Path(path).stem or "BringupConstants"
        package = self._derive_java_package(path, default_dir)
        constants: List[Tuple[str, int]] = []
        used_names: Dict[str, int] = {}
        for node in self._device_nodes():
            name = self._sanitize_java_identifier(node.label)
            name = f"CAN_ID_{name}"
            if name in used_names:
                used_names[name] += 1
                name = f"{name}_{node.can_id}"
            else:
                used_names[name] = 1
            constants.append((name, int(node.can_id)))
        constants.sort(key=lambda item: item[0])
        lines: List[str] = []
        if package:
            lines.append(f"package {package};")
            lines.append("")
        lines.append("/**")
        lines.append(" * Auto-generated CAN ID constants.")
        lines.append(f" * Profile: {profile_name}")
        lines.append(" */")
        lines.append(f"public final class {class_name} {{")
        lines.append(f"    private {class_name}() {{}}")
        lines.append("")
        if not constants:
            lines.append("    // No device nodes available.")
        else:
            for name, can_id in constants:
                lines.append(f"    public static final int {name} = {can_id};")
        lines.append("}")
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines))
                handle.write("\n")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to write {path}: {exc}")
            return
        messagebox.showinfo("Exported", f"Wrote Java constants to {path}")

    def _sanitize_java_identifier(self, label: str) -> str:
        """
        NAME
            _sanitize_java_identifier - Convert a label into a Java identifier suffix.
        """
        cleaned = re.sub(r"[^A-Za-z0-9]+", "_", label.strip().upper())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if not cleaned:
            cleaned = "NODE"
        if not cleaned[0].isalpha():
            cleaned = f"NODE_{cleaned}"
        return cleaned

    def _derive_java_package(self, path: str, root_dir: Path) -> str:
        """
        NAME
            _derive_java_package - Infer package name from a Java source path.
        """
        try:
            file_path = Path(path).resolve()
            root_path = root_dir.resolve()
            rel = file_path.relative_to(root_path)
        except Exception:
            return ""
        parts = list(rel.parts[:-1])
        if not parts:
            return ""
        return ".".join(parts)

    def _nearest_bus_and_row(self, y: float) -> Tuple[int, int]:
        """
        NAME
            _nearest_bus_and_row - Pick the nearest bus and top/bottom row.

        RETURNS
            Tuple of (bus_index, row) where row 0 is above, 1 is below.
        """
        bus_ys = list(self._draw_state.get("bus_ys", []))
        if not bus_ys:
            height = max(self.canvas.winfo_height(), 1)
            base_y = height * 0.5 + self._pan_y
            bus_ys = [base_y]
        nearest = 0
        best = float("inf")
        for idx, bus_y in enumerate(bus_ys):
            dist = abs(y - bus_y)
            if dist < best:
                best = dist
                nearest = idx
        row = 0 if y < bus_ys[nearest] else 1
        return nearest, row

    def _nearest_callout_target(self, cx: float, cy: float) -> Tuple[str, int, Optional[int]]:
        """
        NAME
            _nearest_callout_target - Choose nearest node or bus for callouts.
        """
        scale = max(self._zoom, 0.01)
        bus_ys = list(self._draw_state.get("bus_ys", []))
        if not bus_ys:
            height = max(self.canvas.winfo_height(), 1)
            base_y = height * 0.5 + self._pan_y
            bus_ys = [base_y]
        # Find nearest node center in canvas coords.
        nearest_node = None
        nearest_node_dist = float("inf")
        for node in self._nodes:
            nx = node.x * scale
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys) - 1, 0))
            ny = bus_ys[bus_index]
            dx = cx - nx
            dy = cy - ny
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < nearest_node_dist:
                nearest_node_dist = dist
                nearest_node = node
        # Snap to node if within threshold, else to nearest bus.
        node_snap = 40 * scale
        if nearest_node is not None and nearest_node_dist <= node_snap:
            return "node", nearest_node.bus_index, nearest_node.key
        nearest_bus = 0
        best = float("inf")
        for idx, bus_y in enumerate(bus_ys):
            dist = abs(cy - bus_y)
            if dist < best:
                best = dist
                nearest_bus = idx
        return "bus", nearest_bus, None

    def _bus_hit_test(self, cy: float) -> Optional[int]:
        """
        NAME
            _bus_hit_test - Return bus index if click is near a bus line.
        """
        bus_ys = list(self._draw_state.get("bus_ys", []))
        if not bus_ys:
            height = max(self.canvas.winfo_height(), 1)
            base_y = height * 0.5 + self._pan_y
            bus_ys = [base_y]
        threshold = 6.0
        for idx, bus_y in enumerate(bus_ys):
            if abs(cy - bus_y) <= threshold:
                return idx
        return None

    def _bus_end_hit_test(self, bus_index: int, cx: float, cy: float) -> Optional[str]:
        """
        NAME
            _bus_end_hit_test - Return "left" or "right" when near a segment end.
        """
        if bus_index < 0 or bus_index >= len(self._bus_offsets):
            return None
        bus_ys = list(self._draw_state.get("bus_ys", []))
        if not bus_ys:
            return None
        scale = max(self._zoom, 0.01)
        bus_y = bus_ys[bus_index]
        bus_lefts = self._draw_state.get("bus_lefts", self._bus_lefts)
        bus_rights = self._draw_state.get("bus_rights", self._bus_rights)
        if bus_index >= len(bus_lefts) or bus_index >= len(bus_rights):
            return None
        left_x = bus_lefts[bus_index] * scale
        right_x = bus_rights[bus_index] * scale
        if abs(cy - bus_y) > 10:
            return None
        if abs(cx - left_x) <= 10:
            return "left"
        if abs(cx - right_x) <= 10:
            return "right"
        return None

    def _reorder_buses_by_y(self) -> None:
        """
        NAME
            _reorder_buses_by_y - Reindex bus segments by vertical order.
        """
        bus_ys = list(self._draw_state.get("bus_ys", []))
        if not bus_ys or len(self._bus_offsets) <= 1:
            return
        ordering = sorted(range(len(bus_ys)), key=lambda idx: bus_ys[idx])
        if ordering == list(range(len(bus_ys))):
            return
        new_offsets = [self._bus_offsets[idx] for idx in ordering]
        if self._bus_lefts:
            self._bus_lefts = [self._bus_lefts[idx] for idx in ordering if idx < len(self._bus_lefts)]
        if self._bus_rights:
            self._bus_rights = [self._bus_rights[idx] for idx in ordering if idx < len(self._bus_rights)]
        index_map = {old: new for new, old in enumerate(ordering)}
        for node in self._nodes:
            node.bus_index = index_map.get(node.bus_index, node.bus_index)
        for callout in self._callout_nodes():
            if callout.callout_target_type == "bus":
                callout.callout_target_bus = index_map.get(
                    callout.callout_target_bus, callout.callout_target_bus
                )
        self._bus_offsets = new_offsets
        self._redraw_canvas()

    def _fit_font_size(self, text: str, max_w: float, max_h: float, base_size: int) -> int:
        """
        NAME
            _fit_font_size - Shrink font size until text fits inside a box.
        """
        return fit_font_size_shared(text, max_w, max_h, base_size)

    def _ensure_bus_connectors(self, bus_count: int) -> None:
        """
        NAME
            _ensure_bus_connectors - Ensure connector flags match bus count.
        """
        if bus_count <= BUS_INDEX_FLOOR:
            self._bus_connectors = []
            return
        desired = bus_count - BUS_INDEX_FLOOR
        if not self._bus_connectors:
            self._bus_connectors = [BUS_CONNECT_DEFAULT] * desired
            return
        if len(self._bus_connectors) < desired:
            self._bus_connectors.extend(
                [BUS_CONNECT_DEFAULT] * (desired - len(self._bus_connectors))
            )
        elif len(self._bus_connectors) > desired:
            self._bus_connectors = self._bus_connectors[:desired]

    def _default_bus_connector_side(self, connector_index: int) -> str:
        """
        NAME
            _default_bus_connector_side - Return the legacy inferred side for one join.
        """
        return BUS_CONNECT_SIDE_RIGHT if connector_index % 2 == 0 else BUS_CONNECT_SIDE_LEFT

    def _normalize_bus_connector_side(self, value: object, connector_index: int) -> str:
        """
        NAME
            _normalize_bus_connector_side - Normalize a stored join side token.
        """
        text = str(value).strip().lower() if isinstance(value, str) else EMPTY_STRING
        if text == BUS_CONNECT_SIDE_LEFT:
            return BUS_CONNECT_SIDE_LEFT
        if text == BUS_CONNECT_SIDE_RIGHT:
            return BUS_CONNECT_SIDE_RIGHT
        return self._default_bus_connector_side(connector_index)

    def _ensure_bus_connector_sides(self, bus_count: int) -> None:
        """
        NAME
            _ensure_bus_connector_sides - Ensure join side metadata matches bus count.
        """
        desired = max(bus_count - BUS_INDEX_FLOOR, CANNECT_PORT_ZERO)
        if desired <= 0:
            self._bus_connector_sides = []
            return
        current_sides = list(self.__dict__.get("_bus_connector_sides", []) or [])
        normalized = [
            self._normalize_bus_connector_side(
                current_sides[idx] if idx < len(current_sides) else EMPTY_STRING,
                idx,
            )
            for idx in range(desired)
        ]
        self._bus_connector_sides = normalized

    def _bus_connector_side(self, connector_index: int) -> str:
        """
        NAME
            _bus_connector_side - Return the effective side for a join between adjacent buses.
        """
        current_sides = list(self.__dict__.get("_bus_connector_sides", []) or [])
        if 0 <= connector_index < len(current_sides):
            return self._normalize_bus_connector_side(current_sides[connector_index], connector_index)
        return self._default_bus_connector_side(connector_index)

    @staticmethod
    def _opposite_bus_connector_side(side: str) -> str:
        """
        NAME
            _opposite_bus_connector_side - Return the other legal join side token.
        """
        return BUS_CONNECT_SIDE_LEFT if side == BUS_CONNECT_SIDE_RIGHT else BUS_CONNECT_SIDE_RIGHT

    def _align_join_geometry(self, connector_index: int) -> None:
        """
        NAME
            _align_join_geometry - Align adjacent segment endpoints on the stored join side.
        """
        if connector_index < 0 or connector_index + 1 >= len(self._bus_offsets):
            return
        side = self._bus_connector_side(connector_index)
        if side == BUS_CONNECT_SIDE_RIGHT:
            shared_x = max(
                self._bus_rights[connector_index],
                self._bus_rights[connector_index + 1],
            )
            self._bus_rights[connector_index] = shared_x
            self._bus_rights[connector_index + 1] = shared_x
            return
        shared_x = min(
            self._bus_lefts[connector_index],
            self._bus_lefts[connector_index + 1],
        )
        self._bus_lefts[connector_index] = shared_x
        self._bus_lefts[connector_index + 1] = shared_x

    def _set_bus_connector_side(self, connector_index: int, side: str) -> None:
        """
        NAME
            _set_bus_connector_side - Set one join side and propagate alternating sides through its component.
        """
        if connector_index < 0 or connector_index >= len(self._bus_connectors):
            return
        normalized_side = self._normalize_bus_connector_side(side, connector_index)
        self._ensure_bus_connector_sides(len(self._bus_offsets))
        start = connector_index
        while start - 1 >= 0 and self._bus_connectors[start - 1]:
            start -= 1
        end = connector_index
        while end + 1 < len(self._bus_connectors) and self._bus_connectors[end + 1]:
            end += 1
        current_side = normalized_side
        for idx in range(connector_index, start - 1, -1):
            self._bus_connector_sides[idx] = current_side
            current_side = self._opposite_bus_connector_side(current_side)
        current_side = self._opposite_bus_connector_side(normalized_side)
        for idx in range(connector_index + 1, end + 1):
            self._bus_connector_sides[idx] = current_side
            current_side = self._opposite_bus_connector_side(current_side)
        for idx in range(start, end + 1):
            self._align_join_geometry(idx)

    def _truncate_to_width(self, text: str, font: tkfont.Font, max_w: float) -> str:
        """
        NAME
            _truncate_to_width - Trim text to fit a max pixel width.
        """
        return truncate_to_width_shared(text, font, max_w)

    def _wrap_label_lines(self, text: str, font: tkfont.Font, max_w: float) -> List[str]:
        """
        NAME
            _wrap_label_lines - Wrap label text into at most two lines.
        """
        return wrap_label_lines_shared(text, font, max_w)

    def _schedule_redraw(self) -> None:
        """
        NAME
            _schedule_redraw - Coalesce redraws during drag operations.
        """
        if self._dragging_active:
            return
        if self._redraw_pending:
            return
        self._redraw_pending = True
        self.after(16, self._flush_redraw)

    def _flush_redraw(self) -> None:
        """
        NAME
            _flush_redraw - Execute a queued redraw.
        """
        self._redraw_pending = False
        self._pending_fit_to_window = False
        self._redraw_canvas()

    def _on_zoom_wheel(self, event: tk.Event) -> str:
        """
        NAME
            _on_zoom_wheel - Handle mouse-wheel zoom.
        """
        wheel_delta = getattr(event, "delta", 0)
        button_num = getattr(event, "num", None)
        if wheel_delta > 0 or button_num == MOUSEWHEEL_UP_NUM:
            delta = ZOOM_WHEEL_STEP
        elif wheel_delta < 0 or button_num == MOUSEWHEEL_DOWN_NUM:
            delta = -ZOOM_WHEEL_STEP
        else:
            return "break"
        anchor_x = float(getattr(event, "x", max(self.canvas.winfo_width(), 1) / 2.0))
        anchor_y = float(getattr(event, "y", max(self.canvas.winfo_height(), 1) / 2.0))
        self._zoom_step(delta, anchor_x=anchor_x, anchor_y=anchor_y)
        return "break"

    def _zoom_step(
        self,
        delta: float,
        anchor_x: Optional[float] = None,
        anchor_y: Optional[float] = None,
    ) -> None:
        """
        NAME
            _zoom_step - Apply a zoom increment within bounds.
        """
        old_zoom = max(self._zoom, 0.01)
        new_zoom = max(0.1, min(2.0, self._zoom + delta))
        if abs(new_zoom - self._zoom) < 1e-9:
            return
        view_width = max(float(self.canvas.winfo_width()), 1.0)
        view_height = max(float(self.canvas.winfo_height()), 1.0)
        anchor_px_x = view_width / 2.0 if anchor_x is None else float(anchor_x)
        anchor_px_y = view_height / 2.0 if anchor_y is None else float(anchor_y)
        anchor_canvas_x = float(self.canvas.canvasx(anchor_px_x))
        anchor_canvas_y = float(self.canvas.canvasy(anchor_px_y))
        base_y_before = view_height * 0.5 + self._pan_y
        anchor_world_x = anchor_canvas_x / old_zoom
        anchor_world_offset_y = (anchor_canvas_y - base_y_before) / old_zoom
        self._zoom = new_zoom
        self._dirty = True
        self._zoom_label_var.set(f"Zoom: {int(self._zoom * 100)}%")
        self._redraw_canvas()
        base_y_after = view_height * 0.5 + self._pan_y
        desired_top = base_y_after + anchor_world_offset_y * self._zoom - anchor_px_y
        desired_left = anchor_world_x * self._zoom - anchor_px_x
        self._set_canvas_xview_left(desired_left)
        self._set_canvas_yview_top(desired_top)

    def _zoom_reset(self) -> None:
        """
        NAME
            _zoom_reset - Reset zoom to 100%.
        """
        self._zoom_step(1.0 - self._zoom)

    def _fit_to_window(self) -> None:
        """
        NAME
            _fit_to_window - Fit the diagram to the current canvas size.
        """
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        margin = 24.0
        device_nodes = self._device_nodes()
        callouts = self._callout_nodes()
        if not device_nodes and not callouts and not self._bus_offsets:
            return

        min_x = float("inf")
        max_x = float("-inf")
        min_y = float("inf")
        max_y = float("-inf")

        for node in device_nodes:
            node_scale = max(0.6, min(2.0, node.scale))
            half_w = (self._box_w * node_scale) / 2.0
            half_h = (self._box_h * node_scale) / 2.0
            center_y = self._node_center_y_unscaled(node)
            min_x = min(min_x, node.x - half_w)
            max_x = max(max_x, node.x + half_w)
            min_y = min(min_y, center_y - half_h)
            max_y = max(max_y, center_y + half_h)

        for callout in callouts:
            callout_scale = max(0.6, min(2.0, callout.scale))
            half_w = (180 * callout_scale) / 2.0
            half_h = (50 * callout_scale) / 2.0
            min_x = min(min_x, callout.x - half_w)
            max_x = max(max_x, callout.x + half_w)
            center_y = self._node_center_y_unscaled(callout)
            min_y = min(min_y, center_y - half_h)
            max_y = max(max_y, center_y + half_h)

        if self._bus_offsets:
            bus_min = min(self._bus_offsets) - (self._box_h + 60.0)
            bus_max = max(self._bus_offsets) + (self._box_h + 60.0)
            min_y = min(min_y, bus_min)
            max_y = max(max_y, bus_max)

        max_node_x = max((n.x for n in device_nodes), default=0.0)
        if len(self._bus_lefts) < len(self._bus_offsets):
            self._bus_lefts.extend([40.0] * (len(self._bus_offsets) - len(self._bus_lefts)))
        if len(self._bus_rights) < len(self._bus_offsets):
            self._bus_rights.extend(
                [max_node_x + 200.0] * (len(self._bus_offsets) - len(self._bus_rights))
            )
        if len(self._bus_lefts) > len(self._bus_offsets):
            self._bus_lefts = self._bus_lefts[: len(self._bus_offsets)]
        if len(self._bus_rights) > len(self._bus_offsets):
            self._bus_rights = self._bus_rights[: len(self._bus_offsets)]
        if self._bus_offsets:
            min_left = min(self._bus_lefts, default=40.0)
            max_right = max(self._bus_rights, default=max_node_x + 200.0)
            min_x = min(min_x, min_left)
            max_x = max(max_x, max_right)
        max_x = max(max_x, max_node_x + 200.0)
        min_x = min(min_x, 0.0)

        if min_x == float("inf") or max_x == float("-inf"):
            min_x, max_x = 0.0, 400.0
        if min_y == float("inf") or max_y == float("-inf"):
            min_y, max_y = -200.0, 200.0

        content_w = max(1.0, max_x - min_x)
        content_h = max(1.0, max_y - min_y)

        zoom_x = (width - margin * 2) / content_w
        zoom_y = (height - margin * 2) / content_h
        self._zoom = max(0.1, min(2.0, min(zoom_x, zoom_y)))
        self._zoom_label_var.set(f"Zoom: {int(self._zoom * 100)}%")

        center_y = (min_y + max_y) / 2.0
        self._pan_y = -center_y * self._zoom
        self._dirty = True
        self._redraw_canvas()
        self.update_idletasks()
        content_center_x = ((min_x + max_x) / 2.0) * self._zoom
        self._set_canvas_xview_left(content_center_x - width / 2.0)
        self.canvas.yview_moveto(0.0)

    @staticmethod
    def _tag_to_key(tags: Tuple[str, ...]) -> Optional[int]:
        """
        NAME
            _tag_to_key - Extract node key from canvas tag list.
        """
        for tag in tags:
            if tag.startswith("node_"):
                try:
                    return int(tag.split("_", 1)[1])
                except ValueError:
                    return None
        return None


def _print_version_banner() -> None:
    """
    NAME
        _print_version_banner - Print the CAN topology editor version.
    """
    version = VERSIONS.get(VERSION_APP_NAME, "")
    if not version:
        return
        print(VERSION_TITLE)
        print(format_version_line(VERSION_APP_NAME, version))
        for line in build_lines():
            print(line)

def main() -> int:
    """
    NAME
        main - Launch the CAN topology editor GUI.

    RETURNS
        Process exit code (0).
    """
    parser = argparse.ArgumentParser(description="CAN topology editor")
    parser.add_argument(ARG_VERSION, action=ACTION_STORE_TRUE, help=HELP_VERSION)
    args = parser.parse_args()
    if getattr(args, ARG_VERSION_ATTR, False):
        _print_version_banner()
        return 0
    _print_version_banner()
    app = TopologyEditor()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
