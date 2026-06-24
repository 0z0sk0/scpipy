import pytest

from scpipy.server.exceptions import (
    InvalidHandlerError,
    PatternMismatchError,
    MissingPositionalArgsError,
    MissingKeywordArgsError,
    UnexpectedKeywordArgsError,
)
from scpipy.server.route_handler import RouteHandler
from scpipy.shared.parser import Parser


def make_pattern(command: str):
    return Parser().parse(command)


def test_validate_call_with_variadic_values():
    pattern = make_pattern(
        'SOURce<channel>:POWer<some>[:LEVel][:IMMediate][:AMPLitude] <values>'
    )

    def handler(context, channel: int, some: int, *values):
        return channel, some, values

    route_handler = RouteHandler(handler=handler, pattern=pattern)
    context = object()

    bound = route_handler.validate_call(
        context=context,
        args=('3', '4', '5', '6'),
        kwargs={'channel': '1', 'some': '2'},
    )

    assert bound.args == (context, '1', '2', '3', '4', '5', '6')
    assert bound.kwargs == {}


def test_invoke_with_variadic_values():
    pattern = make_pattern(
        'SOURce<channel>:POWer<some>[:LEVel][:IMMediate][:AMPLitude] <values>'
    )

    def handler(context, channel: int, some: int, *values):
        return channel, some, values

    route_handler = RouteHandler(handler=handler, pattern=pattern)

    result = route_handler.invoke(
        object(),
        '3',
        '4',
        '5',
        '6',
        channel='1',
        some='2',
    )

    assert result == ('1', '2', ('3', '4', '5', '6'))


def test_missing_context_raises():
    pattern = make_pattern(
        'SOURce<channel>:POWer<some>[:LEVel][:IMMediate][:AMPLitude] <values>'
    )

    def handler(context, channel: int, some: int, *values):
        return channel, some, values

    route_handler = RouteHandler(handler=handler, pattern=pattern)

    with pytest.raises(
        InvalidHandlerError,
        match='Missing required context argument',
    ):
        route_handler.validate_call(
            context=None,
            args=('3', '4'),
            kwargs={'channel': '1', 'some': '2'},
        )


def test_missing_required_positional_argument_raises():
    pattern = make_pattern('SOURce<channel>:POWer<some>')

    def handler(context, channel: int, some: int):
        return channel, some

    route_handler = RouteHandler(handler=handler, pattern=pattern)

    with pytest.raises(
        MissingPositionalArgsError,
        match='missing required positional argument: some',
    ):
        route_handler.validate_call(
            context=object(),
            args=(),
            kwargs={'channel': '1'},
        )


def test_missing_required_keyword_only_argument_raises():
    pattern = make_pattern('SOURce<channel>:POWer<some>')

    def handler(context, channel: int, some: int, *, mode):
        return channel, some, mode

    route_handler = RouteHandler(handler=handler, pattern=pattern)

    with pytest.raises(
        MissingKeywordArgsError,
        match='missing required keyword argument: mode',
    ):
        route_handler.validate_call(
            context=object(),
            args=(),
            kwargs={'channel': '1', 'some': '2'},
        )


def test_unexpected_keyword_argument_raises():
    pattern = make_pattern('SOURce<channel>:POWer<some>')

    def handler(context, channel: int, some: int):
        return channel, some

    route_handler = RouteHandler(handler=handler, pattern=pattern)

    with pytest.raises(
        UnexpectedKeywordArgsError,
        match='got unexpected keyword arguments: extra',
    ):
        route_handler.validate_call(
            context=object(),
            args=(),
            kwargs={'channel': '1', 'some': '2', 'extra': 'boom'},
        )


def test_invalid_handler_without_context_raises():
    pattern = make_pattern('SOURce<channel>:POWer<some>')

    def handler(channel: int, some: int):
        return channel, some

    with pytest.raises(
        InvalidHandlerError,
        match='Handler must accept context as its first parameter.',
    ):
        RouteHandler(handler=handler, pattern=pattern)


def test_pattern_mismatch_raises_on_registration():
    pattern = make_pattern('SOURce<channel>:POWer<some>')

    def handler(context, channel: int):
        return channel

    with pytest.raises(PatternMismatchError):
        RouteHandler(handler=handler, pattern=pattern)
