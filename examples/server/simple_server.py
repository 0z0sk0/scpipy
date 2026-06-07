from scpipy.server import Server, Router

HOST = '127.0.0.1'
PORT = 5025

router = Router()


@router.register('SYST:READ?')
def syst_ready_handler(*args, **kwargs):
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
