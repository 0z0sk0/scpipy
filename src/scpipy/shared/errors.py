import collections
import dataclasses
import enum


@dataclasses.dataclass(frozen=True, slots=True)
class ScpiError:
    code: int
    message: str

    def __str__(self) -> str:
        return f'{self.code},"{self.message}"'


class DefaultScpiErrors(enum.Enum):
    NO_ERROR = ScpiError(0, 'No error')
    SYNTAX_ERROR = ScpiError(-102, 'Syntax error')
    DATA_TYPE_ERROR = ScpiError(-104, 'Data type error')
    COMMAND_HEADER_ERROR = ScpiError(-110, 'Command header error')
    QUEUE_OVERFLOW = ScpiError(-350, 'Queue overflow')


class ScpiException(Exception):
    def __init__(self, error: ScpiError):
        self.error = error
        super().__init__(str(error))


class ErrorQueue:
    def __init__(self, max_size: int):
        self.__queue = collections.deque(maxlen=max_size)

    def get(self) -> str:
        if not self.__queue:
            return str(DefaultScpiErrors.NO_ERROR.value)

        return str(self.__queue.popleft())

    def put(self, item: ScpiError):
        if len(self.__queue) == self.__queue.maxlen:
            self.__queue.pop()
            self.__queue.append(DefaultScpiErrors.QUEUE_OVERFLOW.value)
            return

        self.__queue.append(item)

    def clear(self):
        self.__queue.clear()
