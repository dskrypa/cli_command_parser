Rest Api Wrapper
****************


::

    usage: rest_api_wrapper.py {show,find} [--verbose [VERBOSE]] [--env {dev,qa,uat,prod}] [--help]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +-------------+-----------------------------------+
    | Subcommands | .. table::                        |
    |             |     :widths: auto                 |
    |             |                                   |
    |             |     +----------+----------------+ |
    |             |     | ``show`` | Show an object | |
    |             |     +----------+----------------+ |
    |             |     | ``find`` | Find objects   | |
    |             |     +----------+----------------+ |
    +-------------+-----------------------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +----------------+------------------------------------------------------+
    | ``--help, -h`` | Show this help message and exit (default: ``False``) |
    +----------------+------------------------------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +---------------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE], -v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +---------------------------------------------------+--------------------------------------------------------------------------+
    | ``--env {dev,qa,uat,prod}, -e {dev,qa,uat,prod}`` | Environment to connect to (default: ``'prod'``)                          |
    +---------------------------------------------------+--------------------------------------------------------------------------+


Subcommands
===========


Subcommand: show
----------------

Show an object

::

    usage: rest_api_wrapper.py show {foo,bar,baz} [--verbose [VERBOSE]] [--env {dev,qa,uat,prod}] [--help] [--ids IDS]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +-------------------+----------------------------+
    | ``{foo,bar,baz}`` | The type of object to show |
    +-------------------+----------------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-----------------------+------------------------------------------------------+
    | ``--help, -h``        | Show this help message and exit (default: ``False``) |
    +-----------------------+------------------------------------------------------+
    | ``--ids IDS, -i IDS`` | The IDs of the objects to show                       |
    +-----------------------+------------------------------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +---------------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE], -v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +---------------------------------------------------+--------------------------------------------------------------------------+
    | ``--env {dev,qa,uat,prod}, -e {dev,qa,uat,prod}`` | Environment to connect to (default: ``'prod'``)                          |
    +---------------------------------------------------+--------------------------------------------------------------------------+


Subcommand: find
----------------

Find objects

::

    usage: rest_api_wrapper.py find {foo,bar} [--verbose [VERBOSE]] [--env {dev,qa,uat,prod}] [--help] [--limit LIMIT]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +-------------+------------------------------------+
    | Subcommands | .. table::                         |
    |             |     :widths: auto                  |
    |             |                                    |
    |             |     +---------+------------------+ |
    |             |     | ``foo`` | Find foo objects | |
    |             |     +---------+------------------+ |
    |             |     | ``bar`` | Find bar objects | |
    |             |     +---------+------------------+ |
    +-------------+------------------------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-----------------------------+------------------------------------------------------+
    | ``--help, -h``              | Show this help message and exit (default: ``False``) |
    +-----------------------------+------------------------------------------------------+
    | ``--limit LIMIT, -L LIMIT`` | The number of results to show (default: ``10``)      |
    +-----------------------------+------------------------------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +---------------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE], -v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +---------------------------------------------------+--------------------------------------------------------------------------+
    | ``--env {dev,qa,uat,prod}, -e {dev,qa,uat,prod}`` | Environment to connect to (default: ``'prod'``)                          |
    +---------------------------------------------------+--------------------------------------------------------------------------+
