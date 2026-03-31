"""
NAME
    cli_validator_codes.py - Status codes for CLI_VALIDATOR facility.
"""

from tools.can_nt.status.status_catalog import FAC, MSG, SEV
from tools.can_nt.status.status_encode import code

SS__CLI_VALIDATOR__INVALID_VALUE = code(SEV.ERROR, FAC.CLI_VALIDATOR, MSG.CLI_VALIDATOR.INVALID_VALUE)
SS__CLI_VALIDATOR__OUT_OF_RANGE = code(SEV.ERROR, FAC.CLI_VALIDATOR, MSG.CLI_VALIDATOR.OUT_OF_RANGE)
SS__CLI_VALIDATOR__REQUIRED = code(SEV.ERROR, FAC.CLI_VALIDATOR, MSG.CLI_VALIDATOR.REQUIRED)
