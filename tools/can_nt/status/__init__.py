"""
NAME
    __init__.py - Status code package exports.
"""

from tools.can_nt.status.status_encode import format_status, decode, FLAG_PRINT_MESSAGE
from tools.can_nt.status.status_result import StatusResult
from tools.can_nt.status.cli_parser_codes import (
    SS__CLI_PARSER__INVALID_SYNTAX,
    SS__CLI_PARSER__UNKNOWN_COMMAND,
    SS__CLI_PARSER__MISSING_ARGUMENT,
    SS__CLI_PARSER__INVALID_FLAG,
)
from tools.can_nt.status.cli_validator_codes import (
    SS__CLI_VALIDATOR__INVALID_VALUE,
    SS__CLI_VALIDATOR__OUT_OF_RANGE,
    SS__CLI_VALIDATOR__REQUIRED,
)
from tools.can_nt.status.executor_codes import (
    SS__EXECUTOR__SUCCESS,
    SS__EXECUTOR__CANCELLED,
    SS__EXECUTOR__INTERNAL_ERROR,
    SS__EXECUTOR__NOT_SUPPORTED,
)
from tools.can_nt.status.device_codes import (
    SS__DEVICE__NOT_FOUND,
    SS__DEVICE__NOT_DEFINED,
    SS__DEVICE__INVALID_FIELD,
)
from tools.can_nt.status.group_codes import (
    SS__GROUP__NOT_FOUND,
    SS__GROUP__EMPTY,
    SS__GROUP__MEMBER_MISSING,
    SS__GROUP__BINDING_INVALID,
)
from tools.can_nt.status.input_binding_codes import (
    SS__INPUT_BINDING__NOT_FOUND,
    SS__INPUT_BINDING__INVALID,
)
from tools.can_nt.status.network_codes import (
    SS__NETWORK__NOT_CONNECTED,
    SS__NETWORK__COMMAND_SEND_FAILED,
    SS__NETWORK__HANDSHAKE_FAILED,
    SS__NETWORK__CONNECT_FAILED,
    SS__NETWORK__ROBOT_UNAVAILABLE,
    SS__NETWORK__TIMEOUT,
)
from tools.can_nt.status.config_codes import (
    SS__CONFIG__NOT_LOADED,
    SS__CONFIG__INVALID,
    SS__CONFIG__SAVED,
    SS__CONFIG__MERGED,
    SS__CONFIG__IMPORTED,
    SS__CONFIG__VALID,
    SS__CONFIG__PROFILE_REQUIRED,
    SS__CONFIG__DUPLICATE_LABEL,
    SS__CONFIG__MISSING_DEVICE,
)

__all__ = [
    "format_status",
    "decode",
    "FLAG_PRINT_MESSAGE",
    "StatusResult",
    "SS__CLI_PARSER__INVALID_SYNTAX",
    "SS__CLI_PARSER__UNKNOWN_COMMAND",
    "SS__CLI_PARSER__MISSING_ARGUMENT",
    "SS__CLI_PARSER__INVALID_FLAG",
    "SS__CLI_VALIDATOR__INVALID_VALUE",
    "SS__CLI_VALIDATOR__OUT_OF_RANGE",
    "SS__CLI_VALIDATOR__REQUIRED",
    "SS__EXECUTOR__SUCCESS",
    "SS__EXECUTOR__CANCELLED",
    "SS__EXECUTOR__INTERNAL_ERROR",
    "SS__EXECUTOR__NOT_SUPPORTED",
    "SS__DEVICE__NOT_FOUND",
    "SS__DEVICE__NOT_DEFINED",
    "SS__DEVICE__INVALID_FIELD",
    "SS__GROUP__NOT_FOUND",
    "SS__GROUP__EMPTY",
    "SS__GROUP__MEMBER_MISSING",
    "SS__GROUP__BINDING_INVALID",
    "SS__INPUT_BINDING__NOT_FOUND",
    "SS__INPUT_BINDING__INVALID",
    "SS__NETWORK__NOT_CONNECTED",
    "SS__NETWORK__COMMAND_SEND_FAILED",
    "SS__NETWORK__HANDSHAKE_FAILED",
    "SS__NETWORK__CONNECT_FAILED",
    "SS__NETWORK__ROBOT_UNAVAILABLE",
    "SS__NETWORK__TIMEOUT",
    "SS__CONFIG__NOT_LOADED",
    "SS__CONFIG__INVALID",
    "SS__CONFIG__SAVED",
    "SS__CONFIG__MERGED",
    "SS__CONFIG__IMPORTED",
    "SS__CONFIG__VALID",
    "SS__CONFIG__PROFILE_REQUIRED",
    "SS__CONFIG__DUPLICATE_LABEL",
    "SS__CONFIG__MISSING_DEVICE",
]
