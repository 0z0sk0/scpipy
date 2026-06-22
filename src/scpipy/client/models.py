import asyncio
import dataclasses
import enum


class OperationType(enum.Enum):
    """
    Define worker operation kinds.

    The operation type indicates how a queue item should be processed by the
    background worker.

    Variants:
        WRITE: Send a command to the instrument.
        READ: Read a response from the instrument.
        QUERY: Send a command and read the response.
        CLOSE: Stop the worker and close the connection.
    """

    WRITE = enum.auto()
    READ = enum.auto()
    QUERY = enum.auto()
    CLOSE = enum.auto()


@dataclasses.dataclass(slots=True)
class QueueItem:
    """
    Represent a queued worker operation.

    :param type: Type of the queued operation.
    :type type: OperationType
    :param value: Operation payload, usually a command string, or ``None`` for
        operations without a payload.
    :type value: str | None
    :param future: Future used to deliver the operation result or exception.
    :type future: asyncio.Future
    """

    type: OperationType
    value: str | None
    future: asyncio.Future
