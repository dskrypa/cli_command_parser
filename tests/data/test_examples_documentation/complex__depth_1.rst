Complex Example
***************

Simplified example of a complex set of Commands defined across multiple modules.

The expected / intended use case would be for a program that would define an entry point like the following::

    complex_example.py = examples.complex:main


Any number of additional modules could be used, as long as they are imported in the package's ``__init__.py`` with the
base Command so that the base Command is made aware of the presence of the subcommands.

:author: Doug Skrypa


::

    usage: complex_example.py {hello|logs|update} [--verbose [VERBOSE]] [--help]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +-------------+-----------------------+
    | Subcommands | .. table::            |
    |             |     :widths: auto     |
    |             |                       |
    |             |     +------------+--+ |
    |             |     | ``hello``  |  | |
    |             |     +------------+--+ |
    |             |     | ``logs``   |  | |
    |             |     +------------+--+ |
    |             |     | ``update`` |  | |
    |             |     +------------+--+ |
    +-------------+-----------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                                          |
    +-------------------------------------------+--------------------------------------------------------------------------+


Subcommands
===========


Subcommand: hello
-----------------

::

    usage: complex_example.py hello [--verbose [VERBOSE]] [--help] [--name NAME]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                                          |
    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--name NAME``, ``-n NAME``              | The person to say hello to (default: ``'World'``)                        |
    +-------------------------------------------+--------------------------------------------------------------------------+


Subcommand: logs
----------------

::

    usage: complex_example.py logs [--verbose [VERBOSE]] [--help]



.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                                          |
    +-------------------------------------------+--------------------------------------------------------------------------+


Subcommand: update
------------------

::

    usage: complex_example.py update {foo|bar|user|group} [--verbose [VERBOSE]] [--help] [--dry-run] [--ids ID [ID ...]] [--all] [--name NAME] [--description DESCRIPTION]



.. rubric:: Positional arguments

.. table::
    :widths: auto

    +-------------+----------------------+
    | Subcommands | .. table::           |
    |             |     :widths: auto    |
    |             |                      |
    |             |     +-----------+--+ |
    |             |     | ``foo``   |  | |
    |             |     +-----------+--+ |
    |             |     | ``bar``   |  | |
    |             |     +-----------+--+ |
    |             |     | ``user``  |  | |
    |             |     +-----------+--+ |
    |             |     | ``group`` |  | |
    |             |     +-----------+--+ |
    +-------------+----------------------+


.. rubric:: Optional arguments

.. table::
    :widths: auto

    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--verbose [VERBOSE]``, ``-v [VERBOSE]`` | Increase logging verbosity (can specify multiple times) (default: ``0``) |
    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--help``, ``-h``                        | Show this help message and exit                                          |
    +-------------------------------------------+--------------------------------------------------------------------------+
    | ``--dry-run``, ``-D``                     | Print the actions that would be taken instead of taking them             |
    +-------------------------------------------+--------------------------------------------------------------------------+


.. rubric:: Common Fields options

.. table::
    :widths: auto

    +---------------------------------------------------+------------------------------------------------------+
    | ``--name NAME``, ``-n NAME``                      | The new name for the specified item(s)               |
    +---------------------------------------------------+------------------------------------------------------+
    | ``--description DESCRIPTION``, ``-d DESCRIPTION`` | The new description to use for the specified item(s) |
    +---------------------------------------------------+------------------------------------------------------+


.. rubric:: Mutually exclusive options

.. table::
    :widths: auto

    +-------------------------------------------+-------------------------------+
    | ``--ids ID [ID ...]``, ``-i ID [ID ...]`` | The IDs of the item to update |
    +-------------------------------------------+-------------------------------+
    | ``--all``, ``-A``                         | Update all items              |
    +-------------------------------------------+-------------------------------+
