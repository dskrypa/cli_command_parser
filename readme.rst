******************
CLI Command Parser
******************

|downloads| |py_version| |coverage_badge| |build_status| |Blue|

.. |py_version| image:: https://img.shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20-blue
    :target: https://pypi.org/project/cli-command-parser/

.. |coverage_badge| image:: https://codecov.io/gh/dskrypa/cli_command_parser/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/dskrypa/cli_command_parser

.. |build_status| image:: https://github.com/dskrypa/cli_command_parser/actions/workflows/run-tests.yml/badge.svg
    :target: https://github.com/dskrypa/cli_command_parser/actions/workflows/run-tests.yml

.. |Blue| image:: https://img.shields.io/badge/code%20style-blue-blue.svg
    :target: https://blue.readthedocs.io/

.. |downloads| image:: https://img.shields.io/pypi/dm/cli-command-parser
    :target: https://pypistats.org/packages/cli-command-parser


Command Parser is a class-based CLI argument parser that defines parameters with descriptors.

The primary goals of this project:
  - Make it easy to define subcommands and actions in an clean and organized manner
  - Allow for inheritance so that common parameters don't need to be repeated
  - Make it easy to handle common initialization tasks for all actions / subcommands once
  - Reduce the amount of boilerplate code that is necessary for setting up parsing and handling argument values


Installing CLI Command Parser
-----------------------------

CLI Command Parser is available on PyPI::

    $ pip install cli-command-parser


There are no required dependencies.  Support for formatting wide characters correctly in help text descriptions can
be included by adding `wcwidth <https://wcwidth.readthedocs.io>`__ to your project's requirements, and/or by installing
with optional dependencies::

    $ pip install cli-command-parser[wcwidth]


Documentation & Examples
------------------------

User & API `documentation <https://dskrypa.github.io/cli_command_parser/index.html>`_ is available.

Example scripts using CLI Command Parser can be found in the `examples
<https://github.com/dskrypa/cli_command_parser/tree/main/examples>`_ directory.
