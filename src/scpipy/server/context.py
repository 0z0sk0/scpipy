from typing import Any

from scpipy.server.status.system import StatusSystem
from scpipy.shared.errors import (
    ErrorQueue,
    ScpiError,
)


class Context:
    """
    Runtime context for SCPI server.

    Stores shared device state and provide access to error queue.

    :param error_queue_size: Maximum number of errors to store.
    :type error_queue_size: int
    :param state: Optional initial dictionary used to initialize the context.
    :type state: dict
    """

    def __init__(
        self,
        error_queue_size: int = 100,
        state: dict[Any, Any] | None = None,
    ):
        self.status = StatusSystem()
        self.error_queue = ErrorQueue(
            error_queue_size,
            on_change=self._error_queue_changed,
        )

        if state is not None:
            self.state = state
        else:
            self.state = {}

    def push_error(self, error: ScpiError):
        """
        Add an error to the error queue.

        :param error: Error instance to enqueue.
        :type error: ScpiError
        """
        self.error_queue.put(error)

    def get_error(self) -> str:
        """
        Get an error from the error queue.

        :return: String representation of the next queued error.
        :rtype: str
        """
        return self.error_queue.get()

    def clear_errors(self):
        """
        Remove all errors from the error queue.
        """
        self.error_queue.clear()

    def _error_queue_changed(self, error: ScpiError | None):
        self.status.set_error_available(bool(self.error_queue))
        if error is not None:
            self.status.record_error(error.code)

    def clear_status(self):
        """
        Remove all errors from the error queue and clear status registers.
        """
        self.clear_errors()
        self.status.clear()
