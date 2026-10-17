import asyncio

import pytest

from scpipy.client.models import OperationType, QueueItem


@pytest.mark.asyncio
async def test_queue_item_keeps_operation_payload_and_completion_future():
    future = asyncio.get_running_loop().create_future()
    item = QueueItem(OperationType.QUERY, '*IDN?', future)
    assert item.type is OperationType.QUERY
    assert item.value == '*IDN?'
    assert item.future is future
    item.future.set_result('model')
    assert await future == 'model'
    assert len(set(OperationType)) == 4
