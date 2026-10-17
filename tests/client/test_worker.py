import asyncio

import pytest
import pyvisa

from scpipy.client.exceptions import ClientConnectionError, ClientStopped
from scpipy.client.models import OperationType, QueueItem
from scpipy.client.worker import Worker

pytestmark = pytest.mark.asyncio


async def test_worker_serializes_concurrent_operations(instrument):
    calls = []
    instrument.write.side_effect = lambda command: (
        calls.append(('write', command)) or 4
    )
    instrument.query.side_effect = lambda command: (
        calls.append(('query', command)) or '42'
    )
    instrument.read.side_effect = lambda: (
        calls.append(('read', None)) or 'data'
    )
    worker = Worker(instrument, queue_size=1)
    worker.start()
    original_task = worker._task
    worker.start()
    assert worker._task is original_task
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                worker.write('*CLS'),
                worker.query('*OPC?'),
                worker.read(),
            ),
            2,
        )
        assert results == [4, '42', 'data']
        assert calls == [('write', '*CLS'), ('query', '*OPC?'), ('read', None)]
    finally:
        await asyncio.wait_for(worker.close(), 2)
    instrument.close.assert_called_once_with()
    await worker.close()
    assert worker._queue.empty()


@pytest.mark.parametrize(
    'method,args',
    [('write', ('*CLS',)), ('read', ()), ('query', ('*OPC?',))],
)
async def test_worker_rejects_operations_before_start_and_after_close(
    instrument,
    method,
    args,
):
    worker = Worker(instrument)
    with pytest.raises(ClientConnectionError, match='not started'):
        await getattr(worker, method)(*args)
    worker.start()
    await worker.close()
    with pytest.raises(ClientConnectionError, match='already closed'):
        await getattr(worker, method)(*args)


async def test_worker_rejects_submissions_during_close(instrument):
    worker = Worker(instrument)
    worker.start()
    entered, release = asyncio.Event(), asyncio.Event()
    original = worker._execute_item

    async def execute(item):
        entered.set()
        await release.wait()
        return await original(item)

    worker._execute_item = execute
    operation = asyncio.create_task(worker.read())
    await asyncio.wait_for(entered.wait(), 2)
    closing = asyncio.create_task(worker.close())
    try:
        await asyncio.sleep(
            0,
        )
        with pytest.raises(ClientConnectionError, match='closing'):
            await worker.query('*IDN?')
    finally:
        release.set()
        await asyncio.wait_for(asyncio.gather(operation, closing), 2)


@pytest.mark.parametrize(
    'error',
    [RuntimeError('io failed'), pyvisa.errors.VisaIOError(-1073807339)],
)
async def test_operation_error_does_not_kill_worker(instrument, error):
    instrument.query.side_effect = [error, 'ok']
    worker = Worker(instrument)
    worker.start()
    try:
        with pytest.raises(type(error)) as caught:
            await worker.query('*OPC?')
        assert caught.value is error
        assert await worker.query('*OPC?') == 'ok'
    finally:
        await asyncio.wait_for(worker.close(), 2)


async def test_cancelled_queued_request_does_not_kill_worker(instrument):
    worker = Worker(instrument)
    worker.start()
    entered, release = asyncio.Event(), asyncio.Event()

    async def execute(item):
        entered.set()
        await release.wait()
        return 'done'

    worker._execute_item = execute
    first = asyncio.create_task(worker.query('FIRST?'))
    await asyncio.wait_for(entered.wait(), 2)
    second = asyncio.create_task(worker.query('SECOND?'))
    await asyncio.sleep(0)
    second.cancel()
    await asyncio.gather(second, return_exceptions=True)
    release.set()
    assert await asyncio.wait_for(first, 2) == 'done'
    assert await asyncio.wait_for(worker.query('THIRD?'), 2) == 'done'
    await asyncio.wait_for(worker.close(), 2)


@pytest.mark.parametrize(
    'operation',
    [OperationType.WRITE, OperationType.QUERY],
)
async def test_missing_command_is_rejected(instrument, operation):
    worker = Worker(instrument)
    future = asyncio.get_running_loop().create_future()
    with pytest.raises(ValueError, match='requires command'):
        await worker._execute_item(QueueItem(operation, None, future))
    instrument.write.assert_not_called()
    instrument.query.assert_not_called()


async def test_unsupported_operation_is_rejected(instrument):
    item = QueueItem(
        OperationType.CLOSE,
        None,
        asyncio.get_running_loop().create_future(),
    )
    with pytest.raises(ValueError, match='Unsupported operation'):
        await Worker(instrument)._execute_item(item)


async def test_pending_operations_fail_when_worker_is_cancelled(instrument):
    worker = Worker(instrument)
    entered = asyncio.Event()

    async def execute(item):
        entered.set()
        await asyncio.Event().wait()

    worker._execute_item = execute
    worker.start()
    active = asyncio.create_task(worker.read())
    await asyncio.wait_for(entered.wait(), 2)
    pending = asyncio.create_task(worker.query('*OPC?'))
    await asyncio.sleep(0)
    try:
        worker._task.cancel()
        await asyncio.gather(worker._task, return_exceptions=True)
        with pytest.raises(ClientStopped):
            await asyncio.wait_for(pending, 2)
        await asyncio.wait_for(worker._queue.join(), 2)
    finally:
        active.cancel()
        await asyncio.gather(active, return_exceptions=True)
