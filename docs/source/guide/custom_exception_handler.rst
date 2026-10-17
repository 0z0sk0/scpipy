Custom exception handler
========================

The SCPI server supports custom exception handlers for translating internal
Python exceptions into SCPI errors.

This allows users to override the default error mapping for parser failures,
route lookup errors, or handler invocation problems.

Usage example
-------------

.. code-block:: python

   from scpipy.server import Server, RouteNotFound, UnexpectedPositionalArgsError
   from scpipy.shared.errors import ScpiError

   server = Server('127.0.0.1', 5025)

   @server.add_exception_handler(RouteNotFound)
   def route_not_found(exc, context, command):
       return ScpiError(-110, 'Command header error')

   def argument_error(exc, context, command):
       return ScpiError(-108, 'Parameter not allowed')

   server.add_exception_handler(UnexpectedPositionalArgsError, argument_error)

Class registration
------------------

.. code-block:: python

   from scpipy.server import Server
   from scpipy.server.exception_handler import handles
   from scpipy.shared.errors import DefaultScpiErrors, ScpiError

   class MyError(Exception):
       pass

   class MyOtherError(Exception):
       pass

   class UserExceptionHandlers:
       def __init__(self, device_name='Instrument'):
           self.device_name = device_name
           self.handled_count = 0

       @handles(MyError)
       def handle_my_error(self, exc, context, command) -> ScpiError:
           self.handled_count += 1
           return DefaultScpiErrors.EXECUTION_ERROR.value

       @handles(MyOtherError)
       def handle_my_other_error(self, exc, context, command) -> ScpiError:
           self.handled_count += 1
           return DefaultScpiErrors.PARAMETER_NOT_ALLOWED.value

   server = Server('127.0.0.1', 5025)
   handlers = server.exception_handler.include_class(
       UserExceptionHandlers, device_name='Analyzer',
   )

``include_class`` instantiates a class once and returns that instance. Positional
and keyword arguments are forwarded to its constructor. A ready instance can
also be supplied, which supports dependency injection:

.. code-block:: python

   handlers = UserExceptionHandlers(device_name='Analyzer')
   server.exception_handler.include_class(handlers)

The read-only ``server.exception_handler`` property exposes the current registry
already used by the dispatcher. The original ``server.add_exception_handler``
API remains available.

Supported methods
-----------------

* ``@handles(A, B)`` registers one method for multiple exception types.
* Stacked ``@handles`` decorators are supported; repeated types on the same
  method are deduplicated.
* Instance methods, ``staticmethod`` and ``classmethod`` are supported.
  ``@handles`` can appear above or below either descriptor decorator.

For example:

.. code-block:: python

   class SharedHandlers:
       @staticmethod
       @handles(ValueError, TypeError)
       def bad_value(exc, context, command):
           return ScpiError(-222, 'Data out of range')

Validation and precedence
-------------------------

All marked methods must be synchronous and callable with exactly the three
positional arguments ``(exc, context, command)`` after binding.

Only ``Exception`` subclasses are accepted. ``BaseException``,
``KeyboardInterrupt`` and ``SystemExit`` cannot be registered with ``handles``.
