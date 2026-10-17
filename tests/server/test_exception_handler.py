import pytest

from scpipy.server.context import Context
from scpipy.server.exception_handler import ExceptionHandler
from scpipy.server.exceptions import (
    MissingPositionalArgsError,
    ParserSyntaxError,
    RouteNotFound,
    UnexpectedKeywordArgsError,
    UnexpectedPositionalArgsError,
)
from scpipy.shared.errors import DefaultScpiErrors, ScpiError, ScpiException
from scpipy.shared.parser import Parser


@pytest.mark.parametrize(
    'exception,expected',
    [
        (ParserSyntaxError(), DefaultScpiErrors.SYNTAX_ERROR),
        (RouteNotFound(), DefaultScpiErrors.COMMAND_HEADER_ERROR),
        (MissingPositionalArgsError(), DefaultScpiErrors.MISSING_PARAMETER),
        (
            UnexpectedPositionalArgsError(),
            DefaultScpiErrors.PARAMETER_NOT_ALLOWED,
        ),
        (
            UnexpectedKeywordArgsError(),
            DefaultScpiErrors.PARAMETER_NOT_ALLOWED,
        ),
    ],
)
def test_default_mapping(exception, expected):
    assert (
        ExceptionHandler().resolve(exception, Context(), None)
        == expected.value
    )


def test_scpi_exception_preserves_original_error():
    error = ScpiError(-200, 'custom')
    assert (
        ExceptionHandler().resolve(ScpiException(error), Context(), None)
        is error
    )


def test_unknown_exception_is_reraised_unchanged():
    error = RuntimeError('unknown')
    with pytest.raises(RuntimeError) as caught:
        ExceptionHandler().resolve(error, Context(), None)
    assert caught.value is error


def test_handlers_support_decorator_direct_registration_and_mro():
    handlers = ExceptionHandler()
    context = Context()
    command = Parser().parse('SYST:ERR?')[0]
    seen = []

    @handlers.add_exception_handler(Exception)
    def base(exc, ctx, cmd):
        seen.append((exc, ctx, cmd))
        return ScpiError(-200, 'base')

    class SpecificError(ValueError):
        pass

    def specific(exc, ctx, cmd):
        return ScpiError(-201, 'specific')

    assert handlers.add_exception_handler(ValueError, specific) is specific
    assert handlers.resolve(SpecificError(), context, command).code == -201
    error = RuntimeError()
    assert handlers.resolve(error, context, command).code == -200
    assert seen == [(error, context, command)]
    # The broad fallback must not replace a more specific built-in mapping.
    assert handlers.resolve(ParserSyntaxError(), context, None).code == -102


def test_handler_can_override_builtin_mapping():
    handlers = ExceptionHandler()
    handlers.add_exception_handler(
        RouteNotFound,
        lambda *args: ScpiError(-222, 'override'),
    )
    assert handlers.resolve(RouteNotFound(), Context(), None).code == -222


@pytest.mark.parametrize('result', [None, 'error', -102])
def test_handler_must_return_scpi_error(result):
    handlers = ExceptionHandler()
    handlers.add_exception_handler(ValueError, lambda *args: result)
    with pytest.raises(TypeError, match='must return ScpiError'):
        handlers.resolve(ValueError(), Context(), None)


def test_handler_exception_is_not_silenced():
    handlers = ExceptionHandler()
    error = RuntimeError('handler failed')

    def handler(*args):
        raise error

    handlers.add_exception_handler(ValueError, handler)
    with pytest.raises(RuntimeError) as caught:
        handlers.resolve(ValueError(), Context(), None)
    assert caught.value is error
