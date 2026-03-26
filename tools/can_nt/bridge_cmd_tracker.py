from __future__ import annotations

"""
NAME
    bridge_cmd_tracker.py - Shared command pending/timeout/retry tracking.

SYNOPSIS
    from tools.can_nt.bridge_cmd_tracker import CommandTracker

DESCRIPTION
    Provides a shared pending/ACK/OUT tracker with timeout and retry handling.
    Both UI and CLI should use this helper to keep command behavior consistent.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class CommandState:
    """
    NAME
        CommandState - Current command tracking state.
    """

    name: str = ""
    args: Optional[Dict[str, Any]] = None
    seq: Optional[int] = None
    pending_ack: bool = False
    pending_out: bool = False
    pending_since: Optional[float] = None
    retry_pending: bool = False
    retry_count: int = 0
    retryable: bool = True


class CommandTracker:
    """
    NAME
        CommandTracker - Track pending state, timeouts, and retries.
    """

    def __init__(self, timeout_sec: float = 1.5, max_retries: int = 0) -> None:
        self._timeout_sec = float(timeout_sec)
        self._max_retries = int(max_retries)
        self._state = CommandState()

    def start(
        self,
        name: str,
        args: Optional[Dict[str, Any]],
        seq: Optional[int],
        pending_ack: bool = True,
        pending_out: bool = True,
        retryable: bool = True,
        now: Optional[float] = None,
    ) -> None:
        """
        NAME
            start - Begin tracking a command.
        """
        self._state = CommandState(
            name=name,
            args=args,
            seq=seq,
            pending_ack=bool(pending_ack),
            pending_out=bool(pending_out),
            pending_since=now,
            retry_pending=False,
            retry_count=self._state.retry_count,
            retryable=bool(retryable),
        )

    def clear_pending(self) -> None:
        """
        NAME
            clear_pending - Clear pending flags without altering last command.
        """
        self._state.pending_ack = False
        self._state.pending_out = False
        self._state.pending_since = None

    def handle_event(self, event) -> None:
        """
        NAME
            handle_event - Update pending flags based on an ACK/OUT event.
        """
        if event is None or self._state.seq is None:
            return
        if event.seq != self._state.seq:
            return
        if event.type == "ack":
            self._state.pending_ack = False
        elif event.type == "out":
            self._state.pending_out = False
        if not self.is_pending():
            self._state.pending_since = None

    def check_timeout(self, now: float) -> bool:
        """
        NAME
            check_timeout - Return True if the current command timed out.
        """
        if not self.is_pending() or self._state.pending_since is None:
            return False
        if (now - self._state.pending_since) <= self._timeout_sec:
            return False
        self.clear_pending()
        if self._state.retryable and self._state.retry_count < self._max_retries:
            self._state.retry_pending = True
        return True

    def take_retry(self) -> Optional[Tuple[str, Optional[Dict[str, Any]]]]:
        """
        NAME
            take_retry - Return a retry command if pending.
        """
        if not self._state.retry_pending or self.is_pending():
            return None
        if not self._state.retryable or self._state.retry_count >= self._max_retries:
            self._state.retry_pending = False
            return None
        self._state.retry_pending = False
        self._state.retry_count += 1
        return (self._state.name, self._state.args)

    def is_pending(self) -> bool:
        """
        NAME
            is_pending - Return True when ACK/OUT are still pending.
        """
        return bool(self._state.pending_ack or self._state.pending_out)

    def pending_text(self) -> str:
        """
        NAME
            pending_text - Human-friendly pending status text.
        """
        if not self.is_pending():
            return ""
        if self._state.pending_ack and self._state.pending_out:
            return "Waiting: ACK + OUT"
        if self._state.pending_ack:
            return "Waiting: ACK"
        return "Waiting: OUT"

    def last_command(self) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        NAME
            last_command - Return the last command tuple.
        """
        return (self._state.name, self._state.args)

    def clear(self) -> None:
        """
        NAME
            clear - Reset tracker state to idle.
        """
        self._state = CommandState()

