from __future__ import annotations

"""
NAME
    test_execution_service.py - Shared host-side bringup test command helpers.

SYNOPSIS
    from tools.can_nt.test_execution_service import select_test_by_name

DESCRIPTION
    Groups robot-backed test selection and execution commands into one shared
    layer so surfaces do not duplicate test command naming and payload shaping.
"""

from typing import Optional

from tools.can_nt.bridge_session import BridgeSession

CMD_RUN_ALL_TESTS = "runAllTests"
CMD_RUN_TEST = "runTest"
CMD_SELECT_TEST_BY_NAME = "selectTestByName"
CMD_SHOW_TESTS = "showTests"
CMD_TOGGLE_TEST = "toggleTest"
KEY_NAME = "name"


def select_test_by_name(session: BridgeSession, name: str) -> Optional[int]:
    """
    NAME
        select_test_by_name - Select a scripted test by name.
    """
    return session.send_command(CMD_SELECT_TEST_BY_NAME, {KEY_NAME: name})


def toggle_test(session: BridgeSession) -> Optional[int]:
    """
    NAME
        toggle_test - Toggle enabled state of the currently selected test.
    """
    return session.send_command(CMD_TOGGLE_TEST, {})


def run_selected_test(session: BridgeSession) -> Optional[int]:
    """
    NAME
        run_selected_test - Run the currently selected test once.
    """
    return session.send_command(CMD_RUN_TEST, {})


def run_all_tests(session: BridgeSession) -> Optional[int]:
    """
    NAME
        run_all_tests - Run all enabled tests sequentially.
    """
    return session.send_command(CMD_RUN_ALL_TESTS, {})


def show_tests(session: BridgeSession, json_output: bool = False) -> Optional[int]:
    """
    NAME
        show_tests - Request bringup tests overview output.
    """
    args = {"json": True} if json_output else {}
    return session.send_command(CMD_SHOW_TESTS, args)
