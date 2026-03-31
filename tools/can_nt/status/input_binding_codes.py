"""
NAME
    input_binding_codes.py - Status codes for INPUT_BINDING facility.
"""

from tools.can_nt.status.status_catalog import FAC, MSG, SEV
from tools.can_nt.status.status_encode import code

SS__INPUT_BINDING__NOT_FOUND = code(SEV.ERROR, FAC.INPUT_BINDING, MSG.INPUT_BINDING.NOT_FOUND)
SS__INPUT_BINDING__INVALID = code(SEV.ERROR, FAC.INPUT_BINDING, MSG.INPUT_BINDING.INVALID)
