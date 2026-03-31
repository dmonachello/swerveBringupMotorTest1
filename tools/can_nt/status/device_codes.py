"""
NAME
    device_codes.py - Status codes for DEVICE facility.
"""

from tools.can_nt.status.status_catalog import FAC, MSG, SEV
from tools.can_nt.status.status_encode import code

SS__DEVICE__NOT_FOUND = code(SEV.ERROR, FAC.DEVICE, MSG.DEVICE.NOT_FOUND)
SS__DEVICE__NOT_DEFINED = code(SEV.ERROR, FAC.DEVICE, MSG.DEVICE.NOT_DEFINED)
SS__DEVICE__INVALID_FIELD = code(SEV.ERROR, FAC.DEVICE, MSG.DEVICE.INVALID_FIELD)

STATUS_MESSAGES = {
    SS__DEVICE__NOT_FOUND: "Device not found: {device}.",
    SS__DEVICE__NOT_DEFINED: "Device not defined: {device}.",
    SS__DEVICE__INVALID_FIELD: "Invalid device field: {field}.",
}
