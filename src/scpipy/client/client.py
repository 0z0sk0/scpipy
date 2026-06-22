import asyncio
import contextlib
import pyvisa


from scpipy.client.exceptions import ClientConnectionError
from scpipy.client.worker import Worker


class Client:
    """
    Asynchronous SCPI client built on top of PyVISA.

    Manages instrument connection lifecycle, configures the underlying VISA
    resource, and provides asynchronous methods for write, read, and query
    operations.

    :param resource: VISA resource string used to open the instrument.
    :type resource: str
    :param backend: Optional PyVISA backend specification.
    :type backend: str | None
    :param open_timeout: Timeout for opening the VISA resource, in milliseconds.
    :type open_timeout: int
    :param io_timeout: I/O timeout for instrument operations, in milliseconds.
    :type io_timeout: int
    :param read_termination: Read termination character sequence.
    :type read_termination: str
    :param write_termination: Write termination character sequence.
    :type write_termination: str
    :param encoding: Text encoding used for instrument communication.
    :type encoding: str
    :param chunk_size: Maximum chunk size used by the VISA resource.
    :type chunk_size: int
    :param queue_size: Maximum number of queued worker operations. A value of
        ``0`` uses an unbounded queue.
    :type queue_size: int
    """

    def __init__(
        self,
        resource: str,
        *,
        backend: str | None = None,
        open_timeout: int = 5000,
        io_timeout: int = 5000,
        read_termination: str = '\n',
        write_termination: str = '\n',
        encoding: str = 'utf-8',
        chunk_size: int = 1024 * 1024,
        queue_size: int = 0,
    ):
        self._resource = resource
        self._backend = backend
        self._open_timeout = open_timeout
        self._io_timeout = io_timeout
        self._read_termination = read_termination
        self._write_termination = write_termination
        self._encoding = encoding
        self._chunk_size = chunk_size
        self._queue_size = queue_size

        self._rm: pyvisa.ResourceManager | None = None
        self._instrument: pyvisa.resources.MessageBasedResource | None = None
        self._worker: Worker | None = None

        self._started = False
        self._closed = False

    async def connect(self):
        """
        Open the VISA connection and start the background worker.

        If the client is already connected, this method returns immediately.

        :raises ClientConnectionError: If the client is already closed or if
            the VISA resource cannot be opened.
        """
        if self._started:
            return
        if self._closed:
            raise ClientConnectionError('Client is already closed')

        try:
            if self._backend:
                self._rm = await asyncio.to_thread(
                    pyvisa.ResourceManager, self._backend
                )
            else:
                self._rm = await asyncio.to_thread(pyvisa.ResourceManager)

            self._instrument = await asyncio.to_thread(
                self._rm.open_resource,
                self._resource,
                open_timeout=self._open_timeout,
                resource_pyclass=pyvisa.resources.MessageBasedResource,
            )

            self._instrument.timeout = self._io_timeout
            self._instrument.read_termination = self._read_termination
            self._instrument.write_termination = self._write_termination
            self._instrument.chunk_size = self._chunk_size
            self._instrument.encoding = self._encoding

            self._worker = Worker(
                self._instrument, queue_size=self._queue_size
            )
            self._worker.start()
            self._started = True

        except pyvisa.errors.VisaIOError as exc:
            await self._cleanup_connect_error()
            raise ClientConnectionError(
                f'Failed to connect to {self._resource}: {exc}'
            ) from exc
        except Exception:
            await self._cleanup_connect_error()
            raise

    async def close(self):
        """
        Close the client connection and release all associated resources.

        This stops the background worker, closes the VISA resource manager, and
        marks the client as closed.
        """
        if self._closed:
            return

        try:
            if self._worker is not None:
                await self._worker.close()
        finally:
            self._worker = None
            self._instrument = None

            if self._rm is not None:
                await asyncio.to_thread(self._rm.close)
                self._rm = None

            self._started = False
            self._closed = True

    async def __aenter__(self) -> 'Client':
        """
        Enter the asynchronous client context.

        Connects the client and returns the client instance.

        :return: Connected client instance.
        :rtype: Client
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        Exit the asynchronous client context.

        Closes the client connection and releases all associated resources.

        :param exc_type: Exception type raised inside the context, if any.
        :type exc_type: type | None
        :param exc: Exception instance raised inside the context, if any.
        :type exc: BaseException | None
        :param tb: Traceback associated with the exception, if any.
        :type tb: Any
        """
        await self.close()

    async def write(self, command: str) -> int:
        """
        Send a command to the instrument.

        :param command: SCPI command string to send.
        :type command: str

        :return: Number of bytes written.
        :rtype: int

        :raises ClientConnectionError: If the client is not connected or is
            already closed.
        """
        worker = self._get_worker()
        return await worker.write(command)

    async def read(self) -> str:
        """
        Read a response from the instrument.

        :return: Decoded instrument response.
        :rtype: str

        :raises ClientConnectionError: If the client is not connected or is
            already closed.
        """
        worker = self._get_worker()
        return await worker.read()

    async def query(self, command: str) -> str:
        """
        Send a query command and read the response.

        :param command: SCPI query command to send.
        :type command: str

        :return: Decoded instrument response.
        :rtype: str

        :raises ClientConnectionError: If the client is not connected or is
            already closed.
        """
        worker = self._get_worker()
        return await worker.query(command)

    def _get_worker(self) -> Worker:
        if not self._started or self._worker is None:
            raise ClientConnectionError('Client is not connected')
        if self._closed:
            raise ClientConnectionError('Client is already closed')
        return self._worker

    async def _cleanup_connect_error(self):
        self._worker = None
        self._instrument = None

        if self._rm is not None:
            with contextlib.suppress(Exception):
                await asyncio.to_thread(self._rm.close)
            self._rm = None

        self._started = False
