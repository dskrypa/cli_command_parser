Rest Api Wrapper
****************


::

    usage: rest_api_wrapper.py {show|sync|find} [--verbose [VERBOSE]] [--env {dev|qa|uat|prod}] [--help]



.. rubric:: Subcommands

.. table::
    :widths: auto

    +----------+--------------------+
    | ``show`` | Show an object     |
    +----------+--------------------+
    | ``sync`` | Sync group members |
    +----------+--------------------+
    | ``find`` | Find objects       |
    +----------+--------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +--------------------+---------------------------------+
    | ``--help``, ``-h`` | Show this help message and exit |
    +--------------------+---------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--env {dev|qa|uat|prod}``, ``-e {dev|qa|uat|prod}`` | Environment to connect to (default: ``'prod'``)         |
    +-------------------------------------------------------+---------------------------------------------------------+


Subcommands
===========


Subcommand: show
----------------

Show an object

::

    usage: rest_api_wrapper.py show {foo|bar|baz} [--verbose [VERBOSE]] [--env {dev|qa|uat|prod}] [--help] [--ids ID [ID ...]]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +-------------------+----------------------------+
    | ``{foo|bar|baz}`` | The type of object to show |
    +-------------------+----------------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+---------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit |
    +-------------------------------------------+---------------------------------+
    | ``--ids ID [ID ...]``, ``-i ID [ID ...]`` | The IDs of the objects to show  |
    +-------------------------------------------+---------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--env {dev|qa|uat|prod}``, ``-e {dev|qa|uat|prod}`` | Environment to connect to (default: ``'prod'``)         |
    +-------------------------------------------------------+---------------------------------------------------------+


Subcommand: sync
----------------

Sync group members

::

    usage: rest_api_wrapper.py sync [--verbose [VERBOSE]] [--env {dev|qa|uat|prod}] [--help] [--dry-run] [--all] [--role {all|admin|user}] [--group GROUP]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-----------------------+--------------------------------------------------------------+
    | ``--help``, ``-h``    | Show this help message and exit                              |
    +-----------------------+--------------------------------------------------------------+
    | ``--dry-run``, ``-D`` | Print the actions that would be taken instead of taking them |
    +-----------------------+--------------------------------------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--env {dev|qa|uat|prod}``, ``-e {dev|qa|uat|prod}`` | Environment to connect to (default: ``'prod'``)         |
    +-------------------------------------------------------+---------------------------------------------------------+


.. rubric:: Mutually exclusive options

.. table::
    :widths: auto

    +-----------------------------------------------------------------------------------------------------------------+-----------------+
    | ``--all``, ``-a``                                                                                               | Sync all groups |
    +-----------------------------------------------------------------------------------------------------------------+-----------------+
    |                                                                                                                                   |
    | .. rubric:: Optional arguments                                                                                                    |
    |                                                                                                                                   |
    | .. table::                                                                                                                        |
    |     :widths: auto                                                                                                                 |
    |                                                                                                                                   |
    |     +------------------------------------------------------+--------------------------------------------------+                   |
    |     | ``--role {all|admin|user}``, ``-r {all|admin|user}`` | Sync members with this role (default: ``'all'``) |                   |
    |     +------------------------------------------------------+--------------------------------------------------+                   |
    |     | ``--group GROUP``, ``-g GROUP``                      | Sync members for this group                      |                   |
    |     +------------------------------------------------------+--------------------------------------------------+                   |
    +-----------------------------------------------------------------------------------------------------------------+-----------------+


Subcommand: find
----------------

Find objects

::

    usage: rest_api_wrapper.py find {foo|bar|baz|bazs} [--verbose [VERBOSE]] [--env {dev|qa|uat|prod}] [--help] [--limit LIMIT]



.. rubric:: Subcommands

.. table::
    :widths: auto

    +----------+------------------+
    | ``foo``  | Find foo objects |
    +----------+------------------+
    | ``bar``  | Find bar objects |
    +----------+------------------+
    | ``baz``  | Find baz objects |
    +----------+------------------+
    | ``bazs`` | Alias of: baz    |
    +----------+------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +---------------------------------+-------------------------------------------------+
    | ``--help``, ``-h``              | Show this help message and exit                 |
    +---------------------------------+-------------------------------------------------+
    | ``--limit LIMIT``, ``-L LIMIT`` | The number of results to show (default: ``10``) |
    +---------------------------------+-------------------------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--env {dev|qa|uat|prod}``, ``-e {dev|qa|uat|prod}`` | Environment to connect to (default: ``'prod'``)         |
    +-------------------------------------------------------+---------------------------------------------------------+


Subcommand: find foo
--------------------

