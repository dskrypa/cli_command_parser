Shared Logging Init
*******************


::

    usage: shared_logging_init.py {show} [--verbose [VERBOSE]] [--help]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +-------------+--------------------------------------------------+
    | Subcommands | .. table::                                       |
    |             |     :widths: auto                                |
    |             |                                                  |
    |             |     +----------+-------------------------------+ |
    |             |     | ``show`` | Show the results of an action | |
    |             |     +----------+-------------------------------+ |
    +-------------+--------------------------------------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------+---------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                         |
    +-------------------------------------------+---------------------------------------------------------+


Subcommands
===========


Subcommand: show
----------------

Show the results of an action

::

    usage: shared_logging_init.py show {attrs|hello|log_test|rst} [--verbose [VERBOSE]] [--help]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +---------+-------------------------+
    | Actions | .. table::              |
    |         |     :widths: auto       |
    |         |                         |
    |         |     +--------------+--+ |
    |         |     | ``attrs``    |  | |
    |         |     +--------------+--+ |
    |         |     | ``hello``    |  | |
    |         |     +--------------+--+ |
    |         |     | ``log_test`` |  | |
    |         |     +--------------+--+ |
    |         |     | ``rst``      |  | |
    |         |     +--------------+--+ |
    +---------+-------------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------+---------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                         |
    +-------------------------------------------+---------------------------------------------------------+
