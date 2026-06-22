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
    :param state: Optional initial state dictionary used to initialize the context.
    :type state: dict
    """

    def __init__(self, error_queue_size: int = 100, state: dict | None = None):
        self.error_queue = ErrorQueue(error_queue_size)

        if state:
            self.state: dict = state
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
        return str(self.error_queue.get())

    def clear_errors(self):
        """
        Remove all errors from the error queue.
        """
        self.error_queue.clear()
