from __future__ import annotations

"""
NAME
    profile_constants.py - Shared bringup_system.json schema constants.

SYNOPSIS
    from tools.common.profile_constants import PROFILE_SCHEMA_VERSION, KEY_DEVICES

DESCRIPTION
    Centralizes schema keys and interface values so executable code paths avoid
    inline string or numeric literals.
"""

PROFILE_SCHEMA_VERSION = 4
BRIDGE_CONFIG_SCHEMA_VERSION = 2

KEY_SCHEMA_VERSION = "schema_version"
KEY_DATA_VERSION = "data_version"
KEY_DATA_HASH = "data_hash"
KEY_DEFAULT_PROFILE = "default_profile"
KEY_DEVICES = "devices"
KEY_PROFILES = "profiles"
KEY_PROFILE_DEVICES = "devices"
KEY_PROFILE = "profile"
KEY_DIAGRAM = "diagram"
KEY_BRIDGE_CONFIG = "bridgeConfig"
KEY_BRIDGE_SCHEMA_VERSION = "schemaVersion"
KEY_BRIDGE_GENERATED_AT = "generatedAt"
KEY_BRIDGE_BY_PROFILE = "byProfile"
KEY_BRIDGE_GROUPS = "groups"
KEY_BRIDGE_SELECTED_DEVICE = "selectedDevice"
KEY_BRIDGE_BINDINGS = "bindings"
KEY_BRIDGE_TESTS = "tests"
KEY_DEVICE = "device"
KEY_INPUT_ALIASES = "inputAliases"
KEY_NEIGHBOR_LINKS = "neighborLinks"
KEY_NEIGHBOR_PORTS = "neighborPorts"
KEY_LINK_A = "a"
KEY_LINK_B = "b"
KEY_LINK_NODE = "node"
KEY_LINK_PORT = "port"
KEY_LINK_NEIGHBOR = "neighbor"
KEY_LINK_NEIGHBOR_PORT = "neighborPort"
KEY_LINK_DEVICE = "device"
KEY_DEVICE_LINKS = "deviceLinks"
KEY_NODE_KEY = "key"
NEIGHBOR_PORT_LEFT = "left"
NEIGHBOR_PORT_RIGHT = "right"
NEIGHBOR_PORT_NEXT = "next"
NEIGHBOR_PORT_BRANCH1 = "branch1"
NEIGHBOR_PORT_BRANCH2 = "branch2"
CANNECT_PORT_ONE = 1
CANNECT_PORT_TWO = 2
CANNECT_PORT_THREE = 3

KEY_LABEL = "label"
KEY_INTERFACE = "interface"
KEY_ID = "id"
KEY_MANUFACTURER = "manufacturer"
KEY_DEVICE_TYPE = "deviceType"
KEY_MODEL = "model"
KEY_TYPE = "type"
KEY_VENDOR = "vendor"
KEY_ROLE = "role"
KEY_NOTES = "notes"
KEY_TAGS = "tags"
KEY_TERMINATOR = "terminator"
KEY_ATTACHMENTS = "attachments"
KEY_BUS = "bus"
KEY_LIMITS = "limits"

KEY_DIO = "dio"
KEY_INVERT = "invert"
KEY_PWM = "pwm"
KEY_ANALOG = "analog"

INTERFACE_CAN = "CAN"
INTERFACE_DIO = "DIO"
INTERFACE_PWM = "PWM"
INTERFACE_ANALOG = "ANALOG"
INTERFACE_INTERNAL = "INTERNAL"

TYPE_LIMIT_SWITCH = "limitSwitch"
TYPE_ENCODER_INTERNAL = "encoderInternal"
TYPE_ENCODER_EXTERNAL = "encoderExternal"
TYPE_MOTOR = "motor"
