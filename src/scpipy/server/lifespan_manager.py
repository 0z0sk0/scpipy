class LifespanManager:
    def __init__(self, generator):
        self._generator = generator
        self._ctx = None

        self.state = {}

    async def startup(self, target):
        if not self._generator:
            return

        self._ctx = self._generator(target)

        # Safe generator extract
        user_state = await self._ctx.__aenter__()
        if isinstance(user_state, dict):
            self.state.update(user_state)

    async def shutdown(self):
        if not self._ctx:
            return

        try:
            await self._ctx.__aexit__(None, None, None)
        finally:
            self._ctx = None
            self.state.clear()
