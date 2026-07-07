import pytest

from scpipy.shared.errors import ErrorQueue, DefaultScpiErrors


@pytest.fixture
def queue():
    return ErrorQueue(max_size=3)


@pytest.fixture
def small_queue():
    return ErrorQueue(max_size=2)


@pytest.fixture
def no_error():
    return str(DefaultScpiErrors.NO_ERROR.value)


@pytest.fixture
def overflow_error():
    return str(DefaultScpiErrors.QUEUE_OVERFLOW.value)


@pytest.fixture
def sample_errors():
    candidates = [
        error.value
        for error in DefaultScpiErrors
        if error.name
        not in [DefaultScpiErrors.NO_ERROR, DefaultScpiErrors.QUEUE_OVERFLOW]
    ]

    if len(candidates) < 3:
        pytest.skip(
            'Need at least 3 SCPI errors without NO_ERROR and QUEUE_OVERFLOW'
        )

    return candidates[:3]
