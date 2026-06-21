SCPIpy: Python SCPI I/O library with built-in async client and server
============================================


SCPIpy is a Python SCPI I/O library with a built-in client and server.
It provides a clean, asyncio-based interface for sending SCPI commands
to test instruments (via PyVISA) and for building SCPI servers.


.. toctree::
   :maxdepth: 2
   :caption: User Guide

   introduction/installation
   introduction/quickstart

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/client
   api/server
   api/shared

.. toctree::
   :maxdepth: 1
   :caption: Project

   introduction/license


Installation
------------

.. code-block:: bash

   pip install scpipy

Requires Python 3.10+ and PyVISA.

Architecture Overview
---------------------

**SCPIpy** is split into three subpackages:

* **client** — asyncio SCPI client for
  communicating with real instruments over PyVISA transports.
* **server** — asyncio SCPI server for building instrument servers.
* **shared** — SCPI parser with AST nodes, and error definitions shared by
  both client and server.

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
