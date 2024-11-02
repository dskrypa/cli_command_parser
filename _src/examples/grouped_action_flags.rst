Grouped Action Flags
********************


::

    usage: grouped_action_flags.py [--action-a] [--action-b] [--action-c] [--action-d] [--action-w] [--action-x] [--action-y] [--action-z] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +--------------------+---------------------------------+
    | ``--help``, ``-h`` | Show this help message and exit |
    +--------------------+---------------------------------+


.. rubric:: Mutually exclusive options

.. table::
    :widths: auto

    +----------------------------------------+--+
    | ``--action-a``, ``-a``                 |  |
    +----------------------------------------+--+
    | ``--action-b``, ``-b``                 |  |
    +----------------------------------------+--+
    |                                           |
    | .. rubric:: Mutually dependent options    |
    |                                           |
    | .. table::                                |
    |     :widths: auto                         |
    |                                           |
    |     +------------------------+--+         |
    |     | ``--action-c``, ``-c`` |  |         |
    |     +------------------------+--+         |
    |     | ``--action-d``, ``-d`` |  |         |
    |     +------------------------+--+         |
    +----------------------------------------+--+


.. rubric:: Mutually dependent options

.. table::
    :widths: auto

    +----------------------------------------+--+
    | ``--action-w``, ``-w``                 |  |
    +----------------------------------------+--+
    | ``--action-x``, ``-x``                 |  |
    +----------------------------------------+--+
    |                                           |
    | .. rubric:: Mutually exclusive options    |
    |                                           |
    | .. table::                                |
    |     :widths: auto                         |
    |                                           |
    |     +------------------------+--+         |
    |     | ``--action-y``, ``-y`` |  |         |
    |     +------------------------+--+         |
    |     | ``--action-z``, ``-z`` |  |         |
    |     +------------------------+--+         |
    +----------------------------------------+--+
