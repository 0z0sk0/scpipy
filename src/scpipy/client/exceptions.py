class ClientTimeoutError(Exception):
    """Raised when a client operation exceeds the configured timeout."""


class ClientConnectionError(Exception):
    """Raised when the client cannot connect or is used in an invalid state."""


class ClientStopped(Exception):
    """Raised when an operation is attempted on a stopped client."""
