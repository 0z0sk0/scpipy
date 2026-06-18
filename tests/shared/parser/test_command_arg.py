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
