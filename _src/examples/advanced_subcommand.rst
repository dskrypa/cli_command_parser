Advanced Subcommand
*******************


::

    usage: advanced_subcommand.py {foo|run foo|run bar|baz} [--verbose [VERBOSE]] [--help]



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

    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE], -v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--help, -h``                        | Show this help message and exit (default: ``False``)                     |
    +---------------------------------------+--------------------------------------------------------------------------+


Subcommands
===========


Subcommand: foo
---------------

Print foo

::

    usage: advanced_subcommand.py foo [--verbose [VERBOSE]] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE], -v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--help, -h``                        | Show this help message and exit (default: ``False``)                     |
    +---------------------------------------+--------------------------------------------------------------------------+


Subcommand: run foo
-------------------

Run foo

::

    usage: advanced_subcommand.py run foo [--verbose [VERBOSE]] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE], -v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--help, -h``                        | Show this help message and exit (default: ``False``)                     |
    +---------------------------------------+--------------------------------------------------------------------------+


Subcommand: run bar
-------------------

Print bar

::

    usage: advanced_subcommand.py run bar [--verbose [VERBOSE]] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE], -v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--help, -h``                        | Show this help message and exit (default: ``False``)                     |
    +---------------------------------------+--------------------------------------------------------------------------+


Subcommand: baz
---------------

Print baz

::

    usage: advanced_subcommand.py baz [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +----------------+------------------------------------------------------+
    | ``--help, -h`` | Show this help message and exit (default: ``False``) |
    +----------------+------------------------------------------------------+
