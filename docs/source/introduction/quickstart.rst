Quickstart
==========

Client example
--------------

.. code-block:: python

   from scpipy.client import Client

   async with Client('TCPIP::192.168.1.100::INSTR') as client:
       print(await client.query('*IDN?'))

Server example
--------------

.. code-block:: python

   from scpipy.server import Server, Router'

   router = Router()

   @router.register('SYSTem:READy[:STATe]?')
   def syst_ready_handler(context: Context):
       return '1'

   server = Server('127.0.0.1', 5025)
   server.include_router(router)
   server.run()
