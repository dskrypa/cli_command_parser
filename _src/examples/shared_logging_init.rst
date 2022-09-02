Shared Logging Init
*******************


::

    usage: build_docs.py {show} [--verbose [VERBOSE]] [--help]



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

    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE], -v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--help, -h``                        | Show this help message and exit (default: ``False``)                     |
    +---------------------------------------+--------------------------------------------------------------------------+


Subcommands
===========


Subcommand: show
----------------

Show the results of an action

::

    usage: build_docs.py show {attrs|hello|log_test|rst} [--verbose [VERBOSE]] [--help]



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

    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE], -v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +---------------------------------------+--------------------------------------------------------------------------+
    | ``--help, -h``                        | Show this help message and exit (default: ``False``)                     |
    +---------------------------------------+--------------------------------------------------------------------------+
