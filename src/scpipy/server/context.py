from scpipy.shared.errors import (
    ErrorQueue,
    ScpiError,
)


class Context:
    def __init__(self, error_queue_size: int = 100):
        self.error_queue = ErrorQueue(error_queue_size)

    def push_error(self, error: ScpiError):
        self.error_queue.put(error)

    def get_error(self) -> str:
        return str(self.error_queue.get())

    def clear_errors(self):
        self.error_queue.clear()
