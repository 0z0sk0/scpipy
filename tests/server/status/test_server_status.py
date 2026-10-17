import asyncio
from contextlib import asynccontextmanager

import pytest

from scpipy.server.routing import Router
from scpipy.server.status.models import OperationStatus

pytestmark = pytest.mark.asyncio


async def test_tcp_error_esr_stb_and_clear_sequence(
    server_factory,
    monkeypatch,
):
    server = server_factory('127.0.0.1', 0)
    ready = asyncio.Event()
    original = asyncio.start_server

    async def start(*args, **kwargs):
        result = await original(*args, **kwargs)
        ready.set()
        return result

    monkeypatch.setattr(asyncio, 'start_server', start)
    running = asyncio.create_task(server._listen())
    writer = None
    try:
        await asyncio.wait_for(ready.wait(), 5)
        port = server._server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection('127.0.0.1', port)

        async def query(command):
            writer.write(command + b'\n')
            await writer.drain()
            return await asyncio.wait_for(reader.readline(), 5)

        writer.write(b'*CLS\n*ESE 32\n*SRE 32\nUNKNOWN?\n')
        await writer.drain()
        assert await query(b'*STB?') == b'100\n'
        assert await query(b'*STB?') == b'100\n'
        assert await query(b'*ESR?') == b'32\n'
        assert await query(b'*ESR?') == b'0\n'
        assert await query(b'*STB?') == b'4\n'
        assert await query(b'SYST:ERR?') == b'-110,"Command header error"\n'
        assert await query(b'*STB?') == b'0\n'
        writer.write(b'*OPC\n*CLS\n')
        assert await query(b'*ESR?') == b'0\n'
        assert await query(b'*ESE?') == b'32\n'
        assert await query(b'*SRE?') == b'32\n'
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()
        server.stop()
        await asyncio.wait_for(running, 5)


async def test_mav_covers_write_and_drain_and_clears_on_transport_failure(
    server_factory,
    streams,
):
    server = server_factory('127.0.0.1', 0, shared_context=True)
    context = server._get_context()
    reader, writer = streams
    reader.readline.side_effect = [b'*STB?\n', b'']

    async def drain():
        assert context.status.status_byte & 16
        raise ConnectionError('transport failed')

    writer.drain.side_effect = drain
    with pytest.raises(ConnectionError, match='transport failed'):
        await server._handle_client(reader, writer)
    assert not context.status.status_byte & 16
    assert not server._client_tasks
    assert not server._client_writers


async def test_shared_and_isolated_contexts_have_matching_status_ownership(
    server_factory,
):
    shared = server_factory('127.0.0.1', 0, shared_context=True)
    first, second = shared._get_context(), shared._get_context()
    first.status.event_enable = 32
    assert second.status.event_enable == 32
    isolated = server_factory('127.0.0.1', 0)
    first, second = isolated._get_context(), isolated._get_context()
    first.status.event_enable = 32
    first.status.raise_event(32)
    assert second.status.event_enable == 0
    assert second.status.event_status == 128


async def test_empty_application_state_is_shared_after_lifespan_startup(
    server_factory,
):
    @asynccontextmanager
    async def lifespan(server):
        yield {'instrument': 'fake'}

    server = server_factory(
        '127.0.0.1',
        0,
        shared_context=True,
        lifespan=lifespan,
    )
    await server._lifespan_manager.startup(server)
    try:
        assert server._get_context().state is server.state
        assert server._get_context().state == {'instrument': 'fake'}
    finally:
        await server._lifespan_manager.shutdown()


async def test_servers_do_not_leak_routes_into_each_other(server_factory):
    first = server_factory('127.0.0.1', 0)
    second = server_factory('127.0.0.1', 0)
    router = Router()
    router.add_route('USER?', lambda context: 1)
    first.include_router(router)
    assert 'USER?' not in second._router.routes


async def test_background_measurement_handler_registers_work_before_opc(
    server_factory,
    streams,
):
    server = server_factory('127.0.0.1', 0, shared_context=True)
    release = asyncio.Event()
    tasks = []
    context = server._get_context()

    async def measurement():
        context.status.operation.update_condition(
            OperationStatus.MEASURING,
            True,
        )
        try:
            await release.wait()
        finally:
            context.status.operation.update_condition(
                OperationStatus.MEASURING,
                False,
            )

    def initiate(context):
        tasks.append(context.status.start_operation(measurement()))

    router = Router()
    router.add_route('INITiate', initiate)
    server.include_router(router)
    context.clear_status()

    assert (
        await server._dispatcher._dispatch(context, b'INIT;*OPC;*ESR?')
        == b'0\n'
    )
    pending = asyncio.create_task(
        server._dispatcher._dispatch(context, b'*OPC?'),
    )
    await asyncio.sleep(0)
    assert not pending.done()
    release.set()
    await asyncio.gather(*tasks)
    assert await asyncio.wait_for(pending, 2) == b'1\n'
    assert context.status.read_event_status() == 1
    assert context.status.operation.condition == 0
