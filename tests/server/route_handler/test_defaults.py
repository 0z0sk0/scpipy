import pytest

from scpipy.server.route_handler import RouteHandler


class Context:
    pass


@pytest.fixture
def context():
    return Context()


@pytest.fixture
def handler():
    def _handler(context, value, *, channel=1, some=7):
        return context, value, channel, some

    return _handler


@pytest.fixture
def route(defaults_pattern, handler):
    return RouteHandler(handler=handler, pattern=defaults_pattern)


@pytest.mark.parametrize(
    ('kwargs', 'expected'),
    [
        ({}, {'channel': 1, 'some': 7, 'value': '10'}),
        ({'channel': '2'}, {'channel': '2', 'some': 7, 'value': '10'}),
        ({'some': '3'}, {'channel': 1, 'some': '3', 'value': '10'}),
        (
            {'channel': '2', 'some': '3'},
            {'channel': '2', 'some': '3', 'value': '10'},
        ),
    ],
)
def test_validate_call_applies_node_defaults(context, route, kwargs, expected):
    bound = route.validate_call(context=context, args=('10',), kwargs=kwargs)

    assert bound.arguments['context'] is context
    assert bound.arguments['value'] == expected['value']
    assert bound.arguments['channel'] == expected['channel']
    assert bound.arguments['some'] == expected['some']


@pytest.mark.parametrize(
    ('kwargs', 'expected'),
    [
        ({}, '1,7,10'),
        ({'channel': '2'}, '2,7,10'),
        ({'some': '3'}, '1,3,10'),
        ({'channel': '2', 'some': '3'}, '2,3,10'),
    ],
)
def test_invoke_uses_default_node_values(
    context, defaults_pattern, kwargs, expected
):
    def _handler(context, value, *, channel=1, some=7):
        return f'{channel},{some},{value}'

    route = RouteHandler(handler=_handler, pattern=defaults_pattern)

    assert route.invoke(context, '10', **kwargs) == expected


def test_default_node_values_work_with_keyword_only_params(
    context, defaults_pattern
):
    def _handler(context, value, *, channel=11, some=22):
        return f'{channel},{some},{value}'

    route = RouteHandler(handler=_handler, pattern=defaults_pattern)

    assert route.invoke(context, '5') == '11,22,5'


def test_explicit_node_value_overrides_default(context, defaults_pattern):
    def _handler(context, value, *, channel=11, some=22):
        return f'{channel},{some},{value}'

    route = RouteHandler(handler=_handler, pattern=defaults_pattern)

    assert route.invoke(context, '5', channel='9') == '9,22,5'


def test_explicit_none_does_not_trigger_default(context, defaults_pattern):
    def _handler(context, value, *, channel=11, some=22):
        return channel, some, value

    route = RouteHandler(handler=_handler, pattern=defaults_pattern)

    assert route.invoke(context, '5', some=None) == (11, None, '5')


def test_command_arg_stays_positional(context, defaults_pattern):
    def _handler(context, value, *, channel=1, some=7):
        return value, channel, some

    route = RouteHandler(handler=_handler, pattern=defaults_pattern)

    assert route.invoke(context, '123', channel='9') == ('123', '9', 7)
