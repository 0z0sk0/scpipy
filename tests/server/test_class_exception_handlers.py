from functools import wraps

import pytest

from scpipy.server import Context, Router, handles
from scpipy.server.exception_handler import ExceptionHandler
from scpipy.server.exceptions import RouteNotFound
from scpipy.shared.ast import Command
from scpipy.shared.errors import ScpiError, ScpiException
from scpipy.shared.parser import Parser


class DeviceError(Exception):
    pass


class RangeError(DeviceError):
    pass


class OtherError(Exception):
    pass


class UserHandlers:
    def __init__(self, message='device failure'):
        self.message = message
        self.calls = []

    @handles(DeviceError)
    def device_error(self, exc, context, command):
        self.calls.append((exc, context, command))
        return ScpiError(-200, self.message)


def test_include_class_constructs_once_binds_self_and_preserves_arguments():
    registry = ExceptionHandler()
    instance = registry.include_class(UserHandlers, 'custom message')
    context = Context()
    command = Parser().parse('SYST:ERR?')[0]
    exception = RangeError('range')
    assert registry.resolve(exception, context, command) == ScpiError(
        -200,
        'custom message',
    )
    assert instance.calls == [(exception, context, command)]
    registry.resolve(DeviceError(), context, None)
    assert len(instance.calls) == 2


def test_existing_instance_and_keyword_constructor_arguments():
    registry = ExceptionHandler()
    instance = UserHandlers('injected state')
    assert registry.include_class(instance) is instance
    assert (
        registry.resolve(DeviceError(), Context(), None).message
        == 'injected state'
    )
    other = registry.include_class(UserHandlers, message='keyword')
    assert other.message == 'keyword'
    assert (
        registry.resolve(DeviceError(), Context(), None).message == 'keyword'
    )


@pytest.mark.parametrize(
    'args,kwargs',
    [(('extra',), {}), ((), {'message': 'extra'})],
)
def test_instance_rejects_constructor_arguments(args, kwargs):
    with pytest.raises(TypeError, match='require a class'):
        ExceptionHandler().include_class(UserHandlers(), *args, **kwargs)


def test_stacked_and_multiple_exception_types_are_supported():
    class Handlers:
        @handles(DeviceError, OtherError)
        @handles(DeviceError, ValueError)
        def handle(self, exc, context, command):
            return ScpiError(-200, 'shared')

    registry = ExceptionHandler()
    registry.include_class(Handlers)
    for exception in (DeviceError(), RangeError(), OtherError(), ValueError()):
        assert registry.resolve(exception, Context(), None).message == 'shared'


@pytest.mark.parametrize('descriptor', [staticmethod, classmethod])
@pytest.mark.parametrize('outer_handles', [False, True])
def test_descriptors_support_both_decorator_orders(descriptor, outer_handles):
    if descriptor is staticmethod:

        def callback(exc, context, command):
            return ScpiError(-200, 'static')

    else:

        def callback(cls, exc, context, command):
            return ScpiError(-200, cls.__name__)

    if outer_handles:
        decorated = handles(DeviceError)(descriptor(callback))
    else:
        decorated = descriptor(handles(DeviceError)(callback))
    container = type('Handlers', (), {'handle': decorated})
    registry = ExceptionHandler()
    registry.include_class(container)
    expected = 'static' if descriptor is staticmethod else 'Handlers'
    assert registry.resolve(DeviceError(), Context(), None).message == expected


def test_inherited_classmethod_binds_concrete_subclass():
    class Base:
        @classmethod
        @handles(DeviceError)
        def handle(cls, exc, context, command):
            return ScpiError(-200, cls.__name__)

    class Child(Base):
        pass

    registry = ExceptionHandler()
    registry.include_class(Child)
    assert registry.resolve(DeviceError(), Context(), None).message == 'Child'


