from scpipy.server import Server, Router, Context

HOST = '127.0.0.1'
PORT = 5025

router = Router()


@router.register('SYSTem:READy[:STATe]?')
def syst_ready_handler(context: Context):
    return '1'


@router.register(
    'SOURce<channel>:POWer<some>[:LEVel][:IMMediate][:AMPLitude] <value>'
)
def source_handler(context: Context, channel: int, some: int, value: int):
    return f'{channel}:{some} {value}'


if __name__ == '__main__':
    server = Server(HOST, PORT)
    server.include_router(router)
    server.run()
