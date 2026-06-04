from scpipy.server import Server

HOST = '127.0.0.1'
PORT = 5025


def syst_ready_handler(*args, **kwargs):
    return '1'


if __name__ == '__main__':
    server = Server(HOST, PORT)

    dispatcher = server.dispatcher
    dispatcher.register('SYST:READ?', syst_ready_handler)

    try:
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
