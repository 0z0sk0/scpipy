import pytest

from scpipy.shared.parser import Parser


@pytest.fixture
def parser():
    return Parser()


@pytest.fixture
def simple_pattern(parser):
    return parser.parse('SOURce<channel>:POWer<some>')[0]


@pytest.fixture
def variadic_pattern(parser):
    return parser.parse(
        'SOURce<channel>:POWer<some>[:LEVel][:IMMediate][:AMPLitude] <values>'
    )[0]
