from unittest.mock import MagicMock

import pytest
import pyvisa

from scpipy.client.client import Client
from scpipy.client.exceptions import ClientConnectionError

pytestmark = pytest.mark.asyncio
RESOURCE = 'TCPIP::127.0.0.1::5025::SOCKET'


@pytest.fixture
def visa(monkeypatch, instrument):
    manager = MagicMock()
    manager.open_resource.return_value = instrument
    factory = MagicMock(return_value=manager)
    monkeypatch.setattr(pyvisa, 'ResourceManager', factory)
    return factory, manager


@pytest.mark.parametrize('backend', [None, '@py'])
async def test_connect_configures_resource_and_is_idempotent(
    visa,
    instrument,
    backend,
):
    factory, manager = visa
    client = Client(
        RESOURCE,
        backend=backend,
        open_timeout=123,
        io_timeout=456,
        read_termination='\r\n',
        write_termination='\r',
        encoding='ascii',
        chunk_size=2048,
        queue_size=2,
    )
    try:
        await client.connect()
        await client.connect()
        factory.assert_called_once_with(*([backend] if backend else []))
        manager.open_resource.assert_called_once_with(
            RESOURCE,
            open_timeout=123,
            resource_pyclass=pyvisa.resources.MessageBasedResource,
        )
        assert (
            instrument.timeout,
            instrument.read_termination,
            instrument.write_termination,
            instrument.encoding,
            instrument.chunk_size,
        ) == (456, '\r\n', '\r', 'ascii', 2048)
        assert client._worker._queue.maxsize == 2
        assert await client.write('*CLS') == 8
        assert await client.read() == 'response'
        assert await client.query('*OPC?') == '1'
        instrument.write.assert_called_once_with('*CLS')
        instrument.query.assert_called_once_with('*OPC?')
    finally:
        await client.close()
    instrument.close.assert_called_once_with()
    manager.close.assert_called_once_with()


@pytest.mark.parametrize(
    'method,args',
    [('write', ('*CLS',)), ('read', ()), ('query', ('*IDN?',))],
)
async def test_operations_require_connection(method, args):
    with pytest.raises(ClientConnectionError, match='not connected'):
        await getattr(Client(RESOURCE), method)(*args)


async def test_close_before_connect_is_idempotent_and_terminal(visa):
    client = Client(RESOURCE)
    await client.close()
    await client.close()
    with pytest.raises(ClientConnectionError, match='already closed'):
        await client.connect()
    visa[0].assert_not_called()


async def test_context_manager_closes_even_on_body_exception(visa, instrument):
    client = Client(RESOURCE)
    with pytest.raises(ValueError, match='body'):
        async with client as connected:
            assert connected is client
            raise ValueError('body')
    instrument.close.assert_called_once_with()
    visa[1].close.assert_called_once_with()
    await client.close()
    visa[1].close.assert_called_once_with()


@pytest.mark.parametrize('failure_at', ['manager', 'open'])
async def test_visa_connection_error_is_wrapped_and_cleanup_allows_retry(
    visa,
    failure_at,
):
    factory, manager = visa
    error = pyvisa.errors.VisaIOError(
        pyvisa.constants.StatusCode.error_timeout,
    )
    failing_mock = (
        factory if failure_at == 'manager' else manager.open_resource
    )
    failing_mock.side_effect = error
    client = Client(RESOURCE)
    with pytest.raises(ClientConnectionError) as caught:
        await client.connect()
    assert caught.value.__cause__ is error
    assert RESOURCE in str(caught.value)
    assert client._worker is client._instrument is client._rm is None
    assert not client._started
    assert manager.close.call_count == (failure_at == 'open')
    failing_mock.side_effect = None
    await client.connect()
    await client.close()


async def test_non_visa_open_error_is_preserved_even_if_cleanup_fails(visa):
    _, manager = visa
    error = RuntimeError('backend failed')
    manager.open_resource.side_effect = error
    manager.close.side_effect = OSError('cleanup failed')
    client = Client(RESOURCE)
    with pytest.raises(RuntimeError) as caught:
        await client.connect()
    assert caught.value is error
    assert client._rm is None
    assert not client._started


async def test_close_clears_client_when_worker_fails(visa):
    client = Client(RESOURCE)
    await client.connect()
    worker = client._worker
    await worker.close()
    from unittest.mock import AsyncMock

    worker.close = AsyncMock(side_effect=RuntimeError('worker close'))
    with pytest.raises(RuntimeError, match='worker close'):
        await client.close()
    assert client._closed
    assert not client._started
    assert client._worker is client._instrument is client._rm is None
    visa[1].close.assert_called_once_with()
