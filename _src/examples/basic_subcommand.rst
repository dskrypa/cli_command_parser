Basic Subcommand
****************


::

    usage: basic_subcommand.py {foo|bar} [--help]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +-------------+-----------------------------+
    | Subcommands | .. table::                  |
    |             |     :widths: auto           |
    |             |                             |
    |             |     +---------+-----------+ |
    |             |     | ``foo`` | Print foo | |
    |             |     +---------+-----------+ |
    |             |     | ``bar`` | Print bar | |
    |             |     +---------+-----------+ |
    +-------------+-----------------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +----------------+------------------------------------------------------+
    | ``--help, -h`` | Show this help message and exit (default: ``False``) |
    +----------------+------------------------------------------------------+


Subcommands
===========


Subcommand: foo
---------------

Print foo

::

    usage: basic_subcommand.py foo [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +----------------+------------------------------------------------------+
    | ``--help, -h`` | Show this help message and exit (default: ``False``) |
    +----------------+------------------------------------------------------+


Subcommand: bar
---------------

Print bar

::

    usage: basic_subcommand.py bar [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +----------------+------------------------------------------------------+
    | ``--help, -h`` | Show this help message and exit (default: ``False``) |
    +----------------+------------------------------------------------------+
