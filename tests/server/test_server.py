import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from scpipy.server.exceptions import (
    AlreadyStarted,
    ConfigureException,
    LogicException,
)
from scpipy.server.routing import Router
from scpipy.shared.errors import ScpiError


@pytest.mark.parametrize('host,port', [(None, 5025), ('127.0.0.1', None)])
def test_run_requires_address(server_factory, host, port):
    with pytest.raises(ConfigureException):
        server_factory(host, port).run()


def test_run_rejects_already_started_server(server_factory):
    server = server_factory('127.0.0.1', 0)
    server._server = object()
    with pytest.raises(AlreadyStarted):
        server.run()


def test_run_uses_lifecycle_and_resets_stop_event(server_factory, monkeypatch):
    server = server_factory('127.0.0.1', 0)

    async def listen():
        assert not server._stop_event.is_set()

    server._listen = listen
    server.stop()
    server.run()


def test_context_sharing_and_queue_capacity(server_factory):
    server = server_factory(
        '127.0.0.1',
        0,
        shared_context=True,
        error_queue_size=2,
    )
    assert server._get_context() is server._get_context()
    separate = server_factory('127.0.0.1', 0)
    first, second = separate._get_context(), separate._get_context()
    assert first is not second
    first.push_error(ScpiError(-1, 'first'))
    assert second.get_error() == '0,"No error"'


@pytest.mark.asyncio
async def test_client_handler_returns_responses_and_queues_errors(
    server_factory,
    streams,
):
    server = server_factory('127.0.0.1', 0)
    reader, writer = streams
    reader.readline.side_effect = [
        b'UNKNOWN?\n',
        b'SYST:ERR?\n',
        b'SYST:ERR?\n',
        b'',
    ]
    await server._handle_client(reader, writer)
    assert [call.args[0] for call in writer.write.call_args_list] == [
        b'-110,"Command header error"\n',
        b'0,"No error"\n',
    ]
    assert writer.drain.await_count == 2
    writer.close.assert_called_once_with()
    writer.wait_closed.assert_awaited_once_with()
    assert not server._client_tasks and not server._client_writers


@pytest.mark.asyncio
async def test_include_router_and_custom_exception_handler(
    server_factory,
    streams,
):
    server = server_factory('127.0.0.1', 0)
    router = Router()

    def fail(context):
        raise ValueError('custom')

    router.add_route('USER?', fail)
    server.include_router([router])

    @server.add_exception_handler(ValueError)
    def handler(exc, context, command):
        return ScpiError(-222, 'custom')

    reader, writer = streams
    reader.readline.side_effect = [b'USER?\n', b'SYST:ERR?\n', b'']
    await server._handle_client(reader, writer)
    writer.write.assert_called_once_with(b'-222,"custom"\n')


@pytest.mark.asyncio
async def test_setter_does_not_write_or_drain(server_factory, streams):
    server = server_factory('127.0.0.1', 0)
    reader, writer = streams
    reader.readline.side_effect = [b'*CLS\n', b'']
    await server._handle_client(reader, writer)
    writer.write.assert_not_called()
    writer.drain.assert_not_awaited()


@pytest.mark.asyncio
async def test_handler_cancelled_read_cleans_up_and_propagates(
    server_factory,
    streams,
):
    server = server_factory('127.0.0.1', 0)
    reader, writer = streams
    reader.readline.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await server._handle_client(reader, writer)
    writer.close.assert_called_once_with()
    assert not server._client_tasks and not server._client_writers


@pytest.mark.asyncio
async def test_close_client_suppresses_connection_close_error(
    server_factory,
    streams,
):
    server = server_factory('127.0.0.1', 0)
    _, writer = streams
    writer.wait_closed.side_effect = ConnectionError('peer gone')
    server._init_client(writer, None)
    await server._close_client(writer, None)
    assert writer not in server._client_writers


@pytest.mark.asyncio
async def test_unconfigured_dispatcher_raises(server_factory, streams):
    server = server_factory('127.0.0.1', 0)
    server._dispatcher = None
    with pytest.raises(LogicException, match='Dispatcher'):
        await server._handle_client(*streams)


@pytest.mark.asyncio
async def test_close_listener_and_guard(server_factory):
    server = server_factory('127.0.0.1', 0)
    with pytest.raises(LogicException):
        await server._close()
    listener = MagicMock()
    listener.wait_closed = AsyncMock()
    server._server = listener
    await server._close()
    listener.close.assert_called_once_with()
    listener.wait_closed.assert_awaited_once_with()
    assert server._server is None


@pytest.mark.asyncio
async def test_close_writers_and_tasks(server_factory, streams):
    server = server_factory('127.0.0.1', 0)
    _, writer = streams
    server._client_writers.add(writer)
    task = asyncio.create_task(asyncio.Event().wait())
    server._client_tasks.add(task)
    await server._close_writers()
    await server._close_tasks()
    assert task.cancelled()
    writer.close.assert_called_once_with()
    await server_factory('127.0.0.1', 0)._close_tasks()


@pytest.mark.asyncio
async def test_tcp_lifecycle_handles_error_and_keeps_connection_alive(
    server_factory,
    monkeypatch,
):
    events = []

    @asynccontextmanager
    async def lifespan(server):
        events.append('startup')
        yield {'ready': True}
        events.append('shutdown')

    server = server_factory('127.0.0.1', 0, lifespan=lifespan)
    listening = asyncio.Event()
    original = asyncio.start_server

    async def start_server(*args, **kwargs):
        listener = await original(*args, **kwargs)
        listening.set()
        return listener

    monkeypatch.setattr(asyncio, 'start_server', start_server)
    task = asyncio.create_task(server._listen())
    writer = None
    try:
        await asyncio.wait_for(listening.wait(), 5)
        port = server._server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection('127.0.0.1', port)
        writer.write(b':CHANnel<>:DISPlay?\nSYST:ERR?\nSYST:ERR?\n')
        await writer.drain()
        assert (
            await asyncio.wait_for(reader.readline(), 5)
            == b'-102,"Syntax error"\n'
        )
        assert (
            await asyncio.wait_for(reader.readline(), 5) == b'0,"No error"\n'
        )
        assert server.state == {'ready': True}
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()
        server.stop()
        await asyncio.wait_for(task, 5)
    assert events == ['startup', 'shutdown']
    assert not server._client_tasks and not server._client_writers
    assert server._server is None
    assert server.state == {}
