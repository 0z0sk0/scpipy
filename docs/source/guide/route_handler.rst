Route handler
================

SCPIpy binds parsed SCPI command patterns to Python handlers.

The goal is simple:

- keep command patterns and handler signatures in sync;
- fail early when a route is registered incorrectly;
- return clear, actionable errors when a command cannot be executed.

Why this matters
----------------

SCPI users usually work with command strings, not Python internals. When a
command is parsed incorrectly or a handler expects the wrong arguments, the
error should explain what is wrong in plain language.

For example, if a command expects ``<channel>`` and ``<some>``, the handler must
accept matching parameters. If the handler requires an extra keyword-only
argument, the route is invalid and should not be registered.

Defining a handler
------------------

A handler always receives ``context`` as its first argument.

Example::

   @router.register('SOURce<channel>:POWer<some>[:LEVel][:IMMediate][:AMPLitude] <values>')
   def source_handler(context, channel, some, *values):
       return channel, some, values

Rules:

- ``context`` is always the first argument.
- Pattern values are matched from left to right.
- Named pattern values are passed by name.
- ``*values`` receives any remaining positional values.
- ``**kwargs`` receives any remaining keyword values.

Pattern matching
----------------

A route is registered against a parsed SCPI pattern. The pattern determines
which values are available to the handler.

The following parts are matched:

- node placeholders such as ``<channel>`` and ``<some>``;
- trailing command arguments such as ``<values>``;
- optional command sections, which may or may not be present.

If the handler signature cannot accept the values produced by the pattern, the
route registration fails immediately.

Example::

   SOURce<channel>:POWer<some>[:LEVel][:IMMediate][:AMPLitude] <values>

This pattern can match commands such as:

- ``SOURce1:POWer2 10 20 30``
- ``SOURce1:POWer2:LEVel 10``
- ``SOURce1:POWer2:LEVel:IMMediate 10 20``

Error handling
--------------

The library raises explicit errors when a command or handler does not match the
expected shape.

Common cases:

- missing required positional argument;
- missing required keyword-only argument;
- unexpected extra positional argument;
- unexpected extra keyword argument;
- handler signature mismatch during route registration.

Typical error messages are designed to tell you:

- which argument is missing or unexpected;
- whether the problem is in the handler or in the incoming command;
- how to fix the command or the route definition.

Error examples
--------------

Missing positional argument::

   MissingPositionalArgsError: missing required positional argument: some

Missing keyword-only argument::

   MissingKeywordArgsError: missing required keyword argument: mode

Unexpected positional argument::

   UnexpectedPositionalArgsError: too many positional arguments: ('10',)

Unexpected keyword argument::

   UnexpectedKeywordArgsError: got unexpected keyword arguments: extra

Registration mismatch::

   PatternMismatchError: handler signature does not match the command pattern

Recommended usage
-----------------

Keep handlers small and explicit.

Good::

   @router.register('SOURce<channel>:POWer<some> <values>')
   def set_power(context, channel, some, *values):
       ...

Avoid handlers that require arguments not represented by the SCPI pattern.

Bad::

   @router.register('SOURce<channel>:POWer<some>')
   def set_power(context, channel, some, *, mode):
       ...

In the second example, ``mode`` cannot be supplied by the route, so the handler
is not compatible with the command pattern.