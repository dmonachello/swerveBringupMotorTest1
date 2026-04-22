"""
NAME
    status_messages.py - Status code message templates.

SYNOPSIS
    from tools.can_nt.status.status_messages import get_message_template

DESCRIPTION
    Aggregates per-facility status messages defined alongside code constants.
"""

from __future__ import annotations

from typing import Dict, Optional

from tools.can_nt.status.status_catalog import COMPILED_CATALOG_PATH

if COMPILED_CATALOG_PATH.exists():
    import json

    payload = json.loads(COMPILED_CATALOG_PATH.read_text(encoding="utf-8"))
    data = payload.get("data", {})
    raw = data.get("messageText", {})
    MESSAGE_TABLE: Dict[int, str] = {
        int(code): str(text)
        for code, text in raw.items()
        if str(code).isdigit()
    }
else:
    from tools.can_nt.status.cli_parser_codes import STATUS_MESSAGES as CLI_PARSER_MESSAGES
    from tools.can_nt.status.cli_validator_codes import STATUS_MESSAGES as CLI_VALIDATOR_MESSAGES
    from tools.can_nt.status.executor_codes import STATUS_MESSAGES as EXECUTOR_MESSAGES
    from tools.can_nt.status.device_codes import STATUS_MESSAGES as DEVICE_MESSAGES
    from tools.can_nt.status.group_codes import STATUS_MESSAGES as GROUP_MESSAGES
    from tools.can_nt.status.input_binding_codes import STATUS_MESSAGES as INPUT_BINDING_MESSAGES
    from tools.can_nt.status.network_codes import STATUS_MESSAGES as NETWORK_MESSAGES
    from tools.can_nt.status.config_codes import STATUS_MESSAGES as CONFIG_MESSAGES


    MESSAGE_TABLE = {}


    def _merge(table: Dict[int, str]) -> None:
        MESSAGE_TABLE.update(table)


    _merge(CLI_PARSER_MESSAGES)
    _merge(CLI_VALIDATOR_MESSAGES)
    _merge(EXECUTOR_MESSAGES)
    _merge(DEVICE_MESSAGES)
    _merge(GROUP_MESSAGES)
    _merge(INPUT_BINDING_MESSAGES)
    _merge(NETWORK_MESSAGES)
    _merge(CONFIG_MESSAGES)


def get_message_template(code: int) -> Optional[str]:
    """
    NAME
        get_message_template - Return message template for a status code.
    """

    template = MESSAGE_TABLE.get(code)
    if isinstance(template, str) and template:
        return template
    return None
