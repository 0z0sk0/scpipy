import asyncio

from scpipy.server.exceptions import ScpiException, RouteNotFound
from scpipy.server.routing import Router


class Dispatcher:
    def __init__(self, router: Router, terminator: str):
        self._router = router
        self._terminator = terminator

    async def _dispatch(self, data: bytes) -> bytes | None:
        processed_data = data.decode()
        command, args = self._parse_command(processed_data)

        try:
            route = self._router.route(command)
        except RouteNotFound:
            # TODO: raise exceptions as standard SCPI errors
            raise ScpiException('Unknown command')

        result = route.handler(args)

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
