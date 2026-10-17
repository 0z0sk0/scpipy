import asyncio

import pytest

from scpipy.server.context import Context
from scpipy.server.dispatcher import Dispatcher
from scpipy.server.routing import Router
from scpipy.shared.errors import DefaultScpiErrors, ScpiException


@pytest.mark.parametrize('system', ['SYST', 'SYSTEM', 'sYsTeM'])
@pytest.mark.parametrize('ready', ['READ', 'READY', 'read', 'rEaDy'])
def test_dispatch_accepts_exact_short_and_long_forms(system, ready):
    router = Router()
    router.add_route('SYSTem:READy?', lambda context: 1)
    dispatcher = Dispatcher(router, '\n')

    response = asyncio.run(
        dispatcher._dispatch(Context(), f'{system}:{ready}?'.encode()),
    )

    assert response == b'1\n'


@pytest.mark.parametrize(
    'command',
    [
        'SYST:READsadfsdfsdfsdf?',
        'SYST:READSADFSDFSDF?',
        'SYST:READout?',
        'SYST:READYY?',
        'SYSTE:READ?',
        'SYSTemExtra:READ?',
        'SYST:REA?',
        '*IDNextra?',
    ],
)
def test_dispatch_rejects_invalid_keyword_without_invoking_handler(command):
    calls = []
    router = Router()
    router.add_route('SYSTem:READy?', lambda context: calls.append(context))
    router.add_route('*IDN?', lambda context: calls.append(context))
    dispatcher = Dispatcher(router, '\n')

    with pytest.raises(ScpiException) as caught:
        asyncio.run(dispatcher._dispatch(Context(), command.encode()))

    assert caught.value.error == DefaultScpiErrors.COMMAND_HEADER_ERROR.value
    assert calls == []


@pytest.mark.parametrize(
    'command',
    [
        'SOUR2:POW?',
        'source2:power?',
        'SoUrCe2:PoWeR:LeVeL?',
        'SOUR2:POW:LEV?',
    ],
)
def test_keyword_matching_preserves_indices_and_optional_nodes(command):
    router = Router()
    router.add_route(
        'SOURce<channel>:POWer[:LEVel]?',
        lambda context, channel: channel,
    )
    dispatcher = Dispatcher(router, '\n')

    response = asyncio.run(dispatcher._dispatch(Context(), command.encode()))

    assert response == b'2\n'


@pytest.mark.parametrize(
    'command',
    ['SOURceExtra2:POW?', 'SOUR2:POWerExtra?', 'SOUR2:POW:LEVE?'],
)
def test_dispatch_rejects_invalid_indexed_or_optional_keyword(command):
    router = Router()
    router.add_route(
        'SOURce<channel>:POWer[:LEVel]?',
        lambda context, channel: channel,
    )
    dispatcher = Dispatcher(router, '\n')

    with pytest.raises(ScpiException) as caught:
        asyncio.run(dispatcher._dispatch(Context(), command.encode()))

    assert caught.value.error == DefaultScpiErrors.COMMAND_HEADER_ERROR.value


@pytest.mark.parametrize('command', ['SYST:READOUT?', 'system:readout?'])
def test_long_form_selects_correct_route_with_shared_short_form(command):
    router = Router()
    router.add_route('SYSTem:READy?', lambda context: 'ready')
    router.add_route('SYSTem:READout?', lambda context: 'readout')
    dispatcher = Dispatcher(router, '\n')

    response = asyncio.run(dispatcher._dispatch(Context(), command.encode()))

    assert response == b'readout\n'
