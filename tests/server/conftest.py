import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from scpipy.server.builtin_router import builtin_router
from scpipy.server.routing import Router


@pytest.fixture
def server_factory(monkeypatch):
    module = importlib.import_module('scpipy.server.server')
    router = Router()
    router.include_router(builtin_router)
    monkeypatch.setattr(module, 'builtin_router', router)
    return module.Server


@pytest.fixture
def streams():
    reader = MagicMock()
    reader.readline = AsyncMock(return_value=b'')
    writer = MagicMock()
    writer.drain = AsyncMock()
    writer.wait_closed = AsyncMock()
    return reader, writer
