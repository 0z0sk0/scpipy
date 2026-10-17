import asyncio
import dataclasses
from contextlib import asynccontextmanager

from scpipy.server import (
    Context,
    OperationStatus,
    QuestionableStatus,
    Router,
    Server,
)
from scpipy.shared.errors import DefaultScpiErrors, ScpiError, ScpiException

HOST = '127.0.0.1'
PORT = 5025


@dataclasses.dataclass
class Instrument:
    last_value: float | None = None
    acquisition: asyncio.Task[None] | None = None


router = Router()


@router.register('*IDN?')
def identification(context: Context) -> str:
    return 'scpipy,MegaDevice,00000001,1.0'


async def acquire(context: Context, instrument: Instrument):
    context.status.operation.update_condition(OperationStatus.MEASURING, True)
    try:
        await asyncio.sleep(0.25)
        instrument.last_value = 42.0
    finally:
        context.status.operation.update_condition(
            OperationStatus.MEASURING,
            False,
        )


@router.register('INITiate')
def initiate(context: Context):
    instrument: Instrument = context.state['instrument']
    if (
        instrument.acquisition is not None
        and not instrument.acquisition.done()
    ):
        raise ScpiException(ScpiError(-200, 'Execution error'))

    task = context.status.start_operation(acquire(context, instrument))
    instrument.acquisition = task

    def finished(completed: asyncio.Task[None]):
        if completed.cancelled():
            return
        error = completed.exception()
        if error is not None:
            context.push_error(ScpiError(-300, 'Device-specific error'))

    task.add_done_callback(finished)


@router.register('SIMulate:OVERload <state>')
def simulate_overload(context: Context, state: str):
    if state not in ('0', '1'):
        raise ScpiException(DefaultScpiErrors.DATA_OUT_OF_RANGE.value)
    context.status.questionable.update_condition(
        QuestionableStatus.POWER,
        state == '1',
    )


@asynccontextmanager
async def lifespan(server: Server):
    instrument = Instrument()
    try:
        yield {'instrument': instrument}
    finally:
        task = instrument.acquisition
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


if __name__ == '__main__':
    server = Server(HOST, PORT, shared_context=True, lifespan=lifespan)
    server.include_router(router)
    server.run()
