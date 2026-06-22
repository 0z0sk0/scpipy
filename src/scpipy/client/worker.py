import asyncio
import contextlib
import pyvisa

from scpipy.client.exceptions import ClientConnectionError, ClientStopped
from scpipy.client.models import QueueItem, OperationType


class Worker:
    """
    Execute instrument operations in a background task.

    Serializes access to a message-based VISA instrument through an internal
    asynchronous queue and provides asynchronous write, read, query, and close
    operations.

    :param instrument: Message-based VISA instrument used for I/O operations.
    :type instrument: pyvisa.resources.MessageBasedResource
    :param queue_size: Maximum number of queued operations. A value of ``0``
        uses an unbounded queue.
    :type queue_size: int
    """

    def __init__(
        self,
        instrument: pyvisa.resources.MessageBasedResource,
        *,
        queue_size: int = 0,
    ):
        self._instrument = instrument
        self._queue: asyncio.Queue[QueueItem] = asyncio.Queue(
            maxsize=queue_size
        )
        self._task: asyncio.Task[None] | None = None
        self._closing = False
        self._closed = False

    def start(self):
        """
        Start the background worker task.

        If the worker is already started, this method returns immediately.
        """
        if self._task is not None:
            return
        self._task = asyncio.create_task(
            self._run(), name='scpipy-client-worker'
        )

    async def write(self, command: str) -> int:
        """
        Enqueue a write operation.

        :param command: SCPI command string to send to the instrument.
        :type command: str

        :return: Number of bytes written.
        :rtype: int

        :raises ClientConnectionError: If the worker is not started, is
            closing, or is already closed.
        """
        result = await self._submit(OperationType.WRITE, command)
        return int(result)

    async def read(self) -> str:
        """
        Enqueue a read operation.

        :return: Response read from the instrument.
        :rtype: str

        :raises ClientConnectionError: If the worker is not started, is
            closing, or is already closed.
        """
        result = await self._submit(OperationType.READ, None)
        return str(result)

    async def query(self, command: str) -> str:
        """
        Enqueue a query operation.

        :param command: SCPI query string to send to the instrument.
        :type command: str

        :return: Response read from the instrument.
        :rtype: str

        :raises ClientConnectionError: If the worker is not started, is
            closing, or is already closed.
        """
        result = await self._submit(OperationType.QUERY, command)
        return str(result)

    async def close(self):
        """
        Stop the worker and close the instrument.

        Enqueues a close operation, waits for the background task to finish,
        and marks the worker as closed.
        """
        if self._closed or self._closing:
            return

        self._closing = True
        loop = asyncio.get_running_loop()
        future: asyncio.Future[int | str | None] = loop.create_future()

        await self._queue.put(QueueItem(OperationType.CLOSE, None, future))

        try:
            await future
        finally:
            if self._task is not None:
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task

            self._closed = True
            self._closing = False

    async def _submit(
        self,
        op: OperationType,
        value: str | None,
    ) -> int | str | None:
        if self._closed:
            raise ClientConnectionError('Client is already closed')
        if self._closing:
            raise ClientConnectionError('Client is closing')
        if self._task is None:
            raise ClientConnectionError('Client worker is not started')

        loop = asyncio.get_running_loop()
        future: asyncio.Future[int | str | None] = loop.create_future()
        await self._queue.put(QueueItem(op, value, future))
        return await future

    async def _run(self):
        try:
            while True:
                item = await self._queue.get()
                try:
                    if item.type is OperationType.CLOSE:
                        await asyncio.to_thread(self._sync_close)
                        if not item.future.done():
                            item.future.set_result(None)
                        break

                    result = await self._execute_item(item)

                    if not item.future.done():
                        item.future.set_result(result)

                except asyncio.CancelledError:
                    raise
                except pyvisa.errors.VisaIOError as exc:
                    if not item.future.done():
                        item.future.set_exception(exc)
                except Exception as exc:
                    if not item.future.done():
                        item.future.set_exception(exc)
                finally:
                    self._queue.task_done()

        except asyncio.CancelledError:
            raise
        finally:
            self._fail_pending_operations(ClientStopped())
            self._closed = True

    async def _execute_item(self, item: QueueItem) -> int | str:
        match (item.type):
            case OperationType.WRITE:
                if item.value is None:
                    raise ValueError('Write operation requires command')
                return await asyncio.to_thread(
                    self._instrument.write, item.value
                )

            case OperationType.READ:
                return await asyncio.to_thread(self._instrument.read)

            case OperationType.QUERY:
                if item.value is None:
                    raise ValueError('Query operation requires command')
                return await asyncio.to_thread(
                    self._instrument.query, item.value
                )

            case _:
                raise ValueError(f'Unsupported operation type: {item.type}')

    def _sync_close(self):
        self._instrument.close()

    def _fail_pending_operations(self, exc: Exception):
        while True:
            try:
                item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            try:
                if not item.future.done():
                    item.future.set_exception(exc)
            finally:
                self._queue.task_done()
