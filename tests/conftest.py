from unittest.mock import MagicMock

import pytest


@pytest.fixture
def instrument():
    resource = MagicMock()
    resource.write.return_value = 8
    resource.read.return_value = 'response'
    resource.query.return_value = '1'
    return resource
