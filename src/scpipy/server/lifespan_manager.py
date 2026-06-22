class LifespanManager:
    """
    Manage application lifespan hooks and shared state.

    The lifespan manager enters the user-provided async context manager during
    startup and exits it during shutdown. If the context manager yields a
    dictionary, its contents are merged into the shared state.

    :param generator: Async context manager factory used to handle startup and
        shutdown logic.
    :type generator: Any
    """

    def __init__(self, generator):
        self._generator = generator
        self._ctx = None

        self.state = {}

    async def startup(self, target):
        """
        Run startup logic and initialize shared state.

        If the lifespan factory returns an async context manager whose
        ``__aenter__()`` result is a dictionary, that dictionary is merged into
        ``state``.

        :param target: Target object passed to the lifespan factory.
        :type target: Any
        """
        if not self._generator:
            return

        self._ctx = self._generator(target)

        # Safe generator extract
        user_state = await self._ctx.__aenter__()
        if isinstance(user_state, dict):
            self.state.update(user_state)

    async def shutdown(self):
        """
        Run shutdown logic and clear managed state.

        Exits the active async context manager, resets the internal context
        reference, and clears the shared state dictionary.
        """
        if not self._ctx:
            return

        try:
            await self._ctx.__aexit__(None, None, None)
        finally:
            self._ctx = None
            self.state.clear()
