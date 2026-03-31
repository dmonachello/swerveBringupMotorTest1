from __future__ import annotations

"""
NAME
    power_diag_constants.py - Constants for power distribution normalization.

SYNOPSIS
    from tools.can_nt.power_diag_constants import KEY_DEVICES

DESCRIPTION
    Centralizes JSON keys and labels used to normalize PDH/PDP telemetry.
"""

KEY_DEVICES = "devices"
KEY_LABEL = "label"
KEY_TYPE = "type"
KEY_VENDOR = "vendor"
KEY_PRESENT = "present"
KEY_PRESENCE_CONF = "presenceConfidence"

TYPE_PDH = "PDH"
TYPE_PDP = "PDP"

FIELD_BUS_V = "busV"
FIELD_TOTAL_CURRENT_A = "totalCurrentA"
FIELD_TEMP_C = "tempC"
FIELD_SWITCHABLE_ENABLED = "switchableEnabled"
FIELD_BROWNOUT = "brownout"
FIELD_CAN_WARNING = "canWarning"
FIELD_HARDWARE_FAULT = "hardwareFault"
FIELD_STICKY_BROWNOUT = "stickyBrownout"
FIELD_STICKY_CAN_WARNING = "stickyCanWarning"
FIELD_STICKY_CAN_BUS_OFF = "stickyCanBusOff"
FIELD_STICKY_HAS_RESET = "stickyHasReset"
FIELD_CHANNEL_CURRENT_A = "channelCurrentA"
FIELD_CHANNEL_FAULT = "channelFault"
FIELD_CHANNEL_STICKY_FAULT = "channelStickyFault"

FLAG_BROWNOUT = "brownout"
FLAG_CAN_WARNING = "canWarning"
FLAG_CAN_BUS_OFF = "canBusOff"
FLAG_HAS_RESET = "hasReset"
FLAG_HARDWARE_FAULT = "hardwareFault"

STR_EMPTY = ""
FLOAT_ZERO = 0.0
INT_ZERO = 0
INT_ONE = 1
