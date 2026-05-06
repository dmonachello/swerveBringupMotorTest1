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

from typing import Dict

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
KEY_DSL_TESTS = "dslTests"
KEY_DSL_TEST_SET = "dslTestSet"
KEY_DSL_SCHEMA_VERSION = "schemaVersion"
KEY_DSL_TESTS_BY_NAME = "testsByName"
KEY_DSL_TEST_SETS = "testSets"
KEY_DSL_DEFAULT_SET = "defaultSet"
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
KEY_INTERFACE = "deviceInterface"
KEY_INTERFACE_LEGACY = "interface"
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
KEY_ENABLED = "enabled"
KEY_ESTOPPED = "estopped"
KEY_MODE = "mode"
KEY_NAME = "name"
KEY_MEMBERS = "members"
KEY_MEMBER_COUNT = "memberCount"
KEY_BINDING_COUNT = "bindingCount"
KEY_INPUT = "input"
KEY_KIND = "kind"
KEY_VALUE = "value"
KEY_GROUP_COUNT = "groupCount"
KEY_GENERATED_AT_MS = "generatedAtMs"
KEY_SOURCES = "sources"
KEY_SOURCES_NAME = "name"
KEY_SOURCES_PATH = "path"
KEY_SOURCES_EXISTS = "exists"
KEY_TESTS_ACTIVE_SET = "activeSet"
KEY_TESTS_DEFAULT_SET = "defaultSet"
KEY_TESTS_USING_SETS = "usingTestSets"
KEY_TESTS_TOTAL_COUNT = "totalCount"
KEY_TESTS_ENABLED_COUNT = "enabledCount"
KEY_TESTS_ROWS = "rows"
KEY_TESTS_INDEX = "index"
KEY_TESTS_NAME = "name"
KEY_TESTS_ENABLED = "enabled"
KEY_TESTS_SELECTED = "selected"
KEY_TESTS_TYPE = "type"
KEY_TESTS_STATUS = "status"
KEY_TESTS_MOTORS = "motors"
KEY_VERSION = "version"

INTERFACE_CAN = "CAN"
INTERFACE_DIO = "DIO"
INTERFACE_PWM = "PWM"
INTERFACE_ANALOG = "ANALOG"
INTERFACE_INTERNAL = "INTERNAL"

TYPE_LIMIT_SWITCH = "limitSwitch"
TYPE_ENCODER_INTERNAL = "encoderInternal"
TYPE_ENCODER_EXTERNAL = "encoderExternal"
TYPE_MOTOR = "motor"


def get_device_interface(entry: Dict[str, object]) -> object:
    """
    NAME
        get_device_interface - Read the device interface with backward compatibility.

    DESCRIPTION
        The canonical JSON key is deviceInterface. For one-iteration compatibility,
        accept the legacy key 'interface' when present.
    """
    value = entry.get(KEY_INTERFACE)
    if value is not None:
        return value
    return entry.get(KEY_INTERFACE_LEGACY)
