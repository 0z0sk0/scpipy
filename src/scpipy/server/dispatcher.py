import asyncio

from scpipy.server.exceptions import (
    RouteNotFound,
    ParserSyntaxError,
)
from scpipy.server.routing import Router, Route
from scpipy.server.context import Context
from scpipy.server.exception_handler import ExceptionHandler

from scpipy.shared.parser import Parser, ParseError
from scpipy.shared.ast import Command, Node
from scpipy.shared.errors import ScpiException


class Dispatcher:
    """
    Dispatch SCPI commands to registered route handlers.

    Parses incoming SCPI messages, resolves matching routes, invokes the
    corresponding handlers, and encodes the response payload.

    :param router: Router used to resolve SCPI command handlers.
    :type router: Router
    :param terminator: Line terminator appended to outgoing responses.
    :type terminator: str
    """

    def __init__(
        self,
        router: Router,
        terminator: str,
        exception_handler: ExceptionHandler | None = None,
    ) -> None:
        self._router = router
        self._terminator = terminator
        self._exception_handlers = exception_handler or ExceptionHandler()

        self._parser = Parser()

    async def _dispatch(self, context: Context, data: bytes) -> bytes | None:
        line = data.decode()

        try:
            commands = self._parser.parse(line)
        except ParseError:
            raise ScpiException(
                self._exception_handlers.resolve(
                    ParserSyntaxError, context, None
                )
            )

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
            positional_args = [arg.value for arg in command.args]

            result = route.invoke(context, *positional_args, **bindings)

            if asyncio.iscoroutine(result):
                result = await result

            if result is None:
                return None

            return str(result)
        except Exception as exc:
            raise ScpiException(
                self._exception_handlers.resolve(exc, context, command)
            )

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
