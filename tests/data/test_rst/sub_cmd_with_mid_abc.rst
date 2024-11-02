sub_cmd_with_mid_abc
********************

Test case for RST documentation generation.


::

    usage: sub_cmd_with_mid_abc.py {sub} [--foo FOO] [--help]


test


.. rubric:: Subcommands

.. table::
    :widths: auto

    +---------+--------+
    | ``sub`` | do foo |
    +---------+--------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +--------------------+---------------------------------+
    | ``--foo FOO``      |                                 |
    +--------------------+---------------------------------+
    | ``--help``, ``-h`` | Show this help message and exit |
    +--------------------+---------------------------------+


Subcommands
===========


Subcommand: sub
---------------

do foo

::

    usage: sub_cmd_with_mid_abc.py sub [--foo FOO] [--help] [--bar] [--baz]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +--------------------+---------------------------------+
    | ``--foo FOO``      |                                 |
    +--------------------+---------------------------------+
    | ``--help``, ``-h`` | Show this help message and exit |
    +--------------------+---------------------------------+
    | ``--bar``          |                                 |
    +--------------------+---------------------------------+
    | ``--baz``          |                                 |
    +--------------------+---------------------------------+
