class ConfigureException(Exception):
    """Raised when the server configuration is invalid."""


class AlreadyStarted(Exception):
    """Raised when an operation tries to start an already running server."""


class LogicException(Exception):
    """Raised when the internal server state is inconsistent."""


class RouterException(Exception):
    """Base exception for router-related failures."""


class InvalidHandlerError(RouterException):
    """Raised when the passed handler with errors."""


class PatternMismatchError(RouterException):
    """Raised when the passed handler doesn't equal pattern."""


class DispatcherError(Exception):
    """Base exception for dispatcher-related failures."""


class RouteNotFound(DispatcherError):
    """Raised when no route matches the requested SCPI command."""


class ParserSyntaxError(DispatcherError):
    """Raised when a SCPI syntax error occurs."""


class MissingPositionalArgsError(DispatcherError):
    """Raised when no positional arguments are passed."""


class MissingKeywordArgsError(DispatcherError):
    """Raised when no positional arguments are passed."""


class UnexpectedPositionalArgsError(DispatcherError):
    """Raised when unexpected positional arguments are passed."""


class UnexpectedKeywordArgsError(DispatcherError):
    """Raised when unexpected keyword arguments are passed."""
