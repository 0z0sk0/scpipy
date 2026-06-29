import pytest

from scpipy.server.exceptions import (
    InvalidHandlerError,
    MissingKeywordArgsError,
    UnexpectedKeywordArgsError,
)
from scpipy.server.route_handler import RouteHandler


def test_init_requires_context_as_first_argument(simple_pattern):
    def handler(channel: int, some: int):
        return channel, some

    with pytest.raises(
        InvalidHandlerError,
        match='Handler must accept context as its first parameter.',
    ):
        RouteHandler(handler=handler, pattern=simple_pattern)


def test_init_rejects_invalid_context_kind(simple_pattern):
    def handler(*, context, channel: int, some: int):
        return channel, some

    with pytest.raises(
        InvalidHandlerError,
        match='Handler context argument must be positional.',
    ):
        RouteHandler(handler=handler, pattern=simple_pattern)


def test_init_raises_unexpected_keyword_args(simple_pattern):
    def handler(context, channel: int):
        return channel

    with pytest.raises(
        UnexpectedKeywordArgsError,
        match='got unexpected keyword arguments: some',
    ):
        RouteHandler(handler=handler, pattern=simple_pattern)


def test_init_accepts_variadic_handler(variadic_pattern):
    def handler(context, channel: int, some: int, *values):
        return channel, some, values

    route_handler = RouteHandler(handler=handler, pattern=variadic_pattern)

    assert route_handler.handler is handler


def test_init_raises_missing_keyword_args_for_required_keyword_only_arg(
    simple_pattern,
):
    def handler(context, channel: int, some: int, *, mode):
        return channel, some, mode

    with pytest.raises(
        MissingKeywordArgsError,
        match='missing required keyword argument: mode',
    ):
        RouteHandler(handler=handler, pattern=simple_pattern)
