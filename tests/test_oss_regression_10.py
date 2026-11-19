import asyncio
from unittest.mock import MagicMock, call

import pytest

from scpipy.client import Client


@pytest.mark.asyncio
async def test_client_sends_ordered_bulk_messages(monkeypatch, instrument):
    manager = MagicMock()
    manager.open_resource.return_value = instrument
    monkeypatch.setattr('pyvisa.ResourceManager', lambda: manager)
    instrument.query.side_effect = ['1;2', '3']

    def two_then_one(commands):
        assert commands == (':MEAS:VOLT?', ':SENS:CURR?', '*OPC?')
        return (2, 1)

    async with Client('GPIB0::1::INSTR', queue_size=1) as client:
        write_many = getattr(client, 'write_many', None)
        assert callable(write_many), 'Client lacks a bulk write operation'
        assert await write_many(
            ('SOUR:VOLT 1', ':OUTP ON', '*CLS', 'DISP:TEXT "a;b?"'),
        ) == [8]

        replies, response = await asyncio.gather(
            client.query_many(
                ('MEAS:VOLT?', 'SENS:CURR?', '*OPC?'),
                policy=two_then_one,
            ),
            client.read(),
        )
        assert replies == ['1;2', '3']
        assert response == 'response'
        assert await client.write_many(()) == []

        with pytest.raises(ValueError, match='only write'):
            await client.write_many(('*CLS', '*OPC?'))
        with pytest.raises(ValueError, match='every command'):
            await client.query_many(('*OPC?', '*IDN?'), policy=lambda _: (1,))

        assert instrument.method_calls == [
            call.write(':SOUR:VOLT 1;:OUTP ON;*CLS;:DISP:TEXT "a;b?"'),
            call.query(':MEAS:VOLT?;:SENS:CURR?'),
            call.query('*OPC?'),
            call.read(),
        ]
