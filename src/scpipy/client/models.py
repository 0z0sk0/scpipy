import asyncio
import dataclasses
import enum


class OperationType(enum.Enum):
    WRITE = enum.auto()
    READ = enum.auto()
    QUERY = enum.auto()
    CLOSE = enum.auto()


@dataclasses.dataclass(slots=True)
class QueueItem:
    type: OperationType
    value: str | None
    future: asyncio.Future
