"""
NAME
    cli_parser_codes.py - Status codes for CLI_PARSER facility.
"""

from tools.can_nt.status.status_catalog import FAC, MSG, SEV
from tools.can_nt.status.status_encode import code

SS__CLI_PARSER__INVALID_SYNTAX = code(SEV.ERROR, FAC.CLI_PARSER, MSG.CLI_PARSER.INVALID_SYNTAX)
SS__CLI_PARSER__UNKNOWN_COMMAND = code(SEV.ERROR, FAC.CLI_PARSER, MSG.CLI_PARSER.UNKNOWN_COMMAND)
SS__CLI_PARSER__MISSING_ARGUMENT = code(SEV.ERROR, FAC.CLI_PARSER, MSG.CLI_PARSER.MISSING_ARGUMENT)
SS__CLI_PARSER__INVALID_FLAG = code(SEV.ERROR, FAC.CLI_PARSER, MSG.CLI_PARSER.INVALID_FLAG)

STATUS_MESSAGES = {
    SS__CLI_PARSER__INVALID_SYNTAX: "Invalid command syntax.",
    SS__CLI_PARSER__UNKNOWN_COMMAND: "Unknown command.",
    SS__CLI_PARSER__MISSING_ARGUMENT: "Missing required argument: {arg}.",
    SS__CLI_PARSER__INVALID_FLAG: "Invalid flag: {flag}.",
}
