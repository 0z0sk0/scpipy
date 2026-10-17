import pytest

from scpipy.shared.utils import (
    format_scpi_full_keyword,
    format_scpi_short_keyword,
    scpi_short_length,
)


@pytest.mark.parametrize(
    'word,short,full',
    [
        ('', '', ''),
        ('X', 'X', 'X'),
        ('ON', 'ON', 'ON'),
        ('OFF', 'OFF', 'OFF'),
        ('POWer', 'POW', 'POWer'),
        ('VOLTage', 'VOLT', 'VOLTage'),
        ('SYSTem', 'SYST', 'SYSTem'),
        ('READy', 'READ', 'READy'),
        ('IMMediate', 'IMM', 'IMMediate'),
        ('FREQuency', 'FREQ', 'FREQuency'),
    ],
)
def test_keyword_formatting(word, short, full):
    for variant in (word, word.lower(), word.upper()):
        assert scpi_short_length(variant) == len(short)
        assert format_scpi_short_keyword(variant) == short
        assert format_scpi_full_keyword(variant) == full
