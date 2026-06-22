from collections.abc import Callable

from scpipy.server.context import Context
from scpipy.server.exceptions import (
    RouteNotFound,
    ArgumentBindingError,
    ParserSyntaxError,
)

from scpipy.shared.ast import Command
from scpipy.shared.errors import (
    ScpiError,
    ScpiException,
    DefaultScpiErrors,
)

ExceptionHandler = Callable[[Exception, Context, Command | None], ScpiError]


class ExceptionHandler:
    """
    Store and resolve exception handlers for SCPI dispatching.
    """

    def __init__(self):
        self._handlers: dict[type[Exception], ExceptionHandler] = {}
        self._register_default_exceptions()

    def _register_default_exceptions(self):
        self._handlers[ScpiException] = self._handle_scpi_exception
        self._handlers[ParserSyntaxError] = self._handle_parse_error
        self._handlers[RouteNotFound] = self._handle_route_not_found
        self._handlers[ArgumentBindingError] = (
            self._handle_argument_binding_error
        )

    def add_exception_handler(
        self,
        exc_type: type[Exception],
        handler: ExceptionHandler | None = None,
    ):
        """
        Register an exception handler.

        :param exc_type: Exception type handled by the callback.
        :type exc_type: type[Exception]
        :param handler: Callback that converts an exception into a SCPI error.
        :type handler: ExceptionHandler | None

        :return: Registered handler or decorator wrapper.
        :rtype: ExceptionHandler
        """
        if handler is not None:
            self._handlers[exc_type] = handler
            return handler

        def wrapper(func: ExceptionHandler):
            self._handlers[exc_type] = func
            return func

        return wrapper

    def resolve(
        self,
        exc: Exception,
        context: Context,
        command: Command | None,
    ) -> ScpiError:
        """
        Resolve an exception into a SCPI error.

        :param exc: Raised exception.
        :type exc: Exception
        :param context: Current execution context.
        :type context: Context
        :param command: Parsed command being processed, if available.
        :type command: Command | None

        :return: Mapped SCPI error.
        :rtype: ScpiError

        :raises Exception: Re-raises the exception if no handler is registered.
        :raises TypeError: If a handler returns a non-SCPI error value.
        """
        handler = self._find_handler(type(exc))
        if handler is None:
            raise exc

        mapped = handler(exc, context, command)
        if not isinstance(mapped, ScpiError):
            raise TypeError('Exception handler must return ScpiError')

        return mapped

    def _find_handler(
        self,
        exc_type: type[Exception],
    ) -> ExceptionHandler | None:
        for cls in exc_type.__mro__:
            handler = self._handlers.get(cls)
            if handler is not None:
                return handler
        return None

    @staticmethod
    def _handle_scpi_exception(
        exc: Exception,
        context: Context,
        command: Command | None,
    ) -> ScpiError:
        assert isinstance(exc, ScpiException)
        return exc.error

    @staticmethod
    def _handle_parse_error(
        exc: Exception,
        context: Context,
        command: Command | None,
    ) -> ScpiError:
        return DefaultScpiErrors.SYNTAX_ERROR.value

    @staticmethod
    def _handle_route_not_found(
        exc: Exception,
        context: Context,
        command: Command | None,
    ) -> ScpiError:
        return DefaultScpiErrors.COMMAND_HEADER_ERROR.value

    @staticmethod
    def _handle_argument_binding_error(
        exc: Exception,
        context: Context,
        command: Command | None,
    ) -> ScpiError:
        return DefaultScpiErrors.DATA_TYPE_ERROR.value
