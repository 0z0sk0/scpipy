import asyncio

from . import exceptions


class Dispatcher:
    def __init__(self, terminator: str):
        self._terminator = terminator

        self._handlers = {}

    def register(self, command: str, handler):
        normalized_command = command.upper()

        self._handlers[normalized_command] = handler

    async def dispatch(self, data: bytes) -> bytes | None:
        processed_data = data.decode()
        command, args = self._parse_command(processed_data)

        handler = self._handlers.get(command)
        if handler is None:
            # TODO: raise exceptions as standard SCPI errors
            raise exceptions.ScpiException('Unknown command')

        result = handler(args)

        if asyncio.iscoroutine(result):
            result = await result

        if result:
            result += self._terminator
            return result.encode()

    def _parse_command(self, line: str) -> tuple[str, list[str]]:
        # TODO: must be determined in shared component
        # TODO: parse carefully

        parts = line.strip().split()
        command = parts[0].upper()
        args = parts[1:]

        return command, args
