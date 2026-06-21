import asyncio
from contextlib import asynccontextmanager

from scpipy.server import Server, Router, Context

HOST = '127.0.0.1'
PORT = 5025


class Source:
    def __init__(self):
        self._connected: bool = False
        self._power: float = 0.0

    async def connect(self):
        await asyncio.sleep(1)
        self._connected = True

    async def set_power(self, power: float):
        if not self._connected:
            raise RuntimeError('Not connected')

        self._power = power

    def get_power(self) -> float:
        if not self._connected:
            raise RuntimeError('Not connected')

        return self._power

    async def disconnect(self):
        await asyncio.sleep(1)
        self._connected = False


router = Router()


@router.register('SOURce:POWer')
async def source_set_handler(context: Context, value: float):
    source: Source = context.state['source']
    await source.set_power(value)


@router.register('SOURce:POWer?')
def source_get_handler(context: Context):
    source: Source = context.state['source']

    return source.get_power()


@asynccontextmanager
async def lifespan(server: Server):
    source = Source()
    await source.connect()
    yield {'source': source}
    await source.disconnect()


if __name__ == '__main__':
    server = Server(HOST, PORT, lifespan=lifespan)
    server.include_router(router)
    server.run()
