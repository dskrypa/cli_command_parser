Advanced Subcommand
*******************


::

    usage: build_docs.py {foo|run foo|run bar|baz} [--verbose [VERBOSE]] [--help]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +-------------+---------------------------------+
    | Subcommands | .. table::                      |
    |             |     :widths: auto               |
    |             |                                 |
    |             |     +-------------+-----------+ |
    |             |     | ``foo``     | Print foo | |
    |             |     +-------------+-----------+ |
    |             |     | ``run foo`` | Run foo   | |
    |             |     +-------------+-----------+ |
    |             |     | ``run bar`` | Print bar | |
    |             |     +-------------+-----------+ |
    |             |     | ``baz``     | Print baz | |
    |             |     +-------------+-----------+ |
    +-------------+---------------------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                                          |
    +-------------------------------------------+--------------------------------------------------------------------------+


Subcommands
===========


Subcommand: foo
---------------

Print foo

::

    usage: build_docs.py foo [--verbose [VERBOSE]] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                                          |
    +-------------------------------------------+--------------------------------------------------------------------------+


Subcommand: run foo
-------------------

Run foo

::

    usage: build_docs.py run foo [--verbose [VERBOSE]] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                                          |
    +-------------------------------------------+--------------------------------------------------------------------------+


Subcommand: run bar
-------------------

Print bar

::

    usage: build_docs.py run bar [--verbose [VERBOSE]] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                                          |
    +-------------------------------------------+--------------------------------------------------------------------------+


Subcommand: baz
---------------

Print baz

::

    usage: build_docs.py baz [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +--------------------+---------------------------------+
    | ``--help``, ``-h`` | Show this help message and exit |
    +--------------------+---------------------------------+
