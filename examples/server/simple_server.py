from scpipy.server import Server, Router, Context

HOST = '127.0.0.1'
PORT = 5025

router = Router()


@router.register('SYSTem:READy[:STATe]?')
def syst_ready_handler(context: Context):
    return '1'


if __name__ == '__main__':
    server = Server(HOST, PORT)
    server.include_router(router)

    try:
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
