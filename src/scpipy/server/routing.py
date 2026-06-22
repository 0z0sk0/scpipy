from __future__ import annotations
import dataclasses
from collections.abc import Callable, Iterable

from scpipy.server.exceptions import RouteNotFound

from scpipy.shared.parser import Parser
from scpipy.shared.ast import Command


@dataclasses.dataclass
class Route:
    command: str
    handler: Callable

    pattern: Command = dataclasses.field(init=False)

    def __post_init__(self):
        parser = Parser()
        commands = parser.parse(self.command)

        if len(commands) != 1:
            raise ValueError('Route must contain exactly one command')

        self.pattern = commands[0]


class Router:
    def __init__(self):
        self._routes: dict[str, Route] = {}

    @property
    def routes(self) -> dict[str, Route]:
        return self._routes

    def route(self, command: str) -> Route:
        target = self.routes.get(command)
        if target is None:
            raise RouteNotFound

        return target

    def register(self, command: str):
        def wrapper(func: Callable):
            self.add_route(command, func)

        return wrapper

    def include_router(self, routers: Router | Iterable[Router]):
        if isinstance(routers, Router):
            routers = [routers]

        for router in routers:
            for route in router.routes.values():
                if route.command in self.routes.keys():
                    raise ValueError('Route already registered')

                self.add_route(route.command, route.handler)

    def add_route(self, command: str, handler: Callable):
        """
        Register an SCPI command route.

        :param command: SCPI command pattern to register, for example: '*IDN?', '*OPC?', 'SENSe:FREQuency:CENTer?'.
        :type command: str
        :param handler: Callable that will be invoked when the command is dispatched.
        :type handler: Callable

        :raises ValueError: if the command is already registered.
        """
        route = Route(command=command, handler=handler)

        if any(
            existing.pattern == route.pattern
            for existing in self._routes.values()
        ):
            raise ValueError('Route already registered')

        self._routes[command] = route
