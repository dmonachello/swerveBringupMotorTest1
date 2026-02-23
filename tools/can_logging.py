from __future__ import annotations


class PcapLogger:
    def __init__(self, path: str):
        self.path = path
        self._logger = None

    def start(self) -> None:
        if not self.path:
            return
        from can.io import Logger  # type: ignore
        try:
            self._logger = Logger(self.path)
        except ValueError as exc:
            print(f"WARNING: {exc}. Logging disabled.")
            self._logger = None

    def log(self, msg) -> None:
        if self._logger is None:
            return
        try:
            self._logger.on_message_received(msg)
        except Exception:
            pass

    def stop(self) -> None:
        if self._logger is None:
            return
        try:
            self._logger.stop()
        except Exception:
            pass
        self._logger = None
