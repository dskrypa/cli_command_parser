Advanced Subcommand
*******************


::

    usage: advanced_subcommand.py {foo|run foo|run bar|baz} [--verbose [VERBOSE]] [--help]



.. rubric:: Subcommands

.. table::
    :widths: auto

    +-------------+-----------+
    | ``foo``     | Print foo |
    +-------------+-----------+
    | ``run foo`` | Run foo   |
    +-------------+-----------+
    | ``run bar`` | Print bar |
    +-------------+-----------+
    | ``baz``     | Print baz |
    +-------------+-----------+


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


Subcommand: foo
---------------

Print foo

::

    usage: advanced_subcommand.py foo [--verbose [VERBOSE]] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------+---------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                         |
    +-------------------------------------------+---------------------------------------------------------+


Subcommand: run foo
-------------------

Run foo

::

    usage: advanced_subcommand.py run foo [--verbose [VERBOSE]] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------+---------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                         |
    +-------------------------------------------+---------------------------------------------------------+


Subcommand: run bar
-------------------

Print bar

::

    usage: advanced_subcommand.py run bar [--verbose [VERBOSE]] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------+---------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                         |
    +-------------------------------------------+---------------------------------------------------------+


Subcommand: baz
---------------

Print baz

::

    usage: advanced_subcommand.py baz [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +--------------------+---------------------------------+
    | ``--help``, ``-h`` | Show this help message and exit |
    +--------------------+---------------------------------+