def test_decorated_override_and_inherited_methods():
    class Base(UserHandlers):
        @handles(OtherError)
        def other(self, exc, context, command):
            return ScpiError(-201, 'inherited')

    class Child(Base):
        @handles(RangeError)
        def device_error(self, exc, context, command):
            return ScpiError(-222, 'child')

    registry = ExceptionHandler()
    registry.include_class(Child)
    assert (
        registry.resolve(OtherError(), Context(), None).message == 'inherited'
    )
    assert registry.resolve(RangeError(), Context(), None).message == 'child'
    with pytest.raises(DeviceError):
        registry.resolve(DeviceError(), Context(), None)


def test_undecorated_override_suppresses_base_handler():
    class Child(UserHandlers):
        def device_error(self, exc, context, command):
            return ScpiError(-222, 'undecorated')

        @handles(OtherError)
        def other(self, exc, context, command):
            return ScpiError(-201, 'other')

    registry = ExceptionHandler()
    registry.include_class(Child)
    with pytest.raises(DeviceError):
        registry.resolve(DeviceError(), Context(), None)


def test_diamond_mro_uses_effective_method_once():
    class Root:
        @handles(DeviceError)
        def handle(self, exc, context, command):
            return ScpiError(-200, 'root')

    class Left(Root):
        @handles(DeviceError)
        def handle(self, exc, context, command):
            return ScpiError(-200, 'left')

    class Right(Root):
        @handles(DeviceError)
        def handle(self, exc, context, command):
            return ScpiError(-200, 'right')

    class Child(Left, Right):
        pass

    registry = ExceptionHandler()
    registry.include_class(Child)
    assert registry.resolve(DeviceError(), Context(), None).message == 'left'


def test_unrelated_properties_are_never_evaluated():
    class Handlers(UserHandlers):
        @property
        def dangerous(self):
            raise RuntimeError('must not execute property')

    registry = ExceptionHandler()
    registry.include_class(Handlers)
    assert registry.resolve(DeviceError(), Context(), None).code == -200


def test_decorated_property_is_rejected_without_calling_getter():
    class Handlers:
        @property
        @handles(DeviceError)
        def bad(self):
            raise RuntimeError('must not execute property')

    with pytest.raises(TypeError, match='property'):
        ExceptionHandler().include_class(Handlers)


def test_wrapped_synchronous_handler_is_supported():
    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    class Handlers:
        @handles(DeviceError)
        @wrap
        def handle(self, exc, context, command):
            return ScpiError(-200, 'wrapped')

    registry = ExceptionHandler()
    registry.include_class(Handlers)
    assert (
        registry.resolve(DeviceError(), Context(), None).message == 'wrapped'
    )


def test_duplicate_class_handlers_do_not_partially_override_registry():
    class Handlers:
        @handles(RouteNotFound)
        def first(self, exc, context, command):
            return ScpiError(-200, 'override')

        @handles(RouteNotFound)
        def duplicate(self, exc, context, command):
            return ScpiError(-201, 'duplicate')

    registry = ExceptionHandler()
    previous = registry._handlers.copy()
    with pytest.raises(
        ValueError,
        match='Duplicate handler for RouteNotFound',
    ):
        registry.include_class(Handlers)
    assert registry._handlers == previous


@pytest.mark.parametrize(
    'callback',
    [
        lambda self, exc: None,
        lambda self, exc, context, command, required: None,
        lambda self, *, exc, context, command: None,
    ],
)
def test_bad_signature_does_not_partially_register(callback):
    class Handlers(UserHandlers):
        bad = handles(OtherError)(callback)

    registry = ExceptionHandler()
    previous = registry._handlers.copy()
    with pytest.raises(TypeError, match='must accept'):
        registry.include_class(Handlers)
    assert registry._handlers == previous


@pytest.mark.parametrize(
    'kind',
    ['coroutine', 'async_generator', 'generator', 'wrapped_coroutine'],
)
def test_non_synchronous_handlers_are_rejected_at_registration(kind):
    async def coroutine(self, exc, context, command):
        return ScpiError(-200, 'async')

    async def async_generator(self, exc, context, command):
        yield ScpiError(-200, 'async gen')

    def generator(self, exc, context, command):
        yield ScpiError(-200, 'gen')

    @wraps(coroutine)
    def wrapped_coroutine(*args, **kwargs):
        return coroutine(*args, **kwargs)

    callbacks = {
        'coroutine': coroutine,
        'async_generator': async_generator,
        'generator': generator,
        'wrapped_coroutine': wrapped_coroutine,
    }
    container = type(
        'Handlers',
        (),
        {'handle': handles(DeviceError)(callbacks[kind])},
    )
    with pytest.raises(TypeError, match='synchronous'):
        ExceptionHandler().include_class(container)


