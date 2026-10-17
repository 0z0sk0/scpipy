import re
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from scpipy.server.context import Context
from scpipy.server.routing import Router
from scpipy.shared.errors import DefaultScpiErrors, ScpiException

builtin_router = Router()

_DECIMAL = re.compile(
    r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?',
)
_NON_DECIMAL = re.compile(r'#([HhQqBb])([0-9A-Fa-f]+)')


def _register_value(raw: str, maximum: int) -> int:
    raw = raw.strip()
    match = _NON_DECIMAL.fullmatch(raw)
    if match is not None:
        base = {'H': 16, 'Q': 8, 'B': 2}[match[1].upper()]
        try:
            value = int(match[2], base)
        except ValueError as exc:
            raise ScpiException(
                DefaultScpiErrors.DATA_TYPE_ERROR.value,
            ) from exc
    elif _DECIMAL.fullmatch(raw):
        try:
            number = Decimal(raw)
        except InvalidOperation as exc:
            raise ScpiException(
                DefaultScpiErrors.DATA_OUT_OF_RANGE.value,
            ) from exc
        if not number.is_finite():
            raise ScpiException(DefaultScpiErrors.DATA_OUT_OF_RANGE.value)
        if number < -1 or number > maximum + 1:
            raise ScpiException(DefaultScpiErrors.DATA_OUT_OF_RANGE.value)
        value = int(number.to_integral_value(rounding=ROUND_HALF_EVEN))
    else:
        raise ScpiException(DefaultScpiErrors.DATA_TYPE_ERROR.value)
    if not 0 <= value <= maximum:
        raise ScpiException(DefaultScpiErrors.DATA_OUT_OF_RANGE.value)
    return value


@builtin_router.register('*CLS')
def clear_errors(context: Context):
    context.clear_status()


@builtin_router.register('SYSTem:ERRor[:NEXT]?')
def system_error(context: Context) -> str:
    return context.get_error()


@builtin_router.register('*ESE <value>')
def set_event_enable(context: Context, value: str):
    context.status.event_enable = _register_value(value, 255)


@builtin_router.register('*ESE?')
def event_enable(context: Context) -> int:
    return context.status.event_enable


@builtin_router.register('*ESR?')
def event_status(context: Context) -> int:
    return context.status.read_event_status()


@builtin_router.register('*SRE <value>')
def set_service_request_enable(context: Context, value: str):
    context.status.service_request_enable = _register_value(value, 255)


@builtin_router.register('*SRE?')
def service_request_enable(context: Context) -> int:
    return context.status.service_request_enable


@builtin_router.register('*STB?')
def status_byte(context: Context) -> int:
    return context.status.status_byte


@builtin_router.register('STATus:PRESet')
def preset_status(context: Context):
    context.status.preset()


@builtin_router.register('*OPC')
def operation_complete(context: Context):
    context.status.request_operation_complete()


@builtin_router.register('*OPC?')
async def operation_complete_query(context: Context) -> int | None:
    completed = await context.status.wait_for_operations(cancel_on_clear=True)
    return 1 if completed else None


@builtin_router.register('*WAI')
async def wait_for_operations(context: Context):
    await context.status.wait_for_operations()


def _register_status_group(prefix: str, attribute: str):
    def read_event(context: Context) -> int:
        return getattr(context.status, attribute).read_event()

    def read_condition(context: Context) -> int:
        return getattr(context.status, attribute).condition

    builtin_router.add_route(prefix + '[:EVENt]?', read_event)
    builtin_router.add_route(prefix + ':CONDition?', read_condition)

    def register_mask(suffix: str, field: str):
        def read_mask(context: Context) -> int:
            return getattr(getattr(context.status, attribute), field)

        def write_mask(context: Context, value: str):
            parsed = _register_value(value, 65535)
            setattr(getattr(context.status, attribute), field, parsed)

        builtin_router.add_route(prefix + suffix + '?', read_mask)
        builtin_router.add_route(prefix + suffix + ' <value>', write_mask)

    register_mask(':ENABle', 'enable')
    register_mask(':PTRansition', 'positive_transition')
    register_mask(':NTRansition', 'negative_transition')


_register_status_group('STATus:OPERation', 'operation')
_register_status_group('STATus:QUEStionable', 'questionable')
