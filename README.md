SCPIpy
======

A python package for support of the Standard Commands for Programmable Instruments (SCPI) that allows you to create a server and an asynchronous client.

Descirption
-----------

The package provides (almost) full support for the SCPI standard for server creation, which simplifies the process of writing your code.

“Full support” refers to all standard functionality (except for status registry at this time), including a command parser that constructs an AST tree.

In addition, this package allows you to implement asynchronous communication with another SCPI server, since we have an asynchronous wrapper for pyVISA.

Requirements
------------

- Python (3.10+)
- VISA (or pyvisa-py for client)

Installation
------------

Using pip:

    $ pip install scpipy

Documentation
-------------

The documentation can be read online at https://scpipy.readthedocs.org
