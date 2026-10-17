from scpipy.server import Context, Router, Server
from scpipy.server.exception_handler import handles
from scpipy.shared.errors import DefaultScpiErrors, ScpiError

HOST = '127.0.0.1'
PORT = 5025


class InvalidLevelError(Exception):
    pass


class UserExceptionHandlers:
    def __init__(self, device_name: str = 'Demo device'):
        self.device_name = device_name
        self.handled_count = 0

    @handles(InvalidLevelError, ValueError)
    def invalid_level(self, exc, context, command) -> ScpiError:
        self.handled_count += 1
        return DefaultScpiErrors.DATA_OUT_OF_RANGE.value


router = Router()


@router.register('SOURce:LEVel <value>')
def set_level(context: Context, value: str):
    level = float(value)
    if not 0 <= level <= 10:
        raise InvalidLevelError('Level must be in range 0-10')
    context.state['level'] = level


if __name__ == '__main__':
    server = Server(HOST, PORT)
    server.include_router(router)
    server.exception_handler.include_class(
        UserExceptionHandlers,
        device_name='Example instrument',
    )
    server.run()
