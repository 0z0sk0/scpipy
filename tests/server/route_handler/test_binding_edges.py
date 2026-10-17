import pytest

from scpipy.server.context import Context
from scpipy.server.exceptions import (
    InvalidHandlerError,
    MissingPositionalArgsError,
    UnexpectedPositionalArgsError,
)
from scpipy.server.route_handler import RouteHandler
from scpipy.shared.parser import Parser


def test_positional_only_value_is_forwarded():
    def handler(context, value, /):
        return context, value

    route = RouteHandler(handler, Parser().parse('VOLTage <value>')[0])
    context = Context()
    assert route.invoke(context, '12') == (context, '12')
    with pytest.raises(MissingPositionalArgsError):
        route.invoke(context)


def test_extra_positional_arguments_are_rejected():
    route = RouteHandler(lambda context: None, Parser().parse('*CLS')[0])
    with pytest.raises(UnexpectedPositionalArgsError):
        route.invoke(Context(), 'unexpected')


def test_variadic_keyword_bindings_are_preserved():
    route = RouteHandler(
        lambda context, **kwargs: kwargs,
        Parser().parse('SOURce<channel>:POWer<port>')[0],
    )
    assert route.invoke(Context(), channel='2', port='3') == {
        'channel': '2',
        'port': '3',
    }


def test_empty_handler_signature_is_rejected():
    with pytest.raises(InvalidHandlerError):
        RouteHandler(lambda: None, Parser().parse('*CLS')[0])
