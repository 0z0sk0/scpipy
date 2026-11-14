import pytest

from scpipy.shared.exceptions import ParseError
from scpipy.shared.parser import Parser


@pytest.mark.parametrize(
    'arguments',
    [
        '1,,2',
        ',1',
        '1,',
        ',1,2',
        '1,2,',
        '1, ,2',
        ' ,1,2',
        '1,2, ',
        ',',
        ',,',
        '"A,B",,2',
        '"",,2',
    ],
)
def test_reject_empty_command_parameters(arguments):
    with pytest.raises(ParseError, match='^Empty argument$'):
        Parser().parse('SOUR:POW ' + arguments)


@pytest.mark.parametrize(
    ('command', 'expected'),
    [
        ('SOUR:POW', []),
        ('SOUR:POW   ', []),
        ('SOUR:POW?', []),
        ('SOUR:POW 1, 2', ['1', '2']),
        ('DISP:TEXT "", \'\'', ['""', "''"]),
        ('DISP:TEXT "A,B", \'C;D\'', ['"A,B"', "'C;D'"]),
        ('DISP:TEXT "  "', ['"  "']),
    ],
)
def test_valid_command_parameters_are_preserved(command, expected):
    parsed = Parser().parse(command)

    assert len(parsed) == 1
    assert [argument.value for argument in parsed[0].args] == expected
