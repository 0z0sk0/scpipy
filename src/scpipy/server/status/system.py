import asyncio
from collections.abc import Coroutine, Generator
from contextlib import contextmanager
from typing import Any, TypeVar

from scpipy.server.status.models import StandardEvent, StatusByte
from scpipy.server.status.register import StatusRegister
from scpipy.server.status.utils import _soft_clamp_value

Result = TypeVar('Result')


class StatusSystem:
    """
    Status Register System in SCPI is based on IEEE 488.2 standard
    and is used to track errors, monitor instrument status and
    compelete operations.
    """

    def __init__(self):
        self._event_status = int(StandardEvent.POWER_ON)
        self._event_enable = 0
        self._service_request_enable = 0
        self._error_available = False
        self._responses_pending = 0
        self._service_request = asyncio.Event()
        self.operation = StatusRegister(on_change=self._refresh)
        self.questionable = StatusRegister(on_change=self._refresh)
        self._pending: set[Any] = set()
        self._opc_requests: list[set[Any]] = []
        self._waiters: list[tuple[set[Any], asyncio.Future[bool], bool]] = []

    @property
    def event_status(self) -> int:
        """
        *ESR?, without clearing statuses.

        :return: A number from 0 to 255 representing sum of weights of set bits
        :rtype: int
        """
        return self._event_status

    def read_event_status(self) -> int:
        """
        *ESR?, with(!) clearing statuses.

        :return: A number from 0 to 255 representing sum of weights of set bits
        :rtype: int
        """
        result = self._event_status
        self._event_status = 0
        self._refresh()
        return result

    def raise_event(self, mask: int):
        self._event_status |= _soft_clamp_value(mask, 0xFF)
        self._refresh()

    @property
    def event_enable(self) -> int:
        """
        *ESE?, without clearing register.

        :return: Currently set mask
        :rtype: int
        """
        return self._event_enable

    @event_enable.setter
    def event_enable(self, value: int):
        """
        *ESE.

        It controls which specific events from register are passed on and
        triggering setting of ESB bit in main status byte.

        :param value: A number from 0 to 255.
        :type value: int
        """
        self._event_enable = _soft_clamp_value(value, 0xFF)
        self._refresh()

    @property
    def service_request_enable(self) -> int:
        """
        *SRE?, without clearing register.

        :return: Currently set mask
        :rtype: int
        """
        return self._service_request_enable

    @service_request_enable.setter
    def service_request_enable(self, value: int):
        """
        *SRE.

        It controls which specific summary bits from Status Byte Register
        are allowed to generate a Service Request.

        Bit 6 (MSS/RQS) is masked out as it cannot be enabled.

        :param value: A number from 0 to 255.
        :type value: int
        """
        self._service_request_enable = _soft_clamp_value(value, 0xFF) & 0xBF
        self._refresh()

    @property
    def status_byte(self) -> int:
        """
        *STB?, without clearing register.

        It reads the Status Byte Register, which aggregates summary bits
        from all other status groups and queues.

        Bit 6 (MSS) is dynamically set if any enabled bit is active.

        :return: Status Byte value representing current instrument state
        :rtype: int
        """

        value = 0
        if self._error_available:
            value |= StatusByte.ERROR_QUEUE
        if self.questionable.summary:
            value |= StatusByte.QUESTIONABLE
        if self._responses_pending:
            value |= StatusByte.MESSAGE_AVAILABLE
        if self._event_status & self._event_enable:
            value |= StatusByte.EVENT_STATUS
        if self.operation.summary:
            value |= StatusByte.OPERATION
        if value & self._service_request_enable:
            value |= StatusByte.MASTER_SUMMARY
        return value

    @property
    def service_requested(self) -> bool:
        """
        Check if a Service Request (SRQ) has been generated.

        It determines if instrument requires service by checking
        Master Summary Status (MSS) bit within the Status Byte.

        :return: True if service is requested, False otherwise
        :rtype: bool
        """
        return bool(self.status_byte & StatusByte.MASTER_SUMMARY)

    def _refresh(self):
        if self.service_requested:
            self._service_request.set()
        else:
            self._service_request.clear()

    async def wait_for_service_request(self):
        """Wait until a Service Request (SRQ) is triggered by instrument."""
        await self._service_request.wait()

    def set_error_available(self, value: bool):
        self._error_available = value
        self._refresh()

    @contextmanager
    def response_pending(self) -> Generator[None, None, None]:
        self._responses_pending += 1
        self._refresh()
        try:
            yield
        finally:
            self._responses_pending -= 1
            self._refresh()

    def record_error(self, code: int):
        if -199 <= code <= -100:
            event = StandardEvent.COMMAND_ERROR
        elif -299 <= code <= -200:
            event = StandardEvent.EXECUTION_ERROR
        elif -399 <= code <= -300 or code > 0:
            event = StandardEvent.DEVICE_DEPENDENT_ERROR
        elif -499 <= code <= -400:
            event = StandardEvent.QUERY_ERROR
        elif -599 <= code <= -500:
            event = StandardEvent.POWER_ON
        elif -699 <= code <= -600:
            event = StandardEvent.USER_REQUEST
        elif -799 <= code <= -700:
            event = StandardEvent.REQUEST_CONTROL
        elif -899 <= code <= -800:
            event = StandardEvent.OPERATION_COMPLETE
        else:
            return
        self.raise_event(event)

    def preset(self):
        """
        STATus:PRESet.

        It restores SCPI status registers to their default configurations.
        """
        self.operation.preset()
        self.questionable.preset()

    def clear(self):
        """
        *CLS.

        It clears all event status registers, error queue, and aborts any
        pending *OPC requests.
        """
        self._opc_requests.clear()
        for _, future, cancel_on_clear in tuple(self._waiters):
            if cancel_on_clear and not future.done():
                future.set_result(False)
        self._event_status = 0
        self.operation.clear()
        self.questionable.clear()
        self._refresh()

    @contextmanager
    def pending_operation(self) -> Generator[None, None, None]:
        token = object()
        self._pending.add(token)
        try:
            yield
        finally:
            self._complete_operation(token)

    def start_operation(
        self,
        coroutine: Coroutine[Any, Any, Result],
    ) -> asyncio.Task[Result]:
        """
        Start an asynchronous operation and register it as pending.

        It wraps the coroutine into an asyncio Task, attaches a unique tracking
        token to internal pending operations set, and schedules an automatic
        cleanup callback upon task completion.

        :param coroutine: Coroutine representing operation.
        :type coroutine: Coroutine[Any, Any, _Result]
        :return: Scheduled asyncio Task handling operation.
        :rtype: asyncio.Task[_Result]
        """
        task = asyncio.create_task(coroutine)
        token = object()
        self._pending.add(token)
        task.add_done_callback(
            lambda finished: self._complete_operation(token),
        )
        return task

    def _complete_operation(self, token: Any):
        self._pending.remove(token)
        for request in tuple(self._opc_requests):
            request.discard(token)
            if not request:
                self._opc_requests.remove(request)
                self.raise_event(StandardEvent.OPERATION_COMPLETE)
        for pending, future, _ in tuple(self._waiters):
            pending.discard(token)
            if not pending and not future.done():
                future.set_result(True)

    def request_operation_complete(self):
        """
        *OPC.

        It requests setting of Operation Complete bit in Standard
        Event Status Register when all pending operations have finished.

        If no operations are active, event is raised immediately.
        """
        if self._pending:
            self._opc_requests.append(set(self._pending))
        else:
            self.raise_event(StandardEvent.OPERATION_COMPLETE)

    async def wait_for_operations(
        self,
        *,
        cancel_on_clear: bool = False,
    ) -> bool:
        if not self._pending:
            return True
        future = asyncio.get_running_loop().create_future()
        waiter = (set(self._pending), future, cancel_on_clear)
        self._waiters.append(waiter)
        try:
            return await future
        finally:
            self._waiters.remove(waiter)
