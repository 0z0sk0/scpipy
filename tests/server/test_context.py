import pytest

from scpipy.server.context import Context
from scpipy.shared.errors import DefaultScpiErrors, ScpiError


def test_error_queue_is_fifo_and_clear_preserves_state():
    context = Context(state={'operator': 'test'})
    context.push_error(ScpiError(-1, 'first'))
    context.push_error(ScpiError(-2, 'second'))
    assert context.get_error() == '-1,"first"'
    context.clear_errors()
    assert context.get_error() == '0,"No error"'
    assert context.state == {'operator': 'test'}


def test_contexts_have_independent_default_state_and_queues():
    first, second = Context(), Context()
    first.state['changed'] = True
    first.push_error(DefaultScpiErrors.SYNTAX_ERROR.value)
    assert second.state == {}
    assert second.get_error() == '0,"No error"'


def test_nonempty_state_is_shared_by_reference():
    state = {'ready': False}
    context = Context(state=state)
    assert context.state is state
    state['ready'] = True
    assert context.state['ready'] is True


def test_error_queue_capacity_is_forwarded():
    context = Context(error_queue_size=2)
    for code in (-1, -2, -3):
        context.push_error(ScpiError(code, str(code)))
    assert context.get_error() == '-1,"-1"'
    assert context.get_error() == '-350,"Queue overflow"'
    assert context.get_error() == '0,"No error"'


@pytest.mark.parametrize('size', [0, -1])
def test_context_rejects_invalid_error_queue_size(size):
    with pytest.raises(ValueError, match='max_size'):
        Context(error_queue_size=size)