Find foo objects

::

    usage: rest_api_wrapper.py find foo QUERY [--verbose [VERBOSE]] [--env {dev|qa|uat|prod}] [--help] [--limit LIMIT]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +-----------+-------------------------------------------------+
    | ``QUERY`` | Find foo objects that match the specified query |
    +-----------+-------------------------------------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +---------------------------------+-------------------------------------------------+
    | ``--help``, ``-h``              | Show this help message and exit                 |
    +---------------------------------+-------------------------------------------------+
    | ``--limit LIMIT``, ``-L LIMIT`` | The number of results to show (default: ``10``) |
    +---------------------------------+-------------------------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--env {dev|qa|uat|prod}``, ``-e {dev|qa|uat|prod}`` | Environment to connect to (default: ``'prod'``)         |
    +-------------------------------------------------------+---------------------------------------------------------+


Subcommand: find bar
--------------------

Find bar objects

::

    usage: rest_api_wrapper.py find bar [--verbose [VERBOSE]] [--env {dev|qa|uat|prod}] [--help] [--limit LIMIT] [--pattern PATTERN] [--all]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +---------------------------------------+-------------------------------------------------+
    | ``--help``, ``-h``                    | Show this help message and exit                 |
    +---------------------------------------+-------------------------------------------------+
    | ``--limit LIMIT``, ``-L LIMIT``       | The number of results to show (default: ``10``) |
    +---------------------------------------+-------------------------------------------------+
    | ``--pattern PATTERN``, ``-p PATTERN`` | Pattern to find                                 |
    +---------------------------------------+-------------------------------------------------+
    | ``--all``, ``-a``                     | Show all (default: only even)                   |
    +---------------------------------------+-------------------------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--env {dev|qa|uat|prod}``, ``-e {dev|qa|uat|prod}`` | Environment to connect to (default: ``'prod'``)         |
    +-------------------------------------------------------+---------------------------------------------------------+


Subcommand: find baz
--------------------

Find baz objects

::

    usage: rest_api_wrapper.py find baz [--verbose [VERBOSE]] [--env {dev|qa|uat|prod}] [--help] [--limit LIMIT] [--foo NAME] [--bar ID]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +---------------------------------+-------------------------------------------------+
    | ``--help``, ``-h``              | Show this help message and exit                 |
    +---------------------------------+-------------------------------------------------+
    | ``--limit LIMIT``, ``-L LIMIT`` | The number of results to show (default: ``10``) |
    +---------------------------------+-------------------------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--env {dev|qa|uat|prod}``, ``-e {dev|qa|uat|prod}`` | Environment to connect to (default: ``'prod'``)         |
    +-------------------------------------------------------+---------------------------------------------------------+


.. rubric:: Filter Choices (mutually exclusive)

.. table::
    :widths: auto

    +-----------------------------+--------------------------------------------------------------------+
    | ``--foo NAME``, ``-f NAME`` | Find baz objects related to the foo object with the specified name |
    +-----------------------------+--------------------------------------------------------------------+
    | ``--bar ID``, ``-b ID``     | Find baz objects related to the bar object with the specified ID   |
    +-----------------------------+--------------------------------------------------------------------+


Subcommand: find bazs
---------------------

Find baz objects

::

    usage: rest_api_wrapper.py find bazs [--verbose [VERBOSE]] [--env {dev|qa|uat|prod}] [--help] [--limit LIMIT] [--foo NAME] [--bar ID]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +---------------------------------+-------------------------------------------------+
    | ``--help``, ``-h``              | Show this help message and exit                 |
    +---------------------------------+-------------------------------------------------+
    | ``--limit LIMIT``, ``-L LIMIT`` | The number of results to show (default: ``10``) |
    +---------------------------------+-------------------------------------------------+


.. rubric:: Common options

.. table::
    :widths: auto

    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]``             | Increase logging verbosity (can specify multiple times) |
    +-------------------------------------------------------+---------------------------------------------------------+
    | ``--env {dev|qa|uat|prod}``, ``-e {dev|qa|uat|prod}`` | Environment to connect to (default: ``'prod'``)         |
    +-------------------------------------------------------+---------------------------------------------------------+


.. rubric:: Filter Choices (mutually exclusive)

.. table::
    :widths: auto

    +-----------------------------+--------------------------------------------------------------------+
    | ``--foo NAME``, ``-f NAME`` | Find baz objects related to the foo object with the specified name |
    +-----------------------------+--------------------------------------------------------------------+
    | ``--bar ID``, ``-b ID``     | Find baz objects related to the bar object with the specified ID   |
    +-----------------------------+--------------------------------------------------------------------+
