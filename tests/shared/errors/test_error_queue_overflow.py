from scpipy.shared.errors import ErrorQueue


def test_overflow_replace_last_item_queue_overflow(
    small_queue,
    sample_errors,
    overflow_error,
    no_error,
):
    err1, err2, err3 = sample_errors

    small_queue.put(err1)
    small_queue.put(err2)
    small_queue.put(err3)

    assert small_queue.get() == str(err1)
    assert small_queue.get() == overflow_error
    assert small_queue.get() == no_error


def test_overflow_save_older_items(
    sample_errors,
    overflow_error,
    no_error,
):
    queue = ErrorQueue(max_size=3)
    err1, err2, err3 = sample_errors

    queue.put(err1)
    queue.put(err2)
    queue.put(err3)
    queue.put(err1)

    assert queue.get() == str(err1)
    assert queue.get() == str(err2)
    assert queue.get() == overflow_error
    assert queue.get() == no_error


def test_multiple_overflows(
    sample_errors,
    overflow_error,
    no_error,
):
    queue = ErrorQueue(max_size=2)
    err1, err2, err3 = sample_errors

    queue.put(err1)
    queue.put(err2)
    queue.put(err3)
    queue.put(err1)

    assert queue.get() == str(err1)
    assert queue.get() == overflow_error
    assert queue.get() == no_error
