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
            route, bindings = self._route(command)
        except RouteNotFound:
            raise ScpiException(DefaultScpiErrors.COMMAND_HEADER_ERROR.value)

        positional_args = [arg.value for arg in command.args]

        try:
            result = route.handler(context, *positional_args, **bindings)
        except TypeError:
            raise ScpiException(DefaultScpiErrors.DATA_TYPE_ERROR.value)

        if asyncio.iscoroutine(result):
            result = await result

        if result is None:
            return None

        return str(result)

    def _route(self, command: Command) -> tuple[Route, dict[str, str]]:
        for route in self._router.routes.values():
            bindings = self._match_command(command, route.pattern)
            if bindings is not None:
                return route, bindings

        raise RouteNotFound

    def _match_command(
        self, command: Command, pattern: Command
    ) -> dict[str, str] | None:
        if command.common != pattern.common:
            return None

        if command.query != pattern.query:
            return None

        return self._match_nodes(command.nodes, pattern.nodes)

    def _match_nodes(
        self, nodes: list[Node], pattern_nodes: list[Node]
    ) -> dict[str, str] | None:
        node_index = 0
        bindings = {}

        for pattern_node in pattern_nodes:
            if node_index >= len(nodes):
                if pattern_node.optional:
                    continue
                return None

            matched = self._match_node(nodes[node_index], pattern_node)
            if matched is not None:
                bindings.update(matched)
                node_index += 1
            elif not pattern_node.optional:
                return None

        if node_index != len(nodes):
            return None

        return bindings

    @staticmethod
    def _match_node(node: Node, pattern: Node) -> dict[str, str] | None:
        if node.short != pattern.short:
            return None

        node_arg = node.arg.value if node.arg is not None else None
        pattern_arg = pattern.arg.value if pattern.arg is not None else None

        if pattern_arg is None:
            return {} if node_arg is None else None

        if node_arg is None:
            return None

        if pattern.arg.pattern:
            return {pattern_arg: node_arg}

        return {} if node_arg == pattern_arg else None
