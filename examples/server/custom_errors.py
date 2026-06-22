from scpipy.server import (
    Server,
    Router,
    Context,
    ArgumentBindingError,
    RouteNotFound,
)
from scpipy.shared.errors import ScpiError, ScpiException

HOST = '127.0.0.1'
PORT = 5025

router = Router()


@router.register('SYSTem:READy[:STATe]?')
def syst_ready_handler(context: Context):
    return '1'


def handle_argument_error(exc, context: Context, command):
    return ScpiError(-20001, 'Invalid command arguments')


if __name__ == '__main__':
    server = Server(HOST, PORT)
    server.include_router(router)

    server.add_exception_handler(
        ArgumentBindingError,
        handle_argument_error,
    )

    @server.add_exception_handler(RouteNotFound)
    def unknown_command_error(exc, context: Context, command):
        return ScpiError(-20002, 'Unknown command')

    server.run()
