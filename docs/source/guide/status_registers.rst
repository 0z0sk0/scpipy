Status Register System
======================

Every :class:`scpipy.server.context.Context` has a ``status`` object.
The following built-in commands implement the core status model:

.. list-table:: Built-in commands
   :header-rows: 1
   :widths: 45 55

   * - Commands
     - Behaviour
   * - ``*ESE <value>``, ``*ESE?``
     - Standard Event Enable (0..255).
   * - ``*ESR?``
     - Return and clear Standard Event Status.
   * - ``*SRE <value>``, ``*SRE?``
     - Service Request Enable; bit 6 is ignored and reads as zero.
   * - ``*STB?``
     - Non-destructive Status Byte query with MSS in bit 6.
   * - ``STATus:OPERation[:EVENt]?``, ``STATus:QUEStionable[:EVENt]?``
     - Return and clear the selected group's latched events.
   * - ``:CONDition?`` under either group
     - Read current conditions without clearing anything.
   * - ``:ENABle``, ``:PTRansition``, ``:NTRansition`` under either group
     - Write/query enable and transition masks.
   * - ``STATus:PRESet``
     - Preset mandatory SCPI groups; events and error queue survive.
   * - ``*CLS``
     - Clear event registers and error queue; cancel pending OPC requests.
   * - ``*OPC``, ``*OPC?``, ``*WAI``
     - Synchronize with operations tracked by this context.

Status Byte
-----------

Use ``await context.status.wait_for_service_request()`` for an application-side
MSS notification.

The error queue is observed even when accessed directly through
``context.error_queue``.

``clear_errors()`` only empties the queue. Use ``clear_status()`` for the full
``*CLS`` action. Reading ESR does not consume errors from the queue.

Conditions and transition filters
---------------------------------

The application supplies real device conditions. For example:

.. code-block:: python

   from scpipy.server import OperationStatus, QuestionableStatus

   context.status.operation.update_condition(OperationStatus.MEASURING, True)
   context.status.operation.update_condition(OperationStatus.MEASURING, False)
   context.status.questionable.update_condition(QuestionableStatus.FREQUENCY, True)

Clearing, preset and power-on
-----------------------------

``*CLS`` clears events and error queue, preserving current conditions,
ESE/SRE, enable masks, filters and running operations. It disarms queued
``*OPC`` requests. An outstanding ``*OPC?`` on the same shared context is
abandoned without a response. ``*WAI`` continues waiting for its snapshot.

``STAT:PRESet`` sets both mandatory group enables to zero, PTR to 32767 and
NTR to zero.

Each new Context starts with Power On in ESR, ESE=0 and SRE=0.

With ``shared_context=False`` (by default), each client has independent status,
with ``shared_context=True``, clients share it.

Operation completion
--------------------

An awaited handler is sequential: its work finishes before the next command
runs. For overlapped work, register it before acknowledging the initiating
command. ``start_operation`` does this atomically in the owning event loop:

.. code-block:: python

   import asyncio
   from scpipy.server import OperationStatus, Router
   from scpipy.shared.errors import ScpiError

   router = Router()
   background_tasks = set()

   async def acquire(context):
       context.status.operation.update_condition(OperationStatus.MEASURING, True)
       try:
           await asyncio.sleep(0.1)
       finally:
           context.status.operation.update_condition(OperationStatus.MEASURING, False)

   @router.register('INITiate')
   def initiate(context):
       task = context.status.start_operation(acquire(context))
       background_tasks.add(task)

       def finished(task):
           background_tasks.discard(task)
           if not task.cancelled():
               error = task.exception()
               if error is not None:
                   context.push_error(ScpiError(-300, str(error)))

       task.add_done_callback(finished)

The application owns these tasks and must cancel/await them in lifespan shutdown.
Task failure or cancellation ends the operation.

Publish failure separately via ``push_error`` and/or conditions.
Use a task counter rather than a single MEASURING boolean if acquisitions
can overlap.
