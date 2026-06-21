import asyncio

from collections.abc import Iterable

from . import exceptions
from . import dispatcher
from scpipy.server.routing import Router
from scpipy.server.context import Context
from scpipy.server.builtin_router import builtin_router
from scpipy.server.lifespan_manager import LifespanManager

from scpipy.shared.errors import ScpiException


class Server:
    def __init__(
        self,
        host: str,
        port: int,
        terminator: str = '\n',
        error_queue_size: int = 100,
        shared_context: bool = False,
        *,
        lifespan=None,
    ):
        self._host: str = host
        self._port: int = port

        self._server: asyncio.Server | None = None
        self._stop_event: asyncio.Event = asyncio.Event()

        self._client_tasks: set[asyncio.Task] = set()
        self._client_writers: set[asyncio.StreamWriter] = set()

        self._router = builtin_router
        self._dispatcher = dispatcher.Dispatcher(self._router, terminator)

        self._error_queue_size = error_queue_size

        self._lifespan_manager = LifespanManager(lifespan)

        self._context = None
        if shared_context:
            self._context = self._create_context()

    @property
    def state(self) -> dict:
        return self._lifespan_manager.state

    def include_router(self, routers: Router | Iterable[Router]):
        self._router.include_router(routers)

    def run(self):
        if self._host is None or self._port is None:
            raise exceptions.ConfigureException(
                'Host or port was not configured'
            )

        if self._server is not None:
            raise exceptions.AlreadyStarted('Server already started')

        self._stop_event.clear()
        asyncio.run(self._listen())

    def stop(self):
        self._stop_event.set()

    async def _listen(self):
        await self._lifespan_manager.startup(self)

        try:
            self._server = await asyncio.start_server(
                self._handle_client, self._host, self._port
            )

            await self._wait_stop()

        except asyncio.CancelledError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            await self._close()
            await self._close_writers()
            await self._close_tasks()

            await self._lifespan_manager.shutdown()

    async def _wait_stop(self):
        await self._stop_event.wait()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        if self._dispatcher is None:
            raise exceptions.LogicException('Dispatcher was not configured')

        context = self._get_context()

        task = asyncio.current_task()
        self._init_client(writer, task)

        try:
            while not self._stop_event.is_set():
                data = await reader.readline()
                if not data:
                    break

                try:
                    response = await self._dispatcher._dispatch(context, data)
                except ScpiException as exc:
                    context.push_error(exc.error)
                    continue

                if response:
                    writer.write(response)
                    await writer.drain()

        except asyncio.CancelledError:
            raise
        finally:
            await self._close_client(writer, task)

    def _init_client(
        self, writer: asyncio.StreamWriter, task: asyncio.Task | None
    ):
        if task is not None:
            self._client_tasks.add(task)
        self._client_writers.add(writer)

    async def _close_client(
        self, writer: asyncio.StreamWriter, task: asyncio.Task | None
    ):
        self._client_writers.discard(writer)

        if task is not None:
            self._client_tasks.discard(task)

        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

    async def _close(self):
        if self._server is None:
            raise exceptions.LogicException('Server cleaned up before')

        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def _close_writers(self):
        writers = list(self._client_writers)
        for writer in writers:
            writer.close()

        if writers:
            await asyncio.gather(
                *(writer.wait_closed() for writer in writers),
                return_exceptions=True,
            )

    async def _close_tasks(self):
        tasks = list(self._client_tasks)
        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _get_context(self) -> Context:
        if self._shared_context():
            assert self._context is not None
            return self._context

        return self._create_context()

    def _create_context(self) -> Context:
        return Context(
            error_queue_size=self._error_queue_size, state=self.state
        )

    def _shared_context(self) -> bool:
        return self._context is not None
