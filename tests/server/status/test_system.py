import asyncio

import pytest

from scpipy.server.context import Context
from scpipy.server.status.models import StandardEvent, StatusByte
from scpipy.server.status.system import StatusSystem
from scpipy.shared.errors import ScpiError


def test_power_on_and_event_status_read_clear():
    status = StatusSystem()
    assert status.event_status == StandardEvent.POWER_ON
    assert status.status_byte == 0
    status.event_enable = 128
    assert status.status_byte == StatusByte.EVENT_STATUS
    assert status.read_event_status() == 128
    assert status.read_event_status() == status.status_byte == 0


def test_esb_and_mss_follow_masks_without_clearing_events():
    status = StatusSystem()
    status.clear()
    status.raise_event(StandardEvent.COMMAND_ERROR | StandardEvent.QUERY_ERROR)
    assert status.status_byte == 0
    status.event_enable = 32
    assert status.status_byte == 32
    status.service_request_enable = 32
    assert status.status_byte == 96
    assert status.status_byte == 96
    status.event_enable = 0
    assert status.status_byte == 0
    assert status.event_status == 36
    status.event_enable = 4
    assert status.status_byte == 96
    assert status.service_requested


@pytest.mark.parametrize(
    'mask,expected',
    [(0, 0), (64, 0), (255, 191), (96, 32)],
)
def test_sre_bit_six_is_ignored(mask, expected):
    status = StatusSystem()
    status.service_request_enable = mask
    assert status.service_request_enable == expected


@pytest.mark.parametrize('field', ['event_enable', 'service_request_enable'])
@pytest.mark.parametrize('value', [-1, 256, '1', 1.5])
def test_ieee_mask_setters_reject_invalid_values(field, value):
    with pytest.raises(ValueError):
        setattr(StatusSystem(), field, value)


@pytest.mark.parametrize(
    'code,event',
    [
        (-100, 32),
        (-199, 32),
        (-200, 16),
        (-299, 16),
        (-300, 8),
        (-399, 8),
        (123, 8),
        (-400, 4),
        (-499, 4),
        (-500, 128),
        (-599, 128),
        (-600, 64),
        (-699, 64),
        (-700, 2),
        (-799, 2),
        (-800, 1),
        (-899, 1),
        (0, 0),
        (-99, 0),
        (-900, 0),
    ],
)
def test_error_event_classification(code, event):
    status = StatusSystem()
    status.clear()
    status.record_error(code)
    assert status.read_event_status() == event


def test_error_queue_summary_is_independent_of_esr_reading():
    context = Context()
    context.clear_status()
    context.status.event_enable = 32
    context.status.service_request_enable = 36
    context.push_error(ScpiError(-102, 'Syntax error'))
    assert context.status.status_byte == 100
    assert context.status.read_event_status() == 32
    assert context.status.status_byte == 68
    assert context.get_error() == '-102,"Syntax error"'
    assert context.status.status_byte == 0


def test_consuming_queue_does_not_clear_latched_standard_events():
    context = Context()
    context.clear_status()
    context.push_error(ScpiError(-222, 'Data out of range'))
    context.get_error()
    assert context.status.status_byte == 0
    assert context.status.read_event_status() == 16


def test_direct_queue_access_is_observed_and_overflow_records_both_causes():
    context = Context(error_queue_size=2)
    context.clear_status()
    context.error_queue.put(ScpiError(-102, 'Syntax error'))
    context.error_queue.put(ScpiError(-102, 'Syntax error'))
    context.status.read_event_status()
    context.error_queue.put(ScpiError(-222, 'Data out of range'))
    assert context.status.read_event_status() == 24
    assert len(context.error_queue) == 2
    assert context.error_queue.get() == '-102,"Syntax error"'
    context.error_queue.put(ScpiError(-410, 'Query INTERRUPTED'))
    assert context.status.read_event_status() == 4
    context.error_queue.clear()
    assert context.status.status_byte == 0


def test_more_errors_when_full_still_latch_class_and_overflow_survives():
    context = Context(error_queue_size=1)
    context.clear_status()
    context.push_error(ScpiError(-102, 'Syntax error'))
    context.push_error(ScpiError(-102, 'Syntax error'))
    context.status.read_event_status()
    context.push_error(ScpiError(-222, 'Data out of range'))
    assert context.status.read_event_status() == 16
    assert context.get_error() == '-350,"Queue overflow"'


def test_operation_and_questionable_summary_bits():
    status = StatusSystem()
    for register, bit in [(status.operation, 128), (status.questionable, 8)]:
        register.set_condition(16)
        assert not status.status_byte & bit
        register.enable = 16
        assert status.status_byte & bit
        assert register.condition == 16
        register.read_event()
        assert not status.status_byte & bit


def test_cls_preserves_enable_filters_and_real_conditions():
    context = Context()
    status = context.status
    status.event_enable = 255
    status.service_request_enable = 255
    for group in (status.operation, status.questionable):
        group.enable = 5
        group.negative_transition = 2
        group.set_condition(5)
    context.push_error(ScpiError(-222, 'Data out of range'))
    context.clear_status()
    assert status.event_status == status.status_byte == 0
    assert status.event_enable == 255
    assert status.service_request_enable == 191
    assert context.get_error() == '0,"No error"'
    for group in (status.operation, status.questionable):
        assert group.condition == 5
        assert group.enable == 5
        assert group.negative_transition == 2
        assert group.positive_transition == 32767
        assert group.event == 0


def test_preset_does_not_clear_ieee_events_masks_queue_or_conditions():
    context = Context()
    status = context.status
    context.push_error(ScpiError(-102, 'Syntax error'))
    status.event_enable = 32
    status.service_request_enable = 4
    status.operation.enable = 5
    status.operation.set_condition(5)
    status.operation.positive_transition = 0
    status.operation.negative_transition = 5
    before = status.event_status
    status.preset()
    assert status.event_status == before
    assert (status.event_enable, status.service_request_enable) == (32, 4)
    assert len(context.error_queue) == 1
    assert status.operation.condition == status.operation.event == 5
    assert (
        status.operation.enable,
        status.operation.positive_transition,
        status.operation.negative_transition,
    ) == (0, 32767, 0)


@pytest.mark.asyncio
async def test_mss_waiter_and_mav_pending_context_are_level_sensitive():
    status = StatusSystem()
    status.service_request_enable = 16
    assert not status.service_requested
    waiter = asyncio.create_task(status.wait_for_service_request())
    await asyncio.sleep(0)
    assert not waiter.done()
    with status.response_pending():
        assert status.status_byte == 80
        await asyncio.wait_for(waiter, 2)
        with status.response_pending():
            assert status.status_byte == 80
        assert status.status_byte == 80
    assert status.status_byte == 0
    with pytest.raises(RuntimeError):
        with status.response_pending():
            raise RuntimeError('transport failed')
    assert status.status_byte == 0
