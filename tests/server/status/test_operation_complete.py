import asyncio

import pytest

from scpipy.server.status.system import StatusSystem


def test_opc_without_pending_operations_latches_immediately():
    status = StatusSystem()
    status.clear()
    status.request_operation_complete()
    assert status.read_event_status() == 1


def test_opc_waits_for_all_tracked_operations_and_cls_disarms():
    status = StatusSystem()
    status.clear()
    with status.pending_operation():
        with status.pending_operation():
            status.request_operation_complete()
        assert status.event_status == 0
    assert status.read_event_status() == 1
    with status.pending_operation():
        status.request_operation_complete()
        status.clear()
    assert status.event_status == 0


def test_opc_does_not_wait_for_operations_started_after_the_command():
    status = StatusSystem()
    status.clear()
    first = status.pending_operation()
    second = status.pending_operation()
    with first:
        status.request_operation_complete()
        second.__enter__()
    try:
        assert status.read_event_status() == 1
    finally:
        second.__exit__(None, None, None)
    assert status.event_status == 0


@pytest.mark.asyncio
async def test_wait_without_work_returns_without_setting_opc_bit():
    status = StatusSystem()
    status.clear()
    assert await status.wait_for_operations()
    assert status.event_status == 0


@pytest.mark.asyncio
async def test_wait_operations_captures_snapshot_not_later_work():
    status = StatusSystem()
    status.clear()
    later = status.pending_operation()
    with status.pending_operation():
        waiting = asyncio.create_task(status.wait_for_operations())
        await asyncio.sleep(0)
        assert not waiting.done()
        later.__enter__()
    try:
        assert await asyncio.wait_for(waiting, 2)
        assert status.event_status == 0
    finally:
        later.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_cls_aborts_opc_query_but_not_wai_waiter():
    status = StatusSystem()
    with status.pending_operation():
        query = asyncio.create_task(
            status.wait_for_operations(cancel_on_clear=True),
        )
        wai = asyncio.create_task(status.wait_for_operations())
        await asyncio.sleep(0)
        status.clear()
        assert await asyncio.wait_for(query, 2) is False
        assert not wai.done()
    assert await asyncio.wait_for(wai, 2) is True
    assert status.event_status == 0


@pytest.mark.asyncio
async def test_cancelled_waiter_is_removed_without_cancelling_operation():
    status = StatusSystem()
    status.clear()
    with status.pending_operation():
        waiting = asyncio.create_task(status.wait_for_operations())
        await asyncio.sleep(0)
        waiting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiting
        assert status._waiters == []
        status.request_operation_complete()
    assert status.event_status == 1


@pytest.mark.asyncio
async def test_start_operation_registers_before_coroutine_first_runs():
    status = StatusSystem()
    status.clear()
    release = asyncio.Event()
    task = status.start_operation(release.wait())
    status.request_operation_complete()
    assert status.event_status == 0
    release.set()
    await task
    await asyncio.sleep(0)
    assert status.read_event_status() == 1
    assert not status._pending


@pytest.mark.asyncio
async def test_background_cancel_before_first_entry_does_not_leak_barrier():
    status = StatusSystem()
    status.clear()
    task = status.start_operation(asyncio.sleep(1000))
    status.request_operation_complete()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert await asyncio.wait_for(status.wait_for_operations(), 2)
    assert not status._pending
    assert status.read_event_status() == 1


@pytest.mark.asyncio
async def test_failed_background_operation_finishes_barrier():
    status = StatusSystem()
    status.clear()

    async def fail():
        raise ValueError('measurement failed')

    task = status.start_operation(fail())
    status.request_operation_complete()
    with pytest.raises(ValueError, match='measurement failed'):
        await task
    assert await asyncio.wait_for(status.wait_for_operations(), 2)
    assert status.event_status == 1


def test_scope_exit_on_exception_completes_pending_operation():
    status = StatusSystem()
    status.clear()
    with pytest.raises(RuntimeError):
        with status.pending_operation():
            status.request_operation_complete()
            raise RuntimeError('operation ended with error')
    assert status.event_status == 1
