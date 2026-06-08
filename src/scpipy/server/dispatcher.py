import asyncio

from scpipy.server.exceptions import RouteNotFound
from scpipy.server.routing import Router, Route
from scpipy.server.context import Context

from scpipy.shared.parser import Parser, ParseError
from scpipy.shared.ast import Command, Node
from scpipy.shared.errors import ScpiException, DefaultScpiErrors


class Dispatcher:
    def __init__(self, router: Router, terminator: str):
        self._router = router
        self._terminator = terminator

        self._parser = Parser()

    async def _dispatch(self, context: Context, data: bytes) -> bytes | None:
        line = data.decode()

        try:
            commands = self._parser.parse(line)
        except ParseError:
            raise ScpiException(DefaultScpiErrors.SYNTAX_ERROR.value)

        responses = []

        for command in commands:
            response = await self._dispatch_command(context, command)
            if response is not None:
                responses.append(response)

        if not responses:
            return None

        payload = ';'.join(responses) + self._terminator
        return payload.encode()

    async def _dispatch_command(
        self, context: Context, command: Command
    ) -> str | None:
        try:
            route = self._route(command)
        except RouteNotFound:
            raise ScpiException(DefaultScpiErrors.COMMAND_HEADER_ERROR.value)

        args = [arg.value for arg in command.args]

        try:
            result = route.handler(context, *args)
        except TypeError:
            raise ScpiException(DefaultScpiErrors.DATA_TYPE_ERROR.value)

        if asyncio.iscoroutine(result):
            result = await result

        if result is None:
            return None

        return str(result)

    def _route(self, command: Command) -> Route:
        for route in self._router.routes.values():
            if self._match_command(command, route.pattern):
                return route

        raise RouteNotFound

    def _match_command(self, command: Command, pattern: Command) -> bool:
        if command.common != pattern.common:
            return False

        if command.query != pattern.query:
            return False

        return self._match_nodes(command.nodes, pattern.nodes)

    def _match_nodes(
        self, nodes: list[Node], pattern_nodes: list[Node]
    ) -> bool:
        node_index = 0

        for pattern_node in pattern_nodes:
            if node_index >= len(nodes):
                return pattern_node.optional

            if self._match_node(nodes[node_index], pattern_node):
                node_index += 1
            elif not pattern_node.optional:
                return False

        return node_index == len(nodes)

    @staticmethod
    def _match_node(node: Node, pattern: Node) -> bool:
        if node.short != pattern.short:
            return False

        node_arg = node.arg.value if node.arg is not None else None
        pattern_arg = pattern.arg.value if pattern.arg is not None else None

        return node_arg == pattern_arg
