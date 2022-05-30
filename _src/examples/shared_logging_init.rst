Shared Logging Init
*******************


::

    usage: shared_logging_init.py {show} [--verbose [VERBOSE]] [--help]


.. table:: Positional arguments
    :widths: 11 40

    +-------------+------------------------------------------+
    | Subcommands | +------+-------------------------------+ |
    |             | | show | Show the results of an action | |
    |             | +------+-------------------------------+ |
    +-------------+------------------------------------------+

.. table:: Optional arguments
    :widths: 33 68

    +-----------------------------------+----------------------------------------------------------------------+
    | --verbose [VERBOSE], -v [VERBOSE] | Increase logging verbosity (can specify multiple times) (default: 0) |
    +-----------------------------------+----------------------------------------------------------------------+
    | --help, -h                        | Show this help message and exit (default: False)                     |
    +-----------------------------------+----------------------------------------------------------------------+


Subcommands
===========


Subcommand: show
----------------

Show the results of an action

::

    usage: shared_logging_init.py show {attrs,hello,log_test,rst} [--verbose [VERBOSE]] [--help]


.. table:: Positional arguments
    :widths: 7 15

    +---------+-----------------+
    | Actions | +----------+--+ |
    |         | | attrs    |  | |
    |         | +----------+--+ |
    |         | | hello    |  | |
    |         | +----------+--+ |
    |         | | log_test |  | |
    |         | +----------+--+ |
    |         | | rst      |  | |
    |         | +----------+--+ |
    +---------+-----------------+

.. table:: Optional arguments
    :widths: 33 68

    +-----------------------------------+----------------------------------------------------------------------+
    | --verbose [VERBOSE], -v [VERBOSE] | Increase logging verbosity (can specify multiple times) (default: 0) |
    +-----------------------------------+----------------------------------------------------------------------+
    | --help, -h                        | Show this help message and exit (default: False)                     |
    +-----------------------------------+----------------------------------------------------------------------+