@pytest.mark.parametrize(
    'exception_types',
    [
        (),
        (None,),
        (str,),
        (BaseException,),
        (KeyboardInterrupt,),
        (DeviceError, 123),
    ],
)
def test_handles_rejects_invalid_exception_types(exception_types):
    with pytest.raises(TypeError):
        handles(*exception_types)


@pytest.mark.parametrize('target', [None, 42, property(lambda self: None)])
def test_handles_rejects_non_methods(target):
    with pytest.raises(TypeError, match='expects a method'):
        handles(DeviceError)(target)


def test_empty_container_is_rejected():
    with pytest.raises(ValueError, match='No methods'):
        ExceptionHandler().include_class(object())


def test_constructor_failure_preserves_registry_and_original_error():
    error = RuntimeError('constructor')

    class Handlers(UserHandlers):
        def __init__(self):
            raise error

    registry = ExceptionHandler()
    previous = registry._handlers.copy()
    with pytest.raises(RuntimeError) as caught:
        registry.include_class(Handlers)
    assert caught.value is error
    assert registry._handlers == previous


def test_class_registration_can_override_builtin_and_be_overridden_directly():
    class Handlers:
        @handles(RouteNotFound)
        def missing(self, exc, context, command):
            return ScpiError(-200, 'class')

    registry = ExceptionHandler()
    registry.include_class(Handlers)
    assert (
        registry.resolve(RouteNotFound(), Context(), None).message == 'class'
    )
    registry.add_exception_handler(
        RouteNotFound,
        lambda *args: ScpiError(-201, 'direct'),
    )
    assert (
        registry.resolve(RouteNotFound(), Context(), None).message == 'direct'
    )


def test_class_return_value_is_still_checked_at_resolution():
    class Handlers:
        @handles(DeviceError)
        def bad(self, exc, context, command):
            return 'not a ScpiError'

    registry = ExceptionHandler()
    registry.include_class(Handlers)
    with pytest.raises(TypeError, match='must return ScpiError'):
        registry.resolve(DeviceError(), Context(), None)


@pytest.mark.asyncio
async def test_public_server_registry_is_used_by_dispatcher(server_factory):
    server = server_factory('127.0.0.1', 0)
    instance = server.exception_handler.include_class(
        UserHandlers,
        'registered',
    )
    assert server.exception_handler is server.exception_handler
    router = Router()

    def fail(context):
        raise DeviceError('device failed')

    router.add_route('USER?', fail)
    server.include_router(router)
    context = Context()
    with pytest.raises(ScpiException) as caught:
        await server._dispatcher._dispatch(context, b'USER?')
    assert caught.value.error.message == 'registered'
    assert len(instance.calls) == 1
    assert instance.calls[0][1] is context
    assert isinstance(instance.calls[0][2], Command)


@pytest.mark.asyncio
async def test_class_handler_error_reaches_queue_and_srs(
    server_factory,
    streams,
):
    server = server_factory('127.0.0.1', 0, shared_context=True)
    server.exception_handler.include_class(UserHandlers)
    context = server._get_context()
    context.clear_status()
    context.status.event_enable = 16
    context.status.service_request_enable = 32
    router = Router()

    def fail(context):
        raise DeviceError('failed')

    router.add_route('USER?', fail)
    server.include_router(router)
    reader, writer = streams
    reader.readline.side_effect = [
        b'USER?\n',
        b'*STB?\n',
        b'*ESR?\n',
        b'SYST:ERR?\n',
        b'',
    ]
    await server._handle_client(reader, writer)
    assert [call.args[0] for call in writer.write.call_args_list] == [
        b'100\n',
        b'16\n',
        b'-200,"device failure"\n',
    ]
