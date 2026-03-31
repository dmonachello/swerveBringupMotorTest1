"""
NAME
    group_codes.py - Status codes for GROUP facility.
"""

from tools.can_nt.status.status_catalog import FAC, MSG, SEV
from tools.can_nt.status.status_encode import code

SS__GROUP__NOT_FOUND = code(SEV.ERROR, FAC.GROUP, MSG.GROUP.NOT_FOUND)
SS__GROUP__EMPTY = code(SEV.WARNING, FAC.GROUP, MSG.GROUP.EMPTY)
SS__GROUP__MEMBER_MISSING = code(SEV.ERROR, FAC.GROUP, MSG.GROUP.MEMBER_MISSING)
SS__GROUP__BINDING_INVALID = code(SEV.ERROR, FAC.GROUP, MSG.GROUP.BINDING_INVALID)
