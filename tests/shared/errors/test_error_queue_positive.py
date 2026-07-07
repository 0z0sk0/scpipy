import pytest

from scpipy.shared.errors import ErrorQueue


def test_get_empty_queue_return_no_error(queue, no_error):
    assert queue.get() == no_error


def test_put_and_get_single_error(queue, sample_errors):
    error = sample_errors[0]

    queue.put(error)

    assert queue.get() == str(error)


def test_queue_return_items_in_fifo_order(queue, sample_errors):
    err1, err2, err3 = sample_errors

    queue.put(err1)
    queue.put(err2)
    queue.put(err3)

    assert queue.get() == str(err1)
    assert queue.get() == str(err2)
    assert queue.get() == str(err3)


def test_get_return_no_error_after_queue_empty(queue, sample_errors, no_error):
    err1 = sample_errors[0]

    queue.put(err1)

    assert queue.get() == str(err1)
    assert queue.get() == no_error


def test_clear_removes_all_items(queue, sample_errors, no_error):
    err1, err2, _ = sample_errors

    queue.put(err1)
    queue.put(err2)
    queue.clear()

    assert queue.get() == no_error


@pytest.mark.parametrize('count', [1, 2, 3])
def test_queue_max_size(count, sample_errors, no_error):
    queue = ErrorQueue(max_size=3)

    for error in sample_errors[:count]:
        queue.put(error)

    for error in sample_errors[:count]:
        assert queue.get() == str(error)

    assert queue.get() == no_error
