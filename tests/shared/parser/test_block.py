def test_parser_block_command(parser):
    parsed_commands = parser.parse('SYSTem:READy;STATe')

    assert len(parsed_commands) == 2

    first = parsed_commands[0]
    second = parsed_commands[1]

    assert first.query is False
    assert first.root_node is False
    assert first.common is False
    assert len(first.nodes) == 2

    first_root_node = first.nodes[0]
    assert first_root_node.short == 'SYST'
    assert first_root_node.full == 'SYSTem'
    assert first_root_node.optional is False

    first_child_node = first.nodes[1]
    assert first_child_node.short == 'READ'
    assert first_child_node.full == 'READy'
    assert first_child_node.optional is False

    assert second.query is False
    assert second.root_node is False
    assert second.common is False
    assert len(second.nodes) == 2

    second_root_node = second.nodes[0]
    assert second_root_node.short == 'SYST'
    assert second_root_node.full == 'SYSTem'
    assert second_root_node.optional is False

    second_child_node = second.nodes[1]
    assert second_child_node.short == 'STAT'
    assert second_child_node.full == 'STATe'
    assert second_child_node.optional is False


def test_parser_block_command_with_args(parser):
    parsed_commands = parser.parse('SOURce1:POWer 10;VOLTage 20')

    first = parsed_commands[0]
    second = parsed_commands[1]

    assert first.nodes[0].arg
    assert first.nodes[0].arg.value == '1'

    assert second.nodes[0].short == 'SOUR'
    assert second.nodes[0].arg
    assert second.nodes[0].arg.value == '1'
    assert second.nodes[1].short == 'VOLT'


def test_parser_block_command_with_mixed_query(parser):
    parsed_commands = parser.parse('SYSTem:READy?;STATe?')

    assert len(parsed_commands) == 2

    first = parsed_commands[0]
    second = parsed_commands[1]

    assert first.query is True
    assert first.common is False
    assert first.root_node is False

    assert second.query is True
    assert second.common is False
    assert second.root_node is False
    assert len(second.nodes) == 2


def test_parser_block_command_with_common_query(parser):
    parsed_commands = parser.parse('*IDN?;*CLS?')

    assert len(parsed_commands) == 2

    first = parsed_commands[0]
    second = parsed_commands[1]

    assert first.query is True
    assert first.common is True
    assert first.root_node is True
    assert len(first.nodes) == 1
    assert first.nodes[0].full == '*IDN'

    assert second.query is True
    assert second.common is True
    assert second.root_node is True
    assert len(second.nodes) == 1
    assert second.nodes[0].full == '*CLS'
