import asyncio
import time

from scpipy.client import Client

ADDRESS = 'TCPIP0::localhost::5025::SOCKET'


async def some_background_task():
    while True:
        print(f'[{time.time()}] some task in background')
        await asyncio.sleep(0.2)


async def worker_task(client: Client, task_name: str, command: str):
    print(f'[{time.time()}] await {task_name}')
    response = await client.query(command)
    print(
        f'[{time.time()}] {task_name} done -> {response}'
    )


async def main():
    async with Client(ADDRESS, backend='@py') as client:
        some_tasks_loop = asyncio.create_task(some_background_task())

        await asyncio.gather(
            worker_task(client, 'Instrument ready', 'SYST:READ?'),
            worker_task(
                client,
                'Sweep',
                'INIT:CONT 0;:TRIG:SOUR BUS;:INIT;:TRIG:SING;:*OPC?',
            ),
            worker_task(client, 'Intstrument start frequency', 'SENS:FREQ:STAR?'),
        )

        some_tasks_loop.cancel()
        try:
            await some_tasks_loop
        except asyncio.CancelledError:
            pass


asyncio.run(main())
