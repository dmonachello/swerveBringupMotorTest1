"""
NAME
    executor_codes.py - Status codes for EXECUTOR facility.
"""

from tools.can_nt.status.status_catalog import FAC, MSG, SEV
from tools.can_nt.status.status_encode import code

SS__NORMAL = code(SEV.SUCCESS, FAC.EXECUTOR, MSG.EXECUTOR.SUCCESS)
SS__EXECUTOR__CANCELLED = code(SEV.WARNING, FAC.EXECUTOR, MSG.EXECUTOR.CANCELLED)
SS__EXECUTOR__INTERNAL_ERROR = code(SEV.ERROR, FAC.EXECUTOR, MSG.EXECUTOR.INTERNAL_ERROR)
SS__EXECUTOR__NOT_SUPPORTED = code(SEV.ERROR, FAC.EXECUTOR, MSG.EXECUTOR.NOT_SUPPORTED)
SS__EXECUTOR__FAILED = code(SEV.ERROR, FAC.EXECUTOR, MSG.EXECUTOR.FAILED)

STATUS_MESSAGES = {
    SS__NORMAL: "Success.",
    SS__EXECUTOR__CANCELLED: "Operation cancelled.",
    SS__EXECUTOR__INTERNAL_ERROR: "Internal error.",
    SS__EXECUTOR__NOT_SUPPORTED: "Operation not supported.",
    SS__EXECUTOR__FAILED: "Command failed.",
}
