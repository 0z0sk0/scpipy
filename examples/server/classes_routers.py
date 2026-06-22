from scpipy.server import Server, Router, Context

HOST = '127.0.0.1'
PORT = 5025


class ClassRouter:
    def __init__(self):
        self.router = Router()

        self.router.add_route('SYSTem:READy[:STATe]?', self.syst_ready_handler)
        self.router.add_route(
            'SOURce<channel>:POWer<some>[:LEVel][:IMMediate][:AMPLitude]',
            self.source_handler,
        )

    def syst_ready_handler(self, context: Context):
        return '1'

    def source_handler(
        self, context: Context, value: float, channel: int, some: int
    ):
        return f'{channel}:{some}:{value}'


if __name__ == '__main__':
    class_router = ClassRouter()

    server = Server(HOST, PORT)
    server.include_router(class_router.router)
    server.run()
