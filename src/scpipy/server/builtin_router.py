from scpipy.server.context import Context
from scpipy.server.routing import Router

builtin_router = Router()


@builtin_router.register('*CLS')
def clear_errors(context: Context):
    context.clear_errors()


@builtin_router.register('SYSTem:ERRor[:NEXT]?')
def system_error(context: Context) -> str:
    return context.get_error()
