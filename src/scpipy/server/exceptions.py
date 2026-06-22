class ConfigureException(Exception):
    """Raised when the server configuration is invalid."""


class AlreadyStarted(Exception):
    """Raised when an operation tries to start an already running server."""


class LogicException(Exception):
    """Raised when the internal server state is inconsistent."""


class DispatcherError(Exception):
    """Base exception for dispatcher-related failures."""


class RouteNotFound(DispatcherError):
    """Raised when no route matches the requested SCPI command."""


class ArgumentBindingError(DispatcherError):
    """Raised when a route handler cannot be called with parsed arguments."""


class ParserSyntaxError(DispatcherError):
    """Raised when a SCPI syntax error occurs."""
