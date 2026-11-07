import pytest

from scpipy.server.context import Context
from scpipy.server.exceptions import InvalidHandlerError, RouteNotFound
from scpipy.server.routing import Route, Router


def test_registration_lookup_and_invocation():
    router = Router()

    @router.register('SOURce<channel>:VOLTage <value>')
    def set_voltage(context, value, *, channel=1):
        context.state[channel] = value

    route = router.route('SOURce<channel>:VOLTage <value>')
    assert route.handler is set_voltage
    direct_context = Context()
    assert set_voltage(direct_context, '5', channel='3') is None
    assert direct_context.state == {'3': '5'}

    context = Context()
    assert route.invoke(context, '10', channel='2') is None
    assert context.state == {'2': '10'}
    assert route.pattern.nodes[0].arg.value == 'channel'


def test_stacked_registration_keeps_handler():
    router = Router()

    @router.register('FIRST?')
    @router.register('SECOND?')
    def handler(context):
        return 'ok'

    assert handler(Context()) == 'ok'
    for command in ('FIRST?', 'SECOND?'):
        route = router.route(command)
        assert route.handler is handler
        assert route.invoke(Context()) == 'ok'


def test_missing_route_raises():
    with pytest.raises(RouteNotFound):
        Router().route('UNKNOWN?')


def test_equivalent_patterns_are_rejected_but_query_and_set_are_distinct():
    router = Router()
    handler = lambda context: 1
    router.add_route('SYSTem:READy?', handler)
    with pytest.raises(ValueError, match='already registered'):
        router.add_route('system:ready?', handler)
    router.add_route('SYSTem:READy', handler)
    assert len(router.routes) == 2


@pytest.mark.parametrize('commands', ['SYST:ERR?;*CLS', ';'])
def test_route_requires_one_command(commands):
    with pytest.raises(ValueError, match='exactly one command'):
        Route(commands, lambda context: None)


@pytest.mark.parametrize('as_iterable', [False, True])
def test_include_router_copies_routes_without_mutating_source(as_iterable):
    first, second = Router(), Router()
    first.add_route('*IDN?', lambda context: 'id')
    second.include_router([first] if as_iterable else first)
    assert second.route('*IDN?').invoke(Context()) == 'id'
    second.add_route('*OPC?', lambda context: 1)
    assert len(first.routes) == 1
    with pytest.raises(ValueError, match='already registered'):
        second.include_router(first)


def test_invalid_handler_does_not_add_route():
    router = Router()
    with pytest.raises(InvalidHandlerError):
        router.add_route('*CLS', lambda: None)
    assert router.routes == {}
