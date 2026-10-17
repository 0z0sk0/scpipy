import asyncio

import pytest

from scpipy.server.builtin_router import builtin_router
from scpipy.server.context import Context
from scpipy.server.dispatcher import Dispatcher
from scpipy.shared.errors import ScpiException
from scpipy.shared.parser import Parser

pytestmark = pytest.mark.asyncio


@pytest.fixture
def dispatcher():
    return Dispatcher(builtin_router, '\n')


@pytest.mark.parametrize(
    'write,read,expected',
    [
        ('*ESE 255', '*ESE?', 255),
        ('*SRE 255', '*SRE?', 191),
        ('*SRE 64', '*SRE?', 0),
        ('*ESE +3.2E1', '*ESE?', 32),
        ('*ESE 31.7', '*ESE?', 32),
        ('*ESE 2.5', '*ESE?', 2),
        ('*ESE #HFF', '*ESE?', 255),
        ('*ESE #h20', '*ESE?', 32),
        ('*ESE #Q40', '*ESE?', 32),
        ('*ESE #B100000', '*ESE?', 32),
        ('STAT:OPER:ENAB 65535', 'STAT:OPER:ENAB?', 32767),
        ('STAT:OPER:ENAB 32768', 'STAT:OPER:ENAB?', 0),
        ('STAT:QUES:PTR #HFFFF', 'STAT:QUES:PTR?', 32767),
        ('STAT:QUES:NTR 8.0E0', 'STAT:QUES:NTR?', 8),
        ('status:operation:enable 8', 'status:operation:enable?', 8),
    ],
)
async def test_register_write_and_query(dispatcher, write, read, expected):
    context = Context()
    assert await dispatcher._dispatch(context, write.encode()) is None
    assert (
        await dispatcher._dispatch(context, read.encode())
        == f'{expected}\n'.encode()
    )


@pytest.mark.parametrize(
    'command,code',
    [
        ('*ESE -1', -222),
        ('*ESE 256', -222),
        ('*SRE 256', -222),
        ('STAT:OPER:ENAB 65536', -222),
        ('STAT:QUES:PTR -1', -222),
        ('*ESE 1E99999', -222),
        ('*ESE 1E999999999999999999999', -222),
        ('*ESE MAX', -104),
        ('*ESE NAN', -104),
        ('*ESE "32"', -104),
        ('*ESE #HZZ', -104),
        ('*ESE #B2', -104),
        ('*ESE #Q8', -104),
        ('*ESE 1_0', -104),
        ('*ESE 1V', -104),
        ('*ESE', -109),
        ('*ESE 1,2', -108),
        ('*ESE? 1', -108),
        ('*ESR', -110),
        ('*STB', -110),
        ('STAT:PRES?', -110),
        ('STAT:OPER:COND 1', -110),
        ('STAT:QUES:EVEN 1', -110),
        ('*ES 32', -110),
        ('*SR 32', -110),
        ('*WA', -110),
    ],
)
async def test_invalid_arguments_raise_scpi_errors_without_mutating_register(
    dispatcher,
    command,
    code,
):
    context = Context()
    context.status.event_enable = 3
    with pytest.raises(ScpiException) as caught:
        await dispatcher._dispatch(context, command.encode())
    assert caught.value.error.code == code
    assert context.status.event_enable == 3


@pytest.mark.parametrize('group', ['OPER', 'QUES'])
@pytest.mark.parametrize('event_suffix', ['', ':EVEN', ':EVENt'])
async def test_event_query_optional_node_clears_but_condition_read_does_not(
    dispatcher,
    group,
    event_suffix,
):
    context = Context()
    register = (
        context.status.operation
        if group == 'OPER'
        else context.status.questionable
    )
    register.set_condition(5)
    assert (
        await dispatcher._dispatch(context, f'STAT:{group}:COND?'.encode())
        == b'5\n'
    )
    assert (
        await dispatcher._dispatch(context, f'STAT:{group}:COND?'.encode())
        == b'5\n'
    )
    assert (
        await dispatcher._dispatch(
            context,
            f'STAT:{group}{event_suffix}?'.encode(),
        )
        == b'5\n'
    )
    assert (
        await dispatcher._dispatch(context, f'STAT:{group}?'.encode())
        == b'0\n'
    )


async def test_status_initialization_block_and_opc_query_do_not_set_esr_bit(
    dispatcher,
):
    context = Context()
    response = await dispatcher._dispatch(
        context,
        b'*CLS;*ESE 1;*SRE 32;STAT:PRES;*OPC?;*ESR?;*STB?',
    )
    assert response == b'1;0;0\n'
    assert (
        await dispatcher._dispatch(context, b'*OPC;*STB?;*ESR?;*STB?')
        == b'96;1;0\n'
    )


async def test_common_commands_do_not_change_relative_status_path(dispatcher):
    context = Context()
    result = await dispatcher._dispatch(
        context,
        b'STAT:OPER:ENAB 16;*ESE 32;PTR 8;NTR 4;ENAB?',
    )
    assert result == b'16\n'
    assert context.status.operation.positive_transition == 8
    assert context.status.operation.negative_transition == 4


async def test_common_commands_have_no_abbreviations_in_ast():
    for keyword in ('*ESE', '*SRE', '*WAI'):
        node = Parser().parse(keyword)[0].nodes[0]
        assert node.short == node.full == keyword


async def test_opc_is_nonblocking_and_query_waits_for_every_operation(
    dispatcher,
):
    context = Context()
    context.clear_status()
    first = context.status.pending_operation()
    second = context.status.pending_operation()
    first.__enter__()
    second.__enter__()
    try:
        assert await dispatcher._dispatch(context, b'*OPC;*ESR?') == b'0\n'
        waiting = asyncio.create_task(dispatcher._dispatch(context, b'*OPC?'))
        await asyncio.sleep(0)
        first.__exit__(None, None, None)
        assert not waiting.done()
        second.__exit__(None, None, None)
        assert await asyncio.wait_for(waiting, 2) == b'1\n'
        assert await dispatcher._dispatch(context, b'*ESR?') == b'1\n'
    finally:
        if context.status._pending:
            first.__exit__(None, None, None)
            second.__exit__(None, None, None)


async def test_wai_blocks_subsequent_commands_without_setting_opc(dispatcher):
    context = Context()
    context.clear_status()
    with context.status.pending_operation():
        waiting = asyncio.create_task(
            dispatcher._dispatch(context, b'*WAI;*ESE 32;*ESR?'),
        )
        await asyncio.sleep(0)
        assert not waiting.done()
        assert context.status.event_enable == 0
    assert await asyncio.wait_for(waiting, 2) == b'0\n'
    assert context.status.event_enable == 32


async def test_decimal_traps_disabled(dispatcher):
    from decimal import InvalidOperation, localcontext

    with localcontext() as decimal_context:
        decimal_context.traps[InvalidOperation] = False
        with pytest.raises(ScpiException) as caught:
            await dispatcher._dispatch(
                Context(),
                b'*ESE 1E999999999999999999999',
            )
    assert caught.value.error.code == -222


async def test_cls_abandons_pending_opc_query_without_a_response(dispatcher):
    context = Context()
    with context.status.pending_operation():
        query = asyncio.create_task(
            dispatcher._dispatch(context, b'*OPC?'),
        )
        await asyncio.sleep(0)
        assert not query.done()
        assert await dispatcher._dispatch(context, b'*CLS') is None
        assert await asyncio.wait_for(query, 2) is None
    assert context.status.event_status == 0
