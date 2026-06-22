Custom exception handler
========================

The SCPI server supports custom exception handlers for translating internal
Python exceptions into SCPI errors.

This allows users to override the default error mapping for parser failures,
route lookup errors, or handler invocation problems.

Usage example
-------------

.. code-block:: python

   from scpipy.server import Server, Router, RouteNotFound, ArgumentBindingError
   from scpipy.shared.errors import ScpiError

   def handle_argument_error(exc, context, command):
       return ScpiError(-20001, 'Invalid command arguments')

   server = Server('127.0.0.1', 5025)

   # Add as decorator
   @server.add_exception_handler(RouteNotFound)
   def route_not_found_handler(exc, context, command):
       return ScpiError(-20002, 'Unknown command')

   # Or direct call method
   server.add_exception_handler(
       ArgumentBindingError,
       handle_argument_error
   )

   server.run()

Behavior
--------

The exception handler registry resolves handlers by exception type and its
base classes.

If no custom handler is registered, the server uses its built-in default
mapping.

Handlers receive:

* the raised exception,
* the current execution context,
* the parsed command, if available.

The handler must return an instance of ``ScpiError``.

Notes
-----

Custom handlers are useful when you want to:

* return vendor-specific SCPI error codes.
* customize error messages.
* inspect session state through ``context``.