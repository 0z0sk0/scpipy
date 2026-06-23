from __future__ import annotations

import dataclasses
import inspect
from collections.abc import Callable

from scpipy.server.exceptions import (
    InvalidHandlerError,
    PatternMismatchError,
    MissingPositionalArgsError,
    MissingKeywordArgsError,
    UnexpectedPositionalArgsError,
    UnexpectedKeywordArgsError,
)
from scpipy.shared.ast import Command


@dataclasses.dataclass(slots=True)
class RouteHandler:
    """Bind an SCPI command pattern to a handler callable."""

    handler: Callable
    pattern: Command
    _signature: inspect.Signature = dataclasses.field(init=False)
    _user_defined_args: tuple[inspect.Parameter, ...] = dataclasses.field(
        init=False
    )

    def __post_init__(self):
        self._signature = inspect.signature(self.handler)
        handler_args = tuple(self._signature.parameters.values())

        if not handler_args or handler_args[0].name != 'context':
            raise InvalidHandlerError(
                'Handler must accept context as its first parameter.'
            )

        if handler_args[0].kind in (
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise InvalidHandlerError(
                'Handler context argument must be positional.'
            )

        self._user_defined_args = handler_args[1:]
        self._validate_handler()

    def _validate_handler(self):
        node_pattern_args_count = sum(
            1
            for node in self.pattern.nodes
            if node.arg is not None and node.arg.pattern
        )

        command_args_count = len(self.pattern.args)
        total_pos_count = node_pattern_args_count + command_args_count

        try:
            dummy_pos = (None,) * total_pos_count
            dummy_kw = {}

            args, kwargs = self._build_call_args(None, dummy_pos, dummy_kw)
            self._signature.bind(*args, **kwargs)
        except TypeError as e:
            raise PatternMismatchError(
                f'Handler signature mismatch with pattern: {e}'
            ) from e

    def _build_call_args(
        self, context, args: tuple, kwargs: dict
    ) -> tuple[list, dict]:
        # Context always first arg
        out_args = [context]
        out_kwargs = {}

        # TODO: debug logging
        print('Pattern:', self.pattern)
        print('Signature:', self._signature)
        print('Call args:', args)
        print('Call kwargs:', kwargs)

        handler_remaining_args = list(args)
        handler_remaining_kwargs = dict(kwargs)

        for handler_arg in self._user_defined_args:
            # TODO: debug logging
            print(f'Handler arg: "{handler_arg}"')
            print('Kind:', handler_arg.kind)
            print('Handler remaining args:', handler_remaining_args)
            print('Handler remaining kwargs:', handler_remaining_kwargs)

            if handler_arg.kind is inspect.Parameter.POSITIONAL_ONLY:
                # f(context, 'some_value')
                #            ^^^^^^^^^^^^
                #
                # Positional arg, not variable of count.

                # TODO: debug logging
                print(
                    'This is a positional arg, positional args are remaining?'
                )
                if handler_remaining_args:
                    first_handler_remaining_arg = handler_remaining_args.pop(0)
                    out_args.append(first_handler_remaining_arg)

                else:
                    raise MissingPositionalArgsError(
                        f'missing required positional argument: {handler_arg.name}'
                    )

            elif handler_arg.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD:
                # f(context, 'some_value', 'another_value')
                #            ^^^^^^^^^^^^  ^^^^^^^^^^^^^^^
                #
                # f(context, some=1, other=2)
                #            ^^^^^^  ^^^^^^^
                #
                # Combined positional and keyword arg, which can be passed with keyword or positional alone.

                # TODO: debug logging
                print(
                    'Its positional or keyword arg, positional or keyword args remaining?'
                )
                if handler_arg.name in handler_remaining_kwargs:
                    # TODO: debug logging
                    print('Keyword args remaining, take by name')
                    value = handler_remaining_kwargs.pop(handler_arg.name)
                    out_args.append(value)

                elif handler_remaining_args:
                    # TODO: debug logging
                    print('Positional args remaining, take first')
                    first_handler_remaining_arg_value = (
                        handler_remaining_args.pop(0)
                    )
                    out_args.append(first_handler_remaining_arg_value)

                elif handler_arg.default is inspect._empty:
                    raise MissingPositionalArgsError(
                        f'missing required positional argument: {handler_arg.name}'
                    )

            elif handler_arg.kind is inspect.Parameter.VAR_POSITIONAL:
                # f(context, *args)
                #            ^^^^^^
                #
                # Variable positional args, takes all remaining args inside.

                # TODO: debug logging
                print(
                    'Its variable positional arg, take all remaining positional args'
                )
                out_args.extend(handler_remaining_args)
                handler_remaining_args.clear()

            elif handler_arg.kind is inspect.Parameter.KEYWORD_ONLY:
                # f(context, *, some=1)
                #               ^^^^^^
                #
                # Keyword arg, which can be passed only with keyword.

                # TODO: debug logging
                print('Its keyword arg, arg in keyword args?')
                if handler_arg.name in handler_remaining_kwargs:
                    # TODO: debug logging
                    print('Arg in keyword args, take by name')
                    value = handler_remaining_kwargs.pop(handler_arg.name)
                    out_kwargs[handler_arg.name] = value

                elif handler_arg.default is inspect._empty:
                    raise MissingKeywordArgsError(
                        f'missing required keyword argument: {handler_arg.name}'
                    )

            elif handler_arg.kind is inspect.Parameter.VAR_KEYWORD:
                # f(context, **extra)
                #            ^^^^^^^
                #
                # Variable keyword args, which can be passed only with keyword for each arg.
                # TODO: debug logging
                print(
                    'Its variable keyword arg, take all remaining keyword args'
                )
                out_kwargs.update(handler_remaining_kwargs)
                handler_remaining_kwargs.clear()

        # If handler still has positional args, raise an exception.
        if handler_remaining_args:
            raise UnexpectedPositionalArgsError(
                f'too many positional arguments: {tuple(handler_remaining_args)!r}'
            )

        # If handler still has named args, raise an exception.
        if handler_remaining_kwargs:
            unexpected = ', '.join(sorted(handler_remaining_kwargs))
            raise UnexpectedKeywordArgsError(
                f'got unexpected keyword arguments: {unexpected}'
            )

        return out_args, out_kwargs

    def validate_call(
        self,
        context,
        args: tuple,
        kwargs: dict,
    ) -> inspect.BoundArguments:
        """Validate a handler call and return the bound arguments."""
        if context is None:
            raise InvalidHandlerError('Missing required context argument')

        try:
            args, kwargs = self._build_call_args(context, args, kwargs)
            bound = self._signature.bind(*args, **kwargs)
            bound.apply_defaults()
            return bound
        except TypeError as e:
            msg = str(e)
            if 'missing' in msg:
                raise MissingPositionalArgsError(msg) from e
            if 'positional argument' in msg:
                raise UnexpectedPositionalArgsError(msg) from e
            if 'keyword argument' in msg:
                raise UnexpectedKeywordArgsError(msg) from e
            raise InvalidHandlerError(msg) from e

    def invoke(self, context, *args, **kwargs):
        """Validate the call and invoke the wrapped handler."""
        bound = self.validate_call(context, args, kwargs)
        return self.handler(*bound.args, **bound.kwargs)
