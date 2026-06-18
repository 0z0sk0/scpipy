import pytest

from scpipy.shared.parser import Parser


@pytest.fixture
def parser():
    return Parser()
