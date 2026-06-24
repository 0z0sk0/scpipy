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

    def _get_dummy_arg_count(self) -> int:
        pattern_arg_count = sum(
            1
            for node in self.pattern.nodes
            if node.arg is not None and node.arg.pattern
        )
        command_arg_count = len(self.pattern.args)
        return pattern_arg_count + command_arg_count

    def _validate_handler(self):
        try:
            dummy_args = (None,) * self._get_dummy_arg_count()
            args, kwargs = self._build_call_args(None, dummy_args, {})
            self._signature.bind(*args, **kwargs)
        except TypeError as exc:
            raise PatternMismatchError(
                f'Handler signature mismatch with pattern: {exc}'
            )

    def _build_call_args(
        self, context, args: tuple, kwargs: dict
    ) -> tuple[list, dict]:
        out_args = [context]
        out_kwargs = {}

        handler_remaining_args = list(args)
        handler_remaining_kwargs = dict(kwargs)

        for handler_arg in self._user_defined_args:
            if handler_arg.kind is inspect.Parameter.POSITIONAL_ONLY:
                if handler_remaining_args:
                    out_args.append(handler_remaining_args.pop(0))

                else:
                    raise MissingPositionalArgsError(
                        f'missing required positional argument: {handler_arg.name}'
                    )

            elif handler_arg.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD:
                if handler_arg.name in handler_remaining_kwargs:
                    out_args.append(
                        handler_remaining_kwargs.pop(handler_arg.name)
                    )

                elif handler_remaining_args:
                    out_args.append(handler_remaining_args.pop(0))

                elif handler_arg.default is inspect._empty:
                    raise MissingPositionalArgsError(
                        f'missing required positional argument: {handler_arg.name}'
                    )

            elif handler_arg.kind is inspect.Parameter.VAR_POSITIONAL:
                out_args.extend(handler_remaining_args)
                handler_remaining_args.clear()

            elif handler_arg.kind is inspect.Parameter.KEYWORD_ONLY:
                if handler_arg.name in handler_remaining_kwargs:
                    out_kwargs[handler_arg.name] = (
                        handler_remaining_kwargs.pop(handler_arg.name)
                    )

                elif handler_arg.default is inspect._empty:
                    raise MissingKeywordArgsError(
                        f'missing required keyword argument: {handler_arg.name}'
                    )

            elif handler_arg.kind is inspect.Parameter.VAR_KEYWORD:
                out_kwargs.update(handler_remaining_kwargs)
                handler_remaining_kwargs.clear()

        if handler_remaining_args:
            raise UnexpectedPositionalArgsError(
                f'too many positional arguments: {tuple(handler_remaining_args)!r}'
            )

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
                raise MissingPositionalArgsError(msg)
            if 'positional argument' in msg:
                raise UnexpectedPositionalArgsError(msg)
            if 'keyword argument' in msg:
                raise UnexpectedKeywordArgsError(msg)
            raise InvalidHandlerError(msg)

    def invoke(self, context, *args, **kwargs):
        """Validate the call and invoke the wrapped handler."""
        bound = self.validate_call(context, args, kwargs)
        return self.handler(*bound.args, **bound.kwargs)
