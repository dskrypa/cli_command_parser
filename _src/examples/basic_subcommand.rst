Basic Subcommand
****************


::

    usage: basic_subcommand.py {foo,bar} [--help]


.. table:: Positional arguments
    :widths: 11 19

    +-------------+---------------------+
    | Subcommands | +-----+-----------+ |
    |             | | foo | Print foo | |
    |             | +-----+-----------+ |
    |             | | bar | Print bar | |
    |             | +-----+-----------+ |
    +-------------+---------------------+

.. table:: Optional arguments
    :widths: 10 48

    +------------+--------------------------------------------------+
    | --help, -h | Show this help message and exit (default: False) |
    +------------+--------------------------------------------------+


Subcommands
===========


Subcommand: foo
---------------

Print foo

::

    usage: basic_subcommand.py foo [--help]


.. table:: Optional arguments
    :widths: 10 48

    +------------+--------------------------------------------------+
    | --help, -h | Show this help message and exit (default: False) |
    +------------+--------------------------------------------------+


Subcommand: bar
---------------

Print bar

::

    usage: basic_subcommand.py bar [--help]


.. table:: Optional arguments
    :widths: 10 48

    +------------+--------------------------------------------------+
    | --help, -h | Show this help message and exit (default: False) |
    +------------+--------------------------------------------------+
