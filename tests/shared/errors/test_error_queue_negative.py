import pytest

from scpipy.shared.errors import ErrorQueue


@pytest.mark.parametrize('bad_size', [0, -1, -10])
def test_init_rejects_non_positive_max_size(bad_size):
    with pytest.raises(ValueError, match='max_size must be > 0'):
        ErrorQueue(max_size=bad_size)


def test_get_empty_queue_call_multiple_times(queue, no_error):
    assert queue.get() == no_error
    assert queue.get() == no_error
    assert queue.get() == no_error
