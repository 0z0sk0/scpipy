import dataclasses
from collections.abc import Callable

from scpipy.server.exceptions import RouteNotFound


@dataclasses.dataclass(frozen=True)
class Route:
    command: str
    handler: Callable


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
            self._add_route(command, func)

        return wrapper

    def include_router(self, router: Router):
        for route in router.routes.values():
            if route.command in self.routes.keys():
                raise ValueError('Route already registered')

            self._add_route(route.command, route.handler)

    def _add_route(self, command: str, handler: Callable):
        if command in self._routes.keys():
            raise ValueError('Route already registered')

        self._routes[command] = Route(command=command, handler=handler)
