from __future__ import annotations

"""
NAME
    bridge_robot_control_facade.py - Robot command transport facade for Bridge CLI.

SYNOPSIS
    Internal helper module used by bridge_cli facades.

DESCRIPTION
    Encapsulates robot command send/wait/failure handling behind a narrow
    transport context so command execution no longer reaches directly into the
    full BridgeCli object surface.
"""

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from tools.can_nt.bridge_ops import BridgeCommand
from tools.can_nt.bridge_session import BridgeEvent
from tools.can_nt.status import SS__NETWORK__COMMAND_SEND_FAILED, SS__NORMAL, StatusResult


MESSAGE_ERR_SEND_FAILED = "ERROR: Failed to send {name}."
COMMAND_GROUP_ADD_DEVICE = "groupAddDevice"
FIELD_DEVICE = "device"
FIELD_GROUP = "group"
EMPTY_STRING = ""


@dataclass(frozen=True)
class BridgeRobotControlTransport:
    """
    NAME
        BridgeRobotControlTransport - Narrow transport contract for robot commands.
    """

    send_command: Callable[[str, dict[str, Any]], Optional[int]]
    mark_command_sent: Callable[[str, float], None]
    wait_for_seq: Callable[[Optional[int]], Optional[BridgeEvent]]
    event_failed: Callable[[Optional[BridgeEvent], str], bool]
    handle_add_device_conflict: Callable[[Optional[BridgeEvent], str, str], bool]


class BridgeRobotControlFacade:
    """
    NAME
        BridgeRobotControlFacade - Execute bridge robot commands through transport.
    """

    def execute_command(self, transport: BridgeRobotControlTransport, command: BridgeCommand) -> StatusResult:
        seq = transport.send_command(command.name, command.args)
        if seq is None:
            print(MESSAGE_ERR_SEND_FAILED.format(name=command.name))
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        transport.mark_command_sent(command.name, time.time())
        event = transport.wait_for_seq(seq)
        if transport.event_failed(event, command.name):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        if command.name == COMMAND_GROUP_ADD_DEVICE:
            device = str(command.args.get(FIELD_DEVICE, EMPTY_STRING))
            group = str(command.args.get(FIELD_GROUP, EMPTY_STRING))
            if transport.handle_add_device_conflict(event, group, device):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        return StatusResult(code=SS__NORMAL)

