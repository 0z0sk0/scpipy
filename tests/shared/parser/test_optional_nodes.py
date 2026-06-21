import pytest

from scpipy.shared.exceptions import ParseError


def test_parse_multiple_optional_nodes(parser):
    command = parser.parse('SOURce<Ch>:POWer[:LEVel][:IMMediate][:AMPLitude]')[
        0
    ]

    assert [node.full for node in command.nodes] == [
        'SOURce',
        'POWer',
        'LEVel',
        'IMMediate',
        'AMPLitude',
    ]
    assert [node.short for node in command.nodes] == [
        'SOUR',
        'POW',
        'LEV',
        'IMM',
        'AMPL',
    ]
    assert [node.optional for node in command.nodes] == [
        False,
        False,
        True,
        True,
        True,
    ]

    assert command.nodes[0].arg is not None
    assert command.nodes[0].arg.value == 'Ch'
    assert command.nodes[0].arg.pattern is True


def test_parse_single_optional_node(parser):
    command = parser.parse('POWer[:LEVel]')[0]
    assert [node.full for node in command.nodes] == ['POWer', 'LEVel']
    assert [node.optional for node in command.nodes] == [False, True]


def test_parse_no_optional_nodes(parser):
    command = parser.parse('POWer')[0]
    assert [node.full for node in command.nodes] == ['POWer']
    assert [node.optional for node in command.nodes] == [False]


def test_reject_unclosed_optional_node(parser):
    with pytest.raises(ParseError, match='Invalid bracket usage'):
        parser.parse('POWer[:LEVel')


def test_reject_empty_optional_node(parser):
    with pytest.raises(ParseError, match='Invalid node'):
        parser.parse('POWer[:]')


def test_reject_invalid_optional_syntax(parser):
    with pytest.raises(ParseError, match='Invalid node'):
        parser.parse('POWer[LEVel]')
