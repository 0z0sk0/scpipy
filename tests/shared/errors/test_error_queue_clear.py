def test_queue_clear(queue, sample_errors, no_error):
    error = sample_errors[0]

    queue.put(error)
    queue.clear()
    assert queue.get() == no_error


def test_clear_on_empty_queue(queue, no_error):
    queue.clear()
    assert queue.get() == no_error


def test_put_after_clear(queue, sample_errors):
    error = sample_errors[0]

    queue.clear()
    queue.put(error)

    assert queue.get() == str(error)
