Lifespan Events
===================

We are supporting lifespan events for managing the
startup and shutdown lifecycle of the SCPI server.

Usage example
-------------

.. code-block:: python

   from contextlib import asynccontextmanager
   from scpipy.server import Server, Router

   @asynccontextmanager
   async def lifespan(server: Server):
       # Prepare
       yield
       # Clean-up

   server = Server('127.0.0.1', 5025, lifespan=lifespan)
   server.run()
