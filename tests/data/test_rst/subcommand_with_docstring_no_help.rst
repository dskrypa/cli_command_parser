subcommand_with_docstring_no_help
*********************************


::

    usage: foo.py {bar|baz} [--help]



.. rubric:: Subcommands

.. table::
    :widths: auto

    +---------+-------------+
    | ``bar`` | This is bar |
    +---------+-------------+
    | ``baz`` | Do baz      |
    +---------+-------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +--------------------+---------------------------------+
    | ``--help``, ``-h`` | Show this help message and exit |
    +--------------------+---------------------------------+


Subcommands
===========


Subcommand: bar
---------------

This is bar

::

    usage: foo.py bar [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +--------------------+---------------------------------+
    | ``--help``, ``-h`` | Show this help message and exit |
    +--------------------+---------------------------------+


Subcommand: baz
---------------

Do baz

::

    usage: foo.py baz [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +--------------------+---------------------------------+
    | ``--help``, ``-h`` | Show this help message and exit |
    +--------------------+---------------------------------+
