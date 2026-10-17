import pytest

from scpipy.server.builtin_router import builtin_router
from scpipy.server.context import Context
from scpipy.server.dispatcher import Dispatcher
from scpipy.shared.errors import DefaultScpiErrors, ScpiError, ScpiException

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    'query',
    ['SYST:ERR?', 'SYSTem:ERRor?', 'system:error:next?'],
)
async def test_system_error_pops_one_entry_then_returns_no_error(query):
    context = Context()
    context.push_error(ScpiError(-102, 'Syntax error'))
    dispatcher = Dispatcher(builtin_router, '\n')
    assert (
        await dispatcher._dispatch(context, query.encode())
        == b'-102,"Syntax error"\n'
    )
    assert (
        await dispatcher._dispatch(context, query.encode())
        == b'0,"No error"\n'
    )


async def test_cls_clears_queue_without_reply_or_changing_state():
    context = Context(state={'value': 42})
    context.push_error(ScpiError(-102, 'Syntax error'))
    dispatcher = Dispatcher(builtin_router, '\n')
    assert await dispatcher._dispatch(context, b'*cls') is None
    assert context.state == {'value': 42}
    assert (
        await dispatcher._dispatch(context, b'SYST:ERR?') == b'0,"No error"\n'
    )


@pytest.mark.parametrize(
    'command,error',
    [
        ('*CLS?', DefaultScpiErrors.COMMAND_HEADER_ERROR),
        ('*CLS 1', DefaultScpiErrors.PARAMETER_NOT_ALLOWED),
    ],
)
async def test_cls_rejects_query_and_arguments(command, error):
    with pytest.raises(ScpiException) as caught:
        await Dispatcher(builtin_router, '\n')._dispatch(
            Context(),
            command.encode(),
        )
    assert caught.value.error == error.value
