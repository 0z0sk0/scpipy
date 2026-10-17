import inspect
from collections.abc import Callable
from typing import TypeVar

from scpipy.server.context import Context
from scpipy.server.exceptions import (
    MissingPositionalArgsError,
    ParserSyntaxError,
    RouteNotFound,
    UnexpectedKeywordArgsError,
    UnexpectedPositionalArgsError,
)
from scpipy.shared.ast import Command
from scpipy.shared.errors import (
    DefaultScpiErrors,
    ScpiError,
    ScpiException,
)

ExceptionCallback = Callable[[Exception, Context, Command | None], ScpiError]
_Handler = TypeVar('_Handler')
_Container = TypeVar('_Container')
_HANDLES_ATTRIBUTE = '__scpipy_exception_types__'


def handles(*exc_types: type[Exception]) -> Callable[[_Handler], _Handler]:
    """Mark a method for ExceptionHandler.include_class()."""

    if not exc_types:
        raise TypeError('handles() requires at least one exception type')
    for exc_type in exc_types:
        if not isinstance(exc_type, type) or not issubclass(
            exc_type,
            Exception,
        ):
            raise TypeError('handles() expects Exception subclasses')

    def decorate(handler: _Handler) -> _Handler:
        target = (
            handler.__func__
            if isinstance(handler, (staticmethod, classmethod))
            else handler
        )
        if not inspect.isfunction(target):
            raise TypeError(
                'handles() expects a method, staticmethod or classmethod',
            )
        previous = getattr(target, _HANDLES_ATTRIBUTE, ())
        setattr(
            target,
            _HANDLES_ATTRIBUTE,
            tuple(dict.fromkeys(previous + exc_types)),
        )
        return handler

    return decorate


class ExceptionHandler:
    """
    Store and resolve exception handlers for SCPI dispatching.
    """

    def __init__(self):
        self._handlers: dict[type[Exception], ExceptionCallback] = {}
        self._register_default_exceptions()

    def _register_default_exceptions(self):
        self._handlers[ScpiException] = self._handle_scpi_exception
        self._handlers[ParserSyntaxError] = self._handle_parse_error
        self._handlers[RouteNotFound] = self._handle_route_not_found
        self._handlers[MissingPositionalArgsError] = (
            self._handle_missed_argument_error
        )
        self._handlers[UnexpectedPositionalArgsError] = (
            self._handle_unexpected_argument_error
        )
        self._handlers[UnexpectedKeywordArgsError] = (
            self._handle_unexpected_argument_error
        )

    def add_exception_handler(
        self,
        exc_type: type[Exception],
        handler: ExceptionCallback | None = None,
    ):
        """
        Register an exception handler.

        :param exc_type: Exception type handled by the callback.
        :type exc_type: type[Exception]
        :param handler: Callback that converts an exception into a SCPI error.
        :type handler: ExceptionCallback | None

        :return: Registered handler or decorator wrapper.
        :rtype: ExceptionCallback
        """
        if handler is not None:
            self._handlers[exc_type] = handler
            return handler

        def wrapper(func: ExceptionCallback):
            self._handlers[exc_type] = func
            return func

        return wrapper

    def include_class(
        self,
        container: type[_Container] | _Container,
        *args,
        **kwargs,
    ) -> _Container:
        """Bind and register all methods marked with handles()"""
        if inspect.isclass(container):
            instance = container(*args, **kwargs)
        else:
            if args or kwargs:
                raise TypeError('Constructor arguments require a class')
            instance = container

        pending: dict[type[Exception], ExceptionCallback] = {}
        names: set[str] = set()
        for owner in type(instance).__mro__:
            for name, member in vars(owner).items():
                if name in names:
                    continue

                names.add(name)
                target = (
                    member.__func__
                    if isinstance(member, (staticmethod, classmethod))
                    else member
                )

                if isinstance(target, property):
                    if getattr(target.fget, _HANDLES_ATTRIBUTE, ()):
                        raise TypeError('handles() cannot decorate a property')
                    continue

                if not inspect.isfunction(target):
                    continue

                exc_types = getattr(target, _HANDLES_ATTRIBUTE, ())
                if not exc_types:
                    continue

                callback = getattr(instance, name)
                self._validate_class_handler(callback, name)

                for exc_type in exc_types:
                    if exc_type in pending:
                        raise ValueError(
                            f'Duplicate handler for {exc_type.__name__}',
                        )
                    pending[exc_type] = callback

        if not pending:
            raise ValueError('No methods decorated with handles() found')

        self._handlers.update(pending)
        return instance

    @staticmethod
    def _validate_class_handler(
        callback: ExceptionCallback,
        name: str,
    ) -> None:
        target = inspect.unwrap(callback)
        if (
            inspect.iscoroutinefunction(target)
            or inspect.isasyncgenfunction(target)
            or inspect.isgeneratorfunction(target)
        ):
            raise TypeError('Exception handler cannot be asynchronous')

        try:
            inspect.signature(callback).bind(None, None, None)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                'Exception handler must accept (exc, context, command)',
            ) from exc

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
    ) -> ExceptionCallback | None:
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
    def _handle_missed_argument_error(
        exc: Exception,
        context: Context,
        command: Command | None,
    ) -> ScpiError:
        return DefaultScpiErrors.MISSING_PARAMETER.value

    @staticmethod
    def _handle_unexpected_argument_error(
        exc: Exception,
        context: Context,
        command: Command | None,
    ) -> ScpiError:
        return DefaultScpiErrors.PARAMETER_NOT_ALLOWED.value
