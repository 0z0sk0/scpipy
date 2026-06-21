import pytest

from scpipy.shared.exceptions import ParseError


def test_parser_command_with_single_numeric_arg(parser):
    parsed_command = parser.parse('SOURce:POWer 10')[0]

    assert len(parsed_command.args) == 1
    assert parsed_command.args[0].value == '10'


def test_parser_command_with_multiple_args(parser):
    parsed_command = parser.parse('SOURce:POWer 10,20,30')[0]

    assert len(parsed_command.args) == 3
    assert [arg.value for arg in parsed_command.args] == ['10', '20', '30']


def test_parser_command_with_enum_arg(parser):
    parsed_command = parser.parse('SOURce:FUNCtion SIN')[0]

    assert len(parsed_command.args) == 1
    assert parsed_command.args[0].value == 'SIN'


def test_parser_command_with_string_arg(parser):
    parsed_command = parser.parse('SOURce:NAMe "TEST"')[0]

    assert len(parsed_command.args) == 1
    assert parsed_command.args[0].value == '"TEST"'


def test_parse_node_with_numeric_arg(parser):
    parsed_command = parser.parse(':CHANnel1:DISPlay?')[0]
    assert parsed_command.nodes[0].arg is not None
    assert parsed_command.nodes[0].arg.value == '1'


def test_parse_node_with_pattern_arg(parser):
    parsed_command = parser.parse(':CHANnel<Arg>:DISPlay?')[0]
    assert parsed_command.nodes[0].arg is not None
    assert parsed_command.nodes[0].arg.value == 'Arg'


def test_parse_node_with_multiple_pattern_args(parser):
    parsed_command = parser.parse(':SENSe<Ch>:TRACe<Tr>:DATA?')[0]
    assert parsed_command.nodes[0].arg.value == 'Ch'
    assert parsed_command.nodes[1].arg.value == 'Tr'


def test_reject_empty_pattern_arg(parser):
    with pytest.raises(ParseError, match='Invalid node'):
        parser.parse(':CHANnel<>:DISPlay?')


def test_reject_mixed_numeric_and_pattern_arg(parser):
    with pytest.raises(ParseError, match='Invalid node'):
        parser.parse(':CHANnel1<Arg>:DISPlay?')


def test_reject_mixed_optional_node_and_pattern_arg(parser):
    with pytest.raises(ParseError, match='Invalid bracket usage'):
        parser.parse(':CHANnel[:SELected]<Arg>:DISPlay?')
