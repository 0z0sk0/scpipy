import pytest

from scpipy.server.exceptions import (
    InvalidHandlerError,
    MissingPositionalArgsError,
    UnexpectedKeywordArgsError,
)
from scpipy.server.route_handler import RouteHandler


def test_validate_call_with_variadic_values(variadic_pattern):
    def handler(context, channel: int, some: int, *values):
        return channel, some, values

    route_handler = RouteHandler(handler=handler, pattern=variadic_pattern)
    context = object()

    bound = route_handler.validate_call(
        context=context,
        args=('3', '4', '5', '6'),
        kwargs={'channel': '1', 'some': '2'},
    )

    assert bound.args == (context, '1', '2', '3', '4', '5', '6')
    assert bound.kwargs == {}


def test_validate_call_raises_on_missing_context(variadic_pattern):
    def handler(context, channel: int, some: int, *values):
        return channel, some, values

    route_handler = RouteHandler(handler=handler, pattern=variadic_pattern)

    with pytest.raises(
        InvalidHandlerError,
        match='Missing required context argument',
    ):
        route_handler.validate_call(
            context=None,
            args=('3', '4'),
            kwargs={'channel': '1', 'some': '2'},
        )


def test_validate_call_raises_on_missing_required_positional_arg(
    simple_pattern,
):
    def handler(context, channel: int, some: int):
        return channel, some

    route_handler = RouteHandler(handler=handler, pattern=simple_pattern)

    with pytest.raises(
        MissingPositionalArgsError,
        match='missing required positional argument: some',
    ):
        route_handler.validate_call(
            context=object(),
            args=(),
            kwargs={'channel': '1'},
        )


def test_validate_call_raises_on_unexpected_keyword_arg(simple_pattern):
    def handler(context, channel: int, some: int):
        return channel, some

    route_handler = RouteHandler(handler=handler, pattern=simple_pattern)

    with pytest.raises(
        UnexpectedKeywordArgsError,
        match='got unexpected keyword arguments: extra',
    ):
        route_handler.validate_call(
            context=object(),
            args=(),
            kwargs={'channel': '1', 'some': '2', 'extra': 'x'},
        )
