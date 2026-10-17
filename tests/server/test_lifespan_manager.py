from contextlib import asynccontextmanager

import pytest

from scpipy.server.lifespan_manager import LifespanManager

pytestmark = pytest.mark.asyncio


async def test_no_lifespan_is_noop():
    manager = LifespanManager(None)
    await manager.startup(object())
    await manager.shutdown()
    assert manager.state == {}


async def test_lifespan_merges_state_and_exits_once():
    events = []
    target = object()

    @asynccontextmanager
    async def lifespan(actual):
        assert actual is target
        events.append('startup')
        yield {'instrument': 'fake'}
        events.append('shutdown')

    manager = LifespanManager(lifespan)
    state = manager.state
    state['existing'] = 1
    await manager.startup(target)
    assert manager.state is state
    assert state == {'existing': 1, 'instrument': 'fake'}
    await manager.shutdown()
    await manager.shutdown()
    assert events == ['startup', 'shutdown']
    assert state == {}


@pytest.mark.parametrize('state', [None, 123, ['not', 'a', 'dict']])
async def test_non_dictionary_yield_does_not_modify_state(state):
    @asynccontextmanager
    async def lifespan(target):
        yield state

    manager = LifespanManager(lifespan)
    await manager.startup(object())
    assert manager.state == {}
    await manager.shutdown()


async def test_shutdown_failure_still_clears_context_and_state():
    @asynccontextmanager
    async def lifespan(target):
        yield {'ready': True}
        raise RuntimeError('shutdown')

    manager = LifespanManager(lifespan)
    await manager.startup(object())
    with pytest.raises(RuntimeError, match='shutdown'):
        await manager.shutdown()
    assert manager.state == {}
    await manager.shutdown()


async def test_startup_error_is_preserved():
    @asynccontextmanager
    async def lifespan(target):
        raise ValueError('startup')
        yield

    with pytest.raises(ValueError, match='startup'):
        await LifespanManager(lifespan).startup(object())
