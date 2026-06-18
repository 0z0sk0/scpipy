def test_parser_single_node_with_numeric_node_arg(parser):
    parsed_command = parser.parse('SOURce1')[0]

    assert len(parsed_command.nodes) == 1

    node = parsed_command.nodes[0]
    assert node.short == 'SOUR'
    assert node.full == 'SOURce'
    assert node.optional is False
    assert node.arg
    assert node.arg.value == '1'


def test_parser_rooted_command_with_numeric_node_arg(parser):
    parsed_command = parser.parse(':SOURce1:POWer')[0]

    assert parsed_command.root_node is True
    assert len(parsed_command.nodes) == 2

    root_node = parsed_command.nodes[0]
    assert root_node.short == 'SOUR'
    assert root_node.full == 'SOURce'
    assert root_node.optional is False
    assert root_node.arg
    assert root_node.arg.value == '1'

    child_node = parsed_command.nodes[1]
    assert child_node.short == 'POW'
    assert child_node.full == 'POWer'
    assert child_node.optional is False
    assert not child_node.arg


def test_parser_optional_node_with_numeric_node_arg(parser):
    parsed_command = parser.parse('[:SOURce]:POWer')[0]

    assert len(parsed_command.nodes) == 2

    optional_node = parsed_command.nodes[0]
    assert optional_node.short == 'SOUR'
    assert optional_node.full == 'SOURce'
    assert optional_node.optional is True
    assert not optional_node.arg

    child_node = parsed_command.nodes[1]
    assert child_node.short == 'POW'
    assert child_node.full == 'POWer'
    assert child_node.optional is False
    assert not child_node.arg


def test_parser_query_with_numeric_node_arg(parser):
    parsed_command = parser.parse('SOURce1:POWer?')[0]

    assert parsed_command.query is True
    assert len(parsed_command.nodes) == 2

    root_node = parsed_command.nodes[0]
    assert root_node.arg
    assert root_node.arg.value == '1'
