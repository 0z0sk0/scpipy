import collections
import dataclasses
import enum
from collections.abc import Callable


@dataclasses.dataclass(frozen=True, slots=True)
class ScpiError:
    """Represent an SCPI error entry."""

    code: int
    message: str

    def __str__(self) -> str:
        """
        Return the SCPI error formatted as an SCPI error response.

        :return: Error string in SCPI error queue format.
        :rtype: str
        """
        return f'{self.code},"{self.message}"'


class DefaultScpiErrors(enum.Enum):
    """
    Protocol built-in SCPI error values.
    """

    NO_ERROR = ScpiError(0, 'No error')
    SYNTAX_ERROR = ScpiError(-102, 'Syntax error')
    DATA_TYPE_ERROR = ScpiError(-104, 'Data type error')
    PARAMETER_NOT_ALLOWED = ScpiError(-108, 'Parameter not allowed')
    MISSING_PARAMETER = ScpiError(-109, 'Missing parameter')
    COMMAND_HEADER_ERROR = ScpiError(-110, 'Command header error')
    QUEUE_OVERFLOW = ScpiError(-350, 'Queue overflow')
    DATA_OUT_OF_RANGE = ScpiError(-222, 'Data out of range')


class ScpiException(Exception):
    """
    Wrap an ``ScpiError`` as an exception.

    :param error: SCPI error associated with the exception.
    :type error: ScpiError
    """

    def __init__(self, error: ScpiError):
        self.error = error
        super().__init__(str(error))


class ErrorQueue:
    """
    Store SCPI errors in a bounded FIFO queue.

    :param max_size: Maximum number of errors stored in the queue.
    :type max_size: int
    :param on_change: Observer. Receives an inserted/detected error,
    :type on_change: Callable[[ScpiError | None], None] | None
    """

    def __init__(
        self,
        max_size: int,
        *,
        on_change: Callable[[ScpiError | None], None] | None = None,
    ):
        if max_size <= 0:
            raise ValueError('max_size must be > 0')

        self._on_change = on_change
        self.__queue: collections.deque[ScpiError] = collections.deque(
            maxlen=max_size,
        )

    def get(self) -> str:
        """
        Return the next error from the queue.

        If the queue is empty, returns ``0,"No error"``.

        :return: String representation of next SCPI-error from the queue.
        :rtype: str
        """
        if not self.__queue:
            return str(DefaultScpiErrors.NO_ERROR.value)

        error = self.__queue.popleft()
        self._notify(None)
        return str(error)

    def put(self, item: ScpiError):
        """
        Add an error to the queue.

        If the queue is full, the last queued error is replaced with
        ``QUEUE_OVERFLOW``.

        :param item: SCPI error to add to the queue.
        :type item: ScpiError
        """
        if len(self.__queue) < self.__queue.maxlen:
            self.__queue.append(item)
            self._notify(item)
            return

        if self.__queue[-1] == DefaultScpiErrors.QUEUE_OVERFLOW.value:
            self._notify(item)
            return

        self.__queue.pop()
        self.__queue.append(DefaultScpiErrors.QUEUE_OVERFLOW.value)
        self._notify(item)
        self._notify(DefaultScpiErrors.QUEUE_OVERFLOW.value)

    def clear(self):
        """
        Remove all errors from the queue.
        """
        self.__queue.clear()
        self._notify(None)

    def __len__(self) -> int:
        return len(self.__queue)

    def _notify(self, error: ScpiError | None) -> None:
        if self._on_change is not None:
            self._on_change(error)
